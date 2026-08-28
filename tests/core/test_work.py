# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import dataclasses
import unittest

from digital_colleagues.core import (
    CompletionEvidence,
    FiniteWork,
    Obligation,
    ObligationState,
    Responsibility,
    ResponsibilityState,
    WorkState,
    transition_work,
    validate_work_dependency_graph,
)
from digital_colleagues.core.errors import CoreInvariantError, LifecycleError, RevisionMismatchError
from tests.core.fixtures import T0, T1, colleague_namespace, human_user


def completion_evidence() -> CompletionEvidence:
    return CompletionEvidence(
        evidence_id="evidence-001",
        kind="synthetic-check",
        safe_summary="All synthetic completion conditions passed.",
        observed_at=T1,
        actor=human_user(),
    )


def finite_work(*, state: WorkState = WorkState.PLANNED) -> FiniteWork:
    return FiniteWork(
        namespace=colleague_namespace(),
        work_id="work-001",
        title="Finite synthetic work",
        description="A bounded unit of work.",
        state=state,
        dependency_ids=("work-dependency-001",),
        responsibility_ids=("responsibility-main",),
        assignee_principal_id="principal-model",
        actor=human_user(),
        mandate_id="mandate-alpha",
        mandate_revision=1,
        completion_evidence=(),
        correlation_id="correlation-001",
        causation_id="input-event-001",
        created_at=T0,
        updated_at=T0,
        revision=1,
    )


def graph_work(work_id: str, dependency_ids: tuple[str, ...]) -> FiniteWork:
    return dataclasses.replace(
        finite_work(),
        work_id=work_id,
        dependency_ids=dependency_ids,
    )


class WorkTests(unittest.TestCase):
    def test_dependency_graph_rejects_missing_nodes_and_cycles(self) -> None:
        root = graph_work("work-root", ())
        child = graph_work("work-child", ("work-root",))
        validate_work_dependency_graph((child, root))
        with self.assertRaises(CoreInvariantError):
            validate_work_dependency_graph((graph_work("work-orphan", ("work-missing",)),))
        with self.assertRaises(CoreInvariantError):
            validate_work_dependency_graph(
                (
                    graph_work("work-cycle-a", ("work-cycle-b",)),
                    graph_work("work-cycle-b", ("work-cycle-a",)),
                )
            )

    def test_finite_work_dependency_and_revision_invariants(self) -> None:
        work = finite_work()
        with self.assertRaises(LifecycleError):
            transition_work(
                work,
                expected_revision=1,
                next_state=WorkState.READY,
                occurred_at=T1,
            )
        ready = transition_work(
            work,
            expected_revision=1,
            next_state=WorkState.READY,
            occurred_at=T1,
            satisfied_dependency_ids=frozenset({"work-dependency-001"}),
        )
        self.assertEqual(ready.state, WorkState.READY)
        self.assertEqual(ready.revision, 2)
        with self.assertRaises(RevisionMismatchError):
            transition_work(
                ready,
                expected_revision=1,
                next_state=WorkState.IN_PROGRESS,
                occurred_at=T1,
                satisfied_dependency_ids=frozenset({"work-dependency-001"}),
            )

    def test_completion_requires_evidence_and_is_terminal(self) -> None:
        ready = transition_work(
            finite_work(),
            expected_revision=1,
            next_state=WorkState.READY,
            occurred_at=T1,
            satisfied_dependency_ids=frozenset({"work-dependency-001"}),
        )
        active = transition_work(
            ready,
            expected_revision=2,
            next_state=WorkState.IN_PROGRESS,
            occurred_at=T1,
            satisfied_dependency_ids=frozenset({"work-dependency-001"}),
        )
        with self.assertRaises(LifecycleError):
            transition_work(
                active,
                expected_revision=3,
                next_state=WorkState.COMPLETED,
                occurred_at=T1,
            )
        completed = transition_work(
            active,
            expected_revision=3,
            next_state=WorkState.COMPLETED,
            occurred_at=T1,
            completion_evidence=(completion_evidence(),),
        )
        self.assertEqual(completed.state, WorkState.COMPLETED)
        self.assertEqual(len(completed.completion_evidence), 1)
        with self.assertRaises(LifecycleError):
            transition_work(
                completed,
                expected_revision=4,
                next_state=WorkState.IN_PROGRESS,
                occurred_at=T1,
            )

    def test_self_dependency_is_rejected(self) -> None:
        with self.assertRaises(CoreInvariantError):
            FiniteWork(
                namespace=colleague_namespace(),
                work_id="work-self",
                title="Invalid work",
                description="Synthetic invalid fixture.",
                state=WorkState.PLANNED,
                dependency_ids=("work-self",),
                responsibility_ids=("responsibility-main",),
                assignee_principal_id="principal-model",
                actor=human_user(),
                mandate_id="mandate-alpha",
                mandate_revision=1,
                completion_evidence=(),
                correlation_id="correlation-001",
                causation_id=None,
                created_at=T0,
                updated_at=T0,
                revision=1,
            )

    def test_responsibility_and_obligation_records_are_explicit(self) -> None:
        responsibility = Responsibility(
            namespace=colleague_namespace(),
            responsibility_id="responsibility-main",
            mandate_id="mandate-alpha",
            mandate_revision=1,
            description="Keep work explicit.",
            owner_principal_id="principal-model",
            state=ResponsibilityState.ACTIVE,
            actor=human_user(),
            correlation_id="correlation-001",
            causation_id="mandate-alpha",
            created_at=T0,
            updated_at=T0,
            revision=1,
        )
        obligation = Obligation(
            namespace=colleague_namespace(),
            obligation_id="obligation-001",
            responsibility_id=responsibility.responsibility_id,
            description="Record a synthetic result.",
            state=ObligationState.PENDING,
            due_at=T1,
            work_id="work-001",
            resolution_evidence=(),
            actor=human_user(),
            correlation_id="correlation-001",
            causation_id="work-001",
            created_at=T0,
            updated_at=T0,
            revision=1,
        )
        self.assertEqual(obligation.responsibility_id, responsibility.responsibility_id)
        self.assertEqual(obligation.schema_version, 1)

    def test_resolved_obligation_requires_evidence(self) -> None:
        with self.assertRaises(CoreInvariantError):
            Obligation(
                namespace=colleague_namespace(),
                obligation_id="obligation-001",
                responsibility_id="responsibility-main",
                description="Record a synthetic result.",
                state=ObligationState.SATISFIED,
                due_at=T1,
                work_id="work-001",
                resolution_evidence=(),
                actor=human_user(),
                correlation_id="correlation-001",
                causation_id="work-001",
                created_at=T0,
                updated_at=T1,
                revision=2,
            )


if __name__ == "__main__":
    unittest.main()
