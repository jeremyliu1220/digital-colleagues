# SPDX-License-Identifier: Apache-2.0

"""Verify complete P11 implementation provenance and privacy declarations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.p11_gate_support import (  # noqa: E402
    EVIDENCE_CLASSES,
    SUMMARY_PATH,
    GateError,
    acceptance_paths,
    read_json,
)

OFFICIAL_PREFIXES = ("https://docs.github.com/", "https://cli.github.com/manual/")


def check_provenance(root: Path) -> dict[str, object]:
    receipt = read_json(root / "provenance/p11-migration-receipt.json")
    if not isinstance(receipt, dict) or receipt.get("schema_version") != 1:
        raise GateError("P11 provenance receipt shape is invalid")
    expected = set(acceptance_paths(root)) - {SUMMARY_PATH}
    covered = receipt.get("covered_paths")
    if not isinstance(covered, list) or set(covered) != expected or len(covered) != len(expected):
        raise GateError("P11 provenance path coverage is incomplete")
    if receipt.get("parent_research_working_tree_read") is not False:
        raise GateError("P11 parent research boundary declaration is invalid")
    if (
        receipt.get("source_migration_count") != 0
        or receipt.get("transformed_migration_count") != 0
    ):
        raise GateError("P11 source migration counts must remain zero")
    references = receipt.get("external_references")
    if not isinstance(references, list) or len(references) < 6:
        raise GateError("P11 official attestation references are incomplete")
    for reference in references:
        if (
            not isinstance(reference, dict)
            or reference.get("checked_at") != "2026-09-09"
            or not isinstance(reference.get("url"), str)
            or not reference["url"].startswith(OFFICIAL_PREFIXES)
            or not reference.get("observed_basis")
        ):
            raise GateError("P11 external reference is not exact and official")
    privacy = receipt.get("privacy")
    if not isinstance(privacy, dict) or any(value is not False for value in privacy.values()):
        raise GateError("P11 privacy exclusion declaration is invalid")
    if tuple(receipt.get("evidence_classes", ())) != EVIDENCE_CLASSES:
        raise GateError("P11 evidence class vocabulary drifted")
    serialized = json.dumps(receipt, ensure_ascii=False)
    if "/Users/" in serialized or "sk-" in serialized or "dc_session=" in serialized:
        raise GateError("P11 provenance contains private or credential material")
    return {
        "schema_version": 1,
        "gate": "p11_provenance",
        "status": "passed",
        "covered_path_count": len(covered),
        "official_reference_count": len(references),
        "source_migration_count": 0,
        "transformed_migration_count": 0,
        "privacy_leak_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        result = check_provenance(Path(args.root).resolve())
    except (OSError, GateError) as exc:
        print(f"P11 provenance check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
