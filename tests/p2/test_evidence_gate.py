# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.collect_p2_evidence import (
    P1_BASELINE_COMMIT,
    REQUIRED_EVIDENCE_GATES,
    EvidenceError,
    write_p2_evidence,
)


def valid_unittest() -> dict[str, object]:
    return {
        "tests_run": 1,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "expected_failures": 0,
        "unexpected_successes": 0,
        "gate_passed": True,
    }


def valid_results() -> dict[str, dict[str, object]]:
    return {
        "boundary": {
            "gate": "public_boundary_clean",
            "files_scanned": 1,
            "exceptions_applied": 0,
            "policy_version": "p0-v1",
        },
        "repository": {
            "gate": "p2_repository_clean",
            "runtime_dependency_count": 0,
            "requires_python": ">=3.12",
        },
        "provenance": {
            "gate": "p2_provenance_clean",
            "source_revision": "dea9a9accc82fbedd35deb7117dcb5173223cf44",
            "transformed_migration_count": 0,
            "new_implementation_count": 1,
            "receipt_digest": "sha256:" + ("a" * 64),
            "new_implementation_digest": "sha256:" + ("b" * 64),
        },
        "architecture": {
            "gate": "p2_architecture_clean",
            "forbidden_imports": 0,
            "forbidden_io_imports": 0,
            "dependency_violations": 0,
            "nondeterministic_calls": 0,
        },
        "core_contracts": {
            "gate": "p2_core_contracts_clean",
            "immutability": "passed",
            "namespace": "passed",
            "principal_separation": "passed",
            "authority_approval": "passed",
            "serialization": "passed",
            "effect_payload_redacted": True,
        },
    }


def write_valid(evidence: Path, **overrides: object) -> None:
    results = valid_results()
    arguments: dict[str, object] = {
        "evidence_path": evidence,
        "boundary": results["boundary"],
        "repository": results["repository"],
        "provenance": results["provenance"],
        "architecture": results["architecture"],
        "core_contracts": results["core_contracts"],
        "unittest_outcome": valid_unittest(),
        "verified_gates": set(REQUIRED_EVIDENCE_GATES),
        "evaluated_branch": "codex/p2-core-primitives",
        "evaluated_head": "c" * 40,
        "merge_base": P1_BASELINE_COMMIT,
        "public_tree_digest": "sha256:" + ("d" * 64),
        "remote_count": 0,
    }
    arguments.update(overrides)
    write_p2_evidence(**arguments)  # type: ignore[arg-type]


class P2EvidenceGateTests(unittest.TestCase):
    def test_valid_results_write_passed_evidence_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "summary.json"
            write_valid(evidence)
            summary = json.loads(evidence.read_text(encoding="utf-8"))
        self.assertEqual(summary["milestone"], "P2")
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["results"]["unittest"]["skipped"], 0)
        self.assertEqual(summary["migration"]["transformed_migration_count"], 0)
        self.assertEqual(
            summary["non_mechanical_claims"]["parent_worktree_unchanged"],
            "not_evaluated",
        )

    def test_missing_gate_does_not_overwrite_passed_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "summary.json"
            original = b'{"status":"passed","sentinel":true}\n'
            evidence.write_bytes(original)
            incomplete = set(REQUIRED_EVIDENCE_GATES) - {"mypy_strict"}
            with self.assertRaisesRegex(EvidenceError, "missing required mechanical gates"):
                write_valid(evidence, verified_gates=incomplete)
            self.assertEqual(evidence.read_bytes(), original)

    def test_skip_failure_or_invalid_output_does_not_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "summary.json"
            original = b'{"status":"passed","sentinel":true}\n'
            evidence.write_bytes(original)
            outcome = valid_unittest()
            outcome["skipped"] = 1
            outcome["gate_passed"] = False
            with self.assertRaisesRegex(EvidenceError, "zero-exception gate"):
                write_valid(evidence, unittest_outcome=outcome)
            self.assertEqual(evidence.read_bytes(), original)

    def test_wrong_merge_base_or_remote_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "summary.json"
            with self.assertRaisesRegex(EvidenceError, "accepted P1 baseline"):
                write_valid(evidence, merge_base="e" * 40)
            with self.assertRaisesRegex(EvidenceError, "no configured Git remotes"):
                write_valid(evidence, remote_count=1)


if __name__ == "__main__":
    unittest.main()
