# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import copy
import json
import subprocess
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any

from scripts.check_p9_provenance import check_provenance
from scripts.check_p9_rebaseline import check_rebaseline
from scripts.check_p9_repository import (
    BASE_COMMIT,
    BRANCH,
    EXPECTED_FAULT_BOUNDARIES,
    REQUIRED_FINAL_EVIDENCE_TESTS,
    RepositoryError,
    check_repository,
)
from scripts.collect_p9_evidence import (
    REQUIRED_GATES,
    EvidenceError,
    public_tree_digest,
    write_p9_evidence,
)
from tests.p9.fixtures import clone_repository, commit_all


def _unittest_result() -> dict[str, object]:
    return {
        "tests_run": 2,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "expected_failures": 0,
        "unexpected_successes": 0,
        "gate_passed": True,
        "test_ids": ["test.one", "test.two"],
        "fault_boundaries": ["p9_fixture_boundary"],
    }


def _results() -> dict[str, dict[str, object]]:
    return {
        "repository": {
            "candidate_phase": "implementation",
            "acceptance_contract_immutable": True,
            "acceptance_commit_isolated": True,
            "historical_drift_count": 0,
            "migration_count": 7,
            "migration_008": False,
            "product_runtime_implementation_change_count": 0,
            "cleanup_residue_count": 0,
            "staged_change_path_count": 0,
            "unstaged_change_path_count": 0,
            "untracked_path_count": 0,
        },
        "provenance": {
            "gate": "p9_provenance_clean",
            "transformed_migration_count": 0,
            "source_migration_count": 0,
            "parent_working_tree_read": False,
        },
        "rebaseline": {
            "gate": "p9_rebaseline_clean",
            "p9_through_p15_order": "passed",
            "fixed_product_decisions": "passed",
            "product_runtime_implementation_change_count": 0,
            "openai_live": "not_evaluated",
            "microsoft_365_live": "not_evaluated",
            "human_evaluation": "not_evaluated",
        },
    }


def _write(path: Path, **overrides: object) -> dict[str, object]:
    arguments: dict[str, object] = {
        "evidence_path": path,
        "root": path.parent,
        "results": _results(),
        "unittest_outcome": _unittest_result(),
        "verified_gates": set(REQUIRED_GATES),
        "branch": BRANCH,
        "implementation_commit": "2" * 40,
        "merge_base": BASE_COMMIT,
        "tree_digest": "sha256:" + "3" * 64,
        "tree_clean": True,
        "implementation_committed": True,
    }
    arguments.update(overrides)
    return write_p9_evidence(**arguments)  # type: ignore[arg-type]


def _implementation_candidate(directory: Path) -> Path:
    root = clone_repository(directory)
    summary = root / "artifacts/p9/summary.json"
    if summary.exists():
        subprocess.run(["git", "switch", "--quiet", "--detach", "HEAD^"], cwd=root, check=True)
    return root


def _local_main_exists(root: Path) -> bool:
    completed = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", "refs/heads/main"],
        cwd=root,
        check=False,
    )
    if completed.returncode not in (0, 1):
        raise subprocess.CalledProcessError(completed.returncode, completed.args)
    return completed.returncode == 0


def _switch_fixture_to_main(root: Path) -> None:
    current_branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=root, text=True
    ).strip()
    if current_branch == "main":
        return
    subprocess.run(["git", "branch", "--force", "main", "HEAD"], cwd=root, check=True)
    subprocess.run(["git", "switch", "--quiet", "main"], cwd=root, check=True)


def _commit_final_summary(root: Path) -> str:
    repository = check_repository(root)
    self_contained_repository = dict(repository)
    self_contained_repository["branch"] = BRANCH
    implementation_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    evidence_path = root / "artifacts/p9/summary.json"
    test_ids = sorted(
        REQUIRED_FINAL_EVIDENCE_TESTS
        | {
            "tests.p9.test_evidence_gate.P9EvidenceTests."
            "test_valid_static_synthetic_summary_has_exact_claim_boundary"
        }
    )
    write_p9_evidence(
        evidence_path=evidence_path,
        root=root,
        results={
            "repository": self_contained_repository,
            "provenance": check_provenance(root),
            "rebaseline": check_rebaseline(root),
        },
        unittest_outcome={
            "tests_run": len(test_ids),
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "expected_failures": 0,
            "unexpected_successes": 0,
            "gate_passed": True,
            "test_ids": test_ids,
            "fault_boundaries": EXPECTED_FAULT_BOUNDARIES,
        },
        verified_gates=set(REQUIRED_GATES) | {"python_lock_install"},
        branch=BRANCH,
        implementation_commit=implementation_commit,
        merge_base=BASE_COMMIT,
        tree_digest=public_tree_digest(root, evidence_path),
        tree_clean=True,
        implementation_committed=True,
    )
    return commit_all(root, "record P9 test evidence")


