# SPDX-License-Identifier: Apache-2.0

"""Run all retained P3 and current P4 gates in disposable locked environments."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from scripts.check_p4_repository import BASE_COMMIT
from scripts.collect_p4_evidence import (
    EvidenceError,
    public_tree_digest,
    validate_unittest,
    write_p4_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements/p4.lock"
EVIDENCE = ROOT / "artifacts/p4/summary.json"
SCOPES = {"all", "bootstrap", "build", "lint", "test", "typecheck"}


class ToolchainError(RuntimeError):
    """A P4 toolchain gate failed with sanitized diagnostics."""


def _sanitized(value: str, temporary: Path) -> str:
    result = value
    for private, public in (
        (str(ROOT), "<project>"),
        (str(temporary), "<temporary>"),
        (str(Path.home()), "<home>"),
    ):
        result = result.replace(private, public)
    return result[-12_000:]


def _run(
    label: str,
    command: list[str],
    *,
    cwd: Path,
    temporary: Path,
    environment: dict[str, str] | None = None,
) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ToolchainError(f"{label} failed\n{_sanitized(completed.stdout, temporary)}")
    print(f"[pass] {label}")
    return completed.stdout


def _json(output: str, label: str) -> dict[str, Any]:
    try:
        result = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ToolchainError(f"{label} returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise ToolchainError(f"{label} returned a non-object result")
    return result


def _environment(temporary: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONWARNINGS"] = "ignore"
    environment["MYPY_CACHE_DIR"] = str(temporary / "mypy-cache")
    environment["RUFF_CACHE_DIR"] = str(temporary / "ruff-cache")
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
        "P4 exact Python lock",
        [
            str(executable),
            "-m",
            "pip",
            "--disable-pip-version-check",
            "install",
            "-r",
            str(LOCK),
        ],
        cwd=ROOT,
        temporary=temporary,
    )
    return executable, _environment(temporary)


def _prepare_studio(temporary: Path) -> Path:
    workspace = temporary / "studio"
    shutil.copytree(
        ROOT / "studio",
        workspace,
        ignore=shutil.ignore_patterns("dist", "node_modules", "*.tsbuildinfo"),
    )
    _run(
        "Studio exact lock",
        ["npm", "ci", "--ignore-scripts", "--no-audit"],
        cwd=workspace,
        temporary=temporary,
    )
    return workspace


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
        raise ToolchainError("Git evidence inspection failed")
    return completed.stdout.strip()


def _full_unittest(python: Path, *, temporary: Path, environment: dict[str, str]) -> dict[str, Any]:
    output_path = temporary / "p4-unittest.json"
    _run(
        "P4 full Python unittest",
        [
            str(python),
            "-B",
            "scripts/run_p4_unittest_suite.py",
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
        outcome = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolchainError("P4 unittest outcome is invalid") from exc
    if not isinstance(outcome, dict):
        raise ToolchainError("P4 unittest outcome is not an object")
    return validate_unittest(outcome)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run P4 gates in disposable environments.")
    parser.add_argument("--scope", choices=sorted(SCOPES), default="all")
    parser.add_argument("--write-evidence", action="store_true")
    parser.add_argument("--studio-dev", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.write_evidence and arguments.scope != "all":
        print("P4 toolchain failed: evidence requires complete scope", file=sys.stderr)
        return 2
    verified: set[str] = set()
    results: dict[str, dict[str, Any]] = {}
    unittest_outcome: dict[str, Any] | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-toolchain-") as name:
            temporary = Path(name)
            if arguments.studio_dev:
                studio_preview = _prepare_studio(temporary)
                return subprocess.run(
                    ["npm", "run", "dev"], cwd=studio_preview, check=False
                ).returncode
            python: Path | None = None
            environment: dict[str, str] | None = None
            studio: Path | None = None
            if arguments.scope in {"all", "bootstrap", "lint", "test", "typecheck"}:
                python, environment = _prepare_python(temporary)
                verified.add("python_lock_install")
            if arguments.scope in {"all", "bootstrap", "build", "lint", "test", "typecheck"}:
                studio = _prepare_studio(temporary)
                verified.add("studio_lock_install")
            if arguments.scope == "all":
                assert python is not None and environment is not None
                commands = (
                    (
                        "P3 repository",
                        "p3_repository",
                        "p3_repository",
                        "scripts/check_p3_repository.py",
                    ),
                    (
                        "Public boundary",
                        "boundary",
                        "public_boundary",
                        "scripts/check_public_boundary.py",
                    ),
                    (
                        "P3 provenance",
                        "p3_provenance",
                        "p3_provenance",
                        "scripts/check_p3_provenance.py",
                    ),
                    (
                        "P3 architecture",
                        "p3_architecture",
                        "p3_architecture",
                        "scripts/check_p3_architecture.py",
                    ),
                    (
                        "P3 migrations",
                        "p3_migrations",
                        "p3_migrations",
                        "scripts/check_p3_migrations.py",
                    ),
                    (
                        "P3 persistence",
                        "p3_persistence",
                        "p3_persistence",
                        "scripts/check_p3_persistence.py",
                    ),
                    (
                        "P3 runtime",
                        "p3_runtime",
                        "p3_runtime_contracts",
                        "scripts/check_p3_runtime_contracts.py",
                    ),
                    (
                        "P3 Golden Path",
                        "p3_golden",
                        "p3_golden_path",
                        "scripts/check_p3_golden_path.py",
                    ),
                    (
                        "P2 core regression",
                        "p2_core",
                        "p2_core_regression",
                        "scripts/check_p2_core_contracts.py",
                    ),
                    (
                        "P4 repository",
                        "repository",
                        "p4_repository",
                        "scripts/check_p4_repository.py",
                    ),
                    (
                        "P4 provenance",
                        "provenance",
                        "p4_provenance",
                        "scripts/check_p4_provenance.py",
                    ),
                    (
                        "P4 architecture",
                        "architecture",
                        "p4_architecture",
                        "scripts/check_p4_architecture.py",
                    ),
                    (
                        "P4 migrations",
                        "migrations",
                        "p4_migrations",
                        "scripts/check_p4_migrations.py",
                    ),
                    (
                        "P4 authentication",
                        "authentication",
                        "p4_authentication",
                        "scripts/check_p4_authentication.py",
                    ),
                    ("P4 Studio", "studio", "p4_studio", "scripts/check_p4_studio.py"),
                    ("P4 Compose", "compose", "p4_compose", "scripts/check_p4_compose.py"),
                    (
                        "P4 Golden Path",
                        "golden_path",
                        "p4_golden_path",
                        "scripts/check_p4_golden_path.py",
                    ),
                )
                for label, key, gate, script in commands:
                    results[key] = _json(
                        _run(
                            label,
                            [str(python), "-B", script, "."],
                            cwd=ROOT,
                            temporary=temporary,
                            environment=environment,
                        ),
                        label,
                    )
                    verified.add(gate)
                if arguments.write_evidence:
                    results["compose_runtime"] = _json(
                        _run(
                            "P4 actual Compose runtime",
                            [str(python), "-B", "scripts/check_p4_compose_runtime.py", "."],
                            cwd=ROOT,
                            temporary=temporary,
                            environment=environment,
                        ),
                        "P4 actual Compose runtime",
                    )
                    verified.add("p4_compose_runtime")
                _run(
                    "Git diff whitespace", ["git", "diff", "--check"], cwd=ROOT, temporary=temporary
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
                    [str(python), "-m", "ruff", "format", "--check", "src", "scripts", "tests"],
                    cwd=ROOT,
                    temporary=temporary,
                    environment=environment,
                )
                verified.add("ruff_format")
                _run("Studio lint", ["npm", "run", "lint"], cwd=studio, temporary=temporary)
                verified.add("studio_eslint")
                _run(
                    "Studio format", ["npm", "run", "format:check"], cwd=studio, temporary=temporary
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
                    ["npm", "run", "typecheck"],
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
                _run("Studio tests", ["npm", "test"], cwd=studio, temporary=temporary)
                verified.add("studio_vitest")
            if arguments.scope in {"all", "build"}:
                assert studio is not None
                _run("Studio build", ["npm", "run", "build"], cwd=studio, temporary=temporary)
                verified.add("studio_vite_build")
            if arguments.write_evidence:
                if _git("status", "--porcelain"):
                    raise ToolchainError("P4 evidence requires a clean implementation tree")
                if unittest_outcome is None:
                    raise ToolchainError("P4 evidence lacks full unittest results")
                branch = _git("branch", "--show-current")
                implementation_commit = _git("rev-parse", "HEAD")
                merge_base = _git("merge-base", "HEAD", BASE_COMMIT)
                digest = public_tree_digest(ROOT, excluded=EVIDENCE)
                write_p4_evidence(
                    evidence_path=EVIDENCE,
                    results=results,
                    unittest_outcome=unittest_outcome,
                    verified_gates=verified,
                    branch=branch,
                    implementation_commit=implementation_commit,
                    merge_base=merge_base,
                    tree_digest=digest,
                )
                print("[pass] P4 evidence written")
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
        print(f"P4 toolchain failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
