# SPDX-License-Identifier: Apache-2.0

"""Validate the immutable P12 contract, linear topology, and exact path boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

BASE_COMMIT = "c1562ea5201394d8a278f4b644daf4029cbb5bd4"
BASE_TREE = "ae0f33263cfc7445fef69656ad9c5cb04d4a2d00"
ACCEPTANCE_COMMIT = "dbdb75b6afcd226059484ec536fec82532eb3613"
ACCEPTANCE_TREE = "f8d0dad5c04253eefd24353f8c9afd965cf0d6ea"
ACCEPTANCE_PATH = "docs/p12/acceptance.md"
ACCEPTANCE_BLOB = "b574bb350a83a36f9ad7f521514c7d58e97393d9"
ACCEPTANCE_SHA256 = "f0159ea7d164a2b57c61d62e339798ea4ea568880934b571119c67ee781c2d45"
ACCEPTANCE_LINE_COUNT = 3844
ACCEPTANCE_BYTE_COUNT = 382481
SUMMARY_PATH = "artifacts/p12/summary.json"
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
BRANCH = "codex/p12-public-pilot-continuity-rebaseline-v4"
REJECTED_V1_BRANCH = "codex/p12-public-pilot-continuity-rebaseline"
REJECTED_V1_COMMIT = "8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3"
REJECTED_V1_TREE = "557a74e9174247483362bbbd15cd265113775d12"
REJECTED_V2_BRANCH = "codex/p12-public-pilot-continuity-rebaseline-v2"
REJECTED_V2_ACCEPTANCE_COMMIT = "3639fa08ca44820bb922e0644095c9fb9c24d3e6"
REJECTED_V2_ACCEPTANCE_BLOB = "50453e154cf642bc7b90644660e1d956b04f966a"
REJECTED_V2_ACCEPTANCE_SHA256 = "be3ad1967a98c67ae34ad7c22c35a9ec1f637a780c930ae4e8349f126e64800b"
REJECTED_V2_COMMIT = "8e08c3891dc8f761ada096c3f829ef31d3fbfd7c"
REJECTED_V2_TREE = "01ee7b08cc870a626698ac9a3fc46ec92bf0f4e0"
SUPERSEDED_V3_BRANCH = "codex/p12-public-pilot-continuity-rebaseline-v3"
SUPERSEDED_V3_COMMIT = "e31bc733cbdd333648f2ce1c52ac9fe1fad83179"
SUPERSEDED_V3_TREE = "1cdce2a41f84ee4243d04be781ad187eb5f5fab9"
SUPERSEDED_V3_ACCEPTANCE_BLOB = "40c93a2aa8930c71e14fefac2053a10ed137af58"
SUPERSEDED_V3_ACCEPTANCE_SHA256 = "6afddd55f4f8458c94dcd56b781e47fef66a06d954d4246aa3855b4daf2e0e3c"
SUPERSEDED_V3_ACCEPTANCE_LINE_COUNT = 3488
SUPERSEDED_V3_ACCEPTANCE_BYTE_COUNT = 232313
# Backward-compatible alias for P12 modules that only need the v1 identity.
REJECTED_COMMIT = REJECTED_V1_COMMIT
MAKE_MARKER = "\n# P12 v4 historical-platform continuity governance\n"
NEW_TARGETS = (
    "p12-test",
    "p12-current-ci",
    "p12-portable-history",
    "p12-implementation-check",
    "p12-ci",
    "p12-evidence-preflight",
    "evidence-p12",
    "p12-check",
)
EXPECTED_MAKEFILE_ADDITION = """.PHONY: p12-test p12-current-ci p12-portable-history p12-implementation-check p12-ci p12-evidence-preflight evidence-p12 p12-check

p12-test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B -m scripts.run_p12_toolchain --scope test

p12-current-ci:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B -m scripts.run_p12_toolchain --scope current-ci

p12-portable-history:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B -m scripts.run_p12_toolchain --scope portable-history

p12-implementation-check:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B -m scripts.run_p12_toolchain --scope implementation-check

p12-ci:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B -m scripts.run_p12_toolchain --scope ci

p12-evidence-preflight:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B -m scripts.run_p12_toolchain --scope evidence-preflight --implementation-head "$(P12_FINAL_IMPLEMENTATION_HEAD)" --ci-run-id "$(P12_CI_RUN_ID)" --ci-run-attempt "$(P12_CI_RUN_ATTEMPT)" --receipt-directory "$(P12_RECEIPT_DIRECTORY)"

evidence-p12:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B scripts/collect_p12_evidence.py --receipt "$(P12_RECEIPT)" --receipt-sha256 "$(P12_RECEIPT_SHA256)" --authorization "$(P12_EVIDENCE_AUTHORIZATION)"

