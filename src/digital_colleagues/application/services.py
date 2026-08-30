# SPDX-License-Identifier: Apache-2.0

"""Headless P3 orchestration over stable ports and pure governance."""

from __future__ import annotations

from datetime import timedelta

from digital_colleagues.application.contracts import (
    ChannelEffect,
    ChannelOutcomeKind,
    DispatchBundle,
    DispatchResult,
    IntelligenceRequest,
    OutboxClaim,
    ReconciliationKind,
    RequestPrincipalContext,
    WakeRunResult,
)
from digital_colleagues.application.errors import PermissionDeniedError, ValidationError
from digital_colleagues.application.ports import (
    CheckpointPort,
    ClockPort,
    IdentifierPort,
    IntelligencePort,
    ReferenceChannelPort,
    RuntimePersistencePort,
)
from digital_colleagues.core.authority import Mandate, Profile
from digital_colleagues.core.effects import ApprovalChoice, HumanApprovalDecision
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import HumanRole, Principal, PrincipalKind
from digital_colleagues.core.runtime import InputEvent
from digital_colleagues.core.work import FiniteWork
from digital_colleagues.governance.approvals import (
    authorize_effect_proposal,
    authorize_human_approval,
    require_authoritative_human_role,
)


class _NoopCheckpoint:
    def hit(self, checkpoint: str) -> None:
        del checkpoint


class BootstrapService:
    def __init__(self, store: RuntimePersistencePort, clock: ClockPort) -> None:
        self._store = store
        self._clock = clock

    def initialize(
        self,
        *,
        context: RequestPrincipalContext,
        principals: tuple[Principal, ...],
        profile: Profile,
        mandate: Mandate,
        work: FiniteWork,
        correlation_id: str,
    ) -> bool:
        require_authoritative_human_role(
            context.principal,
            accepted_roles=frozenset({HumanRole.TENANT_ADMIN}),
        )
        context.namespace.require_exact(profile.namespace)
        context.namespace.require_exact(mandate.namespace)
        context.namespace.require_exact(work.namespace)
        return self._store.bootstrap(
            namespace=context.namespace,
            principals=principals,
            profile=profile,
            mandate=mandate,
            work=work,
            actor=context.principal,
            correlation_id=correlation_id,
            occurred_at=self._clock.now(),
        )


class EventService:
    def __init__(self, store: RuntimePersistencePort, identifiers: IdentifierPort) -> None:
        self._store = store
        self._identifiers = identifiers

    def submit(
        self,
        *,
        context: RequestPrincipalContext,
        event: InputEvent,
        idempotency_key: str,
    ) -> tuple[InputEvent, bool]:
        context.namespace.require_exact(event.namespace)
        if event.actor != context.principal:
            raise PermissionDeniedError("event actor does not match request authority")
        trigger_id = self._identifiers.derive("trigger", event.event_id, idempotency_key)
        return self._store.ingest_event(
            event,
            idempotency_key=idempotency_key,
            trigger_id=trigger_id,
        )


