# SPDX-License-Identifier: Apache-2.0

"""Pure validation for the minimum causal audit chain."""

from __future__ import annotations

from digital_colleagues.core.effects import (
    ActionResult,
    EffectAttempt,
    EffectProposal,
    HumanApprovalDecision,
)
from digital_colleagues.core.errors import CoreInvariantError
from digital_colleagues.core.runtime import (
    AgendaItem,
    Decision,
    InputEvent,
    WakeCycle,
    validate_event_wake_agenda_chain,
)


def validate_causal_audit_chain(
    event: InputEvent,
    wake_cycle: WakeCycle,
    agenda_item: AgendaItem,
    decision: Decision,
    proposal: EffectProposal,
    approval: HumanApprovalDecision,
    attempt: EffectAttempt,
    result: ActionResult,
) -> None:
    validate_event_wake_agenda_chain(event, wake_cycle, agenda_item)
    records = (wake_cycle, agenda_item, decision, proposal, approval, attempt, result)
    for record in records:
        event.namespace.require_exact(record.namespace)
        if record.correlation_id != event.correlation_id:
            raise CoreInvariantError("causal audit correlation mismatch")
    if decision.wake_cycle_id != wake_cycle.wake_cycle_id:
        raise CoreInvariantError("decision does not cite the wake cycle")
    if decision.agenda_item_id != agenda_item.agenda_item_id:
        raise CoreInvariantError("decision does not cite the agenda item")
    if proposal.decision_id != decision.decision_id:
        raise CoreInvariantError("proposal does not cite the decision")
    if decision.proposed_effect_id != proposal.proposal_id:
        raise CoreInvariantError("decision does not cite the proposal")
    if approval.proposal_id != proposal.proposal_id:
        raise CoreInvariantError("approval does not cite the proposal")
    if approval.proposal_revision != proposal.revision:
        raise CoreInvariantError("approval does not cite the proposal revision")
    if approval.proposal_payload_digest != proposal.payload_digest:
        raise CoreInvariantError("approval does not cite the immutable proposal payload")
    if approval.proposal_digest != proposal.proposal_digest:
        raise CoreInvariantError("approval does not cite the complete immutable proposal")
    if attempt.proposal_id != proposal.proposal_id:
        raise CoreInvariantError("effect attempt does not cite the proposal")
    if attempt.proposal_revision != proposal.revision:
        raise CoreInvariantError("effect attempt does not cite the proposal revision")
    if attempt.approval_decision_id != approval.approval_decision_id:
        raise CoreInvariantError("effect attempt does not cite the approval")
    if result.effect_attempt_id != attempt.effect_attempt_id:
        raise CoreInvariantError("action result does not cite the effect attempt")
