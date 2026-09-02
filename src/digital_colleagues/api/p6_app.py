# SPDX-License-Identifier: Apache-2.0

"""Typed FastAPI mapping edge for P6 local governance."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Self

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from digital_colleagues.api.p4_app import SESSION_COOKIE
from digital_colleagues.application.errors import PermissionDeniedError
from digital_colleagues.application.p4_contracts import AuthenticatedSession
from digital_colleagues.application.p6_contracts import (
    ChangeDecisionRequest,
    EnrollmentAuthorizationRequest,
    RecoveryAuthorizationRequest,
)
from digital_colleagues.application.p6_ports import GovernancePersistencePort
from digital_colleagues.application.p6_services import (
    P6AuditService,
    P6AuthenticationService,
    P6ChangeService,
    governance_action_matrix,
)
from digital_colleagues.core.governance import (
    AuditExportQuery,
    AuthorizationAction,
    ChangeChoice,
    MembershipStatus,
)
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import HumanRole
from digital_colleagues.core.serialization import contract_to_public_data, datetime_to_z


class _StrictMutation(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EnrollmentScopeMutation(_StrictMutation):
    colleague_ids: list[str] = Field(min_length=1, max_length=32)
    idempotency_key: str = Field(min_length=1, max_length=128)


class AdminEnrollmentMutation(_StrictMutation):
    approved_change_decision_id: str | None = Field(default=None, min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)


class CredentialExchangeMutation(_StrictMutation):
    token: str = Field(min_length=32, max_length=256)


class RecoveryMutation(_StrictMutation):
    principal_id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)


class ActiveColleagueMutation(_StrictMutation):
    colleague_id: str = Field(min_length=1, max_length=128)


class DraftChangeMutation(_StrictMutation):
    draft_revision: int = Field(gt=0)
    canonical_digest: str = Field(pattern="^sha256:[0-9a-f]{64}$")
    idempotency_key: str = Field(min_length=1, max_length=128)


class MembershipChangeMutation(_StrictMutation):
    target_principal_id: str = Field(min_length=1, max_length=128)
    proposed_role: HumanRole
    proposed_status: MembershipStatus
    proposed_colleague_ids: list[str] = Field(min_length=1, max_length=32)
    idempotency_key: str = Field(min_length=1, max_length=128)


class ChangeDecisionMutation(_StrictMutation):
    proposal_revision: int = Field(gt=0)
    proposal_digest: str = Field(pattern="^sha256:[0-9a-f]{64}$")
    choice: ChangeChoice
    idempotency_key: str = Field(min_length=1, max_length=128)


class ApplyChangeMutation(_StrictMutation):
    decision_id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)


class AuditExportMutation(_StrictMutation):
    start_at: datetime
    end_at: datetime
    record_types: list[str] = Field(min_length=1, max_length=24)
    limit: int = Field(gt=0, le=500)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError("audit export timestamps must be timezone-aware")
        return self


def _membership_data(value: object) -> dict[str, object]:
    raw = contract_to_public_data(value)
    assert isinstance(raw, dict)
    return raw


def _credential_data(value: object) -> dict[str, object]:
    raw = contract_to_public_data(value)
    assert isinstance(raw, dict)
    for secret_field in ("token_digest", "credential_digest", "csrf_digest"):
        raw.pop(secret_field, None)
    return raw


def _session_data(
    session: AuthenticatedSession, csrf_token: str, membership: object
) -> dict[str, object]:
    assert session.expires_at is not None
    return {
        "authenticated": True,
        "principal": {
            "principal_id": session.principal.principal_id,
            "kind": session.principal.kind.value,
            "roles": [role.value for role in session.principal.roles],
            "role_revision": session.role_revision,
        },
        "membership": _membership_data(membership),
        "active_colleague_id": session.active_colleague_id,
        "membership_revision": session.membership_revision,
        "session_revision": session.revision,
        "expires_at": datetime_to_z(session.expires_at),
        "csrf_token": csrf_token,
    }


def install_p6_routes(
    app: FastAPI,
    *,
    authentication: P6AuthenticationService,
    changes: P6ChangeService,
    audit: P6AuditService,
    store: GovernancePersistencePort,
    expected_origin: str,
    secure_cookie: bool = False,
) -> None:
    """Install P6 routes and authorization for every retained P4/P5 route."""

    def cookie(request: Request) -> str:
        value = request.cookies.get(SESSION_COOKIE, "")
        if not value:
            raise HTTPException(
                status_code=401,
                detail={"code": "session_required", "message": "authentication required"},
            )
        return value

    def read_session(request: Request) -> AuthenticatedSession:
        return authentication.resolve(cookie(request))

    def mutation_session(request: Request) -> AuthenticatedSession:
        return authentication.authorize_mutation(
            session_credential=cookie(request),
            origin=request.headers.get("origin"),
            csrf_token=request.headers.get("x-csrf-token"),
            expected_origin=expected_origin,
        )

    @app.middleware("http")
    async def retained_route_authorization(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        action: AuthorizationAction | None = None
        tenant_scope = False
        if path == "/auth/session":
            action = AuthorizationAction.READ_SESSION_SECURITY
            tenant_scope = True
        elif path in {"/studio/state", "/evaluation/metrics"}:
            action = AuthorizationAction.READ_COLLEAGUE
        elif path == "/p5/studio/state":
            action = AuthorizationAction.READ_COLLEAGUE
        elif path.startswith("/audit/"):
            action = AuthorizationAction.READ_GOVERNANCE
        elif path == "/work":
            action = AuthorizationAction.ASSIGN_WORK
        elif path == "/runtime/triggers":
            action = AuthorizationAction.SUBMIT_TRIGGER
        elif path == "/runtime/process":
            action = AuthorizationAction.PROCESS_RUNTIME
        elif path.startswith("/proposals/"):
            action = AuthorizationAction.DECIDE_EFFECT
        elif path == "/colleagues" or path == "/colleagues/preview":
            action = AuthorizationAction.MANAGE_DRAFT
            tenant_scope = path == "/colleagues"
        elif path.startswith("/colleagues/drafts"):
            action = (
                AuthorizationAction.READ_GOVERNANCE
                if request.method == "GET"
                else AuthorizationAction.MANAGE_DRAFT
            )
        if action is not None:
            try:
                session = read_session(request)
                namespace = (
                    Namespace.tenant(session.tenant_id)
                    if tenant_scope
                    else session.colleague_namespace()
                )
                authentication.authorize(
                    session=session,
                    action=action,
                    namespace=namespace,
                )
            except HTTPException as error:
                return JSONResponse(
                    status_code=error.status_code,
                    content={"detail": error.detail},
                )
            except (PermissionDeniedError, ValueError):
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": {
                            "code": "PermissionDeniedError",
                            "message": "request refused",
                        }
                    },
                )
        return await call_next(request)

    @app.post("/auth/enrollment/exchange", status_code=201)
    def exchange_enrollment(
        body: CredentialExchangeMutation, request: Request, response: Response
    ) -> dict[str, object]:
        if request.headers.get("origin") != expected_origin:
            raise PermissionDeniedError("enrollment Origin was refused")
        grant = authentication.exchange_enrollment(body.token)
        session = grant.session_grant.session
        assert session.created_at is not None and session.expires_at is not None
        response.set_cookie(
            key=SESSION_COOKIE,
            value=grant.session_grant.session_credential,
            httponly=True,
            secure=secure_cookie,
            samesite="strict",
            path="/",
            max_age=max(1, int((session.expires_at - session.created_at).total_seconds())),
        )
        return _session_data(session, grant.session_grant.csrf_token, grant.membership)

    @app.get("/governance/rbac")
    def rbac(request: Request) -> dict[str, object]:
        session = read_session(request)
        user_session = HumanRole.COLLEAGUE_USER in session.principal.roles
        authentication.authorize(
            session=session,
            action=(
                AuthorizationAction.READ_SESSION_SECURITY
                if user_session
                else AuthorizationAction.READ_GOVERNANCE
            ),
            namespace=(
                Namespace.principal(session.tenant_id, session.principal.principal_id)
                if user_session
                else (
                    Namespace.tenant(session.tenant_id)
                    if HumanRole.TENANT_ADMIN in session.principal.roles
                    else session.colleague_namespace()
                )
            ),
        )
        return {"schema_version": 1, "roles": governance_action_matrix()}

    @app.get("/governance/state")
    def governance_state(request: Request) -> dict[str, object]:
        session = read_session(request)
        user_session = HumanRole.COLLEAGUE_USER in session.principal.roles
        namespace = (
            Namespace.principal(session.tenant_id, session.principal.principal_id)
            if user_session
            else (
                Namespace.tenant(session.tenant_id)
                if session.active_colleague_id is None
                else session.colleague_namespace()
            )
        )
        authentication.authorize(
            session=session,
            action=(
                AuthorizationAction.READ_SESSION_SECURITY
                if user_session
                else AuthorizationAction.READ_GOVERNANCE
            ),
            namespace=namespace,
        )
        snapshot = store.p6_studio_snapshot(session=session, evaluated_at=authentication.now())
        assert snapshot.session.expires_at is not None
        return {
            "state": "ready",
            "session": {
                "session_id": snapshot.session.session_id,
                "revision": snapshot.session.revision,
                "role_revision": snapshot.session.role_revision,
                "membership_revision": snapshot.session.membership_revision,
                "expires_at": datetime_to_z(snapshot.session.expires_at),
            },
            "membership": _membership_data(snapshot.membership),
            "bootstrap_transition_state": snapshot.bootstrap_transition_state,
            "credentials": [_credential_data(item) for item in snapshot.credentials],
            "change_proposals": [
                contract_to_public_data(item) for item in snapshot.change_proposals
            ],
            "change_decisions": [
                contract_to_public_data(item) for item in snapshot.change_decisions
            ],
            "generated_at": datetime_to_z(snapshot.generated_at),
        }

    @app.post("/governance/session/active-colleague")
    def set_active_colleague(body: ActiveColleagueMutation, request: Request) -> dict[str, object]:
        session = mutation_session(request)
        updated = authentication.bind_colleague(session, body.colleague_id)
        return {
            "active_colleague_id": updated.active_colleague_id,
            "session_revision": updated.revision,
        }

    def authorize_enrollment(
        *,
        session: AuthenticatedSession,
        role: HumanRole,
        colleague_ids: tuple[str, ...],
        idempotency_key: str,
        decision_id: str | None = None,
    ) -> dict[str, object]:
        credential = authentication.authorize_enrollment(
            session=session,
            request=EnrollmentAuthorizationRequest(
                role=role,
                colleague_ids=colleague_ids,
                idempotency_key=idempotency_key,
                approved_change_decision_id=decision_id,
            ),
        )
        return {"credential": _credential_data(credential), "plaintext_returned": False}

    @app.post("/governance/enrollments/users", status_code=201)
    def authorize_user_enrollment(
        body: EnrollmentScopeMutation, request: Request
    ) -> dict[str, object]:
        return authorize_enrollment(
            session=mutation_session(request),
            role=HumanRole.COLLEAGUE_USER,
            colleague_ids=tuple(body.colleague_ids),
            idempotency_key=body.idempotency_key,
        )

    @app.post("/governance/enrollments/auditors", status_code=201)
    def authorize_auditor_enrollment(
        body: EnrollmentScopeMutation, request: Request
    ) -> dict[str, object]:
        return authorize_enrollment(
            session=mutation_session(request),
            role=HumanRole.AUDITOR,
            colleague_ids=tuple(body.colleague_ids),
            idempotency_key=body.idempotency_key,
        )

    @app.post("/governance/enrollments/admins", status_code=201)
    def authorize_admin_enrollment(
        body: AdminEnrollmentMutation, request: Request
    ) -> dict[str, object]:
        return authorize_enrollment(
            session=mutation_session(request),
            role=HumanRole.TENANT_ADMIN,
            colleague_ids=("*",),
            idempotency_key=body.idempotency_key,
            decision_id=body.approved_change_decision_id,
        )

    @app.post("/governance/recovery", status_code=201)
    def authorize_recovery(body: RecoveryMutation, request: Request) -> dict[str, object]:
        credential = authentication.authorize_recovery(
            session=mutation_session(request),
            request=RecoveryAuthorizationRequest(
                principal_id=body.principal_id,
                idempotency_key=body.idempotency_key,
            ),
        )
        return {"credential": _credential_data(credential), "plaintext_returned": False}

    @app.post("/governance/credentials/{credential_id}/revoke")
    def revoke_credential(credential_id: str, request: Request) -> dict[str, object]:
        session = mutation_session(request)
        authentication.authorize(
            session=session,
            action=AuthorizationAction.MANAGE_CREDENTIAL,
            namespace=Namespace.tenant(session.tenant_id),
        )
        credential = store.revoke_credential(
            tenant_id=session.tenant_id,
            credential_id=credential_id,
            actor=session.principal,
            occurred_at=authentication.now(),
        )
        return {"credential": _credential_data(credential)}

    @app.post("/governance/drafts/{draft_id}/proposals", status_code=201)
    def propose_draft_change(
        draft_id: str, body: DraftChangeMutation, request: Request
    ) -> dict[str, object]:
        proposal = changes.propose_draft(
            session=mutation_session(request),
            draft_id=draft_id,
            expected_revision=body.draft_revision,
            expected_digest=body.canonical_digest,
            idempotency_key=body.idempotency_key,
        )
        return {"proposal": contract_to_public_data(proposal)}

    @app.post("/governance/memberships/proposals", status_code=201)
    def propose_membership_change(
        body: MembershipChangeMutation, request: Request
    ) -> dict[str, object]:
        proposal = changes.propose_membership(
            session=mutation_session(request),
            target_principal_id=body.target_principal_id,
            role=body.proposed_role,
            status=body.proposed_status,
            colleague_ids=tuple(body.proposed_colleague_ids),
            idempotency_key=body.idempotency_key,
        )
        return {"proposal": contract_to_public_data(proposal)}

    @app.post("/governance/admin-enrollments/proposals", status_code=201)
    def propose_admin_enrollment(
        body: AdminEnrollmentMutation, request: Request
    ) -> dict[str, object]:
        proposal = changes.propose_admin_enrollment(
            session=mutation_session(request), idempotency_key=body.idempotency_key
        )
        return {"proposal": contract_to_public_data(proposal)}

    def change_namespace(session: AuthenticatedSession, scope: str) -> Namespace:
        if scope == "tenant":
            return Namespace.tenant(session.tenant_id)
        if scope == "colleague":
            return session.colleague_namespace()
        raise PermissionDeniedError("change namespace was refused")

    @app.post("/governance/changes/{scope}/{proposal_id}/decision", status_code=201)
    def decide_change(
        scope: str,
        proposal_id: str,
        body: ChangeDecisionMutation,
        request: Request,
    ) -> dict[str, object]:
        session = mutation_session(request)
        proposal, decision = changes.decide(
            session=session,
            namespace=change_namespace(session, scope),
            proposal_id=proposal_id,
            request=ChangeDecisionRequest(
                proposal_revision=body.proposal_revision,
                proposal_digest=body.proposal_digest,
                choice=body.choice,
                idempotency_key=body.idempotency_key,
            ),
        )
        return {
            "proposal": contract_to_public_data(proposal),
            "decision": contract_to_public_data(decision),
        }

    @app.post("/governance/changes/colleague/{proposal_id}/apply")
    def apply_draft_change(
        proposal_id: str, body: ApplyChangeMutation, request: Request
    ) -> dict[str, object]:
        session = mutation_session(request)
        result = changes.apply_draft(
            session=session,
            namespace=session.colleague_namespace(),
            proposal_id=proposal_id,
            decision_id=body.decision_id,
            idempotency_key=body.idempotency_key,
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

    @app.post("/governance/changes/tenant/{proposal_id}/apply")
    def apply_membership_change(
        proposal_id: str, body: ApplyChangeMutation, request: Request
    ) -> dict[str, object]:
        session = mutation_session(request)
        membership = changes.apply_membership(
            session=session,
            proposal_id=proposal_id,
            decision_id=body.decision_id,
        )
        return {"membership": _membership_data(membership)}

    @app.post("/governance/audit/export")
    def export_audit(body: AuditExportMutation, request: Request) -> dict[str, object]:
        session = mutation_session(request)
        records = audit.export(
            session=session,
            query=AuditExportQuery(
                namespace=session.colleague_namespace(),
                start_at=body.start_at,
                end_at=body.end_at,
                record_types=tuple(body.record_types),
                limit=body.limit,
            ),
        )
        return {
            "schema_version": 1,
            "namespace": contract_to_public_data(session.colleague_namespace()),
            "ordering": ["occurred_at", "record_type", "record_id", "revision"],
            "bounded": True,
            "records": [contract_to_public_data(item) for item in records],
        }
