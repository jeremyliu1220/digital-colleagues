# SPDX-License-Identifier: Apache-2.0

"""Run the synthetic headless restart Golden Path as a focused gate."""

from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "src"))

from scripts.run_unittest_suite import run_suite  # noqa: E402

GOLDEN_TEST_ID = (
    "tests.p3.test_golden_path.GoldenPathTests."
    "test_headless_restart_golden_path_is_recoverable_and_byte_equivalent"
)


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromName(GOLDEN_TEST_ID)
    stream = io.StringIO()
    outcome = run_suite(suite, stream=stream)
    if not outcome.gate_passed or outcome.tests_run != 1:
        print("P3 Golden Path check failed", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "schema_version": 1,
                "gate": "p3_golden_path_clean",
                "golden_test_id": GOLDEN_TEST_ID,
                "tests_run": outcome.tests_run,
                "restart_recovery": "passed",
                "replay_suppression": "passed",
                "byte_equivalence": "passed",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
