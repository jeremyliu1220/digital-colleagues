# SPDX-License-Identifier: Apache-2.0

"""Validate all P3 gate results and atomically write a narrowly scoped summary."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from scripts.run_p3_unittest_suite import REQUIRED_TEST_BOUNDARIES

P2_BASE_COMMIT = "37fa1c3d21440130fcbeeaacf0534e445afeb343"
SOURCE_REVISION = "dea9a9accc82fbedd35deb7117dcb5173223cf44"
ARCHITECTURE_POLICY = "p3-dependency-determinism-allowlist-v1"
PARENT_FIELDS = frozenset(
    {
        "schema_version",
        "source_label",
        "source_revision",
        "head_revision",
        "scope",
        "excluded_repo_relative_subtree",
        "status_entry_count",
        "status_digest",
        "tracked_diff_digest",
        "index_diff_digest",
        "untracked_entry_count",
        "untracked_state_digest",
        "ignored_entry_count",
        "ignored_state_digest",
    }
)
REQUIRED_GATES = frozenset(
    {
        "mypy_strict",
        "git_diff_check",
        "p2_core_regression",
        "p3_architecture",
        "p3_golden_path",
        "p3_migrations",
        "p3_parent_fingerprint",
        "p3_persistence",
        "p3_provenance",
        "p3_repository",
        "p3_runtime_contracts",
        "public_boundary",
        "python_lock_install",
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
COUNT_FIELDS = (
    "tests_run",
    "failures",
    "errors",
    "skipped",
    "expected_failures",
    "unexpected_successes",
)


class EvidenceError(RuntimeError):
    """P3 evidence cannot safely represent the supplied mechanical results."""


def _lower_hex(value: object, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def validate_unittest(outcome: dict[str, Any]) -> dict[str, Any]:
    expected = {*COUNT_FIELDS, "gate_passed", "test_ids", "fault_boundaries"}
    if set(outcome) != expected:
        raise EvidenceError("unittest outcome has unexpected fields")
    for field in COUNT_FIELDS:
        if type(outcome[field]) is not int or outcome[field] < 0:
            raise EvidenceError("unittest outcome count is invalid")
    if outcome["tests_run"] < 1 or outcome["gate_passed"] is not True:
        raise EvidenceError("unittest outcome did not pass")
    if any(outcome[field] != 0 for field in COUNT_FIELDS[1:]):
        raise EvidenceError("unittest zero-exception gate failed")
    test_ids = outcome["test_ids"]
    boundaries = outcome["fault_boundaries"]
    if (
        not isinstance(test_ids, list)
        or not all(isinstance(item, str) for item in test_ids)
        or len(test_ids) != len(set(test_ids))
        or not isinstance(boundaries, list)
        or not all(isinstance(item, str) for item in boundaries)
    ):
        raise EvidenceError("unittest execution identity is invalid")
    missing_tests = set(REQUIRED_TEST_BOUNDARIES) - set(test_ids)
    missing_boundaries = set(REQUIRED_TEST_BOUNDARIES.values()) - set(boundaries)
    if missing_tests or missing_boundaries:
        raise EvidenceError("required P3 test IDs or fault boundaries did not execute")
    return outcome


def validate_parent_pair(before: dict[str, Any], after: dict[str, Any]) -> dict[str, object]:
    for value in (before, after):
        if set(value) != PARENT_FIELDS:
            raise EvidenceError("a P3 parent fingerprint has unexpected fields")
        if (
            value.get("schema_version") != 2
            or value.get("source_label") != "digital-colleague-runtime-research"
            or value.get("source_revision") != SOURCE_REVISION
            or value.get("scope") != "parent_source_excluding_authorized_target_subtree"
            or value.get("excluded_repo_relative_subtree") != "digital-colleagues"
        ):
            raise EvidenceError("a P3 parent fingerprint identity changed")
        if not _lower_hex(value.get("head_revision"), 40):
            raise EvidenceError("a P3 parent fingerprint HEAD is invalid")
        for field in (
            "status_entry_count",
            "untracked_entry_count",
            "ignored_entry_count",
        ):
            if type(value.get(field)) is not int or value[field] < 0:
                raise EvidenceError("a P3 fingerprint count is invalid")
        for field in (
            "status_digest",
            "tracked_diff_digest",
            "index_diff_digest",
            "untracked_state_digest",
            "ignored_state_digest",
        ):
            if not _lower_hex(value.get(field), 64):
                raise EvidenceError("a P3 fingerprint digest is invalid")
    if before != after:
        raise EvidenceError("P3 parent before/after fingerprints differ")
    canonical = json.dumps(before, separators=(",", ":"), sort_keys=True).encode("utf-8")
    digest = "sha256:" + hashlib.sha256(canonical).hexdigest()
    return {
        "status": "passed",
        "scope": "adjacent_p3_development_cycle_only",
        "matching_field_count": len(PARENT_FIELDS),
        "before_fingerprint_digest": digest,
        "after_fingerprint_digest": digest,
        "source_revision": SOURCE_REVISION,
    }


def public_tree_digest(project_root: Path, *, excluded: Path) -> str:
    aggregate = hashlib.sha256()
    for document in sorted(project_root.rglob("*")):
        relative = document.relative_to(project_root)
        if relative.parts[:1] == (".git",) or document == excluded or not document.is_file():
            continue
        for value in (
            relative.as_posix().encode("utf-8"),
            hashlib.sha256(document.read_bytes()).digest(),
        ):
            aggregate.update(len(value).to_bytes(8, "big"))
            aggregate.update(value)
    return "sha256:" + aggregate.hexdigest()


def _require_gate(result: dict[str, Any], expected: str) -> None:
    if result.get("gate") != expected:
        raise EvidenceError("a required P3 gate result is not passing")


def write_p3_evidence(
    *,
    evidence_path: Path,
    results: dict[str, dict[str, Any]],
    parent_before: dict[str, Any],
    parent_after: dict[str, Any],
    unittest_outcome: dict[str, Any],
    verified_gates: set[str],
    branch: str,
    implementation_commit: str,
    merge_base: str,
    tree_digest: str,
    remote_count: int,
) -> None:
    if REQUIRED_GATES - verified_gates:
        raise EvidenceError("P3 evidence is missing required mechanical gates")
    outcome = validate_unittest(unittest_outcome)
    parent = validate_parent_pair(parent_before, parent_after)
    expected_results = {
        "repository": "p3_repository_clean",
        "boundary": "public_boundary_clean",
        "provenance": "p3_provenance_clean",
        "architecture": "p3_architecture_clean",
        "migrations": "p3_migrations_clean",
        "persistence": "p3_persistence_clean",
        "runtime_contracts": "p3_runtime_contracts_clean",
        "golden_path": "p3_golden_path_clean",
        "p2_core": "p2_core_contracts_clean",
    }
    for key, gate in expected_results.items():
        if key not in results:
            raise EvidenceError("a required P3 result is missing")
        _require_gate(results[key], gate)
    if results["boundary"].get("exceptions_applied") != 0:
        raise EvidenceError("P3 evidence requires zero public-boundary exceptions")
    if results["architecture"].get("policy_version") != ARCHITECTURE_POLICY:
        raise EvidenceError("P3 architecture policy version drifted")
    for field in (
        "unapproved_imports",
        "dependency_violations",
        "edge_type_leaks",
        "nondeterministic_imports",
        "nondeterministic_calls",
        "alias_resolved_unsafe_calls",
        "stable_port_leaks",
    ):
        if results["architecture"].get(field) != 0:
            raise EvidenceError("P3 architecture contains a violation")
    if (
        results["migrations"].get("journal_mode") != "wal"
        or results["migrations"].get("foreign_keys") is not True
        or results["migrations"].get("migration_count", 0) < 1
    ):
        raise EvidenceError("P3 migration evidence is incomplete")
    if results["provenance"].get("transformed_migration_count") != 0:
        raise EvidenceError("P3 unexpectedly claims transformed source")
    if results["golden_path"].get("golden_test_id") not in REQUIRED_TEST_BOUNDARIES:
        raise EvidenceError("P3 Golden Path test identity drifted")
    if branch != "codex/p3-headless-deterministic-slice":
        raise EvidenceError("P3 evidence requires the authorized branch")
    if merge_base != P2_BASE_COMMIT:
        raise EvidenceError("P3 branch is not derived from the accepted P2 base")
    if not _lower_hex(implementation_commit, 40):
        raise EvidenceError("P3 implementation commit is invalid")
    if (
        not isinstance(tree_digest, str)
        or not tree_digest.startswith("sha256:")
        or len(tree_digest) != 71
    ):
        raise EvidenceError("P3 public-tree digest is invalid")
    if remote_count != 0:
        raise EvidenceError("P3 evidence requires zero Git remotes")
    summary = {
        "schema_version": 1,
        "milestone": "P3",
        "gate": "p3_headless_deterministic_slice",
        "status": "passed",
        "completed_date": date.today().isoformat(),
        "claim_scope": "P3 local synthetic headless deterministic reference semantics only.",
        "p2_base_commit": P2_BASE_COMMIT,
        "source_revision": SOURCE_REVISION,
        "evaluated_tree": {
            "branch": branch,
            "implementation_commit": implementation_commit,
            "merge_base": merge_base,
            "public_tree_digest_excluding_summary": tree_digest,
            "summary_exclusion_rule": "exclude_exact_artifacts/p3/summary.json_path_only",
            "evidence_commit_binding": "the subsequent commit containing these exact summary bytes",
            "remote_count": remote_count,
        },
        "results": {
            **results,
            "parent_worktree": parent,
            "unittest": outcome,
            "python": {
                "lock_install": "passed",
                "ruff_lint": "passed",
                "ruff_format": "passed",
                "mypy_strict": "passed",
            },
            "studio": {
                "lock_install": "passed",
                "eslint": "passed",
                "prettier": "passed",
                "typescript": "passed",
                "vitest": "passed",
                "vite_build": "passed",
                "runtime_workflow": "not_implemented_p4",
            },
        },
        "provenance": {
            "classification": "new_implementation",
            "transformed_migration_count": results["provenance"]["transformed_migration_count"],
            "new_implementation_count": results["provenance"]["new_implementation_count"],
            "receipt_digest": results["provenance"]["receipt_digest"],
            "implementation_tree_digest": results["provenance"]["implementation_tree_digest"],
        },
        "non_mechanical_claims": {
            "historical_parent_stability_before_adjacent_p3_pair": "not_evaluated",
            "parent_worktree_content_used": "not_evaluated",
            "rights_review_beyond_receipt_shape": "not_evaluated",
            "published": "not_evaluated",
            "security_effectiveness": "not_evaluated",
            "privacy_effectiveness": "not_evaluated",
            "live_provider_acceptance": "not_evaluated",
        },
        "not_evidence_for": [
            "P4 authentication, enrollment, sessions, CSRF, Origin, Studio, or Docker Compose",
            "PostgreSQL, distributed execution, high availability, or production tenancy",
            "enterprise IAM, security certification, compliance, or production readiness",
            "real model or provider behavior, delivery, accounts, workspaces, or messages",
            "semantic memory, skill learning, or enterprise world models",
        ],
        "verification_commands": [
            "git diff --check",
            "python3 -B -m unittest discover -s tests -v",
            "python3 -B scripts/check_public_boundary.py .",
            "python3 -B scripts/check_p3_repository.py .",
            "python3 -B scripts/check_p3_provenance.py .",
            "python3 -B scripts/check_p3_architecture.py .",
            "PYTHONPATH=src python3 -B scripts/check_p3_migrations.py .",
            "PYTHONPATH=src python3 -B scripts/check_p3_persistence.py",
            "PYTHONPATH=src python3 -B scripts/check_p3_runtime_contracts.py .",
            "PYTHONPATH=src python3 -B scripts/check_p3_golden_path.py",
            "make check",
            "make evidence-p3",
        ],
    }
    serialized = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=evidence_path.parent,
        prefix=".p3-summary-",
        text=True,
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
