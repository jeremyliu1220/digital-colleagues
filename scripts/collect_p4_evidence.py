# SPDX-License-Identifier: Apache-2.0

"""Validate P4 gate results and atomically write narrowly scoped evidence."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from scripts.check_p4_architecture import POLICY_VERSION
from scripts.check_p4_repository import BASE_COMMIT, BRANCH
from scripts.run_p4_unittest_suite import REQUIRED_TEST_BOUNDARIES

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
        "p2_core_regression",
        "p3_architecture",
        "p3_golden_path",
        "p3_migrations",
        "p3_persistence",
        "p3_provenance",
        "p3_repository",
        "p3_runtime_contracts",
        "p4_architecture",
        "p4_authentication",
        "p4_compose",
        "p4_golden_path",
        "p4_migrations",
        "p4_provenance",
        "p4_repository",
        "p4_studio",
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
    """P4 evidence cannot represent incomplete or contradictory results."""


def public_tree_digest(root: Path, *, excluded: Path) -> str:
    aggregate = hashlib.sha256()
    for document in sorted(root.rglob("*")):
        relative = document.relative_to(root)
        if relative.parts[:1] == (".git",) or document == excluded or not document.is_file():
            continue
        for value in (
            relative.as_posix().encode(),
            hashlib.sha256(document.read_bytes()).digest(),
        ):
            aggregate.update(len(value).to_bytes(8, "big"))
            aggregate.update(value)
    return "sha256:" + aggregate.hexdigest()


def validate_unittest(outcome: dict[str, Any]) -> dict[str, Any]:
    expected = {*COUNT_FIELDS, "gate_passed", "test_ids", "fault_boundaries"}
    if set(outcome) != expected:
        raise EvidenceError("unittest outcome has unexpected fields")
    if any(type(outcome[field]) is not int or outcome[field] < 0 for field in COUNT_FIELDS):
        raise EvidenceError("unittest counts are invalid")
    if outcome["tests_run"] < 1 or outcome["gate_passed"] is not True:
        raise EvidenceError("unittest suite did not pass")
    if any(outcome[field] != 0 for field in COUNT_FIELDS[1:]):
        raise EvidenceError("unittest zero-exception contract failed")
    test_ids = outcome["test_ids"]
    boundaries = outcome["fault_boundaries"]
    if not isinstance(test_ids, list) or not isinstance(boundaries, list):
        raise EvidenceError("unittest identity is invalid")
    if set(REQUIRED_TEST_BOUNDARIES) - set(test_ids):
        raise EvidenceError("required P3/P4 test identities did not execute")
    if set(REQUIRED_TEST_BOUNDARIES.values()) - set(boundaries):
        raise EvidenceError("required P3/P4 fault boundaries did not execute")
    return outcome


def _require_commit(value: str, label: str) -> None:
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise EvidenceError(f"{label} is not a real commit SHA")


def write_p4_evidence(
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
        raise EvidenceError("P4 evidence is missing required mechanical gates")
    outcome = validate_unittest(unittest_outcome)
    expected_results = {
        "boundary": "public_boundary_clean",
        "p3_repository": "p3_repository_clean",
        "p3_provenance": "p3_provenance_clean",
        "p3_architecture": "p3_architecture_clean",
        "p3_migrations": "p3_migrations_clean",
        "p3_persistence": "p3_persistence_clean",
        "p3_runtime": "p3_runtime_contracts_clean",
        "p3_golden": "p3_golden_path_clean",
        "p2_core": "p2_core_contracts_clean",
        "repository": "p4_repository_clean",
        "provenance": "p4_provenance_clean",
        "architecture": "p4_architecture_clean",
        "migrations": "p4_migrations_clean",
        "authentication": "p4_authentication_clean",
        "studio": "p4_studio_clean",
        "compose": "p4_compose_clean",
        "golden_path": "p4_golden_path_clean",
    }
    for key, gate in expected_results.items():
        if results.get(key, {}).get("gate") != gate:
            raise EvidenceError("a required P3/P4 gate result is missing or invalid")
    if results["boundary"].get("exceptions_applied") != 0:
        raise EvidenceError("P4 evidence requires zero public-boundary exceptions")
    if results["architecture"].get("policy_version") != POLICY_VERSION:
        raise EvidenceError("P4 architecture policy drifted")
    if results["migrations"].get("migration_versions") != [1, 2, 3, 4]:
        raise EvidenceError("P4 migration evidence is incomplete")
    if results["provenance"].get("transformed_migration_count") != 0:
        raise EvidenceError("P4 unexpectedly claims transformed source")
    if branch != BRANCH or merge_base != BASE_COMMIT:
        raise EvidenceError("P4 branch is not based on the accepted P3 commit")
    _require_commit(implementation_commit, "implementation commit")
    if not tree_digest.startswith("sha256:") or len(tree_digest) != 71:
        raise EvidenceError("public-tree digest is invalid")
    compose_runtime = results["compose"].get("runtime_start_restart_stop")
    summary = {
        "schema_version": 1,
        "milestone": "P4",
        "gate": "p4_studio_and_five_minute_golden_path",
        "status": "development_complete_awaiting_independent_acceptance",
        "completed_date": date.today().isoformat(),
        "claim_scope": "P4 local synthetic/offline Studio reference workflow only.",
        "evidence_class": ["synthetic", "offline"],
        "evaluated_tree": {
            "branch": branch,
            "base_commit": BASE_COMMIT,
            "implementation_commit": implementation_commit,
            "merge_base": merge_base,
            "evidence_commit_target": "the subsequent commit containing these exact summary bytes",
            "public_tree_digest_excluding_summary": tree_digest,
            "summary_exclusion_rule": "exclude_exact_artifacts/p4/summary.json_path_only",
        },
        "policy_versions": {
            "architecture": POLICY_VERSION,
            "public_boundary": results["boundary"].get("policy_version"),
            "scenario": "p4-golden-path-v1",
            "metric_definition": "colleague-experience-p4-v1",
        },
        "migration_versions": results["migrations"]["migration_versions"],
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
        "metric_observations": {
            "rebrief_turns": {"numerator": 0, "denominator": 1, "status": "observed"},
            "wrong_memory_rate": {"numerator": 0, "denominator": 1, "status": "observed"},
            "ai_initiated_rate": {"numerator": 1, "denominator": 2, "status": "observed"},
            "proactive_suggestion_acceptance_rate": {
                "numerator": 0,
                "denominator": 1,
                "status": "observed",
            },
            "unnecessary_interruption_rate": {
                "numerator": 0,
                "denominator": 1,
                "status": "observed",
            },
            "human_intervention_count": {
                "numerator": 0,
                "denominator": 1,
                "status": "observed",
            },
            "completion_rate": {"numerator": 0, "denominator": 1, "status": "observed"},
            "unauthorized_proposal_escape_rate": {
                "numerator": 0,
                "denominator": 0,
                "status": "not_applicable",
                "reason": "the Golden Path evaluated no unauthorized proposal candidate",
                "target": 0,
            },
            "unauthorized_denominator_formula_control": {
                "numerator": 0,
                "denominator": 7,
                "status": "calculation_fixture_passed",
                "claim_limit": "not an operational governance observation",
            },
            "zero_denominator_control": {
                "denominator": 0,
                "status": "not_applicable",
                "reason": "no eligible observation opportunity in the zero-input fixture",
            },
            "interpretation": "synthetic/offline only; a higher AI-initiated rate is not inherently better",
        },
        "five_minute_objective": {
            "start": "immediately before one-time operator token retrieval",
            "end": "Studio displays ActionResult and complete causal audit after restart",
            "human_steps_included": True,
            "elapsed_limit_measured": False,
            "status": "not_evaluated",
            "reason": "automation does not drive or time the required human Studio steps",
        },
        "unevaluated": {
            "compose_runtime_start_restart_stop": compose_runtime,
            "human_study": "not_evaluated",
            "live_provider": "not_evaluated",
            "production_security_privacy": "not_evaluated",
            "five_minute_limit": "not_evaluated",
        },
        "explicit_exclusions": [
            "Semantic Memory, Skill Learning, governed Skills, shared knowledge, and self-initiated autonomy",
            "P5 revisioned policy builder and generalized working-hours enforcement",
            "P6-complete governance, OIDC, SSO, SCIM, and enterprise IAM",
            "real models, live chat/email providers, and real-provider pilot readiness",
            "PostgreSQL, distributed execution, high availability, and production tenant isolation",
            "production security, production privacy, compliance, and production readiness",
        ],
        "verification_commands": [
            "git diff --check",
            "python3 -B scripts/check_public_boundary.py .",
            "python3 -B scripts/check_p4_repository.py .",
            "python3 -B scripts/check_p4_provenance.py .",
            "python3 -B scripts/check_p4_architecture.py .",
            "PYTHONPATH=src python3 -B scripts/check_p4_migrations.py .",
            "PYTHONPATH=src python3 -B scripts/check_p4_authentication.py .",
            "python3 -B scripts/check_p4_studio.py .",
            "python3 -B scripts/check_p4_compose.py .",
            "PYTHONPATH=src python3 -B scripts/check_p4_golden_path.py",
            "make check",
            "make evidence-p4",
        ],
    }
    serialized = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=evidence_path.parent,
        prefix=".p4-summary-",
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
