# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.build_p10_candidate import CandidateError, build_bundle
from scripts.check_p10_compose_runtime import LocalCandidate
from scripts.check_p10_operations import check_operations
from scripts.check_p10_quickstart import run_quickstart_trials
from scripts.p10_gate_support import GateError
from tests.p10.fixtures import ROOT


class P10OperationsTests(unittest.TestCase):
    def test_finite_cli_and_verified_bundle_pass(self) -> None:
        result = check_operations(ROOT)
        self.assertEqual(result["command_count"], 9)
        self.assertFalse(result["remote_update_authorized"])

    def test_mutable_image_and_existing_output_are_rejected(self) -> None:
        revision = "11aa240af8db2ca515325dc059b1a77f7badc874"
        with tempfile.TemporaryDirectory(prefix="dc-p10-operations-test-") as name:
            output = Path(name) / "bundle"
            with self.assertRaisesRegex(CandidateError, "image_reference_invalid"):
                build_bundle(
                    ROOT,
                    output,
                    revision,
                    "example.invalid/runtime:latest",
                    "example.invalid/studio:latest",
                )

    def test_update_restore_unsafe_root_locale_and_concurrency_refuse(self) -> None:
        revision = "11aa240af8db2ca515325dc059b1a77f7badc874"
        runtime = "example.invalid/dc/runtime@sha256:" + "a" * 64
        studio = "example.invalid/dc/studio@sha256:" + "b" * 64
        with tempfile.TemporaryDirectory(prefix="dc-p10-cli-refusal-") as name:
            temporary = Path(name)
            bundle = temporary / "bundle"
            build_bundle(ROOT, bundle, revision, runtime, studio)
            managed = (temporary / "Digital Colleagues").resolve()

            def invoke(*arguments: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [str(bundle / "dc"), "--json", "--managed-root", str(managed), *arguments],
                    cwd=bundle,
                    capture_output=True,
                    text=True,
                    check=False,
                )

            updated = invoke("update")
            self.assertEqual(updated.returncode, 8)
            self.assertEqual(
                json.loads(updated.stdout)["category"], "remote_distribution_authorization_required"
            )
            restored = invoke("restore", "--backup", "safe.tar.gz")
            self.assertEqual(restored.returncode, 7)
            self.assertEqual(json.loads(restored.stdout)["category"], "confirmation_required")
            (temporary / "Digital Colleagues.lock").mkdir(mode=0o700)
            concurrent = invoke("down")
            self.assertEqual(concurrent.returncode, 5)
            self.assertEqual(json.loads(concurrent.stdout)["category"], "concurrent_invocation")
            unsafe = subprocess.run(
                [
                    str(bundle / "dc"),
                    "--json",
                    "--locale",
                    "unknown",
                    "--managed-root",
                    "/",
                    "doctor",
                ],
                cwd=bundle,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(unsafe.returncode, 3)
            self.assertEqual(json.loads(unsafe.stdout)["category"], "invalid_managed_root")

    def test_quickstart_partial_health_and_timeout_faults_fail(self) -> None:
        candidate = LocalCandidate(Path("bundle"), "runtime", "studio", "r", "s", "a" * 40, {})
        with tempfile.TemporaryDirectory(prefix="dc-p10-quickstart-fault-") as name:
            work = Path(name)
            responses = [
                (0, {"ready": False, "duration_seconds": 1.0}, ""),
                (0, {"status": "ok"}, ""),
            ]
            with (
                patch("scripts.check_p10_quickstart.dc_command", side_effect=responses),
                patch("scripts.check_p10_quickstart.subprocess.check_output", return_value=""),
                self.assertRaisesRegex(GateError, "quickstart_trial_not_ready"),
            ):
                run_quickstart_trials(ROOT, candidate, work)


if __name__ == "__main__":
    unittest.main()
