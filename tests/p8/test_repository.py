# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.check_p4_compose_runtime import ComposeRuntimeError
from scripts.check_p8_compose_runtime import _operation_json
from scripts.check_p8_repository import RepositoryError, check_repository
from scripts.collect_p8_evidence import (
    EvidenceError,
    validate_studio_tests,
    write_p8_evidence,
)
from scripts.p8_release_support import ACCEPTANCE_COMMIT, BASE_COMMIT
from scripts.run_p8_toolchain import PRIOR_CURRENT_TREE
from tests.p8.fixtures import ROOT


def _clone(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "repository"
    subprocess.run(["git", "clone", "--quiet", "--shared", str(ROOT), str(destination)], check=True)
    return destination


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
        self.assertEqual(len(PRIOR_CURRENT_TREE), 38)
        self.assertEqual(
            set(PRIOR_CURRENT_TREE),
            {
                "p2_architecture",
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
        self.assertEqual(result["historical_drift_count"], 0)
        self.assertEqual(result["residue_count"], 0)
        self.assertFalse(result["migration_008"])

    def test_acceptance_historical_migration_and_residue_drift_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-repository-") as name:
            temporary = Path(name)
            for category in ("acceptance", "history", "migration", "residue"):
                root = _clone(temporary / category)
                if category == "acceptance":
                    path = root / "docs/p8/acceptance.md"
                    path.write_text(path.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
                elif category == "history":
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

    def test_wrong_ancestry_and_missing_required_file_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-ancestry-") as name:
            root = _clone(Path(name))
            subprocess.run(
                ["git", "checkout", "--quiet", "--detach", BASE_COMMIT], cwd=root, check=True
            )
            with self.assertRaisesRegex(RepositoryError, "acceptance commit"):
                check_repository(root)
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-required-") as name:
            root = _clone(Path(name))
            target = root / "docs/p8/operations.md"
            target.unlink()
            with self.assertRaisesRegex(RepositoryError, "required P8"):
                check_repository(root)

    def test_source_base_and_acceptance_objects_remain_available(self) -> None:
        for commit in (BASE_COMMIT, ACCEPTANCE_COMMIT):
            self.assertEqual(
                subprocess.run(
                    ["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT
                ).returncode,
                0,
            )
        self.assertIsNotNone(shutil.which("git"))

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
