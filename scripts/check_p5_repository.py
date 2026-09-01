# SPDX-License-Identifier: Apache-2.0

"""Validate the fixed P5 branch/base, immutable acceptance, files, and residue."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p4_repository import check_repository as check_p4_repository

BASE_COMMIT = "259e5627c0a4d713934263efe18caf8c675a1669"
ACCEPTANCE_COMMIT = "705554c20f4e3e0407620f147cbbeb3425ec64f9"
BRANCH = "codex/p5-revisioned-colleague-builder"
REQUIRED_FILES = {
    "docs/adr/0004-revisioned-colleague-policy-model.md",
    "docs/p5/acceptance.md",
    "docs/p5/golden-path.md",
    "migrations/006_revisioned_colleague_builder.sql",
    "provenance/p5-migration-receipt.json",
    "scripts/check_p5_architecture.py",
    "scripts/check_p5_builder.py",
    "scripts/check_p5_compose.py",
    "scripts/check_p5_compose_runtime.py",
    "scripts/check_p5_golden_path.py",
    "scripts/check_p5_migrations.py",
    "scripts/check_p5_policy.py",
    "scripts/check_p5_provenance.py",
    "scripts/check_p5_repository.py",
    "scripts/check_p5_studio.py",
    "scripts/collect_p5_evidence.py",
    "scripts/run_p5_toolchain.py",
    "scripts/run_p5_unittest_suite.py",
    "src/digital_colleagues/adapters/sqlite/p5_store.py",
    "src/digital_colleagues/api/p5_app.py",
    "src/digital_colleagues/application/p5_contracts.py",
    "src/digital_colleagues/application/p5_ports.py",
    "src/digital_colleagues/application/p5_services.py",
    "src/digital_colleagues/core/builder.py",
    "src/digital_colleagues/core/policy.py",
    "src/digital_colleagues/governance/policy.py",
    "tests/p5/test_builder.py",
    "tests/p5/test_migrations.py",
    "tests/p5/test_policy.py",
}


class RepositoryError(RuntimeError):
    """The current tree does not satisfy the fixed P5 repository contract."""


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryError("Git history inspection failed")
    return completed.stdout.strip()


def _same_as_commit(root: Path, commit: str, relative: str) -> bool:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0 and (root / relative).read_bytes() == completed.stdout


def check_repository(root: Path) -> dict[str, object]:
    root = root.resolve()
    prior = check_p4_repository(root)
    branch = _git(root, "branch", "--show-current")
    head = _git(root, "rev-parse", "HEAD")
    merge_base = _git(root, "merge-base", "HEAD", BASE_COMMIT)
    if branch != BRANCH:
        raise RepositoryError("P5 work must remain on the fixed development branch")
    if merge_base != BASE_COMMIT:
        raise RepositoryError("P5 merge-base drifted from the accepted P4 main baseline")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ACCEPTANCE_COMMIT, "HEAD"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if ancestor.returncode != 0:
        raise RepositoryError("the fixed P5 acceptance commit is not an ancestor")
    for relative in (
        "docs/p5/acceptance.md",
        "docs/p5/golden-path.md",
        "docs/adr/0004-revisioned-colleague-policy-model.md",
    ):
        if not _same_as_commit(root, ACCEPTANCE_COMMIT, relative):
            raise RepositoryError("a fixed P5 acceptance document changed after its commit")
    missing = sorted(relative for relative in REQUIRED_FILES if not (root / relative).is_file())
    if missing:
        raise RepositoryError("required P5 files are missing")
    migration_digest = (
        "sha256:"
        + hashlib.sha256(
            (root / "migrations/006_revisioned_colleague_builder.sql").read_bytes()
        ).hexdigest()
    )
    return {
        "schema_version": 1,
        "gate": "p5_repository_clean",
        "branch": branch,
        "head_commit": head,
        "base_commit": BASE_COMMIT,
        "merge_base": merge_base,
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "acceptance_documents_immutable": True,
        "required_file_count": len(REQUIRED_FILES),
        "residue_count": prior["residue_count"],
        "migration_006_digest": migration_digest,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the P5 repository boundary.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_repository(Path(arguments.root))
    except (OSError, RepositoryError) as exc:
        print(f"P5 repository check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
