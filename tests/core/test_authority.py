# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import dataclasses
import unittest

from digital_colleagues.core import (
    CapabilityGrant,
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


if __name__ == "__main__":
    unittest.main()
