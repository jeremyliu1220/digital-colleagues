# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import shutil
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from digital_colleagues.adapters.sqlite.migrations import MigrationError
from digital_colleagues.adapters.sqlite.p6_store import SQLiteP6Store
from digital_colleagues.adapters.sqlite.p11_store import SQLiteP11Store
from digital_colleagues.adapters.system.deterministic import FixedClock, StableHashIdentifier
from digital_colleagues.application.p4_services import (
    AuthenticationService,
    InitialColleagueService,
)
from digital_colleagues.local.security import CredentialDigests
from tests.p4.fixtures import SequenceTokens
from tests.p6.fixtures import initial_request
from tests.p11.fixtures import NOW, ROOT, build_harness


class MigrationTests(unittest.TestCase):
    def test_fresh_install_reaches_schema_eight_without_deployments(self) -> None:
        with TemporaryDirectory() as value:
            harness = build_harness(Path(value) / "fresh.sqlite")
            rows = harness.store._connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
            self.assertEqual([row[0] for row in rows], list(range(1, 9)))
            self.assertEqual(harness.store.list_deployments("tenant-local"), ())
            harness.store.close()

    def test_named_active_limit_triggers_exist(self) -> None:
        with TemporaryDirectory() as value:
            harness = build_harness(Path(value) / "triggers.sqlite")
            names = {
                row[0]
                for row in harness.store._connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'p11_%'"
                )
            }
            self.assertEqual(names, {"p11_active_limit_insert", "p11_active_limit_update"})
            harness.store.close()

    def test_repeated_open_is_idempotent(self) -> None:
        with TemporaryDirectory() as value:
            database = Path(value) / "restart.sqlite"
            first = build_harness(database)
            first.store.close()
            reopened = SQLiteP11Store(
                database, migrations_path=ROOT / "migrations", clock=FixedClock(NOW)
            )
            count = reopened._connection.execute(
                "SELECT COUNT(*) FROM schema_migrations"
            ).fetchone()[0]
            self.assertEqual(count, 8)
            reopened.close()

    def test_retained_manual_creation_receives_legacy_deployment_binding(self) -> None:
        with TemporaryDirectory() as value:
            harness = build_harness(Path(value) / "compatibility.sqlite")
            profile, mandate, _ = InitialColleagueService(
                store=harness.store,
                runtime_store=harness.store,
                identifiers=StableHashIdentifier("p11-compatibility-test"),
                clock=FixedClock(NOW),
            ).create(session=harness.session, request=initial_request())
            deployment = harness.store.get_deployment(profile.namespace)
            self.assertEqual(deployment.profile_id, profile.profile_id)
            self.assertEqual(deployment.mandate_id, mandate.mandate_id)
            self.assertEqual(deployment.lifecycle.value, "active")
            self.assertTrue(deployment.legacy_manual)
            harness.store.close()

    def test_schema_seven_upgrade_preserves_legacy_manual_identity(self) -> None:
        with TemporaryDirectory() as value:
            root = Path(value)
            migrations = root / "migrations"
            migrations.mkdir()
            manifest = json.loads((ROOT / "migrations/manifest.json").read_text())
            manifest["migrations"] = manifest["migrations"][:7]
            (migrations / "manifest.json").write_text(json.dumps(manifest))
            for entry in manifest["migrations"]:
                shutil.copyfile(ROOT / "migrations" / entry["file"], migrations / entry["file"])
            database = root / "legacy.sqlite"
            clock = FixedClock(NOW)
            store = SQLiteP6Store(database, migrations_path=migrations, clock=clock)
            tokens = SequenceTokens([])
            authentication = AuthenticationService(
                store=store,
                clock=clock,
                tokens=tokens,
                digests=CredentialDigests(),
                tenant_id="tenant-local",
            )
            _, token = authentication.ensure_bootstrap()
            assert token is not None
            authentication.claim_operator_retrieval(token)
            session = authentication.exchange(token).session
            identifiers = StableHashIdentifier("legacy-test")
            profile, mandate, _ = InitialColleagueService(
                store=store,
                runtime_store=store,
                identifiers=identifiers,
                clock=clock,
            ).create(session=session, request=initial_request())
            store.close()
            upgraded = SQLiteP11Store(database, migrations_path=ROOT / "migrations", clock=clock)
            deployment = upgraded.get_deployment(profile.namespace)
            self.assertEqual(deployment.profile_id, profile.profile_id)
            self.assertEqual(deployment.mandate_id, mandate.mandate_id)
            self.assertTrue(deployment.legacy_manual)
            self.assertTrue(deployment.legacy_policy_unconfirmed)
            upgraded.close()

    def test_manifest_prefix_is_immutable(self) -> None:
        manifest = json.loads((ROOT / "migrations/manifest.json").read_text())
        self.assertEqual(
            manifest["migrations"][6]["checksum"],
            "sha256:ba572b74ffe7d16ed09ffd58791d7bb23b875806996ec897b2e73c82a593cf9c",
        )
        self.assertEqual(
            manifest["migrations"][7]["file"], "008_agent_packages_and_deployments.sql"
        )

    def test_active_slot_constraint_rejects_out_of_range_value(self) -> None:
        with TemporaryDirectory() as value:
            harness = build_harness(Path(value) / "constraint.sqlite")
            sql = (ROOT / "migrations/008_agent_packages_and_deployments.sql").read_text()
            self.assertIn("active_slot BETWEEN 1 AND 10", sql)
            with self.assertRaises(sqlite3.IntegrityError):
                harness.store._connection.execute(
                    "INSERT INTO p11_colleague_deployments("
                    + "schema_version,tenant_id,namespace_scope,namespace_scope_id,deployment_id,"
                    + "package_id,package_version,package_digest,profile_id,profile_revision,"
                    + "mandate_id,mandate_revision,lifecycle,execution_host_id,active_slot,"
                    + "legacy_manual,legacy_policy_unconfirmed,updated_by_principal_id,"
                    + "updated_by_kind,created_at,updated_at,correlation_id,causation_id,revision"
                    + ") VALUES(1,'tenant-local','colleague','x','x','missing','1.0.0',"
                    + "'sha256:"
                    + "0" * 64
                    + "','p',1,'m',1,'active','local',11,0,0,"
                    + "'x','service','2026-09-09T00:00:00.000000Z',"
                    + "'2026-09-09T00:00:00.000000Z','c','d',1)"
                )
            harness.store.close()

    def test_active_limit_is_global_to_the_local_execution_host(self) -> None:
        with TemporaryDirectory() as value:
            harness = build_harness(Path(value) / "host-limit.sqlite")
            connection = harness.store._connection
            package_digest = "sha256:" + "a" * 64
            archive_digest = "sha256:" + "b" * 64
            timestamp = NOW.isoformat().replace("+00:00", "Z")
            for index in range(1, 12):
                tenant_id = f"tenant-{index}"
                connection.execute(
                    """INSERT INTO p11_package_versions(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      package_id, package_version, package_digest, archive_digest,
                      package_json, source, trust_state, install_state, attestation_json,
                      created_by_principal_id, created_by_kind, created_at, updated_at,
                      correlation_id, causation_id, revision
                    ) VALUES (1, ?, 'tenant', '', 'fixture', '1.0.0', ?, ?, '{}',
                              'local', 'trusted', 'installed', NULL, 'service', 'service',
                              ?, ?, 'correlation', 'causation', 1)""",
                    (tenant_id, package_digest, archive_digest, timestamp, timestamp),
                )
                insert = """INSERT INTO p11_colleague_deployments(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      deployment_id, package_id, package_version, package_digest,
                      profile_id, profile_revision, mandate_id, mandate_revision,
                      policy_id, policy_revision, lifecycle, execution_host_id, active_slot,
                      legacy_manual, legacy_policy_unconfirmed, future_connection_slot,
                      updated_by_principal_id, updated_by_kind, created_at, updated_at,
                      correlation_id, causation_id, revision
                    ) VALUES (1, ?, 'colleague', ?, ?, 'fixture', '1.0.0', ?,
                              'profile', 1, 'mandate', 1, NULL, NULL, 'active', 'local', ?,
                              0, 0, NULL, 'service', 'service', ?, ?,
                              'correlation', 'causation', 1)"""
                arguments = (
                    tenant_id,
                    f"agent-{index}",
                    f"agent-{index}",
                    package_digest,
                    ((index - 1) % 10) + 1,
                    timestamp,
                    timestamp,
                )
                if index <= 10:
                    connection.execute(insert, arguments)
                else:
                    with self.assertRaisesRegex(
                        sqlite3.IntegrityError, "active_deployment_limit_reached"
                    ):
                        connection.execute(insert, arguments)
            harness.store.close()

    def test_legacy_count_above_ten_aborts_migration_atomically(self) -> None:
        with TemporaryDirectory() as value:
            root = Path(value)
            migrations = root / "migrations"
            migrations.mkdir()
            manifest = json.loads((ROOT / "migrations/manifest.json").read_text())
            manifest["migrations"] = manifest["migrations"][:7]
            (migrations / "manifest.json").write_text(json.dumps(manifest))
            for entry in manifest["migrations"]:
                shutil.copyfile(ROOT / "migrations" / entry["file"], migrations / entry["file"])
            database = root / "too-many.sqlite"
            store = SQLiteP6Store(database, migrations_path=migrations, clock=FixedClock(NOW))
            for index in range(11):
                for record_type in ("profile", "mandate"):
                    store._connection.execute(
                        """
                        INSERT INTO domain_records(
                          schema_version, tenant_id, namespace_scope, namespace_scope_id,
                          record_type, record_id, revision, immutable, payload_json,
                          actor_principal_id, correlation_id, causation_id, occurred_at
                        ) VALUES (1, ?, 'colleague', ?, ?, ?, 1, 0, '{}', ?, ?, ?, ?)
                        """,
                        (
                            "tenant-over-limit",
                            f"legacy-{index}",
                            record_type,
                            f"{record_type}-{index}",
                            "migration-fixture",
                            f"correlation-{index}",
                            f"causation-{index}",
                            NOW.isoformat().replace("+00:00", "Z"),
                        ),
                    )
            store.close()
            with self.assertRaises(MigrationError):
                SQLiteP11Store(database, migrations_path=ROOT / "migrations", clock=FixedClock(NOW))
            connection = sqlite3.connect(database)
            try:
                version = connection.execute(
                    "SELECT MAX(version) FROM schema_migrations"
                ).fetchone()[0]
                p11_tables = connection.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name LIKE 'p11_%'"
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(version, 7)
            self.assertEqual(p11_tables, 0)


if __name__ == "__main__":
    unittest.main()
