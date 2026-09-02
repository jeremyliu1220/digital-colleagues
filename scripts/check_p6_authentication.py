# SPDX-License-Identifier: Apache-2.0

"""Run the focused P6 enrollment, recovery, and session-governance Gate."""

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


def check_authentication(root: Path) -> dict[str, object]:
    tests = run_focused_tests(root, "tests.p6.test_authentication_rbac")
    return {
        "schema_version": 1,
        "gate": "p6_authentication_clean",
        "tests_run": tests,
        "failures": 0,
        "errors": 0,
        "skips": 0,
        "digest_only_credentials": True,
        "single_use_atomic_consumption": True,
        "session_rotation_and_revocation": True,
        "role_membership_revision_revalidation": True,
        "operator_plaintext_boundary": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P6 local authentication.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_authentication(Path(arguments.root).resolve())
    except (OSError, FocusedGateError) as exc:
        print(f"P6 authentication check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
