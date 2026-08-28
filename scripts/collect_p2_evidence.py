# SPDX-License-Identifier: Apache-2.0

"""Validate complete P2 gate results and atomically write sanitized evidence."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

P1_BASELINE_COMMIT = "bd6953b3dceeebd33a53f52b03ce94534ff5624b"
SOURCE_REVISION = "dea9a9accc82fbedd35deb7117dcb5173223cf44"
REQUIRED_EVIDENCE_GATES = frozenset(
    {
        "mypy_strict",
        "p2_architecture",
        "p2_core_contracts",
        "p2_provenance",
        "p2_repository",
        "public_boundary",
        "python_tools",
        "python_unittest",
        "ruff_format",
        "ruff_lint",
        "studio_eslint",
        "studio_lock_install",
        "studio_prettier",
        "studio_typescript",
        "studio_vite_build",
        "studio_vitest",
    }
)
UNITTEST_INTEGER_FIELDS = (
    "tests_run",
    "failures",
    "errors",
    "skipped",
    "expected_failures",
    "unexpected_successes",
)


class EvidenceError(RuntimeError):
    """P2 evidence cannot safely represent the supplied mechanical results."""


def validate_unittest_outcome(outcome: dict[str, Any]) -> dict[str, int | bool]:
    expected_fields = {*UNITTEST_INTEGER_FIELDS, "gate_passed"}
    if set(outcome) != expected_fields:
        raise EvidenceError("the unittest outcome has unexpected fields")
    for field in UNITTEST_INTEGER_FIELDS:
        if type(outcome[field]) is not int or outcome[field] < 0:
            raise EvidenceError("the unittest outcome has an invalid count")
    if outcome["tests_run"] == 0:
        raise EvidenceError("the unittest suite ran zero tests")
    if outcome["gate_passed"] is not True or any(
        outcome[field] != 0 for field in UNITTEST_INTEGER_FIELDS[1:]
    ):
        raise EvidenceError("the unittest outcome does not satisfy the zero-exception gate")
    return {field: outcome[field] for field in (*UNITTEST_INTEGER_FIELDS, "gate_passed")}


def _require_gate(result: dict[str, Any], expected: str, label: str) -> None:
    if result.get("gate") != expected:
        raise EvidenceError(f"the {label} result is not passing")


def write_p2_evidence(
    *,
    evidence_path: Path,
    boundary: dict[str, Any],
    repository: dict[str, Any],
    provenance: dict[str, Any],
    architecture: dict[str, Any],
    core_contracts: dict[str, Any],
    unittest_outcome: dict[str, Any],
    verified_gates: set[str],
    evaluated_branch: str,
    evaluated_head: str,
    merge_base: str,
    public_tree_digest: str,
    remote_count: int,
) -> None:
    missing = REQUIRED_EVIDENCE_GATES - verified_gates
    if missing:
        raise EvidenceError("P2 evidence is missing required mechanical gates")
    outcome = validate_unittest_outcome(unittest_outcome)
    _require_gate(boundary, "public_boundary_clean", "public-boundary")
    _require_gate(repository, "p2_repository_clean", "repository")
    _require_gate(provenance, "p2_provenance_clean", "provenance")
    _require_gate(architecture, "p2_architecture_clean", "architecture")
    _require_gate(core_contracts, "p2_core_contracts_clean", "core-contract")
    if boundary.get("exceptions_applied") != 0:
        raise EvidenceError("P2 evidence requires zero public-boundary exceptions")
    if repository.get("runtime_dependency_count") != 0:
        raise EvidenceError("P2 evidence requires zero Python runtime dependencies")
    if provenance.get("source_revision") != SOURCE_REVISION:
        raise EvidenceError("P2 provenance uses the wrong source revision")
    for field in (
        "forbidden_imports",
        "forbidden_io_imports",
        "dependency_violations",
        "nondeterministic_calls",
    ):
        if architecture.get(field) != 0:
            raise EvidenceError("P2 architecture result contains a violation")
    for field in (
        "immutability",
        "namespace",
        "principal_separation",
        "authority_approval",
        "complete_effect_binding",
        "constraint_enforcement",
        "direct_construction_invariants",
        "human_approval_requirement",
        "serialization",
    ):
        if core_contracts.get(field) != "passed":
            raise EvidenceError("P2 core-contract result is incomplete")
    if core_contracts.get("effect_payload_redacted") is not True:
        raise EvidenceError("P2 public effect serialization was not proven redacted")
    if core_contracts.get("complete_effect_digest_exposed") is not True:
        raise EvidenceError("P2 complete effect digest was not proven serializable")
    for field in (
        "public_dataclass_count",
        "mutable_input_probe_count",
        "authoritative_effect_field_mutations_checked",
        "constraint_negative_cases_checked",
    ):
        if type(core_contracts.get(field)) is not int or core_contracts[field] < 1:
            raise EvidenceError("P2 core-contract mechanical counts are incomplete")
    if not evaluated_branch.startswith("codex/"):
        raise EvidenceError("P2 evidence requires a codex task branch")
    if merge_base != P1_BASELINE_COMMIT:
        raise EvidenceError("P2 branch is not derived from the accepted P1 baseline")
    if not isinstance(evaluated_head, str) or len(evaluated_head) != 40:
        raise EvidenceError("evaluated HEAD is invalid")
    if not public_tree_digest.startswith("sha256:") or len(public_tree_digest) != 71:
        raise EvidenceError("evaluated public tree digest is invalid")
    if remote_count != 0:
        raise EvidenceError("P2 evidence requires no configured Git remotes")

    summary = {
        "schema_version": 2,
        "milestone": "P2",
        "gate": "p2_core_primitives",
        "status": "passed",
        "completed_date": date.today().isoformat(),
        "claim_scope": "P2 framework-independent core primitives only.",
        "p1_baseline_commit": P1_BASELINE_COMMIT,
        "source_revision": SOURCE_REVISION,
        "evaluated_tree": {
            "branch": evaluated_branch,
            "head_commit_before_evidence": evaluated_head,
            "merge_base": merge_base,
            "public_tree_digest_excluding_summary": public_tree_digest,
            "remote_count": remote_count,
        },
        "migration": {
            "transformed_migration_count": provenance["transformed_migration_count"],
            "new_implementation_count": provenance["new_implementation_count"],
            "receipt_digest": provenance["receipt_digest"],
            "new_implementation_digest": provenance["new_implementation_digest"],
        },
        "results": {
            "public_boundary": {
                "status": "passed",
                "files_scanned": boundary["files_scanned"],
                "findings": 0,
                "exceptions_applied": boundary["exceptions_applied"],
                "policy_version": boundary["policy_version"],
            },
            "architecture": architecture,
            "core_contracts": core_contracts,
            "immutability": {"status": core_contracts["immutability"]},
            "namespace": {"status": core_contracts["namespace"]},
            "principal_separation": {"status": core_contracts["principal_separation"]},
            "authority_approval": {"status": core_contracts["authority_approval"]},
            "complete_effect_binding": {
                "status": core_contracts["complete_effect_binding"],
                "authoritative_field_mutations_checked": core_contracts[
                    "authoritative_effect_field_mutations_checked"
                ],
                "digest_exposed_without_payload": core_contracts["complete_effect_digest_exposed"],
            },
            "constraint_enforcement": {
                "status": core_contracts["constraint_enforcement"],
                "negative_cases_checked": core_contracts["constraint_negative_cases_checked"],
                "human_approval_requirement": core_contracts["human_approval_requirement"],
            },
            "direct_construction_invariants": {
                "status": core_contracts["direct_construction_invariants"],
                "public_dataclass_count": core_contracts["public_dataclass_count"],
                "mutable_input_probe_count": core_contracts["mutable_input_probe_count"],
            },
            "serialization": {"status": core_contracts["serialization"]},
            "repository": repository,
            "python": {
                "ruff_lint": "passed",
                "ruff_format": "passed",
                "mypy_strict": "passed",
                "runtime_dependency_count": repository["runtime_dependency_count"],
                "requires_python": repository["requires_python"],
            },
            "studio": {
                "npm_lock_install": "passed",
                "eslint": "passed",
                "prettier": "passed",
                "typescript": "passed",
                "vitest": "passed",
                "vite_build": "passed",
                "runtime_orchestration": "not_implemented_p3",
            },
            "unittest": outcome,
        },
        "non_mechanical_claims": {
            "parent_worktree_content_used": "not_evaluated",
            "parent_worktree_unchanged": "not_evaluated",
            "personal_data_used": "not_evaluated",
            "published": "not_evaluated",
            "rights_review_beyond_receipt_shape": "not_evaluated",
        },
        "not_evidence_for": [
            "P3 application orchestration",
            "database persistence or restart recovery",
            "authentication implementation",
            "effect execution",
            "a runnable product Golden Path",
            "security effectiveness",
            "privacy effectiveness",
            "production readiness",
            "live provider acceptance",
        ],
        "verification_commands": [
            "make check",
            "make evidence-p2",
            "python3 -B -m unittest discover -s tests -v",
            "python3 -B scripts/check_public_boundary.py .",
            "python3 -B scripts/check_p2_architecture.py .",
            "PYTHONPATH=src python3 -B scripts/check_p2_core_contracts.py .",
        ],
    }
    serialized = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=evidence_path.parent, prefix=".p2-summary-", text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(serialized)
        os.replace(temporary_name, evidence_path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def public_tree_digest(project_root: Path, *, excluded: Path) -> str:
    """Hash public path/content pairs without persisting a local path."""

    aggregate = hashlib.sha256()
    for document in sorted(project_root.rglob("*")):
        relative = document.relative_to(project_root)
        if relative.parts[:1] == (".git",) or document == excluded or not document.is_file():
            continue
        path_bytes = relative.as_posix().encode("utf-8")
        content_digest = hashlib.sha256(document.read_bytes()).digest()
        for value in (path_bytes, content_digest):
            aggregate.update(len(value).to_bytes(8, "big"))
            aggregate.update(value)
    return "sha256:" + aggregate.hexdigest()
