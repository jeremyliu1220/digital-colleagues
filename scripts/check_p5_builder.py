# SPDX-License-Identifier: Apache-2.0

"""Run the focused P5 revisioned-builder lifecycle and authority Gate."""

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


def check_builder(root: Path) -> dict[str, object]:
    tests = run_focused_tests(root, "tests.p5.test_builder")
    return {
        "schema_version": 1,
        "gate": "p5_builder_clean",
        "tests_run": tests,
        "failures": 0,
        "errors": 0,
        "skips": 0,
        "exact_confirmation": True,
        "stale_concurrency": True,
        "atomic_apply": True,
        "ambiguous_authority_refused": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P5 builder semantics.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_builder(Path(arguments.root).resolve())
    except (OSError, FocusedGateError) as exc:
        print(f"P5 builder check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
