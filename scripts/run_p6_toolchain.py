# SPDX-License-Identifier: Apache-2.0

"""Run retained P0-P5 and current P6 gates in disposable locked environments."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from scripts.check_p6_repository import BASE_COMMIT
from scripts.collect_p6_evidence import (
    EvidenceError,
    public_tree_digest,
    validate_unittest,
    write_p6_evidence,
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
from scripts.run_p5_toolchain import _p4_commands, _p5_commands

EVIDENCE = ROOT / "artifacts/p6/summary.json"
FOCUSED: dict[str, tuple[str, str, str]] = {
    "repository": ("P6 repository", "p6_repository", "scripts/check_p6_repository.py"),
    "provenance": ("P6 provenance", "p6_provenance", "scripts/check_p6_provenance.py"),
    "architecture": ("P6 architecture", "p6_architecture", "scripts/check_p6_architecture.py"),
    "migrations": ("P6 migrations", "p6_migrations", "scripts/check_p6_migrations.py"),
    "authentication": (
        "P6 authentication",
        "p6_authentication",
        "scripts/check_p6_authentication.py",
    ),
    "rbac": ("P6 RBAC", "p6_rbac", "scripts/check_p6_rbac.py"),
    "change-approval": (
        "P6 change approval",
        "p6_change_approval",
        "scripts/check_p6_change_approval.py",
    ),
    "effect-approval": (
        "P6 effect approval",
        "p6_effect_approval",
        "scripts/check_p6_effect_approval.py",
    ),
    "audit-export": (
        "P6 audit export",
        "p6_audit_export",
        "scripts/check_p6_audit_export.py",
    ),
    "abuse": ("P6 abuse", "p6_abuse", "scripts/check_p6_abuse.py"),
    "studio": ("P6 Studio", "p6_studio", "scripts/check_p6_studio.py"),
    "compose": ("P6 Compose", "p6_compose", "scripts/check_p6_compose.py"),
    "golden": (
        "P6 security Golden Path",
        "p6_golden_path",
        "scripts/check_p6_golden_path.py",
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


def _full_unittest(python: Path, *, temporary: Path, environment: dict[str, str]) -> dict[str, Any]:
    output_path = temporary / "p6-unittest.json"
    _run(
        "P6 full Python unittest",
        [
            str(python),
            "-B",
            "scripts/run_p6_unittest_suite.py",
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
        raise ToolchainError("P6 unittest outcome is invalid") from exc
    if not isinstance(value, dict):
        raise ToolchainError("P6 unittest outcome is not an object")
    return validate_unittest(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run P6 gates in disposable environments.")
    parser.add_argument("--scope", choices=sorted(SCOPES), default="all")
    parser.add_argument("--write-evidence", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.write_evidence and arguments.scope != "all":
        print("P6 toolchain failed: evidence requires complete scope", file=sys.stderr)
        return 2
    verified: set[str] = set()
    results: dict[str, dict[str, Any]] = {}
    unittest_outcome: dict[str, Any] | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-toolchain-") as name:
            temporary = Path(name)
            python: Path | None = None
            environment: dict[str, str] | None = None
            studio: Path | None = None
            if arguments.scope != "build":
                python, environment = _prepare_python(temporary)
                environment["RUFF_CACHE_DIR"] = str(temporary / "ruff-cache")
                verified.add("python_lock_install")
            if arguments.scope in {"all", "bootstrap", "build", "lint", "test", "typecheck"}:
                studio = _prepare_studio(temporary)
                verified.add("studio_lock_install")
            if arguments.scope in FOCUSED:
                assert python is not None and environment is not None
                label, gate, script = FOCUSED[arguments.scope]
                results[arguments.scope] = _json(
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
                retained_p4: list[str] = []
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
                    retained_p4.append(gate)
                results["p4_aggregate"] = {
                    "schema_version": 1,
                    "gate": "p4_aggregate_clean",
                    "retained_gates": sorted(retained_p4),
                }
                verified.update({"p4_aggregate", "public_boundary"})
                retained_p5: list[str] = []
                for label, key, gate, script in _p5_commands():
                    results["p5_" + key] = _json(
                        _run(
                            label,
                            [str(python), "-B", script, "."],
                            cwd=ROOT,
                            temporary=temporary,
                            environment=environment,
                        ),
                        label,
                    )
                    retained_p5.append(gate)
                results["p5_aggregate"] = {
                    "schema_version": 1,
                    "gate": "p5_aggregate_clean",
                    "retained_gates": sorted(retained_p5),
                }
                verified.add("p5_aggregate")
                for key, (label, gate, script) in FOCUSED.items():
                    results[key.replace("-", "_")] = _json(
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
                            "P6 actual Compose runtime",
                            [str(python), "-B", "scripts/check_p6_compose_runtime.py", "."],
                            cwd=ROOT,
                            temporary=temporary,
                            environment=environment,
                        ),
                        "P6 actual Compose runtime",
                    )
                    verified.add("p6_compose_runtime")
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
                    raise ToolchainError("P6 evidence requires a clean implementation tree")
                if unittest_outcome is None:
                    raise ToolchainError("P6 evidence lacks full unittest results")
                implementation_commit = _git("rev-parse", "HEAD")
                branch = _git("branch", "--show-current")
                merge_base = _git("merge-base", "HEAD", BASE_COMMIT)
                migration_digest = (
                    "sha256:"
                    + hashlib.sha256(
                        (ROOT / "migrations/007_governance_hardening.sql").read_bytes()
                    ).hexdigest()
                )
                tree_digest = public_tree_digest(ROOT, EVIDENCE)
                write_p6_evidence(
                    evidence_path=EVIDENCE,
                    root=ROOT,
                    results=results,
                    unittest_outcome=unittest_outcome,
                    verified_gates=verified,
                    branch=branch,
                    implementation_commit=implementation_commit,
                    merge_base=merge_base,
                    tree_digest=tree_digest,
                    migration_digest=migration_digest,
                )
                print("[pass] P6 evidence written")
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
        print(f"P6 toolchain failed: {safe}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
