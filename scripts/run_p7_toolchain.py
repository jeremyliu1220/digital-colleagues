# SPDX-License-Identifier: Apache-2.0

"""Run retained P0-P6 and current P7 gates in disposable locked environments."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from scripts.check_p7_repository import ACCEPTANCE_COMMIT, BASE_COMMIT
from scripts.collect_p7_evidence import (
    EvidenceError,
    public_tree_digest,
    validate_unittest,
    write_p7_evidence,
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
from scripts.run_p6_toolchain import FOCUSED as P6_FOCUSED

EVIDENCE = ROOT / "artifacts/p7/summary.json"
FOCUSED: dict[str, tuple[str, str, str]] = {
    "repository": ("P7 repository", "p7_repository", "scripts/check_p7_repository.py"),
    "provenance": ("P7 provenance", "p7_provenance", "scripts/check_p7_provenance.py"),
    "architecture": ("P7 architecture", "p7_architecture", "scripts/check_p7_architecture.py"),
    "model-adapter": (
        "P7 model adapter",
        "p7_model_adapter",
        "scripts/check_p7_model_adapter.py",
    ),
    "channel-adapter": (
        "P7 channel adapter",
        "p7_channel_adapter",
        "scripts/check_p7_channel_adapter.py",
    ),
    "configuration": (
        "P7 configuration",
        "p7_configuration",
        "scripts/check_p7_configuration.py",
    ),
    "abuse": ("P7 abuse", "p7_abuse", "scripts/check_p7_abuse.py"),
    "compose": ("P7 Compose", "p7_compose", "scripts/check_p7_compose.py"),
    "golden": (
        "P7 adapter Golden Path",
        "p7_golden_path",
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


def _full_unittest(python: Path, *, temporary: Path, environment: dict[str, str]) -> dict[str, Any]:
    output_path = temporary / "p7-unittest.json"
    _run(
        "P7 full Python unittest",
        [
            str(python),
            "-B",
            "scripts/run_p7_unittest_suite.py",
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
        raise ToolchainError("P7 unittest outcome is invalid") from exc
    if not isinstance(value, dict):
        raise ToolchainError("P7 unittest outcome is not an object")
    return validate_unittest(value)


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


def _accepted_p6_provenance(
    python: Path,
    *,
    temporary: Path,
    environment: dict[str, str],
) -> dict[str, Any]:
    snapshot = temporary / "accepted-p6"
    _run(
        "P6 accepted-tree checkout",
        [
            "git",
            "clone",
            "--quiet",
            "--shared",
            "--no-checkout",
            str(ROOT),
            str(snapshot),
        ],
        cwd=temporary,
        temporary=temporary,
    )
    _run(
        "P6 accepted-tree selection",
        ["git", "checkout", "--quiet", "--detach", BASE_COMMIT],
        cwd=snapshot,
        temporary=temporary,
    )
    return _json(
        _run(
            "P6 provenance",
            [
                str(python),
                "-B",
                str(ROOT / "scripts/check_p6_provenance.py"),
                str(snapshot),
            ],
            cwd=ROOT,
            temporary=temporary,
            environment=environment,
        ),
        "P6 provenance",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run P7 gates in disposable environments.")
    parser.add_argument("--scope", choices=sorted(SCOPES), default="all")
    parser.add_argument("--write-evidence", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.write_evidence and arguments.scope != "all":
        print("P7 toolchain failed: evidence requires complete scope", file=sys.stderr)
        return 2
    verified: set[str] = set()
    results: dict[str, dict[str, Any]] = {}
    unittest_outcome: dict[str, Any] | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-toolchain-") as name:
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
                retained_p4: list[str] = []
                for label, key, gate, script in _p4_commands():
                    value = _gate(
                        python,
                        label=label,
                        script=script,
                        temporary=temporary,
                        environment=environment,
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
                    results["p5_" + key] = _gate(
                        python,
                        label=label,
                        script=script,
                        temporary=temporary,
                        environment=environment,
                    )
                    retained_p5.append(gate)
                results["p5_aggregate"] = {
                    "schema_version": 1,
                    "gate": "p5_aggregate_clean",
                    "retained_gates": sorted(retained_p5),
                }
                verified.add("p5_aggregate")
                retained_p6: list[str] = []
                for key, (label, gate, script) in P6_FOCUSED.items():
                    if key == "provenance":
                        results["p6_provenance"] = _accepted_p6_provenance(
                            python,
                            temporary=temporary,
                            environment=environment,
                        )
                    else:
                        results["p6_" + key.replace("-", "_")] = _gate(
                            python,
                            label=label,
                            script=script,
                            temporary=temporary,
                            environment=environment,
                        )
                    retained_p6.append(gate)
                results["p6_aggregate"] = {
                    "schema_version": 1,
                    "gate": "p6_aggregate_clean",
                    "retained_gates": sorted(retained_p6),
                }
                verified.add("p6_aggregate")
                for key, (label, gate, script) in FOCUSED.items():
                    results[key.replace("-", "_")] = _gate(
                        python,
                        label=label,
                        script=script,
                        temporary=temporary,
                        environment=environment,
                    )
                    verified.add(gate)
                if arguments.write_evidence:
                    results["compose_runtime"] = _gate(
                        python,
                        label="P7 actual Compose runtime",
                        script="scripts/check_p7_compose_runtime.py",
                        temporary=temporary,
                        environment=environment,
                    )
                    verified.add("p7_compose_runtime")
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
                    python,
                    temporary=temporary,
                    environment=environment,
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
                    raise ToolchainError("P7 evidence requires a clean implementation tree")
                if unittest_outcome is None:
                    raise ToolchainError("P7 evidence lacks full unittest results")
                implementation_commit = _git("rev-parse", "HEAD")
                branch = _git("branch", "--show-current")
                merge_base = _git("merge-base", "HEAD", BASE_COMMIT)
                _git("merge-base", "--is-ancestor", ACCEPTANCE_COMMIT, implementation_commit)
                tree_digest = public_tree_digest(ROOT, EVIDENCE)
                write_p7_evidence(
                    evidence_path=EVIDENCE,
                    root=ROOT,
                    results=results,
                    unittest_outcome=unittest_outcome,
                    verified_gates=verified,
                    branch=branch,
                    implementation_commit=implementation_commit,
                    merge_base=merge_base,
                    tree_digest=tree_digest,
                    tree_clean=True,
                )
                print("[pass] P7 evidence written")
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
        print(f"P7 toolchain failed: {safe}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
