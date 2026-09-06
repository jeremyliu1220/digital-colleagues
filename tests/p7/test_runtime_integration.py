# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import time
import unittest
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from digital_colleagues.adapters.channel.reference import ReferenceChannel
from digital_colleagues.adapters.http_json.channel import HttpJsonChannel
from digital_colleagues.adapters.http_json.model import HttpJsonIntelligence
from digital_colleagues.adapters.intelligence.deterministic import DeterministicIntelligence
from digital_colleagues.adapters.sqlite.store import SQLiteRuntimeStore
from digital_colleagues.adapters.system.deterministic import FixedClock, StableHashIdentifier
from digital_colleagues.application.contracts import (
    ChannelOutcomeKind,
    ReconciliationKind,
    ReconciliationOutcome,
    RequestPrincipalContext,
)
from digital_colleagues.application.errors import ConflictError, PermissionDeniedError
from digital_colleagues.application.p4_contracts import (
    InitialColleagueRequest,
    WorkAssignmentRequest,
)
from digital_colleagues.application.ports import ClockPort
from digital_colleagues.application.services import (
    ApprovalService,
    BootstrapService,
    DispatchService,
    EventService,
    WakeService,
)
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.effects import ApprovalChoice, EffectProposal
from digital_colleagues.core.namespace import Namespace
from tests.p3.fixtures import (
    T0,
    T1,
    T2,
    T3,
    admin,
    approval_request,
    finite_work,
    input_event_request,
    mandate,
    model,
    namespace,
    principals,
    profile,
    service,
    user,
)
from tests.p3.scenario import new_store
from tests.p7.fixtures import (
    LoopbackStub,
    StubBehavior,
    channel_response,
    credential_file,
    environment,
    intelligence_request,
    model_response,
    settings,
)


def _integration_response() -> dict[str, object]:
    response = model_response()
    result = response["result"]
    assert isinstance(result, dict)
    result.update(
        {
            "action": "record_message",
            "destination": {"kind": "reference_channel", "target": "synthetic-target"},
        }
    )
    return response


def _prepare(
    database: Path,
    intelligence: HttpJsonIntelligence,
) -> tuple[SQLiteRuntimeStore, StableHashIdentifier, EffectProposal]:
    store = new_store(database)
    identifiers = StableHashIdentifier("p7-integration")
    BootstrapService(store, FixedClock(T0)).initialize(
        context=RequestPrincipalContext(namespace(), admin()),
        principals=principals(),
        profile=profile(),
        mandate=mandate(),
        work=finite_work(),
        correlation_id="correlation-p7-bootstrap",
    )
    EventService(store, identifiers, FixedClock(T0)).submit(
        context=RequestPrincipalContext(namespace(), user()),
        request=input_event_request(),
        idempotency_key="p7-event-key",
    )
    wake = WakeService(
        store=store,
        intelligence=intelligence,
        clock=FixedClock(T1),
        identifiers=identifiers,
        service_principal=service(),
        model_principal=model(),
        mandate_id="mandate-synthetic",
        owner_id="p7-wake",
    )
    wake.materialize_next(namespace())
    wake.run(namespace())
    agenda_id = identifiers.derive("agenda", "event-synthetic")
    request_id = identifiers.derive("request", agenda_id, "1")
    proposal = store.get_proposal(namespace(), identifiers.derive("proposal", request_id))
    return store, identifiers, proposal


def _dispatch(
    store: object,
    identifiers: StableHashIdentifier,
    channel: object,
    *,
    clock: ClockPort | None = None,
    owner_id: str = "p7-dispatch",
    reconciliation_backoff: timedelta = timedelta(seconds=2),
) -> DispatchService:
    return DispatchService(
        store=store,  # type: ignore[arg-type]
        channel=channel,  # type: ignore[arg-type]
        clock=clock or FixedClock(T3),
        identifiers=identifiers,
        result_actor=service(),
        owner_id=owner_id,
        mandate_id="mandate-synthetic",
        reconciliation_backoff=reconciliation_backoff,
    )


def _record_count(store: SQLiteRuntimeStore, record_type: str) -> int:
    row = store._connection.execute(  # noqa: SLF001
        "SELECT COUNT(*) AS total FROM domain_records WHERE record_type = ?",
        (record_type,),
    ).fetchone()
    return int(row["total"])


@dataclass(slots=True)
class MutableClock:
    value: datetime

    def now(self) -> datetime:
        return self.value


