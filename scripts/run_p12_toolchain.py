# SPDX-License-Identifier: Apache-2.0

"""Run P12 governance gates and exact-object historical replay."""

from __future__ import annotations

import argparse
import base64
import binascii
import errno
import hashlib
import json
import os
import re
import secrets
import shlex
import shutil
import signal
import ssl
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TextIO

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import check_p12_historical_inventory as historical_inventory  # noqa: E402
from scripts.check_p12_ci_policy import (  # noqa: E402
    NODE_ENGINE,
    NODE_VERSION,
    NPM_VERSION,
    PACKAGE_MANAGER,
    check_ci_policy,
)
from scripts.check_p12_migrations import check_migrations  # noqa: E402
from scripts.check_p12_provenance import check_provenance  # noqa: E402
from scripts.check_p12_rebaseline import check_rebaseline  # noqa: E402
from scripts.check_p12_repository import (  # noqa: E402
    ACCEPTANCE_BLOB,
    ACCEPTANCE_COMMIT,
    BASE_COMMIT,
    BRANCH,
    SUMMARY_PATH,
    P12GateError,
    check_git_indirections,
    check_repository,
    git,
)
from scripts.collect_p12_evidence import (  # noqa: E402
    PLATFORM_STATUS,
    canonical_json,
    implementation_range,
    implementation_range_digest,
    parse_json_unique,
    validate_preflight_receipt,
)
from scripts.run_p8_toolchain import _prepare_python, _prepare_studio  # noqa: E402
from scripts.run_p8_unittest_suite import run_suite  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HistoricalInventoryError = historical_inventory.HistoricalInventoryError
ITEM_COUNTS = historical_inventory.ITEM_COUNTS
OBJECT_ORDER = historical_inventory.OBJECT_ORDER
OBJECT_TIMEOUTS = historical_inventory.OBJECT_TIMEOUTS
OPERATION_TIMEOUTS = historical_inventory.OPERATION_TIMEOUTS
EXCLUDED_GATE_IDS = historical_inventory.EXCLUDED_GATE_IDS
PYPROJECT = (
    "pyproject.toml",
    "77df2013d93d8b8b6d0441cccb44a127f9c88f07",
    "25683ddd04aa1f2abf21ae60d42a1a44bb7e198d721cfa6d452b8fb61483c15a",
)
PYTHON_LOCK = (
    "requirements/p8.lock",
    "819980980ba87d1b7166af4b4b0da53ca4e4ac63",
    "5afb5bc2f6bf2cfdc77d0457b92255f822d89cd3cd754ebb876741d7ee6430d0",
)
CERTIFI_VERSION = "2026.7.22"
PACKAGING_VERSION = "26.3"
CERTIFI_WHEEL_HASH = "62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775"
PACKAGING_WHEEL_HASH = "d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c"
CERTIFI_BUNDLE_SHA256 = "9cc2a774b5198dcff14d9be1e66091f538975d867ce029a96bce15a55dfd730f"
P12_TEST_MODULES = (
    "tests.p12.test_ci_policy",
    "tests.p12.test_evidence_gate",
    "tests.p12.test_historical_inventory",
    "tests.p12.test_migrations",
    "tests.p12.test_provenance",
    "tests.p12.test_rebaseline",
    "tests.p12.test_repository",
)
P12_TEST_COUNT = 136
P12_TEST_IDS = (
    "tests.p12.test_ci_policy.CiPolicyTests.test_exact_canonical_workflow_passes",
    "tests.p12.test_ci_policy.CiPolicyTests.test_pull_request_target_is_rejected",
    "tests.p12.test_ci_policy.CiPolicyTests.test_workflow_dispatch_is_rejected",
    "tests.p12.test_ci_policy.CiPolicyTests.test_workflow_call_is_rejected",
    "tests.p12.test_ci_policy.CiPolicyTests.test_schedule_is_rejected",
    "tests.p12.test_ci_policy.CiPolicyTests.test_write_permission_is_rejected",
    "tests.p12.test_ci_policy.CiPolicyTests.test_oidc_permission_is_rejected",
    "tests.p12.test_ci_policy.CiPolicyTests.test_secret_context_is_rejected",
    "tests.p12.test_ci_policy.CiPolicyTests.test_mutable_action_reference_is_rejected",
    "tests.p12.test_ci_policy.CiPolicyTests.test_persisted_checkout_credentials_are_rejected",
    "tests.p12.test_ci_policy.CiPolicyTests.test_direct_node_version_is_rejected",
    "tests.p12.test_ci_policy.CiPolicyTests.test_wrong_node_file_content_is_rejected",
    "tests.p12.test_ci_policy.CiPolicyTests.test_package_manager_integrity_drift_is_rejected",
    "tests.p12.test_ci_policy.CiPolicyTests.test_historical_gate_is_not_current_ci",
    "tests.p12.test_ci_policy.CiPolicyTests.test_evidence_preflight_is_rejected_in_ci",
    "tests.p12.test_ci_policy.CiPolicyTests.test_publication_command_is_rejected",
    "tests.p12.test_ci_policy.CiPolicyTests.test_compose_without_main_push_condition_is_rejected",
    "tests.p12.test_ci_policy.CiPolicyTests.test_ubuntu_2404_is_exact",
    "tests.p12.test_ci_policy.CiPolicyTests.test_two_required_jobs_are_exact",
    "tests.p12.test_ci_policy.CiPolicyTests.test_action_inventory_is_exact",
    "tests.p12.test_ci_policy.CiPolicyTests.test_portable_timeout_contract_is_exact",
    "tests.p12.test_ci_policy.CiPolicyTests.test_artifact_transport_is_rejected",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_claim_and_status_are_narrow",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_canonical_json_is_sorted_compact_utf8",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_range_digest_is_order_sensitive_and_prefixed",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_valid_unexpired_authorization_passes",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_expired_authorization_fails_closed",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_authorization_for_another_head_fails_closed",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_writer_creates_only_summary",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_writer_refuses_existing_summary",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_preflight_receipt_is_canonical_mode_0600",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_preflight_receipt_refuses_nonempty_directory",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_preflight_receipt_refuses_repository_path",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_exact_ghcr_inventory_passes",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_extra_ghcr_inventory_entry_fails_closed",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_tls_ca_fallback_allows_only_certificate_failure",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_public_evidence_vocabulary_contains_no_live_claim",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_exact_two_ci_envelopes_pass",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_forged_marker_fails_closed",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_duplicate_envelope_fails_closed",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_wrong_job_fails_closed",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_wrong_attempt_fails_closed",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_truncated_log_fails_closed",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_unbound_dynamic_field_fails_closed",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_missing_malformed_or_digest_mismatch_fails_closed",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_wrong_run_or_head_fails_closed",
    "tests.p12.test_evidence_gate.EvidenceGateTests.test_full_actions_log_retention_fails_closed",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_canonical_inventory_passes",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_typed_counts_are_exact",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_exact_five_platform_exclusions",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_gate_set_difference_is_exact",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_p8_bootstrap_is_setup_only",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_anchors_are_not_gate_results",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_per_object_resource_limits",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_cross_object_state_is_rejected",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_historical_subprocess_is_required",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_current_tree_module_shadowing_is_rejected",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_module_blob_mismatch_is_rejected",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_leaf_results_remain_individual",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_recursive_aggregate_is_rejected",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_object_cleanup_precedes_next_setup",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_timeout_values_are_exact",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_missing_gate_fails_closed",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_extra_exclusion_fails_closed",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_dynamic_membership_fails_closed",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_entrypoint_identity_is_exact",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_five_embedded_darwin_anchors_are_platform_scoped",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_linux_claim_laundering_fails_closed",
    "tests.p12.test_historical_inventory.HistoricalInventoryTests.test_zero_residue_is_required",
    "tests.p12.test_migrations.MigrationTests.test_exact_current_migration_gate_passes",
    "tests.p12.test_migrations.MigrationTests.test_manifest_identity_is_exact",
    "tests.p12.test_migrations.MigrationTests.test_migrations_one_through_eight_are_exact",
    "tests.p12.test_migrations.MigrationTests.test_future_owners_are_exact",
    "tests.p12.test_migrations.MigrationTests.test_migration_009_owner_drift_fails_closed",
    "tests.p12.test_migrations.MigrationTests.test_migration_011_owner_drift_fails_closed",
    "tests.p12.test_migrations.MigrationTests.test_migration_012_owner_drift_fails_closed",
    "tests.p12.test_migrations.MigrationTests.test_migration_013_owner_drift_fails_closed",
    "tests.p12.test_migrations.MigrationTests.test_migration_014_owner_drift_fails_closed",
    "tests.p12.test_migrations.MigrationTests.test_migration_015_cannot_gain_an_owner",
    "tests.p12.test_provenance.ProvenanceTests.test_complete_receipt_passes",
    "tests.p12.test_provenance.ProvenanceTests.test_historical_anchor_set_is_exact",
    "tests.p12.test_provenance.ProvenanceTests.test_p10_subjects_are_fixed",
    "tests.p12.test_provenance.ProvenanceTests.test_active_and_superseded_sets_are_both_protected",
    "tests.p12.test_provenance.ProvenanceTests.test_all_nine_p10_runs_are_fixed",
    "tests.p12.test_provenance.ProvenanceTests.test_receipt_rejects_missing_covered_path",
    "tests.p12.test_provenance.ProvenanceTests.test_receipt_rejects_source_read",
    "tests.p12.test_provenance.ProvenanceTests.test_receipt_rejects_publication",
    "tests.p12.test_provenance.ProvenanceTests.test_receipt_rejects_p10_lifecycle_drift",
    "tests.p12.test_provenance.ProvenanceTests.test_receipt_rejects_local_absolute_path",
    "tests.p12.test_provenance.ProvenanceTests.test_rejected_attempt_chains_and_run_summaries_are_exact",
    "tests.p12.test_provenance.ProvenanceTests.test_blueprint_source_identity_is_exact",
    "tests.p12.test_rebaseline.RebaselineTests.test_complete_living_rebaseline_passes",
    "tests.p12.test_rebaseline.RebaselineTests.test_exact_living_document_inventory",
    "tests.p12.test_rebaseline.RebaselineTests.test_exact_p12_through_p20_titles",
    "tests.p12.test_rebaseline.RebaselineTests.test_exact_core_record_contract_passes",
    "tests.p12.test_rebaseline.RebaselineTests.test_project_scope_authority_expansion_fails_closed",
    "tests.p12.test_rebaseline.RebaselineTests.test_project_running_state_fails_closed",
    "tests.p12.test_rebaseline.RebaselineTests.test_waiting_kind_rename_fails_closed",
    "tests.p12.test_rebaseline.RebaselineTests.test_goal_binding_owner_drift_fails_closed",
    "tests.p12.test_rebaseline.RebaselineTests.test_memory_admission_lifecycle_expansion_fails_closed",
    "tests.p12.test_rebaseline.RebaselineTests.test_memory_record_silent_overwrite_fails_closed",
    "tests.p12.test_rebaseline.RebaselineTests.test_trigger_correlation_status_expansion_fails_closed",
    "tests.p12.test_rebaseline.RebaselineTests.test_automatic_authorization_owner_drift_fails_closed",
    "tests.p12.test_rebaseline.RebaselineTests.test_current_roadmap_order_passes",
    "tests.p12.test_rebaseline.RebaselineTests.test_swapped_roadmap_phase_fails_closed",
    "tests.p12.test_rebaseline.RebaselineTests.test_renamed_roadmap_owner_fails_closed",
    "tests.p12.test_rebaseline.RebaselineTests.test_adr_has_all_core_contract_markers",
    "tests.p12.test_rebaseline.RebaselineTests.test_missing_core_marker_fails_closed",
    "tests.p12.test_rebaseline.RebaselineTests.test_governance_only_claim_boundary_passes",
    "tests.p12.test_rebaseline.RebaselineTests.test_runtime_overclaim_fails_closed",
    "tests.p12.test_rebaseline.RebaselineTests.test_public_pilot_overclaim_fails_closed",
    "tests.p12.test_rebaseline.RebaselineTests.test_all_four_future_gates_are_independent",
    "tests.p12.test_rebaseline.RebaselineTests.test_three_platform_status_dimensions_are_independent",
    "tests.p12.test_rebaseline.RebaselineTests.test_five_darwin_evidence_bindings_are_platform_scoped",
    "tests.p12.test_rebaseline.RebaselineTests.test_p20_l0_is_first_blocking_subgate",
    "tests.p12.test_rebaseline.RebaselineTests.test_p20_l0_does_not_reorder_p13_through_p20",
    "tests.p12.test_repository.RepositoryTests.test_acceptance_allowlist_has_exactly_forty_two_paths",
    "tests.p12.test_repository.RepositoryTests.test_implementation_allowlist_has_exactly_forty_paths",
    "tests.p12.test_repository.RepositoryTests.test_implementation_changed_set_has_exactly_forty_one_paths",
    "tests.p12.test_repository.RepositoryTests.test_final_changed_set_has_exactly_forty_two_paths",
    "tests.p12.test_repository.RepositoryTests.test_acceptance_commit_parent_tree_and_blob_are_exact",
    "tests.p12.test_repository.RepositoryTests.test_acceptance_working_file_identity_is_exact",
    "tests.p12.test_repository.RepositoryTests.test_acceptance_commit_changes_only_contract",
    "tests.p12.test_repository.RepositoryTests.test_implementation_path_set_validates",
    "tests.p12.test_repository.RepositoryTests.test_final_path_set_validates",
    "tests.p12.test_repository.RepositoryTests.test_missing_implementation_path_fails_closed",
    "tests.p12.test_repository.RepositoryTests.test_unexpected_path_fails_closed",
    "tests.p12.test_repository.RepositoryTests.test_summary_is_required_only_for_final",
    "tests.p12.test_repository.RepositoryTests.test_makefile_change_is_exactly_bounded",
    "tests.p12.test_repository.RepositoryTests.test_preexisting_makefile_recipe_drift_fails_closed",
    "tests.p12.test_repository.RepositoryTests.test_generic_ci_alias_must_point_only_to_p12",
    "tests.p12.test_repository.RepositoryTests.test_new_makefile_target_set_is_exact",
    "tests.p12.test_repository.RepositoryTests.test_v1_v2_v3_refs_are_preserved",
    "tests.p12.test_repository.RepositoryTests.test_v1_v2_v3_are_not_v4_ancestors",
    "tests.p12.test_repository.RepositoryTests.test_attempt_ref_presence_and_absence_are_exact",
    "tests.p12.test_repository.RepositoryTests.test_pr14_close_without_merge_boundary_is_exact",
)
INVENTORY_PATH = "docs/p12/portable-historical-inventory.json"
ENVELOPE_SCHEMA = "digital-colleagues.p12-v4-ci-result-envelope.v1"
ENVELOPE_PREFIX = "P12_V4_RESULT_ENVELOPE_V1"
ENVELOPE_PAYLOAD_MAX = 32_768
ENVELOPE_TOKEN_MAX = 43_691
ENVELOPE_LINE_MAX = 43_850
ENVELOPE_PATTERN = re.compile(
    rb"^(?:[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    rb"(?:\.[0-9]{1,9})?Z )?P12_V4_RESULT_ENVELOPE_V1 "
    rb"([A-Za-z0-9_-]+) sha256=([0-9a-f]{64})\r?$"
)
SAFE_VALUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+() /:-]{0,127}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
REPOSITORY = "jeremyliu1220/digital-colleagues"
WORKFLOW_PATH = ".github/workflows/ci.yml"
WORKFLOW_REF_PREFIX = f"{REPOSITORY}/{WORKFLOW_PATH}@"
V4_BRANCH = BRANCH
CONTRACTED_RUNNER = "ubuntu-24.04"
JOB_KINDS = {
    "current_governance": {
        "job_id": "current-ci",
        "job_name": "Current P12 governance non-publishing verification",
        "gate_id": "p12_current_ci",
        "test_count": 136,
        "test_count_semantics": "p12_governance_unittest_methods",
        "inventory_status": "bound_not_executed_by_this_job",
    },
    "portable_history": {
        "job_id": "portable-history",
        "job_name": "Portable historical replay",
        "gate_id": "p12_portable_historical_replay",
        "test_count": 616,
        "test_count_semantics": "historical_python_unittest_cases",
        "inventory_status": "passed",
    },
}
ENVELOPE_KEYS = {
    "base_ref",
    "base_sha",
    "cleanup_residue_count",
    "contracted_runner_family",
    "event",
    "gate",
    "head_branch",
    "head_sha",
    "inventory",
    "job_id",
    "job_name",
    "observed_environment",
    "p12_current_p10_registry_protection",
    "platform_status",
    "publication_count",
    "pull_request_number",
    "repository",
    "run_attempt",
    "run_id",
    "schema",
    "workflow_name",
    "workflow_path",
}
OBSERVED_KEYS = {
    "runner_os",
    "runner_image_os",
    "runner_image_version",
    "architecture",
    "docker_server_version",
    "docker_compose_version",
    "python_version",
    "node_version",
    "npm_version",
}
GATE_KEYS = {
    "error_count",
    "failure_count",
    "gate_id",
    "result_digest",
    "skip_count",
    "status",
    "test_count",
    "test_count_semantics",
}
INVENTORY_KEYS = {
    "evidence_anchor_count",
    "excluded_acceptance_gate_count",
    "excluded_gate_ids",
    "execution_status",
    "included_acceptance_gate_count",
    "inventory_blob",
    "inventory_digest",
    "inventory_path",
    "inventory_sha256",
    "item_results",
    "item_results_digest",
    "passed_acceptance_gate_count",
    "setup_count",
    "skip_count",
    "total_item_count",
}
REGISTRY_PLACEHOLDER = {
    "reason": "evidence_preflight_only",
    "status": "not_evaluated",
}
CI_PLATFORM_STATUS: dict[str, object] = {
    "linux_public_pilot_readiness": "blocked",
    "p12_governance_result": "passed",
    "ubuntu_historical_execution_status": {gate_id: "not_proven" for gate_id in EXCLUDED_GATE_IDS},
}
RECEIPT_SCHEMA = "digital-colleagues.p12-v4-evidence-preflight-receipt.v1"
RECEIPT_KEYS = {
    "acceptance",
    "ca_verification",
    "ci",
    "cleanup_residue_count",
    "expires_at",
    "implementation",
    "inventory",
    "issued_at",
    "lifecycle",
    "nonce",
    "p10_protected_identity_digest",
    "p12_current_p10_registry_protection",
    "package_verification_digest",
    "platform_status",
    "publication_count",
    "repository",
    "schema",
}


def _safe(_value: str) -> str:
    """Return a fixed diagnostic that cannot reproduce untrusted input."""

    return "bounded failure diagnostic withheld"


def _run(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
    timeout: int = 3_600,
) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise P12GateError("P12 toolchain command failed")
    return completed.stdout


def _run_status(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
    timeout: int = 3_600,
) -> int:
    """Run an ordinary gate without retaining or echoing its untrusted diagnostics."""

    status, _ = _leaf_process(
        command,
        cwd=cwd,
        environment=os.environ.copy() if environment is None else environment,
        timeout=float(timeout),
        cleanup_deadline=time.monotonic() + timeout + 40.0,
        capture_output=False,
    )
    if status == 126:
        raise P12GateError("P12 ordinary gate process cleanup could not be proved")
    return status


def _flatten(suite: unittest.TestSuite) -> list[unittest.case.TestCase]:
    tests: list[unittest.case.TestCase] = []
    for value in suite:
        if isinstance(value, unittest.TestSuite):
            tests.extend(_flatten(value))
        elif isinstance(value, unittest.case.TestCase):
            tests.append(value)
        else:
            raise P12GateError("P12 test inventory contains an unknown test type")
    return tests


def _suite_outcome_status(
    result: dict[str, Any],
    *,
    expected_count: int,
    expected_ids: tuple[str, ...],
    label: str,
) -> str:
    counts: dict[str, int] = {}
    for key in (
        "tests_run",
        "failures",
        "errors",
        "skipped",
        "expected_failures",
        "unexpected_successes",
    ):
        value = result.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise P12GateError(f"P12 {label} result counts are malformed")
        counts[key] = value
    test_ids = result.get("test_ids")
    gate_passed = result.get("gate_passed")
    logical_pass = counts["tests_run"] > 0 and all(
        counts[key] == 0 for key in counts if key != "tests_run"
    )
    if (
        counts["tests_run"] != expected_count
        or not isinstance(test_ids, list)
        or test_ids != sorted(expected_ids)
        or type(gate_passed) is not bool
        or gate_passed != logical_pass
    ):
        raise P12GateError(f"P12 {label} result identity is invalid")
    return "passed" if gate_passed else "failed"


def run_p12_tests(root: Path, *, stream: TextIO) -> dict[str, Any]:
    suite = unittest.defaultTestLoader.loadTestsFromNames(P12_TEST_MODULES)
    tests = _flatten(suite)
    failures = [test for test in tests if test.__class__.__name__ == "_FailedTest"]
    identifiers = tuple(test.id() for test in tests)
    if failures or len(set(identifiers)) != len(identifiers):
        raise P12GateError("P12 literal governance test inventory is invalid")
    if (
        P12_TEST_COUNT != 136
        or len(P12_TEST_IDS) != P12_TEST_COUNT
        or len(set(P12_TEST_IDS)) != P12_TEST_COUNT
        or len(identifiers) != P12_TEST_COUNT
        or set(identifiers) != set(P12_TEST_IDS)
    ):
        raise P12GateError("P12 governance test count differs from the fixed inventory")
    result = run_suite(suite, stream=stream)
    status = _suite_outcome_status(
        result,
        expected_count=P12_TEST_COUNT,
        expected_ids=P12_TEST_IDS,
        label="governance test suite",
    )
    return {
        **result,
        "status": status,
        "suite": "p12_governance_suite",
        "module_inventory": list(P12_TEST_MODULES),
        "inventory_count": P12_TEST_COUNT,
        "literal_test_ids": list(P12_TEST_IDS),
    }


def current_p11_test_ids(root: Path) -> tuple[str, ...]:
    try:
        text = (root / "docs/p11r/acceptance.md").read_text(encoding="utf-8")
        section = text.split("## Exact current-tree P11 regression inventory", 1)[1]
        block = section.split("```text", 1)[1].split("```", 1)[0]
    except (OSError, UnicodeError, IndexError) as exc:
        raise P12GateError("P12 cannot load the exact current-tree P11 inventory") from exc
    identifiers = tuple(line.strip() for line in block.splitlines() if line.strip())
    if len(identifiers) != 100 or len(set(identifiers)) != 100:
        raise P12GateError("P12 current-tree P11 inventory is not exactly 100 tests")
    return identifiers


