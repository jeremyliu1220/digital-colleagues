# SPDX-License-Identifier: Apache-2.0

"""Run the complete P4 suite and record required regression identities."""

from __future__ import annotations

import argparse
import json
import sys
import unittest
from pathlib import Path
from typing import Any, TextIO

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_p3_unittest_suite import REQUIRED_TEST_BOUNDARIES as P3_BOUNDARIES

P4_BOUNDARIES = {
    "tests.p4.test_authentication.P4AuthenticationTests.test_bootstrap_is_strong_one_time_digest_only_and_operator_retrieval_is_atomic": "p4_bootstrap_single_use_digest",
    "tests.p4.test_authentication.P4AuthenticationTests.test_bootstrap_and_session_expiry_origin_csrf_and_principal_kind_fail_closed": "p4_session_mutation_defenses",
    "tests.p4.test_metrics.P4MetricTests.test_unauthorized_denominator_includes_governance_rejections_and_zero_is_not_applicable": "p4_metric_denominators",
    "tests.p4.test_studio_golden_path.P4StudioGoldenPathTests.test_authenticated_studio_golden_path_restart_and_causal_chain": "p4_authenticated_restart_golden_path",
    "tests.p4.test_studio_golden_path.P4StudioGoldenPathTests.test_timer_noop_metrics_and_reject_create_no_effect_attempt": "p4_timer_noop_reject_metrics",
}
REQUIRED_TEST_BOUNDARIES = {**P3_BOUNDARIES, **P4_BOUNDARIES}


class RecordingResult(unittest.TextTestResult):
    test_ids: list[str]

    def startTestRun(self) -> None:
        self.test_ids = []
        super().startTestRun()

    def startTest(self, test: unittest.case.TestCase) -> None:
        self.test_ids.append(test.id())
        super().startTest(test)


class RecordingRunner(unittest.TextTestRunner):
    resultclass = RecordingResult  # type: ignore[assignment]


def _outcome(result: RecordingResult) -> dict[str, Any]:
    test_ids = sorted(result.test_ids)
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    expected_failures = len(result.expectedFailures)
    unexpected_successes = len(result.unexpectedSuccesses)
    return {
        "tests_run": result.testsRun,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "expected_failures": expected_failures,
        "unexpected_successes": unexpected_successes,
        "gate_passed": (
            result.testsRun > 0
            and failures == 0
            and errors == 0
            and skipped == 0
            and expected_failures == 0
            and unexpected_successes == 0
        ),
        "test_ids": test_ids,
        "fault_boundaries": sorted(
            boundary
            for test_id, boundary in REQUIRED_TEST_BOUNDARIES.items()
            if test_id in test_ids
        ),
    }


def run_suite(suite: unittest.TestSuite, *, stream: TextIO) -> dict[str, Any]:
    result = RecordingRunner(stream=stream, verbosity=2).run(suite)
    assert isinstance(result, RecordingResult)
    return _outcome(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the complete P4 unittest suite once.")
    parser.add_argument("--start-directory", default="tests")
    parser.add_argument("--pattern", default="test*.py")
    parser.add_argument("--top-level-directory")
    parser.add_argument("--json-output")
    arguments = parser.parse_args(argv)
    suite = unittest.defaultTestLoader.discover(
        start_dir=arguments.start_directory,
        pattern=arguments.pattern,
        top_level_dir=arguments.top_level_directory,
    )
    outcome = run_suite(suite, stream=sys.stderr)
    serialized = json.dumps(outcome, indent=2, sort_keys=True) + "\n"
    if arguments.json_output:
        Path(arguments.json_output).write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0 if outcome["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
