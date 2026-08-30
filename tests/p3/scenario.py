# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from digital_colleagues.adapters.intelligence.deterministic import DeterministicIntelligence
from digital_colleagues.adapters.sqlite.store import SQLiteRuntimeStore
from digital_colleagues.adapters.system.deterministic import FixedClock, StableHashIdentifier
from digital_colleagues.application.contracts import RequestPrincipalContext
from digital_colleagues.application.services import (
    ApprovalService,
    BootstrapService,
    EventService,
    WakeService,
)
from digital_colleagues.core.effects import ApprovalChoice, EffectProposal, HumanApprovalDecision
from tests.p3.fixtures import (
    T0,
    T1,
    T2,
    T4,
    admin,
    finite_work,
    input_event,
    mandate,
    model,
    namespace,
    principals,
    profile,
    service,
    user,
)

ROOT = Path(__file__).resolve().parents[2]


@dataclass(slots=True)
class PreparedScenario:
    store: SQLiteRuntimeStore
    identifiers: StableHashIdentifier
    proposal: EffectProposal
    decision: HumanApprovalDecision | None = None


def new_store(database: Path) -> SQLiteRuntimeStore:
    return SQLiteRuntimeStore(
        database,
        migrations_path=ROOT / "migrations",
        clock=FixedClock(T0),
    )


def prepare_proposal(database: Path, *, identifier_namespace: str = "scenario") -> PreparedScenario:
    store = new_store(database)
    identifiers = StableHashIdentifier(identifier_namespace)
    BootstrapService(store, FixedClock(T0)).initialize(
        context=RequestPrincipalContext(namespace(), admin()),
        principals=principals(),
        profile=profile(),
        mandate=mandate(),
        work=finite_work(),
        correlation_id="correlation-bootstrap",
    )
    EventService(store, identifiers).submit(
        context=RequestPrincipalContext(namespace(), user()),
        event=input_event(),
        idempotency_key="event-key-synthetic",
    )
    wake = WakeService(
        store=store,
        intelligence=DeterministicIntelligence(),
        clock=FixedClock(T1),
        identifiers=identifiers,
        service_principal=service(),
        model_principal=model(),
        mandate_id="mandate-synthetic",
        owner_id="worker-wake-scenario",
    )
    wake.materialize_next(namespace())
    wake.run(namespace())
    agenda_id = identifiers.derive("agenda", "event-synthetic")
    request_id = identifiers.derive("request", agenda_id, "1")
    proposal_id = identifiers.derive("proposal", request_id)
    return PreparedScenario(store, identifiers, store.get_proposal(namespace(), proposal_id))


def approve(scenario: PreparedScenario) -> HumanApprovalDecision:
    proposal = scenario.proposal
    decision = HumanApprovalDecision(
        namespace=namespace(),
        approval_decision_id="approval-synthetic",
        proposal_id=proposal.proposal_id,
        proposal_revision=proposal.revision,
        proposal_payload_digest=proposal.payload_digest,
        proposal_digest=proposal.proposal_digest,
        choice=ApprovalChoice.APPROVE,
        author=user(),
        idempotency_key="approval-key-synthetic",
        correlation_id=proposal.correlation_id,
        causation_id=proposal.proposal_id,
        occurred_at=T2,
        valid_until=T4,
        revision=1,
    )
    ApprovalService(
        store=scenario.store,
        clock=FixedClock(T2),
        identifiers=scenario.identifiers,
        service_principal=service(),
    ).decide(
        context=RequestPrincipalContext(namespace(), user()),
        mandate_id="mandate-synthetic",
        expected_mandate_revision=1,
        decision=decision,
    )
    scenario.decision = decision
    return decision
