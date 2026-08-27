# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import unittest
from pathlib import Path, PurePosixPath
from typing import Any, ClassVar

from scripts.verify_source_allowlist import ENTRY_FIELDS, validate_manifests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXED_REVISION = "dea9a9accc82fbedd35deb7117dcb5173223cf44"


class SourceAllowlistTests(unittest.TestCase):
    allowlist: ClassVar[dict[str, Any]]
    denylist: ClassVar[dict[str, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.allowlist = json.loads(
            (PROJECT_ROOT / "provenance" / "source-allowlist.json").read_text(encoding="utf-8")
        )
        cls.denylist = json.loads(
            (PROJECT_ROOT / "provenance" / "source-denylist.json").read_text(encoding="utf-8")
        )

    def test_manifest_is_fixed_revision_and_has_expected_count(self) -> None:
        entries = validate_manifests(self.allowlist, self.denylist)
        self.assertEqual(self.allowlist["source_revision"], FIXED_REVISION)
        self.assertEqual(len(entries), 33)

    def test_entries_contain_only_approved_provenance_fields(self) -> None:
        for entry in self.allowlist["entries"]:
            self.assertEqual(set(entry), ENTRY_FIELDS)

    def test_paths_are_relative_files_and_destinations_are_unique(self) -> None:
        destinations: set[str] = set()
        for entry in self.allowlist["entries"]:
            for key in ("source_path", "destination"):
                candidate = PurePosixPath(entry[key])
                self.assertFalse(candidate.is_absolute())
                self.assertNotIn("..", candidate.parts)
                self.assertFalse(entry[key].endswith("/"))
            self.assertNotIn(entry["destination"], destinations)
            destinations.add(entry["destination"])

    def test_every_entry_requires_rights_notice_and_transform_review(self) -> None:
        for entry in self.allowlist["entries"]:
            transform = entry["required_transform"].casefold()
            self.assertIn("rights", transform)
            self.assertIn("notices", transform)
            self.assertTrue(
                entry["classification"].startswith(
                    ("transform_required", "refactor_required", "rewrite_required")
                )
            )

    def test_rights_confirmation_is_conditional_and_migration_is_off(self) -> None:
        record = json.loads(
            (PROJECT_ROOT / "provenance" / "source-rights-confirmation.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(record["source_revision"], FIXED_REVISION)
        self.assertEqual(record["intended_outbound_license"], "Apache-2.0")
        self.assertFalse(record["p0_authorizes_source_migration"])
        self.assertEqual(record["unresolved"], [])


if __name__ == "__main__":
    unittest.main()
