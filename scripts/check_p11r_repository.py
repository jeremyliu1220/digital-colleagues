# SPDX-License-Identifier: Apache-2.0

"""Verify P11R ancestry, immutable history, exact scope, and repository residue."""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

BASE_COMMIT = "7e5387f148f86b5c9b07820dd8b8f4e18e12dc38"
BASE_TREE = "6d7c1b3053fefc1f3b14a4b39fde2d5adb641990"
ACCEPTANCE_COMMIT = "61d5c94e24157b93bc4b4bcca42b4d8d2eab8fec"
ACCEPTANCE_BLOB = "46e6244e06cfad64c10e21071959555dd29a49d3"
ACCEPTANCE_PATH = "docs/p11r/acceptance.md"
SUMMARY_PATH = "artifacts/p11r/summary.json"
BRANCH = "codex/p11r-ci-alignment"
MAKE_MARKER = "\n# P11R current-main CI alignment\n"
NEW_TARGETS = (
    "p11-ci",
    "ci",
    "p11r-test",
    "p11r-compose-smoke",
    "p11r-check",
    "evidence-p11r",
)
ALLOWLIST = (
    ".github/workflows/ci.yml",
    "Makefile",
    "artifacts/p11r/summary.json",
    "docs/p11r/acceptance.md",
    "docs/p11r/operations.md",
    "provenance/p11r-change-receipt.json",
    "scripts/check_p11r_ci_policy.py",
    "scripts/check_p11r_repository.py",
    "scripts/check_p11r_provenance.py",
    "scripts/collect_p11r_evidence.py",
    "scripts/run_p11r_toolchain.py",
    "tests/p11r/__init__.py",
    "tests/p11r/test_ci_policy.py",
    "tests/p11r/test_evidence_gate.py",
    "tests/p11r/test_repository.py",
)


class P11RGateError(RuntimeError):
    """A P11R contract boundary failed closed."""


def git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise P11RGateError("Git identity inspection failed")
    return completed.stdout.strip()


def acceptance_paths(root: Path) -> tuple[str, ...]:
    try:
        text = (root / ACCEPTANCE_PATH).read_text(encoding="utf-8")
        section = text.split("## Exact changed-file allowlist", 1)[1]
        block = section.split("```text", 1)[1].split("```", 1)[0]
    except (OSError, UnicodeError, IndexError) as exc:
        raise P11RGateError("P11R allowlist is unavailable") from exc
    paths = tuple(line.strip() for line in block.splitlines() if line.strip())
    if paths != ALLOWLIST or len(set(paths)) != 15:
        raise P11RGateError("P11R allowlist identity is invalid")
    return paths


def implementation_paths(root: Path) -> tuple[str, ...]:
    return tuple(
        path for path in acceptance_paths(root) if path not in {ACCEPTANCE_PATH, SUMMARY_PATH}
    )


def _changed_paths(root: Path) -> tuple[str, ...]:
    return tuple(
        sorted(
            path
            for path in git(root, "diff", "--name-only", BASE_COMMIT, "HEAD").splitlines()
            if path
        )
    )


def validate_makefile_contents(base: str, current: str) -> None:
    if current.count(MAKE_MARKER) != 1:
        raise P11RGateError("P11R Makefile marker is absent or duplicated")
    prefix, addition = current.split(MAKE_MARKER, 1)
    if not addition.strip():
        raise P11RGateError("P11R Makefile target block is absent")
    lines = prefix.splitlines()
    if len(lines) < 5 or not lines[4].startswith(".PHONY: "):
        raise P11RGateError("Makefile PHONY declaration is unavailable")
    tokens = lines[4].split()
    for target in NEW_TARGETS:
        if tokens.count(target) != 1:
            raise P11RGateError("P11R Makefile PHONY target identity is invalid")
        tokens.remove(target)
    lines[4] = " ".join(tokens)
    normalized = "\n".join(lines) + "\n"
    if normalized != base:
        raise P11RGateError("A pre-existing Makefile byte or recipe changed")
    declared = {
        line.split(":", 1)[0]
        for line in addition.splitlines()
        if line and not line.startswith(("\t", "#")) and ":" in line
    }
    if declared != set(NEW_TARGETS):
        raise P11RGateError("P11R Makefile target set is not exact")


def _check_makefile_additive(root: Path) -> None:
    base = git(root, "show", f"{BASE_COMMIT}:Makefile") + "\n"
    current = (root / "Makefile").read_text(encoding="utf-8")
    validate_makefile_contents(base, current)


