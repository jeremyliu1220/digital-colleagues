# SPDX-License-Identifier: Apache-2.0

"""Deterministic public serialization for stable core contracts."""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum

from digital_colleagues.core.authority import (
    CapabilityGrant,
    Constraint,
    EffectBoundary,
    IdentityCard,
    Mandate,
    MandateAuthorityDiff,
    Profile,
    ResponsibilityDefinition,
)
from digital_colleagues.core.common import FrozenJsonObject, require_utc
from digital_colleagues.core.effects import (
    ActionResult,
    EffectAttempt,
    EffectConstraints,
    EffectDestination,
    EffectProposal,
    HumanApprovalDecision,
)
from digital_colleagues.core.errors import CoreInvariantError
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import Principal
from digital_colleagues.core.runtime import (
    AgendaItem,
    Decision,
    InputEvent,
    TimerOccurrence,
    WakeCycle,
)
from digital_colleagues.core.work import CompletionEvidence, FiniteWork, Obligation, Responsibility


def datetime_to_z(value: datetime) -> str:
    require_utc(value, "datetime")
    return value.isoformat(timespec="microseconds").removesuffix("+00:00") + "Z"


def datetime_from_z(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise CoreInvariantError("serialized datetime must use an ISO 8601 Z suffix")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CoreInvariantError("serialized datetime is invalid") from exc
    return require_utc(parsed, "datetime")


def _contract_items(value: object) -> tuple[tuple[str, object], ...] | None:
    if isinstance(value, Profile):
        return (
            ("namespace", value.namespace),
            ("profile_id", value.profile_id),
            ("display_name", value.display_name),
            ("description", value.description),
            ("presentation", value.presentation),
            ("revision", value.revision),
            ("updated_by", value.updated_by),
            ("updated_at", value.updated_at),
            ("schema_version", value.schema_version),
        )
    if isinstance(value, ResponsibilityDefinition):
        return (
            ("responsibility_id", value.responsibility_id),
            ("description", value.description),
            ("obligations", value.obligations),
            ("completion_conditions", value.completion_conditions),
        )
    if isinstance(value, CapabilityGrant):
        return (("capability_id", value.capability_id), ("description", value.description))
    if isinstance(value, Constraint):
        return (("constraint_id", value.constraint_id), ("description", value.description))
    if isinstance(value, EffectBoundary):
        return (
            ("boundary_id", value.boundary_id),
            ("effect_kind", value.effect_kind),
            ("allowed_destination_kinds", value.allowed_destination_kinds),
            ("allowed_actions", value.allowed_actions),
            ("constraints", value.constraints),
            ("human_approval_required", value.human_approval_required),
        )
    if isinstance(value, Mandate):
        return (
            ("namespace", value.namespace),
            ("mandate_id", value.mandate_id),
            ("mission", value.mission),
            ("service_relationship", value.service_relationship),
            ("responsibilities", value.responsibilities),
            ("capabilities", value.capabilities),
            ("constraints", value.constraints),
            ("working_context", value.working_context),
            ("effect_boundaries", value.effect_boundaries),
            ("revision", value.revision),
            ("issued_by", value.issued_by),
            ("effective_at", value.effective_at),
            ("schema_version", value.schema_version),
        )
    if isinstance(value, IdentityCard):
        return (
            ("namespace", value.namespace),
            ("profile_id", value.profile_id),
            ("profile_revision", value.profile_revision),
            ("display_name", value.display_name),
            ("description", value.description),
            ("mandate_id", value.mandate_id),
            ("mandate_revision", value.mandate_revision),
            ("mission", value.mission),
            ("responsibility_summaries", value.responsibility_summaries),
            ("capability_summaries", value.capability_summaries),
            ("schema_version", value.schema_version),
        )
    if isinstance(value, MandateAuthorityDiff):
        return (
            ("namespace", value.namespace),
            ("mandate_id", value.mandate_id),
            ("from_revision", value.from_revision),
            ("to_revision", value.to_revision),
            ("mission_changed", value.mission_changed),
            ("service_relationship_changed", value.service_relationship_changed),
            ("working_context_changed", value.working_context_changed),
            ("added_responsibility_ids", value.added_responsibility_ids),
            ("removed_responsibility_ids", value.removed_responsibility_ids),
            ("changed_responsibility_ids", value.changed_responsibility_ids),
            ("added_capability_ids", value.added_capability_ids),
            ("removed_capability_ids", value.removed_capability_ids),
            ("changed_capability_ids", value.changed_capability_ids),
            ("added_constraint_ids", value.added_constraint_ids),
            ("removed_constraint_ids", value.removed_constraint_ids),
            ("changed_constraint_ids", value.changed_constraint_ids),
            ("added_effect_boundary_ids", value.added_effect_boundary_ids),
            ("removed_effect_boundary_ids", value.removed_effect_boundary_ids),
            ("changed_effect_boundary_ids", value.changed_effect_boundary_ids),
            ("schema_version", value.schema_version),
        )
    if isinstance(value, EffectDestination):
        return (("kind", value.kind), ("target", value.target))
    if isinstance(value, EffectConstraints):
        return (
            ("boundary_id", value.boundary_id),
            ("idempotency_key", value.idempotency_key),
            ("valid_until", value.valid_until),
            ("maximum_attempts", value.maximum_attempts),
            ("parameters", value.parameters),
        )
    if isinstance(value, EffectProposal):
        return (
            ("namespace", value.namespace),
            ("proposal_id", value.proposal_id),
            ("decision_id", value.decision_id),
            ("effect_kind", value.effect_kind),
            ("destination", value.destination),
            ("action", value.action),
            ("safe_projection", value.safe_projection),
            ("constraints", value.constraints),
            ("state", value.state),
            ("actor", value.actor),
            ("correlation_id", value.correlation_id),
            ("causation_id", value.causation_id),
            ("occurred_at", value.occurred_at),
            ("revision", value.revision),
            ("schema_version", value.schema_version),
            ("mandate_id", value.mandate_id),
            ("mandate_revision", value.mandate_revision),
            ("payload_digest", value.payload_digest),
            ("proposal_digest", value.proposal_digest),
        )
    if isinstance(value, HumanApprovalDecision):
        return (
            ("namespace", value.namespace),
            ("approval_decision_id", value.approval_decision_id),
            ("proposal_id", value.proposal_id),
            ("proposal_revision", value.proposal_revision),
            ("proposal_payload_digest", value.proposal_payload_digest),
            ("proposal_digest", value.proposal_digest),
            ("choice", value.choice),
            ("author", value.author),
            ("idempotency_key", value.idempotency_key),
            ("correlation_id", value.correlation_id),
            ("causation_id", value.causation_id),
            ("occurred_at", value.occurred_at),
            ("valid_until", value.valid_until),
            ("revision", value.revision),
            ("schema_version", value.schema_version),
        )
    if isinstance(value, EffectAttempt):
        return (
            ("namespace", value.namespace),
            ("effect_attempt_id", value.effect_attempt_id),
            ("proposal_id", value.proposal_id),
            ("proposal_revision", value.proposal_revision),
            ("approval_decision_id", value.approval_decision_id),
            ("attempt_number", value.attempt_number),
            ("state", value.state),
            ("actor", value.actor),
            ("correlation_id", value.correlation_id),
            ("causation_id", value.causation_id),
            ("occurred_at", value.occurred_at),
            ("revision", value.revision),
            ("schema_version", value.schema_version),
        )
    if isinstance(value, ActionResult):
        return (
            ("namespace", value.namespace),
            ("action_result_id", value.action_result_id),
            ("effect_attempt_id", value.effect_attempt_id),
            ("state", value.state),
            ("safe_projection", value.safe_projection),
            ("result_digest", value.result_digest),
            ("actor", value.actor),
            ("correlation_id", value.correlation_id),
            ("causation_id", value.causation_id),
            ("occurred_at", value.occurred_at),
            ("revision", value.revision),
            ("schema_version", value.schema_version),
        )
    if isinstance(value, Namespace):
        return (
            ("tenant_id", value.tenant_id),
            ("scope", value.scope),
            ("scope_id", value.scope_id),
        )
    if isinstance(value, Principal):
        return (
            ("namespace", value.namespace),
            ("principal_id", value.principal_id),
            ("kind", value.kind),
            ("roles", value.roles),
            ("revision", value.revision),
            ("schema_version", value.schema_version),
        )
    if isinstance(value, InputEvent):
        return (
            ("namespace", value.namespace),
            ("event_id", value.event_id),
            ("event_type", value.event_type),
            ("state", value.state),
            ("safe_projection", value.safe_projection),
            ("payload_digest", value.payload_digest),
            ("actor", value.actor),
            ("correlation_id", value.correlation_id),
            ("causation_id", value.causation_id),
            ("occurred_at", value.occurred_at),
            ("revision", value.revision),
            ("schema_version", value.schema_version),
        )
    if isinstance(value, TimerOccurrence):
        return (
            ("namespace", value.namespace),
            ("timer_id", value.timer_id),
            ("occurrence_id", value.occurrence_id),
            ("state", value.state),
            ("due_at", value.due_at),
            ("safe_projection", value.safe_projection),
            ("actor", value.actor),
            ("correlation_id", value.correlation_id),
            ("causation_id", value.causation_id),
            ("occurred_at", value.occurred_at),
            ("revision", value.revision),
            ("schema_version", value.schema_version),
        )
    if isinstance(value, WakeCycle):
        return (
            ("namespace", value.namespace),
            ("wake_cycle_id", value.wake_cycle_id),
            ("state", value.state),
            ("trigger_event_ids", value.trigger_event_ids),
            ("agenda_item_ids", value.agenda_item_ids),
            ("actor", value.actor),
            ("correlation_id", value.correlation_id),
            ("causation_id", value.causation_id),
            ("occurred_at", value.occurred_at),
            ("revision", value.revision),
            ("schema_version", value.schema_version),
            ("fencing_token", value.fencing_token),
            ("checkpoint_generation", value.checkpoint_generation),
            ("trigger_timer_occurrence_ids", value.trigger_timer_occurrence_ids),
        )
    if isinstance(value, AgendaItem):
        return (
            ("namespace", value.namespace),
            ("agenda_item_id", value.agenda_item_id),
            ("wake_cycle_id", value.wake_cycle_id),
            ("source_event_id", value.source_event_id),
            ("work_id", value.work_id),
            ("title", value.title),
            ("state", value.state),
            ("priority", value.priority),
            ("due_at", value.due_at),
            ("actor", value.actor),
            ("correlation_id", value.correlation_id),
            ("causation_id", value.causation_id),
            ("occurred_at", value.occurred_at),
            ("revision", value.revision),
            ("schema_version", value.schema_version),
            ("generation", value.generation),
            ("handled_generation", value.handled_generation),
            ("cause_ids", value.cause_ids),
            ("source_timer_occurrence_id", value.source_timer_occurrence_id),
        )
    if isinstance(value, Decision):
        return (
            ("namespace", value.namespace),
            ("decision_id", value.decision_id),
            ("wake_cycle_id", value.wake_cycle_id),
            ("agenda_item_id", value.agenda_item_id),
            ("kind", value.kind),
            ("rationale", value.rationale),
            ("proposed_effect_id", value.proposed_effect_id),
            ("actor", value.actor),
            ("correlation_id", value.correlation_id),
            ("causation_id", value.causation_id),
            ("occurred_at", value.occurred_at),
            ("revision", value.revision),
            ("schema_version", value.schema_version),
        )
    if isinstance(value, CompletionEvidence):
        return (
            ("evidence_id", value.evidence_id),
            ("kind", value.kind),
            ("safe_summary", value.safe_summary),
            ("observed_at", value.observed_at),
            ("actor", value.actor),
            ("schema_version", value.schema_version),
        )
    if isinstance(value, FiniteWork):
        return (
            ("namespace", value.namespace),
            ("work_id", value.work_id),
            ("title", value.title),
            ("description", value.description),
            ("state", value.state),
            ("dependency_ids", value.dependency_ids),
            ("responsibility_ids", value.responsibility_ids),
            ("assignee_principal_id", value.assignee_principal_id),
            ("actor", value.actor),
            ("mandate_id", value.mandate_id),
            ("mandate_revision", value.mandate_revision),
            ("completion_evidence", value.completion_evidence),
            ("correlation_id", value.correlation_id),
            ("causation_id", value.causation_id),
            ("created_at", value.created_at),
            ("updated_at", value.updated_at),
            ("revision", value.revision),
            ("schema_version", value.schema_version),
        )
    if isinstance(value, Responsibility):
        return (
            ("namespace", value.namespace),
            ("responsibility_id", value.responsibility_id),
            ("mandate_id", value.mandate_id),
            ("mandate_revision", value.mandate_revision),
            ("description", value.description),
            ("owner_principal_id", value.owner_principal_id),
            ("state", value.state),
            ("actor", value.actor),
            ("correlation_id", value.correlation_id),
            ("causation_id", value.causation_id),
            ("created_at", value.created_at),
            ("updated_at", value.updated_at),
            ("revision", value.revision),
            ("schema_version", value.schema_version),
        )
    if isinstance(value, Obligation):
        return (
            ("namespace", value.namespace),
            ("obligation_id", value.obligation_id),
            ("responsibility_id", value.responsibility_id),
            ("description", value.description),
            ("state", value.state),
            ("due_at", value.due_at),
            ("work_id", value.work_id),
            ("resolution_evidence", value.resolution_evidence),
            ("actor", value.actor),
            ("correlation_id", value.correlation_id),
            ("causation_id", value.causation_id),
            ("created_at", value.created_at),
            ("updated_at", value.updated_at),
            ("revision", value.revision),
            ("schema_version", value.schema_version),
        )
    return None


def contract_to_public_data(value: object) -> object:
    """Convert a contract to safe JSON data without exposing effect payload bytes."""

    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, datetime):
        return datetime_to_z(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, FrozenJsonObject):
        return {key: contract_to_public_data(item) for key, item in value.as_entries()}
    if isinstance(value, tuple):
        return [contract_to_public_data(item) for item in value]
    if isinstance(value, frozenset):
        return sorted(contract_to_public_data(item) for item in value)  # type: ignore[type-var]
    contract_items = _contract_items(value)
    if contract_items is not None:
        return {
            field_name: contract_to_public_data(field_value)
            for field_name, field_value in contract_items
        }
    raise CoreInvariantError("unsupported public contract value")


def to_canonical_json(value: object) -> str:
    return json.dumps(
        contract_to_public_data(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
