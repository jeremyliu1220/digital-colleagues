# SPDX-License-Identifier: Apache-2.0

"""Additive SQLite persistence for P11 package and deployment governance."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import cast

from digital_colleagues.adapters.sqlite.codec import from_storage_json, to_storage_json
from digital_colleagues.adapters.sqlite.migrations import MigrationError, MigrationRunner
from digital_colleagues.adapters.sqlite.p6_store import SQLiteP6Store
from digital_colleagues.adapters.sqlite.store import _ns
from digital_colleagues.application.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    PersistenceError,
    ReplayConflictError,
    StaleConflictError,
)
from digital_colleagues.application.p4_contracts import AuthenticatedSession
from digital_colleagues.application.ports import ClockPort
from digital_colleagues.core.agent_package import PackageSource, agent_package_from_mapping
from digital_colleagues.core.authority import Mandate, Profile
from digital_colleagues.core.common import SCHEMA_VERSION, FrozenJsonObject, freeze_json
from digital_colleagues.core.deployment import (
    ALLOWED_LIFECYCLE_TRANSITIONS,
    AttestationVerification,
    ColleagueDeployment,
    DeploymentDraft,
    DeploymentDraftKind,
    DeploymentDraftState,
    DeploymentLifecycle,
    GitHubAttestation,
    LifecycleTransitionResult,
    PackageInstallState,
    PackageRecord,
    PackageTrustState,
)
from digital_colleagues.core.governance import AuthorizationAction
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.policy import ColleaguePolicy
from digital_colleagues.core.principals import HumanRole, Principal, PrincipalKind
from digital_colleagues.core.serialization import (
    contract_to_public_data,
    datetime_from_z,
    datetime_to_z,
)

_LEGACY_PACKAGE_DIGEST = "sha256:060b07c809db61f98486d6feed53042ca7266fb916d4933dc6950ce1d35e23cd"
_LEGACY_PACKAGE_JSON = (
    '{"content":{"prompts":{"en-US":"Preserved legacy/manual compatibility package.",'
    '"zh-TW":"保留既有手動部署的相容套件。"},"requested_capabilities":["manage_work",'
    '"read_work"],"workflow":{"entrypoint":"complete","steps":[{"id":"complete",'
    '"type":"complete"}]}},"content_digest":"sha256:ab12b78f9e0d5d800498453e53a6781642975'
    '00b6db8134a7f3eed6eb75ad6cb","metadata":{"display":{"en-US":{"name":"Legacy Manual",'
    '"summary":"Preserved pre-P11 colleague deployment."},"zh-TW":{"name":"既有手動部署",'
    '"summary":"保留 P11 之前的同事部署。"}},"package_id":"legacy-manual","runtime_api":"1",'
    '"version":"1.0.0"},"schema":"dc-agent/v1","schema_version":1}'
)


class _P11MigrationRunner(MigrationRunner):
    """Preserve complete SQLite statements so migration-owned triggers stay atomic."""

    @staticmethod
    def _statements(content: str) -> tuple[str, ...]:
        statements: list[str] = []
        buffer: list[str] = []
        for character in content:
            buffer.append(character)
            if character == ";" and sqlite3.complete_statement("".join(buffer)):
                statements.append("".join(buffer).strip())
                buffer.clear()
        if "".join(buffer).strip() or not statements:
            raise MigrationError("a migration contains incomplete SQL")
        return tuple(statements)


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_json(value).encode()).hexdigest()


class SQLiteP11Store(SQLiteP6Store):
    """Single-host reference store with serialized activation and exact namespaces."""

    def __init__(
        self,
        database_path: Path,
        *,
        migrations_path: Path,
        clock: ClockPort,
        busy_timeout_ms: int = 5_000,
    ) -> None:
        if type(busy_timeout_ms) is not int or busy_timeout_ms < 1:
            raise ValueError("busy timeout must be a positive integer")
        self._database_path = database_path
        self._clock = clock
        self._closed = False
        self._lock = threading.RLock()
        connection: sqlite3.Connection | None = None
        try:
            database_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(
                database_path,
                timeout=busy_timeout_ms / 1_000,
                isolation_level=None,
                check_same_thread=False,
            )
            self._connection = connection
            self._connection.row_factory = sqlite3.Row
            self._connection.execute(f"PRAGMA busy_timeout = {busy_timeout_ms}")
            mode = self._connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
            self._connection.execute("PRAGMA foreign_keys = ON")
            foreign_keys = self._connection.execute("PRAGMA foreign_keys").fetchone()[0]
            if str(mode).lower() != "wal" or foreign_keys != 1:
                raise PersistenceError("required SQLite safety pragmas were not enabled")
            self._migrations = _P11MigrationRunner(migrations_path).apply(
                self._connection,
                applied_at=clock.now(),
            )
        except (OSError, sqlite3.Error) as exc:
            if connection is not None:
                connection.close()
            self._closed = True
            raise PersistenceError("SQLite reference store initialization failed") from exc
        except Exception:
            if connection is not None:
                connection.close()
            self._closed = True
            raise

    def create_initial_colleague(
        self,
        *,
        namespace: Namespace,
        profile: Profile,
        mandate: Mandate,
        runtime_principals: tuple[Principal, ...],
        actor: Principal,
        correlation_id: str,
        occurred_at: datetime,
        idempotency_key: str,
    ) -> bool:
        """Retain P4 creation and atomically add its legacy/manual binding."""

        namespace.require_exact(profile.namespace)
        namespace.require_exact(mandate.namespace)
        if actor.kind is not PrincipalKind.HUMAN or HumanRole.TENANT_ADMIN not in actor.roles:
            raise PermissionDeniedError("initial colleague requires a durable tenant Admin")
        with self._transaction() as connection:
            replay = connection.execute(
                """
                SELECT record_id FROM replay_ledger
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND ledger_kind = 'p4_initial_colleague' AND idempotency_key = ?
                """,
                (*_ns(namespace), idempotency_key),
            ).fetchone()
            if replay is not None:
                existing_profile = self._get_record(
                    connection, namespace, "profile", replay["record_id"], Profile
                )
                existing_mandate = self._get_record(
                    connection, namespace, "mandate", mandate.mandate_id, Mandate
                )
                normalized_profile = replace(profile, updated_at=existing_profile.updated_at)
                normalized_mandate = replace(mandate, effective_at=existing_mandate.effective_at)
                if normalized_profile != existing_profile or normalized_mandate != existing_mandate:
                    raise ConflictError("initial colleague idempotency replay drifted")
                legacy = connection.execute(
                    "SELECT 1 FROM p11_colleague_deployments "
                    "WHERE tenant_id = ? AND deployment_id = ? AND legacy_manual = 1",
                    (namespace.tenant_id, namespace.scope_id),
                ).fetchone()
                if legacy is None:
                    raise ConflictError("initial colleague legacy binding is incomplete")
                return False
            existing = connection.execute(
                "SELECT COUNT(*) AS count FROM domain_records "
                "WHERE tenant_id = ? AND record_type = 'profile'",
                (namespace.tenant_id,),
            ).fetchone()["count"]
            if existing:
                raise ConflictError("P4 supports exactly one initial colleague")
            durable_actor = self._get_record(
                connection,
                actor.namespace,
                "principal",
                actor.principal_id,
                Principal,
            )
            if durable_actor != actor:
                raise PermissionDeniedError("initial colleague actor binding drifted")
            for principal in runtime_principals:
                if principal.kind not in {PrincipalKind.MODEL, PrincipalKind.SERVICE}:
                    raise PermissionDeniedError("runtime principals cannot be human")
                self._insert_record(
                    connection,
                    principal,
                    actor=actor,
                    correlation_id=correlation_id,
                    causation_id=profile.profile_id,
                    occurred_at=occurred_at,
                )
            self._insert_record(connection, profile, correlation_id=correlation_id)
            self._insert_record(connection, mandate, correlation_id=correlation_id)
            connection.execute(
                """
                INSERT INTO replay_ledger(
                  schema_version, tenant_id, namespace_scope, namespace_scope_id,
                  ledger_kind, idempotency_key, record_type, record_id, created_at
                ) VALUES (?, ?, ?, ?, 'p4_initial_colleague', ?, 'profile', ?, ?)
                """,
                (
                    SCHEMA_VERSION,
                    *_ns(namespace),
                    idempotency_key,
                    profile.profile_id,
                    datetime_to_z(occurred_at),
                ),
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO p11_package_versions(
                  schema_version, tenant_id, namespace_scope, namespace_scope_id,
                  package_id, package_version, package_digest, archive_digest, package_json,
                  source, trust_state, install_state, attestation_json,
                  created_by_principal_id, created_by_kind, created_at, updated_at,
                  correlation_id, causation_id, revision
                ) VALUES (?, ?, 'tenant', '', 'legacy-manual', '1.0.0', ?, ?, ?,
                          'official_builtin', 'legacy_preserved', 'installed', NULL,
                          'p11-compatibility', 'service', ?, ?, ?, ?, 1)
                """,
                (
                    SCHEMA_VERSION,
                    namespace.tenant_id,
                    _LEGACY_PACKAGE_DIGEST,
                    _LEGACY_PACKAGE_DIGEST,
                    _LEGACY_PACKAGE_JSON,
                    datetime_to_z(occurred_at),
                    datetime_to_z(occurred_at),
                    correlation_id,
                    profile.profile_id,
                ),
            )
            occupied = {
                row[0]
                for row in connection.execute(
                    "SELECT active_slot FROM p11_colleague_deployments "
                    "WHERE execution_host_id = 'local' AND lifecycle = 'active'"
                )
            }
            slot = next(
                (candidate for candidate in range(1, 11) if candidate not in occupied), None
            )
            if slot is None:
                raise ConflictError("active_deployment_limit_reached")
            connection.execute(
                """
                INSERT INTO p11_colleague_deployments(
                  schema_version, tenant_id, namespace_scope, namespace_scope_id, deployment_id,
                  package_id, package_version, package_digest,
                  profile_id, profile_revision, mandate_id, mandate_revision,
                  policy_id, policy_revision, lifecycle, execution_host_id, active_slot,
                  legacy_manual, legacy_policy_unconfirmed, future_connection_slot,
                  updated_by_principal_id, updated_by_kind, created_at, updated_at,
                  correlation_id, causation_id, revision
                ) VALUES (?, ?, ?, ?, ?, 'legacy-manual', '1.0.0', ?, ?, ?, ?, ?,
                          NULL, NULL, 'active', 'local', ?, 1, 1, NULL,
                          'p11-compatibility', 'service', ?, ?, ?, ?, 1)
                """,
                (
                    SCHEMA_VERSION,
                    *_ns(namespace),
                    namespace.scope_id,
                    _LEGACY_PACKAGE_DIGEST,
                    profile.profile_id,
                    profile.revision,
                    mandate.mandate_id,
                    mandate.revision,
                    slot,
                    datetime_to_z(occurred_at),
                    datetime_to_z(occurred_at),
                    correlation_id,
                    profile.profile_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO p11_deployment_package_history(
                  schema_version, tenant_id, deployment_id, sequence,
                  package_id, package_version, package_digest, accepted_at,
                  actor_principal_id, correlation_id, causation_id
                ) VALUES (?, ?, ?, 1, 'legacy-manual', '1.0.0', ?, ?,
                          'p11-compatibility', ?, ?)
                """,
                (
                    SCHEMA_VERSION,
                    namespace.tenant_id,
                    namespace.scope_id,
                    _LEGACY_PACKAGE_DIGEST,
                    datetime_to_z(occurred_at),
                    correlation_id,
                    profile.profile_id,
                ),
            )
        return True

    def _actor(self, tenant_id: str, principal_id: str, kind: str) -> Principal:
        if kind == PrincipalKind.SERVICE.value:
            return Principal.service(tenant_id=tenant_id, principal_id=principal_id)
        return self.get_principal(tenant_id, principal_id)

    @staticmethod
    def _attestation(value: str | None) -> GitHubAttestation | None:
        if value is None:
            return None
        raw = json.loads(value)
        if not isinstance(raw, dict):
            raise ConflictError("durable attestation shape is invalid")
        return GitHubAttestation(
            verification=AttestationVerification(raw["verification"]),
            artifact_digest=raw["artifact_digest"],
            signer=raw["signer"],
            repository=raw["repository"],
            workflow=raw["workflow"],
            build_identity=raw["build_identity"],
            source_ref=raw["source_ref"],
            source_digest=raw["source_digest"],
            predicate_type=raw["predicate_type"],
            verified_at=datetime_from_z(raw["verified_at"]),
        )

    @staticmethod
    def _attestation_json(value: GitHubAttestation | None) -> str | None:
        if value is None:
            return None
        return _json(
            {
                "verification": value.verification.value,
                "artifact_digest": value.artifact_digest,
                "signer": value.signer,
                "repository": value.repository,
                "workflow": value.workflow,
                "build_identity": value.build_identity,
                "source_ref": value.source_ref,
                "source_digest": value.source_digest,
                "predicate_type": value.predicate_type,
                "verified_at": datetime_to_z(value.verified_at),
            }
        )

    def _package_from_row(self, row: sqlite3.Row) -> PackageRecord:
        raw = json.loads(row["package_json"])
        package = agent_package_from_mapping(raw)
        return PackageRecord(
            namespace=Namespace.tenant(row["tenant_id"]),
            package=package,
            package_digest=row["package_digest"],
            archive_digest=row["archive_digest"],
            source=PackageSource(row["source"]),
            trust_state=PackageTrustState(row["trust_state"]),
            install_state=PackageInstallState(row["install_state"]),
            attestation=self._attestation(row["attestation_json"]),
            created_by=self._actor(
                row["tenant_id"], row["created_by_principal_id"], row["created_by_kind"]
            ),
            created_at=datetime_from_z(row["created_at"]),
            updated_at=datetime_from_z(row["updated_at"]),
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            revision=row["revision"],
            schema_version=row["schema_version"],
        )

    def _deployment_draft_from_row(self, row: sqlite3.Row) -> DeploymentDraft:
        diff = freeze_json(json.loads(row["permission_diff_json"]))
        if not isinstance(diff, FrozenJsonObject):
            raise ConflictError("durable permission diff shape is invalid")
        return DeploymentDraft(
            namespace=Namespace.colleague(row["tenant_id"], row["namespace_scope_id"]),
            draft_id=row["draft_id"],
            kind=DeploymentDraftKind(row["kind"]),
            package_id=row["package_id"],
            package_version=row["package_version"],
            package_digest=row["package_digest"],
            profile=from_storage_json(row["profile_json"], Profile),
            mandate=from_storage_json(row["mandate_json"], Mandate),
            policy=from_storage_json(row["policy_json"], ColleaguePolicy),
            base_deployment_revision=row["base_deployment_revision"],
            permission_diff=diff,
            canonical_digest=row["canonical_digest"],
            state=DeploymentDraftState(row["state"]),
            author=self.get_principal(row["tenant_id"], row["author_principal_id"]),
            created_at=datetime_from_z(row["created_at"]),
            updated_at=datetime_from_z(row["updated_at"]),
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            revision=row["revision"],
            schema_version=row["schema_version"],
        )

    def _deployment_from_row(self, row: sqlite3.Row) -> ColleagueDeployment:
        return ColleagueDeployment(
            namespace=Namespace.colleague(row["tenant_id"], row["deployment_id"]),
            deployment_id=row["deployment_id"],
            package_id=row["package_id"],
            package_version=row["package_version"],
            package_digest=row["package_digest"],
            profile_id=row["profile_id"],
            profile_revision=row["profile_revision"],
            mandate_id=row["mandate_id"],
            mandate_revision=row["mandate_revision"],
            policy_id=row["policy_id"],
            policy_revision=row["policy_revision"],
            lifecycle=DeploymentLifecycle(row["lifecycle"]),
            execution_host_id=row["execution_host_id"],
            legacy_manual=bool(row["legacy_manual"]),
            legacy_policy_unconfirmed=bool(row["legacy_policy_unconfirmed"]),
            future_connection_slot=None,
            updated_by=self._actor(
                row["tenant_id"], row["updated_by_principal_id"], row["updated_by_kind"]
            ),
            created_at=datetime_from_z(row["created_at"]),
            updated_at=datetime_from_z(row["updated_at"]),
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            revision=row["revision"],
            schema_version=row["schema_version"],
        )

    @staticmethod
    def _replay_result(
        connection: sqlite3.Connection,
        *,
        namespace: Namespace,
        operation: str,
        actor_id: str,
        idempotency_key: str,
        request_digest: str,
    ) -> dict[str, object] | None:
        row = connection.execute(
            """
            SELECT request_digest, result_json FROM p11_operation_replay
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND operation = ? AND actor_principal_id = ? AND idempotency_key = ?
            """,
            (*_ns(namespace), operation, actor_id, idempotency_key),
        ).fetchone()
        if row is None:
            return None
        if row["request_digest"] != request_digest:
            raise ReplayConflictError("P11 idempotency key was rebound")
        try:
            result = json.loads(row["result_json"])
        except json.JSONDecodeError as exc:
            raise ConflictError("durable P11 replay result is invalid") from exc
        if not isinstance(result, dict):
            raise ConflictError("durable P11 replay result is invalid")
        return result

    @classmethod
    def _replay(
        cls,
        connection: sqlite3.Connection,
        *,
        namespace: Namespace,
        operation: str,
        actor_id: str,
        idempotency_key: str,
        request_digest: str,
    ) -> bool:
        return (
            cls._replay_result(
                connection,
                namespace=namespace,
                operation=operation,
                actor_id=actor_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
            )
            is not None
        )

    @staticmethod
    def _record_replay(
        connection: sqlite3.Connection,
        *,
        namespace: Namespace,
        operation: str,
        actor_id: str,
        idempotency_key: str,
        request_digest: str,
        result: object,
        occurred_at: datetime,
    ) -> None:
        connection.execute(
            """
            INSERT INTO p11_operation_replay(
              schema_version, tenant_id, namespace_scope, namespace_scope_id,
              operation, actor_principal_id, idempotency_key, request_digest,
              result_json, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SCHEMA_VERSION,
                *_ns(namespace),
                operation,
                actor_id,
                idempotency_key,
                request_digest,
                _json(result),
                datetime_to_z(occurred_at),
            ),
        )

    @staticmethod
    def _audit(
        connection: sqlite3.Connection,
        *,
        namespace: Namespace,
        action: str,
        result: str,
        record_type: str,
        record_id: str,
        record_revision: int,
        actor: Principal,
        correlation_id: str,
        causation_id: str,
        occurred_at: datetime,
        projection: dict[str, object],
    ) -> None:
        audit_seed = (
            f"{record_type}\0{record_id}\0{record_revision}\0{action}\0{result}\0"
            f"{actor.principal_id}\0{causation_id}"
        )
        audit_id = "p11:" + hashlib.sha256(audit_seed.encode()).hexdigest()[:32]
        serialized = _json(projection)
        connection.execute(
            """
            INSERT INTO p11_causal_audit(
              schema_version, tenant_id, namespace_scope, namespace_scope_id,
              audit_id, action, result, record_type, record_id, record_revision,
              actor_principal_id, actor_kind, correlation_id, causation_id, occurred_at,
              safe_projection_json, payload_digest
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SCHEMA_VERSION,
                *_ns(namespace),
                audit_id,
                action,
                result,
                record_type,
                record_id,
                record_revision,
                actor.principal_id,
                actor.kind.value,
                correlation_id,
                causation_id,
                datetime_to_z(occurred_at),
                serialized,
                "sha256:" + hashlib.sha256(serialized.encode()).hexdigest(),
            ),
        )

    def register_package(self, record: PackageRecord, *, idempotency_key: str) -> PackageRecord:
        namespace = record.namespace
        with self._transaction() as connection:
            self._require_current_membership(
                connection,
                actor=record.created_by,
                action=AuthorizationAction.MANAGE_AGENT_PACKAGES,
                namespace=namespace,
            )
            request_digest = _digest(
                {
                    "archive_digest": record.archive_digest,
                    "package_digest": record.package_digest,
                    "source": record.source.value,
                }
            )
            if self._replay(
                connection,
                namespace=namespace,
                operation="register_package",
                actor_id=record.created_by.principal_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
            ):
                return self.get_package(
                    namespace.tenant_id,
                    record.package.package_id,
                    record.package.version,
                    record.package_digest,
                )
            try:
                connection.execute(
                    """
                    INSERT INTO p11_package_versions(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      package_id, package_version, package_digest, archive_digest,
                      package_json, source, trust_state, install_state, attestation_json,
                      created_by_principal_id, created_by_kind, created_at, updated_at,
                      correlation_id, causation_id, revision
                    ) VALUES (?, ?, 'tenant', '', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.schema_version,
                        namespace.tenant_id,
                        record.package.package_id,
                        record.package.version,
                        record.package_digest,
                        record.archive_digest,
                        _json(record.package.to_data()),
                        record.source.value,
                        record.trust_state.value,
                        record.install_state.value,
                        self._attestation_json(record.attestation),
                        record.created_by.principal_id,
                        record.created_by.kind.value,
                        datetime_to_z(record.created_at),
                        datetime_to_z(record.updated_at),
                        record.correlation_id,
                        record.causation_id,
                        record.revision,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ConflictError("package version identity already exists") from exc
            self._audit(
                connection,
                namespace=namespace,
                action="registered",
                result="untrusted",
                record_type="agent_package",
                record_id=f"{record.package.package_id}:{record.package.version}",
                record_revision=record.revision,
                actor=record.created_by,
                correlation_id=record.correlation_id,
                causation_id=record.causation_id,
                occurred_at=record.created_at,
                projection={"package_digest": record.package_digest, "source": record.source.value},
            )
            self._record_replay(
                connection,
                namespace=namespace,
                operation="register_package",
                actor_id=record.created_by.principal_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
                result={"package_digest": record.package_digest},
                occurred_at=record.created_at,
            )
        return record

    def registration_replay(
        self,
        *,
        namespace: Namespace,
        actor: Principal,
        package_id: str,
        version: str,
        digest: str,
        idempotency_key: str,
        request_digest: str,
    ) -> PackageRecord | None:
        """Return an exact durable registration replay before external verification."""

        with self._transaction() as connection:
            self._require_current_membership(
                connection,
                actor=actor,
                action=AuthorizationAction.MANAGE_AGENT_PACKAGES,
                namespace=namespace,
            )
            replay = self._replay_result(
                connection,
                namespace=namespace,
                operation="register_package",
                actor_id=actor.principal_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
            )
            if replay is None:
                return None
            if replay.get("package_digest") != digest:
                raise ConflictError("durable package registration replay is invalid")
            return self.get_package(namespace.tenant_id, package_id, version, digest)

    def get_package(
        self, tenant_id: str, package_id: str, version: str, digest: str
    ) -> PackageRecord:
        row = self._connection.execute(
            """
            SELECT * FROM p11_package_versions
            WHERE tenant_id = ? AND package_id = ? AND package_version = ?
              AND package_digest = ?
            """,
            (tenant_id, package_id, version, digest),
        ).fetchone()
        if row is None:
            raise NotFoundError("exact package version was not found")
        return self._package_from_row(row)

    def list_packages(self, tenant_id: str) -> tuple[PackageRecord, ...]:
        rows = self._connection.execute(
            "SELECT * FROM p11_package_versions WHERE tenant_id = ? "
            "ORDER BY package_id, package_version, package_digest",
            (tenant_id,),
        ).fetchall()
        return tuple(self._package_from_row(row) for row in rows)

    def change_package_state(
        self,
        *,
        record: PackageRecord,
        actor: Principal,
        action: str,
        expected_revision: int,
        idempotency_key: str,
        request_digest: str,
    ) -> PackageRecord:
        namespace = record.namespace
        with self._transaction() as connection:
            self._require_current_membership(
                connection,
                actor=actor,
                action=AuthorizationAction.MANAGE_AGENT_PACKAGES,
                namespace=namespace,
            )
            if self._replay(
                connection,
                namespace=namespace,
                operation=action,
                actor_id=actor.principal_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
            ):
                return self.get_package(
                    namespace.tenant_id,
                    record.package.package_id,
                    record.package.version,
                    record.package_digest,
                )
            current_row = connection.execute(
                """
                SELECT * FROM p11_package_versions
                WHERE tenant_id = ? AND package_id = ? AND package_version = ?
                  AND package_digest = ?
                """,
                (
                    namespace.tenant_id,
                    record.package.package_id,
                    record.package.version,
                    record.package_digest,
                ),
            ).fetchone()
            if current_row is None:
                raise NotFoundError("exact package version was not found")
            current = self._package_from_row(current_row)
            if current.revision != expected_revision:
                raise StaleConflictError("package revision is stale")
            allowed = {
                "trust": current.trust_state is PackageTrustState.UNTRUSTED
                and record.trust_state is PackageTrustState.TRUSTED
                and record.install_state is current.install_state,
                "revoke": current.trust_state
                in {
                    PackageTrustState.UNTRUSTED,
                    PackageTrustState.TRUSTED,
                    PackageTrustState.LEGACY_PRESERVED,
                }
                and record.trust_state is PackageTrustState.REVOKED
                and record.install_state is current.install_state,
                "install": current.trust_state is PackageTrustState.TRUSTED
                and current.install_state is PackageInstallState.NOT_INSTALLED
                and record.trust_state is PackageTrustState.TRUSTED
                and record.install_state is PackageInstallState.INSTALLED,
            }
            if action not in allowed or not allowed[action]:
                raise PermissionDeniedError("package lifecycle transition is forbidden")
            cursor = connection.execute(
                """
                UPDATE p11_package_versions
                SET trust_state = ?, install_state = ?, updated_at = ?,
                    correlation_id = ?, causation_id = ?, revision = ?
                WHERE tenant_id = ? AND package_id = ? AND package_version = ?
                  AND package_digest = ? AND revision = ?
                """,
                (
                    record.trust_state.value,
                    record.install_state.value,
                    datetime_to_z(record.updated_at),
                    record.correlation_id,
                    record.causation_id,
                    record.revision,
                    namespace.tenant_id,
                    record.package.package_id,
                    record.package.version,
                    record.package_digest,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1 or record.revision != expected_revision + 1:
                raise StaleConflictError("package revision is stale")
            if action in {"trust", "revoke"}:
                connection.execute(
                    """
                    INSERT INTO p11_package_trust_decisions(
                      schema_version, tenant_id, decision_id, package_id,
                      package_version, package_digest, decision, actor_principal_id,
                      occurred_at, correlation_id, causation_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        SCHEMA_VERSION,
                        namespace.tenant_id,
                        f"{action}:{record.package_digest[7:31]}:{record.revision}",
                        record.package.package_id,
                        record.package.version,
                        record.package_digest,
                        record.trust_state.value,
                        actor.principal_id,
                        datetime_to_z(record.updated_at),
                        record.correlation_id,
                        record.causation_id,
                    ),
                )
            if action == "revoke":
                blocked = connection.execute(
                    """
                    SELECT * FROM p11_colleague_deployments
                    WHERE tenant_id = ? AND package_id = ? AND package_version = ?
                      AND package_digest = ? AND lifecycle = 'active'
                    """,
                    (
                        namespace.tenant_id,
                        record.package.package_id,
                        record.package.version,
                        record.package_digest,
                    ),
                ).fetchall()
                for row in blocked:
                    next_revision = row["revision"] + 1
                    connection.execute(
                        """
                        UPDATE p11_colleague_deployments
                        SET lifecycle = 'blocked', active_slot = NULL,
                            updated_by_principal_id = ?, updated_by_kind = 'human',
                            updated_at = ?, correlation_id = ?, causation_id = ?, revision = ?
                        WHERE tenant_id = ? AND deployment_id = ? AND revision = ?
                        """,
                        (
                            actor.principal_id,
                            datetime_to_z(record.updated_at),
                            record.correlation_id,
                            record.causation_id,
                            next_revision,
                            namespace.tenant_id,
                            row["deployment_id"],
                            row["revision"],
                        ),
                    )
                    self._audit(
                        connection,
                        namespace=Namespace.colleague(namespace.tenant_id, row["deployment_id"]),
                        action="package_revocation_blocked",
                        result="blocked",
                        record_type="colleague_deployment",
                        record_id=row["deployment_id"],
                        record_revision=next_revision,
                        actor=actor,
                        correlation_id=record.correlation_id,
                        causation_id=record.causation_id,
                        occurred_at=record.updated_at,
                        projection={"package_digest": record.package_digest},
                    )
            self._audit(
                connection,
                namespace=namespace,
                action=action,
                result=(record.trust_state.value if action != "install" else "installed"),
                record_type="agent_package",
                record_id=f"{record.package.package_id}:{record.package.version}",
                record_revision=record.revision,
                actor=actor,
                correlation_id=record.correlation_id,
                causation_id=record.causation_id,
                occurred_at=record.updated_at,
                projection={"package_digest": record.package_digest},
            )
            self._record_replay(
                connection,
                namespace=namespace,
                operation=action,
                actor_id=actor.principal_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
                result={"revision": record.revision},
                occurred_at=record.updated_at,
            )
        return record

    def create_deployment_draft(
        self, draft: DeploymentDraft, *, idempotency_key: str, request_digest: str
    ) -> DeploymentDraft:
        with self._transaction() as connection:
            self._require_current_membership(
                connection,
                actor=draft.author,
                action=AuthorizationAction.MANAGE_DEPLOYMENTS,
                namespace=draft.namespace,
            )
            if self._replay(
                connection,
                namespace=draft.namespace,
                operation=f"{draft.kind.value}_draft",
                actor_id=draft.author.principal_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
            ):
                return self.get_deployment_draft(draft.namespace, draft.draft_id)
            connection.execute(
                """
                INSERT INTO p11_deployment_drafts(
                  schema_version, tenant_id, namespace_scope, namespace_scope_id,
                  draft_id, kind, package_id, package_version, package_digest,
                  profile_json, mandate_json, policy_json, base_deployment_revision,
                  permission_diff_json, canonical_digest, state, author_principal_id,
                  created_at, updated_at, correlation_id, causation_id, revision
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    draft.schema_version,
                    *_ns(draft.namespace),
                    draft.draft_id,
                    draft.kind.value,
                    draft.package_id,
                    draft.package_version,
                    draft.package_digest,
                    to_storage_json(draft.profile),
                    to_storage_json(draft.mandate),
                    to_storage_json(draft.policy),
                    draft.base_deployment_revision,
                    _json(contract_to_public_data(draft.permission_diff)),
                    draft.canonical_digest,
                    draft.state.value,
                    draft.author.principal_id,
                    datetime_to_z(draft.created_at),
                    datetime_to_z(draft.updated_at),
                    draft.correlation_id,
                    draft.causation_id,
                    draft.revision,
                ),
            )
            self._audit(
                connection,
                namespace=draft.namespace,
                action=f"{draft.kind.value}_draft_created",
                result="draft",
                record_type="deployment_draft",
                record_id=draft.draft_id,
                record_revision=draft.revision,
                actor=draft.author,
                correlation_id=draft.correlation_id,
                causation_id=draft.causation_id,
                occurred_at=draft.created_at,
                projection={"canonical_digest": draft.canonical_digest},
            )
            self._record_replay(
                connection,
                namespace=draft.namespace,
                operation=f"{draft.kind.value}_draft",
                actor_id=draft.author.principal_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
                result={"draft_id": draft.draft_id},
                occurred_at=draft.created_at,
            )
        return draft

    def deployment_draft_replay(
        self,
        *,
        namespace: Namespace,
        actor: Principal,
        kind: str,
        draft_id: str,
        idempotency_key: str,
        request_digest: str,
    ) -> DeploymentDraft | None:
        """Resolve a draft replay before evaluating time-varying deployment state."""

        with self._transaction() as connection:
            self._require_current_membership(
                connection,
                actor=actor,
                action=AuthorizationAction.MANAGE_DEPLOYMENTS,
                namespace=namespace,
            )
            replay = self._replay_result(
                connection,
                namespace=namespace,
                operation=f"{kind}_draft",
                actor_id=actor.principal_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
            )
            if replay is None:
                return None
            if replay.get("draft_id") != draft_id:
                raise ConflictError("durable deployment draft replay is invalid")
            return self.get_deployment_draft(namespace, draft_id)

    def get_deployment_draft(self, namespace: Namespace, draft_id: str) -> DeploymentDraft:
        row = self._connection.execute(
            "SELECT * FROM p11_deployment_drafts WHERE tenant_id = ? "
            "AND namespace_scope = ? AND namespace_scope_id = ? AND draft_id = ?",
            (*_ns(namespace), draft_id),
        ).fetchone()
        if row is None:
            raise NotFoundError("deployment draft was not found")
        return self._deployment_draft_from_row(row)

    def list_deployment_drafts(self, tenant_id: str) -> tuple[DeploymentDraft, ...]:
        rows = self._connection.execute(
            "SELECT * FROM p11_deployment_drafts WHERE tenant_id = ? ORDER BY updated_at, draft_id",
            (tenant_id,),
        ).fetchall()
        return tuple(self._deployment_draft_from_row(row) for row in rows)

    def review_deployment_draft(
        self,
        *,
        draft: DeploymentDraft,
        expected_revision: int,
        idempotency_key: str,
        request_digest: str,
    ) -> DeploymentDraft:
        updated = replace(
            draft,
            state=DeploymentDraftState.REVIEWED,
            revision=expected_revision + 1,
        )
        with self._transaction() as connection:
            self._require_current_membership(
                connection,
                actor=draft.author,
                action=AuthorizationAction.MANAGE_DEPLOYMENTS,
                namespace=draft.namespace,
            )
            if self._replay(
                connection,
                namespace=draft.namespace,
                operation="review_draft",
                actor_id=draft.author.principal_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
            ):
                return self.get_deployment_draft(draft.namespace, draft.draft_id)
            if draft.state is not DeploymentDraftState.DRAFT:
                raise StaleConflictError("only a draft can be reviewed")
            cursor = connection.execute(
                """
                UPDATE p11_deployment_drafts
                SET state = 'reviewed', revision = ?, updated_at = ?
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND draft_id = ? AND revision = ? AND state = 'draft'
                """,
                (
                    updated.revision,
                    datetime_to_z(updated.updated_at),
                    *_ns(updated.namespace),
                    updated.draft_id,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise StaleConflictError("deployment draft revision is stale")
            self._audit(
                connection,
                namespace=updated.namespace,
                action="draft_reviewed",
                result="reviewed",
                record_type="deployment_draft",
                record_id=updated.draft_id,
                record_revision=updated.revision,
                actor=updated.author,
                correlation_id=updated.correlation_id,
                causation_id=updated.causation_id,
                occurred_at=updated.updated_at,
                projection={"canonical_digest": updated.canonical_digest},
            )
            self._record_replay(
                connection,
                namespace=updated.namespace,
                operation="review_draft",
                actor_id=updated.author.principal_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
                result={"revision": updated.revision},
                occurred_at=updated.updated_at,
            )
        return updated

    def confirm_deployment_draft(
        self,
        *,
        draft: DeploymentDraft,
        expected_revision: int,
        idempotency_key: str,
        request_digest: str,
        model_principal: Principal,
        service_principal: Principal,
    ) -> ColleagueDeployment:
        with self._transaction() as connection:
            self._require_current_membership(
                connection,
                actor=draft.author,
                action=AuthorizationAction.MANAGE_DEPLOYMENTS,
                namespace=draft.namespace,
            )
            if self._replay(
                connection,
                namespace=draft.namespace,
                operation="confirm_draft",
                actor_id=draft.author.principal_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
            ):
                return self.get_deployment(draft.namespace)
            if draft.state is not DeploymentDraftState.REVIEWED:
                raise StaleConflictError("only a reviewed draft can be confirmed")
            package = self.get_package(
                draft.namespace.tenant_id,
                draft.package_id,
                draft.package_version,
                draft.package_digest,
            )
            if (
                package.trust_state is not PackageTrustState.TRUSTED
                or package.install_state is not PackageInstallState.INSTALLED
            ):
                raise PermissionDeniedError("deployment requires a trusted installed exact package")
            existing_row = connection.execute(
                "SELECT * FROM p11_colleague_deployments WHERE tenant_id = ? AND deployment_id = ?",
                (draft.namespace.tenant_id, draft.namespace.scope_id),
            ).fetchone()
            if draft.kind is DeploymentDraftKind.CREATE:
                if existing_row is not None or draft.base_deployment_revision != 0:
                    raise StaleConflictError("deployment creation base is stale")
                for principal in (model_principal, service_principal):
                    self._insert_record(
                        connection,
                        principal,
                        actor=draft.author,
                        correlation_id=draft.correlation_id,
                        causation_id=draft.draft_id,
                        occurred_at=draft.updated_at,
                    )
                self._insert_record(connection, draft.profile, correlation_id=draft.correlation_id)
                self._insert_record(connection, draft.mandate, correlation_id=draft.correlation_id)
                self._insert_record(connection, draft.policy, correlation_id=draft.correlation_id)
                self._upsert_run_state(
                    connection,
                    policy=draft.policy,
                    actor=draft.author,
                    correlation_id=draft.correlation_id,
                    causation_id=draft.draft_id,
                    occurred_at=draft.updated_at,
                    reason="p11_deployment_confirmed",
                )
                deployment = ColleagueDeployment(
                    namespace=draft.namespace,
                    deployment_id=cast(str, draft.namespace.scope_id),
                    package_id=draft.package_id,
                    package_version=draft.package_version,
                    package_digest=draft.package_digest,
                    profile_id=draft.profile.profile_id,
                    profile_revision=draft.profile.revision,
                    mandate_id=draft.mandate.mandate_id,
                    mandate_revision=draft.mandate.revision,
                    policy_id=draft.policy.policy_id,
                    policy_revision=draft.policy.revision,
                    lifecycle=DeploymentLifecycle.DRAFT,
                    execution_host_id="local",
                    legacy_manual=False,
                    legacy_policy_unconfirmed=False,
                    future_connection_slot=None,
                    updated_by=draft.author,
                    created_at=draft.updated_at,
                    updated_at=draft.updated_at,
                    correlation_id=draft.correlation_id,
                    causation_id=draft.draft_id,
                )
                connection.execute(
                    """
                    INSERT INTO p11_colleague_deployments(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      deployment_id, package_id, package_version, package_digest,
                      profile_id, profile_revision, mandate_id, mandate_revision,
                      policy_id, policy_revision, lifecycle, execution_host_id, active_slot,
                      legacy_manual, legacy_policy_unconfirmed, future_connection_slot,
                      updated_by_principal_id, updated_by_kind, created_at, updated_at,
                      correlation_id, causation_id, revision
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, NULL,
                              ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        deployment.schema_version,
                        *_ns(deployment.namespace),
                        deployment.deployment_id,
                        deployment.package_id,
                        deployment.package_version,
                        deployment.package_digest,
                        deployment.profile_id,
                        deployment.profile_revision,
                        deployment.mandate_id,
                        deployment.mandate_revision,
                        deployment.policy_id,
                        deployment.policy_revision,
                        deployment.lifecycle.value,
                        deployment.execution_host_id,
                        int(deployment.legacy_manual),
                        int(deployment.legacy_policy_unconfirmed),
                        deployment.updated_by.principal_id,
                        deployment.updated_by.kind.value,
                        datetime_to_z(deployment.created_at),
                        datetime_to_z(deployment.updated_at),
                        deployment.correlation_id,
                        deployment.causation_id,
                        deployment.revision,
                    ),
                )
            else:
                if existing_row is None:
                    raise StaleConflictError("deployment rebinding base is missing")
                existing = self._deployment_from_row(existing_row)
                if existing.revision != draft.base_deployment_revision:
                    raise StaleConflictError("deployment rebinding base is stale")
                deployment = replace(
                    existing,
                    package_id=draft.package_id,
                    package_version=draft.package_version,
                    package_digest=draft.package_digest,
                    lifecycle=DeploymentLifecycle.DRAFT,
                    updated_by=draft.author,
                    updated_at=draft.updated_at,
                    correlation_id=draft.correlation_id,
                    causation_id=draft.draft_id,
                    revision=existing.revision + 1,
                )
                connection.execute(
                    """
                    UPDATE p11_colleague_deployments
                    SET package_id = ?, package_version = ?, package_digest = ?,
                        lifecycle = 'draft', active_slot = NULL,
                        updated_by_principal_id = ?, updated_by_kind = 'human',
                        updated_at = ?, correlation_id = ?, causation_id = ?, revision = ?
                    WHERE tenant_id = ? AND deployment_id = ? AND revision = ?
                    """,
                    (
                        deployment.package_id,
                        deployment.package_version,
                        deployment.package_digest,
                        deployment.updated_by.principal_id,
                        datetime_to_z(deployment.updated_at),
                        deployment.correlation_id,
                        deployment.causation_id,
                        deployment.revision,
                        deployment.namespace.tenant_id,
                        deployment.deployment_id,
                        existing.revision,
                    ),
                )
            sequence = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 AS value "
                "FROM p11_deployment_package_history WHERE tenant_id = ? AND deployment_id = ?",
                (deployment.namespace.tenant_id, deployment.deployment_id),
            ).fetchone()["value"]
            connection.execute(
                """
                INSERT OR IGNORE INTO p11_deployment_package_history(
                  schema_version, tenant_id, deployment_id, sequence,
                  package_id, package_version, package_digest, accepted_at,
                  actor_principal_id, correlation_id, causation_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    SCHEMA_VERSION,
                    deployment.namespace.tenant_id,
                    deployment.deployment_id,
                    sequence,
                    deployment.package_id,
                    deployment.package_version,
                    deployment.package_digest,
                    datetime_to_z(deployment.updated_at),
                    deployment.updated_by.principal_id,
                    deployment.correlation_id,
                    deployment.causation_id,
                ),
            )
            confirmed_revision = expected_revision + 1
            cursor = connection.execute(
                """
                UPDATE p11_deployment_drafts SET state = 'confirmed', revision = ?, updated_at = ?
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND draft_id = ? AND revision = ? AND state = 'reviewed'
                """,
                (
                    confirmed_revision,
                    datetime_to_z(draft.updated_at),
                    *_ns(draft.namespace),
                    draft.draft_id,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise StaleConflictError("deployment draft confirmation is stale")
            self._audit(
                connection,
                namespace=deployment.namespace,
                action="deployment_confirmed",
                result="draft",
                record_type="colleague_deployment",
                record_id=deployment.deployment_id,
                record_revision=deployment.revision,
                actor=draft.author,
                correlation_id=draft.correlation_id,
                causation_id=draft.draft_id,
                occurred_at=draft.updated_at,
                projection={"package_digest": deployment.package_digest},
            )
            self._record_replay(
                connection,
                namespace=draft.namespace,
                operation="confirm_draft",
                actor_id=draft.author.principal_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
                result={"deployment_id": deployment.deployment_id},
                occurred_at=draft.updated_at,
            )
        return deployment

    def get_deployment(self, namespace: Namespace) -> ColleagueDeployment:
        namespace.require_colleague()
        row = self._connection.execute(
            "SELECT * FROM p11_colleague_deployments WHERE tenant_id = ? "
            "AND namespace_scope = ? AND namespace_scope_id = ? AND deployment_id = ?",
            (*_ns(namespace), namespace.scope_id),
        ).fetchone()
        if row is None:
            raise NotFoundError("exact deployment was not found")
        return self._deployment_from_row(row)

    def list_deployments(self, tenant_id: str) -> tuple[ColleagueDeployment, ...]:
        rows = self._connection.execute(
            "SELECT * FROM p11_colleague_deployments WHERE tenant_id = ? ORDER BY deployment_id",
            (tenant_id,),
        ).fetchall()
        return tuple(self._deployment_from_row(row) for row in rows)

    def transition_deployment(
        self,
        *,
        namespace: Namespace,
        target: str,
        actor: Principal,
        expected_revision: int,
        expected_package_digest: str,
        idempotency_key: str,
        request_digest: str,
        occurred_at: datetime,
        correlation_id: str,
        causation_id: str,
    ) -> LifecycleTransitionResult:
        desired = DeploymentLifecycle(target)
        with self._transaction() as connection:
            self._require_current_membership(
                connection,
                actor=actor,
                action=AuthorizationAction.MANAGE_DEPLOYMENTS,
                namespace=namespace,
            )
            replay = self._replay_result(
                connection,
                namespace=namespace,
                operation="lifecycle",
                actor_id=actor.principal_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
            )
            if replay is not None:
                current = self.get_deployment(namespace)
                active = self._active_count(connection)
                accepted = replay.get("accepted")
                replay_result = replay.get("result", "transition_applied")
                if type(accepted) is not bool or not isinstance(replay_result, str):
                    raise ConflictError("durable P11 lifecycle replay result is invalid")
                return LifecycleTransitionResult(current, accepted, replay_result, active)
            current = self.get_deployment(namespace)
            if (
                current.revision != expected_revision
                or current.package_digest != expected_package_digest
            ):
                raise StaleConflictError("deployment lifecycle binding is stale")
            if desired not in ALLOWED_LIFECYCLE_TRANSITIONS[current.lifecycle]:
                raise PermissionDeniedError("deployment lifecycle transition is forbidden")
            package = self.get_package(
                namespace.tenant_id,
                current.package_id,
                current.package_version,
                current.package_digest,
            )
            if desired is DeploymentLifecycle.ACTIVE and (
                package.trust_state
                not in {PackageTrustState.TRUSTED, PackageTrustState.LEGACY_PRESERVED}
                or package.install_state is not PackageInstallState.INSTALLED
            ):
                raise PermissionDeniedError("activation requires a trusted installed package")
            slot: int | None = None
            if desired is DeploymentLifecycle.ACTIVE:
                occupied = {
                    row["active_slot"]
                    for row in connection.execute(
                        "SELECT active_slot FROM p11_colleague_deployments "
                        "WHERE execution_host_id = 'local' AND lifecycle = 'active'"
                    )
                }
                slot = next(
                    (candidate for candidate in range(1, 11) if candidate not in occupied), None
                )
                if slot is None:
                    self._audit(
                        connection,
                        namespace=namespace,
                        action="lifecycle",
                        result="active_deployment_limit_reached",
                        record_type="colleague_deployment",
                        record_id=current.deployment_id,
                        record_revision=current.revision,
                        actor=actor,
                        correlation_id=correlation_id,
                        causation_id=causation_id,
                        occurred_at=occurred_at,
                        projection={"active_count": 10, "active_limit": 10},
                    )
                    self._record_replay(
                        connection,
                        namespace=namespace,
                        operation="lifecycle",
                        actor_id=actor.principal_id,
                        idempotency_key=idempotency_key,
                        request_digest=request_digest,
                        result={"accepted": False, "result": "active_deployment_limit_reached"},
                        occurred_at=occurred_at,
                    )
                    return LifecycleTransitionResult(
                        current, False, "active_deployment_limit_reached", 10
                    )
            next_deployment = replace(
                current,
                lifecycle=desired,
                updated_by=actor,
                updated_at=occurred_at,
                correlation_id=correlation_id,
                causation_id=causation_id,
                revision=current.revision + 1,
            )
            try:
                cursor = connection.execute(
                    """
                    UPDATE p11_colleague_deployments
                    SET lifecycle = ?, active_slot = ?, updated_by_principal_id = ?,
                        updated_by_kind = 'human', updated_at = ?, correlation_id = ?,
                        causation_id = ?, revision = ?
                    WHERE tenant_id = ? AND deployment_id = ? AND revision = ?
                    """,
                    (
                        desired.value,
                        slot,
                        actor.principal_id,
                        datetime_to_z(occurred_at),
                        correlation_id,
                        causation_id,
                        next_deployment.revision,
                        namespace.tenant_id,
                        current.deployment_id,
                        expected_revision,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                if "active_deployment_limit_reached" in str(exc):
                    raise ConflictError("active_deployment_limit_reached") from exc
                raise ConflictError("deployment lifecycle constraint conflict") from exc
            if cursor.rowcount != 1:
                raise StaleConflictError("deployment lifecycle revision is stale")
            active_count = self._active_count(connection)
            self._audit(
                connection,
                namespace=namespace,
                action="lifecycle",
                result=desired.value,
                record_type="colleague_deployment",
                record_id=current.deployment_id,
                record_revision=next_deployment.revision,
                actor=actor,
                correlation_id=correlation_id,
                causation_id=causation_id,
                occurred_at=occurred_at,
                projection={"from": current.lifecycle.value, "to": desired.value},
            )
            self._record_replay(
                connection,
                namespace=namespace,
                operation="lifecycle",
                actor_id=actor.principal_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
                result={
                    "accepted": True,
                    "result": "transition_applied",
                    "lifecycle": desired.value,
                },
                occurred_at=occurred_at,
            )
        return LifecycleTransitionResult(next_deployment, True, "transition_applied", active_count)

    @staticmethod
    def _active_count(connection: sqlite3.Connection) -> int:
        return cast(
            int,
            connection.execute(
                "SELECT COUNT(*) FROM p11_colleague_deployments "
                "WHERE execution_host_id = 'local' AND lifecycle = 'active'"
            ).fetchone()[0],
        )

    def package_in_history(
        self, namespace: Namespace, package_id: str, version: str, digest: str
    ) -> bool:
        row = self._connection.execute(
            """
            SELECT 1 FROM p11_deployment_package_history
            WHERE tenant_id = ? AND deployment_id = ? AND package_id = ?
              AND package_version = ? AND package_digest = ?
            """,
            (namespace.tenant_id, namespace.scope_id, package_id, version, digest),
        ).fetchone()
        return row is not None

    def audit_for_deployment(
        self, namespace: Namespace, *, limit: int = 100
    ) -> tuple[dict[str, object], ...]:
        namespace.require_colleague()
        if not 1 <= limit <= 500:
            raise ValueError("audit limit is outside the fixed bound")
        rows = self._connection.execute(
            """
            SELECT action, result, record_type, record_id, record_revision,
                   actor_principal_id, actor_kind, correlation_id, causation_id,
                   occurred_at, safe_projection_json, payload_digest
            FROM p11_causal_audit
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
            ORDER BY occurred_at, audit_id LIMIT ?
            """,
            (*_ns(namespace), limit),
        ).fetchall()
        return tuple(
            {
                "action": row["action"],
                "result": row["result"],
                "record_type": row["record_type"],
                "record_id": row["record_id"],
                "record_revision": row["record_revision"],
                "actor_principal_id": row["actor_principal_id"],
                "actor_kind": row["actor_kind"],
                "correlation_id": row["correlation_id"],
                "causation_id": row["causation_id"],
                "occurred_at": row["occurred_at"],
                "safe_projection": json.loads(row["safe_projection_json"]),
                "payload_digest": row["payload_digest"],
            }
            for row in rows
        )

    def deployment_is_active(self, namespace: Namespace) -> bool:
        try:
            return self.get_deployment(namespace).lifecycle is DeploymentLifecycle.ACTIVE
        except NotFoundError:
            return False

    def set_active_colleague_replay(
        self,
        *,
        session: AuthenticatedSession,
        colleague_id: str,
        idempotency_key: str,
        request_digest: str,
        occurred_at: datetime,
    ) -> AuthenticatedSession:
        """Atomically select an exact deployment and record P11 causal audit."""

        namespace = Namespace.colleague(session.tenant_id, colleague_id)
        with self._transaction() as connection:
            membership = self._require_current_membership(
                connection,
                actor=session.principal,
                action=AuthorizationAction.SELECT_DEPLOYMENT,
                namespace=namespace,
            )
            replay = connection.execute(
                """SELECT request_digest, result_json FROM p4_mutation_replay
                WHERE tenant_id = ? AND namespace_scope = 'principal'
                  AND namespace_scope_id = ?
                  AND action = 'p6:set-active-colleague:atomic'
                  AND idempotency_key = ?""",
                (session.tenant_id, session.principal.principal_id, idempotency_key),
            ).fetchone()
            if replay is not None:
                if replay["request_digest"] != request_digest:
                    raise ReplayConflictError("active colleague idempotency key was rebound")
                return from_storage_json(replay["result_json"], AuthenticatedSession)
            current_row = connection.execute(
                """SELECT * FROM p4_sessions
                WHERE tenant_id = ? AND namespace_scope = 'principal'
                  AND namespace_scope_id = ? AND session_id = ? AND revoked_at IS NULL""",
                (session.tenant_id, session.principal.principal_id, session.session_id),
            ).fetchone()
            if (
                current_row is None
                or self._session_from_row(current_row) != session
                or session.role_revision != membership.role_revision
                or session.membership_revision != membership.membership_revision
            ):
                raise PermissionDeniedError("session deployment binding was refused")
            deployment_row = connection.execute(
                """SELECT * FROM p11_colleague_deployments
                WHERE tenant_id = ? AND namespace_scope = 'colleague'
                  AND namespace_scope_id = ? AND deployment_id = ?""",
                (session.tenant_id, colleague_id, colleague_id),
            ).fetchone()
            if deployment_row is None:
                raise NotFoundError("exact deployment was not found")
            deployment = self._deployment_from_row(deployment_row)
            changed = connection.execute(
                """UPDATE p4_sessions
                SET active_colleague_id = ?, revision = revision + 1
                WHERE tenant_id = ? AND namespace_scope = 'principal'
                  AND namespace_scope_id = ? AND session_id = ? AND revision = ?""",
                (
                    colleague_id,
                    session.tenant_id,
                    session.principal.principal_id,
                    session.session_id,
                    session.revision,
                ),
            )
            if changed.rowcount != 1:
                raise ConflictError("session deployment binding lost its atomic claim")
            updated = replace(
                session,
                active_colleague_id=colleague_id,
                revision=session.revision + 1,
            )
            connection.execute(
                """INSERT INTO p4_mutation_replay(
                  schema_version, tenant_id, namespace_scope, namespace_scope_id,
                  session_id, action, idempotency_key, request_digest, result_json, created_at
                ) VALUES (?, ?, 'principal', ?, ?, 'p6:set-active-colleague:atomic', ?, ?, ?, ?)""",
                (
                    SCHEMA_VERSION,
                    session.tenant_id,
                    session.principal.principal_id,
                    session.session_id,
                    idempotency_key,
                    request_digest,
                    to_storage_json(updated),
                    datetime_to_z(occurred_at),
                ),
            )
            self._audit(
                connection,
                namespace=namespace,
                action="deployment_selected",
                result=deployment.lifecycle.value,
                record_type="colleague_deployment",
                record_id=deployment.deployment_id,
                record_revision=deployment.revision,
                actor=session.principal,
                correlation_id=session.session_id,
                causation_id=idempotency_key,
                occurred_at=occurred_at,
                projection={
                    "lifecycle": deployment.lifecycle.value,
                    "package_digest": deployment.package_digest,
                },
            )
        return updated
