# SPDX-License-Identifier: Apache-2.0

"""Consistent SQLite online backup and fail-closed atomic restore."""

from __future__ import annotations

import gzip
import io
import json
import os
import re
import secrets
import sqlite3
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn, cast
from urllib.parse import quote

from digital_colleagues.operations.metadata import (
    MetadataError,
    MigrationBinding,
    ReleaseBinding,
    load_migration_bindings,
    load_release_binding,
    sha256_file,
)

BACKUP_FORMAT_VERSION = 1
BACKUP_MEMBERS = ("manifest.json", "state.sqlite")
MAX_MANIFEST_BYTES = 64 * 1024
MAX_DATABASE_BYTES = 1024 * 1024 * 1024
BACKUP_ID_PATTERN = re.compile(r"^backup-[0-9a-f]{32}$")


class BackupError(RuntimeError):
    """A private backup or restore operation failed with a finite safe category."""


@dataclass(frozen=True)
class BackupReport:
    status: str
    schema_version: int
    migration_count: int


@dataclass(frozen=True)
class RestoreReport:
    status: str
    schema_version: int
    migration_count: int
    rollback_backup_created: bool


def _raise(category: str, cause: BaseException | None = None) -> NoReturn:
    if cause is None:
        raise BackupError(category)
    raise BackupError(category) from cause


def _require_regular_no_symlink(path: Path, category: str) -> None:
    try:
        if path.is_symlink() or not path.is_file():
            _raise(category)
    except OSError as exc:
        _raise(category, exc)


def _require_safe_parent(path: Path) -> None:
    parent = path.parent
    try:
        if not parent.is_dir() or parent.is_symlink():
            _raise("destination_parent_invalid")
    except OSError as exc:
        _raise("destination_parent_invalid", exc)


def _open_read_only(path: Path) -> sqlite3.Connection:
    uri = "file:" + quote(path.absolute().as_posix(), safe="/") + "?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=5)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
    except sqlite3.Error as exc:
        _raise("database_open_failed", exc)


def _database_migrations(
    connection: sqlite3.Connection, expected: tuple[MigrationBinding, ...]
) -> tuple[MigrationBinding, ...]:
    try:
        integrity = connection.execute("PRAGMA quick_check").fetchone()
        if integrity != ("ok",):
            _raise("database_integrity_failed")
        rows = connection.execute(
            "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
        ).fetchall()
    except sqlite3.Error as exc:
        _raise("database_schema_invalid", exc)
    if not rows or len(rows) != len(expected):
        _raise("database_schema_incompatible")
    applied: list[MigrationBinding] = []
    for position, row in enumerate(rows):
        if (
            not isinstance(row[0], int)
            or not isinstance(row[1], str)
            or not isinstance(row[2], str)
        ):
            _raise("database_schema_invalid")
        binding = MigrationBinding(row[0], row[1], row[2])
        if binding != expected[position]:
            _raise("database_migration_incompatible")
        applied.append(binding)
    return tuple(applied)


def _bindings(
    *, release_manifest: Path, migrations_directory: Path
) -> tuple[ReleaseBinding, tuple[MigrationBinding, ...]]:
    try:
        release = load_release_binding(release_manifest)
        digest, migrations = load_migration_bindings(migrations_directory)
    except MetadataError as exc:
        _raise(str(exc), exc)
    if digest != release.migration_manifest_digest:
        _raise("migration_manifest_incompatible")
    return release, migrations


