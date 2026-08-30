# SPDX-License-Identifier: Apache-2.0

"""Network-free deterministic intelligence with inspectable typed output."""

from __future__ import annotations

from dataclasses import dataclass

from digital_colleagues.application.contracts import (
    IntelligenceRequest,
    SemanticDecision,
    SemanticOutcome,
)
from digital_colleagues.core.authority import EffectKind
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.effects import (
    EffectConstraints,
    EffectDestination,
    EffectProposal,
    EffectProposalState,
)
from digital_colleagues.core.principals import PrincipalKind
from digital_colleagues.core.runtime import Decision, DecisionKind


@dataclass(slots=True)
class DeterministicIntelligence:
    call_count: int = 0

    def decide(self, request: IntelligenceRequest) -> SemanticDecision:
        if request.model_principal.kind is not PrincipalKind.MODEL:
            raise ValueError("deterministic intelligence requires a model principal")
        self.call_count += 1
        if request.agenda_item.title.startswith("noop:"):
            decision = Decision(
                namespace=request.namespace,
                decision_id=request.decision_id,
                wake_cycle_id=request.wake_cycle.wake_cycle_id,
                agenda_item_id=request.agenda_item.agenda_item_id,
                kind=DecisionKind.NO_ACTION,
                rationale="Deterministic no-op selected by the synthetic fixture.",
                proposed_effect_id=None,
                actor=request.model_principal,
                correlation_id=request.agenda_item.correlation_id,
                causation_id=request.agenda_item.agenda_item_id,
                occurred_at=request.occurred_at,
                revision=1,
            )
            return SemanticDecision(SemanticOutcome.NO_OP, decision, None, request.request_id)
        boundary = request.mandate.effect_boundaries[0]
        if boundary.effect_kind is not EffectKind.REFERENCE_MESSAGE:
            raise ValueError("deterministic reference path requires a reference-message boundary")
        decision = Decision(
            namespace=request.namespace,
            decision_id=request.decision_id,
            wake_cycle_id=request.wake_cycle.wake_cycle_id,
            agenda_item_id=request.agenda_item.agenda_item_id,
            kind=DecisionKind.PROPOSE_EFFECT,
            rationale="Synthetic finite work deterministically requires one reference effect.",
            proposed_effect_id=request.proposal_id,
            actor=request.model_principal,
            correlation_id=request.agenda_item.correlation_id,
            causation_id=request.agenda_item.agenda_item_id,
            occurred_at=request.occurred_at,
            revision=1,
        )
        proposal = EffectProposal(
            namespace=request.namespace,
            proposal_id=request.proposal_id,
            decision_id=request.decision_id,
            effect_kind=EffectKind.REFERENCE_MESSAGE,
            destination=EffectDestination(kind="reference_channel", target="synthetic-target"),
            action="record_message",
            payload=FrozenJsonObject.from_mapping({"body": "Synthetic deterministic work update."}),
            safe_projection=FrozenJsonObject.from_mapping(
                {"content_class": "synthetic_update", "work_id": request.agenda_item.work_id}
            ),
            constraints=EffectConstraints(
                boundary_id=boundary.boundary_id,
                idempotency_key=request.effect_idempotency_key,
                valid_until=request.proposal_valid_until,
                maximum_attempts=3,
                parameters=boundary.constraints,
            ),
            state=EffectProposalState.PENDING_APPROVAL,
            actor=request.model_principal,
            correlation_id=request.agenda_item.correlation_id,
            causation_id=request.decision_id,
            occurred_at=request.occurred_at,
            revision=1,
            mandate_id=request.mandate.mandate_id,
            mandate_revision=request.mandate.revision,
        )
        return SemanticDecision(SemanticOutcome.PROPOSAL, decision, proposal, request.request_id)
