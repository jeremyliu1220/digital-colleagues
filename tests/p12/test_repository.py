# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

from scripts.check_p12_repository import (
    ACCEPTANCE_BLOB,
    ACCEPTANCE_COMMIT,
    ACCEPTANCE_PATH,
    ACCEPTANCE_SHA256,
    ACCEPTANCE_TREE,
    ALLOWLIST,
    BASE_COMMIT,
    BASE_TREE,
    NEW_TARGETS,
    SUMMARY_PATH,
    P12GateError,
    acceptance_paths,
    expected_changed_paths,
    git,
    implementation_paths,
    validate_changed_path_set,
    validate_makefile_contents,
)

ROOT = Path(__file__).resolve().parents[2]


class RepositoryTests(unittest.TestCase):
    def test_acceptance_allowlist_has_exactly_thirty_nine_paths(self) -> None:
        paths = acceptance_paths(ROOT)
        self.assertEqual(paths, ALLOWLIST)
        self.assertEqual(len(paths), 39)

    def test_implementation_allowlist_has_exactly_thirty_seven_paths(self) -> None:
        paths = implementation_paths(ROOT)
        self.assertEqual(len(paths), 37)
        self.assertNotIn(ACCEPTANCE_PATH, paths)
        self.assertNotIn(SUMMARY_PATH, paths)

    def test_implementation_changed_set_has_exactly_thirty_eight_paths(self) -> None:
        paths = expected_changed_paths(ROOT, final=False)
        self.assertEqual(len(paths), 38)
        self.assertIn(ACCEPTANCE_PATH, paths)
        self.assertNotIn(SUMMARY_PATH, paths)

    def test_final_changed_set_has_exactly_thirty_nine_paths(self) -> None:
        self.assertEqual(expected_changed_paths(ROOT, final=True), tuple(sorted(ALLOWLIST)))

    def test_acceptance_commit_parent_tree_and_blob_are_exact(self) -> None:
        self.assertEqual(git(ROOT, "rev-parse", f"{ACCEPTANCE_COMMIT}^"), BASE_COMMIT)
        self.assertEqual(git(ROOT, "rev-parse", f"{BASE_COMMIT}^{{tree}}"), BASE_TREE)
        self.assertEqual(git(ROOT, "rev-parse", f"{ACCEPTANCE_COMMIT}^{{tree}}"), ACCEPTANCE_TREE)
        self.assertEqual(
            git(ROOT, "rev-parse", f"{ACCEPTANCE_COMMIT}:{ACCEPTANCE_PATH}"), ACCEPTANCE_BLOB
        )

    def test_acceptance_working_file_identity_is_exact(self) -> None:
        self.assertEqual(git(ROOT, "hash-object", ACCEPTANCE_PATH), ACCEPTANCE_BLOB)
        digest = subprocess.check_output(
            ["shasum", "-a", "256", ACCEPTANCE_PATH], cwd=ROOT, text=True
        ).split()[0]
        self.assertEqual(digest, ACCEPTANCE_SHA256)

    def test_acceptance_commit_changes_only_contract(self) -> None:
        changed = git(
            ROOT,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            ACCEPTANCE_COMMIT,
        )
        self.assertEqual(changed, ACCEPTANCE_PATH)

    def test_implementation_path_set_validates(self) -> None:
        validate_changed_path_set(
            acceptance_paths(ROOT), expected_changed_paths(ROOT, final=False), final=False
        )

    def test_final_path_set_validates(self) -> None:
        validate_changed_path_set(
            acceptance_paths(ROOT), expected_changed_paths(ROOT, final=True), final=True
        )

    def test_missing_implementation_path_fails_closed(self) -> None:
        changed = expected_changed_paths(ROOT, final=False)[:-1]
        with self.assertRaises(P12GateError):
            validate_changed_path_set(acceptance_paths(ROOT), changed, final=False)

    def test_unexpected_path_fails_closed(self) -> None:
        changed = (*expected_changed_paths(ROOT, final=False), "src/new.py")
        with self.assertRaises(P12GateError):
            validate_changed_path_set(acceptance_paths(ROOT), changed, final=False)

    def test_summary_is_required_only_for_final(self) -> None:
        with self.assertRaises(P12GateError):
            validate_changed_path_set(
                acceptance_paths(ROOT), expected_changed_paths(ROOT, final=False), final=True
            )

    def test_makefile_change_is_exactly_bounded(self) -> None:
        base = subprocess.check_output(
            ["git", "show", f"{BASE_COMMIT}:Makefile"], cwd=ROOT, text=True
        )
        validate_makefile_contents(base, (ROOT / "Makefile").read_text(encoding="utf-8"))

    def test_preexisting_makefile_recipe_drift_fails_closed(self) -> None:
        base = subprocess.check_output(
            ["git", "show", f"{BASE_COMMIT}:Makefile"], cwd=ROOT, text=True
        )
        current = (ROOT / "Makefile").read_text(encoding="utf-8")
        mutated = current.replace("p11r-test:\n", "p11r-test-old:\n", 1)
        with self.assertRaises(P12GateError):
            validate_makefile_contents(base, mutated)

    def test_generic_ci_alias_must_point_only_to_p12(self) -> None:
        base = subprocess.check_output(
            ["git", "show", f"{BASE_COMMIT}:Makefile"], cwd=ROOT, text=True
        )
        current = (ROOT / "Makefile").read_text(encoding="utf-8")
        mutated = current.replace("ci: p12-ci", "ci: p12-ci p11-ci", 1)
        with self.assertRaises(P12GateError):
            validate_makefile_contents(base, mutated)

    def test_new_makefile_target_set_is_exact(self) -> None:
        self.assertEqual(
            NEW_TARGETS,
            (
                "p12-test",
                "p12-implementation-check",
                "p12-ci",
                "p12-evidence-preflight",
                "evidence-p12",
                "p12-check",
            ),
        )


if __name__ == "__main__":
    unittest.main()
