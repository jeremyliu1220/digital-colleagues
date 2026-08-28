# SPDX-License-Identifier: Apache-2.0

"""Run every P2 gate in disposable tool environments."""

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

from scripts.collect_p2_evidence import (
    P1_BASELINE_COMMIT,
    EvidenceError,
    public_tree_digest,
    validate_unittest_outcome,
    write_p2_evidence,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = PROJECT_ROOT / "artifacts/p2/summary.json"
PYTHON_TOOLS = ("mypy==2.3.1", "ruff==0.16.4")
SCOPES = {"all", "bootstrap", "build", "lint", "test", "typecheck"}


class ToolchainError(RuntimeError):
    """A P2 verification failure with sanitized diagnostics."""


def _sanitized(text: str, temporary: Path) -> str:
    replacements = {
        str(PROJECT_ROOT): "<project>",
        str(temporary): "<temporary>",
        str(Path.home()): "<home>",
    }
    result = text
    for private, public in replacements.items():
        result = result.replace(private, public)
    return result[-6_000:]


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


def _json_result(output: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ToolchainError(f"{label} returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise ToolchainError(f"{label} returned a non-object result")
    return value


def _base_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def _prepare_python(temporary: Path) -> tuple[Path, dict[str, str]]:
    environment_root = temporary / "python"
    _run(
        "Python environment",
        [sys.executable, "-m", "venv", str(environment_root)],
        cwd=PROJECT_ROOT,
        temporary=temporary,
    )
    executable = environment_root / "bin" / "python"
    _run(
        "Python locked tools",
        [
            str(executable),
            "-m",
            "pip",
            "--disable-pip-version-check",
            "install",
            *PYTHON_TOOLS,
        ],
        cwd=PROJECT_ROOT,
        temporary=temporary,
    )
    environment = _base_environment()
    environment["MYPY_CACHE_DIR"] = str(temporary / "mypy-cache")
    environment["RUFF_CACHE_DIR"] = str(temporary / "ruff-cache")
    return executable, environment


def _prepare_studio(temporary: Path) -> Path:
    workspace = temporary / "studio"
    shutil.copytree(
        PROJECT_ROOT / "studio",
        workspace,
        ignore=shutil.ignore_patterns("dist", "node_modules", "*.tsbuildinfo"),
    )
    _run(
        "Studio locked dependencies",
        ["npm", "ci", "--ignore-scripts", "--no-audit"],
        cwd=workspace,
        temporary=temporary,
    )
    return workspace


def _run_unittest_once(
    executable: Path,
    *,
    temporary: Path,
    environment: dict[str, str],
) -> dict[str, int | bool]:
    outcome_path = temporary / "unittest-outcome.json"
    completed = subprocess.run(
        [
            str(executable),
            "-B",
            "scripts/run_unittest_suite.py",
            "--start-directory",
            "tests",
            "--top-level-directory",
            ".",
            "--json-output",
            str(outcome_path),
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    try:
        raw = json.loads(outcome_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ToolchainError(
            "Python tests produced no valid outcome\n" + _sanitized(completed.stdout, temporary)
        ) from exc
    if not isinstance(raw, dict):
        raise ToolchainError("Python tests produced a non-object outcome")
    try:
        outcome = validate_unittest_outcome(raw)
    except EvidenceError as exc:
        raise ToolchainError(
            f"Python tests failed: {exc}\n{_sanitized(completed.stdout, temporary)}"
        ) from exc
    if completed.returncode != 0:
        raise ToolchainError("Python tests failed\n" + _sanitized(completed.stdout, temporary))
    print("[pass] Python tests")
    return outcome


def _git_text(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ToolchainError("Git evidence inspection failed")
    return completed.stdout.strip()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run P2 gates in disposable environments.")
    parser.add_argument("--scope", choices=sorted(SCOPES), default="all")
    parser.add_argument("--write-evidence", action="store_true")
    parser.add_argument("--studio-dev", action="store_true")
    parser.add_argument("--fix-python", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--fix-studio", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.write_evidence and arguments.scope != "all":
        print("P2 toolchain failed: evidence requires the complete scope", file=sys.stderr)
        return 2

    verified_gates: set[str] = set()
    unittest_outcome: dict[str, int | bool] | None = None
    repository: dict[str, Any] | None = None
    boundary: dict[str, Any] | None = None
    provenance: dict[str, Any] | None = None
    architecture: dict[str, Any] | None = None
    core_contracts: dict[str, Any] | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p2-") as temporary_name:
            temporary = Path(temporary_name)
            if arguments.fix_python:
                formatter, environment = _prepare_python(temporary)
                _run(
                    "Ruff fixes",
                    [str(formatter), "-m", "ruff", "check", "--fix", "src", "scripts", "tests"],
                    cwd=PROJECT_ROOT,
                    temporary=temporary,
                    environment=environment,
                )
                _run(
                    "Ruff formatting",
                    [str(formatter), "-m", "ruff", "format", "src", "scripts", "tests"],
                    cwd=PROJECT_ROOT,
                    temporary=temporary,
                    environment=environment,
                )
                return 0
            if arguments.fix_studio:
                workspace = _prepare_studio(temporary)
                prettier = workspace / "node_modules/.bin/prettier"
                _run(
                    "Studio formatting fixes",
                    [
                        str(prettier),
                        "--write",
                        "--ignore-path",
                        "studio/.prettierignore",
                        "studio",
                    ],
                    cwd=PROJECT_ROOT,
                    temporary=temporary,
                )
                return 0
            if arguments.studio_dev:
                workspace = _prepare_studio(temporary)
                return subprocess.run(["npm", "run", "dev"], cwd=workspace, check=False).returncode

            base_environment = _base_environment()
            if arguments.scope == "all":
                gate_commands = (
                    ("P2 repository", "p2_repository", "scripts/check_p2_repository.py"),
                    ("Public boundary", "public_boundary", "scripts/check_public_boundary.py"),
                    ("P2 provenance", "p2_provenance", "scripts/check_p2_provenance.py"),
                    ("P2 architecture", "p2_architecture", "scripts/check_p2_architecture.py"),
                    (
                        "P2 core contracts",
                        "p2_core_contracts",
                        "scripts/check_p2_core_contracts.py",
                    ),
                )
                results: dict[str, dict[str, Any]] = {}
                for label, gate_name, script in gate_commands:
                    results[gate_name] = _json_result(
                        _run(
                            label,
                            [sys.executable, "-B", script, "."],
                            cwd=PROJECT_ROOT,
                            temporary=temporary,
                            environment=base_environment,
                        ),
                        label,
                    )
                    verified_gates.add(gate_name)
                repository = results["p2_repository"]
                boundary = results["public_boundary"]
                provenance = results["p2_provenance"]
                architecture = results["p2_architecture"]
                core_contracts = results["p2_core_contracts"]

            python_scopes = {"all", "bootstrap", "lint", "test", "typecheck"}
            studio_scopes = {"all", "bootstrap", "build", "lint", "test", "typecheck"}
            python: Path | None = None
            python_environment: dict[str, str] | None = None
            studio: Path | None = None
            if arguments.scope in python_scopes:
                python, python_environment = _prepare_python(temporary)
                verified_gates.add("python_tools")
            if arguments.scope in studio_scopes:
                studio = _prepare_studio(temporary)
                verified_gates.add("studio_lock_install")

            if arguments.scope in {"all", "lint"}:
                assert python is not None and python_environment is not None and studio is not None
                _run(
                    "Ruff lint",
                    [str(python), "-m", "ruff", "check", "src", "scripts", "tests"],
                    cwd=PROJECT_ROOT,
                    temporary=temporary,
                    environment=python_environment,
                )
                verified_gates.add("ruff_lint")
                _run(
                    "Ruff format",
                    [str(python), "-m", "ruff", "format", "--check", "src", "scripts", "tests"],
                    cwd=PROJECT_ROOT,
                    temporary=temporary,
                    environment=python_environment,
                )
                verified_gates.add("ruff_format")
                _run("Studio lint", ["npm", "run", "lint"], cwd=studio, temporary=temporary)
                verified_gates.add("studio_eslint")
                _run(
                    "Studio format",
                    ["npm", "run", "format:check"],
                    cwd=studio,
                    temporary=temporary,
                )
                verified_gates.add("studio_prettier")

            if arguments.scope in {"all", "typecheck"}:
                assert python is not None and python_environment is not None and studio is not None
                _run(
                    "mypy strict",
                    [str(python), "-m", "mypy", "src", "scripts", "tests"],
                    cwd=PROJECT_ROOT,
                    temporary=temporary,
                    environment=python_environment,
                )
                verified_gates.add("mypy_strict")
                _run(
                    "Studio type-check",
                    ["npm", "run", "typecheck"],
                    cwd=studio,
                    temporary=temporary,
                )
                verified_gates.add("studio_typescript")

            if arguments.scope in {"all", "test"}:
                assert python is not None and python_environment is not None and studio is not None
                unittest_outcome = _run_unittest_once(
                    python, temporary=temporary, environment=python_environment
                )
                verified_gates.add("python_unittest")
                _run("Studio tests", ["npm", "test"], cwd=studio, temporary=temporary)
                verified_gates.add("studio_vitest")

            if arguments.scope in {"all", "build"}:
                assert studio is not None
                _run("Studio build", ["npm", "run", "build"], cwd=studio, temporary=temporary)
                verified_gates.add("studio_vite_build")

            if arguments.write_evidence:
                assert all(
                    value is not None
                    for value in (
                        repository,
                        boundary,
                        provenance,
                        architecture,
                        core_contracts,
                        unittest_outcome,
                    )
                )
                branch = _git_text("branch", "--show-current")
                head = _git_text("rev-parse", "HEAD")
                merge_base = _git_text("merge-base", "HEAD", P1_BASELINE_COMMIT)
                remotes = tuple(line for line in _git_text("remote").splitlines() if line)
                write_p2_evidence(
                    evidence_path=EVIDENCE_PATH,
                    boundary=boundary or {},
                    repository=repository or {},
                    provenance=provenance or {},
                    architecture=architecture or {},
                    core_contracts=core_contracts or {},
                    unittest_outcome=unittest_outcome or {},
                    verified_gates=verified_gates,
                    evaluated_branch=branch,
                    evaluated_head=head,
                    merge_base=merge_base,
                    public_tree_digest=public_tree_digest(PROJECT_ROOT, excluded=EVIDENCE_PATH),
                    remote_count=len(remotes),
                )
                print("[pass] P2 evidence written")
        return 0
    except (EvidenceError, OSError, ToolchainError) as exc:
        print(f"P2 toolchain failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
