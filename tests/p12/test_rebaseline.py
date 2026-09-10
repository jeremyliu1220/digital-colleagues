# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest
from pathlib import Path

from scripts.check_p12_rebaseline import (
    ADR_MARKERS,
    CORE_RECORDS,
    LIVING_DOCUMENTS,
    ROADMAP_TITLES,
    check_rebaseline,
    require_markers,
    validate_claim_boundary,
    validate_core_records,
    validate_roadmap_order,
)
from scripts.check_p12_repository import P12GateError

ROOT = Path(__file__).resolve().parents[2]


class RebaselineTests(unittest.TestCase):
    def _acceptance(self) -> str:
        return (ROOT / "docs/p12/acceptance.md").read_text(encoding="utf-8")

    def test_complete_living_rebaseline_passes(self) -> None:
        result = check_rebaseline(ROOT)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["public_pilot_claim"], "not_evaluated")

    def test_exact_living_document_inventory(self) -> None:
        self.assertEqual(len(LIVING_DOCUMENTS), 20)
        self.assertEqual(len(set(LIVING_DOCUMENTS)), 20)

    def test_exact_p12_through_p20_titles(self) -> None:
        self.assertEqual(len(ROADMAP_TITLES), 9)
        self.assertEqual(ROADMAP_TITLES[0], "Public Pilot Continuity Rebaseline")
        self.assertEqual(ROADMAP_TITLES[-1], "Always-on Public Pilot Release")

    def test_exact_core_record_contract_passes(self) -> None:
        validate_core_records(self._acceptance())
        self.assertEqual(len(CORE_RECORDS), 12)

    def test_project_scope_authority_expansion_fails_closed(self) -> None:
        mutated = self._acceptance().replace(
            "Exactly the deployment Namespace and project_id;",
            "Namespace, project_id, Mandate and grant;",
            1,
        )
        with self.assertRaises(P12GateError):
            validate_core_records(mutated)

    def test_project_running_state_fails_closed(self) -> None:
        mutated = self._acceptance().replace(
            "Exactly active, waiting, needs_human, completed, or stopped;",
            "Exactly active, running, waiting, needs_human, completed, or stopped;",
            1,
        )
        with self.assertRaises(P12GateError):
            validate_core_records(mutated)

    def test_waiting_kind_rename_fails_closed(self) -> None:
        mutated = self._acceptance().replace(
            "Exact kind human_decision, external_reply, timer_at, dependency, or effect_reconciliation;",
            "Exact kind approval, external_reply, timer_at, dependency, or effect_reconciliation;",
            1,
        )
        with self.assertRaises(P12GateError):
            validate_core_records(mutated)

    def test_goal_binding_owner_drift_fails_closed(self) -> None:
        mutated = self._acceptance().replace("| GoalBinding | P15 |", "| GoalBinding | P18 |", 1)
        with self.assertRaises(P12GateError):
            validate_core_records(mutated)

    def test_memory_admission_lifecycle_expansion_fails_closed(self) -> None:
        mutated = self._acceptance().replace(
            "Exactly admit or reject for one candidate,",
            "Exactly admit, reject, correct or delete for one candidate,",
            1,
        )
        with self.assertRaises(P12GateError):
            validate_core_records(mutated)

    def test_memory_record_silent_overwrite_fails_closed(self) -> None:
        mutated = self._acceptance().replace("no silent overwrite", "silent overwrite allowed", 1)
        with self.assertRaises(P12GateError):
            validate_core_records(mutated)

    def test_trigger_correlation_status_expansion_fails_closed(self) -> None:
        mutated = self._acceptance().replace(
            "Exact status received, matched, ambiguous, consumed, or ignored;",
            "Exact status received, running, matched, ambiguous, consumed, or ignored;",
            1,
        )
        with self.assertRaises(P12GateError):
            validate_core_records(mutated)

    def test_automatic_authorization_owner_drift_fails_closed(self) -> None:
        mutated = self._acceptance().replace(
            "| AutomaticEffectAuthorization | P18 |",
            "| AutomaticEffectAuthorization | P14 |",
            1,
        )
        with self.assertRaises(P12GateError):
            validate_core_records(mutated)

    def test_current_roadmap_order_passes(self) -> None:
        validate_roadmap_order((ROOT / "docs/roadmap.md").read_text(encoding="utf-8"))

    def test_swapped_roadmap_phase_fails_closed(self) -> None:
        text = (ROOT / "docs/roadmap.md").read_text(encoding="utf-8")
        mutated = text.replace("## P16 —", "## P99 —", 1)
        with self.assertRaises(P12GateError):
            validate_roadmap_order(mutated)

    def test_renamed_roadmap_owner_fails_closed(self) -> None:
        text = (ROOT / "docs/roadmap.md").read_text(encoding="utf-8")
        mutated = text.replace(
            "## P18 — Bounded Goal-driven Proactivity", "## P18 — Connector Writes", 1
        )
        with self.assertRaises(P12GateError):
            validate_roadmap_order(mutated)

    def test_adr_has_all_core_contract_markers(self) -> None:
        text = (ROOT / "docs/adr/0011-public-pilot-continuity-rebaseline.md").read_text(
            encoding="utf-8"
        )
        require_markers(text, ADR_MARKERS, label="test ADR")

    def test_missing_core_marker_fails_closed(self) -> None:
        with self.assertRaises(P12GateError):
            require_markers("only one marker", ("required marker",), label="test")

    def test_governance_only_claim_boundary_passes(self) -> None:
        validate_claim_boundary("governance-only; not_evaluated; zero publication; does not start")

    def test_runtime_overclaim_fails_closed(self) -> None:
        with self.assertRaises(P12GateError):
            validate_claim_boundary(
                "governance-only; not_evaluated; zero publication; does not start; "
                "P12 implements Semantic Memory"
            )

    def test_public_pilot_overclaim_fails_closed(self) -> None:
        with self.assertRaises(P12GateError):
            validate_claim_boundary(
                "governance-only; not_evaluated; zero publication; does not start; "
                "P12 is Public Pilot ready"
            )

    def test_all_four_future_gates_are_independent(self) -> None:
        result = check_rebaseline(ROOT)
        self.assertEqual(
            [
                result[name]
                for name in ("continuation_gate", "memory_gate", "trigger_gate", "proactivity_gate")
            ],
            ["independent"] * 4,
        )


if __name__ == "__main__":
    unittest.main()
