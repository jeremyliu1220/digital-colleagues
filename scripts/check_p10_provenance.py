# SPDX-License-Identifier: Apache-2.0

"""Validate complete P10 provenance without parent-source migration."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.p10_gate_support import (
    OFFICIAL_URLS,
    SUMMARY_PATH,
    UTC_TIMESTAMP,
    GateError,
    acceptance_allowed_paths,
    emit_main,
    git,
    load_json,
    safe_relative,
)

RECEIPT = "provenance/p10-migration-receipt.json"
BASIS = "accepted_p9_p10_contract_and_listed_official_public_documentation"


def check_provenance(root: Path) -> dict[str, object]:
    allowed_paths = acceptance_allowed_paths(root)
    implementation_paths = allowed_paths - {SUMMARY_PATH}
    path = root / RECEIPT
    if not path.is_file() or path.is_symlink():
        raise GateError("receipt_file_invalid")
    receipt = load_json(path)
    if set(receipt) != {
        "schema_version",
        "milestone",
        "source_basis",
        "parent_research_working_tree_read",
        "source_migration_count",
        "transformed_migration_count",
        "official_documentation",
        "new_implementations",
    }:
        raise GateError("receipt_shape_invalid")
    if (
        receipt["schema_version"] != 1
        or receipt["milestone"] != "P10"
        or receipt["source_basis"] != BASIS
    ):
        raise GateError("receipt_identity_invalid")
    if (
        receipt["parent_research_working_tree_read"] is not False
        or receipt["source_migration_count"] != 0
        or receipt["transformed_migration_count"] != 0
    ):
        raise GateError("source_migration_boundary_invalid")
    documents = receipt["official_documentation"]
    if not isinstance(documents, list) or {
        item.get("url") for item in documents if isinstance(item, dict)
    } != set(OFFICIAL_URLS):
        raise GateError("official_documentation_inventory_invalid")
    for item in documents:
        if (
            not isinstance(item, dict)
            or set(item) != {"url", "checked_at", "observed_contract"}
            or not isinstance(item["checked_at"], str)
            or not UTC_TIMESTAMP.fullmatch(item["checked_at"])
            or not isinstance(item["observed_contract"], str)
            or not item["observed_contract"].strip()
        ):
            raise GateError("official_documentation_entry_invalid")
    entries = receipt["new_implementations"]
    if not isinstance(entries, list):
        raise GateError("implementation_inventory_invalid")
    destinations: set[str] = set()
    for item in entries:
        if not isinstance(item, dict) or set(item) != {
            "destination",
            "classification",
            "implementation_basis",
            "gate_result",
        }:
            raise GateError("implementation_entry_invalid")
        destination = safe_relative(item["destination"])
        if (
            destination in destinations
            or item["classification"] != "new_or_modified_p10_implementation"
            or item["implementation_basis"] != BASIS
            or item["gate_result"] != "not_a_source_migration"
        ):
            raise GateError("implementation_classification_invalid")
        destinations.add(destination)
    if destinations != implementation_paths:
        raise GateError("provenance_coverage_invalid")
    committed = {
        line
        for line in str(
            git(
                root,
                "diff",
                "--name-only",
                "11aa240af8db2ca515325dc059b1a77f7badc874",
                "HEAD",
                "--",
            )
        ).splitlines()
        if line
    }
    if committed not in (set(implementation_paths), set(allowed_paths)):
        raise GateError("committed_phase_invalid")
    text = path.read_text(encoding="utf-8")
    if (
        str(root) in text
        or str(Path.home()) in text
        or "/.codex/attachments/" in text
        or any(value in text.lower() for value in ("client_secret", "bearer ", "access_token"))
    ):
        raise GateError("private_material_in_receipt")
    return {
        "schema_version": 1,
        "gate": "p10_provenance_clean",
        "source_migration_count": 0,
        "transformed_migration_count": 0,
        "new_implementation_count": len(destinations),
        "official_documentation_count": len(documents),
        "parent_research_working_tree_read": False,
        "receipt_digest": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    return emit_main(check_provenance, argv, __doc__)


if __name__ == "__main__":
    raise SystemExit(main())
