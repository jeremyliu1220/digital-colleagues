# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import dataclasses
import unittest
from datetime import datetime

from digital_colleagues.core import (
    EffectConstraints,
    EffectDestination,
    EffectKind,
    EffectProposal,
    EffectProposalState,
    HumanRole,
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


if __name__ == "__main__":
    unittest.main()