def run_current_p11_tests(root: Path, *, stream: TextIO) -> dict[str, Any]:
    identifiers = current_p11_test_ids(root)
    suite = unittest.defaultTestLoader.loadTestsFromNames(identifiers)
    loaded = tuple(test.id() for test in _flatten(suite))
    if loaded != identifiers:
        raise P12GateError("P12 current-tree P11 tests did not load one-for-one")
    result = run_suite(suite, stream=stream)
    status = _suite_outcome_status(
        result,
        expected_count=100,
        expected_ids=identifiers,
        label="current-tree P11 regression",
    )
    return {
        **result,
        "status": status,
        "suite": "p12_current_tree_p11_regression",
        "inventory_count": 100,
    }


def _read_result(path: Path, expected: str) -> dict[str, Any]:
    value = _load_gate_result(str(path))
    if value.get("suite") != expected:
        raise P12GateError("P12 subprocess test result identity is invalid")
    return value


def _child_result_entry_state(path: Path) -> str:
    """Inspect only the expected result entry through its held private parent."""

    try:
        with _held_private_directory(
            path.parent,
            label="subprocess test result",
        ) as directory_descriptor:
            try:
                os.stat(
                    path.name,
                    dir_fd=directory_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                return "absent"
            except OSError:
                return "infrastructure_error"
    except (OSError, P12GateError):
        return "infrastructure_error"
    return "present"


def _ordinary_child_result_error(path: Path, error: BaseException) -> bool:
    state = _child_result_entry_state(path)
    if isinstance(error, FileNotFoundError):
        return state == "absent"
    if state == "absent":
        return isinstance(error.__cause__, FileNotFoundError)
    if state != "present":
        return False
    return not isinstance(error.__cause__, OSError)


def _read_suite_result(
    path: Path,
    *,
    expected_suite: str,
    expected_count: int,
    expected_ids: tuple[str, ...],
    exit_status: int,
) -> dict[str, Any]:
    if exit_status not in {0, 1}:
        raise P12GateError("P12 subprocess test runner ended abnormally")
    value = _read_result(path, expected_suite)
    status = _suite_outcome_status(
        value,
        expected_count=expected_count,
        expected_ids=expected_ids,
        label=expected_suite,
    )
    if value.get("status") != status or (exit_status == 0) != (status == "passed"):
        raise P12GateError("P12 subprocess test status and result disagree")
    return value


def _failed_suite_counts(value: dict[str, Any]) -> tuple[int, int]:
    failures = int(value["failures"])
    errors = sum(
        int(value[key])
        for key in ("errors", "skipped", "expected_failures", "unexpected_successes")
    )
    if failures + errors == 0:
        errors = 1
    return failures, errors


def _quality(root: Path, temporary: Path) -> dict[str, Any]:
    temporary.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(temporary, 0o700)
    python, environment = _prepare_python(temporary / "python-environment")
    result: dict[str, Any] = {
        "status": "passed",
        "test_count": 0,
        "failure_count": 0,
        "error_count": 0,
        "skip_count": 0,
        "failed_gate": None,
        "failed_exit_status": None,
        "python_lock": PYTHON_LOCK[0],
        "hash_locked_environment": True,
        "ruff_lint": "not_run_due_to_prior_failure",
        "ruff_format": "not_run_due_to_prior_failure",
        "mypy": "not_run_due_to_prior_failure",
        "current_tree_p11": {"status": "not_run_due_to_prior_failure"},
        "p12": {"status": "not_run_due_to_prior_failure"},
    }
    for gate_name, command in (
        ("ruff_lint", [str(python), "-m", "ruff", "check", "src", "scripts", "tests"]),
        (
            "ruff_format",
            [str(python), "-m", "ruff", "format", "--check", "src", "scripts", "tests"],
        ),
        ("mypy", [str(python), "-m", "mypy", "src", "scripts", "tests"]),
    ):
        status = _run_status(command, cwd=root, environment=environment, timeout=900)
        result[gate_name] = "passed" if status == 0 else "failed"
        if status != 0:
            result.update(
                {
                    "status": "failed",
                    "failure_count": 1,
                    "failed_gate": gate_name,
                    "failed_exit_status": status,
                }
            )
            return result
    p11_path = temporary / "current-p11.json"
    p11_status = _run_status(
        [
            str(python),
            "-B",
            "-m",
            "scripts.run_p12_toolchain",
            "--scope",
            "current-p11-tests",
            "--json-output",
            str(p11_path),
        ],
        cwd=root,
        environment=environment,
        timeout=900,
    )
    if p11_status == 124:
        result.update(
            {
                "status": "failed",
                "error_count": 1,
                "failed_gate": "current_tree_p11_timeout",
                "failed_exit_status": p11_status,
            }
        )
        return result
    if p11_status not in {0, 1}:
        result.update(
            {
                "status": "failed",
                "error_count": 1,
                "failed_gate": "current_tree_p11_runner",
                "failed_exit_status": p11_status,
            }
        )
        return result
    try:
        p11_result = _read_suite_result(
            p11_path,
            expected_suite="p12_current_tree_p11_regression",
            expected_count=100,
            expected_ids=current_p11_test_ids(root),
            exit_status=p11_status,
        )
    except FileNotFoundError as exc:
        if not _ordinary_child_result_error(p11_path, exc):
            raise
        result.update(
            {
                "status": "failed",
                "error_count": 1,
                "failed_gate": "current_tree_p11_result",
                "failed_exit_status": p11_status,
            }
        )
        return result
    except (UnicodeError, json.JSONDecodeError):
        result.update(
            {
                "status": "failed",
                "error_count": 1,
                "failed_gate": "current_tree_p11_result",
                "failed_exit_status": p11_status,
            }
        )
        return result
    except P12GateError as exc:
        if not _ordinary_child_result_error(p11_path, exc):
            raise
        result.update(
            {
                "status": "failed",
                "error_count": 1,
                "failed_gate": "current_tree_p11_result",
                "failed_exit_status": p11_status,
            }
        )
        return result
    result["current_tree_p11"] = p11_result
    if p11_result["status"] == "failed":
        failures, errors = _failed_suite_counts(p11_result)
        result.update(
            {
                "status": "failed",
                "failure_count": failures,
                "error_count": errors,
                "failed_gate": "current_tree_p11",
                "failed_exit_status": p11_status,
            }
        )
        return result
    p12_path = temporary / "p12.json"
    p12_status = _run_status(
        [
            str(python),
            "-B",
            "-m",
            "scripts.run_p12_toolchain",
            "--scope",
            "p12-tests",
            "--json-output",
            str(p12_path),
        ],
        cwd=root,
        environment=environment,
        timeout=900,
    )
    if p12_status == 124:
        result.update(
            {
                "status": "failed",
                "error_count": 1,
                "failed_gate": "p12_timeout",
                "failed_exit_status": p12_status,
            }
        )
        return result
    if p12_status not in {0, 1}:
        result.update(
            {
                "status": "failed",
                "error_count": 1,
                "failed_gate": "p12_runner",
                "failed_exit_status": p12_status,
            }
        )
        return result
    try:
        p12_result = _read_suite_result(
            p12_path,
            expected_suite="p12_governance_suite",
            expected_count=P12_TEST_COUNT,
            expected_ids=P12_TEST_IDS,
            exit_status=p12_status,
        )
    except FileNotFoundError as exc:
        if not _ordinary_child_result_error(p12_path, exc):
            raise
        result.update(
            {
                "status": "failed",
                "error_count": 1,
                "failed_gate": "p12_result",
                "failed_exit_status": p12_status,
            }
        )
        return result
    except (UnicodeError, json.JSONDecodeError):
        result.update(
            {
                "status": "failed",
                "error_count": 1,
                "failed_gate": "p12_result",
                "failed_exit_status": p12_status,
            }
        )
        return result
    except P12GateError as exc:
        if not _ordinary_child_result_error(p12_path, exc):
            raise
        result.update(
            {
                "status": "failed",
                "error_count": 1,
                "failed_gate": "p12_result",
                "failed_exit_status": p12_status,
            }
        )
        return result
    result["p12"] = p12_result
    result["test_count"] = p12_result["tests_run"]
    if p12_result["status"] == "failed":
        failures, errors = _failed_suite_counts(p12_result)
        result.update(
            {
                "status": "failed",
                "failure_count": failures,
                "error_count": errors,
                "failed_gate": "p12",
                "failed_exit_status": p12_status,
            }
        )
    return result


def _studio(temporary: Path) -> dict[str, object]:
    studio = _prepare_studio(temporary / "studio-environment")
    commands = (
        ["corepack", "npm", "run", "lint"],
        ["corepack", "npm", "run", "format:check"],
        ["corepack", "npm", "run", "typecheck"],
        ["corepack", "npm", "test", "--", "--run"],
        ["corepack", "npm", "run", "build"],
    )
    result: dict[str, object] = {
        "status": "passed",
        "command_count": len(commands),
        "executed_command_count": 0,
        "failure_count": 0,
        "failed_command_index": None,
        "failed_exit_status": None,
        "node_version": NODE_VERSION,
        "node_engine": NODE_ENGINE,
        "npm_version": NPM_VERSION,
        "package_manager": PACKAGE_MANAGER,
    }
    for index, command in enumerate(commands, 1):
        status = _run_status(command, cwd=studio, timeout=600)
        result["executed_command_count"] = index
        if status != 0:
            result.update(
                {
                    "status": "failed",
                    "failure_count": 1,
                    "failed_command_index": index,
                    "failed_exit_status": status,
                }
            )
            break
    return result


def run_tests(root: Path, temporary: Path) -> dict[str, Any]:
    quality = _quality(root, temporary / "quality")
    if quality["status"] == "failed":
        return {
            "status": "failed",
            "test_count": quality["test_count"],
            "failure_count": quality["failure_count"],
            "error_count": quality["error_count"],
            "skip_count": 0,
            "quality": quality,
            "studio": {"status": "not_run_due_to_prior_failure"},
        }
    studio = _studio(temporary)
    return {
        "status": studio["status"],
        "test_count": quality["test_count"],
        "failure_count": studio["failure_count"],
        "error_count": 0,
        "skip_count": 0,
        "quality": quality,
        "studio": studio,
    }


def _public_boundary(root: Path) -> dict[str, object]:
    output = _run(
        [sys.executable, "-B", "scripts/check_public_boundary.py", "."],
        cwd=root,
        timeout=300,
    )
    value = json.loads(output)
    if not isinstance(value, dict) or value.get("gate") != "public_boundary_clean":
        raise P12GateError("P12 public-boundary result is invalid")
    return value


def static_gates(root: Path, *, mode: str) -> dict[str, Any]:
    return {
        "repository": check_repository(root, mode=mode),
        "ci_policy": check_ci_policy(root),
        "historical_inventory": historical_inventory.check_historical_inventory(root),
        "migrations": check_migrations(root),
        "rebaseline": check_rebaseline(root),
        "provenance": check_provenance(root),
        "public_boundary": _public_boundary(root),
    }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _leaf_process(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    timeout: float,
    cleanup_deadline: float | None = None,
    capture_output: bool = True,
) -> tuple[int, bytes]:
    """Run one historical leaf in its own process group without retry."""

    def signal_group(process_group: int, requested_signal: signal.Signals) -> bool:
        try:
            os.killpg(process_group, requested_signal)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        return True

    def bounded_grace(limit: float) -> float:
        if cleanup_deadline is None:
            return limit
        return max(0.001, min(limit, cleanup_deadline - time.monotonic()))

    def group_exists(process_group: int) -> bool:
        try:
            os.killpg(process_group, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def wait_group_gone(process_group: int, limit: float) -> bool:
        end = time.monotonic() + bounded_grace(limit)
        while time.monotonic() < end:
            if not group_exists(process_group):
                return True
            time.sleep(0.01)
        return not group_exists(process_group)

    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL,
        stderr=subprocess.STDOUT if capture_output else subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        captured, _ = process.communicate(timeout=timeout)
        output = captured or b""
    except subprocess.TimeoutExpired as timeout_error:
        output = timeout_error.output or b""
        signal_group(process.pid, signal.SIGTERM)
        try:
            captured, _ = process.communicate(timeout=bounded_grace(30.0))
            output = captured or output
        except subprocess.TimeoutExpired as termination_error:
            output = termination_error.output or output
            signal_group(process.pid, signal.SIGKILL)
            try:
                captured, _ = process.communicate(timeout=bounded_grace(5.0))
                output = captured or output
            except subprocess.TimeoutExpired as kill_error:
                output = kill_error.output or output
                if process.stdout is not None:
                    process.stdout.close()
                try:
                    process.wait(timeout=bounded_grace(5.0))
                except subprocess.TimeoutExpired:
                    process.kill()
                    try:
                        process.wait(timeout=bounded_grace(1.0))
                    except subprocess.TimeoutExpired:
                        pass
        if group_exists(process.pid):
            signal_group(process.pid, signal.SIGKILL)
        if not wait_group_gone(process.pid, 5.0):
            return 126, output[-262_144:]
        return 124, output[-262_144:]
    residue = group_exists(process.pid)
    if residue:
        signal_group(process.pid, signal.SIGTERM)
        if not wait_group_gone(process.pid, 5.0):
            signal_group(process.pid, signal.SIGKILL)
            if not wait_group_gone(process.pid, 5.0):
                return 126, output[-262_144:]
    return (125 if residue and process.returncode == 0 else process.returncode), output[-262_144:]


OBJECT_CLEANUP_RESERVE_SECONDS = 120


class HistoricalTimeout(P12GateError):
    """One bounded historical operation exhausted its available deadline."""


class HistoricalResidueError(P12GateError):
    """One historical child process group could not be proved absent."""


def _remaining_timeout(
    deadline: float,
    limit: int,
    *,
    label: str,
    reserve: int = 0,
) -> float:
    remaining = deadline - time.monotonic() - reserve
    if remaining <= 0:
        raise HistoricalTimeout(f"P12 historical {label} timed out")
    return min(float(limit), remaining)


def _operation_deadline(deadline: float, limit: int, *, label: str) -> float:
    now = time.monotonic()
    if deadline <= now:
        raise HistoricalTimeout(f"P12 historical {label} timed out")
    return min(deadline, now + limit)


def _historical_process(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None,
    deadline: float,
    cleanup_deadline: float | None = None,
    limit: int,
    label: str,
    reserve: int = 0,
) -> bytes:
    if cleanup_deadline is None:
        cleanup_deadline = deadline
    if cleanup_deadline < deadline:
        raise P12GateError("P12 historical cleanup deadline precedes operation deadline")
    status, output = _leaf_process(
        command,
        cwd=cwd,
        environment=os.environ.copy() if environment is None else environment,
        timeout=_remaining_timeout(deadline, limit, label=label, reserve=reserve),
        cleanup_deadline=cleanup_deadline,
    )
    if status == 124:
        raise HistoricalTimeout(f"P12 historical {label} timed out")
    if status == 126:
        raise HistoricalResidueError(f"P12 historical {label} left process residue")
    if status != 0:
        raise P12GateError(f"P12 historical {label} failed")
    return output


def _docker_ids(kind: str, project: str, *, deadline: float) -> tuple[str, ...]:
    command = [
        "docker",
        kind,
        "ls",
        "-q",
        "--filter",
        f"label=com.docker.compose.project={project}",
    ]
    if kind == "volume":
        command = [
            "docker",
            "volume",
            "ls",
            "-q",
            "--filter",
            f"label=com.docker.compose.project={project}",
        ]
    elif kind == "network":
        command = [
            "docker",
            "network",
            "ls",
            "-q",
            "--filter",
            f"label=com.docker.compose.project={project}",
        ]
    elif kind == "container":
        command = [
            "docker",
            "container",
            "ls",
            "-aq",
            "--filter",
            f"label=com.docker.compose.project={project}",
        ]
    output = _historical_process(
        command,
        cwd=ROOT,
        environment=None,
        deadline=deadline,
        limit=60,
        label="Docker residue inspection",
        reserve=0,
    )
    return tuple(value for value in output.decode("utf-8").splitlines() if value)


def _docker_remove(kind: str, values: tuple[str, ...], *, deadline: float) -> None:
    if not values:
        return
    command = ["docker", kind, "rm", *values]
    if kind == "container":
        command = ["docker", "container", "rm", "--force", *values]
    _historical_process(
        command,
        cwd=ROOT,
        environment=None,
        deadline=deadline,
        limit=120,
        label=f"Docker {kind} cleanup",
        reserve=0,
    )


def _cleanup_docker(project: str, *, deadline: float) -> None:
    error: P12GateError | None = None
    for kind in ("container", "network", "volume"):
        try:
            values = _docker_ids(kind, project, deadline=deadline)
            _docker_remove(kind, values, deadline=deadline)
        except P12GateError as exc:
            error = exc
    residue = False
    for kind in ("container", "network", "volume"):
        try:
            residue = bool(_docker_ids(kind, project, deadline=deadline)) or residue
        except P12GateError as exc:
            error = exc
    if residue:
        raise P12GateError("P12 historical object cleanup left Docker residue")
    if error is not None:
        raise error


def _docker_snapshot(*, deadline: float, reserve: int = 0) -> dict[str, tuple[str, ...]]:
    commands = {
        "containers": ["docker", "container", "ls", "-aq"],
        "networks": ["docker", "network", "ls", "-q"],
        "volumes": ["docker", "volume", "ls", "-q"],
    }
    result: dict[str, tuple[str, ...]] = {}
    for key, command in commands.items():
        output = _historical_process(
            command,
            cwd=ROOT,
            environment=None,
            deadline=deadline,
            limit=60,
            label="Docker baseline inspection",
            reserve=reserve,
        )
        result[key] = tuple(sorted(value for value in output.decode("utf-8").splitlines() if value))
    return result


def _git_bytes(
    root: Path,
    object_name: str,
    *,
    deadline: float | None = None,
    cleanup_deadline: float | None = None,
) -> bytes:
    if deadline is None:
        deadline = time.monotonic() + 120
    if cleanup_deadline is None:
        cleanup_deadline = deadline
    return _historical_process(
        ["git", "show", object_name],
        cwd=root,
        environment=None,
        deadline=deadline,
        cleanup_deadline=cleanup_deadline,
        limit=120,
        label="Git object read",
    )


def _remove_object_directory(path: Path, *, deadline: float) -> None:
    if path.is_symlink():
        raise P12GateError("P12 historical object temporary root is invalid")
    if not path.exists():
        return
    if not path.is_dir():
        raise P12GateError("P12 historical object temporary root is invalid")
    _historical_process(
        [
            sys.executable,
            "-I",
            "-c",
            "import shutil,sys; shutil.rmtree(sys.argv[1])",
            str(path),
        ],
        cwd=path.parent,
        environment=None,
        deadline=deadline,
        limit=120,
        label="object temporary cleanup",
    )


NPM_GATE_BLOCKS: dict[str, tuple[str, ...]] = {
    "P8": (
        "p8_studio_eslint",
        "p8_studio_prettier",
        "p8_studio_typescript",
        "p8_studio_vitest",
        "p8_studio_vite_build",
    ),
    "P9": (),
    "P10": (
        "p10_studio_eslint",
        "p10_studio_prettier",
        "p10_studio_typescript",
        "p10_studio_vitest",
        "p10_studio_vite_build",
    ),
    "P11": (
        "p11_studio_eslint",
        "p11_studio_prettier",
        "p11_studio_typescript",
        "p11_studio_vitest",
        "p11_studio_vite_build",
    ),
    "P11R": (
        "p11r_studio_eslint",
        "p11r_studio_prettier",
        "p11r_studio_typescript",
        "p11r_studio_vitest",
        "p11r_studio_vite_build",
    ),
}
NPM_GENERATED_DIRECTORIES = ("node_modules", "dist", ".vite", "coverage")


def _safe_checkout_relative(value: str) -> str:
    candidate = Path(value.rstrip("/"))
    if (
        not value
        or candidate.is_absolute()
        or not candidate.parts
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise P12GateError("P12 historical checkout contains an unsafe path")
    return candidate.as_posix()


def _npm_gate_block(
    object_name: str,
    object_items: list[dict[str, Any]],
    *,
    npm_workspace_count: object,
) -> tuple[str, ...]:
    expected = NPM_GATE_BLOCKS.get(object_name)
    if expected is None:
        raise P12GateError("P12 historical npm object identity is invalid")
    actual = tuple(
        str(item.get("gate_id"))
        for item in object_items
        if item.get("command_kind") == "npm_script"
    )
    indices = [
        index for index, item in enumerate(object_items) if item.get("command_kind") == "npm_script"
    ]
    expected_count = 0 if object_name == "P9" else 1
    if (
        type(npm_workspace_count) is not int
        or npm_workspace_count != expected_count
        or actual != expected
        or (indices and indices != list(range(indices[0], indices[-1] + 1)))
    ):
        raise P12GateError("P12 historical npm gate block is not exact and contiguous")
    return actual


def _checkout_status_paths(checkout: Path, *, deadline: float) -> tuple[str, ...]:
    raw = _historical_process(
        [
            "git",
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignored=matching",
        ],
        cwd=checkout,
        environment=None,
        deadline=deadline,
        limit=120,
        label="historical checkout status",
    )
    paths: list[str] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        if len(record) < 4 or record[2:3] != b" " or record[:2] not in {b"??", b"!!"}:
            raise P12GateError("P12 historical tracked checkout state drifted")
        try:
            path = _safe_checkout_relative(record[3:].decode("utf-8"))
        except UnicodeError as exc:
            raise P12GateError("P12 historical checkout path is not UTF-8") from exc
        paths.append(path)
    if len(paths) != len(set(paths)) or len({path.casefold() for path in paths}) != len(paths):
        raise P12GateError("P12 historical checkout status contains an alias")
    return tuple(sorted(paths, key=lambda value: value.encode("utf-8")))


def _tracked_checkout_identity(checkout: Path, *, deadline: float) -> tuple[str, str]:
    raw = _historical_process(
        ["git", "ls-files", "--stage", "-z"],
        cwd=checkout,
        environment=None,
        deadline=deadline,
        limit=120,
        label="historical tracked checkout identity",
    )
    digest = hashlib.sha256()
    paths: list[str] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            header, encoded_path = record.split(b"\t", 1)
            encoded_mode, _, encoded_stage = header.split(b" ", 2)
            path = _safe_checkout_relative(encoded_path.decode("utf-8"))
            mode = encoded_mode.decode("ascii")
            stage = encoded_stage.decode("ascii")
        except (ValueError, UnicodeError) as exc:
            raise P12GateError("P12 historical tracked checkout identity is malformed") from exc
        if stage != "0" or mode not in {"100644", "100755", "120000"}:
            raise P12GateError("P12 historical tracked checkout mode is unsupported")
        target = checkout.joinpath(*Path(path).parts)
        try:
            metadata = os.lstat(target)
            if mode == "120000":
                if not stat.S_ISLNK(metadata.st_mode):
                    raise P12GateError("P12 historical tracked symlink identity drifted")
                content = os.fsencode(os.readlink(target))
                kind = b"symlink"
            else:
                if not stat.S_ISREG(metadata.st_mode) or target.is_symlink():
                    raise P12GateError("P12 historical tracked file identity drifted")
                content = target.read_bytes()
                kind = b"regular"
        except OSError as exc:
            raise P12GateError("P12 historical tracked checkout is unreadable") from exc
        digest.update(encoded_path)
        digest.update(b"\0")
        digest.update(encoded_mode)
        digest.update(b"\0")
        digest.update(str(stat.S_IMODE(metadata.st_mode)).encode("ascii"))
        digest.update(b"\0")
        digest.update(kind)
        digest.update(b"\0")
        digest.update(hashlib.sha256(content).digest())
        digest.update(b"\n")
        paths.append(path)
        if time.monotonic() >= deadline:
            raise HistoricalTimeout("P12 historical tracked checkout inspection timed out")
    if len(paths) != len(set(paths)) or len({path.casefold() for path in paths}) != len(paths):
        raise P12GateError("P12 historical tracked checkout contains an alias")
    return hashlib.sha256(raw).hexdigest(), digest.hexdigest()


def _checkout_metadata(
    checkout: Path,
    *,
    deadline: float,
    opaque_roots: tuple[str, ...] = (),
) -> dict[str, tuple[str, int]]:
    opaque_parts = {Path(value).parts for value in opaque_roots}
    result: dict[str, tuple[str, int]] = {}
    casefolded: set[str] = set()
    pending: list[tuple[Path, tuple[str, ...]]] = [(checkout, ())]
    while pending:
        directory, prefix = pending.pop()
        try:
            entries = sorted(os.scandir(directory), key=lambda item: os.fsencode(item.name))
        except OSError as exc:
            raise P12GateError("P12 historical checkout metadata is unreadable") from exc
        for entry in entries:
            parts = (*prefix, entry.name)
            if parts == (".git",):
                continue
            path = _safe_checkout_relative(Path(*parts).as_posix())
            folded = path.casefold()
            if folded in casefolded:
                raise P12GateError("P12 historical checkout metadata contains a case alias")
            casefolded.add(folded)
            try:
                metadata = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise P12GateError("P12 historical checkout metadata is unreadable") from exc
            if stat.S_ISLNK(metadata.st_mode):
                kind = "symlink"
            elif stat.S_ISDIR(metadata.st_mode):
                kind = "directory"
            elif stat.S_ISREG(metadata.st_mode):
                kind = "regular"
            else:
                raise P12GateError("P12 historical checkout contains a special file")
            result[path] = (kind, stat.S_IMODE(metadata.st_mode))
            if kind == "directory" and parts not in opaque_parts:
                pending.append((Path(entry.path), parts))
        if time.monotonic() >= deadline:
            raise HistoricalTimeout("P12 historical checkout metadata inspection timed out")
    return result


@dataclass(frozen=True)
class _HistoricalCheckoutGuard:
    checkout: Path
    head: str
    index_digest: str
    tracked_digest: str
    metadata: dict[str, tuple[str, int]]

    @classmethod
    def capture(cls, checkout: Path, *, deadline: float) -> _HistoricalCheckoutGuard:
        status = _checkout_status_paths(checkout, deadline=deadline)
        if status:
            raise P12GateError("P12 historical checkout was not clean before npm setup")
        head = (
            _historical_process(
                ["git", "rev-parse", "HEAD"],
                cwd=checkout,
                environment=None,
                deadline=deadline,
                limit=60,
                label="historical checkout HEAD identity",
            )
            .decode("ascii")
            .strip()
        )
        index_digest, tracked_digest = _tracked_checkout_identity(checkout, deadline=deadline)
        metadata = _checkout_metadata(checkout, deadline=deadline)
        for generated in NPM_GENERATED_DIRECTORIES:
            path = f"studio/{generated}"
            if path in metadata:
                raise P12GateError("P12 historical checkout contains pre-existing npm residue")
        return cls(checkout, head, index_digest, tracked_digest, metadata)

    def _assert_tracked(self, *, deadline: float) -> None:
        head = (
            _historical_process(
                ["git", "rev-parse", "HEAD"],
                cwd=self.checkout,
                environment=None,
                deadline=deadline,
                limit=60,
                label="historical checkout HEAD identity",
            )
            .decode("ascii")
            .strip()
        )
        index_digest, tracked_digest = _tracked_checkout_identity(self.checkout, deadline=deadline)
        if (
            head != self.head
            or index_digest != self.index_digest
            or tracked_digest != self.tracked_digest
        ):
            raise P12GateError("P12 historical tracked bytes, mode, or index drifted")

    def assert_clean(self, *, deadline: float) -> None:
        self._assert_tracked(deadline=deadline)
        if _checkout_metadata(self.checkout, deadline=deadline) != self.metadata:
            raise P12GateError("P12 historical checkout metadata residue remains")
        if _checkout_status_paths(self.checkout, deadline=deadline):
            raise P12GateError("P12 historical checkout residue remains")

    def generated_tsbuildinfo(self, *, deadline: float) -> tuple[Path, ...]:
        dynamic_roots = tuple(f"studio/{value}" for value in NPM_GENERATED_DIRECTORIES)
        current = _checkout_metadata(
            self.checkout,
            deadline=deadline,
            opaque_roots=dynamic_roots,
        )
        generated: list[Path] = []
        filtered: dict[str, tuple[str, int]] = {}
        for path, identity in current.items():
            parts = Path(path).parts
            if any(parts[: len(Path(root).parts)] == Path(root).parts for root in dynamic_roots):
                continue
            if (
                path not in self.metadata
                and parts
                and parts[0] == "studio"
                and path.endswith(".tsbuildinfo")
            ):
                if identity[0] != "regular":
                    raise P12GateError("P12 historical generated tsbuildinfo is unsafe")
                generated.append(self.checkout.joinpath(*parts))
                continue
            filtered[path] = identity
        if filtered != self.metadata:
            raise P12GateError("P12 historical npm command changed unapproved checkout state")
        return tuple(sorted(generated, key=lambda value: os.fsencode(value.as_posix())))

    def assert_npm_residue(
        self,
        *,
        deadline: float,
        installed_only: bool,
    ) -> tuple[Path, ...]:
        self._assert_tracked(deadline=deadline)
        generated = self.generated_tsbuildinfo(deadline=deadline)
        allowed_roots = (
            ("studio/node_modules",)
            if installed_only
            else tuple(f"studio/{value}" for value in NPM_GENERATED_DIRECTORIES)
        )
        for path in _checkout_status_paths(self.checkout, deadline=deadline):
            parts = Path(path).parts
            in_allowed_root = any(
                parts[: len(Path(root).parts)] == Path(root).parts for root in allowed_roots
            )
            if not in_allowed_root and self.checkout.joinpath(*parts) not in generated:
                raise P12GateError("P12 historical npm command left unexpected residue")
        if installed_only and generated:
            raise P12GateError("P12 historical npm setup left unexpected residue")
        return generated


def _device_id(path: Path) -> int:
    return os.stat(path, follow_symlinks=False).st_dev


def _validate_plain_directory(path: Path, *, mode: int | None = None) -> None:
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise P12GateError("P12 historical npm directory is unavailable") from exc
    if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise P12GateError("P12 historical npm directory is not physical")
    if mode is not None and stat.S_IMODE(metadata.st_mode) != mode:
        raise P12GateError("P12 historical npm holding directory mode drifted")


def _validate_no_symlink_tree(path: Path) -> None:
    _validate_plain_directory(path)
    pending = [path]
    while pending:
        directory = pending.pop()
        try:
            entries = list(os.scandir(directory))
        except OSError as exc:
            raise P12GateError("P12 historical generated directory is unreadable") from exc
        for entry in entries:
            try:
                metadata = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise P12GateError("P12 historical generated path is unreadable") from exc
            if stat.S_ISLNK(metadata.st_mode):
                raise P12GateError("P12 historical generated directory contains a symlink")
            if stat.S_ISDIR(metadata.st_mode):
                pending.append(Path(entry.path))
            elif not stat.S_ISREG(metadata.st_mode):
                raise P12GateError("P12 historical generated directory contains a special file")


def _remove_generated_directory(path: Path, *, allow_internal_symlinks: bool) -> None:
    _validate_plain_directory(path)
    if not allow_internal_symlinks:
        _validate_no_symlink_tree(path)
    try:
        shutil.rmtree(path)
    except OSError as exc:
        raise P12GateError("P12 historical generated directory cleanup failed") from exc


class _HistoricalNpmWorkspace:
    def __init__(
        self,
        *,
        object_directory: Path,
        guard: _HistoricalCheckoutGuard,
        npm_gate_ids: tuple[str, ...],
    ) -> None:
        if not npm_gate_ids:
            raise P12GateError("P12 historical npm lifecycle lacks a gate block")
        self.guard = guard
        self.workspace = guard.checkout / "studio"
        self.holding_root = object_directory / "npm-holding"
        self.payload = self.holding_root / "node_modules"
        self.npm_gate_ids = npm_gate_ids
        self.phase = "installed_in_checkout"
        _validate_plain_directory(self.workspace)
        try:
            object_root = object_directory.resolve(strict=True)
            checkout_root = guard.checkout.resolve(strict=True)
            workspace_root = self.workspace.resolve(strict=True)
        except OSError as exc:
            raise P12GateError("P12 historical npm workspace identity is invalid") from exc
        if workspace_root != checkout_root / "studio" or object_root == checkout_root:
            raise P12GateError("P12 historical npm workspace escaped its exact checkout")
        try:
            self.holding_root.mkdir(mode=0o700)
        except OSError as exc:
            raise P12GateError("P12 historical npm holding directory creation failed") from exc
        _validate_plain_directory(self.holding_root, mode=0o700)
        if self.holding_root.parent.resolve(strict=True) != object_root:
            raise P12GateError("P12 historical npm holding directory escaped its object")
        if _device_id(self.holding_root) != _device_id(guard.checkout):
            raise P12GateError("P12 historical npm holding directory is cross-filesystem")
        self._assert_holding_layout(payload_expected=False)
        self._assert_endpoint_pair(source_expected=True)

    def _assert_holding_layout(self, *, payload_expected: bool) -> None:
        _validate_plain_directory(self.holding_root, mode=0o700)
        try:
            entries = list(os.scandir(self.holding_root))
        except OSError as exc:
            raise P12GateError("P12 historical npm holding directory is unreadable") from exc
        names = {entry.name for entry in entries}
        expected = {"node_modules"} if payload_expected else set()
        if names != expected or names & {"package.json", "package-lock.json"}:
            raise P12GateError("P12 historical npm holding directory layout drifted")
        if payload_expected:
            _validate_plain_directory(self.payload)

    def _assert_endpoint_pair(self, *, source_expected: bool) -> None:
        source_exists = self.workspace.joinpath("node_modules").exists()
        destination_exists = self.payload.exists()
        if source_exists == destination_exists or source_exists != source_expected:
            raise P12GateError("P12 historical npm payload endpoint state is invalid")
        target = self.workspace / "node_modules" if source_expected else self.payload
        _validate_plain_directory(target)

    def park(self, *, deadline: float) -> None:
        if self.phase != "installed_in_checkout":
            raise P12GateError("P12 historical npm lifecycle phase is invalid")
        self.guard.assert_npm_residue(deadline=deadline, installed_only=True)
        self._assert_holding_layout(payload_expected=False)
        self._assert_endpoint_pair(source_expected=True)
        os.replace(self.workspace / "node_modules", self.payload)
        self.phase = "parked"
        self._assert_endpoint_pair(source_expected=False)
        self._assert_holding_layout(payload_expected=True)
        self.guard.assert_clean(deadline=deadline)

    def activate(self, gate_id: str, *, deadline: float) -> None:
        if self.phase != "parked" or gate_id != self.npm_gate_ids[0]:
            raise P12GateError("P12 historical npm activation phase is invalid")
        self.guard.assert_clean(deadline=deadline)
        self._assert_holding_layout(payload_expected=True)
        self._assert_endpoint_pair(source_expected=False)
        if _device_id(self.holding_root) != _device_id(self.guard.checkout):
            raise P12GateError("P12 historical npm activation became cross-filesystem")
        os.replace(self.payload, self.workspace / "node_modules")
        self.phase = "active_for_npm_block"
        self._assert_endpoint_pair(source_expected=True)
        self._assert_holding_layout(payload_expected=False)
        self.guard.assert_npm_residue(deadline=deadline, installed_only=False)

    def command_cwd(self, gate_id: str) -> Path:
        if self.phase != "active_for_npm_block" or gate_id not in self.npm_gate_ids:
            raise P12GateError("P12 historical npm command phase is invalid")
        if self.workspace == self.holding_root or self.workspace == self.payload:
            raise P12GateError("P12 historical npm command cannot use the holding directory")
        return self.workspace

    def assert_active(self, *, deadline: float) -> None:
        if self.phase != "active_for_npm_block":
            raise P12GateError("P12 historical npm lifecycle phase is invalid")
        self._assert_endpoint_pair(source_expected=True)
        self._assert_holding_layout(payload_expected=False)
        self.guard.assert_npm_residue(deadline=deadline, installed_only=False)

    def retire(self, *, deadline: float) -> None:
        self.assert_active(deadline=deadline)
        generated = self.guard.generated_tsbuildinfo(deadline=deadline)
        os.replace(self.workspace / "node_modules", self.payload)
        self.phase = "retiring"
        self._assert_endpoint_pair(source_expected=False)
        self._assert_holding_layout(payload_expected=True)
        _remove_generated_directory(self.payload, allow_internal_symlinks=True)
        for name in NPM_GENERATED_DIRECTORIES[1:]:
            target = self.workspace / name
            if target.exists() or target.is_symlink():
                _remove_generated_directory(target, allow_internal_symlinks=False)
        for target in generated:
            try:
                metadata = os.lstat(target)
            except OSError as exc:
                raise P12GateError("P12 historical generated tsbuildinfo is unavailable") from exc
            if target.is_symlink() or not stat.S_ISREG(metadata.st_mode):
                raise P12GateError("P12 historical generated tsbuildinfo is unsafe")
            target.unlink()
        self.phase = "retired"
        self._assert_holding_layout(payload_expected=False)
        self.guard.assert_clean(deadline=deadline)

    def before_leaf(self, item: dict[str, Any], *, deadline: float) -> Path:
        gate_id = str(item.get("gate_id"))
        if item.get("command_kind") == "npm_script":
            if gate_id == self.npm_gate_ids[0]:
                self.activate(gate_id, deadline=deadline)
            elif self.phase != "active_for_npm_block" or gate_id not in self.npm_gate_ids:
                raise P12GateError("P12 historical npm gate block is discontinuous")
            return self.command_cwd(gate_id)
        if self.phase == "active_for_npm_block":
            raise P12GateError("P12 historical npm gate block is discontinuous")
        self.guard.assert_clean(deadline=deadline)
        return self.guard.checkout

    def after_leaf(self, item: dict[str, Any], status: int, *, deadline: float) -> None:
        gate_id = str(item.get("gate_id"))
        if item.get("command_kind") != "npm_script":
            self.guard.assert_clean(deadline=deadline)
            return
        if status != 0 or gate_id == self.npm_gate_ids[-1]:
            self.retire(deadline=deadline)
        else:
            self.assert_active(deadline=deadline)

    def assert_object_end(self, *, failed: bool, deadline: float) -> None:
        if self.phase == "active_for_npm_block":
            raise P12GateError("P12 historical npm block ended without retirement")
        if not failed and self.phase != "retired":
            raise P12GateError("P12 historical npm block did not execute exactly once")
        if self.phase == "parked":
            self._assert_endpoint_pair(source_expected=False)
            self._assert_holding_layout(payload_expected=True)
        elif self.phase == "retired":
            self._assert_holding_layout(payload_expected=False)
        self.guard.assert_clean(deadline=deadline)


def _verify_historical_entrypoint(
    checkout: Path,
    item: dict[str, Any],
    *,
    deadline: float,
    cleanup_deadline: float | None = None,
) -> None:
    if cleanup_deadline is None:
        cleanup_deadline = deadline
    entrypoint = item.get("entrypoint")
    if entrypoint is None:
        return
    if not isinstance(entrypoint, dict):
        raise P12GateError("P12 historical entrypoint metadata is invalid")
    path = entrypoint.get("path")
    blob = entrypoint.get("blob")
    mode = entrypoint.get("mode")
    if not isinstance(path, str) or not isinstance(blob, str) or mode != "100644":
        raise P12GateError("P12 historical entrypoint identity is incomplete")
    target = checkout / path
    if target.is_symlink() or not target.is_file():
        raise P12GateError("P12 historical entrypoint is not a regular checkout file")
    actual = (
        _historical_process(
            ["git", "rev-parse", f"HEAD:{path}"],
            cwd=checkout,
            environment=None,
            deadline=deadline,
            cleanup_deadline=cleanup_deadline,
            limit=60,
            label="entrypoint commit identity",
        )
        .decode("ascii")
        .strip()
    )
    working = (
        _historical_process(
            ["git", "hash-object", path],
            cwd=checkout,
            environment=None,
            deadline=deadline,
            cleanup_deadline=cleanup_deadline,
            limit=60,
            label="entrypoint worktree identity",
        )
        .decode("ascii")
        .strip()
    )
    listing = (
        _historical_process(
            ["git", "ls-tree", "HEAD", "--", path],
            cwd=checkout,
            environment=None,
            deadline=deadline,
            cleanup_deadline=cleanup_deadline,
            limit=60,
            label="entrypoint mode identity",
        )
        .decode("utf-8")
        .removesuffix("\n")
    )
    if actual != blob or working != blob or listing != f"100644 blob {blob}\t{path}":
        raise P12GateError("P12 historical entrypoint blob resolution drifted")
    historical_inventory.validate_entrypoint_resolution(
        item,
        checkout_root=checkout,
        resolved_path=target,
        resolved_blob=working,
    )


def _verify_anchor(
    checkout: Path,
    item: dict[str, Any],
    *,
    deadline: float | None = None,
    cleanup_deadline: float | None = None,
) -> None:
    if deadline is None:
        declared = item.get("timeout_seconds")
        if not isinstance(declared, int) or isinstance(declared, bool) or declared <= 0:
            raise P12GateError("P12 historical evidence anchor timeout is invalid")
        deadline = time.monotonic() + declared
    if cleanup_deadline is None:
        cleanup_deadline = deadline
    expected = item.get("expected")
    if not isinstance(expected, dict):
        raise P12GateError("P12 historical evidence anchor is incomplete")
    anchor_commit = expected.get("anchor_commit")
    anchor_tree = expected.get("anchor_tree")
    path = expected.get("path")
    blob = expected.get("blob")
    sha256 = expected.get("sha256")
    if not all(
        isinstance(value, str) and value
        for value in (anchor_commit, anchor_tree, path, blob, sha256)
    ):
        raise P12GateError("P12 historical evidence anchor identity is incomplete")
    actual_tree = (
        _historical_process(
            ["git", "rev-parse", f"{anchor_commit}^{{tree}}"],
            cwd=checkout,
            environment=None,
            deadline=deadline,
            cleanup_deadline=cleanup_deadline,
            limit=120,
            label="anchor tree identity",
        )
        .decode("ascii")
        .strip()
    )
    actual_blob = (
        _historical_process(
            ["git", "rev-parse", f"{anchor_commit}:{path}"],
            cwd=checkout,
            environment=None,
            deadline=deadline,
            cleanup_deadline=cleanup_deadline,
            limit=120,
            label="anchor blob identity",
        )
        .decode("ascii")
        .strip()
    )
    if actual_tree != anchor_tree or actual_blob != blob:
        raise P12GateError("P12 historical evidence anchor Git identity drifted")
    encoded = _git_bytes(
        checkout,
        f"{anchor_commit}:{path}",
        deadline=deadline,
        cleanup_deadline=cleanup_deadline,
    )
    if hashlib.sha256(encoded).hexdigest() != sha256:
        raise P12GateError("P12 historical evidence anchor SHA-256 drifted")
    expectations = expected.get("json_expectations")
    pointer_expectations = expected.get("json_pointer_expectations")
    if expectations is not None or pointer_expectations is not None:
        try:
            value = parse_json_unique(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError, P12GateError) as exc:
            raise P12GateError("P12 historical evidence anchor JSON is malformed") from exc
        if not isinstance(value, dict):
            raise P12GateError("P12 historical evidence anchor content drifted")
        if expectations is not None:
            if not isinstance(expectations, dict):
                raise P12GateError("P12 historical evidence anchor content drifted")
            for key, expected_value in expectations.items():
                if key == "compose_environment_host":
                    compose = value.get("compose_runtime")
                    environment = compose.get("environment") if isinstance(compose, dict) else None
                    actual = environment.get("host") if isinstance(environment, dict) else None
                elif key == "compose_status":
                    compose = value.get("compose_runtime")
                    actual = compose.get("status") if isinstance(compose, dict) else None
                else:
                    actual = value.get(key)
                if actual != expected_value:
                    raise P12GateError("P12 historical evidence anchor content drifted")
        if pointer_expectations is not None:
            if not isinstance(pointer_expectations, dict):
                raise P12GateError("P12 historical evidence anchor content drifted")
            for pointer, expected_value in pointer_expectations.items():
                if not isinstance(pointer, str) or not pointer.startswith("/"):
                    raise P12GateError("P12 historical evidence anchor JSON pointer is invalid")
                pointer_actual: object = value
                for token in pointer[1:].split("/"):
                    token = token.replace("~1", "/").replace("~0", "~")
                    if not isinstance(pointer_actual, dict) or token not in pointer_actual:
                        raise P12GateError("P12 historical evidence anchor JSON pointer is absent")
                    pointer_actual = pointer_actual[token]
                if pointer_actual != expected_value:
                    raise P12GateError("P12 historical evidence anchor content drifted")


def _verify_working_lock(
    checkout: Path,
    item: dict[str, Any],
    *,
    deadline: float,
    cleanup_deadline: float,
) -> None:
    """Bind one consumed working lock file to its declared immutable blob."""

    expected = item.get("expected")
    path = expected.get("path") if isinstance(expected, dict) else None
    blob = expected.get("blob") if isinstance(expected, dict) else None
    if (
        item.get("item_type") != "evidence_anchor"
        or not isinstance(path, str)
        or not path
        or Path(path).is_absolute()
        or ".." in Path(path).parts
        or not isinstance(blob, str)
        or SHA.fullmatch(blob) is None
    ):
        raise P12GateError("P12 historical working lock identity is incomplete")
    target = checkout / path
    try:
        checkout_root = checkout.resolve(strict=True)
        resolved_target = target.resolve(strict=True)
        metadata = os.lstat(target)
        resolved_target.relative_to(checkout_root)
    except (OSError, ValueError) as exc:
        raise P12GateError("P12 historical working lock path is invalid") from exc
    if (
        target.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o644
        or resolved_target != checkout_root / path
    ):
        raise P12GateError("P12 historical working lock is not an exact regular file")
    actual = (
        _historical_process(
            ["git", "rev-parse", f"HEAD:{path}"],
            cwd=checkout,
            environment=None,
            deadline=deadline,
            cleanup_deadline=cleanup_deadline,
            limit=60,
            label="working lock commit identity",
        )
        .decode("ascii")
        .strip()
    )
    working = (
        _historical_process(
            ["git", "hash-object", "--no-filters", "--", path],
            cwd=checkout,
            environment=None,
            deadline=deadline,
            cleanup_deadline=cleanup_deadline,
            limit=60,
            label="working lock content identity",
        )
        .decode("ascii")
        .strip()
    )
    listing = (
        _historical_process(
            ["git", "ls-tree", "HEAD", "--", path],
            cwd=checkout,
            environment=None,
            deadline=deadline,
            cleanup_deadline=cleanup_deadline,
            limit=60,
            label="working lock mode identity",
        )
        .decode("utf-8")
        .removesuffix("\n")
    )
    if actual != blob or working != blob or listing != f"100644 blob {blob}\t{path}":
        raise P12GateError("P12 historical working lock blob or mode drifted")


def _historical_setup(
    root: Path,
    object_directory: Path,
    setup: dict[str, Any],
    object_items: list[dict[str, Any]],
    *,
    deadline: float,
) -> tuple[
    Path,
    Path,
    dict[str, str],
    _HistoricalCheckoutGuard,
    _HistoricalNpmWorkspace | None,
    str,
]:
    object_name = str(setup["object"]).lower()
    checkout = object_directory / "checkout"
    environment_path = object_directory / "python-environment"
    output = object_directory / "output"
    output.mkdir(mode=0o700)
    project = f"dcp12{object_name}{secrets.token_hex(6)}"
    work_deadline = deadline - OBJECT_CLEANUP_RESERVE_SECONDS
    if work_deadline <= time.monotonic():
        raise HistoricalTimeout(f"P12 historical {object_name} setup timed out")

    checkout_deadline = _operation_deadline(
        work_deadline,
        OPERATION_TIMEOUTS["checkout_ref"],
        label=f"{object_name} checkout/ref setup",
    )
    _historical_process(
        ["git", "clone", "--quiet", "--shared", "--no-checkout", str(root), str(checkout)],
        cwd=object_directory,
        environment=None,
        deadline=checkout_deadline,
        cleanup_deadline=deadline,
        limit=OPERATION_TIMEOUTS["checkout_ref"],
        label=f"{object_name} checkout clone",
    )
    ref_layout = setup.get("ref_layout")
    if not isinstance(ref_layout, dict):
        raise P12GateError("P12 historical ref layout is invalid")
    branch_ref = ref_layout.get("branch_ref")
    head = ref_layout.get("head")
    main = ref_layout.get("main")
    origin_main = ref_layout.get("origin_main")
    if not all(
        isinstance(value, str) and value for value in (branch_ref, head, main, origin_main)
    ) or not str(branch_ref).startswith("refs/heads/"):
        raise P12GateError("P12 historical ref layout is incomplete")
    branch = str(branch_ref).removeprefix("refs/heads/")
    _historical_process(
        ["git", "checkout", "--quiet", "-B", str(branch), str(head)],
        cwd=checkout,
        environment=None,
        deadline=checkout_deadline,
        cleanup_deadline=deadline,
        limit=OPERATION_TIMEOUTS["checkout_ref"],
        label=f"{object_name} checkout ref",
    )
    _historical_process(
        ["git", "branch", "--force", "main", str(main)],
        cwd=checkout,
        environment=None,
        deadline=checkout_deadline,
        cleanup_deadline=deadline,
        limit=OPERATION_TIMEOUTS["checkout_ref"],
        label=f"{object_name} main ref",
    )
    _historical_process(
        ["git", "update-ref", "refs/remotes/origin/main", str(origin_main)],
        cwd=checkout,
        environment=None,
        deadline=checkout_deadline,
        cleanup_deadline=deadline,
        limit=OPERATION_TIMEOUTS["checkout_ref"],
        label=f"{object_name} origin/main ref",
    )
    actual_head = (
        _historical_process(
            ["git", "rev-parse", "HEAD"],
            cwd=checkout,
            environment=None,
            deadline=checkout_deadline,
            cleanup_deadline=deadline,
            limit=OPERATION_TIMEOUTS["checkout_ref"],
            label=f"{object_name} HEAD identity",
        )
        .decode("ascii")
        .strip()
    )
    actual_tree = (
        _historical_process(
            ["git", "rev-parse", "HEAD^{tree}"],
            cwd=checkout,
            environment=None,
            deadline=checkout_deadline,
            cleanup_deadline=deadline,
            limit=OPERATION_TIMEOUTS["checkout_ref"],
            label=f"{object_name} tree identity",
        )
        .decode("ascii")
        .strip()
    )
    if actual_head != setup.get("commit"):
        raise P12GateError("P12 historical checkout HEAD drifted")
    if actual_tree != setup.get("tree"):
        raise P12GateError("P12 historical checkout tree drifted")

    resources = setup.get("resources")
    if (
        not isinstance(resources, dict)
        or resources.get("checkout_count") != 1
        or resources.get("python_environment_count") != 1
        or resources.get("object_timeout_seconds") != OBJECT_TIMEOUTS[str(setup["object"])]
    ):
        raise P12GateError("P12 historical setup resource model drifted")
    npm_gate_ids = _npm_gate_block(
        str(setup["object"]),
        object_items,
        npm_workspace_count=resources.get("npm_workspace_count"),
    )
    lock_ids = resources.get("lock_anchor_ids")
    if not isinstance(lock_ids, list) or any(not isinstance(value, str) for value in lock_ids):
        raise P12GateError("P12 historical setup lock-anchor binding is invalid")
    anchor_by_id = {
        str(item["gate_id"]): item
        for item in object_items
        if item.get("item_type") == "evidence_anchor"
    }
    if set(lock_ids) - set(anchor_by_id):
        raise P12GateError("P12 historical setup names an unavailable lock anchor")
    for gate_id in lock_ids:
        anchor = anchor_by_id[gate_id]
        declared = anchor.get("timeout_seconds")
        if not isinstance(declared, int) or isinstance(declared, bool) or declared <= 0:
            raise P12GateError("P12 historical setup lock-anchor timeout is invalid")
        _verify_anchor(
            checkout,
            anchor,
            deadline=_operation_deadline(
                work_deadline,
                declared,
                label=f"{object_name} setup lock anchor",
            ),
            cleanup_deadline=deadline,
        )

    python_deadline = _operation_deadline(
        work_deadline,
        OPERATION_TIMEOUTS["venv_install"],
        label=f"{object_name} Python setup",
    )
    _historical_process(
        [sys.executable, "-m", "venv", str(environment_path)],
        cwd=checkout,
        environment=None,
        deadline=python_deadline,
        cleanup_deadline=deadline,
        limit=OPERATION_TIMEOUTS["venv_install"],
        label=f"{object_name} Python environment creation",
    )
    python = environment_path / "bin" / "python"
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "P10_REMOTE_USE_INSTALLED_TOOLS": "1",
            "TMPDIR": str(output),
            "PIP_CACHE_DIR": str(object_directory / "pip-cache"),
            "PIP_CONFIG_FILE": os.devnull,
            "NPM_CONFIG_CACHE": str(object_directory / "npm-cache"),
            "COMPOSE_PROJECT_NAME": project,
            "PYTHONPATH": os.pathsep.join((str(checkout), str(checkout / "src"))),
        }
    )
    python_lock = anchor_by_id.get(f"{object_name}_python_lock_anchor")
    if not isinstance(python_lock, dict):
        raise P12GateError("P12 historical Python lock anchor is unavailable")
    _verify_working_lock(
        checkout,
        python_lock,
        deadline=python_deadline,
        cleanup_deadline=deadline,
    )
    _historical_process(
        [
            str(python),
            "-m",
            "pip",
            "--disable-pip-version-check",
            "--isolated",
            "install",
            "--require-hashes",
            "--no-deps",
            "--no-cache-dir",
            "-r",
            "requirements/p8.lock",
        ],
        cwd=checkout,
        environment=environment,
        deadline=python_deadline,
        cleanup_deadline=deadline,
        limit=OPERATION_TIMEOUTS["venv_install"],
        label=f"{object_name} hash-locked Python installation",
    )
    guard = _HistoricalCheckoutGuard.capture(checkout, deadline=work_deadline)
    npm_lifecycle: _HistoricalNpmWorkspace | None = None
    if npm_gate_ids:
        npm_workspace = checkout / "studio"
        npm_deadline = _operation_deadline(
            work_deadline,
            OPERATION_TIMEOUTS["npm_install"],
            label=f"{object_name} npm setup",
        )
        npm_lock = anchor_by_id.get(f"{object_name}_npm_lock_anchor")
        if not isinstance(npm_lock, dict):
            raise P12GateError("P12 historical npm lock anchor is unavailable")
        _verify_working_lock(
            checkout,
            npm_lock,
            deadline=npm_deadline,
            cleanup_deadline=deadline,
        )
        status, _ = _leaf_process(
            ["corepack", "npm", "ci", "--ignore-scripts", "--no-audit", "--fund=false"],
            cwd=npm_workspace,
            environment=environment,
            timeout=_remaining_timeout(
                npm_deadline,
                OPERATION_TIMEOUTS["npm_install"],
                label=f"{object_name} npm setup",
            ),
            cleanup_deadline=deadline,
        )
        if status == 124:
            raise HistoricalTimeout(f"P12 historical {object_name} npm setup timed out")
        if status == 126:
            raise HistoricalResidueError(
                f"P12 historical {object_name} npm setup left process residue"
            )
        if status != 0:
            raise P12GateError(f"P12 historical {object_name} npm setup failed")
        npm_lifecycle = _HistoricalNpmWorkspace(
            object_directory=object_directory,
            guard=guard,
            npm_gate_ids=npm_gate_ids,
        )
        npm_lifecycle.park(deadline=npm_deadline)
    else:
        guard.assert_clean(deadline=work_deadline)
    return checkout, python, environment, guard, npm_lifecycle, project


HISTORICAL_RESULT_MAX_BYTES = 1_048_576
HISTORICAL_RESULT_PARSE_RESERVE_SECONDS = 5


def _command_timeout(item: dict[str, Any], deadline: float, *, reserve: int = 0) -> float:
    declared = item.get("timeout_seconds")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared <= 0:
        raise P12GateError("P12 historical item timeout is invalid")
    return _remaining_timeout(deadline, declared, label="leaf operation", reserve=reserve)


def _structured_result_path(
    item: dict[str, Any],
    *,
    command_text: str,
    output_directory: Path,
) -> Path | None:
    expected = item.get("expected")
    if not isinstance(expected, dict):
        return None
    test_count = expected.get("test_count")
    if not isinstance(test_count, int) or isinstance(test_count, bool):
        return None
    arguments = shlex.split(command_text)
    positions = [index for index, value in enumerate(arguments) if value == "--json-output"]
    if len(positions) != 1 or positions[0] + 1 >= len(arguments):
        raise P12GateError("P12 historical unittest output binding is absent")
    candidate = Path(arguments[positions[0] + 1])
    if (
        not candidate.is_absolute()
        or candidate.parent != output_directory
        or candidate.name in {"", ".", ".."}
    ):
        raise P12GateError("P12 historical unittest output path escaped its object")
    return candidate


def _bounded_result_bytes(path: Path, *, deadline: float) -> bytes:
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise P12GateError("P12 historical unittest output directory is invalid")
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise P12GateError("P12 historical unittest result is unavailable") from exc
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or not 0 <= metadata.st_size <= HISTORICAL_RESULT_MAX_BYTES
        ):
            raise P12GateError("P12 historical unittest result file is invalid")
        chunks: list[bytes] = []
        total = 0
        while True:
            if time.monotonic() >= deadline:
                raise HistoricalTimeout("P12 historical unittest result parsing timed out")
            chunk = os.read(descriptor, min(65_536, HISTORICAL_RESULT_MAX_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > HISTORICAL_RESULT_MAX_BYTES:
                raise P12GateError("P12 historical unittest result is oversized")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _structured_leaf_result(
    item: dict[str, Any],
    result_path: Path | None,
    *,
    process_status: int,
    deadline: float,
) -> dict[str, int] | None:
    expected = item.get("expected")
    if not isinstance(expected, dict):
        return None
    test_count = expected.get("test_count")
    if not isinstance(test_count, int) or isinstance(test_count, bool):
        return None
    if result_path is None:
        raise P12GateError("P12 historical unittest output binding is absent")
    try:
        value = parse_json_unique(_bounded_result_bytes(result_path, deadline=deadline))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise P12GateError("P12 historical unittest result is malformed") from exc
    if time.monotonic() >= deadline:
        raise HistoricalTimeout("P12 historical unittest result parsing timed out")
    count_values: dict[str, int] = {}
    for key in ("tests_run", "failures", "errors", "skipped"):
        candidate = value.get(key) if isinstance(value, dict) else None
        if isinstance(candidate, bool) or not isinstance(candidate, int) or candidate < 0:
            raise P12GateError("P12 historical unittest counts are malformed")
        count_values[key] = candidate
    gate_passed = value.get("gate_passed") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or count_values["tests_run"] != test_count
        or type(gate_passed) is not bool
        or gate_passed != (process_status == 0)
        or (
            process_status == 0
            and any(count_values[key] != 0 for key in ("failures", "errors", "skipped"))
        )
    ):
        raise P12GateError("P12 historical unittest count or outcome drifted")
    return count_values


def _execute_history_item(
    item: dict[str, Any],
    *,
    checkout: Path,
    python: Path,
    environment: dict[str, str],
    npm_workspace: Path | None,
    output_directory: Path,
    predecessor_result: tuple[bytes, str] | None,
    inventory_digest: str,
    deadline: float,
) -> tuple[int, bytes, dict[str, int] | None]:
    work_deadline = deadline - OBJECT_CLEANUP_RESERVE_SECONDS
    declared = item.get("timeout_seconds")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared <= 0:
        raise P12GateError("P12 historical item timeout is invalid")
    operation_deadline = _operation_deadline(
        work_deadline,
        declared,
        label="leaf operation",
    )
    kind = item.get("command_kind")
    if kind == "predecessor_result":
        if predecessor_result is None:
            raise P12GateError("P12 historical predecessor result is unavailable")
        raw, digest = predecessor_result
        historical_inventory.validate_predecessor_result(
            str(item["object"]),
            object_result_bytes=raw,
            object_result_digest_value=digest,
            inventory_digest=inventory_digest,
        )
        return 0, b"", None
    if kind == "identity_check":
        _verify_anchor(
            checkout,
            item,
            deadline=operation_deadline,
            cleanup_deadline=deadline,
        )
        return 0, b"", None
    command_text = item.get("command")
    if not isinstance(command_text, str) or not command_text:
        raise P12GateError("P12 historical leaf command is invalid")
    object_name = str(item["object"]).lower()
    command_text = command_text.replace(f"<{object_name}-python>", str(python))
    command_text = command_text.replace(f"<{object_name}-temp>", str(output_directory))
    if "<" in command_text or ">" in command_text:
        raise P12GateError("P12 historical command contains an unresolved placeholder")
    result_path = _structured_result_path(
        item,
        command_text=command_text,
        output_directory=output_directory,
    )
    if kind in {"python_script", "python_function", "npm_script"}:
        _verify_historical_entrypoint(
            checkout,
            item,
            deadline=operation_deadline,
            cleanup_deadline=deadline,
        )
    if kind == "python_function":
        entrypoint = item.get("entrypoint")
        if not isinstance(entrypoint, dict) or entrypoint.get("callable") != "candidate_diff_check":
            raise P12GateError("P12 historical Python function identity is invalid")
        command = [
            str(python),
            "-B",
            "-c",
            (
                "from pathlib import Path; "
                "from scripts.p11_gate_support import candidate_diff_check; "
                "candidate_diff_check(Path('.'))"
            ),
        ]
    else:
        command = shlex.split(command_text)
    cwd = npm_workspace if kind == "npm_script" else checkout
    if cwd is None:
        raise P12GateError("P12 historical npm leaf lacks an object-scoped workspace")
    status, output = _leaf_process(
        command,
        cwd=cwd,
        environment=environment,
        timeout=_command_timeout(
            item,
            operation_deadline,
            reserve=(HISTORICAL_RESULT_PARSE_RESERVE_SECONDS if result_path else 0),
        ),
        cleanup_deadline=deadline,
    )
    if status == 126:
        raise HistoricalResidueError("P12 historical leaf left process residue")
    structured = None
    if status != 124:
        structured = _structured_leaf_result(
            item,
            result_path,
            process_status=status,
            deadline=operation_deadline,
        )
    return status, output, structured


def run_portable_history(root: Path, temporary: Path) -> dict[str, Any]:
    """Execute the literal 151-item manifest strictly object by object."""

    executor_deadline = time.monotonic() + OPERATION_TIMEOUTS["executor"]
    if OPERATION_TIMEOUTS["executor"] != 9_900:
        raise P12GateError("P12 portable executor deadline drifted")
    check_git_indirections(root)
    historical_inventory.check_historical_inventory(root)
    items = historical_inventory.load_inventory(root)
    if len(items) != ITEM_COUNTS["total"]:
        raise P12GateError("P12 portable inventory total changed before execution")
    inventory_digest = f"sha256:{hashlib.sha256(canonical_json(list(items))).hexdigest()}"
    if executor_deadline <= time.monotonic():
        raise HistoricalTimeout("P12 portable executor prechecks timed out")
    results: list[dict[str, object]] = []
    leaf_records: list[dict[str, object]] = []
    object_results: list[dict[str, object]] = []
    predecessor_result: tuple[bytes, str] | None = None
    total_python_tests = 0
    failure_seen = False
    failure_count = 0
    error_count = 0
    skip_count = 0

    def record(
        item: dict[str, Any],
        outcome: str,
        exit_status: int | None,
        *,
        started_at: str,
        safe_failure_category: str | None = None,
        structured_result: dict[str, int] | None = None,
    ) -> dict[str, object]:
        compact: dict[str, object] = {
            "gate_id": item["gate_id"],
            "item_type": item["item_type"],
            "result": outcome,
            "exit_status": exit_status,
        }
        if item.get("item_type") == "excluded_acceptance_gate":
            compact["platform_result"] = historical_inventory.excluded_platform_result(item)
            compact["embedded_anchor"] = item["embedded_anchor"]
        results.append(compact)
        leaf_records.append(
            {
                **compact,
                "command_identity": item["command"],
                "command_kind": item["command_kind"],
                "entrypoint_identity": item.get("entrypoint"),
                "started_at": started_at,
                "completed_at": _utc_now(),
                "safe_failure_category": safe_failure_category,
                "structured_result": (
                    {"exit_status": exit_status, "result": outcome}
                    if structured_result is None
                    else {
                        "exit_status": exit_status,
                        "result": outcome,
                        "unittest": structured_result,
                    }
                ),
            }
        )
        return compact

    for object_name in OBJECT_ORDER:
        object_items = [item for item in items if item.get("object") == object_name]
        if not object_items or object_items[0].get("item_type") != "setup":
            raise P12GateError("P12 historical object setup ordering is invalid")
        if failure_seen:
            for item in object_items:
                record(
                    item,
                    "not_run_due_to_prior_failure",
                    None,
                    started_at=_utc_now(),
                    safe_failure_category="prior_failure",
                )
            continue
        started = _utc_now()
        deadline = min(
            executor_deadline,
            time.monotonic() + OBJECT_TIMEOUTS[object_name],
        )
        object_directory = temporary / object_name.lower()
        project = ""
        failed = False
        guard: _HistoricalCheckoutGuard | None = None
        npm_lifecycle: _HistoricalNpmWorkspace | None = None
        object_result_start = len(results)
        docker_before = _docker_snapshot(
            deadline=deadline,
            reserve=OBJECT_CLEANUP_RESERVE_SECONDS,
        )
        object_directory.mkdir(mode=0o700, parents=True)
        try:
            setup_started = _utc_now()
            try:
                (
                    checkout,
                    python,
                    environment,
                    guard,
                    npm_lifecycle,
                    project,
                ) = _historical_setup(
                    root,
                    object_directory,
                    object_items[0],
                    object_items,
                    deadline=deadline,
                )
            except HistoricalResidueError:
                raise
            except HistoricalTimeout as exc:
                record(
                    object_items[0],
                    "failed",
                    124,
                    started_at=setup_started,
                    safe_failure_category=type(exc).__name__,
                )
                failed = True
                failure_seen = True
                failure_count += 1
                for item in object_items[1:]:
                    record(
                        item,
                        "not_run_due_to_prior_failure",
                        None,
                        started_at=_utc_now(),
                        safe_failure_category="prior_failure",
                    )
            except (OSError, UnicodeError, subprocess.SubprocessError, P12GateError) as exc:
                record(
                    object_items[0],
                    "failed",
                    2,
                    started_at=setup_started,
                    safe_failure_category=type(exc).__name__,
                )
                failed = True
                failure_seen = True
                failure_count += 1
                error_count += 1
                for item in object_items[1:]:
                    record(
                        item,
                        "not_run_due_to_prior_failure",
                        None,
                        started_at=_utc_now(),
                        safe_failure_category="prior_failure",
                    )
            else:
                record(object_items[0], "passed", 0, started_at=setup_started)
                for item in object_items[1:]:
                    item_type = item.get("item_type")
                    leaf_started = _utc_now()
                    if failed:
                        record(
                            item,
                            "not_run_due_to_prior_failure",
                            None,
                            started_at=leaf_started,
                            safe_failure_category="prior_failure",
                        )
                        continue
                    if item_type == "excluded_acceptance_gate":
                        if npm_lifecycle is not None:
                            npm_lifecycle.before_leaf(item, deadline=deadline)
                        elif guard is not None:
                            guard.assert_clean(deadline=deadline)
                        record(
                            item,
                            "not_run_platform_excluded",
                            None,
                            started_at=leaf_started,
                        )
                        continue
                    if deadline - time.monotonic() <= OBJECT_CLEANUP_RESERVE_SECONDS:
                        status = 124
                        failure_category = "object_timeout"
                        structured = None
                        if (
                            npm_lifecycle is not None
                            and npm_lifecycle.phase == "active_for_npm_block"
                        ):
                            npm_lifecycle.retire(deadline=deadline)
                    else:
                        status = 2
                        leaf_entered = False
                        try:
                            if npm_lifecycle is not None:
                                npm_workspace = npm_lifecycle.before_leaf(item, deadline=deadline)
                            else:
                                if guard is None:
                                    raise P12GateError(
                                        "P12 historical checkout guard is unavailable"
                                    )
                                guard.assert_clean(deadline=deadline)
                                npm_workspace = None
                            leaf_entered = True
                            try:
                                status, _, structured = _execute_history_item(
                                    item,
                                    checkout=checkout,
                                    python=python,
                                    environment=environment,
                                    npm_workspace=npm_workspace,
                                    output_directory=object_directory / "output",
                                    predecessor_result=predecessor_result,
                                    inventory_digest=inventory_digest,
                                    deadline=deadline,
                                )
                            finally:
                                if leaf_entered:
                                    if npm_lifecycle is not None:
                                        npm_lifecycle.after_leaf(item, status, deadline=deadline)
                                    elif guard is not None:
                                        guard.assert_clean(deadline=deadline)
                            failure_category = "leaf_timeout" if status == 124 else "leaf_nonzero"
                        except HistoricalResidueError:
                            raise
                        except HistoricalTimeout as exc:
                            status = 124
                            structured = None
                            failure_category = type(exc).__name__
                        except (
                            OSError,
                            UnicodeError,
                            subprocess.SubprocessError,
                            HistoricalInventoryError,
                            P12GateError,
                        ) as exc:
                            status = 2
                            structured = None
                            failure_category = type(exc).__name__
                            error_count += 1
                    if structured is not None:
                        total_python_tests += structured["tests_run"]
                    if status != 0:
                        failed = True
                        failure_seen = True
                        if structured is None:
                            failure_count += 1
                        else:
                            structured_failures = structured["failures"]
                            structured_errors = structured["errors"] + structured["skipped"]
                            if structured_failures + structured_errors == 0:
                                structured_errors = 1
                            failure_count += structured_failures
                            error_count += structured_errors
                        record(
                            item,
                            "failed",
                            status,
                            started_at=leaf_started,
                            safe_failure_category=failure_category,
                            structured_result=structured,
                        )
                        continue
                    result_name = (
                        "identity_verified" if item_type == "evidence_anchor" else "passed"
                    )
                    record(
                        item,
                        result_name,
                        None if item_type == "evidence_anchor" else 0,
                        started_at=leaf_started,
                        structured_result=structured,
                    )
                    expected = item.get("expected")
                    if (
                        structured is None
                        and isinstance(expected, dict)
                        and isinstance(expected.get("test_count"), int)
                    ):
                        raise P12GateError(
                            "P12 historical passed unittest has no structured result"
                        )
                if guard is None:
                    raise P12GateError("P12 historical checkout guard is unavailable")
                if npm_lifecycle is not None:
                    npm_lifecycle.assert_object_end(failed=failed, deadline=deadline)
                else:
                    guard.assert_clean(deadline=deadline)
        finally:
            cleanup_error: BaseException | None = None
            if project:
                try:
                    _cleanup_docker(project, deadline=deadline)
                except (OSError, UnicodeError, subprocess.SubprocessError, P12GateError) as exc:
                    cleanup_error = exc
            try:
                if object_directory.exists():
                    _remove_object_directory(object_directory, deadline=deadline)
                if object_directory.exists():
                    raise P12GateError("P12 historical object temporary residue remains")
            except (OSError, UnicodeError, P12GateError) as exc:
                cleanup_error = exc
            try:
                if _docker_snapshot(deadline=deadline) != docker_before:
                    raise P12GateError("P12 historical object changed the Docker baseline")
            except (OSError, UnicodeError, subprocess.SubprocessError, P12GateError) as exc:
                cleanup_error = exc
            if time.monotonic() > deadline:
                cleanup_error = HistoricalTimeout(
                    f"P12 historical {object_name.lower()} cleanup deadline expired"
                )
            if cleanup_error is not None:
                raise cleanup_error
        closed_result = historical_inventory.build_object_result(
            object_name,
            inventory_digest=inventory_digest,
            ordered_item_results=results[object_result_start:],
            cleanup_residue_count=0,
        )
        closed_bytes = canonical_json(closed_result)
        closed_digest = historical_inventory.object_result_digest(closed_result)
        object_results.append(
            {
                "completed_at": _utc_now(),
                "object_result": closed_result,
                "object_result_digest": closed_digest,
                "started_at": started,
            }
        )
        predecessor_result = (closed_bytes, closed_digest)
    historical_inventory.validate_item_results(items, results)
    if not failure_seen and total_python_tests != 616:
        raise P12GateError("P12 historical Python test total is not exactly 616")
    overall_status = "failed" if failure_seen else "passed"
    platform_status = dict(PLATFORM_STATUS)
    platform_status["p12_governance_result"] = overall_status
    return {
        "schema_version": 1,
        "gate": "p12_portable_historical_replay",
        "status": overall_status,
        "test_count": total_python_tests,
        "test_count_semantics": "historical_python_unittest_cases",
        "failure_count": failure_count,
        "error_count": error_count,
        "skip_count": skip_count,
        "inventory_count": len(items),
        "item_results": results,
        "leaf_records": leaf_records,
        "object_results": object_results,
        "excluded_gate_ids": list(EXCLUDED_GATE_IDS),
        "inventory_digest": inventory_digest,
        "passed_acceptance_gate_count": sum(
            item.get("item_type") == "included_acceptance_gate" and result.get("result") == "passed"
            for item, result in zip(items, results, strict=True)
        ),
        "platform_status": platform_status,
        "cleanup_residue_count": 0,
        "publication_count": 0,
    }


def run_implementation(root: Path) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "gate": "p12_implementation",
        "status": "passed",
        "gates": static_gates(root, mode="implementation"),
    }


