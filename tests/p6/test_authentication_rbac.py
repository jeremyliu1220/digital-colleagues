# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from digital_colleagues.adapters.sqlite.p6_store import SQLiteP6Store
from digital_colleagues.adapters.system.deterministic import FixedClock
from digital_colleagues.application.errors import (
    ConflictError,
    PermissionDeniedError,
)
from digital_colleagues.application.p4_contracts import SessionGrant
from digital_colleagues.application.p6_contracts import (
    CredentialGrant,
    EnrollmentAuthorizationRequest,
    RecoveryAuthorizationRequest,
)
from digital_colleagues.application.p6_services import P6AuthenticationService
from digital_colleagues.core.errors import AuthorizationError
from digital_colleagues.core.governance import (
    AuthorizationAction,
    Membership,
    MembershipStatus,
)
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import HumanRole, Principal
from digital_colleagues.governance.rbac import action_matrix, authorize_action
from tests.p6.fixtures import NOW, ORIGIN, P6Harness, build_harness


def bootstrap(harness: P6Harness) -> tuple[str, SessionGrant]:
    _, plaintext = harness.authentication.ensure_bootstrap()
    assert plaintext is not None
    harness.authentication.claim_operator_retrieval(plaintext)
    grant = harness.authentication.exchange(plaintext)
    return grant.session_credential, grant


def enroll(
    harness: P6Harness,
    *,
    issuer: SessionGrant,
    role: HumanRole,
    scopes: tuple[str, ...],
    key: str,
    decision_id: str | None = None,
) -> tuple[str, CredentialGrant]:
    session = issuer.session
    credential = harness.authentication.authorize_enrollment(
        session=session,
        request=EnrollmentAuthorizationRequest(
            role=role,
            colleague_ids=scopes,
            idempotency_key=key,
            approved_change_decision_id=decision_id,
        ),
    )
    token = harness.authentication.retrieve_operator_credential(credential.credential_id)
    grant = harness.authentication.exchange_enrollment(token)
    return token, grant


