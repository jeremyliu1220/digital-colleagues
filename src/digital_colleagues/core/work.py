# SPDX-License-Identifier: Apache-2.0

"""Finite work, durable responsibility, obligation, and completion primitives."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from digital_colleagues.core.common import (
    SCHEMA_VERSION,
    freeze_strings,
    require_revision,
    require_schema_version,
    require_stable_id,
    require_text,
    require_utc,
)
from digital_colleagues.core.errors import CoreInvariantError, LifecycleError, RevisionMismatchError
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import Principal


@dataclass(frozen=True, slots=True)
class CompletionEvidence:
    evidence_id: str
    kind: str
    safe_summary: str
    observed_at: datetime
    actor: Principal
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        require_stable_id(self.evidence_id, "evidence_id")
        object.__setattr__(self, "kind", require_stable_id(self.kind, "evidence kind"))
        object.__setattr__(
            self,
            "safe_summary",
            require_text(self.safe_summary, "safe_summary", maximum=1_024),
        )
        require_utc(self.observed_at, "observed_at")


class WorkState(StrEnum):
    PLANNED = "planned"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


_WORK_TRANSITIONS = {
    WorkState.PLANNED: frozenset({WorkState.READY, WorkState.CANCELLED}),
    WorkState.READY: frozenset({WorkState.IN_PROGRESS, WorkState.BLOCKED, WorkState.CANCELLED}),
    WorkState.IN_PROGRESS: frozenset({WorkState.BLOCKED, WorkState.COMPLETED, WorkState.CANCELLED}),
    WorkState.BLOCKED: frozenset({WorkState.READY, WorkState.IN_PROGRESS, WorkState.CANCELLED}),
    WorkState.COMPLETED: frozenset(),
    WorkState.CANCELLED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class FiniteWork:
    namespace: Namespace
    work_id: str
    title: str
    description: str
    state: WorkState
    dependency_ids: tuple[str, ...]
    responsibility_ids: tuple[str, ...]
    assignee_principal_id: str
    actor: Principal
    mandate_id: str
    mandate_revision: int
    completion_evidence: tuple[CompletionEvidence, ...]
    correlation_id: str
    causation_id: str | None
    created_at: datetime
    updated_at: datetime
    revision: int
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.namespace.require_colleague()
        require_stable_id(self.work_id, "work_id")
        object.__setattr__(self, "title", require_text(self.title, "title"))
        object.__setattr__(self, "description", require_text(self.description, "description"))
        if not isinstance(self.state, WorkState):
            raise CoreInvariantError("work state must be explicit")
        dependencies = freeze_strings(self.dependency_ids, "dependency_ids")
        for dependency_id in dependencies:
            require_stable_id(dependency_id, "dependency_id")
        if self.work_id in dependencies:
            raise CoreInvariantError("finite work cannot depend on itself")
        object.__setattr__(self, "dependency_ids", dependencies)
        responsibilities = freeze_strings(
            self.responsibility_ids, "responsibility_ids", allow_empty=False
        )
        for responsibility_id in responsibilities:
            require_stable_id(responsibility_id, "responsibility_id")
        object.__setattr__(self, "responsibility_ids", responsibilities)
        require_stable_id(self.assignee_principal_id, "assignee_principal_id")
        self.namespace.require_same_tenant(self.actor.namespace)
        require_stable_id(self.mandate_id, "mandate_id")
        require_revision(self.mandate_revision, "mandate_revision")
        evidence = tuple(self.completion_evidence)
        if not all(isinstance(item, CompletionEvidence) for item in evidence):
            raise CoreInvariantError("completion_evidence contains an invalid record")
        if self.state is WorkState.COMPLETED and not evidence:
            raise CoreInvariantError("completed work requires completion evidence")
        if self.state is not WorkState.COMPLETED and evidence:
            raise CoreInvariantError("only completed work may carry completion evidence")
        for item in evidence:
            self.namespace.require_same_tenant(item.actor.namespace)
        object.__setattr__(self, "completion_evidence", evidence)
        require_stable_id(self.correlation_id, "correlation_id")
        if self.causation_id is not None:
            require_stable_id(self.causation_id, "causation_id")
        require_utc(self.created_at, "created_at")
        require_utc(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            raise CoreInvariantError("updated_at cannot precede created_at")
        require_revision(self.revision)


def transition_work(
    work: FiniteWork,
    *,
    expected_revision: int,
    next_state: WorkState,
    occurred_at: datetime,
    satisfied_dependency_ids: frozenset[str] = frozenset(),
    completion_evidence: tuple[CompletionEvidence, ...] = (),
) -> FiniteWork:
    """Return a new work revision after validating an explicit transition."""

    require_utc(occurred_at, "occurred_at")
    if expected_revision != work.revision:
        raise RevisionMismatchError("finite work revision is stale")
    if next_state not in _WORK_TRANSITIONS[work.state]:
        raise LifecycleError("finite work lifecycle transition is invalid")
    if next_state in {WorkState.READY, WorkState.IN_PROGRESS}:
        missing = set(work.dependency_ids) - satisfied_dependency_ids
        if missing:
            raise LifecycleError("finite work dependencies are not satisfied")
    if next_state is WorkState.COMPLETED and not completion_evidence:
        raise LifecycleError("completion requires explicit evidence")
    if next_state is not WorkState.COMPLETED and completion_evidence:
        raise LifecycleError("completion evidence is only valid for completion")
    return replace(
        work,
        state=next_state,
        completion_evidence=completion_evidence,
        updated_at=occurred_at,
        revision=work.revision + 1,
    )


def validate_work_dependency_graph(works: tuple[FiniteWork, ...]) -> None:
    """Reject missing, cross-namespace, duplicate, or cyclic finite-work dependencies."""

    if not works:
        raise CoreInvariantError("work dependency graph must not be empty")
    namespace = works[0].namespace
    by_id: dict[str, FiniteWork] = {}
    for work in works:
        namespace.require_exact(work.namespace)
        if work.work_id in by_id:
            raise CoreInvariantError("work dependency graph contains a duplicate work ID")
        by_id[work.work_id] = work
    for work in works:
        if any(dependency_id not in by_id for dependency_id in work.dependency_ids):
            raise CoreInvariantError("work dependency graph references unknown work")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(work_id: str) -> None:
        if work_id in visiting:
            raise CoreInvariantError("work dependency graph contains a cycle")
        if work_id in visited:
            return
        visiting.add(work_id)
        for dependency_id in by_id[work_id].dependency_ids:
            visit(dependency_id)
        visiting.remove(work_id)
        visited.add(work_id)

    for work_id in sorted(by_id):
        visit(work_id)


class ResponsibilityState(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    FULFILLED = "fulfilled"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class Responsibility:
    namespace: Namespace
    responsibility_id: str
    mandate_id: str
    mandate_revision: int
    description: str
    owner_principal_id: str
    state: ResponsibilityState
    actor: Principal
    correlation_id: str
    causation_id: str | None
    created_at: datetime
    updated_at: datetime
    revision: int
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.namespace.require_colleague()
        require_stable_id(self.responsibility_id, "responsibility_id")
        require_stable_id(self.mandate_id, "mandate_id")
        require_revision(self.mandate_revision, "mandate_revision")
        object.__setattr__(self, "description", require_text(self.description, "description"))
        require_stable_id(self.owner_principal_id, "owner_principal_id")
        if not isinstance(self.state, ResponsibilityState):
            raise CoreInvariantError("responsibility state must be explicit")
        self.namespace.require_same_tenant(self.actor.namespace)
        require_stable_id(self.correlation_id, "correlation_id")
        if self.causation_id is not None:
            require_stable_id(self.causation_id, "causation_id")
        require_utc(self.created_at, "created_at")
        require_utc(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            raise CoreInvariantError("updated_at cannot precede created_at")
        require_revision(self.revision)


class ObligationState(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SATISFIED = "satisfied"
    WAIVED = "waived"
    OVERDUE = "overdue"


@dataclass(frozen=True, slots=True)
class Obligation:
    namespace: Namespace
    obligation_id: str
    responsibility_id: str
    description: str
    state: ObligationState
    due_at: datetime | None
    work_id: str | None
    resolution_evidence: tuple[CompletionEvidence, ...]
    actor: Principal
    correlation_id: str
    causation_id: str | None
    created_at: datetime
    updated_at: datetime
    revision: int
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.namespace.require_colleague()
        require_stable_id(self.obligation_id, "obligation_id")
        require_stable_id(self.responsibility_id, "responsibility_id")
        object.__setattr__(self, "description", require_text(self.description, "description"))
        if not isinstance(self.state, ObligationState):
            raise CoreInvariantError("obligation state must be explicit")
        if self.due_at is not None:
            require_utc(self.due_at, "due_at")
        if self.work_id is not None:
            require_stable_id(self.work_id, "work_id")
        evidence = tuple(self.resolution_evidence)
        if not all(isinstance(item, CompletionEvidence) for item in evidence):
            raise CoreInvariantError("resolution_evidence contains an invalid record")
        resolved = self.state in {ObligationState.SATISFIED, ObligationState.WAIVED}
        if resolved != bool(evidence):
            raise CoreInvariantError(
                "resolved obligations require evidence and only they may carry it"
            )
        for item in evidence:
            self.namespace.require_same_tenant(item.actor.namespace)
        object.__setattr__(self, "resolution_evidence", evidence)
        self.namespace.require_same_tenant(self.actor.namespace)
        require_stable_id(self.correlation_id, "correlation_id")
        if self.causation_id is not None:
            require_stable_id(self.causation_id, "causation_id")
        require_utc(self.created_at, "created_at")
        require_utc(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            raise CoreInvariantError("updated_at cannot precede created_at")
        require_revision(self.revision)