def run_current_ci(root: Path, temporary: Path) -> dict[str, Any]:
    mode = "final" if (root / SUMMARY_PATH).exists() else "ci"
    tests = run_tests(root, temporary / "tests")
    status = str(tests["status"])
    test_count = int(tests["test_count"])
    failure_count = int(tests["failure_count"])
    error_count = int(tests["error_count"])
    if status == "failed":
        gates: dict[str, Any] = {"status": "not_run_due_to_prior_failure"}
    else:
        try:
            gates = static_gates(root, mode=mode)
        except (
            UnicodeError,
            json.JSONDecodeError,
            subprocess.TimeoutExpired,
            HistoricalInventoryError,
            P12GateError,
        ):
            status = "failed"
            failure_count += 1
            gates = {
                "status": "failed",
                "safe_failure_category": "static_gate_failure",
            }
    result = {
        "schema_version": 1,
        "gate": "p12_current_ci",
        "status": status,
        "mode": "final_candidate" if mode == "final" else "implementation",
        "test_count": test_count,
        "failure_count": failure_count,
        "error_count": error_count,
        "skip_count": 0,
        "test_count_semantics": "p12_governance_unittest_methods",
        "tests": tests,
        "gates": gates,
        "cleanup_residue_count": 0,
        "publication_count": 0,
    }
    if mode == "final" and status == "passed":
        from scripts.collect_p12_evidence import validate_summary

        try:
            result["committed_summary"] = validate_summary(root)
        except P12GateError:
            failure_count += 1
            result["status"] = "failed"
            result["failure_count"] = failure_count
            result["gates"] = {
                "status": "failed",
                "safe_failure_category": "committed_summary_failure",
            }
    if result["status"] == "failed" and failure_count + error_count == 0:
        raise P12GateError("P12 failed current CI result lacks a real failure count")
    return result


