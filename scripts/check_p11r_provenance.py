# SPDX-License-Identifier: Apache-2.0

"""Validate the complete P11R implementation receipt and no-capability boundary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p11r_ci_policy import (
    NODE_ENGINE,
    NODE_VERSION,
    NPM_VERSION,
    PACKAGE_MANAGER,
)
from scripts.check_p11r_repository import (
    ACCEPTANCE_COMMIT,
    BASE_COMMIT,
    P11RGateError,
    implementation_paths,
)

RECEIPT_PATH = "provenance/p11r-change-receipt.json"


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise P11RGateError("P11R provenance receipt is unavailable or invalid") from exc


def check_provenance(root: Path) -> dict[str, object]:
    receipt = _read_json(root / RECEIPT_PATH)
    if not isinstance(receipt, dict) or receipt.get("schema_version") != 1:
        raise P11RGateError("P11R provenance receipt shape is invalid")
    if (
        receipt.get("change") != "P11R"
        or receipt.get("classification") != "post_p11_governance_and_ci_alignment"
        or receipt.get("base_commit") != BASE_COMMIT
        or receipt.get("acceptance_commit") != ACCEPTANCE_COMMIT
    ):
        raise P11RGateError("P11R provenance identity is invalid")
    covered = receipt.get("covered_paths")
    expected = list(implementation_paths(root))
    if covered != expected:
        raise P11RGateError("P11R provenance path coverage is not exact and ordered")
    if (
        receipt.get("parent_research_working_tree_read") is not False
        or receipt.get("source_migration_count") != 0
        or receipt.get("transformed_migration_count") != 0
    ):
        raise P11RGateError("P11R source provenance boundary is invalid")
    accepted = receipt.get("accepted_p11")
    if not isinstance(accepted, dict) or accepted != {
        "commit": BASE_COMMIT,
        "tree": "6d7c1b3053fefc1f3b14a4b39fde2d5adb641990",
        "acceptance_blob": "85f2a91b85d3ec223d4f458199913a3eadbaabe9",
        "implementation_tree_digest": "sha256:8bc5a7d431aae4fd1d46d94fd3af96f664b2f39d1b1d6ab679c50571ca8220e6",
    }:
        raise P11RGateError("Accepted P11 provenance binding is invalid")
    toolchain = receipt.get("toolchain")
    if not isinstance(toolchain, dict) or toolchain != {
        "node_version_file": ".nvmrc",
        "node_version": NODE_VERSION,
        "node_engine": NODE_ENGINE,
        "npm_version": NPM_VERSION,
        "package_manager": PACKAGE_MANAGER,
        "python_lock": "requirements/p8.lock",
    }:
        raise P11RGateError("P11R toolchain provenance is invalid")
    baseline = receipt.get("known_baseline")
    if not isinstance(baseline, dict) or baseline != {
        "run_id": 34414627643,
        "classification": "post_merge_ci_configuration_drift",
        "p11_product_defect": False,
        "p11_acceptance_failure": False,
    }:
        raise P11RGateError("P11R known-baseline classification is invalid")
    counts = receipt.get("change_counts")
    if not isinstance(counts, dict) or any(value != 0 for value in counts.values()):
        raise P11RGateError("P11R product, Studio, schema, or migration count is nonzero")
    privacy = receipt.get("privacy")
    publication = receipt.get("publication")
    if (
        not isinstance(privacy, dict)
        or not isinstance(publication, dict)
        or any(value is not False for value in privacy.values())
        or any(value is not False for value in publication.values())
    ):
        raise P11RGateError("P11R privacy or non-publication declaration is invalid")
    serialized = json.dumps(receipt, ensure_ascii=False)
    if any(marker in serialized for marker in ("/Users/", "sk-", "dc_session=")):
        raise P11RGateError("P11R provenance contains private or credential material")
    return {
        "schema_version": 1,
        "gate": "p11r_provenance",
        "status": "passed",
        "covered_path_count": len(covered),
        "source_migration_count": 0,
        "transformed_migration_count": 0,
        "product_change_count": 0,
        "privacy_leak_count": 0,
        "publication_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        result = check_provenance(Path(args.root).resolve())
    except P11RGateError as exc:
        print(f"P11R provenance check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
