# SPDX-License-Identifier: Apache-2.0

"""Validate absent pre-evidence state or the exact isolated P10 evidence commit."""

from __future__ import annotations

import re
import statistics
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p10_repository import check_repository
from scripts.p10_gate_support import (
    ACCEPTANCE_COMMIT,
    BASE_COMMIT,
    BRANCH,
    DISPLAY_VERSION,
    IMPLEMENTATION_PATHS,
    MATURITY,
    P10_ALLOWED_PATHS,
    PYTHON_VERSION,
    REMOTE_STATES,
    SUMMARY_PATH,
    UTC_TIMESTAMP,
    GateError,
    emit_main,
    git,
    load_json,
    tree_digest,
)

EVIDENCE_CLASSES = [
    "local_mac_runtime",
    "local_oci",
    "remote_registry",
    "static",
    "synthetic_offline",
]
CLAIM = "p10_mac_quickstart_distribution_candidate"
STATUS = "remote_distribution_candidate_ready_for_independent_acceptance"
LOCAL_REQUIRED_GATES = {
    "retained_p9_toolchain",
    "p10_repository",
    "p10_provenance",
    "p10_distribution",
    "p10_security",
    "p10_operations",
    "p10_i18n",
    "p10_compatibility",
    "p10_reproducibility",
    "p10_compose_runtime",
    "p10_quickstart",
    "p10_evidence",
    "p10_unittest",
    "ruff_lint",
    "ruff_format",
    "mypy_strict",
    "studio_eslint",
    "studio_prettier",
    "studio_typescript",
    "studio_vitest",
    "studio_vite_build",
    "public_boundary",
    "git_diff_check",
}
REQUIRED_GATES = LOCAL_REQUIRED_GATES | {"p10_remote_distribution"}
SUMMARY_KEYS = {
    "schema_version",
    "milestone",
    "status",
    "claim",
    "fixed_base",
    "merge_base",
    "acceptance_commit",
    "development_branch",
    "implementation_commit",
    "published_source_revision",
    "tree_digest",
    "generated_at",
    "product",
    "changed_path_count",
    "historical_drift_count",
    "migrations",
    "capability_boundary",
    "verified_gates",
    "unittest",
    "repository",
    "provenance",
    "distribution",
    "security",
    "operations",
    "i18n",
    "compatibility",
    "reproducibility",
    "compose_runtime",
    "quickstart",
    "remote_distribution",
    "remote_quickstart",
    "evidence",
    "aggregate",
    "evidence_classes",
    "claim_exclusions",
    *REMOTE_STATES,
}


def _safe(value: object, root: Path) -> None:
    if isinstance(value, dict):
        forbidden_keys = {
            "token",
            "cookie",
            "credential",
            "secret",
            "hostname",
            "container_id",
            "username",
            "ip",
        }
        if any(str(key).lower() in forbidden_keys for key in value):
            raise GateError("evidence_private_field")
        for child in value.values():
            _safe(child, root)
    elif isinstance(value, list):
        for child in value:
            _safe(child, root)
    elif isinstance(value, str):
        if (
            str(root) in value
            or str(Path.home()) in value
            or "/.codex/attachments/" in value
            or re.search(r"(?:sk-|bearer |session=)[A-Za-z0-9_=-]{8,}", value, re.I)
        ):
            raise GateError("evidence_private_material")


