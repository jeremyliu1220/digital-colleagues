# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from digital_colleagues.adapters.sqlite.migrations import MigrationError
from digital_colleagues.adapters.sqlite.store import SQLiteRuntimeStore
from digital_colleagues.adapters.system.deterministic import FixedClock, StableHashIdentifier
from digital_colleagues.application.contracts import RequestPrincipalContext
from digital_colleagues.application.errors import ConflictError, NotFoundError
from digital_colleagues.application.services import BootstrapService, EventService
from tests.p3.fixtures import (
    T0,
    T1,
    T2,
    T3,
    admin,
    finite_work,
    input_event,
    mandate,
    namespace,
    other_namespace,
    principals,
    profile,
    request_for_event,
    service,
    user,
)
from tests.p3.scenario import ROOT, approve, new_store, prepare_proposal


class SQLiteSemanticsTests(unittest.TestCase):
    def test_migration_order_checksum_tampering_and_future_schema_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-migrations-") as temporary:
            root = Path(temporary)
            migrations = root / "migrations"
            shutil.copytree(ROOT / "migrations", migrations)
            database = root / "state.sqlite"
            store = SQLiteRuntimeStore(database, migrations_path=migrations, clock=FixedClock(T0))
            store.close()
            initial = migrations / "001_initial.sql"
            initial.write_text(initial.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaises(MigrationError):
                SQLiteRuntimeStore(database, migrations_path=migrations, clock=FixedClock(T0))
            shutil.rmtree(migrations)
            shutil.copytree(ROOT / "migrations", migrations)
            connection = sqlite3.connect(database)
            connection.execute(
                "INSERT INTO schema_migrations(version, name, checksum, applied_at) "
                "VALUES (99, 'future', 'sha256:future', '2026-02-03T04:05:06.000000Z')"
            )
            connection.commit()
            connection.close()
            with self.assertRaises(MigrationError):
                SQLiteRuntimeStore(database, migrations_path=migrations, clock=FixedClock(T0))

    def test_migration_failure_rolls_back_without_partial_schema_or_metadata(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="digital-colleagues-p3-migration-rollback-"
        ) as temporary:
            root = Path(temporary)
            migrations = root / "migrations"
            shutil.copytree(ROOT / "migrations", migrations)
            database = root / "state.sqlite"
            store = SQLiteRuntimeStore(database, migrations_path=migrations, clock=FixedClock(T0))
            store.close()
            current_manifest = json.loads(
                (migrations / "manifest.json").read_text(encoding="utf-8")
            )
            current_versions = [item["version"] for item in current_manifest["migrations"]]
            next_version = len(current_manifest["migrations"]) + 1
            bad = migrations / f"{next_version:03d}_atomic_failure.sql"
            bad.write_text(
                "CREATE TABLE must_rollback(value TEXT);\nTHIS IS NOT SQL;\n",
                encoding="utf-8",
            )
            manifest = current_manifest
            manifest["migrations"].append(
                {
                    "version": next_version,
                    "name": "atomic_failure",
                    "file": bad.name,
                    "checksum": "sha256:" + hashlib.sha256(bad.read_bytes()).hexdigest(),
                }
            )
            (migrations / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(MigrationError):
                SQLiteRuntimeStore(database, migrations_path=migrations, clock=FixedClock(T0))
            connection = sqlite3.connect(database)
            tables = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
            versions = [
                row[0]
                for row in connection.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                )
            ]
            connection.close()
            self.assertNotIn("must_rollback", tables)
            self.assertEqual(versions, current_versions)

    def test_v2_database_upgrades_to_timer_schema_without_losing_durable_records(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-v2-upgrade-") as temporary:
            root = Path(temporary)
            migrations = root / "migrations"
            migrations.mkdir()
            current_manifest = json.loads(
                (ROOT / "migrations" / "manifest.json").read_text(encoding="utf-8")
            )
            for filename in ("001_initial.sql", "002_runtime_indexes.sql"):
                shutil.copy2(ROOT / "migrations" / filename, migrations / filename)
            v2_manifest = dict(current_manifest)
            v2_manifest["migrations"] = current_manifest["migrations"][:2]
            (migrations / "manifest.json").write_text(json.dumps(v2_manifest), encoding="utf-8")
            database = root / "state.sqlite"
            v2 = SQLiteRuntimeStore(database, migrations_path=migrations, clock=FixedClock(T0))
            BootstrapService(v2, FixedClock(T0)).initialize(
                context=RequestPrincipalContext(namespace(), admin()),
                principals=principals(),
                profile=profile(),
                mandate=mandate(),
                work=finite_work(),
                correlation_id="correlation-v2-upgrade",
            )
            v2.close()

            for entry in current_manifest["migrations"][2:]:
                filename = entry["file"]
                shutil.copy2(ROOT / "migrations" / filename, migrations / filename)
            (migrations / "manifest.json").write_text(
                json.dumps(current_manifest), encoding="utf-8"
            )
            upgraded = SQLiteRuntimeStore(
                database, migrations_path=migrations, clock=FixedClock(T1)
            )
            versions = [
                row[0]
                for row in upgraded._connection.execute(  # noqa: SLF001
                    "SELECT version FROM schema_migrations ORDER BY version"
                )
            ]
            tables = {
                row[0]
                for row in upgraded._connection.execute(  # noqa: SLF001
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertEqual(
                versions,
                [item["version"] for item in current_manifest["migrations"]],
            )
            self.assertIn("timer_triggers", tables)
            self.assertIn("p4_sessions", tables)
            self.assertEqual(upgraded.get_profile(namespace(), "profile-synthetic"), profile())
            self.assertEqual(upgraded.get_work(namespace(), "work-synthetic"), finite_work())
            upgraded.close()

    def test_every_store_connection_enables_wal_foreign_keys_and_busy_handling(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-pragmas-") as temporary:
            store = new_store(Path(temporary) / "state.sqlite")
            health = store.healthcheck()
            self.assertEqual(health["journal_mode"], "wal")
            self.assertTrue(health["foreign_keys"])
            busy_timeout = health["busy_timeout_ms"]
            self.assertIsInstance(busy_timeout, int)
            assert isinstance(busy_timeout, int)
            self.assertGreaterEqual(busy_timeout, 1)
            with self.assertRaises(sqlite3.IntegrityError):
                store._connection.execute(  # noqa: SLF001 - mechanical foreign-key probe
                    """
                    INSERT INTO audit_records(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      audit_id, record_type, record_id, record_revision,
                      actor_principal_id, correlation_id, occurred_at,
                      payload_digest, safe_projection_json
                    ) VALUES (1, 'tenant-synthetic', 'colleague', 'colleague-synthetic',
                              'audit:missing', 'missing', 'missing', 1,
                              'human-admin', 'correlation-missing',
                              '2026-02-03T04:05:06.000000Z',
                              'sha256:0000000000000000000000000000000000000000000000000000000000000000',
                              '{}')
                    """
                )
            store.close()

    def test_namespace_isolation_and_atomic_bootstrap_rollback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-namespace-") as temporary:
            store = new_store(Path(temporary) / "state.sqlite")
            bootstrap = BootstrapService(store, FixedClock(T0))
            with self.assertRaises(ConflictError):
                bootstrap.initialize(
                    context=RequestPrincipalContext(namespace(), admin()),
                    principals=principals() + (replace(service(), namespace=service().namespace),),
                    profile=profile(),
                    mandate=mandate(),
                    work=finite_work(),
                    correlation_id="correlation-bootstrap",
                )
            for table in (
                "domain_records",
                "audit_records",
                "triggers",
                "agenda_runtime",
                "outbox",
                "replay_ledger",
            ):
                count = store._connection.execute(  # noqa: SLF001
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
                self.assertEqual(count, 0, table)
            bootstrap.initialize(
                context=RequestPrincipalContext(namespace(), admin()),
                principals=principals(),
                profile=profile(),
                mandate=mandate(),
                work=finite_work(),
                correlation_id="correlation-bootstrap",
            )
            with self.assertRaises(NotFoundError):
                store.get_profile(other_namespace(), "profile-synthetic")
            self.assertEqual(store.get_profile(namespace(), "profile-synthetic"), profile())
            store.close()

    def test_transaction_crash_and_optimistic_revision_conflict_roll_back_atomically(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-uow-") as temporary:
            store = new_store(Path(temporary) / "state.sqlite")
            BootstrapService(store, FixedClock(T0)).initialize(
                context=RequestPrincipalContext(namespace(), admin()),
                principals=principals(),
                profile=profile(),
                mandate=mandate(),
                work=finite_work(),
                correlation_id="correlation-bootstrap",
            )
            original = store.get_mandate(namespace(), "mandate-synthetic")
            revised = replace(original, revision=2, effective_at=T2)
            original_audits = store._connection.execute(  # noqa: SLF001
                "SELECT COUNT(*) FROM audit_records WHERE record_type = 'mandate'"
            ).fetchone()[0]
            with self.assertRaisesRegex(RuntimeError, "synthetic transaction crash"):
                with store._transaction() as connection:  # noqa: SLF001
                    store._update_record(  # noqa: SLF001
                        connection,
                        revised,
                        expected_revision=1,
                    )
                    raise RuntimeError("synthetic transaction crash")
            self.assertEqual(store.get_mandate(namespace(), "mandate-synthetic"), original)
            self.assertEqual(
                store._connection.execute(  # noqa: SLF001
                    "SELECT COUNT(*) FROM audit_records WHERE record_type = 'mandate'"
                ).fetchone()[0],
                original_audits,
            )
            with store._transaction() as connection:  # noqa: SLF001
                store._update_record(  # noqa: SLF001
                    connection,
                    revised,
                    expected_revision=1,
                )
            with self.assertRaises(ConflictError):
                with store._transaction() as connection:  # noqa: SLF001
                    store._update_record(  # noqa: SLF001
                        connection,
                        revised,
                        expected_revision=1,
                    )
            self.assertEqual(store.get_mandate(namespace(), "mandate-synthetic"), revised)
            store.close()

    def test_outbox_lease_takeover_increments_fence_and_refuses_stale_owner(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-outbox-fence-") as temporary:
            scenario = prepare_proposal(
                Path(temporary) / "state.sqlite", identifier_namespace="outbox-fence"
            )
            approve(scenario)
            first = scenario.store.claim_outbox(
                namespace(), owner="outbox-owner-a", now=T2, lease_until=T2
            )
            assert first is not None
            second = scenario.store.claim_outbox(
                namespace(), owner="outbox-owner-b", now=T3, lease_until=T3
            )
            assert second is not None
            self.assertGreater(second.fencing_token, first.fencing_token)
            with self.assertRaises(ConflictError):
                scenario.store.mark_dispatch_started(first, occurred_at=T2)
            started = scenario.store.mark_dispatch_started(second, occurred_at=T2)
            self.assertEqual(started.effect_attempt_id, second.effect_attempt_id)
            scenario.store.close()

    def test_trigger_lease_takeover_increments_fence_and_refuses_stale_owner(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-fencing-") as temporary:
            store = new_store(Path(temporary) / "state.sqlite")
            BootstrapService(store, FixedClock(T0)).initialize(
                context=RequestPrincipalContext(namespace(), admin()),
                principals=principals(),
                profile=profile(),
                mandate=mandate(),
                work=finite_work(),
                correlation_id="correlation-bootstrap",
            )
            EventService(store, StableHashIdentifier("fence"), FixedClock(T0)).submit(
                context=RequestPrincipalContext(namespace(), user()),
                request=request_for_event(input_event()),
                idempotency_key="event-key-fence",
            )
            first = store.claim_trigger(namespace(), owner="owner-a", now=T1, lease_until=T1)
            assert first is not None
            second = store.claim_trigger(namespace(), owner="owner-b", now=T2, lease_until=T2)
            assert second is not None
            self.assertGreater(second.fencing_token, first.fencing_token)
            with self.assertRaises(ConflictError):
                store.materialize_agenda(
                    first,
                    wake_cycle_id="wake-stale",
                    agenda_item_id="agenda-stale",
                    actor=service(),
                    occurred_at=T1,
                )
            store.materialize_agenda(
                second,
                wake_cycle_id="wake-current",
                agenda_item_id="agenda-current",
                actor=service(),
                occurred_at=T1,
            )
            store.close()


if __name__ == "__main__":
    unittest.main()
