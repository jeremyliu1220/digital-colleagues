# SPDX-License-Identifier: Apache-2.0

"""Run the isolated P4 authenticated restart Golden Path smoke test."""

from __future__ import annotations

import io
import json
import sys
import unittest
import warnings
from pathlib import Path

if __package__ in {None, ""}:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "src"))

GOLDEN_TEST_ID = (
    "tests.p4.test_studio_golden_path.P4StudioGoldenPathTests."
    "test_authenticated_studio_golden_path_restart_and_causal_chain"
)


def main() -> int:
    warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient`.*")
    suite = unittest.defaultTestLoader.loadTestsFromName(GOLDEN_TEST_ID)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    if not result.wasSuccessful() or result.testsRun != 1:
        print("P4 Golden Path check failed", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "schema_version": 1,
                "gate": "p4_golden_path_clean",
                "golden_test_id": GOLDEN_TEST_ID,
                "tests_run": 1,
                "evidence_class": "synthetic_offline",
                "fresh_instance_restart_recovery": "passed",
                "exact_approval_and_action_result": "passed",
                "causal_chain": "passed",
                "compose_runtime_restart": "not_evaluated_by_this_smoke",
                "five_minute_limit": "not_evaluated",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
