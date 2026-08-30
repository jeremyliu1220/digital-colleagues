# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from digital_colleagues.adapters.channel.reference import ReferenceChannel
from digital_colleagues.adapters.intelligence.deterministic import DeterministicIntelligence
from digital_colleagues.adapters.sqlite.codec import to_storage_json
from digital_colleagues.adapters.system.deterministic import FixedClock
from digital_colleagues.application.contracts import (
    ChannelOutcomeKind,
    IntelligenceRequest,
    ReconciliationKind,
    RequestPrincipalContext,
)
from digital_colleagues.application.errors import (
    ConflictError,
    PermissionDeniedError,
    PersistenceError,
)
from digital_colleagues.application.services import (
    ApprovalService,
    DispatchService,
    EventService,
    WakeService,
)
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.effects import ApprovalChoice, HumanApprovalDecision
from digital_colleagues.core.runtime import AgendaItemState
from tests.p3.fixtures import (
    T0,
    T2,
    T3,
    T4,
    approval_request,
    input_event,
    model,
    namespace,
    request_for_event,
    service,
    user,
)
from tests.p3.scenario import approve, new_store, prepare_proposal


class _CrashAt:
    def __init__(self, target: str) -> None:
        self.target = target

    def hit(self, checkpoint: str) -> None:
        if checkpoint == self.target:
            raise RuntimeError("synthetic crash")


def _dispatch(
    scenario: object, channel: ReferenceChannel, clock: object = None, **extra: object
) -> DispatchService:
    return DispatchService(
        store=scenario.store,  # type: ignore[attr-defined]
        channel=channel,
        clock=clock or FixedClock(T3),  # type: ignore[arg-type]
        identifiers=scenario.identifiers,  # type: ignore[attr-defined]
        result_actor=service(),
        owner_id="worker-dispatch-runtime",
        mandate_id="mandate-synthetic",
        **extra,  # type: ignore[arg-type]
    )


