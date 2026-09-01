# SPDX-License-Identifier: Apache-2.0

"""Run the complete P5 suite and record retained plus P5 fault identities."""

from __future__ import annotations

import argparse
import json
import sys
import unittest
from pathlib import Path
from typing import Any, TextIO

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_p4_unittest_suite import REQUIRED_TEST_BOUNDARIES as P4_BOUNDARIES

P5_BOUNDARIES = {
    "tests.p5.test_builder.P5BuilderTests.test_draft_is_inert_defaults_are_explicit_and_exact_confirmation_restarts": "p5_inert_defaults_exact_restart",
    "tests.p5.test_builder.P5BuilderTests.test_same_base_concurrency_is_atomic_and_second_draft_remains_stale": "p5_atomic_concurrent_stale",
    "tests.p5.test_builder.P5BuilderTests.test_terminal_lifecycle_authority_input_and_mutation_guards_fail_closed": "p5_terminal_ambiguous_authority_guards",
    "tests.p5.test_policy.P5PolicyTests.test_working_hours_timezone_overlap_cross_midnight_and_dst_are_deterministic": "p5_working_hours_dst_validation",
    "tests.p5.test_policy.P5PolicyTests.test_budget_is_restart_safe_duplicate_class_cannot_evade_and_stop_requires_revision": "p5_durable_budget_stop_resume",
    "tests.p5.test_policy.P5PolicyTests.test_disallowed_outside_hours_proactivity_notification_and_interruption_are_separate": "p5_trigger_working_hours_proactivity",
    "tests.p5.test_policy.P5PolicyTests.test_finite_stop_blocked_and_repeated_failure_escalations_are_typed": "p5_notification_interruption_typed_stop_escalation",
    "tests.p5.test_policy.P5PolicyTests.test_policy_change_makes_old_proposal_and_context_stale_before_approval_or_dispatch": "p5_stale_policy_proposal_context",
    "tests.p5.test_migrations.P5MigrationTests.test_migration_006_checksum_fresh_and_v5_upgrade_are_identical": "p5_migration_fresh_v5_upgrade",
}
REQUIRED_TEST_BOUNDARIES = {**P4_BOUNDARIES, **P5_BOUNDARIES}


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
    counts = {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "expected_failures": len(result.expectedFailures),
        "unexpected_successes": len(result.unexpectedSuccesses),
    }
    return {
        **counts,
        "gate_passed": counts["tests_run"] > 0
        and all(counts[item] == 0 for item in counts if item != "tests_run"),
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
    parser = argparse.ArgumentParser(description="Run the complete P5 unittest suite once.")
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
