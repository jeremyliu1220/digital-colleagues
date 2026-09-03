# SPDX-License-Identifier: Apache-2.0

"""Strict provider-neutral HTTP JSON channel and reconciliation adapter."""

from __future__ import annotations

import hashlib

from digital_colleagues.adapters.http_json.configuration import HttpJsonSettings
from digital_colleagues.adapters.http_json.errors import (
    PROTOCOL_VERSION,
    AdapterFailure,
    AdapterFailureCategory,
    safe_digest,
)
from digital_colleagues.adapters.http_json.model import _json_value
from digital_colleagues.adapters.http_json.transport import (
    HttpJsonTransport,
    canonical_json,
    parse_json_object,
)
from digital_colleagues.application.contracts import (
    ChannelEffect,
    ChannelOutcome,
    ChannelOutcomeKind,
    ReconciliationKind,
    ReconciliationOutcome,
)
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.effects import EffectAttemptState

_RESPONSE_FIELDS = {"protocol_version", "result_kind", "result"}
_RESULT_FIELDS = {"classification"}
_CLASSIFICATION_BY_RESULT = {
    ChannelOutcomeKind.SUCCEEDED.value: "applied",
    ChannelOutcomeKind.KNOWN_NOT_EXECUTED.value: "not_executed",
    ChannelOutcomeKind.RETRYABLE_FAILURE.value: "retryable",
    ChannelOutcomeKind.PERMANENT_FAILURE.value: "permanent",
    ChannelOutcomeKind.AMBIGUOUS.value: "unknown",
    ReconciliationKind.CONFIRMED_APPLIED.value: "applied",
    ReconciliationKind.CONFIRMED_ABSENT.value: "absent",
    ReconciliationKind.STILL_UNKNOWN.value: "unknown",
}


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def channel_request_document(effect: ChannelEffect) -> dict[str, object]:
    proposal = effect.proposal
    attempt = effect.attempt
    return {
        "effect": {
            "action": proposal.action,
            "attempt_id": attempt.effect_attempt_id,
            "attempt_number": attempt.attempt_number,
            "constraints": {
                "boundary_id": proposal.constraints.boundary_id,
                "maximum_attempts": proposal.constraints.maximum_attempts,
                "parameters": _json_value(proposal.constraints.parameters),
                "valid_until": proposal.constraints.valid_until.isoformat().replace("+00:00", "Z"),
            },
            "destination": {
                "kind": proposal.destination.kind,
                "target": proposal.destination.target,
            },
            "effect_kind": proposal.effect_kind.value,
            "idempotency_key": effect.effect_idempotency_key,
            "mandate_id": proposal.mandate_id,
            "mandate_revision": proposal.mandate_revision,
            "payload": _json_value(proposal.payload),
            "payload_digest": proposal.payload_digest,
            "policy_id": proposal.policy_id,
            "policy_revision": proposal.policy_revision,
            "proposal_digest": proposal.proposal_digest,
            "proposal_id": proposal.proposal_id,
            "proposal_revision": proposal.revision,
            "safe_projection": _json_value(proposal.safe_projection),
        },
        "namespace": {
            "scope": proposal.namespace.scope.value,
            "scope_id": proposal.namespace.scope_id,
            "tenant_id": proposal.namespace.tenant_id,
        },
        "protocol_version": PROTOCOL_VERSION,
        "request_kind": "channel_effect",
        "schema_version": effect.schema_version,
    }


def reconciliation_request_document(effect_key: str, binding_digest: str) -> dict[str, object]:
    return {
        "effect_binding_digest": binding_digest,
        "effect_idempotency_key": effect_key,
        "protocol_version": PROTOCOL_VERSION,
        "request_kind": "channel_reconciliation",
        "schema_version": 1,
    }


def _projection(kind: str, classification: str) -> FrozenJsonObject:
    return FrozenJsonObject.from_mapping(
        {
            "adapter": "http_json_v1",
            "classification": classification,
            "protocol_version": PROTOCOL_VERSION,
            "result": kind,
        }
    )


def _failure_outcome(failure: AdapterFailure) -> ChannelOutcome:
    if failure.after_submit and failure.category in {
        AdapterFailureCategory.AUTHORITY_INJECTION,
        AdapterFailureCategory.CONNECT_FAILURE,
        AdapterFailureCategory.DISCONNECTED,
        AdapterFailureCategory.INVALID_RESPONSE,
        AdapterFailureCategory.OVERSIZED_RESPONSE,
        AdapterFailureCategory.TIMEOUT,
    }:
        kind = ChannelOutcomeKind.AMBIGUOUS
    elif failure.category in {
        AdapterFailureCategory.CONNECT_FAILURE,
        AdapterFailureCategory.DNS_FAILURE,
        AdapterFailureCategory.RATE_LIMITED,
        AdapterFailureCategory.SERVER_FAILURE,
        AdapterFailureCategory.TLS_FAILURE,
    }:
        kind = ChannelOutcomeKind.RETRYABLE_FAILURE
    else:
        kind = ChannelOutcomeKind.PERMANENT_FAILURE
    return ChannelOutcome(
        kind,
        _projection(kind.value, failure.category.value),
        failure.diagnostic_digest,
    )


def _http_failure(status: int) -> AdapterFailure:
    if status in {401, 403}:
        category = AdapterFailureCategory.UNAUTHORIZED
        result = "authorization_refused"
    elif status == 429:
        category = AdapterFailureCategory.RATE_LIMITED
        result = "rate_limited"
    elif 500 <= status <= 599:
        category = AdapterFailureCategory.SERVER_FAILURE
        result = "server_failure"
    else:
        category = AdapterFailureCategory.HTTP_FAILURE
        result = "http_refused"
    return AdapterFailure(category, result_class=result, after_submit=True)


