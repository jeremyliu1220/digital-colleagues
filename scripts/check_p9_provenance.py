# SPDX-License-Identifier: Apache-2.0

"""Validate complete P9 governance provenance without source migration."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p9_repository import BASE_COMMIT, P9_ALLOWED_PATHS, SUMMARY_PATH

RECEIPT = "provenance/p9-migration-receipt.json"
EXCLUDED = {RECEIPT, SUMMARY_PATH}
FIELDS = {"destination", "classification", "implementation_basis", "gate_result"}
BASIS = (
    "approved_v0_2_product_decisions_public_official_documentation_and_accepted_p8_implementation"
)
CLASSIFICATION = "new_or_modified_p9_governance"
GATE_RESULT = "not_a_source_migration"


class ProvenanceError(RuntimeError):
    """P9 provenance coverage is incomplete or unsafe."""


def _git(root: Path, *arguments: str, text: bool = True) -> str | bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=text,
        check=False,
    )
    if completed.returncode != 0:
        raise ProvenanceError("Git P9 provenance inspection failed")
    return cast(str | bytes, completed.stdout)


def _safe_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ProvenanceError("receipt destination is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ProvenanceError("receipt destination is not repository-relative")
    return value


def changed_files(root: Path) -> set[str]:
    output = _git(root, "diff", "--name-only", BASE_COMMIT, "HEAD", "--")
    assert isinstance(output, str)
    return {path for path in output.splitlines() if path and path not in EXCLUDED}


def framed_digest(root: Path, paths: set[str]) -> str:
    aggregate = hashlib.sha256()
    for relative in sorted(paths):
        content = _git(root, "show", f"HEAD:{relative}", text=False)
        assert isinstance(content, bytes)
        for value in (relative.encode(), hashlib.sha256(content).digest()):
            aggregate.update(len(value).to_bytes(8, "big"))
            aggregate.update(value)
    return "sha256:" + aggregate.hexdigest()


def check_provenance(root: Path) -> dict[str, object]:
    root = root.resolve()
    top = _git(root, "rev-parse", "--show-toplevel")
    assert isinstance(top, str)
    if Path(top.strip()).resolve() != root:
        raise ProvenanceError("P9 provenance repository root is not exact")

    committed = set(
        line
        for line in str(_git(root, "diff", "--name-only", BASE_COMMIT, "HEAD", "--")).splitlines()
        if line
    )
    allowed_phases = {frozenset(P9_ALLOWED_PATHS), frozenset(P9_ALLOWED_PATHS - {SUMMARY_PATH})}
    if frozenset(committed) not in allowed_phases:
        raise ProvenanceError("P9 committed delta is incomplete or outside the allowlist")

    path = root / RECEIPT
    try:
        if not path.is_file() or path.is_symlink():
            raise ProvenanceError("P9 receipt has an unsafe file type")
        receipt_bytes = path.read_bytes()
        accepted_receipt = _git(root, "show", f"HEAD:{RECEIPT}", text=False)
        assert isinstance(accepted_receipt, bytes)
        if receipt_bytes != accepted_receipt:
            raise ProvenanceError("the committed P9 receipt changed")
        receipt: Any = json.loads(receipt_bytes.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProvenanceError("P9 receipt is unreadable") from exc
    if not isinstance(receipt, dict) or set(receipt) != {
        "schema_version",
        "milestone",
        "source_basis",
        "transformed_entries",
        "new_implementations",
    }:
        raise ProvenanceError("P9 receipt shape is unsupported")
    if receipt["schema_version"] != 1 or receipt["milestone"] != "P9":
        raise ProvenanceError("P9 receipt identity is unsupported")
    if receipt["source_basis"] != BASIS or receipt["transformed_entries"] != []:
        raise ProvenanceError("P9 source classification drifted")
    entries = receipt["new_implementations"]
    if not isinstance(entries, list):
        raise ProvenanceError("P9 implementation entries must be a list")
    destinations: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != FIELDS:
            raise ProvenanceError("a P9 implementation entry has unsafe fields")
        if (
            entry["classification"] != CLASSIFICATION
            or entry["implementation_basis"] != BASIS
            or entry["gate_result"] != GATE_RESULT
        ):
            raise ProvenanceError("a P9 implementation classification is invalid")
        destination = _safe_path(entry["destination"])
        if destination in destinations:
            raise ProvenanceError("P9 receipt destinations are duplicated")
        destinations.add(destination)

    actual = changed_files(root)
    if destinations != actual or actual != P9_ALLOWED_PATHS - EXCLUDED:
        raise ProvenanceError("P9 receipt does not cover the complete change inventory")
    forbidden_markers = (str(root), str(Path.home()), "/.codex/attachments/")
    decoded = receipt_bytes.decode("utf-8")
    if any(marker and marker in decoded for marker in forbidden_markers):
        raise ProvenanceError("P9 receipt contains a local or attachment path")
    if any(marker in decoded.lower() for marker in ("tenant-id", "client_secret", "bearer ")):
        raise ProvenanceError("P9 receipt contains private or credential-shaped material")

    return {
        "schema_version": 1,
        "gate": "p9_provenance_clean",
        "implementation_range": f"{BASE_COMMIT}..HEAD",
        "transformed_migration_count": 0,
        "new_implementation_count": len(destinations),
        "source_basis": BASIS,
        "receipt_digest": "sha256:" + hashlib.sha256(receipt_bytes).hexdigest(),
        "implementation_tree_digest": framed_digest(root, actual),
        "parent_working_tree_read": False,
        "source_migration_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate complete P9 provenance.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_provenance(Path(arguments.root))
    except (OSError, ProvenanceError) as exc:
        print(f"P9 provenance check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
