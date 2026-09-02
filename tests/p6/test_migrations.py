# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast

from digital_colleagues.adapters.sqlite.migrations import MigrationError
from digital_colleagues.adapters.sqlite.p5_store import SQLiteP5Store
from digital_colleagues.adapters.sqlite.p6_store import SQLiteP6Store
from digital_colleagues.adapters.system.deterministic import FixedClock
from tests.p6.fixtures import NOW, ROOT

BASE_COMMIT = "f1dff72c3fb15b2fc7b3c7d989aa85e275cb31ac"


def schema(connection: sqlite3.Connection) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        cast(tuple[str, str, str], tuple(row))
        for row in connection.execute(
            """SELECT type, name, sql FROM sqlite_master
            WHERE type IN ('table', 'index') AND name NOT LIKE 'sqlite_%'
            ORDER BY type, name"""
        )
    )


def copy_migrations(destination: Path, entries: list[dict[str, Any]], *, count: int) -> None:
    destination.mkdir()
    for entry in entries[:count]:
        shutil.copy2(ROOT / "migrations" / cast(str, entry["file"]), destination)
    (destination / "manifest.json").write_text(
        json.dumps({"schema_version": 1, "migrations": entries[:count]}, indent=2) + "\n",
        encoding="utf-8",
    )


class P6MigrationTests(unittest.TestCase):
    def test_migration_007_is_additive_checksummed_and_fresh_equals_v6_upgrade(self) -> None:
        manifest = cast(
            dict[str, Any],
            json.loads((ROOT / "migrations/manifest.json").read_text(encoding="utf-8")),
        )
        entries = cast(list[dict[str, Any]], manifest["migrations"])
        self.assertEqual([entry["version"] for entry in entries], list(range(1, 8)))
        for entry in entries[:6]:
            relative = "migrations/" + cast(str, entry["file"])
            accepted = subprocess.run(
                ["git", "show", f"{BASE_COMMIT}:{relative}"],
                cwd=ROOT,
                check=True,
                capture_output=True,
            ).stdout
            self.assertEqual((ROOT / relative).read_bytes(), accepted)
        migration = ROOT / "migrations/007_governance_hardening.sql"
        digest = "sha256:" + hashlib.sha256(migration.read_bytes()).hexdigest()
        self.assertEqual(entries[6]["checksum"], digest)

        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-migration-") as name:
            temporary = Path(name)
            v6_directory = temporary / "v6"
            copy_migrations(v6_directory, entries, count=6)
            upgraded_path = temporary / "upgraded.sqlite"
            v6 = SQLiteP5Store(upgraded_path, migrations_path=v6_directory, clock=FixedClock(NOW))
            v6.close()
            upgraded = SQLiteP6Store(
                upgraded_path, migrations_path=ROOT / "migrations", clock=FixedClock(NOW)
            )
            fresh = SQLiteP6Store(
                temporary / "fresh.sqlite",
                migrations_path=ROOT / "migrations",
                clock=FixedClock(NOW),
            )
            self.assertEqual(schema(upgraded._connection), schema(fresh._connection))  # noqa: SLF001
            self.assertEqual(
                [
                    row[0]
                    for row in upgraded._connection.execute(  # noqa: SLF001
                        "SELECT version FROM schema_migrations ORDER BY version"
                    )
                ],
                list(range(1, 8)),
            )
            health = fresh.healthcheck()
            self.assertEqual(health["journal_mode"], "wal")
            self.assertTrue(health["foreign_keys"])
            p6_tables = {
                row[0]
                for row in fresh._connection.execute(  # noqa: SLF001
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'p6_%'"
                )
            }
            self.assertEqual(
                p6_tables,
                {
                    "p6_memberships",
                    "p6_bootstrap_transitions",
                    "p6_governance_credentials",
                    "p6_change_proposals",
                    "p6_change_decisions",
                    "p6_effect_approval_bindings",
                    "p6_governance_audit",
                },
            )
            upgraded.close()
            fresh.close()

    def test_failed_007_rolls_back_schema_and_migration_record(self) -> None:
        manifest = cast(
            dict[str, Any],
            json.loads((ROOT / "migrations/manifest.json").read_text(encoding="utf-8")),
        )
        entries = cast(list[dict[str, Any]], manifest["migrations"])
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-rollback-") as name:
            temporary = Path(name)
            v6_directory = temporary / "v6"
            copy_migrations(v6_directory, entries, count=6)
            database = temporary / "state.sqlite"
            v6 = SQLiteP5Store(database, migrations_path=v6_directory, clock=FixedClock(NOW))
            before = schema(v6._connection)  # noqa: SLF001
            v6.close()

            broken_directory = temporary / "broken"
            copy_migrations(broken_directory, entries, count=7)
            broken = (broken_directory / "007_governance_hardening.sql").read_text(
                encoding="utf-8"
            ) + "\nTHIS IS NOT SQL;\n"
            (broken_directory / "007_governance_hardening.sql").write_text(broken, encoding="utf-8")
            broken_entries = cast(
                list[dict[str, Any]],
                cast(
                    dict[str, Any],
                    json.loads((broken_directory / "manifest.json").read_text(encoding="utf-8")),
                )["migrations"],
            )
            broken_entries[6]["checksum"] = (
                "sha256:" + hashlib.sha256(broken.encode("utf-8")).hexdigest()
            )
            (broken_directory / "manifest.json").write_text(
                json.dumps({"schema_version": 1, "migrations": broken_entries}, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(MigrationError):
                SQLiteP6Store(database, migrations_path=broken_directory, clock=FixedClock(NOW))
            connection = sqlite3.connect(database)
            self.assertEqual(schema(connection), before)
            self.assertEqual(
                connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0],
                6,
            )
            connection.close()


if __name__ == "__main__":
    unittest.main()
