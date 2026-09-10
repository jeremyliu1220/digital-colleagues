# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_p11r_ci_policy import (
    EXPECTED_WORKFLOW,
    PACKAGE_MANAGER,
    check_ci_policy,
)
from scripts.check_p11r_repository import P11RGateError


class CiPolicyTests(unittest.TestCase):
    def _root(self, temporary: str, workflow: str = EXPECTED_WORKFLOW) -> Path:
        root = Path(temporary)
        (root / ".github/workflows").mkdir(parents=True)
        (root / "studio").mkdir()
        (root / ".github/workflows/ci.yml").write_text(workflow, encoding="utf-8")
        (root / ".nvmrc").write_text("24.15.0\n", encoding="utf-8")
        (root / "studio/package.json").write_text(
            json.dumps(
                {
                    "packageManager": PACKAGE_MANAGER,
                    "engines": {"node": ">=24.15.0 <25"},
                }
            ),
            encoding="utf-8",
        )
        return root

    def _rejects(self, before: str, after: str) -> None:
        with TemporaryDirectory() as value:
            root = self._root(value, EXPECTED_WORKFLOW.replace(before, after, 1))
            with self.assertRaises(P11RGateError):
                check_ci_policy(root)

    def test_exact_canonical_workflow_passes(self) -> None:
        with TemporaryDirectory() as value:
            result = check_ci_policy(self._root(value))
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["node_version"], "24.15.0")
        self.assertEqual(result["publication_command_count"], 0)

    def test_pull_request_target_is_rejected(self) -> None:
        self._rejects("pull_request:", "pull_request_target:")

    def test_workflow_dispatch_is_rejected(self) -> None:
        self._rejects("  push:\n", "  workflow_dispatch:\n  push:\n")

    def test_schedule_is_rejected(self) -> None:
        self._rejects("  push:\n", "  schedule:\n    - cron: '0 0 * * *'\n  push:\n")

    def test_write_permission_is_rejected(self) -> None:
        self._rejects("contents: read", "contents: write")

    def test_oidc_permission_is_rejected(self) -> None:
        self._rejects("  contents: read\n", "  contents: read\n  id-token: write\n")

    def test_secret_context_is_rejected(self) -> None:
        self._rejects("PYTHONPATH: src", "PYTHONPATH: ${{ secrets.RUNTIME_PATH }}")

    def test_mutable_action_reference_is_rejected(self) -> None:
        self._rejects(
            "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
            "actions/checkout@v6",
        )

    def test_persisted_checkout_credentials_are_rejected(self) -> None:
        self._rejects("persist-credentials: false", "persist-credentials: true")

    def test_direct_node_version_is_rejected(self) -> None:
        self._rejects("node-version-file: .nvmrc", 'node-version: "24.15.0"')

    def test_wrong_node_file_content_is_rejected(self) -> None:
        with TemporaryDirectory() as value:
            root = self._root(value)
            (root / ".nvmrc").write_text("24.20.0\n", encoding="utf-8")
            with self.assertRaises(P11RGateError):
                check_ci_policy(root)

    def test_package_manager_integrity_drift_is_rejected(self) -> None:
        with TemporaryDirectory() as value:
            root = self._root(value)
            package = json.loads((root / "studio/package.json").read_text())
            package["packageManager"] = "npm@11.12.1"
            (root / "studio/package.json").write_text(json.dumps(package), encoding="utf-8")
            with self.assertRaises(P11RGateError):
                check_ci_policy(root)

    def test_historical_p10_current_ci_command_is_rejected(self) -> None:
        self._rejects("run: make ci", "run: make p10-ci")

    def test_branch_bound_p11_gate_is_rejected(self) -> None:
        self._rejects("run: make ci", "run: make p11-check")

    def test_publication_command_is_rejected(self) -> None:
        self._rejects("run: make ci", "run: docker push example.invalid/image")

    def test_compose_without_main_push_condition_is_rejected(self) -> None:
        self._rejects(
            "if: github.event_name == 'push' && github.ref == 'refs/heads/main'",
            "if: always()",
        )


if __name__ == "__main__":
    unittest.main()
