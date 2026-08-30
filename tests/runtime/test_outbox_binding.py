# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

from digital_colleagues.adapters.channel.reference import ReferenceChannel
from digital_colleagues.adapters.system.deterministic import FixedClock
from digital_colleagues.application.contracts import ChannelOutcomeKind
from digital_colleagues.application.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    PersistenceError,
)
from digital_colleagues.application.services import DispatchService
from tests.p3.fixtures import T3, namespace, service
from tests.p3.scenario import PreparedScenario, approve, prepare_proposal


def _tamper_outbox(scenario: PreparedScenario, column: str, value: object) -> None:
    allowed = {
        "proposal_id",
        "approval_decision_id",
        "effect_attempt_id",
        "effect_idempotency_key",
        "attempt_number",
        "maximum_attempts",
    }
    if column not in allowed:
        raise AssertionError("test attempted an unsupported outbox mutation")
    connection = scenario.store._connection  # noqa: SLF001
    if column == "effect_attempt_id":
        connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute(f"UPDATE outbox SET {column} = ?", (value,))
    if column == "effect_attempt_id":
        connection.execute("PRAGMA foreign_keys = ON")


def _tamper_record(
    scenario: PreparedScenario,
    record_type: str,
    field: str,
    value: object,
) -> None:
    connection = scenario.store._connection  # noqa: SLF001
    row = connection.execute(
        "SELECT payload_json FROM domain_records WHERE record_type = ?", (record_type,)
    ).fetchone()
    payload = json.loads(row["payload_json"])
    payload["fields"][field] = value
    connection.execute(
        "UPDATE domain_records SET payload_json = ? WHERE record_type = ?",
        (json.dumps(payload, separators=(",", ":"), sort_keys=True), record_type),
    )


class OutboxBindingTests(unittest.TestCase):
    def test_complete_outbox_binding_tampering_never_calls_channel(self) -> None:
        different_digest = "sha256:" + ("9" * 64)
        mutations: tuple[tuple[str, Callable[[PreparedScenario], None]], ...] = (
            ("outbox_proposal", lambda s: _tamper_outbox(s, "proposal_id", "proposal-drift")),
            (
                "outbox_approval",
                lambda s: _tamper_outbox(s, "approval_decision_id", "approval-drift"),
            ),
            (
                "outbox_attempt",
                lambda s: _tamper_outbox(s, "effect_attempt_id", "attempt-drift"),
            ),
            (
                "outbox_effect_key",
                lambda s: _tamper_outbox(s, "effect_idempotency_key", "effect-drift"),
            ),
            ("outbox_attempt_number", lambda s: _tamper_outbox(s, "attempt_number", 2)),
            ("outbox_attempt_limit", lambda s: _tamper_outbox(s, "maximum_attempts", 99)),
            (
                "approval_payload_digest",
                lambda s: _tamper_record(
                    s, "human_approval", "proposal_payload_digest", different_digest
                ),
            ),
            (
                "approval_proposal_digest",
                lambda s: _tamper_record(s, "human_approval", "proposal_digest", different_digest),
            ),
            (
                "attempt_proposal_revision",
                lambda s: _tamper_record(s, "effect_attempt", "proposal_revision", 2),
            ),
            (
                "attempt_approval",
                lambda s: _tamper_record(
                    s, "effect_attempt", "approval_decision_id", "approval-drift"
                ),
            ),
            (
                "attempt_number",
                lambda s: _tamper_record(s, "effect_attempt", "attempt_number", 2),
            ),
            (
                "proposal_mandate_revision",
                lambda s: _tamper_record(s, "effect_proposal", "mandate_revision", 2),
            ),
        )
        for name, mutate in mutations:
            with (
                self.subTest(binding=name),
                tempfile.TemporaryDirectory(
                    prefix=f"digital-colleagues-p3-outbox-{name}-"
                ) as temporary,
            ):
                scenario = prepare_proposal(
                    Path(temporary) / "state.sqlite",
                    identifier_namespace=f"outbox-{name}",
                )
                approve(scenario)
                mutate(scenario)
                channel = ReferenceChannel()
                dispatch = DispatchService(
                    store=scenario.store,
                    channel=channel,
                    clock=FixedClock(T3),
                    identifiers=scenario.identifiers,
                    result_actor=service(),
                    owner_id="worker-outbox-binding",
                    mandate_id="mandate-synthetic",
                )
                with self.assertRaises(
                    (ConflictError, NotFoundError, PermissionDeniedError, PersistenceError)
                ):
                    dispatch.dispatch_once(namespace())
                self.assertEqual(channel.call_count, 0)
                scenario.store.close()

    def test_retryable_failures_stop_exactly_at_durable_maximum_attempts(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="digital-colleagues-p3-outbox-attempt-limit-"
        ) as temporary:
            scenario = prepare_proposal(
                Path(temporary) / "state.sqlite", identifier_namespace="outbox-attempt-limit"
            )
            approve(scenario)
            channel = ReferenceChannel(
                (
                    ChannelOutcomeKind.RETRYABLE_FAILURE,
                    ChannelOutcomeKind.RETRYABLE_FAILURE,
                    ChannelOutcomeKind.RETRYABLE_FAILURE,
                    ChannelOutcomeKind.SUCCEEDED,
                )
            )
            dispatch = DispatchService(
                store=scenario.store,
                channel=channel,
                clock=FixedClock(T3),
                identifiers=scenario.identifiers,
                result_actor=service(),
                owner_id="worker-outbox-attempt-limit",
                mandate_id="mandate-synthetic",
            )
            outcomes = [dispatch.dispatch_once(namespace()) for _ in range(4)]
            self.assertTrue(all(result.dispatched for result in outcomes[:3]))
            self.assertFalse(outcomes[3].dispatched)
            self.assertEqual(channel.call_count, 3)
            attempt_count = scenario.store._connection.execute(  # noqa: SLF001
                "SELECT COUNT(*) FROM domain_records WHERE record_type = 'effect_attempt'"
            ).fetchone()[0]
            self.assertEqual(attempt_count, 3)
            outbox = scenario.store._connection.execute(  # noqa: SLF001
                "SELECT attempt_number, maximum_attempts, state FROM outbox"
            ).fetchone()
            self.assertEqual(
                (outbox["attempt_number"], outbox["maximum_attempts"], outbox["state"]),
                (3, 3, "terminal_failed"),
            )
            scenario.store.close()


if __name__ == "__main__":
    unittest.main()
