# SPDX-License-Identifier: Apache-2.0

"""Run P12 governance gates and exact-object historical replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import ssl
import stat
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p12_ci_policy import (  # noqa: E402
    NODE_ENGINE,
    NODE_VERSION,
    NPM_VERSION,
    PACKAGE_MANAGER,
    check_ci_policy,
)
from scripts.check_p12_migrations import check_migrations  # noqa: E402
from scripts.check_p12_provenance import check_provenance  # noqa: E402
from scripts.check_p12_rebaseline import check_rebaseline  # noqa: E402
from scripts.check_p12_repository import (  # noqa: E402
    ACCEPTANCE_BLOB,
    ACCEPTANCE_COMMIT,
    BASE_COMMIT,
    SUMMARY_PATH,
    P12GateError,
    check_repository,
    git,
)
from scripts.run_p8_toolchain import _prepare_python, _prepare_studio  # noqa: E402
from scripts.run_p8_unittest_suite import run_suite  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ACCEPTED_P11 = "7e5387f148f86b5c9b07820dd8b8f4e18e12dc38"
P11R_BRANCH = "codex/p11r-ci-alignment"
PYPROJECT = (
    "pyproject.toml",
    "77df2013d93d8b8b6d0441cccb44a127f9c88f07",
    "25683ddd04aa1f2abf21ae60d42a1a44bb7e198d721cfa6d452b8fb61483c15a",
)
PYTHON_LOCK = (
    "requirements/p8.lock",
    "819980980ba87d1b7166af4b4b0da53ca4e4ac63",
    "5afb5bc2f6bf2cfdc77d0457b92255f822d89cd3cd754ebb876741d7ee6430d0",
)
CERTIFI_VERSION = "2026.7.22"
PACKAGING_VERSION = "26.3"
CERTIFI_WHEEL_HASH = "62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775"
CERTIFI_BUNDLE_SHA256 = "9cc2a774b5198dcff14d9be1e66091f538975d867ce029a96bce15a55dfd730f"
P12_TEST_MODULES = (
    "tests.p12.test_ci_policy",
    "tests.p12.test_evidence_gate",
    "tests.p12.test_migrations",
    "tests.p12.test_provenance",
    "tests.p12.test_rebaseline",
    "tests.p12.test_repository",
)
P12_TEST_COUNT = 89


def _safe(value: str) -> str:
    return value.replace(str(ROOT), "<project>")


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
        raise P12GateError(f"P12 toolchain command failed\n{_safe(tail)}")
    return completed.stdout


def _flatten(suite: unittest.TestSuite) -> list[unittest.case.TestCase]:
    tests: list[unittest.case.TestCase] = []
    for value in suite:
        if isinstance(value, unittest.TestSuite):
            tests.extend(_flatten(value))
        elif isinstance(value, unittest.case.TestCase):
            tests.append(value)
        else:
            raise P12GateError("P12 test inventory contains an unknown test type")
    return tests


def run_p12_tests(root: Path, *, stream: TextIO) -> dict[str, Any]:
    suite = unittest.defaultTestLoader.loadTestsFromNames(P12_TEST_MODULES)
    tests = _flatten(suite)
    failures = [test for test in tests if test.__class__.__name__ == "_FailedTest"]
    identifiers = tuple(test.id() for test in tests)
    if failures or len(set(identifiers)) != len(identifiers):
        raise P12GateError("P12 literal governance test inventory is invalid")
    if P12_TEST_COUNT <= 0 or len(identifiers) != P12_TEST_COUNT:
        raise P12GateError("P12 governance test count differs from the fixed inventory")
    result = run_suite(suite, stream=stream)
    if result.get("gate_passed") is not True or result.get("tests_run") != P12_TEST_COUNT:
        raise P12GateError("P12 governance test suite failed closed")
    return {
        **result,
        "suite": "p12_governance_suite",
        "module_inventory": list(P12_TEST_MODULES),
        "inventory_count": P12_TEST_COUNT,
    }


def current_p11_test_ids(root: Path) -> tuple[str, ...]:
    try:
        text = (root / "docs/p11r/acceptance.md").read_text(encoding="utf-8")
        section = text.split("## Exact current-tree P11 regression inventory", 1)[1]
        block = section.split("```text", 1)[1].split("```", 1)[0]
    except (OSError, UnicodeError, IndexError) as exc:
        raise P12GateError("P12 cannot load the exact current-tree P11 inventory") from exc
    identifiers = tuple(line.strip() for line in block.splitlines() if line.strip())
    if len(identifiers) != 100 or len(set(identifiers)) != 100:
        raise P12GateError("P12 current-tree P11 inventory is not exactly 100 tests")
    return identifiers


def run_current_p11_tests(root: Path, *, stream: TextIO) -> dict[str, Any]:
    identifiers = current_p11_test_ids(root)
    suite = unittest.defaultTestLoader.loadTestsFromNames(identifiers)
    loaded = tuple(test.id() for test in _flatten(suite))
    if loaded != identifiers:
        raise P12GateError("P12 current-tree P11 tests did not load one-for-one")
    result = run_suite(suite, stream=stream)
    if result.get("gate_passed") is not True or result.get("tests_run") != 100:
        raise P12GateError("P12 current-tree P11 regression failed closed")
    return {**result, "suite": "p12_current_tree_p11_regression", "inventory_count": 100}


def _read_result(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("suite") != expected:
        raise P12GateError("P12 subprocess test result identity is invalid")
    return value


def _quality(root: Path, temporary: Path) -> dict[str, Any]:
    python, environment = _prepare_python(temporary / "python-environment")
    for command in (
        [str(python), "-m", "ruff", "check", "src", "scripts", "tests"],
        [str(python), "-m", "ruff", "format", "--check", "src", "scripts", "tests"],
        [str(python), "-m", "mypy", "src", "scripts", "tests"],
    ):
        _run(command, cwd=root, environment=environment, timeout=900)
    p11_path = temporary / "current-p11.json"
    _run(
        [
            str(python),
            "-B",
            "-m",
            "scripts.run_p12_toolchain",
            "--scope",
            "current-p11-tests",
            "--json-output",
            str(p11_path),
        ],
        cwd=root,
        environment=environment,
        timeout=900,
    )
    p12_path = temporary / "p12.json"
    _run(
        [
            str(python),
            "-B",
            "-m",
            "scripts.run_p12_toolchain",
            "--scope",
            "p12-tests",
            "--json-output",
            str(p12_path),
        ],
        cwd=root,
        environment=environment,
        timeout=900,
    )
    return {
        "python_lock": PYTHON_LOCK[0],
        "hash_locked_environment": True,
        "ruff_lint": "passed",
        "ruff_format": "passed",
        "mypy": "passed",
        "current_tree_p11": _read_result(p11_path, "p12_current_tree_p11_regression"),
        "p12": _read_result(p12_path, "p12_governance_suite"),
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
        "node_version": NODE_VERSION,
        "node_engine": NODE_ENGINE,
        "npm_version": NPM_VERSION,
        "package_manager": PACKAGE_MANAGER,
    }


def run_tests(root: Path, temporary: Path) -> dict[str, Any]:
    return {"quality": _quality(root, temporary / "quality"), "studio": _studio(temporary)}


def _public_boundary(root: Path) -> dict[str, object]:
    output = _run(
        [sys.executable, "-B", "scripts/check_public_boundary.py", "."],
        cwd=root,
        timeout=300,
    )
    value = json.loads(output)
    if not isinstance(value, dict) or value.get("gate") != "public_boundary_clean":
        raise P12GateError("P12 public-boundary result is invalid")
    return value


def static_gates(root: Path, *, mode: str) -> dict[str, Any]:
    return {
        "repository": check_repository(root, mode=mode),
        "ci_policy": check_ci_policy(root),
        "migrations": check_migrations(root),
        "rebaseline": check_rebaseline(root),
        "provenance": check_provenance(root),
        "public_boundary": _public_boundary(root),
    }


def _json_from_make(output: str) -> dict[str, Any]:
    start = output.find("{")
    if start < 0:
        raise P12GateError("Accepted P11R aggregate emitted no JSON")
    value = json.loads(output[start:])
    if not isinstance(value, dict) or value.get("gate") != "p11r_all":
        raise P12GateError("Accepted P11R aggregate result is invalid")
    return value


def replay_accepted_p11r(root: Path, temporary: Path) -> dict[str, Any]:
    checkout = temporary / "accepted-p11r"
    temporary.mkdir(parents=True, exist_ok=True)
    _run(
        ["git", "clone", "--quiet", "--shared", "--no-checkout", str(root), str(checkout)],
        cwd=temporary,
        timeout=120,
    )
    _run(
        ["git", "checkout", "--quiet", "-B", P11R_BRANCH, BASE_COMMIT],
        cwd=checkout,
        timeout=60,
    )
    _run(["git", "branch", "--force", "main", ACCEPTED_P11], cwd=checkout, timeout=60)
    _run(
        ["git", "update-ref", "refs/remotes/origin/main", ACCEPTED_P11],
        cwd=checkout,
        timeout=60,
    )
    if _run(["git", "status", "--porcelain"], cwd=checkout).strip():
        raise P12GateError("Accepted P11R temporary checkout is not clean")
    result = _json_from_make(_run(["make", "p11r-check"], cwd=checkout, timeout=7_200))
    accepted = result.get("accepted_p11")
    if not isinstance(accepted, dict) or accepted.get("status") != "passed":
        raise P12GateError("Accepted P11 exact-object replay did not pass through P11R")
    current = result.get("current_ci")
    if not isinstance(current, dict) or current.get("status") != "passed":
        raise P12GateError("Accepted P11R current CI replay did not pass")
    compose = result.get("compose_runtime")
    if not isinstance(compose, dict) or compose.get("cleanup_residue_count") != 0:
        raise P12GateError("Accepted P11R replay left Compose residue")
    return {
        "status": "passed",
        "object": BASE_COMMIT,
        "tree": git(root, "rev-parse", f"{BASE_COMMIT}^{{tree}}"),
        "branch": P11R_BRANCH,
        "historical_main": ACCEPTED_P11,
        "command": "make p11r-check",
        "accepted_p11_tests": accepted["tests"],
        "current_tree_p11_tests": current["tests"]["quality"]["current_tree_p11"],
        "p11r_governance_tests": current["tests"]["quality"]["p11r"],
        "cleanup_residue_count": 0,
        "temporary_checkout": True,
        "repository_ref_mutation_count": 0,
    }


def run_implementation(root: Path) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "gate": "p12_implementation",
        "status": "passed",
        "gates": static_gates(root, mode="implementation"),
    }


def run_ci(root: Path, temporary: Path) -> dict[str, Any]:
    mode = "final" if (root / SUMMARY_PATH).exists() else "ci"
    result = {
        "schema_version": 1,
        "gate": "p12_current_ci",
        "status": "passed",
        "mode": "final_candidate" if mode == "final" else "implementation",
        "tests": run_tests(root, temporary / "tests"),
        "gates": static_gates(root, mode=mode),
        "historical_replay": replay_accepted_p11r(root, temporary / "historical"),
        "cleanup_residue_count": 0,
    }
    if mode == "final":
        from scripts.collect_p12_evidence import validate_summary

        result["committed_summary"] = validate_summary(root)
    return result


def _verify_locked_file(root: Path, identity: tuple[str, str, str]) -> None:
    relative, blob, digest = identity
    path = root / relative
    if path.is_symlink() or not stat.S_ISREG(os.lstat(path).st_mode):
        raise P12GateError("P12 preflight locked input is not a regular file")
    if git(root, "ls-tree", BASE_COMMIT, relative) != f"100644 blob {blob}\t{relative}":
        raise P12GateError("P12 preflight locked input Git mode drifted")
    if git(root, "rev-parse", f"{BASE_COMMIT}:{relative}") != blob:
        raise P12GateError("P12 preflight locked input base blob drifted")
    if git(root, "hash-object", relative) != blob:
        raise P12GateError("P12 preflight locked input working blob drifted")
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise P12GateError("P12 preflight locked input SHA-256 drifted")


def ca_fallback_allowed(error: BaseException) -> bool:
    if isinstance(error, ssl.SSLCertVerificationError):
        return True
    return isinstance(error, urllib.error.URLError) and isinstance(
        error.reason, ssl.SSLCertVerificationError
    )


def _tls_probe(url: str, certifi_bundle: Path | None = None) -> str:
    context = (
        ssl.create_default_context()
        if certifi_bundle is None
        else ssl.create_default_context(cafile=str(certifi_bundle))
    )
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "dc-p12"})
    try:
        with urllib.request.urlopen(request, timeout=30, context=context):
            pass
    except urllib.error.HTTPError:
        pass
    return "system_default" if certifi_bundle is None else "locked_certifi"


def _package_report(root: Path, python: Path, environment: dict[str, str]) -> dict[str, Any]:
    program = r"""import hashlib
