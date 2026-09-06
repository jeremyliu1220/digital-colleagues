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
from scripts.check_p8_repository import (
    ACCEPTED_P8_COMMIT,
    RepositoryError,
    check_repository,
)
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
PUBLIC_STATUS_PATHS = (
    "README.md",
    "SECURITY.md",
    "docs/roadmap.md",
    "docs/product/capability-matrix.md",
    "docs/p8/release-checklist.md",
)
P8_CAPABILITIES = (
    "Upgrade, backup, restore, and release rollback",
    "Redacted support diagnostics",
    "Reproducible release candidate",
    "Release supply-chain inventory",
)
COMMON_STATUS_REQUIREMENTS = (
    "P8 passed independent acceptance and was fast-forward merged from "
    "codex/p8-release-readiness to main",
    f"the accepted P8 commit is {ACCEPTED_P8_COMMIT}",
    "v0.1 local reference release candidate",
    "0.1.0",
    "no tag has been created, and nothing has been published, uploaded, or formally released",
    "not production-ready and establishes no production security, high availability, "
    "enterprise IAM, real-provider readiness, compliance",
    "Human evaluation, live-provider evidence, and the unmeasured five-minute target "
    "remain not_evaluated",
    "Post-v0.1 S1–S4 and Self-initiated autonomy have not started and do not start automatically",
    "P0–P8",
    "artifacts",
    "evidence",
    "acceptance contracts",
    "receipts",
    "migrations",
    "unchanged",
)
STALE_CURRENT_STATUS = (
    "p8 development complete, awaiting independent acceptance",
    "awaiting independent re-acceptance",
    "p8 is not accepted",
    "p8 is not merged",
)
UNSAFE_CURRENT_STATUS = (
    "p8 is formally released",
    "p8 has been formally released",
    "p8 is production-ready",
    "p8 is live-provider accepted",
    "live-provider acceptance passed",
    "real-provider readiness is established",
    "production security is established",
)


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


def _section(document: str, start: str, end: str) -> str:
    start_index = document.find(start)
    if start_index < 0:
        raise ReleaseError("public_status_section_missing")
    end_index = document.find(end, start_index + len(start))
    if end_index < 0:
        raise ReleaseError("public_status_section_missing")
    return document[start_index:end_index]


def _normalized_status(scope: str) -> str:
    without_markup = re.sub(r"[`*>]", "", scope)
    return re.sub(r"\s+", " ", without_markup).casefold()


def _matrix_rows(document: str) -> dict[str, tuple[str, str]]:
    rows: dict[str, tuple[str, str]] = {}
    for line in document.splitlines():
        if not line.startswith("|"):
            continue
        cells = tuple(cell.strip() for cell in line.strip("|").split("|"))
        if len(cells) != 4 or cells[0] not in P8_CAPABILITIES:
            continue
        rows[cells[0]] = (cells[2], cells[3])
    return rows


def _accepted_document(root: Path, relative: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{ACCEPTED_P8_COMMIT}:{relative}"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise ReleaseError("accepted_public_status_object_missing")
    try:
        return completed.stdout.decode("utf-8")
    except UnicodeError as exc:
        raise ReleaseError("accepted_public_status_object_invalid") from exc


def _public_status_documents(root: Path) -> None:
    documents = {
        relative: (root / relative).read_text(encoding="utf-8") for relative in PUBLIC_STATUS_PATHS
    }
    readme_status = _section(
        documents["README.md"],
        "> **Project status",
        "## P8 release-candidate verification",
    )
    security_status = _section(
        documents["SECURITY.md"],
        "## Supported status",
        "## Reporting a vulnerability",
    )
    roadmap_checkpoint = _section(
        documents["docs/roadmap.md"],
        "Current checkpoint:",
        "Rebaseline boundary:",
    )
    roadmap_p8 = _section(
        documents["docs/roadmap.md"],
        "## P8 — Release and operational readiness",
        "## Post-v0.1 outlook",
    )
    matrix_status = _section(
        documents["docs/product/capability-matrix.md"],
        "Current checkpoint:",
        "| Capability |",
    )
    checklist_status = _section(
        documents["docs/p8/release-checklist.md"],
        "# P8 Release Candidate Checklist",
        "## Source and history",
    )
    status_scopes = {
        "README.md": readme_status,
        "SECURITY.md": security_status,
        "docs/roadmap.md": roadmap_checkpoint + roadmap_p8,
        "docs/product/capability-matrix.md": matrix_status,
        "docs/p8/release-checklist.md": checklist_status,
    }
    for scope in status_scopes.values():
        lowered = _normalized_status(scope)
        if any(requirement.casefold() not in lowered for requirement in COMMON_STATUS_REQUIREMENTS):
            raise ReleaseError("public_status_incomplete")
        if any(stale in lowered for stale in STALE_CURRENT_STATUS):
            raise ReleaseError("public_status_stale")
        if any(unsafe in lowered for unsafe in UNSAFE_CURRENT_STATUS):
            raise ReleaseError("public_status_overclaim")
    if "p7 has passed independent acceptance" in roadmap_checkpoint.casefold():
        raise ReleaseError("roadmap_checkpoint_stale")

    matrix_rows = _matrix_rows(documents["docs/product/capability-matrix.md"])
    accepted_rows = _matrix_rows(_accepted_document(root, "docs/product/capability-matrix.md"))
    if set(matrix_rows) != set(P8_CAPABILITIES) or any(
        matrix_rows[capability][0] != "P8 accepted main baseline" for capability in P8_CAPABILITIES
    ):
        raise ReleaseError("capability_matrix_status_invalid")
    if any(
        capability not in accepted_rows
        or matrix_rows[capability][1] != accepted_rows[capability][1]
        for capability in P8_CAPABILITIES
    ):
        raise ReleaseError("capability_matrix_boundary_invalid")

    checklist = documents["docs/p8/release-checklist.md"]
    source_history = _section(
        checklist,
        "## Source and history",
        "## Version, inventory, and attribution",
    )
    checkboxes = re.findall(r"^- \[([^]])\]", checklist, flags=re.MULTILINE)
    if not checkboxes or any(value != " " for value in checkboxes):
        raise ReleaseError("release_checklist_not_unchecked")
    if (
        "clean `main` containing accepted P8 commit" not in source_history
        or "explicitly authorized descendant" not in source_history
        or "HEAD is on `codex/p8-release-readiness`" in source_history
        or "make evidence-p8" in checklist
    ):
        raise ReleaseError("release_checklist_history_invalid")


def _release_documents(root: Path) -> None:
    makefile = (root / "Makefile").read_text(encoding="utf-8")
    if any(f"{target}:" not in makefile for target in REQUIRED_MAKE_TARGETS):
        raise ReleaseError("release_command_missing")
    _public_status_documents(root)
    required = {
        "docs/development.md": ("make check", "make p8-golden", "evidence-p8"),
        "docs/p8/operations.md": ("online backup API", "atomic replacement", "0600"),
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