class P6AuthenticationRbacTests(unittest.TestCase):
    def test_second_admin_transition_is_single_use_and_credentials_are_digest_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-auth-") as name:
            database = Path(name) / "state.sqlite"
            harness = build_harness(database)
            _, first = bootstrap(harness)
            token, second = enroll(
                harness,
                issuer=first,
                role=HumanRole.TENANT_ADMIN,
                scopes=("*",),
                key="second-admin",
            )
            self.assertNotIn(token.encode(), database.read_bytes())
            self.assertEqual(second.membership.roles, (HumanRole.TENANT_ADMIN,))
            transition = harness.store._connection.execute(  # noqa: SLF001
                "SELECT state, consumed_principal_id FROM p6_bootstrap_transitions"
            ).fetchone()
            self.assertEqual(transition["state"], "consumed")
            self.assertEqual(transition["consumed_principal_id"], second.membership.principal_id)
            with self.assertRaises(PermissionDeniedError):
                harness.authentication.exchange_enrollment(token)
            with self.assertRaises(PermissionDeniedError):
                harness.authentication.authorize_enrollment(
                    session=first.session,
                    request=EnrollmentAuthorizationRequest(
                        role=HumanRole.TENANT_ADMIN,
                        colleague_ids=("*",),
                        idempotency_key="third-admin-without-change",
                    ),
                )
            harness.store.close()

    def test_scoped_roles_matrix_api_authority_injection_and_idor_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-rbac-") as name:
            harness = build_harness(Path(name) / "state.sqlite")
            first_cookie, first = bootstrap(harness)
            _, second = enroll(
                harness,
                issuer=first,
                role=HumanRole.TENANT_ADMIN,
                scopes=("*",),
                key="second-admin",
            )
            _, user = enroll(
                harness,
                issuer=first,
                role=HumanRole.COLLEAGUE_USER,
                scopes=("colleague:alpha",),
                key="scoped-user",
            )
            _, auditor = enroll(
                harness,
                issuer=second.session_grant,
                role=HumanRole.AUDITOR,
                scopes=("colleague:alpha",),
                key="scoped-auditor",
            )
            matrix = action_matrix()
            self.assertIn(AuthorizationAction.MANAGE_CREDENTIAL.value, matrix["tenant_admin"])
            self.assertIn(AuthorizationAction.DECIDE_EFFECT.value, matrix["colleague_user"])
            self.assertEqual(
                set(matrix["auditor"]),
                {
                    AuthorizationAction.READ_SESSION_SECURITY.value,
                    AuthorizationAction.READ_COLLEAGUE.value,
                    AuthorizationAction.READ_GOVERNANCE.value,
                    AuthorizationAction.EXPORT_AUDIT.value,
                },
            )
            with self.assertRaises(AuthorizationError):
                authorize_action(
                    principal=user.session_grant.session.principal,
                    membership=user.membership,
                    action=AuthorizationAction.READ_COLLEAGUE,
                    namespace=Namespace.colleague("tenant-local", "colleague:other"),
                )
            with self.assertRaises(AuthorizationError):
                authorize_action(
                    principal=auditor.session_grant.session.principal,
                    membership=auditor.membership,
                    action=AuthorizationAction.ASSIGN_WORK,
                    namespace=Namespace.colleague("tenant-local", "colleague:alpha"),
                )
            model = Principal.model(tenant_id="tenant-local", principal_id="model:forgery")
            forged = Membership(
                namespace=model.namespace,
                membership_id="membership:forgery",
                principal_id=model.principal_id,
                roles=(HumanRole.TENANT_ADMIN,),
                colleague_ids=("*",),
                status=MembershipStatus.ACTIVE,
                role_revision=1,
                membership_revision=1,
                issued_by=first.session.principal,
                created_at=NOW,
                updated_at=NOW,
                correlation_id="correlation:forgery",
                causation_id="cause:forgery",
            )
            with self.assertRaises(AuthorizationError):
                authorize_action(
                    principal=model,
                    membership=forged,
                    action=AuthorizationAction.MANAGE_MEMBERSHIP,
                    namespace=Namespace.tenant("tenant-local"),
                )

            client = TestClient(harness.app())
            client.cookies.set("dc_session", first_cookie)
            session_response = client.get("/auth/session")
            self.assertEqual(session_response.status_code, 200, session_response.text)
            csrf = session_response.json()["csrf_token"]
            injected = client.post(
                "/governance/enrollments/users",
                headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
                json={
                    "colleague_ids": ["colleague:alpha"],
                    "idempotency_key": "api-injection",
                    "role": "tenant_admin",
                    "tenant_id": "tenant:other",
                    "principal_id": "human:chosen",
                },
            )
            self.assertEqual(injected.status_code, 422, injected.text)
            missing_csrf = client.post(
                "/governance/recovery",
                headers={"Origin": ORIGIN},
                json={
                    "principal_id": user.membership.principal_id,
                    "idempotency_key": "missing-csrf",
                },
            )
            self.assertEqual(missing_csrf.status_code, 403, missing_csrf.text)
            wrong_origin = client.post(
                "/governance/recovery",
                headers={"Origin": "http://cross-site.invalid", "X-CSRF-Token": csrf},
                json={
                    "principal_id": user.membership.principal_id,
                    "idempotency_key": "wrong-origin",
                },
            )
            self.assertEqual(wrong_origin.status_code, 403, wrong_origin.text)

            user_client = TestClient(harness.app())
            user_client.cookies.set("dc_session", user.session_grant.session_credential)
            user_rbac = user_client.get("/governance/rbac")
            self.assertEqual(user_rbac.status_code, 200, user_rbac.text)
            user_state = user_client.get("/governance/state")
            self.assertEqual(user_state.status_code, 200, user_state.text)
            self.assertEqual(user_state.json()["credentials"], [])
            self.assertEqual(user_state.json()["change_proposals"], [])

            auditor_client = TestClient(harness.app())
            auditor_client.cookies.set("dc_session", auditor.session_grant.session_credential)
            auditor_state = auditor_client.get("/governance/state")
            self.assertEqual(auditor_state.status_code, 200, auditor_state.text)
            auditor_mutation = auditor_client.post(
                "/governance/recovery",
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": auditor.session_grant.csrf_token,
                },
                json={
                    "principal_id": auditor.membership.principal_id,
                    "idempotency_key": "auditor-recovery-bypass",
                },
            )
            self.assertEqual(auditor_mutation.status_code, 403, auditor_mutation.text)
            harness.store.close()

    def test_recovery_rotates_session_and_revoked_expired_or_guessed_tokens_fail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-recovery-") as name:
            harness = build_harness(Path(name) / "state.sqlite")
            _, first = bootstrap(harness)
            _, second = enroll(
                harness,
                issuer=first,
                role=HumanRole.TENANT_ADMIN,
                scopes=("*",),
                key="second-admin",
            )
            _, user = enroll(
                harness,
                issuer=first,
                role=HumanRole.COLLEAGUE_USER,
                scopes=("colleague:alpha",),
                key="user",
            )
            old_session = user.session_grant.session_credential
            recovery = harness.authentication.authorize_recovery(
                session=second.session_grant.session,
                request=RecoveryAuthorizationRequest(
                    principal_id=user.membership.principal_id,
                    idempotency_key="recover-user",
                ),
            )
            token = harness.authentication.retrieve_operator_credential(recovery.credential_id)
            rotated = harness.authentication.exchange_recovery(token)
            with self.assertRaises(PermissionDeniedError):
                harness.authentication.resolve(old_session)
            self.assertEqual(
                harness.authentication.resolve(
                    rotated.session_grant.session_credential
                ).principal.principal_id,
                user.membership.principal_id,
            )
            with self.assertRaises(PermissionDeniedError):
                harness.authentication.exchange_recovery(token)
            with self.assertRaises(PermissionDeniedError):
                harness.authentication.exchange_recovery("g" * 64)

            stale = harness.authentication.authorize_recovery(
                session=first.session,
                request=RecoveryAuthorizationRequest(
                    principal_id=user.membership.principal_id,
                    idempotency_key="stale-recovery-binding",
                ),
            )
            stale_token = harness.authentication.retrieve_operator_credential(stale.credential_id)
            harness.store._connection.execute(  # noqa: SLF001
                "UPDATE p6_memberships SET membership_revision = membership_revision + 1 "
                "WHERE tenant_id = ? AND principal_id = ?",
                ("tenant-local", user.membership.principal_id),
            )
            with self.assertRaises(PermissionDeniedError):
                harness.authentication.exchange_recovery(stale_token)

            revoked = harness.authentication.authorize_recovery(
                session=first.session,
                request=RecoveryAuthorizationRequest(
                    principal_id=user.membership.principal_id,
                    idempotency_key="revoked-recovery",
                ),
            )
            harness.store.revoke_credential(
                tenant_id="tenant-local",
                credential_id=revoked.credential_id,
                actor=first.session.principal,
                occurred_at=NOW,
            )
            with self.assertRaises(ConflictError):
                harness.authentication.retrieve_operator_credential(revoked.credential_id)

            expired = harness.authentication.authorize_recovery(
                session=first.session,
                request=RecoveryAuthorizationRequest(
                    principal_id=user.membership.principal_id,
                    idempotency_key="expired-recovery",
                ),
            )
            retrieved_expired = harness.authentication.authorize_recovery(
                session=first.session,
                request=RecoveryAuthorizationRequest(
                    principal_id=user.membership.principal_id,
                    idempotency_key="retrieved-expired-recovery",
                ),
            )
            retrieved_expired_token = harness.authentication.retrieve_operator_credential(
                retrieved_expired.credential_id
            )
            expired_authentication = P6AuthenticationService(
                store=harness.store,
                clock=FixedClock(NOW + timedelta(minutes=11)),
                tokens=harness.tokens,
                digests=harness.digests,
                identifiers=harness.identifiers,
                tenant_id="tenant-local",
            )
            with self.assertRaises(PermissionDeniedError):
                expired_authentication.retrieve_operator_credential(expired.credential_id)
            with self.assertRaises(PermissionDeniedError):
                expired_authentication.exchange_recovery(retrieved_expired_token)
            expired_row = harness.store._connection.execute(  # noqa: SLF001
                "SELECT state, token_digest FROM p6_governance_credentials WHERE credential_id = ?",
                (retrieved_expired.credential_id,),
            ).fetchone()
            self.assertEqual(expired_row["state"], "expired")
            self.assertIsNone(expired_row["token_digest"])
            harness.store.close()

    def test_role_and_membership_revisions_are_checked_on_every_session_use(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-session-revision-") as name:
            harness = build_harness(Path(name) / "state.sqlite")
            _, first = bootstrap(harness)
            current = harness.store.membership_for_principal(
                "tenant-local", first.session.principal.principal_id
            )
            harness.store._connection.execute(  # noqa: SLF001
                "UPDATE p6_memberships SET membership_revision = membership_revision + 1 "
                "WHERE tenant_id = ? AND principal_id = ?",
                ("tenant-local", current.principal_id),
            )
            with self.assertRaises(PermissionDeniedError):
                harness.authentication.resolve(first.session_credential)
            harness.store.close()

    def test_concurrent_enrollment_consumption_has_exactly_one_atomic_winner(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-token-race-") as name:
            database = Path(name) / "state.sqlite"
            harness = build_harness(database)
            _, first = bootstrap(harness)
            credential = harness.authentication.authorize_enrollment(
                session=first.session,
                request=EnrollmentAuthorizationRequest(
                    role=HumanRole.COLLEAGUE_USER,
                    colleague_ids=("colleague:alpha",),
                    idempotency_key="concurrent-user",
                ),
            )
            plaintext = harness.authentication.retrieve_operator_credential(
                credential.credential_id
            )
            harness.store.close()
            barrier = threading.Barrier(2)

            def consume(index: int) -> str:
                store = SQLiteP6Store(
                    database,
                    migrations_path=Path(__file__).resolve().parents[2] / "migrations",
                    clock=FixedClock(NOW),
                )
                authentication = P6AuthenticationService(
                    store=store,
                    clock=FixedClock(NOW),
                    tokens=type(harness.tokens)([]),
                    digests=harness.digests,
                    identifiers=harness.identifiers,
                    tenant_id="tenant-local",
                )
                try:
                    barrier.wait()
                    authentication.exchange_enrollment(plaintext)
                    return f"winner-{index}"
                except (PermissionDeniedError, ConflictError):
                    return "refused"
                finally:
                    store.close()

            with ThreadPoolExecutor(max_workers=2) as executor:
                outcomes = list(executor.map(consume, (1, 2)))
            self.assertEqual(outcomes.count("refused"), 1)
            self.assertEqual(sum(value.startswith("winner-") for value in outcomes), 1)
            recovered = SQLiteP6Store(
                database,
                migrations_path=Path(__file__).resolve().parents[2] / "migrations",
                clock=FixedClock(NOW),
            )
            row = recovered._connection.execute(  # noqa: SLF001
                "SELECT state, consumed_principal_id FROM p6_governance_credentials "
                "WHERE credential_id = ?",
                (credential.credential_id,),
            ).fetchone()
            self.assertEqual(row["state"], "consumed")
            self.assertIsNotNone(row["consumed_principal_id"])
            recovered.close()


if __name__ == "__main__":
    unittest.main()