import importlib.metadata
import json
import os
import pathlib
import re
import stat
import sys
import tomllib
from packaging.requirements import Requirement
from packaging.version import Version

pyproject = pathlib.Path(sys.argv[1])
lock = pathlib.Path(sys.argv[2])
project = tomllib.loads(pyproject.read_text(encoding="utf-8"))
declared = list(project["project"].get("dependencies", []))
for values in project["project"].get("optional-dependencies", {}).values():
    declared.extend(values)
direct = {}
for raw in declared:
    requirement = Requirement(raw)
    installed = Version(importlib.metadata.version(requirement.name))
    if installed not in requirement.specifier:
        raise SystemExit("direct dependency specifier mismatch")
    direct[requirement.name] = {
        "declared": str(requirement.specifier),
        "installed": str(installed),
    }
logical = re.sub(r"\\\n\s*", " ", lock.read_text(encoding="utf-8"))
locked = {}
for line in logical.splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        continue
    match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s]+)", stripped)
    if match is None:
        raise SystemExit("unparseable locked requirement")
    requirement = Requirement(f"{match.group(1)}=={match.group(2)}")
    declared_version = Version(match.group(2))
    installed_version = Version(importlib.metadata.version(requirement.name))
    if installed_version != declared_version:
        raise SystemExit("locked dependency version mismatch")
    locked[requirement.name] = str(installed_version)
