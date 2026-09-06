# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.check_p9_provenance import ProvenanceError, check_provenance
from scripts.check_p9_repository import (
    ACCEPTANCE_COMMIT,
    BASE_COMMIT,
    IMPLEMENTATION_PATHS,
    P9_ALLOWED_PATHS,
    RepositoryError,
    _parse_name_status,
    check_repository,
)
from tests.p9.fixtures import ROOT, clone_repository, commit_all


class P9RepositoryTests(unittest.TestCase):
    def test_exact_healthy_candidate_passes_repository_and_provenance(self) -> None:
        repository = check_repository(ROOT)
        provenance = check_provenance(ROOT)
        expected = (
            P9_ALLOWED_PATHS
            if repository["candidate_phase"] == "final_evidence"
            else IMPLEMENTATION_PATHS
        )
        self.assertEqual(repository["gate"], "p9_repository_clean")
        self.assertEqual(repository["base_commit"], BASE_COMMIT)
        self.assertEqual(repository["acceptance_commit"], ACCEPTANCE_COMMIT)
        self.assertEqual(repository["changed_path_count"], len(expected))
        self.assertEqual(repository["migration_count"], 7)
        self.assertFalse(repository["migration_008"])
        self.assertEqual(repository["product_runtime_implementation_change_count"], 0)
        self.assertEqual(repository["cleanup_residue_count"], 0)
        self.assertEqual(provenance["gate"], "p9_provenance_clean")
        self.assertEqual(provenance["source_migration_count"], 0)
        self.assertFalse(provenance["parent_working_tree_read"])

    def test_wrong_base_and_missing_p8_ancestor_fail_closed(self) -> None:
        with (
            patch("scripts.check_p9_repository.BASE_COMMIT", "e" * 40),
            self.assertRaisesRegex(RepositoryError, "base commit is unavailable"),
        ):
            check_repository(ROOT)
        with (
            patch("scripts.check_p9_repository.ACCEPTED_P8_COMMIT", "f" * 40),
            self.assertRaisesRegex(RepositoryError, "accepted P8 commit is unavailable"),
        ):
            check_repository(ROOT)

    def test_exact_root_is_required(self) -> None:
        with self.assertRaisesRegex(RepositoryError, "root is not exact"):
            check_repository(ROOT / "docs")

    def test_staged_unstaged_and_untracked_states_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-dirty-") as name:
            temporary = Path(name)
            for state in ("staged", "unstaged", "untracked"):
                with self.subTest(state=state):
                    root = clone_repository(temporary / state)
                    if state == "untracked":
                        (root / "p9-untracked.txt").write_text("dirty\n", encoding="utf-8")
                    else:
                        path = root / "README.md"
                        path.write_text(
                            path.read_text(encoding="utf-8") + "\ndirty\n", encoding="utf-8"
                        )
                        if state == "staged":
                            subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
                    with self.assertRaisesRegex(RepositoryError, "clean index and worktree"):
                        check_repository(root)

    def test_historical_acceptance_artifact_receipt_and_migration_drift_are_rejected(
        self,
    ) -> None:
        paths = (
            "docs/p8/acceptance.md",
            "artifacts/p8/summary.json",
            "provenance/p8-migration-receipt.json",
            "migrations/007_governance_hardening.sql",
        )
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-history-") as name:
            temporary = Path(name)
            for index, relative in enumerate(paths):
                with self.subTest(relative=relative):
                    root = clone_repository(temporary / str(index))
                    path = root / relative
                    path.write_bytes(path.read_bytes() + b"\nhistorical drift\n")
                    commit_all(root, f"drift {relative}")
                    with self.assertRaises(RepositoryError):
                        check_repository(root)

    def test_migration_008_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-migration-") as name:
            root = clone_repository(Path(name))
            (root / "migrations/008_forbidden.sql").write_text("SELECT 1;\n", encoding="utf-8")
            commit_all(root, "add forbidden migration")
            with self.assertRaises(RepositoryError):
                check_repository(root)

    def test_product_studio_compose_dependency_and_version_changes_are_rejected(self) -> None:
        paths = (
            "src/digital_colleagues/__init__.py",
            "studio/src/App.tsx",
            "compose.yaml",
            "Dockerfile",
            "requirements/p8.lock",
            "pyproject.toml",
            "studio/package.json",
        )
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-runtime-") as name:
            temporary = Path(name)
            for index, relative in enumerate(paths):
                with self.subTest(relative=relative):
                    root = clone_repository(temporary / str(index))
                    path = root / relative
                    path.write_bytes(path.read_bytes() + b"\np9 forbidden change\n")
                    commit_all(root, f"change {relative}")
                    with self.assertRaises(RepositoryError):
                        check_repository(root)

    def test_incomplete_and_extra_changed_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-paths-") as name:
            temporary = Path(name)
            incomplete = clone_repository(temporary / "incomplete")
            (incomplete / "docs/p9/rebaseline-checklist.md").unlink()
            commit_all(incomplete, "remove a P9 path")
            with self.assertRaisesRegex(RepositoryError, "partial or incomplete"):
                check_repository(incomplete)

            extra = clone_repository(temporary / "extra")
            (extra / "docs/p9/extra.md").write_text("extra\n", encoding="utf-8")
            commit_all(extra, "add extra P9 path")
            with self.assertRaisesRegex(RepositoryError, "outside the exact allowlist"):
                check_repository(extra)

    def test_rename_copy_path_traversal_symlink_and_special_file_bypasses_fail(self) -> None:
        with self.assertRaises(RepositoryError):
            _parse_name_status(b"M\0../escape\0")
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-bypass-") as name:
            temporary = Path(name)
            renamed = clone_repository(temporary / "rename")
            subprocess.run(
                ["git", "mv", "docs/p9/rebaseline-checklist.md", "docs/p9/renamed.md"],
                cwd=renamed,
                check=True,
            )
            commit_all(renamed, "rename P9 path")
            with self.assertRaises(RepositoryError):
                check_repository(renamed)

            copied = clone_repository(temporary / "copy")
            source = copied / "docs/p9/rebaseline-checklist.md"
            (copied / "docs/p9/copied.md").write_bytes(source.read_bytes())
            commit_all(copied, "copy P9 path")
            with self.assertRaises(RepositoryError):
                check_repository(copied)

            linked = clone_repository(temporary / "symlink")
            target = linked / "docs/p9/rebaseline-checklist.md"
            target.unlink()
            target.symlink_to("acceptance.md")
            commit_all(linked, "replace P9 file with symlink")
            with self.assertRaises(RepositoryError):
                check_repository(linked)

            special = clone_repository(temporary / "special")
            os.mkfifo(special / "p9-special")
            with self.assertRaises(RepositoryError):
                check_repository(special)

    def test_acceptance_contract_change_or_deletion_after_fixed_commit_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-acceptance-") as name:
            temporary = Path(name)
            for operation in ("change", "delete"):
                with self.subTest(operation=operation):
                    root = clone_repository(temporary / operation)
                    path = root / "docs/p9/acceptance.md"
                    if operation == "change":
                        path.write_bytes(path.read_bytes() + b"\nchanged\n")
                    else:
                        path.unlink()
                    with self.assertRaisesRegex(RepositoryError, "acceptance contract changed"):
                        check_repository(root)

    def test_provenance_rejects_receipt_drift_and_incomplete_coverage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-provenance-") as name:
            temporary = Path(name)
            drifted = clone_repository(temporary / "drifted")
            receipt = drifted / "provenance/p9-migration-receipt.json"
            receipt.write_bytes(receipt.read_bytes() + b"\n")
            with self.assertRaisesRegex(ProvenanceError, "receipt changed"):
                check_provenance(drifted)

            incomplete = clone_repository(temporary / "incomplete")
            receipt = incomplete / "provenance/p9-migration-receipt.json"
            text = receipt.read_text(encoding="utf-8")
            marker = '      "destination": "AGENTS.md",\n'
            receipt.write_text(
                text.replace(marker, marker.replace("AGENTS.md", "README.md")), encoding="utf-8"
            )
            commit_all(incomplete, "make receipt coverage incomplete")
            with self.assertRaises(ProvenanceError):
                check_provenance(incomplete)


if __name__ == "__main__":
    unittest.main()
