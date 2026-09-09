# SPDX-License-Identifier: Apache-2.0

"""Stable P11 package, attestation, and deployment persistence ports."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from digital_colleagues.application.p11_contracts import GitHubAttestationPolicy
from digital_colleagues.core.deployment import (
    ColleagueDeployment,
    DeploymentDraft,
    GitHubAttestation,
    LifecycleTransitionResult,
    PackageRecord,
)
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import Principal


class GitHubAttestationVerificationPort(Protocol):
    def verify(
        self,
        *,
        artifact: bytes,
        artifact_digest: str,
        bundle: bytes,
        policy: GitHubAttestationPolicy,
    ) -> GitHubAttestation: ...


class P11PersistencePort(Protocol):
    def registration_replay(
        self,
        *,
        namespace: Namespace,
        actor: Principal,
        package_id: str,
        version: str,
        digest: str,
        idempotency_key: str,
        request_digest: str,
    ) -> PackageRecord | None: ...

    def register_package(self, record: PackageRecord, *, idempotency_key: str) -> PackageRecord: ...

    def get_package(
        self, tenant_id: str, package_id: str, version: str, digest: str
    ) -> PackageRecord: ...

    def list_packages(self, tenant_id: str) -> tuple[PackageRecord, ...]: ...

    def change_package_state(
        self,
        *,
        record: PackageRecord,
        actor: Principal,
        action: str,
        expected_revision: int,
        idempotency_key: str,
        request_digest: str,
    ) -> PackageRecord: ...

    def deployment_draft_replay(
        self,
        *,
        namespace: Namespace,
        actor: Principal,
        kind: str,
        draft_id: str,
        idempotency_key: str,
        request_digest: str,
    ) -> DeploymentDraft | None: ...

    def create_deployment_draft(
        self, draft: DeploymentDraft, *, idempotency_key: str, request_digest: str
    ) -> DeploymentDraft: ...

    def get_deployment_draft(self, namespace: Namespace, draft_id: str) -> DeploymentDraft: ...

    def list_deployment_drafts(self, tenant_id: str) -> tuple[DeploymentDraft, ...]: ...

    def review_deployment_draft(
        self,
        *,
        draft: DeploymentDraft,
        expected_revision: int,
        idempotency_key: str,
        request_digest: str,
    ) -> DeploymentDraft: ...

    def confirm_deployment_draft(
        self,
        *,
        draft: DeploymentDraft,
        expected_revision: int,
        idempotency_key: str,
        request_digest: str,
        model_principal: Principal,
        service_principal: Principal,
    ) -> ColleagueDeployment: ...

    def get_deployment(self, namespace: Namespace) -> ColleagueDeployment: ...

    def list_deployments(self, tenant_id: str) -> tuple[ColleagueDeployment, ...]: ...

    def transition_deployment(
        self,
        *,
        namespace: Namespace,
        target: str,
        actor: Principal,
        expected_revision: int,
        expected_package_digest: str,
        idempotency_key: str,
        request_digest: str,
        occurred_at: datetime,
        correlation_id: str,
        causation_id: str,
    ) -> LifecycleTransitionResult: ...

    def package_in_history(
        self, namespace: Namespace, package_id: str, version: str, digest: str
    ) -> bool: ...

    def audit_for_deployment(
        self, namespace: Namespace, *, limit: int = 100
    ) -> tuple[dict[str, object], ...]: ...

    def deployment_is_active(self, namespace: Namespace) -> bool: ...
