# SPDX-License-Identifier: Apache-2.0

"""Stable ports for P4 local authentication and Studio persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from digital_colleagues.application.p4_contracts import (
    AuthenticatedSession,
    BootstrapRecord,
    MutationReplay,
    StudioSnapshot,
)
from digital_colleagues.core.authority import Mandate, Profile
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import Principal, PrincipalKind
from digital_colleagues.core.work import FiniteWork


class CredentialDigestPort(Protocol):
    def digest(self, purpose: str, plaintext: str) -> str: ...

    def matches(self, expected: str, actual: str) -> bool: ...


class SecretTokenPort(Protocol):
    def issue(self, byte_count: int) -> str: ...


class AuthenticationPersistencePort(Protocol):
    def get_bootstrap(self, tenant_id: str) -> BootstrapRecord | None: ...

    def create_bootstrap(self, record: BootstrapRecord) -> bool: ...

    def claim_bootstrap_retrieval(
        self, *, tenant_id: str, token_digest: str, occurred_at: datetime
    ) -> BootstrapRecord: ...

    def consume_bootstrap(
        self,
        *,
        tenant_id: str,
        token_digest: str,
        principal: Principal,
        session: AuthenticatedSession,
        occurred_at: datetime,
    ) -> AuthenticatedSession: ...

    def get_session(
        self, *, credential_digest: str, evaluated_at: datetime
    ) -> AuthenticatedSession: ...

    def set_active_colleague(
        self, *, session: AuthenticatedSession, colleague_id: str, occurred_at: datetime
    ) -> AuthenticatedSession: ...

    def get_mutation_replay(
        self, *, session: AuthenticatedSession, action: str, idempotency_key: str
    ) -> MutationReplay | None: ...

    def record_mutation_replay(
        self,
        *,
        session: AuthenticatedSession,
        action: str,
        idempotency_key: str,
        replay: MutationReplay,
        occurred_at: datetime,
    ) -> None: ...


class StudioPersistencePort(Protocol):
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
    ) -> bool: ...

    def assign_work(self, work: FiniteWork, *, idempotency_key: str) -> tuple[FiniteWork, bool]: ...

    def list_record_payloads(self, namespace: Namespace, record_type: str) -> tuple[str, ...]: ...

    def first_principal(self, tenant_id: str, kind: PrincipalKind) -> Principal: ...

    def pending_namespaces(self) -> tuple[Namespace, ...]: ...

    def studio_snapshot(self, namespace: Namespace) -> StudioSnapshot: ...
