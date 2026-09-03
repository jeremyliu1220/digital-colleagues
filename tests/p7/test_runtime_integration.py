# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from digital_colleagues.adapters.channel.reference import ReferenceChannel
from digital_colleagues.adapters.http_json.channel import HttpJsonChannel
from digital_colleagues.adapters.http_json.errors import AdapterFailure
from digital_colleagues.adapters.http_json.model import HttpJsonIntelligence
from digital_colleagues.adapters.intelligence.deterministic import DeterministicIntelligence
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
) -> tuple[object, StableHashIdentifier, object]:
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
                store=store,  # type: ignore[arg-type]
                clock=FixedClock(T2),
                identifiers=identifiers,
                service_principal=service(),
            ).decide(
                context=RequestPrincipalContext(namespace(), user()),
                mandate_id="mandate-synthetic",
                expected_mandate_revision=1,
                request=approval_request(proposal),  # type: ignore[arg-type]
            )
            stub.enqueue(StubBehavior(document=channel_response("succeeded")))
            dispatched = _dispatch(store, identifiers, channel).dispatch_once(namespace())
            self.assertTrue(dispatched.dispatched)
            self.assertEqual(dispatched.outcome, ChannelOutcomeKind.SUCCEEDED)
            self.assertEqual(len(stub.state.requests), 2)
            store.close()  # type: ignore[attr-defined]

    def test_provider_failure_preserves_pending_causal_work_across_restart(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-causal-") as temporary,
            LoopbackStub() as stub,
        ):
            root = Path(temporary)
            database = root / "state.sqlite"
            credential = credential_file(root)
            stub.enqueue(StubBehavior(raw_body=b"malformed"))
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
            with self.assertRaises(AdapterFailure):
                wake.run(namespace())
            self.assertEqual(store.pending_agenda_count(namespace()), 1)
            store.close()
            restarted = new_store(database)
            self.assertEqual(restarted.pending_agenda_count(namespace()), 1)
            restarted.close()

    def test_ambiguous_dispatch_is_not_resent_and_restart_stays_unknown(self) -> None:
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
                store=store,  # type: ignore[arg-type]
                clock=FixedClock(T2),
                identifiers=identifiers,
                service_principal=service(),
            ).decide(
                context=RequestPrincipalContext(namespace(), user()),
                mandate_id="mandate-synthetic",
                expected_mandate_revision=1,
                request=approval_request(proposal),  # type: ignore[arg-type]
            )
            stub.enqueue(StubBehavior(disconnect_after_read=True))
            first = _dispatch(
                store,
                identifiers,
                HttpJsonChannel(settings(stub.endpoint, credential)),
            ).dispatch_once(namespace())
            self.assertEqual(first.outcome, ChannelOutcomeKind.AMBIGUOUS)
            request_count = len(stub.state.requests)
            store.close()  # type: ignore[attr-defined]
            restarted_store = new_store(database)
            restarted_channel = HttpJsonChannel(settings(stub.endpoint, credential))
            reconciliation = _dispatch(
                restarted_store,
                identifiers,
                restarted_channel,
            ).reconcile_once(namespace())
            self.assertEqual(reconciliation.outcome, ChannelOutcomeKind.AMBIGUOUS)
            self.assertIsNone(reconciliation.action_result_id)
            self.assertEqual(len(stub.state.requests), request_count)
            self.assertFalse(
                _dispatch(restarted_store, identifiers, restarted_channel)
                .dispatch_once(namespace())
                .dispatched
            )
            restarted_store.close()

    def test_default_reference_semantic_output_is_unchanged(self) -> None:
        request = intelligence_request()
        expected = DeterministicIntelligence().decide(request)
        actual = DeterministicIntelligence().decide(request)
        self.assertEqual(actual, expected)
        self.assertEqual(ReferenceChannel().outcomes, (ChannelOutcomeKind.SUCCEEDED,))


if __name__ == "__main__":
    unittest.main()
