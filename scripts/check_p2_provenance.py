# SPDX-License-Identifier: Apache-2.0

"""Validate the sanitized P2 migration receipt and new-implementation boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any

FIXED_SOURCE_REVISION = "dea9a9accc82fbedd35deb7117dcb5173223cf44"
SOURCE_LABEL = "digital-colleague-runtime-research"
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
NEW_IMPLEMENTATION_FIELDS = {
    "destination",
    "classification",
    "implementation_basis",
    "gate_result",
}


class ProvenanceError(RuntimeError):
    """A P2 receipt is incomplete, unsafe, or inconsistent."""


def _safe_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ProvenanceError("a receipt destination is invalid")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or ".." in candidate.parts or value.endswith("/"):
        raise ProvenanceError("receipt paths must be repository-relative files")
    return candidate.as_posix()


def _framed_digest(root: Path, destinations: list[str]) -> str:
    aggregate = hashlib.sha256()
    for destination in sorted(destinations):
        document = root / destination
        if not document.is_file():
            raise ProvenanceError("a new implementation destination is unavailable")
        content_digest = hashlib.sha256(document.read_bytes()).digest()
        for value in (destination.encode("utf-8"), content_digest):
            aggregate.update(len(value).to_bytes(8, "big"))
            aggregate.update(value)
    return "sha256:" + aggregate.hexdigest()


def check_p2_provenance(root: Path) -> dict[str, object]:
    receipt_path = root / "provenance/p2-migration-receipt.json"
    try:
        receipt: Any = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProvenanceError("the P2 migration receipt is unreadable") from exc
    if not isinstance(receipt, dict):
        raise ProvenanceError("the P2 migration receipt must be an object")
    expected_fields = {
        "schema_version",
        "milestone",
        "source_label",
        "fixed_source_revision",
        "transformed_entries",
        "new_implementations",
    }
    if set(receipt) != expected_fields:
        raise ProvenanceError("the P2 migration receipt has unexpected fields")
    if receipt.get("schema_version") != 1 or receipt.get("milestone") != "P2":
        raise ProvenanceError("the P2 migration receipt version is unsupported")
    if receipt.get("source_label") != SOURCE_LABEL:
        raise ProvenanceError("the P2 source label changed")
    if receipt.get("fixed_source_revision") != FIXED_SOURCE_REVISION:
        raise ProvenanceError("the P2 source revision changed")

    transformed = receipt.get("transformed_entries")
    if not isinstance(transformed, list):
        raise ProvenanceError("transformed_entries must be a list")
    for entry in transformed:
        if not isinstance(entry, dict) or set(entry) != TRANSFORMED_FIELDS:
            raise ProvenanceError("a transformed entry does not use the approved receipt fields")
        _safe_path(entry["source_path"])
        _safe_path(entry["destination"])

    implementations = receipt.get("new_implementations")
    if not isinstance(implementations, list) or not implementations:
        raise ProvenanceError("P2 must identify its new implementations")
    destinations: list[str] = []
    for entry in implementations:
        if not isinstance(entry, dict) or set(entry) != NEW_IMPLEMENTATION_FIELDS:
            raise ProvenanceError("a new implementation entry has unexpected fields")
        destination = _safe_path(entry["destination"])
        if not destination.startswith(
            ("src/digital_colleagues/core/", "src/digital_colleagues/governance/")
        ):
            raise ProvenanceError("new implementation is outside the P2 product boundary")
        if entry.get("classification") != "new_implementation":
            raise ProvenanceError("new implementation classification is invalid")
        if entry.get("implementation_basis") != "public_architecture_documents":
            raise ProvenanceError("new implementation basis is invalid")
        if entry.get("gate_result") != "not_a_source_migration":
            raise ProvenanceError("new implementation must not claim source migration")
        destinations.append(destination)
    if len(destinations) != len(set(destinations)):
        raise ProvenanceError("receipt destinations must be unique")

    actual_product_files = {
        document.relative_to(root).as_posix()
        for directory in (
            root / "src/digital_colleagues/core",
            root / "src/digital_colleagues/governance",
        )
        for document in directory.rglob("*.py")
    }
    if set(destinations) != actual_product_files:
        raise ProvenanceError("receipt does not cover every P2 product implementation")
    receipt_digest = "sha256:" + hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    return {
        "schema_version": 1,
        "gate": "p2_provenance_clean",
        "source_revision": FIXED_SOURCE_REVISION,
        "transformed_migration_count": len(transformed),
        "new_implementation_count": len(destinations),
        "receipt_digest": receipt_digest,
        "new_implementation_digest": _framed_digest(root, destinations),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the P2 migration receipt.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_p2_provenance(Path(arguments.root))
    except (OSError, ProvenanceError) as exc:
        print(f"P2 provenance check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
