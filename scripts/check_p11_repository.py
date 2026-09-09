# SPDX-License-Identifier: Apache-2.0

"""Verify P11 ancestry, immutable contract, path scope, and historical boundary."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.p11_gate_support import (  # noqa: E402
    ACCEPTANCE_COMMIT,
    BASE_COMMIT,
    BRANCH,
    SUMMARY_PATH,
    GateError,
    acceptance_paths,
    git,
)


def _working_paths(root: Path) -> set[str]:
    tracked = set(git(root, "diff", "--name-only", BASE_COMMIT).splitlines())
    untracked = set(git(root, "ls-files", "--others", "--exclude-standard").splitlines())
    return {value for value in tracked | untracked if value}


def check_repository(root: Path) -> dict[str, object]:
    paths = acceptance_paths(root)
    if git(root, "branch", "--show-current") != BRANCH:
        raise GateError("P11 branch identity is invalid")
    if git(root, "merge-base", "HEAD", BASE_COMMIT) != BASE_COMMIT:
        raise GateError("P11 base ancestry is invalid")
    if git(root, "merge-base", "HEAD", ACCEPTANCE_COMMIT) != ACCEPTANCE_COMMIT:
        raise GateError("P11 implementation does not descend from its acceptance commit")
    if (
        git(root, "rev-parse", "main") != BASE_COMMIT
        or git(root, "rev-parse", "origin/main") != BASE_COMMIT
    ):
        raise GateError("P11 development moved the accepted local or remote main reference")
    if git(root, "rev-list", "--merges", f"{BASE_COMMIT}..HEAD"):
        raise GateError("P11 development history contains a merge commit")
    if git(root, "rev-parse", f"{ACCEPTANCE_COMMIT}^") != BASE_COMMIT:
        raise GateError("P11 acceptance commit is not first after the exact base")
    acceptance_change = tuple(
        git(
            root, "diff-tree", "--no-commit-id", "--name-only", "-r", ACCEPTANCE_COMMIT
        ).splitlines()
    )
    if acceptance_change != ("docs/p11/acceptance.md",):
        raise GateError("P11 acceptance commit is not isolated")
    committed_blob = git(root, "rev-parse", f"{ACCEPTANCE_COMMIT}:docs/p11/acceptance.md")
    working_blob = git(root, "hash-object", "docs/p11/acceptance.md")
    if working_blob != committed_blob:
        raise GateError("P11 acceptance contract drifted")
    changed = _working_paths(root)
    allowed = set(paths)
    if not changed <= allowed:
        raise GateError("P11 changed path escaped the exact allowlist")
    required = allowed - {SUMMARY_PATH}
    if not required <= changed:
        raise GateError("P11 implementation path set is incomplete")
    for relative in changed:
        candidate = root / relative
        if not candidate.exists() or candidate.is_symlink():
            raise GateError("P11 path deletion or link is forbidden")
        mode = os.lstat(candidate).st_mode
        if not stat.S_ISREG(mode):
            raise GateError("P11 changed paths must be regular files")
    historical = {
        path
        for path in changed
        if path.startswith(tuple(f"docs/p{value}/" for value in range(0, 11)))
        or path.startswith(tuple(f"artifacts/p{value}/" for value in range(0, 11)))
        or path
        in {
            f"migrations/{value:03d}_{name}.sql"
            for value, name in (
                (1, "initial"),
                (2, "runtime_indexes"),
                (3, "timer_triggers"),
                (4, "local_authentication"),
                (5, "evaluation_observations"),
                (6, "revisioned_colleague_builder"),
                (7, "governance_hardening"),
            )
        }
    }
    if historical:
        raise GateError("accepted P0-P10 history drifted")
    return {
        "schema_version": 1,
        "gate": "p11_repository",
        "status": "passed",
        "branch": BRANCH,
        "base": BASE_COMMIT,
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "allowlist_count": len(paths),
        "changed_count": len(changed),
        "historical_drift_count": 0,
        "unexpected_path_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_repository(Path(arguments.root).resolve())
    except (OSError, GateError) as exc:
        print(f"P11 repository check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
