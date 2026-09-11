# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_p12_ci_policy import (
    COSIGN_INSTALLER_PIN,
    COSIGN_RELEASE,
    EXPECTED_WORKFLOW,
    PACKAGE_MANAGER,
    check_ci_policy,
)
from scripts.check_p12_repository import P12GateError


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
            with self.assertRaises(P12GateError):
                check_ci_policy(root)

    def test_exact_canonical_workflow_passes(self) -> None:
        with TemporaryDirectory() as value:
            result = check_ci_policy(self._root(value))
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["action_pin_count"], 6)
        self.assertEqual(result["cosign_installer_pin"], COSIGN_INSTALLER_PIN)
        self.assertEqual(result["cosign_release"], COSIGN_RELEASE)
        self.assertEqual(result["publication_command_count"], 0)

    def test_pull_request_target_is_rejected(self) -> None:
        self._rejects("pull_request:", "pull_request_target:")

    def test_workflow_dispatch_is_rejected(self) -> None:
        self._rejects("  push:\n", "  workflow_dispatch:\n  push:\n")

    def test_workflow_call_is_rejected(self) -> None:
        self._rejects("  push:\n", "  workflow_call:\n  push:\n")

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
        self._rejects(
            "sigstore/cosign-installer@6f9f17788090df1f26f669e9d70d6ae9567deba6",
            "sigstore/cosign-installer@main",
        )
        self._rejects("cosign-release: v3.0.6", "cosign-release: v3.0.5")

    def test_persisted_checkout_credentials_are_rejected(self) -> None:
        self._rejects("persist-credentials: false", "persist-credentials: true")

    def test_direct_node_version_is_rejected(self) -> None:
        self._rejects("node-version-file: .nvmrc", 'node-version: "24.15.0"')

    def test_wrong_node_file_content_is_rejected(self) -> None:
        with TemporaryDirectory() as value:
            root = self._root(value)
            (root / ".nvmrc").write_text("24.20.0\n", encoding="utf-8")
            with self.assertRaises(P12GateError):
                check_ci_policy(root)

    def test_package_manager_integrity_drift_is_rejected(self) -> None:
        with TemporaryDirectory() as value:
            root = self._root(value)
            package = json.loads((root / "studio/package.json").read_text())
            package["packageManager"] = "npm@11.12.1"
            (root / "studio/package.json").write_text(json.dumps(package), encoding="utf-8")
            with self.assertRaises(P12GateError):
                check_ci_policy(root)

    def test_historical_gate_is_not_current_ci(self) -> None:
        self._rejects("run: make ci", "run: make p11r-check")

    def test_evidence_preflight_is_rejected_in_ci(self) -> None:
        self._rejects("run: make ci", "run: make p12-evidence-preflight")

    def test_publication_command_is_rejected(self) -> None:
        self._rejects("run: make ci", "run: docker push example.invalid/image")

    def test_compose_without_main_push_condition_is_rejected(self) -> None:
        self._rejects(
            "if: github.event_name == 'push' && github.ref == 'refs/heads/main'",
            "if: always()",
        )


if __name__ == "__main__":
    unittest.main()
