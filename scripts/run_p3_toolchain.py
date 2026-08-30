# SPDX-License-Identifier: Apache-2.0

"""Run every P3 gate in disposable locked tool environments."""

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

from scripts.collect_p3_evidence import (
    P2_BASE_COMMIT,
    EvidenceError,
    public_tree_digest,
    validate_unittest,
    write_p3_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "artifacts/p3/summary.json"
FINGERPRINT_BEFORE = ROOT / "artifacts/p3/parent-fingerprint-before.json"
FINGERPRINT_AFTER = ROOT / "artifacts/p3/parent-fingerprint-after.json"
LOCK = ROOT / "requirements/p3.lock"
SCOPES = {"all", "bootstrap", "build", "lint", "test", "typecheck"}


class ToolchainError(RuntimeError):
    """A P3 gate failed with sanitized diagnostics."""


def _sanitized(value: str, temporary: Path) -> str:
    result = value
    for private, public in (
        (str(ROOT), "<project>"),
        (str(temporary), "<temporary>"),
        (str(Path.home()), "<home>"),
    ):
        result = result.replace(private, public)
    return result[-8_000:]


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
        value = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ToolchainError(f"{label} returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise ToolchainError(f"{label} returned a non-object result")
    return value


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ToolchainError(f"{label} is unavailable or invalid") from exc
    if not isinstance(value, dict):
        raise ToolchainError(f"{label} is not a JSON object")
    return value


def _environment(temporary: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
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
    executable = environment_root / "bin" / "python"
    _run(
        "P3 exact Python lock",
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


def _full_unittest(
    python: Path,
    *,
    temporary: Path,
    environment: dict[str, str],
) -> dict[str, Any]:
    outcome_path = temporary / "p3-unittest.json"
    output = _run(
        "P3 full Python unittest",
        [
            str(python),
            "-B",
            "scripts/run_p3_unittest_suite.py",
            "--start-directory",
            "tests",
            "--top-level-directory",
            ".",
            "--json-output",
            str(outcome_path),
        ],
        cwd=ROOT,
        temporary=temporary,
        environment=environment,
    )
    del output
    return validate_unittest(_read_json(outcome_path, "P3 unittest outcome"))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run P3 gates in disposable environments.")
    parser.add_argument("--scope", choices=sorted(SCOPES), default="all")
    parser.add_argument("--write-evidence", action="store_true")
    parser.add_argument("--studio-dev", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.write_evidence and arguments.scope != "all":
        print("P3 toolchain failed: evidence requires complete scope", file=sys.stderr)
        return 2
    verified: set[str] = set()
    results: dict[str, dict[str, Any]] = {}
    unittest_outcome: dict[str, Any] | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-toolchain-") as name:
            temporary = Path(name)
            if arguments.studio_dev:
                preview_studio = _prepare_studio(temporary)
                return subprocess.run(
                    ["npm", "run", "dev"], cwd=preview_studio, check=False
                ).returncode
            python_scopes = {"all", "bootstrap", "lint", "test", "typecheck"}
            studio_scopes = {"all", "bootstrap", "build", "lint", "test", "typecheck"}
            python: Path | None = None
            environment: dict[str, str] | None = None
            studio: Path | None = None
            if arguments.scope in python_scopes:
                python, environment = _prepare_python(temporary)
                verified.add("python_lock_install")
            if arguments.scope in studio_scopes:
                studio = _prepare_studio(temporary)
                verified.add("studio_lock_install")
            if arguments.scope == "all":
                assert python is not None and environment is not None
                commands = (
                    (
                        "P3 repository",
                        "repository",
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
                        "provenance",
                        "p3_provenance",
                        "scripts/check_p3_provenance.py",
                    ),
                    (
                        "P3 architecture",
                        "architecture",
                        "p3_architecture",
                        "scripts/check_p3_architecture.py",
                    ),
                    (
                        "P3 migrations",
                        "migrations",
                        "p3_migrations",
                        "scripts/check_p3_migrations.py",
                    ),
                    (
                        "P3 persistence",
                        "persistence",
                        "p3_persistence",
                        "scripts/check_p3_persistence.py",
                    ),
                    (
                        "P3 runtime contracts",
                        "runtime_contracts",
                        "p3_runtime_contracts",
                        "scripts/check_p3_runtime_contracts.py",
                    ),
                    (
                        "P3 Golden Path",
                        "golden_path",
                        "p3_golden_path",
                        "scripts/check_p3_golden_path.py",
                    ),
                    (
                        "P2 core regression",
                        "p2_core",
                        "p2_core_regression",
                        "scripts/check_p2_core_contracts.py",
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
                    [str(python), "-m", "ruff", "format", "--check", "src", "scripts", "tests"],
                    cwd=ROOT,
                    temporary=temporary,
                    environment=environment,
                )
                verified.add("ruff_format")
                _run("Studio lint", ["npm", "run", "lint"], cwd=studio, temporary=temporary)
                verified.add("studio_eslint")
                _run(
                    "Studio format",
                    ["npm", "run", "format:check"],
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
                    raise ToolchainError("P3 evidence requires a clean implementation tree")
                if unittest_outcome is None:
                    raise ToolchainError("P3 evidence lacks the full unittest outcome")
                branch = _git("branch", "--show-current")
                head = _git("rev-parse", "HEAD")
                merge_base = _git("merge-base", "HEAD", P2_BASE_COMMIT)
                remote_count = len(tuple(line for line in _git("remote").splitlines() if line))
                before = _read_json(FINGERPRINT_BEFORE, "P3 parent before fingerprint")
                after = _read_json(FINGERPRINT_AFTER, "P3 parent after fingerprint")
                verified.add("p3_parent_fingerprint")
                write_p3_evidence(
                    evidence_path=EVIDENCE,
                    results=results,
                    parent_before=before,
                    parent_after=after,
                    unittest_outcome=unittest_outcome,
                    verified_gates=verified,
                    branch=branch,
                    implementation_commit=head,
                    merge_base=merge_base,
                    tree_digest=public_tree_digest(ROOT, excluded=EVIDENCE),
                    remote_count=remote_count,
                )
                print("[pass] P3 evidence written")
        return 0
    except (EvidenceError, OSError, ToolchainError) as exc:
        print(f"P3 toolchain failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
