# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

from scripts.check_p11r_repository import (
    ACCEPTANCE_BLOB,
    ACCEPTANCE_COMMIT,
    ACCEPTANCE_PATH,
    BASE_COMMIT,
    NEW_TARGETS,
    SUMMARY_PATH,
    P11RGateError,
    acceptance_paths,
    git,
    implementation_paths,
    validate_changed_path_set,
    validate_makefile_contents,
)
from scripts.run_p11r_toolchain import DEVELOPMENT_ONLY_TEST, current_tree_test_ids

ROOT = Path(__file__).resolve().parents[2]


class RepositoryTests(unittest.TestCase):
    def test_acceptance_allowlist_has_exactly_fifteen_paths(self) -> None:
        paths = acceptance_paths(ROOT)
        self.assertEqual(len(paths), 15)
        self.assertEqual(
            paths[7:9], ("scripts/check_p11r_repository.py", "scripts/check_p11r_provenance.py")
        )

    def test_implementation_allowlist_has_exactly_thirteen_paths(self) -> None:
        paths = implementation_paths(ROOT)
        self.assertEqual(len(paths), 13)
        self.assertNotIn(ACCEPTANCE_PATH, paths)
        self.assertNotIn(SUMMARY_PATH, paths)

    def test_acceptance_commit_parent_and_blob_are_exact(self) -> None:
        self.assertEqual(git(ROOT, "rev-parse", f"{ACCEPTANCE_COMMIT}^"), BASE_COMMIT)
        self.assertEqual(
            git(ROOT, "rev-parse", f"{ACCEPTANCE_COMMIT}:{ACCEPTANCE_PATH}"),
            ACCEPTANCE_BLOB,
        )

    def test_acceptance_commit_changes_only_the_contract(self) -> None:
        changed = git(
            ROOT,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            ACCEPTANCE_COMMIT,
        )
        self.assertEqual(changed, ACCEPTANCE_PATH)

    def test_current_tree_inventory_has_exactly_one_hundred_literal_ids(self) -> None:
        identifiers = current_tree_test_ids(ROOT)
        self.assertEqual(len(identifiers), 100)
        self.assertEqual(len(set(identifiers)), 100)
        self.assertTrue(all(value.startswith("tests.p11.") for value in identifiers))

    def test_development_only_test_is_the_sole_exclusion(self) -> None:
        identifiers = current_tree_test_ids(ROOT)
        self.assertNotIn(DEVELOPMENT_ONLY_TEST, identifiers)
        self.assertEqual(
            DEVELOPMENT_ONLY_TEST,
            "tests.p11.test_repository.RepositoryTests."
            "test_repository_gate_accepts_exact_development_scope",
        )

    def test_implementation_and_evidence_path_sets_are_distinct_and_exact(self) -> None:
        paths = acceptance_paths(ROOT)
        implementation = tuple(path for path in paths if path != SUMMARY_PATH)
        self.assertFalse(validate_changed_path_set(paths, implementation))
        self.assertTrue(validate_changed_path_set(paths, paths))

    def test_missing_implementation_path_fails_closed(self) -> None:
        paths = acceptance_paths(ROOT)
        changed = tuple(path for path in paths if path not in {SUMMARY_PATH, "Makefile"})
        with self.assertRaises(P11RGateError):
            validate_changed_path_set(paths, changed)

    def test_unexpected_path_fails_closed(self) -> None:
        paths = acceptance_paths(ROOT)
        changed = (*tuple(path for path in paths if path != SUMMARY_PATH), "src/new.py")
        with self.assertRaises(P11RGateError):
            validate_changed_path_set(paths, changed)

    def test_makefile_change_is_strictly_additive(self) -> None:
        base = subprocess.check_output(
            ["git", "show", f"{BASE_COMMIT}:Makefile"], cwd=ROOT, text=True
        )
        validate_makefile_contents(base, (ROOT / "Makefile").read_text(encoding="utf-8"))

    def test_existing_makefile_recipe_drift_fails_closed(self) -> None:
        base = subprocess.check_output(
            ["git", "show", f"{BASE_COMMIT}:Makefile"], cwd=ROOT, text=True
        )
        current = (ROOT / "Makefile").read_text(encoding="utf-8")
        mutated = current.replace(
            "$(PYTHON) -B -m scripts.run_p11_toolchain --scope test",
            "$(PYTHON) -B -m scripts.run_p11r_toolchain --scope test",
            1,
        )
        with self.assertRaises(P11RGateError):
            validate_makefile_contents(base, mutated)

    def test_new_makefile_target_set_is_exact(self) -> None:
        self.assertEqual(
            set(NEW_TARGETS),
            {"p11-ci", "ci", "p11r-test", "p11r-compose-smoke", "p11r-check", "evidence-p11r"},
        )


if __name__ == "__main__":
    unittest.main()
