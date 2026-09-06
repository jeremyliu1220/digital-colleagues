# SPDX-License-Identifier: Apache-2.0

"""Validate documented P8 operator commands, safety boundaries, and rollback semantics."""

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

REQUIRED_DOCUMENTS = (
    "docs/p8/acceptance.md",
    "docs/p8/operations.md",
    "docs/p8/release-checklist.md",
    "docs/p8/release-golden-path.md",
)
REQUIRED_OPERATION_TERMS = (
    "online backup API",
    "WAL",
    "0600",
    "atomic replacement",
    "pre-upgrade",
    "down-migration",
    "session",
    "credential",
    "approval",
    "authority",
)


def check_operations(root: Path) -> dict[str, object]:
    for relative in REQUIRED_DOCUMENTS:
        if not (root / relative).is_file():
            raise FocusedGateError("a required P8 operations document is missing")
    operations = (root / "docs/p8/operations.md").read_text(encoding="utf-8")
    if any(term not in operations for term in REQUIRED_OPERATION_TERMS):
        raise FocusedGateError("P8 operator safety semantics are incomplete")
    tests = run_focused_tests(
        root,
        "tests.p8.test_backup_restore",
        "tests.p8.test_diagnostics",
    )
    return {
        "schema_version": 1,
        "gate": "p8_operations_clean",
        "tests_run": tests,
        "document_count": len(REQUIRED_DOCUMENTS),
        "upgrade": "verify_backup_stop_start_health_smoke",
        "rollback": "restore_verified_pre_upgrade_backup_with_matching_code",
        "destructive_down_migration": False,
        "private_backup_boundary": True,
        "restored_authority_requires_revalidation": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P8 operator readiness.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_operations(Path(arguments.root).resolve())
    except (OSError, UnicodeError, FocusedGateError) as exc:
        print(f"P8 operations check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
