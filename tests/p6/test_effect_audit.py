# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from typing import cast

from fastapi.testclient import TestClient

from digital_colleagues.adapters.channel.reference import ReferenceChannel
from digital_colleagues.adapters.sqlite.p6_store import SQLiteP6Store
from digital_colleagues.adapters.system.deterministic import FixedClock
from digital_colleagues.application.contracts import RequestPrincipalContext
from digital_colleagues.application.errors import PermissionDeniedError
from digital_colleagues.application.p5_services import P5DispatchAuthorizer
from digital_colleagues.application.p6_services import P6DispatchAuthorizer
from digital_colleagues.application.ports import IdentifierPort
from digital_colleagues.application.services import ApprovalService, DispatchService
from digital_colleagues.core.effects import HumanApprovalDecision
from digital_colleagues.core.errors import AuthorizationError, CoreInvariantError
from digital_colleagues.core.governance import (
    AuditExportQuery,
    Membership,
    MembershipStatus,
)
from digital_colleagues.core.principals import HumanRole
from scripts.check_p6_abuse import (
    observe_unauthorized_proposal_escape,
    require_zero_unauthorized_escape,
)
from scripts.p6_gate_support import FocusedGateError
from tests.p3.fixtures import T0, T2, T3, admin, approval_request, namespace, service, user
from tests.p3.scenario import prepare_proposal
from tests.p6.fixtures import NOW, ROOT, build_harness, initial_request
from tests.p6.test_authentication_rbac import bootstrap, enroll


def _effect_store(
    database: Path,
) -> tuple[SQLiteP6Store, IdentifierPort, HumanApprovalDecision]:
    scenario = prepare_proposal(database, identifier_namespace="p6-effect")
    proposal = scenario.proposal
    identifiers = scenario.identifiers
    scenario.store.close()
    store = SQLiteP6Store(database, migrations_path=ROOT / "migrations", clock=FixedClock(T0))
    for principal, role, scopes in (
        (admin(), HumanRole.TENANT_ADMIN, ("*",)),
        (user(), HumanRole.COLLEAGUE_USER, (namespace().scope_id or "missing",)),
    ):
        membership = Membership(
            namespace=principal.namespace,
            membership_id="membership:" + principal.principal_id,
            principal_id=principal.principal_id,
            roles=(role,),
            colleague_ids=scopes,
            status=MembershipStatus.ACTIVE,
            role_revision=1,
            membership_revision=1,
            issued_by=admin(),
            created_at=T0,
            updated_at=T0,
            correlation_id="correlation:membership:" + principal.principal_id,
            causation_id="cause:membership:" + principal.principal_id,
        )
        with store._transaction() as connection:  # noqa: SLF001
            store._insert_membership(connection, membership)  # noqa: SLF001
    decision, _, created = ApprovalService(
        store=store,
        clock=FixedClock(T2),
        identifiers=identifiers,
        service_principal=service(),
    ).decide(
        context=RequestPrincipalContext(namespace(), user()),
        mandate_id="mandate-synthetic",
        expected_mandate_revision=1,
        request=approval_request(proposal),
    )
    assert created
    return store, identifiers, decision


