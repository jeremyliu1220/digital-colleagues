# SPDX-License-Identifier: Apache-2.0

"""Mechanically inspect the required P2 public contract surface."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from digital_colleagues import core
from digital_colleagues.core.errors import (
    AuthorizationError,
    CoreInvariantError,
    NamespaceMismatchError,
    RevisionMismatchError,
)
from digital_colleagues.governance import (
    authorize_human_approval,
    require_authoritative_human_role,
)

REQUIRED_DATACLASSES = {
    "ActionResult",
    "AgendaItem",
    "CapabilityGrant",
    "CompletionEvidence",
    "Constraint",
    "Decision",
    "EffectAttempt",
    "EffectBoundary",
    "EffectConstraints",
    "EffectDestination",
    "EffectProposal",
    "FiniteWork",
    "FrozenJsonObject",
    "HumanApprovalDecision",
    "IdentityCard",
    "InputEvent",
    "Mandate",
    "MandateAuthorityDiff",
    "Namespace",
    "Obligation",
    "Principal",
    "Profile",
    "Responsibility",
    "ResponsibilityDefinition",
    "WakeCycle",
}
REQUIRED_ENUMS = {
    "ActionResultState",
    "AgendaItemState",
    "ApprovalChoice",
    "DecisionKind",
    "EffectAttemptState",
    "EffectKind",
    "EffectProposalState",
    "HumanRole",
    "InputEventState",
    "NamespaceScope",
    "ObligationState",
    "PrincipalKind",
    "ResponsibilityState",
    "WakeCycleState",
    "WorkState",
}
REQUIRED_PROTOCOLS = {"Clock", "EntropySource", "IdentifierSource"}
REQUIRED_RECORD_FIELDS = {
    "schema_version",
    "namespace",
    "revision",
}


class ContractCheckError(RuntimeError):
    """A required public core contract is missing or mutable."""


def _is_frozen_dataclass(value: object) -> bool:
    parameters = getattr(value, "__dataclass_params__", None)
    return dataclasses.is_dataclass(value) and parameters is not None and parameters.frozen


def check_core_contracts(_root: Path) -> dict[str, object]:
    exported = set(core.__all__)
    missing = sorted((REQUIRED_DATACLASSES | REQUIRED_ENUMS | REQUIRED_PROTOCOLS) - exported)
    if missing:
        raise ContractCheckError("required P2 exports are missing: " + ", ".join(missing))
    mutable = sorted(
        name for name in REQUIRED_DATACLASSES if not _is_frozen_dataclass(getattr(core, name))
    )
    if mutable:
        raise ContractCheckError("P2 dataclasses are not frozen: " + ", ".join(mutable))
    unslotted = sorted(
        name for name in REQUIRED_DATACLASSES if not hasattr(getattr(core, name), "__slots__")
    )
    if unslotted:
        raise ContractCheckError("P2 dataclasses are not slotted: " + ", ".join(unslotted))
    invalid_enums = sorted(
        name
        for name in REQUIRED_ENUMS
        if not isinstance(getattr(core, name), type) or not issubclass(getattr(core, name), Enum)
    )
    if invalid_enums:
        raise ContractCheckError("P2 enum contracts are invalid: " + ", ".join(invalid_enums))
    invalid_protocols = sorted(
        name
        for name in REQUIRED_PROTOCOLS
        if not isinstance(getattr(core, name), type)
        or getattr(getattr(core, name), "_is_protocol", False) is not True
    )
    if invalid_protocols:
        raise ContractCheckError(
            "P2 injection protocols are invalid: " + ", ".join(invalid_protocols)
        )

    record_names = {
        "ActionResult",
        "AgendaItem",
        "Decision",
        "EffectAttempt",
        "EffectProposal",
        "FiniteWork",
        "HumanApprovalDecision",
        "InputEvent",
        "Mandate",
        "Obligation",
        "Profile",
        "Responsibility",
        "WakeCycle",
    }
    for name in record_names:
        field_names = {field.name for field in dataclasses.fields(getattr(core, name))}
        absent = REQUIRED_RECORD_FIELDS - field_names
        if absent:
            raise ContractCheckError(f"{name} is missing persisted record fields")
    actor_fields = {
        "ActionResult": "actor",
        "AgendaItem": "actor",
        "Decision": "actor",
        "EffectAttempt": "actor",
        "EffectProposal": "actor",
        "FiniteWork": "actor",
        "HumanApprovalDecision": "author",
        "InputEvent": "actor",
        "Mandate": "issued_by",
        "Obligation": "actor",
        "Profile": "updated_by",
        "Responsibility": "actor",
        "WakeCycle": "actor",
    }
    for name, actor_field in actor_fields.items():
        field_names = {field.name for field in dataclasses.fields(getattr(core, name))}
        if actor_field not in field_names:
            raise ContractCheckError(f"{name} is missing its actor principal")
    causal_record_names = record_names - {"Mandate", "Profile"}
    for name in causal_record_names:
        field_names = {field.name for field in dataclasses.fields(getattr(core, name))}
        if not {"correlation_id", "causation_id"}.issubset(field_names):
            raise ContractCheckError(f"{name} is missing causal references")

    namespace = core.Namespace.colleague("tenant-check", "colleague-check")
    try:
        namespace.require_exact(core.Namespace.colleague("tenant-other", "colleague-check"))
    except NamespaceMismatchError:
        namespace_result = "passed"
    else:
        raise ContractCheckError("namespace mismatch did not fail closed")

    mutable_source: dict[str, Any] = {"nested": [1, {"value": "original"}]}
    frozen = core.FrozenJsonObject.from_mapping(mutable_source)
    nested_source = mutable_source["nested"]
    if isinstance(nested_source, list):
        nested_source.append("later")
    if core.to_canonical_json(frozen) != '{"nested":[1,{"value":"original"}]}':
        raise ContractCheckError("nested values are not deeply immutable")

    moment = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    if core.datetime_from_z(core.datetime_to_z(moment)) != moment:
        raise ContractCheckError("UTC Z serialization does not round trip")
    try:
        core.datetime_to_z(datetime(2026, 1, 2, 3, 4, 5))
    except CoreInvariantError:
        serialization_result = "passed"
    else:
        raise ContractCheckError("naive datetime did not fail closed")

    kinds = {kind.value for kind in core.PrincipalKind}
    roles = {role.value for role in core.HumanRole}
    if kinds != {"human", "model", "service"}:
        raise ContractCheckError("principal kinds are not the required disjoint set")
    if roles != {"tenant_admin", "colleague_user", "auditor"}:
        raise ContractCheckError("human roles are not the canonical set")

    model = core.Principal.model(tenant_id="tenant-check", principal_id="principal-model-check")
    human = core.Principal.human(
        tenant_id="tenant-check",
        principal_id="principal-human-check",
        roles=(core.HumanRole.COLLEAGUE_USER,),
    )
    proposal = core.EffectProposal(
        namespace=namespace,
        proposal_id="proposal-check",
        decision_id="decision-check",
        effect_kind=core.EffectKind.REFERENCE_MESSAGE,
        destination=core.EffectDestination(kind="reference-channel", target="synthetic-target"),
        action="deliver",
        payload=core.FrozenJsonObject.from_mapping({"body": "sensitive-check-value"}),
        safe_projection=core.FrozenJsonObject.from_mapping({"summary": "Synthetic check"}),
        constraints=core.EffectConstraints(
            boundary_id="boundary-check",
            idempotency_key="effect-key-check",
            valid_until=moment + timedelta(hours=1),
            maximum_attempts=1,
            parameters=core.FrozenJsonObject.from_mapping({"network": False}),
        ),
        state=core.EffectProposalState.PENDING_APPROVAL,
        actor=model,
        correlation_id="correlation-check",
        causation_id="decision-check",
        occurred_at=moment,
        revision=1,
    )

    def approval(
        author: core.Principal, *, proposal_revision: int = 1
    ) -> core.HumanApprovalDecision:
        return core.HumanApprovalDecision(
            namespace=namespace,
            approval_decision_id="approval-check",
            proposal_id=proposal.proposal_id,
            proposal_revision=proposal_revision,
            proposal_payload_digest=proposal.payload_digest,
            choice=core.ApprovalChoice.APPROVE,
            author=author,
            idempotency_key="approval-key-check",
            correlation_id=proposal.correlation_id,
            causation_id=proposal.proposal_id,
            occurred_at=moment + timedelta(minutes=1),
            valid_until=moment + timedelta(minutes=30),
            revision=1,
        )

    try:
        approval(model)
    except AuthorizationError:
        principal_result = "passed"
    else:
        raise ContractCheckError("model principal authored a human approval")
    valid_approval = approval(human)
    authorization = authorize_human_approval(
        proposal,
        valid_approval,
        evaluated_at=moment + timedelta(minutes=2),
    )
    if authorization.proposal_payload_digest != proposal.payload_digest:
        raise ContractCheckError("approval did not bind the immutable effect payload")
    try:
        authorize_human_approval(
            proposal,
            approval(human, proposal_revision=2),
            evaluated_at=moment + timedelta(minutes=2),
        )
    except RevisionMismatchError:
        approval_result = "passed"
    else:
        raise ContractCheckError("stale proposal revision did not fail closed")
    try:
        require_authoritative_human_role(
            human,
            accepted_roles=frozenset({core.HumanRole.TENANT_ADMIN}),
            caller_supplied_role_ids=("tenant_admin",),
        )
    except AuthorizationError:
        pass
    else:
        raise ContractCheckError("caller-supplied role became authoritative")
    serialized_proposal = core.to_canonical_json(proposal)
    if "sensitive-check-value" in serialized_proposal or '"payload"' in serialized_proposal:
        raise ContractCheckError("public serialization exposed an effect payload")

    return {
        "schema_version": 1,
        "gate": "p2_core_contracts_clean",
        "frozen_dataclass_count": len(REQUIRED_DATACLASSES),
        "enum_count": len(REQUIRED_ENUMS),
        "protocol_count": len(REQUIRED_PROTOCOLS),
        "record_shape_count": len(record_names),
        "immutability": "passed",
        "namespace": namespace_result,
        "principal_separation": principal_result,
        "authority_approval": approval_result,
        "serialization": serialization_result,
        "effect_payload_redacted": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P2 public core contracts.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_core_contracts(Path(arguments.root))
    except ContractCheckError as exc:
        print(f"P2 core contract check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
