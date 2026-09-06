# SPDX-License-Identifier: Apache-2.0

"""Validate and atomically write safe synthetic/offline P8 evidence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.check_p8_repository import BRANCH
from scripts.p8_release_support import ACCEPTANCE_COMMIT, BASE_COMMIT

REQUIRED_GATES = frozenset(
    {
        "accepted_p7_baseline",
        "public_boundary",
        "p8_repository",
        "p8_provenance",
        "p8_operations",
        "p8_backup_restore",
        "p8_diagnostics",
        "p8_supply_chain",
        "p8_reproducibility",
        "p8_release",
        "p8_compose_runtime",
        "p8_golden_path",
        "ruff_lint",
        "ruff_format",
        "mypy_strict",
        "python_unittest",
        "studio_eslint",
        "studio_prettier",
        "studio_typescript",
        "studio_vitest",
        "studio_vite_build",
        "git_diff_check",
        "p2_core_current_tree",
        "p3_architecture_current_tree",
        "p3_migrations_current_tree",
        "p3_persistence_current_tree",
        "p3_runtime_current_tree",
        "p3_golden_current_tree",
        "p4_architecture_current_tree",
        "p4_migrations_current_tree",
        "p4_authentication_current_tree",
        "p4_studio_current_tree",
        "p4_compose_current_tree",
        "p4_golden_current_tree",
        "p5_architecture_current_tree",
        "p5_migrations_current_tree",
        "p5_builder_current_tree",
        "p5_policy_current_tree",
        "p5_studio_current_tree",
        "p5_compose_current_tree",
        "p5_golden_current_tree",
        "p6_architecture_current_tree",
        "p6_migrations_current_tree",
        "p6_authentication_current_tree",
        "p6_rbac_current_tree",
        "p6_change_approval_current_tree",
        "p6_effect_approval_current_tree",
        "p6_audit_export_current_tree",
        "p6_abuse_current_tree",
        "p6_studio_current_tree",
        "p6_compose_current_tree",
        "p6_golden_current_tree",
        "p7_architecture_current_tree",
        "p7_model_adapter_current_tree",
        "p7_channel_adapter_current_tree",
        "p7_configuration_current_tree",
        "p7_abuse_current_tree",
        "p7_compose_current_tree",
        "p7_golden_current_tree",
    }
)
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
SECRET_KEYS = {
    "api_key",
    "cookie",
    "credential",
    "credential_digest",
    "credential_value",
    "csrf",
    "csrf_digest",
    "csrf_token",
    "private_payload",
    "session_credential",
    "token",
    "token_digest",
}


class EvidenceError(RuntimeError):
    """P8 evidence is incomplete, unsafe, or outside the fixed boundary."""


def public_tree_digest(root: Path, excluded: Path) -> str:
    aggregate = hashlib.sha256()
    documents = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path != excluded
        and ".git" not in path.relative_to(root).parts
        and not any(
            part in {"node_modules", "__pycache__", ".mypy_cache", ".ruff_cache", "dist"}
            for part in path.relative_to(root).parts
        )
    )
    for document in documents:
        relative = document.relative_to(root).as_posix().encode()
        digest = hashlib.sha256(document.read_bytes()).digest()
        for value in (relative, digest):
            aggregate.update(len(value).to_bytes(8, "big"))
            aggregate.update(value)
    return "sha256:" + aggregate.hexdigest()


def validate_unittest(value: dict[str, Any]) -> dict[str, Any]:
    required = {
        "tests_run",
        "failures",
        "errors",
        "skipped",
        "expected_failures",
        "unexpected_successes",
        "gate_passed",
        "test_ids",
        "fault_boundaries",
    }
    if set(value) != required:
        raise EvidenceError("P8 unittest result shape is incomplete")
    if (
        type(value["tests_run"]) is not int
        or value["tests_run"] < 1
        or value["gate_passed"] is not True
        or any(
            value[key] != 0
            for key in (
                "failures",
                "errors",
                "skipped",
                "expected_failures",
                "unexpected_successes",
            )
        )
    ):
        raise EvidenceError("P8 unittest suite did not pass with zero skips")
    if not isinstance(value["test_ids"], list) or not isinstance(value["fault_boundaries"], list):
        raise EvidenceError("P8 unittest identities are invalid")
    return value


def validate_studio_tests(value: dict[str, Any]) -> dict[str, Any]:
    required = {
        "command",
        "test_files",
        "test_count",
        "passed",
        "failed",
        "skipped",
        "errors",
        "unexpected_failures",
        "status",
        "result",
    }
    if set(value) != required:
        raise EvidenceError("Studio test result shape is incomplete")
    count_fields = (
        "test_files",
        "test_count",
        "passed",
        "failed",
        "skipped",
        "errors",
        "unexpected_failures",
    )
    if (
        value["command"] != "corepack npm test -- --reporter=json --outputFile=<temporary>"
        or any(type(value[key]) is not int or value[key] < 0 for key in count_fields)
        or value["test_files"] < 1
        or value["test_count"] < 1
        or value["passed"] != value["test_count"]
        or any(value[key] != 0 for key in ("failed", "skipped", "errors", "unexpected_failures"))
        or value["status"] != "passed"
        or value["result"] != "passed"
    ):
        raise EvidenceError("Studio tests did not pass with a positive count and zero skips")
    return value


def _assert_safe(value: object, *, root: Path) -> None:
    forbidden_values = (str(root), str(Path.home()))
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in SECRET_KEYS:
                raise EvidenceError("P8 evidence contains a secret-bearing field")
            _assert_safe(child, root=root)
    elif isinstance(value, list):
        for child in value:
            _assert_safe(child, root=root)
    elif isinstance(value, str):
        if any(item and item in value for item in forbidden_values):
            raise EvidenceError("P8 evidence contains a local absolute path")
        if re.search(r"(?:sk-|bearer |session=|dc_session=)[A-Za-z0-9_=-]{12,}", value, re.I):
            raise EvidenceError("P8 evidence contains credential-shaped material")


def write_p8_evidence(
    *,
    evidence_path: Path,
    root: Path,
    results: dict[str, dict[str, Any]],
    unittest_outcome: dict[str, Any],
    studio_test_outcome: dict[str, Any],
    verified_gates: set[str],
    branch: str,
    implementation_commit: str,
    merge_base: str,
    tree_digest: str,
    tree_clean: bool,
) -> dict[str, Any]:
    if tree_clean is not True:
        raise EvidenceError("P8 evidence requires a clean implementation tree")
    if branch != BRANCH or merge_base != BASE_COMMIT:
        raise EvidenceError("P8 evidence branch or merge-base drifted")
    if not COMMIT_PATTERN.fullmatch(implementation_commit):
        raise EvidenceError("P8 implementation commit is not a real SHA")
    if implementation_commit in {BASE_COMMIT, ACCEPTANCE_COMMIT}:
        raise EvidenceError("P8 implementation commit is missing")
    if not DIGEST_PATTERN.fullmatch(tree_digest):
        raise EvidenceError("P8 evidence digest shape is invalid")
    missing = REQUIRED_GATES - verified_gates
    if missing:
        raise EvidenceError("P8 evidence is missing required mechanical gates")
    outcome = validate_unittest(unittest_outcome)
    studio_outcome = validate_studio_tests(studio_test_outcome)
    repository = results.get("repository", {})
    if (
        repository.get("acceptance_documents_immutable") is not True
        or repository.get("historical_drift_count") != 0
        or repository.get("migration_008") is not False
        or repository.get("residue_count") != 0
    ):
        raise EvidenceError("P8 repository boundary is incomplete")
    supply_chain = results.get("supply_chain", {})
    if (
        supply_chain.get("unresolved_licenses") != 0
        or supply_chain.get("unresolved_attributions") != 0
        or supply_chain.get("record_count") != 243
    ):
        raise EvidenceError("P8 supply-chain boundary is incomplete")
    reproducibility = results.get("reproducibility", {})
    if (
        reproducibility.get("status") != "passed"
        or reproducibility.get("artifact_count") != 6
        or reproducibility.get("raw_oci_image_reproducibility_claimed") is not False
        or reproducibility.get("repository_residue") != 0
    ):
        raise EvidenceError("P8 reproducibility claim is incomplete")
    runtime = results.get("compose_runtime", {})
    cleanup = runtime.get("cleanup") if isinstance(runtime, dict) else None
    transition = runtime.get("first_release_transition") if isinstance(runtime, dict) else None
    runtime_toolchain = runtime.get("studio_build_toolchain") if isinstance(runtime, dict) else None
    if (
        runtime.get("status") != "passed"
        or runtime.get("external_provider_calls") != 0
        or runtime.get("human_evaluation") != "not_evaluated"
        or runtime.get("live_provider_evidence") != "not_evaluated"
        or runtime.get("five_minute_target") != "not_evaluated"
        or not isinstance(transition, dict)
        or transition.get("status") != "passed"
        or transition.get("source_commit") != BASE_COMMIT
        or transition.get("source_version") != "0.0.0"
        or transition.get("source_release_manifest") != "not_available_before_first_release"
        or transition.get("target_version") != "0.1.0"
        or transition.get("pre_upgrade_backup") != "created_and_verified_before_p8_service_start"
        or transition.get("rollback_runtime") != "exact_accepted_p7_git_object"
        or transition.get("rollback_state_equal") is not True
        or runtime_toolchain
        != {
            "host_node": "24.15.0",
            "host_npm": "11.12.1",
            "container_node": "24.15.0",
            "container_npm": "11.12.1",
            "container_build_asserted_and_runtime_metadata_verified": True,
        }
        or not isinstance(cleanup, dict)
        or cleanup.get("passed") is not True
        or any(
            cleanup.get(key) != 0
            for key in (
                "containers_remaining",
                "networks_remaining",
                "volumes_remaining",
                "backup_files_remaining",
                "credential_files_remaining",
                "diagnostic_bundles_remaining",
                "extracted_release_trees_remaining",
                "build_workspaces_remaining",
            )
        )
    ):
        raise EvidenceError("P8 Compose runtime or cleanup is incomplete")
    golden = results.get("golden", {})
    if (
        golden.get("status") != "passed"
        or golden.get("claim") != "v0_1_local_reference_release_candidate"
        or golden.get("human_evaluation") != "not_evaluated"
        or golden.get("live_provider_evidence") != "not_evaluated"
        or golden.get("five_minute_target") != "not_evaluated"
    ):
        raise EvidenceError("P8 Golden Path claim boundary is incomplete")
    current_tree_regressions = results.get("current_tree_regressions", {})
    if (
        not isinstance(current_tree_regressions, dict)
        or len(current_tree_regressions) != 37
        or any(
            not isinstance(result, dict)
            or not isinstance(result.get("gate"), str)
            or not result["gate"].endswith("_clean")
            for result in current_tree_regressions.values()
        )
    ):
        raise EvidenceError("P0-P7 current-tree regressions are incomplete")
    summary: dict[str, Any] = {
        "schema_version": 1,
        "milestone": "P8",
        "status": "development_complete_awaiting_independent_acceptance",
        "claim": "v0_1_local_reference_release_candidate",
        "release_version": "0.1.0",
        "fixed_base": BASE_COMMIT,
        "merge_base": merge_base,
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "development_branch": BRANCH,
        "implementation_commit": implementation_commit,
        "tree_digest": tree_digest,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "verified_gates": sorted(verified_gates),
        "unittest": outcome,
        "studio_tests": studio_outcome,
        "repository": repository,
        "provenance": results["provenance"],
        "operations": results["operations"],
        "backup_restore": results["backup_restore"],
        "diagnostics": results["diagnostics"],
        "supply_chain": supply_chain,
        "reproducibility": reproducibility,
        "release": results["release"],
        "compose_runtime": runtime,
        "golden_path": golden,
        "historical_boundary": results["accepted_p7"],
        "current_tree_regressions": current_tree_regressions,
        "evidence_classes": {
            "mechanical": "synthetic_offline",
            "docker_runtime": "actually_executed_synthetic_offline",
            "license_review": "declared_metadata_review_not_legal_advice",
            "human_evaluation": "not_evaluated",
            "live_provider": "not_evaluated",
        },
        "claim_exclusions": [
            "formal_release_or_publication",
            "production_readiness",
            "production_security_or_privacy",
            "enterprise_iam_or_tenancy",
            "named_provider_compatibility",
            "real_message_delivery",
            "human_evaluation",
            "five_minute_target",
            "post_v0_1_capabilities",
        ],
    }
    _assert_safe(summary, root=root)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=evidence_path.parent,
        prefix=".p8-summary-",
        delete=False,
    ) as handle:
        handle.write(serialized)
        temporary = Path(handle.name)
    try:
        os.replace(temporary, evidence_path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return summary
