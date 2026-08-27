# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_p1_toolchain import (
    APACHE_LICENSE_DIGEST,
    REQUIRED_EVIDENCE_GATES,
    ToolchainError,
    write_p1_evidence,
)
from scripts.run_unittest_suite import run_suite


def _valid_boundary() -> dict[str, object]:
    return {
        "gate": "public_boundary_clean",
        "files_scanned": 1,
        "exceptions_applied": 0,
        "policy_version": "p0-v1",
    }


def _valid_scaffold() -> dict[str, object]:
    return {
        "gate": "p1_scaffold_contract_clean",
        "p2_product_paths_present": 0,
        "runtime_dependency_count": 0,
        "requires_python": ">=3.12",
        "license_digest": APACHE_LICENSE_DIGEST,
        "notice_operator_review_record_present": True,
    }


def _valid_unittest_outcome() -> dict[str, object]:
    return {
        "tests_run": 1,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "expected_failures": 0,
        "unexpected_successes": 0,
        "gate_passed": True,
    }


class EvidenceGateTests(unittest.TestCase):
    def test_synthetic_skipped_test_cannot_pass_the_gate(self) -> None:
        def skipped_test(_case: unittest.TestCase) -> None:
            return None

        skipped = unittest.skip("synthetic required skip")(skipped_test)
        case_type = type("SyntheticSkippedCase", (unittest.TestCase,), {"test_required": skipped})
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(case_type)

        outcome = run_suite(suite, stream=io.StringIO())

        self.assertEqual(outcome.tests_run, 1)
        self.assertEqual(outcome.skipped, 1)
        self.assertFalse(outcome.gate_passed)

    def test_root_git_fixture_blocks_evidence_without_overwriting_passed_artifact(self) -> None:
        for administrative_kind in ("directory", "worktree_pointer"):
            with self.subTest(administrative_kind=administrative_kind):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    if administrative_kind == "directory":
                        (root / ".git").mkdir()
                    else:
                        (root / ".git").write_text(
                            "gitdir: ../private-administrative-directory\n",
                            encoding="utf-8",
                        )
                    evidence = root / "artifacts/p1/summary.json"
                    evidence.parent.mkdir(parents=True)
                    original = b'{"status":"passed","sentinel":true}\n'
                    evidence.write_bytes(original)

                    with self.assertRaisesRegex(ToolchainError, "pre-Git project root"):
                        write_p1_evidence(
                            project_root=root,
                            evidence_path=evidence,
                            boundary=_valid_boundary(),
                            scaffold=_valid_scaffold(),
                            unittest_outcome=_valid_unittest_outcome(),
                            verified_gates=set(REQUIRED_EVIDENCE_GATES),
                        )

                    self.assertEqual(evidence.read_bytes(), original)

    def test_skipped_outcome_blocks_evidence_without_overwriting(self) -> None:
        outcome = _valid_unittest_outcome()
        outcome["skipped"] = 1
        outcome["gate_passed"] = False
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "summary.json"
            original = b'{"status":"passed","sentinel":true}\n'
            evidence.write_bytes(original)

            with self.assertRaisesRegex(ToolchainError, "zero-exception gate"):
                write_p1_evidence(
                    project_root=root,
                    evidence_path=evidence,
                    boundary=_valid_boundary(),
                    scaffold=_valid_scaffold(),
                    unittest_outcome=outcome,
                    verified_gates=set(REQUIRED_EVIDENCE_GATES),
                )

            self.assertEqual(evidence.read_bytes(), original)

    def test_missing_mechanical_gate_blocks_evidence_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "summary.json"
            original = b'{"status":"passed","sentinel":true}\n'
            evidence.write_bytes(original)
            incomplete = set(REQUIRED_EVIDENCE_GATES) - {"studio_vite_build"}

            with self.assertRaisesRegex(ToolchainError, "missing required mechanical gates"):
                write_p1_evidence(
                    project_root=root,
                    evidence_path=evidence,
                    boundary=_valid_boundary(),
                    scaffold=_valid_scaffold(),
                    unittest_outcome=_valid_unittest_outcome(),
                    verified_gates=incomplete,
                )

            self.assertEqual(evidence.read_bytes(), original)

    def test_valid_fixture_writes_noncontradictory_schema_two_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "summary.json"

            write_p1_evidence(
                project_root=root,
                evidence_path=evidence,
                boundary=_valid_boundary(),
                scaffold=_valid_scaffold(),
                unittest_outcome=_valid_unittest_outcome(),
                verified_gates=set(REQUIRED_EVIDENCE_GATES),
            )

            summary = json.loads(evidence.read_text(encoding="utf-8"))
            self.assertEqual(summary["schema_version"], 2)
            self.assertEqual(summary["status"], "passed")
            self.assertFalse(summary["mechanically_verified_boundaries"]["git_initialized"])
            self.assertEqual(
                summary["non_mechanical_claims"]["published"],
                "not_evaluated_by_automated_evidence",
            )


if __name__ == "__main__":
    unittest.main()
