# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import dataclasses
import unittest
from typing import Any

from digital_colleagues.core import (
    CapabilityGrant,
    IdentityCard,
    MandateAuthorityDiff,
    diff_mandate_authority,
    project_identity_card,
)
from digital_colleagues.core.errors import CoreInvariantError, NamespaceMismatchError
from tests.core.fixtures import mandate, profile


class AuthorityTests(unittest.TestCase):
    def test_profile_change_does_not_change_mandate_authority(self) -> None:
        authority = mandate()
        before_card = project_identity_card(profile(), authority)
        after_card = project_identity_card(
            profile(revision=2, description="Changed descriptive presentation"), authority
        )
        self.assertEqual(before_card.mandate_revision, after_card.mandate_revision)
        self.assertEqual(before_card.mission, after_card.mission)
        self.assertNotEqual(before_card.description, after_card.description)
        self.assertEqual(authority, mandate())

    def test_identity_card_is_a_frozen_one_way_projection(self) -> None:
        card = project_identity_card(profile(), mandate())
        with self.assertRaises(dataclasses.FrozenInstanceError):
            card.mission = "Expanded authority"  # type: ignore[misc]
        self.assertFalse(hasattr(card, "to_mandate"))

    def test_mandate_revision_has_deterministic_authority_diff(self) -> None:
        before = mandate()
        after = mandate(
            revision=2,
            capabilities=(
                *before.capabilities,
                CapabilityGrant(
                    capability_id="capability-summarize",
                    description="Summarize synthetic work.",
                ),
            ),
        )
        change = diff_mandate_authority(before, after)
        self.assertEqual(change.from_revision, 1)
        self.assertEqual(change.to_revision, 2)
        self.assertEqual(change.added_capability_ids, ("capability-summarize",))
        self.assertEqual(change.removed_capability_ids, ())

    def test_authority_diff_rejects_wrong_identity_or_stale_revision(self) -> None:
        before = mandate()
        with self.assertRaises(CoreInvariantError):
            diff_mandate_authority(before, mandate(revision=1))
        with self.assertRaises(NamespaceMismatchError):
            dataclasses.replace(
                mandate(revision=2),
                namespace=before.namespace.__class__.colleague("tenant-beta", "colleague-beta"),
            )

    def test_mandate_nested_collections_are_immutable(self) -> None:
        authority = mandate()
        self.assertIsInstance(authority.responsibilities, tuple)
        self.assertIsInstance(authority.responsibilities[0].obligations, tuple)
        with self.assertRaises(AttributeError):
            authority.capabilities.append(authority.capabilities[0])  # type: ignore[attr-defined]

    def test_identity_card_defensively_copies_mutable_summaries(self) -> None:
        responsibilities = ["Original responsibility"]
        capabilities = ["Original capability"]
        card = IdentityCard(
            namespace=mandate().namespace,
            profile_id="profile-direct",
            profile_revision=1,
            display_name="Direct card",
            description="Direct construction regression fixture.",
            mandate_id="mandate-direct",
            mandate_revision=1,
            mission="Keep direct contracts immutable.",
            responsibility_summaries=responsibilities,  # type: ignore[arg-type]
            capability_summaries=capabilities,  # type: ignore[arg-type]
        )
        responsibilities.append("Injected later")
        capabilities.append("Injected later")
        self.assertEqual(card.responsibility_summaries, ("Original responsibility",))
        self.assertEqual(card.capability_summaries, ("Original capability",))
        with self.assertRaises(CoreInvariantError):
            dataclasses.replace(card, profile_revision=0)

    def test_authority_diff_validates_and_copies_direct_inputs(self) -> None:
        added: Any = ["capability-added"]
        empty: Any = []
        change = MandateAuthorityDiff(
            namespace=mandate().namespace,
            mandate_id="mandate-alpha",
            from_revision=1,
            to_revision=2,
            mission_changed=False,
            service_relationship_changed=False,
            working_context_changed=False,
            added_responsibility_ids=empty,
            removed_responsibility_ids=empty,
            changed_responsibility_ids=empty,
            added_capability_ids=added,
            removed_capability_ids=empty,
            changed_capability_ids=empty,
            added_constraint_ids=empty,
            removed_constraint_ids=empty,
            changed_constraint_ids=empty,
            added_effect_boundary_ids=empty,
            removed_effect_boundary_ids=empty,
            changed_effect_boundary_ids=empty,
        )
        added.append("injected-later")
        self.assertEqual(change.added_capability_ids, ("capability-added",))
        with self.assertRaises(CoreInvariantError):
            dataclasses.replace(change, from_revision=0)
        invalid_bool: Any = 1
        with self.assertRaises(CoreInvariantError):
            dataclasses.replace(change, mission_changed=invalid_bool)
        with self.assertRaises(CoreInvariantError):
            dataclasses.replace(
                change,
                removed_capability_ids=("capability-added",),
            )


if __name__ == "__main__":
    unittest.main()
