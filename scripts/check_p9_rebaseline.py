# SPDX-License-Identifier: Apache-2.0

"""Mechanically validate the fixed P9 productization rebaseline contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

DOCUMENTS = (
    "AGENTS.md",
    "README.md",
    "SECURITY.md",
    "docs/architecture/target-architecture.md",
    "docs/development.md",
    "docs/roadmap.md",
    "docs/product/capability-matrix.md",
    "docs/product/post-v0.1-capability-outlook.md",
    "docs/product/v0.2-public-pilot-product-brief.md",
    "docs/product/v0.2-public-pilot-capability-matrix.md",
    "docs/product/v0.2-external-dependency-register.md",
    "docs/adr/0007-declarative-agent-package-and-deployment-model.md",
    "docs/adr/0008-external-identity-connections-and-automatic-authorization.md",
    "docs/security/threat-model.md",
    "docs/security/privacy-boundary.md",
    "docs/security/v0.2-public-pilot-threat-model.md",
    "docs/security/v0.2-public-pilot-privacy-boundary.md",
    "docs/p9/acceptance.md",
    "docs/p9/rebaseline-checklist.md",
)
ROADMAP = "docs/roadmap.md"
BRIEF = "docs/product/v0.2-public-pilot-product-brief.md"
ARCHITECTURE = "docs/architecture/target-architecture.md"
PACKAGE_ADR = "docs/adr/0007-declarative-agent-package-and-deployment-model.md"
AUTHORIZATION_ADR = "docs/adr/0008-external-identity-connections-and-automatic-authorization.md"
THREAT = "docs/security/v0.2-public-pilot-threat-model.md"
PRIVACY = "docs/security/v0.2-public-pilot-privacy-boundary.md"
DEPENDENCIES = "docs/product/v0.2-external-dependency-register.md"
CAPABILITY_MATRIX = "docs/product/v0.2-public-pilot-capability-matrix.md"
ALLOWED_EVIDENCE_CLASSES = frozenset(
    {"static", "synthetic_offline", "loopback", "live_private", "human_evaluation", "not_evaluated"}
)
ALLOWED_DOMAINS = frozenset(
    {
        "developers.openai.com",
        "platform.openai.com",
        "learn.microsoft.com",
        "docs.github.com",
        "docs.sigstore.dev",
    }
)
REQUIRED_EXTERNAL_URLS = frozenset(
    {
        "https://developers.openai.com/api/docs/models/gpt-5.5",
        "https://developers.openai.com/api/reference/cli/resources/responses/methods/create",
        "https://learn.microsoft.com/en-us/entra/identity-platform/msal-authentication-flows",
        "https://learn.microsoft.com/en-us/graph/api/message-delta?view=graph-rest-1.0",
        "https://learn.microsoft.com/en-us/graph/api/chat-list-messages?view=graph-rest-1.0",
        "https://learn.microsoft.com/en-us/graph/api/plannertask-update?view=graph-rest-1.0",
        "https://learn.microsoft.com/en-us/graph/permissions-selected-overview",
        "https://learn.microsoft.com/en-us/graph/api/driveitem-get-content?view=graph-rest-1.0",
    }
)


class RebaselineError(RuntimeError):
    """P9 documents do not satisfy the fixed rebaseline contract."""


def _read(root: Path, relative: str) -> str:
    path = root / relative
    try:
        if not path.is_file() or path.is_symlink():
            raise RebaselineError("a required P9 document is missing or unsafe")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise RebaselineError("a required P9 document is unreadable") from exc


def _require(text: str, values: tuple[str, ...], label: str) -> None:
    missing = [value for value in values if value not in text]
    if missing:
        raise RebaselineError(f"{label} is incomplete")


def _check_roadmap(text: str) -> None:
    phases = [int(value) for value in re.findall(r"^## P(\d+) —", text, re.MULTILINE)]
    if phases != list(range(16)):
        raise RebaselineError("P0-P15 phases are missing, reordered, duplicated, or merged")
    _require(
        text,
        (
            "The following phases are non-mergeable and non-skippable.",
            "development complete",
            "independent acceptance",
            "scoped correction when required",
            "final acceptance",
            "fast-forward merge",
            "main verification",
            "P9 acceptance does not authorize P10.",
            "Migration 008 may first be",
            "not milestone names",
            "tag has been created",
            "nothing has been published, uploaded, or formally released",
        ),
        "P9-P15 sequencing and compatibility contract",
    )


def _check_product(text: str) -> None:
    _require(
        text,
        (
            "v0.2 Public Pilot",
            "unpublished `0.1.0` local reference candidate",
            "five minutes",
            "fifteen minutes",
            "ten active Agents",
            "Mac local",
            "Linux/Mac mini always-on",
            "MacBook",
            "Outlook",
            "Teams",
            "Planner",
            "zh-TW",
            "en-US",
            "not production-ready",
            "high availability",
            "enterprise IAM",
            "compliance",
        ),
        "public-pilot product decisions",
    )


def _check_package_and_architecture(package: str, architecture: str) -> None:
    combined = package + "\n" + architecture
    _require(
        combined,
        (
            "AgentPackage",
            "ColleagueDeployment",
            "ExternalConnection",
            "ConnectorGrant",
            "AutomaticEffectAuthorization",
            "SourceReference",
            "SourceCursor",
            "official built-in",
            "local development package",
            "GitHub Release artifact",
            "not an S4 Skill",
            "Semantic Memory",
            "do not imply S3 shared knowledge",
            "Python",
            "Node",
            "shell",
            "binaries",
            "dynamic import",
            "eval",
            "exec",
            "unbounded loop",
            "cannot authorize",
            "never auto-applies",
            "stale/revoked",
            "Package source",
            "External event",
            "fail closed",
            "/api/v1",
            "`/p5`",
            "`/p6`",
        ),
        "package, deployment, and architecture boundary",
    )


def _check_authorization(text: str) -> None:
    _require(
        text,
        (
            "AutomaticEffectAuthorization",
            "HumanApprovalDecision",
            "different schemas",
            "MODEL",
            "SERVICE",
            "new recipient/chat",
            "external domain",
            "attachment",
            "mention, cross-tenant",
            "cross-tenant",
            "stale ETag",
            "budget",
            "Self-reply",
            "Agent-to-Agent loops",
            "duplicate message/effect",
            "notification flooding",
            "delete_task",
        ),
        "automatic-effect authorization boundary",
    )


def _check_security(threat: str, privacy: str) -> None:
    combined = threat + "\n" + privacy
    _require(
        combined,
        (
            "FileVault",
            "`0700`",
            "`0600`",
            "read-only service mount",
            "environment",
            "SQLite",
            "audit",
            "backup",
            "diagnostics",
            "logs",
            "errors",
            "command arguments",
            "encrypted volume",
            "Temporary source maximums",
            "redaction",
            "discard",
            "crash directory",
            "cleanup counter",
            "SourceReference",
            "safe projection",
        ),
        "secret and privacy boundary",
    )


def _check_live_prerequisites(texts: dict[str, str]) -> None:
    combined = "\n".join(texts.values())
    _require(
        combined,
        (
            "two Microsoft 365 test tenants",
            "ten dedicated Agent test accounts",
            "one usable OpenAI test project",
            "verified project multi-tenant Entra public-client App",
            "BYO single-tenant App",
            "user-consent",
            "Admin-consent",
            "real Outlook/Teams/Planner/SharePoint test data",
            "private live-acceptance storage",
            "mock, stub, or loopback cannot",
        ),
        "P15 live prerequisites",
    )


def _check_dependencies(text: str) -> int:
    if not re.search(r"checked at `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z`", text):
        raise RebaselineError("external dependency checked-at UTC is missing")
    urls = set(re.findall(r"https://[^\s|)>]+", text))
    normalized = {url.rstrip(".,") for url in urls}
    if not REQUIRED_EXTERNAL_URLS.issubset(normalized):
        raise RebaselineError("external dependency register lacks a required official document")
    for url in normalized:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_DOMAINS:
            raise RebaselineError("external dependency register uses a non-official domain")
    _require(
        text,
        (
            "gpt-5.5",
            "Responses",
            "Structured Outputs",
            "`store:false`",
            "no tools",
            "Device-code",
            "public client",
            "per collection",
            "bounded page size",
            "If-Match",
            "409",
            "412",
            "selected",
            "preauthenticated redirect",
            "not a security guarantee",
            "Change Decision",
        ),
        "external dependency observations",
    )
    return len(normalized)


def _check_evidence_classes(texts: dict[str, str]) -> None:
    combined = "\n".join(texts.values())
    _require(
        combined,
        tuple(f"`{value}`" for value in sorted(ALLOWED_EVIDENCE_CLASSES)),
        "evidence-class vocabulary",
    )
    _require(
        combined,
        (
            "OpenAI live",
            "Microsoft 365 live",
            "human evaluation",
            "not_evaluated",
            "p9_productization_rebaseline_candidate",
            "development_complete_awaiting_independent_acceptance",
        ),
        "P9 evidence and claim boundary",
    )
    evidence_section = texts[CAPABILITY_MATRIX].split("## Evidence status at P9", 1)
    if len(evidence_section) != 2:
        raise RebaselineError("P9 evidence status table is missing")
    table_values = set(re.findall(r"\| `([a-z_]+)` \|", evidence_section[1]))
    if table_values - ALLOWED_EVIDENCE_CLASSES:
        raise RebaselineError("P9 evidence status uses an unapproved evidence class")


def _check_unsafe_claims(texts: dict[str, str], root: Path) -> None:
    combined = "\n".join(texts.values())
    forbidden = (
        r"\bis production-ready\b",
        r"\bsupports high availability\b",
        r"\bimplements enterprise IAM\b",
        r"\bcompliance[- ]certified\b",
        r"AgentPackage is an executable (?:S4 )?Skill",
        r"AgentPackage (?:may|can) self-grant",
        r"AgentPackage self-activates",
        r"source context is persistent (?:Semantic )?[Mm]emory",
        r"deployments? (?:enable|provide|establish) (?:S3 )?(?:Agent )?collaboration",
        r"AutomaticEffectAuthorization is (?:a )?HumanApprovalDecision",
        r"mock(?:, stub,)? or loopback (?:is|counts as|satisfies) live_private",
    )
    if any(re.search(pattern, combined, re.IGNORECASE) for pattern in forbidden):
        raise RebaselineError("P9 documents contain an unsafe implementation or acceptance claim")
    unsafe_literals = (str(root), str(Path.home()), "/.codex/attachments/", "PRIVATE_LIVE_RECEIPT")
    if any(value and value in combined for value in unsafe_literals):
        raise RebaselineError("P9 documents contain a local path or private marker")
    local_path_pattern = r"/" + r"(?:Users|home)/[^\s`]+"
    if re.search(local_path_pattern, combined):
        raise RebaselineError("P9 documents contain a local absolute path")
    if re.search(r"(?:sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._=-]{12,})", combined, re.I):
        raise RebaselineError("P9 documents contain credential-shaped material")
    if re.search(r"(?:tenant|client|account)[_-]?id\s*[:=]\s*[0-9a-f-]{16,}", combined, re.I):
        raise RebaselineError("P9 documents contain a live identifier")


def check_rebaseline(root: Path) -> dict[str, object]:
    root = root.resolve()
    texts = {relative: _read(root, relative) for relative in DOCUMENTS}
    _check_roadmap(texts[ROADMAP])
    _check_product(texts[BRIEF])
    _check_package_and_architecture(texts[PACKAGE_ADR], texts[ARCHITECTURE])
    _check_authorization(texts[AUTHORIZATION_ADR])
    _check_security(texts[THREAT], texts[PRIVACY])
    _check_live_prerequisites(texts)
    dependency_count = _check_dependencies(texts[DEPENDENCIES])
    _check_evidence_classes(texts)
    _check_unsafe_claims(texts, root)
    return {
        "schema_version": 1,
        "gate": "p9_rebaseline_clean",
        "document_count": len(texts),
        "phase_count": 16,
        "p9_through_p15_order": "passed",
        "fixed_product_decisions": "passed",
        "deferred_capability_separation": "passed",
        "authorization_record_separation": "passed",
        "p15_live_prerequisite_status": "complete",
        "evidence_classes": sorted(ALLOWED_EVIDENCE_CLASSES),
        "external_document_count": dependency_count,
        "external_domains": sorted(ALLOWED_DOMAINS),
        "openai_live": "not_evaluated",
        "microsoft_365_live": "not_evaluated",
        "human_evaluation": "not_evaluated",
        "product_runtime_implementation_change_count": 0,
        "claim": "p9_productization_rebaseline_candidate",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the P9 rebaseline documents.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_rebaseline(Path(arguments.root))
    except (OSError, RebaselineError) as exc:
        safe = str(exc).replace(str(Path.home()), "<home>")
        print(f"P9 rebaseline check failed: {safe}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
