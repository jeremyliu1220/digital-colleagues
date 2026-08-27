# SPDX-License-Identifier: Apache-2.0

"""Verify the versioned source allowlist against a fixed Git revision without copying."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST_PATH = PROJECT_ROOT / "provenance" / "source-allowlist.json"
DENYLIST_PATH = PROJECT_ROOT / "provenance" / "source-denylist.json"
ENTRY_FIELDS = {
    "source_path",
    "destination",
    "digest",
    "classification",
    "required_transform",
}


class AllowlistError(RuntimeError):
    """A verification error whose message is safe for public output."""


def _load_json(document: Path) -> dict[str, Any]:
    try:
        value = json.loads(document.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AllowlistError("a provenance manifest is unreadable") from exc
    if not isinstance(value, dict):
        raise AllowlistError("a provenance manifest is not an object")
    return value


def _relative_file(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise AllowlistError(f"{field} must be a non-empty repository-relative string")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or ".." in candidate.parts or value.endswith("/"):
        raise AllowlistError(f"{field} must identify one repository-relative file")
    return candidate.as_posix()


def validate_manifests(allowlist: dict[str, Any], denylist: dict[str, Any]) -> list[dict[str, str]]:
    if allowlist.get("schema_version") != 1 or allowlist.get("manifest_version") != "p0-v1":
        raise AllowlistError("the allowlist version is not supported")
    if denylist.get("schema_version") != 1 or denylist.get("policy_version") != "p0-v1":
        raise AllowlistError("the denylist version is not supported")
    if allowlist.get("source_label") != denylist.get("source_label"):
        raise AllowlistError("source labels disagree")
    if allowlist.get("source_revision") != denylist.get("source_revision"):
        raise AllowlistError("source revisions disagree")

    raw_entries = allowlist.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise AllowlistError("the allowlist must contain individual file entries")
    raw_rules = denylist.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise AllowlistError("the denylist must contain explicit rules")

    deny_rules: list[tuple[str, str]] = []
    for raw_rule in raw_rules:
        if not isinstance(raw_rule, dict):
            raise AllowlistError("a denylist rule is invalid")
        match_kind = raw_rule.get("match_kind")
        source_path = raw_rule.get("source_path")
        if match_kind not in {"exact", "prefix"} or not isinstance(source_path, str):
            raise AllowlistError("a denylist rule must be exact or prefix-scoped")
        if PurePosixPath(source_path).is_absolute() or ".." in PurePosixPath(source_path).parts:
            raise AllowlistError("a denylist rule contains an unsafe path")
        deny_rules.append((match_kind, source_path))

    entries: list[dict[str, str]] = []
    source_paths: set[str] = set()
    destinations: set[str] = set()
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict) or set(raw_entry) != ENTRY_FIELDS:
            raise AllowlistError("an allowlist entry has unapproved fields")
        source_path = _relative_file(raw_entry["source_path"], "source_path")
        destination = _relative_file(raw_entry["destination"], "destination")
        digest = raw_entry.get("digest")
        classification = raw_entry.get("classification")
        required_transform = raw_entry.get("required_transform")
        if not isinstance(digest, str) or not digest.startswith("sha256:") or len(digest) != 71:
            raise AllowlistError(f"invalid digest for {source_path}")
        try:
            bytes.fromhex(digest.removeprefix("sha256:"))
        except ValueError as exc:
            raise AllowlistError(f"invalid digest for {source_path}") from exc
        if not isinstance(classification, str) or not classification:
            raise AllowlistError(f"missing classification for {source_path}")
        if not isinstance(required_transform, str) or len(required_transform) < 24:
            raise AllowlistError(f"missing required transform for {source_path}")
        if source_path in source_paths or destination in destinations:
            raise AllowlistError("allowlist source paths and destinations must be unique")
        for match_kind, denied_path in deny_rules:
            denied = (
                source_path == denied_path
                if match_kind == "exact"
                else source_path.startswith(denied_path)
            )
            if denied:
                raise AllowlistError(f"allowlist and denylist conflict at {source_path}")
        source_paths.add(source_path)
        destinations.add(destination)
        entries.append({key: str(raw_entry[key]) for key in ENTRY_FIELDS})
    return entries


def _git(source: Path, *arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=source,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AllowlistError("fixed-revision source inspection failed") from exc
    return completed.stdout


def verify_source(
    source: Path,
    revision: str,
    allowlist: dict[str, Any],
    denylist: dict[str, Any],
) -> dict[str, object]:
    if not source.is_dir():
        raise AllowlistError("source checkout is unavailable")
    manifest_revision = allowlist.get("source_revision")
    if revision != manifest_revision:
        raise AllowlistError("requested revision does not match the approved manifest")
    entries = validate_manifests(allowlist, denylist)
    _git(source, "cat-file", "-e", f"{revision}^{{commit}}")
    for entry in entries:
        source_path = entry["source_path"]
        content = _git(source, "show", f"{revision}:{source_path}")
        actual = "sha256:" + hashlib.sha256(content).hexdigest()
        if actual != entry["digest"]:
            raise AllowlistError(f"fixed-revision digest mismatch at {source_path}")

    canonical_manifest = json.dumps(
        allowlist, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return {
        "schema_version": 1,
        "gate": "source_allowlist_verified",
        "source_label": allowlist["source_label"],
        "source_revision": manifest_revision,
        "entry_count": len(entries),
        "manifest_digest": "sha256:" + hashlib.sha256(canonical_manifest).hexdigest(),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify approved file digests without copying or printing source locations."
    )
    parser.add_argument("--source", required=True, help="Runtime source checkout location.")
    parser.add_argument("--revision", required=True, help="Approved Git revision.")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        result = verify_source(
            Path(arguments.source),
            arguments.revision,
            _load_json(ALLOWLIST_PATH),
            _load_json(DENYLIST_PATH),
        )
    except AllowlistError as exc:
        print(f"allowlist verification failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
