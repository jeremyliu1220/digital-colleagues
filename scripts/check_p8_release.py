# SPDX-License-Identifier: Apache-2.0

"""Build and validate the exact P8 public release-candidate artifact set."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p8_provenance import ProvenanceError, check_provenance
from scripts.check_p8_repository import RepositoryError, check_repository
from scripts.check_p8_supply_chain import SupplyChainError, check_supply_chain
from scripts.p8_release_support import (
    BASE_COMMIT,
    ReleaseError,
    build_candidate,
    validate_candidate,
)

REQUIRED_MAKE_TARGETS = (
    "p8-repository",
    "p8-provenance",
    "p8-operations",
    "p8-backup-restore",
    "p8-diagnostics",
    "p8-supply-chain",
    "p8-reproducibility",
    "p8-release",
    "p8-compose-runtime",
    "p8-golden",
    "evidence-p8",
)
MARKDOWN_LINK = re.compile(r"\]\(([^)]+)\)")


def _public_boundary(root: Path) -> None:
    completed = subprocess.run(
        [sys.executable, "-B", "scripts/check_public_boundary.py", "."],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise ReleaseError("public_boundary_failed")


def _release_documents(root: Path) -> None:
    makefile = (root / "Makefile").read_text(encoding="utf-8")
    if any(f"{target}:" not in makefile for target in REQUIRED_MAKE_TARGETS):
        raise ReleaseError("release_command_missing")
    required = {
        "README.md": ("0.1.0", "deterministic", "independent acceptance"),
        "SECURITY.md": ("0.1.0", "production", "independent acceptance"),
        "docs/development.md": ("make check", "make p8-golden", "evidence-p8"),
        "docs/roadmap.md": ("P7", "P8", "not"),
        "docs/product/capability-matrix.md": ("P8", "not_evaluated", "No"),
        "docs/p8/operations.md": ("online backup API", "atomic replacement", "0600"),
        "docs/p8/release-checklist.md": ("SHA256SUMS", "not_evaluated", "cleanup"),
        "docs/p8/release-golden-path.md": ("synthetic/offline", "zero containers", "P8"),
    }
    for relative, terms in required.items():
        document = (root / relative).read_text(encoding="utf-8")
        if any(term not in document for term in terms):
            raise ReleaseError("release_documentation_incomplete")
    for document_path in root.joinpath("docs").rglob("*.md"):
        document = document_path.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(document):
            target = match.group(1).strip().strip("<>").split(maxsplit=1)[0]
            if target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            local = unquote(target.split("#", 1)[0])
            if local and not (document_path.parent / local).resolve().exists():
                raise ReleaseError("release_document_link_invalid")
    compose = (root / "compose.yaml").read_text(encoding="utf-8")
    optional = (root / "compose.p7.yaml").read_text(encoding="utf-8")
    if "DC_P7_MODEL_MODE" in compose or "profiles:" not in optional:
        raise ReleaseError("adapter_default_boundary_invalid")


def _license_unchanged(root: Path) -> None:
    current = hashlib.sha256((root / "LICENSE").read_bytes()).digest()
    accepted = subprocess.run(
        ["git", "show", f"{BASE_COMMIT}:LICENSE"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if accepted.returncode != 0 or hashlib.sha256(accepted.stdout).digest() != current:
        raise ReleaseError("license_boundary_invalid")


def check_release(root: Path) -> dict[str, object]:
    repository = check_repository(root)
    provenance = check_provenance(root)
    _public_boundary(root)
    _release_documents(root)
    _license_unchanged(root)
    supply_chain = check_supply_chain(root)
    with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-release-") as name:
        output = Path(name) / "candidate"
        candidate = build_candidate(root, output, python=Path(sys.executable))
        digests = validate_candidate(output, expected_commit=candidate.source_commit)
        private_suffixes = (".sqlite", ".db", ".backup", ".log")
        if any(name.endswith(private_suffixes) for name in digests):
            raise ReleaseError("private_release_artifact")
        result = {
            "schema_version": 1,
            "gate": "p8_release_clean",
            "status": "passed",
            "release_version": "0.1.0",
            "source_commit": candidate.source_commit,
            "artifact_count": len(digests),
            "artifacts": sorted(digests),
            "checksums_verified": True,
            "release_manifest_verified": True,
            "source_archive_allowlist": "passed",
            "wheel_version": "0.1.0",
            "studio_version": "0.1.0",
            "supply_chain_gate": supply_chain["gate"],
            "repository_gate": repository["gate"],
            "provenance_gate": provenance["gate"],
            "public_boundary_exceptions": 0,
            "license_notice_inventory": "reviewed",
            "documented_commands": "validated",
            "implementation_ancestry": "validated",
            "private_artifacts": 0,
            "build_residue": 0,
            "default_path": "deterministic_intelligence_and_reference_channel",
            "optional_adapters": "explicit_opt_in",
            "evidence_class": "synthetic_offline",
        }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P8 release candidate.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_release(Path(arguments.root).resolve())
    except (OSError, ProvenanceError, ReleaseError, RepositoryError, SupplyChainError) as exc:
        safe = str(exc).replace(str(Path(arguments.root).resolve()), "<project>")
        print(f"P8 release check failed: {safe}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
