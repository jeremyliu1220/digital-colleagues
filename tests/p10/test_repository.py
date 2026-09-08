# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.check_p10_provenance import check_provenance
from scripts.check_p10_repository import check_repository
from scripts.p10_gate_support import (
    ACCEPTANCE_COMMIT,
    BASE_COMMIT,
    GateError,
    safe_relative,
)
from tests.p10.fixtures import ROOT, clone_repository, commit_all


class P10RepositoryTests(unittest.TestCase):
    def test_exact_candidate_has_fixed_base_acceptance_and_no_history_drift(self) -> None:
        result = check_repository(ROOT)
        self.assertEqual(result["gate"], "p10_repository_clean")
        self.assertEqual(result["base_commit"], BASE_COMMIT)
        self.assertEqual(result["acceptance_commit"], ACCEPTANCE_COMMIT)
        self.assertEqual(result["historical_drift_count"], 0)
        self.assertFalse(result["migration_008"])
        provenance = check_provenance(ROOT)
        self.assertEqual(provenance["source_migration_count"], 0)
        self.assertFalse(provenance["parent_research_working_tree_read"])

    def test_dirty_staged_unstaged_untracked_wrong_branch_and_base_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="dc-p10-repository-") as name:
            temporary = Path(name)
            for state in ("untracked", "staged", "unstaged"):
                root = clone_repository(temporary / state)
                if state == "untracked":
                    (root / "dirty").write_text("dirty\n", encoding="utf-8")
                else:
                    readme = root / "README.md"
                    readme.write_text(
                        readme.read_text(encoding="utf-8") + "\ndirty\n", encoding="utf-8"
                    )
                    if state == "staged":
                        subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
                with (
                    self.subTest(state=state),
                    self.assertRaisesRegex(GateError, "clean_index_worktree_required"),
                ):
                    check_repository(root)
        with patch("scripts.check_p10_repository.BRANCH", "wrong"):
            with self.assertRaisesRegex(GateError, "development_branch_invalid"):
                check_repository(ROOT)
        with patch("scripts.check_p10_repository.BASE_COMMIT", "f" * 40):
            with self.assertRaisesRegex(GateError, "base_commit_unavailable"):
                check_repository(ROOT)
        with patch("scripts.check_p10_repository._ancestor", return_value=False):
            with self.assertRaisesRegex(GateError, "trusted_ancestry_invalid"):
                check_repository(ROOT)

    def test_path_traversal_is_rejected(self) -> None:
        for value in ("../outside", "/absolute", "a/../b", ""):
            with self.subTest(value=value), self.assertRaises(GateError):
                safe_relative(value)

    def test_dependabot_base_drift_is_rejected_by_changed_path_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="dc-p10-dependabot-") as name:
            root = clone_repository(Path(name))
            config = root / ".github/dependabot.yml"
            config.write_text(
                config.read_text(encoding="utf-8").replace(
                    "open-pull-requests-limit: 5",
                    "open-pull-requests-limit: 0",
                    1,
                ),
                encoding="utf-8",
            )
            commit_all(root, "negative non-contract path drift")
            with self.assertRaisesRegex(
                GateError, "changed_path_set_invalid_missing_0_extra_1"
            ):
                check_repository(root)

    def test_acceptance_history_migration_allowlist_and_p11_drift_fail(self) -> None:
        cases = {
            "acceptance": ("docs/p10/acceptance.md", "\nchanged\n"),
            "history": ("docs/p9/acceptance.md", "\nhistorical drift\n"),
            "migration": ("migrations/008_forbidden.sql", "select 1;\n"),
            "extra": ("docs/p10/extra.md", "extra\n"),
            "p11": ("dc", "\n# OpenAI provider gateway\n"),
        }
        with tempfile.TemporaryDirectory(prefix="dc-p10-drift-") as name:
            temporary = Path(name)
            for label, (relative, content) in cases.items():
                root = clone_repository(temporary / label)
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    path.write_text(path.read_text(encoding="utf-8") + content, encoding="utf-8")
                else:
                    path.write_text(content, encoding="utf-8")
                commit_all(root, f"negative {label}")
                with self.subTest(label=label), self.assertRaises(GateError):
                    check_repository(root)

    def test_rename_copy_symlink_and_special_file_fail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="dc-p10-path-bypass-") as name:
            temporary = Path(name)
            renamed = clone_repository(temporary / "rename")
            subprocess.run(
                ["git", "mv", "docs/p10/operations.md", "docs/p10/renamed.md"],
                cwd=renamed,
                check=True,
            )
            commit_all(renamed, "rename")
            with self.assertRaises(GateError):
                check_repository(renamed)

            copied = clone_repository(temporary / "copy")
            (copied / "docs/p10/copied.md").write_bytes(
                (copied / "docs/p10/operations.md").read_bytes()
            )
            commit_all(copied, "copy")
            with self.assertRaises(GateError):
                check_repository(copied)

            linked = clone_repository(temporary / "symlink")
            target = linked / "docs/p10/operations.md"
            target.unlink()
            target.symlink_to("acceptance.md")
            commit_all(linked, "symlink")
            with self.assertRaises(GateError):
                check_repository(linked)

            special = clone_repository(temporary / "special")
            os.mkfifo(special / "special-fifo")
            with self.assertRaises(GateError):
                check_repository(special)

    def test_provenance_private_path_and_incomplete_coverage_fail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="dc-p10-provenance-") as name:
            temporary = Path(name)
            private = clone_repository(temporary / "private")
            receipt = private / "provenance/p10-migration-receipt.json"
            receipt.write_text(
                receipt.read_text(encoding="utf-8").replace(
                    "Multi-platform output uses an OCI index",
                    str(Path.home()),
                    1,
                ),
                encoding="utf-8",
            )
            commit_all(private, "private path")
            with self.assertRaises(GateError):
                check_provenance(private)
            incomplete = clone_repository(temporary / "incomplete")
            receipt = incomplete / "provenance/p10-migration-receipt.json"
            value = json.loads(receipt.read_text(encoding="utf-8"))
            value["new_implementations"].pop()
            receipt.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
            commit_all(incomplete, "incomplete coverage")
            with self.assertRaisesRegex(GateError, "coverage_invalid"):
                check_provenance(incomplete)


if __name__ == "__main__":
    unittest.main()
