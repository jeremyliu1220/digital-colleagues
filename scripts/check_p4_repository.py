# SPDX-License-Identifier: Apache-2.0

"""Validate the P4 tree, retained history, and generated-residue boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import cast

BASE_COMMIT = "660a191b03472ab090fcc19c1e9fffda6b6ca9fd"
BRANCH = "codex/p4-studio-golden-path"
REQUIRED_FILES = {
    ".dockerignore",
    "Dockerfile",
    "compose.yaml",
    "docs/p4/acceptance.md",
    "docs/p4/golden-path.md",
    "migrations/004_local_authentication.sql",
    "migrations/005_evaluation_observations.sql",
    "provenance/p4-migration-receipt.json",
    "requirements/p4.lock",
    "scripts/check_p4_architecture.py",
    "scripts/check_p4_authentication.py",
    "scripts/check_p4_compose.py",
    "scripts/check_p4_compose_runtime.py",
    "scripts/check_p4_golden_path.py",
    "scripts/check_p4_migrations.py",
    "scripts/check_p4_provenance.py",
    "scripts/check_p4_repository.py",
    "scripts/check_p4_studio.py",
    "scripts/collect_p4_evidence.py",
    "scripts/run_p4_toolchain.py",
    "scripts/run_p4_unittest_suite.py",
    "src/digital_colleagues/adapters/sqlite/p4_store.py",
    "src/digital_colleagues/api/p4_app.py",
    "src/digital_colleagues/application/p4_contracts.py",
    "src/digital_colleagues/application/p4_ports.py",
    "src/digital_colleagues/application/p4_services.py",
    "src/digital_colleagues/local/operator.py",
    "src/digital_colleagues/local/runtime.py",
    "src/digital_colleagues/local/security.py",
    "src/digital_colleagues/local/worker.py",
    "studio/Dockerfile",
    "studio/nginx.conf",
    "studio/src/studioContract.ts",
    "tests/p4/test_authentication.py",
    "tests/p4/test_metrics.py",
    "tests/p4/test_studio_golden_path.py",
    "tests/p4/test_worker_authority.py",
}
FORBIDDEN_PARTS = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "coverage",
    "dist",
    "node_modules",
}
FORBIDDEN_SUFFIXES = (".sqlite", ".sqlite-wal", ".sqlite-shm", ".db", ".log", ".coverage")


class RepositoryError(RuntimeError):
    """The current tree does not satisfy the fixed P4 repository contract."""


def _git(root: Path, *arguments: str, text: bool = True) -> str | bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=text,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryError("Git history inspection failed")
    return cast(str | bytes, completed.stdout)


def _historical_paths(root: Path) -> tuple[str, ...]:
    output = _git(root, "ls-tree", "-r", "--name-only", BASE_COMMIT)
    assert isinstance(output, str)
    protected = []
    for path in output.splitlines():
        if path.startswith(("docs/p0/", "docs/p1/", "docs/p2/", "docs/p3/")):
            protected.append(path)
        elif path.startswith(("artifacts/p0/", "artifacts/p1/", "artifacts/p2/", "artifacts/p3/")):
            protected.append(path)
        elif path.startswith("provenance/"):
            protected.append(path)
        elif path in {
            "migrations/001_initial.sql",
            "migrations/002_runtime_indexes.sql",
            "migrations/003_timer_triggers.sql",
        }:
            protected.append(path)
    return tuple(sorted(protected))


def _require_history_unchanged(root: Path) -> int:
    protected = _historical_paths(root)
    for path in protected:
        document = root / path
        if not document.is_file():
            raise RepositoryError("a protected P0-P3 historical file is missing")
        baseline = _git(root, "show", f"{BASE_COMMIT}:{path}", text=False)
        assert isinstance(baseline, bytes)
        if document.read_bytes() != baseline:
            raise RepositoryError("a protected P0-P3 historical file changed")
    return len(protected)


def check_repository(root: Path) -> dict[str, object]:
    root = root.resolve()
    top = _git(root, "rev-parse", "--show-toplevel")
    branch = _git(root, "branch", "--show-current")
    base = _git(root, "rev-parse", "main")
    assert isinstance(top, str) and isinstance(branch, str) and isinstance(base, str)
    if Path(top.strip()).resolve() != root:
        raise RepositoryError("P4 repository root is not exact")
    if branch.strip() != BRANCH or base.strip() != BASE_COMMIT:
        raise RepositoryError("P4 branch or accepted base commit drifted")
    missing = sorted(path for path in REQUIRED_FILES if not (root / path).is_file())
    if missing:
        raise RepositoryError("required P4 files are missing")
    protected_count = _require_history_unchanged(root)
    residue: list[str] = []
    for document in root.rglob("*"):
        relative = document.relative_to(root)
        if relative.parts[:1] == (".git",):
            continue
        if any(part in FORBIDDEN_PARTS for part in relative.parts):
            residue.append(relative.as_posix())
        elif document.is_file() and document.name.endswith(FORBIDDEN_SUFFIXES):
            residue.append(relative.as_posix())
    if residue:
        raise RepositoryError("runtime, credential, or build residue is present")
    compose_digest = "sha256:" + hashlib.sha256((root / "compose.yaml").read_bytes()).hexdigest()
    return {
        "schema_version": 1,
        "gate": "p4_repository_clean",
        "base_commit": BASE_COMMIT,
        "branch": BRANCH,
        "historical_file_count": protected_count,
        "required_file_count": len(REQUIRED_FILES),
        "residue_count": 0,
        "compose_digest": compose_digest,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the P4 repository boundary.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_repository(Path(arguments.root))
    except (OSError, RepositoryError) as exc:
        print(f"P4 repository check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
