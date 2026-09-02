# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import check_p6_repository as repository_gate
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


if __name__ == "__main__":
    unittest.main()
