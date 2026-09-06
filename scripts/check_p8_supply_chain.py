# SPDX-License-Identifier: Apache-2.0

"""Validate deterministic release inventory, locks, base images, Actions, and NOTICE scope."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.p8_release_support import (
    BASE_COMMIT,
    NODE_VERSION,
    NPM_VERSION,
    ReleaseError,
    build_supply_chain_inventory,
)

FROM_PATTERN = re.compile(r"^FROM\s+([^\s]+)", re.MULTILINE)
ACTION_PATTERN = re.compile(r"uses:\s*([^@\s]+)@([0-9a-f]{40})")
PACKAGE_MANAGER_PATTERN = re.compile(r"^npm@([0-9]+(?:\.[0-9]+){2})\+sha224\.[0-9a-f]{56}$")


class SupplyChainError(RuntimeError):
    """Supply-chain inputs, metadata, or attribution treatment are incomplete."""


def _git(root: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise SupplyChainError("supply-chain Git inspection failed")
    return completed.stdout


def check_supply_chain(root: Path) -> dict[str, object]:
    commit = _git(root, "rev-parse", "HEAD").decode().strip()
    first = build_supply_chain_inventory(root, commit)
    second = build_supply_chain_inventory(root, commit)
    if first != second:
        raise SupplyChainError("supply-chain inventory is not deterministic")
    records = first.get("records")
    if not isinstance(records, list) or not records:
        raise SupplyChainError("supply-chain inventory is empty")
    identities: list[tuple[str, str, str]] = []
    for record in records:
        if not isinstance(record, dict) or set(record) != {
            "ecosystem",
            "name",
            "version",
            "source_class",
            "immutable_references",
            "declared_license",
            "role",
            "included_in_release_artifact",
            "attribution_treatment",
        }:
            raise SupplyChainError("a supply-chain record is incomplete")
        references = record["immutable_references"]
        if (
            not record["declared_license"]
            or not isinstance(references, list)
            or not references
            or any(not isinstance(value, str) or not value for value in references)
        ):
            raise SupplyChainError("license or immutable reference is unresolved")
        identities.append((str(record["ecosystem"]), str(record["name"]), str(record["version"])))
    if identities != sorted(identities) or len(identities) != len(set(identities)):
        raise SupplyChainError("supply-chain ordering or identity is not deterministic")
    inputs = json.loads((root / "release/supply-chain-inputs.json").read_text(encoding="utf-8"))
    expected_bases = {
        f"{item['name'].removeprefix('docker.io/library/')}:{item['version']}@{item['digest']}"
        for item in inputs["docker_bases"]
    }
    actual_bases: set[str] = set()
    for relative in ("Dockerfile", "Dockerfile.p7", "studio/Dockerfile", "studio/Dockerfile.p7"):
        document = (root / relative).read_text(encoding="utf-8")
        matches = FROM_PATTERN.findall(document)
        if not matches or any("@sha256:" not in value for value in matches):
            raise SupplyChainError("a Docker base is mutable or missing")
        if re.search(r"\b(?:apt-get|apk|dnf|yum)\s+(?:install|add)\b", document):
            raise SupplyChainError("a Dockerfile installs an uninventoried OS package")
        actual_bases.update(matches)
    if not actual_bases.issubset(expected_bases) or len(actual_bases) != 3:
        raise SupplyChainError("Docker base inventory drifted")
    package = json.loads((root / "studio/package.json").read_text(encoding="utf-8"))
    manager = package.get("packageManager")
    manager_match = PACKAGE_MANAGER_PATTERN.fullmatch(manager) if isinstance(manager, str) else None
    studio_dockerfiles = tuple(
        (root / relative).read_text(encoding="utf-8")
        for relative in ("studio/Dockerfile", "studio/Dockerfile.p7")
    )
    node_reference = next(
        (item for item in inputs["docker_bases"] if item.get("name") == "docker.io/library/node"),
        None,
    )
    operator_versions = {item.get("name"): item.get("version") for item in inputs["operator_tools"]}
    if (
        (root / ".nvmrc").read_text(encoding="utf-8").strip() != NODE_VERSION
        or package.get("engines", {}).get("node") != f">={NODE_VERSION} <25"
        or manager_match is None
        or manager_match.group(1) != NPM_VERSION
        or operator_versions.get("node") != NODE_VERSION
        or operator_versions.get("npm") != NPM_VERSION
        or not isinstance(node_reference, dict)
        or node_reference.get("version") != f"{NODE_VERSION}-alpine"
        or any(
            f'test "$(node --version)" = "v{NODE_VERSION}"' not in document
            or f'test "$(corepack npm --version)" = "{NPM_VERSION}"' not in document
            or "corepack npm ci --ignore-scripts --no-audit" not in document
            or "corepack npm run build" not in document
            or (f'\'{{"node":"{NODE_VERSION}","npm":"{NPM_VERSION}","schema_version":1}}\'')
            not in document
            or re.search(r"(?m)^RUN npm\s", document) is not None
            for document in studio_dockerfiles
        )
    ):
        raise SupplyChainError("host, container, or declared Studio toolchain drifted")
    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    actions = set(ACTION_PATTERN.findall(workflow))
    expected_actions = {(item["name"], item["commit"]) for item in inputs["github_actions"]}
    if actions != expected_actions:
        raise SupplyChainError("GitHub Action pin inventory drifted")
    if _git(root, "show", f"{BASE_COMMIT}:NOTICE") != (root / "NOTICE").read_bytes():
        raise SupplyChainError("root NOTICE changed without a reviewed P8 decision")
    counts = Counter(str(record["ecosystem"]) for record in records)
    if counts != Counter(
        {"python": 27, "npm": 202, "oci": 3, "github_action": 3, "operator_tool": 7}
    ):
        raise SupplyChainError("supply-chain coverage count drifted")
    bundled = [
        record
        for record in records
        if record["ecosystem"] == "npm" and record["included_in_release_artifact"] is True
    ]
    if len(bundled) != 3 or any(
        record["attribution_treatment"] != "studio_THIRD_PARTY_LICENSES.txt" for record in bundled
    ):
        raise SupplyChainError("Studio bundled attribution treatment is incomplete")
    return {
        "schema_version": 1,
        "gate": "p8_supply_chain_clean",
        "record_count": len(records),
        "ecosystem_counts": dict(sorted(counts.items())),
        "python_hash_locked": True,
        "studio_integrity_locked": True,
        "docker_bases_digest_pinned": True,
        "github_actions_commit_pinned": True,
        "host_node_version": NODE_VERSION,
        "host_npm_version": NPM_VERSION,
        "container_node_version": NODE_VERSION,
        "container_npm_version": NPM_VERSION,
        "container_toolchain_build_asserted": True,
        "uninventoried_os_packages": 0,
        "bundled_studio_license_text_count": len(bundled),
        "root_notice": "unchanged_reviewed_project_notice",
        "review_class": "declared_metadata_review_not_legal_advice",
        "unresolved_licenses": 0,
        "unresolved_attributions": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P8 supply-chain inventory.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_supply_chain(Path(arguments.root).resolve())
    except (OSError, UnicodeError, json.JSONDecodeError, ReleaseError, SupplyChainError) as exc:
        print(f"P8 supply-chain check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
