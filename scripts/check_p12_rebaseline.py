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

FUTURE_MIGRATION_OWNERS = {
    13: "009",
    14: "010",
    15: "011",
    16: "012",
    17: "013",
    18: "014",
}

LIFECYCLE_STAGES = (
    "Blueprint owner review",
    "Repository-external v4 acceptance drafting",
    "Independent acceptance-draft pre-commit validation",
    "Content-bearing repository-external WIP snapshot",
    "Independent WIP snapshot verification",
    "v4 branch and acceptance-only commit in an independent temporary Git worktree",
    "Independent post-commit verification",
    "Per-file read-only WIP reuse review",
    "Governance implementation authorization and linear allowlisted commits",
    "Local formal gates",
    "Candidate push and PR authorization",
    "Exact implementation-head PR CI",
    "Evidence-preflight authorization",
    "Evidence-generation and summary-only commit authorization",
    "Final-candidate push / PR update authorization",
    "Exact final-candidate CI",
    "Independent acceptance",
    "Project-owner final acceptance",
    "Local fast-forward-only merge authorization",
    "Remote main push authorization",
    "Exact push-to-main CI envelope and remote closeout verification",
)

EXCLUDED_GATE_IDS = (
    "p8_compose_runtime",
    "p8_golden_path",
    "p10_compose_runtime",
    "p10_quickstart",
    "p10_remote_distribution",
)

V2_CHAIN = (
    (
        "3639fa08ca44820bb922e0644095c9fb9c24d3e6",
        "c1562ea5201394d8a278f4b644daf4029cbb5bd4",
        "71c411660e0f7ff26e8ad1451acaa0ea26fa384b",
        "acceptance-only v2 contract",
    ),
    (
        "eb4dbc7e1cd1c1a1671f58441bb3e49d08e77a5e",
        "3639fa08ca44820bb922e0644095c9fb9c24d3e6",
        "42c05dea50cfe45b92a055c835e63045ec88a082",
        "living-document alignment",
    ),
    (
        "5d0818ab9671dc023afd5ad23b6b0995e79ef68a",
        "eb4dbc7e1cd1c1a1671f58441bb3e49d08e77a5e",
        "99e0fd7a60df0584661d8e9162bf9dde1d0abf22",
        "governance gates and tests",
    ),
    (
        "b255d79df2b435ba754b7afe450d0a45559ea72a",
        "5d0818ab9671dc023afd5ad23b6b0995e79ef68a",
        "d4517e99bb155353704726d8a11e22e935dfe7dc",
        "provenance integration",
    ),
    (
        "fc145550b750c172899bc1497ff5fede387c07dc",
        "b255d79df2b435ba754b7afe450d0a45559ea72a",
        "0d4ec3cba2040d640e3adb8880c98a4525fa2207",
        "public-boundary fixture correction",
    ),
    (
        "098ba1399f7146258027674d5d312966fbdfe037",
        "fc145550b750c172899bc1497ff5fede387c07dc",
        "f0f65517dea5b3292c6f3f87c8c10b90295487e8",
        "replay diagnostic propagation correction",
    ),
    (
        "5722067571b70911c38b50ead23d198dcfbd4f20",
        "098ba1399f7146258027674d5d312966fbdfe037",
        "f66d1a7fada6db1a883c830f91ac6222983fa6c8",
        "installed-tool provisioning correction",
    ),
    (
        "8e08c3891dc8f761ada096c3f829ef31d3fbfd7c",
        "5722067571b70911c38b50ead23d198dcfbd4f20",
        "01ee7b08cc870a626698ac9a3fc46ec92bf0f4e0",
        "import-order correction and final rejected v2 head",
    ),
)

