# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from scripts.check_p9_repository import BASE_COMMIT, BRANCH
from scripts.collect_p9_evidence import REQUIRED_GATES, EvidenceError, write_p9_evidence


def _unittest_result() -> dict[str, object]:
    return {
        "tests_run": 2,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "expected_failures": 0,
        "unexpected_successes": 0,
        "gate_passed": True,
        "test_ids": ["test.one", "test.two"],
        "fault_boundaries": ["p9_fixture_boundary"],
    }


def _results() -> dict[str, dict[str, object]]:
    return {
        "repository": {
            "candidate_phase": "implementation",
            "acceptance_contract_immutable": True,
            "acceptance_commit_isolated": True,
            "historical_drift_count": 0,
            "migration_count": 7,
            "migration_008": False,
            "product_runtime_implementation_change_count": 0,
            "cleanup_residue_count": 0,
            "staged_change_path_count": 0,
            "unstaged_change_path_count": 0,
            "untracked_path_count": 0,
        },
        "provenance": {
            "gate": "p9_provenance_clean",
            "transformed_migration_count": 0,
            "source_migration_count": 0,
            "parent_working_tree_read": False,
        },
        "rebaseline": {
            "gate": "p9_rebaseline_clean",
            "p9_through_p15_order": "passed",
            "fixed_product_decisions": "passed",
            "product_runtime_implementation_change_count": 0,
            "openai_live": "not_evaluated",
            "microsoft_365_live": "not_evaluated",
            "human_evaluation": "not_evaluated",
        },
    }


def _write(path: Path, **overrides: object) -> dict[str, object]:
    arguments: dict[str, object] = {
        "evidence_path": path,
        "root": path.parent,
        "results": _results(),
        "unittest_outcome": _unittest_result(),
        "verified_gates": set(REQUIRED_GATES),
        "branch": BRANCH,
        "implementation_commit": "2" * 40,
        "merge_base": BASE_COMMIT,
        "tree_digest": "sha256:" + "3" * 64,
        "tree_clean": True,
        "implementation_committed": True,
    }
    arguments.update(overrides)
    return write_p9_evidence(**arguments)  # type: ignore[arg-type]


class P9EvidenceTests(unittest.TestCase):
    def test_valid_static_synthetic_summary_has_exact_claim_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-evidence-") as name:
            path = Path(name) / "summary.json"
            summary = _write(path)
            self.assertTrue(path.is_file())
            self.assertEqual(summary["claim"], "p9_productization_rebaseline_candidate")
            self.assertEqual(
                summary["status"], "development_complete_awaiting_independent_acceptance"
            )
            evidence = summary["evidence_classes"]
            self.assertIsInstance(evidence, dict)
            assert isinstance(evidence, dict)
            self.assertEqual(evidence["documentation_and_governance"], "static")
            self.assertEqual(evidence["mechanical_regression"], "synthetic_offline")
            self.assertEqual(evidence["openai_live"], "not_evaluated")
            self.assertEqual(evidence["microsoft_365_live"], "not_evaluated")
            self.assertEqual(evidence["human_evaluation"], "not_evaluated")

    def test_evidence_writer_rejects_failure_skip_dirty_branch_and_uncommitted_input(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-refusal-") as name:
            temporary = Path(name)
            cases: list[tuple[str, dict[str, object]]] = [
                ("dirty", {"tree_clean": False}),
                ("branch", {"branch": "main"}),
                ("uncommitted", {"implementation_committed": False}),
                ("gate", {"verified_gates": set()}),
            ]
            skipped = _unittest_result()
            skipped["skipped"] = 1
            cases.append(("skip", {"unittest_outcome": skipped}))
            failed = _unittest_result()
            failed["failures"] = 1
            cases.append(("failure", {"unittest_outcome": failed}))
            for label, overrides in cases:
                with self.subTest(label=label):
                    path = temporary / f"{label}.json"
                    with self.assertRaises(EvidenceError):
                        _write(path, **overrides)
                    self.assertFalse(path.exists())

    def test_repository_gate_counts_and_live_statuses_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-result-") as name:
            temporary = Path(name)
            cases = (
                ("historical_drift_count", 1),
                ("migration_count", 8),
                ("migration_008", True),
                ("product_runtime_implementation_change_count", 1),
                ("cleanup_residue_count", 1),
                ("staged_change_path_count", 1),
            )
            for index, (key, value) in enumerate(cases):
                with self.subTest(key=key):
                    results = _results()
                    results["repository"][key] = value
                    with self.assertRaisesRegex(EvidenceError, "repository boundary"):
                        _write(temporary / f"repository-{index}.json", results=results)

            for index, key in enumerate(("openai_live", "microsoft_365_live", "human_evaluation")):
                with self.subTest(key=key):
                    results = _results()
                    results["rebaseline"][key] = "live_private"
                    with self.assertRaisesRegex(EvidenceError, "claim boundary"):
                        _write(temporary / f"live-{index}.json", results=results)

    def test_summary_rejects_local_path_credential_and_private_marker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-safe-") as name:
            temporary = Path(name)
            values = (
                str(temporary),
                "sk" + "-examplecredential123456",
                "/.codex/" + "attachments/x",
            )
            for index, value in enumerate(values):
                with self.subTest(value=value):
                    results = copy.deepcopy(_results())
                    results["rebaseline"]["unsafe_fixture"] = value
                    with self.assertRaises(EvidenceError):
                        _write(temporary / f"unsafe-{index}.json", results=results)

    def test_commit_and_digest_shapes_are_exact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-shape-") as name:
            temporary = Path(name)
            for label, overrides in (
                ("base", {"implementation_commit": BASE_COMMIT}),
                ("short", {"implementation_commit": "abc"}),
                ("digest", {"tree_digest": "sha256:bad"}),
                ("merge-base", {"merge_base": "f" * 40}),
            ):
                with self.subTest(label=label):
                    with self.assertRaises(EvidenceError):
                        _write(temporary / f"{label}.json", **overrides)


if __name__ == "__main__":
    unittest.main()
