# SPDX-License-Identifier: Apache-2.0

"""Run the complete P7 suite once and record required adapter fault identities."""

from __future__ import annotations

import argparse
import json
import sys
import unittest
from pathlib import Path
from typing import Any, TextIO

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_p6_unittest_suite import REQUIRED_TEST_BOUNDARIES as P6_BOUNDARIES

P7_BOUNDARIES = {
    "tests.p7.test_configuration.P7ConfigurationTests.test_default_selection_is_deterministic_and_network_free": "p7_default_deterministic_reference",
    "tests.p7.test_configuration.P7ConfigurationTests.test_unknown_modes_missing_fields_and_stray_network_settings_fail_closed": "p7_explicit_opt_in_fail_closed",
    "tests.p7.test_configuration.P7ConfigurationTests.test_url_userinfo_query_fragment_scheme_and_non_loopback_http_are_refused": "p7_endpoint_ssrf_refusal",
    "tests.p7.test_configuration.P7ConfigurationTests.test_credential_must_be_regular_bounded_non_writable_file": "p7_credential_file_boundary",
    "tests.p7.test_model_adapter.P7ModelAdapterTests.test_success_reconstructs_all_authority_from_the_server_request": "p7_model_authority_rebinding",
    "tests.p7.test_model_adapter.P7ModelAdapterTests.test_unknown_fields_authority_injection_and_unknown_outcome_fail_closed": "p7_model_authority_injection_refusal",
    "tests.p7.test_model_adapter.P7ModelAdapterTests.test_malformed_duplicate_non_json_content_and_oversize_fail_safely": "p7_model_malformed_oversize",
    "tests.p7.test_model_adapter.P7ModelAdapterTests.test_timeout_disconnect_redirect_connect_dns_and_tls_are_typed": "p7_model_transport_failures",
    "tests.p7.test_channel_adapter.P7ChannelAdapterTests.test_timeout_and_disconnect_after_submission_are_ambiguous": "p7_channel_post_submit_ambiguity",
    "tests.p7.test_channel_adapter.P7ChannelAdapterTests.test_authority_binding_and_idempotency_rebinding_fail_before_network": "p7_channel_exact_binding_replay",
    "tests.p7.test_channel_adapter.P7ChannelAdapterTests.test_reconciliation_failure_and_fresh_restart_never_invent_absence": "p7_reconciliation_restart_unknown",
    "tests.p7.test_runtime_integration.P7RuntimeIntegrationTests.test_optional_model_exact_human_approval_and_channel_complete_existing_path": "p7_exact_approval_integration",
    "tests.p7.test_runtime_integration.P7RuntimeIntegrationTests.test_provider_failure_preserves_pending_causal_work_across_restart": "p7_failure_causal_restart",
    "tests.p7.test_runtime_integration.P7RuntimeIntegrationTests.test_ambiguous_dispatch_is_not_resent_and_restart_stays_unknown": "p7_ambiguous_no_blind_resend",
    "tests.p7.test_runtime_integration.P7RuntimeIntegrationTests.test_default_reference_semantic_output_is_unchanged": "p7_deterministic_regression",
    "tests.p7.test_repository.P7RepositoryGateTests.test_historical_drift_and_migration_008_fail_closed": "p7_historical_immutability",
    "tests.p7.test_repository.P7RepositoryGateTests.test_evidence_writer_requires_exact_branch_gates_claims_and_zero_cleanup": "p7_evidence_fail_closed",
}
REQUIRED_TEST_BOUNDARIES = {**P6_BOUNDARIES, **P7_BOUNDARIES}


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
    parser = argparse.ArgumentParser(description="Run the complete P7 unittest suite once.")
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
