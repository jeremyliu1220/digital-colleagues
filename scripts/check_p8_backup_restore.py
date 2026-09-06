# SPDX-License-Identifier: Apache-2.0

"""Run consistent-backup, atomic-restore, corruption, and rollback gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    root_path = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root_path))
    sys.path.insert(0, str(root_path / "src"))

from scripts.p8_gate_support import FocusedGateError, run_focused_tests  # noqa: E402


def check_backup_restore(root: Path) -> dict[str, object]:
    tests = run_focused_tests(root, "tests.p8.test_backup_restore")
    return {
        "schema_version": 1,
        "gate": "p8_backup_restore_clean",
        "tests_run": tests,
        "backup_consistency": "sqlite_online_backup_api_wal_safe",
        "backup_format_version": 1,
        "restore_validation": "format_digest_schema_migration_integrity",
        "replacement": "explicit_offline_atomic_with_private_rollback_backup",
        "failed_migration_rollback": "transactional_retained_p3_p6_evidence",
        "release_rollback": "verified_pre_upgrade_backup_and_matching_code",
        "destructive_down_migration": False,
        "required_state_categories": 16,
        "private_artifacts_emitted": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P8 backup and restore semantics.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_backup_restore(Path(arguments.root).resolve())
    except (OSError, FocusedGateError) as exc:
        print(f"P8 backup/restore check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
