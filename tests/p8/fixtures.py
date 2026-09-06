# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from digital_colleagues.application.p4_contracts import WorkAssignmentRequest
from digital_colleagues.application.p6_contracts import ChangeDecisionRequest
from digital_colleagues.core.effects import ApprovalChoice
from digital_colleagues.core.governance import ChangeChoice
from digital_colleagues.core.principals import HumanRole
from tests.p6.fixtures import P6Harness, build_harness, initial_request
from tests.p6.test_authentication_rbac import bootstrap, enroll

ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMMIT = "1" * 40


def write_release_manifest(directory: Path, *, migration_digest: str | None = None) -> Path:
    digest = (
        migration_digest
        or "sha256:" + hashlib.sha256((ROOT / "migrations/manifest.json").read_bytes()).hexdigest()
    )
    path = directory / "release-manifest.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "release_version": "0.1.0",
                "source_commit": SOURCE_COMMIT,
                "source_timestamp": "2026-09-06T00:00:00Z",
                "migration_manifest_digest": digest,
                "artifacts": [],
                "build_inputs": [],
                "evidence_classes": {},
                "claim_exclusions": [],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def create_full_state(database: Path) -> tuple[P6Harness, str]:
    harness = build_harness(database)
    _, grant = bootstrap(harness)
    _, second = enroll(
        harness,
        issuer=grant,
        role=HumanRole.TENANT_ADMIN,
        scopes=("*",),
        key="p8-second-admin",
    )
    profile, mandate, _ = harness.colleagues.create(
        session=grant.session, request=initial_request()
    )
    colleague_id = profile.namespace.scope_id
    assert colleague_id is not None
    session = harness.authentication.bind_colleague(
        grant.session, colleague_id, idempotency_key="p8-bind"
    )
    second_session = harness.authentication.bind_colleague(
        second.session_grant.session,
        colleague_id,
        idempotency_key="p8-second-bind",
    )
    draft = harness.inner_builder.create(session=session, idempotency_key="p8-policy-draft")
    reviewed = harness.inner_builder.review(
        session=session, draft_id=draft.draft_id, expected_revision=draft.revision
    )
    change_proposal = harness.changes.propose_draft(
        session=session,
        draft_id=reviewed.draft_id,
        expected_revision=reviewed.revision,
        expected_digest=reviewed.canonical_digest,
        idempotency_key="p8-policy-proposal",
    )
    _, decision = harness.changes.decide(
        session=second_session,
        namespace=profile.namespace,
        proposal_id=change_proposal.proposal_id,
        request=ChangeDecisionRequest(
            proposal_revision=change_proposal.revision,
            proposal_digest=change_proposal.canonical_digest,
            choice=ChangeChoice.APPROVE,
            idempotency_key="p8-policy-approval",
        ),
    )
    harness.changes.apply_draft(
        session=session,
        namespace=profile.namespace,
        proposal_id=change_proposal.proposal_id,
        decision_id=decision.decision_id,
        idempotency_key="p8-policy-confirm",
    )
    active_profile, active_mandate = harness.store.active_configuration(profile.namespace)
    work, _ = harness.colleagues.assign_work(
        session=session,
        request=WorkAssignmentRequest(
            title="P8 finite synthetic work",
            description="Exercise private backup and atomic restore.",
            responsibility_id=active_mandate.responsibilities[0].responsibility_id,
            idempotency_key="p8-work",
        ),
    )
    for trigger_class, no_op, key in (
        ("timer", True, "p8-timer"),
        ("event", False, "p8-event"),
    ):
        harness.controller.submit_trigger(
            session=session,
            work_id=work.work_id,
            trigger_class=trigger_class,
            deterministic_noop=no_op,
            idempotency_key=key,
        )
        harness.controller.process_once(
            harness.controller.service_context(active_profile.namespace)
        )
    snapshot = harness.store.studio_snapshot(active_profile.namespace)
    effect_proposal = snapshot.proposals[0]
    harness.controller.decide_proposal(
        session=session,
        proposal=effect_proposal,
        choice=ApprovalChoice.APPROVE,
        idempotency_key="p8-approval",
        expected_proposal_revision=effect_proposal.revision,
        expected_payload_digest=effect_proposal.payload_digest,
        expected_proposal_digest=effect_proposal.proposal_digest,
        expected_mandate_id=effect_proposal.mandate_id or "missing",
        expected_mandate_revision=effect_proposal.mandate_revision or 1,
        expected_policy_id=effect_proposal.policy_id,
        expected_policy_revision=effect_proposal.policy_revision,
    )
    harness.controller.process_once(harness.controller.service_context(active_profile.namespace))
    return harness, colleague_id


def canonical_database_state(database: Path) -> dict[str, list[list[Any]]]:
    connection = sqlite3.connect(database)
    try:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            )
        ]
        result: dict[str, list[list[Any]]] = {}
        for table in tables:
            columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
            order = ", ".join(f'"{column}"' for column in columns)
            rows = connection.execute(f'SELECT {order} FROM "{table}" ORDER BY {order}').fetchall()
            result[table] = [list(row) for row in rows]
        return result
    finally:
        connection.close()


def required_state_counts(database: Path) -> dict[str, int]:
    connection = sqlite3.connect(database)
    try:
        record_types = {
            row[0]: row[1]
            for row in connection.execute(
                "SELECT record_type, COUNT(*) FROM domain_records GROUP BY record_type"
            )
        }
        return {
            "profile": record_types.get("profile", 0),
            "mandate": record_types.get("mandate", 0),
            "colleague_policy": record_types.get("colleague_policy", 0),
            "finite_work": record_types.get("finite_work", 0),
            "input_event": record_types.get("input_event", 0),
            "timer_occurrence": record_types.get("timer_occurrence", 0),
            "wake_cycle": record_types.get("wake_cycle", 0),
            "agenda_item": record_types.get("agenda_item", 0),
            "effect_proposal": record_types.get("effect_proposal", 0),
            "human_approval": record_types.get("human_approval", 0),
            "action_result": record_types.get("action_result", 0),
            "audit_records": connection.execute("SELECT COUNT(*) FROM audit_records").fetchone()[0],
            "drafts": connection.execute("SELECT COUNT(*) FROM p5_colleague_drafts").fetchone()[0],
            "confirmations": connection.execute(
                "SELECT COUNT(*) FROM p5_draft_confirmations"
            ).fetchone()[0],
            "memberships": connection.execute("SELECT COUNT(*) FROM p6_memberships").fetchone()[0],
            "sessions": connection.execute("SELECT COUNT(*) FROM p4_sessions").fetchone()[0],
        }
    finally:
        connection.close()
