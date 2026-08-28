# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from digital_colleagues.core import (
    ActionResult,
    ActionResultState,
    AgendaItem,
    AgendaItemState,
    ApprovalChoice,
    CapabilityGrant,
    Constraint,
    Decision,
    DecisionKind,
    EffectAttempt,
    EffectAttemptState,
    EffectBoundary,
    EffectConstraints,
    EffectDestination,
    EffectKind,
    EffectProposal,
    EffectProposalState,
    FrozenJsonObject,
    HumanApprovalDecision,
    HumanRole,
    InputEvent,
    InputEventState,
    Mandate,
    Namespace,
    Principal,
    Profile,
    ResponsibilityDefinition,
    WakeCycle,
    WakeCycleState,
)

T0 = datetime(2026, 1, 2, 3, 4, 5, 6000, tzinfo=UTC)
T1 = T0 + timedelta(minutes=1)
T2 = T0 + timedelta(minutes=2)
T3 = T0 + timedelta(minutes=3)
T4 = T0 + timedelta(minutes=4)
T5 = T0 + timedelta(minutes=5)
T6 = T0 + timedelta(minutes=6)
T7 = T0 + timedelta(minutes=7)
EXPIRY = T0 + timedelta(hours=1)


def colleague_namespace() -> Namespace:
    return Namespace.colleague("tenant-alpha", "colleague-alpha")


def other_namespace() -> Namespace:
    return Namespace.colleague("tenant-beta", "colleague-beta")


def human_admin() -> Principal:
    return Principal.human(
        tenant_id="tenant-alpha",
        principal_id="principal-human-admin",
        roles=(HumanRole.TENANT_ADMIN,),
    )


def human_user() -> Principal:
    return Principal.human(
        tenant_id="tenant-alpha",
        principal_id="principal-human-user",
        roles=(HumanRole.COLLEAGUE_USER,),
    )


def model_principal() -> Principal:
    return Principal.model(tenant_id="tenant-alpha", principal_id="principal-model")


def service_principal() -> Principal:
    return Principal.service(tenant_id="tenant-alpha", principal_id="principal-service")


def frozen(values: dict[str, object]) -> FrozenJsonObject:
    return FrozenJsonObject.from_mapping(values)


def profile(*, revision: int = 1, description: str = "Synthetic descriptive profile") -> Profile:
    return Profile(
        namespace=colleague_namespace(),
        profile_id="profile-alpha",
        display_name="Reference Colleague",
        description=description,
        presentation=frozen({"accent": "graphite", "labels": ["reference", "synthetic"]}),
        revision=revision,
        updated_by=human_admin(),
        updated_at=T0,
    )


def mandate(
    *, revision: int = 1, capabilities: tuple[CapabilityGrant, ...] | None = None
) -> Mandate:
    return Mandate(
        namespace=colleague_namespace(),
        mandate_id="mandate-alpha",
        mission="Maintain an inspectable synthetic work queue.",
        service_relationship="Serves authorized users within the tenant boundary.",
        responsibilities=(
            ResponsibilityDefinition(
                responsibility_id="responsibility-main",
                description="Keep finite work explicit.",
                obligations=("Track assigned work.",),
                completion_conditions=("Record completion evidence.",),
            ),
        ),
        capabilities=capabilities
        or (
            CapabilityGrant(
                capability_id="capability-propose",
                description="Propose a reference message effect.",
            ),
        ),
        constraints=(
            Constraint(
                constraint_id="constraint-no-network",
                description="Do not contact a network provider.",
            ),
        ),
        working_context=frozen({"timezone": "UTC", "mode": "deterministic"}),
        effect_boundaries=(
            EffectBoundary(
                boundary_id="boundary-reference-message",
                effect_kind=EffectKind.REFERENCE_MESSAGE,
                allowed_destination_kinds=("reference-channel",),
                allowed_actions=("deliver",),
                constraints=frozen({"network": False}),
            ),
        ),
        revision=revision,
        issued_by=human_admin(),
        effective_at=T0,
    )


def input_event() -> InputEvent:
    return InputEvent(
        namespace=colleague_namespace(),
        event_id="input-event-001",
        event_type="work-assigned",
        state=InputEventState.ACCEPTED,
        safe_projection=frozen({"summary": "Synthetic work assigned"}),
        payload_digest="sha256:" + ("a" * 64),
        actor=human_user(),
        correlation_id="correlation-001",
        causation_id=None,
        occurred_at=T0,
        revision=1,
    )


