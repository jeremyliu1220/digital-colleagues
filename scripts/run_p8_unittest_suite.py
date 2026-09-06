# SPDX-License-Identifier: Apache-2.0

"""Run the complete P8 suite once and record required readiness boundaries."""

from __future__ import annotations

import argparse
import json
import sys
import unittest
from pathlib import Path
from typing import Any, TextIO

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_p7_unittest_suite import REQUIRED_TEST_BOUNDARIES as P7_BOUNDARIES

P8_BOUNDARIES = {
    "tests.p8.test_backup_restore.P8BackupRestoreTests.test_first_release_p7_source_binding_and_cross_version_rollback_are_exact": "p8_first_release_transition_binding",
    "tests.p8.test_backup_restore.P8BackupRestoreTests.test_read_only_database_uri_encodes_reserved_path_characters_without_urllib": "p8_uri_encoding_without_network_namespace",
    "tests.p8.test_backup_restore.P8BackupRestoreTests.test_live_wal_backup_restore_preserves_identity_authority_work_and_causality": "p8_wal_backup_restore_state",
    "tests.p8.test_backup_restore.P8BackupRestoreTests.test_restore_rejects_existing_state_corruption_and_incompatible_manifest": "p8_restore_corruption_manifest_refusal",
    "tests.p8.test_backup_restore.P8BackupRestoreTests.test_archive_path_traversal_symlink_unknown_member_and_future_schema_fail_closed": "p8_archive_and_future_schema_refusal",
    "tests.p8.test_backup_restore.P8BackupRestoreTests.test_backup_output_never_overwrites_and_archive_has_exact_private_members": "p8_private_backup_boundary",
    "tests.p8.test_diagnostics.P8DiagnosticsTests.test_bundle_is_exact_allowlisted_bounded_and_canary_free": "p8_diagnostics_allowlist_redaction",
    "tests.p8.test_diagnostics.P8DiagnosticsTests.test_diagnostics_rejects_unbounded_ids_existing_output_and_path_errors_are_finite": "p8_diagnostics_finite_failure",
    "tests.p8.test_release.P8ReleaseTests.test_supply_chain_is_complete_sorted_hash_pinned_and_notice_scoped": "p8_supply_chain_complete",
    "tests.p8.test_release.P8ReleaseTests.test_nested_npm_package_identities_are_exact_and_scoped_names_survive": "p8_nested_npm_identity",
    "tests.p8.test_release.P8ReleaseTests.test_container_host_toolchain_and_os_dependency_drift_fail_closed": "p8_toolchain_and_os_dependency_drift_refusal",
    "tests.p8.test_release.P8ReleaseTests.test_source_archive_policy_excludes_evidence_and_private_residue": "p8_source_archive_allowlist",
    "tests.p8.test_release.P8ReleaseTests.test_release_builder_refuses_dirty_tree_before_emitting_candidate": "p8_dirty_release_refusal",
    "tests.p8.test_repository.P8RepositoryTests.test_acceptance_historical_migration_and_residue_drift_fail_closed": "p8_history_residue_refusal",
    "tests.p8.test_repository.P8RepositoryTests.test_compose_operation_json_accepts_stderr_and_rejects_missing_results": "p8_compose_operation_result_parsing",
    "tests.p8.test_repository.P8RepositoryTests.test_p8_aggregate_executes_all_prior_current_tree_regressions": "p8_prior_current_tree_regressions",
    "tests.p8.test_repository.P8RepositoryTests.test_studio_evidence_requires_positive_machine_readable_counts": "p8_studio_test_evidence",
    "tests.p8.test_repository.P8RepositoryTests.test_evidence_writer_refuses_dirty_or_incomplete_results": "p8_evidence_fail_closed",
}
REQUIRED_TEST_BOUNDARIES = {**P7_BOUNDARIES, **P8_BOUNDARIES}


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


def outcome(result: RecordingResult) -> dict[str, Any]:
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
        and all(counts[key] == 0 for key in counts if key != "tests_run"),
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
    return outcome(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the complete P8 unittest suite once.")
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
    result = run_suite(suite, stream=sys.stderr)
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if arguments.json_output:
        Path(arguments.json_output).write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0 if result["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