p12-check:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B -m scripts.run_p12_toolchain --scope final-check
"""

ALLOWLIST = (
    "docs/p12/acceptance.md",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/pull_request_template.md",
    ".github/workflows/ci.yml",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "Makefile",
    "README.md",
    "SECURITY.md",
    "docs/adr/0011-public-pilot-continuity-rebaseline.md",
    "docs/architecture/target-architecture.md",
    "docs/development.md",
    "docs/p12/portable-historical-inventory.json",
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
    "scripts/check_p12_historical_inventory.py",
    "scripts/check_p12_migrations.py",
    "scripts/check_p12_provenance.py",
    "scripts/check_p12_rebaseline.py",
    "scripts/check_p12_repository.py",
    "scripts/collect_p12_evidence.py",
    "scripts/run_p12_toolchain.py",
    "tests/p12/__init__.py",
    "tests/p12/test_ci_policy.py",
    "tests/p12/test_evidence_gate.py",
    "tests/p12/test_historical_inventory.py",
    "tests/p12/test_migrations.py",
    "tests/p12/test_provenance.py",
    "tests/p12/test_rebaseline.py",
    "tests/p12/test_repository.py",
    "artifacts/p12/summary.json",
)


class P12GateError(RuntimeError):
    """A fixed P12 governance boundary failed closed."""


class ChangeRecord(TypedDict):
    path: str
    status: str
    old_mode: str | None
    new_mode: str | None


class CommitRecord(TypedDict):
    commit: str
    parent: str
    tree: str
    message_sha256: str
    changes: list[ChangeRecord]


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


def ref_exists(root: Path, ref: str) -> bool:
    return git_succeeds(root, "show-ref", "--verify", "--quiet", ref)


def raw_commit_identity(root: Path, commit: str) -> tuple[str, tuple[str, ...], bytes]:
    """Read the stored commit object without replacement-object interpretation."""

    completed = subprocess.run(
        ["git", "--no-replace-objects", "cat-file", "commit", commit],
        cwd=root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0 or b"\n\n" not in completed.stdout:
        raise P12GateError("P12 raw commit identity is unavailable")
    header, message = completed.stdout.split(b"\n\n", 1)
    tree_values = tuple(line[5:] for line in header.splitlines() if line.startswith(b"tree "))
    parent_values = tuple(line[7:] for line in header.splitlines() if line.startswith(b"parent "))
    try:
        trees = tuple(value.decode("ascii") for value in tree_values)
        parents = tuple(value.decode("ascii") for value in parent_values)
    except UnicodeDecodeError as exc:
        raise P12GateError("P12 raw commit identity is malformed") from exc
    if (
        len(trees) != 1
        or SHA_RE.fullmatch(trees[0]) is None
        or any(SHA_RE.fullmatch(parent) is None for parent in parents)
    ):
        raise P12GateError("P12 raw commit identity is malformed")
    return trees[0], parents, message


def raw_blob_bytes(root: Path, blob: str) -> bytes:
    completed = subprocess.run(
        ["git", "--no-replace-objects", "cat-file", "blob", blob],
        cwd=root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise P12GateError("P12 preserved acceptance blob is unavailable")
    return completed.stdout


def validate_no_graft(path: Path) -> None:
    try:
        os.lstat(path)
    except FileNotFoundError:
        return
    raise P12GateError("P12 forbids Git grafts")


def check_git_indirections(root: Path) -> None:
    """Reject legacy grafts and replacement refs before any ancestry decision."""

    forbidden_environment = {
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG_SYSTEM",
        "GIT_DIR",
        "GIT_GRAFT_FILE",
        "GIT_INDEX_FILE",
        "GIT_NAMESPACE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_REPLACE_REF_BASE",
        "GIT_SHALLOW_FILE",
        "GIT_WORK_TREE",
    }
    configured_environment = set(os.environ)
    if configured_environment & forbidden_environment or any(
        re.fullmatch(r"GIT_CONFIG_(?:KEY|VALUE)_[0-9]+", name) for name in configured_environment
    ):
        raise P12GateError("P12 forbids Git ancestry environment indirection")
    graft_value = git(root, "rev-parse", "--git-path", "info/grafts")
    graft_path = Path(graft_value)
    if not graft_path.is_absolute():
        graft_path = root / graft_path
    validate_no_graft(graft_path)
    if git(root, "for-each-ref", "--format=%(refname)", "refs/replace/"):
        raise P12GateError("P12 forbids Git replace refs")


def acceptance_paths(root: Path) -> tuple[str, ...]:
    try:
        text = (root / ACCEPTANCE_PATH).read_text(encoding="utf-8")
        section = text.split("### Exact allowlist", 1)[1]
        table = section.split("### WIP preservation, content-bearing snapshot", 1)[0]
    except (OSError, UnicodeError, IndexError) as exc:
        raise P12GateError("P12 allowlist is unavailable") from exc
    paths: list[str] = []
    for line in table.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0] in {"Acceptance-only", "Implementation", "Summary-only"}:
            paths.append(cells[1].strip("`"))
    result = tuple(paths)
    if result != ALLOWLIST or len(result) != 42 or len(set(result)) != 42:
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


def validate_pr14_metadata(value: object) -> str:
    """Validate the preserved v2 pull request's closed-without-merge boundary."""

    if not isinstance(value, dict):
        raise P12GateError("P12 PR #14 metadata is not an object")
    expected_keys = {
        "number",
        "state",
        "baseRefName",
        "baseRefOid",
        "headRefName",
        "headRefOid",
        "autoMergeRequest",
        "mergedAt",
        "mergeCommit",
        "url",
    }
    if set(value) != expected_keys:
        raise P12GateError("P12 PR #14 field-complete metadata is unavailable")
    expected = {
        "number": 14,
        "state": "CLOSED",
        "baseRefName": "main",
        "baseRefOid": BASE_COMMIT,
        "headRefName": REJECTED_V2_BRANCH,
        "headRefOid": REJECTED_V2_COMMIT,
        "autoMergeRequest": None,
        "mergedAt": None,
        "mergeCommit": None,
        "url": "https://github.com/jeremyliu1220/digital-colleagues/pull/14",
    }
    if any(value.get(key) != expected_value for key, expected_value in expected.items()):
        raise P12GateError("P12 PR #14 identity or null merge boundary drifted")
    return "CLOSED"


