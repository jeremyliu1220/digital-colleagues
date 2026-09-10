# SPDX-License-Identifier: Apache-2.0

"""Validate the immutable P12 contract, linear topology, and exact path boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

BASE_COMMIT = "c1562ea5201394d8a278f4b644daf4029cbb5bd4"
BASE_TREE = "ae0f33263cfc7445fef69656ad9c5cb04d4a2d00"
ACCEPTANCE_COMMIT = "3639fa08ca44820bb922e0644095c9fb9c24d3e6"
ACCEPTANCE_TREE = "71c411660e0f7ff26e8ad1451acaa0ea26fa384b"
ACCEPTANCE_PATH = "docs/p12/acceptance.md"
ACCEPTANCE_BLOB = "50453e154cf642bc7b90644660e1d956b04f966a"
ACCEPTANCE_SHA256 = "be3ad1967a98c67ae34ad7c22c35a9ec1f637a780c930ae4e8349f126e64800b"
SUMMARY_PATH = "artifacts/p12/summary.json"
BRANCH = "codex/p12-public-pilot-continuity-rebaseline-v2"
REJECTED_BRANCH = "codex/p12-public-pilot-continuity-rebaseline"
REJECTED_COMMIT = "8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3"
MAKE_MARKER = "\n# P12 Public Pilot continuity governance\n"
NEW_TARGETS = (
    "p12-test",
    "p12-implementation-check",
    "p12-ci",
    "p12-evidence-preflight",
    "evidence-p12",
    "p12-check",
)

ALLOWLIST = (
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/pull_request_template.md",
    ".github/workflows/ci.yml",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "Makefile",
    "README.md",
    "SECURITY.md",
    "artifacts/p12/summary.json",
    "docs/adr/0011-public-pilot-continuity-rebaseline.md",
    "docs/architecture/target-architecture.md",
    "docs/development.md",
    "docs/p12/acceptance.md",
    "docs/p12/rebaseline-checklist.md",
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
    "provenance/p12-change-receipt.json",
    "scripts/check_p12_ci_policy.py",
    "scripts/check_p12_migrations.py",
    "scripts/check_p12_provenance.py",
    "scripts/check_p12_rebaseline.py",
    "scripts/check_p12_repository.py",
    "scripts/collect_p12_evidence.py",
    "scripts/run_p12_toolchain.py",
    "tests/p12/__init__.py",
    "tests/p12/test_ci_policy.py",
    "tests/p12/test_evidence_gate.py",
    "tests/p12/test_migrations.py",
    "tests/p12/test_provenance.py",
    "tests/p12/test_rebaseline.py",
    "tests/p12/test_repository.py",
)


class P12GateError(RuntimeError):
    """A fixed P12 governance boundary failed closed."""


class CommitRecord(TypedDict):
    commit: str
    parent: str
    tree: str
    changed_paths: tuple[str, ...]


def git(root: Path, *arguments: str, allow_failure: bool = False) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0 and not allow_failure:
        raise P12GateError("Git identity inspection failed")
    return completed.stdout.strip()


def git_succeeds(root: Path, *arguments: str) -> bool:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=120,
        check=False,
    )
    return completed.returncode == 0


def acceptance_paths(root: Path) -> tuple[str, ...]:
    try:
        text = (root / ACCEPTANCE_PATH).read_text(encoding="utf-8")
        section = text.split("## Exact 39-path P12 changed-file allowlist", 1)[1]
        table = section.split("## Architectural and data-contract boundary", 1)[0]
    except (OSError, UnicodeError, IndexError) as exc:
        raise P12GateError("P12 allowlist is unavailable") from exc
    paths: list[str] = []
    for line in table.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[0].isdigit():
            paths.append(cells[1])
    result = tuple(paths)
    if result != ALLOWLIST or len(result) != 39 or len(set(result)) != 39:
        raise P12GateError("P12 allowlist identity is invalid")
    return result


def implementation_paths(root: Path) -> tuple[str, ...]:
    return tuple(
        path for path in acceptance_paths(root) if path not in {ACCEPTANCE_PATH, SUMMARY_PATH}
    )


def expected_changed_paths(root: Path, *, final: bool) -> tuple[str, ...]:
    excluded = set() if final else {SUMMARY_PATH}
    return tuple(sorted(path for path in acceptance_paths(root) if path not in excluded))


def validate_changed_path_set(
    allowed: tuple[str, ...], changed: tuple[str, ...], *, final: bool
) -> None:
    excluded = set() if final else {SUMMARY_PATH}
    expected = {path for path in allowed if path not in excluded}
    if set(changed) != expected or len(changed) != len(expected):
        raise P12GateError("P12 changed path set is incomplete or escaped the allowlist")


def validate_makefile_contents(base: str, current: str) -> None:
    if current.count(MAKE_MARKER) != 1:
        raise P12GateError("P12 Makefile marker is absent or duplicated")
    prefix, addition = current.split(MAKE_MARKER, 1)
    if not addition.strip():
        raise P12GateError("P12 Makefile target block is absent")
    normalized = prefix
    normalized = normalized.replace("ci: p12-ci\n", "ci: p11-ci\n", 1)
    if normalized != base:
        raise P12GateError("A pre-existing Makefile byte or recipe changed")
    phony = [line for line in addition.splitlines() if line.startswith(".PHONY: ")]
    if phony != [f".PHONY: {' '.join(NEW_TARGETS)}"]:
        raise P12GateError("P12 Makefile PHONY target identity is invalid")
    declared = {
        line.split(":", 1)[0]
        for line in addition.splitlines()
        if line and not line.startswith(("\t", "#", ".PHONY:")) and ":" in line
    }
    if declared != set(NEW_TARGETS):
        raise P12GateError("P12 Makefile target set is not exact")
    if addition.count("scripts.run_p12_toolchain") != 5:
        raise P12GateError("P12 runner target graph is not exact")
    if addition.count("scripts/collect_p12_evidence.py") != 1:
        raise P12GateError("P12 evidence target graph is not exact")


def commit_records(root: Path, start: str, end: str) -> tuple[CommitRecord, ...]:
    commits = tuple(
        line for line in git(root, "rev-list", "--reverse", f"{start}..{end}").splitlines() if line
    )
    records: list[CommitRecord] = []
    parent = start
    for commit in commits:
        fields = git(root, "rev-list", "--parents", "-n", "1", commit).split()
        if fields != [commit, parent]:
            raise P12GateError("P12 implementation topology is not linear and single-parent")
        paths = tuple(
            sorted(
                line
                for line in git(
                    root, "diff-tree", "--no-commit-id", "--name-only", "-r", commit
                ).splitlines()
                if line
            )
        )
        records.append(
            {
                "commit": commit,
                "parent": parent,
                "tree": git(root, "rev-parse", f"{commit}^{{tree}}"),
                "changed_paths": paths,
            }
        )
        parent = commit
    return tuple(records)


def _check_fixed_contract(root: Path) -> None:
    if git(root, "rev-parse", f"{BASE_COMMIT}^{{tree}}") != BASE_TREE:
        raise P12GateError("P12 base tree identity is invalid")
    if git(root, "rev-parse", f"{ACCEPTANCE_COMMIT}^") != BASE_COMMIT:
        raise P12GateError("P12 acceptance parent is invalid")
    if git(root, "rev-parse", f"{ACCEPTANCE_COMMIT}^{{tree}}") != ACCEPTANCE_TREE:
        raise P12GateError("P12 acceptance tree identity is invalid")
    change = tuple(
        git(
            root, "diff-tree", "--no-commit-id", "--name-only", "-r", ACCEPTANCE_COMMIT
        ).splitlines()
    )
    if change != (ACCEPTANCE_PATH,):
        raise P12GateError("P12 acceptance commit is not isolated")
    if git(root, "rev-parse", f"{ACCEPTANCE_COMMIT}:{ACCEPTANCE_PATH}") != ACCEPTANCE_BLOB:
        raise P12GateError("P12 acceptance blob identity is invalid")
    path = root / ACCEPTANCE_PATH
    if git(root, "hash-object", ACCEPTANCE_PATH) != ACCEPTANCE_BLOB:
        raise P12GateError("P12 acceptance contract drifted")
    if hashlib.sha256(path.read_bytes()).hexdigest() != ACCEPTANCE_SHA256:
        raise P12GateError("P12 acceptance file SHA-256 drifted")


def _check_history(root: Path, *, final: bool) -> tuple[CommitRecord, ...]:
    git(root, "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD")
    git(root, "merge-base", "--is-ancestor", ACCEPTANCE_COMMIT, "HEAD")
    if git_succeeds(root, "merge-base", "--is-ancestor", REJECTED_COMMIT, "HEAD"):
        raise P12GateError("Rejected P12 v1 is an ancestor of the v2 candidate")
    if git(root, "rev-list", "--merges", f"{BASE_COMMIT}..HEAD"):
        raise P12GateError("P12 history contains a merge commit")
    records = commit_records(root, ACCEPTANCE_COMMIT, "HEAD")
    if not records:
        raise P12GateError("P12 implementation commit set is empty")
    allowed_middle = set(implementation_paths(root))
    for index, record in enumerate(records):
        paths = set(record["changed_paths"])
        is_tip = index == len(records) - 1
        if final and is_tip:
            if paths != {SUMMARY_PATH}:
                raise P12GateError("P12 final commit is not summary-only")
        elif not paths or not paths <= allowed_middle:
            raise P12GateError("P12 implementation commit changes a protected path")
    if final and len(records) < 2:
        raise P12GateError("P12 final candidate has no implementation parent")
    return records


def _check_makefile(root: Path) -> None:
    base = git(root, "show", f"{BASE_COMMIT}:Makefile") + "\n"
    current = (root / "Makefile").read_text(encoding="utf-8")
    validate_makefile_contents(base, current)


def _check_diff(root: Path) -> None:
    completed = subprocess.run(
        ["git", "diff", "--check", BASE_COMMIT, "HEAD"],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise P12GateError("P12 committed diff contains whitespace errors")


def check_repository(root: Path, *, mode: str) -> dict[str, object]:
    if mode not in {"implementation", "ci", "final"}:
        raise P12GateError("P12 repository mode is invalid")
    _check_fixed_contract(root)
    final = SUMMARY_PATH in git(root, "diff", "--name-only", BASE_COMMIT, "HEAD").splitlines()
    if mode == "implementation" and final:
        raise P12GateError("P12 implementation mode forbids the summary")
    if mode == "final" and not final:
        raise P12GateError("P12 final mode requires the summary")
    records = _check_history(root, final=final)
    paths = acceptance_paths(root)
    changed = tuple(
        sorted(
            line
            for line in git(root, "diff", "--name-only", BASE_COMMIT, "HEAD").splitlines()
            if line
        )
    )
    validate_changed_path_set(paths, changed, final=final)
    for relative in changed:
        candidate = root / relative
        if not candidate.exists() or candidate.is_symlink():
            raise P12GateError("P12 changed path is absent or a link")
        if not stat.S_ISREG(os.lstat(candidate).st_mode):
            raise P12GateError("P12 changed paths must be regular files")
    if git(root, "status", "--porcelain=v2", "--untracked-files=all"):
        raise P12GateError("P12 repository or index is not clean")
    if git(root, "tag", "--list"):
        raise P12GateError("P12 requires zero local tags")
    if mode in {"implementation", "final"}:
        if git(root, "branch", "--show-current") != BRANCH:
            raise P12GateError("P12 candidate branch identity is invalid")
        if git(root, "rev-parse", f"refs/heads/{REJECTED_BRANCH}") != REJECTED_COMMIT:
            raise P12GateError("Rejected P12 v1 local ref moved")
        if (
            git(root, "rev-parse", "refs/heads/main") != BASE_COMMIT
            or git(root, "rev-parse", "refs/remotes/origin/main") != BASE_COMMIT
        ):
            raise P12GateError("P12 moved local or origin main")
    _check_makefile(root)
    _check_diff(root)
    return {
        "schema_version": 1,
        "gate": "p12_repository",
        "status": "passed",
        "mode": "final_candidate" if final else "implementation",
        "base_commit": BASE_COMMIT,
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "allowlist_count": len(paths),
        "changed_path_count": len(changed),
        "implementation_path_count": len(implementation_paths(root)),
        "implementation_commit_count": len(records) - (1 if final else 0),
        "summary_present": final,
        "merge_commit_count": 0,
        "local_tag_count": 0,
        "product_runtime_change_count": 0,
        "studio_behavior_change_count": 0,
        "schema_change_count": 0,
        "migration_change_count": 0,
        "historical_drift_count": 0,
        "residue_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument(
        "--mode", choices=("implementation", "ci", "final"), default="implementation"
    )
    args = parser.parse_args(argv)
    try:
        result = check_repository(Path(args.root).resolve(), mode=args.mode)
    except (OSError, UnicodeError, P12GateError) as exc:
        print(f"P12 repository check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
