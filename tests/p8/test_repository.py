# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.check_p4_compose_runtime import ComposeRuntimeError
from scripts.check_p8_compose_runtime import _operation_json
from scripts.check_p8_provenance import ProvenanceError, check_provenance
from scripts.check_p8_repository import (
    ACCEPTED_P8_COMMIT,
    ACCEPTED_P8_IMMUTABLE_PATHS,
    RepositoryError,
    check_repository,
)
from scripts.collect_p8_evidence import (
    EvidenceError,
    validate_studio_tests,
    write_p8_evidence,
)
from scripts.p8_release_support import ACCEPTANCE_COMMIT, BASE_COMMIT
from scripts.run_p8_toolchain import PRIOR_CURRENT_TREE
from tests.p8.fixtures import ROOT

EXPECTED_POST_MERGE_PATHS = {
    "README.md",
    "SECURITY.md",
    "docs/p8/release-checklist.md",
    "docs/product/capability-matrix.md",
    "docs/roadmap.md",
    "scripts/check_p8_provenance.py",
    "scripts/check_p8_release.py",
    "scripts/check_p8_repository.py",
    "tests/p8/test_release.py",
    "tests/p8/test_repository.py",
}


def _clone(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "repository"
    subprocess.run(["git", "clone", "--quiet", "--shared", str(ROOT), str(destination)], check=True)
    return destination


def _commit(root: Path, message: str, *, allow_empty: bool = False) -> str:
    arguments = [
        "git",
        "-c",
        "user.name=Digital Colleagues Tests",
        "-c",
        "user.email=digital-colleagues-tests.invalid",
        "commit",
        "--quiet",
        "-m",
        message,
    ]
    if allow_empty:
        arguments.append("--allow-empty")
    subprocess.run(arguments, cwd=root, check=True)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def _append_and_commit(root: Path, relative: str) -> str:
    path = root / relative
    path.write_bytes(path.read_bytes() + b"\npost-merge descendant drift\n")
    subprocess.run(["git", "add", relative], cwd=root, check=True)
    return _commit(root, f"change {relative}")


class P8RepositoryTests(unittest.TestCase):
    def test_compose_operation_json_accepts_stderr_and_rejects_missing_results(self) -> None:
        expected = {"schema_version": 1, "status": "restored"}
        self.assertEqual(
            _operation_json("", "compose progress\n" + json.dumps(expected) + "\n"),
            expected,
        )
        with self.assertRaisesRegex(ComposeRuntimeError, "no JSON object"):
            _operation_json("compose progress\n", "warning\n")

    def test_studio_evidence_requires_positive_machine_readable_counts(self) -> None:
        valid = {
            "command": "corepack npm test -- --reporter=json --outputFile=<temporary>",
            "test_files": 1,
            "test_count": 5,
            "passed": 5,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "unexpected_failures": 0,
            "status": "passed",
            "result": "passed",
        }
        self.assertEqual(validate_studio_tests(valid), valid)
        for key, value in (("test_count", 0), ("passed", 4), ("skipped", 1), ("errors", 1)):
            changed = {**valid, key: value}
            with self.assertRaises(EvidenceError, msg=key):
                validate_studio_tests(changed)

    def test_p8_aggregate_executes_all_prior_current_tree_regressions(self) -> None:
        self.assertEqual(len(PRIOR_CURRENT_TREE), 37)
        self.assertEqual(
            set(PRIOR_CURRENT_TREE),
            {
                "p2_core",
                "p3_architecture",
                "p3_migrations",
                "p3_persistence",
                "p3_runtime",
                "p3_golden",
                "p4_architecture",
                "p4_migrations",
                "p4_authentication",
                "p4_studio",
                "p4_compose",
                "p4_golden",
                "p5_architecture",
                "p5_migrations",
                "p5_builder",
                "p5_policy",
                "p5_studio",
                "p5_compose",
                "p5_golden",
                "p6_architecture",
                "p6_migrations",
                "p6_authentication",
                "p6_rbac",
                "p6_change_approval",
                "p6_effect_approval",
                "p6_audit_export",
                "p6_abuse",
                "p6_studio",
                "p6_compose",
                "p6_golden",
                "p7_architecture",
                "p7_model_adapter",
                "p7_channel_adapter",
                "p7_configuration",
                "p7_abuse",
                "p7_compose",
                "p7_golden",
            },
        )

    def test_real_tree_has_fixed_base_acceptance_history_and_required_files(self) -> None:
        result = check_repository(ROOT)
        self.assertEqual(result["gate"], "p8_repository_clean")
        self.assertEqual(result["base_commit"], BASE_COMMIT)
        self.assertEqual(result["merge_base"], BASE_COMMIT)
        self.assertEqual(result["acceptance_commit"], ACCEPTANCE_COMMIT)
        self.assertEqual(result["accepted_p8_commit"], ACCEPTED_P8_COMMIT)
        self.assertTrue(result["accepted_p8_ancestor"])
        self.assertEqual(
            result["accepted_p8_immutable_file_count"], len(ACCEPTED_P8_IMMUTABLE_PATHS)
        )
        self.assertEqual(result["historical_drift_count"], 0)
        self.assertEqual(result["residue_count"], 0)
        self.assertFalse(result["migration_008"])
        self.assertEqual(result["descendant_boundary_status"], "passed")
        self.assertEqual(result["post_merge_change_count"], 10)
        self.assertEqual(result["post_merge_path_count"], 10)
        self.assertEqual(result["post_merge_allowed_path_count"], 10)
        self.assertEqual(result["post_merge_unexpected_path_count"], 0)

    def test_real_hotfix_committed_delta_is_exactly_the_reviewed_ten_paths(self) -> None:
        changed = set(
            subprocess.check_output(
                ["git", "diff", "--name-only", ACCEPTED_P8_COMMIT, "HEAD", "--"],
                cwd=ROOT,
                text=True,
            ).splitlines()
        )
        self.assertEqual(changed, EXPECTED_POST_MERGE_PATHS)
        repository = check_repository(ROOT)
        provenance = check_provenance(ROOT)
        for result in (repository, provenance):
            self.assertEqual(result["descendant_boundary_status"], "passed")
            self.assertEqual(result["post_merge_path_count"], len(EXPECTED_POST_MERGE_PATHS))
            self.assertEqual(result["post_merge_unexpected_path_count"], 0)

    def test_committed_out_of_scope_descendant_paths_fail_both_gates(self) -> None:
        paths = (
            "src/digital_colleagues/__init__.py",
            "Dockerfile",
            "Dockerfile.p7",
            "compose.yaml",
            "requirements/p8.lock",
            "release/supply-chain-inputs.json",
            "artifacts/p8/summary.json",
            "provenance/p8-migration-receipt.json",
            "migrations/manifest.json",
            "docs/p8/acceptance.md",
            "docs/p7/acceptance.md",
            "artifacts/p7/summary.json",
            "provenance/p7-migration-receipt.json",
            "docs/development.md",
            "scripts/check_p8_operations.py",
            "tests/p8/test_backup_restore.py",
        )
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-scope-") as name:
            temporary = Path(name)
            for index, relative in enumerate(paths):
                with self.subTest(relative=relative):
                    root = _clone(temporary / str(index))
                    _append_and_commit(root, relative)
                    with self.assertRaisesRegex(RepositoryError, "post-merge commit"):
                        check_repository(root)
                    with self.assertRaisesRegex(ProvenanceError, "post-merge commit"):
                        check_provenance(root)

    def test_rename_and_copy_sources_and_destinations_cannot_escape_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-rename-") as name:
            temporary = Path(name)

            outside_to_allowed = _clone(temporary / "outside-to-allowed")
            (outside_to_allowed / "README.md").unlink()
            subprocess.run(
                ["git", "mv", "-f", "docs/development.md", "README.md"],
                cwd=outside_to_allowed,
                check=True,
            )
            _commit(outside_to_allowed, "rename outside path to allowed path")

            allowed_to_outside = _clone(temporary / "allowed-to-outside")
            subprocess.run(
                ["git", "mv", "README.md", "docs/post-merge-escape.md"],
                cwd=allowed_to_outside,
                check=True,
            )
            _commit(allowed_to_outside, "rename allowed path to outside path")

            copy_to_allowed = _clone(temporary / "copy-to-allowed")
            shutil.copyfile(copy_to_allowed / "docs/development.md", copy_to_allowed / "README.md")
            subprocess.run(["git", "add", "README.md"], cwd=copy_to_allowed, check=True)
            _commit(copy_to_allowed, "copy outside path to allowed path")

            for label, root in (
                ("outside-to-allowed", outside_to_allowed),
                ("allowed-to-outside", allowed_to_outside),
                ("copy-to-allowed", copy_to_allowed),
            ):
                with self.subTest(label=label):
                    with self.assertRaisesRegex(RepositoryError, "post-merge commit"):
                        check_repository(root)
                    with self.assertRaisesRegex(ProvenanceError, "post-merge commit"):
                        check_provenance(root)

    def test_out_of_scope_staged_unstaged_and_untracked_paths_fail_both_gates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-dirty-") as name:
            temporary = Path(name)
            for state in ("staged", "unstaged", "untracked"):
                with self.subTest(state=state):
                    root = _clone(temporary / state)
                    if state == "untracked":
                        (root / "docs/post-merge-untracked.md").write_text(
                            "post-merge descendant drift\n", encoding="utf-8"
                        )
                    else:
                        path = root / "src/digital_colleagues/__init__.py"
                        path.write_bytes(path.read_bytes() + b"\npost-merge descendant drift\n")
                        if state == "staged":
                            subprocess.run(
                                ["git", "add", "src/digital_colleagues/__init__.py"],
                                cwd=root,
                                check=True,
                            )
                    with self.assertRaisesRegex(RepositoryError, "working tree"):
                        check_repository(root)
                    with self.assertRaisesRegex(ProvenanceError, "working tree"):
                        check_provenance(root)

    def test_accepted_p8_immutable_files_modified_or_deleted_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-immutable-") as name:
            temporary = Path(name)
            for relative in ACCEPTED_P8_IMMUTABLE_PATHS:
                for operation in ("modify", "delete"):
                    label = relative.replace("/", "-") + "-" + operation
                    root = _clone(temporary / label)
                    path = root / relative
                    if operation == "modify":
                        path.write_bytes(path.read_bytes() + b"\n")
                    else:
                        path.unlink()
                    with self.assertRaisesRegex(
                        RepositoryError, "accepted P8 immutable file", msg=label
                    ):
                        check_repository(root)
                    with self.assertRaises(ProvenanceError, msg=label):
                        check_provenance(root)

    def test_historical_migration_and_residue_drift_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-repository-") as name:
            temporary = Path(name)
            for category in ("history", "migration", "residue"):
                root = _clone(temporary / category)
                if category == "history":
                    path = root / "docs/p7/acceptance.md"
                    path.write_text(path.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
                elif category == "migration":
                    (root / "migrations/008_forbidden.sql").write_text(
                        "SELECT 1;\n", encoding="utf-8"
                    )
                else:
                    (root / "runtime.log").write_text("residue\n", encoding="utf-8")
                with self.assertRaises(RepositoryError, msg=category):
                    check_repository(root)
                if category != "residue":
                    with self.assertRaises(ProvenanceError, msg=category):
                        check_provenance(root)

    def test_wrong_ancestry_and_missing_required_file_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-ancestry-") as name:
            root = _clone(Path(name))
            subprocess.run(
                ["git", "switch", "--quiet", "--orphan", "unrelated"], cwd=root, check=True
            )
            _commit(root, "unrelated history", allow_empty=True)
            with self.assertRaisesRegex(RepositoryError, "accepted P8 commit is not an ancestor"):
                check_repository(root)
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-required-") as name:
            root = _clone(Path(name))
            target = root / "docs/p8/operations.md"
            target.unlink()
            with self.assertRaisesRegex(RepositoryError, "required P8"):
                check_repository(root)

    def test_source_base_and_acceptance_objects_remain_available(self) -> None:
        for commit in (BASE_COMMIT, ACCEPTANCE_COMMIT, ACCEPTED_P8_COMMIT):
            self.assertEqual(
                subprocess.run(
                    ["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT
                ).returncode,
                0,
            )
        self.assertIsNotNone(shutil.which("git"))

    def test_unavailable_accepted_p8_commit_fails_closed(self) -> None:
        with patch("scripts.check_p8_repository.ACCEPTED_P8_COMMIT", "f" * 40):
            with self.assertRaisesRegex(RepositoryError, "accepted P8 commit is unavailable"):
                check_repository(ROOT)

    def test_post_merge_descendant_passes_and_provenance_stays_accepted_commit_anchored(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-descendant-") as name:
            root = _clone(Path(name))
            baseline = check_provenance(root)
            readme = root / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8") + "\nPost-merge checkpoint fixture.\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
            descendant = _commit(root, "post-merge checkpoint fixture")
            repository = check_repository(root)
            provenance = check_provenance(root)
            self.assertNotEqual(descendant, ACCEPTED_P8_COMMIT)
            self.assertTrue(repository["accepted_p8_ancestor"])
            self.assertEqual(provenance["accepted_p8_commit"], ACCEPTED_P8_COMMIT)
            self.assertEqual(
                provenance["implementation_range"], f"{BASE_COMMIT}..{ACCEPTED_P8_COMMIT}"
            )
            self.assertEqual(
                provenance["implementation_tree_digest"], baseline["implementation_tree_digest"]
            )
            self.assertEqual(provenance["receipt_digest"], baseline["receipt_digest"])

    def test_provenance_fails_without_accepted_ancestor_or_with_receipt_drift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-provenance-") as name:
            temporary = Path(name)
            unrelated = _clone(temporary / "unrelated")
            subprocess.run(
                ["git", "switch", "--quiet", "--orphan", "unrelated"],
                cwd=unrelated,
                check=True,
            )
            _commit(unrelated, "unrelated history", allow_empty=True)
            with self.assertRaisesRegex(ProvenanceError, "not an ancestor"):
                check_provenance(unrelated)

            drifted = _clone(temporary / "receipt-drift")
            receipt = drifted / "provenance/p8-migration-receipt.json"
            receipt.write_bytes(receipt.read_bytes() + b"\n")
            with self.assertRaises(ProvenanceError):
                check_provenance(drifted)

    def test_missing_accepted_implementation_object_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-object-") as name:
            root = _clone(Path(name))
            (root / "docs/p8/operations.md").unlink()
            subprocess.run(["git", "add", "docs/p8/operations.md"], cwd=root, check=True)
            incomplete_commit = _commit(root, "remove accepted implementation object")
            with (
                patch(
                    "scripts.check_p8_provenance.ACCEPTED_P8_COMMIT",
                    incomplete_commit,
                ),
                self.assertRaises(ProvenanceError),
            ):
                check_provenance(root)

    def test_evidence_writer_refuses_dirty_or_incomplete_results(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-evidence-") as name:
            with self.assertRaisesRegex(EvidenceError, "clean implementation"):
                write_p8_evidence(
                    evidence_path=Path(name) / "summary.json",
                    root=ROOT,
                    results={},
                    unittest_outcome={},
                    studio_test_outcome={},
                    verified_gates=set(),
                    branch="codex/p8-release-readiness",
                    implementation_commit="2" * 40,
                    merge_base=BASE_COMMIT,
                    tree_digest="sha256:" + "3" * 64,
                    tree_clean=False,
                )
            self.assertFalse((Path(name) / "summary.json").exists())
