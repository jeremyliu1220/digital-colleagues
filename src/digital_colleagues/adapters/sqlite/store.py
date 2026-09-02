# SPDX-License-Identifier: Apache-2.0

"""Transactional namespaced SQLite reference persistence for the P3 slice."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import TypeVar, cast

from digital_colleagues.adapters.sqlite.codec import from_storage_json, to_storage_json
from digital_colleagues.adapters.sqlite.migrations import MigrationRunner
from digital_colleagues.application.contracts import (
    AgendaClaim,
    ChannelOutcome,
    ChannelOutcomeKind,
    DispatchBundle,
    OutboxClaim,
    ReconciliationKind,
    ReconciliationOutcome,
    SemanticDecision,
    TriggerClaim,
)
from digital_colleagues.application.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    PersistenceError,
)
from digital_colleagues.application.ports import ClockPort
from digital_colleagues.core.authority import Mandate, Profile
from digital_colleagues.core.common import SCHEMA_VERSION, FrozenJsonObject
from digital_colleagues.core.effects import (
    ActionResult,
    ActionResultState,
    ApprovalChoice,
    EffectAttempt,
    EffectAttemptState,
    EffectProposal,
    HumanApprovalDecision,
)
from digital_colleagues.core.namespace import Namespace, NamespaceScope
from digital_colleagues.core.policy import ColleaguePolicy
from digital_colleagues.core.principals import Principal, PrincipalKind
from digital_colleagues.core.runtime import (
    AgendaItem,
    AgendaItemState,
    Decision,
    InputEvent,
    TimerOccurrence,
    WakeCycle,
    WakeCycleState,
)
from digital_colleagues.core.serialization import (
    contract_to_public_data,
    datetime_from_z,
    datetime_to_z,
)
from digital_colleagues.core.work import FiniteWork
from digital_colleagues.governance.approvals import (
    authorize_effect_proposal,
    authorize_human_approval,
)

RecordT = TypeVar("RecordT")

_RECORD_IDENTITIES: dict[type[object], tuple[str, str, bool]] = {
    Principal: ("principal", "principal_id", False),
    Profile: ("profile", "profile_id", False),
    Mandate: ("mandate", "mandate_id", False),
    ColleaguePolicy: ("colleague_policy", "policy_id", False),
    FiniteWork: ("finite_work", "work_id", False),
    InputEvent: ("input_event", "event_id", True),
    TimerOccurrence: ("timer_occurrence", "occurrence_id", True),
    WakeCycle: ("wake_cycle", "wake_cycle_id", False),
    AgendaItem: ("agenda_item", "agenda_item_id", False),
    Decision: ("decision", "decision_id", True),
    EffectProposal: ("effect_proposal", "proposal_id", True),
    HumanApprovalDecision: ("human_approval", "approval_decision_id", True),
    EffectAttempt: ("effect_attempt", "effect_attempt_id", False),
    ActionResult: ("action_result", "action_result_id", True),
}


def _record_identity(record: object) -> tuple[str, str, bool]:
    identity = _RECORD_IDENTITIES.get(type(record))
    if identity is None:
        raise PersistenceError("unsupported durable record type")
    record_type, field, immutable = identity
    return record_type, cast(str, getattr(record, field)), immutable


def _namespace(record: object) -> Namespace:
    namespace = getattr(record, "namespace", None)
    if not isinstance(namespace, Namespace):
        raise PersistenceError("durable record namespace is missing")
    return namespace


def _ns(namespace: Namespace) -> tuple[str, str, str]:
    scope_id = namespace.scope_id or ""
    return namespace.tenant_id, namespace.scope.value, scope_id


def _namespace_from_row(row: sqlite3.Row) -> Namespace:
    scope = NamespaceScope(row["namespace_scope"])
    scope_id = row["namespace_scope_id"] or None
    return Namespace(row["tenant_id"], scope, scope_id)


def _digest_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _audit_id(record_type: str, record_id: str, revision: int) -> str:
    encoded = f"{record_type}\0{record_id}\0{revision}".encode()
    return "audit:" + hashlib.sha256(encoded).hexdigest()[:32]


class SQLiteRuntimeStore:
    """One injectable local database; every query still requires an exact Namespace."""

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
            self._migrations = MigrationRunner(migrations_path).apply(
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

    def close(self) -> None:
        if not self._closed:
            self._connection.close()
            self._closed = True

    def __enter__(self) -> SQLiteRuntimeStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        if self._closed:
            raise PersistenceError("SQLite reference store is closed")
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                yield self._connection
                self._connection.execute("COMMIT")
            except Exception:
                try:
                    self._connection.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise

    def healthcheck(self) -> dict[str, object]:
        if self._closed:
            raise PersistenceError("SQLite reference store is closed")
        mode = self._connection.execute("PRAGMA journal_mode").fetchone()[0]
        foreign_keys = self._connection.execute("PRAGMA foreign_keys").fetchone()[0]
        busy_timeout = self._connection.execute("PRAGMA busy_timeout").fetchone()[0]
        return {
            "schema_version": SCHEMA_VERSION,
            "journal_mode": str(mode).lower(),
            "foreign_keys": foreign_keys == 1,
            "busy_timeout_ms": busy_timeout,
            "migration_count": len(self._migrations),
            "migration_checksums": tuple(item.checksum for item in self._migrations),
        }

    def _insert_record(
        self,
        connection: sqlite3.Connection,
        record: object,
        *,
        actor: Principal | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        record_type, record_id, immutable = _record_identity(record)
        namespace = _namespace(record)
        revision = cast(int, getattr(record, "revision", 1))
        record_actor = actor or getattr(record, "actor", None)
        if record_actor is None:
            record_actor = getattr(record, "author", None)
        if record_actor is None:
            record_actor = getattr(record, "updated_by", None)
        if record_actor is None:
            record_actor = getattr(record, "issued_by", None)
        if not isinstance(record_actor, Principal):
            raise PersistenceError("durable record actor is missing")
        record_correlation = correlation_id or getattr(record, "correlation_id", None)
        if not isinstance(record_correlation, str):
            raise PersistenceError("durable record correlation is missing")
        record_causation = causation_id
        if causation_id is None:
            candidate = getattr(record, "causation_id", None)
            record_causation = candidate if isinstance(candidate, str) else None
        record_occurred = occurred_at
        if record_occurred is None:
            for field in ("occurred_at", "updated_at", "effective_at", "created_at"):
                candidate = getattr(record, field, None)
                if isinstance(candidate, datetime):
                    record_occurred = candidate
                    break
        if record_occurred is None:
            raise PersistenceError("durable record timestamp is missing")
        serialized = to_storage_json(record)
        try:
            connection.execute(
                """
                INSERT INTO domain_records(
                  schema_version, tenant_id, namespace_scope, namespace_scope_id,
                  record_type, record_id, revision, immutable, payload_json,
                  actor_principal_id, correlation_id, causation_id, occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    SCHEMA_VERSION,
                    *_ns(namespace),
                    record_type,
                    record_id,
                    revision,
                    int(immutable),
                    serialized,
                    record_actor.principal_id,
                    record_correlation,
                    record_causation,
                    datetime_to_z(record_occurred),
                ),
            )
            self._insert_audit(
                connection,
                record=record,
                record_type=record_type,
                record_id=record_id,
                revision=revision,
                actor=record_actor,
                correlation_id=record_correlation,
                causation_id=record_causation,
                occurred_at=record_occurred,
                serialized=serialized,
            )
        except sqlite3.IntegrityError as exc:
            raise ConflictError("durable record identity or constraint conflict") from exc

    def _insert_audit(
        self,
        connection: sqlite3.Connection,
        *,
        record: object,
        record_type: str,
        record_id: str,
        revision: int,
        actor: Principal,
        correlation_id: str,
        causation_id: str | None,
        occurred_at: datetime,
        serialized: str,
    ) -> None:
        namespace = _namespace(record)
        safe_projection = json.dumps(
            contract_to_public_data(record),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        connection.execute(
            """
            INSERT INTO audit_records(
              schema_version, tenant_id, namespace_scope, namespace_scope_id,
              audit_id, record_type, record_id, record_revision,
              actor_principal_id, correlation_id, causation_id, occurred_at,
              payload_digest, safe_projection_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SCHEMA_VERSION,
                *_ns(namespace),
                _audit_id(record_type, record_id, revision),
                record_type,
                record_id,
                revision,
                actor.principal_id,
                correlation_id,
                causation_id,
                datetime_to_z(occurred_at),
                _digest_text(serialized),
                safe_projection,
            ),
        )

    def _update_record(
        self,
        connection: sqlite3.Connection,
        record: object,
        *,
        expected_revision: int,
    ) -> None:
        record_type, record_id, immutable = _record_identity(record)
        if immutable:
            raise PersistenceError("immutable causal records cannot be updated")
        namespace = _namespace(record)
        revision = getattr(record, "revision", None)
        if not isinstance(revision, int):
            raise PersistenceError("updated durable record revision is missing")
        if revision != expected_revision + 1:
            raise ConflictError("record revision did not advance exactly once")
        actor = getattr(record, "actor", None)
        if actor is None:
            actor = getattr(record, "updated_by", None)
        if actor is None:
            actor = getattr(record, "issued_by", None)
        if not isinstance(actor, Principal):
            raise PersistenceError("updated durable record actor is missing")
        correlation_id = getattr(record, "correlation_id", None)
        if not isinstance(correlation_id, str):
            correlation_id = f"record:{record_id}"
        causation_id = getattr(record, "causation_id", None)
        occurred_at = getattr(record, "occurred_at", None)
        if not isinstance(occurred_at, datetime):
            occurred_at = getattr(record, "updated_at", None)
        if not isinstance(occurred_at, datetime):
            occurred_at = getattr(record, "effective_at", None)
        if not isinstance(occurred_at, datetime):
            raise PersistenceError("updated durable record timestamp is missing")
        serialized = to_storage_json(record)
        cursor = connection.execute(
            """
            UPDATE domain_records
            SET revision = ?, payload_json = ?, actor_principal_id = ?,
                correlation_id = ?, causation_id = ?, occurred_at = ?
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND record_type = ? AND record_id = ? AND revision = ? AND immutable = 0
            """,
            (
                revision,
                serialized,
                actor.principal_id,
                correlation_id,
                causation_id,
                datetime_to_z(occurred_at),
                *_ns(namespace),
                record_type,
                record_id,
                expected_revision,
            ),
        )
        if cursor.rowcount != 1:
            raise ConflictError("optimistic record revision conflict")
        self._insert_audit(
            connection,
            record=record,
            record_type=record_type,
            record_id=record_id,
            revision=revision,
            actor=actor,
            correlation_id=correlation_id,
            causation_id=causation_id,
            occurred_at=occurred_at,
            serialized=serialized,
        )

    def _get_record(
        self,
        connection: sqlite3.Connection,
        namespace: Namespace,
        record_type: str,
        record_id: str,
        expected: type[RecordT],
    ) -> RecordT:
        row = connection.execute(
            """
            SELECT payload_json FROM domain_records
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND record_type = ? AND record_id = ?
            """,
            (*_ns(namespace), record_type, record_id),
        ).fetchone()
        if row is None:
            raise NotFoundError("namespaced durable record was not found")
        return from_storage_json(row["payload_json"], expected)

    def get_principal(self, tenant_id: str, principal_id: str) -> Principal:
        return self._get_record(
            self._connection,
            Namespace.principal(tenant_id, principal_id),
            "principal",
            principal_id,
            Principal,
        )

    def get_profile(self, namespace: Namespace, profile_id: str) -> Profile:
        return self._get_record(self._connection, namespace, "profile", profile_id, Profile)

    def get_mandate(self, namespace: Namespace, mandate_id: str) -> Mandate:
        return self._get_record(self._connection, namespace, "mandate", mandate_id, Mandate)

    def get_work(self, namespace: Namespace, work_id: str) -> FiniteWork:
        return self._get_record(self._connection, namespace, "finite_work", work_id, FiniteWork)

    def get_event(self, namespace: Namespace, event_id: str) -> InputEvent:
        return self._get_record(self._connection, namespace, "input_event", event_id, InputEvent)

    def get_timer_occurrence(self, namespace: Namespace, occurrence_id: str) -> TimerOccurrence:
        return self._get_record(
            self._connection,
            namespace,
            "timer_occurrence",
            occurrence_id,
            TimerOccurrence,
        )

    def get_wake_cycle(self, namespace: Namespace, wake_cycle_id: str) -> WakeCycle:
        return self._get_record(self._connection, namespace, "wake_cycle", wake_cycle_id, WakeCycle)

    def get_agenda_item(self, namespace: Namespace, agenda_item_id: str) -> AgendaItem:
        return self._get_record(
            self._connection, namespace, "agenda_item", agenda_item_id, AgendaItem
        )

    def get_proposal(self, namespace: Namespace, proposal_id: str) -> EffectProposal:
        return self._get_record(
            self._connection, namespace, "effect_proposal", proposal_id, EffectProposal
        )

    def get_approval(
        self, namespace: Namespace, approval_decision_id: str
    ) -> HumanApprovalDecision:
        return self._get_record(
            self._connection,
            namespace,
            "human_approval",
            approval_decision_id,
            HumanApprovalDecision,
        )

    def get_approval_replay(
        self, namespace: Namespace, idempotency_key: str
    ) -> tuple[HumanApprovalDecision, EffectAttempt | None] | None:
        replay = self._connection.execute(
            """
            SELECT record_id FROM replay_ledger
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND ledger_kind = 'approval' AND idempotency_key = ?
            """,
            (*_ns(namespace), idempotency_key),
        ).fetchone()
        if replay is None:
            return None
        decision = self._get_record(
            self._connection,
            namespace,
            "human_approval",
            replay["record_id"],
            HumanApprovalDecision,
        )
        attempt_row = self._connection.execute(
            """
            SELECT effect_attempt_id FROM outbox
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND approval_decision_id = ?
            """,
            (*_ns(namespace), decision.approval_decision_id),
        ).fetchone()
        attempt = (
            None
            if attempt_row is None
            else self._get_record(
                self._connection,
                namespace,
                "effect_attempt",
                attempt_row["effect_attempt_id"],
                EffectAttempt,
            )
        )
        return decision, attempt

    def get_action_result(self, namespace: Namespace, action_result_id: str) -> ActionResult:
        return self._get_record(
            self._connection, namespace, "action_result", action_result_id, ActionResult
        )

    def causal_history(
        self, namespace: Namespace, correlation_id: str
    ) -> tuple[dict[str, object], ...]:
        rows = self._connection.execute(
            """
            SELECT schema_version, tenant_id, namespace_scope, namespace_scope_id,
                   audit_id, record_type, record_id, record_revision,
                   actor_principal_id, correlation_id, causation_id, occurred_at,
                   payload_digest, safe_projection_json
            FROM audit_records
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND correlation_id = ?
            ORDER BY occurred_at, audit_id
            """,
            (*_ns(namespace), correlation_id),
        ).fetchall()
        return tuple(
            {
                "schema_version": row["schema_version"],
                "namespace": {
                    "tenant_id": row["tenant_id"],
                    "scope": row["namespace_scope"],
                    "scope_id": row["namespace_scope_id"],
                },
                "audit_id": row["audit_id"],
                "record_type": row["record_type"],
                "record_id": row["record_id"],
                "record_revision": row["record_revision"],
                "actor_principal_id": row["actor_principal_id"],
                "correlation_id": row["correlation_id"],
                "causation_id": row["causation_id"],
                "occurred_at": row["occurred_at"],
                "payload_digest": row["payload_digest"],
                "safe_projection": json.loads(row["safe_projection_json"]),
            }
            for row in rows
        )

    def bootstrap(
        self,
        *,
        namespace: Namespace,
        principals: tuple[Principal, ...],
        profile: Profile,
        mandate: Mandate,
        work: FiniteWork,
        actor: Principal,
        correlation_id: str,
        occurred_at: datetime,
    ) -> bool:
        namespace.require_exact(profile.namespace)
        namespace.require_exact(mandate.namespace)
        namespace.require_exact(work.namespace)
        namespace.require_same_tenant(actor.namespace)
        if not principals or actor not in principals:
            raise PermissionDeniedError("bootstrap actor must be a durable supplied principal")
        with self._transaction() as connection:
            exists = connection.execute(
                """
                SELECT payload_json FROM domain_records
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND record_type = 'profile' AND record_id = ?
                """,
                (*_ns(namespace), profile.profile_id),
            ).fetchone()
            if exists is not None:
                existing = from_storage_json(exists["payload_json"], Profile)
                if existing != profile:
                    raise ConflictError("bootstrap profile identity already exists with drift")
                return False
            for principal in principals:
                if principal.namespace.tenant_id != namespace.tenant_id:
                    raise PermissionDeniedError("bootstrap principal crosses tenant namespace")
                self._insert_record(
                    connection,
                    principal,
                    actor=actor,
                    correlation_id=correlation_id,
                    causation_id=None,
                    occurred_at=occurred_at,
                )
            self._insert_record(
                connection,
                profile,
                actor=actor,
                correlation_id=correlation_id,
                causation_id=None,
                occurred_at=occurred_at,
            )
            self._insert_record(
                connection,
                mandate,
                actor=actor,
                correlation_id=correlation_id,
                causation_id=profile.profile_id,
                occurred_at=occurred_at,
            )
            self._insert_record(connection, work)
        return True

    def ingest_event(
        self, event: InputEvent, *, idempotency_key: str, trigger_id: str
    ) -> tuple[InputEvent, bool]:
        with self._transaction() as connection:
            replay = connection.execute(
                """
                SELECT record_id FROM replay_ledger
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND ledger_kind = 'input_event' AND idempotency_key = ?
                """,
                (*_ns(event.namespace), idempotency_key),
            ).fetchone()
            if replay is not None:
                existing = self._get_record(
                    connection,
                    event.namespace,
                    "input_event",
                    replay["record_id"],
                    InputEvent,
                )
                if replace(event, occurred_at=existing.occurred_at) != existing:
                    raise ConflictError("input idempotency replay drifted")
                return existing, False
            self._insert_record(connection, event)
            try:
                connection.execute(
                    """
                    INSERT INTO replay_ledger(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      ledger_kind, idempotency_key, record_type, record_id, created_at
                    ) VALUES (?, ?, ?, ?, 'input_event', ?, 'input_event', ?, ?)
                    """,
                    (
                        SCHEMA_VERSION,
                        *_ns(event.namespace),
                        idempotency_key,
                        event.event_id,
                        datetime_to_z(event.occurred_at),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO triggers(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      trigger_id, trigger_kind, event_id, due_at, state,
                      correlation_id, causation_id, actor_principal_id, created_at, revision
                    ) VALUES (?, ?, ?, ?, ?, 'event', ?, ?, 'pending', ?, ?, ?, ?, 1)
                    """,
                    (
                        SCHEMA_VERSION,
                        *_ns(event.namespace),
                        trigger_id,
                        event.event_id,
                        datetime_to_z(event.occurred_at),
                        event.correlation_id,
                        event.event_id,
                        event.actor.principal_id,
                        datetime_to_z(event.occurred_at),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ConflictError("input replay or trigger identity conflict") from exc
        return event, True

    def ingest_timer(
        self,
        occurrence: TimerOccurrence,
        *,
        idempotency_key: str,
        trigger_id: str,
    ) -> tuple[TimerOccurrence, bool]:
        with self._transaction() as connection:
            replay = connection.execute(
                """
                SELECT record_id FROM replay_ledger
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND ledger_kind = 'timer_occurrence' AND idempotency_key = ?
                """,
                (*_ns(occurrence.namespace), idempotency_key),
            ).fetchone()
            if replay is not None:
                existing = self._get_record(
                    connection,
                    occurrence.namespace,
                    "timer_occurrence",
                    replay["record_id"],
                    TimerOccurrence,
                )
                if replace(occurrence, occurred_at=existing.occurred_at) != existing:
                    raise ConflictError("timer occurrence replay drifted")
                return existing, False
            self._insert_record(connection, occurrence)
            try:
                connection.execute(
                    """
                    INSERT INTO replay_ledger(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      ledger_kind, idempotency_key, record_type, record_id, created_at
                    ) VALUES (?, ?, ?, ?, 'timer_occurrence', ?, 'timer_occurrence', ?, ?)
                    """,
                    (
                        SCHEMA_VERSION,
                        *_ns(occurrence.namespace),
                        idempotency_key,
                        occurrence.occurrence_id,
                        datetime_to_z(occurrence.occurred_at),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO timer_triggers(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      trigger_id, occurrence_id, timer_id, due_at, state,
                      correlation_id, causation_id, actor_principal_id, created_at, revision
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, 1)
                    """,
                    (
                        SCHEMA_VERSION,
                        *_ns(occurrence.namespace),
                        trigger_id,
                        occurrence.occurrence_id,
                        occurrence.timer_id,
                        datetime_to_z(occurrence.due_at),
                        occurrence.correlation_id,
                        occurrence.occurrence_id,
                        occurrence.actor.principal_id,
                        datetime_to_z(occurrence.occurred_at),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ConflictError("timer replay or trigger identity conflict") from exc
        return occurrence, True

    def claim_trigger(
        self,
        namespace: Namespace,
        *,
        owner: str,
        now: datetime,
        lease_until: datetime,
    ) -> TriggerClaim | None:
        with self._transaction() as connection:
            event_row = connection.execute(
                """
                SELECT * FROM triggers
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND due_at <= ?
                  AND (
                    state = 'pending'
                    OR (state = 'claimed' AND lease_until < ?)
                  )
                ORDER BY due_at, trigger_id
                LIMIT 1
                """,
                (*_ns(namespace), datetime_to_z(now), datetime_to_z(now)),
            ).fetchone()
            timer_row = connection.execute(
                """
                SELECT * FROM timer_triggers
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND due_at <= ?
                  AND (
                    state = 'pending'
                    OR (state = 'claimed' AND lease_until < ?)
                  )
                ORDER BY due_at, trigger_id
                LIMIT 1
                """,
                (*_ns(namespace), datetime_to_z(now), datetime_to_z(now)),
            ).fetchone()
            candidates = tuple(
                (source_type, candidate)
                for source_type, candidate in (
                    ("input_event", event_row),
                    ("timer_occurrence", timer_row),
                )
                if candidate is not None
            )
            if not candidates:
                return None
            source_record_type, row = min(
                candidates,
                key=lambda item: (
                    item[1]["due_at"],
                    item[1]["trigger_id"],
                    item[0],
                ),
            )
            trigger_table = "triggers" if source_record_type == "input_event" else "timer_triggers"
            fencing = row["fencing_token"] + 1
            cursor = connection.execute(
                f"""
                UPDATE {trigger_table}
                SET state = 'claimed', lease_owner = ?, lease_until = ?,
                    fencing_token = ?, attempt_count = attempt_count + 1,
                    revision = revision + 1
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND trigger_id = ? AND revision = ?
                """,
                (
                    owner,
                    datetime_to_z(lease_until),
                    fencing,
                    *_ns(namespace),
                    row["trigger_id"],
                    row["revision"],
                ),
            )
            if cursor.rowcount != 1:
                raise ConflictError("trigger optimistic claim conflict")
            return TriggerClaim(
                namespace=namespace,
                trigger_id=row["trigger_id"],
                source_record_type=source_record_type,
                source_id=(
                    row["event_id"] if source_record_type == "input_event" else row["occurrence_id"]
                ),
                trigger_kind=row["trigger_kind"],
                lease_owner=owner,
                lease_until=lease_until,
                fencing_token=fencing,
                correlation_id=row["correlation_id"],
                causation_id=row["causation_id"],
            )

    @staticmethod
    def _event_source_key(event: InputEvent) -> tuple[str, str | None, int, str]:
        work_id = event.safe_projection.get("work_id")
        work = work_id if isinstance(work_id, str) and work_id else None
        source_key = f"work:{work}" if work is not None else f"event:{event.event_type}"
        raw_priority = event.safe_projection.get("priority")
        priority = raw_priority if type(raw_priority) is int else 100
        raw_title = event.safe_projection.get("title")
        title = (
            raw_title if isinstance(raw_title, str) and raw_title.strip() else "finite work update"
        )
        return source_key, work, priority, title

    @staticmethod
    def _timer_source_key(
        occurrence: TimerOccurrence,
    ) -> tuple[str, str | None, int, str]:
        work_id = occurrence.safe_projection.get("work_id")
        work = work_id if isinstance(work_id, str) and work_id else None
        source_key = f"timer:{occurrence.timer_id}"
        raw_priority = occurrence.safe_projection.get("priority")
        priority = raw_priority if type(raw_priority) is int else 100
        raw_title = occurrence.safe_projection.get("title")
        title = (
            raw_title
            if isinstance(raw_title, str) and raw_title.strip()
            else "scheduled timer work"
        )
        return source_key, work, priority, title

    def materialize_agenda(
        self,
        claim: TriggerClaim,
        *,
        wake_cycle_id: str,
        agenda_item_id: str,
        actor: Principal,
        occurred_at: datetime,
    ) -> tuple[WakeCycle, AgendaItem]:
        with self._transaction() as connection:
            trigger_table = (
                "triggers"
                if claim.source_record_type == "input_event"
                else "timer_triggers"
                if claim.source_record_type == "timer_occurrence"
                else ""
            )
            if not trigger_table:
                raise ConflictError("trigger source type is unsupported")
            trigger = connection.execute(
                f"""
                SELECT * FROM {trigger_table}
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND trigger_id = ?
                """,
                (*_ns(claim.namespace), claim.trigger_id),
            ).fetchone()
            if (
                trigger is None
                or trigger["state"] != "claimed"
                or trigger["lease_owner"] != claim.lease_owner
                or trigger["fencing_token"] != claim.fencing_token
            ):
                raise ConflictError("stale trigger owner or fencing token")
            source: InputEvent | TimerOccurrence
            trigger_event_ids: tuple[str, ...]
            trigger_timer_ids: tuple[str, ...]
            if claim.source_record_type == "input_event":
                source = self._get_record(
                    connection,
                    claim.namespace,
                    "input_event",
                    claim.source_id,
                    InputEvent,
                )
                source_key, work_id, priority, title = self._event_source_key(source)
                source_event_id: str | None = source.event_id
                source_timer_id: str | None = None
                trigger_event_ids = (source.event_id,)
                trigger_timer_ids = ()
            else:
                source = self._get_record(
                    connection,
                    claim.namespace,
                    "timer_occurrence",
                    claim.source_id,
                    TimerOccurrence,
                )
                source_key, work_id, priority, title = self._timer_source_key(source)
                source_event_id = None
                source_timer_id = source.occurrence_id
                trigger_event_ids = ()
                trigger_timer_ids = (source.occurrence_id,)
            existing = connection.execute(
                """
                SELECT * FROM agenda_runtime
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND source_key = ?
                """,
                (*_ns(claim.namespace), source_key),
            ).fetchone()
            actual_agenda_id = agenda_item_id if existing is None else existing["agenda_item_id"]
            generation = 1 if existing is None else existing["generation"] + 1
            causes = (
                [claim.source_id]
                if existing is None
                else list(json.loads(existing["cause_ids_json"])) + [claim.source_id]
            )
            if len(causes) != len(set(causes)):
                raise ConflictError("Agenda cause replay was not coalesced safely")
            wake = WakeCycle(
                namespace=claim.namespace,
                wake_cycle_id=wake_cycle_id,
                state=WakeCycleState.RUNNING,
                trigger_event_ids=trigger_event_ids,
                agenda_item_ids=(actual_agenda_id,),
                actor=actor,
                correlation_id=source.correlation_id,
                causation_id=claim.source_id,
                occurred_at=occurred_at,
                revision=1,
                fencing_token=claim.fencing_token,
                checkpoint_generation=generation,
                trigger_timer_occurrence_ids=trigger_timer_ids,
                policy_id=source.policy_id,
                policy_revision=source.policy_revision,
            )
            self._insert_record(connection, wake)
            if existing is None:
                agenda = AgendaItem(
                    namespace=claim.namespace,
                    agenda_item_id=actual_agenda_id,
                    wake_cycle_id=wake_cycle_id,
                    source_event_id=source_event_id,
                    work_id=work_id,
                    title=title,
                    state=AgendaItemState.PENDING,
                    priority=priority,
                    due_at=None,
                    actor=actor,
                    correlation_id=source.correlation_id,
                    causation_id=wake_cycle_id,
                    occurred_at=occurred_at,
                    revision=1,
                    generation=1,
                    handled_generation=0,
                    cause_ids=tuple(causes),
                    source_timer_occurrence_id=source_timer_id,
                    policy_id=source.policy_id,
                    policy_revision=source.policy_revision,
                )
                self._insert_record(connection, agenda)
                connection.execute(
                    """
                    INSERT INTO agenda_runtime(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      agenda_item_id, source_key, generation, handled_generation,
                      cause_ids_json, state, priority, due_at, current_wake_cycle_id, revision
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, 0, ?, 'pending', ?, NULL, ?, 1)
                    """,
                    (
                        SCHEMA_VERSION,
                        *_ns(claim.namespace),
                        actual_agenda_id,
                        source_key,
                        json.dumps(causes, separators=(",", ":")),
                        priority,
                        wake_cycle_id,
                    ),
                )
            else:
                existing_agenda = self._get_record(
                    connection,
                    claim.namespace,
                    "agenda_item",
                    existing["agenda_item_id"],
                    AgendaItem,
                )
                state = (
                    AgendaItemState.SELECTED
                    if existing["state"] == "selected"
                    else AgendaItemState.PENDING
                )
                agenda = replace(
                    existing_agenda,
                    wake_cycle_id=wake_cycle_id,
                    source_event_id=source_event_id,
                    source_timer_occurrence_id=source_timer_id,
                    state=state,
                    actor=actor,
                    correlation_id=source.correlation_id,
                    causation_id=wake_cycle_id,
                    occurred_at=occurred_at,
                    revision=existing_agenda.revision + 1,
                    generation=generation,
                    cause_ids=tuple(causes),
                    policy_id=source.policy_id,
                    policy_revision=source.policy_revision,
                )
                self._update_record(connection, agenda, expected_revision=existing_agenda.revision)
                connection.execute(
                    """
                    UPDATE agenda_runtime
                    SET generation = ?, cause_ids_json = ?, state = ?,
                        current_wake_cycle_id = ?, revision = revision + 1
                    WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                      AND agenda_item_id = ?
                    """,
                    (
                        generation,
                        json.dumps(causes, separators=(",", ":")),
                        state.value,
                        wake_cycle_id,
                        *_ns(claim.namespace),
                        existing["agenda_item_id"],
                    ),
                )
            cursor = connection.execute(
                f"""
                UPDATE {trigger_table}
                SET state = 'completed', lease_owner = NULL, lease_until = NULL,
                    revision = revision + 1
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND trigger_id = ? AND lease_owner = ? AND fencing_token = ?
                """,
                (
                    *_ns(claim.namespace),
                    claim.trigger_id,
                    claim.lease_owner,
                    claim.fencing_token,
                ),
            )
            if cursor.rowcount != 1:
                raise ConflictError("stale trigger checkpoint was refused")
            return wake, agenda

    def claim_agenda(
        self,
        namespace: Namespace,
        *,
        owner: str,
        now: datetime,
        lease_until: datetime,
    ) -> AgendaClaim | None:
        with self._transaction() as connection:
            row = connection.execute(
                """
                SELECT * FROM agenda_runtime
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND generation > handled_generation
                  AND (
                    state = 'pending'
                    OR (state = 'selected' AND lease_until < ?)
                  )
                ORDER BY
                  starvation_count DESC,
                  priority DESC,
                  CASE WHEN due_at IS NULL THEN 1 ELSE 0 END,
                  due_at,
                  agenda_item_id
                LIMIT 1
                """,
                (*_ns(namespace), datetime_to_z(now)),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                """
                UPDATE agenda_runtime
                SET starvation_count = starvation_count + 1
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND generation > handled_generation AND state = 'pending'
                  AND agenda_item_id <> ?
                """,
                (*_ns(namespace), row["agenda_item_id"]),
            )
            fencing = row["fencing_token"] + 1
            cursor = connection.execute(
                """
                UPDATE agenda_runtime
                SET state = 'selected', lease_owner = ?, lease_until = ?,
                    fencing_token = ?, starvation_count = 0, revision = revision + 1
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND agenda_item_id = ? AND revision = ?
                """,
                (
                    owner,
                    datetime_to_z(lease_until),
                    fencing,
                    *_ns(namespace),
                    row["agenda_item_id"],
                    row["revision"],
                ),
            )
            if cursor.rowcount != 1:
                raise ConflictError("Agenda optimistic claim conflict")
            existing = self._get_record(
                connection, namespace, "agenda_item", row["agenda_item_id"], AgendaItem
            )
            selected = replace(
                existing,
                state=AgendaItemState.SELECTED,
                revision=existing.revision + 1,
            )
            self._update_record(connection, selected, expected_revision=existing.revision)
            return AgendaClaim(
                namespace=namespace,
                agenda_item=selected,
                lease_owner=owner,
                lease_until=lease_until,
                fencing_token=fencing,
                claimed_generation=row["generation"],
            )

    def _require_agenda_claim(
        self, connection: sqlite3.Connection, claim: AgendaClaim
    ) -> sqlite3.Row:
        row = connection.execute(
            """
            SELECT * FROM agenda_runtime
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND agenda_item_id = ?
            """,
            (*_ns(claim.namespace), claim.agenda_item.agenda_item_id),
        ).fetchone()
        if (
            row is None
            or row["state"] != "selected"
            or row["lease_owner"] != claim.lease_owner
            or row["fencing_token"] != claim.fencing_token
        ):
            raise ConflictError("stale Agenda owner or fencing token")
        return cast(sqlite3.Row, row)

    def release_agenda(self, claim: AgendaClaim) -> None:
        with self._transaction() as connection:
            row = self._require_agenda_claim(connection, claim)
            connection.execute(
                """
                UPDATE agenda_runtime
                SET state = 'pending', lease_owner = NULL, lease_until = NULL,
                    revision = revision + 1
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND agenda_item_id = ? AND fencing_token = ?
                """,
                (
                    *_ns(claim.namespace),
                    claim.agenda_item.agenda_item_id,
                    claim.fencing_token,
                ),
            )
            current = self._get_record(
                connection,
                claim.namespace,
                "agenda_item",
                claim.agenda_item.agenda_item_id,
                AgendaItem,
            )
            released = replace(
                current,
                state=AgendaItemState.PENDING,
                revision=current.revision + 1,
                generation=row["generation"],
                handled_generation=row["handled_generation"],
            )
            self._update_record(connection, released, expected_revision=current.revision)

    def commit_semantic_decision(self, claim: AgendaClaim, semantic: SemanticDecision) -> None:
        with self._transaction() as connection:
            row = self._require_agenda_claim(connection, claim)
            semantic = self._prepare_semantic_decision(connection, claim, semantic)
            semantic.decision.namespace.require_exact(claim.namespace)
            if semantic.decision.agenda_item_id != claim.agenda_item.agenda_item_id:
                raise ConflictError("semantic decision cites a different Agenda item")
            if semantic.decision.wake_cycle_id != claim.agenda_item.wake_cycle_id:
                raise ConflictError("semantic decision cites a different wake cycle")
            self._insert_record(connection, semantic.decision)
            if semantic.proposal is not None:
                if semantic.proposal.decision_id != semantic.decision.decision_id:
                    raise ConflictError("effect proposal decision binding drifted")
                self._insert_record(connection, semantic.proposal)
            current_generation = row["generation"]
            handled = max(row["handled_generation"], claim.claimed_generation)
            final_state = (
                "pending" if current_generation > claim.claimed_generation else "completed"
            )
            cursor = connection.execute(
                """
                UPDATE agenda_runtime
                SET handled_generation = ?, state = ?, lease_owner = NULL, lease_until = NULL,
                    revision = revision + 1
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND agenda_item_id = ? AND lease_owner = ? AND fencing_token = ?
                """,
                (
                    handled,
                    final_state,
                    *_ns(claim.namespace),
                    claim.agenda_item.agenda_item_id,
                    claim.lease_owner,
                    claim.fencing_token,
                ),
            )
            if cursor.rowcount != 1:
                raise ConflictError("stale Agenda checkpoint was refused")
            current = self._get_record(
                connection,
                claim.namespace,
                "agenda_item",
                claim.agenda_item.agenda_item_id,
                AgendaItem,
            )
            completed = replace(
                current,
                state=(
                    AgendaItemState.PENDING
                    if final_state == "pending"
                    else AgendaItemState.COMPLETED
                ),
                revision=current.revision + 1,
                generation=current_generation,
                handled_generation=handled,
            )
            self._update_record(connection, completed, expected_revision=current.revision)
            wake = self._get_record(
                connection,
                claim.namespace,
                "wake_cycle",
                semantic.decision.wake_cycle_id,
                WakeCycle,
            )
            finalized_wake = replace(
                wake,
                state=WakeCycleState.COMPLETED,
                revision=wake.revision + 1,
                checkpoint_generation=claim.claimed_generation,
            )
            self._update_record(connection, finalized_wake, expected_revision=wake.revision)

    def _prepare_semantic_decision(
        self,
        connection: sqlite3.Connection,
        claim: AgendaClaim,
        semantic: SemanticDecision,
    ) -> SemanticDecision:
        del connection, claim
        return semantic

    def pending_agenda_count(self, namespace: Namespace) -> int:
        row = self._connection.execute(
            """
            SELECT COUNT(*) AS count FROM agenda_runtime
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND generation > handled_generation
            """,
            _ns(namespace),
        ).fetchone()
        return cast(int, row["count"])

    def commit_approval_and_attempt(
        self,
        *,
        namespace: Namespace,
        mandate_id: str,
        expected_mandate_revision: int,
        decision: HumanApprovalDecision,
        effect_attempt_id: str,
        outbox_id: str,
        service_actor: Principal,
        occurred_at: datetime,
    ) -> tuple[HumanApprovalDecision, EffectAttempt | None, bool]:
        namespace.require_exact(decision.namespace)
        with self._transaction() as connection:
            replay = connection.execute(
                """
                SELECT record_id FROM replay_ledger
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND ledger_kind = 'approval' AND idempotency_key = ?
                """,
                (*_ns(namespace), decision.idempotency_key),
            ).fetchone()
            if replay is not None:
                existing = self._get_record(
                    connection,
                    namespace,
                    "human_approval",
                    replay["record_id"],
                    HumanApprovalDecision,
                )
                if (
                    replace(
                        decision,
                        occurred_at=existing.occurred_at,
                        valid_until=existing.valid_until,
                    )
                    != existing
                ):
                    raise ConflictError("approval idempotency replay drifted")
                attempt_row = connection.execute(
                    """
                    SELECT effect_attempt_id FROM outbox
                    WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                      AND approval_decision_id = ?
                    """,
                    (*_ns(namespace), decision.approval_decision_id),
                ).fetchone()
                attempt = (
                    None
                    if attempt_row is None
                    else self._get_record(
                        connection,
                        namespace,
                        "effect_attempt",
                        attempt_row["effect_attempt_id"],
                        EffectAttempt,
                    )
                )
                return existing, attempt, False
            proposal = self._get_record(
                connection, namespace, "effect_proposal", decision.proposal_id, EffectProposal
            )
            mandate = self._get_record(connection, namespace, "mandate", mandate_id, Mandate)
            approver = self._get_record(
                connection,
                Namespace.principal(namespace.tenant_id, decision.author.principal_id),
                "principal",
                decision.author.principal_id,
                Principal,
            )
            if approver != decision.author:
                raise PermissionDeniedError("approval durable principal binding drifted")
            if proposal.mandate_id != mandate.mandate_id:
                raise PermissionDeniedError("proposal names a different Mandate")
            if proposal.mandate_revision != mandate.revision:
                raise PermissionDeniedError("proposal Mandate revision is stale")
            authorize_effect_proposal(
                proposal,
                mandate,
                expected_mandate_revision=expected_mandate_revision,
            )
            authorization_decision = (
                decision
                if decision.choice is ApprovalChoice.APPROVE
                else replace(decision, choice=ApprovalChoice.APPROVE)
            )
            authorize_human_approval(
                proposal,
                authorization_decision,
                evaluated_at=occurred_at,
            )
            proposal_binding = f"{proposal.proposal_id}:{proposal.revision}"
            binding_replay = connection.execute(
                """
                SELECT 1 FROM replay_ledger
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND ledger_kind = 'proposal_approval' AND idempotency_key = ?
                """,
                (*_ns(namespace), proposal_binding),
            ).fetchone()
            if binding_replay is not None:
                raise ConflictError("proposal revision already has a durable decision")
            self._insert_record(connection, decision)
            for ledger_kind, key in (
                ("approval", decision.idempotency_key),
                ("proposal_approval", proposal_binding),
            ):
                connection.execute(
                    """
                    INSERT INTO replay_ledger(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      ledger_kind, idempotency_key, record_type, record_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'human_approval', ?, ?)
                    """,
                    (
                        SCHEMA_VERSION,
                        *_ns(namespace),
                        ledger_kind,
                        key,
                        decision.approval_decision_id,
                        datetime_to_z(occurred_at),
                    ),
                )
            if decision.choice is ApprovalChoice.REJECT:
                return decision, None, True
            attempt = EffectAttempt(
                namespace=namespace,
                effect_attempt_id=effect_attempt_id,
                proposal_id=proposal.proposal_id,
                proposal_revision=proposal.revision,
                approval_decision_id=decision.approval_decision_id,
                attempt_number=1,
                state=EffectAttemptState.PLANNED,
                actor=service_actor,
                correlation_id=proposal.correlation_id,
                causation_id=decision.approval_decision_id,
                occurred_at=occurred_at,
                revision=1,
            )
            self._insert_record(connection, attempt)
            try:
                connection.execute(
                    """
                    INSERT INTO outbox(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      outbox_id, proposal_id, approval_decision_id, effect_attempt_id,
                      effect_idempotency_key, state, attempt_number, maximum_attempts,
                      next_attempt_at, actor_principal_id, correlation_id, causation_id,
                      created_at, updated_at, revision
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 1, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        SCHEMA_VERSION,
                        *_ns(namespace),
                        outbox_id,
                        proposal.proposal_id,
                        decision.approval_decision_id,
                        attempt.effect_attempt_id,
                        proposal.constraints.idempotency_key,
                        proposal.constraints.maximum_attempts,
                        datetime_to_z(occurred_at),
                        service_actor.principal_id,
                        proposal.correlation_id,
                        decision.approval_decision_id,
                        datetime_to_z(occurred_at),
                        datetime_to_z(occurred_at),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO replay_ledger(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      ledger_kind, idempotency_key, record_type, record_id, created_at
                    ) VALUES (?, ?, ?, ?, 'effect', ?, 'effect_attempt', ?, ?)
                    """,
                    (
                        SCHEMA_VERSION,
                        *_ns(namespace),
                        proposal.constraints.idempotency_key,
                        attempt.effect_attempt_id,
                        datetime_to_z(occurred_at),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ConflictError("effect replay or outbox identity conflict") from exc
            return decision, attempt, True

    def _claim_outbox_state(
        self,
        namespace: Namespace,
        *,
        owner: str,
        now: datetime,
        lease_until: datetime,
        source_states: tuple[str, ...],
        target_state: str,
    ) -> OutboxClaim | None:
        placeholders = ",".join("?" for _ in source_states)
        with self._transaction() as connection:
            row = connection.execute(
                f"""
                SELECT * FROM outbox
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND state IN ({placeholders})
                  AND next_attempt_at <= ?
                  AND (lease_until IS NULL OR lease_until < ?)
                  AND attempt_number <= maximum_attempts
                ORDER BY next_attempt_at, outbox_id
                LIMIT 1
                """,
                (
                    *_ns(namespace),
                    *source_states,
                    datetime_to_z(now),
                    datetime_to_z(now),
                ),
            ).fetchone()
            if row is None:
                return None
            fencing = row["fencing_token"] + 1
            cursor = connection.execute(
                """
                UPDATE outbox
                SET state = ?, lease_owner = ?, lease_until = ?, fencing_token = ?,
                    updated_at = ?, revision = revision + 1
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND outbox_id = ? AND revision = ?
                """,
                (
                    target_state,
                    owner,
                    datetime_to_z(lease_until),
                    fencing,
                    datetime_to_z(now),
                    *_ns(namespace),
                    row["outbox_id"],
                    row["revision"],
                ),
            )
            if cursor.rowcount != 1:
                raise ConflictError("outbox optimistic claim conflict")
            return OutboxClaim(
                namespace=namespace,
                outbox_id=row["outbox_id"],
                proposal_id=row["proposal_id"],
                approval_decision_id=row["approval_decision_id"],
                effect_attempt_id=row["effect_attempt_id"],
                effect_idempotency_key=row["effect_idempotency_key"],
                attempt_number=row["attempt_number"],
                lease_owner=owner,
                lease_until=lease_until,
                fencing_token=fencing,
            )

    def claim_outbox(
        self,
        namespace: Namespace,
        *,
        owner: str,
        now: datetime,
        lease_until: datetime,
    ) -> OutboxClaim | None:
        return self._claim_outbox_state(
            namespace,
            owner=owner,
            now=now,
            lease_until=lease_until,
            source_states=("pending", "retry", "claimed"),
            target_state="claimed",
        )

    def claim_ambiguous(
        self,
        namespace: Namespace,
        *,
        owner: str,
        now: datetime,
        lease_until: datetime,
    ) -> OutboxClaim | None:
        return self._claim_outbox_state(
            namespace,
            owner=owner,
            now=now,
            lease_until=lease_until,
            source_states=("ambiguous", "ambiguous_claimed"),
            target_state="ambiguous_claimed",
        )

    def _require_outbox_claim(
        self,
        connection: sqlite3.Connection,
        claim: OutboxClaim,
        *,
        states: tuple[str, ...],
    ) -> sqlite3.Row:
        row = connection.execute(
            """
            SELECT * FROM outbox
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND outbox_id = ?
            """,
            (*_ns(claim.namespace), claim.outbox_id),
        ).fetchone()
        if (
            row is None
            or row["state"] not in states
            or row["lease_owner"] != claim.lease_owner
            or row["fencing_token"] != claim.fencing_token
            or row["proposal_id"] != claim.proposal_id
            or row["approval_decision_id"] != claim.approval_decision_id
            or row["effect_attempt_id"] != claim.effect_attempt_id
            or row["effect_idempotency_key"] != claim.effect_idempotency_key
            or row["attempt_number"] != claim.attempt_number
        ):
            raise ConflictError("stale or drifted outbox claim binding")
        return cast(sqlite3.Row, row)

    def load_dispatch_bundle(self, claim: OutboxClaim, *, mandate_id: str) -> DispatchBundle:
        row = self._require_outbox_claim(
            self._connection,
            claim,
            states=("claimed", "ambiguous_claimed"),
        )
        proposal = self._get_record(
            self._connection,
            claim.namespace,
            "effect_proposal",
            claim.proposal_id,
            EffectProposal,
        )
        approval = self._get_record(
            self._connection,
            claim.namespace,
            "human_approval",
            claim.approval_decision_id,
            HumanApprovalDecision,
        )
        attempt = self._get_record(
            self._connection,
            claim.namespace,
            "effect_attempt",
            claim.effect_attempt_id,
            EffectAttempt,
        )
        approver = self.get_principal(claim.namespace.tenant_id, approval.author.principal_id)
        mandate = self.get_mandate(claim.namespace, mandate_id)
        expected_attempt_state = (
            EffectAttemptState.PLANNED
            if row["state"] == "claimed"
            else EffectAttemptState.AMBIGUOUS
        )
        bindings_valid = (
            row["proposal_id"] == proposal.proposal_id == attempt.proposal_id
            and row["approval_decision_id"]
            == approval.approval_decision_id
            == attempt.approval_decision_id
            and row["effect_attempt_id"] == attempt.effect_attempt_id
            and row["attempt_number"] == attempt.attempt_number
            and row["maximum_attempts"] == proposal.constraints.maximum_attempts
            and row["effect_idempotency_key"] == proposal.constraints.idempotency_key
            and attempt.proposal_revision == proposal.revision
            and approval.proposal_id == proposal.proposal_id
            and approval.proposal_revision == proposal.revision
            and approval.proposal_payload_digest == proposal.payload_digest
            and approval.proposal_digest == proposal.proposal_digest
            and claim.proposal_id == row["proposal_id"]
            and claim.approval_decision_id == row["approval_decision_id"]
            and claim.effect_attempt_id == row["effect_attempt_id"]
            and claim.effect_idempotency_key == row["effect_idempotency_key"]
            and claim.attempt_number == row["attempt_number"]
            and proposal.mandate_id == mandate.mandate_id
            and proposal.mandate_revision == mandate.revision
            and approval.author == approver
            and approval.author.kind is PrincipalKind.HUMAN
            and attempt.actor.kind is PrincipalKind.SERVICE
            and attempt.state is expected_attempt_state
            and proposal.correlation_id
            == approval.correlation_id
            == attempt.correlation_id
            == row["correlation_id"]
            and approval.causation_id == proposal.proposal_id
            and attempt.causation_id == approval.approval_decision_id
            and row["causation_id"] == approval.approval_decision_id
            and row["actor_principal_id"] == attempt.actor.principal_id
        )
        if not bindings_valid:
            raise PermissionDeniedError("complete durable outbox effect binding drifted")
        return DispatchBundle(
            proposal=proposal,
            approval=approval,
            attempt=attempt,
            approver=approver,
            effect_idempotency_key=row["effect_idempotency_key"],
            maximum_attempts=row["maximum_attempts"],
        )

    def mark_dispatch_started(self, claim: OutboxClaim, *, occurred_at: datetime) -> EffectAttempt:
        with self._transaction() as connection:
            self._require_outbox_claim(connection, claim, states=("claimed",))
            attempt = self._get_record(
                connection,
                claim.namespace,
                "effect_attempt",
                claim.effect_attempt_id,
                EffectAttempt,
            )
            if attempt.state is not EffectAttemptState.PLANNED:
                raise ConflictError("effect attempt is not dispatchable")
            started = replace(
                attempt,
                state=EffectAttemptState.STARTED,
                occurred_at=occurred_at,
                revision=attempt.revision + 1,
            )
            self._update_record(connection, started, expected_revision=attempt.revision)
            connection.execute(
                """
                UPDATE outbox
                SET state = 'dispatching', updated_at = ?, revision = revision + 1
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND outbox_id = ? AND lease_owner = ? AND fencing_token = ?
                """,
                (
                    datetime_to_z(occurred_at),
                    *_ns(claim.namespace),
                    claim.outbox_id,
                    claim.lease_owner,
                    claim.fencing_token,
                ),
            )
            return started

    @staticmethod
    def _result_states(
        outcome: ChannelOutcomeKind,
    ) -> tuple[ActionResultState, EffectAttemptState, str]:
        mapping = {
            ChannelOutcomeKind.SUCCEEDED: (
                ActionResultState.SUCCEEDED,
                EffectAttemptState.SUCCEEDED,
                "completed",
            ),
            ChannelOutcomeKind.KNOWN_NOT_EXECUTED: (
                ActionResultState.NOT_EXECUTED,
                EffectAttemptState.FAILED,
                "terminal_failed",
            ),
            ChannelOutcomeKind.RETRYABLE_FAILURE: (
                ActionResultState.RETRYABLE_FAILURE,
                EffectAttemptState.FAILED,
                "terminal_failed",
            ),
            ChannelOutcomeKind.PERMANENT_FAILURE: (
                ActionResultState.PERMANENT_FAILURE,
                EffectAttemptState.FAILED,
                "terminal_failed",
            ),
            ChannelOutcomeKind.AMBIGUOUS: (
                ActionResultState.AMBIGUOUS,
                EffectAttemptState.AMBIGUOUS,
                "ambiguous",
            ),
        }
        return mapping[outcome]

    def _create_retry_attempt(
        self,
        connection: sqlite3.Connection,
        *,
        previous: EffectAttempt,
        next_attempt_id: str,
        actor: Principal,
        occurred_at: datetime,
    ) -> EffectAttempt:
        retry = EffectAttempt(
            namespace=previous.namespace,
            effect_attempt_id=next_attempt_id,
            proposal_id=previous.proposal_id,
            proposal_revision=previous.proposal_revision,
            approval_decision_id=previous.approval_decision_id,
            attempt_number=previous.attempt_number + 1,
            state=EffectAttemptState.PLANNED,
            actor=actor,
            correlation_id=previous.correlation_id,
            causation_id=previous.approval_decision_id,
            occurred_at=occurred_at,
            revision=1,
        )
        self._insert_record(connection, retry)
        return retry

    def _finalize_dispatch_in_transaction(
        self,
        connection: sqlite3.Connection,
        claim: OutboxClaim,
        *,
        outcome: ChannelOutcome,
        action_result_id: str,
        result_actor: Principal,
        occurred_at: datetime,
        next_attempt_id: str | None,
        required_state: str,
    ) -> ActionResult:
        row = self._require_outbox_claim(connection, claim, states=(required_state,))
        attempt = self._get_record(
            connection,
            claim.namespace,
            "effect_attempt",
            claim.effect_attempt_id,
            EffectAttempt,
        )
        result_state, attempt_state, outbox_state = self._result_states(outcome.kind)
        if required_state == "dispatching" and attempt.state is not EffectAttemptState.STARTED:
            raise ConflictError("dispatch outcome does not follow a started attempt")
        completed_attempt = replace(
            attempt,
            state=attempt_state,
            actor=result_actor,
            occurred_at=occurred_at,
            revision=attempt.revision + 1,
        )
        self._update_record(connection, completed_attempt, expected_revision=attempt.revision)
        result = ActionResult(
            namespace=claim.namespace,
            action_result_id=action_result_id,
            effect_attempt_id=attempt.effect_attempt_id,
            state=result_state,
            safe_projection=outcome.safe_projection,
            result_digest=outcome.result_digest,
            actor=result_actor,
            correlation_id=attempt.correlation_id,
            causation_id=attempt.effect_attempt_id,
            occurred_at=occurred_at,
            revision=1,
        )
        self._insert_record(connection, result)
        next_attempt = None
        if next_attempt_id is not None:
            if outcome.kind not in {
                ChannelOutcomeKind.KNOWN_NOT_EXECUTED,
                ChannelOutcomeKind.RETRYABLE_FAILURE,
            }:
                raise ConflictError("only confirmed-absent outcomes may be retried")
            if attempt.attempt_number >= row["maximum_attempts"]:
                raise ConflictError("effect retry would exceed its attempt limit")
            next_attempt = self._create_retry_attempt(
                connection,
                previous=attempt,
                next_attempt_id=next_attempt_id,
                actor=result_actor,
                occurred_at=occurred_at,
            )
            outbox_state = "retry"
        connection.execute(
            """
            UPDATE outbox
            SET state = ?, effect_attempt_id = ?, attempt_number = ?,
                next_attempt_at = ?, lease_owner = NULL, lease_until = NULL,
                last_outcome = ?, actor_principal_id = ?, updated_at = ?,
                revision = revision + 1
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND outbox_id = ? AND lease_owner = ? AND fencing_token = ?
            """,
            (
                outbox_state,
                next_attempt.effect_attempt_id if next_attempt else attempt.effect_attempt_id,
                next_attempt.attempt_number if next_attempt else attempt.attempt_number,
                datetime_to_z(occurred_at),
                outcome.kind.value,
                result_actor.principal_id,
                datetime_to_z(occurred_at),
                *_ns(claim.namespace),
                claim.outbox_id,
                claim.lease_owner,
                claim.fencing_token,
            ),
        )
        return result

    def finalize_dispatch(
        self,
        claim: OutboxClaim,
        *,
        outcome: ChannelOutcome,
        action_result_id: str,
        result_actor: Principal,
        occurred_at: datetime,
        next_attempt_id: str | None,
    ) -> ActionResult:
        with self._transaction() as connection:
            return self._finalize_dispatch_in_transaction(
                connection,
                claim,
                outcome=outcome,
                action_result_id=action_result_id,
                result_actor=result_actor,
                occurred_at=occurred_at,
                next_attempt_id=next_attempt_id,
                required_state="dispatching",
            )

    def recover_expired_dispatches(
        self,
        namespace: Namespace,
        *,
        now: datetime,
        result_actor: Principal,
        result_id: str,
    ) -> int:
        with self._transaction() as connection:
            row = connection.execute(
                """
                SELECT * FROM outbox
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND state = 'dispatching' AND lease_until < ?
                ORDER BY lease_until, outbox_id
                LIMIT 1
                """,
                (*_ns(namespace), datetime_to_z(now)),
            ).fetchone()
            if row is None:
                return 0
            claim = OutboxClaim(
                namespace=namespace,
                outbox_id=row["outbox_id"],
                proposal_id=row["proposal_id"],
                approval_decision_id=row["approval_decision_id"],
                effect_attempt_id=row["effect_attempt_id"],
                effect_idempotency_key=row["effect_idempotency_key"],
                attempt_number=row["attempt_number"],
                lease_owner=row["lease_owner"],
                lease_until=datetime_from_z(row["lease_until"]),
                fencing_token=row["fencing_token"],
            )
            synthetic = ChannelOutcome(
                kind=ChannelOutcomeKind.AMBIGUOUS,
                safe_projection=FrozenJsonObject.from_mapping(
                    {"outcome": "restart_recovery_ambiguous"}
                ),
                result_digest=_digest_text(f"restart-recovery\0{claim.effect_idempotency_key}"),
            )
            self._finalize_dispatch_in_transaction(
                connection,
                claim,
                outcome=synthetic,
                action_result_id=result_id,
                result_actor=result_actor,
                occurred_at=now,
                next_attempt_id=None,
                required_state="dispatching",
            )
            return 1

    def reconcile_ambiguous(
        self,
        claim: OutboxClaim,
        *,
        outcome: ReconciliationOutcome,
        action_result_id: str,
        result_actor: Principal,
        occurred_at: datetime,
        next_attempt_id: str | None,
    ) -> ActionResult | None:
        with self._transaction() as connection:
            row = self._require_outbox_claim(connection, claim, states=("ambiguous_claimed",))
            attempt = self._get_record(
                connection,
                claim.namespace,
                "effect_attempt",
                claim.effect_attempt_id,
                EffectAttempt,
            )
            if attempt.state is not EffectAttemptState.AMBIGUOUS:
                raise ConflictError("reconciliation requires an ambiguous attempt")
            if outcome.kind is ReconciliationKind.STILL_UNKNOWN:
                connection.execute(
                    """
                    UPDATE outbox
                    SET state = 'ambiguous', lease_owner = NULL, lease_until = NULL,
                        last_outcome = ?, updated_at = ?, revision = revision + 1
                    WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                      AND outbox_id = ? AND lease_owner = ? AND fencing_token = ?
                    """,
                    (
                        outcome.kind.value,
                        datetime_to_z(occurred_at),
                        *_ns(claim.namespace),
                        claim.outbox_id,
                        claim.lease_owner,
                        claim.fencing_token,
                    ),
                )
                return None
            result_state = (
                ActionResultState.SUCCEEDED
                if outcome.kind is ReconciliationKind.CONFIRMED_APPLIED
                else ActionResultState.NOT_EXECUTED
            )
            attempt_state = (
                EffectAttemptState.SUCCEEDED
                if outcome.kind is ReconciliationKind.CONFIRMED_APPLIED
                else EffectAttemptState.FAILED
            )
            resolved_attempt = replace(
                attempt,
                state=attempt_state,
                actor=result_actor,
                occurred_at=occurred_at,
                revision=attempt.revision + 1,
            )
            self._update_record(connection, resolved_attempt, expected_revision=attempt.revision)
            result = ActionResult(
                namespace=claim.namespace,
                action_result_id=action_result_id,
                effect_attempt_id=attempt.effect_attempt_id,
                state=result_state,
                safe_projection=outcome.safe_projection,
                result_digest=outcome.result_digest,
                actor=result_actor,
                correlation_id=attempt.correlation_id,
                causation_id=attempt.effect_attempt_id,
                occurred_at=occurred_at,
                revision=1,
            )
            self._insert_record(connection, result)
            next_attempt = None
            state = "completed"
            if outcome.kind is ReconciliationKind.CONFIRMED_ABSENT:
                state = "terminal_failed"
                if next_attempt_id is not None:
                    if attempt.attempt_number >= row["maximum_attempts"]:
                        raise ConflictError("reconciled retry exceeds the attempt limit")
                    next_attempt = self._create_retry_attempt(
                        connection,
                        previous=attempt,
                        next_attempt_id=next_attempt_id,
                        actor=result_actor,
                        occurred_at=occurred_at,
                    )
                    state = "retry"
            connection.execute(
                """
                UPDATE outbox
                SET state = ?, effect_attempt_id = ?, attempt_number = ?,
                    next_attempt_at = ?, lease_owner = NULL, lease_until = NULL,
                    last_outcome = ?, updated_at = ?, revision = revision + 1
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND outbox_id = ? AND lease_owner = ? AND fencing_token = ?
                """,
                (
                    state,
                    next_attempt.effect_attempt_id if next_attempt else attempt.effect_attempt_id,
                    next_attempt.attempt_number if next_attempt else attempt.attempt_number,
                    datetime_to_z(occurred_at),
                    outcome.kind.value,
                    datetime_to_z(occurred_at),
                    *_ns(claim.namespace),
                    claim.outbox_id,
                    claim.lease_owner,
                    claim.fencing_token,
                ),
            )
            return result
