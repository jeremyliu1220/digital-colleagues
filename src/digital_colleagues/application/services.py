# SPDX-License-Identifier: Apache-2.0

"""Headless P3 orchestration over stable ports and pure governance."""

from __future__ import annotations

from datetime import datetime, timedelta

from digital_colleagues.application.contracts import (
    ApprovalRequest,
    ChannelEffect,
    ChannelOutcomeKind,
    DispatchBundle,
    DispatchResult,
    InputEventRequest,
    IntelligenceRequest,
    OutboxClaim,
    ReconciliationKind,
    RequestPrincipalContext,
    SemanticDecision,
    SemanticOutcome,
    TimerScheduleRequest,
    WakeRunResult,
)
from digital_colleagues.application.errors import (
    ConflictError,
    ExternalAdapterError,
    PermissionDeniedError,
    ValidationError,
)
from digital_colleagues.application.ports import (
    CheckpointPort,
    ClockPort,
    DispatchAuthorizationPort,
    IdentifierPort,
    IntelligencePort,
    ReferenceChannelPort,
    RuntimePersistencePort,
)
from digital_colleagues.core.authority import Mandate, Profile
from digital_colleagues.core.effects import ApprovalChoice, HumanApprovalDecision
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import HumanRole, Principal, PrincipalKind
from digital_colleagues.core.runtime import (
    Decision,
    DecisionKind,
    InputEvent,
    InputEventState,
    TimerOccurrence,
    TimerOccurrenceState,
)
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
    def __init__(
        self,
        store: RuntimePersistencePort,
        identifiers: IdentifierPort,
        clock: ClockPort,
    ) -> None:
        self._store = store
        self._identifiers = identifiers
        self._clock = clock

    def submit(
        self,
        *,
        context: RequestPrincipalContext,
        request: InputEventRequest,
        idempotency_key: str,
    ) -> tuple[InputEvent, bool]:
        if not idempotency_key:
            raise ValidationError("event idempotency identity is required")
        event = InputEvent(
            namespace=context.namespace,
            event_id=request.event_id,
            event_type=request.event_type,
            state=InputEventState.ACCEPTED,
            safe_projection=request.safe_projection,
            payload_digest=request.payload_digest,
            actor=context.principal,
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
            occurred_at=self._clock.now(),
            revision=1,
            policy_id=request.policy_id,
            policy_revision=request.policy_revision,
        )
        trigger_id = self._identifiers.derive("trigger", request.event_id, idempotency_key)
        return self._store.ingest_event(
            event,
            idempotency_key=idempotency_key,
            trigger_id=trigger_id,
        )


class TimerService:
    def __init__(
        self,
        store: RuntimePersistencePort,
        identifiers: IdentifierPort,
        clock: ClockPort,
        service_principal: Principal,
    ) -> None:
        if service_principal.kind is not PrincipalKind.SERVICE:
            raise ValidationError("timer scheduler must be a service principal")
        self._store = store
        self._identifiers = identifiers
        self._clock = clock
        self._service_principal = service_principal

    def schedule(
        self,
        *,
        namespace: Namespace,
        request: TimerScheduleRequest,
    ) -> tuple[TimerOccurrence, bool]:
        namespace.require_same_tenant(self._service_principal.namespace)
        occurred_at = self._clock.now()
        occurrence = TimerOccurrence(
            namespace=namespace,
            timer_id=request.timer_id,
            occurrence_id=request.occurrence_id,
            state=TimerOccurrenceState.SCHEDULED,
            due_at=request.due_at,
            safe_projection=request.safe_projection,
            actor=self._service_principal,
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
            occurred_at=occurred_at,
            revision=1,
            policy_id=request.policy_id,
            policy_revision=request.policy_revision,
        )
        trigger_id = self._identifiers.derive(
            "timer-trigger",
            request.timer_id,
            request.occurrence_id,
            request.idempotency_key,
        )
        return self._store.ingest_timer(
            occurrence,
            idempotency_key=request.idempotency_key,
            trigger_id=trigger_id,
        )