@dataclass(slots=True)
class AdvancingReconciliationChannel:
    clock: MutableClock
    seconds: int
    kind: ReconciliationKind
    mutation: Callable[[], None] | None = None
    reconciliation_count: int = 0

    def reconcile(
        self,
        effect_idempotency_key: str,
        binding_digest: str | None = None,
    ) -> ReconciliationOutcome:
        del effect_idempotency_key, binding_digest
        self.reconciliation_count += 1
        if self.mutation is not None:
            self.mutation()
        self.clock.value += timedelta(seconds=self.seconds)
        return ReconciliationOutcome(
            self.kind,
            FrozenJsonObject.from_mapping({"classification": self.kind.value}),
            "sha256:" + ("4" * 64),
        )

    def apply(self, effect: object) -> object:
        del effect
        raise AssertionError("reconciliation test unexpectedly submitted an effect")


def _prepare_ambiguous(
    database: Path,
    stub: LoopbackStub,
    credential: Path,
) -> tuple[SQLiteRuntimeStore, StableHashIdentifier, EffectProposal]:
    stub.enqueue(StubBehavior(document=_integration_response()))
    store, identifiers, proposal = _prepare(
        database,
        HttpJsonIntelligence(settings(stub.endpoint, credential)),
    )
    ApprovalService(
        store=store,
        clock=FixedClock(T2),
        identifiers=identifiers,
        service_principal=service(),
    ).decide(
        context=RequestPrincipalContext(namespace(), user()),
        mandate_id="mandate-synthetic",
        expected_mandate_revision=1,
        request=approval_request(proposal),
    )
    stub.enqueue(StubBehavior(disconnect_after_read=True))
    dispatched = _dispatch(
        store,
        identifiers,
        HttpJsonChannel(settings(stub.endpoint, credential)),
    ).dispatch_once(namespace())
    if dispatched.outcome is not ChannelOutcomeKind.AMBIGUOUS:
        raise AssertionError("test fixture did not create a durable ambiguous effect")
    return store, identifiers, proposal


