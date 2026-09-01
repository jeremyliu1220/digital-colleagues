# SPDX-License-Identifier: Apache-2.0

"""Run the in-process authenticated P5 builder and policy Golden Path."""

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


def check_golden_path(root: Path) -> dict[str, object]:
    tests = run_focused_tests(
        root,
        "tests.p5.test_builder.P5BuilderTests.test_draft_is_inert_defaults_are_explicit_and_exact_confirmation_restarts",
        "tests.p5.test_builder.P5BuilderTests.test_same_base_concurrency_is_atomic_and_second_draft_remains_stale",
        "tests.p5.test_policy.P5PolicyTests.test_budget_is_restart_safe_duplicate_class_cannot_evade_and_stop_requires_revision",
        "tests.p5.test_policy.P5PolicyTests.test_policy_change_makes_old_proposal_and_context_stale_before_approval_or_dispatch",
    )
    return {
        "schema_version": 1,
        "gate": "p5_in_process_golden_path_clean",
        "tests_run": tests,
        "failures": 0,
        "errors": 0,
        "skips": 0,
        "fresh_builder_restart": True,
        "stale_draft_fault": "refused_and_persisted",
        "stale_proposal_fault": "refused_before_approval_dispatch",
        "evidence_class": "synthetic_offline",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the P5 in-process Golden Path.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_golden_path(Path(arguments.root).resolve())
    except (OSError, FocusedGateError) as exc:
        print(f"P5 Golden Path failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
