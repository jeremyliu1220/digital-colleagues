# SPDX-License-Identifier: Apache-2.0

"""Run retained exact P10 and every P11 candidate gate."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p11_architecture import check_architecture  # noqa: E402
from scripts.check_p11_compatibility import check_compatibility  # noqa: E402
from scripts.check_p11_compose_runtime import check_compose_runtime  # noqa: E402
from scripts.check_p11_migrations import check_migrations  # noqa: E402
from scripts.check_p11_provenance import check_provenance  # noqa: E402
from scripts.check_p11_repository import check_repository  # noqa: E402
from scripts.check_p11_studio import check_studio  # noqa: E402
from scripts.p11_gate_support import BASE_COMMIT, GateError  # noqa: E402
from scripts.run_p8_toolchain import _prepare_python  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STATIC: dict[str, Callable[[Path], dict[str, object]]] = {
    "repository": check_repository,
    "provenance": check_provenance,
    "architecture": check_architecture,
    "migrations": check_migrations,
    "compatibility": check_compatibility,
    "studio": check_studio,
}


def _run(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
    timeout: int = 3_600,
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
        tail = "\n".join(completed.stdout.splitlines()[-40:])
        raise GateError(f"toolchain command failed\n{tail}")
    return completed.stdout


def _retained_p10(root: Path, temporary: Path) -> None:
    temporary.mkdir(parents=True, exist_ok=True)
    checkout = temporary / "accepted-p10"
    _run(
        ["git", "clone", "--quiet", "--shared", "--no-checkout", str(root), str(checkout)],
        cwd=temporary,
        timeout=120,
    )
    _run(
        ["git", "checkout", "--quiet", "-B", "codex/p10-mac-quickstart", BASE_COMMIT],
        cwd=checkout,
        timeout=60,
    )
    _run(["make", "check"], cwd=checkout)


def _quality(root: Path, temporary: Path) -> dict[str, object]:
    python, environment = _prepare_python(temporary)
    for command in (
        [str(python), "-m", "ruff", "check", "src", "scripts", "tests"],
        [str(python), "-m", "ruff", "format", "--check", "src", "scripts", "tests"],
        [str(python), "-m", "mypy", "src", "scripts", "tests"],
    ):
        _run(command, cwd=root, environment=environment, timeout=900)
    outcome_path = temporary / "p11-unittest.json"
    _run(
        [
            str(python),
            "-B",
            "scripts/run_p8_unittest_suite.py",
            "--start-directory",
            "tests/p11",
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
        or outcome.get("tests_run", 0) < 40
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
        raise GateError("P11 test floor or zero-exception policy failed")
    return outcome


def _studio(root: Path, temporary: Path) -> dict[str, object]:
    studio = temporary / "studio"
    shutil.copytree(root / "studio", studio, ignore=shutil.ignore_patterns("node_modules", "dist"))
    _run(["corepack", "npm", "ci", "--ignore-scripts", "--no-audit"], cwd=studio, timeout=600)
    commands = (
        ["corepack", "npm", "run", "lint"],
        ["corepack", "npm", "run", "format:check"],
        ["corepack", "npm", "run", "typecheck"],
        ["corepack", "npm", "test", "--", "--run"],
        ["corepack", "npm", "run", "build"],
    )
    for command in commands:
        _run(command, cwd=studio, timeout=600)
    return {"gate_passed": True, "command_count": len(commands), "failure_count": 0}


def run_all(root: Path, temporary: Path) -> dict[str, Any]:
    _retained_p10(root, temporary / "retained")
    quality = _quality(root, temporary / "quality")
    studio_quality = _studio(root, temporary / "studio-quality")
    results = {name: checker(root) for name, checker in STATIC.items()}
    _run([sys.executable, "-B", "scripts/check_public_boundary.py", "."], cwd=root, timeout=300)
    _run(["git", "diff", "--check"], cwd=root, timeout=60)
    results["compose_runtime"] = check_compose_runtime(root)
    return {
        "retained_p10": {"status": "passed", "object": BASE_COMMIT},
        "quality": quality,
        "studio_quality": studio_quality,
        "gates": results,
        "public_boundary": {"status": "passed", "failure_count": 0},
        "diff_check": {"status": "passed", "failure_count": 0},
    }


def run_tests(root: Path, temporary: Path) -> dict[str, Any]:
    return {
        "quality": _quality(root, temporary / "quality"),
        "studio_quality": _studio(root, temporary / "studio-quality"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scope", choices=("all", "test", "compose-runtime", *STATIC), default="all"
    )
    args = parser.parse_args(argv)
    try:
        with tempfile.TemporaryDirectory(prefix="dc-p11-toolchain-") as value:
            temporary = Path(value)
            if args.scope == "all":
                result: object = run_all(ROOT, temporary)
            elif args.scope == "test":
                result = run_tests(ROOT, temporary)
            elif args.scope == "compose-runtime":
                result = check_compose_runtime(ROOT)
            else:
                result = STATIC[args.scope](ROOT)
    except (OSError, subprocess.SubprocessError, GateError) as exc:
        safe = str(exc).replace(str(ROOT), "<project>")
        print(f"P11 toolchain failed: {safe}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