def validate_makefile_contents(base: str, current: str) -> None:
    if current.count(MAKE_MARKER) != 1:
        raise P12GateError("P12 Makefile marker is absent or duplicated")
    prefix, addition = current.split(MAKE_MARKER, 1)
    if not addition.strip():
        raise P12GateError("P12 Makefile target block is absent")
    if addition != EXPECTED_MAKEFILE_ADDITION:
        raise P12GateError("P12 Makefile target recipes are not exact")
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
    if addition.count("scripts.run_p12_toolchain") != 7:
        raise P12GateError("P12 runner target graph is not exact")
    if addition.count("scripts/collect_p12_evidence.py") != 1:
        raise P12GateError("P12 evidence target graph is not exact")


def commit_records(root: Path, start: str, end: str) -> tuple[CommitRecord, ...]:
    commits = tuple(
        line
        for line in git(
            root, "--no-replace-objects", "rev-list", "--reverse", f"{start}..{end}"
        ).splitlines()
        if line
    )
    records: list[CommitRecord] = []
    parent = start
    for commit in commits:
        fields = git(
            root, "--no-replace-objects", "rev-list", "--parents", "-n", "1", commit
        ).split()
        if fields != [commit, parent]:
            raise P12GateError("P12 implementation topology is not linear and single-parent")
        raw_tree, raw_parents, message = raw_commit_identity(root, commit)
        if raw_parents != (parent,):
            raise P12GateError("P12 raw implementation parent is not exact")
        copy_status = git(
            root,
            "--no-replace-objects",
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "--find-copies-harder",
            "--find-copies=100%",
            "-r",
            commit,
        )
        if any(line.startswith(("C", "R")) for line in copy_status.splitlines()):
            raise P12GateError("P12 implementation history contains a copy or rename")
        changes: list[ChangeRecord] = []
        for line in git(
            root,
            "--no-replace-objects",
            "diff-tree",
            "--no-commit-id",
            "--no-renames",
            "--raw",
            "-r",
            commit,
        ).splitlines():
            metadata, separator, path = line.partition("\t")
            fields = metadata.split()
            if separator != "\t" or len(fields) != 5 or not fields[0].startswith(":"):
                raise P12GateError("P12 commit change record is malformed")
            old_mode = fields[0][1:]
            new_mode = fields[1]
            status = fields[4]
            changes.append(
                {
                    "path": path,
                    "status": status,
                    "old_mode": None if old_mode == "000000" else old_mode,
                    "new_mode": None if new_mode == "000000" else new_mode,
                }
            )
        changes.sort(key=lambda change: change["path"].encode("utf-8"))
        records.append(
            {
                "commit": commit,
                "parent": parent,
                "tree": raw_tree,
                "message_sha256": hashlib.sha256(message).hexdigest(),
                "changes": changes,
            }
        )
        parent = commit
    return tuple(records)


