# SPDX-License-Identifier: Apache-2.0

"""Run P11 gates and atomically create the sole final evidence summary."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.p11_gate_support import (  # noqa: E402
    ACCEPTANCE_COMMIT,
    BASE_COMMIT,
    BRANCH,
    CLAIM,
    EVIDENCE_CLASSES,
    STATUS,
    SUMMARY_PATH,
    GateError,
    acceptance_paths,
    git,
    public_tree_digest,
    read_json,
)
from scripts.run_p11_toolchain import ROOT, run_all  # noqa: E402

EXCLUSIONS = (
    "OpenAI live compatibility",
    "Microsoft 365 live compatibility",
    "named-provider compatibility",
    "human evaluation",
    "always-on behavior",
    "production security or privacy",
    "production readiness",
    "high availability",
    "enterprise IAM",
    "compliance",
    "Agent collaboration or delegation",
    "Semantic Memory",
    "executable Skill runtime",
    "formal release or public pilot",
    "P12",
)


def _preconditions(root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if git(root, "branch", "--show-current") != BRANCH:
        raise GateError("evidence branch identity is invalid")
    if git(root, "status", "--porcelain"):
        raise GateError("evidence requires a clean committed implementation")
    if (root / SUMMARY_PATH).exists():
        raise GateError("P11 summary already exists")
    paths = acceptance_paths(root)
    changed = tuple(sorted(git(root, "diff", "--name-only", BASE_COMMIT, "HEAD").splitlines()))
    if set(changed) != set(paths) - {SUMMARY_PATH}:
        raise GateError("implementation commit path set is incomplete")
    commits = tuple(git(root, "rev-list", "--reverse", f"{ACCEPTANCE_COMMIT}..HEAD").splitlines())
    if not commits:
        raise GateError("implementation commits are absent")
    return paths, commits


def build_summary(
    root: Path,
    results: dict[str, Any],
    *,
    paths: tuple[str, ...],
    implementation_commits: tuple[str, ...],
) -> dict[str, object]:
    manifest = read_json(root / "migrations/manifest.json")
    tests = results["quality"]
    return {
        "schema_version": 1,
        "milestone": "P11",
        "claim": CLAIM,
        "status": STATUS,
        "branch": BRANCH,
        "base_commit": BASE_COMMIT,
        "merge_base": git(root, "merge-base", "HEAD", BASE_COMMIT),
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "implementation_commits": list(implementation_commits),
        "implementation_tree_digest": public_tree_digest(root, paths),
        "changed_paths": list(paths),
        "changed_path_count": len(paths),
        "migration": {
            "version": 8,
            "identity": manifest["migrations"][7],
            "retained_prefix": manifest["migrations"][:7],
            "prefix_drift_count": 0,
            "legacy_result": "exact_authority_preserved_without_reconstruction",
        },
        "tests": tests,
        "studio": results["studio_quality"],
        "gates": results["gates"],
        "bounds": {
            "package_canonical_bytes": 65536,
            "prompt_characters_per_locale": 8192,
            "archive_compressed_bytes": 131072,
            "archive_member_bytes": 131072,
            "archive_total_bytes": 131072,
            "archive_parsed_members": 4,
            "archive_ratio": "20:1",
            "archive_depth": 2,
            "workflow_nodes": 32,
            "workflow_depth": 8,
            "workflow_steps": 16,
            "workflow_branches": 2,
            "active_deployments_local": 10,
        },
        "trust_lifecycle": {
            "attestation": "origin_only",
            "trust_install_confirmation_activation": "distinct_durable_states",
            "revocation": "active_exact_binding_blocks",
            "tenth_activation": "accepted",
            "eleventh_activation": "active_deployment_limit_reached",
            "inactive_runtime": "refused",
        },
        "compatibility": {
            "retained_routes": True,
            "api_v1_route_count": 17,
            "console_entry_point": "dc",
            "p10_digest_mutation_count": 0,
        },
        "evidence_classes": list(EVIDENCE_CLASSES),
        "public_boundary": results["public_boundary"],
        "diff_check": results["diff_check"],
        "provenance": "provenance/p11-migration-receipt.json",
        "exclusions": list(EXCLUSIONS),
    }


def write_evidence(root: Path, summary: dict[str, object]) -> None:
    destination = root / SUMMARY_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    temporary_fd, temporary_name = tempfile.mkstemp(prefix=".p11-summary-", dir=destination.parent)
    try:
        with os.fdopen(temporary_fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, destination)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def main() -> int:
    try:
        paths, commits = _preconditions(ROOT)
        with tempfile.TemporaryDirectory(prefix="dc-p11-evidence-") as value:
            results = run_all(ROOT, Path(value))
        write_evidence(
            ROOT,
            build_summary(ROOT, results, paths=paths, implementation_commits=commits),
        )
    except (OSError, GateError) as exc:
        print(f"P11 evidence collection failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "written", "path": SUMMARY_PATH}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
