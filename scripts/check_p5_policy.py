# SPDX-License-Identifier: Apache-2.0

"""Run the focused P5 typed-policy enforcement and restart Gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "src"))

from scripts.p5_gate_support import FocusedGateError, run_focused_tests  # noqa: E402


def check_policy(root: Path) -> dict[str, object]:
    tests = run_focused_tests(root, "tests.p5.test_policy")
    return {
        "schema_version": 1,
        "gate": "p5_policy_clean",
        "tests_run": tests,
        "failures": 0,
        "errors": 0,
        "skips": 0,
        "durable_restart_safe_budget": True,
        "duplicate_trigger_evasion_refused": True,
        "unrelated_confirmation_preserves_durable_stop": True,
        "explicit_resume_requires_applicable_exact_policy_revision": True,
        "queued_wake_stopped_before_provider_or_proposal": True,
        "queued_wake_restart_governed_noop": True,
        "stopped_provider_and_channel_call_counts": 0,
        "stale_policy_proposal_refused": True,
        "unauthorized_proposal_escape_target": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P5 policy semantics.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_policy(Path(arguments.root).resolve())
    except (OSError, FocusedGateError) as exc:
        print(f"P5 policy check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
