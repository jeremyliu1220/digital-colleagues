# SPDX-License-Identifier: Apache-2.0

"""Pure package trust and isolated ColleagueDeployment lifecycle values."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from digital_colleagues.core.agent_package import AgentPackage, PackageSource
from digital_colleagues.core.authority import Mandate, Profile
from digital_colleagues.core.common import (
    SCHEMA_VERSION,
    FrozenJsonObject,
    require_digest,
    require_revision,
    require_schema_version,
    require_stable_id,
    require_utc,
)
from digital_colleagues.core.errors import AuthorizationError, CoreInvariantError
from digital_colleagues.core.namespace import Namespace, NamespaceScope
from digital_colleagues.core.policy import ColleaguePolicy
from digital_colleagues.core.principals import Principal, PrincipalKind


class PackageTrustState(StrEnum):
    UNTRUSTED = "untrusted"
    TRUSTED = "trusted"
    REVOKED = "revoked"
    LEGACY_PRESERVED = "legacy_preserved"


class PackageInstallState(StrEnum):
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"


class AttestationVerification(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    VERIFIED = "verified"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class DeploymentLifecycle(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"
    RETIRED = "retired"


class DeploymentDraftKind(StrEnum):
    CREATE = "create"
    UPGRADE = "upgrade"
    ROLLBACK = "rollback"


class DeploymentDraftState(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    CONFIRMED = "confirmed"
    STALE = "stale"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class GitHubAttestation:
    verification: AttestationVerification
    artifact_digest: str
    signer: str
    signer_digest: str
    repository: str
    workflow: str
    build_identity: str
    source_ref: str
    source_digest: str
    predicate_type: str
    verified_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.verification, AttestationVerification):
            raise CoreInvariantError("attestation verification result is unsupported")
        require_digest(self.artifact_digest, "artifact_digest")
        require_digest(self.signer_digest, "signer_digest")
        for value, field in (
            (self.signer, "signer"),
            (self.repository, "repository"),
            (self.workflow, "workflow"),
            (self.build_identity, "build_identity"),
            (self.source_ref, "source_ref"),
            (self.source_digest, "source_digest"),
            (self.predicate_type, "predicate_type"),
        ):
            if not isinstance(value, str) or not value.strip() or len(value) > 512:
                raise CoreInvariantError(f"{field} must be bounded attestation metadata")
        require_utc(self.verified_at, "verified_at")


@dataclass(frozen=True, slots=True)
class PackageRecord:
    namespace: Namespace
    package: AgentPackage
    package_digest: str
    archive_digest: str
    source: PackageSource
    trust_state: PackageTrustState
    install_state: PackageInstallState
    attestation: GitHubAttestation | None
    created_by: Principal
    created_at: datetime
    updated_at: datetime
    correlation_id: str
    causation_id: str
    revision: int = 1
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        if self.namespace.scope is not NamespaceScope.TENANT:
            raise CoreInvariantError("package record requires a tenant namespace")
        if not isinstance(self.package, AgentPackage):
            raise CoreInvariantError("package record requires a validated package")
        require_digest(self.package_digest, "package_digest")
        require_digest(self.archive_digest, "archive_digest")
        if self.package.package_digest != self.package_digest:
            raise CoreInvariantError("package record digest binding is invalid")
        if not isinstance(self.source, PackageSource):
            raise CoreInvariantError("package source is unsupported")
        if not isinstance(self.trust_state, PackageTrustState) or not isinstance(
            self.install_state, PackageInstallState
        ):
            raise CoreInvariantError("package lifecycle state is unsupported")
        if self.source is PackageSource.GITHUB_RELEASE:
            if (
                self.attestation is None
                or self.attestation.verification is not AttestationVerification.VERIFIED
            ):
                raise CoreInvariantError("GitHub Release package requires verified provenance")
            if self.attestation.artifact_digest != self.archive_digest:
                raise CoreInvariantError("attestation does not bind the exact archive")
        elif self.attestation is not None:
            raise CoreInvariantError("non-GitHub package cannot carry GitHub attestation")
        if self.created_by.kind not in {PrincipalKind.HUMAN, PrincipalKind.SERVICE}:
            raise AuthorizationError("package creator principal kind is unsupported")
        self.namespace.require_same_tenant(self.created_by.namespace)
        require_utc(self.created_at, "created_at")
        require_utc(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            raise CoreInvariantError("package update precedes creation")
        require_stable_id(self.correlation_id, "correlation_id")
        require_stable_id(self.causation_id, "causation_id")
        require_revision(self.revision)


@dataclass(frozen=True, slots=True)
class DeploymentDraft:
    namespace: Namespace
    draft_id: str
    kind: DeploymentDraftKind
    package_id: str
    package_version: str
    package_digest: str
    profile: Profile
    mandate: Mandate
    policy: ColleaguePolicy
    base_deployment_revision: int
    permission_diff: FrozenJsonObject
    canonical_digest: str
    state: DeploymentDraftState
    author: Principal
    created_at: datetime
    updated_at: datetime
    correlation_id: str
    causation_id: str
    revision: int = 1
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.namespace.require_colleague()
        require_stable_id(self.draft_id, "deployment draft id")
        if not isinstance(self.kind, DeploymentDraftKind):
            raise CoreInvariantError("deployment draft kind is unsupported")
        require_stable_id(self.package_id, "package_id")
        if not isinstance(self.package_version, str) or not self.package_version:
            raise CoreInvariantError("package version is missing")
        require_digest(self.package_digest, "package_digest")
        self.namespace.require_exact(self.profile.namespace)
        self.namespace.require_exact(self.mandate.namespace)
        self.namespace.require_exact(self.policy.namespace)
        if self.policy.mandate_id != self.mandate.mandate_id:
            raise CoreInvariantError("deployment Policy does not bind its Mandate")
        if type(self.base_deployment_revision) is not int or self.base_deployment_revision < 0:
            raise CoreInvariantError("base deployment revision must be non-negative")
        if not isinstance(self.permission_diff, FrozenJsonObject):
            raise CoreInvariantError("deployment permission diff must be immutable JSON")
        require_digest(self.canonical_digest, "canonical_digest")
        if not isinstance(self.state, DeploymentDraftState):
            raise CoreInvariantError("deployment draft state is unsupported")
        if self.author.kind is not PrincipalKind.HUMAN:
            raise AuthorizationError("deployment draft author must be HUMAN")
        self.namespace.require_same_tenant(self.author.namespace)
        require_utc(self.created_at, "created_at")
        require_utc(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            raise CoreInvariantError("deployment draft update precedes creation")
        require_stable_id(self.correlation_id, "correlation_id")
        require_stable_id(self.causation_id, "causation_id")
        require_revision(self.revision)


@dataclass(frozen=True, slots=True)
class ColleagueDeployment:
    namespace: Namespace
    deployment_id: str
    package_id: str
    package_version: str
    package_digest: str
    profile_id: str
    profile_revision: int
    mandate_id: str
    mandate_revision: int
    policy_id: str | None
    policy_revision: int | None
    lifecycle: DeploymentLifecycle
    execution_host_id: str
    legacy_manual: bool
    legacy_policy_unconfirmed: bool
    future_connection_slot: None
    updated_by: Principal
    created_at: datetime
    updated_at: datetime
    correlation_id: str
    causation_id: str
    revision: int = 1
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.namespace.require_colleague()
        require_stable_id(self.deployment_id, "deployment_id")
        if self.namespace.scope_id != self.deployment_id:
            raise CoreInvariantError("deployment namespace and identity differ")
        for value, field in (
            (self.package_id, "package_id"),
            (self.profile_id, "profile_id"),
            (self.mandate_id, "mandate_id"),
            (self.execution_host_id, "execution_host_id"),
        ):
            require_stable_id(value, field)
        if not isinstance(self.package_version, str) or not self.package_version:
            raise CoreInvariantError("deployment package version is missing")
        require_digest(self.package_digest, "package_digest")
        require_revision(self.profile_revision, "profile_revision")
        require_revision(self.mandate_revision, "mandate_revision")
        if (self.policy_id is None) != (self.policy_revision is None):
            raise CoreInvariantError("deployment Policy binding is partial")
        if self.policy_id is not None:
            require_stable_id(self.policy_id, "policy_id")
            assert self.policy_revision is not None
            require_revision(self.policy_revision, "policy_revision")
        if not isinstance(self.lifecycle, DeploymentLifecycle):
            raise CoreInvariantError("deployment lifecycle is unsupported")
        if type(self.legacy_manual) is not bool or type(self.legacy_policy_unconfirmed) is not bool:
            raise CoreInvariantError("legacy deployment markers must be boolean")
        if self.legacy_policy_unconfirmed and not self.legacy_manual:
            raise CoreInvariantError("only a legacy deployment may lack a confirmed Policy")
        if self.future_connection_slot is not None:
            raise CoreInvariantError("P11 connection/grant slot must remain empty")
        if self.updated_by.kind not in {PrincipalKind.HUMAN, PrincipalKind.SERVICE}:
            raise AuthorizationError("deployment actor kind is unsupported")
        self.namespace.require_same_tenant(self.updated_by.namespace)
        require_utc(self.created_at, "created_at")
        require_utc(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            raise CoreInvariantError("deployment update precedes creation")
        require_stable_id(self.correlation_id, "correlation_id")
        require_stable_id(self.causation_id, "causation_id")
        require_revision(self.revision)


@dataclass(frozen=True, slots=True)
class LifecycleTransitionResult:
    deployment: ColleagueDeployment
    accepted: bool
    result: str
    active_count: int
    active_limit: int = 10
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        if type(self.accepted) is not bool:
            raise CoreInvariantError("lifecycle result marker must be boolean")
        if self.result not in {"transition_applied", "active_deployment_limit_reached"}:
            raise CoreInvariantError("lifecycle result is unsupported")
        if type(self.active_count) is not int or not 0 <= self.active_count <= self.active_limit:
            raise CoreInvariantError("active deployment count is invalid")


ALLOWED_LIFECYCLE_TRANSITIONS: dict[DeploymentLifecycle, frozenset[DeploymentLifecycle]] = {
    DeploymentLifecycle.DRAFT: frozenset({DeploymentLifecycle.ACTIVE, DeploymentLifecycle.RETIRED}),
    DeploymentLifecycle.ACTIVE: frozenset(
        {DeploymentLifecycle.PAUSED, DeploymentLifecycle.BLOCKED, DeploymentLifecycle.RETIRED}
    ),
    DeploymentLifecycle.PAUSED: frozenset(
        {DeploymentLifecycle.ACTIVE, DeploymentLifecycle.BLOCKED, DeploymentLifecycle.RETIRED}
    ),
    DeploymentLifecycle.BLOCKED: frozenset(
        {DeploymentLifecycle.PAUSED, DeploymentLifecycle.RETIRED}
    ),
    DeploymentLifecycle.RETIRED: frozenset(),
}