class WakeService:
    def __init__(
        self,
        *,
        store: RuntimePersistencePort,
        intelligence: IntelligencePort,
        clock: ClockPort,
        identifiers: IdentifierPort,
        service_principal: Principal,
        model_principal: Principal,
        mandate_id: str,
        owner_id: str,
        lease_duration: timedelta = timedelta(seconds=30),
        max_items: int = 4,
        max_decisions: int = 4,
        checkpoint: CheckpointPort | None = None,
    ) -> None:
        if service_principal.kind is not PrincipalKind.SERVICE:
            raise ValidationError("wake actor must be a service principal")
        if model_principal.kind is not PrincipalKind.MODEL:
            raise ValidationError("intelligence actor must be a model principal")
        if max_items < 1 or max_decisions < 1:
            raise ValidationError("wake bounds must be positive")
        self._store = store
        self._intelligence = intelligence
        self._clock = clock
        self._identifiers = identifiers
        self._service_principal = service_principal
        self._model_principal = model_principal
        self._mandate_id = mandate_id
        self._owner_id = owner_id
        self._lease_duration = lease_duration
        self._max_items = max_items
        self._max_decisions = max_decisions
        self._checkpoint = checkpoint or _NoopCheckpoint()

    def materialize_next(self, namespace: Namespace) -> tuple[str, str] | None:
        now = self._clock.now()
        claim = self._store.claim_trigger(
            namespace,
            owner=self._owner_id,
            now=now,
            lease_until=now + self._lease_duration,
        )
        if claim is None:
            return None
        self._checkpoint.hit("trigger_claimed")
        wake_id = self._identifiers.derive("wake", claim.trigger_id, str(claim.fencing_token))
        agenda_id = self._identifiers.derive("agenda", claim.event_id)
        wake, agenda = self._store.materialize_agenda(
            claim,
            wake_cycle_id=wake_id,
            agenda_item_id=agenda_id,
            actor=self._service_principal,
            occurred_at=now,
        )
        self._checkpoint.hit("agenda_materialized")
        return wake.wake_cycle_id, agenda.agenda_item_id

    def run(self, namespace: Namespace) -> WakeRunResult:
        selected = 0
        decisions = 0
        while selected < self._max_items and decisions < self._max_decisions:
            now = self._clock.now()
            claim = self._store.claim_agenda(
                namespace,
                owner=self._owner_id,
                now=now,
                lease_until=now + self._lease_duration,
            )
            if claim is None:
                break
            selected += 1
            self._checkpoint.hit("agenda_claimed")
            request_id = self._identifiers.derive(
                "request",
                claim.agenda_item.agenda_item_id,
                str(claim.claimed_generation),
            )
            wake = self._store.get_wake_cycle(namespace, claim.agenda_item.wake_cycle_id)
            request = IntelligenceRequest(
                namespace=namespace,
                request_id=request_id,
                wake_cycle=wake,
                agenda_item=claim.agenda_item,
                mandate=self._store.get_mandate(namespace, self._mandate_id),
                model_principal=self._model_principal,
                decision_id=self._identifiers.derive("decision", request_id),
                proposal_id=self._identifiers.derive("proposal", request_id),
                effect_idempotency_key=self._identifiers.derive("effect", request_id),
                occurred_at=now,
                proposal_valid_until=now + timedelta(hours=1),
            )
            try:
                semantic = self._intelligence.decide(request)
                self._checkpoint.hit("decision_produced")
                self._store.commit_semantic_decision(claim, semantic)
                self._checkpoint.hit("decision_committed")
                decisions += 1
            except Exception:
                self._store.release_agenda(claim)
                raise
        pending = self._store.pending_agenda_count(namespace)
        outcome = "bounded_pending" if pending else "terminal"
        return WakeRunResult(selected, decisions, pending, outcome)


class ApprovalService:
    def __init__(
        self,
        *,
        store: RuntimePersistencePort,
        clock: ClockPort,
        identifiers: IdentifierPort,
        service_principal: Principal,
    ) -> None:
        if service_principal.kind is not PrincipalKind.SERVICE:
            raise ValidationError("approval attempt actor must be a service principal")
        self._store = store
        self._clock = clock
        self._identifiers = identifiers
        self._service_principal = service_principal

    def decide(
        self,
        *,
        context: RequestPrincipalContext,
        mandate_id: str,
        expected_mandate_revision: int,
        decision: HumanApprovalDecision,
    ) -> tuple[HumanApprovalDecision, str | None, bool]:
        if decision.author != context.principal:
            raise PermissionDeniedError("approval author does not match request authority")
        if context.principal.kind is not PrincipalKind.HUMAN:
            raise PermissionDeniedError("approval requires a durable human principal")
        context.namespace.require_exact(decision.namespace)
        attempt_id = self._identifiers.derive(
            "attempt", decision.proposal_id, str(decision.proposal_revision), "1"
        )
        outbox_id = self._identifiers.derive("outbox", decision.proposal_id)
        stored, attempt, created = self._store.commit_approval_and_attempt(
            namespace=context.namespace,
            mandate_id=mandate_id,
            expected_mandate_revision=expected_mandate_revision,
            decision=decision,
            effect_attempt_id=attempt_id,
            outbox_id=outbox_id,
            service_actor=self._service_principal,
            occurred_at=self._clock.now(),
        )
        return stored, attempt.effect_attempt_id if attempt is not None else None, created


