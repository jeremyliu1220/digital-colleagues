# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast

from digital_colleagues.adapters.sqlite.p4_store import SQLiteP4Store
from digital_colleagues.adapters.sqlite.p5_store import SQLiteP5Store
from digital_colleagues.adapters.system.deterministic import FixedClock
from tests.p5.fixtures import NOW, ROOT


def _schema(connection: sqlite3.Connection) -> dict[str, str]:
    rows = connection.execute(
        """
        SELECT name, sql FROM sqlite_master
        WHERE type IN ('table', 'index') AND name NOT LIKE 'sqlite_%'
        ORDER BY type, name
        """
    ).fetchall()
    return {cast(str, row[0]): cast(str, row[1]) for row in rows}


class P5MigrationTests(unittest.TestCase):
    def test_migration_006_checksum_fresh_and_v5_upgrade_are_identical(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p5-migration-") as name:
            temporary = Path(name)
            v5_migrations = temporary / "v5-migrations"
            v5_migrations.mkdir()
            manifest = cast(
                dict[str, Any],
                json.loads((ROOT / "migrations/manifest.json").read_text(encoding="utf-8")),
            )
            entries = cast(list[dict[str, Any]], manifest["migrations"])
            self.assertGreaterEqual(len(entries), 6)
            self.assertEqual([item["version"] for item in entries[:6]], [1, 2, 3, 4, 5, 6])
            migration = ROOT / "migrations/006_revisioned_colleague_builder.sql"
            checksum = "sha256:" + hashlib.sha256(migration.read_bytes()).hexdigest()
            self.assertEqual(entries[5]["checksum"], checksum)
            for entry in entries[:5]:
                shutil.copy2(ROOT / "migrations" / cast(str, entry["file"]), v5_migrations)
            (v5_migrations / "manifest.json").write_text(
                json.dumps(
                    {"schema_version": 1, "migrations": entries[:5]},
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            p5_migrations = temporary / "p5-migrations"
            p5_migrations.mkdir()
            for entry in entries[:6]:
                shutil.copy2(ROOT / "migrations" / cast(str, entry["file"]), p5_migrations)
            (p5_migrations / "manifest.json").write_text(
                json.dumps(
                    {"schema_version": 1, "migrations": entries[:6]},
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            upgraded_path = temporary / "upgraded.sqlite"
            v5 = SQLiteP4Store(
                upgraded_path,
                migrations_path=v5_migrations,
                clock=FixedClock(NOW),
            )
            self.assertEqual(
                [row[0] for row in v5._connection.execute("SELECT version FROM schema_migrations")],  # noqa: SLF001
                [1, 2, 3, 4, 5],
            )
            v5.close()
            upgraded = SQLiteP5Store(
                upgraded_path,
                migrations_path=p5_migrations,
                clock=FixedClock(NOW),
            )
            fresh = SQLiteP5Store(
                temporary / "fresh.sqlite",
                migrations_path=p5_migrations,
                clock=FixedClock(NOW),
            )
            self.assertEqual(
                _schema(upgraded._connection),  # noqa: SLF001
                _schema(fresh._connection),  # noqa: SLF001
            )
            self.assertEqual(
                [
                    row[0]
                    for row in upgraded._connection.execute(  # noqa: SLF001
                        "SELECT version FROM schema_migrations ORDER BY version"
                    )
                ],
                [1, 2, 3, 4, 5, 6],
            )
            upgraded.close()
            fresh.close()


if __name__ == "__main__":
    unittest.main()