def _deterministic_noop(request: IntelligenceRequest) -> SemanticDecision | None:
    """Pure application eligibility policy evaluated before the intelligence port."""

    if not request.agenda_item.title.startswith("noop:"):
        return None
    decision = Decision(
        namespace=request.namespace,
        decision_id=request.decision_id,
        wake_cycle_id=request.wake_cycle.wake_cycle_id,
        agenda_item_id=request.agenda_item.agenda_item_id,
        kind=DecisionKind.NO_ACTION,
        rationale="Deterministic application policy completed an explicit no-op.",
        proposed_effect_id=None,
        actor=request.model_principal,
        correlation_id=request.agenda_item.correlation_id,
        causation_id=request.agenda_item.agenda_item_id,
        occurred_at=request.occurred_at,
        revision=1,
        policy_id=request.policy_id,
        policy_revision=request.policy_revision,
    )
    return SemanticDecision(SemanticOutcome.NO_OP, decision, None, request.request_id)


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
        agenda_id = (
            self._identifiers.derive("agenda", claim.source_id)
            if claim.source_record_type == "input_event"
            else self._identifiers.derive("agenda", "timer", claim.source_id)
        )
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
                policy_id=wake.policy_id,
                policy_revision=wake.policy_revision,
            )
            try:
                semantic = _deterministic_noop(request)
                if semantic is None:
                    semantic = self._intelligence.decide(request)
                self._checkpoint.hit("decision_produced")
                self._store.commit_semantic_decision(claim, semantic)
                self._checkpoint.hit("decision_committed")
                decisions += 1
            except ExternalAdapterError as exc:
                failure_decision = Decision(
                    namespace=request.namespace,
                    decision_id=request.decision_id,
                    wake_cycle_id=request.wake_cycle.wake_cycle_id,
                    agenda_item_id=request.agenda_item.agenda_item_id,
                    kind=DecisionKind.DEFER_ITEM,
                    rationale=(
                        "Optional intelligence failure stopped after one bounded attempt: "
                        f"category={exc.failure_category} digest={exc.diagnostic_digest}."
                    ),
                    proposed_effect_id=None,
                    actor=request.model_principal,
                    correlation_id=request.agenda_item.correlation_id,
                    causation_id=request.agenda_item.agenda_item_id,
                    occurred_at=request.occurred_at,
                    revision=1,
                    policy_id=request.policy_id,
                    policy_revision=request.policy_revision,
                )
                self._store.commit_semantic_decision(
                    claim,
                    SemanticDecision(
                        SemanticOutcome.WAIT,
                        failure_decision,
                        None,
                        request.request_id,
                    ),
                )
                self._checkpoint.hit("adapter_failure_committed")
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
        approval_validity: timedelta = timedelta(minutes=15),
    ) -> None:
        if service_principal.kind is not PrincipalKind.SERVICE:
            raise ValidationError("approval attempt actor must be a service principal")
        if approval_validity <= timedelta(0):
            raise ValidationError("approval validity policy must be positive")
        self._store = store
        self._clock = clock
        self._identifiers = identifiers
        self._service_principal = service_principal
        self._approval_validity = approval_validity

    def decide(
        self,
        *,
        context: RequestPrincipalContext,
        mandate_id: str,
        expected_mandate_revision: int,
        request: ApprovalRequest,
    ) -> tuple[HumanApprovalDecision, str | None, bool]:
        if context.principal.kind is not PrincipalKind.HUMAN:
            raise PermissionDeniedError("approval requires a durable human principal")
        replay = self._store.get_approval_replay(context.namespace, request.idempotency_key)
        if replay is not None:
            existing, attempt = replay
            replay_binding = (
                existing.approval_decision_id,
                existing.proposal_id,
                existing.proposal_revision,
                existing.proposal_payload_digest,
                existing.proposal_digest,
                existing.choice,
                existing.idempotency_key,
                existing.author,
            )
            request_binding = (
                request.approval_decision_id,
                request.proposal_id,
                request.proposal_revision,
                request.proposal_payload_digest,
                request.proposal_digest,
                request.choice,
                request.idempotency_key,
                context.principal,
            )
            if replay_binding != request_binding:
                raise ConflictError("approval idempotency replay drifted")
            return (
                existing,
                attempt.effect_attempt_id if attempt is not None else None,
                False,
            )
        now = self._clock.now()
        proposal = self._store.get_proposal(context.namespace, request.proposal_id)
        if now < proposal.occurred_at:
            raise PermissionDeniedError("approval cannot precede the proposal")
        if now > proposal.constraints.valid_until:
            raise PermissionDeniedError("proposal validity has expired")
        decision = HumanApprovalDecision(
            namespace=context.namespace,
            approval_decision_id=request.approval_decision_id,
            proposal_id=request.proposal_id,
            proposal_revision=request.proposal_revision,
            proposal_payload_digest=request.proposal_payload_digest,
            proposal_digest=request.proposal_digest,
            choice=request.choice,
            author=context.principal,
            idempotency_key=request.idempotency_key,
            correlation_id=proposal.correlation_id,
            causation_id=proposal.proposal_id,
            occurred_at=now,
            valid_until=min(now + self._approval_validity, proposal.constraints.valid_until),
            revision=1,
        )
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
        reconciliation_backoff: timedelta = timedelta(0),
        checkpoint: CheckpointPort | None = None,
        policy_authorizer: DispatchAuthorizationPort | None = None,
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
        if reconciliation_backoff < timedelta(0) or reconciliation_backoff > timedelta(seconds=30):
            raise ValidationError("reconciliation backoff must be between zero and 30 seconds")
        self._reconciliation_backoff = reconciliation_backoff
        self._checkpoint = checkpoint or _NoopCheckpoint()
        self._policy_authorizer = policy_authorizer

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
        if self._policy_authorizer is not None:
            self._policy_authorizer.authorize(bundle.proposal, bundle.approval)
        if bundle.attempt.attempt_number > bundle.maximum_attempts:
            raise PermissionDeniedError("effect attempt limit was exceeded")
        return bundle

    @staticmethod
    def _require_live_claim(claim: OutboxClaim, evaluated_at: datetime) -> None:
        if claim.lease_until < evaluated_at:
            raise ConflictError("outbox claim lease expired during provider I/O")

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
        self._require_live_claim(claim, self._clock.now())
        bundle = self._validate_exact_effect(namespace, claim)
        self._require_live_claim(claim, self._clock.now())
        outcome = self._channel.reconcile(
            bundle.effect_idempotency_key,
            bundle.proposal.proposal_digest,
        )
        returned_at = self._clock.now()
        self._require_live_claim(claim, returned_at)
        next_attempt_id = None
        if outcome.kind is ReconciliationKind.CONFIRMED_ABSENT:
            # Provider reconciliation is I/O. Re-read every durable authority and
            # exact-effect binding after it returns, before authorizing a retry.
            bundle = self._validate_exact_effect(namespace, claim)
            if claim.attempt_number < bundle.maximum_attempts:
                next_attempt_id = self._identifiers.derive(
                    "attempt", claim.proposal_id, str(claim.attempt_number + 1)
                )
        finalized_at = self._clock.now()
        self._require_live_claim(claim, finalized_at)
        result_id = self._identifiers.derive("result", claim.effect_attempt_id, outcome.kind.value)
        result = self._store.reconcile_ambiguous(
            claim,
            outcome=outcome,
            action_result_id=result_id,
            result_actor=self._result_actor,
            occurred_at=finalized_at,
            next_attempt_id=next_attempt_id,
            next_reconciliation_at=finalized_at + self._reconciliation_backoff,
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
