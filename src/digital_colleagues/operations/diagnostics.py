# SPDX-License-Identifier: Apache-2.0

"""Allowlisted, bounded, path-free local support bundle generation."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import platform
import sqlite3
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

from digital_colleagues.operations.backup_restore import (
    BackupError,
    _bindings,
    _database_migrations,
    _open_read_only,
    _require_regular_no_symlink,
    _require_safe_parent,
    _tar_info,
)

MAX_CAUSAL_IDENTIFIERS = 16
MAX_IDENTIFIER_BYTES = 256


class DiagnosticsError(RuntimeError):
    """A diagnostics operation failed with a finite safe category."""


@dataclass(frozen=True)
class DiagnosticsReport:
    status: str
    schema_version: int
    causal_digest_count: int


def _causal_digest(value: str) -> str:
    encoded = value.encode("utf-8")
    if not encoded or len(encoded) > MAX_IDENTIFIER_BYTES or any(ord(char) < 32 for char in value):
        raise DiagnosticsError("causal_identifier_invalid")
    return "sha256:" + hashlib.sha256(b"p8-diagnostics-causal-v1\0" + encoded).hexdigest()


def _payload(
    database: Path,
    *,
    release_manifest: Path,
    migrations_directory: Path,
    causal_identifiers: tuple[str, ...],
) -> dict[str, object]:
    if len(causal_identifiers) > MAX_CAUSAL_IDENTIFIERS:
        raise DiagnosticsError("causal_identifier_limit")
    try:
        _require_regular_no_symlink(database, "database_source_invalid")
        release, expected = _bindings(
            source_binding=release_manifest, migrations_directory=migrations_directory
        )
        connection = _open_read_only(database)
        try:
            applied = _database_migrations(connection, expected)
        finally:
            connection.close()
    except BackupError as exc:
        raise DiagnosticsError(str(exc)) from exc
    return {
        "schema_version": 1,
        "bundle_format_version": 1,
        "release": {
            "version": release.release_version,
            "source_commit": release.source_commit,
        },
        "database": {
            "schema_version": applied[-1].version,
            "migration_versions": [item.version for item in applied],
            "migration_checksums": "verified",
            "integrity": "passed",
        },
        "environment": {
            "python": f"{platform.python_version_tuple()[0]}.{platform.python_version_tuple()[1]}",
            "sqlite": ".".join(sqlite3.sqlite_version.split(".")[:2]),
            "platform": platform.system().lower(),
        },
        "health": {"database": "passed", "release_binding": "passed"},
        "causal_identifier_digests": sorted(_causal_digest(value) for value in causal_identifiers),
        "evidence_class": "operator_private_redacted",
    }


def create_diagnostics_bundle(
    database: Path,
    output: Path,
    *,
    release_manifest: Path,
    migrations_directory: Path,
    causal_identifiers: tuple[str, ...] = (),
) -> DiagnosticsReport:
    payload = _payload(
        database,
        release_manifest=release_manifest,
        migrations_directory=migrations_directory,
        causal_identifiers=causal_identifiers,
    )
    try:
        _require_safe_parent(output)
    except BackupError as exc:
        raise DiagnosticsError(str(exc)) from exc
    if output.exists() or output.is_symlink():
        raise DiagnosticsError("diagnostics_destination_exists")
    serialized = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temporary_name: str | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=".dc-diagnostics-", dir=output.parent)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with tarfile.open(
                    mode="w", fileobj=compressed, format=tarfile.PAX_FORMAT
                ) as archive:
                    archive.addfile(
                        _tar_info("diagnostics.json", len(serialized), 0), io.BytesIO(serialized)
                    )
            raw.flush()
            os.fsync(raw.fileno())
        os.chmod(temporary_name, 0o600)
        os.link(temporary_name, output)
        os.unlink(temporary_name)
        temporary_name = None
    except (OSError, tarfile.TarError) as exc:
        raise DiagnosticsError("diagnostics_write_failed") from exc
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
    database_summary = payload["database"]
    if (
        not isinstance(database_summary, dict)
        or type(database_summary.get("schema_version")) is not int
    ):
        raise DiagnosticsError("diagnostics_payload_invalid")
    return DiagnosticsReport("created", database_summary["schema_version"], len(causal_identifiers))
