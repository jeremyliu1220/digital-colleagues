# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest

from scripts.check_p11_repository import check_repository
from scripts.p11_gate_support import (
    ACCEPTANCE_COMMIT,
    BASE_COMMIT,
    BRANCH,
    acceptance_paths,
    git,
)
from tests.p11.fixtures import ROOT


class RepositoryTests(unittest.TestCase):
    def test_acceptance_allowlist_has_exactly_fifty_nine_paths(self) -> None:
        paths = acceptance_paths(ROOT)
        self.assertEqual(len(paths), 59)
        self.assertEqual(tuple(sorted(paths)), paths)

    def test_acceptance_commit_is_first_and_isolated(self) -> None:
        self.assertEqual(git(ROOT, "rev-parse", f"{ACCEPTANCE_COMMIT}^"), BASE_COMMIT)
        changed = git(
            ROOT,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            ACCEPTANCE_COMMIT,
        )
        self.assertEqual(changed, "docs/p11/acceptance.md")

    def test_repository_gate_accepts_exact_development_scope(self) -> None:
        result = check_repository(ROOT)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["branch"], BRANCH)
        self.assertEqual(result["unexpected_path_count"], 0)

    def test_historical_migrations_have_no_base_diff(self) -> None:
        changed = git(ROOT, "diff", "--name-only", BASE_COMMIT, "--", "migrations/00[1-7]_*.sql")
        self.assertEqual(changed, "")


if __name__ == "__main__":
    unittest.main()