def run_ci(root: Path, temporary: Path) -> dict[str, Any]:
    current = run_current_ci(root, temporary / "current")
    historical = run_portable_history(root, temporary / "history")
    status = (
        "passed"
        if current.get("status") == "passed" and historical.get("status") == "passed"
        else "failed"
    )
    return {
        "schema_version": 1,
        "gate": "p12_ci",
        "status": status,
        "mode": current["mode"],
        "current_ci": current,
        "portable_history": historical,
        "cleanup_residue_count": 0,
        "publication_count": 0,
    }


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise P12GateError(f"P12 {label} must be a positive integer")
    return value


def _nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise P12GateError(f"P12 {label} must be a nonnegative integer")
    return value


def _exact_zero(value: object, label: str) -> None:
    if _nonnegative_int(value, label) != 0:
        raise P12GateError(f"P12 {label} must be exactly zero")


def _environment_positive_int(environment: dict[str, str], name: str) -> int:
    value = environment.get(name, "")
    if not re.fullmatch(r"[1-9][0-9]*", value):
        raise P12GateError(f"P12 standard runner input {name} is invalid")
    return int(value)


def _event_payload(environment: dict[str, str]) -> dict[str, Any]:
    raw_path = environment.get("GITHUB_EVENT_PATH", "")
    path = Path(raw_path)
    if not raw_path or not path.is_absolute():
        raise P12GateError("P12 GitHub event payload path is invalid")
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise P12GateError("P12 GitHub event payload is unavailable") from exc
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise P12GateError("P12 GitHub event payload is not a regular file")
    value = parse_json_unique(path.read_bytes())
    if not isinstance(value, dict):
        raise P12GateError("P12 GitHub event payload must be one JSON object")
    return value


