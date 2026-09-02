# SPDX-License-Identifier: Apache-2.0

"""Stable persistence surface for the P5 revisioned builder and policy runtime."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from digital_colleagues.application.p5_contracts import (
    ConfirmationResult,
    P5StudioSnapshot,
    PolicyAdmission,
)
from digital_colleagues.core.authority import Mandate, Profile
from digital_colleagues.core.builder import ColleagueDraft
from digital_colleagues.core.effects import EffectProposal
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.policy import (
    ColleaguePolicy,
    DurableTriggerKind,
    EscalationRecord,
    PolicyEnforcementRecord,
    PolicyRunState,
    PolicyStage,
)
from digital_colleagues.core.principals import Principal


class P5PersistencePort(Protocol):
    def active_configuration(self, namespace: Namespace) -> tuple[Profile, Mandate]: ...

    def get_active_policy(self, namespace: Namespace) -> ColleaguePolicy | None: ...

    def get_runtime_policy_state(
        self, namespace: Namespace
    ) -> tuple[ColleaguePolicy | None, PolicyRunState | None]: ...

    def get_draft(self, namespace: Namespace, draft_id: str) -> ColleagueDraft: ...

    def list_drafts(self, namespace: Namespace) -> tuple[ColleagueDraft, ...]: ...

    def create_draft(self, draft: ColleagueDraft) -> tuple[ColleagueDraft, bool]: ...

    def update_draft(self, draft: ColleagueDraft, *, expected_revision: int) -> ColleagueDraft: ...

    def review_draft(
        self,
        *,
        namespace: Namespace,
        draft_id: str,
        expected_revision: int,
        actor: Principal,
        occurred_at: datetime,
    ) -> ColleagueDraft: ...

    def cancel_draft(
        self,
        *,
        namespace: Namespace,
        draft_id: str,
        expected_revision: int,
        actor: Principal,
        occurred_at: datetime,
    ) -> ColleagueDraft: ...

    def confirm_draft(
        self,
        *,
        namespace: Namespace,
        draft_id: str,
        expected_draft_revision: int,
        expected_base_profile_revision: int,
        expected_base_mandate_revision: int,
        expected_base_policy_revision: int,
        expected_canonical_digest: str,
        actor: Principal,
        idempotency_key: str,
        request_digest: str,
        confirmation_id: str,
        occurred_at: datetime,
        change_decision_id: str | None = None,
    ) -> ConfirmationResult: ...

    def admit_trigger(
        self,
        *,
        policy: ColleaguePolicy,
        trigger_class: DurableTriggerKind,
        source_id: str,
        occurrence_key: str,
        actor: Principal,
        correlation_id: str,
        causation_id: str,
        outcome_id: str,
        escalation_id: str,
        occurred_at: datetime,
    ) -> PolicyAdmission: ...

    def record_policy_outcome(
        self,
        record: PolicyEnforcementRecord,
        *,
        escalation: EscalationRecord | None = None,
    ) -> bool: ...

    def require_current_proposal_policy(
        self, proposal: EffectProposal, *, stage: PolicyStage
    ) -> ColleaguePolicy | None: ...

    def p5_studio_snapshot(self, namespace: Namespace) -> P5StudioSnapshot: ...
