# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import dataclasses
import unittest

from digital_colleagues.core import (
    AgendaItem,
    agenda_order_key,
    validate_causal_audit_chain,
    validate_event_wake_agenda_chain,
)
from digital_colleagues.core.errors import CoreInvariantError, NamespaceMismatchError
from tests.core.fixtures import (
    T2,
    action_result,
    agenda_item,
    approval_decision,
    colleague_namespace,
    decision,
    effect_attempt,
    effect_proposal,
    input_event,
    other_namespace,
    service_principal,
    wake_cycle,
)


class RuntimeAndAuditTests(unittest.TestCase):
    def test_event_wake_agenda_chain_is_explicit(self) -> None:
        event = input_event()
        wake = wake_cycle()
        agenda = agenda_item()
        validate_event_wake_agenda_chain(event, wake, agenda)
        self.assertEqual(wake.causation_id, event.event_id)
        self.assertEqual(agenda.causation_id, wake.wake_cycle_id)
        self.assertEqual(agenda.source_event_id, event.event_id)

    def test_cross_namespace_causal_chain_is_rejected(self) -> None:
        with self.assertRaises(NamespaceMismatchError):
            dataclasses.replace(agenda_item(), namespace=other_namespace())

    def test_agenda_ordering_uses_only_injected_inputs(self) -> None:
        first = agenda_item()
        higher = dataclasses.replace(
            first,
            agenda_item_id="agenda-item-002",
            priority=900,
        )
        no_due = dataclasses.replace(
            first,
            agenda_item_id="agenda-item-003",
            due_at=None,
        )
        ordered = sorted((no_due, first, higher), key=agenda_order_key)
        self.assertEqual(
            tuple(item.agenda_item_id for item in ordered),
            ("agenda-item-002", "agenda-item-001", "agenda-item-003"),
        )

    def test_agenda_requires_its_wake_cycle_as_causation(self) -> None:
        with self.assertRaises(CoreInvariantError):
            AgendaItem(
                namespace=colleague_namespace(),
                agenda_item_id="agenda-item-bad",
                wake_cycle_id="wake-cycle-001",
                source_event_id="input-event-001",
                work_id=None,
                title="Invalid causal item",
                state=agenda_item().state,
                priority=1,
                due_at=None,
                actor=service_principal(),
                correlation_id="correlation-001",
                causation_id="wake-cycle-other",
                occurred_at=T2,
                revision=1,
            )

    def test_full_causal_audit_chain_validates(self) -> None:
        validate_causal_audit_chain(
            input_event(),
            wake_cycle(),
            agenda_item(),
            decision(),
            effect_proposal(),
            approval_decision(),
            effect_attempt(),
            action_result(),
        )

    def test_full_chain_rejects_wrong_effect_revision(self) -> None:
        with self.assertRaises(CoreInvariantError):
            validate_causal_audit_chain(
                input_event(),
                wake_cycle(),
                agenda_item(),
                decision(),
                effect_proposal(revision=2),
                approval_decision(),
                effect_attempt(),
                action_result(),
            )


if __name__ == "__main__":
    unittest.main()
