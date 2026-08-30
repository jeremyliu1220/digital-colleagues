# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from digital_colleagues.adapters.system.deterministic import FixedClock, StableHashIdentifier
from digital_colleagues.application.contracts import RequestPrincipalContext
from digital_colleagues.application.errors import ConflictError, NotFoundError
from digital_colleagues.application.services import BootstrapService, TimerService
from digital_colleagues.core.errors import NamespaceMismatchError
from tests.p3.fixtures import (
    T0,
    T1,
    T2,
    T3,
    admin,
    finite_work,
    mandate,
    namespace,
    other_namespace,
    principals,
    profile,
    service,
    timer_request,
)
from tests.p3.scenario import new_store


class TimerRuntimeTests(unittest.TestCase):
    def test_durable_timer_due_replay_restart_fencing_causation_and_namespace_isolation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-timer-") as temporary:
            database = Path(temporary) / "state.sqlite"
            identifiers = StableHashIdentifier("timer-runtime")
            store = new_store(database)
            BootstrapService(store, FixedClock(T0)).initialize(
                context=RequestPrincipalContext(namespace(), admin()),
                principals=principals(),
                profile=profile(),
                mandate=mandate(),
                work=finite_work(),
                correlation_id="correlation-timer-bootstrap",
            )
            request = timer_request()
            scheduled, created = TimerService(
                store, identifiers, FixedClock(T0), service()
            ).schedule(namespace=namespace(), request=request)
            self.assertTrue(created)
            replayed, replay_created = TimerService(
                store, identifiers, FixedClock(T1), service()
            ).schedule(namespace=namespace(), request=request)
            self.assertFalse(replay_created)
            self.assertEqual(replayed, scheduled)
            timer_rows = store._connection.execute(  # noqa: SLF001
                "SELECT COUNT(*) FROM timer_triggers WHERE occurrence_id = ?",
                (request.occurrence_id,),
            ).fetchone()[0]
            self.assertEqual(timer_rows, 1)
            self.assertIsNone(
                store.claim_trigger(namespace(), owner="early", now=T1, lease_until=T2)
            )
            with self.assertRaises(NotFoundError):
                store.get_timer_occurrence(other_namespace(), request.occurrence_id)
            with self.assertRaises(NamespaceMismatchError):
                TimerService(store, identifiers, FixedClock(T0), service()).schedule(
                    namespace=other_namespace(), request=request
                )

            first = store.claim_trigger(namespace(), owner="timer-owner-a", now=T2, lease_until=T2)
            assert first is not None
            self.assertEqual(first.source_record_type, "timer_occurrence")
            store.close()

            restarted = new_store(database)
            takeover = restarted.claim_trigger(
                namespace(), owner="timer-owner-b", now=T3, lease_until=T3
            )
            assert takeover is not None
            self.assertGreater(takeover.fencing_token, first.fencing_token)
            with self.assertRaises(ConflictError):
                restarted.materialize_agenda(
                    first,
                    wake_cycle_id="wake-timer-stale",
                    agenda_item_id="agenda-timer-stale",
                    actor=service(),
                    occurred_at=T2,
                )
            wake, agenda = restarted.materialize_agenda(
                takeover,
                wake_cycle_id="wake-timer-current",
                agenda_item_id="agenda-timer-current",
                actor=service(),
                occurred_at=T3,
            )
            self.assertEqual(wake.trigger_event_ids, ())
            self.assertEqual(wake.trigger_timer_occurrence_ids, (request.occurrence_id,))
            self.assertIsNone(agenda.source_event_id)
            self.assertEqual(agenda.source_timer_occurrence_id, request.occurrence_id)
            self.assertEqual(agenda.cause_ids, (request.occurrence_id,))
            late_replay, late_replay_created = TimerService(
                restarted, identifiers, FixedClock(T3), service()
            ).schedule(namespace=namespace(), request=request)
            self.assertFalse(late_replay_created)
            self.assertEqual(late_replay, scheduled)
            self.assertIsNone(
                restarted.claim_trigger(namespace(), owner="timer-owner-c", now=T3, lease_until=T3)
            )
            history_before = restarted.causal_history(namespace(), request.correlation_id)
            self.assertTrue(
                {"timer_occurrence", "wake_cycle", "agenda_item"}.issubset(
                    {record["record_type"] for record in history_before}
                )
            )
            canonical_before = json.dumps(
                history_before, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
            restarted.close()

            final = new_store(database)
            self.assertEqual(
                final.get_timer_occurrence(namespace(), request.occurrence_id), scheduled
            )
            history_after = final.causal_history(namespace(), request.correlation_id)
            canonical_after = json.dumps(
                history_after, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
            self.assertEqual(canonical_after, canonical_before)
            final.close()


if __name__ == "__main__":
    unittest.main()
