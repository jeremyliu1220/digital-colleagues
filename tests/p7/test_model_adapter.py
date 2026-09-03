# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import socket
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from digital_colleagues.adapters.http_json.errors import (
    AdapterFailure,
    AdapterFailureCategory,
)
from digital_colleagues.adapters.http_json.model import HttpJsonIntelligence
from digital_colleagues.application.contracts import SemanticOutcome
from digital_colleagues.core.principals import Principal
from tests.p7.fixtures import (
    SYNTHETIC_CREDENTIAL,
    LoopbackStub,
    StubBehavior,
    credential_file,
    intelligence_request,
    model_response,
    settings,
    unused_loopback_endpoint,
)


class P7ModelAdapterTests(unittest.TestCase):
    def test_success_reconstructs_all_authority_from_the_server_request(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-model-") as temporary,
            LoopbackStub() as stub,
        ):
            credential = credential_file(Path(temporary))
            stub.enqueue(StubBehavior(document=model_response()))
            request = intelligence_request()
            semantic = HttpJsonIntelligence(settings(stub.endpoint, credential)).decide(request)
            assert semantic.proposal is not None
            proposal = semantic.proposal
            self.assertEqual(semantic.outcome, SemanticOutcome.PROPOSAL)
            self.assertEqual(proposal.namespace, request.namespace)
            self.assertEqual(proposal.actor, request.model_principal)
            self.assertEqual(proposal.proposal_id, request.proposal_id)
            self.assertEqual(proposal.decision_id, request.decision_id)
            self.assertEqual(proposal.mandate_id, request.mandate.mandate_id)
            self.assertEqual(proposal.mandate_revision, request.mandate.revision)
            self.assertEqual(proposal.constraints.boundary_id, "boundary-reference-message")
            self.assertEqual(
                proposal.constraints.idempotency_key,
                request.effect_idempotency_key,
            )
            self.assertEqual(
                proposal.constraints.parameters, request.mandate.effect_boundaries[0].constraints
            )
            observed = stub.state.requests[0]
            self.assertEqual(observed["protocol"], "dc-http-json-v1")
            self.assertTrue(observed["authorization_present"])
            body = observed["body"]
            assert isinstance(body, bytes)
            self.assertNotIn(SYNTHETIC_CREDENTIAL, body)
            for forbidden in (
                b"csrf",
                b"cookie",
                b"session_credential",
                b"bootstrap",
                b"audit_export",
                b"approval_decision",
            ):
                self.assertNotIn(forbidden, body.lower())

    def test_finite_non_proposal_outcomes_create_no_effect(self) -> None:
        for result_kind in ("no_op", "wait", "escalation"):
            with (
                self.subTest(result_kind=result_kind),
                tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-outcome-") as temporary,
                LoopbackStub() as stub,
            ):
                credential = credential_file(Path(temporary))
                stub.enqueue(StubBehavior(document=model_response(result_kind=result_kind)))
                semantic = HttpJsonIntelligence(settings(stub.endpoint, credential)).decide(
                    intelligence_request()
                )
                self.assertEqual(semantic.outcome.value, result_kind)
                self.assertIsNone(semantic.proposal)
                self.assertIsNone(semantic.decision.proposed_effect_id)

    def test_unknown_fields_authority_injection_and_unknown_outcome_fail_closed(self) -> None:
        cases = (
            (
                model_response(extra={"role": "tenant_admin"}),
                AdapterFailureCategory.AUTHORITY_INJECTION,
            ),
            (
                {**model_response(), "extra": True},
                AdapterFailureCategory.INVALID_RESPONSE,
            ),
            (model_response(result_kind="execute_tool"), AdapterFailureCategory.INVALID_RESPONSE),
        )
        for document, category in cases:
            with (
                self.subTest(category=category),
                tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-injection-") as temporary,
                LoopbackStub() as stub,
            ):
                credential = credential_file(Path(temporary))
                stub.enqueue(StubBehavior(document=document))
                with self.assertRaises(AdapterFailure) as caught:
                    HttpJsonIntelligence(settings(stub.endpoint, credential)).decide(
                        intelligence_request()
                    )
                self.assertEqual(caught.exception.category, category)
                self.assertNotIn(stub.endpoint, str(caught.exception))

    def test_malformed_duplicate_non_json_content_and_oversize_fail_safely(self) -> None:
        cases = (
            StubBehavior(raw_body=b"{"),
            StubBehavior(raw_body=b'{"protocol_version":"dc-http-json-v1","protocol_version":"x"}'),
            StubBehavior(raw_body=b"not-json", content_type="text/plain"),
            StubBehavior(raw_body=b"{" + (b"x" * 400) + b"}"),
        )
        expected = (
            AdapterFailureCategory.INVALID_RESPONSE,
            AdapterFailureCategory.INVALID_RESPONSE,
            AdapterFailureCategory.INVALID_RESPONSE,
            AdapterFailureCategory.OVERSIZED_RESPONSE,
        )
        for behavior, category in zip(cases, expected, strict=True):
            with (
                self.subTest(category=category),
                tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-malformed-") as temporary,
                LoopbackStub() as stub,
            ):
                credential = credential_file(Path(temporary))
                stub.enqueue(behavior)
                adapter_settings = settings(
                    stub.endpoint,
                    credential,
                    maximum_response_bytes=256,
                )
                with self.assertRaises(AdapterFailure) as caught:
                    HttpJsonIntelligence(adapter_settings).decide(intelligence_request())
                self.assertEqual(caught.exception.category, category)
                self.assertNotIn("not-json", str(caught.exception))

    def test_http_statuses_have_typed_safe_failures(self) -> None:
        categories = {
            401: AdapterFailureCategory.UNAUTHORIZED,
            403: AdapterFailureCategory.UNAUTHORIZED,
            429: AdapterFailureCategory.RATE_LIMITED,
            500: AdapterFailureCategory.SERVER_FAILURE,
            503: AdapterFailureCategory.SERVER_FAILURE,
        }
        for status, category in categories.items():
            with (
                self.subTest(status=status),
                tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-status-") as temporary,
                LoopbackStub() as stub,
            ):
                credential = credential_file(Path(temporary))
                stub.enqueue(StubBehavior(status=status, raw_body=b"private response"))
                with self.assertRaises(AdapterFailure) as caught:
                    HttpJsonIntelligence(settings(stub.endpoint, credential)).decide(
                        intelligence_request()
                    )
                self.assertEqual(caught.exception.category, category)
                self.assertNotIn("private response", str(caught.exception))

    def test_timeout_disconnect_redirect_connect_dns_and_tls_are_typed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-failures-") as temporary:
            root = Path(temporary)
            credential = credential_file(root)
            with LoopbackStub() as stub:
                stub.enqueue(StubBehavior(delay_seconds=0.2, document=model_response()))
                with self.assertRaises(AdapterFailure) as caught:
                    HttpJsonIntelligence(
                        settings(
                            stub.endpoint,
                            credential,
                            connect_timeout=0.03,
                            read_timeout=0.03,
                            total_timeout=0.06,
                        )
                    ).decide(intelligence_request())
                self.assertEqual(caught.exception.category, AdapterFailureCategory.TIMEOUT)
                self.assertTrue(caught.exception.after_submit)
            with LoopbackStub() as stub:
                stub.enqueue(StubBehavior(disconnect_after_read=True))
                with self.assertRaises(AdapterFailure) as caught:
                    HttpJsonIntelligence(settings(stub.endpoint, credential)).decide(
                        intelligence_request()
                    )
                self.assertEqual(caught.exception.category, AdapterFailureCategory.DISCONNECTED)
            with LoopbackStub() as stub:
                stub.enqueue(StubBehavior(status=302))
                with self.assertRaises(AdapterFailure) as caught:
                    HttpJsonIntelligence(settings(stub.endpoint, credential)).decide(
                        intelligence_request()
                    )
                self.assertEqual(caught.exception.category, AdapterFailureCategory.REDIRECT_REFUSED)
            with self.assertRaises(AdapterFailure) as caught:
                HttpJsonIntelligence(settings(unused_loopback_endpoint(), credential)).decide(
                    intelligence_request()
                )
            self.assertEqual(caught.exception.category, AdapterFailureCategory.CONNECT_FAILURE)
            with patch("socket.getaddrinfo", side_effect=socket.gaierror()):
                external = settings("https://provider.invalid:443/v1", credential)
                with self.assertRaises(AdapterFailure) as caught:
                    HttpJsonIntelligence(external).decide(intelligence_request())
            self.assertEqual(caught.exception.category, AdapterFailureCategory.DNS_FAILURE)
            with LoopbackStub() as stub:
                tls_endpoint = stub.endpoint.replace("http://", "https://")
                with self.assertRaises(AdapterFailure) as caught:
                    HttpJsonIntelligence(settings(tls_endpoint, credential)).decide(
                        intelligence_request()
                    )
                self.assertEqual(caught.exception.category, AdapterFailureCategory.TLS_FAILURE)

    def test_wrong_principal_and_oversized_request_make_no_network_call(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-preflight-") as temporary,
            LoopbackStub() as stub,
        ):
            credential = credential_file(Path(temporary))
            adapter = HttpJsonIntelligence(
                settings(stub.endpoint, credential, maximum_request_bytes=256)
            )
            with self.assertRaises(AdapterFailure) as caught:
                adapter.decide(intelligence_request())
            self.assertEqual(caught.exception.category, AdapterFailureCategory.OVERSIZED_REQUEST)
            self.assertEqual(stub.state.requests, [])
            request = intelligence_request()
            wrong = Principal.service(
                tenant_id=request.namespace.tenant_id, principal_id="service-p7"
            )

            with self.assertRaises(AdapterFailure):
                HttpJsonIntelligence(settings(stub.endpoint, credential)).decide(
                    replace(request, model_principal=wrong)
                )
            self.assertEqual(stub.state.requests, [])


if __name__ == "__main__":
    unittest.main()
