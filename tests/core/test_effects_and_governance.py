# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import dataclasses
import unittest
from datetime import datetime
from typing import Any

from digital_colleagues.core import (
    ApprovalChoice,
    EffectConstraints,
    EffectDestination,
    EffectKind,
    EffectProposal,
    EffectProposalState,
    HumanRole,
    Namespace,
    to_canonical_json,
)
from digital_colleagues.core.errors import (
    AuthorizationError,
    CoreInvariantError,
    NamespaceMismatchError,
    ReplayError,
    RevisionMismatchError,
)
from digital_colleagues.governance import (
    ApprovalAuthorization,
    authorize_effect_proposal,
    authorize_human_approval,
    require_authoritative_human_role,
)
from tests.core.fixtures import (
    EXPIRY,
    T4,
    T5,
    approval_decision,
    colleague_namespace,
    effect_proposal,
    frozen,
    human_user,
    mandate,
    model_principal,
    other_namespace,
    service_principal,
)


class EffectsAndGovernanceTests(unittest.TestCase):
    def test_effect_must_be_fully_specified(self) -> None:
        with self.assertRaises(CoreInvariantError):
            EffectProposal(
                namespace=colleague_namespace(),
                proposal_id="proposal-empty",
                decision_id="decision-001",
                effect_kind=EffectKind.REFERENCE_MESSAGE,
                destination=EffectDestination(kind="reference-channel", target="target"),
                action="deliver",
                payload=frozen({}),
                safe_projection=frozen({"summary": "Synthetic effect"}),
                constraints=EffectConstraints(
                    boundary_id="boundary-reference-message",
                    idempotency_key="effect-key-empty",
                    valid_until=EXPIRY,
                    maximum_attempts=1,
                    parameters=frozen({"network": False}),
                ),
                state=EffectProposalState.PENDING_APPROVAL,
                actor=model_principal(),
                correlation_id="correlation-001",
                causation_id="decision-001",
                occurred_at=T4,
                revision=1,
            )

    def test_public_serialization_excludes_sensitive_payload(self) -> None:
        serialized = to_canonical_json(effect_proposal())
        self.assertNotIn("sensitive-body-value", serialized)
        self.assertNotIn('"payload"', serialized)
        self.assertIn('"payload_digest"', serialized)
        self.assertIn('"proposal_digest"', serialized)
        self.assertIn("One synthetic reference message", serialized)

    def test_model_and_service_cannot_author_human_approval(self) -> None:
        proposal = effect_proposal()
        for author in (model_principal(), service_principal()):
            with self.subTest(kind=author.kind):
                with self.assertRaises(AuthorizationError):
                    approval_decision(proposal, author=author)

    def test_authorization_binds_exact_proposal_revision_and_payload(self) -> None:
        proposal = effect_proposal()
        decision = approval_decision(proposal)
        authorization = authorize_human_approval(
            proposal,
            decision,
            evaluated_at=T5,
        )
        self.assertEqual(authorization.proposal_revision, proposal.revision)
        self.assertEqual(authorization.proposal_payload_digest, proposal.payload_digest)
        self.assertEqual(authorization.proposal_digest, proposal.proposal_digest)
        self.assertEqual(decision.proposal_digest, proposal.proposal_digest)
        self.assertEqual(authorization.author_principal_id, human_user().principal_id)

    def test_stale_revision_and_wrong_proposal_are_rejected(self) -> None:
        proposal = effect_proposal(revision=2)
        stale = approval_decision(proposal, proposal_revision=1)
        with self.assertRaises(RevisionMismatchError):
            authorize_human_approval(proposal, stale, evaluated_at=T5)

        wrong = approval_decision(proposal, proposal_id="proposal-other")
        with self.assertRaises(CoreInvariantError):
            authorize_human_approval(proposal, wrong, evaluated_at=T5)

    def test_cross_namespace_approval_is_rejected(self) -> None:
        proposal = effect_proposal()
        with self.assertRaises(NamespaceMismatchError):
            dataclasses.replace(approval_decision(proposal), namespace=other_namespace())

    def test_replayed_decision_key_or_proposal_revision_is_rejected(self) -> None:
        proposal = effect_proposal()
        decision = approval_decision(proposal)
        with self.assertRaises(ReplayError):
            authorize_human_approval(
                proposal,
                decision,
                evaluated_at=T5,
                consumed_decision_ids=frozenset({decision.approval_decision_id}),
            )
        with self.assertRaises(ReplayError):
            authorize_human_approval(
                proposal,
                decision,
                evaluated_at=T5,
                consumed_idempotency_keys=frozenset({decision.idempotency_key}),
            )
        with self.assertRaises(ReplayError):
            authorize_human_approval(
                proposal,
                decision,
                evaluated_at=T5,
                consumed_proposal_revisions=frozenset({(proposal.proposal_id, proposal.revision)}),
            )

    def test_expired_decision_is_rejected_with_injected_time(self) -> None:
        proposal = effect_proposal()
        with self.assertRaises(AuthorizationError):
            authorize_human_approval(
                proposal,
                approval_decision(proposal),
                evaluated_at=EXPIRY.replace(hour=EXPIRY.hour + 1),
            )

    def test_rejection_decision_cannot_authorize_an_effect(self) -> None:
        proposal = effect_proposal()
        rejected = dataclasses.replace(
            approval_decision(proposal),
            choice=ApprovalChoice.REJECT,
        )
        with self.assertRaises(AuthorizationError):
            authorize_human_approval(proposal, rejected, evaluated_at=T5)

    def test_caller_supplied_role_never_becomes_authority(self) -> None:
        with self.assertRaises(AuthorizationError):
            require_authoritative_human_role(
                human_user(),
                accepted_roles=frozenset({HumanRole.TENANT_ADMIN}),
                caller_supplied_role_ids=("tenant_admin",),
            )

    def test_effect_policy_uses_exact_mandate_boundary_and_revision(self) -> None:
        proposal = effect_proposal()
        authorize_effect_proposal(proposal, mandate(), expected_mandate_revision=1)
        with self.assertRaises(RevisionMismatchError):
            authorize_effect_proposal(proposal, mandate(), expected_mandate_revision=2)
        wrong_action = dataclasses.replace(proposal, action="delete")
        with self.assertRaises(AuthorizationError):
            authorize_effect_proposal(wrong_action, mandate(), expected_mandate_revision=1)

    def test_effect_boundary_constraints_are_typed_exact_and_fail_closed(self) -> None:
        proposal = effect_proposal()
        authoritative = mandate()
        authorize_effect_proposal(proposal, authoritative, expected_mandate_revision=1)

        boundary = authoritative.effect_boundaries[0]
        cases = {
            "boolean conflict": (
                dataclasses.replace(
                    proposal,
                    constraints=dataclasses.replace(
                        proposal.constraints,
                        parameters=frozen({"network": True}),
                    ),
                ),
                authoritative,
            ),
            "missing constraint": (
                dataclasses.replace(
                    proposal,
                    constraints=dataclasses.replace(
                        proposal.constraints,
                        parameters=frozen({}),
                    ),
                ),
                authoritative,
            ),
            "extra constraint": (
                dataclasses.replace(
                    proposal,
                    constraints=dataclasses.replace(
                        proposal.constraints,
                        parameters=frozen({"network": False, "unknown": False}),
                    ),
                ),
                authoritative,
            ),
            "lookalike wrong type": (
                dataclasses.replace(
                    proposal,
                    constraints=dataclasses.replace(
                        proposal.constraints,
                        parameters=frozen({"network": 0}),
                    ),
                ),
                authoritative,
            ),
            "unknown authoritative constraint": (
                proposal,
                dataclasses.replace(
                    authoritative,
                    effect_boundaries=(
                        dataclasses.replace(
                            boundary,
                            constraints=frozen({"unknown": False}),
                        ),
                    ),
                ),
            ),
        }
        for label, (candidate, candidate_mandate) in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(AuthorizationError):
                    authorize_effect_proposal(
                        candidate,
                        candidate_mandate,
                        expected_mandate_revision=1,
                    )

    def test_human_approval_requirement_changes_effect_policy_outcome(self) -> None:
        proposal = effect_proposal()
        authoritative = mandate()
        boundary = authoritative.effect_boundaries[0]
        with self.assertRaises(AuthorizationError):
            authorize_effect_proposal(
                dataclasses.replace(proposal, state=EffectProposalState.APPROVED),
                authoritative,
                expected_mandate_revision=1,
            )

        no_human_boundary = dataclasses.replace(boundary, human_approval_required=False)
        no_human_mandate = dataclasses.replace(
            authoritative,
            effect_boundaries=(no_human_boundary,),
        )
        with self.assertRaises(AuthorizationError):
            authorize_effect_proposal(
                proposal,
                no_human_mandate,
                expected_mandate_revision=1,
            )
        authorize_effect_proposal(
            dataclasses.replace(proposal, state=EffectProposalState.APPROVED),
            no_human_mandate,
            expected_mandate_revision=1,
        )

    def test_non_utc_approval_time_is_rejected(self) -> None:
        proposal = effect_proposal()
        naive = datetime(2026, 1, 2, 3, 9)
        with self.assertRaises(CoreInvariantError):
            authorize_human_approval(
                proposal,
                approval_decision(proposal),
                evaluated_at=naive,
            )

    def test_approval_payload_binding_cannot_be_rewritten_after_approval(self) -> None:
        proposal = effect_proposal()
        decision = approval_decision(proposal)
        changed_payload = dataclasses.replace(
            proposal,
            payload=frozen({"body": "different-body", "format": "plain"}),
        )
        self.assertNotEqual(changed_payload.payload_digest, proposal.payload_digest)
        with self.assertRaises(RevisionMismatchError):
            authorize_human_approval(changed_payload, decision, evaluated_at=T5)

    def test_approval_binds_every_authoritative_effect_field(self) -> None:
        proposal = effect_proposal()
        decision = approval_decision(proposal)
        other_actor = type(proposal.actor).model(
            tenant_id="tenant-alpha",
            principal_id="principal-model-other",
        )
        constraint_replacements: dict[str, dict[str, Any]] = {
            "boundary ID": {"boundary_id": "boundary-other"},
            "idempotency key": {"idempotency_key": "effect-key-other"},
            "valid-until": {"valid_until": EXPIRY.replace(minute=EXPIRY.minute + 1)},
            "maximum attempts": {"maximum_attempts": 2},
            "constraint parameters": {"parameters": frozen({"network": True})},
        }
        candidates = {
            "destination target": dataclasses.replace(
                proposal,
                destination=dataclasses.replace(proposal.destination, target="different-target"),
            ),
            "destination kind": dataclasses.replace(
                proposal,
                destination=dataclasses.replace(proposal.destination, kind="other-channel"),
            ),
            "action": dataclasses.replace(proposal, action="archive"),
            "effect kind": dataclasses.replace(
                proposal,
                effect_kind=EffectKind.INTERNAL_RECORD,
            ),
            "payload": dataclasses.replace(
                proposal,
                payload=frozen({"body": "different-body", "format": "plain"}),
            ),
            "safe projection": dataclasses.replace(
                proposal,
                safe_projection=frozen({"summary": "Different safe projection"}),
            ),
            "actor identity": dataclasses.replace(proposal, actor=other_actor),
            "occurred-at": dataclasses.replace(
                proposal,
                occurred_at=proposal.occurred_at.replace(second=proposal.occurred_at.second + 1),
            ),
        }
        for label, changes in constraint_replacements.items():
            candidates[label] = dataclasses.replace(
                proposal,
                constraints=dataclasses.replace(proposal.constraints, **changes),
            )
        for label, candidate in candidates.items():
            with self.subTest(label=label):
                self.assertNotEqual(candidate.proposal_digest, proposal.proposal_digest)
                with self.assertRaises(RevisionMismatchError):
                    authorize_human_approval(candidate, decision, evaluated_at=T5)

        with self.assertRaises(RevisionMismatchError):
            authorize_human_approval(
                dataclasses.replace(proposal, revision=2),
                decision,
                evaluated_at=T5,
            )
        other_namespace_proposal = dataclasses.replace(
            proposal,
            namespace=Namespace.colleague("tenant-beta", "colleague-beta"),
            actor=type(proposal.actor).model(
                tenant_id="tenant-beta",
                principal_id="principal-model-beta",
            ),
        )
        with self.assertRaises(NamespaceMismatchError):
            authorize_human_approval(other_namespace_proposal, decision, evaluated_at=T5)

    def test_invalid_approval_authorization_cannot_be_constructed(self) -> None:
        proposal = effect_proposal()
        authorization = authorize_human_approval(
            proposal,
            approval_decision(proposal),
            evaluated_at=T5,
        )
        invalid_values: dict[str, Any] = {
            "proposal_id": "",
            "proposal_revision": 0,
            "proposal_payload_digest": "not-a-digest",
            "proposal_digest": "sha256:not-a-digest",
            "approval_decision_id": "",
            "author_principal_id": "",
            "schema_version": 0,
            "namespace": Namespace.tenant("tenant-alpha"),
        }
        for field_name, invalid in invalid_values.items():
            with self.subTest(field=field_name):
                with self.assertRaises(CoreInvariantError):
                    dataclasses.replace(authorization, **{field_name: invalid})

        with self.assertRaises(CoreInvariantError):
            ApprovalAuthorization(
                namespace=colleague_namespace(),
                proposal_id="",
                proposal_revision=0,
                proposal_payload_digest="invalid",
                proposal_digest="invalid",
                approval_decision_id="",
                author_principal_id="",
            )


if __name__ == "__main__":
    unittest.main()