class RuntimeSemanticsTests(unittest.TestCase):
    def test_server_authoritative_approval_time_is_stamped_and_replay_is_not_reinterpreted(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="digital-colleagues-p3-approval-time-"
        ) as temporary:
            scenario = prepare_proposal(
                Path(temporary) / "state.sqlite", identifier_namespace="approval-time"
            )
            request = approval_request(scenario.proposal)
            for label, now in (
                ("before-proposal", T0),
                ("after-expiry", T4 + timedelta(minutes=2)),
            ):
                candidate = replace(
                    request,
                    approval_decision_id=f"approval-{label}",
                    idempotency_key=f"approval-key-{label}",
                )
                with self.subTest(case=label), self.assertRaises(PermissionDeniedError):
                    ApprovalService(
                        store=scenario.store,
                        clock=FixedClock(now),
                        identifiers=scenario.identifiers,
                        service_principal=service(),
                    ).decide(
                        context=RequestPrincipalContext(namespace(), user()),
                        mandate_id="mandate-synthetic",
                        expected_mandate_revision=1,
                        request=candidate,
                    )
            stored, _, created = ApprovalService(
                store=scenario.store,
                clock=FixedClock(T2),
                identifiers=scenario.identifiers,
                service_principal=service(),
            ).decide(
                context=RequestPrincipalContext(namespace(), user()),
                mandate_id="mandate-synthetic",
                expected_mandate_revision=1,
                request=request,
            )
            self.assertTrue(created)
            self.assertEqual(stored.occurred_at, T2)
            self.assertEqual(stored.valid_until, T2 + timedelta(minutes=15))
            replayed, _, replay_created = ApprovalService(
                store=scenario.store,
                clock=FixedClock(T4 + timedelta(minutes=2)),
                identifiers=scenario.identifiers,
                service_principal=service(),
            ).decide(
                context=RequestPrincipalContext(namespace(), user()),
                mandate_id="mandate-synthetic",
                expected_mandate_revision=1,
                request=request,
            )
            self.assertFalse(replay_created)
            self.assertEqual(replayed, stored)
            scenario.store.close()

    def test_wake_cycle_bounds_preserve_pending_work_and_agenda_takeover_fences_stale_owner(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-wake-bounds-") as temporary:
            scenario = prepare_proposal(
                Path(temporary) / "state.sqlite", identifier_namespace="wake-bounds"
            )
            lease_event = replace(
                input_event(
                    event_id="event-agenda-lease",
                    correlation_id="correlation-agenda-lease",
                ),
                safe_projection=FrozenJsonObject.from_mapping(
                    {"work_id": "work-agenda-lease", "priority": 800, "title": "lease"}
                ),
            )
            EventService(scenario.store, scenario.identifiers, FixedClock(T0)).submit(
                context=RequestPrincipalContext(namespace(), user()),
                request=request_for_event(lease_event),
                idempotency_key="event-key-agenda-lease",
            )
            wake = WakeService(
                store=scenario.store,
                intelligence=DeterministicIntelligence(),
                clock=FixedClock(T2),
                identifiers=scenario.identifiers,
                service_principal=service(),
                model_principal=model(),
                mandate_id="mandate-synthetic",
                owner_id="worker-bounded",
                max_items=1,
                max_decisions=1,
            )
            wake.materialize_next(namespace())
            stale = scenario.store.claim_agenda(
                namespace(), owner="agenda-owner-a", now=T2, lease_until=T2
            )
            assert stale is not None
            takeover = scenario.store.claim_agenda(
                namespace(), owner="agenda-owner-b", now=T3, lease_until=T3
            )
            assert takeover is not None
            self.assertEqual(
                takeover.agenda_item.agenda_item_id,
                stale.agenda_item.agenda_item_id,
            )
            self.assertGreater(takeover.fencing_token, stale.fencing_token)
            with self.assertRaises(ConflictError):
                scenario.store.release_agenda(stale)
            scenario.store.release_agenda(takeover)

            bounded_event = replace(
                input_event(
                    event_id="event-bounded-second",
                    correlation_id="correlation-bounded-second",
                ),
                safe_projection=FrozenJsonObject.from_mapping(
                    {"work_id": "work-bounded-second", "priority": 100, "title": "bounded"}
                ),
            )
            EventService(scenario.store, scenario.identifiers, FixedClock(T0)).submit(
                context=RequestPrincipalContext(namespace(), user()),
                request=request_for_event(bounded_event),
                idempotency_key="event-key-bounded-second",
            )
            wake.materialize_next(namespace())
            first = wake.run(namespace())
            self.assertEqual(first.selected_count, 1)
            self.assertEqual(first.decision_count, 1)
            self.assertEqual(first.pending_count, 1)
            self.assertEqual(first.outcome, "bounded_pending")
            second = wake.run(namespace())
            self.assertEqual(second.selected_count, 1)
            self.assertEqual(second.decision_count, 1)
            self.assertEqual(second.pending_count, 0)
            self.assertEqual(second.outcome, "terminal")
            scenario.store.close()

    def test_attention_order_is_deterministic_and_starved_work_advances(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-attention-") as temporary:
            scenario = prepare_proposal(
                Path(temporary) / "state.sqlite", identifier_namespace="attention"
            )
            for event_id, work_id, priority in (
                ("event-attention-high", "work-attention-high", 900),
                ("event-attention-low", "work-attention-low", 10),
            ):
                event = replace(
                    input_event(event_id=event_id, correlation_id=f"correlation-{event_id}"),
                    safe_projection=FrozenJsonObject.from_mapping(
                        {"work_id": work_id, "priority": priority, "title": event_id}
                    ),
                )
                EventService(scenario.store, scenario.identifiers, FixedClock(T0)).submit(
                    context=RequestPrincipalContext(namespace(), user()),
                    request=request_for_event(event),
                    idempotency_key=f"key-{event_id}",
                )
            wake = WakeService(
                store=scenario.store,
                intelligence=DeterministicIntelligence(),
                clock=FixedClock(T2),
                identifiers=scenario.identifiers,
                service_principal=service(),
                model_principal=model(),
                mandate_id="mandate-synthetic",
                owner_id="worker-attention",
            )
            wake.materialize_next(namespace())
            wake.materialize_next(namespace())
            first = scenario.store.claim_agenda(
                namespace(), owner="attention-owner", now=T2, lease_until=T3
            )
            assert first is not None
            self.assertEqual(first.agenda_item.work_id, "work-attention-high")
            scenario.store.release_agenda(first)
            second = scenario.store.claim_agenda(
                namespace(), owner="attention-owner", now=T2, lease_until=T3
            )
            assert second is not None
            self.assertEqual(second.agenda_item.work_id, "work-attention-low")
            scenario.store.release_agenda(second)
            scenario.store.close()

    def test_exact_effect_tampering_and_stale_mandate_never_call_channel(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-tamper-") as temporary:
            scenario = prepare_proposal(
                Path(temporary) / "state.sqlite", identifier_namespace="tamper"
            )
            approve(scenario)
            row = scenario.store._connection.execute(  # noqa: SLF001
                "SELECT payload_json FROM domain_records WHERE record_type = 'effect_proposal'"
            ).fetchone()
            payload = json.loads(row["payload_json"])
            payload["fields"]["payload"]["$frozen_json"][0][1] = "tampered-body"
            scenario.store._connection.execute(  # noqa: SLF001
                "UPDATE domain_records SET payload_json = ? WHERE record_type = 'effect_proposal'",
                (json.dumps(payload, separators=(",", ":"), sort_keys=True),),
            )
            channel = ReferenceChannel()
            with self.assertRaises(PersistenceError):
                _dispatch(scenario, channel).dispatch_once(namespace())
            self.assertEqual(channel.call_count, 0)
            scenario.store.close()

        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-stale-") as temporary:
            scenario = prepare_proposal(
                Path(temporary) / "state.sqlite", identifier_namespace="stale"
            )
            approve(scenario)
            current = scenario.store.get_mandate(namespace(), "mandate-synthetic")
            with scenario.store._transaction() as connection:  # noqa: SLF001
                scenario.store._update_record(  # noqa: SLF001
                    connection,
                    replace(current, revision=2, effective_at=T2),
                    expected_revision=1,
                )
            channel = ReferenceChannel()
            with self.assertRaises(PermissionDeniedError):
                _dispatch(scenario, channel).dispatch_once(namespace())
            self.assertEqual(channel.call_count, 0)
            scenario.store.close()

    def test_model_and_service_cannot_construct_or_submit_human_approval(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-principal-") as temporary:
            scenario = prepare_proposal(
                Path(temporary) / "state.sqlite", identifier_namespace="principal"
            )
            proposal = scenario.proposal
            values = {
                "namespace": namespace(),
                "approval_decision_id": "approval-invalid",
                "proposal_id": proposal.proposal_id,
                "proposal_revision": proposal.revision,
                "proposal_payload_digest": proposal.payload_digest,
                "proposal_digest": proposal.proposal_digest,
                "choice": ApprovalChoice.APPROVE,
                "idempotency_key": "approval-invalid-key",
                "correlation_id": proposal.correlation_id,
                "causation_id": proposal.proposal_id,
                "occurred_at": T2,
                "valid_until": T3,
                "revision": 1,
            }
            for principal in (model(), service()):
                with self.subTest(kind=principal.kind.value), self.assertRaises(ValueError):
                    HumanApprovalDecision(author=principal, **values)  # type: ignore[arg-type]
            scenario.store.close()

    def test_retryable_outcome_uses_new_attempt_and_stops_at_success(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-retry-") as temporary:
            scenario = prepare_proposal(
                Path(temporary) / "state.sqlite", identifier_namespace="retry"
            )
            approve(scenario)
            channel = ReferenceChannel(
                (
                    ChannelOutcomeKind.RETRYABLE_FAILURE,
                    ChannelOutcomeKind.SUCCEEDED,
                )
            )
            dispatch = _dispatch(scenario, channel)
            first = dispatch.dispatch_once(namespace())
            second = dispatch.dispatch_once(namespace())
            third = dispatch.dispatch_once(namespace())
            self.assertEqual(first.outcome, ChannelOutcomeKind.RETRYABLE_FAILURE)
            self.assertEqual(second.outcome, ChannelOutcomeKind.SUCCEEDED)
            self.assertFalse(third.dispatched)
            self.assertEqual(channel.call_count, 2)
            attempts = scenario.store._connection.execute(  # noqa: SLF001
                "SELECT COUNT(*) FROM domain_records WHERE record_type = 'effect_attempt'"
            ).fetchone()[0]
            self.assertEqual(attempts, 2)
            scenario.store.close()

    def test_ambiguous_outcome_requires_reconciliation_before_confirmed_absent_retry(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-ambiguous-") as temporary:
            scenario = prepare_proposal(
                Path(temporary) / "state.sqlite", identifier_namespace="ambiguous"
            )
            approve(scenario)
            channel = ReferenceChannel(
                (ChannelOutcomeKind.AMBIGUOUS, ChannelOutcomeKind.SUCCEEDED),
                reconciliation=ReconciliationKind.STILL_UNKNOWN,
            )
            dispatch = _dispatch(scenario, channel)
            first = dispatch.dispatch_once(namespace())
            self.assertEqual(first.outcome, ChannelOutcomeKind.AMBIGUOUS)
            self.assertFalse(dispatch.dispatch_once(namespace()).dispatched)
            unknown = dispatch.reconcile_once(namespace())
            self.assertEqual(unknown.outcome, ChannelOutcomeKind.AMBIGUOUS)
            self.assertEqual(channel.call_count, 1)
            channel.reconciliation = ReconciliationKind.CONFIRMED_ABSENT
            absent = dispatch.reconcile_once(namespace())
            self.assertEqual(absent.outcome, ChannelOutcomeKind.KNOWN_NOT_EXECUTED)
            succeeded = dispatch.dispatch_once(namespace())
            self.assertEqual(succeeded.outcome, ChannelOutcomeKind.SUCCEEDED)
            self.assertEqual(channel.call_count, 2)
            scenario.store.close()

    def test_crash_after_channel_return_recovers_as_ambiguous_without_redispatch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-crash-") as temporary:
            scenario = prepare_proposal(
                Path(temporary) / "state.sqlite", identifier_namespace="crash"
            )
            approve(scenario)
            channel = ReferenceChannel(
                (ChannelOutcomeKind.SUCCEEDED,),
                reconciliation=ReconciliationKind.CONFIRMED_APPLIED,
            )
            crashing = _dispatch(
                scenario,
                channel,
                checkpoint=_CrashAt("channel_returned"),
            )
            with self.assertRaisesRegex(RuntimeError, "synthetic crash"):
                crashing.dispatch_once(namespace())
            self.assertEqual(channel.call_count, 1)
            later = FixedClock(T3 + timedelta(minutes=1))
            recovering = _dispatch(scenario, channel, clock=later)
            self.assertEqual(recovering.recover_expired(namespace()), 1)
            self.assertFalse(recovering.dispatch_once(namespace()).dispatched)
            reconciled = recovering.reconcile_once(namespace())
            self.assertEqual(reconciled.outcome, ChannelOutcomeKind.SUCCEEDED)
            self.assertEqual(channel.call_count, 1)
            scenario.store.close()

    def test_claim_dispatch_and_finalized_crash_checkpoints_recover_without_duplicate_effects(
        self,
    ) -> None:
        later = FixedClock(T3 + timedelta(minutes=1))
        for checkpoint in ("outbox_claimed", "dispatch_started", "dispatch_finalized"):
            with (
                self.subTest(checkpoint=checkpoint),
                tempfile.TemporaryDirectory(
                    prefix=f"digital-colleagues-p3-{checkpoint}-"
                ) as temporary,
            ):
                database = Path(temporary) / "state.sqlite"
                scenario = prepare_proposal(database, identifier_namespace=checkpoint)
                approve(scenario)
                channel = ReferenceChannel(
                    (ChannelOutcomeKind.SUCCEEDED,),
                    reconciliation=ReconciliationKind.CONFIRMED_ABSENT,
                )
                with self.assertRaisesRegex(RuntimeError, "synthetic crash"):
                    _dispatch(
                        scenario,
                        channel,
                        checkpoint=_CrashAt(checkpoint),
                    ).dispatch_once(namespace())
                expected_calls_at_crash = 1 if checkpoint == "dispatch_finalized" else 0
                self.assertEqual(channel.call_count, expected_calls_at_crash)
                scenario.store.close()
                scenario.store = new_store(database)
                recovering = _dispatch(scenario, channel, clock=later)
                if checkpoint == "outbox_claimed":
                    completed = recovering.dispatch_once(namespace())
                    self.assertEqual(completed.outcome, ChannelOutcomeKind.SUCCEEDED)
                elif checkpoint == "dispatch_started":
                    self.assertEqual(recovering.recover_expired(namespace()), 1)
                    confirmed_absent = recovering.reconcile_once(namespace())
                    self.assertEqual(
                        confirmed_absent.outcome,
                        ChannelOutcomeKind.KNOWN_NOT_EXECUTED,
                    )
                    completed = recovering.dispatch_once(namespace())
                    self.assertEqual(completed.outcome, ChannelOutcomeKind.SUCCEEDED)
                else:
                    self.assertEqual(recovering.recover_expired(namespace()), 0)
                    self.assertFalse(recovering.dispatch_once(namespace()).dispatched)
                self.assertEqual(channel.call_count, 1)
                self.assertFalse(recovering.dispatch_once(namespace()).dispatched)
                scenario.store.close()

    def test_generation_interleaving_retains_causes_and_old_checkpoint_cannot_finish_new_cause(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-generation-") as temporary:
            scenario = prepare_proposal(
                Path(temporary) / "state.sqlite", identifier_namespace="generation"
            )
            agenda_id = scenario.identifiers.derive("agenda", "event-synthetic")
            original = scenario.store.get_agenda_item(namespace(), agenda_id)
            self.assertEqual(original.handled_generation, 1)
            second_event = input_event(
                event_id="event-synthetic-second",
                correlation_id="correlation-p3-second",
            )
            EventService(scenario.store, scenario.identifiers, FixedClock(T0)).submit(
                context=RequestPrincipalContext(namespace(), user()),
                request=request_for_event(second_event),
                idempotency_key="event-key-second",
            )
            wake = WakeService(
                store=scenario.store,
                intelligence=DeterministicIntelligence(),
                clock=FixedClock(T2),
                identifiers=scenario.identifiers,
                service_principal=service(),
                model_principal=model(),
                mandate_id="mandate-synthetic",
                owner_id="worker-generation",
                max_items=1,
                max_decisions=1,
            )
            wake.materialize_next(namespace())
            interleaved = scenario.store.get_agenda_item(namespace(), agenda_id)
            self.assertEqual(interleaved.generation, 2)
            self.assertEqual(interleaved.handled_generation, 1)
            self.assertEqual(
                interleaved.cause_ids,
                ("event-synthetic", "event-synthetic-second"),
            )
            old_claim = scenario.store.claim_agenda(
                namespace(), owner="owner-old-generation", now=T2, lease_until=T3
            )
            assert old_claim is not None
            third_event = input_event(
                event_id="event-synthetic-third",
                correlation_id="correlation-p3-third",
            )
            EventService(scenario.store, scenario.identifiers, FixedClock(T0)).submit(
                context=RequestPrincipalContext(namespace(), user()),
                request=request_for_event(third_event),
                idempotency_key="event-key-third",
            )
            wake.materialize_next(namespace())
            request = IntelligenceRequest(
                namespace=namespace(),
                request_id="request-generation-two",
                wake_cycle=scenario.store.get_wake_cycle(
                    namespace(), old_claim.agenda_item.wake_cycle_id
                ),
                agenda_item=old_claim.agenda_item,
                mandate=scenario.store.get_mandate(namespace(), "mandate-synthetic"),
                model_principal=model(),
                decision_id="decision-generation-two",
                proposal_id="proposal-generation-two",
                effect_idempotency_key="effect-generation-two",
                occurred_at=T2,
                proposal_valid_until=T3,
            )
            scenario.store.commit_semantic_decision(
                old_claim, DeterministicIntelligence().decide(request)
            )
            pending_new_cause = scenario.store.get_agenda_item(namespace(), agenda_id)
            self.assertEqual(pending_new_cause.generation, 3)
            self.assertEqual(pending_new_cause.handled_generation, 2)
            self.assertEqual(pending_new_cause.state, AgendaItemState.PENDING)
            result = wake.run(namespace())
            self.assertEqual(result.decision_count, 1)
            completed = scenario.store.get_agenda_item(namespace(), agenda_id)
            self.assertEqual(completed.handled_generation, 3)
            scenario.store.close()

    def test_deterministic_provider_is_byte_equivalent_and_no_pending_work_avoids_call(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-determinism-") as temporary:
            scenario = prepare_proposal(
                Path(temporary) / "state.sqlite", identifier_namespace="determinism"
            )
            agenda_id = scenario.identifiers.derive("agenda", "event-synthetic")
            agenda = scenario.store.get_agenda_item(namespace(), agenda_id)
            wake_id = agenda.wake_cycle_id
            request = IntelligenceRequest(
                namespace=namespace(),
                request_id="request-byte-equivalent",
                wake_cycle=scenario.store.get_wake_cycle(namespace(), wake_id),
                agenda_item=replace(agenda, state=AgendaItemState.SELECTED),
                mandate=scenario.store.get_mandate(namespace(), "mandate-synthetic"),
                model_principal=model(),
                decision_id="decision-byte-equivalent",
                proposal_id="proposal-byte-equivalent",
                effect_idempotency_key="effect-byte-equivalent",
                occurred_at=T2,
                proposal_valid_until=T3,
            )
            left = DeterministicIntelligence().decide(request)
            right = DeterministicIntelligence().decide(request)
            self.assertEqual(to_storage_json(left.decision), to_storage_json(right.decision))
            self.assertEqual(to_storage_json(left.proposal), to_storage_json(right.proposal))
            provider = DeterministicIntelligence()
            no_work = WakeService(
                store=scenario.store,
                intelligence=provider,
                clock=FixedClock(T2),
                identifiers=scenario.identifiers,
                service_principal=service(),
                model_principal=model(),
                mandate_id="mandate-synthetic",
                owner_id="worker-noop",
            ).run(namespace())
            self.assertEqual(no_work.selected_count, 0)
            self.assertEqual(provider.call_count, 0)
            scenario.store.close()

    def test_pending_application_noop_is_durable_without_intelligence_or_effects_after_restart(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-noop-") as temporary:
            database = Path(temporary) / "state.sqlite"
            scenario = prepare_proposal(database, identifier_namespace="application-noop")
            noop_event = replace(
                input_event(
                    event_id="event-application-noop",
                    correlation_id="correlation-application-noop",
                ),
                safe_projection=FrozenJsonObject.from_mapping(
                    {
                        "work_id": "work-application-noop",
                        "priority": 500,
                        "title": "noop: deterministic application completion",
                    }
                ),
            )
            EventService(scenario.store, scenario.identifiers, FixedClock(T0)).submit(
                context=RequestPrincipalContext(namespace(), user()),
                request=request_for_event(noop_event),
                idempotency_key="event-key-application-noop",
            )
            intelligence = DeterministicIntelligence()
            wake = WakeService(
                store=scenario.store,
                intelligence=intelligence,
                clock=FixedClock(T2),
                identifiers=scenario.identifiers,
                service_principal=service(),
                model_principal=model(),
                mandate_id="mandate-synthetic",
                owner_id="worker-application-noop",
            )
            self.assertIsNotNone(wake.materialize_next(namespace()))
            result = wake.run(namespace())
            self.assertEqual(result.decision_count, 1)
            self.assertEqual(intelligence.call_count, 0)
            history_before = scenario.store.causal_history(
                namespace(), "correlation-application-noop"
            )
            record_types = {record["record_type"] for record in history_before}
            self.assertIn("decision", record_types)
            self.assertTrue(
                record_types.isdisjoint(
                    {"effect_proposal", "human_approval", "effect_attempt", "action_result"}
                )
            )
            outbox_count = scenario.store._connection.execute(  # noqa: SLF001
                "SELECT COUNT(*) FROM outbox WHERE correlation_id = ?",
                ("correlation-application-noop",),
            ).fetchone()[0]
            self.assertEqual(outbox_count, 0)
            canonical_before = json.dumps(
                history_before, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
            scenario.store.close()

            restarted = new_store(database)
            replay_intelligence = DeterministicIntelligence()
            replay = WakeService(
                store=restarted,
                intelligence=replay_intelligence,
                clock=FixedClock(T3),
                identifiers=scenario.identifiers,
                service_principal=service(),
                model_principal=model(),
                mandate_id="mandate-synthetic",
                owner_id="worker-application-noop-restart",
            ).run(namespace())
            self.assertEqual(replay.selected_count, 0)
            self.assertEqual(replay_intelligence.call_count, 0)
            history_after = restarted.causal_history(namespace(), "correlation-application-noop")
            canonical_after = json.dumps(
                history_after, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
            self.assertEqual(canonical_after, canonical_before)
            self.assertEqual(ReferenceChannel().call_count, 0)
            restarted.close()


if __name__ == "__main__":
    unittest.main()