def _nested(value: object, *keys: str) -> object:
    current = value
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            raise P12GateError("P12 GitHub event payload identity is incomplete")
        current = current[key]
    return current


def _dynamic_identity(root: Path, environment: dict[str, str]) -> dict[str, object]:
    payload = _event_payload(environment)
    event = environment.get("GITHUB_EVENT_NAME", "")
    if event not in {"pull_request", "push"}:
        raise P12GateError("P12 GitHub event is not an authorized variant")
    if environment.get("GITHUB_WORKFLOW") != "CI":
        raise P12GateError("P12 workflow name identity drifted")
    workflow_ref = environment.get("GITHUB_WORKFLOW_REF", "")
    if not workflow_ref.startswith(WORKFLOW_REF_PREFIX):
        raise P12GateError("P12 workflow ref identity drifted")
    ref_suffix = workflow_ref[len(WORKFLOW_REF_PREFIX) :]
    if not ref_suffix.startswith("refs/") or not SAFE_VALUE.fullmatch(ref_suffix):
        raise P12GateError("P12 workflow ref suffix is invalid")
    if environment.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise P12GateError("P12 repository runner identity drifted")
    if _nested(payload, "repository", "full_name") != REPOSITORY:
        raise P12GateError("P12 event repository identity drifted")
    checked_head = git(root, "rev-parse", "HEAD")
    github_sha = environment.get("GITHUB_SHA", "")
    if SHA.fullmatch(checked_head) is None:
        raise P12GateError("P12 checked-out head is invalid")

    if event == "pull_request":
        number = _positive_int(_nested(payload, "pull_request", "number"), "PR number")
        head_branch = _nested(payload, "pull_request", "head", "ref")
        head_sha = _nested(payload, "pull_request", "head", "sha")
        base_ref = _nested(payload, "pull_request", "base", "ref")
        base_sha = _nested(payload, "pull_request", "base", "sha")
        if (
            head_branch != V4_BRANCH
            or head_sha != checked_head
            or base_ref != "main"
            or base_sha != BASE_COMMIT
            or environment.get("GITHUB_HEAD_REF") != head_branch
            or environment.get("GITHUB_BASE_REF") != base_ref
            or ref_suffix not in {f"refs/pull/{number}/merge", f"refs/heads/{head_branch}"}
        ):
            raise P12GateError("P12 pull-request payload, ref, or Git identity drifted")
    else:
        number = None
        head_branch = "main"
        head_sha = _nested(payload, "after")
        base_ref = None
        base_sha = None
        if (
            _nested(payload, "ref") != "refs/heads/main"
            or payload.get("deleted") is True
            or head_sha != checked_head
            or github_sha != checked_head
            or ref_suffix != "refs/heads/main"
            or environment.get("GITHUB_HEAD_REF", "") not in {"", None}
            or environment.get("GITHUB_BASE_REF", "") not in {"", None}
        ):
            raise P12GateError("P12 main-push payload, ref, or Git identity drifted")
    return {
        "event": event,
        "repository": REPOSITORY,
        "workflow_name": "CI",
        "workflow_path": WORKFLOW_PATH,
        "run_id": _environment_positive_int(environment, "GITHUB_RUN_ID"),
        "run_attempt": _environment_positive_int(environment, "GITHUB_RUN_ATTEMPT"),
        "head_branch": head_branch,
        "head_sha": head_sha,
        "base_ref": base_ref,
        "base_sha": base_sha,
        "pull_request_number": number,
    }


def _safe_observed(value: str, label: str) -> str:
    normalized = value[:-1] if value.endswith("\n") else value
    lowered = normalized.lower()
    if (
        not normalized
        or "\n" in normalized
        or "\r" in normalized
        or SAFE_VALUE.fullmatch(normalized) is None
        or normalized.startswith(("/", "~"))
        or re.match(r"[A-Za-z]:/", normalized) is not None
        or re.search(r"(?:^|[\s=:])(?:/|[A-Za-z]:/)|://", normalized) is not None
        or any(
            marker in lowered
            for marker in (
                "/users/",
                "/home/",
                ".codex/",
                "ghp_",
                "sk-",
                "dc_session=",
                "token",
                "bearer",
            )
        )
    ):
        raise P12GateError(f"P12 observed {label} is not a bounded safe value")
    return normalized


