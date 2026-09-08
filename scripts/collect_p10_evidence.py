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
    IMPLEMENTATION_PATHS,
    MATURITY,
    P10_ALLOWED_PATHS,
    PRODUCT_NAME,
    PYTHON_VERSION,
    REMOTE_STATES,
    SUMMARY_PATH,
    GateError,
    git,
    tree_digest,
)

CLAIM_EXCLUSIONS = [
    "public_release_or_download",
    "remote_registry_signature_or_attestation",
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
    if changed != set(IMPLEMENTATION_PATHS) or implementation in {BASE_COMMIT, ACCEPTANCE_COMMIT}:
        raise GateError("evidence_implementation_commit_invalid")
    if unittest.get("gate_passed") is not True or any(
        unittest.get(key) != 0
        for key in ("failures", "errors", "skipped", "expected_failures", "unexpected_successes")
    ):
        raise GateError("evidence_unittest_incomplete")
    quickstart = results["quickstart"]
    compose_runtime = results["compose_runtime"]
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
    ):
        raise GateError("evidence_quickstart_incomplete")
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
        "tree_digest": tree_digest(root, IMPLEMENTATION_PATHS),
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "product": {
            "name": PRODUCT_NAME,
            "python_version": PYTHON_VERSION,
            "display_version": DISPLAY_VERSION,
            "maturity": MATURITY,
            "api_title": API_TITLE,
        },
        "changed_path_count": len(P10_ALLOWED_PATHS),
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
    destination.parent.mkdir(mode=0o755, parents=True, exist_ok=False)
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