DARWIN_ANCHOR_ROWS = (
    (
        "p8_compose_runtime",
        "0bb80ab187932fbad42fbf665b8310987609a1f5",
        "311eb777c3d17a9a3722a16c394b9913c283b416",
        "artifacts/p8/summary.json / 964406b20e9fc1e98b8eeda3c24bf3f22f226768 / 78905893f9a06bf6b5361c76a8e152dbe8de2ec53d1aede84fca2f7ce1b5921b",
        'result = p8_summary["compose_runtime"]',
        "2348",
        "a2acd8e3f935d9c520f58e76b8384514e596e59f94f7bb62e1881ce9183c9bbd",
    ),
    (
        "p8_golden_path",
        "0bb80ab187932fbad42fbf665b8310987609a1f5",
        "311eb777c3d17a9a3722a16c394b9913c283b416",
        "artifacts/p8/summary.json / 964406b20e9fc1e98b8eeda3c24bf3f22f226768 / 78905893f9a06bf6b5361c76a8e152dbe8de2ec53d1aede84fca2f7ce1b5921b",
        'result = p8_summary["golden_path"]',
        "2034",
        "c1f1f8148cd3b0184d92720e862bbadfe7e330fd4087b7eb03190400d6742f44",
    ),
    (
        "p10_compose_runtime",
        "4bef5629d450c6bb3940f606fc90194e008ee8fd",
        "909b566b7ba9f7beb143cd0b29cf95fbd1178bbe",
        "artifacts/p10/summary.json / a4c1a59fffec9c30160787a7bec584e228fb9f35 / 876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae",
        'result = p10_summary["compose_runtime"]',
        "476",
        "4f6f5de0a92d2aa3bea1ab80ad94b869a4fd1cbe5f459804eea3cd86377e137b",
    ),
    (
        "p10_quickstart",
        "4bef5629d450c6bb3940f606fc90194e008ee8fd",
        "909b566b7ba9f7beb143cd0b29cf95fbd1178bbe",
        "artifacts/p10/summary.json / a4c1a59fffec9c30160787a7bec584e228fb9f35 / 876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae",
        'result = p10_summary["quickstart"]',
        "874",
        "75c18fadb57dd93914a8f99996857af22c2da8c82c504582b9eaa412c1f00c1b",
    ),
    (
        "p10_remote_distribution",
        "4bef5629d450c6bb3940f606fc90194e008ee8fd",
        "909b566b7ba9f7beb143cd0b29cf95fbd1178bbe",
        "artifacts/p10/summary.json / a4c1a59fffec9c30160787a7bec584e228fb9f35 / 876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae",
        'result = {"distribution": p10_summary["remote_distribution"], "quickstart": p10_summary["remote_quickstart"]}',
        "2538",
        "4383d540c4cd95f62db32aaadc1dfdf8e027eb0bd81b9909c4a0dda9a3d06c78",
    ),
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

UBUNTU_HISTORICAL_EXECUTION_STATUS = {gate_id: "not_proven" for gate_id in EXCLUDED_GATE_IDS}

PLATFORM_STATUS = {
    "p12_governance_result": "passed",
    "ubuntu_historical_execution_status": UBUNTU_HISTORICAL_EXECUTION_STATUS,
    "linux_public_pilot_readiness": "blocked",
}

DARWIN_ANCHOR_MARKERS = (
    "0bb80ab187932fbad42fbf665b8310987609a1f5",
    "964406b20e9fc1e98b8eeda3c24bf3f22f226768",
    "a2acd8e3f935d9c520f58e76b8384514e596e59f94f7bb62e1881ce9183c9bbd",
    "c1f1f8148cd3b0184d92720e862bbadfe7e330fd4087b7eb03190400d6742f44",
    "4bef5629d450c6bb3940f606fc90194e008ee8fd",
    "a4c1a59fffec9c30160787a7bec584e228fb9f35",
    "4f6f5de0a92d2aa3bea1ab80ad94b869a4fd1cbe5f459804eea3cd86377e137b",
    "75c18fadb57dd93914a8f99996857af22c2da8c82c504582b9eaa412c1f00c1b",
    "4383d540c4cd95f62db32aaadc1dfdf8e027eb0bd81b9909c4a0dda9a3d06c78",
    "`darwin`",
    "own immutable Darwin",
    "Each excluded result is `not_run_platform_excluded` with null exit status",
    "`anchor_platform = darwin`",
    "`anchor_historical_status = passed`",
    "`purpose = immutable_platform_scoped_identity_only`",
)

DARWIN_ANCHOR_CANONICALIZATION_MARKER = (
    "Each embedded-anchor metadata `canonicalization` field remains the contract-required "
    "literal `P12-CJ-1`. The five float-bearing selected composites use the exact Appendix C "
    'legacy anchor canonicalization: UTF-8, sorted keys, separators `(",", ":")`, '
    "`ensure_ascii=false`, `allow_nan=false`, and no terminal newline. That byte algorithm is "
    "distinct from the integer-only general P12-CJ-1 encoder. Bytes and Anchor SHA-256 bind "
    "those exact canonical bytes:"
)

GOVERNANCE_COUNT_MARKERS = (
    "The 129 accepted gate identities are independently derived as 124 included and five excluded.",
    "a literal 151-item portable inventory: 5 setup items, 124 included acceptance gates, "
    "17 evidence anchors, and 5 excluded acceptance gates.",
    "Gate entrypoints are exactly 19 null and 110 non-null, while the complete inventory has "
    "41 null entrypoints.",
    "Portable replay reports exactly 616 historical Python tests; the current governance "
    "inventory has exactly 136 unique P12 test IDs.",
)

CHECKLIST_CONTRACT_MARKERS = (
    "Base is `c1562ea5201394d8a278f4b644daf4029cbb5bd4` with tree `ae0f33263cfc7445fef69656ad9c5cb04d4a2d00`.",
    "Branch is exactly `codex/p12-public-pilot-continuity-rebaseline-v4` and acceptance commit is `dbdb75b6afcd226059484ec536fec82532eb3613`, with sole parent equal to the base, tree `f8d0dad5c04253eefd24353f8c9afd965cf0d6ea`, and acceptance blob `b574bb350a83a36f9ad7f521514c7d58e97393d9`.",
    "`docs/p12/acceptance.md` remains 3844 lines, 382481 bytes, and SHA-256 `f0159ea7d164a2b57c61d62e339798ea4ea568880934b571119c67ee781c2d45`.",
    "The rejected v1 ref remains `8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3` and the rejected v2 local/remote ref remains `8e08c3891dc8f761ada096c3f829ef31d3fbfd7c`. The superseded, not rejected, v3 acceptance-only ref remains `e31bc733cbdd333648f2ce1c52ac9fe1fad83179`. All three remain immutable non-ancestors of every v4 commit.",
    "PR #14 is CLOSED at the exact accepted-base/v2-head identity with `mergedAt`, `mergeCommit`, and `autoMergeRequest` all null; its branch and two failed run attempts remain protected under the retention-aware oracle.",
    "The implementation-head changed path set is exactly acceptance plus all 40 implementation paths: 41 paths total. The final summary path is absent.",
    "The accepted-gate universe is independently derived as exactly 129 identities: 124 included plus 5 excluded; it is not inferred from the inventory classification under test.",
    "The canonical historical inventory has exactly 151 ordered items: 5 setup, 124 included acceptance gates, 17 evidence anchors, and 5 excluded acceptance gates.",
    "Gate-level entrypoints are exactly 19 null and 110 non-null; all 151 inventory rows contain exactly 41 null entrypoints.",
    "Portable replay reports exactly 616 historical Python tests; current governance reports exactly 136 unique P12 test IDs.",
    "P12 governance result, the five Ubuntu historical statuses (`not_proven`), and Linux Public Pilot readiness (`blocked`) remain three independent status dimensions.",
    "`artifacts/p12/summary.json` is absent before evidence authorization.",
)


def validate_roadmap_order(text: str) -> None:
    matches = tuple(re.finditer(r"^## P(\d+) — (.+)$", text, re.MULTILINE))
    numbers = tuple(int(match.group(1)) for match in matches)
    if numbers != tuple(range(21)):
        raise P12GateError("Living roadmap phase headings are not exact P0-P20 order")
    titles = tuple(match.group(2) for match in matches if int(match.group(1)) >= 12)
    if titles != ROADMAP_TITLES:
        raise P12GateError("Living roadmap P12-P20 titles or ownership drifted")

    sections: dict[int, str] = {}
    for index, match in enumerate(matches):
        phase = int(match.group(1))
        if phase < 13:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[phase] = " ".join(text[match.end() : end].split())
    for phase, migration in FUTURE_MIGRATION_OWNERS.items():
        required = f"Migration: P{phase} uniquely owns additive migration {migration}"
        if required not in sections[phase]:
            raise P12GateError("Living roadmap future migration ownership drifted")
    if "P19 owns no connector write primitive and no migration" not in sections[19]:
        raise P12GateError("Living roadmap P19 migration boundary drifted")
    if "P20 owns no migration" not in sections[20]:
        raise P12GateError("Living roadmap P20 migration boundary drifted")
    if (
        "There is no migration 015 owner in this roadmap" not in sections[18]
        or "migration 015 is absent unless a future owner-approved acceptance contract assigns it"
        not in sections[20]
        or "Migration 015 remains unauthorized" not in sections[20]
    ):
        raise P12GateError("Living roadmap migration 015 boundary drifted")

    future_text = " ".join(sections.values())
    owner_claims = (
        r"\bp(?P<phase>1[3-9]|20)\b[^.;]{0,24}\b(?:uniquely\s+)?owns?\s+"
        r"(?:an?\s+)?(?:additive\s+)?migration\s+(?P<migration>0\d{2})\b",
        r"\bmigration\s+(?P<migration>0\d{2})\b[^.;]{0,32}"
        r"\b(?:is\s+)?owned\s+by\s+p(?P<phase>1[3-9]|20)\b",
    )
    for pattern in owner_claims:
        for owner_match in re.finditer(pattern, future_text, re.IGNORECASE):
            phase = int(owner_match.group("phase"))
            migration = owner_match.group("migration")
            if FUTURE_MIGRATION_OWNERS.get(phase) != migration:
                raise P12GateError("Living roadmap assigns a migration to the wrong future owner")


def validate_lifecycle_order(text: str) -> None:
    try:
        section = text.split("## Canonical authorization lifecycle", 1)[1].split(
            "## Implementation-head commands", 1
        )[0]
    except IndexError as exc:
        raise P12GateError("P12 canonical lifecycle section is unavailable") from exc
    matches = tuple(re.finditer(r"^(\d+)\. (.+)\.$", section, re.MULTILINE))
    entries = tuple(match.group(2) for match in matches)
    numbers = tuple(int(match.group(1)) for match in matches)
    if numbers != tuple(range(1, 22)) or entries != LIFECYCLE_STAGES:
        raise P12GateError("P12 canonical 21-stage lifecycle identity or order drifted")
    normalized = " ".join(section.split())
    whole_normalized = " ".join(text.split())
    if (
        "The following 21 stages are distinct, ordered, and separately authorized; no row may be "
        "combined with another or treated as implied by completion of its predecessor:"
        not in normalized
    ):
        raise P12GateError("P12 lifecycle separate-authority rule drifted")
    # A lifecycle claim may put the predecessor or successor first.  Inspect complete
    # clauses so that variants such as "Stage 11 is authorized after Stage 10 passes"
    # cannot evade the canonical separate-authority boundary.  Bare ordering statements
    # and explicit denials remain valid.
    authority_cues = (
        r"\b(?:authoriz\w*|grant\w*|permit\w*|allow\w*|enable\w*|entitl\w*)\b",
        r"\b(?:proceed|advance|continue|enter)\s+to\b",
        r"\b(?:may|can)\s+begin\b",
        r"\b(?:make|makes|made)\b[^.;]{0,40}\beligible\b",
        r"\b(?:follows?\s+automatically|automatically\s+follows?)\b",
        r"\b(?:without\s+(?:a\s+)?(?:separate|further)\s+authorization|"
        r"no\s+(?:separate|further)\s+authorization\s+(?:is\s+)?required)\b",
    )
    next_stage_cues = (
        r"\b(?:may|can)\s+(?:begin|start|commence|proceed|advance|continue|enter)\b",
        r"\b(?:starts?|begins?|commences?|follows?|proceeds?|advances?)\s+automatically\b",
        r"\bautomatically\s+(?:starts?|begins?|commences?|follows?|proceeds?|advances?)\b",
        r"\b(?:triggers?|unlocks?|activates?|clears?|greenlights?|opens?)\b",
        r"\bhands?\s+off\s+to\b",
        r"\b(?:completion|success|approval)\b[^.;]{0,40}\b(?:sufficient|enough)\b"
        r"[^.;]{0,24}\b(?:begin|start|commence|enter)\b",
        r"\bis\s+(?:sufficient|enough)\s+to\s+(?:begin|start|commence|enter)\b",
        r"\brequires?\s+no\s+(?:new|separate|further)\s+"
        r"(?:authority|authorization|approval)\b",
        r"\b(?:gives?|conveys?|provides?)\s+(?:automatic\s+)?"
        r"(?:authority|authorization|approval)\b",
        r"\bapproval\s+covers?\b",
        r"\b(?:encompasses?|includes?)\b",
        r"\bextends?\s+(?:to|through|into)\b",
        r"\b(?:is|are|was|were)\s+covered\s+by\b",
        r"\bcovers?\s+both\b",
        r"\b(?:follows?|proceeds?|advances?)\b[^.;]{0,48}\bwithout\s+"
        r"(?:new|separate|further)\s+(?:authority|authorization|approval)\b",
        r"\brolls?\s+directly\s+into\b",
    )
    denial = re.compile(
        r"\b(?:never|cannot|can't|does\s+not|doesn't|must\s+not|is\s+not|are\s+not)\s+"
        r"(?:automatically\s+)?(?:authoriz\w*|grant\w*|permit\w*|allow\w*|enable\w*|"
        r"entitl\w*|make\w*[^.;]{0,24}eligible|follow\w*\s+automatically)\b|"
        r"\b(?:authoriz\w*|grant\w*|permit\w*|allow\w*|enable\w*|entitl\w*)\s+"
        r"(?:absolutely\s+)?(?:no|neither)\b",
        re.IGNORECASE,
    )
    transition_denial = re.compile(
        r"\b(?:never|cannot|can't|does\s+not|doesn't|must\s+not|may\s+not|can\s+not|"
        r"is\s+not|are\s+not)\s+(?:automatically\s+)?"
        r"(?:begin|start|commence|follow|proceed|advance|trigger|unlock|activate|clear|"
        r"greenlight|open|hand\s+off|roll|give|convey|provide|cover|encompass|include|"
        r"extend)\w*\b|"
        r"\b(?:is|was)\s+not\s+(?:sufficient|enough)\b|"
        r"\b(?:trigger|unlock|activate|clear|greenlight|open|give|convey|provide|cover|"
        r"encompass|include|extend)\w*"
        r"\s+(?:absolutely\s+)?(?:no|neither)\b",
        re.IGNORECASE,
    )
    separate_authority_required = re.compile(
        r"\b(?:requires?|needs?)\s+(?:a\s+)?(?:new|separate|independent|explicit)"
        r"(?:\s+(?:new|separate|independent|explicit|project-owner|owner|stage-specific)){0,2}"
        r"\s+"
        r"(?:authority|authorization|approval)\b|"
        r"\bonly\s+after\s+(?:a\s+)?(?:new|separate|independent|explicit)"
        r"(?:\s+(?:new|separate|independent|explicit|project-owner|owner|stage-specific)){0,2}"
        r"\s+"
        r"(?:authority|authorization|approval)\b|"
        r"\b(?:new|separate|independent|explicit)"
        r"(?:\s+(?:new|separate|independent|explicit|project-owner|owner|stage-specific)){0,2}"
        r"\s+"
        r"(?:authority|authorization|approval)\s+"
        r"(?:is\s+)?(?:still\s+)?required\b",
        re.IGNORECASE,
    )
    for clause in re.split(r"\.\s+", whole_normalized):
        stage_numbers = {int(value) for value in re.findall(r"\bstage\s+(\d+)\b", clause, re.I)}
        if len(stage_numbers) < 2:
            continue
        next_stage_pair = any(number + 1 in stage_numbers for number in stage_numbers)
        positive = any(re.search(pattern, clause, re.IGNORECASE) for pattern in authority_cues)
        positive = positive or (
            next_stage_pair
            and any(re.search(pattern, clause, re.IGNORECASE) for pattern in next_stage_cues)
        )
        denied = denial.search(clause) or transition_denial.search(clause)
        if positive and denied is None and separate_authority_required.search(clause) is None:
            raise P12GateError("P12 lifecycle grants unauthorized cross-stage authority")


def require_markers(text: str, markers: tuple[str, ...], *, label: str) -> None:
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise P12GateError(f"{label} omits required B+ semantics: {missing[0]}")


def _claim_is_negated(text: str, start: int) -> bool:
    prefix = text[max(0, start - 32) : start]
    return re.search(r"\b(?:not|never|no)\b[^.;]{0,24}$", prefix, re.IGNORECASE) is not None


def reject_governance_count_contradictions(text: str) -> None:
    normalized = " ".join(text.split()).lower()
    number_words = {
        "zero": 0,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }
    claims = (
        (r"\b(?P<count>\d+)\s+accepted(?:-|\s+)gate(?:\s+identities|s)?\b", 129),
        (
            r"\baccepted(?:-|\s+)gate(?:\s+universe)?[^.;]{0,40}\b"
            r"(?P<count>\d+)\s+(?:identities|gates)\b",
            129,
        ),
        (r"\b(?P<count>\d+)-item\s+portable\s+inventory\b", 151),
        (
            r"\bportable\s+inventory[^.;]{0,48}\b(?P<count>\d+)"
            r"(?:-item|\s+items?)\b",
            151,
        ),
        (
            r"\bportable\s+replay[^.;]{0,48}\b(?P<count>\d+)\s+"
            r"historical\s+python\s+tests\b",
            616,
        ),
        (
            r"\bcurrent\s+governance(?:\s+inventory)?[^.;]{0,48}\b(?P<count>\d+)"
            r"(?:\s+unique)?\s+p12\s+test\s+ids\b",
            136,
        ),
        (
            r"\b(?P<count>\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten)"
            r"\s+excluded(?:\s+acceptance)?\s+gates\b",
            5,
        ),
    )
    for pattern, expected in claims:
        for match in re.finditer(pattern, normalized):
            if _claim_is_negated(normalized, match.start("count")):
                continue
            raw = match.group("count")
            value = int(raw) if raw.isdigit() else number_words[raw]
            if value != expected:
                raise P12GateError("P12 governance count claim drifted")


def validate_governance_counts(text: str) -> None:
    normalized = " ".join(text.split())
    require_markers(
        normalized,
        GOVERNANCE_COUNT_MARKERS,
        label="P12 accepted-gate, inventory, entrypoint, and test counts",
    )
    reject_governance_count_contradictions(text)


def validate_checklist_contract(text: str) -> None:
    normalized = " ".join(text.split())
    require_markers(normalized, CHECKLIST_CONTRACT_MARKERS, label="P12 rebaseline checklist")
    reject_governance_count_contradictions(text)
    for match in re.finditer(
        r"\bimplementation-head\s+changed(?:\s+path)?\s+set[^.;]{0,64}\b"
        r"(\d+)\s+paths?\s+total\b",
        normalized,
        re.IGNORECASE,
    ):
        if not _claim_is_negated(normalized, match.start(1)) and int(match.group(1)) != 41:
            raise P12GateError("P12 implementation-head path count drifted")
    if re.search(
        r"\b(?:final\s+)?summary(?:\s+path)?\s+(?:is|was|becomes?)\s+"
        r"(?:already\s+)?present\b",
        normalized,
        re.IGNORECASE,
    ):
        raise P12GateError("P12 checklist claims the final summary is present early")


def reject_platform_contradictions(text: str) -> None:
    normalized = " ".join(text.split()).lower()
    outcome = (
        r"passed|succeeds?|succeeded|successful|works?|worked|achieved|complete|completed|"
        r"green|ready|unblocked|proven"
    )
    claim_outcome = (
        rf"{outcome}|passing|portable|cross[-\s]+platform|platform[-\s]+agnostic|supported|"
        r"establish(?:es|ed)?|demonstrat(?:es|ed)?|validat(?:es|ed)?|verif(?:y|ies|ied)|"
        r"certif(?:y|ies|ied)|qualif(?:y|ies|ied)|provides?|delivers?|adds?"
    )
    for sentence in re.split(r"[.;]\s+", normalized):
        positive_sentence = re.sub(
            rf"\b(?:(?:does|do|did|is|are|was|were|has|have|can|could)\s+not|"
            rf"cannot|can't|not|never)\s+(?:been\s+)?(?:{claim_outcome})\b",
            "",
            sentence,
            flags=re.IGNORECASE,
        )
        passed = re.search(r"\bpassed\b", positive_sentence) is not None
        ubuntu_conflict = (
            passed
            and "ubuntu_historical_execution_status" in sentence
            and "not_proven" not in sentence
        )
        linux_conflict = (
            passed and "linux_public_pilot_readiness" in sentence and "blocked" not in sentence
        )
        gate_pass_claim = any(
            re.search(
                rf"(?:\b{gate_id}\b[^.;]{{0,96}}\b(?:{outcome})\b|"
                rf"\b(?:{outcome})\b[^.;]{{0,96}}\b{gate_id}\b)",
                positive_sentence,
            )
            for gate_id in EXCLUDED_GATE_IDS
        )
        gate_conflict = gate_pass_claim and (
            ("ubuntu" in sentence and "not_proven" not in sentence)
            or ("linux" in sentence and "blocked" not in sentence)
            or not re.search(r"\bdarwin\b", sentence)
        )
        cross_platform_proof = re.search(
            r"\bdarwin\b[^.;]{0,96}\b(?:proves?|establishes?|qualifies?|demonstrates?|"
            r"validates?)\b[^.;]{0,64}\b(?:ubuntu|linux)\b|"
            r"\b(?:ubuntu|linux)\b[^.;]{0,96}\b(?:proven|established|qualified|demonstrated|"
            r"validated)\b[^.;]{0,64}\b(?:by|from)\s+darwin\b",
            positive_sentence,
        )
        denied_cross_platform_proof = re.search(
            r"\b(?:not|never|neither|nor|cannot|does\s+not)\b[^.;]{0,48}"
            r"\b(?:proves?|proven|establishes?|established|qualifies?|qualified|demonstrates?|"
            r"demonstrated|validates?|validated)\b",
            sentence,
        )
        natural_status_conflict = any(
            re.search(
                rf"\b{label}\b[^,.;]{{0,48}}(?:"
                rf"\b(?:is|are|was|were|has|have|becomes?|became)\s+(?:been\s+)?"
                rf"`?(?:{outcome}|skipped|waived|equivalent|accepted_by_analogy)\b|"
                r"\b(?:succeeded|worked)\b)",
                positive_sentence,
            )
            for label in (
                r"ubuntu\s+historical(?:\s+execution)?\s+"
                r"(?:statuses?|gates?|executions?|results?|evaluations?)",
                r"linux\s+public\s+pilot\s+readiness",
            )
        )
        direct_linux_proof = re.search(
            r"\bp12(?:\s+v4)?\b\s+(?:now\s+|already\s+|currently\s+)?"
            r"(?:proves?|establishes?|demonstrates?|validates?|verifies?|certifies?|"
            r"provides?|delivers?|adds?)\s+(?:an?\s+|the\s+)?"
            r"(?:native\s+)?linux(?:\s+runtime)?\s+"
            r"(?:compatibility|support|portability)\b|"
            r"\b(?:native\s+)?linux(?:\s+runtime)?\s+"
            r"(?:compatibility|support|portability)\b[^.;]{0,32}"
            r"\b(?:is|was|has\s+been|becomes?|became)\s+(?:now\s+)?"
            r"(?:proven|established|demonstrated|validated|verified|certified)\b",
            positive_sentence,
        )
        darwin_portability = re.search(
            r"\bdarwin(?:[-\s]+scoped)?\s+(?:evidence|anchors?|results?|proof)\b"
            r"[^.;]{0,40}\b(?:is|are|was|were|becomes?|became|remains?|"
            r"qualif(?:y|ies|ied)\s+as|serves?\s+as)\s+(?:now\s+)?"
            r"(?:cross[-\s]+platform|portable|platform[-\s]+agnostic)\b|"
            r"\bdarwin(?:[-\s]+scoped)?\s+(?:evidence|anchors?|results?|proof)\b"
            r"[^.;]{0,40}\b(?:can\s+be|is|are)\s+(?:treated|used|accepted)\s+as\s+"
            r"(?:cross[-\s]+platform|portable|platform[-\s]+agnostic)\b|"
            r"\bdarwin(?:[-\s]+scoped)?\s+(?:evidence|anchors?|results?|proof)\b"
            r"[^.;]{0,40}\b(?:provides?|constitutes?|supplies?)\s+(?:an?\s+)?"
            r"(?:cross[-\s]+platform|portable|platform[-\s]+agnostic)\s+"
            r"(?:proof|evidence)\b",
            positive_sentence,
        )
        collective_excluded_claim = re.search(
            r"\b(?:(?:all|every|each|any|some|the\s+(?:five|5))\s+)?"
            r"excluded(?:\s+acceptance)?\s+gates?\b\s+(?:all\s+)?"
            r"(?:(?:is|are|was|were|remains?|became|becomes?|has|have)\s+"
            r"(?:all\s+)?(?:been\s+)?)?"
            r"(?:pass(?:ed|es|ing)?|succeed(?:s|ed)?|successful|works?|worked|portable|"
            r"cross[-\s]+platform|platform[-\s]+agnostic|supported|proven|verified|"
            r"validated|certified)\b",
            positive_sentence,
        )
        collective_excluded_denial = re.search(
            r"\b(?:no|none\s+of\s+the)\s+(?:(?:five|5)\s+)?"
            r"excluded(?:\s+acceptance)?\s+gates?\b[^.;]{0,32}"
            r"\b(?:pass(?:ed|es|ing)?|succeed(?:s|ed)?|successful|works?|worked|portable|"
            r"cross[-\s]+platform|platform[-\s]+agnostic|supported|proven|verified|"
            r"validated|certified)\b|"
            r"\b(?:must\s+not|cannot|never|does\s+not|may\s+not)\b[^.;]{0,160}"
            r"\b(?:claim|say|imply|allow)\w*\b[^.;]{0,64}"
            r"\b(?:(?:all|every|each|any|some|the\s+(?:five|5))\s+)?"
            r"excluded(?:\s+acceptance)?\s+gates?\b[^.;]{0,32}"
            r"\b(?:pass(?:ed|es|ing)?|succeed(?:s|ed)?|successful|works?|worked|portable|"
            r"cross[-\s]+platform|platform[-\s]+agnostic|supported|proven|verified|"
            r"validated|certified)\b",
            sentence,
        )
        if (
            ubuntu_conflict
            or linux_conflict
            or gate_conflict
            or (cross_platform_proof and denied_cross_platform_proof is None)
            or natural_status_conflict
            or direct_linux_proof
            or darwin_portability
            or (collective_excluded_claim and collective_excluded_denial is None)
        ):
            raise P12GateError("P12 contains a contradictory platform or excluded-gate claim")
    status_fields = (
        ("ubuntu_historical_execution_status", "not_proven"),
        ("linux_public_pilot_readiness", "blocked"),
    )
    for field, expected in status_fields:
        matches = re.finditer(
            rf"\b{field}\b`?(?:\s+values?)?\s*"
            rf"(?:=|is|are|remains?|becomes?|has|have)\s*"
            rf"(?:(not|never)(?:\s+been)?\s+)?`?([a-z0-9_]+)",
            normalized,
        )
        if any(match.group(1) is None and match.group(2) != expected for match in matches):
            raise P12GateError(f"P12 platform status drifted: {field}")
    for field, expected in (
        ("anchor_platform", "darwin"),
        ("anchor_historical_status", "passed"),
        ("purpose", "immutable_platform_scoped_identity_only"),
    ):
        values = re.findall(rf"\b{field}\b`?\s*=\s*`?([a-z0-9_]+)", normalized)
        if any(value != expected for value in values):
            raise P12GateError(f"P12 Darwin anchor qualifier drifted: {field}")


def reject_history_contradictions(text: str) -> None:
    normalized = " ".join(text.split())
    token = r"(?P<value>`[^`]+`|[0-9a-f]{40}|codex/[a-z0-9._/-]+|main)"

    def claim(version: str, field: str) -> str:
        return (
            rf"(?<![-/])\b(?:p12\s+)?{version}\b[^.;]{{0,400}}?\b(?:{field})\b"
            rf"(?:\s+(?:(?P<opposed>is\s+no\s+longer|differs?\s+from)|"
            rf"(?:is\s+now|has\s+(?:changed|moved)\s+to|"
            rf"(?:changed|moved)\s+to|is|was|remains|equals|at)))?"
            rf"(?:\s+exactly)?\s+{token}"
        )

    identities = (
        (claim("v4", r"branch"), "codex/p12-public-pilot-continuity-rebaseline-v4"),
        (
            claim("v4", r"base\s+commit|(?:accepted\s+)?base(?!\s+(?:commit|tree))"),
            "c1562ea5201394d8a278f4b644daf4029cbb5bd4",
        ),
        (claim("v4", r"base\s+tree"), "ae0f33263cfc7445fef69656ad9c5cb04d4a2d00"),
        (
            claim(
                "v4",
                r"acceptance\s+commit|immutable\s+acceptance\s+commit|(?<!base\s)commit",
            ),
            "dbdb75b6afcd226059484ec536fec82532eb3613",
        ),
        (
            claim("v4", r"acceptance\s+tree|(?<!base\s)tree"),
            "f8d0dad5c04253eefd24353f8c9afd965cf0d6ea",
        ),
        (
            claim("v4", r"acceptance\s+blob|blob"),
            "b574bb350a83a36f9ad7f521514c7d58e97393d9",
        ),
        (
            claim("v4", r"sole\s+parent|acceptance\s+parent"),
            "c1562ea5201394d8a278f4b644daf4029cbb5bd4",
        ),
        (claim("v1", r"branch"), "codex/p12-public-pilot-continuity-rebaseline"),
        (claim("v1", r"head|commit"), "8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3"),
        (claim("v1", r"tree"), "557a74e9174247483362bbbd15cd265113775d12"),
        (claim("v1", r"acceptance\s+blob|blob"), "26562d795980ec8d6d9ea36ff3fcc718b41c09e8"),
        (
            claim("v1", r"sole\s+parent|acceptance\s+parent|parent"),
            "c1562ea5201394d8a278f4b644daf4029cbb5bd4",
        ),
        (claim("v2", r"branch"), "codex/p12-public-pilot-continuity-rebaseline-v2"),
        (claim("v2", r"acceptance\s+commit"), "3639fa08ca44820bb922e0644095c9fb9c24d3e6"),
        (claim("v2", r"acceptance\s+tree"), "71c411660e0f7ff26e8ad1451acaa0ea26fa384b"),
        (claim("v2", r"acceptance\s+blob"), "50453e154cf642bc7b90644660e1d956b04f966a"),
        (claim("v2", r"final(?:\s+candidate)?\s+head"), "8e08c3891dc8f761ada096c3f829ef31d3fbfd7c"),
        (claim("v2", r"final(?:\s+candidate)?\s+tree"), "01ee7b08cc870a626698ac9a3fc46ec92bf0f4e0"),
        (
            claim("v2", r"acceptance(?:-only)?(?:\s+commit)?\s+(?:sole\s+)?parent"),
            "c1562ea5201394d8a278f4b644daf4029cbb5bd4",
        ),
        (claim("v3", r"branch"), "codex/p12-public-pilot-continuity-rebaseline-v3"),
        (claim("v3", r"acceptance\s+commit|commit"), "e31bc733cbdd333648f2ce1c52ac9fe1fad83179"),
        (claim("v3", r"acceptance\s+tree|tree"), "1cdce2a41f84ee4243d04be781ad187eb5f5fab9"),
        (claim("v3", r"acceptance\s+blob|blob"), "40c93a2aa8930c71e14fefac2053a10ed137af58"),
        (
            claim("v3", r"sole\s+parent|acceptance\s+parent|parent"),
            "c1562ea5201394d8a278f4b644daf4029cbb5bd4",
        ),
    )
    for pattern, expected_identity in identities:
        for identity_match in re.finditer(pattern, normalized, re.IGNORECASE):
            if (
                identity_match.group("opposed") is not None
                or identity_match.group("value").strip("`") != expected_identity
            ):
                raise P12GateError("P12 contains a contradictory preserved history identity")
    replacement_pattern = (
        r"\breplac(?:e|es|ed|ing)\b[^.;]{0,32}\b(?:p12\s+)?v[1-4]\b"
        r"[^.;]{0,160}\b(?:branch|base|commit|head|tree|blob|parent)\b"
        rf"[^.;]{{0,32}}\b(?:with|by)\s+{token}"
    )
    for replacement_match in re.finditer(replacement_pattern, normalized, re.IGNORECASE):
        if not _claim_is_negated(normalized, replacement_match.start()):
            raise P12GateError("P12 preserved history identity was replaced")
    v2_objects = {commit: (parent, tree) for commit, parent, tree, _ in V2_CHAIN}
    for sentence in re.split(r"[.;]\s+", normalized):
        if re.search(r"(?<![-/])\bv2\b", sentence, re.IGNORECASE):
            commit_match = re.search(
                r"\bcommit\b(?:\s+(?:is|was|=|at))?\s+`?([0-9a-f]{40})`?",
                sentence,
                re.IGNORECASE,
            )
            if commit_match:
                expected_v2_object = v2_objects.get(commit_match.group(1))
                if expected_v2_object is None:
                    raise P12GateError("P12 contains an unknown v2 commit identity")
                for field, expected_value in (
                    ("parent", expected_v2_object[0]),
                    ("tree", expected_v2_object[1]),
                ):
                    field_match = re.search(
                        rf"\b(?:sole\s+)?{field}\b(?:\s+(?:is|was|=|at))?\s+"
                        rf"`?([0-9a-f]{{40}})`?",
                        sentence,
                        re.IGNORECASE,
                    )
                    if field_match and field_match.group(1) != expected_value:
                        raise P12GateError("P12 v2 commit parent or tree identity drifted")
    sentences = re.split(r"\.\s+", normalized)
    prior_was_pr14 = False
    for sentence in sentences:
        direct_pr14 = (
            re.search(
                r"(?:\bpr\s*#?\s*14\b|\bpull request\b[^.;]{0,100}(?:#14|/14|\b14\b))",
                sentence,
                re.IGNORECASE,
            )
            is not None
        )
        inherited_pr14 = prior_was_pr14 and re.match(r"\s*its\b", sentence, re.I) is not None
        prior_was_pr14 = direct_pr14
        if not direct_pr14 and not inherited_pr14:
            continue
        if re.search(
            r"\bstate\s*(?:is|=)\s*`?(?:open|merged)\b|"
            r"\b(?:is|was|remains)\s+(?:exactly\s+)?(?:open|merged)\b|"
            r"\b(?:state\s*(?:is|=)|(?:is|was|remains))\s+"
            r"(?:exactly\s+)?(?:not|no\s+longer)\s+`?closed\b",
            sentence,
            re.IGNORECASE,
        ):
            raise P12GateError("P12 PR #14 state contradicts CLOSED without merge")
        for reopened_match in re.finditer(r"\breopen(?:ed|s|ing)?\b", sentence, re.IGNORECASE):
            if not _claim_is_negated(sentence, reopened_match.start()):
                raise P12GateError("P12 PR #14 state contradicts CLOSED without merge")
        for field in ("mergedAt", "mergeCommit", "autoMergeRequest"):
            for match in re.finditer(
                rf"\b{field}\b`?\s*(?:is|=)\s*`?([^`\s,;.]+)",
                sentence,
                re.IGNORECASE,
            ):
                if match.group(1).lower() != "null":
                    raise P12GateError("P12 PR #14 merge boundary is non-null")
        if re.search(
            r"\b(?:mergedAt|mergeCommit|autoMergeRequest)\b[^.;]{0,120}\bnon-null\b",
            sentence,
            re.IGNORECASE,
        ):
            raise P12GateError("P12 PR #14 merge boundary is non-null")
        explicit_pr_fields = (
            ("baseRefName", "main"),
            ("baseRefOid", "c1562ea5201394d8a278f4b644daf4029cbb5bd4"),
            ("headRefName", "codex/p12-public-pilot-continuity-rebaseline-v2"),
            ("headRefOid", "8e08c3891dc8f761ada096c3f829ef31d3fbfd7c"),
        )
        for field, expected_pr_value in explicit_pr_fields:
            for explicit_field_match in re.finditer(
                rf"\b{field}\b`?\s*(?:is|=)\s*`?([^`\s,;.]+)",
                sentence,
                re.IGNORECASE,
            ):
                if explicit_field_match.group(1) != expected_pr_value:
                    raise P12GateError("P12 PR #14 base/head identity drifted")
        for field, expected_name, expected_oid in (
            ("base", "main", "c1562ea5201394d8a278f4b644daf4029cbb5bd4"),
            (
                "head",
                "codex/p12-public-pilot-continuity-rebaseline-v2",
                "8e08c3891dc8f761ada096c3f829ef31d3fbfd7c",
            ),
        ):
            natural_field_match = re.search(
                rf"\b{field}\b\s*(?:is|=)\s*`?([^`\s,;.]+)`?"
                rf"(?:\s+at\s+`?([0-9a-f]{{40}})`?)?",
                sentence,
                re.IGNORECASE,
            )
            if natural_field_match and (
                natural_field_match.group(1) != expected_name
                or (
                    natural_field_match.group(2) is not None
                    and natural_field_match.group(2) != expected_oid
                )
            ):
                raise P12GateError("P12 PR #14 base/head identity drifted")
    forbidden = (
        r"(?:pr|pull request)\s*#?14[^.]{0,120}\b(?:was|is|remains)\s+merged\b",
        r"run\s+`?34542709145`?[^.]{0,120}\b(?:success|passed)\w*\b",
        r"run\s+`?34564478590`?[^.]{0,120}\b(?:success|passed)\w*\b",
        r"run\s+`?34542709145`?[^.]{0,120}\b(?:no\s+longer|not)\b"
        r"[^.]{0,80}\b(?:failure|failed)\b",
        r"run\s+`?34564478590`?[^.]{0,120}\b(?:no\s+longer|not)\b"
        r"[^.]{0,80}\b(?:failure|failed)\b",
        r"\bv[12]\b[^.]{0,120}\baccepted\s+ancestors?\b",
        r"\bv3\b[^.]{0,160}\bmutable\s+implementation\b",
        r"\bv3\b[^.]{0,160}\bcreated\s+(?:an?\s+)?(?:implementation|summary|remote|pull request|tag|release|publication)\b",
    )
    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in forbidden):
        raise P12GateError("P12 contains a contradictory preserved history claim")


