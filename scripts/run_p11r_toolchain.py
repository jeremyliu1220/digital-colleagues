# SPDX-License-Identifier: Apache-2.0

"""Run branch-independent P11 current CI and separately retained P11R gates."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, TextIO

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p11_architecture import check_architecture  # noqa: E402
from scripts.check_p11_compatibility import check_compatibility  # noqa: E402
from scripts.check_p11_compose_runtime import check_compose_runtime  # noqa: E402
from scripts.check_p11_migrations import check_migrations  # noqa: E402
from scripts.check_p11_studio import check_studio  # noqa: E402
from scripts.check_p11r_ci_policy import (  # noqa: E402
    NODE_ENGINE,
    NODE_VERSION,
    NPM_VERSION,
    PACKAGE_MANAGER,
    check_ci_policy,
)
from scripts.check_p11r_provenance import check_provenance  # noqa: E402
from scripts.check_p11r_repository import (  # noqa: E402
    BASE_COMMIT,
    P11RGateError,
    check_repository,
)
from scripts.run_p8_toolchain import _prepare_python, _prepare_studio  # noqa: E402
from scripts.run_p8_unittest_suite import run_suite  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
P10_BASE = "4bef5629d450c6bb3940f606fc90194e008ee8fd"
P11_BRANCH = "codex/p11-agent-packages"
DEVELOPMENT_ONLY_TEST = (
    "tests.p11.test_repository.RepositoryTests.test_repository_gate_accepts_exact_development_scope"
)
P11_TEST_MODULES = (
    "tests.p11.test_agent_package",
    "tests.p11.test_api_cli",
    "tests.p11.test_archive",
    "tests.p11.test_attestation",
    "tests.p11.test_evidence_gate",
    "tests.p11.test_lifecycle",
    "tests.p11.test_migrations",
    "tests.p11.test_repository",
    "tests.p11.test_studio",
)


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
        tail = "\n".join(completed.stdout.splitlines()[-200:])
        safe = tail.replace(str(ROOT), "<project>")
        raise P11RGateError(f"P11R toolchain command failed\n{safe}")
    return completed.stdout


def _flatten(suite: unittest.TestSuite) -> list[unittest.case.TestCase]:
    tests: list[unittest.case.TestCase] = []
    for value in suite:
        if isinstance(value, unittest.TestSuite):
            tests.extend(_flatten(value))
        else:
            if not isinstance(value, unittest.case.TestCase):
                raise P11RGateError("P11 test inventory contains an unknown test type")
            tests.append(value)
    return tests


def current_tree_test_ids(root: Path) -> tuple[str, ...]:
    try:
        text = (root / "docs/p11r/acceptance.md").read_text(encoding="utf-8")
        section = text.split("## Exact current-tree P11 regression inventory", 1)[1]
        block = section.split("```text", 1)[1].split("```", 1)[0]
    except (OSError, UnicodeError, IndexError) as exc:
        raise P11RGateError("Literal current-tree P11 inventory is unavailable") from exc
    identifiers = tuple(line.strip() for line in block.splitlines() if line.strip())
    if (
        len(identifiers) != 100
        or len(set(identifiers)) != 100
        or DEVELOPMENT_ONLY_TEST in identifiers
        or any(not value.startswith("tests.p11.") for value in identifiers)
    ):
        raise P11RGateError("Literal current-tree P11 inventory identity is invalid")
    return identifiers


def _accepted_p11_test_ids() -> tuple[str, ...]:
    suite = unittest.defaultTestLoader.loadTestsFromNames(P11_TEST_MODULES)
    tests = _flatten(suite)
    failures = [test for test in tests if test.__class__.__name__ == "_FailedTest"]
    if failures:
        raise P11RGateError("Accepted P11 module inventory could not be loaded")
    identifiers = tuple(test.id() for test in tests)
    if len(identifiers) != 101 or len(set(identifiers)) != 101:
        raise P11RGateError("Accepted P11 test inventory is not exactly 101 unique tests")
    return identifiers


def run_current_tree_p11_tests(root: Path, *, stream: TextIO) -> dict[str, Any]:
    identifiers = current_tree_test_ids(root)
    accepted = _accepted_p11_test_ids()
    if set(accepted) != set(identifiers) | {DEVELOPMENT_ONLY_TEST}:
        raise P11RGateError(
            "Current-tree and development-only P11 inventories do not partition 101"
        )
    suite = unittest.defaultTestLoader.loadTestsFromNames(identifiers)
    selected = tuple(test.id() for test in _flatten(suite))
    if selected != identifiers:
        raise P11RGateError("Current-tree P11 tests did not load one-for-one in literal order")
    result = run_suite(suite, stream=stream)
    if (
        result.get("gate_passed") is not True
        or result.get("tests_run") != 100
        or result.get("test_ids") != sorted(identifiers)
    ):
        raise P11RGateError("Current-tree P11 regression suite failed closed")
    return {
        **result,
        "suite": "p11r_current_tree_p11_regression_suite",
        "inventory_count": 100,
        "development_only_exclusion": DEVELOPMENT_ONLY_TEST,
        "exclusion_count": 1,
    }


def run_p11r_tests(root: Path, *, stream: TextIO) -> dict[str, Any]:
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(root / "tests/p11r"),
        pattern="test_*.py",
        top_level_dir=str(root),
    )
    result = run_suite(suite, stream=stream)
    if result.get("gate_passed") is not True or int(result.get("tests_run", 0)) <= 0:
        raise P11RGateError("P11R governance suite failed closed")
    return {**result, "suite": "p11r_governance_suite"}


def _read_result(path: Path, *, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("suite") != expected:
        raise P11RGateError("P11R subprocess test result identity is invalid")
    return value


def _quality(root: Path, temporary: Path) -> dict[str, Any]:
    python, environment = _prepare_python(temporary / "python-environment")
    for command in (
        [str(python), "-m", "ruff", "check", "src", "scripts", "tests"],
        [str(python), "-m", "ruff", "format", "--check", "src", "scripts", "tests"],
        [str(python), "-m", "mypy", "src", "scripts", "tests"],
    ):
        _run(command, cwd=root, environment=environment, timeout=900)
    current_path = temporary / "current-tree-p11.json"
    _run(
        [
            str(python),
            "-B",
            "-m",
            "scripts.run_p11r_toolchain",
            "--scope",
            "current-tests",
            "--json-output",
            str(current_path),
        ],
        cwd=root,
        environment=environment,
        timeout=900,
    )
    p11r_path = temporary / "p11r-tests.json"
    _run(
        [
            str(python),
            "-B",
            "-m",
            "scripts.run_p11r_toolchain",
            "--scope",
            "p11r-tests",
            "--json-output",
            str(p11r_path),
        ],
        cwd=root,
        environment=environment,
        timeout=900,
    )
    return {
        "python_lock": "requirements/p8.lock",
        "hash_locked_environment": True,
        "ruff_lint": "passed",
        "ruff_format": "passed",
        "mypy": "passed",
        "current_tree_p11": _read_result(
            current_path, expected="p11r_current_tree_p11_regression_suite"
        ),
        "p11r": _read_result(p11r_path, expected="p11r_governance_suite"),
    }


def _studio(temporary: Path) -> dict[str, object]:
    studio = _prepare_studio(temporary / "studio-environment")
    commands = (
        ["corepack", "npm", "run", "lint"],
        ["corepack", "npm", "run", "format:check"],
        ["corepack", "npm", "run", "typecheck"],
        ["corepack", "npm", "test", "--", "--run"],
        ["corepack", "npm", "run", "build"],
    )
    for command in commands:
        _run(command, cwd=studio, timeout=600)
    return {
        "status": "passed",
        "command_count": len(commands),
        "failure_count": 0,
        "node_version_file": ".nvmrc",
        "node_version": NODE_VERSION,
        "node_engine": NODE_ENGINE,
        "npm_version": NPM_VERSION,
        "package_manager": PACKAGE_MANAGER,
    }


def run_tests(root: Path, temporary: Path) -> dict[str, Any]:
    return {
        "quality": _quality(root, temporary / "quality"),
        "studio": _studio(temporary / "studio"),
    }


def _public_boundary(root: Path) -> dict[str, object]:
    output = _run(
        [sys.executable, "-B", "scripts/check_public_boundary.py", "."],
        cwd=root,
        timeout=300,
    )
    value = json.loads(output)
    if not isinstance(value, dict) or value.get("gate") != "public_boundary_clean":
        raise P11RGateError("Public-boundary result is invalid")
    return value


def run_ci(root: Path, temporary: Path) -> dict[str, Any]:
    tests = run_tests(root, temporary / "tests")
    return {
        "schema_version": 1,
        "gate": "p11r_current_ci",
        "status": "passed",
        "tests": tests,
        "architecture": check_architecture(root),
        "migrations": check_migrations(root),
        "compatibility": check_compatibility(root),
        "studio_contract": check_studio(root),
        "ci_policy": check_ci_policy(root),
        "repository": check_repository(root, mode="ci"),
        "provenance": check_provenance(root),
        "public_boundary": _public_boundary(root),
    }


def _json_from_make(output: str) -> dict[str, Any]:
    start = output.find("{")
    if start < 0:
        raise P11RGateError("Accepted P11 aggregate emitted no JSON result")
    value = json.loads(output[start:])
    if not isinstance(value, dict):
        raise P11RGateError("Accepted P11 aggregate result shape is invalid")
    return value


def replay_accepted_p11(root: Path, temporary: Path) -> dict[str, Any]:
    checkout = temporary / "accepted-p11"
    temporary.mkdir(parents=True, exist_ok=True)
    _run(
        ["git", "clone", "--quiet", "--shared", "--no-checkout", str(root), str(checkout)],
        cwd=temporary,
        timeout=120,
    )
    _run(
        ["git", "checkout", "--quiet", "-B", P11_BRANCH, BASE_COMMIT],
        cwd=checkout,
        timeout=60,
    )
    _run(["git", "branch", "--force", "main", P10_BASE], cwd=checkout, timeout=60)
    _run(
        ["git", "update-ref", "refs/remotes/origin/main", P10_BASE],
        cwd=checkout,
        timeout=60,
    )
    if _run(["git", "status", "--porcelain"], cwd=checkout).strip():
        raise P11RGateError("Accepted P11 temporary checkout is not clean")
    result = _json_from_make(_run(["make", "p11-check"], cwd=checkout, timeout=7_200))
    quality = result.get("quality")
    if (
        not isinstance(quality, dict)
        or quality.get("tests_run") != 101
        or quality.get("gate_passed") is not True
        or any(
            quality.get(key) != 0
            for key in (
                "failures",
                "errors",
                "skipped",
                "expected_failures",
                "unexpected_successes",
            )
        )
    ):
        raise P11RGateError("Accepted P11 exact-object suite is not exactly 101 clean tests")
    return {
        "status": "passed",
        "object": BASE_COMMIT,
        "branch": P11_BRANCH,
        "historical_base": P10_BASE,
        "command": "make p11-check",
        "tests": quality,
        "temporary_checkout": True,
        "repository_ref_mutation_count": 0,
    }


def run_all(root: Path, temporary: Path) -> dict[str, Any]:
    current_ci = run_ci(root, temporary / "current-ci")
    candidate_repository = check_repository(root, mode="candidate")
    accepted_p11 = replay_accepted_p11(root, temporary / "accepted-p11-replay")
    compose = check_compose_runtime(root)
    if compose.get("cleanup_residue_count") != 0:
        raise P11RGateError("P11R Compose cleanup residue is nonzero")
    return {
        "schema_version": 1,
        "gate": "p11r_all",
        "status": "passed",
        "current_ci": current_ci,
        "candidate_repository": candidate_repository,
        "accepted_p11": accepted_p11,
        "compose_runtime": compose,
    }


def _emit(result: dict[str, Any], path: str | None) -> None:
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if path:
        Path(path).write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scope",
        choices=(
            "all",
            "ci",
            "test",
            "compose-runtime",
            "accepted-p11",
            "current-tests",
            "p11r-tests",
        ),
        default="all",
    )
    parser.add_argument("--json-output")
    args = parser.parse_args(argv)
    try:
        if args.scope == "current-tests":
            result = run_current_tree_p11_tests(ROOT, stream=sys.stderr)
        elif args.scope == "p11r-tests":
            result = run_p11r_tests(ROOT, stream=sys.stderr)
        else:
            with tempfile.TemporaryDirectory(prefix="dc-p11r-toolchain-") as value:
                temporary = Path(value)
                if args.scope == "all":
                    result = run_all(ROOT, temporary)
                elif args.scope == "ci":
                    result = run_ci(ROOT, temporary)
                elif args.scope == "test":
                    result = run_tests(ROOT, temporary)
                elif args.scope == "compose-runtime":
                    result = check_compose_runtime(ROOT)
                else:
                    result = replay_accepted_p11(ROOT, temporary)
        _emit(result, args.json_output)
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
        P11RGateError,
    ) as exc:
        safe = str(exc).replace(str(ROOT), "<project>")
        print(f"P11R toolchain failed: {safe}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
