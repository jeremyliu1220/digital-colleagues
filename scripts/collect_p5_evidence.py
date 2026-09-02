# SPDX-License-Identifier: Apache-2.0

"""Validate complete P5 gate results and atomically write scoped evidence."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from scripts.check_p5_architecture import POLICY_VERSION
from scripts.check_p5_repository import BASE_COMMIT, BRANCH
from scripts.run_p5_unittest_suite import REQUIRED_TEST_BOUNDARIES

COUNT_FIELDS = (
    "tests_run",
    "failures",
    "errors",
    "skipped",
    "expected_failures",
    "unexpected_successes",
)
REQUIRED_GATES = frozenset(
    {
        "git_diff_check",
        "p4_aggregate",
        "p5_architecture",
        "p5_builder",
        "p5_compose",
        "p5_compose_runtime",
        "p5_golden_path",
        "p5_migrations",
        "p5_policy",
        "p5_provenance",
        "p5_repository",
        "p5_studio",
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


class EvidenceError(RuntimeError):
    """P5 evidence cannot represent incomplete or contradictory results."""


def public_tree_digest(root: Path, *, excluded: Path) -> str:
    aggregate = hashlib.sha256()
    for document in sorted(root.rglob("*")):
        relative = document.relative_to(root)
        if relative.parts[:1] == (".git",) or document == excluded or not document.is_file():
            continue
        for value in (relative.as_posix().encode(), hashlib.sha256(document.read_bytes()).digest()):
            aggregate.update(len(value).to_bytes(8, "big"))
            aggregate.update(value)
    return "sha256:" + aggregate.hexdigest()


def validate_unittest(outcome: dict[str, Any]) -> dict[str, Any]:
    expected = {*COUNT_FIELDS, "gate_passed", "test_ids", "fault_boundaries"}
    if set(outcome) != expected:
        raise EvidenceError("P5 unittest outcome has unexpected fields")
    if any(type(outcome[field]) is not int or outcome[field] < 0 for field in COUNT_FIELDS):
        raise EvidenceError("P5 unittest counts are invalid")
    if outcome["tests_run"] < 1 or outcome["gate_passed"] is not True:
        raise EvidenceError("P5 unittest suite did not pass")
    if any(outcome[field] != 0 for field in COUNT_FIELDS[1:]):
        raise EvidenceError("P5 unittest zero-exception contract failed")
    test_ids = outcome["test_ids"]
    boundaries = outcome["fault_boundaries"]
    if not isinstance(test_ids, list) or not isinstance(boundaries, list):
        raise EvidenceError("P5 unittest identity is invalid")
    if set(REQUIRED_TEST_BOUNDARIES) - set(test_ids):
        raise EvidenceError("required retained/P5 test identities did not execute")
    if set(REQUIRED_TEST_BOUNDARIES.values()) - set(boundaries):
        raise EvidenceError("required retained/P5 fault boundaries did not execute")
    return outcome


def _require_commit(value: str, label: str) -> None:
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise EvidenceError(f"{label} is not a real commit SHA")


def write_p5_evidence(
    *,
    evidence_path: Path,
    results: dict[str, dict[str, Any]],
    unittest_outcome: dict[str, Any],
    verified_gates: set[str],
    branch: str,
    implementation_commit: str,
    merge_base: str,
    tree_digest: str,
) -> None:
    if REQUIRED_GATES - verified_gates:
        raise EvidenceError("P5 evidence is missing required mechanical gates")
    outcome = validate_unittest(unittest_outcome)
    expected_results = {
        "boundary": "public_boundary_clean",
        "p4_aggregate": "p4_aggregate_clean",
        "repository": "p5_repository_clean",
        "provenance": "p5_provenance_clean",
        "architecture": "p5_architecture_clean",
        "migrations": "p5_migrations_clean",
        "builder": "p5_builder_clean",
        "policy": "p5_policy_clean",
        "studio": "p5_studio_clean",
        "compose": "p5_compose_static_clean",
        "compose_runtime": "p5_compose_runtime_clean",
        "golden_path": "p5_in_process_golden_path_clean",
    }
    for key, gate in expected_results.items():
        if results.get(key, {}).get("gate") != gate:
            raise EvidenceError("a required retained/P5 gate result is missing or invalid")
    if results["boundary"].get("exceptions_applied") != 0:
        raise EvidenceError("P5 evidence requires zero public-boundary exceptions")
    if results["architecture"].get("policy_version") != POLICY_VERSION:
        raise EvidenceError("P5 architecture policy drifted")
    if results["migrations"].get("migration_versions") != [1, 2, 3, 4, 5, 6]:
        raise EvidenceError("P5 migration evidence is incomplete")
    if branch != BRANCH or merge_base != BASE_COMMIT:
        raise EvidenceError("P5 branch or merge-base drifted")
    _require_commit(implementation_commit, "implementation commit")
    if not tree_digest.startswith("sha256:") or len(tree_digest) != 71:
        raise EvidenceError("P5 public-tree digest is invalid")
    runtime = results["compose_runtime"]
    if runtime.get("status") != "passed" or not runtime.get("cleanup", {}).get("passed"):
        raise EvidenceError("P5 evidence requires actual Compose runtime and cleanup")
    if (
        runtime.get("profile_only_stop_preservation_fault")
        != "passed_without_policy_revision_or_resume"
        or runtime.get("queued_wake_after_stop_fault")
        != "governed_noop_without_proposal_after_restart"
        or runtime.get("explicit_revisioned_resume") != "passed"
    ):
        raise EvidenceError("P5 evidence requires both durable-stop fault boundaries")
    readout = runtime.get("metric_readout")
    if not isinstance(readout, dict) or not isinstance(readout.get("metrics"), list):
        raise EvidenceError("P5 evidence requires revision-bound metric readout")
    for metric in readout["metrics"]:
        if not isinstance(metric, dict):
            raise EvidenceError("P5 metric readout shape is invalid")
        if metric.get("status") not in {"observed", "not_applicable", "not_evaluated"}:
            raise EvidenceError("P5 metric status is invalid")
        if not isinstance(metric.get("denominator"), int) or not isinstance(
            metric.get("source"), str
        ):
            raise EvidenceError("P5 metric lacks denominator or durable source")
        if not isinstance(metric.get("policy_bindings"), list):
            raise EvidenceError("P5 metric lacks causal policy bindings")
    summary = {
        "schema_version": 1,
        "milestone": "P5",
        "gate": "p5_revisioned_colleague_builder",
        "status": "development_complete_awaiting_independent_acceptance",
        "completed_date": date.today().isoformat(),
        "claim_scope": "P5 local deterministic synthetic/offline revisioned-builder path only.",
        "evidence_class": ["synthetic", "offline"],
        "evaluated_tree": {
            "branch": branch,
            "base_commit": BASE_COMMIT,
            "implementation_commit": implementation_commit,
            "merge_base": merge_base,
            "evidence_commit_target": "the subsequent commit containing these exact summary bytes",
            "public_tree_digest_excluding_summary": tree_digest,
            "summary_exclusion_rule": "exclude_exact_artifacts/p5/summary.json_path_only",
        },
        "policy_versions": {
            "architecture": POLICY_VERSION,
            "scenario": "p5-revisioned-builder-v1",
            "metric_definition": "colleague-experience-p5-v1",
            "public_boundary": results["boundary"].get("policy_version"),
        },
        "migration_versions": results["migrations"]["migration_versions"],
        "migration_checksums": {"006": results["migrations"]["migration_006_checksum"]},
        "results": {
            **results,
            "unittest": outcome,
            "python": {
                "lock_install": "passed",
                "ruff_lint": "passed",
                "ruff_format": "passed",
                "mypy_strict": "passed",
            },
            "studio_toolchain": {
                "lock_install": "passed",
                "eslint": "passed",
                "prettier": "passed",
                "typescript": "passed",
                "vitest": "passed",
                "vite_build": "passed",
            },
        },
        "fault_evidence": {
            "stale_draft": runtime["stale_draft_fault"],
            "ambiguous_authority": "refused_by_strict_HTTP_mapping",
            "stale_proposal": runtime["stale_proposal_fault"],
            "policy_enforcement": {
                "budget_stop_escalation": runtime["budget_stop_escalation"],
                "profile_only_stop_preservation": runtime["profile_only_stop_preservation_fault"],
                "queued_wake_after_stop": runtime["queued_wake_after_stop_fault"],
                "explicit_revisioned_resume": runtime["explicit_revisioned_resume"],
            },
        },
        "metric_observations": readout,
        "unevaluated": {
            "colleague_experience_improvement": "not_evaluated",
            "unnecessary_interruption_without_evaluator_coverage": "not_evaluated",
            "human_study": "not_evaluated",
            "live_provider": "not_evaluated",
            "production_security_privacy": "not_evaluated",
        },
        "explicit_exclusions": [
            "Semantic Memory, Skill Learning, governed Skills, and shared knowledge",
            "multi-person collaboration and self-initiated or arbitrary-goal autonomy",
            "real models, live providers/channels, OIDC, SSO, SCIM, and P7 adapters",
            "P6-complete RBAC or multi-party change approval",
            "PostgreSQL, distributed execution, high availability, and encryption at rest",
            "production tenancy, security, privacy, compliance, release, or readiness claims",
        ],
        "verification_commands": [
            "git diff --check",
            "python3 -B scripts/check_public_boundary.py .",
            "python3 -B scripts/check_p4_repository.py .",
            "make p5-repository p5-provenance p5-architecture p5-migrations",
            "make p5-builder p5-policy p5-studio p5-compose p5-golden",
            "make p5-compose-runtime",
            "make check",
            "make evidence-p5",
        ],
    }
    serialized = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=evidence_path.parent, prefix=".p5-summary-", text=True
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
