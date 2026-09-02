# SPDX-License-Identifier: Apache-2.0

"""Stable ports for P6 local governance persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from digital_colleagues.application.p4_contracts import AuthenticatedSession
from digital_colleagues.application.p6_contracts import P6StudioSnapshot
from digital_colleagues.core.governance import (
    AuditExportQuery,
    AuditExportRecord,
    ChangeDecision,
    ChangeProposal,
    GovernanceCredential,
    Membership,
)
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import HumanRole, Principal


class GovernancePersistencePort(Protocol):
    def get_principal(self, tenant_id: str, principal_id: str) -> Principal: ...

    def governed_session(
        self, *, credential_digest: str, evaluated_at: datetime
    ) -> tuple[AuthenticatedSession, Membership]: ...

    def set_active_colleague_replay(
        self,
        *,
        session: AuthenticatedSession,
        colleague_id: str,
        idempotency_key: str,
        request_digest: str,
        occurred_at: datetime,
    ) -> AuthenticatedSession: ...

    def membership_for_principal(self, tenant_id: str, principal_id: str) -> Membership: ...

    def authorize_enrollment(
        self,
        *,
        credential: GovernanceCredential,
        issuer_membership: Membership,
    ) -> GovernanceCredential: ...

    def authorize_recovery(
        self,
        *,
        credential: GovernanceCredential,
        issuer_membership: Membership,
    ) -> GovernanceCredential: ...

    def find_governance_credential(
        self, *, tenant_id: str, credential_id: str
    ) -> GovernanceCredential | None: ...

    def claim_credential_secret(
        self,
        *,
        credential_id: str,
        token_digest: str,
        occurred_at: datetime,
    ) -> GovernanceCredential: ...

    def credential_by_digest(self, *, token_digest: str, kind: str) -> GovernanceCredential: ...

    def expire_credential(
        self, *, credential: GovernanceCredential, occurred_at: datetime
    ) -> GovernanceCredential: ...

    def revoke_credential(
        self,
        *,
        session: AuthenticatedSession,
        credential_id: str,
        idempotency_key: str,
        request_digest: str,
        occurred_at: datetime,
    ) -> GovernanceCredential: ...

    def consume_enrollment(
        self,
        *,
        token_digest: str,
        principal: Principal,
        membership: Membership,
        session: AuthenticatedSession,
        occurred_at: datetime,
    ) -> tuple[GovernanceCredential, Membership, AuthenticatedSession]: ...

    def consume_recovery(
        self,
        *,
        token_digest: str,
        session: AuthenticatedSession,
        occurred_at: datetime,
    ) -> tuple[GovernanceCredential, Membership, AuthenticatedSession]: ...

    def create_change_proposal(self, proposal: ChangeProposal) -> ChangeProposal: ...

    def find_change_proposal_replay(
        self,
        *,
        namespace: Namespace,
        proposer_principal_id: str,
        idempotency_key: str,
    ) -> ChangeProposal | None: ...

    def get_change_proposal(self, namespace: Namespace, proposal_id: str) -> ChangeProposal: ...

    def decide_change(
        self, *, proposal: ChangeProposal, decision: ChangeDecision
    ) -> tuple[ChangeProposal, ChangeDecision]: ...

    def find_change_decision_replay(
        self,
        *,
        namespace: Namespace,
        approver_principal_id: str,
        idempotency_key: str,
    ) -> ChangeDecision | None: ...

    def expire_change_proposal(
        self,
        *,
        proposal: ChangeProposal,
        actor: Principal,
        occurred_at: datetime,
    ) -> ChangeProposal: ...

    def mark_change_proposal_stale(
        self,
        *,
        proposal: ChangeProposal,
        actor: Principal,
        occurred_at: datetime,
    ) -> ChangeProposal: ...

    def list_change_proposals(self, namespace: Namespace) -> tuple[ChangeProposal, ...]: ...

    def list_change_decisions(self, namespace: Namespace) -> tuple[ChangeDecision, ...]: ...

    def apply_membership_change(
        self,
        *,
        proposal: ChangeProposal,
        decision_id: str,
        session: AuthenticatedSession,
        idempotency_key: str,
        request_digest: str,
        occurred_at: datetime,
    ) -> Membership: ...

    def consume_admin_enrollment_change(
        self,
        *,
        decision_id: str,
        role: HumanRole,
        colleague_ids: tuple[str, ...],
        actor: Principal,
        occurred_at: datetime,
    ) -> None: ...

    def require_current_effect_approval(
        self,
        *,
        namespace: Namespace,
        approval_decision_id: str,
        evaluated_at: datetime,
    ) -> None: ...

    def audit_export(
        self,
        *,
        query: AuditExportQuery,
        actor: Principal,
        membership: Membership,
        occurred_at: datetime,
        audit_id: str,
    ) -> tuple[AuditExportRecord, ...]: ...

    def p6_studio_snapshot(
        self, *, session: AuthenticatedSession, evaluated_at: datetime
    ) -> P6StudioSnapshot: ...