def _json_bytes(value: dict[str, object]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _tar_info(name: str, size: int, mtime: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = 0o600
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = mtime
    return info


def _write_archive(output: Path, *, manifest: bytes, database: Path, created_at: datetime) -> None:
    _require_safe_parent(output)
    if output.exists() or output.is_symlink():
        _raise("backup_destination_exists")
    temporary_name: str | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=".dc-backup-", dir=output.parent)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with tarfile.open(
                    mode="w", fileobj=compressed, format=tarfile.PAX_FORMAT
                ) as archive:
                    timestamp = int(created_at.timestamp())
                    archive.addfile(
                        _tar_info("manifest.json", len(manifest), timestamp), io.BytesIO(manifest)
                    )
                    size = database.stat().st_size
                    with database.open("rb") as source:
                        archive.addfile(_tar_info("state.sqlite", size, timestamp), source)
            raw.flush()
            os.fsync(raw.fileno())
        os.chmod(temporary_name, 0o600)
        os.link(temporary_name, output)
        os.unlink(temporary_name)
        temporary_name = None
    except (OSError, tarfile.TarError) as exc:
        _raise("backup_write_failed", exc)
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass


def backup_database(
    database: Path,
    output: Path,
    *,
    release_manifest: Path,
    migrations_directory: Path,
    created_at: datetime | None = None,
    backup_id: str | None = None,
) -> BackupReport:
    _require_regular_no_symlink(database, "database_source_invalid")
    release, expected = _bindings(
        release_manifest=release_manifest, migrations_directory=migrations_directory
    )
    now = created_at or datetime.now(UTC)
    if now.tzinfo is None or now.utcoffset() != UTC.utcoffset(now):
        _raise("backup_time_invalid")
    identifier = backup_id or "backup-" + secrets.token_hex(16)
    if not BACKUP_ID_PATTERN.fullmatch(identifier):
        _raise("backup_identifier_invalid")
    with tempfile.TemporaryDirectory(prefix="digital-colleagues-backup-") as temporary:
        snapshot = Path(temporary) / "state.sqlite"
        source = _open_read_only(database)
        try:
            applied = _database_migrations(source, expected)
            target = sqlite3.connect(snapshot)
            try:
                source.backup(target)
            except sqlite3.Error as exc:
                _raise("database_backup_failed", exc)
            finally:
                target.close()
        finally:
            source.close()
        os.chmod(snapshot, 0o600)
        verified = _open_read_only(snapshot)
        try:
            snapshot_applied = _database_migrations(verified, expected)
        finally:
            verified.close()
        if snapshot_applied != applied:
            _raise("database_backup_inconsistent")
        if not 0 < snapshot.stat().st_size <= MAX_DATABASE_BYTES:
            _raise("database_backup_size_invalid")
        manifest = {
            "schema_version": 1,
            "backup_format_version": BACKUP_FORMAT_VERSION,
            "backup_id": identifier,
            "created_at": now.isoformat().replace("+00:00", "Z"),
            "release_version": release.release_version,
            "source_commit": release.source_commit,
            "schema_version_current": applied[-1].version,
            "migration_versions": [item.version for item in applied],
            "migration_manifest_digest": release.migration_manifest_digest,
            "database_digest": sha256_file(snapshot),
            "database_size_bytes": snapshot.stat().st_size,
            "evidence_class": "operator_private",
        }
        _write_archive(output, manifest=_json_bytes(manifest), database=snapshot, created_at=now)
    return BackupReport("created", applied[-1].version, len(applied))


def _read_archive(archive_path: Path, staging: Path) -> dict[str, object]:
    _require_regular_no_symlink(archive_path, "backup_archive_invalid")
    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            members = archive.getmembers()
            if tuple(member.name for member in members) != BACKUP_MEMBERS:
                _raise("backup_archive_members_invalid")
            if any(
                not member.isfile()
                or member.issym()
                or member.islnk()
                or member.name.startswith("/")
                or ".." in Path(member.name).parts
                for member in members
            ):
                _raise("backup_archive_members_invalid")
            if (
                members[0].size > MAX_MANIFEST_BYTES
                or not 0 < members[1].size <= MAX_DATABASE_BYTES
            ):
                _raise("backup_archive_size_invalid")
            manifest_handle = archive.extractfile(members[0])
            database_handle = archive.extractfile(members[1])
            if manifest_handle is None or database_handle is None:
                _raise("backup_archive_members_invalid")
            manifest_bytes = manifest_handle.read(MAX_MANIFEST_BYTES + 1)
            try:
                manifest = json.loads(manifest_bytes.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                _raise("backup_manifest_invalid", exc)
            if not isinstance(manifest, dict):
                _raise("backup_manifest_invalid")
            with staging.open("xb") as output:
                remaining = members[1].size
                while remaining:
                    block = database_handle.read(min(1024 * 1024, remaining))
                    if not block:
                        _raise("backup_archive_truncated")
                    output.write(block)
                    remaining -= len(block)
                if database_handle.read(1):
                    _raise("backup_archive_size_invalid")
                output.flush()
                os.fsync(output.fileno())
            os.chmod(staging, 0o600)
            return cast(dict[str, object], manifest)
    except BackupError:
        raise
    except (EOFError, OSError, tarfile.TarError) as exc:
        _raise("backup_archive_invalid", exc)


def _validate_manifest(
    manifest: dict[str, object],
    *,
    release: ReleaseBinding,
    applied: tuple[MigrationBinding, ...],
    database: Path,
) -> None:
    required = {
        "schema_version",
        "backup_format_version",
        "backup_id",
        "created_at",
        "release_version",
        "source_commit",
        "schema_version_current",
        "migration_versions",
        "migration_manifest_digest",
        "database_digest",
        "database_size_bytes",
        "evidence_class",
    }
    if set(manifest) != required:
        _raise("backup_manifest_invalid")
    identifier = manifest.get("backup_id")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("backup_format_version") != BACKUP_FORMAT_VERSION
        or not isinstance(identifier, str)
        or not BACKUP_ID_PATTERN.fullmatch(identifier)
        or manifest.get("release_version") != release.release_version
        or manifest.get("source_commit") != release.source_commit
        or manifest.get("migration_manifest_digest") != release.migration_manifest_digest
        or manifest.get("schema_version_current") != applied[-1].version
        or manifest.get("migration_versions") != [item.version for item in applied]
        or manifest.get("database_digest") != sha256_file(database)
        or manifest.get("database_size_bytes") != database.stat().st_size
        or manifest.get("evidence_class") != "operator_private"
    ):
        _raise("backup_manifest_incompatible")
    created_at = manifest.get("created_at")
    if not isinstance(created_at, str) or not created_at.endswith("Z"):
        _raise("backup_manifest_invalid")
    try:
        parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError as exc:
        _raise("backup_manifest_invalid", exc)
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        _raise("backup_manifest_invalid")


def _verified_backup(
    archive_path: Path,
    staging: Path,
    *,
    release_manifest: Path,
    migrations_directory: Path,
) -> tuple[dict[str, object], tuple[MigrationBinding, ...]]:
    release, expected = _bindings(
        release_manifest=release_manifest, migrations_directory=migrations_directory
    )
    manifest = _read_archive(archive_path, staging)
    connection = _open_read_only(staging)
    try:
        applied = _database_migrations(connection, expected)
    finally:
        connection.close()
    _validate_manifest(manifest, release=release, applied=applied, database=staging)
    return manifest, applied


def verify_backup(
    archive_path: Path, *, release_manifest: Path, migrations_directory: Path
) -> BackupReport:
    with tempfile.TemporaryDirectory(prefix="digital-colleagues-backup-verify-") as temporary:
        staging = Path(temporary) / "state.sqlite"
        _, applied = _verified_backup(
            archive_path,
            staging,
            release_manifest=release_manifest,
            migrations_directory=migrations_directory,
        )
    return BackupReport("verified", applied[-1].version, len(applied))


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def restore_database(
    archive_path: Path,
    database: Path,
    *,
    release_manifest: Path,
    migrations_directory: Path,
    replace: bool = False,
    offline_confirmed: bool = False,
    rollback_backup: Path | None = None,
) -> RestoreReport:
    _require_safe_parent(database)
    if database.is_symlink():
        _raise("restore_destination_invalid")
    destination_exists = database.exists()
    if destination_exists and (not replace or not offline_confirmed or rollback_backup is None):
        _raise("restore_existing_state_refused")
    if not destination_exists and (replace or offline_confirmed or rollback_backup is not None):
        _raise("restore_options_invalid")
    if rollback_backup is not None and rollback_backup.absolute() == archive_path.absolute():
        _raise("rollback_backup_invalid")
    descriptor: int | None = None
    staging_path: Path | None = None
    rollback_created = False
    try:
        descriptor, name = tempfile.mkstemp(prefix=".dc-restore-", dir=database.parent)
        os.close(descriptor)
        descriptor = None
        staging_path = Path(name)
        staging_path.unlink()
        _, applied = _verified_backup(
            archive_path,
            staging_path,
            release_manifest=release_manifest,
            migrations_directory=migrations_directory,
        )
        if destination_exists:
            assert rollback_backup is not None
            backup_database(
                database,
                rollback_backup,
                release_manifest=release_manifest,
                migrations_directory=migrations_directory,
            )
            rollback_created = True
            for suffix in ("-wal", "-shm"):
                sidecar = Path(str(database) + suffix)
                if sidecar.is_symlink():
                    _raise("restore_destination_invalid")
                try:
                    sidecar.unlink(missing_ok=True)
                except OSError as exc:
                    _raise("restore_destination_busy", exc)
        os.chmod(staging_path, 0o600)
        os.replace(staging_path, database)
        staging_path = None
        with database.open("rb") as installed:
            os.fsync(installed.fileno())
        _fsync_directory(database.parent)
    except BackupError:
        raise
    except OSError as exc:
        _raise("restore_install_failed", exc)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if staging_path is not None:
            try:
                staging_path.unlink()
            except OSError:
                pass
    return RestoreReport("restored", applied[-1].version, len(applied), rollback_created)
