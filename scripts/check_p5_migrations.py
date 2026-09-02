# SPDX-License-Identifier: Apache-2.0

"""Validate immutable migrations 001-005 and additive P5 migration 006."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

if __package__ in {None, ""}:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "src"))

from digital_colleagues.adapters.sqlite.p4_store import SQLiteP4Store  # noqa: E402
from digital_colleagues.adapters.sqlite.p5_store import SQLiteP5Store  # noqa: E402
from digital_colleagues.adapters.system.deterministic import FixedClock  # noqa: E402
from scripts.check_p5_repository import BASE_COMMIT  # noqa: E402

P5_TABLES = {
    "p5_colleague_drafts",
    "p5_draft_confirmations",
    "p5_draft_audit",
    "p5_policy_outcomes",
    "p5_wake_budget_counters",
    "p5_wake_budget_consumptions",
    "p5_run_states",
    "p5_escalations",
}
NAMESPACE_COLUMNS = {"schema_version", "tenant_id", "namespace_scope", "namespace_scope_id"}


class MigrationError(RuntimeError):
    """P5 migration identity or upgrade topology is invalid."""


def _baseline(root: Path, relative: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{BASE_COMMIT}:{relative}"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise MigrationError("accepted P4 migration inspection failed")
    return completed.stdout


def _schema(connection: sqlite3.Connection) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        cast(tuple[str, str, str], tuple(row))
        for row in connection.execute(
            """
            SELECT type, name, sql FROM sqlite_master
            WHERE type IN ('table', 'index') AND name NOT LIKE 'sqlite_%'
            ORDER BY type, name
            """
        )
    )


def check_migrations(root: Path) -> dict[str, object]:
    for version in range(1, 6):
        matches = tuple((root / "migrations").glob(f"{version:03d}_*.sql"))
        if len(matches) != 1:
            raise MigrationError("an immutable P0-P4 migration identity is missing")
        relative = matches[0].relative_to(root).as_posix()
        if matches[0].read_bytes() != _baseline(root, relative):
            raise MigrationError("an immutable P0-P4 migration changed")
    manifest = cast(
        dict[str, Any],
        json.loads((root / "migrations/manifest.json").read_text(encoding="utf-8")),
    )
    baseline = cast(dict[str, Any], json.loads(_baseline(root, "migrations/manifest.json")))
    entries = manifest.get("migrations")
    if not isinstance(entries, list) or len(entries) < 6:
        raise MigrationError("migration manifest must retain versions 1 through 6")
    if entries[:5] != baseline.get("migrations"):
        raise MigrationError("immutable P0-P4 migration manifest entries changed")
    entry = entries[5]
    migration = root / "migrations/006_revisioned_colleague_builder.sql"
    expected = "sha256:" + hashlib.sha256(migration.read_bytes()).hexdigest()
    if entry != {
        "version": 6,
        "name": "revisioned_colleague_builder",
        "file": migration.name,
        "checksum": expected,
    }:
        raise MigrationError("migration 006 checksum identity is invalid")
    with tempfile.TemporaryDirectory(prefix="digital-colleagues-p5-migrations-") as name:
        temporary = Path(name)
        v5_directory = temporary / "v5"
        v5_directory.mkdir()
        for old in entries[:5]:
            shutil.copy2(root / "migrations" / old["file"], v5_directory)
        (v5_directory / "manifest.json").write_text(
            json.dumps({"schema_version": 1, "migrations": entries[:5]}, indent=2) + "\n",
            encoding="utf-8",
        )
        p5_directory = temporary / "p5"
        p5_directory.mkdir()
        for retained in entries[:6]:
            shutil.copy2(root / "migrations" / retained["file"], p5_directory)
        (p5_directory / "manifest.json").write_text(
            json.dumps({"schema_version": 1, "migrations": entries[:6]}, indent=2) + "\n",
            encoding="utf-8",
        )
        clock = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
        upgraded_path = temporary / "upgrade.sqlite"
        v5_store = SQLiteP4Store(upgraded_path, migrations_path=v5_directory, clock=clock)
        v5_store.close()
        upgraded = SQLiteP5Store(upgraded_path, migrations_path=p5_directory, clock=clock)
        fresh = SQLiteP5Store(temporary / "fresh.sqlite", migrations_path=p5_directory, clock=clock)
        upgraded_schema = _schema(upgraded._connection)  # noqa: SLF001
        fresh_schema = _schema(fresh._connection)  # noqa: SLF001
        versions = [
            row[0]
            for row in upgraded._connection.execute(  # noqa: SLF001
                "SELECT version FROM schema_migrations ORDER BY version"
            )
        ]
        tables = {
            row[0]
            for row in fresh._connection.execute(  # noqa: SLF001
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        for table in P5_TABLES:
            columns = {
                row[1]
                for row in fresh._connection.execute(  # noqa: SLF001
                    f"PRAGMA table_info({table})"
                )
            }
            if not NAMESPACE_COLUMNS.issubset(columns):
                raise MigrationError("a P5 table lacks complete namespace/schema columns")
        health = fresh.healthcheck()
        upgraded.close()
        fresh.close()
    if versions != [1, 2, 3, 4, 5, 6] or upgraded_schema != fresh_schema:
        raise MigrationError("fresh and version-5-upgrade schema identities differ")
    if not P5_TABLES.issubset(tables):
        raise MigrationError("required P5 tables are missing")
    return {
        "schema_version": 1,
        "gate": "p5_migrations_clean",
        "migration_versions": versions,
        "migration_006_checksum": expected,
        "historical_migrations_unchanged": True,
        "fresh_v5_upgrade_schema_equal": True,
        "p5_namespaced_table_count": len(P5_TABLES),
        "journal_mode": health["journal_mode"],
        "foreign_keys": health["foreign_keys"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P5 migrations.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_migrations(Path(arguments.root).resolve())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, MigrationError) as exc:
        print(f"P5 migration check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