def validate_claim_boundary(text: str) -> None:
    required = (
        "governance-only",
        "not_evaluated",
        "zero publication",
        "does not start",
    )
    require_markers(text, required, label="P12 claim boundary")
    named_capability = (
        r"(?:semantic\s+memory|projectcontinuationstate|"
        r"runtime\s+(?:support|capabilit(?:y|ies)|behavio[u]?r)|"
        r"(?:openai\s+(?:model\s+)?gateway|model\s+gateway)|"
        r"(?:microsoft\s+365|m365)\s+(?:connector|provider\s+access|access)|"
        r"provider\s+access|"
        r"(?:api|cli|studio)(?:\s+product)?\s+"
        r"(?:behavio[u]?r|capabilit(?:y|ies)|runtime\s+support)|"
        r"(?:release|publication)(?:\s*/\s*(?:release|publication))?\s+path|"
        r"(?:release|publication)(?!\s+(?:path|capabilit(?:y|ies))\s+"
        r"(?:contract|governance|documentation|documents?|tests?|policy|policies|"
        r"requirements?|boundary|design|plan|planning))|"
        r"(?:release|publication|distribution|connector|product)\s+"
        r"capabilit(?:y|ies)|(?:executable\s+)?product\s+behavio[u]?r)"
    )
    capability_action = (
        r"(?:implements?|implemented|delivers?|delivered|provides?|provided|supplies?|"
        r"supplied|adds?|added|creates?|created|introduces?|introduced|enables?|enabled|"
        r"ships?|shipped|establishes?|established)"
    )
    direct_capability_claim = (
        rf"\bp12(?:\s+v4)?\s+(?:now\s+|already\s+|currently\s+)?"
        rf"{capability_action}\s+(?:an?\s+|the\s+)?"
        rf"(?:(?:working|live|executable|production|runtime|product)\s+){{0,2}}"
        rf"{named_capability}\b"
        r"(?!\s+(?:contract|governance|documentation|documents?|tests?|policy|policies|"
        r"requirements?|boundary|design|plan|planning))"
    )
    passive_capability_claim = (
        rf"\b{named_capability}\b"
        r"(?!\s+(?:contract|governance|documentation|documents?|tests?|policy|policies|"
        r"requirements?|boundary|design|plan|planning))"
        r"[^.;]{0,32}\b(?:is|was|has\s+been)\s+(?:now\s+|already\s+)?"
        r"(?:implemented|delivered|provided|supplied|added|created|introduced|enabled|"
        r"shipped|established)\s+by\s+p12(?:\s+v4)?\b"
    )
    forbidden = (
        direct_capability_claim,
        passive_capability_claim,
        r"\bp12(?:\s+v4)?\s+(?:now\s+|already\s+|currently\s+)?"
        r"is\s+(?:public\s+pilot\s+ready|ready\s+for\s+(?:the\s+)?public\s+pilot|"
        r"production[-\s]+ready)\b",
        r"\bp12(?:\s+v4)?\s+(?:now\s+|already\s+|currently\s+)?"
        r"makes?\s+(?:the\s+)?public\s+pilot\s+(?:launch[-\s]+)?ready\b",
        r"\bp12(?:\s+v4)?\s+(?:now\s+|already\s+|currently\s+)?"
        r"(?:begins?|starts?|authorizes?)\s+p13(?:\s+implementation)?\b",
        r"\bp12(?:\s+v4)?\s+(?:now\s+|already\s+|currently\s+)?"
        r"changes?\s+(?:the\s+)?(?:schema|schemas|migrations?)\b",
    )
    if any(re.search(pattern, text, re.IGNORECASE) for pattern in forbidden):
        raise P12GateError("P12 living records overclaim an unimplemented capability")


