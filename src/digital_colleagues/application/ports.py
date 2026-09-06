# SPDX-License-Identifier: Apache-2.0

"""Stable framework-, database-, and provider-neutral application ports."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from digital_colleagues.application.contracts import (
    AgendaClaim,
    ChannelEffect,
    ChannelOutcome,
    DispatchBundle,
    IntelligenceRequest,
    OutboxClaim,
    ReconciliationOutcome,
    RequestPrincipalContext,
    SemanticDecision,
    TriggerClaim,
)
from digital_colleagues.core.authority import Mandate, Profile
from digital_colleagues.core.effects import (
    ActionResult,
    EffectAttempt,
    EffectProposal,
    HumanApprovalDecision,
)
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import Principal
from digital_colleagues.core.runtime import AgendaItem, InputEvent, TimerOccurrence, WakeCycle
from digital_colleagues.core.work import FiniteWork


class ClockPort(Protocol):
    def now(self) -> datetime: ...


class IdentifierPort(Protocol):
    def derive(self, kind: str, *parts: str) -> str: ...


class EntropyPort(Protocol):
    def token_bytes(self, length: int) -> bytes: ...


class RequestPrincipalContextPort(Protocol):
    def current(self) -> RequestPrincipalContext: ...


class CheckpointPort(Protocol):
    def hit(self, checkpoint: str) -> None: ...


class UnitOfWorkPort(Protocol):
    def healthcheck(self) -> dict[str, object]: ...


class PersistencePort(UnitOfWorkPort, Protocol):
    def bootstrap(
        self,
        *,
        namespace: Namespace,
        principals: tuple[Principal, ...],
        profile: Profile,
        mandate: Mandate,
        work: FiniteWork,
        actor: Principal,
        correlation_id: str,
        occurred_at: datetime,
    ) -> bool: ...

    def get_principal(self, tenant_id: str, principal_id: str) -> Principal: ...

    def get_profile(self, namespace: Namespace, profile_id: str) -> Profile: ...

    def get_mandate(self, namespace: Namespace, mandate_id: str) -> Mandate: ...

    def get_work(self, namespace: Namespace, work_id: str) -> FiniteWork: ...

    def get_event(self, namespace: Namespace, event_id: str) -> InputEvent: ...

    def get_timer_occurrence(self, namespace: Namespace, occurrence_id: str) -> TimerOccurrence: ...

    def get_wake_cycle(self, namespace: Namespace, wake_cycle_id: str) -> WakeCycle: ...

    def get_agenda_item(self, namespace: Namespace, agenda_item_id: str) -> AgendaItem: ...

    def get_proposal(self, namespace: Namespace, proposal_id: str) -> EffectProposal: ...

    def get_approval(
        self, namespace: Namespace, approval_decision_id: str
    ) -> HumanApprovalDecision: ...

    def get_approval_replay(
        self, namespace: Namespace, idempotency_key: str
    ) -> tuple[HumanApprovalDecision, EffectAttempt | None] | None: ...

    def get_action_result(self, namespace: Namespace, action_result_id: str) -> ActionResult: ...

    def causal_history(
        self, namespace: Namespace, correlation_id: str
    ) -> tuple[dict[str, object], ...]: ...


class TriggerAgendaPort(Protocol):
    def ingest_event(
        self, event: InputEvent, *, idempotency_key: str, trigger_id: str
    ) -> tuple[InputEvent, bool]: ...

    def ingest_timer(
        self,
        occurrence: TimerOccurrence,
        *,
        idempotency_key: str,
        trigger_id: str,
    ) -> tuple[TimerOccurrence, bool]: ...

    def claim_trigger(
        self,
        namespace: Namespace,
        *,
        owner: str,
        now: datetime,
        lease_until: datetime,
    ) -> TriggerClaim | None: ...

    def materialize_agenda(
        self,
        claim: TriggerClaim,
        *,
        wake_cycle_id: str,
        agenda_item_id: str,
        actor: Principal,
        occurred_at: datetime,
    ) -> tuple[WakeCycle, AgendaItem]: ...


class WakeCyclePort(Protocol):
    def claim_agenda(
        self,
        namespace: Namespace,
        *,
        owner: str,
        now: datetime,
        lease_until: datetime,
    ) -> AgendaClaim | None: ...

    def commit_semantic_decision(self, claim: AgendaClaim, semantic: SemanticDecision) -> None: ...

    def release_agenda(self, claim: AgendaClaim) -> None: ...

    def pending_agenda_count(self, namespace: Namespace) -> int: ...


class OutboxPort(Protocol):
    def commit_approval_and_attempt(
        self,
        *,
        namespace: Namespace,
        mandate_id: str,
        expected_mandate_revision: int,
        decision: HumanApprovalDecision,
        effect_attempt_id: str,
        outbox_id: str,
        service_actor: Principal,
        occurred_at: datetime,
    ) -> tuple[HumanApprovalDecision, EffectAttempt | None, bool]: ...

    def claim_outbox(
        self,
        namespace: Namespace,
        *,
        owner: str,
        now: datetime,
        lease_until: datetime,
    ) -> OutboxClaim | None: ...

    def load_dispatch_bundle(self, claim: OutboxClaim, *, mandate_id: str) -> DispatchBundle: ...

    def mark_dispatch_started(
        self, claim: OutboxClaim, *, occurred_at: datetime
    ) -> EffectAttempt: ...

    def finalize_dispatch(
        self,
        claim: OutboxClaim,
        *,
        outcome: ChannelOutcome,
        action_result_id: str,
        result_actor: Principal,
        occurred_at: datetime,
        next_attempt_id: str | None,
    ) -> ActionResult: ...

    def recover_expired_dispatches(
        self,
        namespace: Namespace,
        *,
        now: datetime,
        result_actor: Principal,
        result_id: str,
    ) -> int: ...

    def claim_ambiguous(
        self,
        namespace: Namespace,
        *,
        owner: str,
        now: datetime,
        lease_until: datetime,
    ) -> OutboxClaim | None: ...

    def reconcile_ambiguous(
        self,
        claim: OutboxClaim,
        *,
        outcome: ReconciliationOutcome,
        action_result_id: str,
        result_actor: Principal,
        occurred_at: datetime,
        next_attempt_id: str | None,
        next_reconciliation_at: datetime | None = None,
    ) -> ActionResult | None: ...


class RuntimePersistencePort(
    PersistencePort, TriggerAgendaPort, WakeCyclePort, OutboxPort, Protocol
):
    """The complete local semantic persistence surface used by P3 services."""


class IntelligencePort(Protocol):
    def decide(self, request: IntelligenceRequest) -> SemanticDecision: ...


class ReferenceChannelPort(Protocol):
    def apply(self, effect: ChannelEffect) -> ChannelOutcome: ...

    def reconcile(
        self,
        effect_idempotency_key: str,
        binding_digest: str | None = None,
    ) -> ReconciliationOutcome: ...


class DispatchAuthorizationPort(Protocol):
    """Optional additive policy check performed before an attempt or channel call."""

    def authorize(self, proposal: EffectProposal, approval: HumanApprovalDecision) -> None: ...
