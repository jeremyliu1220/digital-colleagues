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

from digital_colleagues import core, governance
from digital_colleagues.core.errors import (
    AuthorizationError,
    CoreInvariantError,
    NamespaceMismatchError,
    ReplayError,
)
from digital_colleagues.governance import (
    authorize_effect_proposal,
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
REQUIRED_GOVERNANCE_DATACLASSES = {"ApprovalAuthorization"}
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


def _exported_dataclasses(module: object) -> dict[str, type[object]]:
    names = getattr(module, "__all__", ())
    return {
        name: value
        for name in names
        if isinstance((value := getattr(module, name)), type) and dataclasses.is_dataclass(value)
    }


def _assert_rejected(label: str, operation: Any) -> None:
    try:
        operation()
    except CoreInvariantError:
        return
    raise ContractCheckError(f"{label} did not fail closed")


def _assert_detached(label: str, source: Any, stored: Any) -> None:
    before = tuple(stored)
    source.append("mutation-after-construction")
    if stored != before or not isinstance(stored, tuple):
        raise ContractCheckError(f"{label} retained mutable caller input")


def check_core_contracts(_root: Path) -> dict[str, object]:
    exported = set(core.__all__)
    missing = sorted((REQUIRED_DATACLASSES | REQUIRED_ENUMS | REQUIRED_PROTOCOLS) - exported)
    if missing:
        raise ContractCheckError("required P2 exports are missing: " + ", ".join(missing))
    missing_governance = sorted(REQUIRED_GOVERNANCE_DATACLASSES - set(governance.__all__))
    if missing_governance:
        raise ContractCheckError(
            "required governance exports are missing: " + ", ".join(missing_governance)
        )
    public_dataclasses = {
        **_exported_dataclasses(core),
        **_exported_dataclasses(governance),
    }
    mutable = sorted(
        name for name, value in public_dataclasses.items() if not _is_frozen_dataclass(value)
    )
    if mutable:
        raise ContractCheckError("P2 dataclasses are not frozen: " + ", ".join(mutable))
    unslotted = sorted(
        name for name, value in public_dataclasses.items() if not hasattr(value, "__slots__")
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
    service = core.Principal.service(
        tenant_id="tenant-check", principal_id="principal-service-check"
    )
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
            proposal_digest=proposal.proposal_digest,
            choice=core.ApprovalChoice.APPROVE,
            author=author,
            idempotency_key="approval-key-check",
            correlation_id=proposal.correlation_id,
            causation_id=proposal.proposal_id,
            occurred_at=moment + timedelta(minutes=1),
            valid_until=moment + timedelta(minutes=30),
            revision=1,
        )

    for non_human in (model, service):
        _assert_rejected(
            f"{non_human.kind.value} principal human approval",
            lambda author=non_human: approval(author),
        )
    valid_approval = approval(human)
    authorization = authorize_human_approval(
        proposal,
        valid_approval,
        evaluated_at=moment + timedelta(minutes=2),
    )
    if (
        authorization.proposal_payload_digest != proposal.payload_digest
        or authorization.proposal_digest != proposal.proposal_digest
        or valid_approval.proposal_digest != proposal.proposal_digest
    ):
        raise ContractCheckError("approval did not bind the complete immutable effect")

    other_model = core.Principal.model(
        tenant_id="tenant-check", principal_id="principal-model-other"
    )
    complete_effect_mutations = {
        "destination target": dataclasses.replace(
            proposal,
            destination=dataclasses.replace(proposal.destination, target="other-target"),
        ),
        "destination kind": dataclasses.replace(
            proposal,
            destination=dataclasses.replace(proposal.destination, kind="other-channel"),
        ),
        "action": dataclasses.replace(proposal, action="archive"),
        "effect kind": dataclasses.replace(proposal, effect_kind=core.EffectKind.INTERNAL_RECORD),
        "payload": dataclasses.replace(
            proposal,
            payload=core.FrozenJsonObject.from_mapping({"body": "changed-sensitive-value"}),
        ),
        "safe projection": dataclasses.replace(
            proposal,
            safe_projection=core.FrozenJsonObject.from_mapping({"summary": "Changed"}),
        ),
        "boundary ID": dataclasses.replace(
            proposal,
            constraints=dataclasses.replace(proposal.constraints, boundary_id="boundary-other"),
        ),
        "idempotency key": dataclasses.replace(
            proposal,
            constraints=dataclasses.replace(
                proposal.constraints, idempotency_key="effect-key-other"
            ),
        ),
        "valid-until": dataclasses.replace(
            proposal,
            constraints=dataclasses.replace(
                proposal.constraints, valid_until=moment + timedelta(hours=2)
            ),
        ),
        "maximum attempts": dataclasses.replace(
            proposal,
            constraints=dataclasses.replace(proposal.constraints, maximum_attempts=2),
        ),
        "constraint parameters": dataclasses.replace(
            proposal,
            constraints=dataclasses.replace(
                proposal.constraints,
                parameters=core.FrozenJsonObject.from_mapping({"network": True}),
            ),
        ),
        "actor identity": dataclasses.replace(proposal, actor=other_model),
        "correlation ID": dataclasses.replace(proposal, correlation_id="correlation-other"),
        "decision and causation IDs": dataclasses.replace(
            proposal,
            decision_id="decision-other",
            causation_id="decision-other",
        ),
        "occurred-at": dataclasses.replace(proposal, occurred_at=moment + timedelta(seconds=1)),
        "proposal revision": dataclasses.replace(proposal, revision=2),
    }
    for label, changed in complete_effect_mutations.items():
        if changed.proposal_digest == proposal.proposal_digest:
            raise ContractCheckError(f"{label} was absent from the complete proposal digest")
        _assert_rejected(
            f"old approval after {label} mutation",
            lambda candidate=changed: authorize_human_approval(
                candidate,
                valid_approval,
                evaluated_at=moment + timedelta(minutes=2),
            ),
        )

    other_namespace = core.Namespace.colleague("tenant-other", "colleague-other")
    other_namespace_proposal = dataclasses.replace(
        proposal,
        namespace=other_namespace,
        actor=core.Principal.model(
            tenant_id="tenant-other", principal_id="principal-model-other-tenant"
        ),
    )
    if other_namespace_proposal.proposal_digest == proposal.proposal_digest:
        raise ContractCheckError("namespace was absent from the complete proposal digest")
    _assert_rejected(
        "cross-namespace approval",
        lambda: authorize_human_approval(
            other_namespace_proposal,
            valid_approval,
            evaluated_at=moment + timedelta(minutes=2),
        ),
    )
    wrong_proposal_approval = dataclasses.replace(
        valid_approval,
        proposal_id="proposal-other",
        causation_id="proposal-other",
    )
    _assert_rejected(
        "wrong proposal approval",
        lambda: authorize_human_approval(
            proposal,
            wrong_proposal_approval,
            evaluated_at=moment + timedelta(minutes=2),
        ),
    )
    _assert_rejected(
        "stale proposal approval",
        lambda: authorize_human_approval(
            proposal,
            approval(human, proposal_revision=2),
            evaluated_at=moment + timedelta(minutes=2),
        ),
    )
    _assert_rejected(
        "rejected approval choice",
        lambda: authorize_human_approval(
            proposal,
            dataclasses.replace(valid_approval, choice=core.ApprovalChoice.REJECT),
            evaluated_at=moment + timedelta(minutes=2),
        ),
    )
    replay_inputs = (
        {"consumed_decision_ids": frozenset({valid_approval.approval_decision_id})},
        {"consumed_idempotency_keys": frozenset({valid_approval.idempotency_key})},
        {"consumed_proposal_revisions": frozenset({(proposal.proposal_id, proposal.revision)})},
    )
    for replay_input in replay_inputs:
        try:
            authorize_human_approval(
                proposal,
                valid_approval,
                evaluated_at=moment + timedelta(minutes=2),
                **replay_input,
            )
        except ReplayError:
            pass
        else:
            raise ContractCheckError("approval replay did not fail closed")

    boundary = core.EffectBoundary(
        boundary_id="boundary-check",
        effect_kind=core.EffectKind.REFERENCE_MESSAGE,
        allowed_destination_kinds=("reference-channel",),
        allowed_actions=("deliver",),
        constraints=core.FrozenJsonObject.from_mapping({"network": False}),
    )
    responsibility = core.ResponsibilityDefinition(
        responsibility_id="responsibility-check",
        description="Check exact governed effects.",
        obligations=("Inspect the effect.",),
        completion_conditions=("Record a deterministic outcome.",),
    )
    capability = core.CapabilityGrant(
        capability_id="capability-check", description="Propose a checked effect."
    )
    constraint = core.Constraint(
        constraint_id="constraint-check", description="Network must remain disabled."
    )
    mandate = core.Mandate(
        namespace=namespace,
        mandate_id="mandate-check",
        mission="Authorize a synthetic checked effect.",
        service_relationship="Serves the synthetic checker tenant.",
        responsibilities=(responsibility,),
        capabilities=(capability,),
        constraints=(constraint,),
        working_context=core.FrozenJsonObject.from_mapping({"mode": "deterministic"}),
        effect_boundaries=(boundary,),
        revision=1,
        issued_by=human,
        effective_at=moment,
    )
    authorize_effect_proposal(proposal, mandate, expected_mandate_revision=1)
    constraint_cases = (
        (
            dataclasses.replace(
                proposal,
                constraints=dataclasses.replace(
                    proposal.constraints,
                    parameters=core.FrozenJsonObject.from_mapping({"network": True}),
                ),
            ),
            mandate,
        ),
        (
            dataclasses.replace(
                proposal,
                constraints=dataclasses.replace(
                    proposal.constraints,
                    parameters=core.FrozenJsonObject.from_mapping({}),
                ),
            ),
            mandate,
        ),
        (
            dataclasses.replace(
                proposal,
                constraints=dataclasses.replace(
                    proposal.constraints,
                    parameters=core.FrozenJsonObject.from_mapping(
                        {"network": False, "unknown": False}
                    ),
                ),
            ),
            mandate,
        ),
        (
            dataclasses.replace(
                proposal,
                constraints=dataclasses.replace(
                    proposal.constraints,
                    parameters=core.FrozenJsonObject.from_mapping({"network": 0}),
                ),
            ),
            mandate,
        ),
        (
            proposal,
            dataclasses.replace(
                mandate,
                effect_boundaries=(
                    dataclasses.replace(
                        boundary,
                        constraints=core.FrozenJsonObject.from_mapping({"unknown": False}),
                    ),
                ),
            ),
        ),
    )
    for constrained_proposal, constrained_mandate in constraint_cases:
        _assert_rejected(
            "invalid effect constraint",
            lambda candidate=constrained_proposal, authority=constrained_mandate: (
                authorize_effect_proposal(candidate, authority, expected_mandate_revision=1)
            ),
        )

    _assert_rejected(
        "required human approval state",
        lambda: authorize_effect_proposal(
            dataclasses.replace(proposal, state=core.EffectProposalState.APPROVED),
            mandate,
            expected_mandate_revision=1,
        ),
    )
    no_human_mandate = dataclasses.replace(
        mandate,
        effect_boundaries=(dataclasses.replace(boundary, human_approval_required=False),),
    )
    _assert_rejected(
        "unrequired human approval state",
        lambda: authorize_effect_proposal(proposal, no_human_mandate, expected_mandate_revision=1),
    )
    authorize_effect_proposal(
        dataclasses.replace(proposal, state=core.EffectProposalState.APPROVED),
        no_human_mandate,
        expected_mandate_revision=1,
    )

    invalid_authorization_values = {
        "proposal_id": "",
        "proposal_revision": 0,
        "proposal_payload_digest": "invalid",
        "proposal_digest": "sha256:invalid",
        "approval_decision_id": "",
        "author_principal_id": "",
        "schema_version": 0,
        "namespace": core.Namespace.tenant("tenant-check"),
    }
    for field_name, invalid_value in invalid_authorization_values.items():
        _assert_rejected(
            f"invalid ApprovalAuthorization {field_name}",
            lambda name=field_name, value=invalid_value: dataclasses.replace(
                authorization, **{name: value}
            ),
        )

    mutation_probe_count = 0

    role_source: Any = [core.HumanRole.COLLEAGUE_USER]
    detached_principal = core.Principal(
        namespace=core.Namespace.principal("tenant-check", "principal-detached"),
        principal_id="principal-detached",
        kind=core.PrincipalKind.HUMAN,
        roles=role_source,
    )
    _assert_detached("Principal.roles", role_source, detached_principal.roles)
    mutation_probe_count += 1

    obligation_source: Any = ["Inspect the effect."]
    completion_source: Any = ["Record the outcome."]
    detached_responsibility = core.ResponsibilityDefinition(
        responsibility_id="responsibility-detached",
        description="Detached responsibility.",
        obligations=obligation_source,
        completion_conditions=completion_source,
    )
    _assert_detached(
        "ResponsibilityDefinition.obligations",
        obligation_source,
        detached_responsibility.obligations,
    )
    _assert_detached(
        "ResponsibilityDefinition.completion_conditions",
        completion_source,
        detached_responsibility.completion_conditions,
    )
    mutation_probe_count += 2

    destination_source: Any = ["reference-channel"]
    action_source: Any = ["deliver"]
    detached_boundary = core.EffectBoundary(
        boundary_id="boundary-detached",
        effect_kind=core.EffectKind.REFERENCE_MESSAGE,
        allowed_destination_kinds=destination_source,
        allowed_actions=action_source,
        constraints=core.FrozenJsonObject.from_mapping({"network": False}),
    )
    _assert_detached(
        "EffectBoundary.allowed_destination_kinds",
        destination_source,
        detached_boundary.allowed_destination_kinds,
    )
    _assert_detached(
        "EffectBoundary.allowed_actions", action_source, detached_boundary.allowed_actions
    )
    mutation_probe_count += 2

    mandate_sources: tuple[Any, ...] = ([responsibility], [capability], [constraint], [boundary])
    detached_mandate = dataclasses.replace(
        mandate,
        responsibilities=mandate_sources[0],
        capabilities=mandate_sources[1],
        constraints=mandate_sources[2],
        effect_boundaries=mandate_sources[3],
    )
    for field_name, source in zip(
        ("responsibilities", "capabilities", "constraints", "effect_boundaries"),
        mandate_sources,
        strict=True,
    ):
        _assert_detached(f"Mandate.{field_name}", source, getattr(detached_mandate, field_name))
        mutation_probe_count += 1

    responsibility_summaries: Any = ["Responsibility summary"]
    capability_summaries: Any = ["Capability summary"]
    identity_card = core.IdentityCard(
        namespace=namespace,
        profile_id="profile-check",
        profile_revision=1,
        display_name="Check colleague",
        description="Synthetic identity projection.",
        mandate_id=mandate.mandate_id,
        mandate_revision=mandate.revision,
        mission=mandate.mission,
        responsibility_summaries=responsibility_summaries,
        capability_summaries=capability_summaries,
    )
    _assert_detached(
        "IdentityCard.responsibility_summaries",
        responsibility_summaries,
        identity_card.responsibility_summaries,
    )
    _assert_detached(
        "IdentityCard.capability_summaries",
        capability_summaries,
        identity_card.capability_summaries,
    )
    mutation_probe_count += 2

    diff_sources: tuple[Any, ...] = tuple([f"{index}-check"] for index in range(12))
    authority_diff = core.MandateAuthorityDiff(
        namespace=namespace,
        mandate_id=mandate.mandate_id,
        from_revision=1,
        to_revision=2,
        mission_changed=False,
        service_relationship_changed=False,
        working_context_changed=False,
        added_responsibility_ids=diff_sources[0],
        removed_responsibility_ids=diff_sources[1],
        changed_responsibility_ids=diff_sources[2],
        added_capability_ids=diff_sources[3],
        removed_capability_ids=diff_sources[4],
        changed_capability_ids=diff_sources[5],
        added_constraint_ids=diff_sources[6],
        removed_constraint_ids=diff_sources[7],
        changed_constraint_ids=diff_sources[8],
        added_effect_boundary_ids=diff_sources[9],
        removed_effect_boundary_ids=diff_sources[10],
        changed_effect_boundary_ids=diff_sources[11],
    )
    diff_field_names = tuple(
        field.name for field in dataclasses.fields(authority_diff) if field.name.endswith("_ids")
    )
    for field_name, source in zip(diff_field_names, diff_sources, strict=True):
        _assert_detached(
            f"MandateAuthorityDiff.{field_name}", source, getattr(authority_diff, field_name)
        )
        mutation_probe_count += 1

    trigger_source: Any = ["event-check"]
    agenda_source: Any = ["agenda-check"]
    wake = core.WakeCycle(
        namespace=namespace,
        wake_cycle_id="wake-check",
        state=core.WakeCycleState.RUNNING,
        trigger_event_ids=trigger_source,
        agenda_item_ids=agenda_source,
        actor=service,
        correlation_id="correlation-check",
        causation_id="event-check",
        occurred_at=moment,
        revision=1,
    )
    _assert_detached("WakeCycle.trigger_event_ids", trigger_source, wake.trigger_event_ids)
    _assert_detached("WakeCycle.agenda_item_ids", agenda_source, wake.agenda_item_ids)
    mutation_probe_count += 2

    dependency_source: Any = []
    work_responsibility_source: Any = ["responsibility-check"]
    completion_evidence_source: Any = []
    work = core.FiniteWork(
        namespace=namespace,
        work_id="work-check",
        title="Checked finite work",
        description="Synthetic mutable-input probe.",
        state=core.WorkState.PLANNED,
        dependency_ids=dependency_source,
        responsibility_ids=work_responsibility_source,
        assignee_principal_id=model.principal_id,
        actor=human,
        mandate_id=mandate.mandate_id,
        mandate_revision=mandate.revision,
        completion_evidence=completion_evidence_source,
        correlation_id="correlation-check",
        causation_id=None,
        created_at=moment,
        updated_at=moment,
        revision=1,
    )
    for label, source, stored in (
        ("FiniteWork.dependency_ids", dependency_source, work.dependency_ids),
        (
            "FiniteWork.responsibility_ids",
            work_responsibility_source,
            work.responsibility_ids,
        ),
        (
            "FiniteWork.completion_evidence",
            completion_evidence_source,
            work.completion_evidence,
        ),
    ):
        _assert_detached(label, source, stored)
        mutation_probe_count += 1

    resolution_source: Any = []
    obligation = core.Obligation(
        namespace=namespace,
        obligation_id="obligation-check",
        responsibility_id="responsibility-check",
        description="Check a synthetic obligation.",
        state=core.ObligationState.PENDING,
        due_at=None,
        work_id=work.work_id,
        resolution_evidence=resolution_source,
        actor=human,
        correlation_id="correlation-check",
        causation_id=work.work_id,
        created_at=moment,
        updated_at=moment,
        revision=1,
    )
    _assert_detached(
        "Obligation.resolution_evidence", resolution_source, obligation.resolution_evidence
    )
    mutation_probe_count += 1
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
    if (
        proposal.proposal_digest not in serialized_proposal
        or '"proposal_digest"' not in serialized_proposal
    ):
        raise ContractCheckError("public serialization omitted the complete proposal digest")

    return {
        "schema_version": 2,
        "gate": "p2_core_contracts_clean",
        "frozen_dataclass_count": len(public_dataclasses),
        "public_dataclass_count": len(public_dataclasses),
        "enum_count": len(REQUIRED_ENUMS),
        "protocol_count": len(REQUIRED_PROTOCOLS),
        "record_shape_count": len(record_names),
        "mutable_input_probe_count": mutation_probe_count,
        "authoritative_effect_field_mutations_checked": len(complete_effect_mutations) + 1,
        "constraint_negative_cases_checked": len(constraint_cases) + 2,
        "immutability": "passed",
        "namespace": namespace_result,
        "principal_separation": "passed",
        "authority_approval": "passed",
        "complete_effect_binding": "passed",
        "constraint_enforcement": "passed",
        "direct_construction_invariants": "passed",
        "human_approval_requirement": "passed",
        "serialization": serialization_result,
        "effect_payload_redacted": True,
        "complete_effect_digest_exposed": True,
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
