# SPDX-License-Identifier: Apache-2.0

"""Validate retained P3 receipt coverage and sanitized source classification."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any

SOURCE_REVISION = "dea9a9accc82fbedd35deb7117dcb5173223cf44"
SOURCE_LABEL = "digital-colleague-runtime-research"
NEW_FIELDS = {"destination", "classification", "implementation_basis", "gate_result"}
TRANSFORMED_FIELDS = {
    "source_label",
    "fixed_source_revision",
    "source_path",
    "destination",
    "verified_source_digest",
    "classification",
    "required_transform",
    "transformation_tool_version",
    "destination_digest",
    "reviewer_role",
    "gate_result",
}


class ProvenanceError(RuntimeError):
    """The P3 provenance receipt is incomplete, unsafe, or inconsistent."""


def _safe_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ProvenanceError("receipt path is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value.endswith("/"):
        raise ProvenanceError("receipt paths must be repository-relative files")
    return path.as_posix()


def _framed_digest(root: Path, paths: set[str]) -> str:
    aggregate = hashlib.sha256()
    for relative in sorted(paths):
        content = hashlib.sha256((root / relative).read_bytes()).digest()
        for value in (relative.encode("utf-8"), content):
            aggregate.update(len(value).to_bytes(8, "big"))
            aggregate.update(value)
    return "sha256:" + aggregate.hexdigest()


def check_provenance(root: Path) -> dict[str, object]:
    path = root / "provenance/p3-migration-receipt.json"
    try:
        receipt: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProvenanceError("P3 receipt is unreadable") from exc
    expected = {
        "schema_version",
        "milestone",
        "source_label",
        "fixed_source_revision",
        "transformed_entries",
        "new_implementations",
    }
    if not isinstance(receipt, dict) or set(receipt) != expected:
        raise ProvenanceError("P3 receipt has an unsupported shape")
    if receipt["schema_version"] != 1 or receipt["milestone"] != "P3":
        raise ProvenanceError("P3 receipt version is unsupported")
    if (
        receipt["source_label"] != SOURCE_LABEL
        or receipt["fixed_source_revision"] != SOURCE_REVISION
    ):
        raise ProvenanceError("P3 source identity drifted")
    transformed = receipt["transformed_entries"]
    implementations = receipt["new_implementations"]
    if not isinstance(transformed, list) or not isinstance(implementations, list):
        raise ProvenanceError("P3 receipt entries must be lists")
    destinations: set[str] = set()
    for entry in transformed:
        if not isinstance(entry, dict) or set(entry) != TRANSFORMED_FIELDS:
            raise ProvenanceError("a transformed receipt entry uses unsafe fields")
        if (
            entry["source_label"] != SOURCE_LABEL
            or entry["fixed_source_revision"] != SOURCE_REVISION
        ):
            raise ProvenanceError("a transformed entry source identity drifted")
        destinations.add(_safe_path(entry["destination"]))
        _safe_path(entry["source_path"])
    for entry in implementations:
        if not isinstance(entry, dict) or set(entry) != NEW_FIELDS:
            raise ProvenanceError("a new implementation entry uses unexpected fields")
        if (
            entry["classification"] != "new_implementation"
            or entry["implementation_basis"] != "public_architecture_documents"
            or entry["gate_result"] != "not_a_source_migration"
        ):
            raise ProvenanceError("new implementation classification is invalid")
        destination = _safe_path(entry["destination"])
        if destination in destinations:
            raise ProvenanceError("P3 receipt destinations are duplicated")
        destinations.add(destination)
    # The receipt is the immutable P3-stage inventory. Later milestones add files
    # inside the same package roots, so a current-tree recursive scan would make
    # the historical P3 gate reject valid additive work. Current-stage completeness
    # is enforced by that stage's provenance gate.
    actual = {destination for destination in destinations if (root / destination).is_file()}
    if destinations != actual:
        raise ProvenanceError("a retained P3 receipt destination is missing")
    return {
        "schema_version": 1,
        "gate": "p3_provenance_clean",
        "source_revision": SOURCE_REVISION,
        "transformed_migration_count": len(transformed),
        "new_implementation_count": len(implementations),
        "receipt_digest": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
        "implementation_tree_digest": _framed_digest(root, actual),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P3 provenance coverage.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_provenance(Path(arguments.root))
    except (OSError, ProvenanceError) as exc:
        print(f"P3 provenance check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
