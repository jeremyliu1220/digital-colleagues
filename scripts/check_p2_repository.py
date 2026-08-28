# SPDX-License-Identifier: Apache-2.0

"""Validate the current P2 repository boundary without reapplying P1 absence rules."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from pathlib import Path

LICENSE_DIGEST = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
P1_SUMMARY_DIGEST = "1b2650cbf90c8e50b05dc193906bed1d6c8fac37aa6b669b88605b572c05ecaa"
REQUIRED_FILES = {
    "artifacts/p1/summary.json",
    "artifacts/p2/summary.json",
    "docs/p2/acceptance.md",
    "provenance/p2-migration-receipt.json",
    "scripts/collect_p2_evidence.py",
    "scripts/check_p2_architecture.py",
    "scripts/check_p2_core_contracts.py",
    "scripts/check_p2_provenance.py",
    "scripts/check_p2_repository.py",
    "scripts/run_p2_toolchain.py",
    "src/digital_colleagues/core/__init__.py",
    "src/digital_colleagues/core/audit.py",
    "src/digital_colleagues/core/authority.py",
    "src/digital_colleagues/core/common.py",
    "src/digital_colleagues/core/effects.py",
    "src/digital_colleagues/core/errors.py",
    "src/digital_colleagues/core/namespace.py",
    "src/digital_colleagues/core/ports.py",
    "src/digital_colleagues/core/principals.py",
    "src/digital_colleagues/core/runtime.py",
    "src/digital_colleagues/core/serialization.py",
    "src/digital_colleagues/core/work.py",
    "src/digital_colleagues/governance/__init__.py",
    "src/digital_colleagues/governance/approvals.py",
}
FORBIDDEN_P3_PATHS = {
    "compose.yaml",
    "docker-compose.yml",
    "migrations",
    "src/digital_colleagues/adapters",
    "src/digital_colleagues/api",
    "src/digital_colleagues/application",
    "src/digital_colleagues/worker",
}


class RepositoryError(RuntimeError):
    """The repository is outside the accepted P2 current-tree boundary."""


def check_p2_repository(root: Path) -> dict[str, object]:
    missing = sorted(path for path in REQUIRED_FILES if not (root / path).is_file())
    if missing:
        raise RepositoryError("required P2 files are missing: " + ", ".join(missing))
    present_p3 = sorted(path for path in FORBIDDEN_P3_PATHS if (root / path).exists())
    if present_p3:
        raise RepositoryError("P3 paths are forbidden during P2: " + ", ".join(present_p3))

    try:
        metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise RepositoryError("Python project metadata is unreadable") from exc
    project = metadata.get("project")
    if not isinstance(project, dict):
        raise RepositoryError("Python project metadata is incomplete")
    if project.get("requires-python") != ">=3.12" or project.get("dependencies") != []:
        raise RepositoryError("P2 Python version or runtime dependency boundary changed")

    license_digest = hashlib.sha256((root / "LICENSE").read_bytes()).hexdigest()
    if license_digest != LICENSE_DIGEST:
        raise RepositoryError("the reviewed Apache-2.0 license changed")
    p1_digest = hashlib.sha256((root / "artifacts/p1/summary.json").read_bytes()).hexdigest()
    if p1_digest != P1_SUMMARY_DIGEST:
        raise RepositoryError("the accepted P1 evidence artifact changed")

    try:
        p2_summary = json.loads((root / "artifacts/p2/summary.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RepositoryError("the P2 evidence artifact is unreadable") from exc
    if not isinstance(p2_summary, dict) or p2_summary.get("status") not in {
        "review_required",
        "passed",
    }:
        raise RepositoryError("the P2 evidence status is invalid")

    return {
        "schema_version": 1,
        "gate": "p2_repository_clean",
        "required_file_count": len(REQUIRED_FILES),
        "p3_paths_present": len(present_p3),
        "requires_python": project["requires-python"],
        "runtime_dependency_count": len(project["dependencies"]),
        "license_digest": "sha256:" + license_digest,
        "p1_summary_digest": "sha256:" + p1_digest,
        "p1_historical_gate_preserved": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the P2 current repository.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_p2_repository(Path(arguments.root))
    except (OSError, RepositoryError) as exc:
        print(f"P2 repository check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