class P6EffectAuditTests(unittest.TestCase):
    def test_escape_metric_is_observed_and_fault_injection_fails_closed(self) -> None:
        observed = observe_unauthorized_proposal_escape()
        require_zero_unauthorized_escape(observed)
        self.assertEqual(observed["status"], "observed")
        self.assertEqual(observed["numerator"], 0)
        self.assertEqual(observed["denominator"], 1)
        self.assertEqual(observed["safe_refusal_count"], 1)
        attempts = cast(list[dict[str, object]], observed["evaluated_attempts"])
        self.assertEqual(len(attempts), 1)
        self.assertFalse(attempts[0]["escaped"])
        self.assertTrue(observed["safe_causal_references"])

        escaped = observe_unauthorized_proposal_escape(fault_escape=True)
        self.assertEqual(escaped["numerator"], 1)
        self.assertEqual(escaped["denominator"], 1)
        self.assertEqual(escaped["safe_refusal_count"], 0)
        escaped_attempts = cast(list[dict[str, object]], escaped["evaluated_attempts"])
        self.assertTrue(escaped_attempts[0]["escaped"])
        with self.assertRaisesRegex(FocusedGateError, "unauthorized proposal candidate escaped"):
            require_zero_unauthorized_escape(escaped)

    def test_effect_dispatch_revalidates_current_membership_and_expiry(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-effect-") as name:
            store, identifiers, decision = _effect_store(Path(name) / "state.sqlite")
            binding = store._connection.execute(  # noqa: SLF001
                "SELECT principal_id, role_revision, membership_revision "
                "FROM p6_effect_approval_bindings"
            ).fetchone()
            self.assertEqual(binding["principal_id"], user().principal_id)
            self.assertEqual((binding["role_revision"], binding["membership_revision"]), (1, 1))
            authorizer = P6DispatchAuthorizer(
                p5=P5DispatchAuthorizer(store), store=store, clock=FixedClock(T3)
            )
            authorizer.authorize(store.get_proposal(namespace(), decision.proposal_id), decision)

            store._connection.execute(  # noqa: SLF001
                "UPDATE p6_memberships SET membership_revision = 2 "
                "WHERE tenant_id = ? AND principal_id = ?",
                (namespace().tenant_id, user().principal_id),
            )
            channel = ReferenceChannel()
            dispatch = DispatchService(
                store=store,
                channel=channel,
                clock=FixedClock(T3),
                identifiers=identifiers,
                result_actor=service(),
                owner_id="worker-p6-stale-role",
                mandate_id="mandate-synthetic",
                policy_authorizer=authorizer,
            )
            with self.assertRaises((PermissionDeniedError, AuthorizationError)):
                dispatch.dispatch_once(namespace())
            self.assertEqual(channel.call_count, 0)
            store.close()

        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-effect-expired-") as name:
            store, identifiers, _ = _effect_store(Path(name) / "state.sqlite")
            channel = ReferenceChannel()
            dispatch = DispatchService(
                store=store,
                channel=channel,
                clock=FixedClock(T2 + timedelta(minutes=16)),
                identifiers=identifiers,
                result_actor=service(),
                owner_id="worker-p6-expired-approval",
                mandate_id="mandate-synthetic",
                policy_authorizer=P6DispatchAuthorizer(
                    p5=P5DispatchAuthorizer(store),
                    store=store,
                    clock=FixedClock(T2 + timedelta(minutes=16)),
                ),
            )
            with self.assertRaises((PermissionDeniedError, AuthorizationError)):
                dispatch.dispatch_once(namespace())
            self.assertEqual(channel.call_count, 0)
            store.close()

    def test_audit_export_is_scoped_bounded_redacted_authorized_and_restart_stable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-audit-") as name:
            database = Path(name) / "state.sqlite"
            harness = build_harness(database)
            _, first = bootstrap(harness)
            _, second = enroll(
                harness,
                issuer=first,
                role=HumanRole.TENANT_ADMIN,
                scopes=("*",),
                key="second-admin",
            )
            profile, _, _ = harness.colleagues.create(
                session=first.session, request=initial_request()
            )
            colleague_id = profile.namespace.scope_id
            assert colleague_id is not None
            admin_session = harness.authentication.bind_colleague(first.session, colleague_id)
            _, auditor = enroll(
                harness,
                issuer=second.session_grant,
                role=HumanRole.AUDITOR,
                scopes=(colleague_id,),
                key="auditor",
            )
            _, colleague_user = enroll(
                harness,
                issuer=second.session_grant,
                role=HumanRole.COLLEAGUE_USER,
                scopes=(colleague_id,),
                key="user",
            )
            harness.builder.create(session=admin_session, idempotency_key="admin-visible-draft")
            user_client = TestClient(harness.app())
            user_client.cookies.set("dc_session", colleague_user.session_grant.session_credential)
            safe_p5_state = user_client.get("/p5/studio/state")
            self.assertEqual(safe_p5_state.status_code, 200, safe_p5_state.text)
            self.assertEqual(safe_p5_state.json()["drafts"], [])
            refused_draft_list = user_client.get("/colleagues/drafts")
            self.assertEqual(refused_draft_list.status_code, 403, refused_draft_list.text)
            with self.assertRaises(PermissionDeniedError):
                harness.builder.create(
                    session=colleague_user.session_grant.session,
                    idempotency_key="user-draft-bypass",
                )
            query = AuditExportQuery(
                namespace=profile.namespace,
                start_at=NOW - timedelta(minutes=1),
                end_at=NOW + timedelta(minutes=1),
                record_types=("profile", "mandate"),
                limit=10,
            )
            records = harness.audit.export(session=auditor.session_grant.session, query=query)
            self.assertEqual(
                records,
                harness.audit.export(session=auditor.session_grant.session, query=query),
            )
            self.assertTrue(records)
            self.assertEqual(
                records,
                tuple(
                    sorted(
                        records,
                        key=lambda item: (
                            item.occurred_at,
                            item.record_type,
                            item.record_id,
                            item.record_revision,
                        ),
                    )
                ),
            )
            self.assertTrue(
                all(
                    dict(item.safe_projection.items()) == {"private_payload_redacted": True}
                    for item in records
                )
            )
            self.assertNotIn("Atlas", str(records))
            with self.assertRaises(PermissionDeniedError):
                harness.audit.export(session=colleague_user.session_grant.session, query=query)
            with self.assertRaises(AuthorizationError):
                AuditExportQuery(
                    namespace=profile.namespace,
                    start_at=query.start_at,
                    end_at=query.end_at,
                    record_types=("audit_export",),
                    limit=10,
                )
            with self.assertRaises(CoreInvariantError):
                AuditExportQuery(
                    namespace=profile.namespace,
                    start_at=query.start_at,
                    end_at=query.end_at,
                    record_types=("profile",),
                    limit=501,
                )
            harness.store.close()

            restarted = build_harness(database)
            recovered_session = restarted.authentication.resolve(first.session_credential)
            recovered = restarted.audit.export(session=recovered_session, query=query)
            self.assertEqual(records, recovered)
            export_audit_count = restarted.store._connection.execute(  # noqa: SLF001
                "SELECT COUNT(*) FROM p6_governance_audit WHERE record_type = 'audit_export'"
            ).fetchone()[0]
            self.assertGreaterEqual(export_audit_count, 1)
            self.assertEqual(
                recovered_session.active_colleague_id, admin_session.active_colleague_id
            )
            restarted.store.close()


if __name__ == "__main__":
    unittest.main()
