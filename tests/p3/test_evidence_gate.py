# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.collect_p3_evidence import (
    P2_BASE_COMMIT,
    REQUIRED_GATES,
    EvidenceError,
    write_p3_evidence,
)
from scripts.run_p3_unittest_suite import REQUIRED_TEST_BOUNDARIES


def _fingerprint() -> dict[str, object]:
    return {
        "schema_version": 2,
        "source_label": "digital-colleague-runtime-research",
        "source_revision": "dea9a9accc82fbedd35deb7117dcb5173223cf44",
        "head_revision": "a" * 40,
        "scope": "parent_source_excluding_authorized_target_subtree",
        "excluded_repo_relative_subtree": "digital-colleagues",
        "status_entry_count": 1,
        "status_digest": "1" * 64,
        "tracked_diff_digest": "2" * 64,
        "index_diff_digest": "3" * 64,
        "untracked_entry_count": 0,
        "untracked_state_digest": "4" * 64,
        "ignored_entry_count": 2,
        "ignored_state_digest": "5" * 64,
    }


def _unittest() -> dict[str, object]:
    return {
        "tests_run": len(REQUIRED_TEST_BOUNDARIES),
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "expected_failures": 0,
        "unexpected_successes": 0,
        "gate_passed": True,
        "test_ids": sorted(REQUIRED_TEST_BOUNDARIES),
        "fault_boundaries": sorted(REQUIRED_TEST_BOUNDARIES.values()),
    }


def _results() -> dict[str, dict[str, object]]:
    return {
        "repository": {"gate": "p3_repository_clean"},
        "boundary": {
            "gate": "public_boundary_clean",
            "exceptions_applied": 0,
            "files_scanned": 1,
            "policy_version": "p0-v1",
        },
        "provenance": {
            "gate": "p3_provenance_clean",
            "transformed_migration_count": 0,
            "new_implementation_count": 1,
            "receipt_digest": "sha256:" + ("a" * 64),
            "implementation_tree_digest": "sha256:" + ("b" * 64),
        },
        "architecture": {
            "gate": "p3_architecture_clean",
            "policy_version": "p3-boundary-specific-determinism-allowlist-v6",
            "unapproved_imports": 0,
            "dependency_violations": 0,
            "edge_type_leaks": 0,
            "nondeterministic_imports": 0,
            "nondeterministic_calls": 0,
            "dynamic_capability_calls": 0,
            "reflection_capability_accesses": 0,
            "alias_resolved_unsafe_calls": 0,
            "stable_port_leaks": 0,
        },
        "migrations": {
            "gate": "p3_migrations_clean",
            "journal_mode": "wal",
            "foreign_keys": True,
            "migration_count": 3,
        },
        "persistence": {"gate": "p3_persistence_clean"},
        "runtime_contracts": {"gate": "p3_runtime_contracts_clean"},
        "golden_path": {
            "gate": "p3_golden_path_clean",
            "golden_test_id": next(
                test_id
                for test_id, boundary in REQUIRED_TEST_BOUNDARIES.items()
                if boundary == "restart_golden_path"
            ),
        },
        "p2_core": {"gate": "p2_core_contracts_clean"},
    }


def _write(path: Path, **overrides: object) -> None:
    arguments: dict[str, object] = {
        "evidence_path": path,
        "results": _results(),
        "parent_before": _fingerprint(),
        "parent_after": _fingerprint(),
        "unittest_outcome": _unittest(),
        "verified_gates": set(REQUIRED_GATES),
        "branch": "codex/p3-headless-deterministic-slice",
        "implementation_commit": "c" * 40,
        "merge_base": P2_BASE_COMMIT,
        "tree_digest": "sha256:" + ("d" * 64),
        "remote_count": 0,
    }
    arguments.update(overrides)
    write_p3_evidence(**arguments)  # type: ignore[arg-type]


class P3EvidenceGateTests(unittest.TestCase):
    def test_valid_complete_results_write_scoped_summary_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "summary.json"
            _write(path)
            summary = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(summary["milestone"], "P3")
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["evaluated_tree"]["merge_base"], P2_BASE_COMMIT)
        self.assertEqual(summary["results"]["unittest"]["skipped"], 0)
        self.assertIn("security_effectiveness", summary["non_mechanical_claims"])

    def test_failed_or_missing_gate_never_overwrites_existing_passed_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "summary.json"
            original = b'{"status":"passed","sentinel":true}\n'
            path.write_bytes(original)
            with self.assertRaises(EvidenceError):
                _write(path, verified_gates=set(REQUIRED_GATES) - {"mypy_strict"})
            self.assertEqual(path.read_bytes(), original)
            outcome = _unittest()
            outcome["skipped"] = 1
            outcome["gate_passed"] = False
            with self.assertRaises(EvidenceError):
                _write(path, unittest_outcome=outcome)
            self.assertEqual(path.read_bytes(), original)

    def test_required_test_identity_and_fault_boundary_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "summary.json"
            outcome = _unittest()
            test_ids = outcome["test_ids"]
            assert isinstance(test_ids, list)
            outcome["test_ids"] = test_ids[1:]
            with self.assertRaisesRegex(EvidenceError, "test IDs or fault boundaries"):
                _write(path, unittest_outcome=outcome)

    def test_fingerprint_branch_base_remote_and_policy_drift_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "summary.json"
            after = _fingerprint()
            after["status_digest"] = "9" * 64
            with self.assertRaises(EvidenceError):
                _write(path, parent_after=after)
            with self.assertRaises(EvidenceError):
                _write(path, merge_base="e" * 40)
            with self.assertRaises(EvidenceError):
                _write(path, remote_count=1)
            results = _results()
            results["architecture"]["dynamic_capability_calls"] = 1
            with self.assertRaises(EvidenceError):
                _write(path, results=results)
            results = _results()
            results["architecture"]["reflection_capability_accesses"] = 1
            with self.assertRaises(EvidenceError):
                _write(path, results=results)
            results = _results()
            results["architecture"]["policy_version"] = "unknown"
            with self.assertRaises(EvidenceError):
                _write(path, results=results)


if __name__ == "__main__":
    unittest.main()
