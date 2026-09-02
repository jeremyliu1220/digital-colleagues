# SPDX-License-Identifier: Apache-2.0

"""Strict Pydantic mappings for the P5 revisioned colleague builder."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Self

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from digital_colleagues.api.p4_app import SESSION_COOKIE
from digital_colleagues.application.errors import ConflictError, ReplayConflictError
from digital_colleagues.application.p4_contracts import AuthenticatedSession, MetricResult
from digital_colleagues.application.p4_services import AuthenticationService, P4EvaluationService
from digital_colleagues.application.p5_contracts import (
    ConfirmDraftRequest,
    DraftUpdateRequest,
    MandateEdit,
    PolicyEdit,
    ProfileEdit,
)
from digital_colleagues.application.p5_ports import P5PersistencePort
from digital_colleagues.application.p5_services import RevisionedColleagueBuilderService
from digital_colleagues.core.authority import (
    CapabilityGrant,
    Constraint,
    EffectBoundary,
    EffectKind,
    ResponsibilityDefinition,
    project_identity_card,
)
from digital_colleagues.core.builder import ColleagueDraft
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.policy import (
    DurableTriggerKind,
    EscalationCondition,
    InterruptionMode,
    NotificationMode,
    OutsideHoursOutcome,
    PolicyRunState,
    ProactivityMode,
    StopCondition,
    WakeBudgetPeriod,
    Weekday,
    WeeklyWindow,
)
from digital_colleagues.core.serialization import contract_to_public_data


class _StrictMutation(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DraftCreateMutation(_StrictMutation):
    idempotency_key: str = Field(min_length=1, max_length=128)


class ProfileEditMutation(_StrictMutation):
    display_name: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=512)
    presentation: dict[str, Any]


class ResponsibilityMutation(_StrictMutation):
    responsibility_id: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=512)
    obligations: list[str] = Field(min_length=1, max_length=16)
    completion_conditions: list[str] = Field(min_length=1, max_length=16)


class CapabilityMutation(_StrictMutation):
    capability_id: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=512)


class ConstraintMutation(_StrictMutation):
    constraint_id: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=512)


class EffectBoundaryMutation(_StrictMutation):
    boundary_id: str = Field(min_length=1, max_length=128)
    effect_kind: EffectKind
    allowed_destination_kinds: list[str] = Field(min_length=1, max_length=16)
    allowed_actions: list[str] = Field(min_length=1, max_length=16)
    constraints: dict[str, Any]
    human_approval_required: bool = True


class MandateEditMutation(_StrictMutation):
    mission: str = Field(min_length=1, max_length=1024)
    service_relationship: str = Field(min_length=1, max_length=512)
    responsibilities: list[ResponsibilityMutation] = Field(min_length=1, max_length=16)
    capabilities: list[CapabilityMutation] = Field(min_length=1, max_length=16)
    constraints: list[ConstraintMutation] = Field(min_length=1, max_length=16)
    working_context: dict[str, Any]
    effect_boundaries: list[EffectBoundaryMutation] = Field(min_length=1, max_length=16)


class WeeklyWindowMutation(_StrictMutation):
    weekday: Weekday
    start_minute: int = Field(ge=0, lt=1_440)
    end_minute: int = Field(ge=0, le=1_440)


class PolicyEditMutation(_StrictMutation):
    timezone: str | None = Field(default=None, min_length=1, max_length=128)
    weekly_windows: list[WeeklyWindowMutation] | None = Field(
        default=None, min_length=1, max_length=32
    )
    allowed_triggers: list[DurableTriggerKind] | None = Field(
        default=None, min_length=1, max_length=2
    )
    proactivity: ProactivityMode | None = None
    notification: NotificationMode | None = None
    interruption: InterruptionMode | None = None
    wake_limit: int | None = Field(default=None, ge=1, le=10_000)
    wake_period: WakeBudgetPeriod | None = None
    outside_hours: OutsideHoursOutcome | None = None
    stop_conditions: list[StopCondition] | None = Field(default=None, max_length=4)
    escalation_conditions: list[EscalationCondition] | None = Field(default=None, max_length=4)
    failure_limit: int | None = Field(default=None, ge=1, le=100)
    run_state: PolicyRunState | None = None
    explicit_resume: bool = False

    @model_validator(mode="after")
    def validate_explicit_resume(self) -> Self:
        if self.explicit_resume and self.run_state is not PolicyRunState.ACTIVE:
            raise ValueError("explicit resume requires an explicit active run state")
        return self


class DraftUpdateMutation(_StrictMutation):
    profile: ProfileEditMutation
    mandate: MandateEditMutation
    policy: PolicyEditMutation
    expected_draft_revision: int = Field(gt=0)
    idempotency_key: str = Field(min_length=1, max_length=128)


class DraftTransitionMutation(_StrictMutation):
    expected_draft_revision: int = Field(gt=0)
    idempotency_key: str = Field(min_length=1, max_length=128)


class DraftConfirmMutation(_StrictMutation):
    expected_draft_revision: int = Field(gt=0)
    expected_base_profile_revision: int = Field(gt=0)
    expected_base_mandate_revision: int = Field(gt=0)
    expected_base_policy_revision: int = Field(ge=0)
    expected_canonical_digest: str = Field(pattern="^sha256:[0-9a-f]{64}$")
    idempotency_key: str = Field(min_length=1, max_length=128)


def _draft_data(draft: ColleagueDraft) -> dict[str, object]:
    identity = project_identity_card(draft.proposed_profile, draft.proposed_mandate)
    identity_data = contract_to_public_data(identity)
    if not isinstance(identity_data, dict):
        raise ValueError("identity-card projection is invalid")
    return {
        "draft": contract_to_public_data(draft),
        "identity_card_preview": {
            **identity_data,
            "projection_only": True,
            "active": False,
            "inert_until_confirmation": True,
        },
        "review_binding": {
            "draft_id": draft.draft_id,
            "draft_revision": draft.revision,
            "base_profile_id": draft.base_profile_id,
            "base_profile_revision": draft.base_profile_revision,
            "base_mandate_id": draft.base_mandate_id,
            "base_mandate_revision": draft.base_mandate_revision,
            "base_policy_id": draft.base_policy_id,
            "base_policy_revision": draft.base_policy_revision,
            "canonical_digest": draft.canonical_digest,
        },
    }


def _contract_data(value: object) -> dict[str, object]:
    mapped = contract_to_public_data(value)
    if not isinstance(mapped, dict):
        raise ValueError("public contract mapping is invalid")
    return mapped


def _metric_data(value: MetricResult) -> dict[str, object]:
    return {
        "schema_version": value.schema_version,
        "metric": value.metric,
        "status": value.status,
        "numerator": value.numerator,
        "denominator": value.denominator,
        "value": value.value,
        "reason": value.reason,
        "source": value.source,
        "safe_causal_references": list(value.safe_causal_references),
        "scenario_version": value.scenario_version,
        "policy_version": value.policy_version,
        "evidence_class": value.evidence_class,
    }


def _update_request(body: DraftUpdateMutation) -> DraftUpdateRequest:
    return DraftUpdateRequest(
        profile=ProfileEdit(
            display_name=body.profile.display_name,
            description=body.profile.description,
            presentation=FrozenJsonObject.from_mapping(body.profile.presentation),
        ),
        mandate=MandateEdit(
            mission=body.mandate.mission,
            service_relationship=body.mandate.service_relationship,
            responsibilities=tuple(
                ResponsibilityDefinition(
                    responsibility_id=item.responsibility_id,
                    description=item.description,
                    obligations=tuple(item.obligations),
                    completion_conditions=tuple(item.completion_conditions),
                )
                for item in body.mandate.responsibilities
            ),
            capabilities=tuple(
                CapabilityGrant(
                    capability_id=item.capability_id,
                    description=item.description,
                )
                for item in body.mandate.capabilities
            ),
            constraints=tuple(
                Constraint(
                    constraint_id=item.constraint_id,
                    description=item.description,
                )
                for item in body.mandate.constraints
            ),
            working_context=FrozenJsonObject.from_mapping(body.mandate.working_context),
            effect_boundaries=tuple(
                EffectBoundary(
                    boundary_id=item.boundary_id,
                    effect_kind=item.effect_kind,
                    allowed_destination_kinds=tuple(item.allowed_destination_kinds),
                    allowed_actions=tuple(item.allowed_actions),
                    constraints=FrozenJsonObject.from_mapping(item.constraints),
                    human_approval_required=item.human_approval_required,
                )
                for item in body.mandate.effect_boundaries
            ),
        ),
        policy=PolicyEdit(
            timezone=body.policy.timezone,
            weekly_windows=(
                None
                if body.policy.weekly_windows is None
                else tuple(
                    WeeklyWindow(item.weekday, item.start_minute, item.end_minute)
                    for item in body.policy.weekly_windows
                )
            ),
            allowed_triggers=(
                None
                if body.policy.allowed_triggers is None
                else tuple(body.policy.allowed_triggers)
            ),
            proactivity=body.policy.proactivity,
            notification=body.policy.notification,
            interruption=body.policy.interruption,
            wake_limit=body.policy.wake_limit,
            wake_period=body.policy.wake_period,
            outside_hours=body.policy.outside_hours,
            stop_conditions=(
                None if body.policy.stop_conditions is None else tuple(body.policy.stop_conditions)
            ),
            escalation_conditions=(
                None
                if body.policy.escalation_conditions is None
                else tuple(body.policy.escalation_conditions)
            ),
            failure_limit=body.policy.failure_limit,
            run_state=body.policy.run_state,
            explicit_resume=body.policy.explicit_resume,
        ),
        expected_draft_revision=body.expected_draft_revision,
        idempotency_key=body.idempotency_key,
    )


def install_p5_routes(
    app: FastAPI,
    *,
    authentication: AuthenticationService,
    builder: RevisionedColleagueBuilderService,
    p5_store: P5PersistencePort,
    expected_origin: str,
    evaluation: P4EvaluationService | None = None,
) -> None:
    """Add P5 routes without replacing the retained P4 API surface."""

    def read_session(request: Request) -> AuthenticatedSession:
        credential = request.cookies.get(SESSION_COOKIE, "")
        if not credential:
            raise HTTPException(
                status_code=401,
                detail={"code": "session_required", "message": "authentication required"},
            )
        return authentication.resolve(credential)

    def mutation_session(request: Request) -> AuthenticatedSession:
        credential = request.cookies.get(SESSION_COOKIE, "")
        if not credential:
            raise HTTPException(
                status_code=401,
                detail={"code": "session_required", "message": "authentication required"},
            )
        return authentication.authorize_mutation(
            session_credential=credential,
            origin=request.headers.get("origin"),
            csrf_token=request.headers.get("x-csrf-token"),
            expected_origin=expected_origin,
        )

    def replayable(
        *,
        session: AuthenticatedSession,
        action: str,
        idempotency_key: str,
        binding: str,
        operation: Callable[[], dict[str, object]],
    ) -> dict[str, object]:
        try:
            replay, request_digest = authentication.mutation_replay(
                session=session,
                action=action,
                idempotency_key=idempotency_key,
                request_binding=binding,
            )
        except ConflictError as error:
            raise ReplayConflictError("P5 mutation idempotency key was rebound") from error
        if replay is not None:
            return dict(replay.items())
        result = operation()
        try:
            authentication.record_mutation(
                session=session,
                action=action,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
                result=result,
            )
        except ConflictError as error:
            raise ReplayConflictError("P5 mutation idempotency key raced") from error
        return result

    @app.get("/p5/studio/state")
    def p5_studio_state(request: Request) -> dict[str, object]:
        session = read_session(request)
        if session.active_colleague_id is None:
            return {"state": "empty", "namespace": None}
        namespace = session.colleague_namespace()
        snapshot = p5_store.p5_studio_snapshot(namespace)
        active_card = project_identity_card(snapshot.profile, snapshot.mandate)
        return {
            "state": "ready",
            "namespace": contract_to_public_data(namespace),
            "active": {
                "identity_card": contract_to_public_data(active_card),
                "profile": contract_to_public_data(snapshot.profile),
                "mandate": contract_to_public_data(snapshot.mandate),
                "policy": (
                    None if snapshot.policy is None else contract_to_public_data(snapshot.policy)
                ),
                "policy_status": snapshot.policy_status.value,
                "profile_revision": snapshot.profile.revision,
                "mandate_revision": snapshot.mandate.revision,
                "policy_revision": (0 if snapshot.policy is None else snapshot.policy.revision),
            },
            "drafts": [_draft_data(item) for item in snapshot.drafts],
            "runtime_policy": {
                "budget_count": snapshot.budget_count,
                "run_state": (None if snapshot.run_state is None else snapshot.run_state.value),
                "outcomes": [contract_to_public_data(item) for item in snapshot.policy_outcomes],
                "escalations": [contract_to_public_data(item) for item in snapshot.escalations],
            },
        }

    @app.get("/p5/evaluation/metrics")
    def p5_evaluation_metrics(request: Request) -> dict[str, object]:
        session = read_session(request)
        if session.active_colleague_id is None:
            return {
                "scenario_version": "p5-revisioned-builder-v1",
                "evidence_class": "synthetic_offline",
                "policy_binding": None,
                "metrics": [],
            }
        if evaluation is None:
            raise HTTPException(
                status_code=503,
                detail={"code": "evaluation_unavailable", "message": "evaluation unavailable"},
            )
        namespace = session.colleague_namespace()
        snapshot = p5_store.p5_studio_snapshot(namespace)
        policy = snapshot.policy
        metrics = evaluation.evaluate(namespace)
        refused = tuple(
            item for item in snapshot.policy_outcomes if item.outcome.value != "allowed"
        )
        return {
            "scenario_version": "p5-revisioned-builder-v1",
            "metric_definition_version": "colleague-experience-p5-v1",
            "evidence_class": "synthetic_offline",
            "policy_binding": (
                None
                if policy is None
                else {
                    "policy_id": policy.policy_id,
                    "policy_revision": policy.revision,
                    "mandate_id": policy.mandate_id,
                    "mandate_revision": policy.mandate_revision,
                }
            ),
            "metrics": [
                {
                    **_metric_data(item),
                    "policy_bindings": [
                        {
                            "policy_id": binding[0],
                            "policy_revision": binding[1],
                            "mandate_id": binding[2],
                            "mandate_revision": binding[3],
                        }
                        for binding in sorted(
                            {
                                (
                                    outcome.policy_id,
                                    outcome.policy_revision,
                                    outcome.mandate_id,
                                    outcome.mandate_revision,
                                )
                                for outcome in snapshot.policy_outcomes
                                if outcome.correlation_id in item.safe_causal_references
                            }
                        )
                    ],
                    "claim_scope": "descriptive_synthetic_only",
                }
                for item in metrics
            ],
            "policy_refusals": {
                "count": len(refused),
                "source": "durable namespaced p5_policy_outcomes",
                "counted_as_successful_interactions": False,
                "outcomes": sorted({item.outcome.value for item in refused}),
            },
            "claim_limits": {
                "colleague_experience_improved": "not_evaluated",
                "human_evidence": "not_evaluated",
                "live_provider_evidence": "not_evaluated",
            },
        }

    @app.get("/colleagues/drafts")
    def list_drafts(request: Request) -> dict[str, object]:
        session = read_session(request)
        if session.active_colleague_id is None:
            return {"drafts": []}
        return {
            "drafts": [
                _draft_data(item) for item in p5_store.list_drafts(session.colleague_namespace())
            ]
        }

    @app.get("/colleagues/drafts/{draft_id}")
    def get_draft(draft_id: str, request: Request) -> dict[str, object]:
        session = read_session(request)
        return _draft_data(p5_store.get_draft(session.colleague_namespace(), draft_id))

    @app.post("/colleagues/drafts", status_code=201)
    def create_draft(body: DraftCreateMutation, request: Request) -> dict[str, object]:
        session = mutation_session(request)
        return replayable(
            session=session,
            action="p5_draft_create",
            idempotency_key=body.idempotency_key,
            binding="clone-active-configuration",
            operation=lambda: _draft_data(
                builder.create(session=session, idempotency_key=body.idempotency_key)
            ),
        )

    @app.put("/colleagues/drafts/{draft_id}")
    def update_draft(
        draft_id: str, body: DraftUpdateMutation, request: Request
    ) -> dict[str, object]:
        session = mutation_session(request)
        mapped = _update_request(body)
        jsonable = body.model_dump(mode="json")
        return replayable(
            session=session,
            action=f"p5_draft_update:{draft_id}",
            idempotency_key=body.idempotency_key,
            binding=json.dumps(jsonable, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
            operation=lambda: _draft_data(
                builder.update(session=session, draft_id=draft_id, request=mapped)
            ),
        )

    @app.post("/colleagues/drafts/{draft_id}/review")
    def review_draft(
        draft_id: str, body: DraftTransitionMutation, request: Request
    ) -> dict[str, object]:
        session = mutation_session(request)
        return replayable(
            session=session,
            action=f"p5_draft_review:{draft_id}",
            idempotency_key=body.idempotency_key,
            binding=f"revision:{body.expected_draft_revision}",
            operation=lambda: _draft_data(
                builder.review(
                    session=session,
                    draft_id=draft_id,
                    expected_revision=body.expected_draft_revision,
                )
            ),
        )

    @app.post("/colleagues/drafts/{draft_id}/cancel")
    def cancel_draft(
        draft_id: str, body: DraftTransitionMutation, request: Request
    ) -> dict[str, object]:
        session = mutation_session(request)
        return replayable(
            session=session,
            action=f"p5_draft_cancel:{draft_id}",
            idempotency_key=body.idempotency_key,
            binding=f"revision:{body.expected_draft_revision}",
            operation=lambda: _draft_data(
                builder.cancel(
                    session=session,
                    draft_id=draft_id,
                    expected_revision=body.expected_draft_revision,
                )
            ),
        )

    @app.post("/colleagues/drafts/{draft_id}/confirm")
    def confirm_draft(
        draft_id: str, body: DraftConfirmMutation, request: Request
    ) -> dict[str, object]:
        session = mutation_session(request)
        result = builder.confirm(
            session=session,
            draft_id=draft_id,
            request=ConfirmDraftRequest(
                expected_draft_revision=body.expected_draft_revision,
                expected_base_profile_revision=body.expected_base_profile_revision,
                expected_base_mandate_revision=body.expected_base_mandate_revision,
                expected_base_policy_revision=body.expected_base_policy_revision,
                expected_canonical_digest=body.expected_canonical_digest,
                idempotency_key=body.idempotency_key,
            ),
        )
        return {
            "confirmation": {
                "schema_version": result.schema_version,
                "draft_id": result.draft_id,
                "draft_revision": result.draft_revision,
                "profile_revision": result.profile_revision,
                "mandate_revision": result.mandate_revision,
                "policy_revision": result.policy_revision,
                "canonical_digest": result.canonical_digest,
                "replayed": result.replayed,
            }
        }
