# SPDX-License-Identifier: Apache-2.0

"""Run the focused persistence, authorization, lease, and outbox P3 contract suite."""

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

TEST_MODULES = (
    "tests.persistence.test_sqlite_semantics",
    "tests.runtime.test_p3_runtime",
)


def main() -> int:
    suite = unittest.TestSuite(
        unittest.defaultTestLoader.loadTestsFromName(name) for name in TEST_MODULES
    )
    stream = io.StringIO()
    outcome = run_suite(suite, stream=stream)
    if not outcome.gate_passed:
        print("P3 persistence check failed", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "schema_version": 1,
                "gate": "p3_persistence_clean",
                "tests_run": outcome.tests_run,
                "failures": outcome.failures,
                "errors": outcome.errors,
                "skipped": outcome.skipped,
                "fault_boundary_count": outcome.tests_run,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
