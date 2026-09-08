# SPDX-License-Identifier: Apache-2.0

"""Build and atomically write the single safe P10 evidence summary."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.check_p10_evidence import (
    CLAIM,
    EVIDENCE_CLASSES,
    REQUIRED_GATES,
    STATUS,
)
from scripts.p10_gate_support import (
    ACCEPTANCE_COMMIT,
    API_TITLE,
    BASE_COMMIT,
    BRANCH,
    DISPLAY_VERSION,
    MATURITY,
    PRODUCT_NAME,
    PYTHON_VERSION,
    REMOTE_STATES,
    SUMMARY_PATH,
    GateError,
    acceptance_allowed_paths,
    git,
    tree_digest,
)

CLAIM_EXCLUSIONS = [
    "formal_release",
    "openai_or_microsoft_365_live_compatibility",
    "first_agent_timing",
    "human_acceptance",
    "always_on_operation",
    "production_security_privacy_or_readiness",
    "high_availability",
    "enterprise_iam_or_tenancy",
    "compliance_certification",
    "p11_through_p15_capabilities",
]


def build_summary(
    root: Path,
    results: dict[str, dict[str, Any]],
    unittest: dict[str, Any],
    verified_gates: set[str],
) -> dict[str, Any]:
    allowed_paths = acceptance_allowed_paths(root)
    implementation_paths = allowed_paths - {SUMMARY_PATH}
    if (
        str(git(root, "status", "--porcelain=v1")).strip()
        or str(git(root, "branch", "--show-current")).strip() != BRANCH
    ):
        raise GateError("evidence_requires_clean_implementation_branch")
    if (root / SUMMARY_PATH).exists() or set(verified_gates) != REQUIRED_GATES:
        raise GateError("evidence_preconditions_incomplete")
    implementation = str(git(root, "rev-parse", "HEAD")).strip()
    changed = {
        line
        for line in str(git(root, "diff", "--name-only", BASE_COMMIT, "HEAD", "--")).splitlines()
        if line
    }
    if changed != set(implementation_paths) or implementation in {BASE_COMMIT, ACCEPTANCE_COMMIT}:
        raise GateError("evidence_implementation_commit_invalid")
    if unittest.get("gate_passed") is not True or any(
        unittest.get(key) != 0
        for key in ("failures", "errors", "skipped", "expected_failures", "unexpected_successes")
    ):
        raise GateError("evidence_unittest_incomplete")
    quickstart = results["quickstart"]
    compose_runtime = results["compose_runtime"]
    remote_distribution = results["remote_distribution"]
    remote_quickstart = results["remote_quickstart"]
    if (
        quickstart.get("trial_count") != 3
        or quickstart.get("all_below_300_seconds") is not True
        or quickstart.get("external_egress_probe_count") != 3
        or quickstart.get("external_egress_control_count") != 3
        or quickstart.get("internal_network_verified") is not True
        or quickstart.get("unexpected_external_egress_count") != 0
        or compose_runtime.get("external_egress_probe_count") != 1
        or compose_runtime.get("external_egress_control_count") != 1
        or compose_runtime.get("internal_network_verified") is not True
        or compose_runtime.get("unexpected_external_egress_count") != 0
        or remote_distribution.get("remote_distribution_gate") != "passed"
        or remote_distribution.get("anonymous_pull") != "passed"
        or remote_distribution.get("public_visibility") != "passed"
        or remote_quickstart.get("trial_count") != 3
        or remote_quickstart.get("all_below_60_seconds") is not True
        or remote_quickstart.get("remote_ghcr_pull_path") != "passed"
        or remote_quickstart.get("docker_residue_check_count") != 6
        or remote_quickstart.get("port_availability_check_count") != 12
    ):
        raise GateError("evidence_quickstart_incomplete")
    published_source_revision = remote_distribution.get("published_source_revision")
    if not isinstance(published_source_revision, str):
        raise GateError("evidence_published_source_revision_missing")
    summary: dict[str, Any] = {
        "schema_version": 1,
        "milestone": "P10",
        "status": STATUS,
        "claim": CLAIM,
        "fixed_base": BASE_COMMIT,
        "merge_base": BASE_COMMIT,
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "development_branch": BRANCH,
        "implementation_commit": implementation,
        "published_source_revision": published_source_revision,
        "tree_digest": tree_digest(root, implementation_paths),
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "product": {
            "name": PRODUCT_NAME,
            "python_version": PYTHON_VERSION,
            "display_version": DISPLAY_VERSION,
            "maturity": MATURITY,
            "api_title": API_TITLE,
        },
        "changed_path_count": len(allowed_paths),
        "historical_drift_count": 0,
        "migrations": {"count": 7, "migration_008": False, "historical_drift_count": 0},
        "capability_boundary": {
            "p10_scope": "mac_quickstart_and_distribution",
            "p11_authorized": False,
            "forbidden_capability_count": 0,
        },
        "verified_gates": sorted(verified_gates),
        "unittest": unittest,
        "repository": results["repository"],
        "provenance": results["provenance"],
        "distribution": results["distribution"],
        "security": results["security"],
        "operations": results["operations"],
        "i18n": results["i18n"],
        "compatibility": results["compatibility"],
        "reproducibility": results["reproducibility"],
        "compose_runtime": results["compose_runtime"],
        "quickstart": quickstart,
        "remote_distribution": remote_distribution,
        "remote_quickstart": remote_quickstart,
        "evidence": results["evidence"],
        "aggregate": {
            "gate": "p10_aggregate_clean",
            "status": "passed",
            "required_gate_count": len(verified_gates),
            "failure_count": 0,
            "error_count": 0,
            "skip_count": 0,
        },
        "evidence_classes": EVIDENCE_CLASSES,
        "claim_exclusions": CLAIM_EXCLUSIONS,
        **REMOTE_STATES,
    }
    return summary


def write_evidence(root: Path, summary: dict[str, Any]) -> None:
    destination = root / SUMMARY_PATH
    try:
        destination.parent.mkdir(mode=0o755, parents=True, exist_ok=False)
    except FileExistsError:
        if destination.parent.is_symlink() or not destination.parent.is_dir():
            raise GateError("evidence_directory_invalid") from None
    if destination.exists() or destination.is_symlink():
        raise GateError("evidence_already_exists")
    content = (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode()
    descriptor, temporary_name = tempfile.mkstemp(prefix=".summary-", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o644)
        os.replace(temporary_name, destination)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
