# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import unittest
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from digital_colleagues.application.errors import PermissionDeniedError
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.effects import ActionResult, ActionResultState
from digital_colleagues.core.errors import AuthorizationError, CoreInvariantError
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.policy import (
    ColleaguePolicy,
    DurableTriggerKind,
    EscalationCondition,
    InterruptionMode,
    NotificationMode,
    OutsideHoursOutcome,
    PolicyRunState,
    ProactivityMode,
    StopCondition,
    WakeBudget,
    WakeBudgetPeriod,
    Weekday,
    WeeklyWindow,
)
from digital_colleagues.core.principals import HumanRole, Principal
from digital_colleagues.core.work import CompletionEvidence, WorkState, transition_work
from digital_colleagues.governance.policy import within_working_hours
from tests.p5.fixtures import P5Harness, build_harness, initial_colleague_body, update_body

ORIGIN = {"Origin": "http://testserver"}


def _policy(
    *,
    timezone: str = "UTC",
    weekly_windows: tuple[WeeklyWindow, ...] | None = None,
    issued_by: Principal | None = None,
) -> ColleaguePolicy:
    admin = Principal.human(
        tenant_id="tenant-policy",
        principal_id="admin-policy",
        roles=(HumanRole.TENANT_ADMIN,),
    )
    return ColleaguePolicy(
        namespace=Namespace.colleague("tenant-policy", "colleague-policy"),
        policy_id="policy-synthetic",
        mandate_id="mandate-synthetic",
        mandate_revision=1,
        timezone=timezone,
        weekly_windows=(
            (WeeklyWindow(Weekday.MONDAY, 9 * 60, 17 * 60),)
            if weekly_windows is None
            else weekly_windows
        ),
        allowed_triggers=(DurableTriggerKind.EVENT,),
        proactivity=ProactivityMode.BOUNDED,
        notification=NotificationMode.ENABLED,
        interruption=InterruptionMode.WORKING_HOURS_ONLY,
        wake_budget=WakeBudget(4, WakeBudgetPeriod.DAY),
        outside_hours=OutsideHoursOutcome.DEFER,
        stop_conditions=(StopCondition.ADMIN_STOP,),
        escalation_conditions=(EscalationCondition.BLOCKED_WORK,),
        failure_limit=3,
        run_state=PolicyRunState.ACTIVE,
        revision=1,
        issued_by=admin if issued_by is None else issued_by,
        effective_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


class P5PolicyTests(unittest.TestCase):
    @staticmethod
    def _headers(csrf: str) -> dict[str, str]:
        return {**ORIGIN, "X-CSRF-Token": csrf}

    def _setup(
        self, database: Path, *, effect_kind: str = "reference_message"
    ) -> tuple[P5Harness, TestClient, str]:
        harness = build_harness(database)
        _, plaintext = harness.authentication.ensure_bootstrap()
        assert plaintext is not None
        harness.authentication.claim_operator_retrieval(plaintext)
        client = TestClient(harness.app())
        exchanged = client.post(
            "/auth/bootstrap/exchange", headers=ORIGIN, json={"token": plaintext}
        )
        self.assertEqual(exchanged.status_code, 201, exchanged.text)
        csrf = exchanged.json()["csrf_token"]
        body = initial_colleague_body()
        body["effect_kind"] = effect_kind
        created = client.post("/colleagues", headers=self._headers(csrf), json=body)
        self.assertEqual(created.status_code, 201, created.text)
        csrf = client.get("/auth/session").json()["csrf_token"]
        return harness, client, csrf

    def _confirm_policy(
        self,
        client: TestClient,
        csrf: str,
        *,
        key: str,
        policy_changes: Mapping[str, object] | None = None,
    ) -> dict[str, Any]:
        created = client.post(
            "/colleagues/drafts",
            headers=self._headers(csrf),
            json={"idempotency_key": "draft-" + key},
        )
        self.assertEqual(created.status_code, 201, created.text)
        draft = created.json()["draft"]
        body = update_body(draft, key="update-" + key)
        if policy_changes:
            policy = body["policy"]
            assert isinstance(policy, dict)
            policy.update(policy_changes)
        updated = client.put(
            f"/colleagues/drafts/{draft['draft_id']}",
            headers=self._headers(csrf),
            json=body,
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        draft = updated.json()["draft"]
        reviewed = client.post(
            f"/colleagues/drafts/{draft['draft_id']}/review",
            headers=self._headers(csrf),
            json={"expected_draft_revision": draft["revision"], "idempotency_key": "review-" + key},
        )
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        draft = reviewed.json()["draft"]
        confirmed = client.post(
            f"/colleagues/drafts/{draft['draft_id']}/confirm",
            headers=self._headers(csrf),
            json={
                "expected_draft_revision": draft["revision"],
                "expected_base_profile_revision": draft["base_profile_revision"],
                "expected_base_mandate_revision": draft["base_mandate_revision"],
                "expected_base_policy_revision": draft["base_policy_revision"],
                "expected_canonical_digest": draft["canonical_digest"],
                "idempotency_key": "confirm-" + key,
            },
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        return cast(dict[str, Any], client.get("/p5/studio/state").json())

    def _assign_work(self, client: TestClient, csrf: str, key: str) -> str:
        state = client.get("/studio/state").json()
        responsibility_id = state["identity"]["mandate"]["responsibilities"][0]["responsibility_id"]
        response = client.post(
            "/work",
            headers=self._headers(csrf),
            json={
                "title": "P5 deterministic work",
                "description": "Exercise exact policy enforcement.",
                "responsibility_id": responsibility_id,
                "idempotency_key": key,
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return cast(str, response.json()["work"]["work_id"])

    def test_working_hours_timezone_overlap_cross_midnight_and_dst_are_deterministic(self) -> None:
        self.assertTrue(within_working_hours(_policy(), datetime(2026, 1, 5, 10, tzinfo=UTC)))
        self.assertFalse(within_working_hours(_policy(), datetime(2026, 1, 5, 18, tzinfo=UTC)))
        overnight = _policy(weekly_windows=(WeeklyWindow(Weekday.MONDAY, 22 * 60, 2 * 60),))
        self.assertTrue(within_working_hours(overnight, datetime(2026, 1, 6, 1, tzinfo=UTC)))
        self.assertFalse(within_working_hours(overnight, datetime(2026, 1, 6, 3, tzinfo=UTC)))
        new_york = _policy(
            timezone="America/New_York",
            weekly_windows=(WeeklyWindow(Weekday.SUNDAY, 60, 180),),
        )
        self.assertTrue(within_working_hours(new_york, datetime(2026, 3, 8, 6, 30, tzinfo=UTC)))
        self.assertFalse(within_working_hours(new_york, datetime(2026, 3, 8, 7, 30, tzinfo=UTC)))
        with self.assertRaises(CoreInvariantError):
            _policy(timezone="Not/A_Zone")
        with self.assertRaises(CoreInvariantError):
            _policy(weekly_windows=())
        with self.assertRaises(CoreInvariantError):
            _policy(
                weekly_windows=(
                    WeeklyWindow(Weekday.MONDAY, 60, 180),
                    WeeklyWindow(Weekday.MONDAY, 120, 240),
                )
            )
        with self.assertRaises(AuthorizationError):
            _policy(issued_by=Principal.model(tenant_id="tenant-policy", principal_id="model-x"))

    def test_budget_is_restart_safe_duplicate_class_cannot_evade_and_stop_requires_revision(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p5-budget-") as temporary:
            database = Path(temporary) / "state.sqlite"
            harness, client, csrf = self._setup(database)
            state = self._confirm_policy(
                client,
                csrf,
                key="budget-one",
                policy_changes={
                    "wake_limit": 1,
                    "stop_conditions": ["admin_stop", "budget_exhausted"],
                    "escalation_conditions": ["budget_exhausted"],
                },
            )
            self.assertEqual(state["active"]["policy_revision"], 1)
            work_id = self._assign_work(client, csrf, "work-budget")
            first = client.post(
                "/runtime/triggers",
                headers=self._headers(csrf),
                json={
                    "work_id": work_id,
                    "trigger_class": "event",
                    "deterministic_noop": True,
                    "idempotency_key": "occurrence-one",
                },
            )
            self.assertEqual(first.status_code, 201, first.text)
            self.assertTrue(first.json()["accepted"])
            duplicate = client.post(
                "/runtime/triggers",
                headers=self._headers(csrf),
                json={
                    "work_id": work_id,
                    "trigger_class": "timer",
                    "deterministic_noop": True,
                    "idempotency_key": "occurrence-one",
                },
            )
            self.assertEqual(duplicate.status_code, 201, duplicate.text)
            self.assertFalse(duplicate.json()["accepted"])
            self.assertEqual(duplicate.json()["policy_outcome"], "duplicate_trigger")
            exhausted = client.post(
                "/runtime/triggers",
                headers=self._headers(csrf),
                json={
                    "work_id": work_id,
                    "trigger_class": "event",
                    "deterministic_noop": False,
                    "idempotency_key": "occurrence-two",
                },
            )
            self.assertFalse(exhausted.json()["accepted"])
            self.assertEqual(exhausted.json()["policy_outcome"], "budget_exhausted")
            self.assertIsNotNone(exhausted.json()["escalation_id"])
            cookie = client.cookies.get("dc_session")
            harness.store.close()
            restarted = build_harness(database)
            restarted_client = TestClient(restarted.app())
            assert cookie is not None
            restarted_client.cookies.set("dc_session", cookie)
            recovered_session = restarted_client.get("/auth/session")
            self.assertEqual(recovered_session.status_code, 200, recovered_session.text)
            csrf = recovered_session.json()["csrf_token"]
            recovered = restarted_client.get("/p5/studio/state").json()
            self.assertEqual(recovered["runtime_policy"]["budget_count"], 1)
            self.assertEqual(recovered["runtime_policy"]["run_state"], "stopped")
            self.assertEqual(len(recovered["runtime_policy"]["escalations"]), 1)
            stopped = restarted_client.post(
                "/runtime/triggers",
                headers=self._headers(csrf),
                json={
                    "work_id": work_id,
                    "trigger_class": "event",
                    "deterministic_noop": True,
                    "idempotency_key": "occurrence-three",
                },
            )
            self.assertEqual(stopped.json()["policy_outcome"], "stopped")
            resumed = self._confirm_policy(
                restarted_client,
                csrf,
                key="explicit-resume",
                policy_changes={"wake_limit": 2, "run_state": "active"},
            )
            self.assertEqual(resumed["active"]["policy_revision"], 2)
            self.assertEqual(resumed["runtime_policy"]["run_state"], "active")
            restarted.store.close()

    def test_disallowed_outside_hours_proactivity_notification_and_interruption_are_separate(
        self,
    ) -> None:
        scenarios = (
            (
                "disallowed",
                {"allowed_triggers": ["timer"]},
                "event",
                "disallowed_trigger",
            ),
            (
                "outside",
                {
                    "weekly_windows": [
                        {"weekday": "monday", "start_minute": 540, "end_minute": 600}
                    ],
                    "outside_hours": "escalate",
                    "escalation_conditions": ["outside_hours"],
                },
                "event",
                "outside_hours_escalate",
            ),
            (
                "proactivity",
                {"proactivity": "disabled"},
                "event",
                "proactivity_suppressed",
            ),
        )
        for name, changes, trigger_class, expected in scenarios:
            with (
                self.subTest(name=name),
                tempfile.TemporaryDirectory(prefix=f"digital-colleagues-p5-{name}-") as temporary,
            ):
                harness, client, csrf = self._setup(Path(temporary) / "state.sqlite")
                self._confirm_policy(client, csrf, key=name, policy_changes=changes)
                work_id = self._assign_work(client, csrf, "work-" + name)
                response = client.post(
                    "/runtime/triggers",
                    headers=self._headers(csrf),
                    json={
                        "work_id": work_id,
                        "trigger_class": trigger_class,
                        "deterministic_noop": False,
                        "idempotency_key": "trigger-" + name,
                    },
                )
                self.assertEqual(response.status_code, 201, response.text)
                self.assertFalse(response.json()["accepted"])
                self.assertEqual(response.json()["policy_outcome"], expected)
                self.assertEqual(client.get("/studio/state").json()["proposals"], [])
                harness.store.close()

    def test_finite_stop_blocked_and_repeated_failure_escalations_are_typed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p5-finite-stop-") as temporary:
            harness, client, csrf = self._setup(Path(temporary) / "state.sqlite")
            self._confirm_policy(
                client,
                csrf,
                key="finite-conditions",
                policy_changes={
                    "stop_conditions": ["finite_work_terminal"],
                    "escalation_conditions": ["blocked_work"],
                },
            )
            work_id = self._assign_work(client, csrf, "work-finite")
            namespace = harness.authentication.resolve(
                client.cookies.get("dc_session", "")
            ).colleague_namespace()
            work = harness.store.get_work(namespace, work_id)
            blocked = transition_work(
                work,
                expected_revision=work.revision,
                next_state=WorkState.BLOCKED,
                occurred_at=harness.clock.now(),
            )
            with harness.store._transaction() as connection:  # noqa: SLF001
                harness.store._update_record(  # noqa: SLF001
                    connection, blocked, expected_revision=work.revision
                )
            escalated = client.post(
                "/runtime/triggers",
                headers=self._headers(csrf),
                json={
                    "work_id": work_id,
                    "trigger_class": "event",
                    "deterministic_noop": False,
                    "idempotency_key": "blocked-escalation",
                },
            )
            self.assertEqual(escalated.json()["policy_outcome"], "blocked_work_escalate")
            self.assertIsNotNone(escalated.json()["escalation_id"])
            in_progress = transition_work(
                blocked,
                expected_revision=blocked.revision,
                next_state=WorkState.IN_PROGRESS,
                occurred_at=harness.clock.now(),
            )
            completed = transition_work(
                in_progress,
                expected_revision=in_progress.revision,
                next_state=WorkState.COMPLETED,
                occurred_at=harness.clock.now(),
                completion_evidence=(
                    CompletionEvidence(
                        evidence_id="evidence-finite",
                        kind="synthetic",
                        safe_summary="Synthetic finite completion",
                        observed_at=harness.clock.now(),
                        actor=work.actor,
                    ),
                ),
            )
            with harness.store._transaction() as connection:  # noqa: SLF001
                harness.store._update_record(  # noqa: SLF001
                    connection, in_progress, expected_revision=blocked.revision
                )
                harness.store._update_record(  # noqa: SLF001
                    connection, completed, expected_revision=in_progress.revision
                )
            stopped = client.post(
                "/runtime/triggers",
                headers=self._headers(csrf),
                json={
                    "work_id": work_id,
                    "trigger_class": "timer",
                    "deterministic_noop": True,
                    "idempotency_key": "finite-terminal-stop",
                },
            )
            self.assertEqual(stopped.json()["policy_outcome"], "finite_work_terminal_stop")
            self.assertEqual(
                client.get("/p5/studio/state").json()["runtime_policy"]["run_state"],
                "stopped",
            )
            harness.store.close()

        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p5-fail-stop-") as temporary:
            harness, client, csrf = self._setup(Path(temporary) / "state.sqlite")
            self._confirm_policy(
                client,
                csrf,
                key="failure-conditions",
                policy_changes={
                    "failure_limit": 3,
                    "stop_conditions": ["repeated_failure"],
                    "escalation_conditions": ["repeated_failure"],
                },
            )
            work_id = self._assign_work(client, csrf, "work-failures")
            namespace = harness.authentication.resolve(
                client.cookies.get("dc_session", "")
            ).colleague_namespace()
            service = harness.controller.service_context(namespace).service_principal
            with harness.store._transaction() as connection:  # noqa: SLF001
                for index in range(3):
                    attempt_id = f"attempt-synthetic-{index}"
                    result = ActionResult(
                        namespace=namespace,
                        action_result_id=f"result-synthetic-{index}",
                        effect_attempt_id=attempt_id,
                        state=ActionResultState.PERMANENT_FAILURE,
                        safe_projection=FrozenJsonObject.from_mapping(
                            {"outcome": "synthetic_failure"}
                        ),
                        result_digest="sha256:" + str(index) * 64,
                        actor=service,
                        correlation_id=f"correlation-failure-{index}",
                        causation_id=attempt_id,
                        occurred_at=harness.clock.now(),
                        revision=1,
                    )
                    harness.store._insert_record(connection, result)  # noqa: SLF001
            refused = client.post(
                "/runtime/triggers",
                headers=self._headers(csrf),
                json={
                    "work_id": work_id,
                    "trigger_class": "event",
                    "deterministic_noop": False,
                    "idempotency_key": "failure-stop",
                },
            )
            self.assertEqual(refused.json()["policy_outcome"], "repeated_failure_stop")
            self.assertIsNotNone(refused.json()["escalation_id"])
            self.assertEqual(harness.channel.call_count, 0)
            harness.store.close()

        for name, effect_kind, changes, expected in (
            (
                "notification",
                "notification",
                {"notification": "suppressed", "interruption": "allowed"},
                "notification_suppressed",
            ),
            (
                "interruption",
                "reference_message",
                {"interruption": "never"},
                "interruption_suppressed",
            ),
        ):
            with (
                self.subTest(name=name),
                tempfile.TemporaryDirectory(prefix=f"digital-colleagues-p5-{name}-") as temporary,
            ):
                harness, client, csrf = self._setup(
                    Path(temporary) / "state.sqlite", effect_kind=effect_kind
                )
                self._confirm_policy(client, csrf, key=name, policy_changes=changes)
                work_id = self._assign_work(client, csrf, "work-" + name)
                accepted = client.post(
                    "/runtime/triggers",
                    headers=self._headers(csrf),
                    json={
                        "work_id": work_id,
                        "trigger_class": "event",
                        "deterministic_noop": False,
                        "idempotency_key": "trigger-" + name,
                    },
                )
                self.assertTrue(accepted.json()["accepted"])
                processed = client.post(
                    "/runtime/process",
                    headers=self._headers(csrf),
                    json={"idempotency_key": "process-" + name},
                )
                self.assertEqual(processed.status_code, 200, processed.text)
                self.assertEqual(client.get("/studio/state").json()["proposals"], [])
                outcomes = client.get("/p5/studio/state").json()["runtime_policy"]["outcomes"]
                self.assertIn(expected, {item["outcome"] for item in outcomes})
                metric_response = client.get("/p5/evaluation/metrics")
                self.assertEqual(metric_response.status_code, 200, metric_response.text)
                readout = metric_response.json()
                self.assertEqual(readout["policy_binding"]["policy_revision"], 1)
                self.assertFalse(readout["policy_refusals"]["counted_as_successful_interactions"])
                metrics = {item["metric"]: item for item in readout["metrics"]}
                self.assertEqual(metrics["ai_initiated_rate"]["numerator"], 0)
                self.assertEqual(metrics["ai_initiated_rate"]["denominator"], 1)
                self.assertEqual(
                    metrics["unnecessary_interruption_rate"]["status"],
                    "not_applicable",
                )
                harness.store.close()

    def test_policy_change_makes_old_proposal_and_context_stale_before_approval_or_dispatch(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="digital-colleagues-p5-stale-proposal-"
        ) as temporary:
            harness, client, csrf = self._setup(Path(temporary) / "state.sqlite")
            self._confirm_policy(client, csrf, key="policy-one")
            work_id = self._assign_work(client, csrf, "work-stale")
            accepted = client.post(
                "/runtime/triggers",
                headers=self._headers(csrf),
                json={
                    "work_id": work_id,
                    "trigger_class": "event",
                    "deterministic_noop": False,
                    "idempotency_key": "trigger-stale",
                },
            )
            self.assertTrue(accepted.json()["accepted"])
            old_context = harness.controller.service_context(
                harness.authentication.resolve(
                    client.cookies.get("dc_session", "")
                ).colleague_namespace()
            )
            client.post(
                "/runtime/process",
                headers=self._headers(csrf),
                json={"idempotency_key": "process-stale"},
            )
            proposal = client.get("/studio/state").json()["proposals"][0]
            self._confirm_policy(
                client,
                csrf,
                key="policy-two",
                policy_changes={"wake_limit": 9},
            )
            metric_response = client.get("/p5/evaluation/metrics")
            self.assertEqual(metric_response.status_code, 200, metric_response.text)
            readout = metric_response.json()
            metrics = {item["metric"]: item for item in readout["metrics"]}
            self.assertEqual(readout["policy_binding"]["policy_revision"], 2)
            self.assertEqual(metrics["ai_initiated_rate"]["numerator"], 1)
            self.assertEqual(
                metrics["unnecessary_interruption_rate"]["status"],
                "not_evaluated",
            )
            self.assertEqual(
                {
                    item["policy_revision"]
                    for item in metrics["ai_initiated_rate"]["policy_bindings"]
                },
                {1},
            )
            stale = client.post(
                f"/proposals/{proposal['proposal_id']}/decision",
                headers=self._headers(csrf),
                json={
                    "proposal_revision": proposal["revision"],
                    "proposal_payload_digest": proposal["payload_digest"],
                    "proposal_digest": proposal["proposal_digest"],
                    "mandate_id": proposal["mandate_id"],
                    "mandate_revision": proposal["mandate_revision"],
                    "policy_id": proposal["policy_id"],
                    "policy_revision": proposal["policy_revision"],
                    "choice": "approve",
                    "idempotency_key": "approve-stale",
                },
            )
            self.assertEqual(stale.status_code, 403, stale.text)
            self.assertEqual(harness.channel.call_count, 0)
            with self.assertRaises(PermissionDeniedError):
                harness.controller.process_once(old_context)
            harness.store.close()


if __name__ == "__main__":
    unittest.main()
