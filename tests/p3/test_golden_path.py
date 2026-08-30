# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from digital_colleagues.adapters.channel.reference import ReferenceChannel
from digital_colleagues.adapters.intelligence.deterministic import DeterministicIntelligence
from digital_colleagues.adapters.sqlite.store import SQLiteRuntimeStore
from digital_colleagues.adapters.system.deterministic import FixedClock, StableHashIdentifier
from digital_colleagues.application.contracts import ChannelOutcomeKind, RequestPrincipalContext
from digital_colleagues.application.services import (
    ApprovalService,
    BootstrapService,
    DispatchService,
    EventService,
    WakeService,
)
from tests.p3.fixtures import (
    T0,
    T1,
    T2,
    T3,
    admin,
    approval_request,
    finite_work,
    input_event,
    input_event_request,
    mandate,
    model,
    namespace,
    principals,
    profile,
    service,
    user,
)

ROOT = Path(__file__).resolve().parents[2]


class GoldenPathTests(unittest.TestCase):
    def test_headless_restart_golden_path_is_recoverable_and_byte_equivalent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-test-") as temporary:
            database = Path(temporary) / "state.sqlite"
            identifiers = StableHashIdentifier("golden")
            store = SQLiteRuntimeStore(
                database,
                migrations_path=ROOT / "migrations",
                clock=FixedClock(T0),
            )
            bootstrap = BootstrapService(store, FixedClock(T0))
            created = bootstrap.initialize(
                context=RequestPrincipalContext(namespace(), admin()),
                principals=principals(),
                profile=profile(),
                mandate=mandate(),
                work=finite_work(),
                correlation_id="correlation-bootstrap",
            )
            self.assertTrue(created)
            event_service = EventService(store, identifiers, FixedClock(T0))
            event = input_event()
            stored_event, event_created = event_service.submit(
                context=RequestPrincipalContext(namespace(), user()),
                request=input_event_request(),
                idempotency_key="event-key-synthetic",
            )
            self.assertTrue(event_created)
            self.assertEqual(stored_event, event)
            intelligence = DeterministicIntelligence()
            wake = WakeService(
                store=store,
                intelligence=intelligence,
                clock=FixedClock(T1),
                identifiers=identifiers,
                service_principal=service(),
                model_principal=model(),
                mandate_id="mandate-synthetic",
                owner_id="worker-wake-a",
            )
            materialized = wake.materialize_next(namespace())
            self.assertIsNotNone(materialized)
            wake_result = wake.run(namespace())
            self.assertEqual(wake_result.decision_count, 1)
            self.assertEqual(wake_result.outcome, "terminal")
            self.assertEqual(intelligence.call_count, 1)
            agenda_id = identifiers.derive("agenda", event.event_id)
            request_id = identifiers.derive("request", agenda_id, "1")
            proposal_id = identifiers.derive("proposal", request_id)
            proposal = store.get_proposal(namespace(), proposal_id)
            approval = approval_request(proposal)
            approval_service = ApprovalService(
                store=store,
                clock=FixedClock(T2),
                identifiers=identifiers,
                service_principal=service(),
            )
            stored_approval, attempt_id, approval_created = approval_service.decide(
                context=RequestPrincipalContext(namespace(), user()),
                mandate_id="mandate-synthetic",
                expected_mandate_revision=1,
                request=approval,
            )
            self.assertTrue(approval_created)
            self.assertIsNotNone(attempt_id)
            decision = stored_approval
            self.assertEqual(decision.occurred_at, T2)
            self.assertEqual(decision.valid_until, T2 + timedelta(minutes=15))
            channel = ReferenceChannel((ChannelOutcomeKind.SUCCEEDED,))
            dispatch = DispatchService(
                store=store,
                channel=channel,
                clock=FixedClock(T3),
                identifiers=identifiers,
                result_actor=service(),
                owner_id="worker-dispatch-a",
                mandate_id="mandate-synthetic",
            )
            dispatched = dispatch.dispatch_once(namespace())
            self.assertTrue(dispatched.dispatched)
            self.assertEqual(dispatched.outcome, ChannelOutcomeKind.SUCCEEDED)
            self.assertEqual(channel.call_count, 1)
            self.assertIsNotNone(dispatched.action_result_id)
            assert dispatched.action_result_id is not None
            result = store.get_action_result(namespace(), dispatched.action_result_id)
            history_before = store.causal_history(namespace(), "correlation-p3")
            record_types = {record["record_type"] for record in history_before}
            self.assertTrue(
                {
                    "input_event",
                    "wake_cycle",
                    "agenda_item",
                    "decision",
                    "effect_proposal",
                    "human_approval",
                    "effect_attempt",
                    "action_result",
                }.issubset(record_types)
            )
            canonical_before = json.dumps(
                history_before, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
            store.close()

            restarted = SQLiteRuntimeStore(
                database,
                migrations_path=ROOT / "migrations",
                clock=FixedClock(T3),
            )
            self.assertEqual(restarted.get_profile(namespace(), "profile-synthetic"), profile())
            self.assertEqual(restarted.get_mandate(namespace(), "mandate-synthetic"), mandate())
            self.assertEqual(restarted.get_work(namespace(), "work-synthetic"), finite_work())
            self.assertEqual(restarted.get_event(namespace(), event.event_id), event)
            self.assertEqual(
                restarted.get_agenda_item(namespace(), agenda_id).handled_generation, 1
            )
            self.assertEqual(
                restarted.get_approval(namespace(), decision.approval_decision_id), decision
            )
            self.assertEqual(
                restarted.get_action_result(namespace(), result.action_result_id), result
            )
            history_after = restarted.causal_history(namespace(), "correlation-p3")
            canonical_after = json.dumps(
                history_after, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
            self.assertEqual(canonical_after, canonical_before)

            replayed_event, replay_event_created = EventService(
                restarted, identifiers, FixedClock(T3)
            ).submit(
                context=RequestPrincipalContext(namespace(), user()),
                request=input_event_request(),
                idempotency_key="event-key-synthetic",
            )
            self.assertFalse(replay_event_created)
            self.assertEqual(replayed_event, event)
            replay_approval = ApprovalService(
                store=restarted,
                clock=FixedClock(T3),
                identifiers=identifiers,
                service_principal=service(),
            ).decide(
                context=RequestPrincipalContext(namespace(), user()),
                mandate_id="mandate-synthetic",
                expected_mandate_revision=1,
                request=approval,
            )
            self.assertFalse(replay_approval[2])
            self.assertEqual(replay_approval[0], decision)
            replay_channel = ReferenceChannel((ChannelOutcomeKind.SUCCEEDED,))
            replay_dispatch = DispatchService(
                store=restarted,
                channel=replay_channel,
                clock=FixedClock(T3),
                identifiers=identifiers,
                result_actor=service(),
                owner_id="worker-dispatch-b",
                mandate_id="mandate-synthetic",
            ).dispatch_once(namespace())
            self.assertFalse(replay_dispatch.dispatched)
            self.assertEqual(replay_channel.call_count, 0)
            self.assertEqual(restarted.causal_history(namespace(), "correlation-p3"), history_after)
            restarted.close()


if __name__ == "__main__":
    unittest.main()