class DispatchService:
    def __init__(
        self,
        *,
        store: RuntimePersistencePort,
        channel: ReferenceChannelPort,
        clock: ClockPort,
        identifiers: IdentifierPort,
        result_actor: Principal,
        owner_id: str,
        mandate_id: str,
        lease_duration: timedelta = timedelta(seconds=30),
        checkpoint: CheckpointPort | None = None,
    ) -> None:
        if result_actor.kind is not PrincipalKind.SERVICE:
            raise ValidationError("result actor must be a service principal")
        self._store = store
        self._channel = channel
        self._clock = clock
        self._identifiers = identifiers
        self._result_actor = result_actor
        self._owner_id = owner_id
        self._mandate_id = mandate_id
        self._lease_duration = lease_duration
        self._checkpoint = checkpoint or _NoopCheckpoint()

    def _validate_exact_effect(self, namespace: Namespace, claim: OutboxClaim) -> DispatchBundle:
        bundle = self._store.load_dispatch_bundle(claim, mandate_id=self._mandate_id)
        mandate = self._store.get_mandate(namespace, self._mandate_id)
        if bundle.proposal.mandate_id != mandate.mandate_id:
            raise PermissionDeniedError("proposal mandate identity is stale")
        if bundle.proposal.mandate_revision != mandate.revision:
            raise PermissionDeniedError("proposal mandate revision is stale")
        if bundle.effect_idempotency_key != bundle.proposal.constraints.idempotency_key:
            raise PermissionDeniedError("effect idempotency identity drifted")
        if bundle.approval.author != bundle.approver:
            raise PermissionDeniedError("approval principal binding drifted")
        authorize_effect_proposal(
            bundle.proposal,
            mandate,
            expected_mandate_revision=mandate.revision,
        )
        authorize_human_approval(
            bundle.proposal,
            bundle.approval,
            evaluated_at=self._clock.now(),
        )
        if bundle.attempt.attempt_number > bundle.maximum_attempts:
            raise PermissionDeniedError("effect attempt limit was exceeded")
        return bundle

    def dispatch_once(self, namespace: Namespace) -> DispatchResult:
        now = self._clock.now()
        claim = self._store.claim_outbox(
            namespace,
            owner=self._owner_id,
            now=now,
            lease_until=now + self._lease_duration,
        )
        if claim is None:
            return DispatchResult(False, None, None)
        self._checkpoint.hit("outbox_claimed")
        bundle = self._validate_exact_effect(namespace, claim)
        started = self._store.mark_dispatch_started(claim, occurred_at=now)
        self._checkpoint.hit("dispatch_started")
        outcome = self._channel.apply(
            ChannelEffect(bundle.proposal, started, bundle.effect_idempotency_key)
        )
        self._checkpoint.hit("channel_returned")
        next_attempt_id = None
        if (
            outcome.kind
            in {
                ChannelOutcomeKind.KNOWN_NOT_EXECUTED,
                ChannelOutcomeKind.RETRYABLE_FAILURE,
            }
            and claim.attempt_number < bundle.maximum_attempts
        ):
            next_attempt_id = self._identifiers.derive(
                "attempt",
                claim.proposal_id,
                str(claim.attempt_number + 1),
            )
        result_id = self._identifiers.derive("result", claim.effect_attempt_id, outcome.kind.value)
        result = self._store.finalize_dispatch(
            claim,
            outcome=outcome,
            action_result_id=result_id,
            result_actor=self._result_actor,
            occurred_at=self._clock.now(),
            next_attempt_id=next_attempt_id,
        )
        self._checkpoint.hit("dispatch_finalized")
        return DispatchResult(True, outcome.kind, result.action_result_id)

    def recover_expired(self, namespace: Namespace) -> int:
        now = self._clock.now()
        result_id = self._identifiers.derive("result", "expired-dispatch", now.isoformat())
        return self._store.recover_expired_dispatches(
            namespace,
            now=now,
            result_actor=self._result_actor,
            result_id=result_id,
        )

    def reconcile_once(self, namespace: Namespace) -> DispatchResult:
        now = self._clock.now()
        claim = self._store.claim_ambiguous(
            namespace,
            owner=self._owner_id,
            now=now,
            lease_until=now + self._lease_duration,
        )
        if claim is None:
            return DispatchResult(False, None, None)
        bundle = self._validate_exact_effect(namespace, claim)
        outcome = self._channel.reconcile(bundle.effect_idempotency_key)
        next_attempt_id = None
        if (
            outcome.kind is ReconciliationKind.CONFIRMED_ABSENT
            and claim.attempt_number < bundle.maximum_attempts
        ):
            next_attempt_id = self._identifiers.derive(
                "attempt", claim.proposal_id, str(claim.attempt_number + 1)
            )
        result_id = self._identifiers.derive("result", claim.effect_attempt_id, outcome.kind.value)
        result = self._store.reconcile_ambiguous(
            claim,
            outcome=outcome,
            action_result_id=result_id,
            result_actor=self._result_actor,
            occurred_at=now,
            next_attempt_id=next_attempt_id,
        )
        mapped = (
            ChannelOutcomeKind.SUCCEEDED
            if outcome.kind is ReconciliationKind.CONFIRMED_APPLIED
            else ChannelOutcomeKind.KNOWN_NOT_EXECUTED
            if outcome.kind is ReconciliationKind.CONFIRMED_ABSENT
            else ChannelOutcomeKind.AMBIGUOUS
        )
        return DispatchResult(True, mapped, result.action_result_id if result else None)


def rejection_decision_creates_no_attempt(choice: ApprovalChoice) -> bool:
    """Small explicit semantic used by contract gates and edge tests."""

    return choice is ApprovalChoice.REJECT