def _check_fixed_contract(root: Path) -> None:
    base_tree, _, _ = raw_commit_identity(root, BASE_COMMIT)
    if base_tree != BASE_TREE:
        raise P12GateError("P12 base tree identity is invalid")
    acceptance_tree, acceptance_parents, _ = raw_commit_identity(root, ACCEPTANCE_COMMIT)
    if acceptance_parents != (BASE_COMMIT,):
        raise P12GateError("P12 acceptance parent is invalid")
    if acceptance_tree != ACCEPTANCE_TREE:
        raise P12GateError("P12 acceptance tree identity is invalid")
    change = tuple(
        git(
            root, "diff-tree", "--no-commit-id", "--name-only", "-r", ACCEPTANCE_COMMIT
        ).splitlines()
    )
    if change != (ACCEPTANCE_PATH,):
        raise P12GateError("P12 acceptance commit is not isolated")
    acceptance_entry = git(root, "ls-tree", ACCEPTANCE_COMMIT, "--", ACCEPTANCE_PATH)
    if acceptance_entry != f"100644 blob {ACCEPTANCE_BLOB}\t{ACCEPTANCE_PATH}":
        raise P12GateError("P12 acceptance path mode or object identity is invalid")
    if git(root, "rev-parse", f"{ACCEPTANCE_COMMIT}:{ACCEPTANCE_PATH}") != ACCEPTANCE_BLOB:
        raise P12GateError("P12 acceptance blob identity is invalid")
    path = root / ACCEPTANCE_PATH
    content = path.read_bytes()
    if git(root, "hash-object", ACCEPTANCE_PATH) != ACCEPTANCE_BLOB:
        raise P12GateError("P12 acceptance contract drifted")
    if hashlib.sha256(content).hexdigest() != ACCEPTANCE_SHA256:
        raise P12GateError("P12 acceptance file SHA-256 drifted")
    if len(content) != ACCEPTANCE_BYTE_COUNT or len(content.splitlines()) != ACCEPTANCE_LINE_COUNT:
        raise P12GateError("P12 acceptance file size identity drifted")


def _check_history(root: Path, *, final: bool) -> tuple[CommitRecord, ...]:
    git(root, "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD")
    git(root, "merge-base", "--is-ancestor", ACCEPTANCE_COMMIT, "HEAD")
    if git_succeeds(root, "merge-base", "--is-ancestor", REJECTED_V1_COMMIT, "HEAD"):
        raise P12GateError("Rejected P12 v1 is an ancestor of the v4 candidate")
    if git_succeeds(root, "merge-base", "--is-ancestor", REJECTED_V2_COMMIT, "HEAD"):
        raise P12GateError("Rejected P12 v2 is an ancestor of the v4 candidate")
    if git_succeeds(root, "merge-base", "--is-ancestor", SUPERSEDED_V3_COMMIT, "HEAD"):
        raise P12GateError("Superseded P12 v3 is an ancestor of the v4 candidate")
    if git(root, "rev-list", "--merges", f"{BASE_COMMIT}..HEAD"):
        raise P12GateError("P12 history contains a merge commit")
    records = commit_records(root, ACCEPTANCE_COMMIT, "HEAD")
    if not records:
        raise P12GateError("P12 implementation commit set is empty")
    allowed_middle = set(implementation_paths(root))
    for index, record in enumerate(records):
        changes = record["changes"]
        paths = {change["path"] for change in changes}
        if any(
            change["status"] not in {"A", "M"}
            or change["new_mode"] != "100644"
            or (change["status"] == "M" and change["old_mode"] != "100644")
            or (change["status"] == "A" and change["old_mode"] is not None)
            for change in changes
        ):
            raise P12GateError("P12 implementation commit contains a forbidden change kind")
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


def _check_changed_file_kinds(root: Path, changed: tuple[str, ...]) -> None:
    status_lines = tuple(
        line
        for line in git(
            root, "diff", "--name-status", "--no-renames", BASE_COMMIT, "HEAD"
        ).splitlines()
        if line
    )
    seen: list[str] = []
    for line in status_lines:
        fields = line.split("\t")
        if len(fields) != 2 or fields[0] not in {"A", "M"}:
            raise P12GateError("P12 changed path has a forbidden Git change kind")
        seen.append(fields[1])
    if tuple(sorted(seen)) != changed:
        raise P12GateError("P12 changed path status inventory is inconsistent")
    for relative in changed:
        entry = git(root, "ls-tree", "HEAD", "--", relative)
        metadata, separator, listed_path = entry.partition("\t")
        fields = metadata.split()
        if (
            separator != "\t"
            or listed_path != relative
            or len(fields) != 3
            or fields[0] != "100644"
            or fields[1] != "blob"
        ):
            raise P12GateError("P12 changed path Git mode or object type is invalid")


