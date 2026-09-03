# SPDX-License-Identifier: Apache-2.0

"""Strict provider-neutral HTTP JSON intelligence adapter."""

from __future__ import annotations

from typing import Any

from digital_colleagues.adapters.http_json.configuration import HttpJsonSettings
from digital_colleagues.adapters.http_json.errors import (
    PROTOCOL_VERSION,
    AdapterFailure,
    AdapterFailureCategory,
)
from digital_colleagues.adapters.http_json.transport import HttpJsonTransport, parse_json_object
from digital_colleagues.application.contracts import (
    IntelligenceRequest,
    SemanticDecision,
    SemanticOutcome,
)
from digital_colleagues.core.authority import EffectBoundary, EffectKind
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.effects import (
    EffectConstraints,
    EffectDestination,
    EffectProposal,
    EffectProposalState,
)
from digital_colleagues.core.principals import PrincipalKind
from digital_colleagues.core.runtime import Decision, DecisionKind

_TOP_LEVEL_FIELDS = {"protocol_version", "result_kind", "result"}
_PROPOSAL_FIELDS = {
    "rationale",
    "effect_kind",
    "destination",
    "action",
    "payload",
    "safe_projection",
}
_DESTINATION_FIELDS = {"kind", "target"}
_NON_PROPOSAL_FIELDS = {"rationale"}
_AUTHORITY_FIELDS = {
    "approval",
    "approval_decision_id",
    "callback",
    "constraints",
    "credential",
    "decision_id",
    "effect_idempotency_key",
    "endpoint",
    "idempotency_key",
    "mandate_id",
    "mandate_revision",
    "namespace",
    "occurred_at",
    "policy_id",
    "policy_revision",
    "principal",
    "principal_id",
    "proposal_id",
    "role",
    "roles",
    "schema_version",
    "tenant_id",
    "tool",
    "valid_until",
}


def _json_value(value: object) -> object:
    if isinstance(value, FrozenJsonObject):
        return {key: _json_value(item) for key, item in value.as_entries()}
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    return value


def _namespace(request: IntelligenceRequest) -> dict[str, object]:
    return {
        "scope": request.namespace.scope.value,
        "scope_id": request.namespace.scope_id,
        "tenant_id": request.namespace.tenant_id,
    }


def _boundary(value: EffectBoundary) -> dict[str, object]:
    return {
        "allowed_actions": list(value.allowed_actions),
        "allowed_destination_kinds": list(value.allowed_destination_kinds),
        "boundary_id": value.boundary_id,
        "constraints": _json_value(value.constraints),
        "effect_kind": value.effect_kind.value,
        "human_approval_required": value.human_approval_required,
    }


def model_request_document(request: IntelligenceRequest) -> dict[str, object]:
    return {
        "authority": {
            "effect_boundaries": [_boundary(item) for item in request.mandate.effect_boundaries],
            "mandate_id": request.mandate.mandate_id,
            "mandate_revision": request.mandate.revision,
            "policy_id": request.policy_id,
            "policy_revision": request.policy_revision,
        },
        "causality": {
            "causation_id": request.agenda_item.agenda_item_id,
            "correlation_id": request.agenda_item.correlation_id,
        },
        "namespace": _namespace(request),
        "protocol_version": PROTOCOL_VERSION,
        "request": {
            "agenda_item_id": request.agenda_item.agenda_item_id,
            "cause_ids": list(request.agenda_item.cause_ids),
            "generation": request.agenda_item.generation,
            "priority": request.agenda_item.priority,
            "source_event_id": request.agenda_item.source_event_id,
            "source_timer_occurrence_id": request.agenda_item.source_timer_occurrence_id,
            "title": request.agenda_item.title,
            "wake_cycle_id": request.wake_cycle.wake_cycle_id,
            "work_id": request.agenda_item.work_id,
        },
        "request_id": request.request_id,
        "request_kind": "semantic_decision",
        "schema_version": request.schema_version,
    }


