# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import gzip
import io
import json
import os
import sqlite3
import tarfile
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from digital_colleagues.operations.backup_restore import (
    BackupError,
    backup_database,
    restore_database,
    verify_backup,
)
from tests.p6.fixtures import build_harness
from tests.p8.fixtures import (
    ROOT,
    canonical_database_state,
    create_full_state,
    required_state_counts,
    write_release_manifest,
)


class P8BackupRestoreTests(unittest.TestCase):
    def test_live_wal_backup_restore_preserves_identity_authority_work_and_causality(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-backup-") as name:
            root = Path(name)
            database = root / "state.sqlite"
            release_manifest = write_release_manifest(root)
            harness, _ = create_full_state(database)
            before = canonical_database_state(database)
            counts = required_state_counts(database)
            for category in (
                "profile",
                "mandate",
                "colleague_policy",
                "finite_work",
                "input_event",
                "timer_occurrence",
                "wake_cycle",
                "agenda_item",
                "effect_proposal",
                "human_approval",
                "action_result",
                "audit_records",
                "drafts",
                "confirmations",
                "memberships",
                "sessions",
            ):
                self.assertGreater(counts[category], 0, category)
            backup = root / "private-backup.tar.gz"
            report = backup_database(
                database,
                backup,
                release_manifest=release_manifest,
                migrations_directory=ROOT / "migrations",
                created_at=datetime(2026, 9, 6, tzinfo=UTC),
                backup_id="backup-" + ("1" * 32),
            )
            self.assertEqual((report.status, report.schema_version), ("created", 7))
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                verify_backup(
                    backup,
                    release_manifest=release_manifest,
                    migrations_directory=ROOT / "migrations",
                ).status,
                "verified",
            )

            harness.store._connection.execute(  # noqa: SLF001
                "UPDATE domain_records SET revision = revision + 50 WHERE record_type = 'finite_work'"
            )
            changed = canonical_database_state(database)
            self.assertNotEqual(changed, before)
            harness.store.close()
            rollback = root / "pre-restore-rollback.tar.gz"
            restored = restore_database(
                backup,
                database,
                release_manifest=release_manifest,
                migrations_directory=ROOT / "migrations",
                replace=True,
                offline_confirmed=True,
                rollback_backup=rollback,
            )
            self.assertTrue(restored.rollback_backup_created)
            self.assertEqual(canonical_database_state(database), before)
            self.assertEqual(
                verify_backup(
                    rollback,
                    release_manifest=release_manifest,
                    migrations_directory=ROOT / "migrations",
                ).status,
                "verified",
            )
            restored_harness = build_harness(database)
            self.assertEqual(restored_harness.store.healthcheck()["migration_count"], 7)
            restored_harness.store.close()

    def test_restore_rejects_existing_state_corruption_and_incompatible_manifest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-refusal-") as name:
            root = Path(name)
            database = root / "state.sqlite"
            release_manifest = write_release_manifest(root)
            harness, _ = create_full_state(database)
            harness.store.close()
            backup = root / "backup.tar.gz"
            backup_database(
                database,
                backup,
                release_manifest=release_manifest,
                migrations_directory=ROOT / "migrations",
            )
            with self.assertRaisesRegex(BackupError, "restore_existing_state_refused"):
                restore_database(
                    backup,
                    database,
                    release_manifest=release_manifest,
                    migrations_directory=ROOT / "migrations",
                )
            truncated = root / "truncated.tar.gz"
            truncated.write_bytes(backup.read_bytes()[:100])
            with self.assertRaises(BackupError):
                verify_backup(
                    truncated,
                    release_manifest=release_manifest,
                    migrations_directory=ROOT / "migrations",
                )
            incompatible = write_release_manifest(root, migration_digest="sha256:" + ("0" * 64))
            with self.assertRaisesRegex(BackupError, "migration_manifest_incompatible"):
                verify_backup(
                    backup,
                    release_manifest=incompatible,
                    migrations_directory=ROOT / "migrations",
                )

    def test_archive_path_traversal_symlink_unknown_member_and_future_schema_fail_closed(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-archive-") as name:
            root = Path(name)
            release_manifest = write_release_manifest(root)
            for label, members in (
                ("traversal", (("../state.sqlite", b"x", tarfile.REGTYPE),)),
                ("symlink", (("manifest.json", b"", tarfile.SYMTYPE),)),
                ("unknown", (("unknown.json", b"{}", tarfile.REGTYPE),)),
            ):
                path = root / f"{label}.tar.gz"
                with path.open("wb") as raw:
                    with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
                        with tarfile.open(fileobj=compressed, mode="w") as archive:
                            for member_name, content, member_type in members:
                                info = tarfile.TarInfo(member_name)
                                info.type = member_type
                                info.size = len(content)
                                if member_type == tarfile.SYMTYPE:
                                    info.linkname = "state.sqlite"
                                archive.addfile(info, io.BytesIO(content))
                with self.assertRaises(BackupError, msg=label):
                    verify_backup(
                        path,
                        release_manifest=release_manifest,
                        migrations_directory=ROOT / "migrations",
                    )

            future = root / "future.sqlite"
            connection = sqlite3.connect(future)
            try:
                connection.execute(
                    "CREATE TABLE schema_migrations(version INTEGER, name TEXT, checksum TEXT)"
                )
                connection.execute(
                    "INSERT INTO schema_migrations VALUES(8, 'future', ?)",
                    ("sha256:" + ("0" * 64),),
                )
                connection.commit()
            finally:
                connection.close()
            with self.assertRaisesRegex(BackupError, "database_(?:schema|migration)_incompatible"):
                backup_database(
                    future,
                    root / "future.tar.gz",
                    release_manifest=release_manifest,
                    migrations_directory=ROOT / "migrations",
                )

    def test_backup_output_never_overwrites_and_archive_has_exact_private_members(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-private-") as name:
            root = Path(name)
            database = root / "state.sqlite"
            release_manifest = write_release_manifest(root)
            harness, _ = create_full_state(database)
            harness.store.close()
            backup = root / "backup.tar.gz"
            backup_database(
                database,
                backup,
                release_manifest=release_manifest,
                migrations_directory=ROOT / "migrations",
            )
            original = backup.read_bytes()
            with self.assertRaisesRegex(BackupError, "backup_destination_exists"):
                backup_database(
                    database,
                    backup,
                    release_manifest=release_manifest,
                    migrations_directory=ROOT / "migrations",
                )
            self.assertEqual(backup.read_bytes(), original)
            with tarfile.open(backup, mode="r:gz") as archive:
                self.assertEqual(
                    [item.name for item in archive.getmembers()], ["manifest.json", "state.sqlite"]
                )
                manifest_file = archive.extractfile("manifest.json")
                assert manifest_file is not None
                manifest = json.load(manifest_file)
            self.assertEqual(manifest["backup_format_version"], 1)
            self.assertEqual(manifest["migration_versions"], list(range(1, 8)))
            self.assertEqual(manifest["evidence_class"], "operator_private")
            self.assertNotIn(str(root), json.dumps(manifest))
            wal = Path(str(database) + "-wal")
            self.assertFalse(wal.exists() and os.path.getsize(wal) > 0)