def check_repository(root: Path, *, mode: str) -> dict[str, object]:
    if mode not in {"implementation", "ci", "final"}:
        raise P12GateError("P12 repository mode is invalid")
    check_git_indirections(root)
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
    _check_changed_file_kinds(root, changed)
    for relative in changed:
        candidate = root / relative
        if not candidate.exists() or candidate.is_symlink():
            raise P12GateError("P12 changed path is absent or a link")
        if not stat.S_ISREG(os.lstat(candidate).st_mode):
            raise P12GateError("P12 changed paths must be regular files")
    if git(root, "status", "--porcelain=v2", "--untracked-files=all", "--ignored=matching"):
        raise P12GateError("P12 repository or index is not clean")
    if git(root, "tag", "--list"):
        raise P12GateError("P12 requires zero local tags")
    if mode in {"implementation", "final"}:
        if git(root, "branch", "--show-current") != BRANCH:
            raise P12GateError("P12 candidate branch identity is invalid")
        if git(root, "rev-parse", f"refs/heads/{REJECTED_V1_BRANCH}") != REJECTED_V1_COMMIT:
            raise P12GateError("Rejected P12 v1 local ref moved")
        if git(root, "rev-parse", f"refs/heads/{REJECTED_V2_BRANCH}") != REJECTED_V2_COMMIT:
            raise P12GateError("Rejected P12 v2 local ref moved")
        if git(root, "rev-parse", f"refs/heads/{SUPERSEDED_V3_BRANCH}") != SUPERSEDED_V3_COMMIT:
            raise P12GateError("Superseded P12 v3 local ref moved")
        if (
            git(root, "rev-parse", f"refs/remotes/origin/{REJECTED_V2_BRANCH}")
            != REJECTED_V2_COMMIT
        ):
            raise P12GateError("Rejected P12 v2 remote-tracking ref moved")
        if ref_exists(root, f"refs/remotes/origin/{REJECTED_V1_BRANCH}"):
            raise P12GateError("Rejected P12 v1 remote-tracking ref unexpectedly exists")
        if ref_exists(root, f"refs/remotes/origin/{SUPERSEDED_V3_BRANCH}"):
            raise P12GateError("Superseded P12 v3 remote-tracking ref unexpectedly exists")
        if git(root, "rev-parse", f"{REJECTED_V1_COMMIT}^{{tree}}") != REJECTED_V1_TREE:
            raise P12GateError("Rejected P12 v1 tree moved")
        if git(root, "rev-parse", f"{REJECTED_V2_COMMIT}^{{tree}}") != REJECTED_V2_TREE:
            raise P12GateError("Rejected P12 v2 tree moved")
        if git(root, "rev-parse", f"{SUPERSEDED_V3_COMMIT}^{{tree}}") != SUPERSEDED_V3_TREE:
            raise P12GateError("Superseded P12 v3 tree moved")
        if (
            git(root, "rev-parse", f"{REJECTED_V2_ACCEPTANCE_COMMIT}:{ACCEPTANCE_PATH}")
            != REJECTED_V2_ACCEPTANCE_BLOB
        ):
            raise P12GateError("Rejected P12 v2 acceptance blob moved")
        if (
            git(root, "rev-parse", f"{SUPERSEDED_V3_COMMIT}:{ACCEPTANCE_PATH}")
            != SUPERSEDED_V3_ACCEPTANCE_BLOB
        ):
            raise P12GateError("Superseded P12 v3 acceptance blob moved")
        v2_acceptance = raw_blob_bytes(root, REJECTED_V2_ACCEPTANCE_BLOB)
        if hashlib.sha256(v2_acceptance).hexdigest() != REJECTED_V2_ACCEPTANCE_SHA256:
            raise P12GateError("Rejected P12 v2 acceptance content drifted")
        v3_acceptance = raw_blob_bytes(root, SUPERSEDED_V3_ACCEPTANCE_BLOB)
        if (
            hashlib.sha256(v3_acceptance).hexdigest() != SUPERSEDED_V3_ACCEPTANCE_SHA256
            or len(v3_acceptance) != SUPERSEDED_V3_ACCEPTANCE_BYTE_COUNT
            or len(v3_acceptance.splitlines()) != SUPERSEDED_V3_ACCEPTANCE_LINE_COUNT
        ):
            raise P12GateError("Superseded P12 v3 acceptance content drifted")
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
