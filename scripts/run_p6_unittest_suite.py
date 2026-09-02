# SPDX-License-Identifier: Apache-2.0

"""Run the complete P6 suite once and record required security fault identities."""

from __future__ import annotations

import argparse
import json
import sys
import unittest
from pathlib import Path
from typing import Any, TextIO

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_p5_unittest_suite import REQUIRED_TEST_BOUNDARIES as P5_BOUNDARIES

P6_BOUNDARIES = {
    "tests.p6.test_authentication_rbac.P6AuthenticationRbacTests.test_second_admin_transition_is_single_use_and_credentials_are_digest_only": "p6_second_admin_digest_single_use",
    "tests.p6.test_authentication_rbac.P6AuthenticationRbacTests.test_scoped_roles_matrix_api_authority_injection_and_idor_fail_closed": "p6_rbac_namespace_authority_injection",
    "tests.p6.test_authentication_rbac.P6AuthenticationRbacTests.test_scoped_auditor_projection_excludes_tenant_and_other_colleague_metadata": "p6_scoped_auditor_projection_refusal",
    "tests.p6.test_authentication_rbac.P6AuthenticationRbacTests.test_browser_credential_replay_is_canonical_and_restart_durable": "p6_browser_credential_replay_restart",
    "tests.p6.test_authentication_rbac.P6AuthenticationRbacTests.test_direct_credential_replay_ignores_server_time_and_concurrent_retry": "p6_direct_credential_time_concurrent_replay",
    "tests.p6.test_authentication_rbac.P6AuthenticationRbacTests.test_active_colleague_and_revoke_browser_mutations_are_replay_safe": "p6_browser_mutation_inventory_replay",
    "tests.p6.test_authentication_rbac.P6AuthenticationRbacTests.test_recovery_rotates_session_and_revoked_expired_or_guessed_tokens_fail": "p6_recovery_rotation_guess_replay_expiry_revoke",
    "tests.p6.test_authentication_rbac.P6AuthenticationRbacTests.test_role_and_membership_revisions_are_checked_on_every_session_use": "p6_session_authority_revision",
    "tests.p6.test_authentication_rbac.P6AuthenticationRbacTests.test_concurrent_enrollment_consumption_has_exactly_one_atomic_winner": "p6_concurrent_token_atomic_winner",
    "tests.p6.test_change_approval.P6ChangeApprovalTests.test_authority_draft_requires_exact_other_admin_approval_and_is_single_use": "p6_draft_separation_exact_single_use_profile_only",
    "tests.p6.test_change_approval.P6ChangeApprovalTests.test_direct_change_workflow_separation_stale_binding_and_membership_revocation": "p6_membership_change_separation_stale_session",
    "tests.p6.test_change_approval.P6ChangeApprovalTests.test_change_replay_and_membership_apply_binding_survive_restart": "p6_change_replay_membership_apply_restart",
    "tests.p6.test_effect_audit.P6EffectAuditTests.test_effect_dispatch_revalidates_current_membership_and_expiry": "p6_effect_dispatch_current_authority_expiry",
    "tests.p6.test_effect_audit.P6EffectAuditTests.test_audit_export_is_scoped_bounded_redacted_authorized_and_restart_stable": "p6_audit_export_scope_bound_redaction_restart",
    "tests.p6.test_effect_audit.P6EffectAuditTests.test_escape_metric_is_observed_and_fault_injection_fails_closed": "p6_observed_escape_metric_fault_injection",
    "tests.p6.test_migrations.P6MigrationTests.test_migration_007_is_additive_checksummed_and_fresh_equals_v6_upgrade": "p6_migration_007_fresh_upgrade",
    "tests.p6.test_migrations.P6MigrationTests.test_failed_007_rolls_back_schema_and_migration_record": "p6_migration_007_rollback",
    "tests.p6.test_repository.P6RepositoryGateTests.test_main_original_branch_and_normal_descendant_pass": "p6_repository_branch_independent_descendant",
    "tests.p6.test_repository.P6RepositoryGateTests.test_wrong_ancestry_and_missing_trusted_commit_fail_closed": "p6_repository_wrong_ancestry_trusted_commit",
    "tests.p6.test_repository.P6RepositoryGateTests.test_acceptance_immutable_drift_and_missing_required_file_fail_closed": "p6_repository_immutable_required",
    "tests.p6.test_repository.P6RepositoryGateTests.test_exact_root_and_real_development_tree_pass": "p6_repository_root_real_tree",
}
REQUIRED_TEST_BOUNDARIES = {**P5_BOUNDARIES, **P6_BOUNDARIES}


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
    parser = argparse.ArgumentParser(description="Run the complete P6 unittest suite once.")
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
