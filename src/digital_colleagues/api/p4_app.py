# SPDX-License-Identifier: Apache-2.0

"""Authenticated P4 Studio mapping edge with no caller-controlled authority fields."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from digital_colleagues.application.errors import (
    ApplicationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from digital_colleagues.application.p4_contracts import (
    AuthenticatedSession,
    InitialColleagueRequest,
    StudioSnapshot,
    WorkAssignmentRequest,
)
from digital_colleagues.application.p4_ports import StudioPersistencePort
from digital_colleagues.application.p4_services import (
    AuthenticationService,
    InitialColleagueService,
    P4RuntimeController,
    calculate_colleague_experience_metrics,
)
from digital_colleagues.application.ports import PersistencePort
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.effects import ApprovalChoice
from digital_colleagues.core.errors import CoreInvariantError
from digital_colleagues.core.serialization import contract_to_public_data, datetime_to_z
from digital_colleagues.core.work import WorkState

SESSION_COOKIE = "dc_session"


class _StrictMutation(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BootstrapExchangeMutation(_StrictMutation):
    token: str = Field(min_length=32, max_length=256)


class InitialColleagueMutation(_StrictMutation):
    display_name: str = Field(min_length=1, max_length=128)
    role_description: str = Field(min_length=1, max_length=512)
    service_relationship: str = Field(min_length=1, max_length=512)
    mission: str = Field(min_length=1, max_length=1024)
    timezone: str = Field(min_length=1, max_length=128)
    working_context: str = Field(min_length=1, max_length=1024)
    working_hours: str = Field(min_length=1, max_length=256)
    working_style: str = Field(min_length=1, max_length=512)
    responsibilities: list[str] = Field(min_length=1, max_length=16)
    capabilities: list[str] = Field(min_length=1, max_length=16)
    constraints: list[str] = Field(min_length=1, max_length=16)
    effect_kind: str = Field(pattern="^(reference_message|internal_record|notification)$")
    destination_kind: str = Field(min_length=1, max_length=128)
    action: str = Field(min_length=1, max_length=128)
    effect_constraints: dict[str, Any]
    idempotency_key: str = Field(min_length=1, max_length=128)


class WorkMutation(_StrictMutation):
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(min_length=1, max_length=1024)
    responsibility_id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)


class TriggerMutation(_StrictMutation):
    work_id: str = Field(min_length=1, max_length=128)
    trigger_class: str = Field(pattern="^(event|timer)$")
    deterministic_noop: bool = False
    idempotency_key: str = Field(min_length=1, max_length=128)


class ProcessMutation(_StrictMutation):
    idempotency_key: str = Field(min_length=1, max_length=128)


class ApprovalMutation(_StrictMutation):
    proposal_revision: int = Field(gt=0)
    proposal_payload_digest: str = Field(pattern="^sha256:[0-9a-f]{64}$")
    proposal_digest: str = Field(pattern="^sha256:[0-9a-f]{64}$")
    mandate_id: str = Field(min_length=1, max_length=128)
    mandate_revision: int = Field(gt=0)
    choice: ApprovalChoice
    idempotency_key: str = Field(min_length=1, max_length=128)


def _application_status(error: ApplicationError) -> int:
    if isinstance(error, NotFoundError):
        return 404
    if isinstance(error, ConflictError):
        return 409
    if isinstance(error, PermissionDeniedError):
        return 403
    if isinstance(error, ValidationError):
        return 400
    return 500


def _namespace_data(session: AuthenticatedSession) -> dict[str, object] | None:
    if session.active_colleague_id is None:
        return None
    return {
        "tenant_id": session.tenant_id,
        "scope": "colleague",
        "scope_id": session.active_colleague_id,
    }


def _session_data(session: AuthenticatedSession, csrf_token: str) -> dict[str, object]:
    assert session.expires_at is not None
    return {
        "authenticated": True,
        "principal": {
            "principal_id": session.principal.principal_id,
            "kind": session.principal.kind.value,
            "roles": [role.value for role in session.principal.roles],
        },
        "namespace": _namespace_data(session),
        "expires_at": datetime_to_z(session.expires_at),
        "csrf_token": csrf_token,
    }


def _proposal_data(snapshot: StudioSnapshot) -> list[dict[str, object]]:
    decisions = {item.proposal_id: item for item in snapshot.approvals}
    return [
        {
            "proposal_id": proposal.proposal_id,
            "revision": proposal.revision,
            "proposal_digest": proposal.proposal_digest,
            "payload_digest": proposal.payload_digest,
            "safe_projection": dict(proposal.safe_projection.items()),
            "destination": {
                "kind": proposal.destination.kind,
                "target": proposal.destination.target,
            },
            "action": proposal.action,
            "effect_kind": proposal.effect_kind.value,
            "effect_boundary": proposal.constraints.boundary_id,
            "constraint_parameters": dict(proposal.constraints.parameters.items()),
            "mandate_id": proposal.mandate_id,
            "mandate_revision": proposal.mandate_revision,
            "actor": {
                "principal_id": proposal.actor.principal_id,
                "kind": proposal.actor.kind.value,
            },
            "namespace": contract_to_public_data(proposal.namespace),
            "expires_at": datetime_to_z(proposal.constraints.valid_until),
            "approval_status": (
                "pending"
                if proposal.proposal_id not in decisions
                else decisions[proposal.proposal_id].choice.value
            ),
            "correlation_id": proposal.correlation_id,
            "causation_id": proposal.causation_id,
        }
        for proposal in snapshot.proposals
    ]


def _wake_data(snapshot: StudioSnapshot) -> list[dict[str, object]]:
    agenda_by_wake = {item.wake_cycle_id: item for item in snapshot.agenda}
    decisions_by_wake = {item.wake_cycle_id: item for item in snapshot.decisions}
    records: list[dict[str, object]] = []
    for wake in snapshot.wakes:
        agenda = agenda_by_wake.get(wake.wake_cycle_id)
        decision = decisions_by_wake.get(wake.wake_cycle_id)
        trigger_class = "timer" if wake.trigger_timer_occurrence_ids else "event"
        trigger_ids = wake.trigger_timer_occurrence_ids or wake.trigger_event_ids
        records.append(
            {
                "wake_cycle_id": wake.wake_cycle_id,
                "wake_reason": None if agenda is None else agenda.title,
                "trigger_class": trigger_class,
                "trigger_identity": trigger_ids[0],
                "agenda_item_id": None if agenda is None else agenda.agenda_item_id,
                "agenda_generation": None if agenda is None else agenda.generation,
                "handled_generation": None if agenda is None else agenda.handled_generation,
                "decision": None
                if decision is None
                else {
                    "decision_id": decision.decision_id,
                    "kind": decision.kind.value,
                    "rationale": decision.rationale,
                    "proposal_id": decision.proposed_effect_id,
                },
                "correlation_id": wake.correlation_id,
                "causation_id": wake.causation_id,
                "occurred_at": datetime_to_z(wake.occurred_at),
                "revision": wake.revision,
                "fencing_token": wake.fencing_token,
            }
        )
    return records


def _snapshot_data(snapshot: StudioSnapshot) -> dict[str, object]:
    return {
        "namespace": contract_to_public_data(snapshot.namespace),
        "identity": {
            "profile": contract_to_public_data(snapshot.profile),
            "mandate": contract_to_public_data(snapshot.mandate),
            "exact_revision": snapshot.mandate.revision,
            "authority_summary": {
                "profile_is_authority": False,
                "responsibility_count": len(snapshot.mandate.responsibilities),
                "capability_count": len(snapshot.mandate.capabilities),
                "constraint_count": len(snapshot.mandate.constraints),
                "effect_boundaries": [
                    contract_to_public_data(item) for item in snapshot.mandate.effect_boundaries
                ],
            },
        },
        "work": [contract_to_public_data(item) for item in snapshot.work],
        "wakes": _wake_data(snapshot),
        "proposals": _proposal_data(snapshot),
        "approvals": [contract_to_public_data(item) for item in snapshot.approvals],
        "attempts": [contract_to_public_data(item) for item in snapshot.attempts],
        "results": [contract_to_public_data(item) for item in snapshot.results],
    }


def create_p4_app(
    *,
    authentication: AuthenticationService,
    colleagues: InitialColleagueService,
    runtime: P4RuntimeController,
    store: PersistencePort,
    studio_store: StudioPersistencePort,
    expected_origin: str,
    secure_cookie: bool = False,
) -> FastAPI:
    app = FastAPI(title="Digital Colleagues P4 local Studio API", version="0.0.0-p4")
    app.state.authentication_boundary = "digest_only_bootstrap_and_server_session"
    app.state.expected_origin = expected_origin

    @app.exception_handler(ApplicationError)
    async def application_error(_: Request, error: ApplicationError) -> JSONResponse:
        return JSONResponse(
            status_code=_application_status(error),
            content={"detail": {"code": type(error).__name__, "message": "request refused"}},
        )

    @app.exception_handler(CoreInvariantError)
    async def core_error(_: Request, error: CoreInvariantError) -> JSONResponse:
        del error
        return JSONResponse(
            status_code=400,
            content={"detail": {"code": "invalid_contract", "message": "request refused"}},
        )

    def _cookie(request: Request) -> str:
        value = request.cookies.get(SESSION_COOKIE, "")
        if not value:
            raise HTTPException(
                status_code=401,
                detail={"code": "session_required", "message": "authentication required"},
            )
        return value

    def _read_session(request: Request) -> tuple[AuthenticatedSession, str]:
        credential = _cookie(request)
        return authentication.resolve(credential), credential

    def _mutation_session(request: Request) -> AuthenticatedSession:
        return authentication.authorize_mutation(
            session_credential=_cookie(request),
            origin=request.headers.get("origin"),
            csrf_token=request.headers.get("x-csrf-token"),
            expected_origin=expected_origin,
        )

    @app.get("/health")
    def health() -> dict[str, object]:
        return {"status": "ok", "persistence": store.healthcheck()}

    @app.post("/auth/bootstrap/exchange", status_code=201)
    def exchange(
        body: BootstrapExchangeMutation, request: Request, response: Response
    ) -> dict[str, object]:
        if request.headers.get("origin") != expected_origin:
            raise PermissionDeniedError("bootstrap Origin was refused")
        grant = authentication.exchange(body.token)
        assert grant.session.expires_at is not None
        response.set_cookie(
            key=SESSION_COOKIE,
            value=grant.session_credential,
            httponly=True,
            secure=secure_cookie,
            samesite="strict",
            path="/",
            max_age=max(
                1,
                int((grant.session.expires_at - grant.session.created_at).total_seconds()),
            )
            if grant.session.created_at is not None
            else None,
        )
        return _session_data(grant.session, grant.csrf_token)

    @app.get("/auth/session")
    def session(request: Request) -> dict[str, object]:
        resolved, credential = _read_session(request)
        return _session_data(resolved, authentication.csrf_for(credential))

    @app.post("/colleagues/preview")
    def preview(body: InitialColleagueMutation, request: Request) -> dict[str, object]:
        _mutation_session(request)
        return {
            "profile": {
                "display_name": body.display_name,
                "role_description": body.role_description,
                "working_style": body.working_style,
                "authoritative": False,
            },
            "mandate": {
                "mission": body.mission,
                "service_relationship": body.service_relationship,
                "responsibilities": body.responsibilities,
                "capabilities": body.capabilities,
                "constraints": body.constraints,
                "working_context": body.working_context,
                "working_hours": body.working_hours,
                "timezone": body.timezone,
                "exact_revision": 1,
                "authoritative": True,
            },
            "effect_boundary": {
                "kind": body.effect_kind,
                "destination_kind": body.destination_kind,
                "action": body.action,
                "constraints": body.effect_constraints,
                "human_approval_required": True,
            },
        }

    @app.post("/colleagues", status_code=201)
    def create_colleague(body: InitialColleagueMutation, request: Request) -> dict[str, object]:
        resolved = _mutation_session(request)
        profile, mandate, _ = colleagues.create(
            session=resolved,
            request=InitialColleagueRequest(
                display_name=body.display_name,
                role_description=body.role_description,
                service_relationship=body.service_relationship,
                mission=body.mission,
                timezone=body.timezone,
                working_context=body.working_context,
                working_hours=body.working_hours,
                working_style=body.working_style,
                responsibilities=tuple(body.responsibilities),
                capabilities=tuple(body.capabilities),
                constraints=tuple(body.constraints),
                effect_kind=body.effect_kind,
                destination_kind=body.destination_kind,
                action=body.action,
                effect_constraints=FrozenJsonObject.from_mapping(body.effect_constraints),
                idempotency_key=body.idempotency_key,
            ),
        )
        authentication.bind_colleague(resolved, profile.namespace.scope_id or "missing")
        return {
            "profile_id": profile.profile_id,
            "mandate_id": mandate.mandate_id,
            "mandate_revision": mandate.revision,
            "namespace": contract_to_public_data(profile.namespace),
        }

    @app.get("/studio/state")
    def studio_state(request: Request) -> dict[str, object]:
        resolved, _ = _read_session(request)
        if resolved.active_colleague_id is None:
            return {"state": "empty", "namespace": None}
        return {
            "state": "ready",
            **_snapshot_data(studio_store.studio_snapshot(resolved.colleague_namespace())),
        }

    @app.post("/work", status_code=201)
    def assign_work(body: WorkMutation, request: Request) -> dict[str, object]:
        resolved = _mutation_session(request)
        work, created = colleagues.assign_work(
            session=resolved,
            request=WorkAssignmentRequest(
                title=body.title,
                description=body.description,
                responsibility_id=body.responsibility_id,
                idempotency_key=body.idempotency_key,
            ),
        )
        return {"created": created, "work": contract_to_public_data(work)}

    @app.post("/runtime/triggers", status_code=201)
    def trigger(body: TriggerMutation, request: Request) -> dict[str, object]:
        resolved = _mutation_session(request)
        correlation_id = runtime.submit_trigger(
            session=resolved,
            work_id=body.work_id,
            trigger_class=body.trigger_class,
            deterministic_noop=body.deterministic_noop,
            idempotency_key=body.idempotency_key,
        )
        return {
            "accepted": True,
            "trigger_class": body.trigger_class,
            "correlation_id": correlation_id,
        }

    @app.post("/runtime/process")
    def process(body: ProcessMutation, request: Request) -> dict[str, object]:
        resolved = _mutation_session(request)
        replay, request_digest = authentication.mutation_replay(
            session=resolved,
            action="runtime_process",
            idempotency_key=body.idempotency_key,
            request_binding="bounded_once",
        )
        if replay is not None:
            return dict(replay.items())
        result = runtime.process_once(resolved)
        authentication.record_mutation(
            session=resolved,
            action="runtime_process",
            idempotency_key=body.idempotency_key,
            request_digest=request_digest,
            result=result,
        )
        return result

    @app.post("/proposals/{proposal_id}/decision", status_code=201)
    def decide(proposal_id: str, body: ApprovalMutation, request: Request) -> dict[str, object]:
        resolved = _mutation_session(request)
        proposal = store.get_proposal(resolved.colleague_namespace(), proposal_id)
        decision, attempt_id, created = runtime.decide_proposal(
            session=resolved,
            proposal=proposal,
            choice=body.choice,
            idempotency_key=body.idempotency_key,
            expected_proposal_revision=body.proposal_revision,
            expected_payload_digest=body.proposal_payload_digest,
            expected_proposal_digest=body.proposal_digest,
            expected_mandate_id=body.mandate_id,
            expected_mandate_revision=body.mandate_revision,
        )
        return {
            "approval_decision_id": decision.approval_decision_id,
            "choice": decision.choice.value,
            "attempt_id": attempt_id,
            "created": created,
        }

    @app.get("/audit/{correlation_id}")
    def audit(correlation_id: str, request: Request) -> dict[str, object]:
        resolved, _ = _read_session(request)
        records = store.causal_history(resolved.colleague_namespace(), correlation_id)
        return {"correlation_id": correlation_id, "records": list(records)}

    @app.get("/evaluation/metrics")
    def metrics(request: Request) -> dict[str, object]:
        resolved, _ = _read_session(request)
        snapshot = studio_store.studio_snapshot(resolved.colleague_namespace())
        approved = sum(item.choice is ApprovalChoice.APPROVE for item in snapshot.approvals)
        results = calculate_colleague_experience_metrics(
            {
                "rebrief_turns": 0,
                "resumptions_evaluated": 1 if snapshot.work else 0,
                "wrong_resumptions": 0,
                "ai_eligible_opportunities": len(snapshot.events) + len(snapshot.timers),
                "ai_visible_outputs": len(snapshot.proposals),
                "proactive_reviewed": len(snapshot.approvals),
                "proactive_accepted": approved,
                "ai_interactions_reviewed": len(snapshot.approvals),
                "unnecessary_interruptions": 0,
                "human_interventions": 0,
                "scenarios_started": len(snapshot.work),
                "scenarios_completed": sum(
                    item.state is WorkState.COMPLETED for item in snapshot.work
                ),
                "unauthorized_candidates": 0,
                "unauthorized_escapes": 0,
            }
        )
        return {
            "evidence_class": "synthetic_offline",
            "scenario_version": "p4-golden-path-v1",
            "metric_definition_version": "colleague-experience-p4-v1",
            "environment": "local_deterministic_reference",
            "source": "durable_namespaced_studio_snapshot_counts",
            "safe_causal_references": sorted(
                {item.correlation_id for item in snapshot.events}
                | {item.correlation_id for item in snapshot.timers}
            ),
            "exclusions": [
                "internal wakes without a user-visible output are excluded from the AI numerator",
                "synthetic observations are not human or live-provider evidence",
            ],
            "metrics": [
                {
                    "schema_version": item.schema_version,
                    "metric": item.metric,
                    "status": item.status,
                    "numerator": item.numerator,
                    "denominator": item.denominator,
                    "value": item.value,
                    "reason": item.reason,
                    "evidence_class": item.evidence_class,
                }
                for item in results
            ],
            "claim_limit": "No human improvement or live-provider outcome is established.",
        }

    return app
