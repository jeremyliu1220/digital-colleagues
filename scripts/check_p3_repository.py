# SPDX-License-Identifier: Apache-2.0

"""Validate the P3 current tree while pinning historical accepted evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from pathlib import Path

P2_BASE_COMMIT = "37fa1c3d21440130fcbeeaacf0534e445afeb343"
HISTORICAL_DIGESTS = {
    "artifacts/p0/source-fingerprint-after.json": "ccebc7f1e822a532c1620a4df8600e64bc19f683b1e69f7c5d0b3c1beb7c5790",
    "artifacts/p0/source-fingerprint-before.json": "ccebc7f1e822a532c1620a4df8600e64bc19f683b1e69f7c5d0b3c1beb7c5790",
    "artifacts/p0/summary.json": "6ed77892d8b078c73547a8bea56da5dd7a89970f142f5ab363bb8d5facea8f71",
    "artifacts/p1/summary.json": "1b2650cbf90c8e50b05dc193906bed1d6c8fac37aa6b669b88605b572c05ecaa",
    "artifacts/p2/parent-fingerprint-after.json": "3c97e05b45a6d5062544e552fc72d8a1306d2b9379cdd2a000edf8401638cb6d",
    "artifacts/p2/parent-fingerprint-before.json": "3c97e05b45a6d5062544e552fc72d8a1306d2b9379cdd2a000edf8401638cb6d",
    "artifacts/p2/summary.json": "0e5263ddbc00c98ddcbad91bca7d301b2d944a7113ce8edc419341b93c09604a",
}
REQUIRED_FILES = {
    "artifacts/p3/parent-fingerprint-before.json",
    "artifacts/p3/parent-fingerprint-after.json",
    "docs/p3/acceptance.md",
    "migrations/001_initial.sql",
    "migrations/002_runtime_indexes.sql",
    "migrations/manifest.json",
    "provenance/p3-migration-receipt.json",
    "requirements/p3.lock",
    "scripts/check_p3_architecture.py",
    "scripts/check_p3_golden_path.py",
    "scripts/check_p3_migrations.py",
    "scripts/check_p3_persistence.py",
    "scripts/check_p3_provenance.py",
    "scripts/check_p3_repository.py",
    "scripts/check_p3_runtime_contracts.py",
    "scripts/collect_p3_evidence.py",
    "scripts/run_p3_toolchain.py",
    "src/digital_colleagues/application/ports.py",
    "src/digital_colleagues/application/services.py",
    "src/digital_colleagues/adapters/sqlite/store.py",
    "src/digital_colleagues/adapters/intelligence/deterministic.py",
    "src/digital_colleagues/adapters/channel/reference.py",
    "src/digital_colleagues/api/app.py",
    "src/digital_colleagues/worker/runtime.py",
}
FORBIDDEN_SUFFIXES = (".sqlite", ".sqlite-wal", ".sqlite-shm", ".db", ".log", ".coverage")
FORBIDDEN_PARTS = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
}


class RepositoryError(RuntimeError):
    """The repository is outside the accepted P3 current-tree boundary."""


def check_repository(root: Path) -> dict[str, object]:
    missing = sorted(path for path in REQUIRED_FILES if not (root / path).is_file())
    if missing:
        raise RepositoryError("required P3 files are missing")
    for accepted_path, expected in HISTORICAL_DIGESTS.items():
        document = root / accepted_path
        if not document.is_file() or hashlib.sha256(document.read_bytes()).hexdigest() != expected:
            raise RepositoryError("accepted P0/P1/P2 evidence changed")
    residue: list[str] = []
    for document in root.rglob("*"):
        relative_path = document.relative_to(root)
        if relative_path.parts[:1] == (".git",):
            continue
        if any(part in FORBIDDEN_PARTS for part in relative_path.parts):
            residue.append(relative_path.as_posix())
        elif document.is_file() and document.name.endswith(FORBIDDEN_SUFFIXES):
            residue.append(relative_path.as_posix())
    if residue:
        raise RepositoryError("runtime or build residue is present")
    try:
        metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise RepositoryError("Python metadata is unreadable") from exc
    project = metadata.get("project")
    optional = project.get("optional-dependencies") if isinstance(project, dict) else None
    if not isinstance(project, dict) or project.get("requires-python") != ">=3.12":
        raise RepositoryError("P3 Python version boundary changed")
    if project.get("dependencies") != ["fastapi==0.141.1", "pydantic==2.13.5"]:
        raise RepositoryError("P3 direct runtime dependency pins changed")
    if not isinstance(optional, dict) or optional.get("dev") != [
        "httpx==0.28.1",
        "mypy==2.3.1",
        "ruff==0.16.4",
    ]:
        raise RepositoryError("P3 direct development dependency pins changed")
    return {
        "schema_version": 1,
        "gate": "p3_repository_clean",
        "p2_base_commit": P2_BASE_COMMIT,
        "required_file_count": len(REQUIRED_FILES),
        "historical_artifact_count": len(HISTORICAL_DIGESTS),
        "runtime_dependency_count": len(project["dependencies"]),
        "runtime_residue_count": 0,
        "requires_python": project["requires-python"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the P3 current repository.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_repository(Path(arguments.root))
    except (OSError, RepositoryError) as exc:
        print(f"P3 repository check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
