# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import unittest
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from scripts.check_p12_provenance import (
    BLUEPRINT_SOURCE,
    HISTORY,
    P10_RUNS,
    P10_SETS,
    P10_SUBJECTS,
    REJECTED_ATTEMPTS,
    STAGE12_FAILURE_DIAGNOSTICS,
    check_provenance,
)
from scripts.check_p12_repository import P12GateError

ROOT = Path(__file__).resolve().parents[2]


class ProvenanceTests(unittest.TestCase):
    def test_complete_receipt_passes(self) -> None:
        result = check_provenance(ROOT)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["covered_path_count"], 40)
        self.assertEqual(result["protected_p10_local_git_identity_count"], 8)

    def test_historical_anchor_set_is_exact(self) -> None:
        self.assertEqual(len(HISTORY), 7)
        self.assertEqual(HISTORY["p11r_final"], "c1562ea5201394d8a278f4b644daf4029cbb5bd4")

    def test_p10_subjects_are_fixed(self) -> None:
        self.assertEqual(len(P10_SUBJECTS), 2)
        self.assertTrue(
            all(subject.startswith("ghcr.io/jeremyliu1220/") for subject in P10_SUBJECTS)
        )

    def test_active_and_superseded_sets_are_both_protected(self) -> None:
        self.assertEqual(set(P10_SETS), {"active", "superseded"})
        self.assertEqual(P10_SETS["active"]["lifecycle"], "passed")
        self.assertEqual(
            P10_SETS["superseded"]["lifecycle"], "superseded_contract_noncompliant_source"
        )

    def test_all_nine_p10_runs_are_fixed(self) -> None:
        self.assertEqual(len(P10_RUNS), 9)
        self.assertEqual(P10_RUNS["34237810474"][1], "success")

    def test_receipt_rejects_missing_covered_path(self) -> None:
        self._mutated_receipt(lambda value: value["allowlist"].pop())

    def test_receipt_rejects_source_read(self) -> None:
        self._mutated_receipt(
            lambda value: value.__setitem__("parent_research_working_tree_read", True)
        )

    def test_receipt_rejects_publication(self) -> None:
        self._mutated_receipt(lambda value: value["publication"].__setitem__("tags", True))

    def test_receipt_rejects_p10_lifecycle_drift(self) -> None:
        self._mutated_receipt(
            lambda value: value["p10_protected_publication"]["sets"]["superseded"].__setitem__(
                "lifecycle", "deleted"
            )
        )

    def test_receipt_rejects_local_absolute_path(self) -> None:
        local_path = str(Path("/", "Users", "example", "private"))
        self.assertEqual(local_path, "/" + "Users/example/private")
        self._mutated_receipt(lambda value: value.__setitem__("note", local_path))
        self._mutated_receipt(
            lambda value: value["evidence_preflight"].__setitem__("containing_commit", "f" * 40)
        )

    def test_rejected_attempt_chains_and_run_summaries_are_exact(self) -> None:
        self.assertEqual(set(REJECTED_ATTEMPTS), {"v1", "v2", "v3"})
        v2 = REJECTED_ATTEMPTS["v2"]
        self.assertEqual(v2["final_commit"], "8e08c3891dc8f761ada096c3f829ef31d3fbfd7c")
        self.assertEqual(len(v2["commit_chain"]), 8)
        self.assertEqual([run["run_id"] for run in v2["failed_runs"]], [34542709145, 34564478590])
        self.assertEqual([len(run["attempts"]) for run in v2["failed_runs"]], [1, 2])
        self.assertEqual(
            v2["safe_failure_boundary"],
            "accepted_p8_actual_compose_pre_start_restore",
        )
        self.assertEqual(REJECTED_ATTEMPTS["v3"]["classification"], "superseded_acceptance_only")
        d4 = STAGE12_FAILURE_DIAGNOSTICS["d4_ci_umask_inheritance"]
        self.assertEqual(d4["run_id"], 34758522278)
        self.assertEqual(d4["head_sha"], "ec4cbbc3df05557e33c1eca137731c548e23cdff")
        self.assertEqual(d4["current_job"]["job_database_id"], 103727050919)
        self.assertEqual(d4["portable_job"]["job_database_id"], 103727050828)
        self.assertFalse(d4["raw_logs_retained"])
        self.assertFalse(d4["stage12_passed"])
        self.assertFalse(d4["stage13_executed"])

        def remove_stage12_diagnostics(value: dict[str, Any]) -> None:
            del value["stage12_failure_diagnostics"]

        def remove_transport_conclusion(value: dict[str, Any]) -> None:
            del value["stage12_failure_diagnostics"]["d4_ci_umask_inheritance"][
                "transport_conclusion"
            ]

        def replace_diagnostic(
            path: tuple[str, ...], replacement: object
        ) -> Callable[[dict[str, Any]], None]:
            def mutate(value: dict[str, Any]) -> None:
                target: Any = value["stage12_failure_diagnostics"]["d4_ci_umask_inheritance"]
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = replacement

            return mutate

        mutations: tuple[tuple[str, Callable[[dict[str, Any]], None]], ...] = (
            (
                "missing_record",
                remove_stage12_diagnostics,
            ),
            (
                "missing_nested_key",
                remove_transport_conclusion,
            ),
            (
                "current_digest",
                replace_diagnostic(("current_job", "envelope_sha256"), "0" * 64),
            ),
            (
                "portable_digest",
                replace_diagnostic(("portable_job", "envelope_sha256"), "0" * 64),
            ),
            (
                "run_id",
                replace_diagnostic(("run_id",), 34758522279),
            ),
            (
                "current_job",
                replace_diagnostic(("current_job", "job_database_id"), 103727050920),
            ),
            (
                "portable_job",
                replace_diagnostic(("portable_job", "job_database_id"), 103727050829),
            ),
            (
                "raw_log_retention",
                replace_diagnostic(("raw_logs_retained",), True),
            ),
            (
                "success_classification",
                replace_diagnostic(("classification",), "material_success_result"),
            ),
            (
                "stage12_success",
                replace_diagnostic(("stage12_passed",), True),
            ),
            (
                "current_success",
                replace_diagnostic(("current_job", "result", "status"), "passed"),
            ),
            (
                "portable_success",
                replace_diagnostic(("portable_job", "result", "status"), "passed"),
            ),
        )
        for case, mutate in mutations:
            with self.subTest(stage12_diagnostic=case):
                self._mutated_receipt(mutate)

    def test_blueprint_source_identity_is_exact(self) -> None:
        self.assertEqual(BLUEPRINT_SOURCE["line_count"], 1183)
        self.assertEqual(BLUEPRINT_SOURCE["byte_count"], 223853)
        self.assertEqual(
            BLUEPRINT_SOURCE["sha256"],
            "7f58f95e7f33f65348162754017da828a9db6272d0d2cec22dd7b91ace0a8263",
        )
        self.assertFalse(BLUEPRINT_SOURCE["repository_evidence"])

    def _mutated_receipt(self, mutate: Callable[[dict[str, Any]], None]) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "provenance").mkdir()
            (root / "docs/p12").mkdir(parents=True)
            receipt = json.loads((ROOT / "provenance/p12-change-receipt.json").read_text())
            mutate(receipt)
            (root / "provenance/p12-change-receipt.json").write_text(
                json.dumps(receipt), encoding="utf-8"
            )
            (root / "docs/p12/acceptance.md").write_bytes(
                (ROOT / "docs/p12/acceptance.md").read_bytes()
            )
            with self.assertRaises(P12GateError):
                check_provenance(root)


if __name__ == "__main__":
    unittest.main()
