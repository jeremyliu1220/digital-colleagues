# SPDX-License-Identifier: Apache-2.0

"""Run the full P3 unittest suite and record required IDs and fault boundaries."""

from __future__ import annotations

import argparse
import json
import sys
import unittest
from pathlib import Path
from typing import Any, TextIO

REQUIRED_TEST_BOUNDARIES = {
    "tests.architecture.test_p3_boundaries.P3ArchitectureTests.test_adversarial_unknown_import_alias_bypass_and_reverse_dependencies_fail": "architecture_adversarial",
    "tests.persistence.test_sqlite_semantics.SQLiteSemanticsTests.test_migration_order_checksum_tampering_and_future_schema_fail_closed": "migration_identity",
    "tests.persistence.test_sqlite_semantics.SQLiteSemanticsTests.test_migration_failure_rolls_back_without_partial_schema_or_metadata": "migration_atomicity",
    "tests.persistence.test_sqlite_semantics.SQLiteSemanticsTests.test_every_store_connection_enables_wal_foreign_keys_and_busy_handling": "sqlite_pragmas",
    "tests.persistence.test_sqlite_semantics.SQLiteSemanticsTests.test_namespace_isolation_and_atomic_bootstrap_rollback": "namespace_atomicity",
    "tests.persistence.test_sqlite_semantics.SQLiteSemanticsTests.test_trigger_lease_takeover_increments_fence_and_refuses_stale_owner": "lease_fencing",
    "tests.persistence.test_sqlite_semantics.SQLiteSemanticsTests.test_transaction_crash_and_optimistic_revision_conflict_roll_back_atomically": "transaction_revision_atomicity",
    "tests.persistence.test_sqlite_semantics.SQLiteSemanticsTests.test_outbox_lease_takeover_increments_fence_and_refuses_stale_owner": "outbox_lease_fencing",
    "tests.runtime.test_p3_runtime.RuntimeSemanticsTests.test_exact_effect_tampering_and_stale_mandate_never_call_channel": "exact_effect_dispatch",
    "tests.runtime.test_p3_runtime.RuntimeSemanticsTests.test_model_and_service_cannot_construct_or_submit_human_approval": "principal_separation",
    "tests.runtime.test_p3_runtime.RuntimeSemanticsTests.test_retryable_outcome_uses_new_attempt_and_stops_at_success": "bounded_retry",
    "tests.runtime.test_p3_runtime.RuntimeSemanticsTests.test_ambiguous_outcome_requires_reconciliation_before_confirmed_absent_retry": "ambiguity_reconciliation",
    "tests.runtime.test_p3_runtime.RuntimeSemanticsTests.test_crash_after_channel_return_recovers_as_ambiguous_without_redispatch": "crash_dispatch_outcome",
    "tests.runtime.test_p3_runtime.RuntimeSemanticsTests.test_claim_dispatch_and_finalized_crash_checkpoints_recover_without_duplicate_effects": "crash_claim_dispatch_finalize",
    "tests.runtime.test_p3_runtime.RuntimeSemanticsTests.test_generation_interleaving_retains_causes_and_old_checkpoint_cannot_finish_new_cause": "agenda_generation_interleaving",
    "tests.runtime.test_p3_runtime.RuntimeSemanticsTests.test_attention_order_is_deterministic_and_starved_work_advances": "attention_starvation",
    "tests.runtime.test_p3_runtime.RuntimeSemanticsTests.test_wake_cycle_bounds_preserve_pending_work_and_agenda_takeover_fences_stale_owner": "wake_bounds_agenda_fencing",
    "tests.runtime.test_p3_runtime.RuntimeSemanticsTests.test_deterministic_provider_is_byte_equivalent_and_no_pending_work_avoids_call": "deterministic_noop",
    "tests.p3.test_golden_path.GoldenPathTests.test_headless_restart_golden_path_is_recoverable_and_byte_equivalent": "restart_golden_path",
    "tests.api.test_fastapi_edge.FastAPIEdgeTests.test_in_process_mapping_derives_authority_and_rejects_caller_authority_fields": "http_authority_mapping",
    "tests.api.test_fastapi_edge.FastAPIEdgeTests.test_exact_approval_mapping_uses_expected_revision_and_stable_errors": "http_exact_approval",
    "tests.core.test_effects_and_governance.EffectsAndGovernanceTests.test_approval_binds_every_authoritative_effect_field": "p2_effect_field_regression",
}


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
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    expected_failures = len(result.expectedFailures)
    unexpected_successes = len(result.unexpectedSuccesses)
    test_ids = sorted(result.test_ids)
    fault_boundaries = sorted(
        boundary for test_id, boundary in REQUIRED_TEST_BOUNDARIES.items() if test_id in test_ids
    )
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
        "fault_boundaries": fault_boundaries,
    }


def run_suite(suite: unittest.TestSuite, *, stream: TextIO) -> dict[str, Any]:
    result = RecordingRunner(stream=stream, verbosity=2).run(suite)
    assert isinstance(result, RecordingResult)
    return _outcome(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the required P3 unittest suite once.")
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