def validate_changed_path_set(paths: tuple[str, ...], changed: tuple[str, ...]) -> bool:
    allowed = set(paths)
    changed_set = set(changed)
    implementation = allowed - {SUMMARY_PATH}
    expected = allowed if SUMMARY_PATH in changed_set else implementation
    if changed_set != expected:
        raise P11RGateError("P11R changed path set is incomplete or escaped the allowlist")
    return SUMMARY_PATH in changed_set


def _check_diff_whitespace(root: Path) -> None:
    completed = subprocess.run(
        ["git", "diff", "--check", f"{ACCEPTANCE_COMMIT}...HEAD"],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise P11RGateError("P11R committed implementation diff contains whitespace errors")


def check_repository(root: Path, *, mode: str) -> dict[str, object]:
    if mode not in {"candidate", "ci"}:
        raise P11RGateError("P11R repository mode is invalid")
    paths = acceptance_paths(root)
    if git(root, "rev-parse", f"{BASE_COMMIT}^{{tree}}") != BASE_TREE:
        raise P11RGateError("Accepted P11 base tree identity is invalid")
    if git(root, "rev-parse", f"{ACCEPTANCE_COMMIT}^") != BASE_COMMIT:
        raise P11RGateError("P11R acceptance commit parent is invalid")
    acceptance_change = tuple(
        git(
            root,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            ACCEPTANCE_COMMIT,
        ).splitlines()
    )
    if acceptance_change != (ACCEPTANCE_PATH,):
        raise P11RGateError("P11R acceptance commit is not isolated")
    if git(root, "rev-parse", f"{ACCEPTANCE_COMMIT}:{ACCEPTANCE_PATH}") != ACCEPTANCE_BLOB:
        raise P11RGateError("P11R acceptance blob identity is invalid")
    if git(root, "hash-object", ACCEPTANCE_PATH) != ACCEPTANCE_BLOB:
        raise P11RGateError("P11R acceptance contract drifted")
    git(root, "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD")
    git(root, "merge-base", "--is-ancestor", ACCEPTANCE_COMMIT, "HEAD")
    if git(root, "rev-list", "--merges", f"{BASE_COMMIT}..HEAD"):
        raise P11RGateError("P11R history contains a merge commit")
    if git(root, "tag", "--contains", ACCEPTANCE_COMMIT):
        raise P11RGateError("P11R history has an unauthorized tag")
    if git(root, "status", "--porcelain", "--untracked-files=all"):
        raise P11RGateError("P11R repository or index is not clean")
    if mode == "candidate":
        if git(root, "branch", "--show-current") != BRANCH:
            raise P11RGateError("P11R candidate branch identity is invalid")
        if (
            git(root, "rev-parse", "refs/heads/main") != BASE_COMMIT
            or git(root, "rev-parse", "refs/remotes/origin/main") != BASE_COMMIT
        ):
            raise P11RGateError("P11R candidate moved accepted local or remote main")
    changed = _changed_paths(root)
    summary_present = validate_changed_path_set(paths, changed)
    for relative in changed:
        candidate = root / relative
        if not candidate.exists() or candidate.is_symlink():
            raise P11RGateError("P11R changed path is absent or a link")
        if not stat.S_ISREG(os.lstat(candidate).st_mode):
            raise P11RGateError("P11R changed paths must be regular files")
    forbidden_prefixes = ("src/", "studio/", "migrations/", "docs/p0", "artifacts/p0")
    if any(path.startswith(forbidden_prefixes) for path in changed):
        raise P11RGateError("P11R changed product or historical content")
    _check_makefile_additive(root)
    _check_diff_whitespace(root)
    return {
        "schema_version": 1,
        "gate": "p11r_repository",
        "status": "passed",
        "mode": mode,
        "base": BASE_COMMIT,
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "branch": BRANCH if mode == "candidate" else "branch_independent",
        "allowlist_count": len(paths),
        "changed_path_count": len(changed),
        "summary_present": summary_present,
        "product_runtime_change_count": 0,
        "studio_behavior_change_count": 0,
        "schema_change_count": 0,
        "migration_change_count": 0,
        "historical_drift_count": 0,
        "merge_commit_count": 0,
        "tag_count": 0,
        "residue_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--mode", choices=("candidate", "ci"), default="candidate")
    args = parser.parse_args(argv)
    try:
        result = check_repository(Path(args.root).resolve(), mode=args.mode)
    except (OSError, UnicodeError, P11RGateError) as exc:
        print(f"P11R repository check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
