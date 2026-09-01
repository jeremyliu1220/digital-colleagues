# SPDX-License-Identifier: Apache-2.0

"""Run retained P0-P4 and current P5 gates in disposable locked environments."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from scripts.check_p5_repository import BASE_COMMIT
from scripts.collect_p5_evidence import (
    EvidenceError,
    public_tree_digest,
    validate_unittest,
    write_p5_evidence,
)
from scripts.run_p4_toolchain import (
    ROOT,
    ToolchainError,
    _git,
    _json,
    _prepare_python,
    _prepare_studio,
    _run,
)

EVIDENCE = ROOT / "artifacts/p5/summary.json"
SCOPES = {
    "all",
    "bootstrap",
    "build",
    "builder",
    "golden",
    "lint",
    "policy",
    "test",
    "typecheck",
}


def _full_unittest(python: Path, *, temporary: Path, environment: dict[str, str]) -> dict[str, Any]:
    output_path = temporary / "p5-unittest.json"
    _run(
        "P5 full Python unittest",
        [
            str(python),
            "-B",
            "scripts/run_p5_unittest_suite.py",
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
        raise ToolchainError("P5 unittest outcome is invalid") from exc
    if not isinstance(outcome, dict):
        raise ToolchainError("P5 unittest outcome is not an object")
    return validate_unittest(outcome)


def _p4_commands() -> tuple[tuple[str, str, str, str], ...]:
    return (
        ("P3 repository", "p3_repository", "p3_repository", "scripts/check_p3_repository.py"),
        ("Public boundary", "boundary", "public_boundary", "scripts/check_public_boundary.py"),
        ("P3 provenance", "p3_provenance", "p3_provenance", "scripts/check_p3_provenance.py"),
        (
            "P3 architecture",
            "p3_architecture",
            "p3_architecture",
            "scripts/check_p3_architecture.py",
        ),
        ("P3 migrations", "p3_migrations", "p3_migrations", "scripts/check_p3_migrations.py"),
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
        ("P3 Golden Path", "p3_golden", "p3_golden_path", "scripts/check_p3_golden_path.py"),
        (
            "P2 core regression",
            "p2_core",
            "p2_core_regression",
            "scripts/check_p2_core_contracts.py",
        ),
        ("P4 repository", "p4_repository", "p4_repository", "scripts/check_p4_repository.py"),
        ("P4 provenance", "p4_provenance", "p4_provenance", "scripts/check_p4_provenance.py"),
        (
            "P4 architecture",
            "p4_architecture",
            "p4_architecture",
            "scripts/check_p4_architecture.py",
        ),
        ("P4 migrations", "p4_migrations", "p4_migrations", "scripts/check_p4_migrations.py"),
        (
            "P4 authentication",
            "p4_authentication",
            "p4_authentication",
            "scripts/check_p4_authentication.py",
        ),
        ("P4 Studio", "p4_studio", "p4_studio", "scripts/check_p4_studio.py"),
        ("P4 Compose", "p4_compose", "p4_compose", "scripts/check_p4_compose.py"),
        (
            "P4 Golden Path",
            "p4_golden_path",
            "p4_golden_path",
            "scripts/check_p4_golden_path.py",
        ),
    )


def _p5_commands() -> tuple[tuple[str, str, str, str], ...]:
    return (
        ("P5 repository", "repository", "p5_repository", "scripts/check_p5_repository.py"),
        ("P5 provenance", "provenance", "p5_provenance", "scripts/check_p5_provenance.py"),
        (
            "P5 architecture",
            "architecture",
            "p5_architecture",
            "scripts/check_p5_architecture.py",
        ),
        ("P5 migrations", "migrations", "p5_migrations", "scripts/check_p5_migrations.py"),
        ("P5 builder", "builder", "p5_builder", "scripts/check_p5_builder.py"),
        ("P5 policy", "policy", "p5_policy", "scripts/check_p5_policy.py"),
        ("P5 Studio", "studio", "p5_studio", "scripts/check_p5_studio.py"),
        ("P5 Compose", "compose", "p5_compose", "scripts/check_p5_compose.py"),
        (
            "P5 Golden Path",
            "golden_path",
            "p5_golden_path",
            "scripts/check_p5_golden_path.py",
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run P5 gates in disposable environments.")
    parser.add_argument("--scope", choices=sorted(SCOPES), default="all")
    parser.add_argument("--write-evidence", action="store_true")
    parser.add_argument("--studio-dev", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.write_evidence and arguments.scope != "all":
        print("P5 toolchain failed: evidence requires complete scope", file=sys.stderr)
        return 2
    verified: set[str] = set()
    results: dict[str, dict[str, Any]] = {}
    unittest_outcome: dict[str, Any] | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p5-toolchain-") as name:
            temporary = Path(name)
            if arguments.studio_dev:
                studio_preview = _prepare_studio(temporary)
                return subprocess.run(
                    ["npm", "run", "dev"], cwd=studio_preview, check=False
                ).returncode
            python: Path | None = None
            environment: dict[str, str] | None = None
            studio: Path | None = None
            if arguments.scope in {
                "all",
                "bootstrap",
                "builder",
                "golden",
                "lint",
                "policy",
                "test",
                "typecheck",
            }:
                python, environment = _prepare_python(temporary)
                verified.add("python_lock_install")
            if arguments.scope in {"all", "bootstrap", "build", "lint", "test", "typecheck"}:
                studio = _prepare_studio(temporary)
                verified.add("studio_lock_install")
            focused = {
                "builder": ("P5 builder", "p5_builder", "scripts/check_p5_builder.py"),
                "policy": ("P5 policy", "p5_policy", "scripts/check_p5_policy.py"),
                "golden": (
                    "P5 Golden Path",
                    "p5_golden_path",
                    "scripts/check_p5_golden_path.py",
                ),
            }
            if arguments.scope in focused:
                assert python is not None and environment is not None
                label, gate, script = focused[arguments.scope]
                _json(
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
            if arguments.scope == "all":
                assert python is not None and environment is not None
                retained_gates: list[str] = []
                for label, key, gate, script in _p4_commands():
                    value = _json(
                        _run(
                            label,
                            [str(python), "-B", script, "."],
                            cwd=ROOT,
                            temporary=temporary,
                            environment=environment,
                        ),
                        label,
                    )
                    if key == "boundary":
                        results["boundary"] = value
                    retained_gates.append(gate)
                results["p4_aggregate"] = {
                    "schema_version": 1,
                    "gate": "p4_aggregate_clean",
                    "retained_gates": sorted(retained_gates),
                }
                verified.add("p4_aggregate")
                verified.add("public_boundary")
                for label, key, gate, script in _p5_commands():
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
                            "P5 actual Compose runtime",
                            [str(python), "-B", "scripts/check_p5_compose_runtime.py", "."],
                            cwd=ROOT,
                            temporary=temporary,
                            environment=environment,
                        ),
                        "P5 actual Compose runtime",
                    )
                    verified.add("p5_compose_runtime")
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
                    raise ToolchainError("P5 evidence requires a clean implementation tree")
                if unittest_outcome is None:
                    raise ToolchainError("P5 evidence lacks full unittest results")
                branch = _git("branch", "--show-current")
                implementation_commit = _git("rev-parse", "HEAD")
                merge_base = _git("merge-base", "HEAD", BASE_COMMIT)
                digest = public_tree_digest(ROOT, excluded=EVIDENCE)
                write_p5_evidence(
                    evidence_path=EVIDENCE,
                    results=results,
                    unittest_outcome=unittest_outcome,
                    verified_gates=verified,
                    branch=branch,
                    implementation_commit=implementation_commit,
                    merge_base=merge_base,
                    tree_digest=digest,
                )
                print("[pass] P5 evidence written")
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
        sanitized = str(exc).replace(str(ROOT), "<project>").replace(str(Path.home()), "<home>")
        print(f"P5 toolchain failed: {sanitized}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
