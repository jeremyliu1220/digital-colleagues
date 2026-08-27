# SPDX-License-Identifier: Apache-2.0

"""Reject private, local, credential, provider, and acceptance material in the public tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = PROJECT_ROOT / "provenance" / "scanner-policy.json"
DEFAULT_EXCEPTIONS = PROJECT_ROOT / "provenance" / "scanner-exceptions.json"
EXCEPTION_FIELDS = {"path", "rule_id", "digest", "reason", "approved_by_role"}
MAX_GIT_POINTER_BYTES = 4_096
GIT_POINTER_PATTERN = re.compile(rb"gitdir: [^\x00\r\n]+(?:\r?\n)?\Z")


@dataclass(frozen=True, order=True)
class Violation:
    path: str
    rule_id: str


class BoundaryError(RuntimeError):
    """A scanner configuration failure with a location-safe message."""


def _read_json(document: Path) -> dict[str, Any]:
    try:
        value = json.loads(document.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BoundaryError("a scanner configuration file is unreadable") from exc
    if not isinstance(value, dict):
        raise BoundaryError("a scanner configuration file is not an object")
    return value


def _safe_relative(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise BoundaryError("an exception path is invalid")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or ".." in candidate.parts or value.endswith("/"):
        raise BoundaryError("exceptions must identify one repository-relative file")
    if any(character in value for character in "*?[]"):
        raise BoundaryError("exception globs are forbidden")
    return candidate.as_posix()


def _validate_policy(policy: dict[str, Any]) -> tuple[set[str], dict[str, list[str]], set[str]]:
    if policy.get("schema_version") != 1 or policy.get("policy_version") != "p0-v1":
        raise BoundaryError("the scanner policy version is not supported")
    raw_rules = policy.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise BoundaryError("the scanner policy has no rules")
    rule_ids: set[str] = set()
    for raw_rule in raw_rules:
        if not isinstance(raw_rule, dict) or raw_rule.get("action") != "reject":
            raise BoundaryError("every P0 scanner rule must reject")
        rule_id = raw_rule.get("id")
        if not isinstance(rule_id, str) or not rule_id or rule_id in rule_ids:
            raise BoundaryError("scanner rule IDs must be unique")
        rule_ids.add(rule_id)

    key_groups: dict[str, list[str]] = {}
    for group in (
        "structured_personal_keys",
        "structured_provider_keys",
        "structured_live_receipt_keys",
        "structured_acceptance_keys",
    ):
        values = policy.get(group)
        if (
            not isinstance(values, list)
            or not values
            or not all(isinstance(item, str) for item in values)
        ):
            raise BoundaryError("structured scanner keys must be explicit non-empty lists")
        key_groups[group] = list(values)

    raw_digests = policy.get("known_private_marker_digests")
    if not isinstance(raw_digests, list):
        raise BoundaryError("private marker digests must be a versioned list")
    marker_digests: set[str] = set()
    for value in raw_digests:
        if not isinstance(value, str) or len(value) != 64:
            raise BoundaryError("a private marker digest is invalid")
        try:
            bytes.fromhex(value)
        except ValueError as exc:
            raise BoundaryError("a private marker digest is invalid") from exc
        marker_digests.add(value)
    return rule_ids, key_groups, marker_digests


def _validate_exceptions(
    document: dict[str, Any], rule_ids: set[str]
) -> dict[tuple[str, str], str]:
    if document.get("schema_version") != 1 or document.get("policy_version") != "p0-v1":
        raise BoundaryError("the exception ledger version is not supported")
    raw_exceptions = document.get("exceptions")
    if not isinstance(raw_exceptions, list):
        raise BoundaryError("the exception ledger is invalid")
    result: dict[tuple[str, str], str] = {}
    for raw_exception in raw_exceptions:
        if not isinstance(raw_exception, dict) or set(raw_exception) != EXCEPTION_FIELDS:
            raise BoundaryError("an exception must use the exact auditable fields")
        relative = _safe_relative(raw_exception["path"])
        rule_id = raw_exception.get("rule_id")
        digest = raw_exception.get("digest")
        reason = raw_exception.get("reason")
        approver = raw_exception.get("approved_by_role")
        if rule_id not in rule_ids:
            raise BoundaryError("an exception names an unknown rule")
        if not isinstance(digest, str) or not digest.startswith("sha256:") or len(digest) != 71:
            raise BoundaryError("an exception digest is invalid")
        try:
            bytes.fromhex(digest.removeprefix("sha256:"))
        except ValueError as exc:
            raise BoundaryError("an exception digest is invalid") from exc
        if not isinstance(reason, str) or len(reason) < 20:
            raise BoundaryError("an exception reason is not auditable")
        if approver not in {"privacy_reviewer", "security_reviewer", "project_owner"}:
            raise BoundaryError("an exception approving role is invalid")
        key = (relative, rule_id)
        if key in result:
            raise BoundaryError("duplicate exceptions are forbidden")
        result[key] = digest
    return result


def _structured_key_pattern(keys: Iterable[str]) -> re.Pattern[str]:
    alternatives = "|".join(re.escape(item) for item in keys)
    return re.compile(rf'["\'](?:{alternatives})["\']\s*[:=]', re.IGNORECASE)


def _rules_for_text(
    text: str, key_groups: dict[str, list[str]], marker_digests: set[str]
) -> set[str]:
    matches: set[str] = set()
    local_patterns = (
        re.compile(re.escape("/" + "Users" + "/") + r"[A-Za-z0-9._-]+/"),
        re.compile(r"/home/[A-Za-z0-9._-]+/"),
        re.compile(r"[A-Za-z]:\\" + re.escape("Users") + r"\\[A-Za-z0-9._-]+\\", re.IGNORECASE),
    )
    if any(pattern.search(text) for pattern in local_patterns):
        matches.add("LOCAL_PATH")

    email_pattern = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
    if email_pattern.search(text):
        matches.add("EMAIL_ADDRESS")

    provider_pattern = re.compile(r"\b[TUCBGW](?=[A-Z0-9]{8,}\b)(?=[A-Z0-9]*[0-9])[A-Z0-9]{8,}\b")
    if provider_pattern.search(text):
        matches.add("PROVIDER_IDENTIFIER")

    credential_patterns = (
        re.compile(re.escape("sk" + "-") + r"[A-Za-z0-9_-]{16,}"),
        re.compile(re.escape("xox" + "b-") + r"[A-Za-z0-9-]{16,}"),
        re.compile(re.escape("xox" + "p-") + r"[A-Za-z0-9-]{16,}"),
        re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
        re.compile(
            r'["\'](?:api_key|access_token|refresh_token|password|secret|session_id)["\']\s*[:=]\s*["\'][^"\']+["\']',
            re.IGNORECASE,
        ),
    )
    if any(pattern.search(text) for pattern in credential_patterns):
        matches.add("CREDENTIAL_PATTERN")

    private_key_marker = "-----BEGIN " + "PRIVATE KEY-----"
    if private_key_marker in text:
        matches.add("PRIVATE_KEY")

    if _structured_key_pattern(key_groups["structured_personal_keys"]).search(text):
        matches.add("PERSONAL_IDENTIFIER")
    if _structured_key_pattern(key_groups["structured_provider_keys"]).search(text):
        matches.add("PROVIDER_IDENTIFIER")
    if _structured_key_pattern(key_groups["structured_live_receipt_keys"]).search(text):
        matches.add("LIVE_RECEIPT")
    if _structured_key_pattern(key_groups["structured_acceptance_keys"]).search(text):
        matches.add("PERSONAL_ACCEPTANCE")

    if marker_digests:
        for token in re.findall(r"[A-Za-z0-9_.@-]{3,}", text):
            digest = hashlib.sha256(token.casefold().encode("utf-8")).hexdigest()
            if digest in marker_digests:
                matches.add("PERSONAL_IDENTIFIER")
                break
    return matches


def _root_git_administrative_kind(root: Path) -> str | None:
    """Validate the exact root Git administrative entry without exposing its pointer."""

    entry = root / ".git"
    try:
        metadata = entry.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise BoundaryError("the root Git administrative entry is unreadable") from exc

    if stat.S_ISDIR(metadata.st_mode):
        return "directory"
    if not stat.S_ISREG(metadata.st_mode):
        raise BoundaryError("the root Git administrative entry is invalid")

    no_follow = getattr(os, "O_NOFOLLOW", None)
    if no_follow is None:
        raise BoundaryError("safe root Git pointer inspection is unavailable")
    descriptor: int | None = None
    try:
        descriptor = os.open(entry, os.O_RDONLY | no_follow)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_size > MAX_GIT_POINTER_BYTES:
            raise BoundaryError("the root Git administrative entry is invalid")
        content = os.read(descriptor, MAX_GIT_POINTER_BYTES + 1)
        if len(content) > MAX_GIT_POINTER_BYTES or os.read(descriptor, 1):
            raise BoundaryError("the root Git administrative entry is invalid")
    except BoundaryError:
        raise
    except OSError as exc:
        raise BoundaryError("the root Git administrative entry is invalid") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)

    if GIT_POINTER_PATTERN.fullmatch(content) is None:
        raise BoundaryError("the root Git administrative entry is invalid")
    return "pointer_file"


def scan_tree(
    root: Path,
    *,
    policy_document: dict[str, Any],
    exception_document: dict[str, Any],
) -> tuple[list[Violation], int, int, int]:
    if not root.is_dir():
        raise BoundaryError("scan root is unavailable")
    rule_ids, key_groups, marker_digests = _validate_policy(policy_document)
    exceptions = _validate_exceptions(exception_document, rule_ids)
    violations: list[Violation] = []
    used_exceptions: set[tuple[str, str]] = set()
    file_count = 0
    total_bytes = 0

    git_administrative_kind = _root_git_administrative_kind(root)

    for document in sorted(root.rglob("*")):
        relative_path = document.relative_to(root)
        if git_administrative_kind == "directory" and relative_path.parts[:1] == (".git",):
            continue
        if git_administrative_kind == "pointer_file" and relative_path.parts == (".git",):
            continue
        if document.is_symlink():
            relative = relative_path.as_posix()
            violations.append(Violation(relative, "UNDECODABLE_FILE"))
            continue
        if not document.is_file():
            continue
        relative = relative_path.as_posix()
        file_count += 1
        try:
            content = document.read_bytes()
        except OSError:
            violations.append(Violation(relative, "UNDECODABLE_FILE"))
            continue
        total_bytes += len(content)
        digest = "sha256:" + hashlib.sha256(content).hexdigest()
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            rules = {"UNDECODABLE_FILE"}
        else:
            rules = _rules_for_text(text, key_groups, marker_digests)
        for rule_id in sorted(rules):
            key = (relative, rule_id)
            if exceptions.get(key) == digest:
                used_exceptions.add(key)
            else:
                violations.append(Violation(relative, rule_id))

    unused = set(exceptions) - used_exceptions
    if unused:
        raise BoundaryError("the exception ledger contains a stale or non-matching exception")
    return sorted(violations), file_count, total_bytes, len(used_exceptions)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan every target file against the versioned public-boundary policy."
    )
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--exceptions", default=str(DEFAULT_EXCEPTIONS))
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        violations, file_count, total_bytes, exceptions_applied = scan_tree(
            Path(arguments.root),
            policy_document=_read_json(Path(arguments.policy)),
            exception_document=_read_json(Path(arguments.exceptions)),
        )
    except BoundaryError as exc:
        print(f"public-boundary scan failed: {exc}", file=sys.stderr)
        return 2
    if violations:
        for violation in violations:
            print(f"{violation.path}: {violation.rule_id}", file=sys.stderr)
        print(f"public-boundary scan rejected {len(violations)} finding(s)", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "schema_version": 1,
                "gate": "public_boundary_clean",
                "policy_version": "p0-v1",
                "files_scanned": file_count,
                "bytes_scanned": total_bytes,
                "exceptions_applied": exceptions_applied,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
