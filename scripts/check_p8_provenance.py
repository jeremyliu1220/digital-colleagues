# SPDX-License-Identifier: Apache-2.0

"""Validate complete P8 change provenance with zero parent-source migration."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p8_repository import ACCEPTED_P8_COMMIT
from scripts.p8_release_support import BASE_COMMIT

RECEIPT = "provenance/p8-migration-receipt.json"
EXCLUDED = {RECEIPT, "artifacts/p8/summary.json"}
FIELDS = {"destination", "classification", "implementation_basis", "gate_result"}
BASIS = "public_documents_and_accepted_p7_implementation"


class ProvenanceError(RuntimeError):
    """P8 provenance coverage is incomplete or unsafe."""


def _git(root: Path, *arguments: str) -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ProvenanceError("Git P8 change inventory failed")
    return tuple(line for line in completed.stdout.splitlines() if line)


def _git_object(root: Path, revision_path: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", revision_path],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise ProvenanceError("an accepted P8 Git object is unavailable")
    return completed.stdout


def _require_commit(root: Path) -> None:
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{ACCEPTED_P8_COMMIT}^{{commit}}"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise ProvenanceError("the accepted P8 commit is unavailable")


def _require_accepted_ancestor(root: Path) -> None:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ACCEPTED_P8_COMMIT, "HEAD"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode == 1:
        raise ProvenanceError("the accepted P8 commit is not an ancestor of HEAD")
    if completed.returncode != 0:
        raise ProvenanceError("Git P8 ancestry inspection failed")


def _safe_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ProvenanceError("receipt destination is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value.endswith("/"):
        raise ProvenanceError("receipt destination is not repository-relative")
    return path.as_posix()


def changed_files(root: Path) -> set[str]:
    changed = set(_git(root, "diff", "--name-only", BASE_COMMIT, ACCEPTED_P8_COMMIT, "--"))
    return {path for path in changed if path not in EXCLUDED}


def framed_digest(root: Path, paths: set[str]) -> str:
    aggregate = hashlib.sha256()
    for relative in sorted(paths):
        content = _git_object(root, f"{ACCEPTED_P8_COMMIT}:{relative}")
        for value in (relative.encode(), hashlib.sha256(content).digest()):
            aggregate.update(len(value).to_bytes(8, "big"))
            aggregate.update(value)
    return "sha256:" + aggregate.hexdigest()


def check_provenance(root: Path) -> dict[str, object]:
    root = root.resolve()
    _require_commit(root)
    _require_accepted_ancestor(root)
    path = root / RECEIPT
    try:
        current_receipt = path.read_bytes()
        accepted_receipt = _git_object(root, f"{ACCEPTED_P8_COMMIT}:{RECEIPT}")
        if current_receipt != accepted_receipt:
            raise ProvenanceError("the accepted P8 receipt changed")
        receipt: Any = json.loads(accepted_receipt.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProvenanceError("P8 receipt is unreadable") from exc
    if not isinstance(receipt, dict) or set(receipt) != {
        "schema_version",
        "milestone",
        "source_basis",
        "transformed_entries",
        "new_implementations",
    }:
        raise ProvenanceError("P8 receipt shape is unsupported")
    if receipt["schema_version"] != 1 or receipt["milestone"] != "P8":
        raise ProvenanceError("P8 receipt identity is unsupported")
    if receipt["source_basis"] != BASIS or receipt["transformed_entries"] != []:
        raise ProvenanceError("P8 source classification drifted")
    entries = receipt["new_implementations"]
    if not isinstance(entries, list):
        raise ProvenanceError("P8 implementation entries must be a list")
    destinations: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != FIELDS:
            raise ProvenanceError("a P8 implementation entry has unsafe fields")
        if (
            entry["classification"] != "new_implementation"
            or entry["implementation_basis"] != BASIS
            or entry["gate_result"] != "not_a_source_migration"
        ):
            raise ProvenanceError("a P8 implementation classification is invalid")
        destination = _safe_path(entry["destination"])
        if destination in destinations:
            raise ProvenanceError("P8 receipt destinations are duplicated")
        destinations.add(destination)
    actual = changed_files(root)
    if destinations != actual:
        raise ProvenanceError("P8 receipt does not cover the complete change inventory")
    return {
        "schema_version": 1,
        "gate": "p8_provenance_clean",
        "accepted_p8_commit": ACCEPTED_P8_COMMIT,
        "implementation_range": f"{BASE_COMMIT}..{ACCEPTED_P8_COMMIT}",
        "transformed_migration_count": 0,
        "new_implementation_count": len(destinations),
        "source_basis": BASIS,
        "receipt_digest": "sha256:" + hashlib.sha256(accepted_receipt).hexdigest(),
        "implementation_tree_digest": framed_digest(root, actual),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate complete P8 provenance.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_provenance(Path(arguments.root).resolve())
    except (OSError, ProvenanceError) as exc:
        print(f"P8 provenance check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
