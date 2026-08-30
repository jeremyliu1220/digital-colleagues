# SPDX-License-Identifier: Apache-2.0

"""Mechanically inspect the P3 SQLite topology in an OS temporary database."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from digital_colleagues.adapters.sqlite.store import SQLiteRuntimeStore  # noqa: E402
from digital_colleagues.adapters.system.deterministic import FixedClock  # noqa: E402

REQUIRED_NAMESPACED_TABLES = {
    "agenda_runtime",
    "audit_records",
    "domain_records",
    "outbox",
    "replay_ledger",
    "triggers",
    "timer_triggers",
}
REQUIRED_NAMESPACE_COLUMNS = {
    "schema_version",
    "tenant_id",
    "namespace_scope",
    "namespace_scope_id",
}


class MigrationGateError(RuntimeError):
    """The reference topology does not satisfy the P3 migration contract."""


def check_migrations(root: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-migration-gate-") as temporary:
        store = SQLiteRuntimeStore(
            Path(temporary) / "state.sqlite",
            migrations_path=root / "migrations",
            clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)),
        )
        health = store.healthcheck()
        tables = {
            row[0]
            for row in store._connection.execute(  # noqa: SLF001
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if not REQUIRED_NAMESPACED_TABLES.issubset(tables):
            raise MigrationGateError("required namespaced tables are missing")
        for table in REQUIRED_NAMESPACED_TABLES:
            columns = {
                row[1]
                for row in store._connection.execute(  # noqa: SLF001
                    f"PRAGMA table_info({table})"
                )
            }
            if not REQUIRED_NAMESPACE_COLUMNS.issubset(columns):
                raise MigrationGateError("a persisted P3 table lacks complete namespace columns")
        foreign_key_count = sum(
            len(store._connection.execute(f"PRAGMA foreign_key_list({table})").fetchall())  # noqa: SLF001
            for table in REQUIRED_NAMESPACED_TABLES
        )
        versions = [
            row[0]
            for row in store._connection.execute(  # noqa: SLF001
                "SELECT version FROM schema_migrations ORDER BY version"
            )
        ]
        store.close()
    if health["journal_mode"] != "wal" or health["foreign_keys"] is not True:
        raise MigrationGateError("required SQLite pragmas are not enforced")
    if versions != list(range(1, len(versions) + 1)) or foreign_key_count < 1:
        raise MigrationGateError("migration order or foreign-key topology is incomplete")
    return {
        "schema_version": 1,
        "gate": "p3_migrations_clean",
        "migration_count": len(versions),
        "migration_versions": versions,
        "migration_checksums": health["migration_checksums"],
        "namespaced_table_count": len(REQUIRED_NAMESPACED_TABLES),
        "foreign_key_count": foreign_key_count,
        "journal_mode": health["journal_mode"],
        "foreign_keys": health["foreign_keys"],
        "busy_timeout_ms": health["busy_timeout_ms"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P3 migrations and SQLite topology.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_migrations(Path(arguments.root))
    except (OSError, MigrationGateError, RuntimeError) as exc:
        print(f"P3 migration check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
