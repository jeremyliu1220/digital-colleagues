# SPDX-License-Identifier: Apache-2.0

"""Framework-neutral application values shared by stable ports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from digital_colleagues.core.authority import Mandate
from digital_colleagues.core.common import (
    SCHEMA_VERSION,
    FrozenJsonObject,
    require_digest,
    require_revision,
    require_schema_version,
    require_stable_id,
    require_utc,
)
from digital_colleagues.core.effects import EffectAttempt, EffectProposal, HumanApprovalDecision
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import Principal
from digital_colleagues.core.runtime import AgendaItem, Decision, WakeCycle


@dataclass(frozen=True, slots=True)
class RequestPrincipalContext:
    """Authority supplied by the server-side request boundary, never a mutation body."""

    namespace: Namespace
    principal: Principal
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.namespace.require_colleague()
        self.namespace.require_same_tenant(self.principal.namespace)


@dataclass(frozen=True, slots=True)
class TriggerClaim:
    namespace: Namespace
    trigger_id: str
    event_id: str
    trigger_kind: str
    lease_owner: str
    lease_until: datetime
    fencing_token: int
    correlation_id: str
    causation_id: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.namespace.require_colleague()
        for value, field in (
            (self.trigger_id, "trigger_id"),
            (self.event_id, "event_id"),
            (self.trigger_kind, "trigger_kind"),
            (self.lease_owner, "lease_owner"),
            (self.correlation_id, "correlation_id"),
            (self.causation_id, "causation_id"),
        ):
            require_stable_id(value, field)
        require_utc(self.lease_until, "lease_until")
        require_revision(self.fencing_token, "fencing_token")


@dataclass(frozen=True, slots=True)
class AgendaClaim:
    namespace: Namespace
    agenda_item: AgendaItem
    lease_owner: str
    lease_until: datetime
    fencing_token: int
    claimed_generation: int
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.namespace.require_exact(self.agenda_item.namespace)
        require_stable_id(self.lease_owner, "lease_owner")
        require_utc(self.lease_until, "lease_until")
        require_revision(self.fencing_token, "fencing_token")
        require_revision(self.claimed_generation, "claimed_generation")


class SemanticOutcome(StrEnum):
    PROPOSAL = "proposal"
    NO_OP = "no_op"
    WAIT = "wait"
    ESCALATION = "escalation"


@dataclass(frozen=True, slots=True)
class IntelligenceRequest:
    namespace: Namespace
    request_id: str
    wake_cycle: WakeCycle
    agenda_item: AgendaItem
    mandate: Mandate
    model_principal: Principal
    decision_id: str
    proposal_id: str
    effect_idempotency_key: str
    occurred_at: datetime
    proposal_valid_until: datetime
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.namespace.require_exact(self.wake_cycle.namespace)
        self.namespace.require_exact(self.agenda_item.namespace)
        self.namespace.require_exact(self.mandate.namespace)
        self.namespace.require_same_tenant(self.model_principal.namespace)
        for value, field in (
            (self.request_id, "request_id"),
            (self.decision_id, "decision_id"),
            (self.proposal_id, "proposal_id"),
            (self.effect_idempotency_key, "effect_idempotency_key"),
        ):
            require_stable_id(value, field)
        require_utc(self.occurred_at, "occurred_at")
        require_utc(self.proposal_valid_until, "proposal_valid_until")
        if self.proposal_valid_until <= self.occurred_at:
            raise ValueError("proposal validity must follow request time")


@dataclass(frozen=True, slots=True)
class SemanticDecision:
    outcome: SemanticOutcome
    decision: Decision
    proposal: EffectProposal | None
    request_id: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        require_stable_id(self.request_id, "request_id")
        if (self.outcome is SemanticOutcome.PROPOSAL) != (self.proposal is not None):
            raise ValueError("proposal outcomes must carry exactly one proposal")
        if self.proposal is not None:
            self.decision.namespace.require_exact(self.proposal.namespace)


class ChannelOutcomeKind(StrEnum):
    SUCCEEDED = "succeeded"
    KNOWN_NOT_EXECUTED = "known_not_executed"
    RETRYABLE_FAILURE = "retryable_failure"
    PERMANENT_FAILURE = "permanent_failure"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class ChannelOutcome:
    kind: ChannelOutcomeKind
    safe_projection: FrozenJsonObject
    result_digest: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        if not isinstance(self.kind, ChannelOutcomeKind):
            raise ValueError("channel outcome kind must be explicit")
        if not isinstance(self.safe_projection, FrozenJsonObject):
            raise ValueError("channel outcome projection must be immutable")
        require_digest(self.result_digest, "result_digest")


class ReconciliationKind(StrEnum):
    CONFIRMED_APPLIED = "confirmed_applied"
    CONFIRMED_ABSENT = "confirmed_absent"
    STILL_UNKNOWN = "still_unknown"


@dataclass(frozen=True, slots=True)
class ReconciliationOutcome:
    kind: ReconciliationKind
    safe_projection: FrozenJsonObject
    result_digest: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        if not isinstance(self.kind, ReconciliationKind):
            raise ValueError("reconciliation kind must be explicit")
        if not isinstance(self.safe_projection, FrozenJsonObject):
            raise ValueError("reconciliation projection must be immutable")
        require_digest(self.result_digest, "result_digest")


@dataclass(frozen=True, slots=True)
class OutboxClaim:
    namespace: Namespace
    outbox_id: str
    proposal_id: str
    approval_decision_id: str
    effect_attempt_id: str
    effect_idempotency_key: str
    attempt_number: int
    lease_owner: str
    lease_until: datetime
    fencing_token: int
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.namespace.require_colleague()
        for value, field in (
            (self.outbox_id, "outbox_id"),
            (self.proposal_id, "proposal_id"),
            (self.approval_decision_id, "approval_decision_id"),
            (self.effect_attempt_id, "effect_attempt_id"),
            (self.effect_idempotency_key, "effect_idempotency_key"),
            (self.lease_owner, "lease_owner"),
        ):
            require_stable_id(value, field)
        require_revision(self.attempt_number, "attempt_number")
        require_utc(self.lease_until, "lease_until")
        require_revision(self.fencing_token, "fencing_token")


@dataclass(frozen=True, slots=True)
class DispatchBundle:
    proposal: EffectProposal
    approval: HumanApprovalDecision
    attempt: EffectAttempt
    approver: Principal
    effect_idempotency_key: str
    maximum_attempts: int
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.proposal.namespace.require_exact(self.approval.namespace)
        self.proposal.namespace.require_exact(self.attempt.namespace)
        self.proposal.namespace.require_same_tenant(self.approver.namespace)
        require_stable_id(self.effect_idempotency_key, "effect_idempotency_key")
        require_revision(self.maximum_attempts, "maximum_attempts")


@dataclass(frozen=True, slots=True)
class ChannelEffect:
    proposal: EffectProposal
    attempt: EffectAttempt
    effect_idempotency_key: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.proposal.namespace.require_exact(self.attempt.namespace)
        require_stable_id(self.effect_idempotency_key, "effect_idempotency_key")


@dataclass(frozen=True, slots=True)
class WakeRunResult:
    selected_count: int
    decision_count: int
    pending_count: int
    outcome: str
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class DispatchResult:
    dispatched: bool
    outcome: ChannelOutcomeKind | None
    action_result_id: str | None
    schema_version: int = SCHEMA_VERSION
