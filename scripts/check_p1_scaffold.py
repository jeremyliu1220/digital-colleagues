# SPDX-License-Identifier: Apache-2.0

"""Validate the P1 repository scaffold without asserting product behavior."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

LICENSE_DIGEST = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
REQUIRED_FILES = {
    ".editorconfig",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/dependabot.yml",
    ".github/pull_request_template.md",
    ".github/workflows/ci.yml",
    ".nvmrc",
    ".python-version",
    "artifacts/p1/summary.json",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "GOVERNANCE.md",
    "LICENSE",
    "Makefile",
    "NOTICE",
    "README.md",
    "SECURITY.md",
    "SUPPORT.md",
    "docs/development.md",
    "docs/licensing/contributing.md",
    "docs/licensing/file-map.json",
    "docs/licensing/notice-review.md",
    "docs/p1/acceptance.md",
    "pyproject.toml",
    "scripts/run_unittest_suite.py",
    "src/digital_colleagues/__init__.py",
    "src/digital_colleagues/py.typed",
    "studio/README.md",
    "studio/eslint.config.js",
    "studio/index.html",
    "studio/package-lock.json",
    "studio/package.json",
    "studio/src/App.test.tsx",
    "studio/src/App.tsx",
    "studio/src/main.tsx",
    "studio/src/styles.css",
    "studio/src/vite-env.d.ts",
    "studio/tsconfig.app.json",
    "studio/tsconfig.json",
    "studio/tsconfig.node.json",
    "studio/vite.config.ts",
    "tests/p1/test_evidence_gate.py",
}
EXPECTED_PYTHON_PACKAGE_FILES = {
    "src/digital_colleagues/__init__.py",
    "src/digital_colleagues/py.typed",
}
EXPECTED_STUDIO_SOURCE_FILES = {
    "studio/src/App.test.tsx",
    "studio/src/App.tsx",
    "studio/src/main.tsx",
    "studio/src/styles.css",
    "studio/src/vite-env.d.ts",
}
FORBIDDEN_P2_PATHS = {
    "compose.yaml",
    "docker-compose.yml",
    "migrations",
    "src/digital_colleagues/adapters",
    "src/digital_colleagues/api",
    "src/digital_colleagues/application",
    "src/digital_colleagues/core",
    "src/digital_colleagues/governance",
    "src/digital_colleagues/worker",
}


class ScaffoldError(RuntimeError):
    """A repository-relative P1 scaffold validation error."""


def _read_json(document: Path) -> dict[str, Any]:
    try:
        value = json.loads(document.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScaffoldError("a P1 JSON document is unreadable") from exc
    if not isinstance(value, dict):
        raise ScaffoldError("a P1 JSON document is not an object")
    return value


def _relative_files(root: Path, directory: str) -> set[str]:
    base = root / directory
    if not base.is_dir():
        return set()
    return {
        document.relative_to(root).as_posix() for document in base.rglob("*") if document.is_file()
    }


def check_scaffold(root: Path) -> dict[str, object]:
    if not root.is_dir():
        raise ScaffoldError("the scaffold root is unavailable")

    missing = sorted(path for path in REQUIRED_FILES if not (root / path).is_file())
    if missing:
        raise ScaffoldError("required P1 files are missing: " + ", ".join(missing))

    present_p2 = sorted(path for path in FORBIDDEN_P2_PATHS if (root / path).exists())
    if present_p2:
        raise ScaffoldError("P2 paths are forbidden in P1: " + ", ".join(present_p2))

    python_files = _relative_files(root, "src/digital_colleagues")
    if python_files != EXPECTED_PYTHON_PACKAGE_FILES:
        raise ScaffoldError("the P1 Python package contains files outside its empty boundary")
    studio_files = _relative_files(root, "studio/src")
    if studio_files != EXPECTED_STUDIO_SOURCE_FILES:
        raise ScaffoldError("the P1 Studio source is outside the reviewed shell boundary")

    license_digest = hashlib.sha256((root / "LICENSE").read_bytes()).hexdigest()
    if license_digest != LICENSE_DIGEST:
        raise ScaffoldError("LICENSE does not match the reviewed Apache-2.0 text")

    try:
        pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ScaffoldError("pyproject.toml is unreadable") from exc
    project = pyproject.get("project")
    if not isinstance(project, dict):
        raise ScaffoldError("pyproject.toml has no project table")
    if project.get("requires-python") != ">=3.12" or project.get("dependencies") != []:
        raise ScaffoldError("the Python version or empty runtime dependency boundary changed")
    if project.get("license") != "Apache-2.0":
        raise ScaffoldError("the Python package license is not Apache-2.0")
    runtime_dependencies = project["dependencies"]

    notice = (root / "NOTICE").read_text(encoding="utf-8")
    notice_review = (root / "docs/licensing/notice-review.md").read_text(encoding="utf-8")
    if "Digital Colleagues contributors" not in notice:
        raise ScaffoldError("NOTICE is missing the reviewed project attribution")
    if "## Decision and consequence" not in notice_review:
        raise ScaffoldError("the NOTICE operator review record is incomplete")

    studio_package = _read_json(root / "studio" / "package.json")
    if studio_package.get("private") is not True:
        raise ScaffoldError("the P1 Studio package must remain private")
    scripts = studio_package.get("scripts")
    if not isinstance(scripts, dict) or not {
        "build",
        "dev",
        "format:check",
        "lint",
        "test",
        "typecheck",
    }.issubset(scripts):
        raise ScaffoldError("the Studio package is missing a required development command")
    if "127.0.0.1" not in str(scripts.get("dev")):
        raise ScaffoldError("the Studio development server must bind to loopback")

    package_lock = _read_json(root / "studio" / "package-lock.json")
    if package_lock.get("lockfileVersion") != 3:
        raise ScaffoldError("the Studio lockfile version is not supported")
    if package_lock.get("packages", {}).get("", {}).get("version") != "0.0.0":
        raise ScaffoldError("the Studio root lock record does not match package metadata")

    workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    required_ci_terms = {
        "mypy src scripts tests",
        "ruff check src scripts tests",
        "npm run build",
        "npm run lint",
        "npm run typecheck",
        "npm test",
        "scripts/check_p1_scaffold.py",
        "scripts/check_public_boundary.py",
        "scripts/run_unittest_suite.py",
    }
    if any(term not in workflow for term in required_ci_terms):
        raise ScaffoldError("the CI workflow is missing a required P1 gate")

    return {
        "schema_version": 1,
        "gate": "p1_scaffold_contract_clean",
        "required_file_count": len(REQUIRED_FILES),
        "python_package_file_count": len(python_files),
        "studio_source_file_count": len(studio_files),
        "license_digest": "sha256:" + license_digest,
        "p2_product_paths_present": 0,
        "requires_python": project["requires-python"],
        "runtime_dependency_count": len(runtime_dependencies),
        "notice_operator_review_record_present": True,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the P1 clean-room scaffold contract.")
    parser.add_argument("root", nargs="?", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        result = check_scaffold(Path(arguments.root))
    except (OSError, ScaffoldError) as exc:
        print(f"P1 scaffold check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
