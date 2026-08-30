# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from digital_colleagues.application.contracts import RequestPrincipalContext
from digital_colleagues.core.authority import (
    CapabilityGrant,
    Constraint,
    EffectBoundary,
    EffectKind,
    Mandate,
    Profile,
    ResponsibilityDefinition,
)
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import HumanRole, Principal
from digital_colleagues.core.runtime import InputEvent, InputEventState
from digital_colleagues.core.work import FiniteWork, WorkState

T0 = datetime(2026, 2, 3, 4, 5, 6, tzinfo=UTC)
T1 = T0 + timedelta(minutes=1)
T2 = T0 + timedelta(minutes=2)
T3 = T0 + timedelta(minutes=3)
T4 = T0 + timedelta(hours=1)


def frozen(values: dict[str, object]) -> FrozenJsonObject:
    return FrozenJsonObject.from_mapping(values)


def namespace() -> Namespace:
    return Namespace.colleague("tenant-synthetic", "colleague-synthetic")


def other_namespace() -> Namespace:
    return Namespace.colleague("tenant-other", "colleague-other")


def admin() -> Principal:
    return Principal.human(
        tenant_id="tenant-synthetic",
        principal_id="human-admin",
        roles=(HumanRole.TENANT_ADMIN,),
    )


def user() -> Principal:
    return Principal.human(
        tenant_id="tenant-synthetic",
        principal_id="human-user",
        roles=(HumanRole.COLLEAGUE_USER,),
    )


def model() -> Principal:
    return Principal.model(tenant_id="tenant-synthetic", principal_id="model-reference")


def service() -> Principal:
    return Principal.service(tenant_id="tenant-synthetic", principal_id="service-runtime")


def request_context(principal: Principal | None = None) -> RequestPrincipalContext:
    return RequestPrincipalContext(namespace(), principal or user())


def profile() -> Profile:
    return Profile(
        namespace=namespace(),
        profile_id="profile-synthetic",
        display_name="Synthetic Reference Colleague",
        description="A deterministic public test identity.",
        presentation=frozen({"classification": "synthetic"}),
        revision=1,
        updated_by=admin(),
        updated_at=T0,
    )


def mandate(*, revision: int = 1) -> Mandate:
    return Mandate(
        namespace=namespace(),
        mandate_id="mandate-synthetic",
        mission="Process finite synthetic work through the reference channel.",
        service_relationship="Serves only the synthetic local reference namespace.",
        responsibilities=(
            ResponsibilityDefinition(
                responsibility_id="responsibility-synthetic",
                description="Maintain deterministic synthetic work.",
                obligations=("Process one finite item.",),
                completion_conditions=("Record a typed action result.",),
            ),
        ),
        capabilities=(
            CapabilityGrant(
                capability_id="capability-reference",
                description="Propose a synthetic reference message.",
            ),
        ),
        constraints=(
            Constraint(
                constraint_id="constraint-offline",
                description="Network access is forbidden.",
            ),
        ),
        working_context=frozen({"mode": "deterministic", "timezone": "UTC"}),
        effect_boundaries=(
            EffectBoundary(
                boundary_id="boundary-reference",
                effect_kind=EffectKind.REFERENCE_MESSAGE,
                allowed_destination_kinds=("reference_channel",),
                allowed_actions=("record_message",),
                constraints=frozen({"network": False}),
                human_approval_required=True,
            ),
        ),
        revision=revision,
        issued_by=admin(),
        effective_at=T0,
    )


def finite_work() -> FiniteWork:
    return FiniteWork(
        namespace=namespace(),
        work_id="work-synthetic",
        title="Produce one deterministic reference result",
        description="Synthetic finite work with no external provider.",
        state=WorkState.READY,
        dependency_ids=(),
        responsibility_ids=("responsibility-synthetic",),
        assignee_principal_id=model().principal_id,
        actor=admin(),
        mandate_id="mandate-synthetic",
        mandate_revision=1,
        completion_evidence=(),
        correlation_id="correlation-work-bootstrap",
        causation_id="mandate-synthetic",
        created_at=T0,
        updated_at=T0,
        revision=1,
    )


def input_event(
    *, event_id: str = "event-synthetic", correlation_id: str = "correlation-p3"
) -> InputEvent:
    return InputEvent(
        namespace=namespace(),
        event_id=event_id,
        event_type="work_assigned",
        state=InputEventState.ACCEPTED,
        safe_projection=frozen(
            {"work_id": "work-synthetic", "priority": 700, "title": "synthetic work"}
        ),
        payload_digest="sha256:" + ("1" * 64),
        actor=user(),
        correlation_id=correlation_id,
        causation_id=None,
        occurred_at=T0,
        revision=1,
    )


def principals() -> tuple[Principal, ...]:
    return admin(), user(), model(), service()
