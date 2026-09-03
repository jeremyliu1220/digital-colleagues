# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from digital_colleagues.adapters.http_json.channel import HttpJsonChannel
from digital_colleagues.application.contracts import (
    ChannelEffect,
    ChannelOutcomeKind,
    ReconciliationKind,
)
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.effects import EffectAttemptState
from tests.p7.fixtures import (
    SYNTHETIC_CREDENTIAL,
    LoopbackStub,
    StubBehavior,
    channel_effect,
    channel_response,
    credential_file,
    settings,
)


class P7ChannelAdapterTests(unittest.TestCase):
    def test_success_carries_exact_binding_and_existing_idempotency_header(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-channel-") as temporary,
            LoopbackStub() as stub,
        ):
            credential = credential_file(Path(temporary))
            stub.enqueue(StubBehavior(document=channel_response("succeeded")))
            effect = channel_effect()
            outcome = HttpJsonChannel(settings(stub.endpoint, credential)).apply(effect)
            self.assertEqual(outcome.kind, ChannelOutcomeKind.SUCCEEDED)
            observed = stub.state.requests[0]
            self.assertEqual(observed["idempotency_key"], effect.effect_idempotency_key)
            document = observed["document"]
            assert isinstance(document, dict)
            transmitted = document["effect"]
            assert isinstance(transmitted, dict)
            self.assertEqual(transmitted["proposal_id"], effect.proposal.proposal_id)
            self.assertEqual(transmitted["proposal_digest"], effect.proposal.proposal_digest)
            self.assertEqual(transmitted["payload_digest"], effect.proposal.payload_digest)
            self.assertEqual(transmitted["mandate_revision"], effect.proposal.mandate_revision)
            body = observed["body"]
            assert isinstance(body, bytes)
            self.assertIn(b"sensitive-body-value", body)
            self.assertNotIn(SYNTHETIC_CREDENTIAL, body)
            self.assertNotIn("sensitive-body-value", str(outcome.safe_projection))

    def test_all_finite_channel_and_reconciliation_results_are_mapped(self) -> None:
        channel_kinds = tuple(ChannelOutcomeKind)
        reconciliation_kinds = tuple(ReconciliationKind)
        with (
            tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-results-") as temporary,
            LoopbackStub() as stub,
        ):
            credential = credential_file(Path(temporary))
            adapter = HttpJsonChannel(settings(stub.endpoint, credential))
            for channel_kind in channel_kinds:
                stub.enqueue(StubBehavior(document=channel_response(channel_kind.value)))
                self.assertEqual(adapter.apply(channel_effect()).kind, channel_kind)
            for reconciliation_kind in reconciliation_kinds:
                stub.enqueue(StubBehavior(document=channel_response(reconciliation_kind.value)))
                self.assertEqual(
                    adapter.reconcile(channel_effect().effect_idempotency_key).kind,
                    reconciliation_kind,
                )

    def test_timeout_and_disconnect_after_submission_are_ambiguous(self) -> None:
        behaviors = (
            StubBehavior(delay_seconds=0.2, document=channel_response("succeeded")),
            StubBehavior(disconnect_after_read=True),
        )
        for behavior in behaviors:
            with (
                self.subTest(disconnect=behavior.disconnect_after_read),
                tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-ambiguous-") as temporary,
                LoopbackStub() as stub,
            ):
                credential = credential_file(Path(temporary))
                stub.enqueue(behavior)
                outcome = HttpJsonChannel(
                    settings(
                        stub.endpoint,
                        credential,
                        connect_timeout=0.03,
                        read_timeout=0.03,
                        total_timeout=0.06,
                    )
                ).apply(channel_effect())
                self.assertEqual(outcome.kind, ChannelOutcomeKind.AMBIGUOUS)

    def test_status_malformed_oversize_and_redirect_failures_are_safe_and_finite(self) -> None:
        cases = (
            (StubBehavior(status=401, raw_body=b"private"), ChannelOutcomeKind.PERMANENT_FAILURE),
            (StubBehavior(status=403, raw_body=b"private"), ChannelOutcomeKind.PERMANENT_FAILURE),
            (StubBehavior(status=429, raw_body=b"private"), ChannelOutcomeKind.RETRYABLE_FAILURE),
            (StubBehavior(status=503, raw_body=b"private"), ChannelOutcomeKind.RETRYABLE_FAILURE),
            (StubBehavior(status=302), ChannelOutcomeKind.PERMANENT_FAILURE),
            (StubBehavior(raw_body=b"{"), ChannelOutcomeKind.AMBIGUOUS),
            (
                StubBehavior(raw_body=b"{" + (b"x" * 400) + b"}"),
                ChannelOutcomeKind.AMBIGUOUS,
            ),
        )
        for behavior, expected in cases:
            with (
                self.subTest(status=behavior.status, expected=expected),
                tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-failure-") as temporary,
                LoopbackStub() as stub,
            ):
                credential = credential_file(Path(temporary))
                stub.enqueue(behavior)
                outcome = HttpJsonChannel(
                    settings(stub.endpoint, credential, maximum_response_bytes=256)
                ).apply(channel_effect())
                self.assertEqual(outcome.kind, expected)
                self.assertNotIn("private", str(outcome.safe_projection))

    def test_authority_binding_and_idempotency_rebinding_fail_before_network(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-binding-") as temporary,
            LoopbackStub() as stub,
        ):
            credential = credential_file(Path(temporary))
            adapter = HttpJsonChannel(settings(stub.endpoint, credential))
            effect = channel_effect()
            wrong_key = replace(effect, effect_idempotency_key="other-key")
            self.assertEqual(
                adapter.apply(wrong_key).kind,
                ChannelOutcomeKind.PERMANENT_FAILURE,
            )
            planned = replace(effect.attempt, state=EffectAttemptState.PLANNED)
            self.assertEqual(
                adapter.apply(replace(effect, attempt=planned)).kind,
                ChannelOutcomeKind.PERMANENT_FAILURE,
            )
            self.assertEqual(stub.state.requests, [])
            stub.enqueue(StubBehavior(document=channel_response("succeeded")))
            self.assertEqual(adapter.apply(effect).kind, ChannelOutcomeKind.SUCCEEDED)
            rebound_proposal = replace(
                effect.proposal,
                payload=FrozenJsonObject.from_mapping({"body": "different synthetic body"}),
            )
            rebound = ChannelEffect(
                rebound_proposal,
                effect.attempt,
                effect.effect_idempotency_key,
            )
            self.assertEqual(
                adapter.apply(rebound).kind,
                ChannelOutcomeKind.PERMANENT_FAILURE,
            )
            self.assertEqual(len(stub.state.requests), 1)

    def test_reconciliation_failure_and_fresh_restart_never_invent_absence(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-reconcile-") as temporary,
            LoopbackStub() as stub,
        ):
            credential = credential_file(Path(temporary))
            adapter = HttpJsonChannel(settings(stub.endpoint, credential))
            stub.enqueue(StubBehavior(document=channel_response("ambiguous")))
            self.assertEqual(adapter.apply(channel_effect()).kind, ChannelOutcomeKind.AMBIGUOUS)
            stub.enqueue(StubBehavior(status=503, raw_body=b"private receipt"))
            unknown = adapter.reconcile(channel_effect().effect_idempotency_key)
            self.assertEqual(unknown.kind, ReconciliationKind.STILL_UNKNOWN)
            requests_before_restart = len(stub.state.requests)
            restarted = HttpJsonChannel(settings(stub.endpoint, credential))
            after_restart = restarted.reconcile(channel_effect().effect_idempotency_key)
            self.assertEqual(after_restart.kind, ReconciliationKind.STILL_UNKNOWN)
            self.assertEqual(len(stub.state.requests), requests_before_restart)
            self.assertNotIn("private receipt", str(unknown.safe_projection))

    def test_authority_fields_in_acknowledgement_are_refused(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-ack-") as temporary,
            LoopbackStub() as stub,
        ):
            credential = credential_file(Path(temporary))
            document = channel_response("succeeded")
            result = document["result"]
            assert isinstance(result, dict)
            result["approval"] = "provider-approved"
            stub.enqueue(StubBehavior(document=document))
            outcome = HttpJsonChannel(settings(stub.endpoint, credential)).apply(channel_effect())
            self.assertEqual(outcome.kind, ChannelOutcomeKind.AMBIGUOUS)
            self.assertNotEqual(outcome.kind, ChannelOutcomeKind.SUCCEEDED)

    def test_untrusted_result_classification_is_not_persisted_or_returned(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                prefix="digital-colleagues-p7-classification-"
            ) as temporary,
            LoopbackStub() as stub,
        ):
            credential = credential_file(Path(temporary))
            private_value = "live-message-identifier"
            stub.enqueue(
                StubBehavior(document=channel_response("succeeded", classification=private_value))
            )
            outcome = HttpJsonChannel(settings(stub.endpoint, credential)).apply(channel_effect())
            self.assertEqual(outcome.kind, ChannelOutcomeKind.AMBIGUOUS)
            self.assertNotIn(private_value, str(outcome.safe_projection))


if __name__ == "__main__":
    unittest.main()
