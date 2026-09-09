# SPDX-License-Identifier: Apache-2.0

"""Strict FastAPI edge for P11 package and deployment operations."""

from __future__ import annotations

import base64
import binascii
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from digital_colleagues.api.p4_app import SESSION_COOKIE
from digital_colleagues.application.errors import ValidationError
from digital_colleagues.application.p6_services import P6AuthenticationService
from digital_colleagues.application.p11_contracts import (
    DeploymentCreationRequest,
    ExactDraftConfirmation,
    ExactLifecycleRequest,
    ExactRebindingRequest,
    GitHubAttestationPolicy,
    PackageRegistrationRequest,
)
from digital_colleagues.application.p11_services import (
    P11DeploymentService,
    P11PackageService,
)
from digital_colleagues.core.agent_package import AgentPackage, PackageSource
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.deployment import DeploymentDraftKind


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ArchiveMutation(_Strict):
    archive_base64: str = Field(min_length=4, max_length=180_000)
    expected_archive_digest: str = Field(pattern="^sha256:[0-9a-f]{64}$")


class ValidateMutation(ArchiveMutation):
    pass


class GitHubPolicyMutation(_Strict):
    repository: str = Field(min_length=1, max_length=512)
    signer_workflow: str = Field(min_length=1, max_length=512)
    signer_digest: str = Field(pattern="^sha256:[0-9a-f]{64}$")
    source_ref: str = Field(min_length=1, max_length=512)
    source_digest: str = Field(pattern="^sha256:[0-9a-f]{64}$")
    build_identity: str = Field(min_length=1, max_length=512)


class RegisterMutation(ArchiveMutation):
    source: PackageSource
    idempotency_key: str = Field(min_length=1, max_length=128)
    attestation_bundle_base64: str | None = Field(default=None, max_length=360_000)
    github_policy: GitHubPolicyMutation | None = None


class ExactPackageMutation(_Strict):
    expected_revision: int = Field(gt=0)
    idempotency_key: str = Field(min_length=1, max_length=128)


class DeploymentDraftMutation(_Strict):
    deployment_id: str = Field(min_length=1, max_length=128)
    package_id: str = Field(min_length=1, max_length=128)
    package_version: str = Field(min_length=1, max_length=32)
    package_digest: str = Field(pattern="^sha256:[0-9a-f]{64}$")
    display_name: str = Field(min_length=1, max_length=256)
    description: str = Field(min_length=1, max_length=4096)
    mission: str = Field(min_length=1, max_length=4096)
    service_relationship: str = Field(min_length=1, max_length=4096)
    granted_capabilities: list[str] = Field(min_length=1, max_length=16)
    timezone: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)


class DraftConfirmationMutation(_Strict):
    deployment_id: str = Field(min_length=1, max_length=128)
    expected_revision: int = Field(gt=0)
    expected_canonical_digest: str = Field(pattern="^sha256:[0-9a-f]{64}$")
    idempotency_key: str = Field(min_length=1, max_length=128)


class LifecycleMutation(_Strict):
    target: str = Field(min_length=1, max_length=32)
    expected_revision: int = Field(gt=0)
    expected_package_digest: str = Field(pattern="^sha256:[0-9a-f]{64}$")
    idempotency_key: str = Field(min_length=1, max_length=128)


class RebindingMutation(_Strict):
    package_id: str = Field(min_length=1, max_length=128)
    package_version: str = Field(min_length=1, max_length=32)
    package_digest: str = Field(pattern="^sha256:[0-9a-f]{64}$")
    expected_deployment_revision: int = Field(gt=0)
    idempotency_key: str = Field(min_length=1, max_length=128)


class SelectMutation(_Strict):
    idempotency_key: str = Field(min_length=1, max_length=128)


def _decode(value: str, *, label: str) -> bytes:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValidationError(f"{label} is not valid base64") from exc
    if not decoded:
        raise ValidationError(f"{label} is empty")
    return decoded


def _public(value: object) -> object:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, datetime):
        return value.isoformat(timespec="microseconds").replace("+00:00", "Z")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, AgentPackage):
        return value.to_data()
    if isinstance(value, FrozenJsonObject):
        return {key: _public(item) for key, item in value.as_entries()}
    if isinstance(value, (tuple, list)):
        return [_public(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _public(item) for key, item in value.items()}
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _public(getattr(value, field.name)) for field in fields(value)}
    raise TypeError("unsupported P11 response value")


