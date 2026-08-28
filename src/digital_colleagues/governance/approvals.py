# SPDX-License-Identifier: Apache-2.0

"""Fail-closed authority and exact-effect approval policies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from digital_colleagues.core.authority import Mandate
from digital_colleagues.core.common import (
    SCHEMA_VERSION,
    FrozenJsonObject,
    require_digest,
    require_revision,
    require_schema_version,
    require_stable_id,
    require_utc,
)
from digital_colleagues.core.effects import (
    ApprovalChoice,
    EffectProposal,
    EffectProposalState,
    HumanApprovalDecision,
)
from digital_colleagues.core.errors import (
    AuthorizationError,
    CoreInvariantError,
    ReplayError,
    RevisionMismatchError,
)
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import (
    HumanRole,
    Principal,
    PrincipalKind,
    canonical_role_ids,
)


def require_authoritative_human_role(
    principal: Principal,
    *,
    accepted_roles: frozenset[HumanRole],
    caller_supplied_role_ids: tuple[str, ...] = (),
) -> None:
    """Authorize only durable server records and reject caller role assertions."""

    if caller_supplied_role_ids:
        canonical_role_ids(caller_supplied_role_ids)
        raise AuthorizationError("caller-supplied roles are never authoritative")
    if principal.kind is not PrincipalKind.HUMAN:
        raise AuthorizationError("operation requires a durable human principal")
    if accepted_roles.isdisjoint(principal.roles):
        raise AuthorizationError("human principal lacks an authoritative accepted role")


def authorize_effect_proposal(
    proposal: EffectProposal,
    mandate: Mandate,
    *,
    expected_mandate_revision: int,
) -> None:
    """Check a fully specified effect against one exact authoritative Mandate revision."""

    proposal.namespace.require_exact(mandate.namespace)
    if mandate.revision != expected_mandate_revision:
        raise RevisionMismatchError("Mandate revision is stale")
    matching = tuple(
        boundary
        for boundary in mandate.effect_boundaries
        if boundary.boundary_id == proposal.constraints.boundary_id
    )
    if len(matching) != 1:
        raise AuthorizationError("effect does not name one authoritative boundary")
    boundary = matching[0]
    if proposal.effect_kind is not boundary.effect_kind:
        raise AuthorizationError("effect kind is outside the authoritative boundary")
    if proposal.destination.kind not in boundary.allowed_destination_kinds:
        raise AuthorizationError("effect destination is outside the authoritative boundary")
    if proposal.action not in boundary.allowed_actions:
        raise AuthorizationError("effect action is outside the authoritative boundary")
    _authorize_constraint_parameters(proposal.constraints.parameters, boundary.constraints)
    required_state = (
        EffectProposalState.PENDING_APPROVAL
        if boundary.human_approval_required
        else EffectProposalState.APPROVED
    )
    if proposal.state is not required_state:
        raise AuthorizationError("effect state does not satisfy the human approval policy")


_SUPPORTED_CONSTRAINT_TYPES: dict[str, type[object]] = {"network": bool}


def _typed_constraint_values(values: FrozenJsonObject) -> dict[str, object]:
    if len(values) == 0:
        raise AuthorizationError("effect constraints must be explicit")
    typed: dict[str, object] = {}
    for key, value in values.as_entries():
        expected_type = _SUPPORTED_CONSTRAINT_TYPES.get(key)
        if expected_type is None:
            raise AuthorizationError("effect constraint is not recognized")
        if type(value) is not expected_type:
            raise AuthorizationError("effect constraint has the wrong value type")
        typed[key] = value
    return typed


def _authorize_constraint_parameters(
    proposal: FrozenJsonObject, authoritative: FrozenJsonObject
) -> None:
    proposed_values = _typed_constraint_values(proposal)
    authoritative_values = _typed_constraint_values(authoritative)
    if proposed_values.keys() != authoritative_values.keys():
        raise AuthorizationError("effect constraint keys do not match the boundary")
    if any(
        type(proposed_values[key]) is not type(authoritative_values[key])
        or proposed_values[key] != authoritative_values[key]
        for key in authoritative_values
    ):
        raise AuthorizationError("effect constraints conflict with the boundary")


@dataclass(frozen=True, slots=True)
class ApprovalAuthorization:
    namespace: Namespace
    proposal_id: str
    proposal_revision: int
    proposal_payload_digest: str
    proposal_digest: str
    approval_decision_id: str
    author_principal_id: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        if not isinstance(self.namespace, Namespace):
            raise CoreInvariantError("approval authorization namespace must be explicit")
        self.namespace.require_colleague()
        require_stable_id(self.proposal_id, "proposal_id")
        require_revision(self.proposal_revision, "proposal_revision")
        require_digest(self.proposal_payload_digest, "proposal_payload_digest")
        require_digest(self.proposal_digest, "proposal_digest")
        require_stable_id(self.approval_decision_id, "approval_decision_id")
        require_stable_id(self.author_principal_id, "author_principal_id")


def authorize_human_approval(
    proposal: EffectProposal,
    decision: HumanApprovalDecision,
    *,
    evaluated_at: datetime,
    consumed_decision_ids: frozenset[str] = frozenset(),
    consumed_idempotency_keys: frozenset[str] = frozenset(),
    consumed_proposal_revisions: frozenset[tuple[str, int]] = frozenset(),
    accepted_roles: frozenset[HumanRole] = frozenset(
        {HumanRole.TENANT_ADMIN, HumanRole.COLLEAGUE_USER}
    ),
    caller_supplied_role_ids: tuple[str, ...] = (),
) -> ApprovalAuthorization:
    """Bind one human decision to one immutable effect revision exactly once."""

    require_utc(evaluated_at, "evaluated_at")
    proposal.namespace.require_exact(decision.namespace)
    require_authoritative_human_role(
        decision.author,
        accepted_roles=accepted_roles,
        caller_supplied_role_ids=caller_supplied_role_ids,
    )
    if proposal.state is not EffectProposalState.PENDING_APPROVAL:
        raise AuthorizationError("proposal is not awaiting approval")
    if decision.choice is not ApprovalChoice.APPROVE:
        raise AuthorizationError("a rejected proposal cannot be authorized")
    if decision.proposal_id != proposal.proposal_id:
        raise CoreInvariantError("approval references the wrong proposal")
    if decision.proposal_revision != proposal.revision:
        raise RevisionMismatchError("approval references a stale proposal revision")
    if decision.proposal_payload_digest != proposal.payload_digest:
        raise RevisionMismatchError("approval payload binding does not match the proposal")
    if decision.proposal_digest != proposal.proposal_digest:
        raise RevisionMismatchError("approval binding does not match the complete proposal")
    if decision.correlation_id != proposal.correlation_id:
        raise CoreInvariantError("approval correlation does not match the proposal")
    if decision.occurred_at < proposal.occurred_at:
        raise CoreInvariantError("approval cannot precede its proposal")
    if evaluated_at > proposal.constraints.valid_until or evaluated_at > decision.valid_until:
        raise AuthorizationError("approval or proposal validity has expired")
    if decision.approval_decision_id in consumed_decision_ids:
        raise ReplayError("approval decision was already consumed")
    if decision.idempotency_key in consumed_idempotency_keys:
        raise ReplayError("approval idempotency key was already consumed")
    binding = (proposal.proposal_id, proposal.revision)
    if binding in consumed_proposal_revisions:
        raise ReplayError("proposal revision already has a consumed decision")
    return ApprovalAuthorization(
        namespace=proposal.namespace,
        proposal_id=proposal.proposal_id,
        proposal_revision=proposal.revision,
        proposal_payload_digest=proposal.payload_digest,
        proposal_digest=proposal.proposal_digest,
        approval_decision_id=decision.approval_decision_id,
        author_principal_id=decision.author.principal_id,
    )
