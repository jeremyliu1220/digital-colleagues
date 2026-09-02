# SPDX-License-Identifier: Apache-2.0

"""Run P6 dispatch-time role/member and retained exact-effect checks."""

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


def check_effect_approval(root: Path) -> dict[str, object]:
    tests = run_focused_tests(
        root,
        "tests.p6.test_effect_audit.P6EffectAuditTests."
        "test_effect_dispatch_revalidates_current_membership_and_expiry",
        "tests.runtime.test_outbox_binding",
    )
    return {
        "schema_version": 1,
        "gate": "p6_effect_approval_clean",
        "tests_run": tests,
        "exact_effect_regression": True,
        "decision_and_dispatch_revalidation": True,
        "role_membership_expiry_binding": True,
        "stale_channel_calls": 0,
        "ambiguous_resend": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P6 exact-effect hardening.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_effect_approval(Path(arguments.root).resolve())
    except (OSError, FocusedGateError) as exc:
        print(f"P6 effect approval check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
