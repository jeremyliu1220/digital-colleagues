# SPDX-License-Identifier: Apache-2.0

"""Validate and atomically write safe synthetic/offline P7 evidence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.check_p7_repository import ACCEPTANCE_COMMIT, BASE_COMMIT, BRANCH

REQUIRED_GATES = frozenset(
    {
        "p4_aggregate",
        "p5_aggregate",
        "p6_aggregate",
        "public_boundary",
        "p7_repository",
        "p7_provenance",
        "p7_architecture",
        "p7_model_adapter",
        "p7_channel_adapter",
        "p7_configuration",
        "p7_abuse",
        "p7_compose",
        "p7_compose_runtime",
        "p7_golden_path",
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
    }
)
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
SECRET_KEYS = {
    "api_key",
    "cookie",
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
    """P7 evidence is incomplete, unsafe, or outside the fixed development boundary."""


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
        raise EvidenceError("P7 unittest result shape is incomplete")
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
        raise EvidenceError("P7 unittest suite did not pass with zero skips")
    if not isinstance(value["test_ids"], list) or not isinstance(value["fault_boundaries"], list):
        raise EvidenceError("P7 unittest identities are invalid")
    return value


def _assert_safe(value: object, *, root: Path) -> None:
    forbidden_values = (str(root), str(Path.home()))
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in SECRET_KEYS:
                raise EvidenceError("P7 evidence contains a secret-bearing field")
            _assert_safe(child, root=root)
    elif isinstance(value, list):
        for child in value:
            _assert_safe(child, root=root)
    elif isinstance(value, str):
        if any(item and item in value for item in forbidden_values):
            raise EvidenceError("P7 evidence contains a local absolute path")
        if re.search(r"(?:sk-|bearer |session=|dc_session=)[A-Za-z0-9_=-]{12,}", value, re.I):
            raise EvidenceError("P7 evidence contains credential-shaped material")


def write_p7_evidence(
    *,
    evidence_path: Path,
    root: Path,
    results: dict[str, dict[str, Any]],
    unittest_outcome: dict[str, Any],
    verified_gates: set[str],
    branch: str,
    implementation_commit: str,
    merge_base: str,
    tree_digest: str,
    tree_clean: bool,
) -> dict[str, Any]:
    if tree_clean is not True:
        raise EvidenceError("P7 evidence requires a clean implementation tree")
    if branch != BRANCH or merge_base != BASE_COMMIT:
        raise EvidenceError("P7 evidence branch or merge-base drifted")
    if not COMMIT_PATTERN.fullmatch(implementation_commit):
        raise EvidenceError("implementation commit is not a real commit SHA")
    if implementation_commit == ACCEPTANCE_COMMIT:
        raise EvidenceError("P7 implementation commit is missing")
    if not DIGEST_PATTERN.fullmatch(tree_digest):
        raise EvidenceError("P7 evidence digest shape is invalid")
    missing = REQUIRED_GATES - verified_gates
    if missing:
        raise EvidenceError("P7 evidence is missing required mechanical gates")
    outcome = validate_unittest(unittest_outcome)
    repository = results.get("repository", {})
    if (
        repository.get("acceptance_documents_immutable") is not True
        or repository.get("historical_drift_count") != 0
        or repository.get("migration_008") is not False
        or repository.get("residue_count") != 0
    ):
        raise EvidenceError("P7 repository history or residue boundary is incomplete")
    runtime = results.get("compose_runtime", {})
    cleanup = runtime.get("cleanup") if isinstance(runtime, dict) else None
    adapter_container = runtime.get("adapter_container") if isinstance(runtime, dict) else None
    if (
        runtime.get("status") != "passed"
        or runtime.get("unexpected_external_egress") != 0
        or runtime.get("live_provider_evidence") != "not_evaluated"
        or not isinstance(cleanup, dict)
        or cleanup.get("passed") is not True
        or cleanup.get("containers_remaining") != 0
        or cleanup.get("networks_remaining") != 0
        or cleanup.get("volumes_remaining") != 0
        or cleanup.get("credential_files_remaining") != 0
        or cleanup.get("stub_processes_remaining") != 0
        or not isinstance(adapter_container, dict)
        or adapter_container.get("status") != "passed"
    ):
        raise EvidenceError("P7 actual Compose runtime or cleanup is incomplete")
    abuse = results.get("abuse", {})
    if (
        abuse.get("authority_expansions") != 0
        or abuse.get("human_approvals_from_provider") != 0
        or abuse.get("unexpected_external_egress") != 0
        or abuse.get("blind_ambiguous_resends") != 0
        or abuse.get("public_boundary_exceptions") != 0
    ):
        raise EvidenceError("P7 abuse results contain a nonzero escape")
    golden = results.get("golden", {})
    if (
        golden.get("deterministic_reference_unchanged") is not True
        or golden.get("claim") != "optional_adapter_contracts_passed"
        or golden.get("human_evaluation") != "not_evaluated"
        or golden.get("live_provider_evidence") != "not_evaluated"
    ):
        raise EvidenceError("P7 Golden Path claim boundary is incomplete")
    summary: dict[str, Any] = {
        "schema_version": 1,
        "milestone": "P7",
        "status": "development_complete_awaiting_independent_acceptance",
        "claim": "optional_adapter_contracts_passed",
        "evidence_classes": {
            "contract": "synthetic_offline",
            "human_evaluation": "not_evaluated",
            "live_provider": "not_evaluated",
        },
        "fixed_base": BASE_COMMIT,
        "merge_base": merge_base,
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "development_branch": BRANCH,
        "implementation_commit": implementation_commit,
        "tree_digest": tree_digest,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "verified_gates": sorted(verified_gates),
        "unittest": outcome,
        "python_tests": {
            key: outcome[key]
            for key in (
                "tests_run",
                "failures",
                "errors",
                "skipped",
                "expected_failures",
                "unexpected_successes",
            )
        },
        "studio_tests": {
            "status": "passed",
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "unexpected_successes": 0,
        },
        "repository": repository,
        "provenance": results["provenance"],
        "architecture": results["architecture"],
        "model_adapter": results["model_adapter"],
        "channel_adapter": results["channel_adapter"],
        "configuration": results["configuration"],
        "abuse": abuse,
        "compose": results["compose"],
        "compose_runtime": runtime,
        "golden_path": golden,
        "historical_boundary": {
            "p0_through_p6_unchanged": True,
            "migrations_001_through_007_unchanged": True,
            "migration_008": False,
            "historical_evidence_collectors_run": False,
        },
        "wire_contracts": {
            "protocol_version": "dc-http-json-v1",
            "model": "strict_finite_json_server_authority_reconstructed",
            "channel": "exact_effect_five_outcomes_idempotency_bound",
            "reconciliation": "confirmed_applied_confirmed_absent_still_unknown",
        },
        "runtime_boundary": {
            "default": "deterministic_intelligence_and_reference_channel",
            "optional": "explicit_allowlisted_startup_opt_in",
            "external_calls": 0,
            "cleanup_residue": 0,
        },
        "claim_exclusions": [
            "human_evaluation",
            "live_provider_acceptance",
            "named_provider_compatibility",
            "real_message_delivery",
            "pilot_readiness",
            "production_reliability",
            "production_privacy_or_security",
            "production_readiness",
            "P8_release_readiness",
        ],
    }
    _assert_safe(summary, root=root)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=evidence_path.parent,
        prefix=".p7-summary-",
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
