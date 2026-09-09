# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import io
import json
import secrets
import threading
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.routing import APIRoute
from pydantic import ValidationError as PydanticValidationError

from digital_colleagues.api.p11_app import (
    DeploymentDraftMutation,
    ExactPackageMutation,
    install_p11_routes,
)
from digital_colleagues.application.errors import PermissionDeniedError
from digital_colleagues.cli import _normalized_api_origin, _request
from digital_colleagues.core.governance import AuthorizationAction
from digital_colleagues.governance.rbac import action_matrix
from tests.p11.fixtures import ROOT, build_harness


class ApiCliTests(unittest.TestCase):
    def test_exact_api_v1_route_inventory_is_installed(self) -> None:
        app = FastAPI()
        install_p11_routes(
            app,
            authentication=MagicMock(),
            packages=MagicMock(),
            deployments=MagicMock(),
            expected_origin="http://testserver",
        )
        actual = {
            (method, route.path)
            for route in app.routes
            if isinstance(route, APIRoute)
            for method in getattr(route, "methods", set())
            if route.path.startswith("/api/v1")
        }
        expected = {
            ("GET", "/api/v1/catalog"),
            ("GET", "/api/v1/agent-packages"),
            ("POST", "/api/v1/agent-packages"),
            ("POST", "/api/v1/agent-packages/validate"),
            ("POST", "/api/v1/agent-packages/{package_id}/versions/{version}/{digest}/trust"),
            ("POST", "/api/v1/agent-packages/{package_id}/versions/{version}/{digest}/revoke"),
            ("POST", "/api/v1/agent-packages/{package_id}/versions/{version}/{digest}/install"),
            ("GET", "/api/v1/deployment-drafts"),
            ("POST", "/api/v1/deployment-drafts"),
            ("POST", "/api/v1/deployment-drafts/{draft_id}/review"),
            ("POST", "/api/v1/deployment-drafts/{draft_id}/confirm"),
            ("GET", "/api/v1/deployments"),
            ("POST", "/api/v1/deployments/{deployment_id}/lifecycle"),
            ("POST", "/api/v1/deployments/{deployment_id}/upgrade-drafts"),
            ("POST", "/api/v1/deployments/{deployment_id}/rollback-drafts"),
            ("POST", "/api/v1/deployments/{deployment_id}/select"),
            ("GET", "/api/v1/deployments/{deployment_id}/audit"),
        }
        self.assertEqual(actual, expected)

    def test_package_mutation_forbids_caller_authority_fields(self) -> None:
        with self.assertRaises(PydanticValidationError):
            ExactPackageMutation(
                expected_revision=1,
                idempotency_key="key-one",
                tenant_id="caller-tenant",  # type: ignore[call-arg]
            )

    def test_deployment_mutation_forbids_caller_role_and_actor(self) -> None:
        values = {
            "deployment_id": "agent-one",
            "package_id": "fixture-agent",
            "package_version": "1.0.0",
            "package_digest": "sha256:" + "1" * 64,
            "display_name": "Agent One",
            "description": "Description",
            "mission": "Mission",
            "service_relationship": "Serves Admin",
            "granted_capabilities": ["notify_human"],
            "timezone": "UTC",
            "idempotency_key": "create-one",
            "role": "tenant_admin",
            "actor": "human:caller",
        }
        with self.assertRaises(PydanticValidationError):
            DeploymentDraftMutation.model_validate(values)

    def test_console_entry_point_is_exactly_dc(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text()
        self.assertIn('dc = "digital_colleagues.cli:main"', pyproject)

    def test_cli_authentication_uses_only_bounded_stdin_envelope(self) -> None:
        source = (ROOT / "src/digital_colleagues/cli.py").read_text()
        self.assertIn("sys.stdin.buffer.read(STDIN_AUTH_MAX_BYTES + 1)", source)
        self.assertNotIn("os.environ", source)
        self.assertNotIn("--session-cookie", source)
        self.assertNotIn("--csrf-token", source)
        self.assertIn('remote.add_argument("--origin")', source)

    def test_cli_accepts_only_exact_ip_literal_loopback_origins(self) -> None:
        self.assertEqual(
            _normalized_api_origin("http://127.0.0.1:8000/"),
            "http://127.0.0.1:8000",
        )
        self.assertEqual(
            _normalized_api_origin("https://[::1]:8443"),
            "https://[::1]:8443",
        )
        invalid = (
            "http://localhost:8000",
            "http://127.0.0.2:8000",
            "http://0.0.0.0:8000",
            "http://user@127.0.0.1:8000",
            "http://127.0.0.1:8000/api/v1",
            "http://127.0.0.1:8000?value=1",
            "http://127.0.0.1:8000#value",
            "http://127.0.0.1:0",
            "http://127.0.0.1:65536",
            "http://127.0.0.1:not-a-port",
            "http://127.0.0.1:",
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                _normalized_api_origin(value)

    def test_cli_refuses_origin_rebinding_before_reading_credentials(self) -> None:
        output = io.StringIO()
        with (
            patch("digital_colleagues.cli._auth") as authentication,
            redirect_stdout(output),
            self.assertRaises(SystemExit),
        ):
            _request(
                base_url="http://127.0.0.1:8000",
                origin="http://127.0.0.1:8001",
                path="/api/v1/catalog",
                method="GET",
                body=None,
            )
        authentication.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["error"]["code"], "invalid_server")

    def test_cli_redirect_refusal_never_forwards_credentials(self) -> None:
        first_observations: list[tuple[str, bool, bool]] = []
        second_request_count = 0

        class DestinationHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                nonlocal second_request_count
                second_request_count += 1
                self.send_response(200)
                self.end_headers()

            do_POST = do_GET

            def log_message(self, format: str, *args: object) -> None:
                del format, args

        destination = ThreadingHTTPServer(("127.0.0.1", 0), DestinationHandler)
        destination_port = destination.server_address[1]

        class SourceHandler(BaseHTTPRequestHandler):
            def _observe(self) -> None:
                first_observations.append(
                    (
                        self.command,
                        "Cookie" in self.headers,
                        "X-CSRF-Token" in self.headers,
                    )
                )

            def do_GET(self) -> None:
                self._observe()
                payload = b"{}"
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_POST(self) -> None:
                self._observe()
                self.send_response(307)
                self.send_header(
                    "Location",
                    f"http://127.0.0.1:{destination_port}/redirect-target",
                )
                self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                del format, args

        source = ThreadingHTTPServer(("127.0.0.1", 0), SourceHandler)
        source_port = source.server_address[1]
        threads = [
            threading.Thread(target=server.serve_forever, daemon=True)
            for server in (source, destination)
        ]
        for thread in threads:
            thread.start()
        try:
            endpoint = f"http://127.0.0.1:{source_port}"
            self._with_cli_auth(
                lambda: _request(
                    base_url=endpoint,
                    origin=endpoint,
                    path="/api/v1/catalog",
                    method="GET",
                    body=None,
                )
            )
            output = io.StringIO()
            with redirect_stdout(output), self.assertRaises(SystemExit):
                self._with_cli_auth(
                    lambda: _request(
                        base_url=endpoint,
                        origin=endpoint,
                        path="/api/v1/agent-packages",
                        method="POST",
                        body={},
                    )
                )
            self.assertEqual(
                first_observations,
                [("GET", True, False), ("POST", True, True)],
            )
            self.assertEqual(second_request_count, 0)
            self.assertEqual(
                json.loads(output.getvalue())["error"]["code"],
                "remote_request_refused",
            )
        finally:
            source.shutdown()
            destination.shutdown()
            source.server_close()
            destination.server_close()
            for thread in threads:
                thread.join(timeout=2)

    @staticmethod
    def _with_cli_auth(operation: object) -> object:
        envelope = json.dumps(
            {
                "session_cookie": secrets.token_urlsafe(24),
                "csrf_token": secrets.token_urlsafe(24),
            }
        ).encode()
        with patch(
            "digital_colleagues.cli.sys.stdin",
            SimpleNamespace(buffer=io.BytesIO(envelope)),
        ):
            return operation()  # type: ignore[operator]

    def test_p11_role_matrix_is_fail_closed_for_management(self) -> None:
        matrix = action_matrix()
        self.assertIn(AuthorizationAction.MANAGE_DEPLOYMENTS.value, matrix["tenant_admin"])
        self.assertNotIn(AuthorizationAction.MANAGE_DEPLOYMENTS.value, matrix["colleague_user"])
        self.assertNotIn(AuthorizationAction.MANAGE_AGENT_PACKAGES.value, matrix["auditor"])
        self.assertIn(AuthorizationAction.READ_DEPLOYMENT_AUDIT.value, matrix["auditor"])

    def test_csrf_and_origin_are_required_for_p11_mutations(self) -> None:
        with TemporaryDirectory() as value:
            harness = build_harness(Path(value) / "csrf.sqlite")
            try:
                for origin, csrf in (
                    ("http://wrong.invalid", harness.csrf),
                    ("http://testserver", None),
                    ("http://testserver", "wrong-token"),
                ):
                    with (
                        self.subTest(origin=origin, csrf=csrf),
                        self.assertRaises(PermissionDeniedError),
                    ):
                        harness.authentication.authorize_mutation(
                            session_credential=harness.credential,
                            origin=origin,
                            csrf_token=csrf,
                            expected_origin="http://testserver",
                        )
            finally:
                harness.store.close()

    def test_selection_response_never_exposes_session_digests(self) -> None:
        source = (ROOT / "src/digital_colleagues/api/p11_app.py").read_text()
        self.assertNotIn('"credential_digest"', source)
        self.assertNotIn('"csrf_digest"', source)


if __name__ == "__main__":
    unittest.main()
