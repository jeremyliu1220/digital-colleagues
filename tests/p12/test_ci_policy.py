# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_p12_ci_policy import (
    COSIGN_INSTALLER_PIN,
    COSIGN_RELEASE,
    CURRENT_JOB_NAME,
    EXPECTED_WORKFLOW,
    MAIN_COMPOSE_JOB_NAME,
    PACKAGE_MANAGER,
    PORTABLE_JOB_NAME,
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
        self.assertIn(before, EXPECTED_WORKFLOW)
        with TemporaryDirectory() as value:
            root = self._root(value, EXPECTED_WORKFLOW.replace(before, after, 1))
            with self.assertRaises(P12GateError):
                check_ci_policy(root)

    def _rejects_each(self, before: str, replacements: tuple[str, ...]) -> None:
        for replacement in replacements:
            with self.subTest(replacement=replacement):
                self._rejects(before, replacement)

    def test_exact_canonical_workflow_passes(self) -> None:
        with TemporaryDirectory() as value:
            result = check_ci_policy(self._root(value))
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["action_pin_count"], 9)
        self.assertEqual(result["required_job_count"], 2)
        self.assertEqual(result["result_envelope_count_per_required_job"], 1)
        self.assertEqual(result["cosign_installer_pin"], COSIGN_INSTALLER_PIN)
        self.assertEqual(result["cosign_release"], COSIGN_RELEASE)
        self.assertIn(f"name: {CURRENT_JOB_NAME}\n", EXPECTED_WORKFLOW)
        self.assertIn(f"name: {PORTABLE_JOB_NAME}\n", EXPECTED_WORKFLOW)
        self.assertIn(f"name: {MAIN_COMPOSE_JOB_NAME}\n", EXPECTED_WORKFLOW)
        with TemporaryDirectory() as value:
            commented = EXPECTED_WORKFLOW.replace(
                "name: CI\n", "name: CI  # structural comments are not policy\n", 1
            )
            self.assertEqual(check_ci_policy(self._root(value, commented))["status"], "passed")

    def test_pull_request_target_is_rejected(self) -> None:
        self._rejects("  pull_request:\n", "  pull_request_target:\n")
        self._rejects(
            "  pull_request:\n    branches:\n      - main\n",
            "  pull_request:\n    branches:\n      - development\n",
        )

    def test_workflow_dispatch_is_rejected(self) -> None:
        self._rejects("  push:\n", "  workflow_dispatch:\n  push:\n")

    def test_workflow_call_is_rejected(self) -> None:
        self._rejects("  push:\n", "  workflow_call:\n  push:\n")

    def test_schedule_is_rejected(self) -> None:
        self._rejects("  push:\n", "  schedule:\n    - cron: '0 0 * * *'\n  push:\n")

    def test_write_permission_is_rejected(self) -> None:
        self._rejects_each(
            "contents: read",
            ("contents: write", "contents: read\n  packages: write", "{}"),
        )
        self._rejects(
            "  current-ci:\n    name:",
            "  current-ci:\n    permissions:\n      contents: read\n    name:",
        )

    def test_oidc_permission_is_rejected(self) -> None:
        self._rejects_each(
            "  contents: read\n",
            (
                "  contents: read\n  id-token: write\n",
                "  contents: read\n  attestations: write\n",
            ),
        )

    def test_secret_context_is_rejected(self) -> None:
        self._rejects_each(
            "PYTHONPATH: src",
            (
                "PYTHONPATH: ${{ secrets.RUNTIME_PATH }}",
                "PYTHONPATH: ${{ github.token }}",
                "GITHUB_TOKEN: caller-controlled",
                "AUTHORIZATION: bearer-value",
            ),
        )

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
        self._rejects_each(
            "make p12-current-ci",
            (
                "make p11r-check",
                "make p11-check",
                "make p10-check",
                "make p9-check",
                "make ci",
                "bash -c 'make p12-current-ci'",
                "eval 'make p12-current-ci'",
            ),
        )
        self._rejects_each(
            "make p12-portable-history",
            (
                "make p11r-check",
                "make p11-check",
                "make p10-check",
                "make p9-check",
                "make ci",
                "make p12-ci",
            ),
        )

    def test_evidence_preflight_is_rejected_in_ci(self) -> None:
        self._rejects_each(
            "make p12-current-ci",
            (
                "make p12-evidence-preflight",
                "make evidence-p12",
                "make p12-check",
            ),
        )
        self._rejects("make p12-portable-history", "make p12-evidence-preflight")

    def test_publication_command_is_rejected(self) -> None:
        self._rejects_each(
            "make p12-current-ci",
            (
                "docker push example.invalid/image",
                "docker login example.invalid",
                "git push origin HEAD",
                "git tag p12",
                "gh release create p12",
                "npm publish",
                "cosign sign example.invalid/image",
                "curl -X POST https://example.invalid",
            ),
        )

    def test_compose_without_main_push_condition_is_rejected(self) -> None:
        self._rejects_each(
            "if: github.event_name == 'push' && github.ref == 'refs/heads/main'",
            (
                "if: always()",
                "if: github.event_name == 'pull_request'",
                "if: github.ref == 'refs/heads/main'",
            ),
        )
        self._rejects(
            "    timeout-minutes: 30\n",
            "    timeout-minutes: 30\n    continue-on-error: true\n",
        )
        self._rejects(
            "    needs:\n      - current-ci\n      - portable-history\n",
            "    needs:\n      - current-ci\n",
        )
        self._rejects("run: make p11r-compose-smoke", "run: make p11r-check")

    def test_ubuntu_2404_is_exact(self) -> None:
        self._rejects_each(
            "runs-on: ubuntu-24.04",
            ("runs-on: ubuntu-latest", "runs-on: self-hosted"),
        )

    def test_two_required_jobs_are_exact(self) -> None:
        self._rejects_each(
            f"name: {PORTABLE_JOB_NAME}",
            (
                "name: Portable exact-object historical verification",
                "name: Portable history verification",
            ),
        )
        self._rejects(f"name: {CURRENT_JOB_NAME}", "name: Current P12 verification")
        self._rejects(f"name: {MAIN_COMPOSE_JOB_NAME}", "name: Current Compose smoke")
        yaml_attacks = (
            "jobs: &shared-jobs\n",
            "jobs: *shared-jobs\n",
            "jobs: !mapping\n",
            "permissions:\n  contents: read\n\njobs:\n",
        )
        for replacement in yaml_attacks:
            with self.subTest(yaml=replacement):
                self._rejects("jobs:\n", replacement)
        self._rejects(
            "        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
            "        name: Duplicate mapping key\n"
            "        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
        )

    def test_action_inventory_is_exact(self) -> None:
        self._rejects(
            "uses: actions/setup-node@249970729cb0ef3589644e2896645e5dc5ba9c38",
            "uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
        )
        self._rejects(
            "      - name: Enable the package-manager integrity boundary\n",
            "      - uses: example/extra-action@0000000000000000000000000000000000000000\n"
            "      - name: Enable the package-manager integrity boundary\n",
        )
        self._rejects(
            "uses: sigstore/cosign-installer@6f9f17788090df1f26f669e9d70d6ae9567deba6",
            "uses: actions/setup-node@249970729cb0ef3589644e2896645e5dc5ba9c38",
        )

    def test_portable_timeout_contract_is_exact(self) -> None:
        self._rejects("9900s make p12-portable-history", "9800s make p12-portable-history")
        self._rejects_each(
            "    timeout-minutes: 45\n",
            ("    timeout-minutes: 44\n", "    timeout-minutes: 46\n"),
        )
        self._rejects_each(
            "    timeout-minutes: 180\n",
            ("    timeout-minutes: 179\n", "    timeout-minutes: 181\n"),
        )
        self._rejects_each(
            "    timeout-minutes: 30\n",
            ("    timeout-minutes: 29\n", "    timeout-minutes: 31\n"),
        )
        lifecycle_mutations = {
            "umask 077": "umask 022",
            'install -d -m 0700 "${gate_dir}"': 'install -d -m 0755 "${gate_dir}"',
            'install -m 0600 /dev/null "${P12_JSON_OUTPUT}"': (
                'install -m 0644 /dev/null "${P12_JSON_OUTPUT}"'
            ),
            "gate_status=$?": "gate_status=0",
            "envelope_status=$?": "envelope_status=0",
            'find "${gate_dir}" -type f -delete || cleanup_status=$?': "cleanup_status=0",
            'rmdir "${gate_dir}" || cleanup_status=$?': "true",
            'if [ "${envelope_status}" -ne 0 ]; then exit "${envelope_status}"; fi': "true",
            'if [ "${cleanup_status}" -ne 0 ]; then exit "${cleanup_status}"; fi': "true",
            "printf '%s\\n' \"${envelope_line}\"": "true",
            'if [ "${gate_status}" -ne 0 ]; then exit "${gate_status}"; fi': "true",
            "exit 0": "exit 1",
        }
        for before, after in lifecycle_mutations.items():
            with self.subTest(lifecycle=before):
                self._rejects(before, after)
        emitter = (
            "python3 -B scripts/run_p12_toolchain.py --scope emit-ci-envelope "
            '--job-kind portable_history --gate-result "${P12_JSON_OUTPUT}" '
            '--gate-exit-status "${gate_status}"'
        )
        self._rejects(emitter, f"{emitter}\n          {emitter}")
        self._rejects(
            "--job-kind current_governance",
            "--job-kind portable_history",
        )
        self._rejects(
            "--job-kind portable_history",
            "--job-kind current_governance",
        )

    def test_artifact_transport_is_rejected(self) -> None:
        self._rejects_each(
            "      - name: Enable the package-manager integrity boundary\n",
            (
                "      - uses: actions/upload-artifact@0000000000000000000000000000000000000000\n"
                "      - name: Enable the package-manager integrity boundary\n",
                "      - uses: actions/download-artifact@0000000000000000000000000000000000000000\n"
                "      - name: Enable the package-manager integrity boundary\n",
            ),
        )


if __name__ == "__main__":
    unittest.main()