class P7RuntimeIntegrationTests(unittest.TestCase):
    def test_optional_model_exact_human_approval_and_channel_complete_existing_path(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-integration-") as temporary,
            LoopbackStub() as stub,
        ):
            root = Path(temporary)
            credential = credential_file(root)
            stub.enqueue(StubBehavior(document=_integration_response()))
            store, identifiers, proposal = _prepare(
                root / "state.sqlite",
                HttpJsonIntelligence(settings(stub.endpoint, credential)),
            )
            channel = HttpJsonChannel(settings(stub.endpoint, credential))
            before = _dispatch(store, identifiers, channel).dispatch_once(namespace())
            self.assertFalse(before.dispatched)
            self.assertEqual(len(stub.state.requests), 1)
            ApprovalService(
                store=store,
                clock=FixedClock(T2),
                identifiers=identifiers,
                service_principal=service(),
            ).decide(
                context=RequestPrincipalContext(namespace(), user()),
                mandate_id="mandate-synthetic",
                expected_mandate_revision=1,
                request=approval_request(proposal),
            )
            stub.enqueue(StubBehavior(document=channel_response("succeeded")))
            dispatched = _dispatch(store, identifiers, channel).dispatch_once(namespace())
            self.assertTrue(dispatched.dispatched)
            self.assertEqual(dispatched.outcome, ChannelOutcomeKind.SUCCEEDED)
            self.assertEqual(len(stub.state.requests), 2)
            store.close()

    def test_provider_failure_commits_bounded_safe_causal_stop_across_restart(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-causal-") as temporary,
            LoopbackStub() as stub,
        ):
            root = Path(temporary)
            database = root / "state.sqlite"
            credential = credential_file(root)
            private_marker = b"malformed-private-provider-body"
            stub.enqueue(StubBehavior(raw_body=private_marker))
            store = new_store(database)
            identifiers = StableHashIdentifier("p7-causal")
            BootstrapService(store, FixedClock(T0)).initialize(
                context=RequestPrincipalContext(namespace(), admin()),
                principals=principals(),
                profile=profile(),
                mandate=mandate(),
                work=finite_work(),
                correlation_id="correlation-p7-causal",
            )
            EventService(store, identifiers, FixedClock(T0)).submit(
                context=RequestPrincipalContext(namespace(), user()),
                request=input_event_request(),
                idempotency_key="p7-causal-event",
            )
            wake = WakeService(
                store=store,
                intelligence=HttpJsonIntelligence(settings(stub.endpoint, credential)),
                clock=FixedClock(T1),
                identifiers=identifiers,
                service_principal=service(),
                model_principal=model(),
                mandate_id="mandate-synthetic",
                owner_id="p7-causal-wake",
            )
            wake.materialize_next(namespace())
            result = wake.run(namespace())
            self.assertEqual(result.decision_count, 1)
            self.assertEqual(result.outcome, "terminal")
            self.assertEqual(store.pending_agenda_count(namespace()), 0)
            history = store.causal_history(namespace(), "correlation-p3")
            decisions = [item for item in history if item["record_type"] == "decision"]
            self.assertEqual(len(decisions), 1)
            projection = str(decisions[0]["safe_projection"])
            self.assertIn("category=invalid_response", projection)
            self.assertIn("sha256:", projection)
            self.assertNotIn(private_marker.decode(), projection)
            store.close()
            self.assertNotIn(private_marker, database.read_bytes())
            restarted = new_store(database)
            self.assertEqual(restarted.pending_agenda_count(namespace()), 0)
            restarted_history = restarted.causal_history(namespace(), "correlation-p3")
            self.assertEqual(restarted_history, history)
            restarted.close()

    def test_one_model_failure_does_not_stop_other_bounded_work(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-isolation-") as temporary,
            LoopbackStub() as stub,
        ):
            root = Path(temporary)
            credential = credential_file(root)
            stub.enqueue(
                StubBehavior(raw_body=b"private-first-work"),
                StubBehavior(document=model_response(result_kind="no_op")),
            )
            store = new_store(root / "state.sqlite")
            identifiers = StableHashIdentifier("p7-isolation")
            BootstrapService(store, FixedClock(T0)).initialize(
                context=RequestPrincipalContext(namespace(), admin()),
                principals=principals(),
                profile=profile(),
                mandate=mandate(),
                work=finite_work(),
                correlation_id="correlation-p7-isolation",
            )
            base = input_event_request()
            events = (
                replace(
                    base,
                    event_id="event-p7-failing-work",
                    correlation_id="correlation-p7-failing-work",
                    safe_projection=FrozenJsonObject.from_mapping(
                        {"priority": 900, "title": "failing work", "work_id": "work-failing"}
                    ),
                ),
                replace(
                    base,
                    event_id="event-p7-continuing-work",
                    correlation_id="correlation-p7-continuing-work",
                    safe_projection=FrozenJsonObject.from_mapping(
                        {
                            "priority": 800,
                            "title": "continuing work",
                            "work_id": "work-continuing",
                        }
                    ),
                ),
            )
            for index, event in enumerate(events, start=1):
                EventService(store, identifiers, FixedClock(T0)).submit(
                    context=RequestPrincipalContext(namespace(), user()),
                    request=event,
                    idempotency_key=f"p7-isolation-event-{index}",
                )
            adapter = HttpJsonIntelligence(settings(stub.endpoint, credential))
            wake = WakeService(
                store=store,
                intelligence=adapter,
                clock=FixedClock(T1),
                identifiers=identifiers,
                service_principal=service(),
                model_principal=model(),
                mandate_id="mandate-synthetic",
                owner_id="p7-isolation-wake",
            )
            self.assertIsNotNone(wake.materialize_next(namespace()))
            self.assertIsNotNone(wake.materialize_next(namespace()))
            result = wake.run(namespace())
            self.assertEqual(result.selected_count, 2)
            self.assertEqual(result.decision_count, 2)
            self.assertEqual(result.outcome, "terminal")
            self.assertEqual(adapter.call_count, 2)
            failing = store.causal_history(namespace(), "correlation-p7-failing-work")
            continuing = store.causal_history(namespace(), "correlation-p7-continuing-work")
            self.assertEqual(
                sum(item["record_type"] == "decision" for item in failing),
                1,
            )
            self.assertEqual(
                sum(item["record_type"] == "decision" for item in continuing),
                1,
            )
            store.close()

    def test_restart_reconciles_unknown_then_absent_before_bounded_retry(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-restart-") as temporary,
            LoopbackStub() as stub,
        ):
            root = Path(temporary)
            database = root / "state.sqlite"
            credential = credential_file(root)
            stub.enqueue(StubBehavior(document=_integration_response()))
            store, identifiers, proposal = _prepare(
                database,
                HttpJsonIntelligence(settings(stub.endpoint, credential)),
            )
            ApprovalService(
                store=store,
                clock=FixedClock(T2),
                identifiers=identifiers,
                service_principal=service(),
            ).decide(
                context=RequestPrincipalContext(namespace(), user()),
                mandate_id="mandate-synthetic",
                expected_mandate_revision=1,
                request=approval_request(proposal),
            )
            stub.enqueue(StubBehavior(disconnect_after_read=True))
            first = _dispatch(
                store,
                identifiers,
                HttpJsonChannel(settings(stub.endpoint, credential)),
            ).dispatch_once(namespace())
            self.assertEqual(first.outcome, ChannelOutcomeKind.AMBIGUOUS)
            request_count = len(stub.state.requests)
            store.close()
            restarted_store = new_store(database)
            restarted_channel = HttpJsonChannel(settings(stub.endpoint, credential))
            stub.enqueue(StubBehavior(document=channel_response("still_unknown")))
            reconciliation = _dispatch(
                restarted_store,
                identifiers,
                restarted_channel,
            ).reconcile_once(namespace())
            self.assertEqual(reconciliation.outcome, ChannelOutcomeKind.AMBIGUOUS)
            self.assertIsNone(reconciliation.action_result_id)
            self.assertEqual(len(stub.state.requests), request_count + 1)
            reconcile_document = stub.state.requests[-1]["document"]
            assert isinstance(reconcile_document, dict)
            self.assertEqual(
                reconcile_document["effect_idempotency_key"],
                proposal.constraints.idempotency_key,
            )
            self.assertEqual(
                reconcile_document["effect_binding_digest"],
                proposal.proposal_digest,
            )
            self.assertFalse(
                _dispatch(restarted_store, identifiers, restarted_channel)
                .dispatch_once(namespace())
                .dispatched
            )
            self.assertEqual(len(stub.state.requests), request_count + 1)
            stub.enqueue(StubBehavior(document=channel_response("confirmed_absent")))
            absent = _dispatch(
                restarted_store,
                identifiers,
                restarted_channel,
                clock=FixedClock(T3 + timedelta(seconds=2)),
            ).reconcile_once(namespace())
            self.assertEqual(absent.outcome, ChannelOutcomeKind.KNOWN_NOT_EXECUTED)
            stub.enqueue(StubBehavior(document=channel_response("succeeded")))
            retried = _dispatch(
                restarted_store,
                identifiers,
                restarted_channel,
                clock=FixedClock(T3 + timedelta(seconds=2)),
            ).dispatch_once(namespace())
            self.assertEqual(retried.outcome, ChannelOutcomeKind.SUCCEEDED)
            apply_requests = [
                item
                for item in stub.state.requests
                if isinstance(item["document"], dict)
                and item["document"].get("request_kind") == "channel_effect"
            ]
            self.assertEqual(len(apply_requests), 2)
            restarted_store.close()

    def test_headless_worker_recovers_ambiguous_only_namespace_across_restart(self) -> None:
        from digital_colleagues.local.runtime import build_local_runtime
        from digital_colleagues.local.worker import run_once

        with (
            tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-worker-restart-") as name,
            LoopbackStub() as stub,
        ):
            state_directory = Path(name) / "state"
            credential = credential_file(Path(name))
            adapter_environment = environment(stub.endpoint, credential)
            runtime = build_local_runtime(
                state_directory,
                adapter_environment=adapter_environment,
            )
            _, bootstrap = runtime.authentication.ensure_bootstrap()
            self.assertIsNotNone(bootstrap)
            assert bootstrap is not None
            runtime.authentication.claim_operator_retrieval(bootstrap)
            grant = runtime.authentication.exchange(bootstrap)
            profile, mandate_value, _ = runtime.colleagues.create(
                session=grant.session,
                request=InitialColleagueRequest(
                    display_name="Worker Restart Atlas",
                    role_description="Synthetic optional adapter colleague",
                    service_relationship="Serves the isolated worker test",
                    mission="Recover one durable ambiguous effect",
                    timezone="UTC",
                    working_context="Synthetic P7 worker state",
                    working_hours="09:00-17:00; initial data only",
                    working_style="Direct and inspectable",
                    responsibilities=("Own finite synthetic adapter work",),
                    capabilities=("Propose a reference message",),
                    constraints=("No external network",),
                    effect_kind="reference_message",
                    destination_kind="reference_channel",
                    action="record_message",
                    effect_constraints=FrozenJsonObject.from_mapping({"network": False}),
                    idempotency_key="p7-worker-restart-colleague",
                ),
            )
            colleague_id = profile.namespace.scope_id
            assert colleague_id is not None
            session = runtime.authentication.bind_colleague(
                grant.session,
                colleague_id,
                idempotency_key="p7-worker-restart-bind",
            )
            work, _ = runtime.colleagues.assign_work(
                session=session,
                request=WorkAssignmentRequest(
                    title="Worker-only P7 recovery",
                    description="Recover one durable ambiguous synthetic effect.",
                    responsibility_id=mandate_value.responsibilities[0].responsibility_id,
                    idempotency_key="p7-worker-restart-work",
                ),
            )
            stub.enqueue(StubBehavior(document=_integration_response()))
            runtime.controller.submit_trigger(
                session=session,
                work_id=work.work_id,
                trigger_class="event",
                deterministic_noop=False,
                idempotency_key="p7-worker-restart-trigger",
            )
            namespace_value = profile.namespace
            context = runtime.controller.service_context(namespace_value)
            produced = runtime.controller.process_once(context)
            self.assertEqual(produced["decisions"], 1)
            proposal = runtime.store.studio_snapshot(namespace_value).proposals[0]
            runtime.controller.decide_proposal(
                session=session,
                proposal=proposal,
                choice=ApprovalChoice.APPROVE,
                idempotency_key="p7-worker-restart-approval",
                expected_proposal_revision=proposal.revision,
                expected_payload_digest=proposal.payload_digest,
                expected_proposal_digest=proposal.proposal_digest,
                expected_mandate_id=proposal.mandate_id or "missing",
                expected_mandate_revision=proposal.mandate_revision or 1,
                expected_policy_id=proposal.policy_id,
                expected_policy_revision=proposal.policy_revision,
            )
            stub.enqueue(StubBehavior(status=503, raw_body=b"private-worker-receipt"))
            ambiguous = runtime.controller.process_once(context)
            self.assertTrue(ambiguous["dispatched"])
            self.assertIsNone(ambiguous["reconciliation_outcome"])
            self.assertEqual(
                runtime.store.pending_namespaces(runtime.clock.now()),
                (namespace_value,),
            )
            submitted = len(stub.state.requests)
            original_effect_key = stub.state.requests[-1]["idempotency_key"]
            runtime.close()

            stub.enqueue(StubBehavior(document=channel_response("still_unknown")))
            self.assertEqual(
                run_once(state_directory, adapter_environment=adapter_environment),
                1,
            )
            self.assertEqual(len(stub.state.requests), submitted + 1)
            reconciliation = stub.state.requests[-1]["document"]
            assert isinstance(reconciliation, dict)
            self.assertEqual(
                reconciliation["effect_idempotency_key"],
                original_effect_key,
            )
            self.assertEqual(
                reconciliation["effect_binding_digest"],
                proposal.proposal_digest,
            )
            self.assertEqual(
                run_once(state_directory, adapter_environment=adapter_environment),
                0,
            )
            self.assertEqual(len(stub.state.requests), submitted + 1)

            time.sleep(2.1)
            stub.enqueue(
                StubBehavior(document=channel_response("confirmed_absent")),
                StubBehavior(document=channel_response("succeeded")),
            )
            self.assertEqual(
                run_once(state_directory, adapter_environment=adapter_environment),
                1,
            )
            final_request_count = len(stub.state.requests)
            self.assertEqual(
                run_once(state_directory, adapter_environment=adapter_environment),
                0,
            )
            self.assertEqual(len(stub.state.requests), final_request_count)
            effect_requests = [
                item
                for item in stub.state.requests
                if isinstance(item["document"], dict)
                and item["document"].get("request_kind") == "channel_effect"
            ]
            self.assertEqual(len(effect_requests), 2)
            inspected = build_local_runtime(
                state_directory,
                adapter_environment=adapter_environment,
            )
            try:
                snapshot = inspected.store.studio_snapshot(namespace_value)
                self.assertEqual(len(snapshot.attempts), 2)
                self.assertEqual(len(snapshot.results), 3)
                self.assertEqual(inspected.store.pending_namespaces(inspected.clock.now()), ())
            finally:
                inspected.close()

    def test_still_unknown_reconciliation_uses_durable_backoff_and_stops_at_budget(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-reconcile-budget-") as name,
            LoopbackStub() as stub,
        ):
            root = Path(name)
            credential = credential_file(root)
            store, identifiers, _ = _prepare_ambiguous(root / "state.sqlite", stub, credential)
            channel = HttpJsonChannel(settings(stub.endpoint, credential))
            checkpoints = (
                (T3, T3 + timedelta(seconds=2)),
                (T3 + timedelta(seconds=2), T3 + timedelta(seconds=6)),
                (T3 + timedelta(seconds=6), T3 + timedelta(seconds=14)),
            )
            for index, (evaluated_at, next_check) in enumerate(checkpoints, start=1):
                stub.enqueue(StubBehavior(document=channel_response("still_unknown")))
                outcome = _dispatch(
                    store,
                    identifiers,
                    channel,
                    clock=FixedClock(evaluated_at),
                    owner_id=f"p7-reconciliation-{index}",
                ).reconcile_once(namespace())
                self.assertEqual(outcome.outcome, ChannelOutcomeKind.AMBIGUOUS)
                self.assertFalse(
                    _dispatch(
                        store,
                        identifiers,
                        channel,
                        clock=FixedClock(evaluated_at),
                    )
                    .reconcile_once(namespace())
                    .dispatched
                )
                row = store._connection.execute(  # noqa: SLF001
                    "SELECT next_attempt_at FROM outbox"
                ).fetchone()
                self.assertEqual(
                    row["next_attempt_at"],
                    next_check.isoformat(timespec="microseconds").replace("+00:00", "Z"),
                )
            self.assertFalse(
                _dispatch(
                    store,
                    identifiers,
                    channel,
                    clock=FixedClock(T3 + timedelta(days=365)),
                )
                .reconcile_once(namespace())
                .dispatched
            )
            self.assertEqual(channel.reconciliation_count, 3)
            self.assertEqual(_record_count(store, "effect_attempt"), 1)
            self.assertEqual(_record_count(store, "action_result"), 1)
            row = store._connection.execute(  # noqa: SLF001
                "SELECT state, last_outcome FROM outbox"
            ).fetchone()
            self.assertEqual(row["state"], "ambiguous")
            self.assertEqual(row["last_outcome"], "still_unknown_stopped:3")
            store.close()

    def test_stale_reconciliation_claim_does_not_stop_other_worker_namespace(self) -> None:
        from digital_colleagues.local.worker import run_once

        first = namespace()
        second = Namespace.colleague(first.tenant_id, "colleague-second")

        class Store:
            def pending_namespaces(self, evaluated_at: datetime) -> tuple[Namespace, ...]:
                del evaluated_at
                return first, second

        class Controller:
            processed: list[Namespace] = []

            def service_context(self, selected: Namespace) -> Namespace:
                return selected

            def process_once(self, selected: Namespace) -> None:
                if selected == first:
                    raise ConflictError("synthetic expired reconciliation lease")
                self.processed.append(selected)

        controller = Controller()
        runtime = SimpleNamespace(
            store=Store(),
            clock=FixedClock(T3),
            controller=controller,
            close=lambda: None,
        )
        with patch("digital_colleagues.local.worker.build_local_runtime", return_value=runtime):
            self.assertEqual(run_once(Path("unused-synthetic-state")), 1)
        self.assertEqual(controller.processed, [second])

    def test_submitted_503_is_never_blindly_resent(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-503-") as temporary,
            LoopbackStub() as stub,
        ):
            root = Path(temporary)
            credential = credential_file(root)
            stub.enqueue(StubBehavior(document=_integration_response()))
            store, identifiers, proposal = _prepare(
                root / "state.sqlite",
                HttpJsonIntelligence(settings(stub.endpoint, credential)),
            )
            ApprovalService(
                store=store,
                clock=FixedClock(T2),
                identifiers=identifiers,
                service_principal=service(),
            ).decide(
                context=RequestPrincipalContext(namespace(), user()),
                mandate_id="mandate-synthetic",
                expected_mandate_revision=1,
                request=approval_request(proposal),
            )
            channel = HttpJsonChannel(settings(stub.endpoint, credential))
            stub.enqueue(StubBehavior(status=503, raw_body=b"private receipt"))
            first = _dispatch(store, identifiers, channel).dispatch_once(namespace())
            self.assertEqual(first.outcome, ChannelOutcomeKind.AMBIGUOUS)
            submitted = len(stub.state.requests)
            self.assertFalse(
                _dispatch(store, identifiers, channel).dispatch_once(namespace()).dispatched
            )
            self.assertEqual(len(stub.state.requests), submitted)
            stub.enqueue(StubBehavior(document=channel_response("still_unknown")))
            unknown = _dispatch(store, identifiers, channel).reconcile_once(namespace())
            self.assertEqual(unknown.outcome, ChannelOutcomeKind.AMBIGUOUS)
            self.assertFalse(
                _dispatch(store, identifiers, channel).dispatch_once(namespace()).dispatched
            )
            apply_requests = [
                item
                for item in stub.state.requests
                if isinstance(item["document"], dict)
                and item["document"].get("request_kind") == "channel_effect"
            ]
            self.assertEqual(len(apply_requests), 1)
            store.close()

    def test_all_uncertain_post_submit_failures_remain_ambiguous_without_retry(self) -> None:
        cases: tuple[tuple[str, StubBehavior, dict[str, Any], bytes | None], ...] = (
            ("302", StubBehavior(status=302), {}, None),
            ("307", StubBehavior(status=307), {}, None),
            ("308", StubBehavior(status=308), {}, None),
            ("408", StubBehavior(status=408, raw_body=b"private-408"), {}, b"private-408"),
            ("429", StubBehavior(status=429, raw_body=b"private-429"), {}, b"private-429"),
            ("500", StubBehavior(status=500, raw_body=b"private-500"), {}, b"private-500"),
            ("503", StubBehavior(status=503, raw_body=b"private-503"), {}, b"private-503"),
            (
                "malformed",
                StubBehavior(raw_body=b"private-malformed-response"),
                {},
                b"private-malformed-response",
            ),
            (
                "content-type",
                StubBehavior(raw_body=b"private-wrong-content", content_type="text/plain"),
                {},
                b"private-wrong-content",
            ),
            (
                "slow-drip",
                StubBehavior(
                    document=channel_response("succeeded"),
                    drip_chunk_size=20,
                    drip_interval_seconds=0.03,
                ),
                {"connect_timeout": 0.05, "read_timeout": 0.06, "total_timeout": 0.10},
                None,
            ),
            ("disconnect", StubBehavior(disconnect_after_read=True), {}, None),
        )
        for label, behavior, transport, private_body in cases:
            with (
                self.subTest(case=label),
                tempfile.TemporaryDirectory(
                    prefix=f"digital-colleagues-p7-post-submit-{label}-"
                ) as temporary,
                LoopbackStub() as stub,
            ):
                root = Path(temporary)
                database = root / "state.sqlite"
                credential = credential_file(root)
                stub.enqueue(StubBehavior(document=_integration_response()))
                store, identifiers, proposal = _prepare(
                    database,
                    HttpJsonIntelligence(settings(stub.endpoint, credential)),
                )
                ApprovalService(
                    store=store,
                    clock=FixedClock(T2),
                    identifiers=identifiers,
                    service_principal=service(),
                ).decide(
                    context=RequestPrincipalContext(namespace(), user()),
                    mandate_id="mandate-synthetic",
                    expected_mandate_revision=1,
                    request=approval_request(proposal),
                )
                channel = HttpJsonChannel(settings(stub.endpoint, credential, **transport))
                stub.enqueue(behavior)
                result = _dispatch(store, identifiers, channel).dispatch_once(namespace())
                self.assertEqual(result.outcome, ChannelOutcomeKind.AMBIGUOUS)
                submitted = len(stub.state.requests)
                self.assertFalse(
                    _dispatch(store, identifiers, channel).dispatch_once(namespace()).dispatched
                )
                self.assertEqual(len(stub.state.requests), submitted)
                self.assertEqual(channel.call_count, 1)
                effect_requests = [
                    item
                    for item in stub.state.requests
                    if isinstance(item["document"], dict)
                    and item["document"].get("request_kind") == "channel_effect"
                ]
                self.assertEqual(len(effect_requests), 1)
                row = store._connection.execute(  # noqa: SLF001
                    "SELECT state, attempt_number FROM outbox"
                ).fetchone()
                self.assertEqual((row["state"], row["attempt_number"]), ("ambiguous", 1))
                self.assertEqual(_record_count(store, "effect_attempt"), 1)
                store.close()
                persisted = database.read_bytes()
                self.assertNotIn(credential.read_bytes(), persisted)
                self.assertNotIn(str(credential).encode(), persisted)
                self.assertNotIn(stub.endpoint.encode(), persisted)
                if private_body is not None:
                    self.assertNotIn(private_body, persisted)

    def test_reconciliation_lease_29_seconds_succeeds_and_31_seconds_fails_closed(self) -> None:
        for elapsed, accepted in ((29, True), (31, False)):
            with (
                self.subTest(elapsed=elapsed),
                tempfile.TemporaryDirectory(
                    prefix=f"digital-colleagues-p7-lease-{elapsed}-"
                ) as temporary,
                LoopbackStub() as stub,
            ):
                root = Path(temporary)
                credential = credential_file(root)
                store, identifiers, _ = _prepare_ambiguous(root / "state.sqlite", stub, credential)
                clock = MutableClock(T3)
                channel = AdvancingReconciliationChannel(
                    clock,
                    elapsed,
                    (
                        ReconciliationKind.CONFIRMED_APPLIED
                        if accepted
                        else ReconciliationKind.CONFIRMED_ABSENT
                    ),
                )
                dispatcher = _dispatch(
                    store,
                    identifiers,
                    channel,
                    clock=clock,
                    owner_id=f"p7-lease-{elapsed}",
                )
                if accepted:
                    result = dispatcher.reconcile_once(namespace())
                    self.assertEqual(result.outcome, ChannelOutcomeKind.SUCCEEDED)
                    self.assertIsNotNone(result.action_result_id)
                    self.assertEqual(_record_count(store, "action_result"), 2)
                else:
                    with self.assertRaisesRegex(ConflictError, "lease expired"):
                        dispatcher.reconcile_once(namespace())
                    self.assertEqual(_record_count(store, "action_result"), 1)
                    self.assertEqual(_record_count(store, "effect_attempt"), 1)
                    row = store._connection.execute(  # noqa: SLF001
                        "SELECT state, attempt_number FROM outbox"
                    ).fetchone()
                    self.assertEqual(
                        (row["state"], row["attempt_number"]), ("ambiguous_claimed", 1)
                    )
                self.assertEqual(channel.reconciliation_count, 1)
                store.close()

    def test_expired_reconciliation_takeover_fences_old_owner_and_recovers(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-takeover-") as temporary,
            LoopbackStub() as stub,
        ):
            root = Path(temporary)
            store, _, _ = _prepare_ambiguous(root / "state.sqlite", stub, credential_file(root))
            old = store.claim_ambiguous(
                namespace(),
                owner="p7-old-owner",
                now=T3,
                lease_until=T3 + timedelta(seconds=30),
            )
            self.assertIsNotNone(old)
            assert old is not None
            takeover_time = T3 + timedelta(seconds=31)
            new = store.claim_ambiguous(
                namespace(),
                owner="p7-new-owner",
                now=takeover_time,
                lease_until=takeover_time + timedelta(seconds=30),
            )
            self.assertIsNotNone(new)
            assert new is not None
            self.assertGreater(new.fencing_token, old.fencing_token)
            outcome = ReconciliationOutcome(
                ReconciliationKind.CONFIRMED_APPLIED,
                FrozenJsonObject.from_mapping({"classification": "applied"}),
                "sha256:" + ("5" * 64),
            )
            with self.assertRaises(ConflictError):
                store.reconcile_ambiguous(
                    old,
                    outcome=outcome,
                    action_result_id="result:stale-owner",
                    result_actor=service(),
                    occurred_at=takeover_time,
                    next_attempt_id=None,
                )
            recovered = store.reconcile_ambiguous(
                new,
                outcome=outcome,
                action_result_id="result:new-owner",
                result_actor=service(),
                occurred_at=takeover_time,
                next_attempt_id=None,
            )
            self.assertIsNotNone(recovered)
            self.assertEqual(_record_count(store, "action_result"), 2)
            store.close()

    def test_authority_change_during_reconciliation_cannot_create_retry(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-rebind-io-") as temporary,
            LoopbackStub() as stub,
        ):
            root = Path(temporary)
            store, identifiers, _ = _prepare_ambiguous(
                root / "state.sqlite", stub, credential_file(root)
            )

            def change_authority() -> None:
                current = store.get_mandate(namespace(), "mandate-synthetic")
                with store._transaction() as connection:  # noqa: SLF001
                    store._update_record(  # noqa: SLF001
                        connection,
                        replace(current, revision=current.revision + 1),
                        expected_revision=current.revision,
                    )

            clock = MutableClock(T3)
            channel = AdvancingReconciliationChannel(
                clock,
                0,
                ReconciliationKind.CONFIRMED_ABSENT,
                mutation=change_authority,
            )
            with self.assertRaises(PermissionDeniedError):
                _dispatch(store, identifiers, channel, clock=clock).reconcile_once(namespace())
            self.assertEqual(_record_count(store, "action_result"), 1)
            self.assertEqual(_record_count(store, "effect_attempt"), 1)
            row = store._connection.execute(  # noqa: SLF001
                "SELECT state, attempt_number FROM outbox"
            ).fetchone()
            self.assertEqual((row["state"], row["attempt_number"]), ("ambiguous_claimed", 1))
            store.close()

    def test_default_reference_semantic_output_is_unchanged(self) -> None:
        request = intelligence_request()
        expected = DeterministicIntelligence().decide(request)
        actual = DeterministicIntelligence().decide(request)
        self.assertEqual(actual, expected)
        self.assertEqual(ReferenceChannel().outcomes, (ChannelOutcomeKind.SUCCEEDED,))


if __name__ == "__main__":
    unittest.main()
