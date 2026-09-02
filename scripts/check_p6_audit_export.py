# SPDX-License-Identifier: Apache-2.0

"""Run the authorized, bounded, redacted P6 audit-export Gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "src"))

from scripts.p6_gate_support import FocusedGateError, run_focused_tests  # noqa: E402


def check_audit_export(root: Path) -> dict[str, object]:
    tests = run_focused_tests(
        root,
        "tests.p6.test_effect_audit.P6EffectAuditTests."
        "test_audit_export_is_scoped_bounded_redacted_authorized_and_restart_stable",
    )
    return {
        "schema_version": 1,
        "gate": "p6_audit_export_clean",
        "tests_run": tests,
        "admin_and_auditor_authorized": True,
        "colleague_user_refused": True,
        "deterministic_ordering": [
            "occurred_at",
            "record_type",
            "record_id",
            "record_revision",
        ],
        "maximum_records": 500,
        "private_payload_redacted": True,
        "recursive_export_refused": True,
        "restart_stable": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P6 audit export.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_audit_export(Path(arguments.root).resolve())
    except (OSError, FocusedGateError) as exc:
        print(f"P6 audit export check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
