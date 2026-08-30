# SPDX-License-Identifier: Apache-2.0

"""Fail-closed numbered and checksummed SQLite migrations."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from digital_colleagues.core.serialization import datetime_to_z


class MigrationError(RuntimeError):
    """The local schema cannot be trusted or safely advanced."""


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    file: str
    checksum: str


class MigrationRunner:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def _load(self) -> tuple[Migration, ...]:
        try:
            raw: Any = json.loads((self._directory / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise MigrationError("migration manifest is unavailable or invalid") from exc
        if not isinstance(raw, dict) or set(raw) != {"schema_version", "migrations"}:
            raise MigrationError("migration manifest has an unsupported shape")
        if raw["schema_version"] != 1 or not isinstance(raw["migrations"], list):
            raise MigrationError("migration manifest version is unsupported")
        migrations: list[Migration] = []
        for position, item in enumerate(raw["migrations"], start=1):
            if not isinstance(item, dict) or set(item) != {
                "version",
                "name",
                "file",
                "checksum",
            }:
                raise MigrationError("migration manifest entry is invalid")
            migration = Migration(**item)
            candidate = PurePosixPath(migration.file)
            if (
                type(migration.version) is not int
                or migration.version != position
                or not migration.name
                or candidate.is_absolute()
                or len(candidate.parts) != 1
                or candidate.name != f"{position:03d}_{migration.name}.sql"
            ):
                raise MigrationError("migration order or identity is invalid")
            try:
                content = (self._directory / migration.file).read_bytes()
            except OSError as exc:
                raise MigrationError("migration content is unavailable") from exc
            actual = "sha256:" + hashlib.sha256(content).hexdigest()
            if actual != migration.checksum:
                raise MigrationError("migration checksum does not match immutable manifest")
            migrations.append(migration)
        if not migrations:
            raise MigrationError("at least one migration is required")
        actual_sql = {path.name for path in self._directory.glob("*.sql") if path.is_file()}
        if actual_sql != {migration.file for migration in migrations}:
            raise MigrationError("unmanifested or missing migration content was found")
        return tuple(migrations)

    @staticmethod
    def _statements(content: str) -> tuple[str, ...]:
        statements = tuple(part.strip() for part in content.split(";") if part.strip())
        if not statements:
            raise MigrationError("a migration contains no SQL statements")
        return statements

    def apply(
        self, connection: sqlite3.Connection, *, applied_at: datetime
    ) -> tuple[Migration, ...]:
        migrations = self._load()
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              version INTEGER PRIMARY KEY,
              name TEXT NOT NULL,
              checksum TEXT NOT NULL,
              applied_at TEXT NOT NULL
            )
            """
        )
        rows = connection.execute(
            "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
        ).fetchall()
        if any(type(row[0]) is not int or row[0] < 1 for row in rows):
            raise MigrationError("applied migration metadata is invalid")
        if rows and rows[-1][0] > migrations[-1].version:
            raise MigrationError("database schema is newer than this runtime")
        expected_by_version = {item.version: item for item in migrations}
        for version, name, checksum in rows:
            expected = expected_by_version.get(version)
            if expected is None or expected.name != name or expected.checksum != checksum:
                raise MigrationError("an applied migration identity or checksum changed")
        applied_versions = {row[0] for row in rows}
        for migration in migrations:
            if migration.version in applied_versions:
                continue
            try:
                content = (self._directory / migration.file).read_text(encoding="utf-8")
                connection.execute("BEGIN IMMEDIATE")
                for statement in self._statements(content):
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations(version, name, checksum, applied_at) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        migration.version,
                        migration.name,
                        migration.checksum,
                        datetime_to_z(applied_at),
                    ),
                )
                connection.execute("COMMIT")
            except (OSError, UnicodeError, sqlite3.Error, ValueError) as exc:
                try:
                    connection.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise MigrationError("migration application failed atomically") from exc
        return migrations
