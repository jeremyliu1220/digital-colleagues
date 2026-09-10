# SPDX-License-Identifier: Apache-2.0

"""Validate exact P12 governance provenance and protected historical identities."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p12_migrations import MANIFEST, MIGRATIONS, OWNERS  # noqa: E402
from scripts.check_p12_repository import (  # noqa: E402
    ACCEPTANCE_BLOB,
    ACCEPTANCE_COMMIT,
    ACCEPTANCE_SHA256,
    ACCEPTANCE_TREE,
    BASE_COMMIT,
    BASE_TREE,
    REJECTED_COMMIT,
    P12GateError,
    git,
    implementation_paths,
)

RECEIPT_PATH = "provenance/p12-change-receipt.json"
P10_RUNS = {
    "34202520699": ("05e73ea23ac650edfae59fa409a770fdf967af3a", "success"),
    "34203006909": ("05e73ea23ac650edfae59fa409a770fdf967af3a", "failure"),
    "34204280131": ("ddc04021f94ca888235c53f96ed64218de8c3e67", "failure"),
    "34204837101": ("ae714c128f844466c76811986c0605e39fce12cc", "failure"),
    "34205272328": ("76b278feedbb79b9a4c0d023e328911096fe57ae", "failure"),
    "34206039435": ("a003d540093df9a08437c47e9c8ff16970e5e645", "success"),
    "34235760264": ("62b226064d2597a4ca6a67f9f2c20a79a815732b", "success"),
    "34236719816": ("d9fd27670a36f699bf299f6154afce180bea64cc", "failure"),
    "34237810474": ("cc4acd3bda3f4d2bdfee9392c7d0f85f90c07688", "success"),
}
P10_SUBJECTS = (
    "ghcr.io/jeremyliu1220/digital-colleagues-runtime",
    "ghcr.io/jeremyliu1220/digital-colleagues-studio",
)
P10_SETS = {
    "superseded": {
        "source_commit": "05e73ea23ac650edfae59fa409a770fdf967af3a",
        "source_tag": "sha-05e73ea23ac650edfae59fa409a770fdf967af3a",
        "runtime_digest": "sha256:41567ba87a088944cf9a2c17b9b0f4359554c66b2ec1f6d52db46067e1ab9092",
        "studio_digest": "sha256:b7dd4c2b35922ec31a9b38c15316283706a9aab0ffab2101a18f7bf106165f2e",
        "lifecycle": "superseded_contract_noncompliant_source",
    },
    "active": {
        "source_commit": "62b226064d2597a4ca6a67f9f2c20a79a815732b",
        "source_tag": "sha-62b226064d2597a4ca6a67f9f2c20a79a815732b",
        "runtime_digest": "sha256:a5bb41bdb85bf7b5a75dc79967e26943c098b024b64fdd345f5b4c6f4688991d",
        "studio_digest": "sha256:7791d80d9fa464bbd1574601deba5a30ca6d980dab8c8275c24c117fae81e4c9",
        "lifecycle": "passed",
    },
}
HISTORY = {
    "p9_final": "11aa240af8db2ca515325dc059b1a77f7badc874",
    "p10_final": "4bef5629d450c6bb3940f606fc90194e008ee8fd",
    "p11_final": "7e5387f148f86b5c9b07820dd8b8f4e18e12dc38",
    "p11r_acceptance": "61d5c94e24157b93bc4b4bcca42b4d8d2eab8fec",
    "p11r_implementation": "4a6df2db5c964b2bd6f052db6276dc303524230b",
    "p11r_final": BASE_COMMIT,
}
P10_GIT_IDENTITIES = {
    "4bef5629d450c6bb3940f606fc90194e008ee8fd^{tree}": "909b566b7ba9f7beb143cd0b29cf95fbd1178bbe",
    "99b0045bba48de8e4d44c10ce07d60ba20738a8b:docs/p10/acceptance.md": "c5ac3acd52a8732da617ce5d1d3a7e66e3671c80",
    "4bef5629d450c6bb3940f606fc90194e008ee8fd:artifacts/p10/summary.json": "a4c1a59fffec9c30160787a7bec584e228fb9f35",
    "4bef5629d450c6bb3940f606fc90194e008ee8fd:provenance/p10-migration-receipt.json": "07565307a35902206ee7c80af66b2a02ab876b83",
    "4bef5629d450c6bb3940f606fc90194e008ee8fd:distribution/p10/verification-policy.json": "02aff9c1f3bdd745a6fc479fed635f2f782c346a",
    "4bef5629d450c6bb3940f606fc90194e008ee8fd:docs/p10/distribution.md": "c55393db711f2db49169fbe35e45f5f5e227849a",
}


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise P12GateError("P12 provenance receipt is unavailable or invalid") from exc


def _dict(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise P12GateError(f"P12 provenance {label} is invalid")
    return value


def check_provenance(root: Path) -> dict[str, object]:
    receipt = _dict(_read_json(root / RECEIPT_PATH), "root")
    if (
        receipt.get("schema_version") != 1
        or receipt.get("change") != "P12"
        or receipt.get("classification") != "governance_only_continuity_rebaseline"
        or receipt.get("base_commit") != BASE_COMMIT
        or receipt.get("base_tree") != BASE_TREE
        or receipt.get("rejected_v1_commit") != REJECTED_COMMIT
    ):
        raise P12GateError("P12 provenance identity is invalid")
    acceptance = _dict(receipt.get("acceptance"), "acceptance")
    if acceptance != {
        "commit": ACCEPTANCE_COMMIT,
        "tree": ACCEPTANCE_TREE,
        "blob": ACCEPTANCE_BLOB,
        "sha256": ACCEPTANCE_SHA256,
    }:
        raise P12GateError("P12 provenance acceptance binding is invalid")
    if receipt.get("covered_paths") != list(implementation_paths(root)):
        raise P12GateError("P12 provenance path coverage is not exact and ordered")
    if (
        receipt.get("parent_research_working_tree_read") is not False
        or receipt.get("source_migration_count") != 0
        or receipt.get("transformed_migration_count") != 0
    ):
        raise P12GateError("P12 source provenance boundary is invalid")
    if _dict(receipt.get("historical_anchors"), "historical anchors") != HISTORY:
        raise P12GateError("P12 historical anchor coverage is invalid")
    for expression, expected in P10_GIT_IDENTITIES.items():
        if git(root, "rev-parse", expression) != expected:
            raise P12GateError("P12 protected P10 local Git identity drifted")
    for commit in (
        "05e73ea23ac650edfae59fa409a770fdf967af3a",
        "62b226064d2597a4ca6a67f9f2c20a79a815732b",
    ):
        if git(root, "cat-file", "-t", commit) != "commit":
            raise P12GateError("P12 protected P10 source commit is unreadable")
    migration = _dict(receipt.get("migration_protection"), "migration protection")
    expected_files = [
        {"path": MANIFEST[0], "blob": MANIFEST[1], "sha256": MANIFEST[2]},
        *[
            {"path": f"migrations/{name}", "blob": blob, "sha256": digest}
            for name, blob, digest in MIGRATIONS
        ],
    ]
    if migration.get("immutable_files") != expected_files:
        raise P12GateError("P12 immutable migration provenance is incomplete")
    if migration.get("future_owners") != OWNERS:
        raise P12GateError("P12 future migration ownership provenance drifted")
    p10 = _dict(receipt.get("p10_protected_publication"), "P10 publication")
    if (
        p10.get("subjects") != list(P10_SUBJECTS)
        or p10.get("sets") != P10_SETS
        or p10.get("runs")
        != {
            run: {"head": identity[0], "conclusion": identity[1]}
            for run, identity in P10_RUNS.items()
        }
        or p10.get("receipt")
        != {
            "path": "provenance/p10-migration-receipt.json",
            "blob": "07565307a35902206ee7c80af66b2a02ab876b83",
        }
        or p10.get("runtime_version_count") != 14
        or p10.get("studio_version_count") != 14
        or p10.get("inventory_sha256")
        != "b58cce2af1e3b672114b050ffd6cb55e9625cbcb8fb54c0a863ea00ebb617f3c"
        or p10.get("overwrite_retag_republish_delete_forbidden") is not True
    ):
        raise P12GateError("P12 complete P10 protection identity is invalid")
    counts = _dict(receipt.get("change_counts"), "change counts")
    if not counts or any(value != 0 for value in counts.values()):
        raise P12GateError("P12 product, evidence, schema, or migration count is nonzero")
    privacy = _dict(receipt.get("privacy"), "privacy")
    publication = _dict(receipt.get("publication"), "publication")
    if any(value is not False for value in privacy.values()) or any(
        value is not False for value in publication.values()
    ):
        raise P12GateError("P12 privacy or zero-publication declaration is invalid")
    serialized = json.dumps(receipt, ensure_ascii=False)
    if any(marker in serialized for marker in ("/Users/", ".codex/", "sk-", "dc_session=")):
        raise P12GateError("P12 provenance contains local, private, or credential material")
    return {
        "schema_version": 1,
        "gate": "p12_provenance",
        "status": "passed",
        "covered_path_count": len(receipt["covered_paths"]),
        "historical_anchor_count": len(HISTORY),
        "immutable_migration_file_count": len(expected_files),
        "protected_p10_subject_count": len(P10_SUBJECTS),
        "protected_p10_set_count": len(P10_SETS),
        "protected_p10_run_count": len(P10_RUNS),
        "protected_p10_local_git_identity_count": len(P10_GIT_IDENTITIES) + 2,
        "source_migration_count": 0,
        "privacy_leak_count": 0,
        "publication_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        result = check_provenance(Path(args.root).resolve())
    except P12GateError as exc:
        print(f"P12 provenance check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
