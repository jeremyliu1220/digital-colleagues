# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest
from typing import Any

from scripts.collect_p4_evidence import EvidenceError, validate_unittest
from scripts.run_p4_unittest_suite import REQUIRED_TEST_BOUNDARIES


def passing_outcome() -> dict[str, Any]:
    test_ids = sorted(REQUIRED_TEST_BOUNDARIES)
    return {
        "tests_run": len(test_ids),
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "expected_failures": 0,
        "unexpected_successes": 0,
        "gate_passed": True,
        "test_ids": test_ids,
        "fault_boundaries": sorted(REQUIRED_TEST_BOUNDARIES.values()),
    }


class P4EvidenceGateTests(unittest.TestCase):
    def test_complete_zero_exception_identity_is_accepted(self) -> None:
        outcome = passing_outcome()
        self.assertEqual(validate_unittest(outcome), outcome)

    def test_missing_required_p4_identity_fails_closed(self) -> None:
        outcome = passing_outcome()
        test_ids = list(outcome["test_ids"])
        test_ids.remove(
            "tests.p4.test_studio_golden_path.P4StudioGoldenPathTests."
            "test_authenticated_studio_golden_path_restart_and_causal_chain"
        )
        outcome["test_ids"] = test_ids
        with self.assertRaises(EvidenceError):
            validate_unittest(outcome)

    def test_skip_or_nonzero_failure_cannot_be_evidence(self) -> None:
        for field in ("failures", "errors", "skipped"):
            with self.subTest(field=field):
                outcome = passing_outcome()
                outcome[field] = 1
                outcome["gate_passed"] = False
                with self.assertRaises(EvidenceError):
                    validate_unittest(outcome)


if __name__ == "__main__":
    unittest.main()
