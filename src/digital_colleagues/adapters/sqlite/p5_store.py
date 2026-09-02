# SPDX-License-Identifier: Apache-2.0

"""Additive SQLite persistence for P5 drafts and deterministic colleague policy."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import replace
from datetime import datetime

from digital_colleagues.adapters.sqlite.codec import from_storage_json, to_storage_json
from digital_colleagues.adapters.sqlite.p4_store import SQLiteP4Store
from digital_colleagues.adapters.sqlite.store import _ns
from digital_colleagues.application.contracts import (
    AgendaClaim,
    SemanticDecision,
    SemanticOutcome,
)
from digital_colleagues.application.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ReplayConflictError,
    StaleConflictError,
    ValidationError,
)
from digital_colleagues.application.p4_contracts import ServiceRuntimeContext
from digital_colleagues.application.p5_contracts import (
    ConfirmationResult,
    P5StudioSnapshot,
    PolicyAdmission,
)
from digital_colleagues.core.authority import Mandate, Profile
from digital_colleagues.core.builder import ColleagueDraft, DraftLifecycle
from digital_colleagues.core.common import SCHEMA_VERSION, FrozenJsonObject
from digital_colleagues.core.effects import ActionResult, ActionResultState, EffectProposal
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.policy import (
    ColleaguePolicy,
    DurableTriggerKind,
    EscalationCondition,
    EscalationRecord,
    OutsideHoursOutcome,
    PolicyEnforcementRecord,
    PolicyOutcomeKind,
    PolicyRunState,
    PolicyStage,
    PolicyStatus,
    ProactivityMode,
    StopCondition,
)
from digital_colleagues.core.principals import HumanRole, Principal, PrincipalKind
from digital_colleagues.core.runtime import DecisionKind, WakeCycle
from digital_colleagues.core.serialization import (
    contract_to_public_data,
    datetime_from_z,
    datetime_to_z,
)
from digital_colleagues.core.work import FiniteWork, WorkState
from digital_colleagues.governance.policy import budget_bucket_start, within_working_hours


def _safe_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


class SQLiteP5Store(SQLiteP4Store):
    def _require_admin(self, connection: sqlite3.Connection, actor: Principal) -> None:
        if actor.kind is not PrincipalKind.HUMAN or HumanRole.TENANT_ADMIN not in actor.roles:
            raise PermissionDeniedError("P5 builder mutation requires a durable tenant Admin")
        durable = self._get_record(
            connection,
            actor.namespace,
            "principal",
            actor.principal_id,
            Principal,
        )
        if durable != actor:
            raise PermissionDeniedError("P5 builder actor binding drifted")

    def active_configuration(self, namespace: Namespace) -> tuple[Profile, Mandate]:
        profiles = self._records(namespace, "profile", Profile)
        mandates = self._records(namespace, "mandate", Mandate)
        if len(profiles) != 1 or len(mandates) != 1:
            raise NotFoundError("active colleague configuration is incomplete")
        return profiles[0], mandates[0]

    def get_active_policy(self, namespace: Namespace) -> ColleaguePolicy | None:
        policies = self._records(namespace, "colleague_policy", ColleaguePolicy)
        if len(policies) > 1:
            raise ConflictError("multiple active colleague policies were refused")
        return None if not policies else policies[0]

    def get_runtime_policy_state(
        self, namespace: Namespace
    ) -> tuple[ColleaguePolicy | None, PolicyRunState | None]:
        policy = self.get_active_policy(namespace)
        row = self._connection.execute(
            """
            SELECT state FROM p5_run_states
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
            """,
            _ns(namespace),
        ).fetchone()
        if row is not None:
            return policy, PolicyRunState(row["state"])
        return policy, None if policy is None else policy.run_state

    @staticmethod
    def _draft_from_row(row: sqlite3.Row) -> ColleagueDraft:
        draft = from_storage_json(row["payload_json"], ColleagueDraft)
        if (
            draft.revision != row["revision"]
            or draft.state.value != row["state"]
            or draft.canonical_digest != row["canonical_digest"]
            or draft.base_profile_revision != row["base_profile_revision"]
            or draft.base_mandate_revision != row["base_mandate_revision"]
            or draft.base_policy_revision != row["base_policy_revision"]
        ):
            raise ConflictError("draft indexed identity drifted")
        return draft

    def get_draft(self, namespace: Namespace, draft_id: str) -> ColleagueDraft:
        row = self._connection.execute(
            """
            SELECT * FROM p5_colleague_drafts
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND draft_id = ?
            """,
            (*_ns(namespace), draft_id),
        ).fetchone()
        if row is None:
            raise NotFoundError("namespaced colleague draft was not found")
        return self._draft_from_row(row)

    def list_drafts(self, namespace: Namespace) -> tuple[ColleagueDraft, ...]:
        rows = self._connection.execute(
            """
            SELECT * FROM p5_colleague_drafts
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
            ORDER BY created_at, draft_id
            """,
            _ns(namespace),
        ).fetchall()
        return tuple(self._draft_from_row(row) for row in rows)

    def _insert_draft_audit(
        self,
        connection: sqlite3.Connection,
        *,
        draft: ColleagueDraft,
        action: str,
        actor: Principal,
        occurred_at: datetime,
    ) -> None:
        serialized = to_storage_json(draft)
        payload_digest = "sha256:" + hashlib.sha256(serialized.encode()).hexdigest()
        audit_id = (
            "draft-audit:"
            + hashlib.sha256(f"{draft.draft_id}\0{draft.revision}\0{action}".encode()).hexdigest()[
                :32
            ]
        )
        safe_projection = {
            "draft_id": draft.draft_id,
            "draft_revision": draft.revision,
            "state": draft.state.value,
            "base_profile_id": draft.base_profile_id,
            "base_profile_revision": draft.base_profile_revision,
            "base_mandate_id": draft.base_mandate_id,
            "base_mandate_revision": draft.base_mandate_revision,
            "base_policy_id": draft.base_policy_id,
            "base_policy_revision": draft.base_policy_revision,
            "canonical_digest": draft.canonical_digest,
            "default_paths": [item.path for item in draft.explicit_defaults],
            "diff": [
                {
                    "section": item.section.value,
                    "path": item.path,
                    "classification": item.classification.value,
                    "authoritative": item.authoritative,
                }
                for item in draft.diff
            ],
        }
        connection.execute(
            """
            INSERT INTO p5_draft_audit(
              schema_version, tenant_id, namespace_scope, namespace_scope_id,
              audit_id, draft_id, draft_revision, state, action, actor_principal_id,
              correlation_id, causation_id, occurred_at, payload_digest, safe_projection_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SCHEMA_VERSION,
                *_ns(draft.namespace),
                audit_id,
                draft.draft_id,
                draft.revision,
                draft.state.value,
                action,
                actor.principal_id,
                draft.correlation_id,
                draft.causation_id,
                datetime_to_z(occurred_at),
                payload_digest,
                _safe_json(safe_projection),
            ),
        )

    def _write_draft(self, connection: sqlite3.Connection, draft: ColleagueDraft) -> None:
        connection.execute(
            """
            UPDATE p5_colleague_drafts
            SET revision = ?, base_profile_revision = ?, base_mandate_revision = ?,
                base_policy_revision = ?, state = ?, canonical_digest = ?, payload_json = ?,
                updated_at = ?
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND draft_id = ?
            """,
            (
                draft.revision,
                draft.base_profile_revision,
                draft.base_mandate_revision,
                draft.base_policy_revision,
                draft.state.value,
                draft.canonical_digest,
                to_storage_json(draft),
                datetime_to_z(draft.updated_at),
                *_ns(draft.namespace),
                draft.draft_id,
            ),
        )

    def _current_revisions(
        self, connection: sqlite3.Connection, draft: ColleagueDraft
    ) -> tuple[int, int, int]:
        profile = self._get_record(
            connection,
            draft.namespace,
            "profile",
            draft.proposed_profile.profile_id,
            Profile,
        )
        mandate = self._get_record(
            connection,
            draft.namespace,
            "mandate",
            draft.proposed_mandate.mandate_id,
            Mandate,
        )
        policy_row = connection.execute(
            """
            SELECT payload_json FROM domain_records
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND record_type = 'colleague_policy' AND record_id = ?
            """,
            (*_ns(draft.namespace), draft.proposed_policy.policy_id),
        ).fetchone()
        policy_revision = (
            0
            if policy_row is None
            else from_storage_json(policy_row["payload_json"], ColleaguePolicy).revision
        )
        return profile.revision, mandate.revision, policy_revision

    def _mark_stale(
        self,
        connection: sqlite3.Connection,
        draft: ColleagueDraft,
        *,
        actor: Principal,
        occurred_at: datetime,
    ) -> ColleagueDraft:
        stale = replace(draft, state=DraftLifecycle.STALE, updated_at=occurred_at)
        self._write_draft(connection, stale)
        self._insert_draft_audit(
            connection,
            draft=stale,
            action="stale_refused",
            actor=actor,
            occurred_at=occurred_at,
        )
        return stale

    def create_draft(self, draft: ColleagueDraft) -> tuple[ColleagueDraft, bool]:
        with self._transaction() as connection:
            self._require_admin(connection, draft.author)
            existing = connection.execute(
                """
                SELECT * FROM p5_colleague_drafts
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND draft_id = ?
                """,
                (*_ns(draft.namespace), draft.draft_id),
            ).fetchone()
            if existing is not None:
                return self._draft_from_row(existing), False
            current = self._current_revisions(connection, draft)
            expected = (
                draft.base_profile_revision,
                draft.base_mandate_revision,
                draft.base_policy_revision,
            )
            if current != expected:
                raise StaleConflictError("draft base revisions are stale")
            connection.execute(
                """
                INSERT INTO p5_colleague_drafts(
                  schema_version, tenant_id, namespace_scope, namespace_scope_id,
                  draft_id, revision, base_profile_revision, base_mandate_revision,
                  base_policy_revision, state, canonical_digest, payload_json,
                  author_principal_id, created_at, updated_at, correlation_id, causation_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    draft.schema_version,
                    *_ns(draft.namespace),
                    draft.draft_id,
                    draft.revision,
                    draft.base_profile_revision,
                    draft.base_mandate_revision,
                    draft.base_policy_revision,
                    draft.state.value,
                    draft.canonical_digest,
                    to_storage_json(draft),
                    draft.author.principal_id,
                    datetime_to_z(draft.created_at),
                    datetime_to_z(draft.updated_at),
                    draft.correlation_id,
                    draft.causation_id,
                ),
            )
            self._insert_draft_audit(
                connection,
                draft=draft,
                action="created",
                actor=draft.author,
                occurred_at=draft.created_at,
            )
        return draft, True

    def update_draft(self, draft: ColleagueDraft, *, expected_revision: int) -> ColleagueDraft:
        stale = False
        with self._transaction() as connection:
            self._require_admin(connection, draft.author)
            row = connection.execute(
                """
                SELECT * FROM p5_colleague_drafts
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND draft_id = ?
                """,
                (*_ns(draft.namespace), draft.draft_id),
            ).fetchone()
            if row is None:
                raise NotFoundError("namespaced colleague draft was not found")
            existing = self._draft_from_row(row)
            if existing.revision != expected_revision or draft.revision != expected_revision + 1:
                raise StaleConflictError("draft optimistic revision conflict")
            if existing.state not in {DraftLifecycle.DRAFT, DraftLifecycle.REVIEWABLE}:
                raise StaleConflictError("terminal colleague draft cannot be updated")
            if (
                existing.base_profile_revision,
                existing.base_mandate_revision,
                existing.base_policy_revision,
            ) != (
                draft.base_profile_revision,
                draft.base_mandate_revision,
                draft.base_policy_revision,
            ):
                raise StaleConflictError("draft base identity cannot be rebound")
            current = self._current_revisions(connection, existing)
            expected = (
                existing.base_profile_revision,
                existing.base_mandate_revision,
                existing.base_policy_revision,
            )
            if current != expected:
                self._mark_stale(
                    connection,
                    existing,
                    actor=draft.author,
                    occurred_at=draft.updated_at,
                )
                stale = True
            else:
                self._write_draft(connection, draft)
                self._insert_draft_audit(
                    connection,
                    draft=draft,
                    action="updated",
                    actor=draft.author,
                    occurred_at=draft.updated_at,
                )
        if stale:
            raise StaleConflictError("draft base revisions are stale")
        return draft

    def _transition_draft(
        self,
        *,
        namespace: Namespace,
        draft_id: str,
        expected_revision: int,
        actor: Principal,
        occurred_at: datetime,
        target: DraftLifecycle,
        action: str,
    ) -> ColleagueDraft:
        stale = False
        result: ColleagueDraft | None = None
        with self._transaction() as connection:
            self._require_admin(connection, actor)
            row = connection.execute(
                """
                SELECT * FROM p5_colleague_drafts
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND draft_id = ?
                """,
                (*_ns(namespace), draft_id),
            ).fetchone()
            if row is None:
                raise NotFoundError("namespaced colleague draft was not found")
            draft = self._draft_from_row(row)
            if draft.revision != expected_revision:
                raise StaleConflictError("draft optimistic revision conflict")
            if target is DraftLifecycle.REVIEWABLE:
                if draft.state is not DraftLifecycle.DRAFT:
                    raise StaleConflictError("only an editable draft can become reviewable")
                current = self._current_revisions(connection, draft)
                expected = (
                    draft.base_profile_revision,
                    draft.base_mandate_revision,
                    draft.base_policy_revision,
                )
                if current != expected:
                    result = self._mark_stale(
                        connection,
                        draft,
                        actor=actor,
                        occurred_at=occurred_at,
                    )
                    stale = True
                elif all(item.classification.value == "unchanged" for item in draft.diff):
                    raise ValidationError("review requires at least one explicit change")
            elif draft.state not in {DraftLifecycle.DRAFT, DraftLifecycle.REVIEWABLE}:
                raise StaleConflictError("terminal colleague draft cannot transition")
            if not stale:
                result = replace(draft, state=target, updated_at=occurred_at)
                self._write_draft(connection, result)
                self._insert_draft_audit(
                    connection,
                    draft=result,
                    action=action,
                    actor=actor,
                    occurred_at=occurred_at,
                )
        if stale:
            raise StaleConflictError("draft base revisions are stale")
        assert result is not None
        return result

    def review_draft(
        self,
        *,
        namespace: Namespace,
        draft_id: str,
        expected_revision: int,
        actor: Principal,
        occurred_at: datetime,
    ) -> ColleagueDraft:
        return self._transition_draft(
            namespace=namespace,
            draft_id=draft_id,
            expected_revision=expected_revision,
            actor=actor,
            occurred_at=occurred_at,
            target=DraftLifecycle.REVIEWABLE,
            action="reviewed",
        )

    def cancel_draft(
        self,
        *,
        namespace: Namespace,
        draft_id: str,
        expected_revision: int,
        actor: Principal,
        occurred_at: datetime,
    ) -> ColleagueDraft:
        return self._transition_draft(
            namespace=namespace,
            draft_id=draft_id,
            expected_revision=expected_revision,
            actor=actor,
            occurred_at=occurred_at,
            target=DraftLifecycle.CANCELLED,
            action="cancelled",
        )

    @staticmethod
    def _same_profile_content(left: Profile, right: Profile) -> bool:
        return (
            left.display_name,
            left.description,
            left.presentation,
        ) == (right.display_name, right.description, right.presentation)

    @staticmethod
    def _same_mandate_content(left: Mandate, right: Mandate) -> bool:
        return (
            left.mission,
            left.service_relationship,
            left.responsibilities,
            left.capabilities,
            left.constraints,
            left.working_context,
            left.effect_boundaries,
        ) == (
            right.mission,
            right.service_relationship,
            right.responsibilities,
            right.capabilities,
            right.constraints,
            right.working_context,
            right.effect_boundaries,
        )

    @staticmethod
    def _same_policy_content(left: ColleaguePolicy, right: ColleaguePolicy) -> bool:
        return (
            left.mandate_id,
            left.mandate_revision,
            left.timezone,
            left.weekly_windows,
            left.allowed_triggers,
            left.proactivity,
            left.notification,
            left.interruption,
            left.wake_budget,
            left.outside_hours,
            left.stop_conditions,
            left.escalation_conditions,
            left.failure_limit,
            left.run_state,
        ) == (
            right.mandate_id,
            right.mandate_revision,
            right.timezone,
            right.weekly_windows,
            right.allowed_triggers,
            right.proactivity,
            right.notification,
            right.interruption,
            right.wake_budget,
            right.outside_hours,
            right.stop_conditions,
            right.escalation_conditions,
            right.failure_limit,
            right.run_state,
        )

    def _upsert_run_state(
        self,
        connection: sqlite3.Connection,
        *,
        policy: ColleaguePolicy,
        actor: Principal,
        correlation_id: str,
        causation_id: str,
        occurred_at: datetime,
        reason: str,
    ) -> None:
        existing = connection.execute(
            """
            SELECT revision FROM p5_run_states
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
            """,
            _ns(policy.namespace),
        ).fetchone()
        revision = 1 if existing is None else existing["revision"] + 1
        connection.execute(
            """
            INSERT INTO p5_run_states(
              schema_version, tenant_id, namespace_scope, namespace_scope_id,
              policy_id, policy_revision, state, reason, actor_principal_id,
              correlation_id, causation_id, updated_at, revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tenant_id, namespace_scope, namespace_scope_id) DO UPDATE SET
              policy_id = excluded.policy_id,
              policy_revision = excluded.policy_revision,
              state = excluded.state,
              reason = excluded.reason,
              actor_principal_id = excluded.actor_principal_id,
              correlation_id = excluded.correlation_id,
              causation_id = excluded.causation_id,
              updated_at = excluded.updated_at,
              revision = excluded.revision
            """,
            (
                SCHEMA_VERSION,
                *_ns(policy.namespace),
                policy.policy_id,
                policy.revision,
                policy.run_state.value,
                reason,
                actor.principal_id,
                correlation_id,
                causation_id,
                datetime_to_z(occurred_at),
                revision,
            ),
        )

    @staticmethod
    def _explicit_resume_change(
        *,
        reason: str,
        current: ColleaguePolicy,
        proposed: ColleaguePolicy,
    ) -> str | None:
        if (
            current.run_state is PolicyRunState.STOPPED
            and proposed.run_state is PolicyRunState.ACTIVE
        ):
            return "admin_run_state_activated"
        if proposed.run_state is not PolicyRunState.ACTIVE:
            return None
        if reason == "budget_exhausted":
            if StopCondition.BUDGET_EXHAUSTED in current.stop_conditions and (
                StopCondition.BUDGET_EXHAUSTED not in proposed.stop_conditions
            ):
                return "budget_stop_condition_removed"
            if current.wake_budget.period != proposed.wake_budget.period:
                return "wake_budget_period_changed"
            if proposed.wake_budget.limit > current.wake_budget.limit:
                return "wake_budget_limit_increased"
            return None
        if reason == "outside_hours_stop":
            if proposed.outside_hours is not OutsideHoursOutcome.STOP:
                return "outside_hours_stop_removed"
            if (
                current.timezone != proposed.timezone
                or current.weekly_windows != proposed.weekly_windows
            ):
                return "working_hours_changed"
            return None
        if reason == PolicyOutcomeKind.REPEATED_FAILURE_STOP.value:
            if StopCondition.REPEATED_FAILURE in current.stop_conditions and (
                StopCondition.REPEATED_FAILURE not in proposed.stop_conditions
            ):
                return "repeated_failure_stop_condition_removed"
            if proposed.failure_limit > current.failure_limit:
                return "failure_limit_increased"
            return None
        if reason == PolicyOutcomeKind.FINITE_WORK_TERMINAL_STOP.value:
            if StopCondition.FINITE_WORK_TERMINAL in current.stop_conditions and (
                StopCondition.FINITE_WORK_TERMINAL not in proposed.stop_conditions
            ):
                return "finite_work_stop_condition_removed"
        return None

    def _record_explicit_resume(
        self,
        connection: sqlite3.Connection,
        *,
        draft: ColleagueDraft,
        policy: ColleaguePolicy,
        actor: Principal,
        occurred_at: datetime,
        previous_stop_reason: str,
        resume_change: str,
    ) -> None:
        projection = {
            "outcome": PolicyOutcomeKind.EXPLICIT_RESUME.value,
            "stage": PolicyStage.STOP.value,
            "previous_stop_reason": previous_stop_reason,
            "resume_change": resume_change,
            "draft_id": draft.draft_id,
            "draft_revision": draft.revision,
        }
        encoded = _safe_json(projection)
        outcome_id = (
            "policy-outcome:"
            + hashlib.sha256(
                f"{draft.draft_id}\0{draft.revision}\0explicit_resume".encode()
            ).hexdigest()[:32]
        )

        self._insert_policy_outcome(
            connection,
            PolicyEnforcementRecord(
                namespace=policy.namespace,
                outcome_id=outcome_id,
                policy_id=policy.policy_id,
                policy_revision=policy.revision,
                mandate_id=policy.mandate_id,
                mandate_revision=policy.mandate_revision,
                stage=PolicyStage.STOP,
                outcome=PolicyOutcomeKind.EXPLICIT_RESUME,
                trigger_class=None,
                source_id=draft.draft_id,
                actor=actor,
                correlation_id=draft.correlation_id,
                causation_id=draft.draft_id,
                occurred_at=occurred_at,
                safe_projection=FrozenJsonObject.from_mapping(projection),
                payload_digest="sha256:" + hashlib.sha256(encoded.encode()).hexdigest(),
            ),
        )

    @staticmethod
    def _draft_requests_explicit_resume(draft: ColleagueDraft) -> bool:
        return any(
            item.section.value == "policy"
            and item.path == "explicit_resume"
            and item.classification.value == "expanded"
            and item.after == FrozenJsonObject.from_mapping({"value": True})
            for item in draft.diff
        )

    def confirm_draft(
        self,
        *,
        namespace: Namespace,
        draft_id: str,
        expected_draft_revision: int,
        expected_base_profile_revision: int,
        expected_base_mandate_revision: int,
        expected_base_policy_revision: int,
        expected_canonical_digest: str,
        actor: Principal,
        idempotency_key: str,
        request_digest: str,
        confirmation_id: str,
        occurred_at: datetime,
    ) -> ConfirmationResult:
        stale = False
        result: ConfirmationResult | None = None
        with self._transaction() as connection:
            self._require_admin(connection, actor)
            replay = connection.execute(
                """
                SELECT request_digest, result_json FROM p5_draft_confirmations
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND idempotency_key = ?
                """,
                (*_ns(namespace), idempotency_key),
            ).fetchone()
            if replay is not None:
                if replay["request_digest"] != request_digest:
                    raise ReplayConflictError("confirmation idempotency key was rebound")
                data = json.loads(replay["result_json"])
                return ConfirmationResult(**data, replayed=True)
            row = connection.execute(
                """
                SELECT * FROM p5_colleague_drafts
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND draft_id = ?
                """,
                (*_ns(namespace), draft_id),
            ).fetchone()
            if row is None:
                raise NotFoundError("namespaced colleague draft was not found")
            draft = self._draft_from_row(row)
            exact = (
                draft.revision == expected_draft_revision
                and draft.base_profile_revision == expected_base_profile_revision
                and draft.base_mandate_revision == expected_base_mandate_revision
                and draft.base_policy_revision == expected_base_policy_revision
                and draft.canonical_digest == expected_canonical_digest
            )
            if not exact:
                raise StaleConflictError("exact draft confirmation binding is stale")
            if draft.state is not DraftLifecycle.REVIEWABLE:
                raise StaleConflictError("only an exact reviewable draft can be confirmed")
            current_revisions = self._current_revisions(connection, draft)
            expected_revisions = (
                expected_base_profile_revision,
                expected_base_mandate_revision,
                expected_base_policy_revision,
            )
            if current_revisions != expected_revisions:
                self._mark_stale(connection, draft, actor=actor, occurred_at=occurred_at)
                stale = True
            else:
                current_profile = self._get_record(
                    connection,
                    namespace,
                    "profile",
                    draft.proposed_profile.profile_id,
                    Profile,
                )
                current_mandate = self._get_record(
                    connection,
                    namespace,
                    "mandate",
                    draft.proposed_mandate.mandate_id,
                    Mandate,
                )
                current_policy = self.get_active_policy(namespace)
                profile_changed = not self._same_profile_content(
                    current_profile, draft.proposed_profile
                )
                mandate_changed = not self._same_mandate_content(
                    current_mandate, draft.proposed_mandate
                )
                policy_changed = current_policy is None or not self._same_policy_content(
                    current_policy, draft.proposed_policy
                )
                if not profile_changed and not mandate_changed and not policy_changed:
                    raise ValidationError("confirmation requires an explicit change")
                applied_profile = current_profile
                if profile_changed:
                    applied_profile = replace(
                        draft.proposed_profile,
                        revision=current_profile.revision + 1,
                        updated_by=actor,
                        updated_at=occurred_at,
                    )
                    self._update_record(
                        connection,
                        applied_profile,
                        expected_revision=current_profile.revision,
                    )
                applied_mandate = current_mandate
                if mandate_changed:
                    applied_mandate = replace(
                        draft.proposed_mandate,
                        revision=current_mandate.revision + 1,
                        issued_by=actor,
                        effective_at=occurred_at,
                    )
                    self._update_record(
                        connection,
                        applied_mandate,
                        expected_revision=current_mandate.revision,
                    )
                applied_policy = current_policy
                if policy_changed:
                    proposed = replace(
                        draft.proposed_policy,
                        mandate_id=applied_mandate.mandate_id,
                        mandate_revision=applied_mandate.revision,
                        revision=(0 if current_policy is None else current_policy.revision) + 1,
                        issued_by=actor,
                        effective_at=occurred_at,
                    )
                    if current_policy is None:
                        self._insert_record(
                            connection,
                            proposed,
                            correlation_id=draft.correlation_id,
                            causation_id=draft.draft_id,
                        )
                    else:
                        self._update_record(
                            connection,
                            proposed,
                            expected_revision=current_policy.revision,
                        )
                    applied_policy = proposed
                assert applied_policy is not None
                confirmed = replace(
                    draft,
                    state=DraftLifecycle.CONFIRMED,
                    updated_at=occurred_at,
                )
                self._write_draft(connection, confirmed)
                self._insert_draft_audit(
                    connection,
                    draft=confirmed,
                    action="confirmed",
                    actor=actor,
                    occurred_at=occurred_at,
                )
                run = connection.execute(
                    """
                    SELECT state, reason FROM p5_run_states
                    WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                    """,
                    _ns(namespace),
                ).fetchone()
                if run is None:
                    self._upsert_run_state(
                        connection,
                        policy=applied_policy,
                        actor=actor,
                        correlation_id=draft.correlation_id,
                        causation_id=draft.draft_id,
                        occurred_at=occurred_at,
                        reason=(
                            "explicit_admin_stop"
                            if applied_policy.run_state is PolicyRunState.STOPPED
                            else "policy_initialized"
                        ),
                    )
                elif run["state"] == PolicyRunState.STOPPED.value:
                    if current_policy is None:
                        raise ConflictError("durable stopped state has no active policy")
                    resume_change = self._explicit_resume_change(
                        reason=run["reason"],
                        current=current_policy,
                        proposed=applied_policy,
                    )
                    resume_requested = self._draft_requests_explicit_resume(draft)
                    if resume_requested and resume_change is None:
                        raise ValidationError(
                            "explicit resume must revise the applicable stop policy"
                        )
                    if resume_requested and resume_change is not None and policy_changed:
                        self._upsert_run_state(
                            connection,
                            policy=applied_policy,
                            actor=actor,
                            correlation_id=draft.correlation_id,
                            causation_id=draft.draft_id,
                            occurred_at=occurred_at,
                            reason="explicit_resume",
                        )
                        self._record_explicit_resume(
                            connection,
                            draft=draft,
                            policy=applied_policy,
                            actor=actor,
                            occurred_at=occurred_at,
                            previous_stop_reason=run["reason"],
                            resume_change=resume_change,
                        )
                    elif policy_changed:
                        self._upsert_run_state(
                            connection,
                            policy=replace(
                                applied_policy,
                                run_state=PolicyRunState.STOPPED,
                            ),
                            actor=actor,
                            correlation_id=draft.correlation_id,
                            causation_id=draft.draft_id,
                            occurred_at=occurred_at,
                            reason=run["reason"],
                        )
                elif policy_changed:
                    self._upsert_run_state(
                        connection,
                        policy=applied_policy,
                        actor=actor,
                        correlation_id=draft.correlation_id,
                        causation_id=draft.draft_id,
                        occurred_at=occurred_at,
                        reason=(
                            "explicit_admin_stop"
                            if applied_policy.run_state is PolicyRunState.STOPPED
                            else "policy_revision_confirmed"
                        ),
                    )
                result = ConfirmationResult(
                    draft_id=draft.draft_id,
                    draft_revision=draft.revision,
                    profile_revision=applied_profile.revision,
                    mandate_revision=applied_mandate.revision,
                    policy_revision=applied_policy.revision,
                    canonical_digest=draft.canonical_digest,
                )
                result_data = {
                    "draft_id": result.draft_id,
                    "draft_revision": result.draft_revision,
                    "profile_revision": result.profile_revision,
                    "mandate_revision": result.mandate_revision,
                    "policy_revision": result.policy_revision,
                    "canonical_digest": result.canonical_digest,
                }
                connection.execute(
                    """
                    INSERT INTO p5_draft_confirmations(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      confirmation_id, draft_id, draft_revision, canonical_digest,
                      profile_revision, mandate_revision, policy_revision, idempotency_key,
                      request_digest, result_json, actor_principal_id, occurred_at,
                      correlation_id, causation_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        SCHEMA_VERSION,
                        *_ns(namespace),
                        confirmation_id,
                        draft.draft_id,
                        draft.revision,
                        draft.canonical_digest,
                        result.profile_revision,
                        result.mandate_revision,
                        result.policy_revision,
                        idempotency_key,
                        request_digest,
                        _safe_json(result_data),
                        actor.principal_id,
                        datetime_to_z(occurred_at),
                        draft.correlation_id,
                        draft.draft_id,
                    ),
                )
        if stale:
            raise StaleConflictError("draft base revisions are stale")
        assert result is not None
        return result

    def _outcome_from_row(self, row: sqlite3.Row) -> PolicyEnforcementRecord:
        actor = self.get_principal(row["tenant_id"], row["actor_principal_id"])
        return PolicyEnforcementRecord(
            namespace=Namespace.colleague(row["tenant_id"], row["namespace_scope_id"]),
            outcome_id=row["outcome_id"],
            policy_id=row["policy_id"],
            policy_revision=row["policy_revision"],
            mandate_id=row["mandate_id"],
            mandate_revision=row["mandate_revision"],
            stage=PolicyStage(row["stage"]),
            outcome=PolicyOutcomeKind(row["outcome"]),
            trigger_class=(
                None if row["trigger_class"] is None else DurableTriggerKind(row["trigger_class"])
            ),
            source_id=row["source_id"],
            actor=actor,
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            occurred_at=datetime_from_z(row["occurred_at"]),
            safe_projection=FrozenJsonObject.from_mapping(json.loads(row["safe_projection_json"])),
            payload_digest=row["payload_digest"],
            schema_version=row["schema_version"],
        )

    def _insert_policy_outcome(
        self, connection: sqlite3.Connection, record: PolicyEnforcementRecord
    ) -> bool:
        existing = connection.execute(
            """
            SELECT * FROM p5_policy_outcomes
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND outcome_id = ?
            """,
            (*_ns(record.namespace), record.outcome_id),
        ).fetchone()
        if existing is not None:
            if self._outcome_from_row(existing) != record:
                raise ConflictError("policy outcome identity was rebound")
            return False
        connection.execute(
            """
            INSERT INTO p5_policy_outcomes(
              schema_version, tenant_id, namespace_scope, namespace_scope_id,
              outcome_id, policy_id, policy_revision, mandate_id, mandate_revision,
              stage, outcome, trigger_class, source_id, actor_principal_id,
              correlation_id, causation_id, occurred_at, safe_projection_json, payload_digest
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.schema_version,
                *_ns(record.namespace),
                record.outcome_id,
                record.policy_id,
                record.policy_revision,
                record.mandate_id,
                record.mandate_revision,
                record.stage.value,
                record.outcome.value,
                None if record.trigger_class is None else record.trigger_class.value,
                record.source_id,
                record.actor.principal_id,
                record.correlation_id,
                record.causation_id,
                datetime_to_z(record.occurred_at),
                _safe_json(contract_to_public_data(record.safe_projection)),
                record.payload_digest,
            ),
        )
        return True

    def _escalation_from_row(self, row: sqlite3.Row) -> EscalationRecord:
        return EscalationRecord(
            namespace=Namespace.colleague(row["tenant_id"], row["namespace_scope_id"]),
            escalation_id=row["escalation_id"],
            policy_id=row["policy_id"],
            policy_revision=row["policy_revision"],
            condition=EscalationCondition(row["condition"]),
            safe_summary=row["safe_summary"],
            actor=self.get_principal(row["tenant_id"], row["actor_principal_id"]),
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            occurred_at=datetime_from_z(row["occurred_at"]),
            revision=row["revision"],
            schema_version=row["schema_version"],
        )

    def _insert_escalation(
        self, connection: sqlite3.Connection, escalation: EscalationRecord
    ) -> bool:
        existing = connection.execute(
            """
            SELECT * FROM p5_escalations
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND escalation_id = ?
            """,
            (*_ns(escalation.namespace), escalation.escalation_id),
        ).fetchone()
        if existing is not None:
            if self._escalation_from_row(existing) != escalation:
                raise ConflictError("escalation identity was rebound")
            return False
        connection.execute(
            """
            INSERT INTO p5_escalations(
              schema_version, tenant_id, namespace_scope, namespace_scope_id,
              escalation_id, policy_id, policy_revision, condition, status,
              safe_summary, actor_principal_id, correlation_id, causation_id,
              occurred_at, revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?)
            """,
            (
                escalation.schema_version,
                *_ns(escalation.namespace),
                escalation.escalation_id,
                escalation.policy_id,
                escalation.policy_revision,
                escalation.condition.value,
                escalation.safe_summary,
                escalation.actor.principal_id,
                escalation.correlation_id,
                escalation.causation_id,
                datetime_to_z(escalation.occurred_at),
                escalation.revision,
            ),
        )
        return True

    def record_policy_outcome(
        self,
        record: PolicyEnforcementRecord,
        *,
        escalation: EscalationRecord | None = None,
    ) -> bool:
        with self._transaction() as connection:
            created = self._insert_policy_outcome(connection, record)
            if escalation is not None:
                record.namespace.require_exact(escalation.namespace)
                self._insert_escalation(connection, escalation)
            return created

    def _prepare_semantic_decision(
        self,
        connection: sqlite3.Connection,
        claim: AgendaClaim,
        semantic: SemanticDecision,
    ) -> SemanticDecision:
        semantic = super()._prepare_semantic_decision(connection, claim, semantic)
        policy = self.get_active_policy(claim.namespace)
        if policy is None:
            return semantic
        run = connection.execute(
            """
            SELECT state FROM p5_run_states
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
            """,
            _ns(claim.namespace),
        ).fetchone()
        stopped = policy.run_state is PolicyRunState.STOPPED or (
            run is not None and run["state"] == PolicyRunState.STOPPED.value
        )
        if not stopped:
            return semantic
        existing = connection.execute(
            """
            SELECT 1 FROM p5_policy_outcomes
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND correlation_id = ? AND causation_id = ? AND outcome = ?
            LIMIT 1
            """,
            (
                *_ns(claim.namespace),
                semantic.decision.correlation_id,
                semantic.decision.agenda_item_id,
                PolicyOutcomeKind.STOPPED.value,
            ),
        ).fetchone()
        if existing is None:
            wake = self._get_record(
                connection,
                claim.namespace,
                "wake_cycle",
                semantic.decision.wake_cycle_id,
                WakeCycle,
            )
            projection = {
                "outcome": PolicyOutcomeKind.STOPPED.value,
                "stage": PolicyStage.POST_MODEL.value,
                "persistence_revalidation": True,
            }
            encoded = _safe_json(projection)
            self._insert_policy_outcome(
                connection,
                PolicyEnforcementRecord(
                    namespace=policy.namespace,
                    outcome_id=(
                        "policy-outcome:"
                        + hashlib.sha256(
                            (
                                semantic.decision.decision_id + "\0proposal-persistence\0stopped"
                            ).encode()
                        ).hexdigest()[:32]
                    ),
                    policy_id=policy.policy_id,
                    policy_revision=policy.revision,
                    mandate_id=policy.mandate_id,
                    mandate_revision=policy.mandate_revision,
                    stage=PolicyStage.POST_MODEL,
                    outcome=PolicyOutcomeKind.STOPPED,
                    trigger_class=(
                        DurableTriggerKind.TIMER
                        if wake.trigger_timer_occurrence_ids
                        else DurableTriggerKind.EVENT
                    ),
                    source_id=wake.causation_id,
                    actor=semantic.decision.actor,
                    correlation_id=semantic.decision.correlation_id,
                    causation_id=semantic.decision.agenda_item_id,
                    occurred_at=semantic.decision.occurred_at,
                    safe_projection=FrozenJsonObject.from_mapping(projection),
                    payload_digest=("sha256:" + hashlib.sha256(encoded.encode()).hexdigest()),
                ),
            )
        if semantic.proposal is None:
            return semantic
        decision = replace(
            semantic.decision,
            kind=DecisionKind.NO_ACTION,
            rationale="Durable stopped state was revalidated before proposal persistence.",
            proposed_effect_id=None,
            policy_id=policy.policy_id,
            policy_revision=policy.revision,
        )
        return SemanticDecision(SemanticOutcome.NO_OP, decision, None, semantic.request_id)

    def _record_for_admission(
        self,
        *,
        policy: ColleaguePolicy,
        outcome: PolicyOutcomeKind,
        trigger_class: DurableTriggerKind,
        source_id: str,
        actor: Principal,
        correlation_id: str,
        causation_id: str,
        outcome_id: str,
        occurred_at: datetime,
    ) -> PolicyEnforcementRecord:
        encoded = _safe_json(
            {
                "outcome": outcome.value,
                "policy_id": policy.policy_id,
                "policy_revision": policy.revision,
                "source_id": source_id,
                "stage": PolicyStage.PRE_WAKE.value,
            }
        )
        return PolicyEnforcementRecord(
            namespace=policy.namespace,
            outcome_id=outcome_id,
            policy_id=policy.policy_id,
            policy_revision=policy.revision,
            mandate_id=policy.mandate_id,
            mandate_revision=policy.mandate_revision,
            stage=PolicyStage.PRE_WAKE,
            outcome=outcome,
            trigger_class=trigger_class,
            source_id=source_id,
            actor=actor,
            correlation_id=correlation_id,
            causation_id=causation_id,
            occurred_at=occurred_at,
            safe_projection=FrozenJsonObject.from_mapping(
                {"outcome": outcome.value, "stage": PolicyStage.PRE_WAKE.value}
            ),
            payload_digest="sha256:" + hashlib.sha256(encoded.encode()).hexdigest(),
        )

    def _budget_count(self, connection: sqlite3.Connection, policy: ColleaguePolicy) -> int:
        row = connection.execute(
            """
            SELECT COALESCE(SUM(consumed_count), 0) AS count
            FROM p5_wake_budget_counters
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND policy_id = ? AND policy_revision = ?
            """,
            (*_ns(policy.namespace), policy.policy_id, policy.revision),
        ).fetchone()
        return int(row["count"])

    def _trigger_work(
        self, connection: sqlite3.Connection, policy: ColleaguePolicy, work_id: str
    ) -> FiniteWork | None:
        row = connection.execute(
            """
            SELECT payload_json FROM domain_records
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND record_type = 'finite_work' AND record_id = ?
            """,
            (*_ns(policy.namespace), work_id),
        ).fetchone()
        return None if row is None else from_storage_json(row["payload_json"], FiniteWork)

    def _deterministic_failure_streak(
        self, connection: sqlite3.Connection, policy: ColleaguePolicy
    ) -> int:
        rows = connection.execute(
            """
            SELECT payload_json FROM domain_records
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND record_type = 'action_result'
            ORDER BY occurred_at DESC, record_id DESC
            """,
            _ns(policy.namespace),
        ).fetchall()
        failures = {
            ActionResultState.FAILED,
            ActionResultState.RETRYABLE_FAILURE,
            ActionResultState.PERMANENT_FAILURE,
        }
        streak = 0
        for row in rows:
            result = from_storage_json(row["payload_json"], ActionResult)
            if result.state not in failures:
                break
            streak += 1
        return streak

    def admit_trigger(
        self,
        *,
        policy: ColleaguePolicy,
        trigger_class: DurableTriggerKind,
        source_id: str,
        occurrence_key: str,
        actor: Principal,
        correlation_id: str,
        causation_id: str,
        outcome_id: str,
        escalation_id: str,
        occurred_at: datetime,
    ) -> PolicyAdmission:
        result: PolicyAdmission | None = None
        with self._transaction() as connection:
            existing_row = connection.execute(
                """
                SELECT * FROM p5_policy_outcomes
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND outcome_id = ?
                """,
                (*_ns(policy.namespace), outcome_id),
            ).fetchone()
            if existing_row is not None:
                record = self._outcome_from_row(existing_row)
                escalation_row = connection.execute(
                    """
                    SELECT * FROM p5_escalations
                    WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                      AND causation_id = ?
                    ORDER BY occurred_at, escalation_id LIMIT 1
                    """,
                    (*_ns(policy.namespace), source_id),
                ).fetchone()
                result = PolicyAdmission(
                    accepted=record.outcome is PolicyOutcomeKind.ALLOWED,
                    outcome=record.outcome,
                    budget_count=self._budget_count(connection, policy),
                    budget_limit=policy.wake_budget.limit,
                    record=record,
                    escalation=(
                        None
                        if escalation_row is None
                        else self._escalation_from_row(escalation_row)
                    ),
                )
            else:
                active = self.get_active_policy(policy.namespace)
                if active != policy:
                    outcome = PolicyOutcomeKind.STALE_POLICY
                else:
                    run = connection.execute(
                        """
                        SELECT state FROM p5_run_states
                        WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                        """,
                        _ns(policy.namespace),
                    ).fetchone()
                    stopped = policy.run_state is PolicyRunState.STOPPED or (
                        run is not None and run["state"] == PolicyRunState.STOPPED.value
                    )
                    if stopped:
                        outcome = PolicyOutcomeKind.STOPPED
                    elif trigger_class not in policy.allowed_triggers:
                        outcome = PolicyOutcomeKind.DISALLOWED_TRIGGER
                    elif policy.proactivity is ProactivityMode.DISABLED:
                        outcome = PolicyOutcomeKind.PROACTIVITY_SUPPRESSED
                    elif not within_working_hours(policy, occurred_at):
                        outcome = {
                            OutsideHoursOutcome.DEFER: PolicyOutcomeKind.OUTSIDE_HOURS_DEFER,
                            OutsideHoursOutcome.NO_OP: PolicyOutcomeKind.OUTSIDE_HOURS_NO_OP,
                            OutsideHoursOutcome.STOP: PolicyOutcomeKind.OUTSIDE_HOURS_STOP,
                            OutsideHoursOutcome.ESCALATE: PolicyOutcomeKind.OUTSIDE_HOURS_ESCALATE,
                        }[policy.outside_hours]
                    else:
                        work = self._trigger_work(connection, policy, causation_id)
                        failure_streak = self._deterministic_failure_streak(connection, policy)
                        if (
                            failure_streak >= policy.failure_limit
                            and StopCondition.REPEATED_FAILURE in policy.stop_conditions
                        ):
                            outcome = PolicyOutcomeKind.REPEATED_FAILURE_STOP
                        elif (
                            failure_streak >= policy.failure_limit
                            and EscalationCondition.REPEATED_FAILURE in policy.escalation_conditions
                        ):
                            outcome = PolicyOutcomeKind.REPEATED_FAILURE_ESCALATE
                        elif (
                            work is not None
                            and work.state in {WorkState.COMPLETED, WorkState.CANCELLED}
                            and StopCondition.FINITE_WORK_TERMINAL in policy.stop_conditions
                        ):
                            outcome = PolicyOutcomeKind.FINITE_WORK_TERMINAL_STOP
                        elif (
                            work is not None
                            and work.state is WorkState.BLOCKED
                            and EscalationCondition.BLOCKED_WORK in policy.escalation_conditions
                        ):
                            outcome = PolicyOutcomeKind.BLOCKED_WORK_ESCALATE
                        else:
                            outcome = PolicyOutcomeKind.ALLOWED
                        consumed = connection.execute(
                            """
                            SELECT 1 FROM p5_wake_budget_consumptions
                            WHERE tenant_id = ? AND namespace_scope = ?
                              AND namespace_scope_id = ? AND occurrence_key = ?
                            """,
                            (*_ns(policy.namespace), occurrence_key),
                        ).fetchone()
                        bucket = budget_bucket_start(policy.wake_budget.period, occurred_at)
                        counter = connection.execute(
                            """
                            SELECT consumed_count, revision FROM p5_wake_budget_counters
                            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                              AND policy_id = ? AND policy_revision = ? AND period = ?
                              AND bucket_start = ?
                            """,
                            (
                                *_ns(policy.namespace),
                                policy.policy_id,
                                policy.revision,
                                policy.wake_budget.period.value,
                                datetime_to_z(bucket),
                            ),
                        ).fetchone()
                        count = 0 if counter is None else counter["consumed_count"]
                        if outcome is not PolicyOutcomeKind.ALLOWED:
                            pass
                        elif consumed is not None:
                            outcome = PolicyOutcomeKind.DUPLICATE_TRIGGER
                        elif count >= policy.wake_budget.limit:
                            outcome = PolicyOutcomeKind.BUDGET_EXHAUSTED
                        else:
                            if counter is None:
                                connection.execute(
                                    """
                                    INSERT INTO p5_wake_budget_counters(
                                      schema_version, tenant_id, namespace_scope,
                                      namespace_scope_id, policy_id, policy_revision,
                                      period, bucket_start, consumed_count, updated_at, revision
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 1)
                                    """,
                                    (
                                        SCHEMA_VERSION,
                                        *_ns(policy.namespace),
                                        policy.policy_id,
                                        policy.revision,
                                        policy.wake_budget.period.value,
                                        datetime_to_z(bucket),
                                        datetime_to_z(occurred_at),
                                    ),
                                )
                            else:
                                connection.execute(
                                    """
                                    UPDATE p5_wake_budget_counters
                                    SET consumed_count = consumed_count + 1,
                                        updated_at = ?, revision = revision + 1
                                    WHERE tenant_id = ? AND namespace_scope = ?
                                      AND namespace_scope_id = ? AND policy_id = ?
                                      AND policy_revision = ? AND period = ? AND bucket_start = ?
                                    """,
                                    (
                                        datetime_to_z(occurred_at),
                                        *_ns(policy.namespace),
                                        policy.policy_id,
                                        policy.revision,
                                        policy.wake_budget.period.value,
                                        datetime_to_z(bucket),
                                    ),
                                )
                            connection.execute(
                                """
                                INSERT INTO p5_wake_budget_consumptions(
                                  schema_version, tenant_id, namespace_scope,
                                  namespace_scope_id, occurrence_key, policy_id,
                                  policy_revision, period, bucket_start, trigger_class,
                                  source_id, consumed_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    SCHEMA_VERSION,
                                    *_ns(policy.namespace),
                                    occurrence_key,
                                    policy.policy_id,
                                    policy.revision,
                                    policy.wake_budget.period.value,
                                    datetime_to_z(bucket),
                                    trigger_class.value,
                                    source_id,
                                    datetime_to_z(occurred_at),
                                ),
                            )
                            outcome = PolicyOutcomeKind.ALLOWED
                record = self._record_for_admission(
                    policy=policy,
                    outcome=outcome,
                    trigger_class=trigger_class,
                    source_id=source_id,
                    actor=actor,
                    correlation_id=correlation_id,
                    causation_id=causation_id,
                    outcome_id=outcome_id,
                    occurred_at=occurred_at,
                )
                self._insert_policy_outcome(connection, record)
                escalation: EscalationRecord | None = None
                if outcome is PolicyOutcomeKind.OUTSIDE_HOURS_STOP:
                    stopped_policy = replace(policy, run_state=PolicyRunState.STOPPED)
                    self._upsert_run_state(
                        connection,
                        policy=stopped_policy,
                        actor=actor,
                        correlation_id=correlation_id,
                        causation_id=source_id,
                        occurred_at=occurred_at,
                        reason="outside_hours_stop",
                    )
                if outcome in {
                    PolicyOutcomeKind.REPEATED_FAILURE_STOP,
                    PolicyOutcomeKind.FINITE_WORK_TERMINAL_STOP,
                }:
                    stopped_policy = replace(policy, run_state=PolicyRunState.STOPPED)
                    self._upsert_run_state(
                        connection,
                        policy=stopped_policy,
                        actor=actor,
                        correlation_id=correlation_id,
                        causation_id=source_id,
                        occurred_at=occurred_at,
                        reason=outcome.value,
                    )
                condition: EscalationCondition | None = None
                if outcome is PolicyOutcomeKind.OUTSIDE_HOURS_ESCALATE:
                    condition = EscalationCondition.OUTSIDE_HOURS
                if outcome is PolicyOutcomeKind.BUDGET_EXHAUSTED:
                    if StopCondition.BUDGET_EXHAUSTED in policy.stop_conditions:
                        stopped_policy = replace(policy, run_state=PolicyRunState.STOPPED)
                        self._upsert_run_state(
                            connection,
                            policy=stopped_policy,
                            actor=actor,
                            correlation_id=correlation_id,
                            causation_id=source_id,
                            occurred_at=occurred_at,
                            reason="budget_exhausted",
                        )
                    if EscalationCondition.BUDGET_EXHAUSTED in policy.escalation_conditions:
                        condition = EscalationCondition.BUDGET_EXHAUSTED
                if (
                    outcome
                    in {
                        PolicyOutcomeKind.REPEATED_FAILURE_STOP,
                        PolicyOutcomeKind.REPEATED_FAILURE_ESCALATE,
                    }
                    and EscalationCondition.REPEATED_FAILURE in policy.escalation_conditions
                ):
                    condition = EscalationCondition.REPEATED_FAILURE
                if outcome is PolicyOutcomeKind.BLOCKED_WORK_ESCALATE:
                    condition = EscalationCondition.BLOCKED_WORK
                if condition is not None:
                    escalation = EscalationRecord(
                        namespace=policy.namespace,
                        escalation_id=escalation_id,
                        policy_id=policy.policy_id,
                        policy_revision=policy.revision,
                        condition=condition,
                        safe_summary=f"Typed policy condition: {condition.value}",
                        actor=actor,
                        correlation_id=correlation_id,
                        causation_id=source_id,
                        occurred_at=occurred_at,
                    )
                    self._insert_escalation(connection, escalation)
                result = PolicyAdmission(
                    accepted=outcome is PolicyOutcomeKind.ALLOWED,
                    outcome=outcome,
                    budget_count=self._budget_count(connection, policy),
                    budget_limit=policy.wake_budget.limit,
                    record=record,
                    escalation=escalation,
                )
        assert result is not None
        return result

    def require_current_proposal_policy(
        self, proposal: EffectProposal, *, stage: PolicyStage
    ) -> ColleaguePolicy | None:
        del stage
        active = self.get_active_policy(proposal.namespace)
        if active is None:
            if proposal.policy_id is None and proposal.policy_revision is None:
                return None
            raise PermissionDeniedError("proposal policy binding is stale")
        if (proposal.policy_id, proposal.policy_revision) != (
            active.policy_id,
            active.revision,
        ):
            raise PermissionDeniedError("proposal policy binding is stale")
        if (proposal.mandate_id, proposal.mandate_revision) != (
            active.mandate_id,
            active.mandate_revision,
        ):
            raise PermissionDeniedError("proposal Mandate/policy binding is stale")
        run = self._connection.execute(
            """
            SELECT state FROM p5_run_states
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
            """,
            _ns(proposal.namespace),
        ).fetchone()
        if active.run_state is PolicyRunState.STOPPED or (
            run is not None and run["state"] == PolicyRunState.STOPPED.value
        ):
            raise PermissionDeniedError("stopped policy refused proposal use")
        return active

    def causal_history(
        self, namespace: Namespace, correlation_id: str
    ) -> tuple[dict[str, object], ...]:
        history = list(super().causal_history(namespace, correlation_id))
        draft_rows = self._connection.execute(
            """
            SELECT schema_version, audit_id, draft_id, draft_revision,
                   actor_principal_id, correlation_id, causation_id, occurred_at,
                   payload_digest, safe_projection_json
            FROM p5_draft_audit
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND correlation_id = ?
            """,
            (*_ns(namespace), correlation_id),
        ).fetchall()
        for row in draft_rows:
            history.append(
                {
                    "schema_version": row["schema_version"],
                    "namespace": contract_to_public_data(namespace),
                    "audit_id": row["audit_id"],
                    "record_type": "colleague_draft",
                    "record_id": row["draft_id"],
                    "record_revision": row["draft_revision"],
                    "actor_principal_id": row["actor_principal_id"],
                    "correlation_id": row["correlation_id"],
                    "causation_id": row["causation_id"],
                    "occurred_at": row["occurred_at"],
                    "payload_digest": row["payload_digest"],
                    "safe_projection": json.loads(row["safe_projection_json"]),
                }
            )
        confirmation_rows = self._connection.execute(
            """
            SELECT schema_version, confirmation_id, draft_id, draft_revision,
                   profile_revision, mandate_revision, policy_revision,
                   actor_principal_id, correlation_id, causation_id, occurred_at,
                   canonical_digest
            FROM p5_draft_confirmations
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND correlation_id = ?
            """,
            (*_ns(namespace), correlation_id),
        ).fetchall()
        for row in confirmation_rows:
            history.append(
                {
                    "schema_version": row["schema_version"],
                    "namespace": contract_to_public_data(namespace),
                    "audit_id": row["confirmation_id"],
                    "record_type": "draft_confirmation",
                    "record_id": row["confirmation_id"],
                    "record_revision": row["draft_revision"],
                    "actor_principal_id": row["actor_principal_id"],
                    "correlation_id": row["correlation_id"],
                    "causation_id": row["causation_id"],
                    "occurred_at": row["occurred_at"],
                    "payload_digest": row["canonical_digest"],
                    "safe_projection": {
                        "draft_id": row["draft_id"],
                        "draft_revision": row["draft_revision"],
                        "profile_revision": row["profile_revision"],
                        "mandate_revision": row["mandate_revision"],
                        "policy_revision": row["policy_revision"],
                    },
                }
            )
        outcome_rows = self._connection.execute(
            """
            SELECT schema_version, outcome_id, policy_revision,
                   actor_principal_id, correlation_id, causation_id, occurred_at,
                   payload_digest, safe_projection_json
            FROM p5_policy_outcomes
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND correlation_id = ?
            """,
            (*_ns(namespace), correlation_id),
        ).fetchall()
        for row in outcome_rows:
            history.append(
                {
                    "schema_version": row["schema_version"],
                    "namespace": contract_to_public_data(namespace),
                    "audit_id": row["outcome_id"],
                    "record_type": "policy_outcome",
                    "record_id": row["outcome_id"],
                    "record_revision": row["policy_revision"],
                    "actor_principal_id": row["actor_principal_id"],
                    "correlation_id": row["correlation_id"],
                    "causation_id": row["causation_id"],
                    "occurred_at": row["occurred_at"],
                    "payload_digest": row["payload_digest"],
                    "safe_projection": json.loads(row["safe_projection_json"]),
                }
            )
        escalation_rows = self._connection.execute(
            """
            SELECT schema_version, escalation_id, policy_revision, condition,
                   safe_summary, actor_principal_id, correlation_id, causation_id,
                   occurred_at, revision
            FROM p5_escalations
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND correlation_id = ?
            """,
            (*_ns(namespace), correlation_id),
        ).fetchall()
        for row in escalation_rows:
            summary = row["safe_summary"]
            history.append(
                {
                    "schema_version": row["schema_version"],
                    "namespace": contract_to_public_data(namespace),
                    "audit_id": row["escalation_id"],
                    "record_type": "policy_escalation",
                    "record_id": row["escalation_id"],
                    "record_revision": row["revision"],
                    "actor_principal_id": row["actor_principal_id"],
                    "correlation_id": row["correlation_id"],
                    "causation_id": row["causation_id"],
                    "occurred_at": row["occurred_at"],
                    "payload_digest": "sha256:" + hashlib.sha256(summary.encode()).hexdigest(),
                    "safe_projection": {
                        "condition": row["condition"],
                        "policy_revision": row["policy_revision"],
                        "safe_summary": summary,
                    },
                }
            )
        return tuple(
            sorted(history, key=lambda item: (str(item["occurred_at"]), str(item["audit_id"])))
        )

    def resolve_runtime_context(
        self,
        *,
        namespace: Namespace,
        model_principal_id: str,
        service_principal_id: str,
        mandate_id: str,
    ) -> ServiceRuntimeContext:
        base = super().resolve_runtime_context(
            namespace=namespace,
            model_principal_id=model_principal_id,
            service_principal_id=service_principal_id,
            mandate_id=mandate_id,
        )
        policy = self.get_active_policy(namespace)
        if policy is None:
            return base
        if (policy.mandate_id, policy.mandate_revision) != (
            base.mandate_id,
            base.mandate_revision,
        ):
            raise PermissionDeniedError("runtime Mandate/policy binding is stale")
        return replace(
            base,
            policy_id=policy.policy_id,
            policy_revision=policy.revision,
        )

    def p5_studio_snapshot(self, namespace: Namespace) -> P5StudioSnapshot:
        profile, mandate = self.active_configuration(namespace)
        policy = self.get_active_policy(namespace)
        outcome_rows = self._connection.execute(
            """
            SELECT * FROM p5_policy_outcomes
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
            ORDER BY occurred_at, outcome_id
            """,
            _ns(namespace),
        ).fetchall()
        escalation_rows = self._connection.execute(
            """
            SELECT * FROM p5_escalations
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
            ORDER BY occurred_at, escalation_id
            """,
            _ns(namespace),
        ).fetchall()
        run = self._connection.execute(
            """
            SELECT state FROM p5_run_states
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
            """,
            _ns(namespace),
        ).fetchone()
        return P5StudioSnapshot(
            profile=profile,
            mandate=mandate,
            policy=policy,
            policy_status=(
                PolicyStatus.LEGACY_UNCONFIRMED if policy is None else PolicyStatus.CONFIRMED
            ),
            drafts=self.list_drafts(namespace),
            policy_outcomes=tuple(self._outcome_from_row(row) for row in outcome_rows),
            escalations=tuple(self._escalation_from_row(row) for row in escalation_rows),
            budget_count=0 if policy is None else self._budget_count(self._connection, policy),
            run_state=None if run is None else PolicyRunState(run["state"]),
        )
