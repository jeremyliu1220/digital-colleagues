# SPDX-License-Identifier: Apache-2.0

"""Validate the exact P9 documentation/governance-only repository boundary."""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BASE_COMMIT = "b093a4fa54bf30cef838c72222d1ae63c4eab9d9"
ACCEPTED_P8_COMMIT = "0bb80ab187932fbad42fbf665b8310987609a1f5"
ACCEPTANCE_COMMIT = "597403bc151da75499acea5bb00ee298e7e5a005"
BRANCH = "codex/p9-productization-rebaseline"
ACCEPTANCE_PATH = "docs/p9/acceptance.md"
SUMMARY_PATH = "artifacts/p9/summary.json"

P9_ALLOWED_PATHS = frozenset(
    {
        "AGENTS.md",
        "Makefile",
        "README.md",
        "SECURITY.md",
        SUMMARY_PATH,
        "docs/adr/0007-declarative-agent-package-and-deployment-model.md",
        "docs/adr/0008-external-identity-connections-and-automatic-authorization.md",
        "docs/architecture/target-architecture.md",
        "docs/development.md",
        ACCEPTANCE_PATH,
        "docs/p9/rebaseline-checklist.md",
        "docs/product/capability-matrix.md",
        "docs/product/post-v0.1-capability-outlook.md",
        "docs/product/v0.2-external-dependency-register.md",
        "docs/product/v0.2-public-pilot-capability-matrix.md",
        "docs/product/v0.2-public-pilot-product-brief.md",
        "docs/roadmap.md",
        "docs/security/privacy-boundary.md",
        "docs/security/threat-model.md",
        "docs/security/v0.2-public-pilot-privacy-boundary.md",
        "docs/security/v0.2-public-pilot-threat-model.md",
        "provenance/p9-migration-receipt.json",
        "scripts/check_p8_provenance.py",
        "scripts/check_p8_repository.py",
        "scripts/check_p9_provenance.py",
        "scripts/check_p9_rebaseline.py",
        "scripts/check_p9_repository.py",
        "scripts/collect_p9_evidence.py",
        "scripts/run_p9_toolchain.py",
        "tests/p8/test_repository.py",
        "tests/p9/__init__.py",
        "tests/p9/fixtures.py",
        "tests/p9/test_evidence_gate.py",
        "tests/p9/test_rebaseline.py",
        "tests/p9/test_repository.py",
    }
)
IMPLEMENTATION_PATHS = P9_ALLOWED_PATHS - {SUMMARY_PATH}
HISTORICAL_PATHS = (
    "artifacts/p0",
    "artifacts/p1",
    "artifacts/p2",
    "artifacts/p3",
    "artifacts/p4",
    "artifacts/p5",
    "artifacts/p6",
    "artifacts/p7",
    "artifacts/p8",
    "docs/p0",
    "docs/p1",
    "docs/p2",
    "docs/p3",
    "docs/p4",
    "docs/p5",
    "docs/p6",
    "docs/p7",
    "docs/p8",
    "migrations",
    "provenance/p2-migration-receipt.json",
    "provenance/p3-migration-receipt.json",
    "provenance/p4-migration-receipt.json",
    "provenance/p5-migration-receipt.json",
    "provenance/p6-migration-receipt.json",
    "provenance/p7-migration-receipt.json",
    "provenance/p8-migration-receipt.json",
    "provenance/source-allowlist.json",
    "provenance/source-rights-confirmation.json",
    "provenance/source-fingerprint-before.json",
    "provenance/source-fingerprint-after.json",
)
MIGRATION_FILES = (
    "001_initial.sql",
    "002_runtime_indexes.sql",
    "003_timer_triggers.sql",
    "004_local_authentication.sql",
    "005_evaluation_observations.sql",
    "006_revisioned_colleague_builder.sql",
    "007_governance_hardening.sql",
    "manifest.json",
)
FORBIDDEN_RESIDUE_PARTS = {
    ".mypy_cache",
    ".pytest_cache",
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
FORBIDDEN_PRODUCT_PREFIXES = (
    "src/digital_colleagues/",
    "studio/",
    "migrations/",
    "requirements/",
    "release/",
)
FORBIDDEN_PRODUCT_FILES = {
    "compose.yaml",
    "compose.p7.yaml",
    "Dockerfile",
    "Dockerfile.p7",
    "pyproject.toml",
}


class RepositoryError(RuntimeError):
    """The repository violates the fixed P9 boundary."""


@dataclass(frozen=True)
class GitChange:
    status: str
    paths: tuple[str, ...]


def _run_git(root: Path, *arguments: str, text: bool = True) -> str | bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=text,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryError("Git P9 repository inspection failed")
    return cast(str | bytes, completed.stdout)


def _require_commit(root: Path, commit: str, label: str) -> None:
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryError(f"the fixed {label} commit is unavailable")


def _is_ancestor(root: Path, ancestor: str, descendant: str = "HEAD") -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        raise RepositoryError("Git P9 ancestry inspection failed")
    return completed.returncode == 0


def _safe_path(field: bytes) -> str:
    try:
        value = field.decode("utf-8")
    except UnicodeError as exc:
        raise RepositoryError("Git P9 path is not UTF-8") from exc
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise RepositoryError("Git P9 path is invalid")
    return value


def _parse_name_status(output: bytes) -> tuple[GitChange, ...]:
    if not output:
        return ()
    fields = output.split(b"\0")
    if fields[-1] != b"":
        raise RepositoryError("Git P9 status is malformed")
    fields.pop()
    changes: list[GitChange] = []
    index = 0
    while index < len(fields):
        try:
            status_value = fields[index].decode("ascii")
        except UnicodeError as exc:
            raise RepositoryError("Git P9 status is invalid") from exc
        index += 1
        code = status_value[:1]
        paths: tuple[str, ...]
        if code in {"R", "C"}:
            score = status_value[1:]
            if not score.isdigit() or int(score) > 100 or index + 2 > len(fields):
                raise RepositoryError("Git P9 rename/copy status is malformed")
            paths = (_safe_path(fields[index]), _safe_path(fields[index + 1]))
            index += 2
        elif status_value in {"A", "D", "M", "T"}:
            if index >= len(fields):
                raise RepositoryError("Git P9 status is malformed")
            paths = (_safe_path(fields[index]),)
            index += 1
        elif code in {"U", "X", "B"}:
            raise RepositoryError("Git P9 change state is unresolved")
        else:
            raise RepositoryError("Git P9 status is unsupported")
        changes.append(GitChange(status_value, paths))
    return tuple(changes)


def _diff(root: Path, *arguments: str) -> tuple[GitChange, ...]:
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
        raise RepositoryError("Git P9 change inspection failed")
    return _parse_name_status(completed.stdout)


def _untracked(root: Path) -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryError("Git P9 untracked inspection failed")
    if not completed.stdout:
        return ()
    fields = completed.stdout.split(b"\0")
    if fields[-1] != b"":
        raise RepositoryError("Git P9 untracked output is malformed")
    return tuple(_safe_path(field) for field in fields[:-1])


def _paths(changes: tuple[GitChange, ...]) -> set[str]:
    return {path for change in changes for path in change.paths}


def _verify_acceptance_commit(root: Path) -> None:
    parent = _run_git(root, "rev-parse", f"{ACCEPTANCE_COMMIT}^")
    assert isinstance(parent, str)
    if parent.strip() != BASE_COMMIT:
        raise RepositoryError("P9 acceptance commit is not the isolated first P9 commit")
    acceptance_delta = _diff(root, f"{ACCEPTANCE_COMMIT}^", ACCEPTANCE_COMMIT)
    if (
        len(acceptance_delta) != 1
        or acceptance_delta[0].status != "A"
        or acceptance_delta[0].paths != (ACCEPTANCE_PATH,)
    ):
        raise RepositoryError("P9 acceptance commit is not isolated")
    accepted = _run_git(root, "show", f"{ACCEPTANCE_COMMIT}:{ACCEPTANCE_PATH}", text=False)
    assert isinstance(accepted, bytes)
    path = root / ACCEPTANCE_PATH
    if not path.is_file() or path.is_symlink() or path.read_bytes() != accepted:
        raise RepositoryError("P9 acceptance contract changed after its fixed commit")


def _verify_historical(root: Path) -> None:
    changed = _run_git(root, "diff", "--name-only", BASE_COMMIT, "HEAD", "--", *HISTORICAL_PATHS)
    assert isinstance(changed, str)
    if changed.strip():
        raise RepositoryError("P0-P8 historical acceptance, artifact, receipt, or migration drift")


def _verify_migrations(root: Path) -> None:
    directory = root / "migrations"
    actual = tuple(sorted(path.name for path in directory.iterdir() if path.is_file()))
    if actual != MIGRATION_FILES:
        raise RepositoryError("migrations must remain exactly 001-007 plus manifest.json")
    for name in MIGRATION_FILES:
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise RepositoryError("a historical migration path has an unsafe type")
        accepted = _run_git(root, "show", f"{BASE_COMMIT}:migrations/{name}", text=False)
        assert isinstance(accepted, bytes)
        if path.read_bytes() != accepted:
            raise RepositoryError("a historical migration digest changed")
    if tuple(directory.glob("008*")):
        raise RepositoryError("migration 008 must be absent in P9")


def _verify_file_types(root: Path, paths: set[str]) -> None:
    for relative in paths:
        path = root / relative
        try:
            mode = path.lstat().st_mode
        except OSError as exc:
            raise RepositoryError("a required P9 path is missing") from exc
        if not stat.S_ISREG(mode) or stat.S_ISLNK(mode):
            raise RepositoryError("P9 changed paths must be regular non-symlink files")


def _residue(root: Path) -> tuple[str, ...]:
    found: list[str] = []
    for directory, names, files in os.walk(root, topdown=True, followlinks=False):
        base = Path(directory)
        relative_dir = base.relative_to(root)
        if ".git" in relative_dir.parts:
            names[:] = []
            continue
        names[:] = [name for name in names if name != ".git"]
        for name in (*names, *files):
            path = base / name
            relative = path.relative_to(root)
            mode = path.lstat().st_mode
            unsafe_type = stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode))
            if (
                unsafe_type
                or any(part in FORBIDDEN_RESIDUE_PARTS for part in relative.parts)
                or name.endswith(FORBIDDEN_RESIDUE_SUFFIXES)
            ):
                found.append(relative.as_posix())
    return tuple(sorted(set(found)))


