# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
import tomllib
import unittest
from pathlib import Path

from scripts.check_p1_scaffold import LICENSE_DIGEST, REQUIRED_FILES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
P1_FIXTURE = json.loads(
    (PROJECT_ROOT / "tests/p1/fixtures/p1-stage-boundary.json").read_text(encoding="utf-8")
)


class RepositoryScaffoldTests(unittest.TestCase):
    def test_required_repository_files_exist(self) -> None:
        missing = sorted(path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).is_file())
        self.assertEqual(missing, [])

    def test_official_apache_license_text_is_exact(self) -> None:
        digest = hashlib.sha256((PROJECT_ROOT / "LICENSE").read_bytes()).hexdigest()
        self.assertEqual(digest, LICENSE_DIGEST)

    def test_notice_review_is_scoped_to_p1_source_distribution(self) -> None:
        notice = (PROJECT_ROOT / "NOTICE").read_text(encoding="utf-8")
        review = (PROJECT_ROOT / "docs/licensing/notice-review.md").read_text(encoding="utf-8")
        self.assertIn("Digital Colleagues contributors", notice)
        self.assertIn("No reviewed direct package", review)
        self.assertIn("future container or release distributions require a fresh", review)

    def test_python_metadata_keeps_no_runtime_dependencies(self) -> None:
        metadata = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(metadata["project"]["requires-python"], ">=3.12")
        self.assertEqual(metadata["project"]["dependencies"], [])

    def test_p1_empty_package_boundary_is_historical_fixture_data(self) -> None:
        self.assertEqual(
            P1_FIXTURE["python_package_files"],
            ["src/digital_colleagues/__init__.py", "src/digital_colleagues/py.typed"],
        )

    def test_studio_is_private_locked_and_has_all_tooling_commands(self) -> None:
        package = json.loads((PROJECT_ROOT / "studio/package.json").read_text(encoding="utf-8"))
        lock = json.loads((PROJECT_ROOT / "studio/package-lock.json").read_text(encoding="utf-8"))
        self.assertTrue(package["private"])
        self.assertEqual(lock["lockfileVersion"], 3)
        self.assertEqual(lock["packages"][""]["version"], package["version"])
        self.assertTrue(
            {"build", "dev", "format:check", "lint", "test", "typecheck"}.issubset(
                package["scripts"]
            )
        )

    def test_studio_shell_states_that_runtime_remains_deferred(self) -> None:
        app = (PROJECT_ROOT / "studio/src/App.tsx").read_text(encoding="utf-8")
        self.assertIn("Runtime orchestration begins", app)
        self.assertIn("in P3", app)
        self.assertNotIn("fetch(", app)
        self.assertNotIn("WebSocket", app)

    def test_p1_studio_copy_is_preserved_as_historical_fixture_data(self) -> None:
        self.assertIn("P1 · Scaffold", P1_FIXTURE["studio_required_phrases"])
        self.assertIn("Runtime behavior begins after P1", P1_FIXTURE["studio_required_phrases"])

    def test_ci_contains_every_current_gate_and_read_only_permissions(self) -> None:
        workflow = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("contents: read", workflow)
        self.assertIn("ruff check src scripts tests", workflow)
        self.assertIn("mypy src scripts tests", workflow)
        self.assertIn("npm run typecheck", workflow)
        self.assertIn("npm run build", workflow)
        self.assertIn("scripts/check_public_boundary.py", workflow)
        self.assertIn("scripts/check_p2_architecture.py", workflow)
        self.assertIn("scripts/check_p2_core_contracts.py", workflow)
        self.assertIn("scripts/run_unittest_suite.py", workflow)

    def test_comment_capable_p1_files_have_spdx_headers(self) -> None:
        extensions = {".css", ".html", ".js", ".md", ".py", ".toml", ".ts", ".tsx", ".yml"}
        exact_names = {".editorconfig", ".gitignore", ".prettierignore", "Makefile"}
        for document in PROJECT_ROOT.rglob("*"):
            if not document.is_file() or ".git" in document.relative_to(PROJECT_ROOT).parts:
                continue
            if document.suffix in extensions or document.name in exact_names:
                first_line = document.read_text(encoding="utf-8").splitlines()[0]
                self.assertIn("SPDX-License-Identifier: Apache-2.0", first_line, document)

    def test_p1_stage_absence_assertions_are_not_current_tree_assertions(self) -> None:
        self.assertIn("src/digital_colleagues/core", P1_FIXTURE["absent_product_paths"])
        self.assertTrue((PROJECT_ROOT / "src/digital_colleagues/core").is_dir())

    def test_evidence_summary_claim_and_boundaries_are_narrow(self) -> None:
        summary = json.loads(
            (PROJECT_ROOT / "artifacts/p1/summary.json").read_text(encoding="utf-8")
        )
        self.assertEqual(summary["gate"], "p1_public_repository_scaffold")
        self.assertEqual(summary["claim_scope"], "Clean-room public repository scaffold only.")
        self.assertIn(summary["status"], {"passed", "review_required"})
        if summary["status"] == "review_required":
            return
        self.assertEqual(summary["schema_version"], 2)
        boundaries = summary["mechanically_verified_boundaries"]
        self.assertFalse(boundaries["git_initialized"])
        self.assertFalse(boundaries["root_git_administrative_entry_present"])
        self.assertEqual(boundaries["p2_product_paths_present"], 0)
        self.assertEqual(summary["results"]["unittest"]["skipped"], 0)
        self.assertTrue(summary["results"]["unittest"]["gate_passed"])
        self.assertEqual(
            summary["non_mechanical_claims"]["published"],
            "not_evaluated_by_automated_evidence",
        )
        self.assertIn("security effectiveness", summary["not_evidence_for"])
        self.assertIn("a runnable product Golden Path", summary["not_evidence_for"])


if __name__ == "__main__":
    unittest.main()
