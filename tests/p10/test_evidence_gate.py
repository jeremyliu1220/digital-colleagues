# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.check_p10_evidence import EVIDENCE_CLASSES, REQUIRED_GATES, _safe, validate_summary
from scripts.collect_p10_evidence import build_summary
from scripts.p10_gate_support import REMOTE_STATES, SUMMARY_PATH, GateError
from tests.p10.fixtures import ROOT, clone_repository


class P10EvidenceTests(unittest.TestCase):
    def test_evidence_constants_keep_remote_and_p11_unaccepted(self) -> None:
        self.assertIn("local_mac_runtime", EVIDENCE_CLASSES)
        self.assertIn("not_evaluated", EVIDENCE_CLASSES)
        self.assertEqual(REMOTE_STATES["remote_distribution_gate"], "authorization_required")

    def test_wrong_identity_private_material_and_timing_fail_closed(self) -> None:
        invalid = {"schema_version": 1}
        with self.assertRaises(GateError):
            validate_summary(ROOT, invalid)
        with self.assertRaisesRegex(GateError, "evidence_private"):
            _safe({"secret": ""}, ROOT)

    def test_writer_rejects_dirty_and_skipped_inputs_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="dc-p10-evidence-refusal-") as name:
            root = clone_repository(Path(name))
            if (root / SUMMARY_PATH).exists():
                subprocess.run(
                    ["git", "checkout", "--quiet", "-B", "codex/p10-mac-quickstart", "HEAD^"],
                    cwd=root,
                    check=True,
                )
            (root / "dirty").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(GateError, "clean_implementation_branch"):
                build_summary(root, {}, {}, set())
            self.assertFalse((root / SUMMARY_PATH).exists())
            (root / "dirty").unlink()
            results = {"quickstart": {"trial_count": 3, "all_below_300_seconds": True}}
            unittest_result = {
                "gate_passed": True,
                "failures": 0,
                "errors": 0,
                "skipped": 1,
                "expected_failures": 0,
                "unexpected_successes": 0,
            }
            with self.assertRaisesRegex(GateError, "unittest_incomplete"):
                build_summary(root, results, unittest_result, set(REQUIRED_GATES))
            self.assertFalse((root / SUMMARY_PATH).exists())


if __name__ == "__main__":
    unittest.main()
