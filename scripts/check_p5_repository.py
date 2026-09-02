# SPDX-License-Identifier: Apache-2.0

"""Validate accepted P5 ancestry, immutable files, retained history, and residue."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p4_repository import check_repository as check_p4_repository

BASE_COMMIT = "259e5627c0a4d713934263efe18caf8c675a1669"
ACCEPTANCE_COMMIT = "705554c20f4e3e0407620f147cbbeb3425ec64f9"
# The evidence writer imports these development-boundary values. General repository
# health checks trust the accepted P5 commit below and never a checkout's branch name.
BRANCH = "codex/p5-revisioned-colleague-builder"
ACCEPTED_P5_COMMIT = "60495d31e0578e054db7e752e0ebb268711585d7"
ACCEPTED_P5_IMMUTABLE_PATHS = (
    "artifacts/p5/summary.json",
    "docs/p5/acceptance.md",
    "migrations/006_revisioned_colleague_builder.sql",
    "provenance/p5-migration-receipt.json",
)
ACCEPTANCE_DOCUMENT_PATHS = (
    "docs/p5/acceptance.md",
    "docs/p5/golden-path.md",
    "docs/adr/0004-revisioned-colleague-policy-model.md",
)
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


def _require_commit(root: Path, commit: str) -> None:
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryError("the accepted P5 commit is unavailable")


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        raise RepositoryError("Git history inspection failed")
    return completed.returncode == 0


def _require_paths_unchanged(
    root: Path,
    *,
    commit: str,
    paths: tuple[str, ...],
    missing_message: str,
    changed_message: str,
) -> int:
    for relative in paths:
        document = root / relative
        if not document.is_file():
            raise RepositoryError(missing_message)
        baseline = _git(root, "show", f"{commit}:{relative}", text=False)
        assert isinstance(baseline, bytes)
        if document.read_bytes() != baseline:
            raise RepositoryError(changed_message)
    return len(paths)


def check_repository(root: Path) -> dict[str, object]:
    root = root.resolve()
    top = _git(root, "rev-parse", "--show-toplevel")
    assert isinstance(top, str)
    if Path(top.strip()).resolve() != root:
        raise RepositoryError("P5 repository root is not exact")
    prior = check_p4_repository(root)
    branch = _git(root, "branch", "--show-current")
    head = _git(root, "rev-parse", "HEAD")
    merge_base = _git(root, "merge-base", "HEAD", BASE_COMMIT)
    assert isinstance(branch, str) and isinstance(head, str) and isinstance(merge_base, str)
    _require_commit(root, ACCEPTED_P5_COMMIT)
    if not _is_ancestor(root, ACCEPTED_P5_COMMIT, "HEAD"):
        raise RepositoryError("the accepted P5 commit is not an ancestor of HEAD")
    accepted_p5_immutable_count = _require_paths_unchanged(
        root,
        commit=ACCEPTED_P5_COMMIT,
        paths=ACCEPTED_P5_IMMUTABLE_PATHS,
        missing_message="an accepted P5 immutable file is missing",
        changed_message="an accepted P5 immutable file changed",
    )
    acceptance_document_count = _require_paths_unchanged(
        root,
        commit=ACCEPTANCE_COMMIT,
        paths=ACCEPTANCE_DOCUMENT_PATHS,
        missing_message="a fixed P5 acceptance document is missing",
        changed_message="a fixed P5 acceptance document changed after its commit",
    )
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
        "accepted_p5_commit": ACCEPTED_P5_COMMIT,
        "accepted_p5_ancestor": True,
        "accepted_p5_immutable_file_count": accepted_p5_immutable_count,
        "branch": branch.strip(),
        "head_commit": head.strip(),
        "base_commit": BASE_COMMIT,
        "merge_base": merge_base.strip(),
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "acceptance_documents_immutable": True,
        "acceptance_document_count": acceptance_document_count,
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
