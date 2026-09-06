# SPDX-License-Identifier: Apache-2.0

"""Validate trusted P7 ancestry, fixed acceptance, historical immutability, and residue."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p6_repository import check_repository as check_p6_repository

BASE_COMMIT = "7e6f4c4dc50b675afb60b6e160fe4f15312dd6c8"
BRANCH = "codex/p7-optional-adapters"
ACCEPTANCE_COMMIT = "9df79441c8fb9f8c41b47114f42643a290df35a6"
TRUSTED_P7_COMMIT = ACCEPTANCE_COMMIT
ACCEPTANCE_DOCUMENT_PATHS = (
    "docs/adr/0006-optional-provider-and-channel-adapters.md",
    "docs/p7/acceptance.md",
    "docs/p7/adapter-golden-path.md",
)
HISTORICAL_PATHS = (
    "artifacts/p0",
    "artifacts/p1",
    "artifacts/p2",
    "artifacts/p3",
    "artifacts/p4",
    "artifacts/p5",
    "artifacts/p6",
    "docs/p0",
    "docs/p1",
    "docs/p2",
    "docs/p3",
    "docs/p4",
    "docs/p5",
    "docs/p6",
    "migrations",
    "provenance/p2-migration-receipt.json",
    "provenance/p3-migration-receipt.json",
    "provenance/p4-migration-receipt.json",
    "provenance/p5-migration-receipt.json",
    "provenance/p6-migration-receipt.json",
)
REQUIRED_FILES = {
    *ACCEPTANCE_DOCUMENT_PATHS,
    "Dockerfile.p7",
    "Dockerfile.p7.dockerignore",
    "compose.p7.yaml",
    "docs/p7/corrective-runtime-notes.md",
    "provenance/p7-migration-receipt.json",
    "scripts/check_p7_abuse.py",
    "scripts/check_p7_architecture.py",
    "scripts/check_p7_channel_adapter.py",
    "scripts/check_p7_compose.py",
    "scripts/check_p7_compose_runtime.py",
    "scripts/check_p7_configuration.py",
    "scripts/check_p7_container_runtime.py",
    "scripts/check_p7_golden_path.py",
    "scripts/check_p7_model_adapter.py",
    "scripts/check_p7_provenance.py",
    "scripts/check_p7_repository.py",
    "scripts/collect_p7_evidence.py",
    "scripts/p7_gate_support.py",
    "scripts/p7_compose_stub.py",
    "scripts/p7_compose_ingress.py",
    "scripts/p7_compose_network_guard.py",
    "scripts/run_p7_toolchain.py",
    "scripts/run_p7_unittest_suite.py",
    "src/digital_colleagues/adapters/http_json/__init__.py",
    "src/digital_colleagues/adapters/http_json/channel.py",
    "src/digital_colleagues/adapters/http_json/configuration.py",
    "src/digital_colleagues/adapters/http_json/errors.py",
    "src/digital_colleagues/adapters/http_json/model.py",
    "src/digital_colleagues/adapters/http_json/transport.py",
    "src/digital_colleagues/local/p7_adapters.py",
    "studio/Dockerfile.p7",
    "studio/nginx.p7.conf",
    "tests/p7/fixtures.py",
    "tests/p7/test_channel_adapter.py",
    "tests/p7/test_configuration.py",
    "tests/p7/test_model_adapter.py",
    "tests/p7/test_repository.py",
    "tests/p7/test_runtime_integration.py",
}


class RepositoryError(RuntimeError):
    """The current tree does not satisfy the trusted P7 repository contract."""


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
        raise RepositoryError("Git P7 history inspection failed")
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
        raise RepositoryError("the trusted P7 commit is unavailable")


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        raise RepositoryError("Git P7 ancestry inspection failed")
    return completed.returncode == 0


def check_repository(root: Path) -> dict[str, object]:
    root = root.resolve()
    top = _git(root, "rev-parse", "--show-toplevel")
    assert isinstance(top, str)
    if Path(top.strip()).resolve() != root:
        raise RepositoryError("P7 repository root is not exact")
    prior = check_p6_repository(root)
    _require_commit(root, TRUSTED_P7_COMMIT)
    if not _is_ancestor(root, TRUSTED_P7_COMMIT, "HEAD"):
        raise RepositoryError("the trusted P7 acceptance commit is not an ancestor of HEAD")
    branch = _git(root, "branch", "--show-current")
    head = _git(root, "rev-parse", "HEAD")
    merge_base = _git(root, "merge-base", "HEAD", BASE_COMMIT)
    assert isinstance(branch, str) and isinstance(head, str) and isinstance(merge_base, str)
    if merge_base.strip() != BASE_COMMIT:
        raise RepositoryError("P7 fixed-base ancestry drifted")
    for relative in ACCEPTANCE_DOCUMENT_PATHS:
        document = root / relative
        if not document.is_file():
            raise RepositoryError("a fixed P7 acceptance document is missing")
        accepted = _git(root, "show", f"{ACCEPTANCE_COMMIT}:{relative}", text=False)
        assert isinstance(accepted, bytes)
        if document.read_bytes() != accepted:
            raise RepositoryError("a fixed P7 acceptance document changed")
    historical = _git(root, "diff", "--name-only", BASE_COMMIT, "--", *HISTORICAL_PATHS)
    assert isinstance(historical, str)
    if historical.strip():
        raise RepositoryError("P0-P6 historical material or migrations changed")
    missing = sorted(relative for relative in REQUIRED_FILES if not (root / relative).is_file())
    if missing:
        raise RepositoryError("required P7 implementation files are missing")
    migration_008 = tuple((root / "migrations").glob("008*"))
    if migration_008:
        raise RepositoryError("P7 must not add migration 008")
    return {
        "schema_version": 1,
        "gate": "p7_repository_clean",
        "trusted_p7_commit": TRUSTED_P7_COMMIT,
        "trusted_p7_ancestor": True,
        "branch": branch.strip(),
        "head_commit": head.strip(),
        "base_commit": BASE_COMMIT,
        "merge_base": merge_base.strip(),
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "acceptance_documents_immutable": True,
        "acceptance_document_count": len(ACCEPTANCE_DOCUMENT_PATHS),
        "required_file_count": len(REQUIRED_FILES),
        "retained_p6_gate": prior["gate"],
        "historical_drift_count": 0,
        "migration_008": False,
        "residue_count": prior["residue_count"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P7 repository health.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_repository(Path(arguments.root))
    except (OSError, RepositoryError) as exc:
        print(f"P7 repository check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
