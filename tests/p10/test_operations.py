# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from scripts.build_p10_candidate import CandidateError, build_bundle
from scripts.check_p10_compose_runtime import LocalCandidate
from scripts.check_p10_distribution import MANIFEST_KEYS, load_manifest, verify_manifest
from scripts.check_p10_operations import check_operations
from scripts.check_p10_quickstart import run_quickstart_trials
from scripts.p10_gate_support import GateError
from tests.p10.fixtures import ROOT


class P10OperationsTests(unittest.TestCase):
    def _refresh_manifest_checksum(self, bundle: Path) -> None:
        manifest_digest = hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest()
        checksums = (bundle / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
        updated = [
            f"{manifest_digest}  manifest.json" if line.endswith("  manifest.json") else line
            for line in checksums
        ]
        (bundle / "SHA256SUMS").write_text("\n".join(updated) + "\n", encoding="utf-8")

    def _invoke_update(self, bundle: Path, managed: Path) -> subprocess.CompletedProcess[str]:
        managed.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        return subprocess.run(
            [str(bundle / "dc"), "--json", "--managed-root", str(managed), "update"],
            cwd=bundle,
            capture_output=True,
            text=True,
            check=False,
        )

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

    def test_generated_manifest_round_trip_and_schema_refusals(self) -> None:
        revision = "11aa240af8db2ca515325dc059b1a77f7badc874"
        runtime = "example.invalid/dc/runtime@sha256:" + "a" * 64
        studio = "example.invalid/dc/studio@sha256:" + "b" * 64
        with tempfile.TemporaryDirectory(prefix="dc-p10-manifest-roundtrip-") as name:
            temporary = Path(name)
            bundle = temporary / "bundle"
            build_bundle(ROOT, bundle, revision, runtime, studio)
            manifest_path = bundle / "manifest.json"
            manifest = load_manifest(manifest_path)
            verify_manifest(manifest, template=False)
            self.assertEqual(set(manifest), MANIFEST_KEYS)
            self.assertNotIn("source_timestamp", manifest)
            binding = json.loads(
                (bundle / "operations-source-binding.json").read_text(encoding="utf-8")
            )
            self.assertIsInstance(binding["source_timestamp"], str)
            if sys.platform == "darwin":
                accepted = self._invoke_update(
                    bundle, (temporary / "valid" / "Digital Colleagues").resolve()
                )
                self.assertEqual(accepted.returncode, 8)

            fixtures: list[tuple[str, dict[str, Any]]] = []
            extra = copy.deepcopy(manifest)
            extra["unknown_field"] = "refuse"
            fixtures.append(("extra", extra))
            missing = copy.deepcopy(manifest)
            del missing["product_name"]
            fixtures.append(("missing", missing))
            wrong_type = copy.deepcopy(manifest)
            wrong_type["schema_version"] = "1"
            fixtures.append(("wrong-type", wrong_type))
            for label, value in fixtures:
                with self.subTest(label=label):
                    with self.assertRaises(GateError):
                        verify_manifest(value, template=False)
                    invalid_bundle = temporary / label
                    shutil.copytree(bundle, invalid_bundle)
                    (invalid_bundle / "manifest.json").write_text(
                        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                    )
                    self._refresh_manifest_checksum(invalid_bundle)
                    if sys.platform == "darwin":
                        refused = self._invoke_update(
                            invalid_bundle,
                            (temporary / f"managed-{label}" / "Digital Colleagues").resolve(),
                        )
                        self.assertEqual(refused.returncode, 4)

            duplicate_bundle = temporary / "duplicate"
            shutil.copytree(bundle, duplicate_bundle)
            original = (duplicate_bundle / "manifest.json").read_text(encoding="utf-8")
            duplicate = original.replace("{\n", '{\n  "product_name": "Digital Colleagues",\n', 1)
            (duplicate_bundle / "manifest.json").write_text(duplicate, encoding="utf-8")
            self._refresh_manifest_checksum(duplicate_bundle)
            with self.assertRaisesRegex(GateError, "duplicate"):
                load_manifest(duplicate_bundle / "manifest.json")
            if sys.platform == "darwin":
                refused = self._invoke_update(
                    duplicate_bundle,
                    (temporary / "managed-duplicate" / "Digital Colleagues").resolve(),
                )
                self.assertEqual(refused.returncode, 4)


if __name__ == "__main__":
    unittest.main()
