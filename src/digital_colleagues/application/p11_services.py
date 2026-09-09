# SPDX-License-Identifier: Apache-2.0

"""P11 package trust, deployment draft, and lifecycle application services."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

from digital_colleagues.adapters.package.archive import validate_package_archive
from digital_colleagues.application.errors import PermissionDeniedError, StaleConflictError
from digital_colleagues.application.p4_contracts import AuthenticatedSession
from digital_colleagues.application.p5_contracts import PolicyEdit
from digital_colleagues.application.p5_services import _policy_from_edit
from digital_colleagues.application.p6_services import P6AuthenticationService
from digital_colleagues.application.p11_contracts import (
    DeploymentCreationRequest,
    ExactDraftConfirmation,
    ExactLifecycleRequest,
    ExactRebindingRequest,
    PackageInspection,
    PackageRegistrationRequest,
    permission_diff,
)
from digital_colleagues.application.p11_ports import (
    GitHubAttestationVerificationPort,
    P11PersistencePort,
)
from digital_colleagues.application.ports import ClockPort, IdentifierPort
from digital_colleagues.core.agent_package import ALLOWED_CAPABILITIES, PackageSource
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
from digital_colleagues.core.deployment import (
    ColleagueDeployment,
    DeploymentDraft,
    DeploymentDraftKind,
    DeploymentDraftState,
    LifecycleTransitionResult,
    PackageInstallState,
    PackageRecord,
    PackageTrustState,
)
from digital_colleagues.core.effects import ApprovalChoice, EffectProposal
from digital_colleagues.core.governance import AuthorizationAction
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import Principal
from digital_colleagues.core.serialization import contract_to_public_data


def _digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return "sha256:" + hashlib.sha256(encoded.encode()).hexdigest()


class P11PackageService:
    def __init__(
        self,
        *,
        store: P11PersistencePort,
        authentication: P6AuthenticationService,
        attestation: GitHubAttestationVerificationPort,
        clock: ClockPort,
        identifiers: IdentifierPort,
    ) -> None:
        self._store = store
        self._authentication = authentication
        self._attestation = attestation
        self._clock = clock
        self._identifiers = identifiers

    @staticmethod
    def inspect(archive: bytes, *, expected_archive_digest: str | None = None) -> PackageInspection:
        validated = validate_package_archive(
            archive,
            expected_archive_digest=expected_archive_digest,
        )
        return PackageInspection(
            package=validated.package,
            package_digest=validated.package_digest,
            archive_digest=validated.archive_digest,
            compressed_size=validated.compressed_size,
            uncompressed_size=validated.uncompressed_size,
        )

    def catalog(self, session: AuthenticatedSession) -> tuple[PackageRecord, ...]:
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.READ_AGENT_PACKAGES,
            namespace=Namespace.tenant(session.tenant_id),
        )
        return self._store.list_packages(session.tenant_id)

    def register(
        self,
        *,
        session: AuthenticatedSession,
        request: PackageRegistrationRequest,
        idempotency_key: str,
    ) -> PackageRecord:
        namespace = Namespace.tenant(session.tenant_id)
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.MANAGE_AGENT_PACKAGES,
            namespace=namespace,
        )
        inspection = self.inspect(
            request.archive,
            expected_archive_digest=request.expected_archive_digest,
        )
        request_digest = _digest(
            {
                "archive_digest": inspection.archive_digest,
                "package_digest": inspection.package_digest,
                "source": request.source.value,
            }
        )
        replay = self._store.registration_replay(
            namespace=namespace,
            actor=session.principal,
            package_id=inspection.package.package_id,
            version=inspection.package.version,
            digest=inspection.package_digest,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
        )
        if replay is not None:
            return replay
        verified = None
        if request.source is PackageSource.GITHUB_RELEASE:
            assert request.attestation_bundle is not None and request.github_policy is not None
            verified = self._attestation.verify(
                artifact=request.archive,
                artifact_digest=inspection.archive_digest,
                bundle=request.attestation_bundle,
                policy=request.github_policy,
            )
        now = self._clock.now()
        record = PackageRecord(
            namespace=namespace,
            package=inspection.package,
            package_digest=inspection.package_digest,
            archive_digest=inspection.archive_digest,
            source=request.source,
            trust_state=PackageTrustState.UNTRUSTED,
            install_state=PackageInstallState.NOT_INSTALLED,
            attestation=verified,
            created_by=session.principal,
            created_at=now,
            updated_at=now,
            correlation_id=self._identifiers.derive("p11-package", inspection.package_digest),
            causation_id=self._identifiers.derive("p11-register", idempotency_key),
        )
        return self._store.register_package(record, idempotency_key=idempotency_key)

    def _mutate(
        self,
        *,
        session: AuthenticatedSession,
        package_id: str,
        version: str,
        digest: str,
        expected_revision: int,
        idempotency_key: str,
        action: str,
    ) -> PackageRecord:
        namespace = Namespace.tenant(session.tenant_id)
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.MANAGE_AGENT_PACKAGES,
            namespace=namespace,
        )
        current = self._store.get_package(session.tenant_id, package_id, version, digest)
        if action == "trust":
            trust_state = PackageTrustState.TRUSTED
            install_state = current.install_state
        elif action == "revoke":
            trust_state = PackageTrustState.REVOKED
            install_state = current.install_state
        elif action == "install":
            trust_state = current.trust_state
            install_state = PackageInstallState.INSTALLED
        else:
            raise ValueError("package mutation is unsupported")
        now = self._clock.now()
        updated = replace(
            current,
            trust_state=trust_state,
            install_state=install_state,
            updated_at=now,
            causation_id=self._identifiers.derive("p11-package-action", action, idempotency_key),
            revision=current.revision + 1,
        )
        request_digest = _digest(
            {
                "action": action,
                "package_id": package_id,
                "version": version,
                "digest": digest,
                "expected_revision": expected_revision,
            }
        )
        return self._store.change_package_state(
            record=updated,
            actor=session.principal,
            action=action,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
        )

    def trust(self, **values: object) -> PackageRecord:
        return self._mutate(action="trust", **values)  # type: ignore[arg-type]

    def revoke(self, **values: object) -> PackageRecord:
        return self._mutate(action="revoke", **values)  # type: ignore[arg-type]

    def install(self, **values: object) -> PackageRecord:
        return self._mutate(action="install", **values)  # type: ignore[arg-type]


class P11DeploymentService:
    def __init__(
        self,
        *,
        store: P11PersistencePort,
        authentication: P6AuthenticationService,
        clock: ClockPort,
        identifiers: IdentifierPort,
    ) -> None:
        self._store = store
        self._authentication = authentication
        self._clock = clock
        self._identifiers = identifiers

    def list(self, session: AuthenticatedSession) -> tuple[ColleagueDeployment, ...]:
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.READ_DEPLOYMENTS,
            namespace=Namespace.tenant(session.tenant_id),
        )
        return self._store.list_deployments(session.tenant_id)

    def list_drafts(self, session: AuthenticatedSession) -> tuple[DeploymentDraft, ...]:
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.READ_DEPLOYMENTS,
            namespace=Namespace.tenant(session.tenant_id),
        )
        return self._store.list_deployment_drafts(session.tenant_id)

    def _package_ready(
        self, tenant_id: str, package_id: str, version: str, digest: str
    ) -> PackageRecord:
        package = self._store.get_package(tenant_id, package_id, version, digest)
        if (
            package.trust_state is not PackageTrustState.TRUSTED
            or package.install_state is not PackageInstallState.INSTALLED
        ):
            raise PermissionDeniedError("deployment requires a trusted installed exact package")
        return package

    def create_draft(
        self, *, session: AuthenticatedSession, request: DeploymentCreationRequest
    ) -> DeploymentDraft:
        namespace = Namespace.colleague(session.tenant_id, request.deployment_id)
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.MANAGE_DEPLOYMENTS,
            namespace=Namespace.tenant(session.tenant_id),
        )
        draft_id = self._identifiers.derive(
            "deployment-draft", request.deployment_id, request.idempotency_key
        )
        request_digest = _digest(
            {
                "kind": "create",
                "deployment_id": request.deployment_id,
                "package_id": request.package_id,
                "package_version": request.package_version,
                "package_digest": request.package_digest,
                "display_name": request.display_name,
                "description": request.description,
                "mission": request.mission,
                "service_relationship": request.service_relationship,
                "granted_capabilities": request.granted_capabilities,
                "timezone": request.timezone,
            }
        )
        replay = self._store.deployment_draft_replay(
            namespace=namespace,
            actor=session.principal,
            kind=DeploymentDraftKind.CREATE.value,
            draft_id=draft_id,
            idempotency_key=request.idempotency_key,
            request_digest=request_digest,
        )
        if replay is not None:
            return replay
        package = self._package_ready(
            session.tenant_id,
            request.package_id,
            request.package_version,
            request.package_digest,
        )
        grants = request.granted_capabilities
        if not grants or any(value not in ALLOWED_CAPABILITIES for value in grants):
            raise PermissionDeniedError("Admin grants must use the finite capability vocabulary")
        effect_map = {
            "propose_reference_message": EffectKind.REFERENCE_MESSAGE,
            "propose_internal_record": EffectKind.INTERNAL_RECORD,
            "notify_human": EffectKind.NOTIFICATION,
        }
        effect_kinds = tuple(effect_map[value] for value in grants if value in effect_map)
        if not effect_kinds:
            raise PermissionDeniedError("a deployment requires an explicit bounded effect boundary")
        now = self._clock.now()
        profile_id = self._identifiers.derive("profile", request.deployment_id)
        mandate_id = self._identifiers.derive("mandate", request.deployment_id)
        policy_id = self._identifiers.derive("policy", request.deployment_id)
        profile = Profile(
            namespace=namespace,
            profile_id=profile_id,
            display_name=request.display_name,
            description=request.description,
            presentation=FrozenJsonObject.from_mapping({"package_id": package.package.package_id}),
            revision=1,
            updated_by=session.principal,
            updated_at=now,
        )
        mandate = Mandate(
            namespace=namespace,
            mandate_id=mandate_id,
            mission=request.mission,
            service_relationship=request.service_relationship,
            responsibilities=(
                ResponsibilityDefinition(
                    responsibility_id="package-work",
                    description="Perform finite assigned work within the confirmed mandate.",
                    obligations=("Respect exact namespace and policy.",),
                    completion_conditions=("Finite work reaches a terminal state.",),
                ),
            ),
            capabilities=tuple(
                CapabilityGrant(capability_id=value, description=f"Admin-confirmed {value} grant.")
                for value in grants
            ),
            constraints=(
                Constraint(
                    constraint_id="package-boundary",
                    description="Package requests do not grant authority or bypass approval.",
                ),
            ),
            working_context=FrozenJsonObject.from_mapping(
                {"package_digest": package.package_digest, "runtime_api": "1"}
            ),
            effect_boundaries=tuple(
                EffectBoundary(
                    boundary_id=f"package-{kind.value}",
                    effect_kind=kind,
                    allowed_destination_kinds=("reference",),
                    allowed_actions=("propose",),
                    constraints=FrozenJsonObject.from_mapping(
                        {"package_digest": package.package_digest}
                    ),
                    human_approval_required=True,
                )
                for kind in effect_kinds
            ),
            revision=1,
            issued_by=session.principal,
            effective_at=now,
        )
        policy, _ = _policy_from_edit(
            namespace=namespace,
            policy_id=policy_id,
            revision=1,
            mandate_id=mandate_id,
            mandate_revision=1,
            actor=session.principal,
            occurred_at=now,
            edit=PolicyEdit(timezone=request.timezone),
        )
        diff = permission_diff(
            package.package,
            grants,
            binding={
                "profile_id": profile_id,
                "profile_revision": 1,
                "mandate_id": mandate_id,
                "mandate_revision": 1,
                "policy_id": policy_id,
                "policy_revision": 1,
            },
        )
        canonical = _digest(
            {
                "draft_id": draft_id,
                "kind": "create",
                "package_digest": package.package_digest,
                "profile": contract_to_public_data(profile),
                "mandate": contract_to_public_data(mandate),
                "policy": contract_to_public_data(policy),
                "permission_diff": contract_to_public_data(diff),
            }
        )
        draft = DeploymentDraft(
            namespace=namespace,
            draft_id=draft_id,
            kind=DeploymentDraftKind.CREATE,
            package_id=package.package.package_id,
            package_version=package.package.version,
            package_digest=package.package_digest,
            profile=profile,
            mandate=mandate,
            policy=policy,
            base_deployment_revision=0,
            permission_diff=diff,
            canonical_digest=canonical,
            state=DeploymentDraftState.DRAFT,
            author=session.principal,
            created_at=now,
            updated_at=now,
            correlation_id=self._identifiers.derive("p11-deployment", request.deployment_id),
            causation_id=self._identifiers.derive("p11-create", request.idempotency_key),
        )
        return self._store.create_deployment_draft(
            draft,
            idempotency_key=request.idempotency_key,
            request_digest=request_digest,
        )

    def rebinding_draft(
        self,
        *,
        session: AuthenticatedSession,
        deployment_id: str,
        request: ExactRebindingRequest,
        kind: DeploymentDraftKind,
    ) -> DeploymentDraft:
        namespace = Namespace.colleague(session.tenant_id, deployment_id)
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.MANAGE_DEPLOYMENTS,
            namespace=namespace,
        )
        draft_id = self._identifiers.derive(
            "deployment-draft", deployment_id, kind.value, request.idempotency_key
        )
        request_digest = _digest(
            {
                "kind": kind.value,
                "deployment_id": deployment_id,
                "package_id": request.package_id,
                "package_version": request.package_version,
                "package_digest": request.package_digest,
                "expected_deployment_revision": request.expected_deployment_revision,
            }
        )
        replay = self._store.deployment_draft_replay(
            namespace=namespace,
            actor=session.principal,
            kind=kind.value,
            draft_id=draft_id,
            idempotency_key=request.idempotency_key,
            request_digest=request_digest,
        )
        if replay is not None:
            return replay
        deployment = self._store.get_deployment(namespace)
        if deployment.revision != request.expected_deployment_revision:
            raise StaleConflictError("deployment rebinding revision is stale")
        if deployment.package_digest == request.package_digest:
            raise PermissionDeniedError("deployment rebinding requires a different package digest")
        package = self._package_ready(
            session.tenant_id,
            request.package_id,
            request.package_version,
            request.package_digest,
        )
        if kind is DeploymentDraftKind.ROLLBACK and not self._store.package_in_history(
            namespace, request.package_id, request.package_version, request.package_digest
        ):
            raise PermissionDeniedError("rollback target is not in accepted deployment history")
        profile = self._store.get_profile(namespace, deployment.profile_id)  # type: ignore[attr-defined]
        mandate = self._store.get_mandate(namespace, deployment.mandate_id)  # type: ignore[attr-defined]
        policy = self._store.get_active_policy(namespace)  # type: ignore[attr-defined]
        if policy is None:
            raise PermissionDeniedError("legacy deployment Policy remains unconfirmed")
        grants = tuple(item.capability_id for item in mandate.capabilities)
        diff = permission_diff(
            package.package,
            grants,
            binding={
                "profile_id": profile.profile_id,
                "profile_revision": profile.revision,
                "mandate_id": mandate.mandate_id,
                "mandate_revision": mandate.revision,
                "policy_id": policy.policy_id,
                "policy_revision": policy.revision,
                "from_package_digest": deployment.package_digest,
            },
        )
        now = self._clock.now()
        canonical = _digest(
            {
                "draft_id": draft_id,
                "kind": kind.value,
                "package_digest": package.package_digest,
                "permission_diff": contract_to_public_data(diff),
            }
        )
        draft = DeploymentDraft(
            namespace=namespace,
            draft_id=draft_id,
            kind=kind,
            package_id=package.package.package_id,
            package_version=package.package.version,
            package_digest=package.package_digest,
            profile=profile,
            mandate=mandate,
            policy=policy,
            base_deployment_revision=deployment.revision,
            permission_diff=diff,
            canonical_digest=canonical,
            state=DeploymentDraftState.DRAFT,
            author=session.principal,
            created_at=now,
            updated_at=now,
            correlation_id=self._identifiers.derive("p11-deployment", deployment_id),
            causation_id=self._identifiers.derive("p11-rebinding", request.idempotency_key),
        )
        return self._store.create_deployment_draft(
            draft,
            idempotency_key=request.idempotency_key,
            request_digest=request_digest,
        )

    def review(
        self,
        *,
        session: AuthenticatedSession,
        deployment_id: str,
        draft_id: str,
        request: ExactDraftConfirmation,
    ) -> DeploymentDraft:
        namespace = Namespace.colleague(session.tenant_id, deployment_id)
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.MANAGE_DEPLOYMENTS,
            namespace=namespace,
        )
        draft = self._store.get_deployment_draft(namespace, draft_id)
        if draft.canonical_digest != request.expected_canonical_digest:
            raise StaleConflictError("deployment draft review binding is stale")
        updated = replace(draft, author=session.principal, updated_at=self._clock.now())
        return self._store.review_deployment_draft(
            draft=updated,
            expected_revision=request.expected_revision,
            idempotency_key=request.idempotency_key,
            request_digest=_digest(
                {
                    "action": "review",
                    "draft_id": draft_id,
                    "revision": request.expected_revision,
                    "canonical_digest": request.expected_canonical_digest,
                }
            ),
        )

    def confirm(
        self,
        *,
        session: AuthenticatedSession,
        deployment_id: str,
        draft_id: str,
        request: ExactDraftConfirmation,
    ) -> ColleagueDeployment:
        namespace = Namespace.colleague(session.tenant_id, deployment_id)
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.MANAGE_DEPLOYMENTS,
            namespace=namespace,
        )
        draft = self._store.get_deployment_draft(namespace, draft_id)
        if draft.canonical_digest != request.expected_canonical_digest:
            raise StaleConflictError("deployment draft confirmation binding is stale")
        now = self._clock.now()
        updated = replace(draft, author=session.principal, updated_at=now)
        return self._store.confirm_deployment_draft(
            draft=updated,
            expected_revision=request.expected_revision,
            idempotency_key=request.idempotency_key,
            request_digest=_digest(
                {
                    "action": "confirm",
                    "draft_id": draft_id,
                    "revision": request.expected_revision,
                    "canonical_digest": request.expected_canonical_digest,
                }
            ),
            model_principal=Principal.model(
                tenant_id=session.tenant_id,
                principal_id=self._identifiers.derive("model", deployment_id),
            ),
            service_principal=Principal.service(
                tenant_id=session.tenant_id,
                principal_id=self._identifiers.derive("service", deployment_id),
            ),
        )

    def transition(
        self,
        *,
        session: AuthenticatedSession,
        deployment_id: str,
        request: ExactLifecycleRequest,
    ) -> LifecycleTransitionResult:
        namespace = Namespace.colleague(session.tenant_id, deployment_id)
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.MANAGE_DEPLOYMENTS,
            namespace=namespace,
        )
        if request.target not in {
            "draft",
            "active",
            "paused",
            "blocked",
            "retired",
        }:
            raise PermissionDeniedError("deployment lifecycle target is unsupported")
        now = self._clock.now()
        return self._store.transition_deployment(
            namespace=namespace,
            target=request.target,
            actor=session.principal,
            expected_revision=request.expected_revision,
            expected_package_digest=request.expected_package_digest,
            idempotency_key=request.idempotency_key,
            request_digest=_digest(
                {
                    "target": request.target,
                    "expected_revision": request.expected_revision,
                    "expected_package_digest": request.expected_package_digest,
                }
            ),
            occurred_at=now,
            correlation_id=self._identifiers.derive("p11-deployment", deployment_id),
            causation_id=self._identifiers.derive("p11-lifecycle", request.idempotency_key),
        )

    def audit(
        self, *, session: AuthenticatedSession, deployment_id: str
    ) -> tuple[dict[str, object], ...]:
        namespace = Namespace.colleague(session.tenant_id, deployment_id)
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.READ_DEPLOYMENT_AUDIT,
            namespace=namespace,
        )
        return self._store.audit_for_deployment(namespace)

    def select(
        self,
        *,
        session: AuthenticatedSession,
        deployment_id: str,
        idempotency_key: str,
    ) -> AuthenticatedSession:
        namespace = Namespace.colleague(session.tenant_id, deployment_id)
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.SELECT_DEPLOYMENT,
            namespace=namespace,
        )
        self._store.get_deployment(namespace)
        return self._authentication.bind_colleague(
            session,
            deployment_id,
            idempotency_key=idempotency_key,
        )


class P11RuntimeController:
    """Fail closed before any inactive deployment reaches retained runtime code."""

    def __init__(self, *, inner: object, store: P11PersistencePort) -> None:
        self._inner = inner
        self._store = store

    def _require_active(self, namespace: Namespace) -> None:
        if not self._store.deployment_is_active(namespace):
            raise PermissionDeniedError("deployment is not active")

    def service_context(self, namespace: Namespace) -> object:
        self._require_active(namespace)
        return self._inner.service_context(namespace)  # type: ignore[attr-defined]

    def submit_trigger(self, *, session: AuthenticatedSession, **values: object) -> object:
        self._require_active(session.colleague_namespace())
        return self._inner.submit_trigger(session=session, **values)  # type: ignore[attr-defined]

    def process_once(self, context: object) -> dict[str, object]:
        namespace = getattr(context, "namespace", None)
        if not isinstance(namespace, Namespace):
            raise PermissionDeniedError("runtime context namespace is invalid")
        self._require_active(namespace)
        return self._inner.process_once(context)  # type: ignore[attr-defined,no-any-return]

    def decide_proposal(
        self,
        *,
        session: AuthenticatedSession,
        proposal: EffectProposal,
        choice: ApprovalChoice,
        **values: object,
    ) -> object:
        self._require_active(proposal.namespace)
        return self._inner.decide_proposal(  # type: ignore[attr-defined]
            session=session,
            proposal=proposal,
            choice=choice,
            **values,
        )
