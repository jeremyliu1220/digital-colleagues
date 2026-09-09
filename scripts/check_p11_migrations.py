# SPDX-License-Identifier: Apache-2.0

"""Verify migration 008 identity, additive shape, schema, and limit enforcement."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from digital_colleagues.adapters.sqlite.p11_store import SQLiteP11Store  # noqa: E402
from digital_colleagues.adapters.system.deterministic import FixedClock  # noqa: E402
from scripts.p11_gate_support import GateError, read_json, sha256_file  # noqa: E402

NOW = datetime(2026, 9, 9, tzinfo=UTC)


def check_migrations(root: Path) -> dict[str, object]:
    manifest = read_json(root / "migrations/manifest.json")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("migrations"), list):
        raise GateError("migration manifest shape is invalid")
    entries = manifest["migrations"]
    if len(entries) != 8:
        raise GateError("P11 requires exactly eight migrations")
    for index, entry in enumerate(entries, start=1):
        if entry.get("version") != index:
            raise GateError("migration order drifted")
        if sha256_file(root / "migrations" / entry["file"]) != entry.get("checksum"):
            raise GateError("migration checksum drifted")
    expected_seven = (
        "sha256:9a9a9c031bd27072333ee30603bcd6c7e2f33f60e7920f3a69ff251836093c02",
        "sha256:b0728e3e910e0f0921271b2121308518945968874a667c340d9dc007cbfea11f",
        "sha256:98325116ff022277aee6ee9038083a3866e912c907d08afeb0da4c48f97d7e98",
        "sha256:dfe550129f32128eadc685cb54b70feed276ceb3274dbcbd76e214053d77e58b",
        "sha256:6649985cf92d9efd378b8b69447357193fdb98eead7d3d23f9bbec1db02b2a61",
        "sha256:7909da4b0b3eb514222f1fd1068c19eb6e8b98d466a786b76c20ae7999e26bcd",
        "sha256:ba572b74ffe7d16ed09ffd58791d7bb23b875806996ec897b2e73c82a593cf9c",
    )
    if tuple(entry["checksum"] for entry in entries[:7]) != expected_seven:
        raise GateError("migration 001-007 prefix drifted")
    eighth = entries[7]
    if (eighth["name"], eighth["file"]) != (
        "agent_packages_and_deployments",
        "008_agent_packages_and_deployments.sql",
    ):
        raise GateError("migration 008 identity is invalid")
    sql = (root / "migrations/008_agent_packages_and_deployments.sql").read_text()
    lowered = sql.lower()
    if any(
        token in lowered
        for token in ("alter table", "drop table", "delete from", "update domain_records")
    ):
        raise GateError("migration 008 is not additive")
    required_tables = {
        "p11_package_versions",
        "p11_package_trust_decisions",
        "p11_deployment_drafts",
        "p11_colleague_deployments",
        "p11_deployment_package_history",
        "p11_operation_replay",
        "p11_causal_audit",
    }
    if any(f"create table {table}" not in lowered for table in required_tables):
        raise GateError("migration 008 table set is incomplete")
    with tempfile.TemporaryDirectory(prefix="dc-p11-migration-") as value:
        store = SQLiteP11Store(
            Path(value) / "state.sqlite",
            migrations_path=root / "migrations",
            clock=FixedClock(NOW),
        )
        version_count = store._connection.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ).fetchone()[0]
        triggers = store._connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'p11_active_limit_%'"
        ).fetchone()[0]
        store.close()
    if version_count != 8 or triggers != 2:
        raise GateError("fresh schema or active-limit trigger result is invalid")
    return {
        "schema_version": 1,
        "gate": "p11_migrations",
        "status": "passed",
        "migration_count": 8,
        "migration_prefix_drift_count": 0,
        "additive_table_count": len(required_tables),
        "active_limit_trigger_count": triggers,
        "fresh_deployment_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        result = check_migrations(Path(args.root).resolve())
    except (OSError, GateError) as exc:
        print(f"P11 migration check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
