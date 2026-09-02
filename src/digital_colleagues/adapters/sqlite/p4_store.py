# SPDX-License-Identifier: Apache-2.0

"""Additive P4 authentication and Studio operations over the P3 SQLite store."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from datetime import datetime

from digital_colleagues.adapters.sqlite.codec import from_storage_json
from digital_colleagues.adapters.sqlite.store import SQLiteRuntimeStore, _ns
from digital_colleagues.application.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from digital_colleagues.application.p4_contracts import (
    AuthenticatedSession,
    BootstrapRecord,
    EvaluationObservation,
    MutationReplay,
    ProposalCandidateObservation,
    ServiceRuntimeContext,
    StudioSnapshot,
)
from digital_colleagues.core.authority import Mandate, Profile
from digital_colleagues.core.common import SCHEMA_VERSION, FrozenJsonObject
from digital_colleagues.core.effects import (
    ActionResult,
    EffectAttempt,
    EffectProposal,
    HumanApprovalDecision,
)
from digital_colleagues.core.namespace import Namespace, NamespaceScope
from digital_colleagues.core.principals import HumanRole, Principal, PrincipalKind
from digital_colleagues.core.runtime import (
    AgendaItem,
    Decision,
    InputEvent,
    TimerOccurrence,
    WakeCycle,
)
from digital_colleagues.core.serialization import (
    contract_to_public_data,
    datetime_from_z,
    datetime_to_z,
)
from digital_colleagues.core.work import FiniteWork


class SQLiteP4Store(SQLiteRuntimeStore):
    def _bootstrap_from_row(self, row: sqlite3.Row) -> BootstrapRecord:
        return BootstrapRecord(
            tenant_id=row["tenant_id"],
            credential_id=row["credential_id"],
            token_digest=row["token_digest"],
            issued_at=datetime_from_z(row["issued_at"]),
            expires_at=datetime_from_z(row["expires_at"]),
            retrieved_at=(
                None if row["retrieved_at"] is None else datetime_from_z(row["retrieved_at"])
            ),
            consumed_at=(
                None if row["consumed_at"] is None else datetime_from_z(row["consumed_at"])
            ),
            revision=row["revision"],
            schema_version=row["schema_version"],
        )

    def get_bootstrap(self, tenant_id: str) -> BootstrapRecord | None:
        row = self._connection.execute(
            """
            SELECT * FROM p4_bootstrap_credentials
            WHERE tenant_id = ? AND namespace_scope = 'tenant' AND namespace_scope_id = ''
              AND credential_id = 'bootstrap-initial'
            """,
            (tenant_id,),
        ).fetchone()
        return None if row is None else self._bootstrap_from_row(row)

    def create_bootstrap(self, record: BootstrapRecord) -> bool:
        with self._transaction() as connection:
            exists = connection.execute(
                """
                SELECT 1 FROM p4_bootstrap_credentials
                WHERE tenant_id = ? AND credential_id = 'bootstrap-initial'
                """,
                (record.tenant_id,),
            ).fetchone()
            if exists is not None:
                return False
            connection.execute(
                """
                INSERT INTO p4_bootstrap_credentials(
                  schema_version, tenant_id, namespace_scope, namespace_scope_id,
                  credential_id, token_digest, issued_at, expires_at, revision
                ) VALUES (?, ?, 'tenant', '', ?, ?, ?, ?, ?)
                """,
                (
                    record.schema_version,
                    record.tenant_id,
                    record.credential_id,
                    record.token_digest,
                    datetime_to_z(record.issued_at),
                    datetime_to_z(record.expires_at),
                    record.revision,
                ),
            )
        return True

    def claim_bootstrap_retrieval(
        self, *, tenant_id: str, token_digest: str, occurred_at: datetime
    ) -> BootstrapRecord:
        with self._transaction() as connection:
            row = connection.execute(
                """
                SELECT * FROM p4_bootstrap_credentials
                WHERE tenant_id = ? AND token_digest = ?
                """,
                (tenant_id, token_digest),
            ).fetchone()
            if row is None:
                raise PermissionDeniedError("bootstrap retrieval was refused")
            record = self._bootstrap_from_row(row)
            if record.retrieved_at is not None or record.consumed_at is not None:
                raise ConflictError("bootstrap token has already been retrieved")
            if occurred_at >= record.expires_at:
                raise PermissionDeniedError("bootstrap token has expired")
            updated = connection.execute(
                """
                UPDATE p4_bootstrap_credentials
                SET retrieved_at = ?, revision = revision + 1
                WHERE tenant_id = ? AND credential_id = ? AND revision = ?
                  AND retrieved_at IS NULL AND consumed_at IS NULL
                """,
                (
                    datetime_to_z(occurred_at),
                    tenant_id,
                    record.credential_id,
                    record.revision,
                ),
            )
            if updated.rowcount != 1:
                raise ConflictError("bootstrap retrieval lost its atomic claim")
        claimed = self.get_bootstrap(tenant_id)
        if claimed is None:
            raise ConflictError("bootstrap retrieval state disappeared")
        return claimed

    def consume_bootstrap(
        self,
        *,
        tenant_id: str,
        token_digest: str,
        principal: Principal,
        session: AuthenticatedSession,
        occurred_at: datetime,
    ) -> AuthenticatedSession:
        if principal.kind is not PrincipalKind.HUMAN or principal.roles != (
            HumanRole.TENANT_ADMIN,
        ):
            raise PermissionDeniedError("bootstrap may create only the first tenant Admin")
        if principal.namespace.tenant_id != tenant_id or session.principal != principal:
            raise PermissionDeniedError("bootstrap authority binding crossed tenant or principal")
        with self._transaction() as connection:
            row = connection.execute(
                """
                SELECT * FROM p4_bootstrap_credentials
                WHERE tenant_id = ? AND token_digest = ?
                """,
                (tenant_id, token_digest),
            ).fetchone()
            if row is None:
                raise PermissionDeniedError("bootstrap exchange was refused")
            bootstrap = self._bootstrap_from_row(row)
            if bootstrap.retrieved_at is None:
                raise PermissionDeniedError("bootstrap token was not retrieved locally")
            if bootstrap.consumed_at is not None:
                raise ConflictError("bootstrap token replay was refused")
            if occurred_at >= bootstrap.expires_at:
                raise PermissionDeniedError("bootstrap token has expired")
            human_count = connection.execute(
                """
                SELECT COUNT(*) AS count FROM domain_records
                WHERE tenant_id = ? AND record_type = 'principal'
                  AND payload_json LIKE '%\"kind\":\"human\"%'
                """,
                (tenant_id,),
            ).fetchone()["count"]
            if human_count != 0:
                raise ConflictError("the first durable human principal already exists")
            self._insert_record(
                connection,
                principal,
                actor=principal,
                correlation_id="correlation:bootstrap",
                causation_id=bootstrap.credential_id,
                occurred_at=occurred_at,
            )
            updated = connection.execute(
                """
                UPDATE p4_bootstrap_credentials
                SET consumed_at = ?, revision = revision + 1
                WHERE tenant_id = ? AND credential_id = ? AND revision = ?
                  AND consumed_at IS NULL
                """,
                (
                    datetime_to_z(occurred_at),
                    tenant_id,
                    bootstrap.credential_id,
                    bootstrap.revision,
                ),
            )
            if updated.rowcount != 1:
                raise ConflictError("bootstrap exchange lost its atomic claim")
            assert session.created_at is not None and session.expires_at is not None
            connection.execute(
                """
                INSERT INTO p4_sessions(
                  schema_version, tenant_id, namespace_scope, namespace_scope_id,
                  session_id, principal_id, credential_digest, csrf_digest,
                  active_colleague_id, created_at, expires_at, revision
                ) VALUES (?, ?, 'principal', ?, ?, ?, ?, ?, NULL, ?, ?, 1)
                """,
                (
                    session.schema_version,
                    tenant_id,
                    principal.principal_id,
                    session.session_id,
                    principal.principal_id,
                    session.credential_digest,
                    session.csrf_digest,
                    datetime_to_z(session.created_at),
                    datetime_to_z(session.expires_at),
                ),
            )
        return session

    def _session_from_row(self, row: sqlite3.Row) -> AuthenticatedSession:
        principal = self._get_record(
            self._connection,
            Namespace.principal(row["tenant_id"], row["principal_id"]),
            "principal",
            row["principal_id"],
            Principal,
        )
        available = set(row.keys())
        return AuthenticatedSession(
            tenant_id=row["tenant_id"],
            session_id=row["session_id"],
            principal=principal,
            credential_digest=row["credential_digest"],
            csrf_digest=row["csrf_digest"],
            active_colleague_id=row["active_colleague_id"],
            created_at=datetime_from_z(row["created_at"]),
            expires_at=datetime_from_z(row["expires_at"]),
            revision=row["revision"],
            role_revision=row["role_revision"] if "role_revision" in available else 1,
            membership_revision=(
                row["membership_revision"] if "membership_revision" in available else 1
            ),
            schema_version=row["schema_version"],
        )

    def get_session(
        self, *, credential_digest: str, evaluated_at: datetime
    ) -> AuthenticatedSession:
        row = self._connection.execute(
            """
            SELECT * FROM p4_sessions
            WHERE credential_digest = ? AND revoked_at IS NULL
            """,
            (credential_digest,),
        ).fetchone()
        if row is None:
            raise PermissionDeniedError("authenticated session was refused")
        session = self._session_from_row(row)
        assert session.expires_at is not None
        if evaluated_at >= session.expires_at:
            raise PermissionDeniedError("authenticated session has expired")
        return session

    def set_active_colleague(
        self, *, session: AuthenticatedSession, colleague_id: str, occurred_at: datetime
    ) -> AuthenticatedSession:
        del occurred_at
        namespace = Namespace.colleague(session.tenant_id, colleague_id)
        exists = self._connection.execute(
            """
            SELECT 1 FROM domain_records
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND record_type = 'profile'
            """,
            _ns(namespace),
        ).fetchone()
        if exists is None:
            raise NotFoundError("active colleague namespace was not found")
        with self._transaction() as connection:
            updated = connection.execute(
                """
                UPDATE p4_sessions SET active_colleague_id = ?, revision = revision + 1
                WHERE tenant_id = ? AND namespace_scope = 'principal'
                  AND namespace_scope_id = ? AND session_id = ? AND revision = ?
                """,
                (
                    colleague_id,
                    session.tenant_id,
                    session.principal.principal_id,
                    session.session_id,
                    session.revision,
                ),
            )
            if updated.rowcount != 1:
                raise ConflictError("session namespace binding is stale")
        return replace(session, active_colleague_id=colleague_id, revision=session.revision + 1)

    def get_mutation_replay(
        self, *, session: AuthenticatedSession, action: str, idempotency_key: str
    ) -> MutationReplay | None:
        row = self._connection.execute(
            """
            SELECT request_digest, result_json FROM p4_mutation_replay
            WHERE tenant_id = ? AND namespace_scope = 'principal' AND namespace_scope_id = ?
              AND action = ? AND idempotency_key = ?
            """,
            (session.tenant_id, session.principal.principal_id, action, idempotency_key),
        ).fetchone()
        if row is None:
            return None
        raw = json.loads(row["result_json"])
        if not isinstance(raw, dict):
            raise ConflictError("mutation replay result shape is invalid")
        return MutationReplay(row["request_digest"], FrozenJsonObject.from_mapping(raw))

    def record_mutation_replay(
        self,
        *,
        session: AuthenticatedSession,
        action: str,
        idempotency_key: str,
        replay: MutationReplay,
        occurred_at: datetime,
    ) -> None:
        with self._transaction() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO p4_mutation_replay(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      session_id, action, idempotency_key, request_digest, result_json, created_at
                    ) VALUES (?, ?, 'principal', ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        SCHEMA_VERSION,
                        session.tenant_id,
                        session.principal.principal_id,
                        session.session_id,
                        action,
                        idempotency_key,
                        replay.request_digest,
                        json.dumps(
                            contract_to_public_data(replay.result),
                            ensure_ascii=False,
                            separators=(",", ":"),
                            sort_keys=True,
                        ),
                        datetime_to_z(occurred_at),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ConflictError("duplicate mutation replay identity") from exc

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
        return True

    def _authorize_work_assignment(self, connection: sqlite3.Connection, work: FiniteWork) -> None:
        del connection, work

    def assign_work(self, work: FiniteWork, *, idempotency_key: str) -> tuple[FiniteWork, bool]:
        with self._transaction() as connection:
            self._authorize_work_assignment(connection, work)
            replay = connection.execute(
                """
                SELECT record_id FROM replay_ledger
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND ledger_kind = 'p4_work' AND idempotency_key = ?
                """,
                (*_ns(work.namespace), idempotency_key),
            ).fetchone()
            if replay is not None:
                existing = self._get_record(
                    connection, work.namespace, "finite_work", replay["record_id"], FiniteWork
                )
                normalized = replace(
                    work,
                    created_at=existing.created_at,
                    updated_at=existing.updated_at,
                )
                if normalized != existing:
                    raise ConflictError("work idempotency replay drifted")
                return existing, False
            mandate = self._get_record(
                connection, work.namespace, "mandate", work.mandate_id, Mandate
            )
            if mandate.revision != work.mandate_revision:
                raise PermissionDeniedError("finite work Mandate revision is stale")
            if not set(work.responsibility_ids).issubset(
                {item.responsibility_id for item in mandate.responsibilities}
            ):
                raise PermissionDeniedError("finite work responsibility is outside the Mandate")
            self._insert_record(connection, work)
            connection.execute(
                """
                INSERT INTO replay_ledger(
                  schema_version, tenant_id, namespace_scope, namespace_scope_id,
                  ledger_kind, idempotency_key, record_type, record_id, created_at
                ) VALUES (?, ?, ?, ?, 'p4_work', ?, 'finite_work', ?, ?)
                """,
                (
                    SCHEMA_VERSION,
                    *_ns(work.namespace),
                    idempotency_key,
                    work.work_id,
                    datetime_to_z(work.created_at),
                ),
            )
        return work, True

    def list_record_payloads(self, namespace: Namespace, record_type: str) -> tuple[str, ...]:
        rows = self._connection.execute(
            """
            SELECT payload_json FROM domain_records
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND record_type = ? ORDER BY record_id
            """,
            (*_ns(namespace), record_type),
        ).fetchall()
        return tuple(row["payload_json"] for row in rows)

    def first_principal(self, tenant_id: str, kind: PrincipalKind) -> Principal:
        rows = self._connection.execute(
            """
            SELECT payload_json FROM domain_records
            WHERE tenant_id = ? AND record_type = 'principal' ORDER BY record_id
            """,
            (tenant_id,),
        ).fetchall()
        for row in rows:
            principal = from_storage_json(row["payload_json"], Principal)
            if principal.kind is kind:
                return principal
        raise NotFoundError("required durable principal kind was not found")

    def pending_namespaces(self) -> tuple[Namespace, ...]:
        rows = self._connection.execute(
            """
            SELECT tenant_id, namespace_scope, namespace_scope_id FROM triggers
            WHERE state = 'pending'
            UNION
            SELECT tenant_id, namespace_scope, namespace_scope_id FROM timer_triggers
            WHERE state = 'pending'
            UNION
            SELECT tenant_id, namespace_scope, namespace_scope_id FROM outbox
            WHERE state IN ('pending', 'retry')
            ORDER BY tenant_id, namespace_scope, namespace_scope_id
            """
        ).fetchall()
        return tuple(
            Namespace(
                tenant_id=row["tenant_id"],
                scope=NamespaceScope(row["namespace_scope"]),
                scope_id=row["namespace_scope_id"],
            )
            for row in rows
        )

    def resolve_runtime_context(
        self,
        *,
        namespace: Namespace,
        model_principal_id: str,
        service_principal_id: str,
        mandate_id: str,
    ) -> ServiceRuntimeContext:
        namespace.require_colleague()
        model = self.get_principal(namespace.tenant_id, model_principal_id)
        service = self.get_principal(namespace.tenant_id, service_principal_id)
        mandate = self.get_mandate(namespace, mandate_id)
        if model.kind is not PrincipalKind.MODEL or service.kind is not PrincipalKind.SERVICE:
            raise PermissionDeniedError("runtime principal kind binding was refused")
        if model.principal_id != model_principal_id or service.principal_id != service_principal_id:
            raise PermissionDeniedError("runtime principal identity binding was refused")
        return ServiceRuntimeContext(
            namespace=namespace,
            model_principal=model,
            service_principal=service,
            mandate_id=mandate.mandate_id,
            mandate_revision=mandate.revision,
        )

    @staticmethod
    def _evaluation_observation_from_row(row: sqlite3.Row) -> EvaluationObservation:
        return EvaluationObservation(
            namespace=Namespace.colleague(row["tenant_id"], row["namespace_scope_id"]),
            observation_id=row["observation_id"],
            metric=row["metric"],
            value=row["value"],
            opportunity_id=row["opportunity_id"],
            source=row["source"],
            evidence_class=row["evidence_class"],
            scenario_version=row["scenario_version"],
            policy_version=row["policy_version"],
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            observed_at=datetime_from_z(row["observed_at"]),
            revision=row["revision"],
            schema_version=row["schema_version"],
        )

    def record_evaluation_observation(self, observation: EvaluationObservation) -> bool:
        with self._transaction() as connection:
            existing = connection.execute(
                """
                SELECT * FROM p4_metric_observations
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND observation_id = ?
                """,
                (*_ns(observation.namespace), observation.observation_id),
            ).fetchone()
            if existing is not None:
                if self._evaluation_observation_from_row(existing) != observation:
                    raise ConflictError("evaluation observation identity was rebound")
                return False
            try:
                connection.execute(
                    """
                    INSERT INTO p4_metric_observations(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      observation_id, metric, value, opportunity_id, source, evidence_class,
                      scenario_version, policy_version, correlation_id, causation_id,
                      observed_at, revision
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        observation.schema_version,
                        *_ns(observation.namespace),
                        observation.observation_id,
                        observation.metric,
                        observation.value,
                        observation.opportunity_id,
                        observation.source,
                        observation.evidence_class,
                        observation.scenario_version,
                        observation.policy_version,
                        observation.correlation_id,
                        observation.causation_id,
                        datetime_to_z(observation.observed_at),
                        observation.revision,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ConflictError("evaluation opportunity was already observed") from exc
        return True

    def list_evaluation_observations(
        self, namespace: Namespace
    ) -> tuple[EvaluationObservation, ...]:
        rows = self._connection.execute(
            """
            SELECT * FROM p4_metric_observations
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
            ORDER BY metric, observed_at, observation_id
            """,
            _ns(namespace),
        ).fetchall()
        return tuple(self._evaluation_observation_from_row(row) for row in rows)

    @staticmethod
    def _proposal_candidate_from_row(row: sqlite3.Row) -> ProposalCandidateObservation:
        return ProposalCandidateObservation(
            namespace=Namespace.colleague(row["tenant_id"], row["namespace_scope_id"]),
            observation_id=row["observation_id"],
            candidate_id=row["candidate_id"],
            boundary_id=row["boundary_id"],
            outcome=row["outcome"],
            source=row["source"],
            evidence_class=row["evidence_class"],
            scenario_version=row["scenario_version"],
            policy_version=row["policy_version"],
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            observed_at=datetime_from_z(row["observed_at"]),
            revision=row["revision"],
            schema_version=row["schema_version"],
        )

    def record_proposal_candidate_observation(
        self, observation: ProposalCandidateObservation
    ) -> bool:
        with self._transaction() as connection:
            existing = connection.execute(
                """
                SELECT * FROM p4_proposal_candidate_observations
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND candidate_id = ?
                """,
                (*_ns(observation.namespace), observation.candidate_id),
            ).fetchone()
            if existing is not None:
                if self._proposal_candidate_from_row(existing) != observation:
                    raise ConflictError("proposal candidate observation was rebound")
                return False
            connection.execute(
                """
                INSERT INTO p4_proposal_candidate_observations(
                  schema_version, tenant_id, namespace_scope, namespace_scope_id,
                  observation_id, candidate_id, boundary_id, outcome, source,
                  evidence_class, scenario_version, policy_version, correlation_id,
                  causation_id, observed_at, revision
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    observation.schema_version,
                    *_ns(observation.namespace),
                    observation.observation_id,
                    observation.candidate_id,
                    observation.boundary_id,
                    observation.outcome,
                    observation.source,
                    observation.evidence_class,
                    observation.scenario_version,
                    observation.policy_version,
                    observation.correlation_id,
                    observation.causation_id,
                    datetime_to_z(observation.observed_at),
                    observation.revision,
                ),
            )
        return True

    def list_proposal_candidate_observations(
        self, namespace: Namespace
    ) -> tuple[ProposalCandidateObservation, ...]:
        rows = self._connection.execute(
            """
            SELECT * FROM p4_proposal_candidate_observations
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
            ORDER BY candidate_id
            """,
            _ns(namespace),
        ).fetchall()
        return tuple(self._proposal_candidate_from_row(row) for row in rows)

    def proposal_candidate_counts(self, namespace: Namespace) -> tuple[int, int, tuple[str, ...]]:
        observations = self.list_proposal_candidate_observations(namespace)
        escaped = 0
        for observation in observations:
            proposal = self._connection.execute(
                """
                SELECT 1 FROM domain_records
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND record_type = 'effect_proposal' AND record_id = ?
                """,
                (*_ns(namespace), observation.candidate_id),
            ).fetchone()
            escaped += proposal is not None
        return (
            len(observations),
            escaped,
            tuple(sorted({item.correlation_id for item in observations})),
        )

    def _records[RecordT](
        self, namespace: Namespace, record_type: str, expected: type[RecordT]
    ) -> tuple[RecordT, ...]:
        return tuple(
            from_storage_json(value, expected)
            for value in self.list_record_payloads(namespace, record_type)
        )

    def studio_snapshot(self, namespace: Namespace) -> StudioSnapshot:
        profiles = self._records(namespace, "profile", Profile)
        mandates = self._records(namespace, "mandate", Mandate)
        if len(profiles) != 1 or len(mandates) != 1:
            raise NotFoundError("initial colleague snapshot is incomplete")
        return StudioSnapshot(
            namespace=namespace,
            profile=profiles[0],
            mandate=mandates[0],
            work=self._records(namespace, "finite_work", FiniteWork),
            events=self._records(namespace, "input_event", InputEvent),
            timers=self._records(namespace, "timer_occurrence", TimerOccurrence),
            wakes=self._records(namespace, "wake_cycle", WakeCycle),
            agenda=self._records(namespace, "agenda_item", AgendaItem),
            decisions=self._records(namespace, "decision", Decision),
            proposals=self._records(namespace, "effect_proposal", EffectProposal),
            approvals=self._records(namespace, "human_approval", HumanApprovalDecision),
            attempts=self._records(namespace, "effect_attempt", EffectAttempt),
            results=self._records(namespace, "action_result", ActionResult),
        )
