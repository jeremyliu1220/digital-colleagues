# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import subprocess
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

from scripts import check_p6_repository as repository_gate
from scripts import collect_p6_evidence as evidence_gate
from tests.p6.fixtures import ROOT


def git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class P6RepositoryGateTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str) -> None:
        document = root / relative
        document.parent.mkdir(parents=True, exist_ok=True)
        document.write_text(content, encoding="utf-8")

    def commit(self, root: Path, message: str) -> str:
        git(root, "add", ".")
        git(
            root,
            "-c",
            "user.name=P6 Gate Test",
            "-c",
            "user.email=p6-gate.invalid",
            "commit",
            "-m",
            message,
        )
        return git(root, "rev-parse", "HEAD")

    def repository(self) -> tuple[Path, dict[str, str]]:
        temporary = tempfile.TemporaryDirectory(prefix="p6-repository-gate-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        git(root, "init", "--initial-branch=main")
        self.write(root, "base.txt", "accepted P5 base\n")
        base = self.commit(root, "accepted P5")
        for relative in repository_gate.ACCEPTANCE_DOCUMENT_PATHS:
            self.write(root, relative, f"fixed P6 acceptance {relative}\n")
        acceptance = self.commit(root, "fixed P6 acceptance")
        self.write(root, "required-p6.txt", "P6 implementation\n")
        self.write(
            root,
            "migrations/007_governance_hardening.sql",
            "-- synthetic P6 repository-gate migration\n",
        )
        implementation = self.commit(root, "P6 implementation")
        return root, {
            "base": base,
            "acceptance": acceptance,
            "implementation": implementation,
        }

    def check(
        self,
        root: Path,
        commits: dict[str, str],
        *,
        trusted: str | None = None,
    ) -> dict[str, object]:
        with (
            patch.object(repository_gate, "BASE_COMMIT", commits["base"]),
            patch.object(repository_gate, "ACCEPTANCE_COMMIT", commits["acceptance"]),
            patch.object(
                repository_gate,
                "TRUSTED_P6_COMMIT",
                trusted or commits["acceptance"],
            ),
            patch.object(
                repository_gate,
                "REQUIRED_FILES",
                {"required-p6.txt", "migrations/007_governance_hardening.sql"},
            ),
            patch.object(
                repository_gate,
                "check_p5_repository",
                return_value={"gate": "p5_repository_clean", "residue_count": 0},
            ),
        ):
            return repository_gate.check_repository(root)

    def test_main_original_branch_and_normal_descendant_pass(self) -> None:
        root, commits = self.repository()
        self.assertEqual(self.check(root, commits)["branch"], "main")
        git(root, "switch", "-c", repository_gate.BRANCH)
        self.assertEqual(self.check(root, commits)["branch"], repository_gate.BRANCH)
        self.write(root, "descendant.txt", "normal descendant\n")
        self.commit(root, "normal descendant")
        self.assertTrue(self.check(root, commits)["trusted_p6_ancestor"])

    def test_wrong_ancestry_and_missing_trusted_commit_fail_closed(self) -> None:
        root, commits = self.repository()
        git(root, "switch", "-c", "unrelated", commits["base"])
        with self.assertRaisesRegex(repository_gate.RepositoryError, "not an ancestor"):
            self.check(root, commits)
        git(root, "switch", "main")
        with self.assertRaisesRegex(repository_gate.RepositoryError, "unavailable"):
            self.check(root, commits, trusted="f" * 40)

    def test_acceptance_immutable_drift_and_missing_required_file_fail_closed(self) -> None:
        root, commits = self.repository()
        target = root / repository_gate.ACCEPTANCE_DOCUMENT_PATHS[0]
        accepted = target.read_bytes()
        target.write_text("drifted\n", encoding="utf-8")
        with self.assertRaisesRegex(repository_gate.RepositoryError, "document changed"):
            self.check(root, commits)
        target.write_bytes(accepted)
        (root / "required-p6.txt").unlink()
        with self.assertRaisesRegex(repository_gate.RepositoryError, "files are missing"):
            self.check(root, commits)

    def test_exact_root_and_real_development_tree_pass(self) -> None:
        root, commits = self.repository()
        nested = root / "nested"
        nested.mkdir()
        with self.assertRaisesRegex(repository_gate.RepositoryError, "root is not exact"):
            self.check(nested, commits)
        current = repository_gate.check_repository(ROOT)
        self.assertTrue(current["trusted_p6_ancestor"])
        self.assertEqual(current["merge_base"], repository_gate.BASE_COMMIT)

    def test_evidence_writer_requires_exact_branch_gates_and_zero_cleanup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p6-evidence-gate-") as name:
            root = Path(name)
            evidence_path = root / "artifacts/p6/summary.json"
            unittest_outcome: dict[str, Any] = {
                "tests_run": 1,
                "failures": 0,
                "errors": 0,
                "skipped": 0,
                "expected_failures": 0,
                "unexpected_successes": 0,
                "gate_passed": True,
                "test_ids": ["synthetic:test"],
                "fault_boundaries": ["synthetic:boundary"],
            }
            cleanup: dict[str, Any] = {
                "passed": True,
                "containers_remaining": 0,
                "networks_remaining": 0,
                "volumes_remaining": 0,
            }
            escape_metric: dict[str, Any] = {
                "status": "observed",
                "numerator": 0,
                "denominator": 1,
                "rate": 0.0,
                "reason": None,
                "source": "durable synthetic candidate observations",
                "safe_causal_references": ["correlation:synthetic-candidate"],
                "evaluated_attempts": [
                    {
                        "candidate_id": "proposal:synthetic-candidate",
                        "escaped": False,
                    }
                ],
                "safe_refusal_count": 1,
                "evidence_class": "synthetic",
            }
            clean_results: dict[str, dict[str, Any]] = {
                "compose_runtime": {"status": "passed", "cleanup": cleanup},
                "abuse": {"unauthorized_proposal_escape_rate": escape_metric},
                "golden": {"unauthorized_proposal_escape_rate": escape_metric},
            }

            def write(
                *,
                branch: str = repository_gate.BRANCH,
                verified_gates: set[str] | None = None,
                results: dict[str, dict[str, Any]] | None = None,
            ) -> None:
                evidence_gate.write_p6_evidence(
                    evidence_path=evidence_path,
                    root=root,
                    results=clean_results if results is None else results,
                    unittest_outcome=unittest_outcome,
                    verified_gates=(
                        set(evidence_gate.REQUIRED_GATES)
                        if verified_gates is None
                        else verified_gates
                    ),
                    branch=branch,
                    implementation_commit="a" * 40,
                    merge_base=repository_gate.BASE_COMMIT,
                    tree_digest="sha256:" + "b" * 64,
                    migration_digest="sha256:" + "c" * 64,
                )

            write()
            accepted = evidence_path.read_bytes()

            attempts: tuple[Callable[[], None], ...] = (
                lambda: write(branch="main"),
                lambda: write(verified_gates=set()),
                lambda: write(
                    results={
                        "compose_runtime": {
                            "status": "passed",
                            "cleanup": {**cleanup, "volumes_remaining": 1},
                        }
                    }
                ),
                lambda: write(
                    results={
                        "compose_runtime": {
                            "status": "passed",
                            "cleanup": cleanup,
                        },
                        "unsafe": {"token": "forbidden-material"},
                    }
                ),
                lambda: write(
                    results={
                        **clean_results,
                        "golden": {
                            "unauthorized_proposal_escape_rate": {
                                **escape_metric,
                                "numerator": 1,
                                "rate": 1.0,
                                "safe_refusal_count": 0,
                                "evaluated_attempts": [
                                    {
                                        "candidate_id": "proposal:synthetic-candidate",
                                        "escaped": True,
                                    }
                                ],
                            }
                        },
                    }
                ),
            )
            for attempt in attempts:
                with self.assertRaises(evidence_gate.EvidenceError):
                    attempt()
                self.assertEqual(evidence_path.read_bytes(), accepted)


if __name__ == "__main__":
    unittest.main()
