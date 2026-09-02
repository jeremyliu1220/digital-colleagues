# SPDX-License-Identifier: Apache-2.0

"""Framework-neutral P6 governance requests and response records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from digital_colleagues.application.p4_contracts import AuthenticatedSession, SessionGrant
from digital_colleagues.core.common import (
    SCHEMA_VERSION,
    require_digest,
    require_revision,
    require_schema_version,
    require_stable_id,
)
from digital_colleagues.core.governance import (
    ChangeChoice,
    ChangeDecision,
    ChangeProposal,
    GovernanceCredential,
    Membership,
)
from digital_colleagues.core.principals import HumanRole


@dataclass(frozen=True, slots=True)
class EnrollmentAuthorizationRequest:
    role: HumanRole
    colleague_ids: tuple[str, ...]
    idempotency_key: str
    approved_change_decision_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.role, HumanRole):
            raise ValueError("enrollment role must be canonical")
        if not self.colleague_ids:
            raise ValueError("enrollment requires explicit scope")
        for colleague_id in self.colleague_ids:
            if colleague_id != "*":
                require_stable_id(colleague_id, "colleague_id")
        require_stable_id(self.idempotency_key, "idempotency_key")
        if self.approved_change_decision_id is not None:
            require_stable_id(
                self.approved_change_decision_id,
                "approved_change_decision_id",
            )


@dataclass(frozen=True, slots=True)
class RecoveryAuthorizationRequest:
    principal_id: str
    idempotency_key: str

    def __post_init__(self) -> None:
        require_stable_id(self.principal_id, "principal_id")
        require_stable_id(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True, slots=True)
class ChangeDecisionRequest:
    proposal_revision: int
    proposal_digest: str
    choice: ChangeChoice
    idempotency_key: str

    def __post_init__(self) -> None:
        require_revision(self.proposal_revision, "proposal_revision")
        require_digest(self.proposal_digest, "proposal_digest")
        if not isinstance(self.choice, ChangeChoice):
            raise ValueError("change decision choice must be explicit")
        require_stable_id(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True, slots=True)
class GovernanceSession:
    session: AuthenticatedSession
    membership: Membership
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.session.principal.namespace.require_exact(self.membership.namespace)
        if self.session.role_revision != self.membership.role_revision:
            raise ValueError("session role revision is stale")
        if self.session.membership_revision != self.membership.membership_revision:
            raise ValueError("session membership revision is stale")


@dataclass(frozen=True, slots=True)
class CredentialGrant:
    credential: GovernanceCredential
    session_grant: SessionGrant
    membership: Membership
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        if self.credential.consumed_principal_id != self.membership.principal_id:
            raise ValueError("credential grant principal binding is incomplete")
        if self.session_grant.session.principal.principal_id != self.membership.principal_id:
            raise ValueError("session grant principal binding is incomplete")


@dataclass(frozen=True, slots=True)
class P6StudioSnapshot:
    session: AuthenticatedSession
    membership: Membership
    credentials: tuple[GovernanceCredential, ...]
    change_proposals: tuple[ChangeProposal, ...]
    change_decisions: tuple[ChangeDecision, ...]
    bootstrap_transition_state: str | None
    generated_at: datetime
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.session.principal.namespace.require_exact(self.membership.namespace)
        if self.bootstrap_transition_state not in {None, "available", "consumed"}:
            raise ValueError("bootstrap transition state is unsupported")