import certifi
bundle = pathlib.Path(certifi.where())
metadata = os.lstat(bundle)
if bundle.is_symlink() or not stat.S_ISREG(metadata.st_mode):
    raise SystemExit("certifi bundle is not a regular non-symlink file")
print(json.dumps({
    "direct": direct,
    "locked": locked,
    "certifi_bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
    "certifi_bundle": str(bundle),
}, sort_keys=True))"""
    output = _run(
        [str(python), "-I", "-c", program, str(root / PYPROJECT[0]), str(root / PYTHON_LOCK[0])],
        cwd=root,
        environment=environment,
        timeout=300,
    )
    report = json.loads(output)
    if not isinstance(report, dict):
        raise P12GateError("P12 preflight package report is invalid")
    locked = report.get("locked")
    direct = report.get("direct")
    bundle = report.get("certifi_bundle")
    if (
        not isinstance(locked, dict)
        or not isinstance(direct, dict)
        or not isinstance(bundle, str)
        or locked.get("certifi") != CERTIFI_VERSION
        or locked.get("packaging") != PACKAGING_VERSION
        or report.get("certifi_bundle_sha256") != CERTIFI_BUNDLE_SHA256
        or not direct
    ):
        raise P12GateError("P12 preflight locked or direct package identity is invalid")
    lock_text = (root / PYTHON_LOCK[0]).read_text(encoding="utf-8")
    if (
        f"certifi=={CERTIFI_VERSION} --hash=sha256:{CERTIFI_WHEEL_HASH}" not in lock_text
        or f"packaging=={PACKAGING_VERSION} " not in lock_text
    ):
        raise P12GateError("P12 preflight accepted tool wheel identity drifted")
    return report


def _gh_json(arguments: list[str], *, cwd: Path) -> Any:
    output = _run(["gh", *arguments], cwd=cwd, timeout=180)
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise P12GateError("P12 preflight GitHub response is invalid") from exc


def _expected_package_inventory(root: Path, heading: str) -> list[dict[str, Any]]:
    text = (root / "docs/p12/acceptance.md").read_text(encoding="utf-8")
    try:
        section = text.split(f"{heading} subject:", 1)[1]
        if heading == "Runtime":
            section = section.split("Studio subject:", 1)[0]
        else:
            section = section.split("The start, evidence-preflight", 1)[0]
    except IndexError as exc:
        raise P12GateError("P12 protected GHCR inventory table is unavailable") from exc
    result: list[dict[str, Any]] = []
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4 or not cells[0].isdigit():
            continue
        result.append(
            {
                "id": int(cells[0]),
                "name": cells[1],
                "tags": [] if cells[2] == "none" else [cells[2]],
                "created_at": cells[3],
                "updated_at": cells[3],
            }
        )
    if len(result) != 14:
        raise P12GateError("P12 protected GHCR inventory table is not exactly 14 versions")
    return result


def validate_package_inventory(actual: object, expected: list[dict[str, Any]]) -> None:
    pages = actual
    if isinstance(pages, list) and pages and all(isinstance(page, list) for page in pages):
        pages = [item for page in pages for item in page]
    if not isinstance(pages, list):
        raise P12GateError("P12 GHCR version response is invalid")
    canonical: list[dict[str, Any]] = []
    for value in pages:
        if not isinstance(value, dict):
            raise P12GateError("P12 GHCR version entry is invalid")
        metadata = value.get("metadata")
        container = metadata.get("container") if isinstance(metadata, dict) else None
        tags = container.get("tags") if isinstance(container, dict) else None
        canonical.append(
            {
                "id": value.get("id"),
                "name": value.get("name"),
                "tags": tags,
                "created_at": value.get("created_at"),
                "updated_at": value.get("updated_at"),
            }
        )
    if canonical != expected:
        raise P12GateError("P12 protected GHCR version inventory drifted")


def _github_and_ghcr(root: Path, *, implementation_head: str, ci_run_id: int) -> dict[str, Any]:
    _run(["gh", "auth", "status", "--hostname", "github.com"], cwd=root, timeout=60)
    repository = "jeremyliu1220/digital-colleagues"
    run = _gh_json(["api", f"repos/{repository}/actions/runs/{ci_run_id}"], cwd=root)
    if not isinstance(run, dict):
        raise P12GateError("P12 implementation-head CI response is invalid")
    pull_requests = run.get("pull_requests")
    if (
        run.get("id") != ci_run_id
        or run.get("head_sha") != implementation_head
        or run.get("event") != "pull_request"
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
        or run.get("name") != "CI"
        or run.get("path") != ".github/workflows/ci.yml"
        or run.get("head_branch") != "codex/p12-public-pilot-continuity-rebaseline-v2"
        or not isinstance(pull_requests, list)
        or len(pull_requests) != 1
        or not isinstance(pull_requests[0], dict)
        or not isinstance(pull_requests[0].get("number"), int)
    ):
        raise P12GateError("P12 implementation-head CI identity or lifecycle is invalid")
    jobs = _gh_json(
        ["api", f"repos/{repository}/actions/runs/{ci_run_id}/jobs?per_page=100"], cwd=root
    )
    values = jobs.get("jobs") if isinstance(jobs, dict) else None
    if not isinstance(values, list):
        raise P12GateError("P12 implementation-head CI jobs response is invalid")
    if any(
        not isinstance(value, dict) or value.get("conclusion") not in {"success", "skipped"}
        for value in values
    ):
        raise P12GateError("P12 implementation-head CI contains a failed required job")
    required = [
        value
        for value in values
        if isinstance(value, dict)
        and value.get("name") == "Current P12 governance non-publishing verification"
    ]
    if len(required) != 1 or required[0].get("conclusion") != "success":
        raise P12GateError("P12 required implementation-head CI job did not pass exactly once")
    subjects = ("digital-colleagues-runtime", "digital-colleagues-studio")
    inventories: dict[str, int] = {}
    for subject, heading in zip(subjects, ("Runtime", "Studio"), strict=True):
        metadata = _gh_json(["api", f"/users/jeremyliu1220/packages/container/{subject}"], cwd=root)
        if (
            not isinstance(metadata, dict)
            or metadata.get("name") != subject
            or metadata.get("package_type") != "container"
            or metadata.get("visibility") != "public"
        ):
            raise P12GateError("P12 protected GHCR subject identity drifted")
        versions = _gh_json(
            [
                "api",
                "--paginate",
                "--slurp",
                f"/users/jeremyliu1220/packages/container/{subject}/versions?per_page=100",
            ],
            cwd=root,
        )
        expected = _expected_package_inventory(root, heading)
        validate_package_inventory(versions, expected)
        inventories[subject] = len(expected)
    digests = (
        (
            "digital-colleagues-runtime",
            "sha256:41567ba87a088944cf9a2c17b9b0f4359554c66b2ec1f6d52db46067e1ab9092",
        ),
        (
            "digital-colleagues-studio",
            "sha256:b7dd4c2b35922ec31a9b38c15316283706a9aab0ffab2101a18f7bf106165f2e",
        ),
        (
            "digital-colleagues-runtime",
            "sha256:a5bb41bdb85bf7b5a75dc79967e26943c098b024b64fdd345f5b4c6f4688991d",
        ),
        (
            "digital-colleagues-studio",
            "sha256:7791d80d9fa464bbd1574601deba5a30ca6d980dab8c8275c24c117fae81e4c9",
        ),
    )
    for subject, digest in digests:
        completed = subprocess.run(
            [
                "docker",
                "buildx",
                "imagetools",
                "inspect",
                f"ghcr.io/jeremyliu1220/{subject}@{digest}",
                "--raw",
            ],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=180,
            check=False,
        )
        if (
            completed.returncode != 0
            or f"sha256:{hashlib.sha256(completed.stdout).hexdigest()}" != digest
        ):
            raise P12GateError("P12 protected GHCR manifest lookup or digest failed")
    return {
        "github": {
            "repository": repository,
            "authentication": "active_read_only",
            "read_packages": "passed",
        },
        "ci": {
            "run_id": ci_run_id,
            "head_sha": implementation_head,
            "event": "pull_request",
            "status": "completed",
            "conclusion": "success",
            "workflow_path": ".github/workflows/ci.yml",
            "pull_request_number": pull_requests[0].get("number"),
            "required_job_count": 1,
        },
        "ghcr": {
            "subjects": list(subjects),
            "version_counts": inventories,
            "protected_manifest_count": len(digests),
            "status": "passed",
        },
    }


def write_preflight_receipt(directory: Path, receipt: dict[str, Any]) -> tuple[Path, str]:
    if not directory.is_absolute() or ROOT == directory or ROOT in directory.parents:
        raise P12GateError("P12 preflight receipt directory must be outside the repository")
    if directory.is_symlink() or not directory.is_dir():
        raise P12GateError("P12 preflight receipt directory is invalid")
    if stat.S_IMODE(os.stat(directory).st_mode) != 0o700:
        raise P12GateError("P12 preflight receipt directory mode must be 0700")
    if any(directory.iterdir()):
        raise P12GateError("P12 preflight receipt directory must be newly empty")
    encoded = (
        json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    destination = directory / "p12-preflight-receipt.json"
    descriptor, temporary_name = tempfile.mkstemp(prefix=".p12-preflight-", dir=directory)
    try:
        os.chmod(temporary_name, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, destination)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise
    return destination, hashlib.sha256(encoded).hexdigest()


def run_evidence_preflight(
    root: Path, *, implementation_head: str, ci_run_id: str, receipt_directory: str
) -> dict[str, Any]:
    if not implementation_head or not ci_run_id.isdigit() or not receipt_directory:
        raise P12GateError("P12 preflight requires exact head, numeric run, and receipt directory")
    if implementation_head != git(root, "rev-parse", "HEAD"):
        raise P12GateError("P12 preflight implementation head is not exact HEAD")
    if (root / SUMMARY_PATH).exists():
        raise P12GateError("P12 preflight requires the summary to be absent")
    check_repository(root, mode="implementation")
    _verify_locked_file(root, PYPROJECT)
    _verify_locked_file(root, PYTHON_LOCK)
    before = git(root, "status", "--porcelain=v2", "--untracked-files=all")
    remote = _github_and_ghcr(
        root, implementation_head=implementation_head, ci_run_id=int(ci_run_id)
    )
    with tempfile.TemporaryDirectory(prefix="dc-p12-preflight-environment-") as value:
        temporary = Path(value)
        python, environment = _prepare_python(temporary / "python-environment")
        package_report = _package_report(root, python, environment)
        bundle_value = package_report.pop("certifi_bundle")
        if not isinstance(bundle_value, str):
            raise P12GateError("P12 certifi CA bundle identity is invalid")
        certifi_bundle = Path(bundle_value)
        tls: dict[str, str] = {}
        for host, url in (
            ("api.github.com", "https://api.github.com/"),
            ("ghcr.io", "https://ghcr.io/v2/"),
        ):
            try:
                tls[host] = _tls_probe(url)
            except (OSError, urllib.error.URLError) as exc:
                if not ca_fallback_allowed(exc):
                    raise P12GateError("P12 default TLS probe failed for a non-CA reason") from exc
                tls[host] = _tls_probe(url, certifi_bundle)
    if git(root, "status", "--porcelain=v2", "--untracked-files=all") != before:
        raise P12GateError("P12 preflight changed repository state")
    local_gates = run_implementation(root)
    receipt = {
        "schema_version": 1,
        "stage": "p12_evidence_preflight",
        "lifecycle": "pending_consumption",
        "repository": "jeremyliu1220/digital-colleagues",
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "acceptance_blob": ACCEPTANCE_BLOB,
        "implementation_head": implementation_head,
        "implementation_tree": git(root, "rev-parse", "HEAD^{tree}"),
        "ci": remote["ci"],
        "github": remote["github"],
        "ghcr": remote["ghcr"],
        "python": {
            "pyproject": {"blob": PYPROJECT[1], "sha256": PYPROJECT[2]},
            "lock": {"blob": PYTHON_LOCK[1], "sha256": PYTHON_LOCK[2]},
            "direct": package_report["direct"],
            "locked": package_report["locked"],
            "installed_version_api": "importlib.metadata.version",
            "comparison": "packaging.version.Version",
            "certifi_bundle_sha256": CERTIFI_BUNDLE_SHA256,
        },
        "tls": {
            "hosts": tls,
            "verification": "certificate_and_hostname_verified",
            "fallback": "locked_certifi_only_after_certificate_failure",
        },
        "local_gates": local_gates,
        "preflight_environment_cleanup": "passed",
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "nonce": secrets.token_hex(32),
    }
    _, digest = write_preflight_receipt(Path(receipt_directory), receipt)
    return {
        "schema_version": 1,
        "gate": "p12_evidence_preflight",
        "status": "passed",
        "receipt_name": "p12-preflight-receipt.json",
        "receipt_sha256": digest,
        "implementation_head": implementation_head,
        "ci_run_id": int(ci_run_id),
        "repository_mutation_count": 0,
        "remote_mutation_count": 0,
        "publication_count": 0,
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
            "test",
            "implementation",
            "ci",
            "final",
            "evidence-preflight",
            "current-p11-tests",
            "p12-tests",
            "accepted-p11r",
        ),
        default="implementation",
    )
    parser.add_argument("--json-output")
    parser.add_argument("--implementation-head", default="")
    parser.add_argument("--ci-run-id", default="")
    parser.add_argument("--receipt-directory", default="")
    args = parser.parse_args(argv)
    try:
        if args.scope == "current-p11-tests":
            result = run_current_p11_tests(ROOT, stream=sys.stderr)
        elif args.scope == "p12-tests":
            result = run_p12_tests(ROOT, stream=sys.stderr)
        elif args.scope == "test":
            result = run_p12_tests(ROOT, stream=sys.stderr)
        elif args.scope == "implementation":
            result = run_implementation(ROOT)
        elif args.scope == "evidence-preflight":
            result = run_evidence_preflight(
                ROOT,
                implementation_head=args.implementation_head,
                ci_run_id=args.ci_run_id,
                receipt_directory=args.receipt_directory,
            )
        else:
            with tempfile.TemporaryDirectory(prefix="dc-p12-toolchain-") as value:
                temporary = Path(value)
                if args.scope == "accepted-p11r":
                    result = replay_accepted_p11r(ROOT, temporary)
                elif args.scope == "final":
                    result = run_ci(ROOT, temporary)
                    if result.get("mode") != "final_candidate":
                        raise P12GateError("P12 final scope requires the summary-only tip")
                else:
                    result = run_ci(ROOT, temporary)
        _emit(result, args.json_output)
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
        P12GateError,
    ) as exc:
        print(f"P12 toolchain failed: {_safe(str(exc))}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
