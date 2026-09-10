# SPDX-License-Identifier: Apache-2.0

"""Validate the accepted B+ P12-P20 governance semantics in living records."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p12_repository import P12GateError  # noqa: E402

ROADMAP_TITLES = (
    "Public Pilot Continuity Rebaseline",
    "Migration Parser Correction and OpenAI Model Gateway",
    "Microsoft 365 Connector Foundation",
    "Durable Project Continuation",
    "Semantic Memory Lifecycle",
    "Trigger, Recurring Schedule, Heartbeat, Correlation, and Recovery",
    "Bounded Goal-driven Proactivity",
    "Built-in Public Pilot Project Tracker",
    "Always-on Public Pilot Release",
)

LIVING_DOCUMENTS = (
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/pull_request_template.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "README.md",
    "SECURITY.md",
    "docs/adr/0011-public-pilot-continuity-rebaseline.md",
    "docs/architecture/target-architecture.md",
    "docs/development.md",
    "docs/p12/rebaseline-checklist.md",
    "docs/product/capability-matrix.md",
    "docs/product/post-v0.1-capability-outlook.md",
    "docs/product/v0.2-external-dependency-register.md",
    "docs/product/v0.2-public-pilot-capability-matrix.md",
    "docs/product/v0.2-public-pilot-product-brief.md",
    "docs/roadmap.md",
    "docs/security/privacy-boundary.md",
    "docs/security/threat-model.md",
    "docs/security/v0.2-public-pilot-privacy-boundary.md",
    "docs/security/v0.2-public-pilot-threat-model.md",
)

ADR_MARKERS = (
    "1. P12 — Public Pilot Continuity Rebaseline.",
    "9. P20 — Always-on Public Pilot Release.",
    "`ProjectScope` contains exactly deployment Namespace and `project_id`",
    "`ProjectContinuationState` has exactly `active`, `waiting`, `needs_human`, `completed`, and",
    "`WaitingCondition.kind` is exactly `human_decision`, `external_reply`, `timer_at`,",
    "Status is exactly `open`, `satisfied`,",
    "HUMAN-accepted objective digest",
    "exact Mandate and Policy revisions",
    "`MemoryAdmissionDecision` has only `admit` and",
    "`MemoryRecord` versions are immutable and have exactly `active`, `superseded`, `revoked`,",
    "`TriggerCorrelation` status is exactly `received`, `matched`, `ambiguous`, `consumed`, or",
    "Outlook existing exact-thread reply",
    "Teams allowlisted existing-chat reply",
    "Planner\nlatest-ETag `If-Match` update",
    "SharePoint stays selected-resource read-only",
    "P18 alone adds `AutomaticEffectAuthorization`",
    "P19 only composes accepted",
    "`RecoveryScanCheckpoint` is only a bounded-scan optimization",
    "migration 009",
    "Migrations 001-008 and their manifest remain immutable",
)

ACCEPTANCE_MARKERS = (
    "ProjectContinuationState has exactly five values: active, waiting, needs_human, completed,",
    "WaitingCondition kind is exactly human_decision, external_reply,",
    "MemoryAdmissionDecision has exactly the values admit and reject.",
    "exactly one lifecycle status: active, superseded, revoked,",
    "Every TriggerCorrelation has exactly one status:",
    "RecoveryScanCheckpoint is not authoritative",
    "## P13 parser-first correction chain",
    "## Evidence-before-write read-only preflight",
    "## P10 complete protected publication identity",
)

CORE_RECORDS = {
    "ProjectScope": (
        "P15",
        "Exactly the deployment Namespace and project_id; a deployment-internal project identity dimension, never a new global namespace or authority container",
    ),
    "ProjectContinuationState": (
        "P15",
        "Exactly active, waiting, needs_human, completed, or stopped; completed and stopped are terminal; holds the exact active authority/source bindings and current checkpoint reference",
    ),
    "WaitingCondition": (
        "P15",
        "Exact kind human_decision, external_reply, timer_at, dependency, or effect_reconciliation; exact status open, satisfied, expired, cancelled, or ambiguous; explicit ANY/ALL grouping, deadline, exact predicates and one-time consumption",
    ),
    "GoalBinding": (
        "P15",
        "HUMAN-accepted objective digest, success criteria, bounds, expiry, exact Mandate and Policy revisions, namespace and causal identity; P15 may persist it but it cannot create proactive triggers before P18 acceptance",
    ),
    "ExternalPartyReference": (
        "P14",
        "Provider-scoped external identity reference and safe display projection; explicitly not a Principal and never HUMAN",
    ),
    "MemoryAdmissionDecision": (
        "P16",
        "Exactly admit or reject for one candidate, with authorized actor or exact accepted SERVICE rule and Policy revision; never a HumanApprovalDecision",
    ),
    "Post-admission lifecycle decision": (
        "P16",
        "Separate from admission; correction, supersession, revocation and deletion use distinct durable lifecycle decisions; MemoryLifecycleDecision is only a P12 non-normative working label and P16 fixes the exact name and schema",
    ),
    "MemoryRecord and version": (
        "P16",
        "Immutable versions with exact lifecycle status active, superseded, revoked, deleted, or expired; admission lineage, scope, classification, citations, content digest, retention and expiry; no silent overwrite",
    ),
    "MemoryRetrievalSet": (
        "P16",
        "Immutable bounded selection containing purpose, checkpoint ID/revision, as-of time, record ID/version, record/content digest, citation/source, inclusion order, exclusion reasons, and canonical retrieval-set ID/digest",
    ),
    "TriggerCorrelation": (
        "P17",
        "Exact status received, matched, ambiguous, consumed, or ignored; unique source occurrence, project/wait/checkpoint/wake mapping, dedupe, correlation and causation; only matched may enter one-time atomic consumption and ambiguous is quarantined",
    ),
    "RecoveryScanCheckpoint": (
        "P17",
        "Host and scanner identity, schema and policy revisions, bounded partition/page cursor, watermark and completion metadata; optimization only, never truth",
    ),
    "AutomaticEffectAuthorization": (
        "P18",
        "Exact low-risk effect revision and proofs under current Mandate, Policy, grant, goal, participant, resource, budget, and freshness boundaries",
    ),
}


def validate_roadmap_order(text: str) -> None:
    matches = re.findall(r"^## P(\d+) — (.+)$", text, re.MULTILINE)
    numbers = tuple(int(number) for number, _ in matches)
    if numbers != tuple(range(21)):
        raise P12GateError("Living roadmap phase headings are not exact P0-P20 order")
    titles = tuple(title for number, title in matches if int(number) >= 12)
    if titles != ROADMAP_TITLES:
        raise P12GateError("Living roadmap P12-P20 titles or ownership drifted")


def require_markers(text: str, markers: tuple[str, ...], *, label: str) -> None:
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise P12GateError(f"{label} omits required B+ semantics: {missing[0]}")


def validate_claim_boundary(text: str) -> None:
    required = (
        "governance-only",
        "not_evaluated",
        "zero publication",
        "does not start",
    )
    require_markers(text, required, label="P12 claim boundary")
    forbidden = (
        "P12 implements ProjectContinuationState",
        "P12 implements Semantic Memory",
        "P12 is Public Pilot ready",
        "P12 is production-ready",
    )
    if any(value in text for value in forbidden):
        raise P12GateError("P12 living records overclaim an unimplemented capability")


def core_record_rows(text: str) -> dict[str, tuple[str, str]]:
    try:
        section = text.split("### Core record set", 1)[1].split(
            "ProjectScope contains only deployment Namespace", 1
        )[0]
    except IndexError as exc:
        raise P12GateError("P12 core-record table is unavailable") from exc
    rows: dict[str, tuple[str, str]] = {}
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0] not in {"Record", "---"}:
            rows[cells[0]] = (cells[1], cells[2])
    return rows


def validate_core_records(text: str) -> None:
    rows = core_record_rows(text)
    for record, identity in CORE_RECORDS.items():
        if rows.get(record) != identity:
            raise P12GateError(f"P12 core-record contract drifted: {record}")


def check_rebaseline(root: Path) -> dict[str, object]:
    documents: dict[str, str] = {}
    for relative in LIVING_DOCUMENTS:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise P12GateError("A P12 living document is missing or is a symlink")
        documents[relative] = path.read_text(encoding="utf-8")
    acceptance = (root / "docs/p12/acceptance.md").read_text(encoding="utf-8")
    validate_roadmap_order(documents["docs/roadmap.md"])
    require_markers(
        documents["docs/adr/0011-public-pilot-continuity-rebaseline.md"],
        ADR_MARKERS,
        label="ADR 0011",
    )
    require_markers(acceptance, ACCEPTANCE_MARKERS, label="P12 acceptance")
    validate_core_records(acceptance)
    combined = "\n".join(documents.values())
    validate_claim_boundary(combined)
    responsibility = documents["docs/product/v0.2-public-pilot-capability-matrix.md"]
    require_markers(
        responsibility,
        (
            "P14",
            "P15",
            "P17",
            "P18",
            "P19",
            "exact HUMAN approval",
            "Composition-only",
        ),
        label="P14/P15/P17/P18/P19 responsibility matrix",
    )
    recovery = documents["docs/architecture/target-architecture.md"]
    require_markers(
        recovery,
        (
            "mandatory checkpoint",
            "new process with an empty chat",
            "not authority",
            "durable incomplete state",
        ),
        label="P12 continuation and recovery architecture",
    )
    parser = documents["docs/roadmap.md"]
    require_markers(
        parser,
        (
            "first implementation commit contains only the shared migration parser correction",
            "Gateway, dependency, API, and Studio behavior remain forbidden",
            "Migrations 001–008 remain immutable",
        ),
        label="P13 parser-first obligation",
    )
    unsafe = ("/Users/", ".codex/visualizations/", "Source attachment:")
    if any(marker in combined for marker in unsafe):
        raise P12GateError("P12 living records contain local or conversation-only identity")
    return {
        "schema_version": 1,
        "gate": "p12_rebaseline",
        "status": "passed",
        "roadmap_phase_count": 21,
        "p12_through_p20_count": len(ROADMAP_TITLES),
        "living_document_count": len(documents),
        "continuation_gate": "independent",
        "memory_gate": "independent",
        "trigger_gate": "independent",
        "proactivity_gate": "independent",
        "automatic_effect_authorization_owner": "P18",
        "public_pilot_claim": "not_evaluated",
        "publication_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        result = check_rebaseline(Path(args.root).resolve())
    except (OSError, UnicodeError, P12GateError) as exc:
        print(f"P12 rebaseline check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