def _healthy_final_candidate(directory: Path) -> Path:
    root = _implementation_candidate(directory)
    _commit_final_summary(root)
    return root


def _clone_candidate(source: Path, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "repository"
    subprocess.run(
        [
            "git",
            "-c",
            "advice.detachedHead=false",
            "clone",
            "--quiet",
            "--shared",
            str(source),
            str(destination),
        ],
        check=True,
    )
    return destination


def _amend_summary(root: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    path = root / "artifacts/p9/summary.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    mutate(value)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", "artifacts/p9/summary.json"], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Digital Colleagues Tests",
            "-c",
            "user.email=digital-colleagues-tests.invalid",
            "commit",
            "--quiet",
            "--amend",
            "--no-edit",
        ],
        cwd=root,
        check=True,
    )


def _replace_value(field: str, replacement: object) -> Callable[[dict[str, Any]], None]:
    def mutate(value: dict[str, Any]) -> None:
        value[field] = replacement

    return mutate


def _replace_nested_value(
    section: str, field: str, replacement: object
) -> Callable[[dict[str, Any]], None]:
    def mutate(value: dict[str, Any]) -> None:
        value[section][field] = replacement

    return mutate


class P9EvidenceTests(unittest.TestCase):
    def test_final_gate_accepts_healthy_evidence_and_implementation_without_summary(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-final-healthy-") as name:
            temporary = Path(name)
            for scenario in (
                "local_main_absent",
                "local_main_exists",
                "already_on_local_main",
            ):
                with self.subTest(scenario=scenario):
                    root = _implementation_candidate(temporary / scenario)
                    self.assertFalse((root / "artifacts/p9/summary.json").exists())
                    self.assertEqual(check_repository(root)["candidate_phase"], "implementation")
                    _commit_final_summary(root)
                    self.assertEqual(check_repository(root)["candidate_phase"], "final_evidence")
                    subprocess.run(
                        ["git", "switch", "--quiet", "--detach", "HEAD"],
                        cwd=root,
                        check=True,
                    )

                    if scenario == "local_main_absent":
                        if _local_main_exists(root):
                            subprocess.run(
                                ["git", "branch", "--delete", "--force", "main"],
                                cwd=root,
                                check=True,
                            )
                        self.assertFalse(_local_main_exists(root))
                    elif scenario == "local_main_exists":
                        subprocess.run(
                            ["git", "branch", "--force", "main", "HEAD^"],
                            cwd=root,
                            check=True,
                        )
                        self.assertTrue(_local_main_exists(root))
                    else:
                        subprocess.run(
                            ["git", "branch", "--force", "main", "HEAD"],
                            cwd=root,
                            check=True,
                        )
                        subprocess.run(
                            ["git", "switch", "--quiet", "main"],
                            cwd=root,
                            check=True,
                        )

                    final_commit = subprocess.check_output(
                        ["git", "rev-parse", "HEAD"], cwd=root, text=True
                    ).strip()
                    _switch_fixture_to_main(root)
                    self.assertEqual(
                        subprocess.check_output(
                            ["git", "rev-parse", "main"], cwd=root, text=True
                        ).strip(),
                        final_commit,
                    )
                    merged = check_repository(root)
                    self.assertEqual(merged["candidate_phase"], "final_evidence")
                    self.assertEqual(merged["branch"], "main")

    def test_final_gate_rejects_claim_status_and_live_promotion(self) -> None:
        cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
            ("claim", _replace_value("claim", "accepted")),
            ("status", _replace_value("status", "accepted")),
        ]
        for key in ("openai_live", "microsoft_365_live", "human_evaluation"):
            cases.append((key, _replace_nested_value("evidence_classes", key, "live_private")))
        for key, replacement in (
            ("documentation_and_governance", "live_private"),
            ("mechanical_regression", "static"),
        ):
            cases.append((key, _replace_nested_value("evidence_classes", key, replacement)))
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-final-claim-") as name:
            temporary = Path(name)
            template = _healthy_final_candidate(temporary / "template")
            for index, (label, mutate) in enumerate(cases):
                with self.subTest(label=label):
                    root = _clone_candidate(template, temporary / str(index))
                    _amend_summary(root, mutate)
                    with self.assertRaises(RepositoryError):
                        check_repository(root)

    def test_final_gate_rejects_wrong_commit_digest_and_identity_metadata(self) -> None:
        cases = (
            ("implementation_commit", BASE_COMMIT),
            ("tree_digest", "sha256:" + "0" * 64),
            ("fixed_base", "0" * 40),
            ("merge_base", "0" * 40),
            ("acceptance_commit", "0" * 40),
            ("development_branch", "main"),
            ("milestone", "P10"),
        )
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-final-identity-") as name:
            temporary = Path(name)
            template = _healthy_final_candidate(temporary / "template")
            for index, (field, replacement) in enumerate(cases):
                with self.subTest(field=field):
                    root = _clone_candidate(template, temporary / str(index))
                    _amend_summary(root, _replace_value(field, replacement))
                    with self.assertRaises(RepositoryError):
                        check_repository(root)

    def test_final_gate_rejects_unknown_fields_and_unsafe_material(self) -> None:
        cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
            ("extra", _replace_value("unknown", "field")),
            ("missing", lambda value: value.pop("claim_exclusions")),
            ("wrong_type", _replace_value("schema_version", True)),
            ("claim_exclusion", lambda value: value["claim_exclusions"].pop()),
            (
                "migration_inventory",
                _replace_nested_value("migrations", "immutable_versions", [1, 2, 3, 4, 5, 6]),
            ),
            (
                "migration_008",
                _replace_nested_value("migrations", "migration_008", "present"),
            ),
            (
                "local_path",
                lambda value: value["unittest"]["test_ids"].__setitem__(
                    0, "/" + "Users/example/private/result"
                ),
            ),
            (
                "credential",
                lambda value: value["unittest"]["test_ids"].__setitem__(
                    0, "sk" + "-examplecredential123456"
                ),
            ),
            (
                "private_marker",
                lambda value: value["unittest"]["test_ids"].__setitem__(
                    0, "PRIVATE_" + "LIVE_RECEIPT"
                ),
            ),
        ]
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-final-safe-") as name:
            temporary = Path(name)
            template = _healthy_final_candidate(temporary / "template")
            for index, (label, mutate) in enumerate(cases):
                with self.subTest(label=label):
                    root = _clone_candidate(template, temporary / str(index))
                    _amend_summary(root, mutate)
                    with self.assertRaises(RepositoryError):
                        check_repository(root)

    def test_final_gate_rejects_mixed_or_nonfinal_evidence_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-final-commit-") as name:
            temporary = Path(name)
            template = _healthy_final_candidate(temporary / "template")
            mixed = _clone_candidate(template, temporary / "mixed")
            readme = mixed / "README.md"
            readme.write_text(readme.read_text(encoding="utf-8") + "\nmixed\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=mixed, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Digital Colleagues Tests",
                    "-c",
                    "user.email=digital-colleagues-tests.invalid",
                    "commit",
                    "--quiet",
                    "--amend",
                    "--no-edit",
                ],
                cwd=mixed,
                check=True,
            )
            with self.assertRaises(RepositoryError):
                check_repository(mixed)

            nonfinal = _clone_candidate(template, temporary / "nonfinal")
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Digital Colleagues Tests",
                    "-c",
                    "user.email=digital-colleagues-tests.invalid",
                    "commit",
                    "--quiet",
                    "--allow-empty",
                    "-m",
                    "commit after P9 evidence",
                ],
                cwd=nonfinal,
                check=True,
            )
            with self.assertRaises(RepositoryError):
                check_repository(nonfinal)

    def test_final_gate_rejects_embedded_gate_and_unittest_mutation(self) -> None:
        cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
            (
                "repository",
                _replace_nested_value("repository", "historical_drift_count", 1),
            ),
            (
                "provenance",
                _replace_nested_value("provenance", "source_migration_count", 1),
            ),
            (
                "rebaseline",
                _replace_nested_value(
                    "rebaseline", "product_runtime_implementation_change_count", 1
                ),
            ),
        ]
        for field in (
            "failures",
            "errors",
            "skipped",
            "expected_failures",
            "unexpected_successes",
        ):
            cases.append((field, _replace_nested_value("unittest", field, 1)))
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-final-result-") as name:
            temporary = Path(name)
            template = _healthy_final_candidate(temporary / "template")
            for index, (label, mutate) in enumerate(cases):
                with self.subTest(label=label):
                    root = _clone_candidate(template, temporary / str(index))
                    _amend_summary(root, mutate)
                    with self.assertRaises(RepositoryError):
                        check_repository(root)

    def test_valid_static_synthetic_summary_has_exact_claim_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-evidence-") as name:
            path = Path(name) / "summary.json"
            summary = _write(path)
            self.assertTrue(path.is_file())
            self.assertEqual(summary["claim"], "p9_productization_rebaseline_candidate")
            self.assertEqual(
                summary["status"], "development_complete_awaiting_independent_acceptance"
            )
            evidence = summary["evidence_classes"]
            self.assertIsInstance(evidence, dict)
            assert isinstance(evidence, dict)
            self.assertEqual(evidence["documentation_and_governance"], "static")
            self.assertEqual(evidence["mechanical_regression"], "synthetic_offline")
            self.assertEqual(evidence["openai_live"], "not_evaluated")
            self.assertEqual(evidence["microsoft_365_live"], "not_evaluated")
            self.assertEqual(evidence["human_evaluation"], "not_evaluated")

    def test_evidence_writer_rejects_failure_skip_dirty_branch_and_uncommitted_input(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-refusal-") as name:
            temporary = Path(name)
            cases: list[tuple[str, dict[str, object]]] = [
                ("dirty", {"tree_clean": False}),
                ("branch", {"branch": "main"}),
                ("uncommitted", {"implementation_committed": False}),
                ("gate", {"verified_gates": set()}),
            ]
            skipped = _unittest_result()
            skipped["skipped"] = 1
            cases.append(("skip", {"unittest_outcome": skipped}))
            failed = _unittest_result()
            failed["failures"] = 1
            cases.append(("failure", {"unittest_outcome": failed}))
            for label, overrides in cases:
                with self.subTest(label=label):
                    path = temporary / f"{label}.json"
                    with self.assertRaises(EvidenceError):
                        _write(path, **overrides)
                    self.assertFalse(path.exists())

    def test_repository_gate_counts_and_live_statuses_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-result-") as name:
            temporary = Path(name)
            cases = (
                ("historical_drift_count", 1),
                ("migration_count", 8),
                ("migration_008", True),
                ("product_runtime_implementation_change_count", 1),
                ("cleanup_residue_count", 1),
                ("staged_change_path_count", 1),
            )
            for index, (key, value) in enumerate(cases):
                with self.subTest(key=key):
                    results = _results()
                    results["repository"][key] = value
                    with self.assertRaisesRegex(EvidenceError, "repository boundary"):
                        _write(temporary / f"repository-{index}.json", results=results)

            for index, key in enumerate(("openai_live", "microsoft_365_live", "human_evaluation")):
                with self.subTest(key=key):
                    results = _results()
                    results["rebaseline"][key] = "live_private"
                    with self.assertRaisesRegex(EvidenceError, "claim boundary"):
                        _write(temporary / f"live-{index}.json", results=results)

    def test_summary_rejects_local_path_credential_and_private_marker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-safe-") as name:
            temporary = Path(name)
            values = (
                str(temporary),
                "sk" + "-examplecredential123456",
                "/.codex/" + "attachments/x",
            )
            for index, value in enumerate(values):
                with self.subTest(value=value):
                    results = copy.deepcopy(_results())
                    results["rebaseline"]["unsafe_fixture"] = value
                    with self.assertRaises(EvidenceError):
                        _write(temporary / f"unsafe-{index}.json", results=results)

    def test_commit_and_digest_shapes_are_exact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-shape-") as name:
            temporary = Path(name)
            for label, overrides in (
                ("base", {"implementation_commit": BASE_COMMIT}),
                ("short", {"implementation_commit": "abc"}),
                ("digest", {"tree_digest": "sha256:bad"}),
                ("merge-base", {"merge_base": "f" * 40}),
            ):
                with self.subTest(label=label):
                    with self.assertRaises(EvidenceError):
                        _write(temporary / f"{label}.json", **overrides)


if __name__ == "__main__":
    unittest.main()