def _contains_authority_field(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            key in _AUTHORITY_FIELDS or _contains_authority_field(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_authority_field(child) for child in value)
    return False


def _invalid(result_class: str, *, authority: bool = False) -> AdapterFailure:
    return AdapterFailure(
        AdapterFailureCategory.AUTHORITY_INJECTION
        if authority
        else AdapterFailureCategory.INVALID_RESPONSE,
        result_class=result_class,
    )


def _require_exact(value: dict[str, Any], fields: set[str], result_class: str) -> None:
    if set(value) != fields:
        raise _invalid(result_class, authority=_contains_authority_field(value))


def _bounded_text(value: object, *, maximum: int, result_class: str) -> str:
    if not isinstance(value, str):
        raise _invalid(result_class)
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise _invalid(result_class)
    return normalized


def _response_failure(status: int) -> AdapterFailure:
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


class HttpJsonIntelligence:
    def __init__(self, settings: HttpJsonSettings) -> None:
        self._settings = settings
        self._transport = HttpJsonTransport(settings)
        self.call_count = 0

    def _post(self, document: dict[str, object]) -> dict[str, Any]:
        attempts = 0
        while True:
            try:
                response = self._transport.post(document)
                break
            except AdapterFailure as exc:
                retryable = (
                    not exc.after_submit
                    and exc.category
                    in {
                        AdapterFailureCategory.CONNECT_FAILURE,
                        AdapterFailureCategory.DNS_FAILURE,
                    }
                    and attempts < self._settings.maximum_pre_submit_retries
                )
                if not retryable:
                    raise
                attempts += 1
        if response.status != 200:
            raise _response_failure(response.status)
        if response.content_type.split(";", 1)[0].strip().lower() != "application/json":
            raise _invalid("invalid_content_type")
        return parse_json_object(response.body)

    def decide(self, request: IntelligenceRequest) -> SemanticDecision:
        if request.model_principal.kind is not PrincipalKind.MODEL:
            raise _invalid("model_principal_required", authority=True)
        self.call_count += 1
        response = self._post(model_request_document(request))
        if _contains_authority_field(response):
            raise _invalid("authority_field_refused", authority=True)
        _require_exact(response, _TOP_LEVEL_FIELDS, "response_fields")
        if response["protocol_version"] != PROTOCOL_VERSION:
            raise _invalid("protocol_mismatch")
        result_kind = response["result_kind"]
        result = response["result"]
        if not isinstance(result_kind, str) or not isinstance(result, dict):
            raise _invalid("result_shape")
        try:
            outcome = SemanticOutcome(result_kind)
        except ValueError:
            raise _invalid("unknown_outcome") from None
        if outcome is SemanticOutcome.PROPOSAL:
            return self._proposal(request, result)
        _require_exact(result, _NON_PROPOSAL_FIELDS, "non_proposal_fields")
        rationale = _bounded_text(result["rationale"], maximum=2_048, result_class="rationale")
        decision_kind = (
            DecisionKind.NO_ACTION if outcome is SemanticOutcome.NO_OP else DecisionKind.DEFER_ITEM
        )
        decision = Decision(
            namespace=request.namespace,
            decision_id=request.decision_id,
            wake_cycle_id=request.wake_cycle.wake_cycle_id,
            agenda_item_id=request.agenda_item.agenda_item_id,
            kind=decision_kind,
            rationale=rationale,
            proposed_effect_id=None,
            actor=request.model_principal,
            correlation_id=request.agenda_item.correlation_id,
            causation_id=request.agenda_item.agenda_item_id,
            occurred_at=request.occurred_at,
            revision=1,
            policy_id=request.policy_id,
            policy_revision=request.policy_revision,
        )
        return SemanticDecision(outcome, decision, None, request.request_id)

    def _proposal(self, request: IntelligenceRequest, result: dict[str, Any]) -> SemanticDecision:
        _require_exact(result, _PROPOSAL_FIELDS, "proposal_fields")
        destination = result["destination"]
        if not isinstance(destination, dict):
            raise _invalid("destination_shape")
        _require_exact(destination, _DESTINATION_FIELDS, "destination_fields")
        effect_kind_value = _bounded_text(
            result["effect_kind"], maximum=128, result_class="effect_kind"
        )
        destination_kind = _bounded_text(
            destination["kind"], maximum=128, result_class="destination_kind"
        )
        target = _bounded_text(
            destination["target"], maximum=512, result_class="destination_target"
        )
        action = _bounded_text(result["action"], maximum=128, result_class="action")
        try:
            effect_kind = EffectKind(effect_kind_value)
        except ValueError:
            raise _invalid("unknown_effect_kind") from None
        matches = tuple(
            boundary
            for boundary in request.mandate.effect_boundaries
            if boundary.effect_kind is effect_kind
            and destination_kind in boundary.allowed_destination_kinds
            and action in boundary.allowed_actions
        )
        if len(matches) != 1 or not matches[0].human_approval_required:
            raise _invalid("outside_mandate", authority=True)
        boundary = matches[0]
        payload = result["payload"]
        safe_projection = result["safe_projection"]
        if (
            not isinstance(payload, dict)
            or not payload
            or not isinstance(safe_projection, dict)
            or not safe_projection
        ):
            raise _invalid("effect_payload_shape")
        try:
            immutable_payload = FrozenJsonObject.from_mapping(payload)
            immutable_projection = FrozenJsonObject.from_mapping(safe_projection)
        except (TypeError, ValueError):
            raise _invalid("effect_json_shape") from None
        rationale = _bounded_text(result["rationale"], maximum=2_048, result_class="rationale")
        decision = Decision(
            namespace=request.namespace,
            decision_id=request.decision_id,
            wake_cycle_id=request.wake_cycle.wake_cycle_id,
            agenda_item_id=request.agenda_item.agenda_item_id,
            kind=DecisionKind.PROPOSE_EFFECT,
            rationale=rationale,
            proposed_effect_id=request.proposal_id,
            actor=request.model_principal,
            correlation_id=request.agenda_item.correlation_id,
            causation_id=request.agenda_item.agenda_item_id,
            occurred_at=request.occurred_at,
            revision=1,
            policy_id=request.policy_id,
            policy_revision=request.policy_revision,
        )
        proposal = EffectProposal(
            namespace=request.namespace,
            proposal_id=request.proposal_id,
            decision_id=request.decision_id,
            effect_kind=effect_kind,
            destination=EffectDestination(kind=destination_kind, target=target),
            action=action,
            payload=immutable_payload,
            safe_projection=immutable_projection,
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
            policy_id=request.policy_id,
            policy_revision=request.policy_revision,
        )
        return SemanticDecision(SemanticOutcome.PROPOSAL, decision, proposal, request.request_id)
