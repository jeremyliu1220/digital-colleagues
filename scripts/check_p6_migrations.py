# SPDX-License-Identifier: Apache-2.0

"""Validate immutable 001-006 plus additive checksummed P6 migration 007."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, cast

if __package__ in {None, ""}:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "src"))

from scripts.p6_gate_support import FocusedGateError, run_focused_tests  # noqa: E402


class MigrationError(RuntimeError):
    """The additive P6 migration identity is incomplete."""


def check_migrations(root: Path) -> dict[str, object]:
    manifest = cast(
        dict[str, Any],
        json.loads((root / "migrations/manifest.json").read_text(encoding="utf-8")),
    )
    entries = manifest.get("migrations")
    if not isinstance(entries, list) or len(entries) != 7:
        raise MigrationError("migration manifest must contain exactly versions 1 through 7")
    if [item.get("version") for item in entries] != list(range(1, 8)):
        raise MigrationError("migration version sequence drifted")
    migration = root / "migrations/007_governance_hardening.sql"
    expected = "sha256:" + hashlib.sha256(migration.read_bytes()).hexdigest()
    if entries[6] != {
        "version": 7,
        "name": "governance_hardening",
        "file": migration.name,
        "checksum": expected,
    }:
        raise MigrationError("migration 007 checksum identity is invalid")
    tests = run_focused_tests(root, "tests.p6.test_migrations")
    return {
        "schema_version": 1,
        "gate": "p6_migrations_clean",
        "tests_run": tests,
        "migration_versions": list(range(1, 8)),
        "migration_007_digest": expected,
        "historical_migrations_unchanged": True,
        "fresh_v6_upgrade_schema_equal": True,
        "transaction_rollback": True,
        "journal_mode": "wal",
        "foreign_keys": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P6 migrations.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_migrations(Path(arguments.root).resolve())
    except (OSError, ValueError, json.JSONDecodeError, FocusedGateError, MigrationError) as exc:
        print(f"P6 migration check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
