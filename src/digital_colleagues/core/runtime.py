# SPDX-License-Identifier: Apache-2.0

"""Pure event, agenda, wake-cycle, and decision contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from digital_colleagues.core.common import (
    SCHEMA_VERSION,
    FrozenJsonObject,
    freeze_strings,
    require_digest,
    require_revision,
    require_schema_version,
    require_stable_id,
    require_text,
    require_utc,
)
from digital_colleagues.core.errors import CoreInvariantError, NamespaceMismatchError
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import Principal


def _validate_causal_record(
    *,
    namespace: Namespace,
    actor: Principal,
    correlation_id: str,
    causation_id: str | None,
    occurred_at: datetime,
    revision: int,
    schema_version: int,
) -> None:
    require_schema_version(schema_version)
    namespace.require_colleague()
    namespace.require_same_tenant(actor.namespace)
    require_stable_id(correlation_id, "correlation_id")
    if causation_id is not None:
        require_stable_id(causation_id, "causation_id")
    require_utc(occurred_at, "occurred_at")
    require_revision(revision)


def _validate_policy_binding(policy_id: str | None, policy_revision: int | None) -> None:
    if (policy_id is None) != (policy_revision is None):
        raise CoreInvariantError("runtime policy identity must be complete")
    if policy_id is not None:
        require_stable_id(policy_id, "policy_id")
        assert policy_revision is not None
        require_revision(policy_revision, "policy_revision")


class InputEventState(StrEnum):
    RECEIVED = "received"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class InputEvent:
    namespace: Namespace
    event_id: str
    event_type: str
    state: InputEventState
    safe_projection: FrozenJsonObject
    payload_digest: str
    actor: Principal
    correlation_id: str
    causation_id: str | None
    occurred_at: datetime
    revision: int
    schema_version: int = SCHEMA_VERSION
    policy_id: str | None = None
    policy_revision: int | None = None

    def __post_init__(self) -> None:
        require_stable_id(self.event_id, "event_id")
        object.__setattr__(self, "event_type", require_stable_id(self.event_type, "event_type"))
        if not isinstance(self.state, InputEventState):
            raise CoreInvariantError("input event state must be explicit")
        if not isinstance(self.safe_projection, FrozenJsonObject):
            raise CoreInvariantError("event safe_projection must be immutable")
        require_digest(self.payload_digest, "payload_digest")
        _validate_causal_record(
            namespace=self.namespace,
            actor=self.actor,
            correlation_id=self.correlation_id,
            causation_id=self.causation_id,
            occurred_at=self.occurred_at,
            revision=self.revision,
            schema_version=self.schema_version,
        )
        _validate_policy_binding(self.policy_id, self.policy_revision)


class TimerOccurrenceState(StrEnum):
    SCHEDULED = "scheduled"
    DUE = "due"


@dataclass(frozen=True, slots=True)
class TimerOccurrence:
    """One durable scheduled occurrence, distinct from an inbound InputEvent."""

    namespace: Namespace
    timer_id: str
    occurrence_id: str
    state: TimerOccurrenceState
    due_at: datetime
    safe_projection: FrozenJsonObject
    actor: Principal
    correlation_id: str
    causation_id: str | None
    occurred_at: datetime
    revision: int
    schema_version: int = SCHEMA_VERSION
    policy_id: str | None = None
    policy_revision: int | None = None

    def __post_init__(self) -> None:
        require_stable_id(self.timer_id, "timer_id")
        require_stable_id(self.occurrence_id, "occurrence_id")
        if not isinstance(self.state, TimerOccurrenceState):
            raise CoreInvariantError("timer occurrence state must be explicit")
        require_utc(self.due_at, "due_at")
        if not isinstance(self.safe_projection, FrozenJsonObject):
            raise CoreInvariantError("timer safe_projection must be immutable")
        _validate_causal_record(
            namespace=self.namespace,
            actor=self.actor,
            correlation_id=self.correlation_id,
            causation_id=self.causation_id,
            occurred_at=self.occurred_at,
            revision=self.revision,
            schema_version=self.schema_version,
        )
        _validate_policy_binding(self.policy_id, self.policy_revision)


class WakeCycleState(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class WakeCycle:
    namespace: Namespace
    wake_cycle_id: str
    state: WakeCycleState
    trigger_event_ids: tuple[str, ...]
    agenda_item_ids: tuple[str, ...]
    actor: Principal
    correlation_id: str
    causation_id: str | None
    occurred_at: datetime
    revision: int
    schema_version: int = SCHEMA_VERSION
    fencing_token: int = 1
    checkpoint_generation: int = 1
    trigger_timer_occurrence_ids: tuple[str, ...] = ()
    policy_id: str | None = None
    policy_revision: int | None = None

    def __post_init__(self) -> None:
        require_stable_id(self.wake_cycle_id, "wake_cycle_id")
        if not isinstance(self.state, WakeCycleState):
            raise CoreInvariantError("wake cycle state must be explicit")
        trigger_ids = freeze_strings(self.trigger_event_ids, "trigger_event_ids")
        timer_ids = freeze_strings(
            self.trigger_timer_occurrence_ids,
            "trigger_timer_occurrence_ids",
        )
        if not trigger_ids and not timer_ids:
            raise CoreInvariantError("wake cycle requires an event or timer occurrence")
        agenda_ids = freeze_strings(self.agenda_item_ids, "agenda_item_ids")
        for identifier in (*trigger_ids, *timer_ids, *agenda_ids):
            require_stable_id(identifier, "causal record ID")
        object.__setattr__(self, "trigger_event_ids", trigger_ids)
        object.__setattr__(self, "trigger_timer_occurrence_ids", timer_ids)
        object.__setattr__(self, "agenda_item_ids", agenda_ids)
        _validate_causal_record(
            namespace=self.namespace,
            actor=self.actor,
            correlation_id=self.correlation_id,
            causation_id=self.causation_id,
            occurred_at=self.occurred_at,
            revision=self.revision,
            schema_version=self.schema_version,
        )
        if self.causation_id not in (*trigger_ids, *timer_ids):
            raise CoreInvariantError("wake cycle causation must name one trigger source")
        require_revision(self.fencing_token, "fencing_token")
        require_revision(self.checkpoint_generation, "checkpoint_generation")
        _validate_policy_binding(self.policy_id, self.policy_revision)


class AgendaItemState(StrEnum):
    PENDING = "pending"
    SELECTED = "selected"
    COMPLETED = "completed"
    DEFERRED = "deferred"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class AgendaItem:
    namespace: Namespace
    agenda_item_id: str
    wake_cycle_id: str
    source_event_id: str | None
    work_id: str | None
    title: str
    state: AgendaItemState
    priority: int
    due_at: datetime | None
    actor: Principal
    correlation_id: str
    causation_id: str
    occurred_at: datetime
    revision: int
    schema_version: int = SCHEMA_VERSION
    generation: int = 1
    handled_generation: int = 0
    cause_ids: tuple[str, ...] = ()
    source_timer_occurrence_id: str | None = None
    policy_id: str | None = None
    policy_revision: int | None = None

    def __post_init__(self) -> None:
        require_stable_id(self.agenda_item_id, "agenda_item_id")
        require_stable_id(self.wake_cycle_id, "wake_cycle_id")
        if (self.source_event_id is None) == (self.source_timer_occurrence_id is None):
            raise CoreInvariantError("Agenda must name exactly one event or timer source")
        if self.source_event_id is not None:
            require_stable_id(self.source_event_id, "source_event_id")
        if self.source_timer_occurrence_id is not None:
            require_stable_id(
                self.source_timer_occurrence_id,
                "source_timer_occurrence_id",
            )
        if self.work_id is not None:
            require_stable_id(self.work_id, "work_id")
        object.__setattr__(self, "title", require_text(self.title, "title"))
        if not isinstance(self.state, AgendaItemState):
            raise CoreInvariantError("agenda item state must be explicit")
        if type(self.priority) is not int or not 0 <= self.priority <= 1_000:
            raise CoreInvariantError("agenda priority must be an integer from 0 through 1000")
        if self.due_at is not None:
            require_utc(self.due_at, "due_at")
        _validate_causal_record(
            namespace=self.namespace,
            actor=self.actor,
            correlation_id=self.correlation_id,
            causation_id=self.causation_id,
            occurred_at=self.occurred_at,
            revision=self.revision,
            schema_version=self.schema_version,
        )
        if self.causation_id != self.wake_cycle_id:
            raise CoreInvariantError("agenda item causation must name its wake cycle")
        require_revision(self.generation, "generation")
        if (
            type(self.handled_generation) is not int
            or not 0 <= self.handled_generation <= self.generation
        ):
            raise CoreInvariantError("handled_generation must be within the Agenda generation")
        source_id = self.source_event_id or self.source_timer_occurrence_id
        assert source_id is not None
        causes = self.cause_ids or (source_id,)
        causes = freeze_strings(causes, "cause_ids", allow_empty=False)
        for cause_id in causes:
            require_stable_id(cause_id, "cause_id")
        if source_id not in causes:
            raise CoreInvariantError("Agenda causes must retain the trigger source")
        object.__setattr__(self, "cause_ids", causes)
        _validate_policy_binding(self.policy_id, self.policy_revision)


def agenda_order_key(item: AgendaItem) -> tuple[int, int, str, str]:
    """Return deterministic priority inputs without reading the clock."""

    due_rank = 0 if item.due_at is not None else 1
    due_value = item.due_at.isoformat() if item.due_at is not None else ""
    return (-item.priority, due_rank, due_value, item.agenda_item_id)


class DecisionKind(StrEnum):
    PROPOSE_EFFECT = "propose_effect"
    COMPLETE_ITEM = "complete_item"
    DEFER_ITEM = "defer_item"
    NO_ACTION = "no_action"


@dataclass(frozen=True, slots=True)
class Decision:
    namespace: Namespace
    decision_id: str
    wake_cycle_id: str
    agenda_item_id: str
    kind: DecisionKind
    rationale: str
    proposed_effect_id: str | None
    actor: Principal
    correlation_id: str
    causation_id: str
    occurred_at: datetime
    revision: int
    schema_version: int = SCHEMA_VERSION
    policy_id: str | None = None
    policy_revision: int | None = None

    def __post_init__(self) -> None:
        require_stable_id(self.decision_id, "decision_id")
        require_stable_id(self.wake_cycle_id, "wake_cycle_id")
        require_stable_id(self.agenda_item_id, "agenda_item_id")
        if not isinstance(self.kind, DecisionKind):
            raise CoreInvariantError("decision kind must be explicit")
        object.__setattr__(
            self,
            "rationale",
            require_text(self.rationale, "rationale", maximum=2_048),
        )
        if self.proposed_effect_id is not None:
            require_stable_id(self.proposed_effect_id, "proposed_effect_id")
        if (self.kind is DecisionKind.PROPOSE_EFFECT) != (self.proposed_effect_id is not None):
            raise CoreInvariantError("effect decision must name exactly one proposed effect")
        _validate_causal_record(
            namespace=self.namespace,
            actor=self.actor,
            correlation_id=self.correlation_id,
            causation_id=self.causation_id,
            occurred_at=self.occurred_at,
            revision=self.revision,
            schema_version=self.schema_version,
        )
        if self.causation_id != self.agenda_item_id:
            raise CoreInvariantError("decision causation must name its agenda item")
        _validate_policy_binding(self.policy_id, self.policy_revision)


def validate_event_wake_agenda_chain(
    event: InputEvent, wake_cycle: WakeCycle, agenda_item: AgendaItem
) -> None:
    """Fail closed unless the records form one namespaced causal chain."""

    event.namespace.require_exact(wake_cycle.namespace)
    event.namespace.require_exact(agenda_item.namespace)
    if len({event.correlation_id, wake_cycle.correlation_id, agenda_item.correlation_id}) != 1:
        raise NamespaceMismatchError("causal chain correlation mismatch")
    if wake_cycle.causation_id != event.event_id:
        raise CoreInvariantError("wake cycle does not cite the input event")
    if agenda_item.wake_cycle_id != wake_cycle.wake_cycle_id:
        raise CoreInvariantError("agenda item does not cite the wake cycle")
    if agenda_item.source_event_id != event.event_id:
        raise CoreInvariantError("agenda item does not cite the input event")
