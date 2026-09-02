# SPDX-License-Identifier: Apache-2.0

"""Validate and atomically write safe synthetic/offline P6 evidence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.check_p6_repository import ACCEPTANCE_COMMIT, BASE_COMMIT, BRANCH

REQUIRED_GATES = frozenset(
    {
        "p4_aggregate",
        "p5_aggregate",
        "public_boundary",
        "p6_repository",
        "p6_provenance",
        "p6_architecture",
        "p6_migrations",
        "p6_authentication",
        "p6_rbac",
        "p6_change_approval",
        "p6_effect_approval",
        "p6_audit_export",
        "p6_abuse",
        "p6_studio",
        "p6_compose",
        "p6_compose_runtime",
        "p6_golden_path",
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
    "token",
    "token_digest",
    "cookie",
    "csrf",
    "csrf_token",
    "csrf_digest",
    "session_credential",
    "credential_digest",
    "private_payload",
}


class EvidenceError(RuntimeError):
    """P6 evidence is incomplete, unsafe, or outside the fixed development boundary."""


def _framed_tree_digest(root: Path, excluded: Path) -> str:
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


def public_tree_digest(root: Path, excluded: Path) -> str:
    return _framed_tree_digest(root, excluded)


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
        raise EvidenceError("P6 unittest result shape is incomplete")
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
        raise EvidenceError("P6 unittest suite did not pass with zero skips")
    if not isinstance(value["test_ids"], list) or not isinstance(value["fault_boundaries"], list):
        raise EvidenceError("P6 unittest identities are invalid")
    return value


def _assert_safe(value: object, *, root: Path) -> None:
    forbidden_values = (str(root), str(Path.home()))
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in SECRET_KEYS:
                raise EvidenceError("P6 evidence contains a secret-bearing field")
            _assert_safe(child, root=root)
    elif isinstance(value, list):
        for child in value:
            _assert_safe(child, root=root)
    elif isinstance(value, str):
        if any(item and item in value for item in forbidden_values):
            raise EvidenceError("P6 evidence contains a local absolute path")
        if re.search(r"(?:sk-|session=|dc_session=)[A-Za-z0-9_-]{12,}", value):
            raise EvidenceError("P6 evidence contains credential-shaped material")


def write_p6_evidence(
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
    migration_digest: str,
) -> dict[str, Any]:
    if branch != BRANCH or merge_base != BASE_COMMIT:
        raise EvidenceError("P6 evidence branch or merge-base drifted")
    if not COMMIT_PATTERN.fullmatch(implementation_commit):
        raise EvidenceError("implementation commit is not a real commit SHA")
    if not DIGEST_PATTERN.fullmatch(tree_digest) or not DIGEST_PATTERN.fullmatch(migration_digest):
        raise EvidenceError("P6 evidence digest shape is invalid")
    missing = REQUIRED_GATES - verified_gates
    if missing:
        raise EvidenceError("P6 evidence is missing required mechanical gates")
    outcome = validate_unittest(unittest_outcome)
    compose = results.get("compose_runtime", {})
    cleanup = compose.get("cleanup") if isinstance(compose, dict) else None
    if (
        compose.get("status") != "passed"
        or not isinstance(cleanup, dict)
        or cleanup.get("passed") is not True
        or cleanup.get("containers_remaining") != 0
        or cleanup.get("networks_remaining") != 0
        or cleanup.get("volumes_remaining") != 0
    ):
        raise EvidenceError("P6 actual Compose runtime or cleanup is incomplete")
    summary: dict[str, Any] = {
        "schema_version": 1,
        "milestone": "P6",
        "status": "development_complete_awaiting_independent_acceptance",
        "evidence_class": "synthetic_offline",
        "fixed_base": BASE_COMMIT,
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "development_branch": BRANCH,
        "implementation_commit": implementation_commit,
        "tree_digest": tree_digest,
        "migration_007_digest": migration_digest,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "verified_gates": sorted(verified_gates),
        "unittest": outcome,
        "results": results,
        "claim_boundary": {
            "synthetic_offline": "evaluated",
            "human_evaluation": "not_evaluated",
            "live_provider_evidence": "not_evaluated",
            "production_security": "not_claimed",
            "enterprise_identity_tenancy": "not_claimed",
            "p7": "not_started",
        },
    }
    _assert_safe(summary, root=root)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".p6-summary-", suffix=".tmp", dir=evidence_path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, evidence_path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return summary