def validate_platform_status(text: str) -> None:
    reject_platform_contradictions(text)
    require_markers(
        text,
        (
            "three independent status dimensions",
            "`p12_governance_result` may become `passed`",
            "five `ubuntu_historical_execution_status` values remains `not_proven`",
            "`linux_public_pilot_readiness` remains `blocked`",
        ),
        label="P12 platform-status separation",
    )
    forbidden = (
        "`ubuntu_historical_execution_status` values remains `passed`",
        "`ubuntu_historical_execution_status = passed`",
        "`linux_public_pilot_readiness` remains `passed`",
        "`linux_public_pilot_readiness = passed`",
    )
    if any(marker in text for marker in forbidden):
        raise P12GateError("P12 Linux platform status was promoted without P20-L0")


def validate_p8_darwin_scope(text: str) -> None:
    reject_platform_contradictions(text)
    require_markers(text, DARWIN_ANCHOR_MARKERS, label="five accepted P8/P10 Darwin anchors")
    try:
        exclusion_section = text.split("The exact ordered exclusions are:", 1)[1].split(
            "Each excluded result", 1
        )[0]
        qualifier_section = text.split("Each excluded result", 1)[1].split(
            "The five proofs remain distinct.", 1
        )[0]
        anchor_section = text.split(
            "| Gate | Source commit | Source tree | Summary path / blob / file SHA-256 |", 1
        )[1].split("The five proofs remain distinct.", 1)[0]
    except IndexError as exc:
        raise P12GateError("P12 Darwin anchor table is unavailable") from exc
    normalized_qualifiers = " ".join(qualifier_section.split())
    normalized_text = " ".join(text.split())
    canonicalization_conflicts = (
        r"\b(?:selected|anchor)\s+composites?\b[^.;]{0,80}\buses?\s+"
        r"`?(?:general\s+)?p12-cj-1\b",
        r"\b(?:appendix\s+c(?:\s+legacy)?(?:\s+anchor)?\s+(?:algorithm|canonicalization)|"
        r"anchor\s+byte\s+algorithm|that\s+byte\s+algorithm)\b[^.;]{0,120}"
        r"\b(?:identical|equivalent|same|not\s+distinct)\b[^.;]{0,80}\bp12-cj-1\b",
        r"\banchor\s+composites?\b[^.;]{0,80}\b(?:allow_nan|ensure_ascii)\s*=\s*true\b",
        r"\bembedded-anchor\s+metadata\b[^.;]{0,80}\bcanonicalization\b[^.;]{0,32}"
        r"\b(?:is|uses?|=)\s+`?appendix\s+c\b",
    )
    if DARWIN_ANCHOR_CANONICALIZATION_MARKER not in normalized_qualifiers or any(
        re.search(pattern, normalized_text, re.IGNORECASE) for pattern in canonicalization_conflicts
    ):
        raise P12GateError("P12 Darwin anchor canonicalization identity drifted")
    exclusions = tuple(
        match.group(1)
        for match in re.finditer(r"^\d+\. `([^`]+)`$", exclusion_section, re.MULTILINE)
    )
    rows: list[tuple[str, ...]] = []
    for line in anchor_section.splitlines():
        if not line.startswith("|") or set(line.replace("|", "").strip()) <= {"-", ":", " "}:
            continue
        cells = tuple(cell.strip().replace("`", "") for cell in line.strip().strip("|").split("|"))
        if len(cells) != 7:
            raise P12GateError("P12 Darwin anchor table row is malformed")
        rows.append(cells)
    if exclusions != EXCLUDED_GATE_IDS or tuple(rows) != DARWIN_ANCHOR_ROWS:
        raise P12GateError("P12 ordered exclusions or Darwin anchor identities drifted")


