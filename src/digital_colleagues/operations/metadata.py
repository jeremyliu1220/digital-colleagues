# SPDX-License-Identifier: Apache-2.0

"""Strict release and migration metadata used by local operator tools."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RELEASE_VERSION = "0.1.0"
ACCEPTED_P7_VERSION = "0.0.0"
ACCEPTED_P7_COMMIT = "df47f8d075f7c0660ab5ed6035f8acfa3d3da4dc"
ACCEPTED_P7_TREE = "4ebfc2bdfcd97e34256ec7a34ff58b0063c05ed7"
ACCEPTED_P7_MIGRATION_MANIFEST_DIGEST = (
    "sha256:5868262fec025a33082afddeb49add29df798f27370b0f71fcbb728de9444436"
)
ACCEPTED_P7_TIMESTAMP = "2026-09-06T02:43:24Z"
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class MetadataError(RuntimeError):
    """Release or migration metadata is incompatible or malformed."""


@dataclass(frozen=True)
class ReleaseBinding:
    release_version: str
    source_commit: str
    migration_manifest_digest: str
    source_class: str
    source_manifest_status: str


@dataclass(frozen=True)
class MigrationBinding:
    version: int
    name: str
    checksum: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _object(path: Path, category: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise MetadataError(category)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MetadataError(category) from exc
    if not isinstance(value, dict):
        raise MetadataError(category)
    return value


def load_release_binding(path: Path) -> ReleaseBinding:
    value = _object(path, "release_manifest_invalid")
    required = {
        "schema_version",
        "release_version",
        "source_commit",
        "source_timestamp",
        "migration_manifest_digest",
        "artifacts",
        "build_inputs",
        "evidence_classes",
        "claim_exclusions",
    }
    if set(value) != required or value.get("schema_version") != 1:
        raise MetadataError("release_manifest_invalid")
    release_version = value.get("release_version")
    source_commit = value.get("source_commit")
    migration_digest = value.get("migration_manifest_digest")
    if (
        release_version != RELEASE_VERSION
        or not isinstance(source_commit, str)
        or not COMMIT_PATTERN.fullmatch(source_commit)
        or not isinstance(migration_digest, str)
        or not DIGEST_PATTERN.fullmatch(migration_digest)
    ):
        raise MetadataError("release_manifest_incompatible")
    return ReleaseBinding(
        release_version,
        source_commit,
        migration_digest,
        "release_manifest",
        "available",
    )


def accepted_p7_source_binding_document() -> dict[str, object]:
    return {
        "schema_version": 1,
        "source_class": "accepted_p7_git_object",
        "source_version": ACCEPTED_P7_VERSION,
        "source_commit": ACCEPTED_P7_COMMIT,
        "source_tree": ACCEPTED_P7_TREE,
        "source_timestamp": ACCEPTED_P7_TIMESTAMP,
        "migration_manifest_digest": ACCEPTED_P7_MIGRATION_MANIFEST_DIGEST,
        "schema_version_current": 7,
        "release_manifest_status": "not_available_before_first_release",
    }


def load_source_binding(path: Path) -> ReleaseBinding:
    value = _object(path, "source_binding_invalid")
    if value.get("source_class") != "accepted_p7_git_object":
        return load_release_binding(path)
    required = {
        "schema_version",
        "source_class",
        "source_version",
        "source_commit",
        "source_tree",
        "source_timestamp",
        "migration_manifest_digest",
        "schema_version_current",
        "release_manifest_status",
    }
    if (
        set(value) != required
        or value.get("schema_version") != 1
        or value.get("source_version") != ACCEPTED_P7_VERSION
        or value.get("source_commit") != ACCEPTED_P7_COMMIT
        or value.get("source_tree") != ACCEPTED_P7_TREE
        or value.get("source_timestamp") != ACCEPTED_P7_TIMESTAMP
        or value.get("schema_version_current") != 7
        or value.get("release_manifest_status") != "not_available_before_first_release"
        or value.get("migration_manifest_digest") != ACCEPTED_P7_MIGRATION_MANIFEST_DIGEST
    ):
        raise MetadataError("accepted_p7_source_binding_invalid")
    return ReleaseBinding(
        ACCEPTED_P7_VERSION,
        ACCEPTED_P7_COMMIT,
        ACCEPTED_P7_MIGRATION_MANIFEST_DIGEST,
        "accepted_p7_git_object",
        "not_available_before_first_release",
    )


def load_migration_bindings(directory: Path) -> tuple[str, tuple[MigrationBinding, ...]]:
    manifest = directory / "manifest.json"
    value = _object(manifest, "migration_manifest_invalid")
    if set(value) != {"schema_version", "migrations"} or value.get("schema_version") != 1:
        raise MetadataError("migration_manifest_invalid")
    items = value.get("migrations")
    if not isinstance(items, list) or not items:
        raise MetadataError("migration_manifest_invalid")
    bindings: list[MigrationBinding] = []
    for position, item in enumerate(items, start=1):
        if not isinstance(item, dict) or set(item) != {"version", "name", "file", "checksum"}:
            raise MetadataError("migration_manifest_invalid")
        version = item.get("version")
        name = item.get("name")
        filename = item.get("file")
        checksum = item.get("checksum")
        if (
            type(version) is not int
            or version != position
            or not isinstance(name, str)
            or not name
            or filename != f"{position:03d}_{name}.sql"
            or not isinstance(checksum, str)
            or not DIGEST_PATTERN.fullmatch(checksum)
        ):
            raise MetadataError("migration_manifest_invalid")
        migration_path = directory / filename
        if migration_path.is_symlink() or not migration_path.is_file():
            raise MetadataError("migration_manifest_invalid")
        if sha256_file(migration_path) != checksum:
            raise MetadataError("migration_checksum_invalid")
        bindings.append(MigrationBinding(version, name, checksum))
    sql_names = {path.name for path in directory.glob("*.sql") if path.is_file()}
    if sql_names != {f"{item.version:03d}_{item.name}.sql" for item in bindings}:
        raise MetadataError("migration_manifest_invalid")
    return sha256_file(manifest), tuple(bindings)
