# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.routing import APIRoute
from pydantic import ValidationError as PydanticValidationError

from digital_colleagues.api.p11_app import (
    DeploymentDraftMutation,
    ExactPackageMutation,
    install_p11_routes,
)
from digital_colleagues.application.errors import PermissionDeniedError
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
