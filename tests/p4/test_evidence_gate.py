# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from scripts import check_p4_repository as repository_gate
from scripts.check_p4_compose import check_compose
from scripts.check_p4_repository import ACCEPTED_P4_COMMIT, BASE_COMMIT, BRANCH, RepositoryError
from scripts.collect_p4_evidence import (
    REQUIRED_GATES,
    EvidenceError,
    validate_unittest,
    write_p4_evidence,
)
from scripts.run_p4_unittest_suite import REQUIRED_TEST_BOUNDARIES

ROOT = Path(__file__).resolve().parents[2]


def passing_outcome() -> dict[str, Any]:
    test_ids = sorted(REQUIRED_TEST_BOUNDARIES)
    return {
        "tests_run": len(test_ids),
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "expected_failures": 0,
        "unexpected_successes": 0,
        "gate_passed": True,
        "test_ids": test_ids,
        "fault_boundaries": sorted(REQUIRED_TEST_BOUNDARIES.values()),
    }


def git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


class P4RepositoryGateTests(unittest.TestCase):
    def repository(self) -> tuple[Path, str, str]:
        temporary = tempfile.TemporaryDirectory(prefix="p4-repository-gate-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        git(root, "init", "--initial-branch=main")
        for relative in (
            "artifacts/p0/summary.json",
            "artifacts/p1/summary.json",
            "artifacts/p2/summary.json",
            "artifacts/p3/summary.json",
            "docs/p0/acceptance.md",
            "docs/p1/acceptance.md",
            "docs/p2/acceptance.md",
            "docs/p3/acceptance.md",
            "migrations/001_initial.sql",
            "migrations/002_runtime_indexes.sql",
            "migrations/003_timer_triggers.sql",
            "provenance/p3-migration-receipt.json",
        ):
            document = root / relative
            document.parent.mkdir(parents=True, exist_ok=True)
            document.write_text(f"baseline {relative}\n", encoding="utf-8")
        git(root, "add", ".")
        git(
            root,
            "-c",
            "user.name=P4 Gate Test",
            "-c",
            "user.email=p4-gate.invalid",
            "commit",
            "-m",
            "baseline",
        )
        base = git(root, "rev-parse", "HEAD")
        (root / "required-p4.txt").write_text("accepted P4\n", encoding="utf-8")
        (root / "compose.yaml").write_text("services: {}\n", encoding="utf-8")
        git(root, "add", "required-p4.txt", "compose.yaml")
        git(
            root,
            "-c",
            "user.name=P4 Gate Test",
            "-c",
            "user.email=p4-gate.invalid",
            "commit",
            "-m",
            "accepted P4",
        )
        return root, base, git(root, "rev-parse", "HEAD")

    def check(self, root: Path, base: str, accepted: str) -> dict[str, object]:
        with (
            patch.object(repository_gate, "BASE_COMMIT", base),
            patch.object(repository_gate, "ACCEPTED_P4_COMMIT", accepted),
            patch.object(
                repository_gate,
                "REQUIRED_FILES",
                {"compose.yaml", "required-p4.txt"},
            ),
        ):
            return repository_gate.check_repository(root)

    def test_accepted_p4_main_and_descendant_pass_repository_check(self) -> None:
        root, base, accepted = self.repository()
        result = self.check(root, base, accepted)
        self.assertEqual(result["branch"], "main")
        self.assertEqual(result["accepted_p4_commit"], accepted)

        git(root, "switch", "-c", "codex/future-development")
        (root / "future.txt").write_text("descendant\n", encoding="utf-8")
        git(root, "add", "future.txt")
        git(
            root,
            "-c",
            "user.name=P4 Gate Test",
            "-c",
            "user.email=p4-gate.invalid",
            "commit",
            "-m",
            "descendant",
        )
        result = self.check(root, base, accepted)
        self.assertEqual(result["branch"], "codex/future-development")
        self.assertTrue(result["accepted_p4_ancestor"])

    def test_hotfix_branch_from_accepted_p4_baseline_passes(self) -> None:
        root, base, accepted = self.repository()
        git(root, "switch", "-c", "codex/p4-post-merge-check")
        result = self.check(root, base, accepted)
        self.assertEqual(result["branch"], "codex/p4-post-merge-check")

    def test_missing_accepted_p4_ancestor_fails_closed(self) -> None:
        root, base, accepted = self.repository()
        git(root, "switch", "-c", "unrelated", base)
        (root / "required-p4.txt").write_text("unrelated\n", encoding="utf-8")
        git(root, "add", "required-p4.txt")
        git(
            root,
            "-c",
            "user.name=P4 Gate Test",
            "-c",
            "user.email=p4-gate.invalid",
            "commit",
            "-m",
            "unrelated",
        )
        with self.assertRaisesRegex(RepositoryError, "not an ancestor"):
            self.check(root, base, accepted)

    def test_historical_file_change_fails_closed(self) -> None:
        root, base, accepted = self.repository()
        for relative in (
            "docs/p0/acceptance.md",
            "docs/p1/acceptance.md",
            "docs/p2/acceptance.md",
            "docs/p3/acceptance.md",
            "migrations/001_initial.sql",
            "migrations/002_runtime_indexes.sql",
            "migrations/003_timer_triggers.sql",
        ):
            with self.subTest(relative=relative):
                document = root / relative
                baseline = document.read_bytes()
                document.write_text("changed\n", encoding="utf-8")
                with self.assertRaisesRegex(RepositoryError, "historical file changed"):
                    self.check(root, base, accepted)
                document.write_bytes(baseline)

    def test_missing_required_p4_file_fails_closed(self) -> None:
        root, base, accepted = self.repository()
        (root / "required-p4.txt").unlink()
        with self.assertRaisesRegex(RepositoryError, "required P4 files are missing"):
            self.check(root, base, accepted)

    def test_runtime_credential_and_build_residue_fail_closed(self) -> None:
        for relative in ("state.sqlite", ".env", "build/output.js"):
            with self.subTest(relative=relative):
                root, base, accepted = self.repository()
                residue = root / relative
                residue.parent.mkdir(parents=True, exist_ok=True)
                residue.write_text("residue\n", encoding="utf-8")
                with self.assertRaisesRegex(RepositoryError, "residue is present"):
                    self.check(root, base, accepted)

    def test_real_hotfix_tree_is_an_accepted_p4_descendant(self) -> None:
        result = repository_gate.check_repository(ROOT)
        self.assertEqual(result["accepted_p4_commit"], ACCEPTED_P4_COMMIT)
        self.assertTrue(result["accepted_p4_ancestor"])


class P4EvidenceGateTests(unittest.TestCase):
    def test_complete_zero_exception_identity_is_accepted(self) -> None:
        outcome = passing_outcome()
        self.assertEqual(validate_unittest(outcome), outcome)

    def test_missing_required_p4_identity_fails_closed(self) -> None:
        outcome = passing_outcome()
        test_ids = list(outcome["test_ids"])
        test_ids.remove(
            "tests.p4.test_studio_golden_path.P4StudioGoldenPathTests."
            "test_authenticated_studio_golden_path_restart_and_causal_chain"
        )
        outcome["test_ids"] = test_ids
        with self.assertRaises(EvidenceError):
            validate_unittest(outcome)

    def test_skip_or_nonzero_failure_cannot_be_evidence(self) -> None:
        for field in ("failures", "errors", "skipped"):
            with self.subTest(field=field):
                outcome = passing_outcome()
                outcome[field] = 1
                outcome["gate_passed"] = False
                with self.assertRaises(EvidenceError):
                    validate_unittest(outcome)

    def test_static_compose_gate_never_claims_runtime_acceptance(self) -> None:
        result = check_compose(ROOT)
        self.assertEqual(result["gate"], "p4_compose_static_clean")
        self.assertEqual(result["scope"], "static_and_config_only")
        self.assertEqual(
            result["runtime_start_restart_stop"],
            "not_evaluated_by_static_gate",
        )
        self.assertNotEqual(result["gate"], "p4_compose_clean")

    def test_evidence_writer_retains_original_branch_and_base_guards(self) -> None:
        summary = json.loads((ROOT / "artifacts/p4/summary.json").read_text(encoding="utf-8"))
        results = summary["results"]
        with tempfile.TemporaryDirectory(prefix="p4-evidence-guard-") as temporary:
            evidence_path = Path(temporary) / "summary.json"
            for branch, merge_base in (("main", BASE_COMMIT), (BRANCH, "d" * 40)):
                with self.subTest(branch=branch, merge_base=merge_base):
                    with self.assertRaisesRegex(EvidenceError, "accepted P3 commit"):
                        write_p4_evidence(
                            evidence_path=evidence_path,
                            results=results,
                            unittest_outcome=passing_outcome(),
                            verified_gates=set(REQUIRED_GATES),
                            branch=branch,
                            implementation_commit="c" * 40,
                            merge_base=merge_base,
                            tree_digest="sha256:" + ("e" * 64),
                        )
            self.assertFalse(evidence_path.exists())


if __name__ == "__main__":
    unittest.main()
