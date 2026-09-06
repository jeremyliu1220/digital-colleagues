# SPDX-License-Identifier: Apache-2.0

"""Validate and atomically write static/synthetic P9 evidence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.check_p9_repository import ACCEPTANCE_COMMIT, BASE_COMMIT, BRANCH

REQUIRED_GATES = frozenset(
    {
        "retained_p8_toolchain",
        "public_boundary",
        "p9_repository",
        "p9_provenance",
        "p9_rebaseline",
        "p9_unittest",
        "git_diff_check",
    }
)
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
SECRET_KEYS = {
    "api_key",
    "client_secret",
    "cookie",
    "credential",
    "password",
    "private_payload",
    "refresh_token",
    "session_credential",
    "tenant_id",
    "token",
}


class EvidenceError(RuntimeError):
    """P9 evidence is incomplete, unsafe, or outside the fixed boundary."""


def public_tree_digest(root: Path, excluded: Path) -> str:
    aggregate = hashlib.sha256()
    documents = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path != excluded
        and ".git" not in path.relative_to(root).parts
        and not any(
            part
            in {
                "node_modules",
                "__pycache__",
                ".mypy_cache",
                ".pytest_cache",
                ".ruff_cache",
                "build",
                "dist",
            }
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
        raise EvidenceError("P9 unittest result shape is incomplete")
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
        or not isinstance(value["test_ids"], list)
        or len(value["test_ids"]) != value["tests_run"]
        or not isinstance(value["fault_boundaries"], list)
        or not value["fault_boundaries"]
    ):
        raise EvidenceError("P9 unittest suite did not pass with positive counts and zero skips")
    return value


def _assert_safe(value: object, *, root: Path) -> None:
    forbidden_values = (str(root), str(Path.home()), "/.codex/attachments/")
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in SECRET_KEYS:
                raise EvidenceError("P9 evidence contains a secret-bearing field")
            _assert_safe(child, root=root)
    elif isinstance(value, list):
        for child in value:
            _assert_safe(child, root=root)
    elif isinstance(value, str):
        if any(item and item in value for item in forbidden_values):
            raise EvidenceError("P9 evidence contains a local absolute or attachment path")
        local_path_pattern = r"/" + r"(?:Users|home)/[^\s`]+"
        if re.search(local_path_pattern, value):
            raise EvidenceError("P9 evidence contains a local absolute path")
        if re.search(r"(?:sk-|bearer |session=|tenant[_-]?id=)[A-Za-z0-9_.=-]{12,}", value, re.I):
            raise EvidenceError("P9 evidence contains credential or live-identifier material")


def write_p9_evidence(
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
    implementation_committed: bool,
) -> dict[str, Any]:
    if tree_clean is not True:
        raise EvidenceError("P9 evidence requires a clean implementation tree")
    if implementation_committed is not True:
        raise EvidenceError("P9 evidence requires a committed implementation")
    if branch != BRANCH:
        raise EvidenceError("P9 evidence requires the exact development branch")
    if merge_base != BASE_COMMIT:
        raise EvidenceError("P9 evidence merge-base drifted")
    if not COMMIT_PATTERN.fullmatch(implementation_commit):
        raise EvidenceError("P9 implementation commit is not a real SHA")
    if implementation_commit in {BASE_COMMIT, ACCEPTANCE_COMMIT}:
        raise EvidenceError("P9 implementation commit is missing")
    if not DIGEST_PATTERN.fullmatch(tree_digest):
        raise EvidenceError("P9 evidence digest shape is invalid")
    missing = REQUIRED_GATES - verified_gates
    if missing:
        raise EvidenceError("P9 evidence is missing required mechanical gates")
    outcome = validate_unittest(unittest_outcome)

    repository = results.get("repository", {})
    provenance = results.get("provenance", {})
    rebaseline = results.get("rebaseline", {})
    if (
        repository.get("candidate_phase") != "implementation"
        or repository.get("acceptance_contract_immutable") is not True
        or repository.get("acceptance_commit_isolated") is not True
        or repository.get("historical_drift_count") != 0
        or repository.get("migration_count") != 7
        or repository.get("migration_008") is not False
        or repository.get("product_runtime_implementation_change_count") != 0
        or repository.get("cleanup_residue_count") != 0
        or any(
            repository.get(key) != 0
            for key in (
                "staged_change_path_count",
                "unstaged_change_path_count",
                "untracked_path_count",
            )
        )
    ):
        raise EvidenceError("P9 repository boundary is incomplete")
    if (
        provenance.get("gate") != "p9_provenance_clean"
        or provenance.get("transformed_migration_count") != 0
        or provenance.get("source_migration_count") != 0
        or provenance.get("parent_working_tree_read") is not False
    ):
        raise EvidenceError("P9 provenance boundary is incomplete")
    if (
        rebaseline.get("gate") != "p9_rebaseline_clean"
        or rebaseline.get("p9_through_p15_order") != "passed"
        or rebaseline.get("fixed_product_decisions") != "passed"
        or rebaseline.get("product_runtime_implementation_change_count") != 0
        or rebaseline.get("openai_live") != "not_evaluated"
        or rebaseline.get("microsoft_365_live") != "not_evaluated"
        or rebaseline.get("human_evaluation") != "not_evaluated"
    ):
        raise EvidenceError("P9 rebaseline claim boundary is incomplete")

    summary: dict[str, Any] = {
        "schema_version": 1,
        "milestone": "P9",
        "status": "development_complete_awaiting_independent_acceptance",
        "claim": "p9_productization_rebaseline_candidate",
        "fixed_base": BASE_COMMIT,
        "merge_base": merge_base,
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "development_branch": BRANCH,
        "implementation_commit": implementation_commit,
        "tree_digest": tree_digest,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "verified_gates": sorted(verified_gates),
        "unittest": outcome,
        "repository": repository,
        "provenance": provenance,
        "rebaseline": rebaseline,
        "evidence_classes": {
            "documentation_and_governance": "static",
            "mechanical_regression": "synthetic_offline",
            "openai_live": "not_evaluated",
            "microsoft_365_live": "not_evaluated",
            "human_evaluation": "not_evaluated",
        },
        "claim_exclusions": [
            "product_or_runtime_implementation",
            "agent_package_or_multi_agent_runtime",
            "openai_or_microsoft_365_compatibility",
            "live_provider_acceptance",
            "human_evaluation",
            "formal_release_or_publication",
            "production_readiness",
            "production_security_or_privacy",
            "high_availability",
            "enterprise_iam_or_tenancy",
            "compliance_certification",
            "p10_through_p15_development",
        ],
        "migrations": {
            "immutable_versions": [1, 2, 3, 4, 5, 6, 7],
            "migration_008": "absent",
        },
    }
    _assert_safe(summary, root=root)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=evidence_path.parent,
        prefix=".p9-summary-",
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