def _observed_command(command: list[str], label: str, *, root: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise P12GateError(f"P12 observed {label} command failed")
    return _safe_observed(completed.stdout, label)


def observed_environment(
    root: Path, environment: dict[str, str], *, command_values: dict[str, str] | None = None
) -> dict[str, str]:
    values = command_values or {
        "docker_server_version": _observed_command(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            "docker server version",
            root=root,
        ),
        "docker_compose_version": _observed_command(
            ["docker", "compose", "version", "--short"],
            "Docker Compose version",
            root=root,
        ),
        "python_version": _observed_command(["python3", "--version"], "Python version", root=root),
        "node_version": _observed_command(["node", "--version"], "Node version", root=root),
        "npm_version": _observed_command(["npm", "--version"], "npm version", root=root),
    }
    result = {
        "runner_os": _safe_observed(environment.get("RUNNER_OS", ""), "runner OS"),
        "runner_image_os": _safe_observed(environment.get("ImageOS", ""), "runner image OS"),
        "runner_image_version": _safe_observed(
            environment.get("ImageVersion", ""), "runner image version"
        ),
        "architecture": _safe_observed(environment.get("RUNNER_ARCH", ""), "architecture"),
        **{key: _safe_observed(value, key) for key, value in values.items()},
    }
    if result["runner_os"].casefold() != "linux" or set(result) != OBSERVED_KEYS:
        raise P12GateError("P12 required job did not observe Linux independently")
    return result


def inventory_binding(
    root: Path, head_sha: str
) -> tuple[dict[str, object], tuple[dict[str, Any], ...]]:
    listing = git(root, "ls-tree", head_sha, "--", INVENTORY_PATH)
    match = re.fullmatch(rf"100644 blob ([0-9a-f]{{40}})\t{re.escape(INVENTORY_PATH)}", listing)
    if match is None:
        raise P12GateError("P12 committed portable inventory mode or blob is invalid")
    encoded = _git_bytes(root, f"{head_sha}:{INVENTORY_PATH}")
    value = parse_json_unique(encoded)
    if not isinstance(value, list) or len(value) != 151 or canonical_json(value) != encoded:
        raise P12GateError("P12 committed portable inventory shape is invalid")
    items = tuple(item for item in value if isinstance(item, dict))
    if len(items) != len(value):
        raise P12GateError("P12 committed portable inventory item shape is invalid")
    try:
        historical_inventory.validate_inventory(items)
    except HistoricalInventoryError as exc:
        raise P12GateError("P12 committed portable inventory contract drifted") from exc
    counts = {
        "setup_count": sum(item.get("item_type") == "setup" for item in items),
        "included_acceptance_gate_count": sum(
            item.get("item_type") == "included_acceptance_gate" for item in items
        ),
        "evidence_anchor_count": sum(item.get("item_type") == "evidence_anchor" for item in items),
        "excluded_acceptance_gate_count": sum(
            item.get("item_type") == "excluded_acceptance_gate" for item in items
        ),
        "total_item_count": len(items),
    }
    if counts != {
        "setup_count": 5,
        "included_acceptance_gate_count": 124,
        "evidence_anchor_count": 17,
        "excluded_acceptance_gate_count": 5,
        "total_item_count": 151,
    }:
        raise P12GateError("P12 committed portable inventory typed counts drifted")
    binding: dict[str, object] = {
        **counts,
        "excluded_gate_ids": list(EXCLUDED_GATE_IDS),
        "inventory_blob": match.group(1),
        "inventory_digest": f"sha256:{hashlib.sha256(canonical_json(value)).hexdigest()}",
        "inventory_path": INVENTORY_PATH,
        "inventory_sha256": hashlib.sha256(encoded).hexdigest(),
    }
    return binding, items


def _gate_counts(result: dict[str, Any], specification: dict[str, object]) -> dict[str, object]:
    status = result.get("status")
    if status not in {"passed", "failed"}:
        raise P12GateError("P12 gate result status is invalid")
    values: dict[str, object] = {}
    for source, destination in (
        ("test_count", "test_count"),
        ("failure_count", "failure_count"),
        ("error_count", "error_count"),
        ("skip_count", "skip_count"),
    ):
        value = result.get(source)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise P12GateError("P12 safe gate result counts are invalid")
        values[destination] = value
    if status == "passed" and (
        values["test_count"] != specification["test_count"]
        or any(values[key] != 0 for key in ("failure_count", "error_count", "skip_count"))
    ):
        raise P12GateError("P12 passed gate result counts are invalid")
    return {
        **values,
        "gate_id": specification["gate_id"],
        "result_digest": f"sha256:{hashlib.sha256(canonical_json(result)).hexdigest()}",
        "status": status,
        "test_count_semantics": specification["test_count_semantics"],
    }


def build_ci_envelope(
    root: Path,
    *,
    job_kind: str,
    gate_result: dict[str, Any],
    gate_exit_status: int,
    environment: dict[str, str] | None = None,
    command_values: dict[str, str] | None = None,
) -> dict[str, object]:
    specification = JOB_KINDS.get(job_kind)
    if specification is None:
        raise P12GateError("P12 CI envelope job kind is invalid")
    env = dict(os.environ if environment is None else environment)
    if env.get("GITHUB_JOB") != specification["job_id"]:
        raise P12GateError("P12 workflow job key does not match its closed mapping")
    if isinstance(gate_exit_status, bool) or not isinstance(gate_exit_status, int):
        raise P12GateError("P12 gate exit status is not an integer")
    identity = _dynamic_identity(root, env)
    binding, items = inventory_binding(root, str(identity["head_sha"]))
    gate = _gate_counts(gate_result, specification)
    if (gate_exit_status == 0) != (gate["status"] == "passed"):
        raise P12GateError("P12 gate exit status and safe result disagree")
    if job_kind == "current_governance":
        item_results: list[dict[str, object]] = []
        passed_acceptance_gate_count: int | None = None
    else:
        candidate = gate_result.get("item_results")
        if not isinstance(candidate, list):
            raise P12GateError("P12 portable gate result has no literal item results")
        historical_inventory.validate_item_results(items, candidate)
        item_results = candidate
        passed_acceptance_gate_count = sum(
            item.get("item_type") == "included_acceptance_gate" and result.get("result") == "passed"
            for item, result in zip(items, item_results, strict=True)
        )
    inventory = {
        **binding,
        "execution_status": (
            specification["inventory_status"]
            if gate["status"] == "passed"
            else (
                "bound_not_executed_by_this_job" if job_kind == "current_governance" else "failed"
            )
        ),
        "item_results": item_results,
        "item_results_digest": f"sha256:{hashlib.sha256(canonical_json(item_results)).hexdigest()}",
        "passed_acceptance_gate_count": passed_acceptance_gate_count,
        "skip_count": 0,
    }
    ubuntu_status = CI_PLATFORM_STATUS["ubuntu_historical_execution_status"]
    if not isinstance(ubuntu_status, dict):
        raise P12GateError("P12 CI platform status shape is invalid")
    platform = {
        **CI_PLATFORM_STATUS,
        "p12_governance_result": gate["status"],
        "ubuntu_historical_execution_status": dict(ubuntu_status),
    }
    envelope: dict[str, object] = {
        **identity,
        "schema": ENVELOPE_SCHEMA,
        "contracted_runner_family": CONTRACTED_RUNNER,
        "job_id": specification["job_id"],
        "job_name": specification["job_name"],
        "observed_environment": observed_environment(root, env, command_values=command_values),
        "p12_current_p10_registry_protection": dict(REGISTRY_PLACEHOLDER),
        "gate": gate,
        "inventory": inventory,
        "platform_status": platform,
        "cleanup_residue_count": gate_result.get("cleanup_residue_count"),
        "publication_count": gate_result.get("publication_count"),
    }
    validate_ci_envelope(envelope)
    return envelope


def validate_ci_envelope(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != ENVELOPE_KEYS:
        raise P12GateError("P12 CI result envelope key set is invalid")
    gate = value.get("gate")
    inventory = value.get("inventory")
    observed = value.get("observed_environment")
    platform = value.get("platform_status")
    registry = value.get("p12_current_p10_registry_protection")
    if (
        value.get("schema") != ENVELOPE_SCHEMA
        or value.get("contracted_runner_family") != CONTRACTED_RUNNER
        or value.get("repository") != REPOSITORY
        or value.get("workflow_name") != "CI"
        or value.get("workflow_path") != WORKFLOW_PATH
        or not isinstance(gate, dict)
        or set(gate) != GATE_KEYS
        or not isinstance(inventory, dict)
        or set(inventory) != INVENTORY_KEYS
        or not isinstance(observed, dict)
        or set(observed) != OBSERVED_KEYS
        or not isinstance(platform, dict)
        or set(platform) != set(CI_PLATFORM_STATUS)
        or registry != REGISTRY_PLACEHOLDER
    ):
        raise P12GateError("P12 CI result envelope schema is invalid")
    _exact_zero(value.get("cleanup_residue_count"), "envelope cleanup residue count")
    _exact_zero(value.get("publication_count"), "envelope publication count")
    for key, item in observed.items():
        if not isinstance(item, str) or _safe_observed(item, key) != item:
            raise P12GateError("P12 CI result envelope observed values are unsafe")
    if str(observed.get("runner_os", "")).casefold() != "linux":
        raise P12GateError("P12 CI result envelope runner is not Linux")
    _positive_int(value.get("run_id"), "envelope run ID")
    _positive_int(value.get("run_attempt"), "envelope run attempt")
    if SHA.fullmatch(str(value.get("head_sha", ""))) is None:
        raise P12GateError("P12 CI result envelope head SHA is invalid")
    if value.get("event") == "pull_request":
        _positive_int(value.get("pull_request_number"), "envelope PR number")
        if (
            value.get("head_branch") != V4_BRANCH
            or value.get("base_ref") != "main"
            or value.get("base_sha") != BASE_COMMIT
        ):
            raise P12GateError("P12 pull-request envelope identity is invalid")
    elif value.get("event") == "push":
        if value.get("head_branch") != "main" or any(
            value.get(key) is not None for key in ("base_ref", "base_sha", "pull_request_number")
        ):
            raise P12GateError("P12 push envelope null-base identity is invalid")
    else:
        raise P12GateError("P12 CI result envelope event is invalid")
    specification = next(
        (
            candidate
            for candidate in JOB_KINDS.values()
            if candidate["job_id"] == value.get("job_id")
            and candidate["job_name"] == value.get("job_name")
        ),
        None,
    )
    if specification is None:
        raise P12GateError("P12 CI result envelope job mapping is invalid")
    if gate.get("status") not in {"passed", "failed"}:
        raise P12GateError("P12 CI result envelope gate result is invalid")
    for key in ("test_count", "failure_count", "error_count", "skip_count"):
        _nonnegative_int(gate.get(key), f"envelope gate {key}")
    if (
        gate.get("gate_id") != specification["gate_id"]
        or gate.get("test_count_semantics") != specification["test_count_semantics"]
        or gate.get("skip_count") != 0
        or (
            gate.get("status") == "passed"
            and (
                gate.get("test_count") != specification["test_count"]
                or gate.get("failure_count") != 0
                or gate.get("error_count") != 0
            )
        )
        or (
            gate.get("status") == "failed"
            and int(gate.get("failure_count", 0)) + int(gate.get("error_count", 0)) == 0
        )
    ):
        raise P12GateError("P12 CI result envelope gate semantics are invalid")
    if not isinstance(gate.get("result_digest"), str) or not re.fullmatch(
        r"sha256:[0-9a-f]{64}", gate["result_digest"]
    ):
        raise P12GateError("P12 CI result envelope gate digest is invalid")
    for key in ("inventory_blob",):
        if SHA.fullmatch(str(inventory.get(key, ""))) is None:
            raise P12GateError("P12 CI result envelope inventory blob is invalid")
    if SHA256.fullmatch(str(inventory.get("inventory_sha256", ""))) is None:
        raise P12GateError("P12 CI result envelope inventory file digest is invalid")
    for key in ("inventory_digest", "item_results_digest"):
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(inventory.get(key, ""))):
            raise P12GateError("P12 CI result envelope inventory digest is invalid")
    for key in (
        "setup_count",
        "included_acceptance_gate_count",
        "evidence_anchor_count",
        "excluded_acceptance_gate_count",
        "total_item_count",
        "skip_count",
    ):
        _nonnegative_int(inventory.get(key), f"envelope inventory {key}")
    if (
        inventory.get("setup_count") != 5
        or inventory.get("included_acceptance_gate_count") != 124
        or inventory.get("evidence_anchor_count") != 17
        or inventory.get("excluded_acceptance_gate_count") != 5
        or inventory.get("total_item_count") != 151
        or inventory.get("excluded_gate_ids") != list(EXCLUDED_GATE_IDS)
        or inventory.get("inventory_path") != INVENTORY_PATH
        or inventory.get("skip_count") != 0
        or platform.get("linux_public_pilot_readiness") != "blocked"
        or platform.get("p12_governance_result") != gate.get("status")
        or platform.get("ubuntu_historical_execution_status")
        != CI_PLATFORM_STATUS["ubuntu_historical_execution_status"]
    ):
        raise P12GateError("P12 CI result envelope inventory or platform binding drifted")
    item_results = inventory.get("item_results")
    if not isinstance(item_results, list) or any(
        not isinstance(item, dict) for item in item_results
    ):
        raise P12GateError("P12 CI result envelope item results are invalid")
    expected_item_digest = f"sha256:{hashlib.sha256(canonical_json(item_results)).hexdigest()}"
    if inventory.get("item_results_digest") != expected_item_digest:
        raise P12GateError("P12 CI result envelope item-result digest mismatched")
    if value.get("job_id") == "current-ci":
        if (
            inventory.get("execution_status") != "bound_not_executed_by_this_job"
            or item_results != []
            or inventory.get("passed_acceptance_gate_count") is not None
        ):
            raise P12GateError("P12 current CI inventory projection is invalid")
    else:
        _nonnegative_int(
            inventory.get("passed_acceptance_gate_count"),
            "envelope passed acceptance gate count",
        )
        try:
            summary = historical_inventory.validate_item_results(
                historical_inventory.CANONICAL_INVENTORY,
                item_results,
            )
        except HistoricalInventoryError as exc:
            raise P12GateError("P12 portable CI item results are invalid") from exc
        for result in item_results:
            if result.get("result") == "passed":
                _exact_zero(
                    result.get("exit_status"),
                    "portable passed-item exit status",
                )
        passed = sum(
            result.get("item_type") == "included_acceptance_gate"
            and result.get("result") == "passed"
            for result in item_results
        )
        if (
            inventory.get("execution_status") != gate.get("status")
            or inventory.get("passed_acceptance_gate_count") != passed
            or summary.get("status") != gate.get("status")
            or (gate.get("status") == "passed" and passed != 124)
        ):
            raise P12GateError("P12 portable CI inventory outcome is invalid")
    return value


def encode_ci_envelope(value: dict[str, object]) -> tuple[str, str]:
    validate_ci_envelope(value)
    encoded = canonical_json(value)
    if len(encoded) > ENVELOPE_PAYLOAD_MAX:
        raise P12GateError("P12 CI result envelope payload is oversized")
    token = base64.urlsafe_b64encode(encoded).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(encoded).hexdigest()
    if len(token) > ENVELOPE_TOKEN_MAX:
        raise P12GateError("P12 CI result envelope token is oversized")
    line = f"{ENVELOPE_PREFIX} {token} sha256={digest}"
    if len(line.encode("ascii")) > ENVELOPE_LINE_MAX:
        raise P12GateError("P12 CI result envelope line is oversized")
    return line, digest


def decode_ci_envelope_line(line: bytes) -> tuple[dict[str, object], str]:
    logical_line = line[:-1] if line.endswith(b"\n") else line
    if len(logical_line) > ENVELOPE_LINE_MAX:
        raise P12GateError("P12 CI result envelope line is oversized")
    match = ENVELOPE_PATTERN.fullmatch(logical_line)
    if match is None:
        raise P12GateError("P12 CI result envelope marker is malformed")
    token, declared_digest = match.groups()
    if len(token) > ENVELOPE_TOKEN_MAX or b"=" in token:
        raise P12GateError("P12 CI result envelope token is malformed")
    try:
        encoded = base64.b64decode(token + b"=" * (-len(token) % 4), altchars=b"-_", validate=True)
    except (ValueError, binascii.Error) as exc:
        raise P12GateError("P12 CI result envelope base64 is invalid") from exc
    if len(encoded) > ENVELOPE_PAYLOAD_MAX:
        raise P12GateError("P12 CI result envelope payload is oversized")
    if base64.urlsafe_b64encode(encoded).rstrip(b"=") != token:
        raise P12GateError("P12 CI result envelope base64 is noncanonical")
    digest = hashlib.sha256(encoded).hexdigest()
    if digest.encode("ascii") != declared_digest:
        raise P12GateError("P12 CI result envelope digest mismatched")
    value = parse_json_unique(encoded)
    if canonical_json(value) != encoded:
        raise P12GateError("P12 CI result envelope is not canonical P12-CJ-1")
    return validate_ci_envelope(value), digest


def extract_ci_envelope(
    stream: Any,
    *,
    run_id: int,
    attempt: int,
    job_database_id: int,
    expected_job_id: str,
    expected_job_name: str,
    head_sha: str,
) -> dict[str, object]:
    _positive_int(run_id, "expected run ID")
    _positive_int(attempt, "expected run attempt")
    _positive_int(job_database_id, "job database ID")
    matches: list[tuple[dict[str, object], str]] = []
    marker = ENVELOPE_PREFIX.encode("ascii")
    for line in stream:
        if not isinstance(line, bytes):
            line = str(line).encode("utf-8")
        logical_line = line[:-1] if line.endswith(b"\n") else line
        if len(logical_line) > ENVELOPE_LINE_MAX:
            if marker in line:
                raise P12GateError("P12 CI result envelope line is oversized")
            continue
        if marker in line:
            matches.append(decode_ci_envelope_line(logical_line))
            if len(matches) > 1:
                raise P12GateError("P12 job log contains duplicate result envelopes")
    if len(matches) != 1:
        raise P12GateError("P12 job log contains no exact result envelope")
    envelope, digest = matches[0]
    if (
        envelope.get("run_id") != run_id
        or envelope.get("run_attempt") != attempt
        or envelope.get("job_id") != expected_job_id
        or envelope.get("job_name") != expected_job_name
        or envelope.get("head_sha") != head_sha
    ):
        raise P12GateError("P12 extracted envelope does not match selected run/job/head")
    inventory = envelope.get("inventory")
    if not isinstance(inventory, dict):
        raise P12GateError("P12 extracted envelope inventory is malformed")
    item_results = inventory.get("item_results")
    if not isinstance(item_results, list):
        raise P12GateError("P12 extracted envelope item results are malformed")
    safe_inventory = {key: value for key, value in inventory.items() if key != "item_results"}
    safe_inventory["excluded_results"] = [
        item
        for item in item_results
        if isinstance(item, dict) and item.get("item_type") == "excluded_acceptance_gate"
    ]
    safe_projection = {key: value for key, value in envelope.items() if key != "inventory"}
    safe_projection["inventory"] = safe_inventory
    return {
        "job_id": expected_job_id,
        "job_name": expected_job_name,
        "job_database_id": job_database_id,
        "envelope_sha256": digest,
        "safe_projection": safe_projection,
    }


def validate_ci_envelope_pair(
    current: dict[str, object], portable: dict[str, object]
) -> dict[str, object]:
    first = validate_ci_envelope(current)
    second = validate_ci_envelope(portable)
    shared = (
        "repository",
        "workflow_name",
        "workflow_path",
        "run_id",
        "run_attempt",
        "event",
        "head_branch",
        "head_sha",
        "base_ref",
        "base_sha",
        "pull_request_number",
        "contracted_runner_family",
        "platform_status",
        "p12_current_p10_registry_protection",
        "publication_count",
    )
    inventory_shared = (
        "inventory_path",
        "inventory_blob",
        "inventory_sha256",
        "inventory_digest",
        "setup_count",
        "included_acceptance_gate_count",
        "evidence_anchor_count",
        "excluded_acceptance_gate_count",
        "total_item_count",
        "excluded_gate_ids",
        "skip_count",
    )
    if any(first[key] != second[key] for key in shared):
        raise P12GateError("P12 required CI envelopes disagree on a shared identity")
    first_inventory = first["inventory"]
    second_inventory = second["inventory"]
    assert isinstance(first_inventory, dict) and isinstance(second_inventory, dict)
    first_gate = first["gate"]
    second_gate = second["gate"]
    if not isinstance(first_gate, dict) or not isinstance(second_gate, dict):
        raise P12GateError("P12 required CI envelope gate shape is invalid")
    if any(first_inventory[key] != second_inventory[key] for key in inventory_shared):
        raise P12GateError("P12 required CI envelopes disagree on inventory binding")
    if (
        first.get("job_id") != "current-ci"
        or second.get("job_id") != "portable-history"
        or first_inventory.get("execution_status") != "bound_not_executed_by_this_job"
        or first_inventory.get("item_results") != []
        or second_inventory.get("execution_status") != "passed"
        or second_inventory.get("passed_acceptance_gate_count") != 124
        or second_inventory.get("skip_count") != 0
        or first_gate.get("status") != "passed"
        or second_gate.get("status") != "passed"
    ):
        raise P12GateError("P12 required CI envelope job outcomes are invalid")
    return {"status": "passed", "required_envelope_count": 2}


def _validate_ci_projection_pair(current: dict[str, object], portable: dict[str, object]) -> None:
    shared = (
        "base_ref",
        "base_sha",
        "contracted_runner_family",
        "event",
        "head_branch",
        "head_sha",
        "p12_current_p10_registry_protection",
        "platform_status",
        "publication_count",
        "pull_request_number",
        "repository",
        "run_attempt",
        "run_id",
        "schema",
        "workflow_name",
        "workflow_path",
    )
    if any(current.get(key) != portable.get(key) for key in shared):
        raise P12GateError("P12 required CI projections disagree on a shared identity")
    current_inventory = current.get("inventory")
    portable_inventory = portable.get("inventory")
    if not isinstance(current_inventory, dict) or not isinstance(portable_inventory, dict):
        raise P12GateError("P12 required CI projection inventory is malformed")
    inventory_shared = (
        "evidence_anchor_count",
        "excluded_acceptance_gate_count",
        "excluded_gate_ids",
        "included_acceptance_gate_count",
        "inventory_blob",
        "inventory_digest",
        "inventory_path",
        "inventory_sha256",
        "setup_count",
        "skip_count",
        "total_item_count",
    )
    if any(current_inventory.get(key) != portable_inventory.get(key) for key in inventory_shared):
        raise P12GateError("P12 required CI projections disagree on inventory binding")
    current_gate = current.get("gate")
    portable_gate = portable.get("gate")
    excluded = portable_inventory.get("excluded_results")
    if (
        current.get("job_id") != "current-ci"
        or current.get("job_name") != "Current P12 governance non-publishing verification"
        or portable.get("job_id") != "portable-history"
        or portable.get("job_name") != "Portable historical replay"
        or not isinstance(current_gate, dict)
        or current_gate.get("status") != "passed"
        or not isinstance(portable_gate, dict)
        or portable_gate.get("status") != "passed"
        or current_inventory.get("execution_status") != "bound_not_executed_by_this_job"
        or current_inventory.get("passed_acceptance_gate_count") is not None
        or current_inventory.get("excluded_results") != []
        or portable_inventory.get("execution_status") != "passed"
        or portable_inventory.get("passed_acceptance_gate_count") != 124
        or not isinstance(excluded, list)
        or [item.get("gate_id") for item in excluded if isinstance(item, dict)]
        != list(EXCLUDED_GATE_IDS)
    ):
        raise P12GateError("P12 required CI projection outcomes are invalid")


def _verify_locked_file(root: Path, identity: tuple[str, str, str]) -> None:
    relative, blob, digest = identity
    path = root / relative
    if path.is_symlink() or not stat.S_ISREG(os.lstat(path).st_mode):
        raise P12GateError("P12 preflight locked input is not a regular file")
    if git(root, "ls-tree", BASE_COMMIT, relative) != f"100644 blob {blob}\t{relative}":
        raise P12GateError("P12 preflight locked input Git mode drifted")
    if git(root, "rev-parse", f"{BASE_COMMIT}:{relative}") != blob:
        raise P12GateError("P12 preflight locked input base blob drifted")
    if git(root, "hash-object", relative) != blob:
        raise P12GateError("P12 preflight locked input working blob drifted")
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise P12GateError("P12 preflight locked input SHA-256 drifted")


@contextmanager
def _private_umask() -> Iterator[None]:
    previous = os.umask(0o077)
    try:
        yield
    finally:
        os.umask(previous)


def _prepare_preflight_python(root: Path, temporary: Path) -> tuple[Path, dict[str, str]]:
    """Create the isolated lock-only environment after bootstrapping trusted packaging."""

    environment_root = temporary / "python-environment"
    installer_root = temporary / "python-installer"
    installer_root.mkdir(mode=0o700)
    environment = os.environ.copy()
    environment.update(
        {
            "PIP_CACHE_DIR": str(installer_root / "cache"),
            "PIP_CONFIG_FILE": os.devnull,
            "PIP_REQUIRE_VIRTUALENV": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "TMPDIR": str(installer_root),
        }
    )
    _run(
        [sys.executable, "-m", "venv", str(environment_root)],
        cwd=root,
        environment=environment,
        timeout=120,
    )
    python = environment_root / "bin" / "python"
    bootstrap_lock = installer_root / "packaging.lock"
    descriptor = os.open(bootstrap_lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(
            descriptor,
            (f"packaging=={PACKAGING_VERSION} --hash=sha256:{PACKAGING_WHEEL_HASH}\n").encode(
                "ascii"
            ),
        )
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    pip = [
        str(python),
        "-m",
        "pip",
        "--disable-pip-version-check",
        "--isolated",
        "install",
        "--require-hashes",
        "--no-deps",
        "--no-cache-dir",
    ]
    _run(
        [*pip, "-r", str(bootstrap_lock)],
        cwd=root,
        environment=environment,
        timeout=600,
    )
    _run(
        [*pip, "-r", str(root / PYTHON_LOCK[0])],
        cwd=root,
        environment=environment,
        timeout=600,
    )
    bootstrap_lock.unlink()
    return python, environment


def ca_fallback_allowed(error: BaseException) -> bool:
    if isinstance(error, ssl.SSLCertVerificationError):
        return True
    return isinstance(error, urllib.error.URLError) and isinstance(
        error.reason, ssl.SSLCertVerificationError
    )


def _tls_probe(url: str, certifi_bundle: Path | None = None) -> str:
    context = (
        ssl.create_default_context()
        if certifi_bundle is None
        else ssl.create_default_context(cafile=str(certifi_bundle))
    )
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "dc-p12"})
    try:
        with urllib.request.urlopen(request, timeout=30, context=context):
            pass
    except urllib.error.HTTPError:
        pass
    return "system_default" if certifi_bundle is None else "locked_certifi"


def _package_report(root: Path, python: Path, environment: dict[str, str]) -> dict[str, Any]:
    program = r"""import hashlib
import importlib.metadata
import json
import os
import pathlib
import re
import stat
import sys
import tomllib
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

pyproject = pathlib.Path(sys.argv[1])
lock = pathlib.Path(sys.argv[2])
project = tomllib.loads(pyproject.read_text(encoding="utf-8"))
declared = list(project["project"].get("dependencies", []))
for values in project["project"].get("optional-dependencies", {}).values():
    declared.extend(values)
direct = {}
for raw in declared:
    requirement = Requirement(raw)
    installed = Version(importlib.metadata.version(requirement.name))
    if installed not in requirement.specifier:
        raise SystemExit("direct dependency specifier mismatch")
    name = canonicalize_name(requirement.name)
    if name in direct:
        raise SystemExit("duplicate direct dependency")
    direct[name] = {
        "declared": str(requirement.specifier),
        "installed": str(installed),
    }
logical = re.sub(r"\\\n\s*", " ", lock.read_text(encoding="utf-8"))
locked = {}
for line in logical.splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        continue
    match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s]+)", stripped)
    if match is None:
        raise SystemExit("unparseable locked requirement")
    requirement = Requirement(f"{match.group(1)}=={match.group(2)}")
    declared_version = Version(match.group(2))
    installed_version = Version(importlib.metadata.version(requirement.name))
    if installed_version != declared_version:
        raise SystemExit("locked dependency version mismatch")
    name = canonicalize_name(requirement.name)
    if name in locked:
        raise SystemExit("duplicate locked dependency")
    locked[name] = str(installed_version)
import certifi
bundle = pathlib.Path(certifi.where())
metadata = os.lstat(bundle)
if bundle.is_symlink() or not stat.S_ISREG(metadata.st_mode):
    raise SystemExit("certifi bundle is not a regular non-symlink file")
print(json.dumps({
    "direct": direct,
    "locked": locked,
    "certifi_bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
    "certifi_bundle": str(bundle),
}, sort_keys=True))"""
    output = _run(
        [str(python), "-I", "-c", program, str(root / PYPROJECT[0]), str(root / PYTHON_LOCK[0])],
        cwd=root,
        environment=environment,
        timeout=300,
    )
    report = json.loads(output)
    if not isinstance(report, dict):
        raise P12GateError("P12 preflight package report is invalid")
    locked = report.get("locked")
    direct = report.get("direct")
    bundle = report.get("certifi_bundle")
    if (
        not isinstance(locked, dict)
        or not isinstance(direct, dict)
        or not isinstance(bundle, str)
        or locked.get("certifi") != CERTIFI_VERSION
        or locked.get("packaging") != PACKAGING_VERSION
        or report.get("certifi_bundle_sha256") != CERTIFI_BUNDLE_SHA256
        or not direct
    ):
        raise P12GateError("P12 preflight locked or direct package identity is invalid")
    lock_text = (root / PYTHON_LOCK[0]).read_text(encoding="utf-8")
    if f"certifi=={CERTIFI_VERSION} --hash=sha256:{CERTIFI_WHEEL_HASH}" not in lock_text or (
        f"packaging=={PACKAGING_VERSION} --hash=sha256:{PACKAGING_WHEEL_HASH}" not in lock_text
    ):
        raise P12GateError("P12 preflight accepted tool wheel identity drifted")
    return report


def _gh_json(arguments: list[str], *, cwd: Path) -> Any:
    completed = subprocess.run(
        ["gh", *arguments],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=180,
        check=False,
    )
    if completed.returncode != 0:
        raise P12GateError("P12 preflight GitHub read failed")
    return parse_json_unique(completed.stdout)