def wake_cycle() -> WakeCycle:
    return WakeCycle(
        namespace=colleague_namespace(),
        wake_cycle_id="wake-cycle-001",
        state=WakeCycleState.RUNNING,
        trigger_event_ids=("input-event-001",),
        agenda_item_ids=("agenda-item-001",),
        actor=service_principal(),
        correlation_id="correlation-001",
        causation_id="input-event-001",
        occurred_at=T1,
        revision=1,
    )


def agenda_item() -> AgendaItem:
    return AgendaItem(
        namespace=colleague_namespace(),
        agenda_item_id="agenda-item-001",
        wake_cycle_id="wake-cycle-001",
        source_event_id="input-event-001",
        work_id="work-001",
        title="Review synthetic work",
        state=AgendaItemState.SELECTED,
        priority=800,
        due_at=T5,
        actor=service_principal(),
        correlation_id="correlation-001",
        causation_id="wake-cycle-001",
        occurred_at=T2,
        revision=1,
    )


def decision() -> Decision:
    return Decision(
        namespace=colleague_namespace(),
        decision_id="decision-001",
        wake_cycle_id="wake-cycle-001",
        agenda_item_id="agenda-item-001",
        kind=DecisionKind.PROPOSE_EFFECT,
        rationale="The synthetic work requests a reference effect.",
        proposed_effect_id="proposal-001",
        actor=model_principal(),
        correlation_id="correlation-001",
        causation_id="agenda-item-001",
        occurred_at=T3,
        revision=1,
    )


def effect_proposal(*, revision: int = 1, namespace: Namespace | None = None) -> EffectProposal:
    return EffectProposal(
        namespace=namespace or colleague_namespace(),
        proposal_id="proposal-001",
        decision_id="decision-001",
        effect_kind=EffectKind.REFERENCE_MESSAGE,
        destination=EffectDestination(kind="reference-channel", target="synthetic-target"),
        action="deliver",
        payload=frozen({"body": "sensitive-body-value", "format": "plain"}),
        safe_projection=frozen({"summary": "One synthetic reference message"}),
        constraints=EffectConstraints(
            boundary_id="boundary-reference-message",
            idempotency_key="effect-key-001",
            valid_until=EXPIRY,
            maximum_attempts=1,
            parameters=frozen({"network": False}),
        ),
        state=EffectProposalState.PENDING_APPROVAL,
        actor=model_principal(),
        correlation_id="correlation-001",
        causation_id="decision-001",
        occurred_at=T4,
        revision=revision,
    )


def approval_decision(
    proposal: EffectProposal | None = None,
    *,
    author: Principal | None = None,
    proposal_id: str | None = None,
    proposal_revision: int | None = None,
) -> HumanApprovalDecision:
    bound = proposal or effect_proposal()
    return HumanApprovalDecision(
        namespace=bound.namespace,
        approval_decision_id="approval-001",
        proposal_id=proposal_id or bound.proposal_id,
        proposal_revision=proposal_revision or bound.revision,
        proposal_payload_digest=bound.payload_digest,
        choice=ApprovalChoice.APPROVE,
        author=author or human_user(),
        idempotency_key="approval-key-001",
        correlation_id="correlation-001",
        causation_id=proposal_id or bound.proposal_id,
        occurred_at=T5,
        valid_until=EXPIRY,
        revision=1,
    )


def effect_attempt() -> EffectAttempt:
    return EffectAttempt(
        namespace=colleague_namespace(),
        effect_attempt_id="effect-attempt-001",
        proposal_id="proposal-001",
        proposal_revision=1,
        approval_decision_id="approval-001",
        attempt_number=1,
        state=EffectAttemptState.SUCCEEDED,
        actor=service_principal(),
        correlation_id="correlation-001",
        causation_id="approval-001",
        occurred_at=T6,
        revision=1,
    )


def action_result() -> ActionResult:
    return ActionResult(
        namespace=colleague_namespace(),
        action_result_id="action-result-001",
        effect_attempt_id="effect-attempt-001",
        state=ActionResultState.SUCCEEDED,
        safe_projection=frozen({"summary": "Synthetic effect completed"}),
        result_digest="sha256:" + ("b" * 64),
        actor=service_principal(),
        correlation_id="correlation-001",
        causation_id="effect-attempt-001",
        occurred_at=T7,
        revision=1,
    )