def validate_v4_identity(text: str) -> None:
    reject_history_contradictions(text)
    normalized = " ".join(text.split())
    required = (
        "P11R closed the accepted P0-P11R line at commit `c1562ea5201394d8a278f4b644daf4029cbb5bd4`.",
        "P12 v1 and v2 are rejected and remain immutable non-ancestors of v4.",
        "V1 used branch `codex/p12-public-pilot-continuity-rebaseline`, head `8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3`, tree `557a74e9174247483362bbbd15cd265113775d12`, and acceptance blob `26562d795980ec8d6d9ea36ff3fcc718b41c09e8`",
        "V2 used branch `codex/p12-public-pilot-continuity-rebaseline-v2`.",
        "Its acceptance commit is `3639fa08ca44820bb922e0644095c9fb9c24d3e6`, acceptance tree is `71c411660e0f7ff26e8ad1451acaa0ea26fa384b`, acceptance blob is `50453e154cf642bc7b90644660e1d956b04f966a`, and acceptance file SHA-256 is `be3ad1967a98c67ae34ad7c22c35a9ec1f637a780c930ae4e8349f126e64800b`.",
        "Its final head is `8e08c3891dc8f761ada096c3f829ef31d3fbfd7c` with tree `01ee7b08cc870a626698ac9a3fc46ec92bf0f4e0`.",
        "Pull request `jeremyliu1220/digital-colleagues#14` remains exactly `CLOSED` without merge.",
        "Its base is `main` at `c1562ea5201394d8a278f4b644daf4029cbb5bd4`; its head is `codex/p12-public-pilot-continuity-rebaseline-v2` at `8e08c3891dc8f761ada096c3f829ef31d3fbfd7c`; and `mergedAt`, `mergeCommit`, and `autoMergeRequest` are all null.",
        "Run `34542709145` is a `pull_request` / `CI` run at head `fc145550b750c172899bc1497ff5fede387c07dc`; it has exactly attempt 1, which is `completed` / `failure`.",
        "Run `34564478590` is a `pull_request` / `CI` run at the final v2 head; it has exactly attempts 1 and 2, both `completed` / `failure`.",
        "Attempt 1 was created at `2026-09-11T05:03:14Z` and completed at `2026-09-11T05:06:34Z`; attempt 2 was created at `2026-09-11T05:12:52Z` and completed at `2026-09-11T05:16:00Z`.",
        "Draft-time Actions retention is 90 days, the maximum allowed is 90 days, and the conservative earliest normal expiry boundary is `2026-12-10T05:03:14Z`.",
        "Both final-head attempts reached the accepted P8 actual Compose boundary and failed safely at `pre_start_restore`.",
        "V2's exact rejection classification is `rejected_linux_historical_replay_contract_infeasible`.",
        "No v2 summary, evidence, merge, tag, Release, or publication exists, and no failed attempt is reclassified.",
        "V3 is not relabeled as rejected. It is a superseded immutable acceptance-only attempt",
        "branch `codex/p12-public-pilot-continuity-rebaseline-v3`, at commit `e31bc733cbdd333648f2ce1c52ac9fe1fad83179`, tree `1cdce2a41f84ee4243d04be781ad187eb5f5fab9`, and acceptance blob `40c93a2aa8930c71e14fefac2053a10ed137af58`, with the accepted P11R base as sole parent.",
        "Its acceptance file is 3488 lines and 232313 bytes with SHA-256 `6afddd55f4f8458c94dcd56b781e47fef66a06d954d4246aa3855b4daf2e0e3c`.",
        "V3 created no implementation, correction, summary, remote branch, pull request, tag, Release, or publication.",
        "it is preserved as a non-ancestor rather than amended.",
        "P12 v4 starts directly from the same accepted base on `codex/p12-public-pilot-continuity-rebaseline-v4`. Its immutable acceptance commit is `dbdb75b6afcd226059484ec536fec82532eb3613`, tree `f8d0dad5c04253eefd24353f8c9afd965cf0d6ea`, and acceptance blob `b574bb350a83a36f9ad7f521514c7d58e97393d9`.",
    )
    require_markers(normalized, required, label="P12 v1/v2/v3/v4 ADR identities")
    try:
        chain_section = text.split("| Commit | Sole parent | Tree | Purpose |", 1)[1].split(
            "Pull request `jeremyliu1220/digital-colleagues#14`", 1
        )[0]
    except IndexError as exc:
        raise P12GateError("P12 retained v2 commit chain is unavailable") from exc
    rows: list[tuple[str, ...]] = []
    for line in chain_section.splitlines():
        if not line.startswith("|") or set(line.replace("|", "").strip()) <= {"-", ":", " "}:
            continue
        cells = tuple(cell.strip().strip("`") for cell in line.strip().strip("|").split("|"))
        if len(cells) != 4:
            raise P12GateError("P12 retained v2 commit-chain row is malformed")
        rows.append(cells)
    if tuple(rows) != V2_CHAIN:
        raise P12GateError("P12 retained v2 commit chain drifted")


