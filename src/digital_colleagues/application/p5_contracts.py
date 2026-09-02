# SPDX-License-Identifier: Apache-2.0

"""Framework-neutral P5 builder and runtime policy request/response values."""

from __future__ import annotations

from dataclasses import dataclass

from digital_colleagues.core.authority import (
    CapabilityGrant,
    Constraint,
    EffectBoundary,
    Mandate,
    Profile,
    ResponsibilityDefinition,
)
from digital_colleagues.core.builder import ColleagueDraft
from digital_colleagues.core.common import (
    SCHEMA_VERSION,
    FrozenJsonObject,
    require_digest,
    require_revision,
    require_schema_version,
    require_stable_id,
    require_text,
)
from digital_colleagues.core.policy import (
    ColleaguePolicy,
    DurableTriggerKind,
    EscalationCondition,
    EscalationRecord,
    InterruptionMode,
    NotificationMode,
    OutsideHoursOutcome,
    PolicyEnforcementRecord,
    PolicyOutcomeKind,
    PolicyRunState,
    PolicyStatus,
    ProactivityMode,
    StopCondition,
    WakeBudgetPeriod,
    WeeklyWindow,
)


@dataclass(frozen=True, slots=True)
class ProfileEdit:
    display_name: str
    description: str
    presentation: FrozenJsonObject

    def __post_init__(self) -> None:
        object.__setattr__(self, "display_name", require_text(self.display_name, "display_name"))
        object.__setattr__(self, "description", require_text(self.description, "description"))
        if not isinstance(self.presentation, FrozenJsonObject):
            raise ValueError("Profile presentation must be immutable JSON")


@dataclass(frozen=True, slots=True)
class MandateEdit:
    mission: str
    service_relationship: str
    responsibilities: tuple[ResponsibilityDefinition, ...]
    capabilities: tuple[CapabilityGrant, ...]
    constraints: tuple[Constraint, ...]
    working_context: FrozenJsonObject
    effect_boundaries: tuple[EffectBoundary, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "mission", require_text(self.mission, "mission"))
        object.__setattr__(
            self,
            "service_relationship",
            require_text(self.service_relationship, "service_relationship"),
        )
        for values, expected, field in (
            (self.responsibilities, ResponsibilityDefinition, "responsibilities"),
            (self.capabilities, CapabilityGrant, "capabilities"),
            (self.constraints, Constraint, "constraints"),
            (self.effect_boundaries, EffectBoundary, "effect_boundaries"),
        ):
            items = tuple(values)
            if not items or not all(isinstance(item, expected) for item in items):
                raise ValueError(f"{field} must contain typed values")
            object.__setattr__(self, field, items)
        if not isinstance(self.working_context, FrozenJsonObject):
            raise ValueError("working context must be immutable JSON")


@dataclass(frozen=True, slots=True)
class PolicyEdit:
    timezone: str | None = None
    weekly_windows: tuple[WeeklyWindow, ...] | None = None
    allowed_triggers: tuple[DurableTriggerKind, ...] | None = None
    proactivity: ProactivityMode | None = None
    notification: NotificationMode | None = None
    interruption: InterruptionMode | None = None
    wake_limit: int | None = None
    wake_period: WakeBudgetPeriod | None = None
    outside_hours: OutsideHoursOutcome | None = None
    stop_conditions: tuple[StopCondition, ...] | None = None
    escalation_conditions: tuple[EscalationCondition, ...] | None = None
    failure_limit: int | None = None
    run_state: PolicyRunState | None = None
    explicit_resume: bool = False

    def __post_init__(self) -> None:
        if type(self.explicit_resume) is not bool:
            raise ValueError("explicit resume intent must be boolean")
        if self.explicit_resume and self.run_state is not PolicyRunState.ACTIVE:
            raise ValueError("explicit resume intent requires an explicit active run state")


@dataclass(frozen=True, slots=True)
class DraftUpdateRequest:
    profile: ProfileEdit
    mandate: MandateEdit
    policy: PolicyEdit
    expected_draft_revision: int
    idempotency_key: str

    def __post_init__(self) -> None:
        if not isinstance(self.profile, ProfileEdit):
            raise ValueError("Profile edit must be typed")
        if not isinstance(self.mandate, MandateEdit):
            raise ValueError("Mandate edit must be typed")
        if not isinstance(self.policy, PolicyEdit):
            raise ValueError("policy edit must be typed")
        require_revision(self.expected_draft_revision, "expected_draft_revision")
        require_stable_id(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True, slots=True)
class ConfirmDraftRequest:
    expected_draft_revision: int
    expected_base_profile_revision: int
    expected_base_mandate_revision: int
    expected_base_policy_revision: int
    expected_canonical_digest: str
    idempotency_key: str

    def __post_init__(self) -> None:
        require_revision(self.expected_draft_revision, "expected_draft_revision")
        require_revision(self.expected_base_profile_revision, "expected_base_profile_revision")
        require_revision(self.expected_base_mandate_revision, "expected_base_mandate_revision")
        if (
            type(self.expected_base_policy_revision) is not int
            or self.expected_base_policy_revision < 0
        ):
            raise ValueError("expected base policy revision must be non-negative")
        require_digest(self.expected_canonical_digest, "expected_canonical_digest")
        require_stable_id(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True, slots=True)
class ConfirmationResult:
    draft_id: str
    draft_revision: int
    profile_revision: int
    mandate_revision: int
    policy_revision: int
    canonical_digest: str
    replayed: bool = False
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        require_stable_id(self.draft_id, "draft_id")
        require_revision(self.draft_revision, "draft_revision")
        require_revision(self.profile_revision, "profile_revision")
        require_revision(self.mandate_revision, "mandate_revision")
        require_revision(self.policy_revision, "policy_revision")
        require_digest(self.canonical_digest, "canonical_digest")
        if type(self.replayed) is not bool:
            raise ValueError("confirmation replay marker must be boolean")


@dataclass(frozen=True, slots=True)
class PolicyAdmission:
    accepted: bool
    outcome: PolicyOutcomeKind
    budget_count: int
    budget_limit: int
    record: PolicyEnforcementRecord
    escalation: EscalationRecord | None = None
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        if type(self.accepted) is not bool:
            raise ValueError("policy admission accepted marker must be boolean")
        if not isinstance(self.outcome, PolicyOutcomeKind):
            raise ValueError("policy admission outcome must be typed")
        if type(self.budget_count) is not int or self.budget_count < 0:
            raise ValueError("policy admission budget count must be non-negative")
        if type(self.budget_limit) is not int or self.budget_limit < 1:
            raise ValueError("policy admission budget limit must be positive")


@dataclass(frozen=True, slots=True)
class P5StudioSnapshot:
    profile: Profile
    mandate: Mandate
    policy: ColleaguePolicy | None
    policy_status: PolicyStatus
    drafts: tuple[ColleagueDraft, ...]
    policy_outcomes: tuple[PolicyEnforcementRecord, ...]
    escalations: tuple[EscalationRecord, ...]
    budget_count: int
    run_state: PolicyRunState | None
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.profile.namespace.require_exact(self.mandate.namespace)
        if self.policy is not None:
            self.profile.namespace.require_exact(self.policy.namespace)
        if not isinstance(self.policy_status, PolicyStatus):
            raise ValueError("policy status must be explicit")
        if (self.policy is None) != (self.policy_status is PolicyStatus.LEGACY_UNCONFIRMED):
            raise ValueError("legacy policy status must match policy absence")
