# SPDX-License-Identifier: Apache-2.0

"""Minimal typed FastAPI mapping edge; authentication remains a P4 boundary."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from digital_colleagues.application.contracts import RequestPrincipalContext
from digital_colleagues.application.errors import (
    ApplicationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from digital_colleagues.application.ports import PersistencePort
from digital_colleagues.application.services import ApprovalService, EventService
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.effects import ApprovalChoice, HumanApprovalDecision
from digital_colleagues.core.errors import (
    AuthorizationError,
    CoreInvariantError,
    NamespaceMismatchError,
    ReplayError,
    RevisionMismatchError,
)
from digital_colleagues.core.runtime import InputEvent, InputEventState


class _MutationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InputEventMutation(_MutationModel):
    event_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=128)
    safe_projection: dict[str, Any]
    payload_digest: str
    correlation_id: str = Field(min_length=1, max_length=128)
    causation_id: str | None = Field(default=None, max_length=128)
    occurred_at: datetime
    idempotency_key: str = Field(min_length=1, max_length=128)


class InputEventResponse(BaseModel):
    event_id: str
    created: bool
    revision: int
    state: str


class ApprovalMutation(_MutationModel):
    approval_decision_id: str = Field(min_length=1, max_length=128)
    proposal_revision: int = Field(gt=0)
    proposal_payload_digest: str
    proposal_digest: str
    choice: ApprovalChoice
    idempotency_key: str = Field(min_length=1, max_length=128)
    occurred_at: datetime
    valid_until: datetime
    mandate_id: str = Field(min_length=1, max_length=128)
    expected_mandate_revision: int = Field(gt=0)


class ApprovalResponse(BaseModel):
    approval_decision_id: str
    attempt_id: str | None
    created: bool
    choice: str


class HistoryResponse(BaseModel):
    correlation_id: str
    records: list[dict[str, Any]]


def _status_for(error: ApplicationError) -> int:
    if isinstance(error, NotFoundError):
        return 404
    if isinstance(error, ConflictError):
        return 409
    if isinstance(error, PermissionDeniedError):
        return 403
    if isinstance(error, ValidationError):
        return 400
    return 500


def _core_status(error: CoreInvariantError) -> int:
    if isinstance(error, (RevisionMismatchError, ReplayError)):
        return 409
    if isinstance(error, (AuthorizationError, NamespaceMismatchError)):
        return 403
    return 400


def create_app(
    *,
    event_service: EventService,
    approval_service: ApprovalService,
    store: PersistencePort,
    context_provider: Callable[[], RequestPrincipalContext],
) -> FastAPI:
    app = FastAPI(title="Digital Colleagues P3 headless edge", version="0.0.0-p3")
    app.state.authentication_boundary = "server_context_injected_p4_authentication_not_implemented"

    @app.post("/events", response_model=InputEventResponse, status_code=201)
    def submit_event(
        body: InputEventMutation,
        context: RequestPrincipalContext = Depends(context_provider),  # noqa: B008
    ) -> InputEventResponse:
        try:
            event = InputEvent(
                namespace=context.namespace,
                event_id=body.event_id,
                event_type=body.event_type,
                state=InputEventState.ACCEPTED,
                safe_projection=FrozenJsonObject.from_mapping(body.safe_projection),
                payload_digest=body.payload_digest,
                actor=context.principal,
                correlation_id=body.correlation_id,
                causation_id=body.causation_id,
                occurred_at=body.occurred_at,
                revision=1,
            )
            stored, created = event_service.submit(
                context=context,
                event=event,
                idempotency_key=body.idempotency_key,
            )
            return InputEventResponse(
                event_id=stored.event_id,
                created=created,
                revision=stored.revision,
                state=stored.state.value,
            )
        except ApplicationError as exc:
            raise HTTPException(
                status_code=_status_for(exc),
                detail={"code": type(exc).__name__, "message": "request could not be committed"},
            ) from exc
        except CoreInvariantError as exc:
            raise HTTPException(
                status_code=_core_status(exc),
                detail={"code": "invalid_contract", "message": "request contract is invalid"},
            ) from exc

    @app.post(
        "/proposals/{proposal_id}/approval",
        response_model=ApprovalResponse,
        status_code=201,
    )
    def submit_approval(
        proposal_id: str,
        body: ApprovalMutation,
        context: RequestPrincipalContext = Depends(context_provider),  # noqa: B008
    ) -> ApprovalResponse:
        try:
            decision = HumanApprovalDecision(
                namespace=context.namespace,
                approval_decision_id=body.approval_decision_id,
                proposal_id=proposal_id,
                proposal_revision=body.proposal_revision,
                proposal_payload_digest=body.proposal_payload_digest,
                proposal_digest=body.proposal_digest,
                choice=body.choice,
                author=context.principal,
                idempotency_key=body.idempotency_key,
                correlation_id=store.get_proposal(context.namespace, proposal_id).correlation_id,
                causation_id=proposal_id,
                occurred_at=body.occurred_at,
                valid_until=body.valid_until,
                revision=1,
            )
            stored, attempt_id, created = approval_service.decide(
                context=context,
                mandate_id=body.mandate_id,
                expected_mandate_revision=body.expected_mandate_revision,
                decision=decision,
            )
            return ApprovalResponse(
                approval_decision_id=stored.approval_decision_id,
                attempt_id=attempt_id,
                created=created,
                choice=stored.choice.value,
            )
        except ApplicationError as exc:
            raise HTTPException(
                status_code=_status_for(exc),
                detail={"code": type(exc).__name__, "message": "request could not be committed"},
            ) from exc
        except CoreInvariantError as exc:
            raise HTTPException(
                status_code=_core_status(exc),
                detail={"code": "invalid_contract", "message": "request contract is invalid"},
            ) from exc

    @app.get("/history/{correlation_id}", response_model=HistoryResponse)
    def history(
        correlation_id: str,
        context: RequestPrincipalContext = Depends(context_provider),  # noqa: B008
    ) -> HistoryResponse:
        records = store.causal_history(context.namespace, correlation_id)
        return HistoryResponse(correlation_id=correlation_id, records=list(records))

    return app
