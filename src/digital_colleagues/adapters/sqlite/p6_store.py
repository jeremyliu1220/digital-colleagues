# SPDX-License-Identifier: Apache-2.0

"""Additive SQLite persistence for P6 local multi-user governance."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import replace
from datetime import datetime
from typing import cast

from digital_colleagues.adapters.sqlite.codec import to_storage_json
from digital_colleagues.adapters.sqlite.p5_store import SQLiteP5Store
from digital_colleagues.adapters.sqlite.store import _namespace_from_row, _ns
from digital_colleagues.application.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ReplayConflictError,
    StaleConflictError,
)
from digital_colleagues.application.p4_contracts import (
    AuthenticatedSession,
    BootstrapRecord,
)
from digital_colleagues.application.p6_contracts import P6StudioSnapshot
from digital_colleagues.core.builder import ColleagueDraft, DiffSection, DraftLifecycle
from digital_colleagues.core.common import SCHEMA_VERSION, FrozenJsonObject
from digital_colleagues.core.effects import EffectProposal, HumanApprovalDecision
from digital_colleagues.core.governance import (
    AuditExportQuery,
    AuditExportRecord,
    AuthorizationAction,
    ChangeChoice,
    ChangeDecision,
    ChangeKind,
    ChangeProposal,
    ChangeState,
    CredentialKind,
    CredentialState,
    GovernanceCredential,
    Membership,
    MembershipStatus,
    governance_change_digest,
)
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import HumanRole, Principal, PrincipalKind
from digital_colleagues.core.serialization import (
    contract_to_public_data,
    datetime_from_z,
    datetime_to_z,
)
from digital_colleagues.core.work import FiniteWork
from digital_colleagues.governance.rbac import authorize_action


def _safe_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _safe_digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_safe_json(value).encode("utf-8")).hexdigest()


def _tuple_json(value: str) -> tuple[str, ...]:
    raw = json.loads(value)
    if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
        raise ConflictError("durable governance scope shape is invalid")
    return tuple(raw)


class SQLiteP6Store(SQLiteP5Store):
    """One-host reference implementation of the P6 governance port."""

    def _require_admin(self, connection: sqlite3.Connection, actor: Principal) -> None:
        self._require_current_membership(
            connection,
            actor=actor,
            action=AuthorizationAction.MANAGE_DRAFT,
            namespace=Namespace.tenant(actor.namespace.tenant_id),
        )

    def _authorize_work_assignment(self, connection: sqlite3.Connection, work: FiniteWork) -> None:
        self._require_current_membership(
            connection,
            actor=work.actor,
            action=AuthorizationAction.ASSIGN_WORK,
            namespace=work.namespace,
        )

    def _membership_from_row(self, row: sqlite3.Row) -> Membership:
        principal = self.get_principal(row["tenant_id"], row["issued_by_principal_id"])
        return Membership(
            namespace=Namespace.principal(row["tenant_id"], row["principal_id"]),
            membership_id=row["membership_id"],
            principal_id=row["principal_id"],
            roles=tuple(HumanRole(role) for role in _tuple_json(row["roles_json"])),
            colleague_ids=_tuple_json(row["colleague_scopes_json"]),
            status=MembershipStatus(row["status"]),
            role_revision=row["role_revision"],
            membership_revision=row["membership_revision"],
            issued_by=principal,
            created_at=datetime_from_z(row["created_at"]),
            updated_at=datetime_from_z(row["updated_at"]),
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            revision=row["revision"],
            schema_version=row["schema_version"],
        )

    def _credential_from_row(self, row: sqlite3.Row) -> GovernanceCredential:
        return GovernanceCredential(
            namespace=Namespace.tenant(row["tenant_id"]),
            credential_id=row["credential_id"],
            kind=CredentialKind(row["kind"]),
            state=CredentialState(row["state"]),
            target_principal_id=row["target_principal_id"],
            target_role_revision=row["target_role_revision"],
            target_membership_revision=row["target_membership_revision"],
            target_role=None if row["target_role"] is None else HumanRole(row["target_role"]),
            colleague_ids=_tuple_json(row["colleague_scopes_json"]),
            bootstrap_transition=bool(row["bootstrap_transition"]),
            issued_by_principal_id=row["issued_by_principal_id"],
            issued_at=datetime_from_z(row["issued_at"]),
            expires_at=datetime_from_z(row["expires_at"]),
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            token_digest=row["token_digest"],
            change_decision_id=row["change_decision_id"],
            retrieved_at=(
                None if row["retrieved_at"] is None else datetime_from_z(row["retrieved_at"])
            ),
            consumed_at=(
                None if row["consumed_at"] is None else datetime_from_z(row["consumed_at"])
            ),
            revoked_at=(None if row["revoked_at"] is None else datetime_from_z(row["revoked_at"])),
            consumed_principal_id=row["consumed_principal_id"],
            revision=row["revision"],
            schema_version=row["schema_version"],
        )

    @staticmethod
    def _change_proposal_from_row(row: sqlite3.Row) -> ChangeProposal:
        return ChangeProposal(
            namespace=_namespace_from_row(row),
            proposal_id=row["proposal_id"],
            change_kind=ChangeKind(row["change_kind"]),
            target_id=row["target_id"],
            target_revision=row["target_revision"],
            canonical_digest=row["canonical_digest"],
            base_profile_revision=row["base_profile_revision"],
            base_mandate_revision=row["base_mandate_revision"],
            base_policy_revision=row["base_policy_revision"],
            proposed_role=(
                None if row["proposed_role"] is None else HumanRole(row["proposed_role"])
            ),
            proposed_status=(
                None if row["proposed_status"] is None else MembershipStatus(row["proposed_status"])
            ),
            proposed_colleague_ids=_tuple_json(row["proposed_scopes_json"]),
            proposer_principal_id=row["proposer_principal_id"],
            proposer_role_revision=row["proposer_role_revision"],
            proposer_membership_revision=row["proposer_membership_revision"],
            issued_at=datetime_from_z(row["issued_at"]),
            expires_at=datetime_from_z(row["expires_at"]),
            state=ChangeState(row["state"]),
            idempotency_key=row["idempotency_key"],
            request_digest=row["request_digest"],
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            decision_id=row["decision_id"],
            consumed_at=(
                None if row["consumed_at"] is None else datetime_from_z(row["consumed_at"])
            ),
            revision=row["revision"],
            schema_version=row["schema_version"],
        )

    @staticmethod
    def _change_decision_from_row(row: sqlite3.Row) -> ChangeDecision:
        return ChangeDecision(
            namespace=_namespace_from_row(row),
            decision_id=row["decision_id"],
            proposal_id=row["proposal_id"],
            proposal_revision=row["proposal_revision"],
            proposal_digest=row["proposal_digest"],
            choice=ChangeChoice(row["choice"]),
            approver_principal_id=row["approver_principal_id"],
            approver_role_revision=row["approver_role_revision"],
            approver_membership_revision=row["approver_membership_revision"],
            occurred_at=datetime_from_z(row["occurred_at"]),
            valid_until=datetime_from_z(row["valid_until"]),
            idempotency_key=row["idempotency_key"],
            request_digest=row["request_digest"],
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            consumed_at=(
                None if row["consumed_at"] is None else datetime_from_z(row["consumed_at"])
            ),
            revision=row["revision"],
            schema_version=row["schema_version"],
        )

    def _insert_governance_audit(
        self,
        connection: sqlite3.Connection,
        *,
        namespace: Namespace,
        record_type: str,
        record_id: str,
        record_revision: int,
        action: str,
        result: str,
        actor: Principal,
        authority_revision: str,
        correlation_id: str,
        causation_id: str,
        occurred_at: datetime,
        safe_projection: dict[str, object],
    ) -> None:
        material = {
            "namespace": contract_to_public_data(namespace),
            "record_type": record_type,
            "record_id": record_id,
            "record_revision": record_revision,
            "action": action,
            "result": result,
            "authority_revision": authority_revision,
            "safe_projection": safe_projection,
        }
        identity = _safe_digest(
            {
                "record_type": record_type,
                "record_id": record_id,
                "record_revision": record_revision,
                "action": action,
            }
        ).removeprefix("sha256:")[:32]
        connection.execute(
            """
            INSERT INTO p6_governance_audit(
              schema_version, tenant_id, namespace_scope, namespace_scope_id,
              audit_id, record_type, record_id, record_revision, action, result,
              actor_principal_id, actor_kind, authority_revision, correlation_id,
              causation_id, occurred_at, safe_digest, safe_projection_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SCHEMA_VERSION,
                *_ns(namespace),
                "audit:p6:" + identity,
                record_type,
                record_id,
                record_revision,
                action,
                result,
                actor.principal_id,
                actor.kind.value,
                authority_revision,
                correlation_id,
                causation_id,
                datetime_to_z(occurred_at),
                _safe_digest(material),
                _safe_json(safe_projection),
            ),
        )

    def _membership_row(
        self, connection: sqlite3.Connection, tenant_id: str, principal_id: str
    ) -> sqlite3.Row:
        row = connection.execute(
            """
            SELECT * FROM p6_memberships
            WHERE tenant_id = ? AND namespace_scope = 'principal'
              AND namespace_scope_id = ? AND principal_id = ?
            """,
            (tenant_id, principal_id, principal_id),
        ).fetchone()
        if row is None:
            raise PermissionDeniedError("governance authority was refused")
        return cast(sqlite3.Row, row)

    def membership_for_principal(self, tenant_id: str, principal_id: str) -> Membership:
        return self._membership_from_row(
            self._membership_row(self._connection, tenant_id, principal_id)
        )

    def _require_current_membership(
        self,
        connection: sqlite3.Connection,
        *,
        actor: Principal,
        action: AuthorizationAction,
        namespace: Namespace,
    ) -> Membership:
        current = self.get_principal(actor.namespace.tenant_id, actor.principal_id)
        membership = self._membership_from_row(
            self._membership_row(connection, actor.namespace.tenant_id, actor.principal_id)
        )
        if current != actor:
            raise PermissionDeniedError("governance principal binding was refused")
        try:
            authorize_action(
                principal=current,
                membership=membership,
                action=action,
                namespace=namespace,
            )
        except (ValueError, RuntimeError) as exc:
            raise PermissionDeniedError("governance authority was refused") from exc
        return membership

    def governed_session(
        self, *, credential_digest: str, evaluated_at: datetime
    ) -> tuple[AuthenticatedSession, Membership]:
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
            raise PermissionDeniedError("authenticated session was refused")
        membership = self.membership_for_principal(
            session.tenant_id, session.principal.principal_id
        )
        if (
            membership.status is not MembershipStatus.ACTIVE
            or session.role_revision != membership.role_revision
            or session.membership_revision != membership.membership_revision
            or session.principal.roles != membership.roles
            or session.principal.revision != membership.role_revision
        ):
            raise PermissionDeniedError("authenticated session was refused")
        if session.active_colleague_id is not None and not membership.allows_namespace(
            session.colleague_namespace()
        ):
            raise PermissionDeniedError("authenticated session was refused")
        return session, membership

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
            raise PermissionDeniedError("bootstrap authority binding was refused")
        governed_session = replace(session, role_revision=1, membership_revision=1)
        with self._transaction() as connection:
            row = connection.execute(
                """SELECT * FROM p4_bootstrap_credentials
                WHERE tenant_id = ? AND token_digest = ?""",
                (tenant_id, token_digest),
            ).fetchone()
            if row is None:
                raise PermissionDeniedError("bootstrap exchange was refused")
            bootstrap: BootstrapRecord = self._bootstrap_from_row(row)
            if bootstrap.retrieved_at is None or occurred_at >= bootstrap.expires_at:
                raise PermissionDeniedError("bootstrap exchange was refused")
            if bootstrap.consumed_at is not None:
                raise ConflictError("bootstrap exchange replay was refused")
            count = connection.execute(
                """SELECT COUNT(*) AS count FROM domain_records
                WHERE tenant_id = ? AND record_type = 'principal'
                  AND payload_json LIKE '%\"kind\":\"human\"%'""",
                (tenant_id,),
            ).fetchone()["count"]
            if count != 0:
                raise ConflictError("the first durable human principal already exists")
            self._insert_record(
                connection,
                principal,
                actor=principal,
                correlation_id="correlation:bootstrap",
                causation_id=bootstrap.credential_id,
                occurred_at=occurred_at,
            )
            membership = Membership(
                namespace=principal.namespace,
                membership_id="membership:" + principal.principal_id.removeprefix("human:"),
                principal_id=principal.principal_id,
                roles=principal.roles,
                colleague_ids=("*",),
                status=MembershipStatus.ACTIVE,
                role_revision=1,
                membership_revision=1,
                issued_by=principal,
                created_at=occurred_at,
                updated_at=occurred_at,
                correlation_id="correlation:bootstrap",
                causation_id=bootstrap.credential_id,
            )
            self._insert_membership(connection, membership)
            connection.execute(
                """
                INSERT INTO p6_bootstrap_transitions(
                  schema_version, tenant_id, namespace_scope, namespace_scope_id,
                  transition_id, state, created_by_principal_id, created_at,
                  updated_at, correlation_id, causation_id, revision
                ) VALUES (
                  ?, ?, 'tenant', '', 'transition:second-admin', 'available', ?,
                  ?, ?, 'correlation:bootstrap', ?, 1
                )
                """,
                (
                    SCHEMA_VERSION,
                    tenant_id,
                    principal.principal_id,
                    datetime_to_z(occurred_at),
                    datetime_to_z(occurred_at),
                    bootstrap.credential_id,
                ),
            )
            updated = connection.execute(
                """UPDATE p4_bootstrap_credentials
                SET consumed_at = ?, revision = revision + 1
                WHERE tenant_id = ? AND credential_id = ? AND revision = ?
                  AND consumed_at IS NULL""",
                (
                    datetime_to_z(occurred_at),
                    tenant_id,
                    bootstrap.credential_id,
                    bootstrap.revision,
                ),
            )
            if updated.rowcount != 1:
                raise ConflictError("bootstrap exchange lost its atomic claim")
            assert governed_session.created_at is not None
            assert governed_session.expires_at is not None
            connection.execute(
                """
                INSERT INTO p4_sessions(
                  schema_version, tenant_id, namespace_scope, namespace_scope_id,
                  session_id, principal_id, credential_digest, csrf_digest,
                  active_colleague_id, created_at, expires_at, revision,
                  role_revision, membership_revision
                ) VALUES (?, ?, 'principal', ?, ?, ?, ?, ?, NULL, ?, ?, 1, 1, 1)
                """,
                (
                    governed_session.schema_version,
                    tenant_id,
                    principal.principal_id,
                    governed_session.session_id,
                    principal.principal_id,
                    governed_session.credential_digest,
                    governed_session.csrf_digest,
                    datetime_to_z(governed_session.created_at),
                    datetime_to_z(governed_session.expires_at),
                ),
            )
            self._insert_governance_audit(
                connection,
                namespace=Namespace.tenant(tenant_id),
                record_type="membership",
                record_id=membership.membership_id,
                record_revision=1,
                action="bootstrap_admin_created",
                result="created",
                actor=principal,
                authority_revision="role:1:member:1",
                correlation_id=membership.correlation_id,
                causation_id=membership.causation_id,
                occurred_at=occurred_at,
                safe_projection={"role": HumanRole.TENANT_ADMIN.value},
            )
        return governed_session

    def _insert_membership(self, connection: sqlite3.Connection, membership: Membership) -> None:
        connection.execute(
            """
            INSERT INTO p6_memberships(
              schema_version, tenant_id, namespace_scope, namespace_scope_id,
              membership_id, principal_record_type, principal_id, roles_json,
              colleague_scopes_json, status, role_revision, membership_revision,
              issued_by_principal_id, created_at, updated_at, correlation_id,
              causation_id, revision
            ) VALUES (?, ?, 'principal', ?, ?, 'principal', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                membership.schema_version,
                membership.namespace.tenant_id,
                membership.principal_id,
                membership.membership_id,
                membership.principal_id,
                _safe_json([role.value for role in membership.roles]),
                _safe_json(list(membership.colleague_ids)),
                membership.status.value,
                membership.role_revision,
                membership.membership_revision,
                membership.issued_by.principal_id,
                datetime_to_z(membership.created_at),
                datetime_to_z(membership.updated_at),
                membership.correlation_id,
                membership.causation_id,
                membership.revision,
            ),
        )

    def authorize_enrollment(
        self,
        *,
        credential: GovernanceCredential,
        issuer_membership: Membership,
    ) -> GovernanceCredential:
        if credential.kind is not CredentialKind.ENROLLMENT:
            raise PermissionDeniedError("credential purpose was refused")
        target_role = credential.target_role
        if target_role is None:
            raise PermissionDeniedError("enrollment role was refused")
        issuer = self.get_principal(
            credential.namespace.tenant_id, credential.issued_by_principal_id
        )
        with self._transaction() as connection:
            current = self._require_current_membership(
                connection,
                actor=issuer,
                action=AuthorizationAction.MANAGE_CREDENTIAL,
                namespace=credential.namespace,
            )
            if current != issuer_membership:
                raise PermissionDeniedError("credential issuer binding was refused")
            existing = connection.execute(
                """SELECT * FROM p6_governance_credentials
                WHERE tenant_id = ? AND credential_id = ?""",
                (credential.namespace.tenant_id, credential.credential_id),
            ).fetchone()
            if existing is not None:
                stored = self._credential_from_row(existing)
                if (
                    replace(stored, state=credential.state, revision=credential.revision)
                    != credential
                ):
                    raise ReplayConflictError("enrollment idempotency key was rebound")
                return stored
            if credential.bootstrap_transition:
                transition = connection.execute(
                    """SELECT * FROM p6_bootstrap_transitions
                    WHERE tenant_id = ? AND transition_id = 'transition:second-admin'""",
                    (credential.namespace.tenant_id,),
                ).fetchone()
                admin_count = connection.execute(
                    """SELECT COUNT(*) AS count FROM p6_memberships
                    WHERE tenant_id = ? AND status = 'active'
                      AND roles_json = '[\"tenant_admin\"]'""",
                    (credential.namespace.tenant_id,),
                ).fetchone()["count"]
                pending = connection.execute(
                    """SELECT COUNT(*) AS count FROM p6_governance_credentials
                    WHERE tenant_id = ? AND kind = 'enrollment'
                      AND bootstrap_transition = 1
                      AND state IN ('authorized', 'retrieved')""",
                    (credential.namespace.tenant_id,),
                ).fetchone()["count"]
                if (
                    transition is None
                    or transition["state"] != "available"
                    or admin_count != 1
                    or pending != 0
                    or credential.target_role is not HumanRole.TENANT_ADMIN
                    or credential.colleague_ids != ("*",)
                ):
                    raise PermissionDeniedError("second-Admin bootstrap transition was refused")
                connection.execute(
                    """UPDATE p6_bootstrap_transitions
                    SET active_credential_id = ?, updated_at = ?, revision = revision + 1
                    WHERE tenant_id = ? AND transition_id = 'transition:second-admin'
                      AND state = 'available' AND revision = ?""",
                    (
                        credential.credential_id,
                        datetime_to_z(credential.issued_at),
                        credential.namespace.tenant_id,
                        transition["revision"],
                    ),
                )
            elif credential.target_role is HumanRole.TENANT_ADMIN:
                if credential.change_decision_id is None:
                    raise PermissionDeniedError("Admin enrollment requires exact change approval")
                self._consume_admin_enrollment_authority(
                    connection,
                    decision_id=credential.change_decision_id,
                    role=credential.target_role,
                    colleague_ids=credential.colleague_ids,
                    actor=issuer,
                    occurred_at=credential.issued_at,
                )
            connection.execute(
                """
                INSERT INTO p6_governance_credentials(
                  schema_version, tenant_id, namespace_scope, namespace_scope_id,
                  credential_id, kind, state, token_digest, target_principal_id,
                  target_role_revision, target_membership_revision,
                  target_role, colleague_scopes_json, bootstrap_transition,
                  change_decision_id, issued_by_principal_id, issued_at, expires_at,
                  correlation_id, causation_id, revision
                ) VALUES (
                  ?, ?, 'tenant', '', ?, ?, ?, NULL, NULL, NULL, NULL,
                  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    credential.schema_version,
                    credential.namespace.tenant_id,
                    credential.credential_id,
                    credential.kind.value,
                    credential.state.value,
                    credential.target_role.value if credential.target_role is not None else None,
                    _safe_json(list(credential.colleague_ids)),
                    int(credential.bootstrap_transition),
                    credential.change_decision_id,
                    credential.issued_by_principal_id,
                    datetime_to_z(credential.issued_at),
                    datetime_to_z(credential.expires_at),
                    credential.correlation_id,
                    credential.causation_id,
                    credential.revision,
                ),
            )
            self._insert_governance_audit(
                connection,
                namespace=credential.namespace,
                record_type="governance_credential",
                record_id=credential.credential_id,
                record_revision=credential.revision,
                action="enrollment_authorized",
                result="authorized",
                actor=issuer,
                authority_revision=(
                    f"role:{current.role_revision}:member:{current.membership_revision}"
                ),
                correlation_id=credential.correlation_id,
                causation_id=credential.causation_id,
                occurred_at=credential.issued_at,
                safe_projection={
                    "kind": credential.kind.value,
                    "role": target_role.value,
                    "bootstrap_transition": credential.bootstrap_transition,
                    "scope_count": len(credential.colleague_ids),
                },
            )
        return credential

    def authorize_recovery(
        self,
        *,
        credential: GovernanceCredential,
        issuer_membership: Membership,
    ) -> GovernanceCredential:
        if credential.kind is not CredentialKind.RECOVERY:
            raise PermissionDeniedError("credential purpose was refused")
        issuer = self.get_principal(
            credential.namespace.tenant_id, credential.issued_by_principal_id
        )
        assert credential.target_principal_id is not None
        with self._transaction() as connection:
            current = self._require_current_membership(
                connection,
                actor=issuer,
                action=AuthorizationAction.MANAGE_CREDENTIAL,
                namespace=credential.namespace,
            )
            if current != issuer_membership:
                raise PermissionDeniedError("credential issuer binding was refused")
            target = self._membership_from_row(
                self._membership_row(
                    connection,
                    credential.namespace.tenant_id,
                    credential.target_principal_id,
                )
            )
            if target.status is not MembershipStatus.ACTIVE:
                raise PermissionDeniedError("recovery target was refused")
            if (
                target.colleague_ids != credential.colleague_ids
                or target.role_revision != credential.target_role_revision
                or target.membership_revision != credential.target_membership_revision
            ):
                raise PermissionDeniedError("recovery authority was rebound")
            try:
                connection.execute(
                    """
                    INSERT INTO p6_governance_credentials(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      credential_id, kind, state, token_digest, target_principal_id,
                      target_role_revision, target_membership_revision,
                      target_role, colleague_scopes_json, bootstrap_transition,
                      change_decision_id, issued_by_principal_id, issued_at, expires_at,
                      correlation_id, causation_id, revision
                    ) VALUES (
                      ?, ?, 'tenant', '', ?, ?, ?, NULL, ?, ?, ?, NULL, ?, 0,
                      NULL, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        credential.schema_version,
                        credential.namespace.tenant_id,
                        credential.credential_id,
                        credential.kind.value,
                        credential.state.value,
                        credential.target_principal_id,
                        credential.target_role_revision,
                        credential.target_membership_revision,
                        _safe_json(list(credential.colleague_ids)),
                        credential.issued_by_principal_id,
                        datetime_to_z(credential.issued_at),
                        datetime_to_z(credential.expires_at),
                        credential.correlation_id,
                        credential.causation_id,
                        credential.revision,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                row = connection.execute(
                    """SELECT * FROM p6_governance_credentials
                    WHERE tenant_id = ? AND credential_id = ?""",
                    (credential.namespace.tenant_id, credential.credential_id),
                ).fetchone()
                if row is None or self._credential_from_row(row) != credential:
                    raise ReplayConflictError("recovery idempotency key was rebound") from exc
                return self._credential_from_row(row)
            self._insert_governance_audit(
                connection,
                namespace=credential.namespace,
                record_type="governance_credential",
                record_id=credential.credential_id,
                record_revision=1,
                action="recovery_authorized",
                result="authorized",
                actor=issuer,
                authority_revision=(
                    f"role:{current.role_revision}:member:{current.membership_revision}"
                ),
                correlation_id=credential.correlation_id,
                causation_id=credential.causation_id,
                occurred_at=credential.issued_at,
                safe_projection={"kind": "recovery", "scope_count": len(target.colleague_ids)},
            )
        return credential

    def claim_credential_secret(
        self,
        *,
        credential_id: str,
        token_digest: str,
        occurred_at: datetime,
    ) -> GovernanceCredential:
        with self._transaction() as connection:
            rows = connection.execute(
                """SELECT * FROM p6_governance_credentials
                WHERE credential_id = ?""",
                (credential_id,),
            ).fetchall()
            if len(rows) != 1:
                raise PermissionDeniedError("credential retrieval was refused")
            credential = self._credential_from_row(rows[0])
            issuer = self.get_principal(
                credential.namespace.tenant_id, credential.issued_by_principal_id
            )
            if credential.state is not CredentialState.AUTHORIZED:
                raise ConflictError("credential retrieval was refused")
            if occurred_at >= credential.expires_at:
                connection.execute(
                    """UPDATE p6_governance_credentials
                    SET state = 'expired', revision = revision + 1
                    WHERE tenant_id = ? AND credential_id = ? AND revision = ?""",
                    (
                        credential.namespace.tenant_id,
                        credential.credential_id,
                        credential.revision,
                    ),
                )
                expired = replace(
                    credential, state=CredentialState.EXPIRED, revision=credential.revision + 1
                )
                self._insert_governance_audit(
                    connection,
                    namespace=credential.namespace,
                    record_type="governance_credential",
                    record_id=credential.credential_id,
                    record_revision=expired.revision,
                    action="credential_expired",
                    result="expired",
                    actor=issuer,
                    authority_revision="credential:expired",
                    correlation_id=credential.correlation_id,
                    causation_id=credential.credential_id,
                    occurred_at=occurred_at,
                    safe_projection={"kind": credential.kind.value},
                )
                return expired
            updated = connection.execute(
                """UPDATE p6_governance_credentials
                SET state = 'retrieved', token_digest = ?, retrieved_at = ?,
                    revision = revision + 1
                WHERE tenant_id = ? AND credential_id = ? AND revision = ?
                  AND state = 'authorized' AND token_digest IS NULL""",
                (
                    token_digest,
                    datetime_to_z(occurred_at),
                    credential.namespace.tenant_id,
                    credential.credential_id,
                    credential.revision,
                ),
            )
            if updated.rowcount != 1:
                raise ConflictError("credential retrieval lost its atomic claim")
            retrieved = replace(
                credential,
                state=CredentialState.RETRIEVED,
                token_digest=token_digest,
                retrieved_at=occurred_at,
                revision=credential.revision + 1,
            )
            self._insert_governance_audit(
                connection,
                namespace=credential.namespace,
                record_type="governance_credential",
                record_id=credential.credential_id,
                record_revision=retrieved.revision,
                action="credential_retrieved",
                result="retrieved",
                actor=issuer,
                authority_revision="credential:retrieved",
                correlation_id=credential.correlation_id,
                causation_id=credential.credential_id,
                occurred_at=occurred_at,
                safe_projection={"kind": credential.kind.value},
            )
        return retrieved

    def credential_by_digest(self, *, token_digest: str, kind: str) -> GovernanceCredential:
        row = self._connection.execute(
            """SELECT * FROM p6_governance_credentials
            WHERE token_digest = ? AND kind = ?""",
            (token_digest, kind),
        ).fetchone()
        if row is None:
            raise PermissionDeniedError("governance credential was refused")
        return self._credential_from_row(row)

    def expire_credential(
        self, *, credential: GovernanceCredential, occurred_at: datetime
    ) -> GovernanceCredential:
        with self._transaction() as connection:
            row = connection.execute(
                """SELECT * FROM p6_governance_credentials
                WHERE tenant_id = ? AND credential_id = ?""",
                (credential.namespace.tenant_id, credential.credential_id),
            ).fetchone()
            if row is None or self._credential_from_row(row) != credential:
                raise PermissionDeniedError("credential expiry binding was refused")
            if (
                credential.state is not CredentialState.RETRIEVED
                or occurred_at < credential.expires_at
            ):
                raise PermissionDeniedError("credential expiry was refused")
            changed = connection.execute(
                """UPDATE p6_governance_credentials
                SET state = 'expired', token_digest = NULL, revision = revision + 1
                WHERE tenant_id = ? AND credential_id = ? AND revision = ?
                  AND state = 'retrieved'""",
                (
                    credential.namespace.tenant_id,
                    credential.credential_id,
                    credential.revision,
                ),
            )
            if changed.rowcount != 1:
                raise ConflictError("credential expiry lost its atomic claim")
            expired = replace(
                credential,
                state=CredentialState.EXPIRED,
                token_digest=None,
                revision=credential.revision + 1,
            )
            issuer = self.get_principal(
                credential.namespace.tenant_id, credential.issued_by_principal_id
            )
            self._insert_governance_audit(
                connection,
                namespace=credential.namespace,
                record_type="governance_credential",
                record_id=credential.credential_id,
                record_revision=expired.revision,
                action="credential_expired",
                result="expired",
                actor=issuer,
                authority_revision="credential:expired",
                correlation_id=credential.correlation_id,
                causation_id=credential.credential_id,
                occurred_at=occurred_at,
                safe_projection={"kind": credential.kind.value},
            )
        return expired

    def revoke_credential(
        self,
        *,
        tenant_id: str,
        credential_id: str,
        actor: Principal,
        occurred_at: datetime,
    ) -> GovernanceCredential:
        with self._transaction() as connection:
            membership = self._require_current_membership(
                connection,
                actor=actor,
                action=AuthorizationAction.MANAGE_CREDENTIAL,
                namespace=Namespace.tenant(tenant_id),
            )
            row = connection.execute(
                """SELECT * FROM p6_governance_credentials
                WHERE tenant_id = ? AND credential_id = ?""",
                (tenant_id, credential_id),
            ).fetchone()
            if row is None:
                raise NotFoundError("governance credential was not found")
            credential = self._credential_from_row(row)
            if credential.state not in {CredentialState.AUTHORIZED, CredentialState.RETRIEVED}:
                raise ConflictError("credential cannot be revoked")
            connection.execute(
                """UPDATE p6_governance_credentials
                SET state = 'revoked', revoked_at = ?, token_digest = NULL,
                    revision = revision + 1
                WHERE tenant_id = ? AND credential_id = ? AND revision = ?""",
                (
                    datetime_to_z(occurred_at),
                    tenant_id,
                    credential_id,
                    credential.revision,
                ),
            )
            revoked = replace(
                credential,
                state=CredentialState.REVOKED,
                token_digest=None,
                revoked_at=occurred_at,
                revision=credential.revision + 1,
            )
            self._insert_governance_audit(
                connection,
                namespace=credential.namespace,
                record_type="governance_credential",
                record_id=credential.credential_id,
                record_revision=revoked.revision,
                action="credential_revoked",
                result="revoked",
                actor=actor,
                authority_revision=(
                    f"role:{membership.role_revision}:member:{membership.membership_revision}"
                ),
                correlation_id=credential.correlation_id,
                causation_id=credential.credential_id,
                occurred_at=occurred_at,
                safe_projection={"kind": credential.kind.value},
            )
        return revoked

    @staticmethod
    def _insert_governed_session(
        connection: sqlite3.Connection, session: AuthenticatedSession
    ) -> None:
        assert session.created_at is not None and session.expires_at is not None
        connection.execute(
            """
            INSERT INTO p4_sessions(
              schema_version, tenant_id, namespace_scope, namespace_scope_id,
              session_id, principal_id, credential_digest, csrf_digest,
              active_colleague_id, created_at, expires_at, revision,
              role_revision, membership_revision
            ) VALUES (?, ?, 'principal', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.schema_version,
                session.tenant_id,
                session.principal.principal_id,
                session.session_id,
                session.principal.principal_id,
                session.credential_digest,
                session.csrf_digest,
                session.active_colleague_id,
                datetime_to_z(session.created_at),
                datetime_to_z(session.expires_at),
                session.revision,
                session.role_revision,
                session.membership_revision,
            ),
        )

    def consume_enrollment(
        self,
        *,
        token_digest: str,
        principal: Principal,
        membership: Membership,
        session: AuthenticatedSession,
        occurred_at: datetime,
    ) -> tuple[GovernanceCredential, Membership, AuthenticatedSession]:
        if principal.kind is not PrincipalKind.HUMAN or session.principal != principal:
            raise PermissionDeniedError("enrollment principal binding was refused")
        principal.namespace.require_exact(membership.namespace)
        with self._transaction() as connection:
            row = connection.execute(
                """SELECT * FROM p6_governance_credentials
                WHERE token_digest = ? AND kind = 'enrollment'""",
                (token_digest,),
            ).fetchone()
            if row is None:
                raise PermissionDeniedError("enrollment exchange was refused")
            credential = self._credential_from_row(row)
            if (
                credential.state is not CredentialState.RETRIEVED
                or credential.retrieved_at is None
                or occurred_at >= credential.expires_at
                or credential.target_role is None
                or principal.namespace.tenant_id != credential.namespace.tenant_id
                or principal.roles != (credential.target_role,)
                or membership.roles != principal.roles
                or membership.colleague_ids != credential.colleague_ids
                or membership.role_revision != 1
                or membership.membership_revision != 1
                or membership.status is not MembershipStatus.ACTIVE
                or session.role_revision != 1
                or session.membership_revision != 1
            ):
                raise PermissionDeniedError("enrollment exchange was refused")
            issuer = self.get_principal(
                credential.namespace.tenant_id, credential.issued_by_principal_id
            )
            if membership.issued_by != issuer:
                raise PermissionDeniedError("enrollment issuer binding was refused")
            if credential.bootstrap_transition:
                transition = connection.execute(
                    """SELECT * FROM p6_bootstrap_transitions
                    WHERE tenant_id = ? AND transition_id = 'transition:second-admin'""",
                    (credential.namespace.tenant_id,),
                ).fetchone()
                admin_count = connection.execute(
                    """SELECT COUNT(*) AS count FROM p6_memberships
                    WHERE tenant_id = ? AND status = 'active'
                      AND roles_json = '[\"tenant_admin\"]'""",
                    (credential.namespace.tenant_id,),
                ).fetchone()["count"]
                if (
                    transition is None
                    or transition["state"] != "available"
                    or transition["active_credential_id"] != credential.credential_id
                    or admin_count != 1
                ):
                    raise PermissionDeniedError("second-Admin transition was refused")
            try:
                self._insert_record(
                    connection,
                    principal,
                    actor=issuer,
                    correlation_id=credential.correlation_id,
                    causation_id=credential.credential_id,
                    occurred_at=occurred_at,
                )
                self._insert_membership(connection, membership)
                self._insert_governed_session(connection, session)
            except sqlite3.IntegrityError as exc:
                raise ConflictError("enrollment atomic consumption lost its claim") from exc
            updated = connection.execute(
                """UPDATE p6_governance_credentials
                SET state = 'consumed', consumed_at = ?, consumed_principal_id = ?,
                    revision = revision + 1
                WHERE tenant_id = ? AND credential_id = ? AND revision = ?
                  AND state = 'retrieved' AND token_digest = ?""",
                (
                    datetime_to_z(occurred_at),
                    principal.principal_id,
                    credential.namespace.tenant_id,
                    credential.credential_id,
                    credential.revision,
                    token_digest,
                ),
            )
            if updated.rowcount != 1:
                raise ConflictError("enrollment atomic consumption lost its claim")
            if credential.bootstrap_transition:
                changed = connection.execute(
                    """UPDATE p6_bootstrap_transitions
                    SET state = 'consumed', consumed_principal_id = ?, updated_at = ?,
                        revision = revision + 1
                    WHERE tenant_id = ? AND transition_id = 'transition:second-admin'
                      AND state = 'available' AND active_credential_id = ?""",
                    (
                        principal.principal_id,
                        datetime_to_z(occurred_at),
                        credential.namespace.tenant_id,
                        credential.credential_id,
                    ),
                )
                if changed.rowcount != 1:
                    raise ConflictError("second-Admin transition lost its atomic claim")
            consumed = replace(
                credential,
                state=CredentialState.CONSUMED,
                consumed_at=occurred_at,
                consumed_principal_id=principal.principal_id,
                revision=credential.revision + 1,
            )
            self._insert_governance_audit(
                connection,
                namespace=credential.namespace,
                record_type="governance_credential",
                record_id=credential.credential_id,
                record_revision=consumed.revision,
                action="enrollment_consumed",
                result="consumed",
                actor=principal,
                authority_revision="role:1:member:1",
                correlation_id=credential.correlation_id,
                causation_id=credential.credential_id,
                occurred_at=occurred_at,
                safe_projection={
                    "role": credential.target_role.value,
                    "bootstrap_transition": credential.bootstrap_transition,
                },
            )
        return consumed, membership, session

    def consume_recovery(
        self,
        *,
        token_digest: str,
        session: AuthenticatedSession,
        occurred_at: datetime,
    ) -> tuple[GovernanceCredential, Membership, AuthenticatedSession]:
        with self._transaction() as connection:
            row = connection.execute(
                """SELECT * FROM p6_governance_credentials
                WHERE token_digest = ? AND kind = 'recovery'""",
                (token_digest,),
            ).fetchone()
            if row is None:
                raise PermissionDeniedError("recovery exchange was refused")
            credential = self._credential_from_row(row)
            if (
                credential.state is not CredentialState.RETRIEVED
                or credential.retrieved_at is None
                or occurred_at >= credential.expires_at
                or credential.target_principal_id is None
            ):
                raise PermissionDeniedError("recovery exchange was refused")
            membership = self._membership_from_row(
                self._membership_row(
                    connection,
                    credential.namespace.tenant_id,
                    credential.target_principal_id,
                )
            )
            principal = self.get_principal(
                credential.namespace.tenant_id, credential.target_principal_id
            )
            if (
                membership.status is not MembershipStatus.ACTIVE
                or membership.colleague_ids != credential.colleague_ids
                or membership.role_revision != credential.target_role_revision
                or membership.membership_revision != credential.target_membership_revision
                or session.principal != principal
                or session.role_revision != membership.role_revision
                or session.membership_revision != membership.membership_revision
                or session.active_colleague_id is not None
                and not membership.allows_namespace(session.colleague_namespace())
            ):
                raise PermissionDeniedError("recovery authority binding was refused")
            connection.execute(
                """UPDATE p4_sessions
                SET revoked_at = ?, revoked_reason = 'recovery_rotation',
                    revision = revision + 1
                WHERE tenant_id = ? AND principal_id = ? AND revoked_at IS NULL""",
                (
                    datetime_to_z(occurred_at),
                    credential.namespace.tenant_id,
                    principal.principal_id,
                ),
            )
            self._insert_governed_session(connection, session)
            updated = connection.execute(
                """UPDATE p6_governance_credentials
                SET state = 'consumed', consumed_at = ?, consumed_principal_id = ?,
                    revision = revision + 1
                WHERE tenant_id = ? AND credential_id = ? AND revision = ?
                  AND state = 'retrieved' AND token_digest = ?""",
                (
                    datetime_to_z(occurred_at),
                    principal.principal_id,
                    credential.namespace.tenant_id,
                    credential.credential_id,
                    credential.revision,
                    token_digest,
                ),
            )
            if updated.rowcount != 1:
                raise ConflictError("recovery atomic consumption lost its claim")
            consumed = replace(
                credential,
                state=CredentialState.CONSUMED,
                consumed_at=occurred_at,
                consumed_principal_id=principal.principal_id,
                revision=credential.revision + 1,
            )
            self._insert_governance_audit(
                connection,
                namespace=credential.namespace,
                record_type="governance_credential",
                record_id=credential.credential_id,
                record_revision=consumed.revision,
                action="recovery_consumed",
                result="rotated",
                actor=principal,
                authority_revision=(
                    f"role:{membership.role_revision}:member:{membership.membership_revision}"
                ),
                correlation_id=credential.correlation_id,
                causation_id=credential.credential_id,
                occurred_at=occurred_at,
                safe_projection={"old_sessions_revoked": True},
            )
        return consumed, membership, session

    def create_change_proposal(self, proposal: ChangeProposal) -> ChangeProposal:
        proposer = self.get_principal(proposal.namespace.tenant_id, proposal.proposer_principal_id)
        with self._transaction() as connection:
            membership = self._require_current_membership(
                connection,
                actor=proposer,
                action=AuthorizationAction.PROPOSE_CHANGE,
                namespace=proposal.namespace,
            )
            if (
                proposal.proposer_role_revision != membership.role_revision
                or proposal.proposer_membership_revision != membership.membership_revision
                or proposal.state is not ChangeState.PENDING
            ):
                raise PermissionDeniedError("change proposer binding was refused")
            existing = connection.execute(
                """SELECT * FROM p6_change_proposals
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND proposer_principal_id = ? AND idempotency_key = ?""",
                (
                    *_ns(proposal.namespace),
                    proposal.proposer_principal_id,
                    proposal.idempotency_key,
                ),
            ).fetchone()
            if existing is not None:
                stored = self._change_proposal_from_row(existing)
                if stored != proposal:
                    raise ReplayConflictError("change proposal idempotency key was rebound")
                return stored
            if proposal.change_kind is ChangeKind.DRAFT:
                row = connection.execute(
                    """SELECT * FROM p5_colleague_drafts
                    WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                      AND draft_id = ?""",
                    (*_ns(proposal.namespace), proposal.target_id),
                ).fetchone()
                if row is None:
                    raise NotFoundError("governance target was not found")
                draft = self._draft_from_row(row)
                if (
                    draft.state is not DraftLifecycle.REVIEWABLE
                    or draft.revision != proposal.target_revision
                    or draft.canonical_digest != proposal.canonical_digest
                    or (
                        draft.base_profile_revision,
                        draft.base_mandate_revision,
                        draft.base_policy_revision,
                    )
                    != (
                        proposal.base_profile_revision,
                        proposal.base_mandate_revision,
                        proposal.base_policy_revision,
                    )
                ):
                    raise StaleConflictError("exact draft change proposal is stale")
            else:
                expected = governance_change_digest(
                    change_kind=proposal.change_kind,
                    target_id=proposal.target_id,
                    target_revision=proposal.target_revision,
                    proposed_role=proposal.proposed_role,
                    proposed_status=proposal.proposed_status,
                    proposed_colleague_ids=proposal.proposed_colleague_ids,
                )
                if expected != proposal.canonical_digest:
                    raise StaleConflictError("governance change digest was refused")
                if proposal.change_kind is ChangeKind.MEMBERSHIP:
                    target = self._membership_from_row(
                        self._membership_row(
                            connection, proposal.namespace.tenant_id, proposal.target_id
                        )
                    )
                    if target.membership_revision != proposal.target_revision:
                        raise StaleConflictError("membership change base is stale")
                    if proposal.proposed_role is None or proposal.proposed_status is None:
                        raise PermissionDeniedError("membership change binding is incomplete")
                elif (
                    proposal.proposed_role is not HumanRole.TENANT_ADMIN
                    or proposal.proposed_status is not MembershipStatus.ACTIVE
                    or proposal.proposed_colleague_ids != ("*",)
                ):
                    raise PermissionDeniedError("Admin enrollment authority was refused")
            connection.execute(
                """
                INSERT INTO p6_change_proposals(
                  schema_version, tenant_id, namespace_scope, namespace_scope_id,
                  proposal_id, change_kind, target_id, target_revision, canonical_digest,
                  base_profile_revision, base_mandate_revision, base_policy_revision,
                  proposed_role, proposed_status, proposed_scopes_json,
                  proposer_principal_id, proposer_role_revision,
                  proposer_membership_revision, issued_at, expires_at, state,
                  idempotency_key, request_digest, correlation_id, causation_id, revision
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.schema_version,
                    *_ns(proposal.namespace),
                    proposal.proposal_id,
                    proposal.change_kind.value,
                    proposal.target_id,
                    proposal.target_revision,
                    proposal.canonical_digest,
                    proposal.base_profile_revision,
                    proposal.base_mandate_revision,
                    proposal.base_policy_revision,
                    None if proposal.proposed_role is None else proposal.proposed_role.value,
                    (None if proposal.proposed_status is None else proposal.proposed_status.value),
                    _safe_json(list(proposal.proposed_colleague_ids)),
                    proposal.proposer_principal_id,
                    proposal.proposer_role_revision,
                    proposal.proposer_membership_revision,
                    datetime_to_z(proposal.issued_at),
                    datetime_to_z(proposal.expires_at),
                    proposal.state.value,
                    proposal.idempotency_key,
                    proposal.request_digest,
                    proposal.correlation_id,
                    proposal.causation_id,
                    proposal.revision,
                ),
            )
            self._insert_governance_audit(
                connection,
                namespace=proposal.namespace,
                record_type="change_proposal",
                record_id=proposal.proposal_id,
                record_revision=proposal.revision,
                action="change_proposed",
                result="pending",
                actor=proposer,
                authority_revision=(
                    f"role:{membership.role_revision}:member:{membership.membership_revision}"
                ),
                correlation_id=proposal.correlation_id,
                causation_id=proposal.causation_id,
                occurred_at=proposal.issued_at,
                safe_projection={
                    "change_kind": proposal.change_kind.value,
                    "target_revision": proposal.target_revision,
                    "canonical_digest": proposal.canonical_digest,
                },
            )
        return proposal

    def get_change_proposal(self, namespace: Namespace, proposal_id: str) -> ChangeProposal:
        row = self._connection.execute(
            """SELECT * FROM p6_change_proposals
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND proposal_id = ?""",
            (*_ns(namespace), proposal_id),
        ).fetchone()
        if row is None:
            raise NotFoundError("governance change was not found")
        return self._change_proposal_from_row(row)

    def decide_change(
        self, *, proposal: ChangeProposal, decision: ChangeDecision
    ) -> tuple[ChangeProposal, ChangeDecision]:
        expired = False
        decided_proposal: ChangeProposal | None = None
        with self._transaction() as connection:
            row = connection.execute(
                """SELECT * FROM p6_change_proposals
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND proposal_id = ?""",
                (*_ns(proposal.namespace), proposal.proposal_id),
            ).fetchone()
            if row is None:
                raise NotFoundError("governance change was not found")
            current_proposal = self._change_proposal_from_row(row)
            if current_proposal != proposal:
                raise StaleConflictError("change proposal binding is stale")
            approver = self.get_principal(
                decision.namespace.tenant_id, decision.approver_principal_id
            )
            membership = self._require_current_membership(
                connection,
                actor=approver,
                action=AuthorizationAction.DECIDE_CHANGE,
                namespace=proposal.namespace,
            )
            if proposal.proposer_principal_id == approver.principal_id:
                raise PermissionDeniedError("change proposer cannot approve their own change")
            if (
                decision.namespace != proposal.namespace
                or decision.proposal_id != proposal.proposal_id
                or decision.proposal_revision != proposal.revision
                or decision.proposal_digest != proposal.canonical_digest
                or decision.approver_role_revision != membership.role_revision
                or decision.approver_membership_revision != membership.membership_revision
                or decision.occurred_at < proposal.issued_at
                or decision.valid_until > proposal.expires_at
            ):
                raise StaleConflictError("exact change decision binding is stale")
            if proposal.state is not ChangeState.PENDING:
                raise ConflictError("change proposal already has a terminal decision")
            if decision.occurred_at >= proposal.expires_at:
                connection.execute(
                    """UPDATE p6_change_proposals
                    SET state = 'expired', revision = revision + 1
                    WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                      AND proposal_id = ? AND revision = ? AND state = 'pending'""",
                    (*_ns(proposal.namespace), proposal.proposal_id, proposal.revision),
                )
                decided_proposal = replace(
                    proposal, state=ChangeState.EXPIRED, revision=proposal.revision + 1
                )
                self._insert_governance_audit(
                    connection,
                    namespace=proposal.namespace,
                    record_type="change_proposal",
                    record_id=proposal.proposal_id,
                    record_revision=decided_proposal.revision,
                    action="change_expired",
                    result="expired",
                    actor=approver,
                    authority_revision=(
                        f"role:{membership.role_revision}:member:{membership.membership_revision}"
                    ),
                    correlation_id=proposal.correlation_id,
                    causation_id=proposal.proposal_id,
                    occurred_at=decision.occurred_at,
                    safe_projection={"change_kind": proposal.change_kind.value},
                )
                expired = True
            else:
                existing = connection.execute(
                    """SELECT * FROM p6_change_decisions
                    WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                      AND approver_principal_id = ? AND idempotency_key = ?""",
                    (
                        *_ns(proposal.namespace),
                        approver.principal_id,
                        decision.idempotency_key,
                    ),
                ).fetchone()
                if existing is not None:
                    stored = self._change_decision_from_row(existing)
                    if stored != decision:
                        raise ReplayConflictError("change decision idempotency key was rebound")
                    return proposal, stored
                connection.execute(
                    """
                    INSERT INTO p6_change_decisions(
                      schema_version, tenant_id, namespace_scope, namespace_scope_id,
                      decision_id, proposal_id, proposal_revision, proposal_digest, choice,
                      approver_principal_id, approver_role_revision,
                      approver_membership_revision, occurred_at, valid_until,
                      idempotency_key, request_digest, correlation_id, causation_id, revision
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        decision.schema_version,
                        *_ns(decision.namespace),
                        decision.decision_id,
                        decision.proposal_id,
                        decision.proposal_revision,
                        decision.proposal_digest,
                        decision.choice.value,
                        decision.approver_principal_id,
                        decision.approver_role_revision,
                        decision.approver_membership_revision,
                        datetime_to_z(decision.occurred_at),
                        datetime_to_z(decision.valid_until),
                        decision.idempotency_key,
                        decision.request_digest,
                        decision.correlation_id,
                        decision.causation_id,
                        decision.revision,
                    ),
                )
                state = (
                    ChangeState.APPROVED
                    if decision.choice is ChangeChoice.APPROVE
                    else ChangeState.REJECTED
                )
                connection.execute(
                    """UPDATE p6_change_proposals
                    SET state = ?, decision_id = ?, revision = revision + 1
                    WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                      AND proposal_id = ? AND revision = ? AND state = 'pending'""",
                    (
                        state.value,
                        decision.decision_id,
                        *_ns(proposal.namespace),
                        proposal.proposal_id,
                        proposal.revision,
                    ),
                )
                decided_proposal = replace(
                    proposal,
                    state=state,
                    decision_id=decision.decision_id,
                    revision=proposal.revision + 1,
                )
                self._insert_governance_audit(
                    connection,
                    namespace=proposal.namespace,
                    record_type="change_decision",
                    record_id=decision.decision_id,
                    record_revision=decision.revision,
                    action="change_decided",
                    result=decision.choice.value,
                    actor=approver,
                    authority_revision=(
                        f"role:{membership.role_revision}:member:{membership.membership_revision}"
                    ),
                    correlation_id=decision.correlation_id,
                    causation_id=decision.causation_id,
                    occurred_at=decision.occurred_at,
                    safe_projection={
                        "proposal_id": proposal.proposal_id,
                        "proposal_digest": proposal.canonical_digest,
                    },
                )
        if expired:
            raise PermissionDeniedError("change proposal validity expired")
        assert decided_proposal is not None
        return decided_proposal, decision

    def expire_change_proposal(
        self,
        *,
        proposal: ChangeProposal,
        actor: Principal,
        occurred_at: datetime,
    ) -> ChangeProposal:
        with self._transaction() as connection:
            membership = self._require_current_membership(
                connection,
                actor=actor,
                action=AuthorizationAction.DECIDE_CHANGE,
                namespace=proposal.namespace,
            )
            if proposal.state is not ChangeState.PENDING or occurred_at < proposal.expires_at:
                raise ConflictError("change proposal is not expirable")
            changed = connection.execute(
                """UPDATE p6_change_proposals
                SET state = 'expired', revision = revision + 1
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND proposal_id = ? AND revision = ? AND state = 'pending'""",
                (*_ns(proposal.namespace), proposal.proposal_id, proposal.revision),
            )
            if changed.rowcount != 1:
                raise ConflictError("change expiry lost its atomic claim")
            expired = replace(proposal, state=ChangeState.EXPIRED, revision=proposal.revision + 1)
            self._insert_governance_audit(
                connection,
                namespace=proposal.namespace,
                record_type="change_proposal",
                record_id=proposal.proposal_id,
                record_revision=expired.revision,
                action="change_expired",
                result="expired",
                actor=actor,
                authority_revision=(
                    f"role:{membership.role_revision}:member:{membership.membership_revision}"
                ),
                correlation_id=proposal.correlation_id,
                causation_id=proposal.proposal_id,
                occurred_at=occurred_at,
                safe_projection={"change_kind": proposal.change_kind.value},
            )
        return expired

    def mark_change_proposal_stale(
        self,
        *,
        proposal: ChangeProposal,
        actor: Principal,
        occurred_at: datetime,
    ) -> ChangeProposal:
        with self._transaction() as connection:
            membership = self._require_current_membership(
                connection,
                actor=actor,
                action=AuthorizationAction.APPLY_CHANGE,
                namespace=proposal.namespace,
            )
            row = connection.execute(
                """SELECT * FROM p6_change_proposals
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND proposal_id = ?""",
                (*_ns(proposal.namespace), proposal.proposal_id),
            ).fetchone()
            if row is None or self._change_proposal_from_row(row) != proposal:
                raise ConflictError("change proposal stale-state claim was refused")
            if proposal.state not in {ChangeState.PENDING, ChangeState.APPROVED}:
                raise ConflictError("change proposal is already terminal")
            changed = connection.execute(
                """UPDATE p6_change_proposals
                SET state = 'stale', revision = revision + 1
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND proposal_id = ? AND revision = ?
                  AND state IN ('pending', 'approved')""",
                (*_ns(proposal.namespace), proposal.proposal_id, proposal.revision),
            )
            if changed.rowcount != 1:
                raise ConflictError("change stale-state update lost its atomic claim")
            stale = replace(proposal, state=ChangeState.STALE, revision=proposal.revision + 1)
            self._insert_governance_audit(
                connection,
                namespace=proposal.namespace,
                record_type="change_proposal",
                record_id=proposal.proposal_id,
                record_revision=stale.revision,
                action="change_stale",
                result="stale",
                actor=actor,
                authority_revision=(
                    f"role:{membership.role_revision}:member:{membership.membership_revision}"
                ),
                correlation_id=proposal.correlation_id,
                causation_id=proposal.proposal_id,
                occurred_at=occurred_at,
                safe_projection={"change_kind": proposal.change_kind.value},
            )
        return stale

    def list_change_proposals(self, namespace: Namespace) -> tuple[ChangeProposal, ...]:
        rows = self._connection.execute(
            """SELECT * FROM p6_change_proposals
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
            ORDER BY issued_at, proposal_id""",
            _ns(namespace),
        ).fetchall()
        return tuple(self._change_proposal_from_row(row) for row in rows)

    def list_change_decisions(self, namespace: Namespace) -> tuple[ChangeDecision, ...]:
        rows = self._connection.execute(
            """SELECT * FROM p6_change_decisions
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
            ORDER BY occurred_at, decision_id""",
            _ns(namespace),
        ).fetchall()
        return tuple(self._change_decision_from_row(row) for row in rows)

    def _validated_change_approval(
        self,
        connection: sqlite3.Connection,
        *,
        proposal: ChangeProposal,
        decision_id: str,
        actor: Principal,
        occurred_at: datetime,
    ) -> tuple[ChangeDecision, Membership]:
        actor_membership = self._require_current_membership(
            connection,
            actor=actor,
            action=AuthorizationAction.APPLY_CHANGE,
            namespace=proposal.namespace,
        )
        if (
            proposal.state is not ChangeState.APPROVED
            or proposal.decision_id != decision_id
            or occurred_at >= proposal.expires_at
            or proposal.consumed_at is not None
        ):
            raise PermissionDeniedError("approved change is stale or expired")
        row = connection.execute(
            """SELECT * FROM p6_change_decisions
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND decision_id = ? AND proposal_id = ?""",
            (*_ns(proposal.namespace), decision_id, proposal.proposal_id),
        ).fetchone()
        if row is None:
            raise PermissionDeniedError("change decision was not found")
        decision = self._change_decision_from_row(row)
        if (
            decision.choice is not ChangeChoice.APPROVE
            or decision.proposal_revision != proposal.revision - 1
            or decision.proposal_digest != proposal.canonical_digest
            or decision.consumed_at is not None
            or occurred_at > decision.valid_until
        ):
            raise PermissionDeniedError("approved change decision is stale or expired")
        proposer = self.get_principal(proposal.namespace.tenant_id, proposal.proposer_principal_id)
        proposer_membership = self._membership_from_row(
            self._membership_row(
                connection, proposal.namespace.tenant_id, proposal.proposer_principal_id
            )
        )
        approver = self.get_principal(proposal.namespace.tenant_id, decision.approver_principal_id)
        approver_membership = self._membership_from_row(
            self._membership_row(
                connection, proposal.namespace.tenant_id, decision.approver_principal_id
            )
        )
        if (
            proposer.principal_id == approver.principal_id
            or proposer_membership.status is not MembershipStatus.ACTIVE
            or approver_membership.status is not MembershipStatus.ACTIVE
            or proposer.revision != proposal.proposer_role_revision
            or proposer_membership.role_revision != proposal.proposer_role_revision
            or proposer_membership.membership_revision != proposal.proposer_membership_revision
            or approver.revision != decision.approver_role_revision
            or approver_membership.role_revision != decision.approver_role_revision
            or approver_membership.membership_revision != decision.approver_membership_revision
            or HumanRole.TENANT_ADMIN not in proposer.roles
            or HumanRole.TENANT_ADMIN not in approver.roles
        ):
            raise PermissionDeniedError("change principal authority became stale")
        return decision, actor_membership

    def _consume_change_rows(
        self,
        connection: sqlite3.Connection,
        *,
        proposal: ChangeProposal,
        decision: ChangeDecision,
        occurred_at: datetime,
    ) -> None:
        proposal_update = connection.execute(
            """UPDATE p6_change_proposals
            SET state = 'applied', consumed_at = ?, revision = revision + 1
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND proposal_id = ? AND revision = ? AND state = 'approved'
              AND consumed_at IS NULL""",
            (
                datetime_to_z(occurred_at),
                *_ns(proposal.namespace),
                proposal.proposal_id,
                proposal.revision,
            ),
        )
        decision_update = connection.execute(
            """UPDATE p6_change_decisions
            SET consumed_at = ?, revision = revision + 1
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND decision_id = ? AND revision = ? AND consumed_at IS NULL""",
            (
                datetime_to_z(occurred_at),
                *_ns(proposal.namespace),
                decision.decision_id,
                decision.revision,
            ),
        )
        if proposal_update.rowcount != 1 or decision_update.rowcount != 1:
            raise ConflictError("change approval consumption lost its atomic claim")

    def _authorize_draft_confirmation(
        self,
        connection: sqlite3.Connection,
        *,
        draft: ColleagueDraft,
        actor: Principal,
        change_decision_id: str | None,
        occurred_at: datetime,
    ) -> None:
        authority_changed = any(
            item.section in {DiffSection.MANDATE, DiffSection.POLICY}
            and item.classification.value != "unchanged"
            for item in draft.diff
        )
        if not authority_changed:
            self._require_current_membership(
                connection,
                actor=actor,
                action=AuthorizationAction.APPLY_CHANGE,
                namespace=draft.namespace,
            )
            if change_decision_id is not None:
                raise PermissionDeniedError("Profile-only change cannot consume unrelated approval")
            return
        if change_decision_id is None:
            raise PermissionDeniedError("authority change requires a separate Admin approval")
        row = connection.execute(
            """SELECT * FROM p6_change_proposals
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND decision_id = ?""",
            (*_ns(draft.namespace), change_decision_id),
        ).fetchone()
        if row is None:
            raise PermissionDeniedError("authority change approval was refused")
        proposal = self._change_proposal_from_row(row)
        if (
            proposal.change_kind is not ChangeKind.DRAFT
            or proposal.target_id != draft.draft_id
            or proposal.target_revision != draft.revision
            or proposal.canonical_digest != draft.canonical_digest
            or (
                proposal.base_profile_revision,
                proposal.base_mandate_revision,
                proposal.base_policy_revision,
            )
            != (
                draft.base_profile_revision,
                draft.base_mandate_revision,
                draft.base_policy_revision,
            )
        ):
            raise StaleConflictError("authority change approval does not bind this draft")
        decision, membership = self._validated_change_approval(
            connection,
            proposal=proposal,
            decision_id=change_decision_id,
            actor=actor,
            occurred_at=occurred_at,
        )
        self._consume_change_rows(
            connection, proposal=proposal, decision=decision, occurred_at=occurred_at
        )
        self._insert_governance_audit(
            connection,
            namespace=draft.namespace,
            record_type="change_proposal",
            record_id=proposal.proposal_id,
            record_revision=proposal.revision + 1,
            action="change_applied",
            result="applied",
            actor=actor,
            authority_revision=(
                f"role:{membership.role_revision}:member:{membership.membership_revision}"
            ),
            correlation_id=proposal.correlation_id,
            causation_id=decision.decision_id,
            occurred_at=occurred_at,
            safe_projection={
                "change_kind": "draft",
                "canonical_digest": proposal.canonical_digest,
            },
        )

    def apply_membership_change(
        self,
        *,
        proposal: ChangeProposal,
        decision_id: str,
        actor: Principal,
        occurred_at: datetime,
    ) -> Membership:
        if proposal.change_kind is not ChangeKind.MEMBERSHIP:
            raise PermissionDeniedError("change kind was refused")
        with self._transaction() as connection:
            row = connection.execute(
                """SELECT * FROM p6_change_proposals
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND proposal_id = ?""",
                (*_ns(proposal.namespace), proposal.proposal_id),
            ).fetchone()
            if row is None or self._change_proposal_from_row(row) != proposal:
                raise StaleConflictError("membership change proposal is stale")
            decision, actor_membership = self._validated_change_approval(
                connection,
                proposal=proposal,
                decision_id=decision_id,
                actor=actor,
                occurred_at=occurred_at,
            )
            target = self._membership_from_row(
                self._membership_row(connection, proposal.namespace.tenant_id, proposal.target_id)
            )
            expected_digest = governance_change_digest(
                change_kind=proposal.change_kind,
                target_id=target.principal_id,
                target_revision=target.membership_revision,
                proposed_role=proposal.proposed_role,
                proposed_status=proposal.proposed_status,
                proposed_colleague_ids=proposal.proposed_colleague_ids,
            )
            if (
                target.membership_revision != proposal.target_revision
                or proposal.canonical_digest != expected_digest
                or proposal.proposed_role is None
                or proposal.proposed_status is None
            ):
                raise StaleConflictError("membership change target is stale")
            current_principal = self.get_principal(
                proposal.namespace.tenant_id, target.principal_id
            )
            role_changed = current_principal.roles != (proposal.proposed_role,)
            removes_admin = HumanRole.TENANT_ADMIN in current_principal.roles and (
                proposal.proposed_role is not HumanRole.TENANT_ADMIN
                or proposal.proposed_status is MembershipStatus.REVOKED
            )
            if removes_admin:
                admin_count = connection.execute(
                    """SELECT COUNT(*) AS count FROM p6_memberships
                    WHERE tenant_id = ? AND status = 'active'
                      AND roles_json = '[\"tenant_admin\"]'""",
                    (proposal.namespace.tenant_id,),
                ).fetchone()["count"]
                if admin_count <= 2:
                    raise PermissionDeniedError(
                        "membership change would break two-person governance"
                    )
            new_role_revision = target.role_revision + int(role_changed)
            new_membership_revision = target.membership_revision + 1
            updated_principal = replace(
                current_principal,
                roles=(proposal.proposed_role,),
                revision=new_role_revision,
            )
            if role_changed:
                serialized = to_storage_json(updated_principal)
                changed_principal = connection.execute(
                    """UPDATE domain_records
                    SET revision = ?, payload_json = ?, actor_principal_id = ?,
                        correlation_id = ?, causation_id = ?, occurred_at = ?
                    WHERE tenant_id = ? AND namespace_scope = 'principal'
                      AND namespace_scope_id = ? AND record_type = 'principal'
                      AND record_id = ? AND revision = ?""",
                    (
                        updated_principal.revision,
                        serialized,
                        actor.principal_id,
                        proposal.correlation_id,
                        decision.decision_id,
                        datetime_to_z(occurred_at),
                        proposal.namespace.tenant_id,
                        target.principal_id,
                        target.principal_id,
                        current_principal.revision,
                    ),
                )
                if changed_principal.rowcount != 1:
                    raise ConflictError("principal role update lost its atomic claim")
                self._insert_audit(
                    connection,
                    record=updated_principal,
                    record_type="principal",
                    record_id=updated_principal.principal_id,
                    revision=updated_principal.revision,
                    actor=actor,
                    correlation_id=proposal.correlation_id,
                    causation_id=decision.decision_id,
                    occurred_at=occurred_at,
                    serialized=serialized,
                )
            changed = connection.execute(
                """UPDATE p6_memberships
                SET roles_json = ?, colleague_scopes_json = ?, status = ?,
                    role_revision = ?, membership_revision = ?, updated_at = ?,
                    correlation_id = ?, causation_id = ?, revision = revision + 1
                WHERE tenant_id = ? AND principal_id = ? AND membership_revision = ?
                  AND revision = ?""",
                (
                    _safe_json([proposal.proposed_role.value]),
                    _safe_json(list(proposal.proposed_colleague_ids)),
                    proposal.proposed_status.value,
                    new_role_revision,
                    new_membership_revision,
                    datetime_to_z(occurred_at),
                    proposal.correlation_id,
                    decision.decision_id,
                    proposal.namespace.tenant_id,
                    target.principal_id,
                    target.membership_revision,
                    target.revision,
                ),
            )
            if changed.rowcount != 1:
                raise ConflictError("membership update lost its atomic claim")
            connection.execute(
                """UPDATE p4_sessions
                SET revoked_at = ?, revoked_reason = 'membership_revision_changed',
                    revision = revision + 1
                WHERE tenant_id = ? AND principal_id = ? AND revoked_at IS NULL""",
                (datetime_to_z(occurred_at), proposal.namespace.tenant_id, target.principal_id),
            )
            self._consume_change_rows(
                connection, proposal=proposal, decision=decision, occurred_at=occurred_at
            )
            updated = replace(
                target,
                roles=(proposal.proposed_role,),
                colleague_ids=proposal.proposed_colleague_ids,
                status=proposal.proposed_status,
                role_revision=new_role_revision,
                membership_revision=new_membership_revision,
                updated_at=occurred_at,
                correlation_id=proposal.correlation_id,
                causation_id=decision.decision_id,
                revision=target.revision + 1,
            )
            self._insert_governance_audit(
                connection,
                namespace=Namespace.principal(proposal.namespace.tenant_id, target.principal_id),
                record_type="membership",
                record_id=target.membership_id,
                record_revision=updated.revision,
                action="membership_changed",
                result=proposal.proposed_status.value,
                actor=actor,
                authority_revision=(
                    f"role:{actor_membership.role_revision}:member:"
                    f"{actor_membership.membership_revision}"
                ),
                correlation_id=proposal.correlation_id,
                causation_id=decision.decision_id,
                occurred_at=occurred_at,
                safe_projection={
                    "role": proposal.proposed_role.value,
                    "scope_count": len(proposal.proposed_colleague_ids),
                    "membership_revision": new_membership_revision,
                },
            )
        return updated

    def _consume_admin_enrollment_authority(
        self,
        connection: sqlite3.Connection,
        *,
        decision_id: str,
        role: HumanRole,
        colleague_ids: tuple[str, ...],
        actor: Principal,
        occurred_at: datetime,
    ) -> None:
        row = connection.execute(
            """SELECT * FROM p6_change_proposals
            WHERE tenant_id = ? AND namespace_scope = 'tenant' AND namespace_scope_id = ''
              AND decision_id = ?""",
            (actor.namespace.tenant_id, decision_id),
        ).fetchone()
        if row is None:
            raise PermissionDeniedError("Admin enrollment change was not found")
        proposal = self._change_proposal_from_row(row)
        expected = governance_change_digest(
            change_kind=ChangeKind.ADMIN_ENROLLMENT,
            target_id=proposal.target_id,
            target_revision=proposal.target_revision,
            proposed_role=role,
            proposed_status=MembershipStatus.ACTIVE,
            proposed_colleague_ids=colleague_ids,
        )
        if (
            proposal.change_kind is not ChangeKind.ADMIN_ENROLLMENT
            or proposal.proposed_role is not role
            or proposal.proposed_status is not MembershipStatus.ACTIVE
            or proposal.proposed_colleague_ids != colleague_ids
            or proposal.canonical_digest != expected
        ):
            raise PermissionDeniedError("Admin enrollment change binding was refused")
        decision, membership = self._validated_change_approval(
            connection,
            proposal=proposal,
            decision_id=decision_id,
            actor=actor,
            occurred_at=occurred_at,
        )
        self._consume_change_rows(
            connection, proposal=proposal, decision=decision, occurred_at=occurred_at
        )
        self._insert_governance_audit(
            connection,
            namespace=proposal.namespace,
            record_type="change_proposal",
            record_id=proposal.proposal_id,
            record_revision=proposal.revision + 1,
            action="admin_enrollment_authority_applied",
            result="applied",
            actor=actor,
            authority_revision=(
                f"role:{membership.role_revision}:member:{membership.membership_revision}"
            ),
            correlation_id=proposal.correlation_id,
            causation_id=decision.decision_id,
            occurred_at=occurred_at,
            safe_projection={"role": role.value, "scope_count": len(colleague_ids)},
        )

    def consume_admin_enrollment_change(
        self,
        *,
        decision_id: str,
        role: HumanRole,
        colleague_ids: tuple[str, ...],
        actor: Principal,
        occurred_at: datetime,
    ) -> None:
        with self._transaction() as connection:
            self._consume_admin_enrollment_authority(
                connection,
                decision_id=decision_id,
                role=role,
                colleague_ids=colleague_ids,
                actor=actor,
                occurred_at=occurred_at,
            )

    def _bind_effect_approval_authority(
        self,
        connection: sqlite3.Connection,
        *,
        namespace: Namespace,
        proposal: EffectProposal,
        decision: HumanApprovalDecision,
        approver: Principal,
        occurred_at: datetime,
    ) -> None:
        membership = self._require_current_membership(
            connection,
            actor=approver,
            action=AuthorizationAction.DECIDE_EFFECT,
            namespace=namespace,
        )
        connection.execute(
            """
            INSERT INTO p6_effect_approval_bindings(
              schema_version, tenant_id, namespace_scope, namespace_scope_id,
              approval_decision_id, principal_id, principal_revision, role_revision,
              membership_revision, proposal_id, proposal_revision, proposal_digest,
              valid_until, consumed_at, revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                SCHEMA_VERSION,
                *_ns(namespace),
                decision.approval_decision_id,
                approver.principal_id,
                approver.revision,
                membership.role_revision,
                membership.membership_revision,
                proposal.proposal_id,
                proposal.revision,
                proposal.proposal_digest,
                datetime_to_z(decision.valid_until),
                datetime_to_z(occurred_at),
            ),
        )
        self._insert_governance_audit(
            connection,
            namespace=namespace,
            record_type="effect_approval_binding",
            record_id=decision.approval_decision_id,
            record_revision=1,
            action="effect_decision_bound",
            result=decision.choice.value,
            actor=approver,
            authority_revision=(
                f"role:{membership.role_revision}:member:{membership.membership_revision}"
            ),
            correlation_id=decision.correlation_id,
            causation_id=decision.proposal_id,
            occurred_at=occurred_at,
            safe_projection={
                "proposal_id": proposal.proposal_id,
                "proposal_revision": proposal.revision,
                "proposal_digest": proposal.proposal_digest,
            },
        )

    def require_current_effect_approval(
        self,
        *,
        namespace: Namespace,
        approval_decision_id: str,
        evaluated_at: datetime,
    ) -> None:
        row = self._connection.execute(
            """SELECT * FROM p6_effect_approval_bindings
            WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
              AND approval_decision_id = ?""",
            (*_ns(namespace), approval_decision_id),
        ).fetchone()
        if row is None or evaluated_at > datetime_from_z(row["valid_until"]):
            raise PermissionDeniedError("effect approval authority was refused")
        principal = self.get_principal(namespace.tenant_id, row["principal_id"])
        membership = self.membership_for_principal(namespace.tenant_id, row["principal_id"])
        if (
            principal.kind is not PrincipalKind.HUMAN
            or principal.revision != row["principal_revision"]
            or membership.status is not MembershipStatus.ACTIVE
            or membership.role_revision != row["role_revision"]
            or membership.membership_revision != row["membership_revision"]
            or not membership.allows_namespace(namespace)
            or set(membership.roles).isdisjoint({HumanRole.TENANT_ADMIN, HumanRole.COLLEAGUE_USER})
        ):
            raise PermissionDeniedError("effect approval authority became stale")

    def audit_export(
        self,
        *,
        query: AuditExportQuery,
        actor: Principal,
        membership: Membership,
        occurred_at: datetime,
        audit_id: str,
    ) -> tuple[AuditExportRecord, ...]:
        allowed_types = {
            "principal",
            "membership",
            "governance_credential",
            "change_proposal",
            "change_decision",
            "effect_approval_binding",
            "input_event",
            "timer_occurrence",
            "wake_cycle",
            "agenda_item",
            "decision",
            "effect_proposal",
            "human_approval",
            "effect_attempt",
            "action_result",
            "finite_work",
            "profile",
            "mandate",
            "colleague_policy",
        }
        if not set(query.record_types).issubset(allowed_types):
            raise PermissionDeniedError("audit export record type was refused")
        with self._transaction() as connection:
            current = self._require_current_membership(
                connection,
                actor=actor,
                action=AuthorizationAction.EXPORT_AUDIT,
                namespace=query.namespace,
            )
            if current != membership:
                raise PermissionDeniedError("audit export authority was refused")
            placeholders = ",".join("?" for _ in query.record_types)
            governance_rows = connection.execute(
                f"""
                SELECT * FROM p6_governance_audit
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND occurred_at >= ? AND occurred_at <= ?
                  AND record_type IN ({placeholders})
                """,
                (
                    *_ns(query.namespace),
                    datetime_to_z(query.start_at),
                    datetime_to_z(query.end_at),
                    *query.record_types,
                ),
            ).fetchall()
            base_rows = connection.execute(
                f"""
                SELECT * FROM audit_records
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND occurred_at >= ? AND occurred_at <= ?
                  AND record_type IN ({placeholders})
                """,
                (
                    *_ns(query.namespace),
                    datetime_to_z(query.start_at),
                    datetime_to_z(query.end_at),
                    *query.record_types,
                ),
            ).fetchall()
            records: list[AuditExportRecord] = []
            for row in governance_rows:
                records.append(
                    AuditExportRecord(
                        namespace=_namespace_from_row(row),
                        record_type=row["record_type"],
                        record_id=row["record_id"],
                        record_revision=row["record_revision"],
                        action=row["action"],
                        result=row["result"],
                        actor_principal_id=row["actor_principal_id"],
                        actor_kind=PrincipalKind(row["actor_kind"]),
                        authority_revision=row["authority_revision"],
                        correlation_id=row["correlation_id"],
                        causation_id=row["causation_id"],
                        occurred_at=datetime_from_z(row["occurred_at"]),
                        safe_digest=row["safe_digest"],
                        safe_projection=FrozenJsonObject.from_mapping(
                            cast(dict[str, object], json.loads(row["safe_projection_json"]))
                        ),
                        schema_version=row["schema_version"],
                    )
                )
            for row in base_rows:
                principal = self.get_principal(query.namespace.tenant_id, row["actor_principal_id"])
                records.append(
                    AuditExportRecord(
                        namespace=_namespace_from_row(row),
                        record_type=row["record_type"],
                        record_id=row["record_id"],
                        record_revision=row["record_revision"],
                        action="recorded",
                        result="persisted",
                        actor_principal_id=row["actor_principal_id"],
                        actor_kind=principal.kind,
                        authority_revision=f"record:{row['record_revision']}",
                        correlation_id=row["correlation_id"],
                        causation_id=row["causation_id"] or row["record_id"],
                        occurred_at=datetime_from_z(row["occurred_at"]),
                        safe_digest=row["payload_digest"],
                        safe_projection=FrozenJsonObject.from_mapping(
                            {"private_payload_redacted": True}
                        ),
                        schema_version=row["schema_version"],
                    )
                )
            ordered = tuple(
                sorted(
                    records,
                    key=lambda item: (
                        item.occurred_at,
                        item.record_type,
                        item.record_id,
                        item.record_revision,
                    ),
                )[: query.limit]
            )
            result_binding = _safe_digest(
                {
                    "query": contract_to_public_data(query),
                    "records": [item.safe_digest for item in ordered],
                }
            ).removeprefix("sha256:")[:24]
            export_record_id = f"{audit_id}:{result_binding}"
            existing_export = connection.execute(
                """SELECT 1 FROM p6_governance_audit
                WHERE tenant_id = ? AND namespace_scope = ? AND namespace_scope_id = ?
                  AND record_type = 'audit_export' AND record_id = ?
                  AND action = 'audit_exported'""",
                (*_ns(query.namespace), export_record_id),
            ).fetchone()
            if existing_export is None:
                self._insert_governance_audit(
                    connection,
                    namespace=query.namespace,
                    record_type="audit_export",
                    record_id=export_record_id,
                    record_revision=1,
                    action="audit_exported",
                    result="completed",
                    actor=actor,
                    authority_revision=(
                        f"role:{membership.role_revision}:member:{membership.membership_revision}"
                    ),
                    correlation_id="correlation:" + audit_id.removeprefix("export:"),
                    causation_id=audit_id,
                    occurred_at=occurred_at,
                    safe_projection={
                        "record_count": len(ordered),
                        "limit": query.limit,
                        "record_type_count": len(query.record_types),
                        "result_binding": result_binding,
                    },
                )
        return ordered

    def p6_studio_snapshot(
        self, *, session: AuthenticatedSession, evaluated_at: datetime
    ) -> P6StudioSnapshot:
        governed, membership = self.governed_session(
            credential_digest=session.credential_digest,
            evaluated_at=evaluated_at,
        )
        if governed.session_id != session.session_id:
            raise PermissionDeniedError("Studio session binding was refused")
        if HumanRole.COLLEAGUE_USER in membership.roles:
            credentials: tuple[GovernanceCredential, ...] = ()
            proposals: tuple[ChangeProposal, ...] = ()
            decisions: tuple[ChangeDecision, ...] = ()
        else:
            rows = self._connection.execute(
                """SELECT * FROM p6_governance_credentials
                WHERE tenant_id = ? ORDER BY issued_at, credential_id""",
                (session.tenant_id,),
            ).fetchall()
            credentials = tuple(
                credential
                for row in rows
                if (credential := self._credential_from_row(row)).colleague_ids == ("*",)
                or set(credential.colleague_ids).intersection(membership.colleague_ids)
                or membership.colleague_ids == ("*",)
            )
            proposal_values: list[ChangeProposal] = []
            decision_values: list[ChangeDecision] = []
            if session.active_colleague_id is not None:
                namespace = session.colleague_namespace()
                proposal_values.extend(self.list_change_proposals(namespace))
                decision_values.extend(self.list_change_decisions(namespace))
            if membership.colleague_ids == ("*",):
                proposal_values.extend(
                    self.list_change_proposals(Namespace.tenant(session.tenant_id))
                )
                decision_values.extend(
                    self.list_change_decisions(Namespace.tenant(session.tenant_id))
                )
            proposals = tuple(proposal_values)
            decisions = tuple(decision_values)
        transition = self._connection.execute(
            """SELECT state FROM p6_bootstrap_transitions
            WHERE tenant_id = ? AND transition_id = 'transition:second-admin'""",
            (session.tenant_id,),
        ).fetchone()
        if transition is None:
            raise ConflictError("bootstrap transition state is missing")
        return P6StudioSnapshot(
            session=governed,
            membership=membership,
            credentials=credentials,
            change_proposals=proposals,
            change_decisions=decisions,
            bootstrap_transition_state=transition["state"],
            generated_at=evaluated_at,
        )
