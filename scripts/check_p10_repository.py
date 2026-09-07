# SPDX-License-Identifier: Apache-2.0

"""Validate P10 ancestry, immutable history, exact paths, and clean state."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.p10_gate_support import (
    ACCEPTANCE_COMMIT,
    ACCEPTANCE_PATH,
    ACCEPTED_P8_COMMIT,
    BASE_COMMIT,
    BRANCH,
    IMPLEMENTATION_PATHS,
    MIGRATIONS,
    P10_ALLOWED_PATHS,
    SUMMARY_PATH,
    GateError,
    emit_main,
    git,
    safe_relative,
)

HISTORICAL_PREFIXES = tuple(
    [f"docs/p{value}/" for value in range(10)]
    + [f"artifacts/p{value}/" for value in range(10)]
    + ["migrations/"]
)
HISTORICAL_RECEIPTS = tuple(f"provenance/p{value}-migration-receipt.json" for value in range(2, 10))
FORBIDDEN_RESIDUE = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
}
FORBIDDEN_SUFFIXES = (
    ".pyc",
    ".sqlite",
    ".sqlite-wal",
    ".sqlite-shm",
    ".log",
    ".tar.gz",
    ".oci.tar",
)
P10_PRODUCT_PATHS = (
    "Dockerfile.p10",
    "compose.p10.yaml",
    "dc",
    "src/digital_colleagues/",
    "studio/",
)
FORBIDDEN_P11_MARKERS = (
    "AgentPackage",
    "ColleagueDeployment",
    "ExternalConnection",
    "ConnectorGrant",
    "AutomaticEffectAuthorization",
    "OpenAI",
    "Microsoft Graph",
    "SharePoint",
    "semantic memory",
    "embeddings",
    "multi-Agent",
    "browser automation",
    "72-hour",
)


def _exists_commit(root: Path, commit: str) -> bool:
    return (
        subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def _ancestor(root: Path, ancestor: str, descendant: str = "HEAD") -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def _changed(root: Path, start: str, end: str = "HEAD") -> set[str]:
    output = git(root, "diff", "--name-only", start, end, "--")
    assert isinstance(output, str)
    return {safe_relative(line) for line in output.splitlines() if line}


def check_repository(root: Path) -> dict[str, object]:
    root = root.resolve()
    top = git(root, "rev-parse", "--show-toplevel")
    assert isinstance(top, str)
    if Path(top.strip()).resolve() != root:
        raise GateError("repository_root_not_exact")
    if str(git(root, "status", "--porcelain=v1")).strip():
        raise GateError("clean_index_worktree_required")
    if str(git(root, "branch", "--show-current")).strip() != BRANCH:
        raise GateError("development_branch_invalid")
    for commit, label in (
        (BASE_COMMIT, "base"),
        (ACCEPTED_P8_COMMIT, "p8"),
        (ACCEPTANCE_COMMIT, "acceptance"),
    ):
        if not _exists_commit(root, commit):
            raise GateError(f"{label}_commit_unavailable")
    if (
        not _ancestor(root, ACCEPTED_P8_COMMIT, BASE_COMMIT)
        or not _ancestor(root, BASE_COMMIT)
        or not _ancestor(root, ACCEPTANCE_COMMIT)
    ):
        raise GateError("trusted_ancestry_invalid")
    if str(git(root, "merge-base", "HEAD", BASE_COMMIT)).strip() != BASE_COMMIT:
        raise GateError("merge_base_invalid")
    if str(git(root, "rev-parse", f"{ACCEPTANCE_COMMIT}^")).strip() != BASE_COMMIT:
        raise GateError("acceptance_parent_invalid")
    if _changed(root, BASE_COMMIT, ACCEPTANCE_COMMIT) != {ACCEPTANCE_PATH}:
        raise GateError("acceptance_commit_not_isolated")
    accepted = git(root, "show", f"{ACCEPTANCE_COMMIT}:{ACCEPTANCE_PATH}", binary=True)
    current = git(root, "show", f"HEAD:{ACCEPTANCE_PATH}", binary=True)
    if (
        accepted != current
        or not (root / ACCEPTANCE_PATH).is_file()
        or (root / ACCEPTANCE_PATH).read_bytes() != current
    ):
        raise GateError("acceptance_contract_changed")

    changed = _changed(root, BASE_COMMIT)
    if changed == IMPLEMENTATION_PATHS:
        phase = "implementation"
    elif changed == P10_ALLOWED_PATHS:
        phase = "final_evidence"
    else:
        missing = len(P10_ALLOWED_PATHS - changed)
        extra = len(changed - P10_ALLOWED_PATHS)
        raise GateError(f"changed_path_set_invalid_missing_{missing}_extra_{extra}")
    status = str(git(root, "diff", "--name-status", "-M", "-C", BASE_COMMIT, "HEAD", "--"))
    for line in status.splitlines():
        parts = line.split("\t")
        if not parts or parts[0][:1] not in {"A", "M"} or len(parts) != 2:
            raise GateError("rename_copy_type_or_delete_rejected")
        safe_relative(parts[1])
    if _changed(root, BASE_COMMIT, "HEAD") & (set(HISTORICAL_RECEIPTS)):
        raise GateError("historical_receipt_changed")
    historical = _changed(root, BASE_COMMIT, "HEAD")
    historical.discard(ACCEPTANCE_PATH)
    if any(path.startswith(HISTORICAL_PREFIXES) for path in historical):
        raise GateError("historical_record_changed")
    migration_files = tuple(
        sorted(path.name for path in (root / "migrations").iterdir() if path.is_file())
    )
    if (
        migration_files != tuple(sorted(MIGRATIONS))
        or (root / "migrations/008_initial.sql").exists()
    ):
        raise GateError("migration_inventory_invalid")
    for relative in changed:
        path = root / relative
        if not path.is_file() or path.is_symlink() or path.stat().st_nlink != 1:
            raise GateError("unsafe_changed_file_type")
        mode = stat.S_IMODE(path.stat().st_mode)
        expected = 0o755 if relative == "dc" else 0o644
        if mode != expected:
            raise GateError("changed_file_mode_invalid")
    for directory, names, files in os.walk(root):
        relative_dir = Path(directory).relative_to(root)
        names[:] = [name for name in names if name != ".git"]
        if any(part in FORBIDDEN_RESIDUE for part in relative_dir.parts):
            raise GateError("cleanup_residue_present")
        for name in files:
            candidate = Path(directory) / name
            candidate_mode = os.lstat(candidate).st_mode
            if not stat.S_ISREG(candidate_mode) or os.lstat(candidate).st_nlink != 1:
                raise GateError("special_symlink_or_hardlink_present")
            if name.endswith(FORBIDDEN_SUFFIXES):
                raise GateError("cleanup_residue_present")
    product_diff = str(
        git(root, "diff", "--unified=0", BASE_COMMIT, "HEAD", "--", *P10_PRODUCT_PATHS)
    )
    additions = "\n".join(
        line[1:]
        for line in product_diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    if any(marker.lower() in additions.lower() for marker in FORBIDDEN_P11_MARKERS):
        raise GateError("forbidden_p11_capability_change")
    if phase == "final_evidence":
        parent = str(git(root, "rev-parse", "HEAD^")).strip()
        if _changed(root, parent, "HEAD") != {SUMMARY_PATH}:
            raise GateError("evidence_commit_not_isolated")
    return {
        "schema_version": 1,
        "gate": "p10_repository_clean",
        "candidate_phase": phase,
        "base_commit": BASE_COMMIT,
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "changed_path_count": len(changed),
        "historical_drift_count": 0,
        "migration_count": 7,
        "migration_008": False,
        "unsafe_path_count": 0,
        "cleanup_residue_count": 0,
        "forbidden_p11_capability_change_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    return emit_main(check_repository, argv, __doc__)


if __name__ == "__main__":
    raise SystemExit(main())