def validate_p20_l0(text: str) -> None:
    try:
        p20 = text.split("## P20 — Always-on Public Pilot Release", 1)[1]
        p20 = p20.split("## Post-v0.1 outlook", 1)[0]
    except IndexError as exc:
        raise P12GateError("P20 roadmap section is unavailable") from exc
    require_markers(
        p20,
        (
            "The first blocking P20 implementation sub-gate is P20-L0",
            "before any other P20 implementation",
            "host operator UID differs from container UID 10001",
            "Containers stay\nnon-root",
            "private directories stay 0700 and private files 0600",
            "Migration 015 remains unauthorized",
        ),
        label="P20-L0 first blocking sub-gate",
    )
    normalized = " ".join(text.split()).lower()
    first_claims = tuple(
        match.group(1) or match.group(2)
        for match in re.finditer(
            r"\bfirst\s+blocking\s+p20(?:\s+implementation)?\s+sub-gate\s+is\s+p20-l(\d+)\b|"
            r"\bp20-l(\d+)\b[^.;]{0,48}\bis\s+(?:the\s+)?first\s+blocking\s+p20"
            r"(?:\s+implementation)?\s+sub-gate\b",
            normalized,
        )
    )
    if any(value != "0" for value in first_claims):
        raise P12GateError("P20-L0 first blocking sub-gate identity drifted")
    if re.search(
        r"\bp20-l0\b[^.;]{0,48}\b(?:is|remains)\s+not\s+(?:the\s+)?first\s+blocking\b",
        normalized,
    ):
        raise P12GateError("P20-L0 was contradicted as the first blocking sub-gate")
    if re.search(
        r"\bmigration\s+015\b[^.;]{0,80}\b(?:is|becomes|became|now)\s+"
        r"(?:now\s+)?authorized\b",
        normalized,
    ):
        raise P12GateError("Migration 015 was prematurely authorized")
    for sentence in re.split(r"[.;]\s+", normalized):
        if re.search(r"\bp20-l0\b[^.;]{0,96}\b(?:follows|comes\s+after|runs\s+after)\b", sentence):
            if (
                re.search(
                    r"\b(?:not|never|cannot|does\s+not|must\s+not)\b[^.;]{0,32}"
                    r"\b(?:follow|follows|come\s+after|comes\s+after|run\s+after|runs\s+after)\b",
                    sentence,
                )
                is None
            ):
                raise P12GateError("P20-L0 was ordered after a later P20 gate")


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
    checklist = documents["docs/p12/rebaseline-checklist.md"]
    validate_lifecycle_order(checklist)
    validate_checklist_contract(checklist)
    reject_platform_contradictions(checklist)
    validate_p20_l0(documents["docs/roadmap.md"])
    require_markers(
        documents["docs/adr/0011-public-pilot-continuity-rebaseline.md"],
        ADR_MARKERS,
        label="ADR 0011",
    )
    validate_platform_status(documents["docs/adr/0011-public-pilot-continuity-rebaseline.md"])
    validate_p8_darwin_scope(documents["docs/adr/0011-public-pilot-continuity-rebaseline.md"])
    validate_governance_counts(documents["docs/adr/0011-public-pilot-continuity-rebaseline.md"])
    validate_v4_identity(documents["docs/adr/0011-public-pilot-continuity-rebaseline.md"])
    require_markers(acceptance, ACCEPTANCE_MARKERS, label="P12 acceptance")
    validate_core_records(acceptance)
    combined = "\n".join(documents.values())
    reject_platform_contradictions(combined)
    reject_history_contradictions(combined)
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
        **PLATFORM_STATUS,
        "p20_first_blocking_subgate": "P20-L0",
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
