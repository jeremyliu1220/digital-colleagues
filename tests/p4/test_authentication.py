# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from digital_colleagues.application.errors import ConflictError, PermissionDeniedError
from digital_colleagues.application.p4_contracts import AuthenticatedSession
from digital_colleagues.application.p4_services import AuthenticationService
from digital_colleagues.core.principals import Principal
from digital_colleagues.local.security import (
    CredentialDigests,
    retrieve_bootstrap_for_operator,
)
from tests.p4.fixtures import NOW, build_harness, initial_colleague_body


class P4AuthenticationTests(unittest.TestCase):
    def test_bootstrap_is_strong_one_time_digest_only_and_operator_retrieval_is_atomic(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-auth-") as temporary:
            database = Path(temporary) / "state.sqlite"
            harness = build_harness(database)
            plaintext = retrieve_bootstrap_for_operator(harness.authentication)
            record = harness.store.get_bootstrap("tenant-local")
            assert record is not None
            self.assertEqual(harness.tokens.calls, [32])
            self.assertNotEqual(record.token_digest, plaintext)
            self.assertNotIn(plaintext.encode(), database.read_bytes())

            with self.assertRaises(RuntimeError):
                retrieve_bootstrap_for_operator(harness.authentication)

            grant = harness.authentication.exchange(plaintext)
            self.assertEqual(grant.session.principal.kind.value, "human")
            self.assertEqual(
                tuple(role.value for role in grant.session.principal.roles),
                ("tenant_admin",),
            )
            self.assertNotIn(grant.session_credential.encode(), database.read_bytes())
            row = harness.store._connection.execute(  # noqa: SLF001
                "SELECT credential_digest, csrf_digest FROM p4_sessions"
            ).fetchone()
            self.assertTrue(row["credential_digest"].startswith("sha256:"))
            self.assertTrue(row["csrf_digest"].startswith("sha256:"))
            with self.assertRaises(ConflictError):
                harness.authentication.exchange(plaintext)
            harness.store.close()

    def test_bootstrap_and_session_expiry_origin_csrf_and_principal_kind_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-auth-expiry-") as temporary:
            database = Path(temporary) / "state.sqlite"
            harness = build_harness(database)
            _, plaintext = harness.authentication.ensure_bootstrap()
            assert plaintext is not None
            harness.authentication.claim_operator_retrieval(plaintext)

            expired = AuthenticationService(
                store=harness.store,
                clock=type(harness.clock)(NOW + timedelta(minutes=10)),
                tokens=harness.tokens,
                digests=CredentialDigests(),
                tenant_id="tenant-local",
            )
            with self.assertRaises(PermissionDeniedError):
                expired.exchange(plaintext)
            harness.store.close()

        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-session-") as temporary:
            harness = build_harness(Path(temporary) / "state.sqlite")
            _, plaintext = harness.authentication.ensure_bootstrap()
            assert plaintext is not None
            harness.authentication.claim_operator_retrieval(plaintext)
            grant = harness.authentication.exchange(plaintext)
            with self.assertRaises(PermissionDeniedError):
                harness.authentication.authorize_mutation(
                    session_credential=grant.session_credential,
                    origin="http://cross-origin.invalid",
                    csrf_token=grant.csrf_token,
                    expected_origin="http://testserver",
                )
            with self.assertRaises(PermissionDeniedError):
                harness.authentication.authorize_mutation(
                    session_credential=grant.session_credential,
                    origin="http://testserver",
                    csrf_token="wrong-csrf",
                    expected_origin="http://testserver",
                )
            resolved = harness.authentication.authorize_mutation(
                session_credential=grant.session_credential,
                origin="http://testserver",
                csrf_token=grant.csrf_token,
                expected_origin="http://testserver",
            )
            self.assertEqual(resolved.session_id, grant.session.session_id)

            service = Principal.service(tenant_id="tenant-local", principal_id="service-test")
            invalid = AuthenticatedSession(
                tenant_id="tenant-local",
                session_id="session:invalid-kind",
                principal=service,
                credential_digest="sha256:" + ("1" * 64),
                csrf_digest="sha256:" + ("2" * 64),
            )
            with self.assertRaises(PermissionDeniedError):
                harness.authentication.bind_colleague(invalid, "colleague-invalid")

            expired_session = AuthenticationService(
                store=harness.store,
                clock=type(harness.clock)(NOW + timedelta(hours=8)),
                tokens=harness.tokens,
                digests=CredentialDigests(),
                tenant_id="tenant-local",
            )
            with self.assertRaises(PermissionDeniedError):
                expired_session.resolve(grant.session_credential)
            harness.store.close()

    def test_https_mode_sets_secure_cookie_without_exposing_server_session_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-cookie-") as temporary:
            harness = build_harness(Path(temporary) / "state.sqlite")
            plaintext = retrieve_bootstrap_for_operator(harness.authentication)
            client = TestClient(harness.app(secure_cookie=True), base_url="https://testserver")
            response = client.post(
                "/auth/bootstrap/exchange",
                headers={"Origin": "http://testserver"},
                json={"token": plaintext},
            )
            self.assertEqual(response.status_code, 201, response.text)
            cookie = response.headers["set-cookie"].lower()
            self.assertIn("secure", cookie)
            self.assertIn("httponly", cookie)
            self.assertIn("samesite=strict", cookie)
            self.assertNotIn("session_id", response.json())
            harness.store.close()

    def test_expired_revoked_and_stale_human_sessions_fail_at_interactive_api(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-api-expired-") as temporary:
            harness = build_harness(Path(temporary) / "state.sqlite")
            plaintext = retrieve_bootstrap_for_operator(harness.authentication)
            grant = harness.authentication.exchange(plaintext)
            expired = AuthenticationService(
                store=harness.store,
                clock=type(harness.clock)(NOW + timedelta(hours=8)),
                tokens=harness.tokens,
                digests=CredentialDigests(),
                tenant_id="tenant-local",
            )
            harness.authentication = expired
            client = TestClient(harness.app())
            client.cookies.set("dc_session", grant.session_credential)
            self.assertEqual(client.get("/auth/session").status_code, 403)
            self.assertEqual(
                client.post(
                    "/colleagues/preview",
                    headers={"Origin": "http://testserver", "X-CSRF-Token": grant.csrf_token},
                    json=initial_colleague_body(),
                ).status_code,
                403,
            )
            harness.store.close()

        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-api-revoked-") as temporary:
            harness = build_harness(Path(temporary) / "state.sqlite")
            plaintext = retrieve_bootstrap_for_operator(harness.authentication)
            grant = harness.authentication.exchange(plaintext)
            harness.store._connection.execute(  # noqa: SLF001
                "UPDATE p4_sessions SET revoked_at = expires_at, revision = revision + 1"
            )
            harness.store._connection.commit()  # noqa: SLF001
            client = TestClient(harness.app())
            client.cookies.set("dc_session", grant.session_credential)
            self.assertEqual(client.get("/auth/session").status_code, 403)
            with self.assertRaises(PermissionDeniedError):
                harness.authentication.authorize_mutation(
                    session_credential=grant.session_credential,
                    origin="http://testserver",
                    csrf_token=grant.csrf_token,
                    expected_origin="http://testserver",
                )
            harness.store.close()

        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-api-stale-") as temporary:
            harness = build_harness(Path(temporary) / "state.sqlite")
            plaintext = retrieve_bootstrap_for_operator(harness.authentication)
            grant = harness.authentication.exchange(plaintext)
            client = TestClient(harness.app())
            client.cookies.set("dc_session", grant.session_credential)
            created = client.post(
                "/colleagues",
                headers={"Origin": "http://testserver", "X-CSRF-Token": grant.csrf_token},
                json=initial_colleague_body(),
            )
            self.assertEqual(created.status_code, 201, created.text)
            with self.assertRaises(ConflictError):
                harness.store.set_active_colleague(
                    session=grant.session,
                    colleague_id=created.json()["namespace"]["scope_id"],
                    occurred_at=NOW,
                )
            harness.store.close()


if __name__ == "__main__":
    unittest.main()
