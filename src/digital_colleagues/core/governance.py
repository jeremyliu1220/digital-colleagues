# SPDX-License-Identifier: Apache-2.0

"""Pure P6 local-governance records and finite authorization vocabulary."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from digital_colleagues.core.common import (
    SCHEMA_VERSION,
    FrozenJsonObject,
    freeze_strings,
    require_digest,
    require_revision,
    require_schema_version,
    require_stable_id,
    require_utc,
)
from digital_colleagues.core.errors import AuthorizationError, CoreInvariantError
from digital_colleagues.core.namespace import Namespace, NamespaceScope
from digital_colleagues.core.principals import HumanRole, Principal, PrincipalKind


class AuthorizationAction(StrEnum):
    READ_SESSION_SECURITY = "read_session_security"
    READ_COLLEAGUE = "read_colleague"
    READ_GOVERNANCE = "read_governance"
    ASSIGN_WORK = "assign_work"
    SUBMIT_TRIGGER = "submit_trigger"
    PROCESS_RUNTIME = "process_runtime"
    DECIDE_EFFECT = "decide_effect"
    MANAGE_DRAFT = "manage_draft"
    PROPOSE_CHANGE = "propose_change"
    DECIDE_CHANGE = "decide_change"
    APPLY_CHANGE = "apply_change"
    MANAGE_CREDENTIAL = "manage_credential"
    MANAGE_MEMBERSHIP = "manage_membership"
    EXPORT_AUDIT = "export_audit"
    READ_AGENT_PACKAGES = "read_agent_packages"
    MANAGE_AGENT_PACKAGES = "manage_agent_packages"
    READ_DEPLOYMENTS = "read_deployments"
    MANAGE_DEPLOYMENTS = "manage_deployments"
    SELECT_DEPLOYMENT = "select_deployment"
    READ_DEPLOYMENT_AUDIT = "read_deployment_audit"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True)
class Membership:
    namespace: Namespace
    membership_id: str
    principal_id: str
    roles: tuple[HumanRole, ...]
    colleague_ids: tuple[str, ...]
    status: MembershipStatus
    role_revision: int
    membership_revision: int
    issued_by: Principal
    created_at: datetime
    updated_at: datetime
    correlation_id: str
    causation_id: str
    revision: int = 1
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        require_stable_id(self.membership_id, "membership_id")
        require_stable_id(self.principal_id, "principal_id")
        self.namespace.require_principal(self.principal_id)
        roles = tuple(self.roles)
        if not roles or len(roles) != len(set(roles)):
            raise CoreInvariantError("membership roles must be non-empty and unique")
        if any(not isinstance(role, HumanRole) for role in roles):
            raise CoreInvariantError("membership roles must be canonical")
        colleague_ids = tuple(self.colleague_ids)
        if not colleague_ids or len(colleague_ids) != len(set(colleague_ids)):
            raise CoreInvariantError("membership colleague scopes must be non-empty and unique")
        if "*" in colleague_ids:
            if colleague_ids != ("*",) or HumanRole.TENANT_ADMIN not in roles:
                raise AuthorizationError("only an Admin may have the tenant governance scope")
        else:
            for colleague_id in colleague_ids:
                require_stable_id(colleague_id, "colleague_id")
        if not isinstance(self.status, MembershipStatus):
            raise CoreInvariantError("membership status must be explicit")
        require_revision(self.role_revision, "role_revision")
        require_revision(self.membership_revision, "membership_revision")
        if self.issued_by.kind is not PrincipalKind.HUMAN:
            raise AuthorizationError("membership issuer must be a durable human")
        self.namespace.require_same_tenant(self.issued_by.namespace)
        require_utc(self.created_at, "created_at")
        require_utc(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            raise CoreInvariantError("membership update cannot precede creation")
        require_stable_id(self.correlation_id, "correlation_id")
        require_stable_id(self.causation_id, "causation_id")
        require_revision(self.revision)
        object.__setattr__(self, "roles", roles)
        object.__setattr__(self, "colleague_ids", colleague_ids)

    def allows_namespace(self, namespace: Namespace) -> bool:
        self.namespace.require_same_tenant(namespace)
        if self.status is not MembershipStatus.ACTIVE:
            return False
        if namespace.scope is NamespaceScope.TENANT:
            return self.colleague_ids == ("*",)
        if namespace.scope is NamespaceScope.PRINCIPAL:
            return namespace.scope_id == self.principal_id
        return self.colleague_ids == ("*",) or namespace.scope_id in self.colleague_ids


class CredentialKind(StrEnum):
    ENROLLMENT = "enrollment"
    RECOVERY = "recovery"


class CredentialState(StrEnum):
    AUTHORIZED = "authorized"
    RETRIEVED = "retrieved"
    CONSUMED = "consumed"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class GovernanceCredential:
    namespace: Namespace
    credential_id: str
    kind: CredentialKind
    state: CredentialState
    target_principal_id: str | None
    target_role_revision: int | None
    target_membership_revision: int | None
    target_role: HumanRole | None
    colleague_ids: tuple[str, ...]
    bootstrap_transition: bool
    issued_by_principal_id: str
    issued_at: datetime
    expires_at: datetime
    correlation_id: str
    causation_id: str
    token_digest: str | None = field(default=None, repr=False)
    change_decision_id: str | None = None
    retrieved_at: datetime | None = None
    consumed_at: datetime | None = None
    revoked_at: datetime | None = None
    consumed_principal_id: str | None = None
    revision: int = 1
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        if self.namespace.scope is not NamespaceScope.TENANT:
            raise CoreInvariantError("governance credential requires a tenant namespace")
        require_stable_id(self.credential_id, "credential_id")
        if not isinstance(self.kind, CredentialKind) or not isinstance(self.state, CredentialState):
            raise CoreInvariantError("credential kind and state must be explicit")
        if self.kind is CredentialKind.ENROLLMENT:
            if (
                self.target_role is None
                or self.target_principal_id is not None
                or self.target_role_revision is not None
                or self.target_membership_revision is not None
            ):
                raise CoreInvariantError("enrollment must fix a role and no existing principal")
        elif (
            self.target_principal_id is None
            or self.target_role is not None
            or self.target_role_revision is None
            or self.target_membership_revision is None
        ):
            raise CoreInvariantError(
                "recovery must fix an existing principal and authority revisions"
            )
        if self.target_principal_id is not None:
            require_stable_id(self.target_principal_id, "target_principal_id")
        if self.target_role_revision is not None:
            require_revision(self.target_role_revision, "target_role_revision")
        if self.target_membership_revision is not None:
            require_revision(self.target_membership_revision, "target_membership_revision")
        scopes = tuple(self.colleague_ids)
        if not scopes or len(scopes) != len(set(scopes)):
            raise CoreInvariantError("credential scopes must be non-empty and unique")
        if "*" in scopes:
            if scopes != ("*",) or self.target_role not in {HumanRole.TENANT_ADMIN, None}:
                raise AuthorizationError("credential tenant scope is restricted to Admin/recovery")
        else:
            for colleague_id in scopes:
                require_stable_id(colleague_id, "colleague_id")
        if type(self.bootstrap_transition) is not bool:
            raise CoreInvariantError("bootstrap transition marker must be boolean")
        if self.bootstrap_transition and (
            self.kind is not CredentialKind.ENROLLMENT
            or self.target_role is not HumanRole.TENANT_ADMIN
        ):
            raise AuthorizationError("bootstrap transition may create only an Admin")
        require_stable_id(self.issued_by_principal_id, "issued_by_principal_id")
        require_utc(self.issued_at, "issued_at")
        require_utc(self.expires_at, "expires_at")
        if self.expires_at <= self.issued_at:
            raise CoreInvariantError("credential expiry must follow issuance")
        if self.token_digest is not None:
            require_digest(self.token_digest, "token_digest")
        if self.change_decision_id is not None:
            require_stable_id(self.change_decision_id, "change_decision_id")
        for value, name in (
            (self.retrieved_at, "retrieved_at"),
            (self.consumed_at, "consumed_at"),
            (self.revoked_at, "revoked_at"),
        ):
            if value is not None:
                require_utc(value, name)
        if self.state is CredentialState.RETRIEVED and (
            self.token_digest is None or self.retrieved_at is None
        ):
            raise CoreInvariantError("retrieved credential binding is incomplete")
        if self.state is CredentialState.CONSUMED and self.consumed_at is None:
            raise CoreInvariantError("consumed credential requires a time")
        if self.state is CredentialState.REVOKED and self.revoked_at is None:
            raise CoreInvariantError("revoked credential requires a time")
        if self.consumed_principal_id is not None:
            require_stable_id(self.consumed_principal_id, "consumed_principal_id")
        require_stable_id(self.correlation_id, "correlation_id")
        require_stable_id(self.causation_id, "causation_id")
        require_revision(self.revision)
        object.__setattr__(self, "colleague_ids", scopes)


class ChangeKind(StrEnum):
    DRAFT = "draft"
    MEMBERSHIP = "membership"
    ADMIN_ENROLLMENT = "admin_enrollment"


class ChangeState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    STALE = "stale"
    APPLIED = "applied"


class ChangeChoice(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


def governance_change_digest(
    *,
    change_kind: ChangeKind,
    target_id: str,
    target_revision: int,
    proposed_role: HumanRole | None,
    proposed_status: MembershipStatus | None,
    proposed_colleague_ids: tuple[str, ...],
) -> str:
    """Return the canonical digest for a non-draft governance authority change."""

    payload = {
        "digest_schema_version": 1,
        "change_kind": change_kind.value,
        "target_id": require_stable_id(target_id, "target_id"),
        "target_revision": require_revision(target_revision, "target_revision"),
        "proposed_role": None if proposed_role is None else proposed_role.value,
        "proposed_status": None if proposed_status is None else proposed_status.value,
        "proposed_colleague_ids": sorted(proposed_colleague_ids),
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ChangeProposal:
    namespace: Namespace
    proposal_id: str
    change_kind: ChangeKind
    target_id: str
    target_revision: int
    canonical_digest: str
    base_profile_revision: int
    base_mandate_revision: int
    base_policy_revision: int
    proposed_role: HumanRole | None
    proposed_status: MembershipStatus | None
    proposed_colleague_ids: tuple[str, ...]
    proposer_principal_id: str
    proposer_role_revision: int
    proposer_membership_revision: int
    issued_at: datetime
    expires_at: datetime
    state: ChangeState
    idempotency_key: str
    request_digest: str
    correlation_id: str
    causation_id: str
    decision_id: str | None = None
    consumed_at: datetime | None = None
    revision: int = 1
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        if self.namespace.scope not in {NamespaceScope.TENANT, NamespaceScope.COLLEAGUE}:
            raise CoreInvariantError("change proposal namespace is unsupported")
        require_stable_id(self.proposal_id, "proposal_id")
        if not isinstance(self.change_kind, ChangeKind):
            raise CoreInvariantError("change kind must be explicit")
        if self.change_kind is ChangeKind.DRAFT:
            self.namespace.require_colleague()
        elif self.namespace.scope is not NamespaceScope.TENANT:
            raise CoreInvariantError("membership changes require the tenant namespace")
        require_stable_id(self.target_id, "target_id")
        require_revision(self.target_revision, "target_revision")
        require_digest(self.canonical_digest, "canonical_digest")
        for value, name in (
            (self.base_profile_revision, "base_profile_revision"),
            (self.base_mandate_revision, "base_mandate_revision"),
            (self.base_policy_revision, "base_policy_revision"),
        ):
            if type(value) is not int or value < 0:
                raise CoreInvariantError(f"{name} must be non-negative")
        scopes = freeze_strings(
            self.proposed_colleague_ids,
            "proposed_colleague_ids",
            allow_empty=self.change_kind is ChangeKind.DRAFT,
        )
        if "*" in scopes and scopes != ("*",):
            raise AuthorizationError("tenant scope cannot be combined with colleague scopes")
        for scope in scopes:
            if scope != "*":
                require_stable_id(scope, "colleague_id")
        require_stable_id(self.proposer_principal_id, "proposer_principal_id")
        require_revision(self.proposer_role_revision, "proposer_role_revision")
        require_revision(self.proposer_membership_revision, "proposer_membership_revision")
        require_utc(self.issued_at, "issued_at")
        require_utc(self.expires_at, "expires_at")
        if self.expires_at <= self.issued_at:
            raise CoreInvariantError("change proposal expiry must follow issuance")
        if not isinstance(self.state, ChangeState):
            raise CoreInvariantError("change state must be explicit")
        require_stable_id(self.idempotency_key, "idempotency_key")
        require_digest(self.request_digest, "request_digest")
        require_stable_id(self.correlation_id, "correlation_id")
        require_stable_id(self.causation_id, "causation_id")
        if self.decision_id is not None:
            require_stable_id(self.decision_id, "decision_id")
        if self.consumed_at is not None:
            require_utc(self.consumed_at, "consumed_at")
        if self.state is ChangeState.APPLIED and self.consumed_at is None:
            raise CoreInvariantError("applied proposal requires consumption time")
        require_revision(self.revision)
        object.__setattr__(self, "proposed_colleague_ids", scopes)


@dataclass(frozen=True, slots=True)
class ChangeDecision:
    namespace: Namespace
    decision_id: str
    proposal_id: str
    proposal_revision: int
    proposal_digest: str
    choice: ChangeChoice
    approver_principal_id: str
    approver_role_revision: int
    approver_membership_revision: int
    occurred_at: datetime
    valid_until: datetime
    idempotency_key: str
    request_digest: str
    correlation_id: str
    causation_id: str
    consumed_at: datetime | None = None
    revision: int = 1
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        require_stable_id(self.decision_id, "decision_id")
        require_stable_id(self.proposal_id, "proposal_id")
        require_revision(self.proposal_revision, "proposal_revision")
        require_digest(self.proposal_digest, "proposal_digest")
        if not isinstance(self.choice, ChangeChoice):
            raise CoreInvariantError("change choice must be explicit")
        require_stable_id(self.approver_principal_id, "approver_principal_id")
        require_revision(self.approver_role_revision, "approver_role_revision")
        require_revision(self.approver_membership_revision, "approver_membership_revision")
        require_utc(self.occurred_at, "occurred_at")
        require_utc(self.valid_until, "valid_until")
        if self.valid_until < self.occurred_at:
            raise CoreInvariantError("change decision expiry precedes its decision")
        require_stable_id(self.idempotency_key, "idempotency_key")
        require_digest(self.request_digest, "request_digest")
        require_stable_id(self.correlation_id, "correlation_id")
        require_stable_id(self.causation_id, "causation_id")
        if self.causation_id != self.proposal_id:
            raise CoreInvariantError("change decision must cite its proposal")
        if self.consumed_at is not None:
            require_utc(self.consumed_at, "consumed_at")
        require_revision(self.revision)


@dataclass(frozen=True, slots=True)
class AuditExportQuery:
    namespace: Namespace
    start_at: datetime
    end_at: datetime
    record_types: tuple[str, ...]
    limit: int
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        require_utc(self.start_at, "start_at")
        require_utc(self.end_at, "end_at")
        if self.end_at < self.start_at:
            raise CoreInvariantError("audit export range is inverted")
        record_types = freeze_strings(self.record_types, "record_types", allow_empty=False)
        if "audit_export" in record_types:
            raise AuthorizationError("audit export records cannot recursively export themselves")
        if type(self.limit) is not int or not 1 <= self.limit <= 500:
            raise CoreInvariantError("audit export limit must be between 1 and 500")
        object.__setattr__(self, "record_types", record_types)


@dataclass(frozen=True, slots=True)
class AuditExportRecord:
    namespace: Namespace
    record_type: str
    record_id: str
    record_revision: int
    action: str
    result: str
    actor_principal_id: str
    actor_kind: PrincipalKind
    authority_revision: str
    correlation_id: str
    causation_id: str
    occurred_at: datetime
    safe_digest: str
    safe_projection: FrozenJsonObject
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        for value, name in (
            (self.record_type, "record_type"),
            (self.record_id, "record_id"),
            (self.action, "action"),
            (self.result, "result"),
            (self.actor_principal_id, "actor_principal_id"),
            (self.authority_revision, "authority_revision"),
            (self.correlation_id, "correlation_id"),
            (self.causation_id, "causation_id"),
        ):
            require_stable_id(value, name)
        require_revision(self.record_revision, "record_revision")
        if not isinstance(self.actor_kind, PrincipalKind):
            raise CoreInvariantError("audit actor kind must be explicit")
        require_utc(self.occurred_at, "occurred_at")
        require_digest(self.safe_digest, "safe_digest")
        if not isinstance(self.safe_projection, FrozenJsonObject):
            raise CoreInvariantError("audit safe projection must be immutable JSON")
