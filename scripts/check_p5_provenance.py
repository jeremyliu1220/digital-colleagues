# SPDX-License-Identifier: Apache-2.0

"""Validate complete P5 change coverage with zero transformed parent source."""

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

from scripts.check_p5_repository import BASE_COMMIT

RECEIPT = "provenance/p5-migration-receipt.json"
EXCLUDED = {RECEIPT, "artifacts/p5/summary.json"}
FIELDS = {"destination", "classification", "implementation_basis", "gate_result"}
BASIS = "public_documents_and_accepted_p4_implementation"


class ProvenanceError(RuntimeError):
    """P5 provenance coverage is incomplete or unsafe."""


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
        raise ProvenanceError("Git P5 change inventory failed")
    return tuple(line for line in completed.stdout.splitlines() if line)


def _safe_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ProvenanceError("receipt destination is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value.endswith("/"):
        raise ProvenanceError("receipt destination is not repository-relative")
    return path.as_posix()


def _changed_files(root: Path) -> set[str]:
    changed = set(_git(root, "diff", "--name-only", BASE_COMMIT, "--"))
    changed.update(_git(root, "ls-files", "--others", "--exclude-standard"))
    return {path for path in changed if path not in EXCLUDED}


def _framed_digest(root: Path, paths: set[str]) -> str:
    aggregate = hashlib.sha256()
    for relative in sorted(paths):
        document = root / relative
        if not document.is_file():
            raise ProvenanceError("a P5 implementation destination is missing")
        for value in (relative.encode(), hashlib.sha256(document.read_bytes()).digest()):
            aggregate.update(len(value).to_bytes(8, "big"))
            aggregate.update(value)
    return "sha256:" + aggregate.hexdigest()


def check_provenance(root: Path) -> dict[str, object]:
    path = root / RECEIPT
    try:
        receipt: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProvenanceError("P5 receipt is unreadable") from exc
    if not isinstance(receipt, dict) or set(receipt) != {
        "schema_version",
        "milestone",
        "source_basis",
        "transformed_entries",
        "new_implementations",
    }:
        raise ProvenanceError("P5 receipt shape is unsupported")
    if receipt["schema_version"] != 1 or receipt["milestone"] != "P5":
        raise ProvenanceError("P5 receipt identity is unsupported")
    if receipt["source_basis"] != BASIS or receipt["transformed_entries"] != []:
        raise ProvenanceError("P5 implementation source classification drifted")
    entries = receipt["new_implementations"]
    if not isinstance(entries, list):
        raise ProvenanceError("P5 implementation entries must be a list")
    destinations: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != FIELDS:
            raise ProvenanceError("a P5 implementation entry has unsafe fields")
        if (
            entry["classification"] != "new_implementation"
            or entry["implementation_basis"] != BASIS
            or entry["gate_result"] != "not_a_source_migration"
        ):
            raise ProvenanceError("a P5 implementation classification is invalid")
        destination = _safe_path(entry["destination"])
        if destination in destinations:
            raise ProvenanceError("P5 receipt destinations are duplicated")
        destinations.add(destination)
    actual = _changed_files(root)
    if destinations != actual:
        raise ProvenanceError("P5 receipt does not cover the complete change inventory")
    return {
        "schema_version": 1,
        "gate": "p5_provenance_clean",
        "transformed_migration_count": 0,
        "new_implementation_count": len(destinations),
        "receipt_digest": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
        "implementation_tree_digest": _framed_digest(root, actual),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate complete P5 provenance.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_provenance(Path(arguments.root).resolve())
    except (OSError, ProvenanceError) as exc:
        print(f"P5 provenance check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
