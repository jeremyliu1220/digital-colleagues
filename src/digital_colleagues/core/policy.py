# SPDX-License-Identifier: Apache-2.0

"""Typed, revisioned colleague policy values for the deterministic P5 runtime."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from digital_colleagues.core.common import (
    SCHEMA_VERSION,
    FrozenJsonObject,
    require_digest,
    require_revision,
    require_schema_version,
    require_stable_id,
    require_utc,
)
from digital_colleagues.core.errors import AuthorizationError, CoreInvariantError
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import Principal, PrincipalKind


class Weekday(StrEnum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


WEEKDAY_INDEX: dict[Weekday, int] = {
    Weekday.MONDAY: 0,
    Weekday.TUESDAY: 1,
    Weekday.WEDNESDAY: 2,
    Weekday.THURSDAY: 3,
    Weekday.FRIDAY: 4,
    Weekday.SATURDAY: 5,
    Weekday.SUNDAY: 6,
}


class DurableTriggerKind(StrEnum):
    EVENT = "event"
    TIMER = "timer"


class ProactivityMode(StrEnum):
    DISABLED = "disabled"
    BOUNDED = "bounded"


class NotificationMode(StrEnum):
    ENABLED = "enabled"
    SUPPRESSED = "suppressed"


class InterruptionMode(StrEnum):
    NEVER = "never"
    WORKING_HOURS_ONLY = "working_hours_only"
    ALLOWED = "allowed"


class WakeBudgetPeriod(StrEnum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"


class OutsideHoursOutcome(StrEnum):
    DEFER = "defer"
    NO_OP = "no_op"
    STOP = "stop"
    ESCALATE = "escalate"


class StopCondition(StrEnum):
    ADMIN_STOP = "admin_stop"
    BUDGET_EXHAUSTED = "budget_exhausted"
    REPEATED_FAILURE = "repeated_failure"
    FINITE_WORK_TERMINAL = "finite_work_terminal"


class EscalationCondition(StrEnum):
    OUTSIDE_HOURS = "outside_hours"
    BUDGET_EXHAUSTED = "budget_exhausted"
    REPEATED_FAILURE = "repeated_failure"
    BLOCKED_WORK = "blocked_work"


class PolicyRunState(StrEnum):
    ACTIVE = "active"
    STOPPED = "stopped"


class PolicyStatus(StrEnum):
    CONFIRMED = "confirmed"
    LEGACY_UNCONFIRMED = "legacy_unconfirmed"


class PolicyStage(StrEnum):
    TRIGGER = "trigger"
    PRE_WAKE = "pre_wake"
    POST_MODEL = "post_model"
    APPROVAL = "approval"
    DISPATCH = "dispatch"
    STOP = "stop"
    ESCALATION = "escalation"


class PolicyOutcomeKind(StrEnum):
    ALLOWED = "allowed"
    STALE_POLICY = "stale_policy"
    DISALLOWED_TRIGGER = "disallowed_trigger"
    OUTSIDE_HOURS_DEFER = "outside_hours_defer"
    OUTSIDE_HOURS_NO_OP = "outside_hours_no_op"
    OUTSIDE_HOURS_STOP = "outside_hours_stop"
    OUTSIDE_HOURS_ESCALATE = "outside_hours_escalate"
    PROACTIVITY_SUPPRESSED = "proactivity_suppressed"
    NOTIFICATION_SUPPRESSED = "notification_suppressed"
    INTERRUPTION_SUPPRESSED = "interruption_suppressed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    DUPLICATE_TRIGGER = "duplicate_trigger"
    REPEATED_FAILURE_STOP = "repeated_failure_stop"
    REPEATED_FAILURE_ESCALATE = "repeated_failure_escalate"
    FINITE_WORK_TERMINAL_STOP = "finite_work_terminal_stop"
    BLOCKED_WORK_ESCALATE = "blocked_work_escalate"
    STOPPED = "stopped"
    EXPLICIT_RESUME = "explicit_resume"


POLICY_REFUSAL_OUTCOMES: frozenset[PolicyOutcomeKind] = frozenset(
    {
        PolicyOutcomeKind.STALE_POLICY,
        PolicyOutcomeKind.DISALLOWED_TRIGGER,
        PolicyOutcomeKind.OUTSIDE_HOURS_DEFER,
        PolicyOutcomeKind.OUTSIDE_HOURS_NO_OP,
        PolicyOutcomeKind.OUTSIDE_HOURS_STOP,
        PolicyOutcomeKind.OUTSIDE_HOURS_ESCALATE,
        PolicyOutcomeKind.PROACTIVITY_SUPPRESSED,
        PolicyOutcomeKind.NOTIFICATION_SUPPRESSED,
        PolicyOutcomeKind.INTERRUPTION_SUPPRESSED,
        PolicyOutcomeKind.BUDGET_EXHAUSTED,
        PolicyOutcomeKind.DUPLICATE_TRIGGER,
        PolicyOutcomeKind.REPEATED_FAILURE_STOP,
        PolicyOutcomeKind.REPEATED_FAILURE_ESCALATE,
        PolicyOutcomeKind.FINITE_WORK_TERMINAL_STOP,
        PolicyOutcomeKind.BLOCKED_WORK_ESCALATE,
        PolicyOutcomeKind.STOPPED,
    }
)


@dataclass(frozen=True, slots=True)
class WeeklyWindow:
    """One local-wall-clock window, attributed to its starting weekday."""

    weekday: Weekday
    start_minute: int
    end_minute: int

    def __post_init__(self) -> None:
        if not isinstance(self.weekday, Weekday):
            raise CoreInvariantError("working-hours weekday must be explicit")
        if type(self.start_minute) is not int or not 0 <= self.start_minute < 1_440:
            raise CoreInvariantError("working-hours start minute must be from 0 through 1439")
        if type(self.end_minute) is not int or not 0 <= self.end_minute <= 1_440:
            raise CoreInvariantError("working-hours end minute must be from 0 through 1440")
        if self.start_minute == self.end_minute:
            raise CoreInvariantError("working-hours window must not have zero duration")
        if self.end_minute == 0:
            raise CoreInvariantError("working-hours end minute 0 is ambiguous")


@dataclass(frozen=True, slots=True)
class WakeBudget:
    limit: int
    period: WakeBudgetPeriod

    def __post_init__(self) -> None:
        if type(self.limit) is not int or not 1 <= self.limit <= 10_000:
            raise CoreInvariantError("wake-budget limit must be from 1 through 10000")
        if not isinstance(self.period, WakeBudgetPeriod):
            raise CoreInvariantError("wake-budget period must be explicit")


def _expanded_intervals(window: WeeklyWindow) -> tuple[tuple[int, int, int], ...]:
    day = WEEKDAY_INDEX[window.weekday]
    if window.end_minute > window.start_minute:
        return ((day, window.start_minute, window.end_minute),)
    return (
        (day, window.start_minute, 1_440),
        ((day + 1) % 7, 0, window.end_minute),
    )


def _validate_windows(windows: tuple[WeeklyWindow, ...]) -> None:
    if not windows:
        raise CoreInvariantError("working-hours windows must not be empty")
    if not all(isinstance(item, WeeklyWindow) for item in windows):
        raise CoreInvariantError("working-hours windows contain an invalid value")
    intervals = sorted(interval for window in windows for interval in _expanded_intervals(window))
    for previous, current in zip(intervals, intervals[1:], strict=False):
        if previous[0] == current[0] and current[1] < previous[2]:
            raise CoreInvariantError("working-hours windows must not overlap")


def _freeze_unique_enums[T: StrEnum](
    values: object, expected: type[T], field: str, *, allow_empty: bool = False
) -> tuple[T, ...]:
    if isinstance(values, (str, bytes)):
        raise CoreInvariantError(f"{field} must be a typed collection")
    if not isinstance(values, tuple):
        raise CoreInvariantError(f"{field} must be a typed immutable collection")
    items: tuple[object, ...] = values
    if not allow_empty and not items:
        raise CoreInvariantError(f"{field} must not be empty")
    if not all(isinstance(item, expected) for item in items):
        raise CoreInvariantError(f"{field} contains an invalid value")
    if len(items) != len(set(items)):
        raise CoreInvariantError(f"{field} must not contain duplicates")
    return cast(tuple[T, ...], items)


@dataclass(frozen=True, slots=True)
class ColleaguePolicy:
    """Authoritative runtime policy; it cannot grant effects absent from its Mandate."""

    namespace: Namespace
    policy_id: str
    mandate_id: str
    mandate_revision: int
    timezone: str
    weekly_windows: tuple[WeeklyWindow, ...]
    allowed_triggers: tuple[DurableTriggerKind, ...]
    proactivity: ProactivityMode
    notification: NotificationMode
    interruption: InterruptionMode
    wake_budget: WakeBudget
    outside_hours: OutsideHoursOutcome
    stop_conditions: tuple[StopCondition, ...]
    escalation_conditions: tuple[EscalationCondition, ...]
    failure_limit: int
    run_state: PolicyRunState
    revision: int
    issued_by: Principal
    effective_at: datetime
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.namespace.require_colleague()
        require_stable_id(self.policy_id, "policy_id")
        require_stable_id(self.mandate_id, "mandate_id")
        require_revision(self.mandate_revision, "mandate_revision")
        if (
            not isinstance(self.timezone, str)
            or not self.timezone
            or self.timezone.strip() != self.timezone
        ):
            raise CoreInvariantError("policy timezone must be a non-empty canonical string")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise CoreInvariantError("policy timezone must be a known IANA timezone") from exc
        windows = tuple(self.weekly_windows)
        _validate_windows(windows)
        object.__setattr__(self, "weekly_windows", windows)
        object.__setattr__(
            self,
            "allowed_triggers",
            _freeze_unique_enums(
                self.allowed_triggers,
                DurableTriggerKind,
                "allowed_triggers",
            ),
        )
        if not isinstance(self.proactivity, ProactivityMode):
            raise CoreInvariantError("proactivity mode must be explicit")
        if not isinstance(self.notification, NotificationMode):
            raise CoreInvariantError("notification mode must be explicit")
        if not isinstance(self.interruption, InterruptionMode):
            raise CoreInvariantError("interruption mode must be explicit")
        if not isinstance(self.wake_budget, WakeBudget):
            raise CoreInvariantError("wake budget must be typed")
        if not isinstance(self.outside_hours, OutsideHoursOutcome):
            raise CoreInvariantError("outside-hours outcome must be explicit")
        object.__setattr__(
            self,
            "stop_conditions",
            _freeze_unique_enums(
                self.stop_conditions,
                StopCondition,
                "stop_conditions",
                allow_empty=True,
            ),
        )
        object.__setattr__(
            self,
            "escalation_conditions",
            _freeze_unique_enums(
                self.escalation_conditions,
                EscalationCondition,
                "escalation_conditions",
                allow_empty=True,
            ),
        )
        if type(self.failure_limit) is not int or not 1 <= self.failure_limit <= 100:
            raise CoreInvariantError("failure limit must be from 1 through 100")
        if not isinstance(self.run_state, PolicyRunState):
            raise CoreInvariantError("policy run state must be explicit")
        require_revision(self.revision)
        if self.issued_by.kind is not PrincipalKind.HUMAN:
            raise AuthorizationError("authoritative colleague policy must be issued by a human")
        self.namespace.require_same_tenant(self.issued_by.namespace)
        require_utc(self.effective_at, "effective_at")


@dataclass(frozen=True, slots=True)
class PolicyEnforcementRecord:
    namespace: Namespace
    outcome_id: str
    policy_id: str
    policy_revision: int
    mandate_id: str
    mandate_revision: int
    stage: PolicyStage
    outcome: PolicyOutcomeKind
    trigger_class: DurableTriggerKind | None
    source_id: str | None
    actor: Principal
    correlation_id: str
    causation_id: str
    occurred_at: datetime
    safe_projection: FrozenJsonObject
    payload_digest: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.namespace.require_colleague()
        for value, field in (
            (self.outcome_id, "outcome_id"),
            (self.policy_id, "policy_id"),
            (self.mandate_id, "mandate_id"),
            (self.correlation_id, "correlation_id"),
            (self.causation_id, "causation_id"),
        ):
            require_stable_id(value, field)
        require_revision(self.policy_revision, "policy_revision")
        require_revision(self.mandate_revision, "mandate_revision")
        if not isinstance(self.stage, PolicyStage):
            raise CoreInvariantError("policy stage must be explicit")
        if not isinstance(self.outcome, PolicyOutcomeKind):
            raise CoreInvariantError("policy outcome must be explicit")
        if self.trigger_class is not None and not isinstance(
            self.trigger_class, DurableTriggerKind
        ):
            raise CoreInvariantError("policy trigger class must be explicit")
        if self.source_id is not None:
            require_stable_id(self.source_id, "source_id")
        self.namespace.require_same_tenant(self.actor.namespace)
        require_utc(self.occurred_at, "occurred_at")
        if not isinstance(self.safe_projection, FrozenJsonObject):
            raise CoreInvariantError("policy safe projection must be immutable JSON")
        require_digest(self.payload_digest, "payload_digest")


@dataclass(frozen=True, slots=True)
class EscalationRecord:
    namespace: Namespace
    escalation_id: str
    policy_id: str
    policy_revision: int
    condition: EscalationCondition
    safe_summary: str
    actor: Principal
    correlation_id: str
    causation_id: str
    occurred_at: datetime
    revision: int = 1
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.namespace.require_colleague()
        for value, field in (
            (self.escalation_id, "escalation_id"),
            (self.policy_id, "policy_id"),
            (self.correlation_id, "correlation_id"),
            (self.causation_id, "causation_id"),
        ):
            require_stable_id(value, field)
        require_revision(self.policy_revision, "policy_revision")
        if not isinstance(self.condition, EscalationCondition):
            raise CoreInvariantError("escalation condition must be explicit")
        if not isinstance(self.safe_summary, str) or not self.safe_summary.strip():
            raise CoreInvariantError("escalation summary must be non-empty")
        self.namespace.require_same_tenant(self.actor.namespace)
        require_utc(self.occurred_at, "occurred_at")
        require_revision(self.revision)