def _gh_auth_status(root: Path) -> None:
    completed = subprocess.run(
        ["gh", "auth", "status", "--hostname", "github.com"],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        raise P12GateError("P12 active GitHub authentication is unavailable")


def _expected_package_inventory(root: Path, heading: str) -> list[dict[str, Any]]:
    text = (root / "docs/p12/acceptance.md").read_text(encoding="utf-8")
    try:
        section = text.split(f"{heading} subject:", 1)[1]
        if heading == "Runtime":
            section = section.split("Studio subject:", 1)[0]
        else:
            section = section.split("The start, evidence-preflight", 1)[0]
    except IndexError as exc:
        raise P12GateError("P12 protected GHCR inventory table is unavailable") from exc
    result: list[dict[str, Any]] = []
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4 or not cells[0].isdigit():
            continue
        result.append(
            {
                "id": int(cells[0]),
                "name": cells[1],
                "tags": [] if cells[2] == "none" else [cells[2]],
                "created_at": cells[3],
                "updated_at": cells[3],
            }
        )
    if len(result) != 14:
        raise P12GateError("P12 protected GHCR inventory table is not exactly 14 versions")
    return result


def validate_package_inventory(actual: object, expected: list[dict[str, Any]]) -> None:
    pages = actual
    if isinstance(pages, list) and pages and all(isinstance(page, list) for page in pages):
        pages = [item for page in pages for item in page]
    if not isinstance(pages, list):
        raise P12GateError("P12 GHCR version response is invalid")
    canonical: list[dict[str, Any]] = []
    for value in pages:
        if not isinstance(value, dict):
            raise P12GateError("P12 GHCR version entry is invalid")
        metadata = value.get("metadata")
        container = metadata.get("container") if isinstance(metadata, dict) else None
        tags = container.get("tags") if isinstance(container, dict) else None
        canonical.append(
            {
                "id": value.get("id"),
                "name": value.get("name"),
                "tags": tags,
                "created_at": value.get("created_at"),
                "updated_at": value.get("updated_at"),
            }
        )
    if canonical != expected:
        raise P12GateError("P12 protected GHCR version inventory drifted")


P10_RUNS = (
    (34202520699, "05e73ea23ac650edfae59fa409a770fdf967af3a", "success"),
    (34203006909, "05e73ea23ac650edfae59fa409a770fdf967af3a", "failure"),
    (34204280131, "ddc04021f94ca888235c53f96ed64218de8c3e67", "failure"),
    (34204837101, "ae714c128f844466c76811986c0605e39fce12cc", "failure"),
    (34205272328, "76b278feedbb79b9a4c0d023e328911096fe57ae", "failure"),
    (34206039435, "a003d540093df9a08437c47e9c8ff16970e5e645", "success"),
    (34235760264, "62b226064d2597a4ca6a67f9f2c20a79a815732b", "success"),
    (34236719816, "d9fd27670a36f699bf299f6154afce180bea64cc", "failure"),
    (34237810474, "cc4acd3bda3f4d2bdfee9392c7d0f85f90c07688", "success"),
)


def _run_pr_identity(run: dict[str, Any]) -> tuple[int, str, str, str, str]:
    pull_requests = run.get("pull_requests")
    if not isinstance(pull_requests, list) or len(pull_requests) != 1:
        raise P12GateError("P12 implementation run PR association is absent or ambiguous")
    association = pull_requests[0]
    if not isinstance(association, dict):
        raise P12GateError("P12 implementation run PR association is malformed")
    number = _positive_int(association.get("number"), "run PR number")
    head_ref = _nested(association, "head", "ref")
    head_sha = _nested(association, "head", "sha")
    base_ref = _nested(association, "base", "ref")
    base_sha = _nested(association, "base", "sha")
    repository = run.get("repository")
    repository_id = repository.get("id") if isinstance(repository, dict) else None
    expected_repository_url = f"https://api.github.com/repos/{REPOSITORY}"
    if not all(isinstance(value, str) for value in (head_ref, head_sha, base_ref, base_sha)):
        raise P12GateError("P12 implementation run PR identity is malformed")
    assert isinstance(head_ref, str)
    assert isinstance(head_sha, str)
    assert isinstance(base_ref, str)
    assert isinstance(base_sha, str)
    if isinstance(repository_id, bool) or not isinstance(repository_id, int) or repository_id <= 0:
        raise P12GateError("P12 implementation run repository identity is malformed")
    for side in ("head", "base"):
        side_repository = _nested(association, side, "repo")
        if (
            not isinstance(side_repository, dict)
            or side_repository.get("id") != repository_id
            or side_repository.get("name") != "digital-colleagues"
            or side_repository.get("url") != expected_repository_url
        ):
            raise P12GateError("P12 implementation run PR repository identity drifted")
    return number, head_ref, head_sha, base_ref, base_sha


def validate_live_v4_pr_metadata(
    value: object,
    *,
    number: int,
    head_ref: str,
    head_sha: str,
    base_ref: str,
    base_sha: str,
) -> str:
    """Validate the field-complete GraphQL view of the live v4 pull request."""

    if not isinstance(value, dict):
        raise P12GateError("P12 live implementation PR metadata is not an object")
    expected = {
        "number": number,
        "state": "OPEN",
        "baseRefName": base_ref,
        "baseRefOid": base_sha,
        "headRefName": head_ref,
        "headRefOid": head_sha,
        "autoMergeRequest": None,
        "mergedAt": None,
        "mergeCommit": None,
        "url": f"https://github.com/{REPOSITORY}/pull/{number}",
    }
    if set(value) != set(expected):
        raise P12GateError("P12 live implementation PR field-complete metadata is unavailable")
    if type(value.get("number")) is not int or any(
        value.get(key) != expected_value for key, expected_value in expected.items()
    ):
        raise P12GateError("P12 live implementation PR identity or null merge boundary drifted")
    return "OPEN"


def _stream_job_envelope(
    root: Path,
    working: Path,
    *,
    run_id: int,
    attempt: int,
    job: dict[str, Any],
    job_id: str,
    job_name: str,
    head_sha: str,
) -> dict[str, object]:
    database_id = _positive_int(job.get("id"), "REST job database ID")
    destination = working / f"envelope-{database_id}.json"
    gh_process = subprocess.Popen(
        ["gh", "api", f"/repos/{REPOSITORY}/actions/jobs/{database_id}/logs"],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    assert gh_process.stdout is not None
    parser = subprocess.Popen(
        [
            sys.executable,
            "-B",
            "scripts/run_p12_toolchain.py",
            "--scope",
            "extract-ci-envelope",
            "--run-id",
            str(run_id),
            "--attempt",
            str(attempt),
            "--job-database-id",
            str(database_id),
            "--expected-job-id",
            job_id,
            "--expected-job-name",
            job_name,
            "--head-sha",
            head_sha,
            "--safe-output",
            str(destination),
        ],
        cwd=root,
        stdin=gh_process.stdout,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    gh_process.stdout.close()
    try:
        parser_status = parser.wait(timeout=300)
        gh_status = gh_process.wait(timeout=30)
    except subprocess.TimeoutExpired as exc:
        for process in (parser, gh_process):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
        raise P12GateError("P12 CI job-log streaming timed out") from exc
    if gh_status != 0 or parser_status != 0:
        raise P12GateError("P12 CI job-log transport or envelope extraction failed")
    try:
        metadata = os.lstat(destination)
        encoded = destination.read_bytes()
    except OSError as exc:
        raise P12GateError("P12 extracted safe envelope projection is unavailable") from exc
    if (
        destination.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o600
    ):
        raise P12GateError("P12 extracted safe envelope projection mode is invalid")
    value = parse_json_unique(encoded)
    if canonical_json(value) != encoded or not isinstance(value, dict):
        raise P12GateError("P12 extracted safe envelope projection is not canonical")
    destination.unlink()
    return value


def _safe_envelope_receipt(projection: dict[str, object]) -> dict[str, object]:
    envelope = projection.get("safe_projection")
    if not isinstance(envelope, dict):
        raise P12GateError("P12 safe envelope projection is malformed")
    return {
        "envelope_sha256": projection["envelope_sha256"],
        "job_database_id": projection["job_database_id"],
        "job_id": projection["job_id"],
        "job_name": projection["job_name"],
        "observed_environment": envelope["observed_environment"],
    }


def _github_and_ghcr(
    root: Path,
    *,
    implementation_head: str,
    ci_run_id: int,
    ci_run_attempt: int,
    working: Path,
) -> dict[str, Any]:
    _gh_auth_status(root)
    run = _gh_json(
        ["api", f"/repos/{REPOSITORY}/actions/runs/{ci_run_id}/attempts/{ci_run_attempt}"],
        cwd=root,
    )
    if not isinstance(run, dict):
        raise P12GateError("P12 implementation-head CI response is invalid")
    repository = run.get("repository")
    number, head_ref, head_sha, base_ref, base_sha = _run_pr_identity(run)
    if (
        run.get("id") != ci_run_id
        or run.get("run_attempt") != ci_run_attempt
        or run.get("head_sha") != implementation_head
        or run.get("event") != "pull_request"
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
        or run.get("name") != "CI"
        or run.get("path") != WORKFLOW_PATH
        or run.get("head_branch") != V4_BRANCH
        or not isinstance(repository, dict)
        or repository.get("full_name") != REPOSITORY
        or head_ref != V4_BRANCH
        or head_sha != implementation_head
        or base_ref != "main"
        or base_sha != BASE_COMMIT
    ):
        raise P12GateError("P12 implementation-head CI identity or lifecycle is invalid")
    live = _gh_json(
        [
            "pr",
            "view",
            str(number),
            "--repo",
            REPOSITORY,
            "--json",
            (
                "number,state,baseRefName,baseRefOid,headRefName,headRefOid,"
                "autoMergeRequest,mergedAt,mergeCommit,url"
            ),
        ],
        cwd=root,
    )
    validate_live_v4_pr_metadata(
        live,
        number=number,
        head_ref=head_ref,
        head_sha=head_sha,
        base_ref=base_ref,
        base_sha=base_sha,
    )
    pages = _gh_json(
        [
            "api",
            "--paginate",
            "--slurp",
            f"/repos/{REPOSITORY}/actions/runs/{ci_run_id}/attempts/{ci_run_attempt}/jobs?per_page=100",
        ],
        cwd=root,
    )
    if not isinstance(pages, list) or any(not isinstance(page, dict) for page in pages):
        raise P12GateError("P12 attempt-specific jobs pagination is invalid")
    jobs: list[dict[str, Any]] = []
    for page in pages:
        values = page.get("jobs")
        if not isinstance(values, list) or any(not isinstance(value, dict) for value in values):
            raise P12GateError("P12 attempt-specific jobs page is malformed")
        jobs.extend(values)
    projections: dict[str, dict[str, object]] = {}
    for specification in JOB_KINDS.values():
        job_id = str(specification["job_id"])
        job_name = str(specification["job_name"])
        selected = [value for value in jobs if value.get("name") == job_name]
        if len(selected) != 1:
            raise P12GateError("P12 required REST job name is absent or ambiguous")
        job = selected[0]
        expected_run_url = f"https://api.github.com/repos/{REPOSITORY}/actions/runs/{ci_run_id}"
        if (
            job.get("status") != "completed"
            or job.get("conclusion") != "success"
            or job.get("run_id") != ci_run_id
            or job.get("run_attempt") != ci_run_attempt
            or job.get("run_url") != expected_run_url
        ):
            raise P12GateError("P12 required REST job lifecycle or run identity drifted")
        projections[job_id] = _stream_job_envelope(
            root,
            working,
            run_id=ci_run_id,
            attempt=ci_run_attempt,
            job=job,
            job_id=job_id,
            job_name=job_name,
            head_sha=implementation_head,
        )
    current_envelope = projections["current-ci"].get("safe_projection")
    portable_envelope = projections["portable-history"].get("safe_projection")
    if not isinstance(current_envelope, dict) or not isinstance(portable_envelope, dict):
        raise P12GateError("P12 required safe envelope projection is malformed")
    _validate_ci_projection_pair(current_envelope, portable_envelope)
    for envelope in (current_envelope, portable_envelope):
        if (
            envelope.get("run_id") != ci_run_id
            or envelope.get("run_attempt") != ci_run_attempt
            or envelope.get("pull_request_number") != number
            or envelope.get("head_sha") != implementation_head
            or envelope.get("base_sha") != BASE_COMMIT
        ):
            raise P12GateError("P12 envelope and REST identity cross-check failed")
    committed_binding, _ = inventory_binding(root, implementation_head)
    for envelope in (current_envelope, portable_envelope):
        envelope_inventory = envelope.get("inventory")
        if not isinstance(envelope_inventory, dict) or any(
            envelope_inventory.get(key) != value for key, value in committed_binding.items()
        ):
            raise P12GateError("P12 envelope inventory does not bind the committed manifest")
    database_ids = {projection.get("job_database_id") for projection in projections.values()}
    if len(database_ids) != 2 or any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
        for value in database_ids
    ):
        raise P12GateError("P12 required REST jobs do not have distinct identities")

    subjects = ("digital-colleagues-runtime", "digital-colleagues-studio")
    inventories: list[dict[str, object]] = []
    for subject, heading in zip(subjects, ("Runtime", "Studio"), strict=True):
        metadata = _gh_json(["api", f"/users/jeremyliu1220/packages/container/{subject}"], cwd=root)
        if (
            not isinstance(metadata, dict)
            or metadata.get("name") != subject
            or metadata.get("package_type") != "container"
            or metadata.get("visibility") != "public"
        ):
            raise P12GateError("P12 protected GHCR subject identity drifted")
        versions = _gh_json(
            [
                "api",
                "--paginate",
                "--slurp",
                f"/users/jeremyliu1220/packages/container/{subject}/versions?per_page=100",
            ],
            cwd=root,
        )
        expected = _expected_package_inventory(root, heading)
        validate_package_inventory(versions, expected)
        if sum(bool(item["tags"]) for item in expected) != 4:
            raise P12GateError("P12 protected GHCR tag inventory drifted")
        inventories.append(
            {
                "inventory_digest": (
                    f"sha256:{hashlib.sha256(canonical_json(expected)).hexdigest()}"
                ),
                "subject": f"ghcr.io/jeremyliu1220/{subject}",
                "tagged_version_count": 4,
                "version_count": 14,
            }
        )
    digests = (
        (
            "superseded",
            "05e73ea23ac650edfae59fa409a770fdf967af3a",
            "superseded_contract_noncompliant_source",
            "digital-colleagues-runtime",
            "sha256:41567ba87a088944cf9a2c17b9b0f4359554c66b2ec1f6d52db46067e1ab9092",
        ),
        (
            "superseded",
            "05e73ea23ac650edfae59fa409a770fdf967af3a",
            "superseded_contract_noncompliant_source",
            "digital-colleagues-studio",
            "sha256:b7dd4c2b35922ec31a9b38c15316283706a9aab0ffab2101a18f7bf106165f2e",
        ),
        (
            "active",
            "62b226064d2597a4ca6a67f9f2c20a79a815732b",
            "passed",
            "digital-colleagues-runtime",
            "sha256:a5bb41bdb85bf7b5a75dc79967e26943c098b024b64fdd345f5b4c6f4688991d",
        ),
        (
            "active",
            "62b226064d2597a4ca6a67f9f2c20a79a815732b",
            "passed",
            "digital-colleagues-studio",
            "sha256:7791d80d9fa464bbd1574601deba5a30ca6d980dab8c8275c24c117fae81e4c9",
        ),
    )
    from scripts.check_p10_distribution import (  # type: ignore[attr-defined]
        GateError as P10DistributionError,
    )
    from scripts.check_p10_distribution import (
        _registry_exchange,
        _verify_attestation,
        _verify_cosign,
    )

    gh_path = shutil.which("gh")
    cosign_path = shutil.which("cosign")
    if gh_path is None or cosign_path is None:
        raise P12GateError("P12 protected registry verification tools are unavailable")
    verification_cache = working / "verification-cache"
    verification_cache.mkdir(mode=0o700)
    verification_environment = os.environ.copy()
    verification_environment["P10_REMOTE_USE_INSTALLED_TOOLS"] = "1"
    verification_environment["TMPDIR"] = str(working)
    verification_environment["XDG_CACHE_HOME"] = str(verification_cache)
    protected_sets: dict[str, dict[str, object]] = {}
    for classification, source_commit, lifecycle, subject, digest in digests:
        try:
            _, manifest_bytes = _registry_exchange(f"ghcr.io/jeremyliu1220/{subject}", digest)
            if f"sha256:{hashlib.sha256(manifest_bytes).hexdigest()}" != digest:
                raise P10DistributionError("protected_manifest_digest_mismatch")
            manifest = parse_json_unique(manifest_bytes)
            descriptors = manifest.get("manifests") if isinstance(manifest, dict) else None
            if not isinstance(descriptors, list) or len(descriptors) != 2:
                raise P10DistributionError("protected_manifest_platform_count_invalid")
            platforms = []
            for descriptor in descriptors:
                platform = descriptor.get("platform") if isinstance(descriptor, dict) else None
                if (
                    not isinstance(platform, dict)
                    or set(platform) != {"architecture", "os"}
                    or platform.get("os") != "linux"
                    or platform.get("architecture") not in {"amd64", "arm64"}
                ):
                    raise P10DistributionError("protected_manifest_platform_invalid")
                platforms.append(f"linux/{platform['architecture']}")
            if sorted(platforms) != ["linux/amd64", "linux/arm64"]:
                raise P10DistributionError("protected_manifest_platform_set_invalid")
            _verify_cosign(
                root,
                Path(cosign_path),
                f"ghcr.io/jeremyliu1220/{subject}",
                digest,
                source_commit,
                verification_environment,
            )
            _verify_attestation(
                root,
                Path(gh_path),
                f"ghcr.io/jeremyliu1220/{subject}",
                digest,
                source_commit,
                verification_environment,
            )
        except (OSError, subprocess.SubprocessError, P10DistributionError) as exc:
            raise P12GateError(
                "P12 protected signature or attestation verification failed"
            ) from exc
        entry = protected_sets.setdefault(
            classification,
            {
                "lifecycle": lifecycle,
                "source_commit": source_commit,
                "source_tag": f"sha-{source_commit}",
            },
        )
        entry["runtime_digest" if subject.endswith("runtime") else "studio_digest"] = digest
    historical_runs: list[dict[str, object]] = []
    for run_id, protected_head, conclusion in P10_RUNS:
        historical = _gh_json(["api", f"/repos/{REPOSITORY}/actions/runs/{run_id}"], cwd=root)
        if (
            not isinstance(historical, dict)
            or historical.get("id") != run_id
            or historical.get("name") != "CI"
            or historical.get("event") != "workflow_dispatch"
            or historical.get("status") != "completed"
            or historical.get("head_branch") != "codex/p10-mac-quickstart"
            or historical.get("head_sha") != protected_head
            or historical.get("conclusion") != conclusion
        ):
            raise P12GateError("P12 protected P10 workflow-run identity drifted")
        historical_runs.append(
            {
                "conclusion": conclusion,
                "event": "workflow_dispatch",
                "head_branch": "codex/p10-mac-quickstart",
                "head_sha": protected_head,
                "run_id": run_id,
                "status": "completed",
                "workflow_name": "CI",
            }
        )
    protection_identity = {
        "certificate_identity": (
            "https://github.com/jeremyliu1220/digital-colleagues/"
            ".github/workflows/ci.yml@refs/heads/codex/p10-mac-quickstart"
        ),
        "historical_runs": historical_runs,
        "inventories": inventories,
        "oidc_issuer": "https://token.actions.githubusercontent.com",
        "protected_sets": protected_sets,
        "repository": REPOSITORY,
        "required_platforms": ["linux/amd64", "linux/arm64"],
        "subjects": [f"ghcr.io/jeremyliu1220/{subject}" for subject in subjects],
        "workflow_path": WORKFLOW_PATH,
        "workflow_ref": "refs/heads/codex/p10-mac-quickstart",
    }
    protection_digest = f"sha256:{hashlib.sha256(canonical_json(protection_identity)).hexdigest()}"
    registry_result = {
        **protection_identity,
        "attestations": "passed",
        "bundles": "passed",
        "manifest_lookups": "passed",
        "publication_count": 0,
        "schema": "digital-colleagues.p12-v4-current-p10-registry-protection.v1",
        "signatures": "passed",
        "status": "passed",
    }
    registry_result_digest = f"sha256:{hashlib.sha256(canonical_json(registry_result)).hexdigest()}"
    receipts = [
        _safe_envelope_receipt(projections["current-ci"]),
        _safe_envelope_receipt(projections["portable-history"]),
    ]
    portable_inventory = portable_envelope["inventory"]
    if not isinstance(portable_inventory, dict):
        raise P12GateError("P12 portable envelope inventory is malformed")
    excluded_results = portable_inventory.get("excluded_results")
    if not isinstance(excluded_results, list):
        raise P12GateError("P12 portable envelope excluded results are malformed")
    if [result.get("gate_id") for result in excluded_results] != list(EXCLUDED_GATE_IDS):
        raise P12GateError("P12 portable envelope exclusion order drifted")
    return {
        "ci": {
            "base_ref": "main",
            "base_sha": BASE_COMMIT,
            "event": "pull_request",
            "head_branch": V4_BRANCH,
            "head_sha": implementation_head,
            "jobs": receipts,
            "pull_request_number": number,
            "run_attempt": ci_run_attempt,
            "run_id": ci_run_id,
            "workflow_path": WORKFLOW_PATH,
        },
        "inventory": {
            "blob": committed_binding["inventory_blob"],
            "digest": committed_binding["inventory_digest"],
            "evidence_anchor_count": 17,
            "excluded_acceptance_gate_count": 5,
            "excluded_gate_ids": list(EXCLUDED_GATE_IDS),
            "excluded_results": excluded_results,
            "included_acceptance_gate_count": 124,
            "item_results_digest": portable_inventory["item_results_digest"],
            "passed_acceptance_gate_count": 124,
            "path": INVENTORY_PATH,
            "setup_count": 5,
            "sha256": committed_binding["inventory_sha256"],
            "skip_count": 0,
            "total_item_count": 151,
        },
        "p10_protected_identity_digest": protection_digest,
        "p12_current_p10_registry_protection": {
            "result_digest": registry_result_digest,
            "status": "passed",
        },
    }


GATE_RESULT_MAX_BYTES = 4_194_304


def _same_file_identity(first: os.stat_result, second: os.stat_result) -> bool:
    return (first.st_dev, first.st_ino) == (second.st_dev, second.st_ino)


def _private_directory_metadata(metadata: os.stat_result) -> bool:
    return stat.S_ISDIR(metadata.st_mode) and stat.S_IMODE(metadata.st_mode) == 0o700


def _directory_binding_matches(directory: Path, descriptor: int) -> bool:
    try:
        path_metadata = os.lstat(directory)
        descriptor_metadata = os.fstat(descriptor)
    except OSError:
        return False
    return (
        _private_directory_metadata(path_metadata)
        and _private_directory_metadata(descriptor_metadata)
        and _same_file_identity(path_metadata, descriptor_metadata)
    )


@contextmanager
def _held_private_directory(directory: Path, *, label: str) -> Iterator[int]:
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    directory_only = getattr(os, "O_DIRECTORY", 0)
    if not directory.is_absolute() or not no_follow or not directory_only:
        raise P12GateError(f"P12 {label} directory boundary is unsupported")
    descriptor: int | None = None
    try:
        before = os.lstat(directory)
        descriptor = os.open(
            directory,
            os.O_RDONLY | no_follow | directory_only | getattr(os, "O_CLOEXEC", 0),
        )
        opened = os.fstat(descriptor)
        after = os.lstat(directory)
    except OSError as exc:
        if descriptor is not None:
            os.close(descriptor)
        raise P12GateError(f"P12 {label} directory is invalid") from exc
    if (
        not _private_directory_metadata(before)
        or not _private_directory_metadata(opened)
        or not _private_directory_metadata(after)
        or not _same_file_identity(before, opened)
        or not _same_file_identity(opened, after)
    ):
        os.close(descriptor)
        raise P12GateError(f"P12 {label} directory is invalid")
    try:
        yield descriptor
    finally:
        os.close(descriptor)


def _entry_name(path: Path, *, label: str) -> str:
    name = path.name
    if name in {"", ".", ".."} or path != path.parent / name:
        raise P12GateError(f"P12 {label} path is invalid")
    return name


def _regular_private_metadata(metadata: os.stat_result) -> bool:
    return (
        stat.S_ISREG(metadata.st_mode)
        and stat.S_IMODE(metadata.st_mode) == 0o600
        and metadata.st_nlink == 1
    )


def _open_bound_private_file(
    directory_descriptor: int,
    name: str,
    *,
    flags: int,
    label: str,
) -> tuple[int, os.stat_result]:
    descriptor: int | None = None
    try:
        before = os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False)
    except OSError as exc:
        raise P12GateError(f"P12 {label} is unavailable") from exc
    if not _regular_private_metadata(before):
        raise P12GateError(f"P12 {label} mode or identity is invalid")
    try:
        descriptor = os.open(
            name,
            flags | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
            dir_fd=directory_descriptor,
        )
        opened = os.fstat(descriptor)
        after = os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False)
    except OSError as exc:
        if descriptor is not None:
            os.close(descriptor)
        raise P12GateError(f"P12 {label} is unavailable") from exc
    if (
        not _regular_private_metadata(before)
        or not _regular_private_metadata(opened)
        or not _regular_private_metadata(after)
        or not _same_file_identity(before, opened)
        or not _same_file_identity(opened, after)
    ):
        os.close(descriptor)
        raise P12GateError(f"P12 {label} mode or identity is invalid")
    return descriptor, opened


