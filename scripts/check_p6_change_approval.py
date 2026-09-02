# SPDX-License-Identifier: Apache-2.0

"""Run the exact two-person P6 governance change Gate."""

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


def check_change_approval(root: Path) -> dict[str, object]:
    tests = run_focused_tests(root, "tests.p6.test_change_approval")
    return {
        "schema_version": 1,
        "gate": "p6_change_approval_clean",
        "tests_run": tests,
        "separate_durable_human_approver": True,
        "exact_revision_digest_base_heads": True,
        "expiry_stale_replay_refused": True,
        "atomic_single_use_apply": True,
        "profile_only_distinction": True,
        "role_elevation_governed": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P6 change approval.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_change_approval(Path(arguments.root).resolve())
    except (OSError, FocusedGateError) as exc:
        print(f"P6 change approval check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
