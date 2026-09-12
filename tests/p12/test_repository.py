# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import os
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

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
    REJECTED_V1_BRANCH,
    REJECTED_V1_COMMIT,
    REJECTED_V2_ACCEPTANCE_BLOB,
    REJECTED_V2_ACCEPTANCE_SHA256,
    REJECTED_V2_BRANCH,
    REJECTED_V2_COMMIT,
    SUMMARY_PATH,
    SUPERSEDED_V3_ACCEPTANCE_BLOB,
    SUPERSEDED_V3_ACCEPTANCE_BYTE_COUNT,
    SUPERSEDED_V3_ACCEPTANCE_LINE_COUNT,
    SUPERSEDED_V3_ACCEPTANCE_SHA256,
    SUPERSEDED_V3_BRANCH,
    SUPERSEDED_V3_COMMIT,
    P12GateError,
    acceptance_paths,
    check_git_indirections,
    expected_changed_paths,
    git,
    git_succeeds,
    implementation_paths,
    raw_blob_bytes,
    raw_commit_identity,
    ref_exists,
    validate_changed_path_set,
    validate_makefile_contents,
    validate_no_graft,
    validate_pr14_metadata,
)

ROOT = Path(__file__).resolve().parents[2]


class RepositoryTests(unittest.TestCase):
    def test_acceptance_allowlist_has_exactly_forty_two_paths(self) -> None:
        paths = acceptance_paths(ROOT)
        self.assertEqual(paths, ALLOWLIST)
        self.assertEqual(len(paths), 42)

    def test_implementation_allowlist_has_exactly_forty_paths(self) -> None:
        paths = implementation_paths(ROOT)
        self.assertEqual(len(paths), 40)
        self.assertNotIn(ACCEPTANCE_PATH, paths)
        self.assertNotIn(SUMMARY_PATH, paths)

    def test_implementation_changed_set_has_exactly_forty_one_paths(self) -> None:
        paths = expected_changed_paths(ROOT, final=False)
        self.assertEqual(len(paths), 41)
        self.assertIn(ACCEPTANCE_PATH, paths)
        self.assertNotIn(SUMMARY_PATH, paths)

    def test_final_changed_set_has_exactly_forty_two_paths(self) -> None:
        self.assertEqual(expected_changed_paths(ROOT, final=True), tuple(sorted(ALLOWLIST)))

    def test_acceptance_commit_parent_tree_and_blob_are_exact(self) -> None:
        self.assertEqual(git(ROOT, "rev-parse", f"{ACCEPTANCE_COMMIT}^"), BASE_COMMIT)
        self.assertEqual(git(ROOT, "rev-parse", f"{BASE_COMMIT}^{{tree}}"), BASE_TREE)
        self.assertEqual(git(ROOT, "rev-parse", f"{ACCEPTANCE_COMMIT}^{{tree}}"), ACCEPTANCE_TREE)
        self.assertEqual(
            git(ROOT, "rev-parse", f"{ACCEPTANCE_COMMIT}:{ACCEPTANCE_PATH}"), ACCEPTANCE_BLOB
        )
        raw_tree, raw_parents, _ = raw_commit_identity(ROOT, ACCEPTANCE_COMMIT)
        self.assertEqual(raw_tree, ACCEPTANCE_TREE)
        self.assertEqual(raw_parents, (BASE_COMMIT,))
        with TemporaryDirectory() as value:
            graft = Path(value) / "grafts"
            validate_no_graft(graft)
            graft.write_text(f"{ACCEPTANCE_COMMIT} {BASE_COMMIT}\n", encoding="ascii")
            with self.assertRaises(P12GateError):
                validate_no_graft(graft)
        for name in (
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_COMMON_DIR",
            "GIT_CONFIG_COUNT",
            "GIT_CONFIG_GLOBAL",
            "GIT_CONFIG_KEY_0",
            "GIT_CONFIG_PARAMETERS",
            "GIT_CONFIG_SYSTEM",
            "GIT_CONFIG_VALUE_0",
            "GIT_DIR",
            "GIT_GRAFT_FILE",
            "GIT_INDEX_FILE",
            "GIT_NAMESPACE",
            "GIT_OBJECT_DIRECTORY",
            "GIT_REPLACE_REF_BASE",
            "GIT_SHALLOW_FILE",
            "GIT_WORK_TREE",
        ):
            with (
                self.subTest(git_environment=name),
                mock.patch.dict(os.environ, {name: "forbidden"}),
            ):
                with self.assertRaises(P12GateError):
                    check_git_indirections(ROOT)

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
        current = (ROOT / "Makefile").read_text(encoding="utf-8")
        validate_makefile_contents(base, current)
        swapped = (
            current.replace("--scope test", "--scope temporary", 1)
            .replace("--scope current-ci", "--scope test", 1)
            .replace("--scope temporary", "--scope current-ci", 1)
        )
        with self.assertRaises(P12GateError):
            validate_makefile_contents(base, swapped)
        with self.assertRaises(P12GateError):
            validate_makefile_contents(base, current + "\t@echo extra\n")

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
                "p12-current-ci",
                "p12-portable-history",
                "p12-implementation-check",
                "p12-ci",
                "p12-evidence-preflight",
                "evidence-p12",
                "p12-check",
            ),
        )

    def test_v1_v2_v3_refs_are_preserved(self) -> None:
        self.assertEqual(
            git(ROOT, "rev-parse", f"refs/heads/{REJECTED_V1_BRANCH}"), REJECTED_V1_COMMIT
        )
        self.assertEqual(
            git(ROOT, "rev-parse", f"refs/heads/{REJECTED_V2_BRANCH}"), REJECTED_V2_COMMIT
        )
        self.assertEqual(
            git(ROOT, "rev-parse", f"refs/remotes/origin/{REJECTED_V2_BRANCH}"),
            REJECTED_V2_COMMIT,
        )
        self.assertEqual(
            git(ROOT, "rev-parse", f"refs/heads/{SUPERSEDED_V3_BRANCH}"),
            SUPERSEDED_V3_COMMIT,
        )
        v2 = raw_blob_bytes(ROOT, REJECTED_V2_ACCEPTANCE_BLOB)
        self.assertEqual(hashlib.sha256(v2).hexdigest(), REJECTED_V2_ACCEPTANCE_SHA256)
        v3 = raw_blob_bytes(ROOT, SUPERSEDED_V3_ACCEPTANCE_BLOB)
        self.assertEqual(hashlib.sha256(v3).hexdigest(), SUPERSEDED_V3_ACCEPTANCE_SHA256)
        self.assertEqual(len(v3), SUPERSEDED_V3_ACCEPTANCE_BYTE_COUNT)
        self.assertEqual(len(v3.splitlines()), SUPERSEDED_V3_ACCEPTANCE_LINE_COUNT)

    def test_v1_v2_v3_are_not_v4_ancestors(self) -> None:
        for commit in (REJECTED_V1_COMMIT, REJECTED_V2_COMMIT, SUPERSEDED_V3_COMMIT):
            with self.subTest(commit=commit):
                self.assertFalse(git_succeeds(ROOT, "merge-base", "--is-ancestor", commit, "HEAD"))

    def test_attempt_ref_presence_and_absence_are_exact(self) -> None:
        expected = {
            f"refs/heads/{REJECTED_V1_BRANCH}": True,
            f"refs/heads/{REJECTED_V2_BRANCH}": True,
            f"refs/heads/{SUPERSEDED_V3_BRANCH}": True,
            f"refs/remotes/origin/{REJECTED_V1_BRANCH}": False,
            f"refs/remotes/origin/{REJECTED_V2_BRANCH}": True,
            f"refs/remotes/origin/{SUPERSEDED_V3_BRANCH}": False,
        }
        for ref, present in expected.items():
            with self.subTest(ref=ref):
                self.assertEqual(ref_exists(ROOT, ref), present)

    def test_pr14_close_without_merge_boundary_is_exact(self) -> None:
        base = {
            "number": 14,
            "state": "CLOSED",
            "baseRefName": "main",
            "baseRefOid": BASE_COMMIT,
            "headRefName": REJECTED_V2_BRANCH,
            "headRefOid": REJECTED_V2_COMMIT,
            "autoMergeRequest": None,
            "mergedAt": None,
            "mergeCommit": None,
            "url": "https://github.com/jeremyliu1220/digital-colleagues/pull/14",
        }
        self.assertEqual(validate_pr14_metadata(base), "CLOSED")
        with self.assertRaises(P12GateError):
            validate_pr14_metadata(dict(base, state="OPEN"))
        for field in ("mergedAt", "mergeCommit", "autoMergeRequest"):
            with self.subTest(non_null=field):
                value = dict(base)
                value[field] = {"oid": "0" * 40} if field == "mergeCommit" else "non-null"
                with self.assertRaises(P12GateError):
                    validate_pr14_metadata(value)
            with self.subTest(missing=field):
                value = dict(base)
                del value[field]
                with self.assertRaises(P12GateError):
                    validate_pr14_metadata(value)
        for field in ("number", "baseRefOid", "headRefOid", "headRefName"):
            with self.subTest(wrong_identity=field):
                value = dict(base)
                value[field] = 15 if field == "number" else "wrong"
                with self.assertRaises(P12GateError):
                    validate_pr14_metadata(value)
        with self.assertRaises(P12GateError):
            validate_pr14_metadata({"state": "CLOSED"})


if __name__ == "__main__":
    unittest.main()
