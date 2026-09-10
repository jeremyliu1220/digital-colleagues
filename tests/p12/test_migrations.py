# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest
from pathlib import Path

from scripts.check_p12_migrations import (
    MANIFEST,
    MIGRATIONS,
    OWNERS,
    check_migrations,
    validate_owner_map,
)
from scripts.check_p12_repository import P12GateError

ROOT = Path(__file__).resolve().parents[2]


class MigrationTests(unittest.TestCase):
    def test_exact_current_migration_gate_passes(self) -> None:
        result = check_migrations(ROOT)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["migration_change_count"], 0)

    def test_manifest_identity_is_exact(self) -> None:
        self.assertEqual(MANIFEST[1], "bfd142486041029bfcc1106ef6ffd4aeb125ed36")
        self.assertEqual(len(MANIFEST[2]), 64)

    def test_migrations_one_through_eight_are_exact(self) -> None:
        self.assertEqual(len(MIGRATIONS), 8)
        self.assertEqual(
            [row[0][:3] for row in MIGRATIONS], [f"{value:03d}" for value in range(1, 9)]
        )

    def test_future_owners_are_exact(self) -> None:
        validate_owner_map(dict(OWNERS))
        self.assertEqual(
            OWNERS,
            {
                "009": "P13",
                "010": "P14",
                "011": "P15",
                "012": "P16",
                "013": "P17",
                "014": "P18",
                "015": "No owner",
            },
        )

    def test_migration_009_owner_drift_fails_closed(self) -> None:
        owners = dict(OWNERS)
        owners["009"] = "P12"
        with self.assertRaises(P12GateError):
            validate_owner_map(owners)

    def test_migration_011_owner_drift_fails_closed(self) -> None:
        owners = dict(OWNERS)
        owners["011"] = "P17"
        with self.assertRaises(P12GateError):
            validate_owner_map(owners)

    def test_migration_012_owner_drift_fails_closed(self) -> None:
        owners = dict(OWNERS)
        owners["012"] = "P15"
        with self.assertRaises(P12GateError):
            validate_owner_map(owners)

    def test_migration_013_owner_drift_fails_closed(self) -> None:
        owners = dict(OWNERS)
        owners["013"] = "P14"
        with self.assertRaises(P12GateError):
            validate_owner_map(owners)

    def test_migration_014_owner_drift_fails_closed(self) -> None:
        owners = dict(OWNERS)
        owners["014"] = "P19"
        with self.assertRaises(P12GateError):
            validate_owner_map(owners)

    def test_migration_015_cannot_gain_an_owner(self) -> None:
        owners = dict(OWNERS)
        owners["015"] = "P20"
        with self.assertRaises(P12GateError):
            validate_owner_map(owners)


if __name__ == "__main__":
    unittest.main()
