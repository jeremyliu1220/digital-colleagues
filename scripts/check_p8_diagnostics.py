# SPDX-License-Identifier: Apache-2.0

"""Run allowlisted support-bundle and canary redaction gates."""

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


def check_diagnostics(root: Path) -> dict[str, object]:
    tests = run_focused_tests(root, "tests.p8.test_diagnostics")
    return {
        "schema_version": 1,
        "gate": "p8_diagnostics_clean",
        "tests_run": tests,
        "bundle_format_version": 1,
        "archive_members": ["diagnostics.json"],
        "output_policy": "allowlisted_bounded_versioned",
        "safe_causal_identifiers": "purpose_framed_sha256",
        "raw_logs_or_audit_exports": False,
        "database_or_backup_bytes": False,
        "canary_leaks": 0,
        "local_path_leaks": 0,
        "credential_leaks": 0,
        "error_categories": "finite",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P8 diagnostics redaction.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_diagnostics(Path(arguments.root).resolve())
    except (OSError, FocusedGateError) as exc:
        print(f"P8 diagnostics check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