def validate_summary(root: Path, summary: dict[str, Any]) -> dict[str, object]:
    if set(summary) != SUMMARY_KEYS:
        raise GateError("evidence_shape_invalid")
    repository = check_repository(root)
    implementation = str(git(root, "rev-parse", "HEAD^")).strip()
    if (
        repository["candidate_phase"] != "final_evidence"
        or summary["schema_version"] != 1
        or summary["milestone"] != "P10"
    ):
        raise GateError("evidence_phase_or_identity_invalid")
    expected = {
        "status": STATUS,
        "claim": CLAIM,
        "fixed_base": BASE_COMMIT,
        "merge_base": BASE_COMMIT,
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "development_branch": BRANCH,
        "implementation_commit": implementation,
        "published_source_revision": summary["distribution"]["published_source_revision"],
        "tree_digest": tree_digest(root, IMPLEMENTATION_PATHS),
        "changed_path_count": len(P10_ALLOWED_PATHS),
        "historical_drift_count": 0,
    }
    if any(summary.get(key) != value for key, value in expected.items()):
        raise GateError("evidence_identity_invalid")
    if not isinstance(summary["generated_at"], str) or not UTC_TIMESTAMP.fullmatch(
        summary["generated_at"]
    ):
        raise GateError("evidence_timestamp_invalid")
    if summary["product"] != {
        "name": "Digital Colleagues",
        "python_version": PYTHON_VERSION,
        "display_version": DISPLAY_VERSION,
        "maturity": MATURITY,
        "api_title": "Digital Colleagues Local API",
    }:
        raise GateError("evidence_product_metadata_invalid")
    if set(summary["verified_gates"]) != REQUIRED_GATES:
        raise GateError("evidence_gate_inventory_invalid")
    unittest = summary["unittest"]
    if (
        not isinstance(unittest, dict)
        or unittest.get("tests_run", 0) < 1
        or unittest.get("gate_passed") is not True
        or any(
            unittest.get(key) != 0
            for key in (
                "failures",
                "errors",
                "skipped",
                "expected_failures",
                "unexpected_successes",
            )
        )
    ):
        raise GateError("evidence_unittest_invalid")
    quickstart = summary["quickstart"]
    durations = quickstart.get("durations_seconds") if isinstance(quickstart, dict) else None
    if (
        not isinstance(durations, list)
        or len(durations) != 3
        or any(type(value) not in {int, float} or value <= 0 or value >= 300 for value in durations)
    ):
        raise GateError("evidence_quickstart_invalid")
    if quickstart.get("maximum_seconds") != max(durations) or quickstart.get(
        "median_seconds"
    ) != statistics.median(durations):
        raise GateError("evidence_quickstart_statistics_invalid")
    remote_quickstart = summary["remote_quickstart"]
    remote_durations = (
        remote_quickstart.get("durations_seconds") if isinstance(remote_quickstart, dict) else None
    )
    if (
        not isinstance(remote_durations, list)
        or len(remote_durations) != 3
        or any(
            type(value) not in {int, float} or value <= 0 or value >= 60
            for value in remote_durations
        )
        or remote_quickstart.get("maximum_seconds") != max(remote_durations)
        or remote_quickstart.get("median_seconds") != statistics.median(remote_durations)
        or remote_quickstart.get("all_below_60_seconds") is not True
        or remote_quickstart.get("remote_ghcr_pull_path") != "passed"
        or remote_quickstart.get("docker_residue_check_count") != 6
        or remote_quickstart.get("port_availability_check_count") != 12
    ):
        raise GateError("evidence_remote_quickstart_invalid")
    compose_runtime = summary["compose_runtime"]
    if (
        quickstart.get("external_egress_probe_count") != 3
        or quickstart.get("external_egress_control_count") != 3
        or quickstart.get("internal_network_verified") is not True
        or quickstart.get("unexpected_external_egress_count") != 0
        or not isinstance(compose_runtime, dict)
        or compose_runtime.get("external_egress_probe_count") != 1
        or compose_runtime.get("external_egress_control_count") != 1
        or compose_runtime.get("internal_network_verified") is not True
        or compose_runtime.get("unexpected_external_egress_count") != 0
    ):
        raise GateError("evidence_external_egress_probe_invalid")
    if summary["evidence_classes"] != EVIDENCE_CLASSES or any(
        summary[key] != value for key, value in REMOTE_STATES.items()
    ):
        raise GateError("evidence_remote_boundary_invalid")
    remote_distribution = summary["remote_distribution"]
    if (
        not isinstance(remote_distribution, dict)
        or remote_distribution.get("remote_distribution_gate") != "passed"
        or remote_distribution.get("published_source_revision")
        != summary["published_source_revision"]
        or remote_distribution.get("anonymous_pull") != "passed"
        or remote_distribution.get("public_visibility") != "passed"
    ):
        raise GateError("evidence_remote_distribution_invalid")
    aggregate = summary["aggregate"]
    if (
        not isinstance(aggregate, dict)
        or aggregate.get("status") != "passed"
        or aggregate.get("required_gate_count") != len(REQUIRED_GATES)
        or any(aggregate.get(key) != 0 for key in ("failure_count", "error_count", "skip_count"))
    ):
        raise GateError("evidence_aggregate_invalid")
    if summary["evidence"] != {
        "schema_version": 1,
        "gate": "p10_evidence_clean",
        "evidence_phase": "not_written",
    }:
        raise GateError("evidence_prewrite_gate_invalid")
    if (
        summary["migrations"] != {"count": 7, "migration_008": False, "historical_drift_count": 0}
        or summary["capability_boundary"].get("p11_authorized") is not False
    ):
        raise GateError("evidence_capability_or_migration_invalid")
    _safe(summary, root)
    return {
        "schema_version": 1,
        "gate": "p10_evidence_clean",
        "evidence_phase": "final_evidence",
        "implementation_commit": implementation,
        "trial_count": 3,
        "private_material_count": 0,
        "remote_distribution_gate": "passed",
    }


def check_evidence(root: Path) -> dict[str, object]:
    path = root / SUMMARY_PATH
    if not path.exists():
        repository = check_repository(root)
        if repository["candidate_phase"] != "implementation":
            raise GateError("pre_evidence_phase_invalid")
        return {"schema_version": 1, "gate": "p10_evidence_clean", "evidence_phase": "not_written"}
    if not path.is_file() or path.is_symlink():
        raise GateError("evidence_file_invalid")
    committed = git(root, "show", f"HEAD:{SUMMARY_PATH}", binary=True)
    if path.read_bytes() != committed:
        raise GateError("evidence_worktree_drift")
    return validate_summary(root, load_json(path))


def main(argv: list[str] | None = None) -> int:
    return emit_main(check_evidence, argv, __doc__)


if __name__ == "__main__":
    raise SystemExit(main())
