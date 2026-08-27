# SPDX-License-Identifier: Apache-2.0

"""Run P1 gates in disposable environments and optionally rebuild safe evidence."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = PROJECT_ROOT / "artifacts" / "p1" / "summary.json"
APACHE_LICENSE_DIGEST = "sha256:cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
PYTHON_TOOLS = ("mypy==2.3.1", "ruff==0.16.4")
SCOPES = {"all", "bootstrap", "build", "lint", "test", "typecheck"}
REQUIRED_EVIDENCE_GATES = frozenset(
    {
        "mypy_strict",
        "public_boundary",
        "p1_scaffold_contract",
        "python_tools",
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
UNITTEST_INTEGER_FIELDS = (
    "tests_run",
    "failures",
    "errors",
    "skipped",
    "expected_failures",
    "unexpected_successes",
)


class ToolchainError(RuntimeError):
    """A P1 verification failure with sanitized diagnostics."""


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
        diagnostic = _sanitized(completed.stdout, temporary)
        raise ToolchainError(f"{label} failed\n{diagnostic}")
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
    environment = os.environ.copy()
    environment["MYPY_CACHE_DIR"] = str(temporary / "mypy-cache")
    environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
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


def _root_git_entry_present(project_root: Path) -> bool:
    try:
        (project_root / ".git").lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise ToolchainError("root Git administrative state is unreadable") from exc
    return True


def _validated_unittest_outcome(outcome: dict[str, Any]) -> dict[str, int | bool]:
    expected_fields = {*UNITTEST_INTEGER_FIELDS, "gate_passed"}
    if set(outcome) != expected_fields:
        raise ToolchainError("the unittest outcome has unexpected fields")
    for field in UNITTEST_INTEGER_FIELDS:
        if type(outcome[field]) is not int or outcome[field] < 0:
            raise ToolchainError("the unittest outcome has an invalid count")
    if outcome["tests_run"] == 0:
        raise ToolchainError("the unittest suite ran zero tests")
    rejected = any(outcome[field] != 0 for field in UNITTEST_INTEGER_FIELDS[1:])
    if outcome["gate_passed"] is not True or rejected:
        raise ToolchainError("the unittest outcome does not satisfy the zero-exception gate")
    return {field: outcome[field] for field in (*UNITTEST_INTEGER_FIELDS, "gate_passed")}


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
        raw_outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        diagnostic = _sanitized(completed.stdout, temporary)
        raise ToolchainError(f"Python tests produced no valid outcome\n{diagnostic}") from exc
    if not isinstance(raw_outcome, dict):
        raise ToolchainError("Python tests produced a non-object outcome")
    try:
        outcome = _validated_unittest_outcome(raw_outcome)
    except ToolchainError as exc:
        diagnostic = _sanitized(completed.stdout, temporary)
        raise ToolchainError(f"Python tests failed: {exc}\n{diagnostic}") from exc
    if completed.returncode != 0:
        diagnostic = _sanitized(completed.stdout, temporary)
        raise ToolchainError(f"Python tests failed\n{diagnostic}")
    print("[pass] Python tests")
    return outcome


def write_p1_evidence(
    *,
    project_root: Path,
    evidence_path: Path,
    boundary: dict[str, Any],
    scaffold: dict[str, Any],
    unittest_outcome: dict[str, Any],
    verified_gates: set[str],
) -> None:
    git_initialized = _root_git_entry_present(project_root)
    if git_initialized:
        raise ToolchainError("P1 evidence requires a pre-Git project root")
    missing_gates = REQUIRED_EVIDENCE_GATES - verified_gates
    if missing_gates:
        raise ToolchainError("P1 evidence is missing required mechanical gates")
    outcome = _validated_unittest_outcome(unittest_outcome)
    if boundary.get("gate") != "public_boundary_clean":
        raise ToolchainError("the public-boundary result is not clean")
    if type(boundary.get("files_scanned")) is not int or boundary["files_scanned"] <= 0:
        raise ToolchainError("the public-boundary file count is invalid")
    if boundary.get("exceptions_applied") != 0:
        raise ToolchainError("P1 evidence requires zero public-boundary exceptions")
    if boundary.get("policy_version") != "p0-v1":
        raise ToolchainError("the public-boundary policy version changed")
    if scaffold.get("gate") != "p1_scaffold_contract_clean":
        raise ToolchainError("the P1 scaffold contract is not clean")
    if scaffold.get("p2_product_paths_present") != 0:
        raise ToolchainError("P2 product paths are present")
    if scaffold.get("runtime_dependency_count") != 0:
        raise ToolchainError("the P1 Python runtime dependency boundary changed")
    if scaffold.get("requires_python") != ">=3.12":
        raise ToolchainError("the P1 Python version boundary changed")
    if scaffold.get("license_digest") != APACHE_LICENSE_DIGEST:
        raise ToolchainError("the reviewed Apache-2.0 license digest changed")
    if scaffold.get("notice_operator_review_record_present") is not True:
        raise ToolchainError("the NOTICE operator review record is unavailable")

    summary = {
        "schema_version": 2,
        "gate": "p1_public_repository_scaffold",
        "status": "passed",
        "completed_date": date.today().isoformat(),
        "claim_scope": "Clean-room public repository scaffold only.",
        "results": {
            "unittest": outcome,
            "python": {
                "ruff_lint": "passed" if "ruff_lint" in verified_gates else "not_run",
                "ruff_format": "passed" if "ruff_format" in verified_gates else "not_run",
                "mypy_strict": "passed" if "mypy_strict" in verified_gates else "not_run",
                "requires_python": scaffold["requires_python"],
                "runtime_dependency_count": scaffold["runtime_dependency_count"],
            },
            "studio": {
                "npm_lock_install": (
                    "passed" if "studio_lock_install" in verified_gates else "not_run"
                ),
                "eslint": "passed" if "studio_eslint" in verified_gates else "not_run",
                "prettier": "passed" if "studio_prettier" in verified_gates else "not_run",
                "typescript": "passed" if "studio_typescript" in verified_gates else "not_run",
                "vitest": "passed" if "studio_vitest" in verified_gates else "not_run",
                "vite_build": "passed" if "studio_vite_build" in verified_gates else "not_run",
            },
            "public_boundary": {
                "files_scanned": boundary["files_scanned"],
                "findings": 0,
                "exceptions_applied": boundary["exceptions_applied"],
                "policy_version": boundary["policy_version"],
            },
            "scaffold_contract": scaffold,
            "licensing": {
                "outbound_license": "Apache-2.0",
                "license_digest": scaffold["license_digest"],
                "license_text_mechanically_verified": True,
                "notice_review": "operator_review_record_present",
            },
        },
        "mechanically_verified_boundaries": {
            "git_initialized": git_initialized,
            "root_git_administrative_entry_present": git_initialized,
            "p2_product_paths_present": scaffold["p2_product_paths_present"],
            "python_runtime_dependency_count": scaffold["runtime_dependency_count"],
            "public_boundary_findings": 0,
            "public_boundary_exceptions_applied": boundary["exceptions_applied"],
        },
        "non_mechanical_claims": {
            "remote_created": "not_evaluated_by_automated_evidence",
            "committed": "not_evaluated_by_automated_evidence",
            "published": "not_evaluated_by_automated_evidence",
            "product_code_migrated": "not_evaluated_by_automated_evidence",
            "parent_worktree_content_used": "not_evaluated_by_automated_evidence",
            "live_provider_evidence_used": "not_evaluated_by_automated_evidence",
            "personal_data_used": "not_evaluated_by_automated_evidence",
        },
        "not_evidence_for": [
            "P2 core primitives",
            "a runnable product Golden Path",
            "security effectiveness",
            "privacy effectiveness",
            "production readiness",
            "production tenancy isolation",
            "enterprise identity and access management",
            "compliance",
            "live provider acceptance",
            "human pilot acceptance",
        ],
        "verification_commands": [
            "make check",
            "make evidence-p1",
            "python3 -B scripts/check_public_boundary.py .",
            "python3 -B scripts/check_p1_scaffold.py .",
            "python3 -B scripts/run_unittest_suite.py --start-directory tests --top-level-directory .",
        ],
    }
    serialized = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=evidence_path.parent, prefix=".p1-summary-", text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(serialized)
        if _root_git_entry_present(project_root):
            raise ToolchainError("P1 evidence requires a pre-Git project root")
        os.replace(temporary_name, evidence_path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run P1 gates in disposable environments.")
    parser.add_argument("--scope", choices=sorted(SCOPES), default="all")
    parser.add_argument("--write-evidence", action="store_true")
    parser.add_argument("--studio-dev", action="store_true")
    parser.add_argument("--fix-python", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--fix-studio", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.write_evidence and arguments.scope != "all":
        print("P1 toolchain failed: evidence requires the complete scope", file=sys.stderr)
        return 2

    verified_gates: set[str] = set()
    unittest_outcome: dict[str, int | bool] | None = None
    try:
        if arguments.write_evidence and _root_git_entry_present(PROJECT_ROOT):
            raise ToolchainError("P1 evidence requires a pre-Git project root")
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p1-") as temporary_name:
            temporary = Path(temporary_name)
            if arguments.fix_python:
                formatter_python, environment = _prepare_python(temporary)
                _run(
                    "Ruff fixes",
                    [
                        str(formatter_python),
                        "-m",
                        "ruff",
                        "check",
                        "--fix",
                        "src",
                        "scripts",
                        "tests",
                    ],
                    cwd=PROJECT_ROOT,
                    temporary=temporary,
                    environment=environment,
                )
                _run(
                    "Ruff formatting",
                    [
                        str(formatter_python),
                        "-m",
                        "ruff",
                        "format",
                        "src",
                        "scripts",
                        "tests",
                    ],
                    cwd=PROJECT_ROOT,
                    temporary=temporary,
                    environment=environment,
                )
                return 0
            if arguments.fix_studio:
                workspace = _prepare_studio(temporary)
                prettier = workspace / "node_modules" / ".bin" / "prettier"
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

            boundary: dict[str, Any] | None = None
            scaffold: dict[str, Any] | None = None
            if arguments.scope == "all":
                scaffold = _json_result(
                    _run(
                        "P1 scaffold contract",
                        [sys.executable, "-B", "scripts/check_p1_scaffold.py", "."],
                        cwd=PROJECT_ROOT,
                        temporary=temporary,
                    ),
                    "P1 scaffold contract",
                )
                verified_gates.add("p1_scaffold_contract")
                boundary = _json_result(
                    _run(
                        "Public boundary",
                        [sys.executable, "-B", "scripts/check_public_boundary.py", "."],
                        cwd=PROJECT_ROOT,
                        temporary=temporary,
                    ),
                    "Public boundary",
                )
                verified_gates.add("public_boundary")

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
                    python,
                    temporary=temporary,
                    environment=python_environment,
                )
                verified_gates.add("python_unittest")
                _run("Studio tests", ["npm", "test"], cwd=studio, temporary=temporary)
                verified_gates.add("studio_vitest")

            if arguments.scope in {"all", "build"}:
                assert studio is not None
                _run("Studio build", ["npm", "run", "build"], cwd=studio, temporary=temporary)
                verified_gates.add("studio_vite_build")

            if arguments.write_evidence:
                assert (
                    boundary is not None and scaffold is not None and unittest_outcome is not None
                )
                write_p1_evidence(
                    project_root=PROJECT_ROOT,
                    evidence_path=EVIDENCE_PATH,
                    boundary=boundary,
                    scaffold=scaffold,
                    unittest_outcome=unittest_outcome,
                    verified_gates=verified_gates,
                )
                print("[pass] P1 evidence summary")
    except (OSError, ToolchainError) as exc:
        print(f"P1 toolchain failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
