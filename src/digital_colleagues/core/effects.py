# SPDX-License-Identifier: Apache-2.0

"""Fully specified immutable effects, approvals, attempts, and results."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from digital_colleagues.core.authority import EffectKind
from digital_colleagues.core.common import (
    SCHEMA_VERSION,
    FrozenJsonObject,
    require_digest,
    require_revision,
    require_stable_id,
    require_text,
    require_utc,
)
from digital_colleagues.core.errors import AuthorizationError, CoreInvariantError
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import Principal, PrincipalKind
from digital_colleagues.core.runtime import _validate_causal_record


def _json_data(value: object) -> object:
    if isinstance(value, FrozenJsonObject):
        return {key: _json_data(item) for key, item in value.as_entries()}
    if isinstance(value, tuple):
        return [_json_data(item) for item in value]
    return value


def _payload_digest(payload: FrozenJsonObject) -> str:
    return _canonical_digest(_json_data(payload))


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _datetime_to_canonical_z(value: datetime) -> str:
    return value.isoformat(timespec="microseconds").removesuffix("+00:00") + "Z"


def _namespace_envelope(namespace: Namespace) -> dict[str, object]:
    return {
        "scope": namespace.scope.value,
        "scope_id": namespace.scope_id,
        "tenant_id": namespace.tenant_id,
    }


def _principal_envelope(principal: Principal) -> dict[str, object]:
    return {
        "kind": principal.kind.value,
        "namespace": _namespace_envelope(principal.namespace),
        "principal_id": principal.principal_id,
        "revision": principal.revision,
        "roles": sorted(role.value for role in principal.roles),
        "schema_version": principal.schema_version,
    }


@dataclass(frozen=True, slots=True)
class EffectDestination:
    kind: str
    target: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", require_stable_id(self.kind, "destination kind"))
        object.__setattr__(
            self,
            "target",
            require_text(self.target, "destination target", maximum=512),
        )


@dataclass(frozen=True, slots=True)
class EffectConstraints:
    boundary_id: str
    idempotency_key: str
    valid_until: datetime
    maximum_attempts: int
    parameters: FrozenJsonObject

    def __post_init__(self) -> None:
        require_stable_id(self.boundary_id, "boundary_id")
        require_stable_id(self.idempotency_key, "idempotency_key")
        require_utc(self.valid_until, "valid_until")
        if type(self.maximum_attempts) is not int or self.maximum_attempts < 1:
            raise CoreInvariantError("maximum_attempts must be a positive integer")
        if not isinstance(self.parameters, FrozenJsonObject):
            raise CoreInvariantError("effect constraint parameters must be immutable")


class EffectProposalState(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class EffectProposal:
    namespace: Namespace
    proposal_id: str
    decision_id: str
    effect_kind: EffectKind
    destination: EffectDestination
    action: str
    payload: FrozenJsonObject = field(repr=False)
    safe_projection: FrozenJsonObject
    constraints: EffectConstraints
    state: EffectProposalState
    actor: Principal
    correlation_id: str
    causation_id: str
    occurred_at: datetime
    revision: int
    schema_version: int = SCHEMA_VERSION
    mandate_id: str | None = None
    mandate_revision: int | None = None
    payload_digest: str = field(init=False)
    proposal_digest: str = field(init=False)

    def __post_init__(self) -> None:
        require_stable_id(self.proposal_id, "proposal_id")
        require_stable_id(self.decision_id, "decision_id")
        if not isinstance(self.effect_kind, EffectKind):
            raise CoreInvariantError("effect kind must be explicit")
        if not isinstance(self.destination, EffectDestination):
            raise CoreInvariantError("effect destination must be fully specified")
        object.__setattr__(self, "action", require_stable_id(self.action, "effect action"))
        if not isinstance(self.payload, FrozenJsonObject) or len(self.payload) == 0:
            raise CoreInvariantError("effect payload must be a non-empty immutable object")
        if not isinstance(self.safe_projection, FrozenJsonObject) or len(self.safe_projection) == 0:
            raise CoreInvariantError("effect safe projection must be non-empty and immutable")
        if not isinstance(self.constraints, EffectConstraints):
            raise CoreInvariantError("effect constraints must be fully specified")
        if not isinstance(self.state, EffectProposalState):
            raise CoreInvariantError("effect proposal state must be explicit")
        _validate_causal_record(
            namespace=self.namespace,
            actor=self.actor,
            correlation_id=self.correlation_id,
            causation_id=self.causation_id,
            occurred_at=self.occurred_at,
            revision=self.revision,
            schema_version=self.schema_version,
        )
        if self.causation_id != self.decision_id:
            raise CoreInvariantError("effect proposal causation must name its decision")
        if self.constraints.valid_until <= self.occurred_at:
            raise CoreInvariantError("effect proposal must expire after it is proposed")
        if (self.mandate_id is None) != (self.mandate_revision is None):
            raise CoreInvariantError("proposal mandate identity must be complete")
        if self.mandate_id is not None:
            require_stable_id(self.mandate_id, "mandate_id")
            assert self.mandate_revision is not None
            require_revision(self.mandate_revision, "mandate_revision")
        payload_digest = _payload_digest(self.payload)
        object.__setattr__(self, "payload_digest", payload_digest)
        envelope = {
            "action": self.action,
            "actor": _principal_envelope(self.actor),
            "causation_id": self.causation_id,
            "constraints": {
                "boundary_id": self.constraints.boundary_id,
                "idempotency_key": self.constraints.idempotency_key,
                "maximum_attempts": self.constraints.maximum_attempts,
                "parameters": _json_data(self.constraints.parameters),
                "valid_until": _datetime_to_canonical_z(self.constraints.valid_until),
            },
            "correlation_id": self.correlation_id,
            "decision_id": self.decision_id,
            "destination": {
                "kind": self.destination.kind,
                "target": self.destination.target,
            },
            "digest_schema_version": 1,
            "effect_kind": self.effect_kind.value,
            "mandate_id": self.mandate_id,
            "mandate_revision": self.mandate_revision,
            "namespace": _namespace_envelope(self.namespace),
            "occurred_at": _datetime_to_canonical_z(self.occurred_at),
            "payload_digest": payload_digest,
            "proposal_id": self.proposal_id,
            "proposal_revision": self.revision,
            "safe_projection": _json_data(self.safe_projection),
            "schema_version": self.schema_version,
            "state": self.state.value,
        }
        object.__setattr__(self, "proposal_digest", _canonical_digest(envelope))


class ApprovalChoice(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class HumanApprovalDecision:
    namespace: Namespace
    approval_decision_id: str
    proposal_id: str
    proposal_revision: int
    proposal_payload_digest: str
    proposal_digest: str
    choice: ApprovalChoice
    author: Principal
    idempotency_key: str
    correlation_id: str
    causation_id: str
    occurred_at: datetime
    valid_until: datetime
    revision: int
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_stable_id(self.approval_decision_id, "approval_decision_id")
        require_stable_id(self.proposal_id, "proposal_id")
        require_revision(self.proposal_revision, "proposal_revision")
        require_digest(self.proposal_payload_digest, "proposal_payload_digest")
        require_digest(self.proposal_digest, "proposal_digest")
        if not isinstance(self.choice, ApprovalChoice):
            raise CoreInvariantError("approval choice must be explicit")
        if self.author.kind is not PrincipalKind.HUMAN:
            raise AuthorizationError("only a durable human principal may author approval")
        require_stable_id(self.idempotency_key, "idempotency_key")
        _validate_causal_record(
            namespace=self.namespace,
            actor=self.author,
            correlation_id=self.correlation_id,
            causation_id=self.causation_id,
            occurred_at=self.occurred_at,
            revision=self.revision,
            schema_version=self.schema_version,
        )
        if self.causation_id != self.proposal_id:
            raise CoreInvariantError("approval causation must name its proposal")
        require_utc(self.valid_until, "valid_until")
        if self.valid_until < self.occurred_at:
            raise CoreInvariantError("approval validity cannot end before its decision time")


class EffectAttemptState(StrEnum):
    PLANNED = "planned"
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class EffectAttempt:
    namespace: Namespace
    effect_attempt_id: str
    proposal_id: str
    proposal_revision: int
    approval_decision_id: str
    attempt_number: int
    state: EffectAttemptState
    actor: Principal
    correlation_id: str
    causation_id: str
    occurred_at: datetime
    revision: int
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_stable_id(self.effect_attempt_id, "effect_attempt_id")
        require_stable_id(self.proposal_id, "proposal_id")
        require_revision(self.proposal_revision, "proposal_revision")
        require_stable_id(self.approval_decision_id, "approval_decision_id")
        if type(self.attempt_number) is not int or self.attempt_number < 1:
            raise CoreInvariantError("attempt_number must be positive")
        if not isinstance(self.state, EffectAttemptState):
            raise CoreInvariantError("effect attempt state must be explicit")
        _validate_causal_record(
            namespace=self.namespace,
            actor=self.actor,
            correlation_id=self.correlation_id,
            causation_id=self.causation_id,
            occurred_at=self.occurred_at,
            revision=self.revision,
            schema_version=self.schema_version,
        )
        if self.causation_id != self.approval_decision_id:
            raise CoreInvariantError("effect attempt causation must name its approval decision")


class ActionResultState(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    NOT_EXECUTED = "not_executed"
    RETRYABLE_FAILURE = "retryable_failure"
    PERMANENT_FAILURE = "permanent_failure"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class ActionResult:
    namespace: Namespace
    action_result_id: str
    effect_attempt_id: str
    state: ActionResultState
    safe_projection: FrozenJsonObject
    result_digest: str
    actor: Principal
    correlation_id: str
    causation_id: str
    occurred_at: datetime
    revision: int
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_stable_id(self.action_result_id, "action_result_id")
        require_stable_id(self.effect_attempt_id, "effect_attempt_id")
        if not isinstance(self.state, ActionResultState):
            raise CoreInvariantError("action result state must be explicit")
        if not isinstance(self.safe_projection, FrozenJsonObject):
            raise CoreInvariantError("action result safe projection must be immutable")
        require_digest(self.result_digest, "result_digest")
        _validate_causal_record(
            namespace=self.namespace,
            actor=self.actor,
            correlation_id=self.correlation_id,
            causation_id=self.causation_id,
            occurred_at=self.occurred_at,
            revision=self.revision,
            schema_version=self.schema_version,
        )
        if self.causation_id != self.effect_attempt_id:
            raise CoreInvariantError("action result causation must name its effect attempt")
