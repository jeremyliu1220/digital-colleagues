# SPDX-License-Identifier: Apache-2.0

"""Framework-neutral P11 package and deployment request/result contracts."""

from __future__ import annotations

from dataclasses import dataclass

from digital_colleagues.core.agent_package import AgentPackage, PackageSource
from digital_colleagues.core.common import (
    SCHEMA_VERSION,
    FrozenJsonObject,
    require_digest,
    require_revision,
    require_schema_version,
    require_stable_id,
    require_text,
)
from digital_colleagues.core.deployment import ColleagueDeployment, DeploymentDraft


@dataclass(frozen=True, slots=True)
class GitHubAttestationPolicy:
    repository: str
    signer_workflow: str
    signer_digest: str
    source_ref: str
    source_digest: str
    build_identity: str

    def __post_init__(self) -> None:
        for value, field in (
            (self.repository, "repository"),
            (self.signer_workflow, "signer_workflow"),
            (self.source_ref, "source_ref"),
            (self.build_identity, "build_identity"),
        ):
            require_text(value, field, maximum=512)
        require_digest(self.signer_digest, "signer_digest")
        require_digest(self.source_digest, "source_digest")


@dataclass(frozen=True, slots=True)
class PackageInspection:
    package: AgentPackage
    package_digest: str
    archive_digest: str
    compressed_size: int
    uncompressed_size: int
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        require_digest(self.package_digest, "package_digest")
        require_digest(self.archive_digest, "archive_digest")
        if self.package.package_digest != self.package_digest:
            raise ValueError("inspection digest binding is invalid")
        if min(self.compressed_size, self.uncompressed_size) < 1:
            raise ValueError("inspection sizes must be positive")


@dataclass(frozen=True, slots=True)
class PackageRegistrationRequest:
    archive: bytes
    source: PackageSource
    expected_archive_digest: str
    attestation_bundle: bytes | None = None
    github_policy: GitHubAttestationPolicy | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.archive, bytes) or not self.archive:
            raise ValueError("package archive is required")
        if not isinstance(self.source, PackageSource):
            raise ValueError("package source is unsupported")
        require_digest(self.expected_archive_digest, "expected_archive_digest")
        github = self.source is PackageSource.GITHUB_RELEASE
        supplied = (self.attestation_bundle is not None, self.github_policy is not None)
        if (github and supplied != (True, True)) or (not github and supplied != (False, False)):
            raise ValueError("GitHub source requires an exact offline attestation binding")


@dataclass(frozen=True, slots=True)
class DeploymentCreationRequest:
    deployment_id: str
    package_id: str
    package_version: str
    package_digest: str
    display_name: str
    description: str
    mission: str
    service_relationship: str
    granted_capabilities: tuple[str, ...]
    timezone: str
    idempotency_key: str

    def __post_init__(self) -> None:
        for value, field in (
            (self.deployment_id, "deployment_id"),
            (self.package_id, "package_id"),
            (self.idempotency_key, "idempotency_key"),
        ):
            require_stable_id(value, field)
        for value, field in (
            (self.package_version, "package_version"),
            (self.display_name, "display_name"),
            (self.description, "description"),
            (self.mission, "mission"),
            (self.service_relationship, "service_relationship"),
            (self.timezone, "timezone"),
        ):
            require_text(value, field)
        require_digest(self.package_digest, "package_digest")
        grants = tuple(self.granted_capabilities)
        if len(grants) != len(set(grants)):
            raise ValueError("granted capabilities must be unique")
        object.__setattr__(self, "granted_capabilities", tuple(sorted(grants)))


@dataclass(frozen=True, slots=True)
class ExactDraftConfirmation:
    expected_revision: int
    expected_canonical_digest: str
    idempotency_key: str

    def __post_init__(self) -> None:
        require_revision(self.expected_revision, "expected_revision")
        require_digest(self.expected_canonical_digest, "expected_canonical_digest")
        require_stable_id(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True, slots=True)
class ExactLifecycleRequest:
    target: str
    expected_revision: int
    expected_package_digest: str
    idempotency_key: str

    def __post_init__(self) -> None:
        require_text(self.target, "target", maximum=32)
        require_revision(self.expected_revision, "expected_revision")
        require_digest(self.expected_package_digest, "expected_package_digest")
        require_stable_id(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True, slots=True)
class ExactRebindingRequest:
    package_id: str
    package_version: str
    package_digest: str
    expected_deployment_revision: int
    idempotency_key: str

    def __post_init__(self) -> None:
        require_stable_id(self.package_id, "package_id")
        require_text(self.package_version, "package_version", maximum=32)
        require_digest(self.package_digest, "package_digest")
        require_revision(self.expected_deployment_revision, "expected_deployment_revision")
        require_stable_id(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True, slots=True)
class P11StudioSnapshot:
    packages: tuple[object, ...]
    drafts: tuple[DeploymentDraft, ...]
    deployments: tuple[ColleagueDeployment, ...]
    selected_deployment_id: str | None
    active_count: int
    active_limit: int = 10
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        if not 0 <= self.active_count <= self.active_limit:
            raise ValueError("active deployment count is invalid")
        if self.selected_deployment_id is not None:
            require_stable_id(self.selected_deployment_id, "selected_deployment_id")


def permission_diff(
    package: AgentPackage,
    granted_capabilities: tuple[str, ...],
    *,
    binding: dict[str, object],
) -> FrozenJsonObject:
    """Keep requested capabilities visibly separate from human-issued grants."""

    requested = set(package.requested_capabilities)
    granted = set(granted_capabilities)
    return FrozenJsonObject.from_mapping(
        {
            "requested": sorted(requested),
            "granted": sorted(granted),
            "admin_extra": sorted(granted - requested),
            "not_granted": sorted(requested - granted),
            "binding": binding,
        }
    )
