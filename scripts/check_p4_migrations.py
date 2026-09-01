# SPDX-License-Identifier: Apache-2.0

"""Validate immutable prior migrations and the additive namespaced P4 schema."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

if __package__ in {None, ""}:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "src"))

from digital_colleagues.adapters.sqlite.p4_store import SQLiteP4Store  # noqa: E402
from digital_colleagues.adapters.system.deterministic import FixedClock  # noqa: E402
from scripts.check_p4_repository import BASE_COMMIT  # noqa: E402

P4_TABLES = {
    "p4_bootstrap_credentials",
    "p4_sessions",
    "p4_mutation_replay",
    "p4_metric_observations",
    "p4_proposal_candidate_observations",
}
NAMESPACE_COLUMNS = {"schema_version", "tenant_id", "namespace_scope", "namespace_scope_id"}


class MigrationError(RuntimeError):
    """P4 migration identity or topology is invalid."""


def _baseline(root: Path, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{BASE_COMMIT}:{path}"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise MigrationError("historical migration inspection failed")
    return completed.stdout


def check_migrations(root: Path) -> dict[str, object]:
    for filename in ("001_initial.sql", "002_runtime_indexes.sql", "003_timer_triggers.sql"):
        path = f"migrations/{filename}"
        if (root / path).read_bytes() != _baseline(root, path):
            raise MigrationError("a historical migration changed")
    manifest = json.loads((root / "migrations/manifest.json").read_text(encoding="utf-8"))
    baseline_manifest = json.loads(_baseline(root, "migrations/manifest.json"))
    entries = manifest.get("migrations") if isinstance(manifest, dict) else None
    if not isinstance(entries, list) or [item.get("version") for item in entries[:5]] != [
        1,
        2,
        3,
        4,
        5,
    ]:
        raise MigrationError("migration manifest lacks the immutable P4 prefix")
    if not isinstance(baseline_manifest, dict) or entries[:3] != baseline_manifest.get(
        "migrations"
    ):
        raise MigrationError("historical migration manifest entries changed")
    migration_004 = root / "migrations/004_local_authentication.sql"
    migration_005 = root / "migrations/005_evaluation_observations.sql"
    expected_004 = "sha256:" + hashlib.sha256(migration_004.read_bytes()).hexdigest()
    expected_005 = "sha256:" + hashlib.sha256(migration_005.read_bytes()).hexdigest()
    if entries[3].get("file") != migration_004.name or entries[3].get("checksum") != expected_004:
        raise MigrationError("migration 004 checksum identity is invalid")
    if entries[4].get("file") != migration_005.name or entries[4].get("checksum") != expected_005:
        raise MigrationError("migration 005 checksum identity is invalid")
    with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-migrations-") as temporary:
        store = SQLiteP4Store(
            Path(temporary) / "state.sqlite",
            migrations_path=root / "migrations",
            clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)),
        )
        applied_versions = [
            row[0]
            for row in store._connection.execute(  # noqa: SLF001
                "SELECT version FROM schema_migrations ORDER BY version"
            )
        ]
        tables = {
            row[0]
            for row in store._connection.execute(  # noqa: SLF001
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if not P4_TABLES.issubset(tables):
            raise MigrationError("required P4 tables are missing")
        for table in P4_TABLES:
            columns = {
                row[1]
                for row in store._connection.execute(  # noqa: SLF001
                    f"PRAGMA table_info({table})"
                )
            }
            if not NAMESPACE_COLUMNS.issubset(columns):
                raise MigrationError("a P4 table lacks full namespace and schema columns")
        health = store.healthcheck()
        store.close()
    if applied_versions[:5] != [1, 2, 3, 4, 5]:
        raise MigrationError("applied migration versions are invalid")
    return {
        "schema_version": 1,
        "gate": "p4_migrations_clean",
        "migration_versions": [1, 2, 3, 4, 5],
        "migration_004_checksum": expected_004,
        "migration_005_checksum": expected_005,
        "historical_migrations_unchanged": True,
        "p4_namespaced_table_count": len(P4_TABLES),
        "journal_mode": health["journal_mode"],
        "foreign_keys": health["foreign_keys"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P4 migrations.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_migrations(Path(arguments.root).resolve())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, MigrationError) as exc:
        print(f"P4 migration check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
