# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from digital_colleagues.adapters.channel.reference import ReferenceChannel
from digital_colleagues.adapters.http_json.channel import HttpJsonChannel
from digital_colleagues.adapters.http_json.model import HttpJsonIntelligence
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
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.effects import EffectProposal
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
) -> DispatchService:
    return DispatchService(
        store=store,  # type: ignore[arg-type]
        channel=channel,  # type: ignore[arg-type]
        clock=FixedClock(T3),
        identifiers=identifiers,
        result_actor=service(),
        owner_id="p7-dispatch",
        mandate_id="mandate-synthetic",
    )


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
            ).reconcile_once(namespace())
            self.assertEqual(absent.outcome, ChannelOutcomeKind.KNOWN_NOT_EXECUTED)
            stub.enqueue(StubBehavior(document=channel_response("succeeded")))
            retried = _dispatch(
                restarted_store,
                identifiers,
                restarted_channel,
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

    def test_default_reference_semantic_output_is_unchanged(self) -> None:
        request = intelligence_request()
        expected = DeterministicIntelligence().decide(request)
        actual = DeterministicIntelligence().decide(request)
        self.assertEqual(actual, expected)
        self.assertEqual(ReferenceChannel().outcomes, (ChannelOutcomeKind.SUCCEEDED,))


if __name__ == "__main__":
    unittest.main()
