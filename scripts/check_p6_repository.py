# SPDX-License-Identifier: Apache-2.0

"""Validate trusted P6 ancestry, fixed acceptance, historical files, and residue."""

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

from scripts.check_p5_repository import check_repository as check_p5_repository

BASE_COMMIT = "f1dff72c3fb15b2fc7b3c7d989aa85e275cb31ac"
BRANCH = "codex/p6-governance-hardening"
ACCEPTANCE_COMMIT = "5cf4d33d6d83d09ce8a9aa1a7b53bfb93dcd29a5"
TRUSTED_P6_COMMIT = ACCEPTANCE_COMMIT
ACCEPTANCE_DOCUMENT_PATHS = (
    "docs/p6/acceptance.md",
    "docs/p6/security-golden-path.md",
    "docs/adr/0005-local-multi-user-governance.md",
)
REQUIRED_FILES = {
    *ACCEPTANCE_DOCUMENT_PATHS,
    "migrations/007_governance_hardening.sql",
    "provenance/p6-migration-receipt.json",
    "scripts/check_p6_abuse.py",
    "scripts/check_p6_architecture.py",
    "scripts/check_p6_audit_export.py",
    "scripts/check_p6_authentication.py",
    "scripts/check_p6_change_approval.py",
    "scripts/check_p6_compose.py",
    "scripts/check_p6_compose_runtime.py",
    "scripts/check_p6_effect_approval.py",
    "scripts/check_p6_golden_path.py",
    "scripts/check_p6_migrations.py",
    "scripts/check_p6_provenance.py",
    "scripts/check_p6_rbac.py",
    "scripts/check_p6_repository.py",
    "scripts/check_p6_studio.py",
    "scripts/collect_p6_evidence.py",
    "scripts/p6_gate_support.py",
    "scripts/run_p6_toolchain.py",
    "scripts/run_p6_unittest_suite.py",
    "src/digital_colleagues/adapters/sqlite/p6_store.py",
    "src/digital_colleagues/api/p6_app.py",
    "src/digital_colleagues/application/p6_contracts.py",
    "src/digital_colleagues/application/p6_ports.py",
    "src/digital_colleagues/application/p6_services.py",
    "src/digital_colleagues/core/governance.py",
    "src/digital_colleagues/governance/rbac.py",
    "tests/p6/test_authentication_rbac.py",
    "tests/p6/test_change_approval.py",
    "tests/p6/test_effect_audit.py",
    "tests/p6/test_migrations.py",
    "tests/p6/test_repository.py",
}


class RepositoryError(RuntimeError):
    """The current tree does not satisfy the trusted P6 repository contract."""


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
        raise RepositoryError("Git P6 history inspection failed")
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
        raise RepositoryError("the trusted P6 commit is unavailable")


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        raise RepositoryError("Git P6 ancestry inspection failed")
    return completed.returncode == 0


def check_repository(root: Path) -> dict[str, object]:
    root = root.resolve()
    top = _git(root, "rev-parse", "--show-toplevel")
    assert isinstance(top, str)
    if Path(top.strip()).resolve() != root:
        raise RepositoryError("P6 repository root is not exact")
    prior = check_p5_repository(root)
    _require_commit(root, TRUSTED_P6_COMMIT)
    if not _is_ancestor(root, TRUSTED_P6_COMMIT, "HEAD"):
        raise RepositoryError("the trusted P6 commit is not an ancestor of HEAD")
    branch = _git(root, "branch", "--show-current")
    head = _git(root, "rev-parse", "HEAD")
    merge_base = _git(root, "merge-base", "HEAD", BASE_COMMIT)
    assert isinstance(branch, str) and isinstance(head, str) and isinstance(merge_base, str)
    if merge_base.strip() != BASE_COMMIT:
        raise RepositoryError("P6 fixed-base ancestry drifted")
    for relative in ACCEPTANCE_DOCUMENT_PATHS:
        document = root / relative
        if not document.is_file():
            raise RepositoryError("a fixed P6 acceptance document is missing")
        accepted = _git(root, "show", f"{ACCEPTANCE_COMMIT}:{relative}", text=False)
        assert isinstance(accepted, bytes)
        if document.read_bytes() != accepted:
            raise RepositoryError("a fixed P6 acceptance document changed")
    missing = sorted(relative for relative in REQUIRED_FILES if not (root / relative).is_file())
    if missing:
        raise RepositoryError("required P6 implementation files are missing")
    migration_digest = (
        "sha256:"
        + hashlib.sha256(
            (root / "migrations/007_governance_hardening.sql").read_bytes()
        ).hexdigest()
    )
    return {
        "schema_version": 1,
        "gate": "p6_repository_clean",
        "trusted_p6_commit": TRUSTED_P6_COMMIT,
        "trusted_p6_ancestor": True,
        "branch": branch.strip(),
        "head_commit": head.strip(),
        "base_commit": BASE_COMMIT,
        "merge_base": merge_base.strip(),
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "acceptance_documents_immutable": True,
        "acceptance_document_count": len(ACCEPTANCE_DOCUMENT_PATHS),
        "required_file_count": len(REQUIRED_FILES),
        "retained_p5_gate": prior["gate"],
        "residue_count": prior["residue_count"],
        "migration_007_digest": migration_digest,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P6 repository health.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_repository(Path(arguments.root))
    except (OSError, RepositoryError) as exc:
        print(f"P6 repository check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