def _strict_response(
    response_body: bytes,
    content_type: str,
    *,
    allowed: type[ChannelOutcomeKind] | type[ReconciliationKind],
) -> tuple[ChannelOutcomeKind | ReconciliationKind, str]:
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise AdapterFailure(
            AdapterFailureCategory.INVALID_RESPONSE,
            result_class="invalid_content_type",
            after_submit=True,
        )
    try:
        response = parse_json_object(response_body)
    except AdapterFailure as exc:
        raise AdapterFailure(
            exc.category,
            result_class=exc.result_class,
            after_submit=True,
        ) from None
    if set(response) != _RESPONSE_FIELDS or response["protocol_version"] != PROTOCOL_VERSION:
        raise AdapterFailure(
            AdapterFailureCategory.INVALID_RESPONSE,
            result_class="response_fields",
            after_submit=True,
        )
    result = response["result"]
    if not isinstance(response["result_kind"], str) or not isinstance(result, dict):
        raise AdapterFailure(
            AdapterFailureCategory.INVALID_RESPONSE,
            result_class="result_shape",
            after_submit=True,
        )
    if set(result) != _RESULT_FIELDS:
        raise AdapterFailure(
            AdapterFailureCategory.AUTHORITY_INJECTION,
            result_class="result_fields",
            after_submit=True,
        )
    classification = result["classification"]
    if not isinstance(classification, str):
        raise AdapterFailure(
            AdapterFailureCategory.INVALID_RESPONSE,
            result_class="classification",
            after_submit=True,
        )
    try:
        kind = allowed(response["result_kind"])
    except ValueError:
        raise AdapterFailure(
            AdapterFailureCategory.INVALID_RESPONSE,
            result_class="unknown_result",
            after_submit=True,
        ) from None
    expected_classification = _CLASSIFICATION_BY_RESULT[kind.value]
    if classification != expected_classification:
        raise AdapterFailure(
            AdapterFailureCategory.INVALID_RESPONSE,
            result_class="classification",
            after_submit=True,
        )
    return kind, expected_classification


class HttpJsonChannel:
    def __init__(self, settings: HttpJsonSettings) -> None:
        self._transport = HttpJsonTransport(settings)
        self._bindings: dict[str, str] = {}
        self.call_count = 0
        self.reconciliation_count = 0

    def apply(self, effect: ChannelEffect) -> ChannelOutcome:
        self.call_count += 1
        if (
            effect.effect_idempotency_key != effect.proposal.constraints.idempotency_key
            or effect.attempt.proposal_id != effect.proposal.proposal_id
            or effect.attempt.proposal_revision != effect.proposal.revision
            or effect.attempt.state is not EffectAttemptState.STARTED
        ):
            failure = AdapterFailure(
                AdapterFailureCategory.AUTHORITY_INJECTION,
                result_class="effect_binding_refused",
            )
            return _failure_outcome(failure)
        document = channel_request_document(effect)
        binding = effect.proposal.proposal_digest
        existing = self._bindings.get(effect.effect_idempotency_key)
        if existing is not None and existing != binding:
            failure = AdapterFailure(
                AdapterFailureCategory.AUTHORITY_INJECTION,
                result_class="idempotency_rebinding",
            )
            return _failure_outcome(failure)
        self._bindings[effect.effect_idempotency_key] = binding
        try:
            response = self._transport.post(
                document,
                idempotency_key=effect.effect_idempotency_key,
            )
            if response.status != 200:
                raise _http_failure(response.status)
            raw_kind, classification = _strict_response(
                response.body,
                response.content_type,
                allowed=ChannelOutcomeKind,
            )
            assert isinstance(raw_kind, ChannelOutcomeKind)
            return ChannelOutcome(
                raw_kind,
                _projection(raw_kind.value, classification),
                _digest(
                    {
                        "binding": binding,
                        "classification": classification,
                        "result": raw_kind.value,
                    }
                ),
            )
        except AdapterFailure as exc:
            return _failure_outcome(exc)

    def reconcile(self, effect_idempotency_key: str) -> ReconciliationOutcome:
        self.reconciliation_count += 1
        binding = self._bindings.get(effect_idempotency_key)
        if binding is None:
            kind = ReconciliationKind.STILL_UNKNOWN
            return ReconciliationOutcome(
                kind,
                _projection(kind.value, "binding_unavailable_after_restart"),
                safe_digest(
                    AdapterFailureCategory.INVALID_RESPONSE,
                    "binding_unavailable_after_restart",
                ),
            )
        document = reconciliation_request_document(effect_idempotency_key, binding)
        try:
            response = self._transport.post(document, idempotency_key=effect_idempotency_key)
            if response.status != 200:
                raise _http_failure(response.status)
            raw_kind, classification = _strict_response(
                response.body,
                response.content_type,
                allowed=ReconciliationKind,
            )
            assert isinstance(raw_kind, ReconciliationKind)
            return ReconciliationOutcome(
                raw_kind,
                _projection(raw_kind.value, classification),
                _digest(
                    {
                        "binding": binding,
                        "classification": classification,
                        "result": raw_kind.value,
                    }
                ),
            )
        except AdapterFailure as exc:
            kind = ReconciliationKind.STILL_UNKNOWN
            return ReconciliationOutcome(
                kind,
                _projection(kind.value, exc.category.value),
                exc.diagnostic_digest,
            )