def _write_all(descriptor: int, encoded: bytes, *, label: str) -> None:
    offset = 0
    while offset < len(encoded):
        try:
            written = os.write(descriptor, encoded[offset:])
        except InterruptedError:
            continue
        if written <= 0:
            raise OSError(errno.EIO, f"short write for {label}")
        offset += written


def _read_bounded(descriptor: int, *, limit: int, label: str) -> bytes:
    before = os.fstat(descriptor)
    if not _regular_private_metadata(before) or not 0 <= before.st_size <= limit:
        raise P12GateError(f"P12 {label} size or mode is invalid")
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(descriptor, min(65_536, limit + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > limit:
            raise P12GateError(f"P12 {label} is oversized")
    after = os.fstat(descriptor)
    if (
        not _regular_private_metadata(after)
        or not _same_file_identity(before, after)
        or after.st_size != total
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
    ):
        raise P12GateError(f"P12 {label} changed while it was read")
    return b"".join(chunks)


def _atomic_private_create(
    directory_descriptor: int,
    name: str,
    encoded: bytes,
    *,
    label: str,
    require_only_temporary: bool = False,
) -> os.stat_result:
    if name in {"", ".", ".."} or Path(name).name != name:
        raise P12GateError(f"P12 {label} filename is invalid")
    temporary_name = ""
    descriptor: int | None = None
    published = False
    temporary_identity: os.stat_result | None = None
    written: os.stat_result | None = None
    try:
        for _ in range(128):
            temporary_name = f".p12-{secrets.token_hex(16)}.tmp"
            try:
                descriptor = os.open(
                    temporary_name,
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | getattr(os, "O_NOFOLLOW", 0)
                    | getattr(os, "O_CLOEXEC", 0),
                    0o600,
                    dir_fd=directory_descriptor,
                )
            except FileExistsError:
                continue
            break
        if descriptor is None:
            raise P12GateError(f"P12 {label} temporary creation failed")
        os.fchmod(descriptor, 0o600)
        metadata = os.fstat(descriptor)
        temporary_identity = metadata
        if not _regular_private_metadata(metadata):
            raise P12GateError(f"P12 {label} temporary file is invalid")
        if require_only_temporary and os.listdir(directory_descriptor) != [temporary_name]:
            raise P12GateError(f"P12 {label} directory is no longer empty")
        _write_all(descriptor, encoded, label=label)
        os.fsync(descriptor)
        written = os.fstat(descriptor)
        if (
            not _regular_private_metadata(written)
            or not _same_file_identity(metadata, written)
            or written.st_size != len(encoded)
        ):
            raise P12GateError(f"P12 {label} temporary write is incomplete")
        os.close(descriptor)
        descriptor = None
        try:
            os.link(
                temporary_name,
                name,
                src_dir_fd=directory_descriptor,
                dst_dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
        except FileExistsError as exc:
            raise P12GateError(f"P12 {label} destination already exists") from exc
        published = True
        os.unlink(temporary_name, dir_fd=directory_descriptor)
        temporary_name = ""
        final = os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False)
        if (
            not _regular_private_metadata(final)
            or not _same_file_identity(written, final)
            or final.st_size != len(encoded)
        ):
            raise P12GateError(f"P12 {label} publication is invalid")
        os.fsync(directory_descriptor)
        return final
    except Exception:
        if descriptor is not None:
            if temporary_identity is None:
                try:
                    temporary_identity = os.fstat(descriptor)
                except OSError:
                    pass
            os.close(descriptor)
        if published and written is not None:
            _unlink_matching_entry(directory_descriptor, name, written)
        if temporary_name and temporary_identity is not None:
            _unlink_matching_entry(
                directory_descriptor,
                temporary_name,
                temporary_identity,
            )
        try:
            os.fsync(directory_descriptor)
        except OSError:
            pass
        raise


def _unlink_matching_entry(
    directory_descriptor: int,
    name: str,
    expected: os.stat_result,
) -> None:
    try:
        current = os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False)
        if _same_file_identity(current, expected):
            os.unlink(name, dir_fd=directory_descriptor)
            os.fsync(directory_descriptor)
    except OSError:
        pass


def write_preflight_receipt(directory: Path, receipt: dict[str, Any]) -> tuple[Path, str]:
    if not directory.is_absolute():
        raise P12GateError("P12 preflight receipt directory must be outside the repository")
    try:
        resolved_directory = directory.resolve(strict=True)
        resolved_root = ROOT.resolve(strict=True)
    except OSError as exc:
        raise P12GateError("P12 preflight receipt directory is invalid") from exc
    if resolved_directory == resolved_root or resolved_root in resolved_directory.parents:
        raise P12GateError("P12 preflight receipt directory is invalid")
    if (
        set(receipt) != RECEIPT_KEYS
        or receipt.get("schema") != RECEIPT_SCHEMA
        or receipt.get("lifecycle") != "pending_consumption"
        or not isinstance(receipt.get("nonce"), str)
        or SHA256.fullmatch(str(receipt.get("nonce", ""))) is None
    ):
        raise P12GateError("P12 preflight receipt closed schema is invalid")
    _exact_zero(receipt.get("cleanup_residue_count"), "preflight cleanup residue count")
    _exact_zero(receipt.get("publication_count"), "preflight publication count")
    forbidden_keys = {
        "actions_log",
        "full_actions_log",
        "complete_envelope",
        "raw_envelope",
        "encoded_envelope",
        "decoded_envelope",
        "safe_envelope",
        "safe_projection",
        "authorization_header",
        "credential",
        "token",
        "certificate_content",
        "absolute_ca_path",
        "receipt_path",
    }

    def safe_receipt_value(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str) or key.lower() in forbidden_keys:
                    raise P12GateError("P12 preflight receipt contains a forbidden field")
                safe_receipt_value(item)
        elif isinstance(value, list):
            for item in value:
                safe_receipt_value(item)
        elif isinstance(value, str):
            lowered = value.lower()
            if (
                str(ROOT) in value
                or str(Path.home()) in value
                or "authorization: bearer" in lowered
                or re.search(r"(?:gh[opsu]_|github_pat_)[a-z0-9_]", lowered)
            ):
                raise P12GateError("P12 preflight receipt contains unsafe retained text")

    safe_receipt_value(receipt)
    encoded = canonical_json(receipt)
    destination = directory / "p12-preflight-receipt.json"
    with _held_private_directory(directory, label="preflight receipt") as directory_descriptor:
        try:
            current_resolved = directory.resolve(strict=True)
        except OSError as exc:
            raise P12GateError("P12 preflight receipt directory is invalid") from exc
        if (
            current_resolved != resolved_directory
            or not _directory_binding_matches(directory, directory_descriptor)
            or os.listdir(directory_descriptor)
        ):
            raise P12GateError("P12 preflight receipt directory must be newly empty")
        published = _atomic_private_create(
            directory_descriptor,
            destination.name,
            encoded,
            label="preflight receipt",
            require_only_temporary=True,
        )
        if not _directory_binding_matches(directory, directory_descriptor) or os.listdir(
            directory_descriptor
        ) != [destination.name]:
            _unlink_matching_entry(directory_descriptor, destination.name, published)
            raise P12GateError("P12 preflight receipt directory changed during publication")
    return destination, hashlib.sha256(encoded).hexdigest()


def run_evidence_preflight(
    root: Path,
    *,
    implementation_head: str,
    ci_run_id: str,
    ci_run_attempt: str,
    receipt_directory: str,
) -> dict[str, Any]:
    if (
        SHA.fullmatch(implementation_head) is None
        or not re.fullmatch(r"[1-9][0-9]*", ci_run_id)
        or not re.fullmatch(r"[1-9][0-9]*", ci_run_attempt)
        or not receipt_directory
    ):
        raise P12GateError(
            "P12 preflight requires exact head, positive run/attempt, and receipt directory"
        )
    if implementation_head != git(root, "rev-parse", "HEAD"):
        raise P12GateError("P12 preflight implementation head is not exact HEAD")
    if (root / SUMMARY_PATH).exists():
        raise P12GateError("P12 preflight requires the summary to be absent")
    check_repository(root, mode="implementation")
    _verify_locked_file(root, PYPROJECT)
    _verify_locked_file(root, PYTHON_LOCK)
    before = git(
        root,
        "status",
        "--porcelain=v2",
        "--untracked-files=all",
        "--ignored=matching",
    )
    with _private_umask(), tempfile.TemporaryDirectory(prefix="dc-p12-v4-preflight-") as value:
        temporary = Path(value)
        os.chmod(temporary, 0o700)
        remote = _github_and_ghcr(
            root,
            implementation_head=implementation_head,
            ci_run_id=int(ci_run_id),
            ci_run_attempt=int(ci_run_attempt),
            working=temporary,
        )
        python, environment = _prepare_preflight_python(root, temporary)
        package_report = _package_report(root, python, environment)
        bundle_value = package_report.pop("certifi_bundle")
        if not isinstance(bundle_value, str):
            raise P12GateError("P12 certifi CA bundle identity is invalid")
        certifi_bundle = Path(bundle_value)
        tls_classes: list[str] = []
        for _host, url in (
            ("api.github.com", "https://api.github.com/"),
            ("ghcr.io", "https://ghcr.io/v2/"),
        ):
            try:
                tls_classes.append(_tls_probe(url))
            except (OSError, urllib.error.URLError) as exc:
                if not ca_fallback_allowed(exc):
                    raise P12GateError("P12 default TLS probe failed for a non-CA reason") from exc
                tls_classes.append(_tls_probe(url, certifi_bundle))
        if len(tls_classes) != 2 or any(
            value not in {"system_default", "locked_certifi"} for value in tls_classes
        ):
            raise P12GateError("P12 TLS verification class is invalid")
        ca_class = "locked_certifi" if "locked_certifi" in tls_classes else "system_default"
        package_verification = {
            "certifi_bundle_sha256": package_report["certifi_bundle_sha256"],
            "comparison": "packaging.version.Version",
            "direct": package_report["direct"],
            "installed_version_api": "importlib.metadata.version",
            "lock": {"blob": PYTHON_LOCK[1], "sha256": PYTHON_LOCK[2]},
            "locked": package_report["locked"],
            "pyproject": {"blob": PYPROJECT[1], "sha256": PYPROJECT[2]},
            "status": "passed",
        }
    if (
        git(
            root,
            "status",
            "--porcelain=v2",
            "--untracked-files=all",
            "--ignored=matching",
        )
        != before
    ):
        raise P12GateError("P12 preflight changed repository state")
    tree = git(root, "rev-parse", "HEAD^{tree}")
    records = implementation_range(root, implementation_head)
    issued = datetime.now(UTC)
    receipt = {
        "acceptance": {"blob": ACCEPTANCE_BLOB, "commit": ACCEPTANCE_COMMIT},
        "ca_verification": {
            "bundle_sha256": (CERTIFI_BUNDLE_SHA256 if ca_class == "locked_certifi" else None),
            "certifi_version": CERTIFI_VERSION,
            "class": ca_class,
            "status": "passed",
        },
        "ci": remote["ci"],
        "cleanup_residue_count": 0,
        "expires_at": (issued + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "implementation": {
            "head": implementation_head,
            "ordered_commits": [record["commit"] for record in records],
            "range_digest": implementation_range_digest(records),
            "tree": tree,
        },
        "inventory": remote["inventory"],
        "issued_at": issued.isoformat().replace("+00:00", "Z"),
        "lifecycle": "pending_consumption",
        "nonce": secrets.token_hex(32),
        "p10_protected_identity_digest": remote["p10_protected_identity_digest"],
        "p12_current_p10_registry_protection": remote["p12_current_p10_registry_protection"],
        "package_verification_digest": (
            f"sha256:{hashlib.sha256(canonical_json(package_verification)).hexdigest()}"
        ),
        "platform_status": dict(PLATFORM_STATUS),
        "publication_count": 0,
        "repository": REPOSITORY,
        "schema": RECEIPT_SCHEMA,
    }
    validate_preflight_receipt(
        root,
        receipt,
        head=implementation_head,
        tree=tree,
        records=records,
    )
    _, digest = write_preflight_receipt(Path(receipt_directory), receipt)
    return {
        "schema_version": 1,
        "gate": "p12_evidence_preflight",
        "status": "passed",
        "receipt_name": "p12-preflight-receipt.json",
        "receipt_sha256": digest,
        "implementation_head": implementation_head,
        "ci_run_id": int(ci_run_id),
        "ci_run_attempt": int(ci_run_attempt),
        "repository_mutation_count": 0,
        "remote_mutation_count": 0,
        "publication_count": 0,
    }


def _emit(result: dict[str, Any], path: str | None) -> None:
    serialized = canonical_json(result)
    if path:
        destination = Path(path)
        if not destination.is_absolute():
            raise P12GateError("P12 JSON output path must be absolute")
        name = _entry_name(destination, label="JSON output")
        with _held_private_directory(
            destination.parent,
            label="JSON output",
        ) as directory_descriptor:
            try:
                os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False)
            except FileNotFoundError:
                published = _atomic_private_create(
                    directory_descriptor,
                    name,
                    serialized,
                    label="JSON output",
                )
                if not _directory_binding_matches(destination.parent, directory_descriptor):
                    _unlink_matching_entry(directory_descriptor, name, published)
                    raise P12GateError(
                        "P12 JSON output directory changed during publication"
                    ) from None
            else:
                descriptor, opened = _open_bound_private_file(
                    directory_descriptor,
                    name,
                    flags=os.O_WRONLY,
                    label="JSON output",
                )
                write_started = False
                try:
                    if opened.st_size != 0:
                        raise P12GateError("P12 JSON output destination is not empty")
                    if not _directory_binding_matches(
                        destination.parent,
                        directory_descriptor,
                    ):
                        raise P12GateError("P12 JSON output directory changed before writing")
                    os.ftruncate(descriptor, 0)
                    write_started = True
                    _write_all(descriptor, serialized, label="JSON output")
                    os.fsync(descriptor)
                    written = os.fstat(descriptor)
                    current = os.stat(
                        name,
                        dir_fd=directory_descriptor,
                        follow_symlinks=False,
                    )
                    if (
                        not _regular_private_metadata(written)
                        or not _regular_private_metadata(current)
                        or not _same_file_identity(opened, written)
                        or not _same_file_identity(written, current)
                        or written.st_size != len(serialized)
                        or not _directory_binding_matches(
                            destination.parent,
                            directory_descriptor,
                        )
                    ):
                        raise P12GateError("P12 JSON output changed while it was written")
                except Exception:
                    if write_started:
                        try:
                            os.ftruncate(descriptor, 0)
                            os.fsync(descriptor)
                        except OSError:
                            pass
                    raise
                finally:
                    os.close(descriptor)
    else:
        output = serialized + b"\n"
        if sys.stdout.buffer.write(output) != len(output):
            raise OSError(errno.EIO, "short write for P12 JSON output")
        sys.stdout.buffer.flush()


def _load_gate_result(path_value: str) -> dict[str, Any]:
    path = Path(path_value)
    if not path.is_absolute():
        raise P12GateError("P12 CI gate result path must be absolute")
    name = _entry_name(path, label="CI gate result")
    with _held_private_directory(path.parent, label="CI gate result") as directory_descriptor:
        descriptor, _ = _open_bound_private_file(
            directory_descriptor,
            name,
            flags=os.O_RDONLY,
            label="CI gate result",
        )
        try:
            encoded = _read_bounded(
                descriptor,
                limit=GATE_RESULT_MAX_BYTES,
                label="CI gate result",
            )
            current = os.stat(
                name,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            opened = os.fstat(descriptor)
            if not _same_file_identity(opened, current) or not _directory_binding_matches(
                path.parent, directory_descriptor
            ):
                raise P12GateError("P12 CI gate result changed while it was read")
        finally:
            os.close(descriptor)
    value = parse_json_unique(encoded)
    if canonical_json(value) != encoded or not isinstance(value, dict):
        raise P12GateError("P12 CI gate result is not canonical safe JSON")
    return value


def _write_safe_projection(path_value: str, value: dict[str, object]) -> None:
    path = Path(path_value)
    if not path.is_absolute():
        raise P12GateError("P12 safe projection destination is invalid")
    name = _entry_name(path, label="safe projection")
    with _held_private_directory(path.parent, label="safe projection") as directory_descriptor:
        published = _atomic_private_create(
            directory_descriptor,
            name,
            canonical_json(value),
            label="safe projection",
        )
        if not _directory_binding_matches(path.parent, directory_descriptor):
            _unlink_matching_entry(directory_descriptor, name, published)
            raise P12GateError("P12 safe projection directory changed during publication")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scope",
        choices=(
            "test",
            "current-ci",
            "portable-history",
            "implementation-check",
            "ci",
            "final-check",
            "evidence-preflight",
            "current-p11-tests",
            "p12-tests",
            "emit-ci-envelope",
            "extract-ci-envelope",
        ),
        default="implementation-check",
    )
    parser.add_argument("--json-output")
    parser.add_argument("--implementation-head", default="")
    parser.add_argument("--ci-run-id", default="")
    parser.add_argument("--ci-run-attempt", default="")
    parser.add_argument("--receipt-directory", default="")
    parser.add_argument("--job-kind", default="")
    parser.add_argument("--gate-result", default="")
    parser.add_argument("--gate-exit-status", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--attempt", default="")
    parser.add_argument("--job-database-id", default="")
    parser.add_argument("--expected-job-id", default="")
    parser.add_argument("--expected-job-name", default="")
    parser.add_argument("--head-sha", default="")
    parser.add_argument("--safe-output", default="")
    args = parser.parse_args(argv)
    try:
        if args.scope == "emit-ci-envelope":
            if not re.fullmatch(r"-?[0-9]+", args.gate_exit_status):
                raise P12GateError("P12 CI gate exit status argument is invalid")
            gate_result = _load_gate_result(args.gate_result)
            envelope = build_ci_envelope(
                ROOT,
                job_kind=args.job_kind,
                gate_result=gate_result,
                gate_exit_status=int(args.gate_exit_status),
            )
            line, _ = encode_ci_envelope(envelope)
            print(line, flush=True)
            return 0
        if args.scope == "extract-ci-envelope":
            if not all(
                re.fullmatch(r"[1-9][0-9]*", value)
                for value in (args.run_id, args.attempt, args.job_database_id)
            ):
                raise P12GateError("P12 envelope extraction numeric identity is invalid")
            projection = extract_ci_envelope(
                sys.stdin.buffer,
                run_id=int(args.run_id),
                attempt=int(args.attempt),
                job_database_id=int(args.job_database_id),
                expected_job_id=args.expected_job_id,
                expected_job_name=args.expected_job_name,
                head_sha=args.head_sha,
            )
            _write_safe_projection(args.safe_output, projection)
            return 0
        if args.scope == "current-p11-tests":
            result = run_current_p11_tests(ROOT, stream=sys.stderr)
        elif args.scope == "p12-tests":
            result = run_p12_tests(ROOT, stream=sys.stderr)
        elif args.scope == "test":
            result = run_p12_tests(ROOT, stream=sys.stderr)
        elif args.scope == "implementation-check":
            result = run_implementation(ROOT)
        elif args.scope == "evidence-preflight":
            result = run_evidence_preflight(
                ROOT,
                implementation_head=args.implementation_head,
                ci_run_id=args.ci_run_id,
                ci_run_attempt=args.ci_run_attempt,
                receipt_directory=args.receipt_directory,
            )
        else:
            with tempfile.TemporaryDirectory(prefix="dc-p12-toolchain-") as value:
                temporary = Path(value)
                if args.scope == "current-ci":
                    result = run_current_ci(ROOT, temporary)
                elif args.scope == "portable-history":
                    result = run_portable_history(ROOT, temporary)
                elif args.scope == "final-check":
                    result = run_ci(ROOT, temporary)
                    if result.get("mode") != "final_candidate":
                        raise P12GateError("P12 final scope requires the summary-only tip")
                else:
                    result = run_ci(ROOT, temporary)
        output_path = args.json_output or os.environ.get("P12_JSON_OUTPUT")
        _emit(result, output_path)
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
        HistoricalInventoryError,
        P12GateError,
    ) as exc:
        print(f"P12 toolchain failed: {_safe(str(exc))}", file=sys.stderr)
        return 2
    return 0 if result.get("status", "passed") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