def install_p11_routes(
    app: FastAPI,
    *,
    authentication: P6AuthenticationService,
    packages: P11PackageService,
    deployments: P11DeploymentService,
    expected_origin: str,
) -> None:
    """Install the exact stable `/api/v1` P11 surface."""

    def cookie(request: Request) -> str:
        value = request.cookies.get(SESSION_COOKIE, "")
        if not value:
            raise HTTPException(
                status_code=401,
                detail={"code": "session_required", "message": "authentication required"},
            )
        return value

    def read(request: Request):  # type: ignore[no-untyped-def]
        return authentication.resolve(cookie(request))

    def mutate(request: Request):  # type: ignore[no-untyped-def]
        return authentication.authorize_mutation(
            session_credential=cookie(request),
            origin=request.headers.get("origin"),
            csrf_token=request.headers.get("x-csrf-token"),
            expected_origin=expected_origin,
        )

    @app.get("/api/v1/catalog")
    def catalog(request: Request) -> object:
        return _public(packages.catalog(read(request)))

    @app.get("/api/v1/agent-packages")
    def agent_packages(request: Request) -> object:
        return _public(packages.catalog(read(request)))

    @app.post("/api/v1/agent-packages/validate")
    def validate(body: ValidateMutation) -> object:
        return _public(
            packages.inspect(
                _decode(body.archive_base64, label="archive"),
                expected_archive_digest=body.expected_archive_digest,
            )
        )

    @app.post("/api/v1/agent-packages", status_code=201)
    def register(body: RegisterMutation, request: Request) -> object:
        policy = (
            None
            if body.github_policy is None
            else GitHubAttestationPolicy(**body.github_policy.model_dump())
        )
        bundle = (
            None
            if body.attestation_bundle_base64 is None
            else _decode(body.attestation_bundle_base64, label="attestation bundle")
        )
        result = packages.register(
            session=mutate(request),
            request=PackageRegistrationRequest(
                archive=_decode(body.archive_base64, label="archive"),
                source=body.source,
                expected_archive_digest=body.expected_archive_digest,
                attestation_bundle=bundle,
                github_policy=policy,
            ),
            idempotency_key=body.idempotency_key,
        )
        return _public(result)

    def package_action(
        action: str,
        package_id: str,
        version: str,
        digest: str,
        body: ExactPackageMutation,
        request: Request,
    ) -> object:
        operation = getattr(packages, action)
        return _public(
            operation(
                session=mutate(request),
                package_id=package_id,
                version=version,
                digest=digest,
                expected_revision=body.expected_revision,
                idempotency_key=body.idempotency_key,
            )
        )

    @app.post("/api/v1/agent-packages/{package_id}/versions/{version}/{digest}/trust")
    def trust(
        package_id: str, version: str, digest: str, body: ExactPackageMutation, request: Request
    ) -> object:
        return package_action("trust", package_id, version, digest, body, request)

    @app.post("/api/v1/agent-packages/{package_id}/versions/{version}/{digest}/revoke")
    def revoke(
        package_id: str, version: str, digest: str, body: ExactPackageMutation, request: Request
    ) -> object:
        return package_action("revoke", package_id, version, digest, body, request)

    @app.post("/api/v1/agent-packages/{package_id}/versions/{version}/{digest}/install")
    def install(
        package_id: str, version: str, digest: str, body: ExactPackageMutation, request: Request
    ) -> object:
        return package_action("install", package_id, version, digest, body, request)

    @app.get("/api/v1/deployment-drafts")
    def deployment_drafts(request: Request) -> object:
        return _public(deployments.list_drafts(read(request)))

    @app.post("/api/v1/deployment-drafts", status_code=201)
    def create_draft(body: DeploymentDraftMutation, request: Request) -> object:
        return _public(
            deployments.create_draft(
                session=mutate(request),
                request=DeploymentCreationRequest(
                    **body.model_dump(exclude={"granted_capabilities"}),
                    granted_capabilities=tuple(body.granted_capabilities),
                ),
            )
        )

    def draft_action(
        action: str,
        draft_id: str,
        body: DraftConfirmationMutation,
        request: Request,
    ) -> object:
        return _public(
            getattr(deployments, action)(
                session=mutate(request),
                deployment_id=body.deployment_id,
                draft_id=draft_id,
                request=ExactDraftConfirmation(
                    expected_revision=body.expected_revision,
                    expected_canonical_digest=body.expected_canonical_digest,
                    idempotency_key=body.idempotency_key,
                ),
            )
        )

    @app.post("/api/v1/deployment-drafts/{draft_id}/review")
    def review(draft_id: str, body: DraftConfirmationMutation, request: Request) -> object:
        return draft_action("review", draft_id, body, request)

    @app.post("/api/v1/deployment-drafts/{draft_id}/confirm")
    def confirm(draft_id: str, body: DraftConfirmationMutation, request: Request) -> object:
        return draft_action("confirm", draft_id, body, request)

    @app.get("/api/v1/deployments")
    def deployment_registry(request: Request) -> object:
        return _public(deployments.list(read(request)))

    @app.post("/api/v1/deployments/{deployment_id}/lifecycle")
    def lifecycle(deployment_id: str, body: LifecycleMutation, request: Request) -> object:
        return _public(
            deployments.transition(
                session=mutate(request),
                deployment_id=deployment_id,
                request=ExactLifecycleRequest(**body.model_dump()),
            )
        )

    def rebinding(
        kind: DeploymentDraftKind,
        deployment_id: str,
        body: RebindingMutation,
        request: Request,
    ) -> object:
        return _public(
            deployments.rebinding_draft(
                session=mutate(request),
                deployment_id=deployment_id,
                request=ExactRebindingRequest(**body.model_dump()),
                kind=kind,
            )
        )

    @app.post("/api/v1/deployments/{deployment_id}/upgrade-drafts")
    def upgrade(deployment_id: str, body: RebindingMutation, request: Request) -> object:
        return rebinding(DeploymentDraftKind.UPGRADE, deployment_id, body, request)

    @app.post("/api/v1/deployments/{deployment_id}/rollback-drafts")
    def rollback(deployment_id: str, body: RebindingMutation, request: Request) -> object:
        return rebinding(DeploymentDraftKind.ROLLBACK, deployment_id, body, request)

    @app.post("/api/v1/deployments/{deployment_id}/select")
    def select(deployment_id: str, body: SelectMutation, request: Request) -> object:
        result = deployments.select(
            session=mutate(request),
            deployment_id=deployment_id,
            idempotency_key=body.idempotency_key,
        )
        return {
            "deployment_id": result.active_colleague_id,
            "session_revision": result.revision,
            "selected": result.active_colleague_id == deployment_id,
        }

    @app.get("/api/v1/deployments/{deployment_id}/audit")
    def audit(deployment_id: str, request: Request) -> object:
        return _public(deployments.audit(session=read(request), deployment_id=deployment_id))
