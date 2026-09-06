# SPDX-License-Identifier: Apache-2.0

"""Validate trusted P8 ancestry, fixed acceptance, history, files, and residue."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p7_repository import check_repository as check_p7_repository
from scripts.p8_release_support import ACCEPTANCE_COMMIT, BASE_COMMIT

# The evidence writer imports BRANCH and the fixed development-boundary commits. General
# repository health is instead anchored to the independently accepted P8 main baseline and
# never to the checkout branch name.
BRANCH = "codex/p8-release-readiness"
ACCEPTED_P8_COMMIT = "0bb80ab187932fbad42fbf665b8310987609a1f5"
ACCEPTED_P8_IMMUTABLE_PATHS = (
    "artifacts/p8/summary.json",
    "docs/p8/acceptance.md",
    "provenance/p8-migration-receipt.json",
)
POST_MERGE_ALLOWED_PATHS = frozenset(
    {
        "README.md",
        "SECURITY.md",
        "docs/p8/release-checklist.md",
        "docs/product/capability-matrix.md",
        "docs/roadmap.md",
        "scripts/check_p8_provenance.py",
        "scripts/check_p8_release.py",
        "scripts/check_p8_repository.py",
        "tests/p8/test_release.py",
        "tests/p8/test_repository.py",
    }
)
ACCEPTANCE_DOCUMENT_PATHS = ("docs/p8/acceptance.md",)
HISTORICAL_PATHS = (
    "artifacts/p0",
    "artifacts/p1",
    "artifacts/p2",
    "artifacts/p3",
    "artifacts/p4",
    "artifacts/p5",
    "artifacts/p6",
    "artifacts/p7",
    "docs/p0",
    "docs/p1",
    "docs/p2",
    "docs/p3",
    "docs/p4",
    "docs/p5",
    "docs/p6",
    "docs/p7",
    "migrations",
    "provenance/p2-migration-receipt.json",
    "provenance/p3-migration-receipt.json",
    "provenance/p4-migration-receipt.json",
    "provenance/p5-migration-receipt.json",
    "provenance/p6-migration-receipt.json",
    "provenance/p7-migration-receipt.json",
    "provenance/source-allowlist.json",
    "provenance/source-rights-confirmation.json",
)
REQUIRED_FILES = {
    *ACCEPTANCE_DOCUMENT_PATHS,
    "docs/p8/operations.md",
    "docs/p8/release-checklist.md",
    "docs/p8/release-golden-path.md",
    "provenance/p8-migration-receipt.json",
    "release/source-archive-policy.json",
    "release/supply-chain-inputs.json",
    "requirements/p8.lock",
    "scripts/build_p8_release.py",
    "scripts/check_p8_backup_restore.py",
    "scripts/check_p8_compose_runtime.py",
    "scripts/check_p8_diagnostics.py",
    "scripts/check_p8_golden_path.py",
    "scripts/check_p8_operations.py",
    "scripts/check_p8_provenance.py",
    "scripts/check_p8_release.py",
    "scripts/check_p8_repository.py",
    "scripts/check_p8_reproducibility.py",
    "scripts/check_p8_supply_chain.py",
    "scripts/collect_p8_evidence.py",
    "scripts/p8_gate_support.py",
    "scripts/p8_release_support.py",
    "scripts/run_p8_toolchain.py",
    "scripts/run_p8_unittest_suite.py",
    "src/digital_colleagues/operations/__init__.py",
    "src/digital_colleagues/operations/__main__.py",
    "src/digital_colleagues/operations/backup_restore.py",
    "src/digital_colleagues/operations/diagnostics.py",
    "src/digital_colleagues/operations/metadata.py",
    "tests/p8/fixtures.py",
    "tests/p8/test_backup_restore.py",
    "tests/p8/test_diagnostics.py",
    "tests/p8/test_release.py",
    "tests/p8/test_repository.py",
}
FORBIDDEN_RESIDUE_PARTS = {
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}
FORBIDDEN_RESIDUE_SUFFIXES = (
    ".backup",
    ".db",
    ".log",
    ".pyc",
    ".sqlite",
    ".sqlite-shm",
    ".sqlite-wal",
    ".tar.gz",
    ".whl",
)


class RepositoryError(RuntimeError):
    """The repository does not satisfy the fixed P8 development boundary."""


@dataclass(frozen=True)
class GitChange:
    status: str
    paths: tuple[str, ...]


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
        raise RepositoryError("Git P8 history inspection failed")
    return cast(str | bytes, completed.stdout)


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        raise RepositoryError("Git P8 ancestry inspection failed")
    return completed.returncode == 0


def _change_path(field: bytes) -> str:
    try:
        value = field.decode("utf-8")
    except UnicodeError as exc:
        raise RepositoryError("Git P8 change path is not UTF-8") from exc
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise RepositoryError("Git P8 change path is invalid")
    return value


def _parse_name_status(output: bytes) -> tuple[GitChange, ...]:
    if not output:
        return ()
    fields = output.split(b"\0")
    if fields[-1] != b"":
        raise RepositoryError("Git P8 change status is malformed")
    fields.pop()
    changes: list[GitChange] = []
    index = 0
    while index < len(fields):
        try:
            status = fields[index].decode("ascii")
        except UnicodeError as exc:
            raise RepositoryError("Git P8 change status is invalid") from exc
        index += 1
        code = status[:1]
        if code in {"R", "C"}:
            score = status[1:]
            if not score.isdigit() or int(score) > 100:
                raise RepositoryError("Git P8 rename or copy status is invalid")
            path_count = 2
        elif status in {"A", "D", "M", "T"}:
            path_count = 1
        elif status in {"U", "X", "B"}:
            raise RepositoryError("Git P8 change state is unresolved")
        else:
            raise RepositoryError("Git P8 change status is unsupported")
        if index + path_count > len(fields):
            raise RepositoryError("Git P8 change status is malformed")
        paths = tuple(_change_path(field) for field in fields[index : index + path_count])
        index += path_count
        changes.append(GitChange(status=status, paths=paths))
    return tuple(changes)


def _diff_changes(root: Path, *arguments: str) -> tuple[GitChange, ...]:
    completed = subprocess.run(
        [
            "git",
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--name-status",
            "-z",
            "--break-rewrites",
            "--find-renames",
            "--find-copies-harder",
            *arguments,
            "--",
        ],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryError("Git P8 descendant change inspection failed")
    return _parse_name_status(completed.stdout)


def _untracked_paths(root: Path) -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryError("Git P8 untracked path inspection failed")
    if not completed.stdout:
        return ()
    fields = completed.stdout.split(b"\0")
    if fields[-1] != b"":
        raise RepositoryError("Git P8 untracked path output is malformed")
    return tuple(_change_path(field) for field in fields[:-1])


def _changed_paths(changes: tuple[GitChange, ...]) -> set[str]:
    return {path for change in changes for path in change.paths}


def _committed_descendant_boundary(root: Path) -> dict[str, int | str]:
    committed = _diff_changes(root, ACCEPTED_P8_COMMIT, "HEAD")
    committed_paths = _changed_paths(committed)
    unexpected_committed = committed_paths - POST_MERGE_ALLOWED_PATHS
    if unexpected_committed:
        raise RepositoryError("P8 post-merge commit changed a path outside the allowlist")
    if committed_paths != POST_MERGE_ALLOWED_PATHS:
        raise RepositoryError("P8 post-merge checkpoint delta is incomplete")
    return {
        "descendant_boundary_status": "passed",
        "post_merge_change_count": len(committed),
        "post_merge_path_count": len(committed_paths),
        "post_merge_allowed_path_count": len(POST_MERGE_ALLOWED_PATHS),
        "post_merge_unexpected_path_count": 0,
    }


def _working_tree_boundary(root: Path) -> dict[str, int]:
    staged = _diff_changes(root, "--cached", "HEAD")
    unstaged = _diff_changes(root)
    untracked = _untracked_paths(root)
    staged_paths = _changed_paths(staged)
    unstaged_paths = _changed_paths(unstaged)
    working_paths = staged_paths | unstaged_paths | set(untracked)
    if working_paths - POST_MERGE_ALLOWED_PATHS:
        raise RepositoryError("P8 working tree changed a path outside the allowlist")
    return {
        "staged_change_path_count": len(staged_paths),
        "unstaged_change_path_count": len(unstaged_paths),
        "untracked_path_count": len(untracked),
    }


def _require_commit(root: Path, commit: str) -> None:
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryError("the accepted P8 commit is unavailable")


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
        accepted = _git(root, "show", f"{commit}:{relative}", text=False)
        assert isinstance(accepted, bytes)
        if document.read_bytes() != accepted:
            raise RepositoryError(changed_message)
    return len(paths)


def _residue(root: Path) -> tuple[str, ...]:
    found: list[str] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        if any(part in FORBIDDEN_RESIDUE_PARTS for part in relative.parts) or (
            path.is_file() and path.name.endswith(FORBIDDEN_RESIDUE_SUFFIXES)
        ):
            found.append(relative.as_posix())
    return tuple(sorted(set(found)))


def check_repository(root: Path) -> dict[str, object]:
    root = root.resolve()
    top = _git(root, "rev-parse", "--show-toplevel")
    assert isinstance(top, str)
    if Path(top.strip()).resolve() != root:
        raise RepositoryError("P8 repository root is not exact")
    _require_commit(root, ACCEPTED_P8_COMMIT)
    if not _is_ancestor(root, ACCEPTED_P8_COMMIT, "HEAD"):
        raise RepositoryError("the accepted P8 commit is not an ancestor of HEAD")
    descendant = _committed_descendant_boundary(root)
    if not _is_ancestor(root, BASE_COMMIT, "HEAD") or not _is_ancestor(
        root, ACCEPTANCE_COMMIT, "HEAD"
    ):
        raise RepositoryError("the fixed P8 base or acceptance commit is not trusted ancestry")
    try:
        prior = check_p7_repository(root)
    except RuntimeError as exc:
        raise RepositoryError("the retained P7 repository boundary failed") from exc
    branch = _git(root, "branch", "--show-current")
    head = _git(root, "rev-parse", "HEAD")
    merge_base = _git(root, "merge-base", "HEAD", BASE_COMMIT)
    assert isinstance(branch, str) and isinstance(head, str) and isinstance(merge_base, str)
    if merge_base.strip() != BASE_COMMIT:
        raise RepositoryError("P8 fixed merge-base drifted")
    accepted_p8_immutable_count = _require_paths_unchanged(
        root,
        commit=ACCEPTED_P8_COMMIT,
        paths=ACCEPTED_P8_IMMUTABLE_PATHS,
        missing_message="an accepted P8 immutable file is missing",
        changed_message="an accepted P8 immutable file changed",
    )
    _require_paths_unchanged(
        root,
        commit=ACCEPTANCE_COMMIT,
        paths=ACCEPTANCE_DOCUMENT_PATHS,
        missing_message="the fixed P8 acceptance contract is missing",
        changed_message="the fixed P8 acceptance contract changed",
    )
    historical = _git(root, "diff", "--name-only", BASE_COMMIT, "--", *HISTORICAL_PATHS)
    assert isinstance(historical, str)
    if historical.strip():
        raise RepositoryError("P0-P7 history, provenance, or migrations changed")
    if tuple((root / "migrations").glob("008*")):
        raise RepositoryError("P8 must not add migration 008")
    missing = sorted(relative for relative in REQUIRED_FILES if not (root / relative).is_file())
    if missing:
        raise RepositoryError("required P8 implementation files are missing")
    residue = _residue(root)
    if residue:
        raise RepositoryError("repository contains forbidden runtime or build residue")
    descendant.update(_working_tree_boundary(root))
    return {
        "schema_version": 1,
        "gate": "p8_repository_clean",
        "accepted_p8_commit": ACCEPTED_P8_COMMIT,
        "accepted_p8_ancestor": True,
        "accepted_p8_immutable_file_count": accepted_p8_immutable_count,
        "branch": branch.strip(),
        "head_commit": head.strip(),
        "base_commit": BASE_COMMIT,
        "merge_base": merge_base.strip(),
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "acceptance_documents_immutable": True,
        "required_file_count": len(REQUIRED_FILES),
        "historical_drift_count": 0,
        "migration_008": False,
        "residue_count": 0,
        "retained_p7_gate": prior["gate"],
        **descendant,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P8 repository health.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_repository(Path(arguments.root))
    except (OSError, RepositoryError) as exc:
        print(f"P8 repository check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
