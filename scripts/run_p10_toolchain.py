# SPDX-License-Identifier: Apache-2.0

"""Run retained P9 at its exact object, then every current P10 gate."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from scripts.check_p10_compatibility import check_compatibility
from scripts.check_p10_compose_runtime import (
    build_local_candidate,
    cleanup_candidate,
    run_compose_runtime,
)
from scripts.check_p10_distribution import check_distribution
from scripts.check_p10_evidence import LOCAL_REQUIRED_GATES, REQUIRED_GATES, check_evidence
from scripts.check_p10_i18n import check_i18n
from scripts.check_p10_operations import check_operations
from scripts.check_p10_provenance import check_provenance
from scripts.check_p10_quickstart import check_remote_distribution, run_quickstart_trials
from scripts.check_p10_repository import check_repository
from scripts.check_p10_reproducibility import check_reproducibility
from scripts.check_p10_security import check_security
from scripts.collect_p10_evidence import build_summary, write_evidence
from scripts.p10_gate_support import BASE_COMMIT, SUMMARY_PATH, GateError, redact
from scripts.run_p8_toolchain import _prepare_python

ROOT = Path(__file__).resolve().parents[1]
STATIC: dict[str, tuple[str, Callable[[Path], dict[str, object]]]] = {
    "repository": ("p10_repository", check_repository),
    "provenance": ("p10_provenance", check_provenance),
    "distribution": ("p10_distribution", check_distribution),
    "security": ("p10_security", check_security),
    "operations": ("p10_operations", check_operations),
    "i18n": ("p10_i18n", check_i18n),
    "compatibility": ("p10_compatibility", check_compatibility),
    "reproducibility": ("p10_reproducibility", check_reproducibility),
}
SCOPES = {"all", "test", "compose-runtime", "quickstart", "remote-distribution", *STATIC}
P10_TEST_BOUNDARIES = {
    "tests.p10.test_repository.P10RepositoryTests.test_dirty_staged_unstaged_untracked_wrong_branch_and_base_fail_closed": "repository_identity_and_dirty_refusal",
    "tests.p10.test_repository.P10RepositoryTests.test_acceptance_history_migration_allowlist_and_p11_drift_fail": "history_migration_scope_refusal",
    "tests.p10.test_repository.P10RepositoryTests.test_rename_copy_symlink_and_special_file_fail": "path_type_bypass_refusal",
    "tests.p10.test_distribution.P10DistributionTests.test_mutable_missing_platform_and_remote_promotion_fail": "mutable_and_remote_promotion_refusal",
    "tests.p10.test_distribution.P10DistributionTests.test_oci_missing_platform_and_digest_mismatch_fail": "oci_integrity_refusal",
    "tests.p10.test_distribution.P10DistributionTests.test_external_network_and_missing_probe_fail_closed": "runtime_egress_boundary_refusal",
    "tests.p10.test_distribution.P10DistributionTests.test_remote_policy_lifecycle_and_failure_states_fail_closed": "remote_lifecycle_identity_digest_visibility_refusal",
    "tests.p10.test_security.P10SecurityTests.test_studio_secret_mount_and_credential_material_fail_closed": "secret_mount_refusal",
    "tests.p10.test_security.P10SecurityTests.test_shipped_filevault_ignores_environment_overrides": "filevault_injection_isolation",
    "tests.p10.test_operations.P10OperationsTests.test_update_restore_unsafe_root_locale_and_concurrency_refuse": "operator_abuse_refusal",
    "tests.p10.test_operations.P10OperationsTests.test_generated_manifest_round_trip_and_schema_refusals": "release_manifest_schema_refusal",
    "tests.p10.test_i18n.P10I18nTests.test_missing_extra_wrong_type_and_placeholder_mismatch_fail": "translation_integrity_refusal",
    "tests.p10.test_evidence_gate.P10EvidenceTests.test_writer_rejects_dirty_and_skipped_inputs_without_writing": "evidence_fail_closed",
}


def _run(
    command: list[str], *, cwd: Path, environment: dict[str, str] | None = None, timeout: int = 3600
) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        tail = "\n".join(completed.stdout.splitlines()[-30:])
        raise GateError(f"toolchain_command_failed\n{tail}")
    return completed.stdout


def _retained_p9(root: Path, temporary: Path) -> None:
    checkout = temporary / "accepted-p9"
    _run(
        ["git", "clone", "--quiet", "--shared", "--no-checkout", str(root), str(checkout)],
        cwd=temporary,
        timeout=120,
    )
    _run(
        ["git", "checkout", "--quiet", "-B", "codex/p9-productization-rebaseline", BASE_COMMIT],
        cwd=checkout,
        timeout=60,
    )
    _run(["make", "check"], cwd=checkout, timeout=3600)


def _studio(root: Path, temporary: Path) -> set[str]:
    temporary.mkdir(mode=0o700, parents=True, exist_ok=True)
    studio = temporary / "studio"
    shutil.copytree(root / "studio", studio, ignore=shutil.ignore_patterns("node_modules", "dist"))
    _run(["corepack", "npm", "ci", "--ignore-scripts", "--no-audit"], cwd=studio, timeout=600)
    gates: set[str] = set()
    for command, gate in (
        (["corepack", "npm", "run", "lint"], "studio_eslint"),
        (["corepack", "npm", "run", "format:check"], "studio_prettier"),
        (["corepack", "npm", "run", "typecheck"], "studio_typescript"),
        (["corepack", "npm", "test", "--", "--run"], "studio_vitest"),
        (["corepack", "npm", "run", "build"], "studio_vite_build"),
    ):
        _run(command, cwd=studio, timeout=600)
        gates.add(gate)
    return gates


def _quality(root: Path, temporary: Path) -> tuple[set[str], dict[str, Any]]:
    python, environment = _prepare_python(temporary)
    gates: set[str] = set()
    _run(
        [str(python), "-m", "ruff", "check", "src", "scripts", "tests"],
        cwd=root,
        environment=environment,
    )
    gates.add("ruff_lint")
    _run(
        [str(python), "-m", "ruff", "format", "--check", "src", "scripts", "tests"],
        cwd=root,
        environment=environment,
    )
    gates.add("ruff_format")
    _run([str(python), "-m", "mypy", "src", "scripts", "tests"], cwd=root, environment=environment)
    gates.add("mypy_strict")
    outcome_path = temporary / "p10-unittest.json"
    _run(
        [
            str(python),
            "-B",
            "scripts/run_p8_unittest_suite.py",
            "--start-directory",
            "tests/p10",
            "--top-level-directory",
            ".",
            "--json-output",
            str(outcome_path),
        ],
        cwd=root,
        environment=environment,
        timeout=900,
    )
    outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
    if (
        not isinstance(outcome, dict)
        or outcome.get("gate_passed") is not True
        or outcome.get("tests_run", 0) < 1
        or any(
            outcome.get(key) != 0
            for key in (
                "failures",
                "errors",
                "skipped",
                "expected_failures",
                "unexpected_successes",
            )
        )
    ):
        raise GateError("p10_unittest_failed_or_skipped")
    test_ids = outcome.get("test_ids")
    if not isinstance(test_ids, list):
        raise GateError("p10_unittest_identity_invalid")
    outcome["fault_boundaries"] = sorted(
        boundary for test_id, boundary in P10_TEST_BOUNDARIES.items() if test_id in test_ids
    )
    if set(outcome["fault_boundaries"]) != set(P10_TEST_BOUNDARIES.values()):
        raise GateError("p10_fault_boundary_coverage_incomplete")
    gates.add("p10_unittest")
    return gates, outcome


def run_all(
    root: Path, temporary: Path
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], set[str]]:
    results: dict[str, dict[str, Any]] = {}
    verified: set[str] = set()
    _retained_p9(root, temporary)
    verified.add("retained_p9_toolchain")
    quality, unittest = _quality(root, temporary / "quality")
    verified |= quality
    verified |= _studio(root, temporary / "studio-quality")
    for key, (identity, checker) in STATIC.items():
        result = checker(root)
        results[key] = dict(result)
        verified.add(identity)
    _run([sys.executable, "-B", "scripts/check_public_boundary.py", "."], cwd=root, timeout=300)
    verified.add("public_boundary")
    _run(["git", "diff", "--check"], cwd=root, timeout=60)
    verified.add("git_diff_check")
    candidate = build_local_candidate(root, temporary / "candidate")
    try:
        results["distribution"]["local_oci"] = candidate.oci
        results["compose_runtime"] = dict(
            run_compose_runtime(root, candidate, temporary / "compose")
        )
        verified.add("p10_compose_runtime")
        results["quickstart"] = dict(
            run_quickstart_trials(root, candidate, temporary / "quickstart")
        )
        verified.add("p10_quickstart")
    finally:
        cleanup_candidate(root, candidate)
    results["evidence"] = dict(check_evidence(root))
    verified.add("p10_evidence")
    if results["distribution"].get("lifecycle_state") == "passed":
        remote = check_remote_distribution(root)
        remote_distribution = remote.get("distribution")
        remote_quickstart = remote.get("quickstart")
        if not isinstance(remote_distribution, dict) or not isinstance(remote_quickstart, dict):
            raise GateError("remote_distribution_result_invalid")
        results["remote_distribution"] = remote_distribution
        results["remote_quickstart"] = remote_quickstart
        verified.add("p10_remote_distribution")
    expected_gates = (
        REQUIRED_GATES
        if results["distribution"].get("lifecycle_state") == "passed"
        else LOCAL_REQUIRED_GATES
    )
    if verified != expected_gates:
        raise GateError("aggregate_gate_inventory_incomplete")
    return results, unittest, verified


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=sorted(SCOPES), default="all")
    parser.add_argument("--write-evidence", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.write_evidence and arguments.scope != "all":
        print('{"status":"failed","category":"evidence_requires_complete_scope"}', file=sys.stderr)
        return 2
    try:
        if arguments.scope in STATIC:
            result = STATIC[arguments.scope][1](ROOT)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if arguments.scope == "test":
            with tempfile.TemporaryDirectory(prefix="dc-p10-test-") as name:
                _, outcome = _quality(ROOT, Path(name))
            print(json.dumps(outcome, indent=2, sort_keys=True))
            return 0
        if arguments.scope == "compose-runtime":
            from scripts.check_p10_compose_runtime import check_compose_runtime

            result = check_compose_runtime(ROOT)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if arguments.scope == "quickstart":
            from scripts.check_p10_quickstart import check_quickstart

            result = check_quickstart(ROOT)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if arguments.scope == "remote-distribution":
            result = check_remote_distribution(ROOT)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if arguments.write_evidence and (ROOT / SUMMARY_PATH).exists():
            raise GateError("evidence_already_exists")
        with tempfile.TemporaryDirectory(prefix="dc-p10-toolchain-") as name:
            results, unittest, verified = run_all(ROOT, Path(name))
            if arguments.write_evidence:
                write_evidence(ROOT, build_summary(ROOT, results, unittest, verified))
        print(
            json.dumps(
                {"schema_version": 1, "scope": "all", "verified_gates": sorted(verified)},
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    except (
        GateError,
        OSError,
        subprocess.SubprocessError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(
            json.dumps({"status": "failed", "category": redact(exc, ROOT)}, sort_keys=True),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
