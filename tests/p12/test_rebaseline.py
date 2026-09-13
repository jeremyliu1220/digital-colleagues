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
    reject_history_contradictions,
    require_markers,
    validate_checklist_contract,
    validate_claim_boundary,
    validate_core_records,
    validate_governance_counts,
    validate_lifecycle_order,
    validate_p8_darwin_scope,
    validate_p20_l0,
    validate_platform_status,
    validate_roadmap_order,
    validate_v4_identity,
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
        checklist = (ROOT / "docs/p12/rebaseline-checklist.md").read_text(encoding="utf-8")
        validate_lifecycle_order(checklist)
        validate_checklist_contract(checklist)
        with self.assertRaises(P12GateError):
            validate_lifecycle_order(
                checklist.replace("10. Local formal gates.", "10. Combined.", 1)
            )
        with self.assertRaises(P12GateError):
            validate_lifecycle_order(
                checklist.replace(
                    "The following 21 stages are distinct, ordered, and separately authorized; no row may be\n"
                    "combined with another or treated as implied by completion of its predecessor:",
                    "The following 21 stages may be combined and are implicitly authorized by predecessors:",
                    1,
                )
            )
        with self.assertRaises(P12GateError):
            validate_lifecycle_order(
                checklist + "\nStage 9 completion grants authority for Stage 10.\n"
            )
        with self.assertRaises(P12GateError):
            validate_lifecycle_order(
                checklist + "\nStage 10 completion grants authority for Stage 11.\n"
            )
        for contradiction in (
            "After Stage 10 passes, Stage 11 is authorized.",
            "Completion of Stage 10 permits Stage 11.",
            "Passing Stage 10 permits Stage 11.",
            "After Stage 10 passes, proceed to Stage 11.",
            "Stage 11 follows automatically after Stage 10 passes.",
            "Completing Stage 10 makes Stage 11 eligible to begin.",
            "Stage 10 passes; Stage 11 may begin.",
            "Stage 11 starts automatically after Stage 10 passes.",
            "Passing Stage 10 triggers Stage 11.",
            "Stage 10 success unlocks Stage 11.",
            "Stage 10 completion is sufficient to begin Stage 11.",
            "Stage 11 requires no new authority after Stage 10.",
            "Stage 10 gives authority for Stage 11.",
            "Stage 11 may commence after Stage 10 passes.",
            "Stage 10 hands off to Stage 11.",
            "Stage 10 completion activates Stage 11.",
            "Stage 10 clears Stage 11 to begin.",
            "Stage 11 follows Stage 10 without further approval.",
            "Stage 10 rolls directly into Stage 11.",
            "Stage 10 approval encompasses Stage 11.",
            "Stage 10 approval extends to Stage 11.",
            "Stage 11 is covered by Stage 10 approval.",
            "Stage 10 approval includes Stage 11.",
            "One project-owner decision covers both Stage 10 and Stage 11.",
        ):
            with self.subTest(implicit_authority=contradiction), self.assertRaises(P12GateError):
                validate_lifecycle_order(checklist + "\n" + contradiction + "\n")
        validate_lifecycle_order(checklist + "\nStage 10 does not authorize Stage 11.\n")
        validate_lifecycle_order(
            checklist
            + "\nStage 11 may start only after separate project-owner authorization following "
            "Stage 10.\n"
        )
        for separate_authority_claim in (
            "Stage 10 approval does not encompass Stage 11.",
            "Stage 10 approval does not extend to Stage 11.",
            "Stage 11 is not covered by Stage 10 approval.",
            "Stage 10 approval does not include Stage 11.",
            "One owner decision does not cover both Stage 10 and Stage 11.",
            "Stage 10 planning includes Stage 11, which requires separate owner authorization.",
        ):
            validate_lifecycle_order(checklist + "\n" + separate_authority_claim + "\n")
        for before, after in (
            ("dbdb75b6afcd226059484ec536fec82532eb3613", "0" * 40),
            ("41 paths total", "40 paths total"),
            ("historical statuses (`not_proven`)", "historical statuses (`passed`)"),
            ("8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3", "0" * 40),
            ("8e08c3891dc8f761ada096c3f829ef31d3fbfd7c", "1" * 40),
            ("e31bc733cbdd333648f2ce1c52ac9fe1fad83179", "2" * 40),
            ("`autoMergeRequest` all null", "`autoMergeRequest` all non-null"),
        ):
            with self.subTest(checklist_drift=before), self.assertRaises(P12GateError):
                validate_checklist_contract(checklist.replace(before, after, 1))
        for contradiction in (
            "The implementation-head changed set has 40 paths total.",
            "The final summary is already present.",
            "There are 130 accepted gates.",
        ):
            with (
                self.subTest(checklist_contradiction=contradiction),
                self.assertRaises(P12GateError),
            ):
                validate_checklist_contract(checklist + "\n" + contradiction + "\n")
        validate_checklist_contract(checklist + "\nThere are not 130 accepted gates.\n")
        validate_checklist_contract(checklist + "\nThe final summary is not present.\n")

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
        for phase, migration, wrong_migration in (
            (13, "009", "010"),
            (14, "010", "011"),
            (15, "011", "012"),
            (16, "012", "013"),
            (17, "013", "014"),
            (18, "014", "015"),
        ):
            with (
                self.subTest(migration_owner=f"P{phase}"),
                self.assertRaises(P12GateError),
            ):
                validate_roadmap_order(
                    text.replace(
                        f"P{phase} uniquely owns additive migration {migration}",
                        f"P{phase} uniquely owns additive migration {wrong_migration}",
                        1,
                    )
                )
        for forbidden_owner in (
            "Migration: P19 uniquely owns additive migration 015.",
            "P20 owns migration 015.",
            "Migration 015 is owned by P19.",
        ):
            with (
                self.subTest(forbidden_migration_owner=forbidden_owner),
                self.assertRaises(P12GateError),
            ):
                validate_roadmap_order(text + "\n" + forbidden_owner + "\n")

    def test_adr_has_all_core_contract_markers(self) -> None:
        text = (ROOT / "docs/adr/0011-public-pilot-continuity-rebaseline.md").read_text(
            encoding="utf-8"
        )
        require_markers(text, ADR_MARKERS, label="test ADR")
        validate_governance_counts(text)
        validate_v4_identity(text)
        with self.assertRaises(P12GateError):
            validate_v4_identity(
                text.replace(
                    "dbdb75b6afcd226059484ec536fec82532eb3613",
                    "0" * 40,
                    1,
                )
            )
        for contradiction in (
            "P12 v4 branch is `codex/not-the-v4-branch`.",
            "P12 v4 base commit is `0000000000000000000000000000000000000000`.",
            "P12 v4 base tree is `0000000000000000000000000000000000000000`.",
            "P12 v4 acceptance tree is `0000000000000000000000000000000000000000`.",
            "P12 v4 acceptance blob is `0000000000000000000000000000000000000000`.",
            "P12 v4 accepted base is `0000000000000000000000000000000000000000`.",
            "P12 v4 sole parent is `0000000000000000000000000000000000000000`.",
            "P12 v1 branch is `codex/wrong-v1`.",
            "V1 head is `0000000000000000000000000000000000000000`.",
            "P12 v1 tree is `0000000000000000000000000000000000000000`.",
            "P12 v1 acceptance blob is `0000000000000000000000000000000000000000`.",
            "P12 v1 sole parent is `0000000000000000000000000000000000000000`.",
            "P12 v2 branch is `codex/wrong-v2`.",
            "V2 acceptance commit is `0000000000000000000000000000000000000000`.",
            "P12 v2 acceptance tree is `0000000000000000000000000000000000000000`.",
            "P12 v2 acceptance blob is `0000000000000000000000000000000000000000`.",
            "V2 final head is `0000000000000000000000000000000000000000`.",
            "P12 v2 final tree is `0000000000000000000000000000000000000000`.",
            "P12 v2 acceptance sole parent is `0000000000000000000000000000000000000000`.",
            "P12 v3 branch is `codex/wrong-v3`.",
            "V3 acceptance commit is `0000000000000000000000000000000000000000`.",
            "P12 v3 acceptance tree is `0000000000000000000000000000000000000000`.",
            "P12 v3 acceptance blob is `0000000000000000000000000000000000000000`.",
            "P12 v3 sole parent is `0000000000000000000000000000000000000000`.",
            "PR #14 was merged.",
            "PR #14 state is OPEN.",
            "PR #14 mergedAt is `2026-09-12T00:00:00Z`.",
            "PR #14 mergeCommit is `0000000000000000000000000000000000000000`.",
            "PR #14 autoMergeRequest is enabled.",
            "PR #14 base is `main` at `0000000000000000000000000000000000000000`.",
            "PR #14 head is `codex/wrong-v2` at `0000000000000000000000000000000000000000`.",
            "PR #14 remains CLOSED. Its mergeCommit is `0000000000000000000000000000000000000000`.",
            "Run 34564478590 completed successfully.",
            "P12 v4 acceptance commit has changed to `0000000000000000000000000000000000000000`.",
            "P12 v4 acceptance commit is no longer `dbdb75b6afcd226059484ec536fec82532eb3613`.",
            "P12 v4 acceptance commit differs from `dbdb75b6afcd226059484ec536fec82532eb3613`.",
            "Replace P12 v4 acceptance commit with `0000000000000000000000000000000000000000`.",
            "The correct P12 v4 branch is now `codex/wrong-v4`.",
            "P12 v2 final head has moved to `0000000000000000000000000000000000000000`.",
            "PR #14 was closed and later reopened.",
            "PR #14 is not CLOSED.",
            "Run 34564478590 no longer has failure conclusion.",
        ):
            with self.subTest(contradiction=contradiction), self.assertRaises(P12GateError):
                reject_history_contradictions(text + "\n" + contradiction)
        reject_history_contradictions(
            text + "\nP12 v2 commit `eb4dbc7e1cd1c1a1671f58441bb3e49d08e77a5e` has sole parent "
            "`3639fa08ca44820bb922e0644095c9fb9c24d3e6` and tree "
            "`42c05dea50cfe45b92a055c835e63045ec88a082`.\n"
        )
        for preserved_claim in (
            "P12 v4 acceptance commit has not changed from "
            "`dbdb75b6afcd226059484ec536fec82532eb3613`.",
            "P12 v4 acceptance commit does not differ from "
            "`dbdb75b6afcd226059484ec536fec82532eb3613`.",
            "Do not replace P12 v4 acceptance commit with "
            "`0000000000000000000000000000000000000000`.",
            "PR #14 was never reopened.",
            "Run 34564478590 still has failure conclusion.",
        ):
            reject_history_contradictions(text + "\n" + preserved_claim + "\n")
        for contradiction in (
            "There are 130 accepted gate identities.",
            "The portable inventory has 150 items.",
            "Portable replay reports 617 historical Python tests.",
            "Current governance has 137 P12 test IDs.",
            "There are six excluded acceptance gates.",
        ):
            with self.subTest(count_contradiction=contradiction), self.assertRaises(P12GateError):
                validate_governance_counts(text + "\n" + contradiction + "\n")
        validate_governance_counts(text + "\nThere are not 130 accepted gates.\n")
        for before, after in (
            ("34542709145", "34542709146"),
            ("34564478590", "34564478591"),
            ("`CLOSED` without merge", "`MERGED` with merge"),
            ("are all null", "are all non-null"),
            ("129 accepted gate identities", "130 accepted gate identities"),
            ("124 included and five", "123 included and six"),
            ("151-item portable inventory", "150-item portable inventory"),
            ("19 null and 110 non-null", "18 null and 111 non-null"),
            ("41 null entrypoints", "40 null entrypoints"),
            ("616 historical Python tests", "615 historical Python tests"),
            ("136 unique P12 test IDs", "135 unique P12 test IDs"),
        ):
            with self.subTest(drift=before):
                mutated = text.replace(before, after, 1)
                with self.assertRaises(P12GateError):
                    validate_governance_counts(mutated) if before[0].isdigit() and before not in {
                        "34542709145",
                        "34564478590",
                    } else validate_v4_identity(mutated)

    def test_missing_core_marker_fails_closed(self) -> None:
        with self.assertRaises(P12GateError):
            require_markers("only one marker", ("required marker",), label="test")

    def test_governance_only_claim_boundary_passes(self) -> None:
        validate_claim_boundary("governance-only; not_evaluated; zero publication; does not start")

    def test_runtime_overclaim_fails_closed(self) -> None:
        base = "governance-only; not_evaluated; zero publication; does not start; "
        for overclaim in (
            "P12 implements Semantic Memory",
            "P12 delivers Semantic Memory",
            "P12 adds ProjectContinuationState runtime support",
            "P12 adds runtime capability",
            "P12 implements OpenAI Gateway",
            "P12 implements the OpenAI Model Gateway",
            "P12 adds a working model gateway",
            "P12 creates a Microsoft 365 connector",
            "P12 implements Microsoft 365 access",
            "P12 provides M365 provider access",
            "P12 enables provider access",
            "P12 delivers API product behavior",
            "P12 supplies CLI product capability",
            "P12 implements Studio product behavior",
            "P12 creates a release path",
            "P12 enables a publication path",
            "P12 implements release",
            "P12 implements publication",
            "P12 ships a connector capability",
            "The OpenAI Model Gateway is implemented by P12",
            "P12 changes schema and migrations",
        ):
            with self.subTest(runtime_overclaim=overclaim), self.assertRaises(P12GateError):
                validate_claim_boundary(base + overclaim)
        for denial in (
            "P12 does not deliver Semantic Memory",
            "P12 adds no ProjectContinuationState runtime support",
            "P12 adds no runtime capability",
            "P12 does not implement the OpenAI Model Gateway",
            "P12 adds no Microsoft 365 connector or provider access",
            "P12 adds no API, CLI, or Studio product behavior",
            "P12 creates no release or publication path",
            "P12 defines a prospective Model Gateway contract for P13",
            "P12 defines a prospective OpenAI Gateway contract for P13",
            "P13 implements the OpenAI Model Gateway only after separate acceptance",
            "P14 may implement Microsoft 365 connectors only after separate authorization",
            "P12 changes no schema or migration",
        ):
            validate_claim_boundary(base + denial)

    def test_public_pilot_overclaim_fails_closed(self) -> None:
        base = "governance-only; not_evaluated; zero publication; does not start; "
        for overclaim in (
            "P12 is Public Pilot ready",
            "P12 is ready for the Public Pilot",
            "P12 makes the Public Pilot launch-ready",
            "P12 is production ready",
            "P12 begins P13",
            "P12 authorizes P13 implementation",
        ):
            with self.subTest(public_pilot_overclaim=overclaim), self.assertRaises(P12GateError):
                validate_claim_boundary(base + overclaim)
        for denial in (
            "P12 is not ready for the Public Pilot",
            "P12 does not make the Public Pilot launch-ready",
            "P12 is not production ready",
            "P12 does not begin P13",
            "P12 does not authorize P13 implementation",
        ):
            validate_claim_boundary(base + denial)

    def test_all_four_future_gates_are_independent(self) -> None:
        result = check_rebaseline(ROOT)
        self.assertEqual(
            [
                result[name]
                for name in ("continuation_gate", "memory_gate", "trigger_gate", "proactivity_gate")
            ],
            ["independent"] * 4,
        )

    def test_three_platform_status_dimensions_are_independent(self) -> None:
        text = (ROOT / "docs/adr/0011-public-pilot-continuity-rebaseline.md").read_text(
            encoding="utf-8"
        )
        validate_platform_status(text)
        with self.assertRaises(P12GateError):
            validate_platform_status(
                text + "\n`ubuntu_historical_execution_status` for p8_compose_runtime is passed.\n"
            )
        with self.assertRaises(P12GateError):
            validate_platform_status(
                text + "\np10_quickstart on Linux has passed historical execution.\n"
            )
        with self.assertRaises(P12GateError):
            validate_platform_status(
                text + "\n`ubuntu_historical_execution_status` is\n`passed`.\n"
            )
        for contradiction in (
            "linux_public_pilot_readiness = unblocked.",
            "ubuntu_historical_execution_status = skipped.",
            "Linux Public Pilot readiness has passed.",
            "Linux Public Pilot readiness is ready.",
            "The five Ubuntu historical statuses are passed.",
            "p8_compose_runtime historical status is passed.",
            "p10_quickstart passed historical replay.",
            "The Darwin anchor proves Linux Public Pilot readiness.",
            "Linux Public Pilot readiness has been achieved.",
            "Linux Public Pilot readiness is complete.",
            "Linux Public Pilot readiness is green.",
            "The five Ubuntu historical gates succeeded.",
            "p8_compose_runtime succeeded on Ubuntu.",
            "p10_quickstart works on Linux.",
            "The Darwin anchor demonstrates Linux compatibility.",
            "Darwin evidence validates Ubuntu execution.",
            "Ubuntu historical execution status is successful.",
            "P12 proves Linux runtime compatibility.",
            "P12 establishes Linux runtime support.",
            "P12 establishes native Linux support.",
            "Native Linux runtime support is proven.",
            "Darwin evidence is cross-platform.",
            "Darwin anchors can be treated as portable.",
            "Darwin evidence provides cross-platform proof.",
            "All excluded gates are portable.",
            "Every excluded gate passed.",
            "The five excluded acceptance gates work on Linux.",
        ):
            with (
                self.subTest(platform_contradiction=contradiction),
                self.assertRaises(P12GateError),
            ):
                validate_platform_status(text + "\n" + contradiction + "\n")
        for preserved_claim in (
            "p8_compose_runtime has not passed on Ubuntu.",
            "Linux Public Pilot readiness has not been achieved.",
            "The five Ubuntu historical gates did not succeed.",
            "p8_compose_runtime did not succeed on Ubuntu.",
            "p10_quickstart does not work on Linux.",
            "The Darwin anchor does not demonstrate Linux compatibility.",
            "Darwin evidence does not validate Ubuntu execution.",
            "P12 does not prove Linux runtime compatibility.",
            "Native Linux support is not proven.",
            "Darwin evidence is not cross-platform.",
            "Darwin anchors cannot be treated as portable.",
            "Darwin evidence does not provide cross-platform proof.",
            "No excluded gate passed.",
            "The five excluded gates are not portable.",
            "P20-L0 must prove native Linux runtime compatibility in the future.",
        ):
            validate_platform_status(text + "\n" + preserved_claim + "\n")
        result = check_rebaseline(ROOT)
        self.assertEqual(result["p12_governance_result"], "passed")
        self.assertEqual(
            result["ubuntu_historical_execution_status"],
            {
                "p8_compose_runtime": "not_proven",
                "p8_golden_path": "not_proven",
                "p10_compose_runtime": "not_proven",
                "p10_quickstart": "not_proven",
                "p10_remote_distribution": "not_proven",
            },
        )
        self.assertEqual(result["linux_public_pilot_readiness"], "blocked")

    def test_five_darwin_evidence_bindings_are_platform_scoped(self) -> None:
        text = (ROOT / "docs/adr/0011-public-pilot-continuity-rebaseline.md").read_text(
            encoding="utf-8"
        )
        validate_p8_darwin_scope(text)
        with self.assertRaises(P12GateError):
            validate_p8_darwin_scope(
                text.replace(
                    "311eb777c3d17a9a3722a16c394b9913c283b416",
                    "0" * 40,
                    1,
                )
            )
        for before, after in (
            ("anchor_platform = darwin", "anchor_platform = linux"),
            ("anchor_historical_status = passed", "anchor_historical_status = failed"),
            (
                "purpose = immutable_platform_scoped_identity_only",
                "purpose = portable_linux_proof",
            ),
            (
                "Each excluded result is `not_run_platform_excluded` with null exit status",
                "Each excluded result is `passed` with exit status 0",
            ),
            (
                "metadata `canonicalization` field remains the contract-required literal "
                "`P12-CJ-1`",
                "metadata `canonicalization` field uses `ad-hoc JSON`",
            ),
            (
                "exact Appendix C legacy anchor canonicalization",
                "general P12-CJ-1 canonicalization",
            ),
            ("`allow_nan=false`", "`allow_nan=true`"),
            (
                "distinct from the integer-only",
                "identical to the integer-only",
            ),
        ):
            with self.subTest(qualifier=before):
                with self.assertRaises(P12GateError):
                    validate_p8_darwin_scope(text.replace(before, after, 1))
        for contradiction in (
            "Every selected composite uses `P12-CJ-1`.",
            "The Appendix C anchor algorithm is identical to the general P12-CJ-1 encoder.",
            "Anchor composites use allow_nan=true.",
            "Embedded-anchor metadata canonicalization is Appendix C.",
        ):
            with (
                self.subTest(canonicalization_contradiction=contradiction),
                self.assertRaises(P12GateError),
            ):
                validate_p8_darwin_scope(text + "\n" + contradiction + "\n")
        with self.assertRaises(P12GateError):
            validate_p8_darwin_scope(text + "\np8_compose_runtime has anchor_platform = linux.\n")
        with self.assertRaises(P12GateError):
            validate_p8_darwin_scope(
                text.replace(
                    "1. `p8_compose_runtime`\n2. `p8_golden_path`",
                    "1. `p8_golden_path`\n2. `p8_compose_runtime`",
                    1,
                )
            )
        ubuntu_status = check_rebaseline(ROOT)["ubuntu_historical_execution_status"]
        assert isinstance(ubuntu_status, dict)
        self.assertEqual(
            set(ubuntu_status),
            {
                "p8_compose_runtime",
                "p8_golden_path",
                "p10_compose_runtime",
                "p10_quickstart",
                "p10_remote_distribution",
            },
        )

    def test_p20_l0_is_first_blocking_subgate(self) -> None:
        text = (ROOT / "docs/roadmap.md").read_text(encoding="utf-8")
        validate_p20_l0(text)
        for contradiction in (
            "P20-L0 is not the first blocking P20 sub-gate.",
            "P20-L1 is the first blocking P20 implementation sub-gate.",
            "Migration 015 is now authorized before P20-L0.",
            "P20-L0 follows the later P20 live gates.",
        ):
            with self.subTest(p20_l0_contradiction=contradiction), self.assertRaises(P12GateError):
                validate_p20_l0(text + "\n" + contradiction + "\n")
        validate_p20_l0(text + "\nP20-L0 never follows a later P20 live gate.\n")
        self.assertEqual(check_rebaseline(ROOT)["p20_first_blocking_subgate"], "P20-L0")

    def test_p20_l0_does_not_reorder_p13_through_p20(self) -> None:
        text = (ROOT / "docs/roadmap.md").read_text(encoding="utf-8")
        validate_roadmap_order(text)
        validate_p20_l0(text)
        p13 = text.index("## P13 —")
        p20 = text.index("## P20 —")
        p20_l0 = text.index("P20-L0", p20)
        self.assertLess(p13, p20)
        self.assertGreater(p20_l0, p20)


if __name__ == "__main__":
    unittest.main()
