# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import subprocess
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

from scripts import check_p7_repository as repository_gate
from scripts import collect_p7_evidence as evidence_gate

ROOT = Path(__file__).resolve().parents[2]


def git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class P7RepositoryGateTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str) -> None:
        document = root / relative
        document.parent.mkdir(parents=True, exist_ok=True)
        document.write_text(content, encoding="utf-8")

    def commit(self, root: Path, message: str) -> str:
        git(root, "add", ".")
        git(
            root,
            "-c",
            "user.name=P7 Gate Test",
            "-c",
            "user.email=p7-gate.invalid",
            "commit",
            "-m",
            message,
        )
        return git(root, "rev-parse", "HEAD")

    def repository(self) -> tuple[Path, dict[str, str]]:
        temporary = tempfile.TemporaryDirectory(prefix="p7-repository-gate-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        git(root, "init", "--initial-branch=main")
        self.write(root, "migrations/007_governance_hardening.sql", "-- accepted P6\n")
        base = self.commit(root, "accepted P6")
        for relative in repository_gate.ACCEPTANCE_DOCUMENT_PATHS:
            self.write(root, relative, f"fixed P7 acceptance {relative}\n")
        acceptance = self.commit(root, "fixed P7 acceptance")
        self.write(root, "required-p7.txt", "P7 implementation\n")
        implementation = self.commit(root, "P7 implementation")
        return root, {
            "base": base,
            "acceptance": acceptance,
            "implementation": implementation,
        }

    def check(self, root: Path, commits: dict[str, str]) -> dict[str, object]:
        with (
            patch.object(repository_gate, "BASE_COMMIT", commits["base"]),
            patch.object(repository_gate, "ACCEPTANCE_COMMIT", commits["acceptance"]),
            patch.object(repository_gate, "TRUSTED_P7_COMMIT", commits["acceptance"]),
            patch.object(repository_gate, "REQUIRED_FILES", {"required-p7.txt"}),
            patch.object(
                repository_gate,
                "check_p6_repository",
                return_value={"gate": "p6_repository_clean", "residue_count": 0},
            ),
        ):
            return repository_gate.check_repository(root)

    def test_main_development_branch_and_normal_descendant_pass(self) -> None:
        root, commits = self.repository()
        self.assertEqual(self.check(root, commits)["branch"], "main")
        git(root, "switch", "-c", repository_gate.BRANCH)
        self.assertEqual(self.check(root, commits)["branch"], repository_gate.BRANCH)
        self.write(root, "descendant.txt", "normal descendant\n")
        self.commit(root, "normal descendant")
        self.assertTrue(self.check(root, commits)["trusted_p7_ancestor"])

    def test_wrong_ancestry_acceptance_drift_and_required_file_fail_closed(self) -> None:
        root, commits = self.repository()
        git(root, "switch", "-c", "unrelated", commits["base"])
        with self.assertRaisesRegex(repository_gate.RepositoryError, "not an ancestor"):
            self.check(root, commits)
        git(root, "switch", "main")
        target = root / repository_gate.ACCEPTANCE_DOCUMENT_PATHS[0]
        accepted = target.read_bytes()
        target.write_text("drifted\n", encoding="utf-8")
        with self.assertRaisesRegex(repository_gate.RepositoryError, "document changed"):
            self.check(root, commits)
        target.write_bytes(accepted)
        (root / "required-p7.txt").unlink()
        with self.assertRaisesRegex(repository_gate.RepositoryError, "files are missing"):
            self.check(root, commits)

    def test_historical_drift_and_migration_008_fail_closed(self) -> None:
        root, commits = self.repository()
        migration = root / "migrations/007_governance_hardening.sql"
        migration.write_text("-- drift\n", encoding="utf-8")
        with self.assertRaisesRegex(repository_gate.RepositoryError, "historical material"):
            self.check(root, commits)
        git(root, "restore", "migrations/007_governance_hardening.sql")
        self.write(root, "migrations/008_forbidden.sql", "-- forbidden\n")
        with self.assertRaisesRegex(repository_gate.RepositoryError, "migration 008"):
            self.check(root, commits)

    def test_exact_root_and_real_development_tree_pass(self) -> None:
        root, commits = self.repository()
        nested = root / "nested"
        nested.mkdir()
        with self.assertRaisesRegex(repository_gate.RepositoryError, "root is not exact"):
            self.check(nested, commits)
        current = repository_gate.check_repository(ROOT)
        self.assertTrue(current["trusted_p7_ancestor"])
        self.assertEqual(current["merge_base"], repository_gate.BASE_COMMIT)

    def test_evidence_writer_requires_exact_branch_gates_claims_and_zero_cleanup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7-evidence-gate-") as name:
            root = Path(name)
            evidence_path = root / "artifacts/p7/summary.json"
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
                "credential_files_remaining": 0,
                "stub_processes_remaining": 0,
            }
            clean_results: dict[str, dict[str, Any]] = {
                key: {}
                for key in (
                    "repository",
                    "provenance",
                    "architecture",
                    "model_adapter",
                    "channel_adapter",
                    "configuration",
                    "compose",
                )
            }
            clean_results["repository"] = {
                "acceptance_documents_immutable": True,
                "historical_drift_count": 0,
                "migration_008": False,
                "residue_count": 0,
            }
            clean_results.update(
                {
                    "compose_runtime": {
                        "status": "passed",
                        "unexpected_external_egress": 0,
                        "live_provider_evidence": "not_evaluated",
                        "human_acceptance_evidence": "not_evaluated",
                        "fresh_service_recreate_count": 2,
                        "optional_topology": [
                            "p7-stub",
                            "p7-api",
                            "p7-worker",
                            "p7-studio",
                        ],
                        "cleanup": cleanup,
                    },
                    "abuse": {
                        "authority_expansions": 0,
                        "human_approvals_from_provider": 0,
                        "unexpected_external_egress": 0,
                        "blind_ambiguous_resends": 0,
                        "public_boundary_exceptions": 0,
                    },
                    "golden": {
                        "deterministic_reference_unchanged": True,
                        "claim": "optional_adapter_contracts_passed",
                        "human_evaluation": "not_evaluated",
                        "live_provider_evidence": "not_evaluated",
                    },
                }
            )

            def write(
                *,
                branch: str = repository_gate.BRANCH,
                verified_gates: set[str] | None = None,
                results: dict[str, dict[str, Any]] | None = None,
                tree_clean: bool = True,
            ) -> None:
                evidence_gate.write_p7_evidence(
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
                    tree_clean=tree_clean,
                )

            write()
            accepted = evidence_path.read_bytes()
            attempts: tuple[Callable[[], None], ...] = (
                lambda: write(branch="main"),
                lambda: write(tree_clean=False),
                lambda: write(verified_gates=set()),
                lambda: write(
                    results={
                        **clean_results,
                        "compose_runtime": {
                            **clean_results["compose_runtime"],
                            "cleanup": {**cleanup, "volumes_remaining": 1},
                        },
                    }
                ),
                lambda: write(
                    results={
                        **clean_results,
                        "golden": {
                            **clean_results["golden"],
                            "live_provider_evidence": "passed",
                        },
                    }
                ),
                lambda: write(
                    results={
                        **clean_results,
                        "abuse": {
                            **clean_results["abuse"],
                            "authority_expansions": 1,
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
