# SPDX-License-Identifier: Apache-2.0

"""Framework-neutral P4 authentication, Studio, and evaluation values."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from digital_colleagues.core.authority import Mandate, Profile
from digital_colleagues.core.common import (
    SCHEMA_VERSION,
    FrozenJsonObject,
    require_digest,
    require_schema_version,
    require_stable_id,
    require_text,
    require_utc,
)
from digital_colleagues.core.effects import (
    ActionResult,
    EffectAttempt,
    EffectProposal,
    HumanApprovalDecision,
)
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import Principal
from digital_colleagues.core.runtime import (
    AgendaItem,
    Decision,
    InputEvent,
    TimerOccurrence,
    WakeCycle,
)
from digital_colleagues.core.work import FiniteWork


@dataclass(frozen=True, slots=True)
class BootstrapRecord:
    tenant_id: str
    credential_id: str
    token_digest: str
    issued_at: datetime
    expires_at: datetime
    retrieved_at: datetime | None
    consumed_at: datetime | None
    revision: int
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        require_stable_id(self.tenant_id, "tenant_id")
        require_stable_id(self.credential_id, "credential_id")
        require_digest(self.token_digest, "token_digest")
        require_utc(self.issued_at, "issued_at")
        require_utc(self.expires_at, "expires_at")
        if self.expires_at <= self.issued_at:
            raise ValueError("bootstrap expiry must follow issue time")
        if self.retrieved_at is not None:
            require_utc(self.retrieved_at, "retrieved_at")
        if self.consumed_at is not None:
            require_utc(self.consumed_at, "consumed_at")
            if self.retrieved_at is None:
                raise ValueError("bootstrap exchange requires prior local retrieval")


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    tenant_id: str
    session_id: str
    principal: Principal
    credential_digest: str = field(repr=False)
    csrf_digest: str = field(repr=False)
    active_colleague_id: str | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None
    revision: int = 1
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        require_stable_id(self.tenant_id, "tenant_id")
        require_stable_id(self.session_id, "session_id")
        require_digest(self.credential_digest, "credential_digest")
        require_digest(self.csrf_digest, "csrf_digest")
        if self.principal.namespace.tenant_id != self.tenant_id:
            raise ValueError("session principal crosses tenant namespace")
        if self.active_colleague_id is not None:
            require_stable_id(self.active_colleague_id, "active_colleague_id")
        if self.created_at is not None:
            require_utc(self.created_at, "created_at")
        if self.expires_at is not None:
            require_utc(self.expires_at, "expires_at")
        if self.created_at is not None and self.expires_at is not None:
            if self.expires_at <= self.created_at:
                raise ValueError("session expiry must follow creation")

    def colleague_namespace(self) -> Namespace:
        if self.active_colleague_id is None:
            raise ValueError("session has no active colleague namespace")
        return Namespace.colleague(self.tenant_id, self.active_colleague_id)


@dataclass(frozen=True, slots=True)
class SessionGrant:
    session: AuthenticatedSession
    session_credential: str = field(repr=False)
    csrf_token: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class InitialColleagueRequest:
    display_name: str
    role_description: str
    service_relationship: str
    mission: str
    timezone: str
    working_context: str
    working_hours: str
    working_style: str
    responsibilities: tuple[str, ...]
    capabilities: tuple[str, ...]
    constraints: tuple[str, ...]
    effect_kind: str
    destination_kind: str
    action: str
    effect_constraints: FrozenJsonObject
    idempotency_key: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.display_name, "display_name"),
            (self.role_description, "role_description"),
            (self.service_relationship, "service_relationship"),
            (self.mission, "mission"),
            (self.timezone, "timezone"),
            (self.working_context, "working_context"),
            (self.working_hours, "working_hours"),
            (self.working_style, "working_style"),
        ):
            require_text(value, name)
        for values, name in (
            (self.responsibilities, "responsibilities"),
            (self.capabilities, "capabilities"),
            (self.constraints, "constraints"),
        ):
            if not values or any(not isinstance(item, str) or not item.strip() for item in values):
                raise ValueError(f"{name} must contain non-empty text")
        require_stable_id(self.effect_kind, "effect_kind")
        require_stable_id(self.destination_kind, "destination_kind")
        require_stable_id(self.action, "action")
        if not isinstance(self.effect_constraints, FrozenJsonObject):
            raise ValueError("effect constraints must be immutable")
        require_stable_id(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True, slots=True)
class WorkAssignmentRequest:
    title: str
    description: str
    responsibility_id: str
    idempotency_key: str

    def __post_init__(self) -> None:
        require_text(self.title, "title")
        require_text(self.description, "description")
        require_stable_id(self.responsibility_id, "responsibility_id")
        require_stable_id(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True, slots=True)
class MutationReplay:
    request_digest: str
    result: FrozenJsonObject

    def __post_init__(self) -> None:
        require_digest(self.request_digest, "request_digest")
        if not isinstance(self.result, FrozenJsonObject):
            raise ValueError("mutation replay result must be immutable")


@dataclass(frozen=True, slots=True)
class MetricResult:
    metric: str
    status: str
    numerator: int | None
    denominator: int
    value: float | None
    reason: str | None
    evidence_class: str = "synthetic_offline"
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        require_stable_id(self.metric, "metric")
        if self.status not in {"observed", "not_applicable"}:
            raise ValueError("metric status is unsupported")
        if type(self.denominator) is not int or self.denominator < 0:
            raise ValueError("metric denominator must be non-negative")
        if self.denominator == 0:
            if self.status != "not_applicable" or self.value is not None or not self.reason:
                raise ValueError("zero denominator requires not_applicable and a reason")
        elif self.status != "observed" or self.numerator is None or self.value is None:
            raise ValueError("observed metric requires numerator and value")


@dataclass(frozen=True, slots=True)
class StudioSnapshot:
    namespace: Namespace
    profile: Profile
    mandate: Mandate
    work: tuple[FiniteWork, ...]
    events: tuple[InputEvent, ...]
    timers: tuple[TimerOccurrence, ...]
    wakes: tuple[WakeCycle, ...]
    agenda: tuple[AgendaItem, ...]
    decisions: tuple[Decision, ...]
    proposals: tuple[EffectProposal, ...]
    approvals: tuple[HumanApprovalDecision, ...]
    attempts: tuple[EffectAttempt, ...]
    results: tuple[ActionResult, ...]
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.namespace.require_exact(self.profile.namespace)
        self.namespace.require_exact(self.mandate.namespace)
        for collection in (
            self.work,
            self.events,
            self.timers,
            self.wakes,
            self.agenda,
            self.decisions,
            self.proposals,
            self.approvals,
            self.attempts,
            self.results,
        ):
            for record in collection:
                self.namespace.require_exact(record.namespace)
