# SPDX-License-Identifier: Apache-2.0

"""Run retained P0-P7 regressions and current P8 gates in locked workspaces."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from scripts.collect_p8_evidence import (
    EvidenceError,
    public_tree_digest,
    validate_studio_tests,
    validate_unittest,
    write_p8_evidence,
)
from scripts.p8_release_support import (
    ACCEPTANCE_COMMIT,
    BASE_COMMIT,
    NODE_VERSION,
    NPM_VERSION,
)
from scripts.run_p4_toolchain import ToolchainError, _json, _run

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements/p8.lock"
EVIDENCE = ROOT / "artifacts/p8/summary.json"
ACCEPTED_P7_SUMMARY_DIGEST = (
    "sha256:799caaa90bb66465df55c243cdfdd5fb9ee68730dc9ab2ddd58cdbf79cbc01f5"
)
FOCUSED: dict[str, tuple[str, str, str]] = {
    "repository": ("P8 repository", "p8_repository", "scripts/check_p8_repository.py"),
    "provenance": ("P8 provenance", "p8_provenance", "scripts/check_p8_provenance.py"),
    "operations": ("P8 operations", "p8_operations", "scripts/check_p8_operations.py"),
    "backup-restore": (
        "P8 backup and restore",
        "p8_backup_restore",
        "scripts/check_p8_backup_restore.py",
    ),
    "diagnostics": (
        "P8 diagnostics",
        "p8_diagnostics",
        "scripts/check_p8_diagnostics.py",
    ),
    "supply-chain": (
        "P8 supply chain",
        "p8_supply_chain",
        "scripts/check_p8_supply_chain.py",
    ),
    "reproducibility": (
        "P8 reproducibility",
        "p8_reproducibility",
        "scripts/check_p8_reproducibility.py",
    ),
    "release": ("P8 release", "p8_release", "scripts/check_p8_release.py"),
    "compose-runtime": (
        "P8 actual Compose runtime",
        "p8_compose_runtime",
        "scripts/check_p8_compose_runtime.py",
    ),
    "golden": ("P8 Golden Path", "p8_golden_path", "scripts/check_p8_golden_path.py"),
}
PRIOR_CURRENT_TREE: dict[str, tuple[str, str, str]] = {
    "p2_architecture": (
        "P2 current-tree architecture",
        "p2_architecture_current_tree",
        "scripts/check_p2_architecture.py",
    ),
    "p2_core": (
        "P2 current-tree core contracts",
        "p2_core_current_tree",
        "scripts/check_p2_core_contracts.py",
    ),
    "p3_architecture": (
        "P3 current-tree architecture",
        "p3_architecture_current_tree",
        "scripts/check_p3_architecture.py",
    ),
    "p3_migrations": (
        "P3 current-tree migrations",
        "p3_migrations_current_tree",
        "scripts/check_p3_migrations.py",
    ),
    "p3_persistence": (
        "P3 current-tree persistence",
        "p3_persistence_current_tree",
        "scripts/check_p3_persistence.py",
    ),
    "p3_runtime": (
        "P3 current-tree runtime",
        "p3_runtime_current_tree",
        "scripts/check_p3_runtime_contracts.py",
    ),
    "p3_golden": (
        "P3 current-tree Golden Path",
        "p3_golden_current_tree",
        "scripts/check_p3_golden_path.py",
    ),
    "p4_architecture": (
        "P4 current-tree architecture",
        "p4_architecture_current_tree",
        "scripts/check_p4_architecture.py",
    ),
    "p4_migrations": (
        "P4 current-tree migrations",
        "p4_migrations_current_tree",
        "scripts/check_p4_migrations.py",
    ),
    "p4_authentication": (
        "P4 current-tree authentication",
        "p4_authentication_current_tree",
        "scripts/check_p4_authentication.py",
    ),
    "p4_studio": (
        "P4 current-tree Studio",
        "p4_studio_current_tree",
        "scripts/check_p4_studio.py",
    ),
    "p4_compose": (
        "P4 current-tree Compose",
        "p4_compose_current_tree",
        "scripts/check_p4_compose.py",
    ),
    "p4_golden": (
        "P4 current-tree Golden Path",
        "p4_golden_current_tree",
        "scripts/check_p4_golden_path.py",
    ),
    "p5_architecture": (
        "P5 current-tree architecture",
        "p5_architecture_current_tree",
        "scripts/check_p5_architecture.py",
    ),
    "p5_migrations": (
        "P5 current-tree migrations",
        "p5_migrations_current_tree",
        "scripts/check_p5_migrations.py",
    ),
    "p5_builder": (
        "P5 current-tree builder",
        "p5_builder_current_tree",
        "scripts/check_p5_builder.py",
    ),
    "p5_policy": (
        "P5 current-tree policy",
        "p5_policy_current_tree",
        "scripts/check_p5_policy.py",
    ),
    "p5_studio": (
        "P5 current-tree Studio",
        "p5_studio_current_tree",
        "scripts/check_p5_studio.py",
    ),
    "p5_compose": (
        "P5 current-tree Compose",
        "p5_compose_current_tree",
        "scripts/check_p5_compose.py",
    ),
    "p5_golden": (
        "P5 current-tree Golden Path",
        "p5_golden_current_tree",
        "scripts/check_p5_golden_path.py",
    ),
    "p6_architecture": (
        "P6 current-tree architecture",
        "p6_architecture_current_tree",
        "scripts/check_p6_architecture.py",
    ),
    "p6_migrations": (
        "P6 current-tree migrations",
        "p6_migrations_current_tree",
        "scripts/check_p6_migrations.py",
    ),
    "p6_authentication": (
        "P6 current-tree authentication",
        "p6_authentication_current_tree",
        "scripts/check_p6_authentication.py",
    ),
    "p6_rbac": (
        "P6 current-tree RBAC",
        "p6_rbac_current_tree",
        "scripts/check_p6_rbac.py",
    ),
    "p6_change_approval": (
        "P6 current-tree change approval",
        "p6_change_approval_current_tree",
        "scripts/check_p6_change_approval.py",
    ),
    "p6_effect_approval": (
        "P6 current-tree effect approval",
        "p6_effect_approval_current_tree",
        "scripts/check_p6_effect_approval.py",
    ),
    "p6_audit_export": (
        "P6 current-tree audit export",
        "p6_audit_export_current_tree",
        "scripts/check_p6_audit_export.py",
    ),
    "p6_abuse": (
        "P6 current-tree abuse",
        "p6_abuse_current_tree",
        "scripts/check_p6_abuse.py",
    ),
    "p6_studio": (
        "P6 current-tree Studio",
        "p6_studio_current_tree",
        "scripts/check_p6_studio.py",
    ),
    "p6_compose": (
        "P6 current-tree Compose",
        "p6_compose_current_tree",
        "scripts/check_p6_compose.py",
    ),
    "p6_golden": (
        "P6 current-tree Golden Path",
        "p6_golden_current_tree",
        "scripts/check_p6_golden_path.py",
    ),
    "p7_architecture": (
        "P7 current-tree architecture",
        "p7_architecture_current_tree",
        "scripts/check_p7_architecture.py",
    ),
    "p7_model_adapter": (
        "P7 current-tree model adapter",
        "p7_model_adapter_current_tree",
        "scripts/check_p7_model_adapter.py",
    ),
    "p7_channel_adapter": (
        "P7 current-tree channel adapter",
        "p7_channel_adapter_current_tree",
        "scripts/check_p7_channel_adapter.py",
    ),
    "p7_configuration": (
        "P7 current-tree configuration",
        "p7_configuration_current_tree",
        "scripts/check_p7_configuration.py",
    ),
    "p7_abuse": (
        "P7 current-tree abuse",
        "p7_abuse_current_tree",
        "scripts/check_p7_abuse.py",
    ),
    "p7_compose": (
        "P7 current-tree Compose",
        "p7_compose_current_tree",
        "scripts/check_p7_compose.py",
    ),
    "p7_golden": (
        "P7 current-tree Golden Path",
        "p7_golden_current_tree",
        "scripts/check_p7_golden_path.py",
    ),
}
SCOPES = {
    "all",
    "bootstrap",
    "build",
    "lint",
    "test",
    "typecheck",
    *FOCUSED,
}


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ToolchainError("Git P8 evidence inspection failed")
    return completed.stdout.strip()


def _environment(temporary: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONPATH": str(ROOT / "src"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONWARNINGS": "ignore",
            "MYPY_CACHE_DIR": str(temporary / "mypy-cache"),
            "RUFF_CACHE_DIR": str(temporary / "ruff-cache"),
        }
    )
    return environment


def _prepare_python(temporary: Path) -> tuple[Path, dict[str, str]]:
    environment_root = temporary / "python"
    _run(
        "Python environment",
        [sys.executable, "-m", "venv", str(environment_root)],
        cwd=ROOT,
        temporary=temporary,
    )
    executable = environment_root / "bin/python"
    _run(
        "P8 hash-locked Python environment",
        [
            str(executable),
            "-m",
            "pip",
            "--disable-pip-version-check",
            "install",
            "--require-hashes",
            "-r",
            str(LOCK),
        ],
        cwd=ROOT,
        temporary=temporary,
    )
    return executable, _environment(temporary)


def _node_versions(temporary: Path) -> None:
    node = _run(
        "Node version", ["node", "--version"], cwd=ROOT / "studio", temporary=temporary
    ).strip()
    npm = _run(
        "Corepack npm version",
        ["corepack", "npm", "--version"],
        cwd=ROOT / "studio",
        temporary=temporary,
    ).strip()
    if node != f"v{NODE_VERSION}" or npm != NPM_VERSION:
        raise ToolchainError("P8 Node or npm version is not exact")


def _prepare_studio(temporary: Path) -> Path:
    _node_versions(temporary)
    workspace = temporary / "studio"
    shutil.copytree(
        ROOT / "studio",
        workspace,
        ignore=shutil.ignore_patterns("dist", "node_modules", "*.tsbuildinfo"),
    )
    _run(
        "Studio exact lock",
        ["corepack", "npm", "ci", "--ignore-scripts", "--no-audit"],
        cwd=workspace,
        temporary=temporary,
    )
    return workspace


def _gate(
    python: Path,
    *,
    label: str,
    script: str,
    temporary: Path,
    environment: dict[str, str],
) -> dict[str, Any]:
    return _json(
        _run(
            label,
            [str(python), "-B", script, "."],
            cwd=ROOT,
            temporary=temporary,
            environment=environment,
        ),
        label,
    )


def _accepted_p7() -> dict[str, Any]:
    accepted = subprocess.run(
        ["git", "show", f"{BASE_COMMIT}:artifacts/p7/summary.json"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if accepted.returncode != 0:
        raise ToolchainError("accepted P7 evidence object is unavailable")
    digest = "sha256:" + hashlib.sha256(accepted.stdout).hexdigest()
    if digest != ACCEPTED_P7_SUMMARY_DIGEST:
        raise ToolchainError("accepted P7 evidence object digest drifted")
    if (ROOT / "artifacts/p7/summary.json").read_bytes() != accepted.stdout:
        raise ToolchainError("accepted P7 evidence changed in the P8 tree")
    value = json.loads(accepted.stdout)
    if (
        value.get("status") != "development_complete_awaiting_independent_acceptance"
        or value.get("claim") != "optional_adapter_contracts_passed"
    ):
        raise ToolchainError("accepted P7 evidence claim is invalid")
    return {
        "schema_version": 1,
        "gate": "accepted_p7_baseline_clean",
        "accepted_commit": BASE_COMMIT,
        "summary_digest": digest,
        "p0_through_p7_records_immutable": True,
        "historical_evidence_rebuilt": False,
    }


def _full_unittest(python: Path, *, temporary: Path, environment: dict[str, str]) -> dict[str, Any]:
    output_path = temporary / "p8-unittest.json"
    _run(
        "P8 full Python unittest",
        [
            str(python),
            "-B",
            "scripts/run_p8_unittest_suite.py",
            "--start-directory",
            "tests",
            "--top-level-directory",
            ".",
            "--json-output",
            str(output_path),
        ],
        cwd=ROOT,
        temporary=temporary,
        environment=environment,
    )
    try:
        value = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolchainError("P8 unittest outcome is invalid") from exc
    if not isinstance(value, dict):
        raise ToolchainError("P8 unittest outcome is not an object")
    return validate_unittest(value)


def _studio_tests(studio: Path, *, temporary: Path) -> dict[str, Any]:
    output_path = temporary / "studio-vitest.json"
    _run(
        "Studio tests",
        [
            "corepack",
            "npm",
            "test",
            "--",
            "--reporter=json",
            f"--outputFile={output_path}",
        ],
        cwd=studio,
        temporary=temporary,
    )
    try:
        raw = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolchainError("Studio test outcome is invalid") from exc
    if not isinstance(raw, dict):
        raise ToolchainError("Studio test outcome is not an object")

    def count(key: str) -> int:
        value = raw.get(key)
        if type(value) is not int or value < 0:
            raise ToolchainError("Studio test counts are invalid")
        return value

    total = count("numTotalTests")
    passed = count("numPassedTests")
    failed = count("numFailedTests")
    pending = count("numPendingTests")
    todo = count("numTodoTests")
    failed_suites = count("numFailedTestSuites")
    test_results = raw.get("testResults")
    if not isinstance(test_results, list) or raw.get("success") is not True:
        raise ToolchainError("Studio test result did not pass")
    outcome = {
        "command": "corepack npm test -- --reporter=json --outputFile=<temporary>",
        "test_files": len(test_results),
        "test_count": total,
        "passed": passed,
        "failed": failed,
        "skipped": pending + todo,
        "errors": failed_suites,
        "unexpected_failures": 0,
        "status": "passed",
        "result": "passed",
    }
    return validate_studio_tests(outcome)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run P8 gates in disposable environments.")
    parser.add_argument("--scope", choices=sorted(SCOPES), default="all")
    parser.add_argument("--write-evidence", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.write_evidence and arguments.scope != "all":
        print("P8 toolchain failed: evidence requires complete scope", file=sys.stderr)
        return 2
    verified: set[str] = set()
    results: dict[str, dict[str, Any]] = {}
    unittest_outcome: dict[str, Any] | None = None
    studio_test_outcome: dict[str, Any] | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-toolchain-") as name:
            temporary = Path(name)
            python: Path | None = None
            environment: dict[str, str] | None = None
            studio: Path | None = None
            if arguments.scope != "build":
                python, environment = _prepare_python(temporary)
                verified.add("python_lock_install")
            if arguments.scope in {"all", "bootstrap", "build", "lint", "test", "typecheck"}:
                studio = _prepare_studio(temporary)
                verified.add("studio_lock_install")
            elif arguments.scope in {"reproducibility", "release", "compose-runtime", "golden"}:
                _node_versions(temporary)
            if arguments.scope in FOCUSED:
                assert python is not None and environment is not None
                label, gate, script = FOCUSED[arguments.scope]
                results[arguments.scope.replace("-", "_")] = _gate(
                    python,
                    label=label,
                    script=script,
                    temporary=temporary,
                    environment=environment,
                )
                verified.add(gate)
            if arguments.scope == "all":
                assert python is not None and environment is not None
                results["accepted_p7"] = _accepted_p7()
                verified.add("accepted_p7_baseline")
                current_tree_regressions: dict[str, Any] = {}
                for key, (label, gate, script) in PRIOR_CURRENT_TREE.items():
                    current_tree_regressions[key] = _gate(
                        python,
                        label=label,
                        script=script,
                        temporary=temporary,
                        environment=environment,
                    )
                    verified.add(gate)
                results["current_tree_regressions"] = current_tree_regressions
                for key, (label, gate, script) in FOCUSED.items():
                    results[key.replace("-", "_")] = _gate(
                        python,
                        label=label,
                        script=script,
                        temporary=temporary,
                        environment=environment,
                    )
                    verified.add(gate)
                _run(
                    "Public boundary",
                    [str(python), "-B", "scripts/check_public_boundary.py", "."],
                    cwd=ROOT,
                    temporary=temporary,
                    environment=environment,
                )
                verified.add("public_boundary")
                _run(
                    "Git diff whitespace",
                    ["git", "diff", "--check"],
                    cwd=ROOT,
                    temporary=temporary,
                )
                verified.add("git_diff_check")
            if arguments.scope in {"all", "lint"}:
                assert python is not None and environment is not None and studio is not None
                _run(
                    "Ruff lint",
                    [str(python), "-m", "ruff", "check", "src", "scripts", "tests"],
                    cwd=ROOT,
                    temporary=temporary,
                    environment=environment,
                )
                verified.add("ruff_lint")
                _run(
                    "Ruff format",
                    [
                        str(python),
                        "-m",
                        "ruff",
                        "format",
                        "--check",
                        "src",
                        "scripts",
                        "tests",
                    ],
                    cwd=ROOT,
                    temporary=temporary,
                    environment=environment,
                )
                verified.add("ruff_format")
                _run(
                    "Studio lint",
                    ["corepack", "npm", "run", "lint"],
                    cwd=studio,
                    temporary=temporary,
                )
                verified.add("studio_eslint")
                _run(
                    "Studio format",
                    ["corepack", "npm", "run", "format:check"],
                    cwd=studio,
                    temporary=temporary,
                )
                verified.add("studio_prettier")
            if arguments.scope in {"all", "typecheck"}:
                assert python is not None and environment is not None and studio is not None
                _run(
                    "mypy strict",
                    [str(python), "-m", "mypy", "src", "scripts", "tests"],
                    cwd=ROOT,
                    temporary=temporary,
                    environment=environment,
                )
                verified.add("mypy_strict")
                _run(
                    "Studio type-check",
                    ["corepack", "npm", "run", "typecheck"],
                    cwd=studio,
                    temporary=temporary,
                )
                verified.add("studio_typescript")
            if arguments.scope in {"all", "test"}:
                assert python is not None and environment is not None and studio is not None
                unittest_outcome = _full_unittest(
                    python, temporary=temporary, environment=environment
                )
                verified.add("python_unittest")
                studio_test_outcome = _studio_tests(studio, temporary=temporary)
                results["studio_tests"] = studio_test_outcome
                verified.add("studio_vitest")
            if arguments.scope in {"all", "build"}:
                assert studio is not None
                _run(
                    "Studio build",
                    ["corepack", "npm", "run", "build"],
                    cwd=studio,
                    temporary=temporary,
                )
                verified.add("studio_vite_build")
            if arguments.write_evidence:
                if _git("status", "--porcelain"):
                    raise ToolchainError("P8 evidence requires a clean implementation tree")
                if unittest_outcome is None:
                    raise ToolchainError("P8 evidence lacks full unittest results")
                if studio_test_outcome is None:
                    raise ToolchainError("P8 evidence lacks Studio test results")
                implementation_commit = _git("rev-parse", "HEAD")
                branch = _git("branch", "--show-current")
                merge_base = _git("merge-base", "HEAD", BASE_COMMIT)
                _git("merge-base", "--is-ancestor", ACCEPTANCE_COMMIT, implementation_commit)
                tree_digest = public_tree_digest(ROOT, EVIDENCE)
                write_p8_evidence(
                    evidence_path=EVIDENCE,
                    root=ROOT,
                    results=results,
                    unittest_outcome=unittest_outcome,
                    studio_test_outcome=studio_test_outcome,
                    verified_gates=verified,
                    branch=branch,
                    implementation_commit=implementation_commit,
                    merge_base=merge_base,
                    tree_digest=tree_digest,
                    tree_clean=True,
                )
                print("[pass] P8 evidence written")
            print(
                json.dumps(
                    {
                        "schema_version": 1,
                        "scope": arguments.scope,
                        "verified_gates": sorted(verified),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
    except (OSError, EvidenceError, ToolchainError) as exc:
        safe = str(exc).replace(str(ROOT), "<project>").replace(str(Path.home()), "<home>")
        print(f"P8 toolchain failed: {safe}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