def check_repository(root: Path, *, require_clean: bool = True) -> dict[str, object]:
    root = root.resolve()
    top = _run_git(root, "rev-parse", "--show-toplevel")
    assert isinstance(top, str)
    if Path(top.strip()).resolve() != root:
        raise RepositoryError("P9 repository root is not exact")
    for commit, label in (
        (BASE_COMMIT, "base"),
        (ACCEPTED_P8_COMMIT, "accepted P8"),
        (ACCEPTANCE_COMMIT, "acceptance"),
    ):
        _require_commit(root, commit, label)
        if not _is_ancestor(root, commit):
            raise RepositoryError(f"the fixed {label} commit is not an ancestor of HEAD")
    merge_base = _run_git(root, "merge-base", "HEAD", BASE_COMMIT)
    branch = _run_git(root, "branch", "--show-current")
    head = _run_git(root, "rev-parse", "HEAD")
    assert isinstance(merge_base, str) and isinstance(branch, str) and isinstance(head, str)
    if merge_base.strip() != BASE_COMMIT:
        raise RepositoryError("P9 exact base or merge-base drifted")

    _verify_acceptance_commit(root)
    _verify_historical(root)
    _verify_migrations(root)

    committed = _diff(root, BASE_COMMIT, "HEAD")
    if any(change.status[:1] in {"R", "C", "T", "D"} for change in committed):
        raise RepositoryError("P9 rename, copy, type change, or deletion is forbidden")
    committed_paths = _paths(committed)
    candidate_phase = "final_evidence" if SUMMARY_PATH in committed_paths else "implementation"
    expected = P9_ALLOWED_PATHS if candidate_phase == "final_evidence" else IMPLEMENTATION_PATHS
    if committed_paths - expected:
        raise RepositoryError("P9 committed change is outside the exact allowlist")
    if committed_paths != expected:
        raise RepositoryError("P9 committed delta is partial or incomplete")
    _verify_file_types(root, committed_paths)

    product_changes = {
        path
        for path in committed_paths
        if path in FORBIDDEN_PRODUCT_FILES
        or any(path.startswith(prefix) for prefix in FORBIDDEN_PRODUCT_PREFIXES)
    }
    if product_changes:
        raise RepositoryError("P9 contains a product/runtime implementation change")

    staged = _diff(root, "--cached", "HEAD")
    unstaged = _diff(root)
    untracked = _untracked(root)
    if require_clean and (staged or unstaged or untracked):
        raise RepositoryError("P9 evidence candidate requires a clean index and worktree")
    dirty_paths = _paths(staged) | _paths(unstaged) | set(untracked)
    if dirty_paths - P9_ALLOWED_PATHS:
        raise RepositoryError("P9 working tree changed a path outside the allowlist")

    residue = _residue(root)
    if residue:
        raise RepositoryError("repository contains runtime, credential, cache, or build residue")

    return {
        "schema_version": 1,
        "gate": "p9_repository_clean",
        "candidate_phase": candidate_phase,
        "branch": branch.strip(),
        "head_commit": head.strip(),
        "base_commit": BASE_COMMIT,
        "merge_base": merge_base.strip(),
        "accepted_p8_commit": ACCEPTED_P8_COMMIT,
        "accepted_p8_ancestor": True,
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "acceptance_contract_immutable": True,
        "acceptance_commit_isolated": True,
        "changed_path_count": len(committed_paths),
        "allowed_path_count": len(expected),
        "historical_drift_count": 0,
        "migration_count": 7,
        "migration_008": False,
        "product_runtime_implementation_change_count": 0,
        "staged_change_path_count": len(_paths(staged)),
        "unstaged_change_path_count": len(_paths(unstaged)),
        "untracked_path_count": len(untracked),
        "cleanup_residue_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P9 repository health.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_repository(Path(arguments.root))
    except (OSError, RepositoryError) as exc:
        print(f"P9 repository check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
