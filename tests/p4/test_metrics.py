# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from digital_colleagues.adapters.channel.reference import ReferenceChannel
from digital_colleagues.adapters.intelligence.deterministic import DeterministicIntelligence
from digital_colleagues.adapters.system.deterministic import StableHashIdentifier
from digital_colleagues.application.contracts import IntelligenceRequest, SemanticDecision
from digital_colleagues.application.p4_contracts import (
    EvaluationObservation,
    ProposalCandidateObservation,
)
from digital_colleagues.application.p4_services import (
    METRIC_POLICY_VERSION,
    SCENARIO_VERSION,
    GovernedObservedIntelligence,
    P4EvaluationService,
    P4RuntimeController,
)
from digital_colleagues.core.namespace import Namespace
from tests.p4.fixtures import P4Harness, build_harness, initial_colleague_body

ORIGIN = {"Origin": "http://testserver"}


class _UnauthorizedIntelligence:
    def __init__(self) -> None:
        self._inner = DeterministicIntelligence()

    def decide(self, request: IntelligenceRequest) -> SemanticDecision:
        semantic = self._inner.decide(request)
        assert semantic.proposal is not None
        proposal = replace(semantic.proposal, action="forbidden_action")
        return replace(semantic, proposal=proposal)


class _EscapingObservedIntelligence:
    """Fault injection: observe an unauthorized candidate but let it escape."""

    def __init__(self, harness: P4Harness, identifiers: StableHashIdentifier) -> None:
        self._inner = _UnauthorizedIntelligence()
        self._harness = harness
        self._identifiers = identifiers

    def decide(self, request: IntelligenceRequest) -> SemanticDecision:
        semantic = self._inner.decide(request)
        assert semantic.proposal is not None
        proposal = semantic.proposal
        self._harness.store.record_proposal_candidate_observation(
            ProposalCandidateObservation(
                namespace=request.namespace,
                observation_id=self._identifiers.derive(
                    "observation", proposal.proposal_id, "unauthorized"
                ),
                candidate_id=proposal.proposal_id,
                boundary_id=proposal.constraints.boundary_id,
                outcome="governance_rejected_before_proposal",
                source="governance.fault_injection.v1",
                evidence_class="synthetic",
                scenario_version=SCENARIO_VERSION,
                policy_version=METRIC_POLICY_VERSION,
                correlation_id=proposal.correlation_id,
                causation_id=semantic.decision.agenda_item_id,
                observed_at=request.occurred_at,
            )
        )
        return semantic


class P4MetricTests(unittest.TestCase):
    def _bootstrap(self, harness: P4Harness) -> tuple[TestClient, str]:
        _, plaintext = harness.authentication.ensure_bootstrap()
        assert plaintext is not None
        harness.authentication.claim_operator_retrieval(plaintext)
        client = TestClient(harness.app())
        response = client.post(
            "/auth/bootstrap/exchange",
            headers=ORIGIN,
            json={"token": plaintext},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return client, response.json()["csrf_token"]

    @staticmethod
    def _headers(csrf: str) -> dict[str, str]:
        return {**ORIGIN, "X-CSRF-Token": csrf}

    def _create_work(self, harness: P4Harness) -> tuple[TestClient, str, dict[str, object]]:
        client, csrf = self._bootstrap(harness)
        created = client.post(
            "/colleagues",
            headers=self._headers(csrf),
            json=initial_colleague_body(),
        )
        self.assertEqual(created.status_code, 201, created.text)
        csrf = client.get("/auth/session").json()["csrf_token"]
        state = client.get("/studio/state").json()
        responsibility_id = state["identity"]["mandate"]["responsibilities"][0]["responsibility_id"]
        assigned = client.post(
            "/work",
            headers=self._headers(csrf),
            json={
                "title": "Metric observation work",
                "description": "Synthetic durable metric opportunity.",
                "responsibility_id": responsibility_id,
                "idempotency_key": "metric-work-key",
            },
        )
        self.assertEqual(assigned.status_code, 201, assigned.text)
        return client, csrf, assigned.json()["work"]

    def test_not_applicable_and_eligible_but_unevaluated_are_distinct(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-metric-status-") as temp:
            harness = build_harness(Path(temp) / "state.sqlite")
            client, csrf = self._bootstrap(harness)
            client.post(
                "/colleagues",
                headers=self._headers(csrf),
                json=initial_colleague_body(),
            )
            empty_metrics = {
                item["metric"]: item for item in client.get("/evaluation/metrics").json()["metrics"]
            }
            self.assertEqual(empty_metrics["rebrief_turns"]["status"], "not_applicable")
            self.assertEqual(empty_metrics["rebrief_turns"]["denominator"], 0)
            self.assertTrue(empty_metrics["rebrief_turns"]["reason"])
            harness.store.close()

        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-metric-pending-") as temp:
            harness = build_harness(Path(temp) / "state.sqlite")
            client, _, _ = self._create_work(harness)
            metrics = {
                item["metric"]: item for item in client.get("/evaluation/metrics").json()["metrics"]
            }
            for metric in (
                "rebrief_turns",
                "wrong_memory_rate",
                "human_intervention_count",
            ):
                self.assertEqual(metrics[metric]["status"], "not_evaluated")
                self.assertEqual(metrics[metric]["denominator"], 1)
                self.assertIsNone(metrics[metric]["numerator"])
                self.assertIn("evaluator", metrics[metric]["source"])
            harness.store.close()

    def test_observed_values_come_from_durable_namespaced_observations_after_restart(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-metric-durable-") as temp:
            database = Path(temp) / "state.sqlite"
            harness = build_harness(database)
            client, _, work = self._create_work(harness)
            namespace_data = client.get("/auth/session").json()["namespace"]
            namespace = Namespace.colleague(namespace_data["tenant_id"], namespace_data["scope_id"])
            work_id = str(work["work_id"])
            correlation_id = str(work["correlation_id"])
            evaluation = P4EvaluationService(harness.store)
            for metric, value in (
                ("rebrief_turns", 2),
                ("wrong_memory_rate", 1),
                ("human_intervention_count", 3),
            ):
                evaluation.record(
                    EvaluationObservation(
                        namespace=namespace,
                        observation_id=f"observation:{metric}",
                        metric=metric,
                        value=value,
                        opportunity_id=work_id,
                        source="offline_evaluator.v1",
                        evidence_class="offline",
                        scenario_version=SCENARIO_VERSION,
                        policy_version=METRIC_POLICY_VERSION,
                        correlation_id=correlation_id,
                        causation_id=work_id,
                        observed_at=harness.clock.now(),
                    )
                )
            harness.store.close()

            restarted = build_harness(database)
            results = {
                item.metric: item
                for item in P4EvaluationService(restarted.store).evaluate(namespace)
            }
            self.assertEqual(results["rebrief_turns"].status, "observed")
            self.assertEqual(results["rebrief_turns"].numerator, 2)
            self.assertEqual(results["wrong_memory_rate"].value, 1.0)
            self.assertEqual(results["human_intervention_count"].numerator, 3)
            self.assertIn("offline_evaluator.v1", results["rebrief_turns"].source)
            self.assertEqual(results["rebrief_turns"].policy_version, METRIC_POLICY_VERSION)
            self.assertEqual(results["rebrief_turns"].schema_version, 1)
            other = Namespace.colleague(namespace.tenant_id, "colleague:other")
            self.assertEqual(restarted.store.list_evaluation_observations(other), ())
            restarted.store.close()

    def test_noop_is_not_ai_visible_and_governance_rejection_is_durable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-metric-governance-") as temp:
            database = Path(temp) / "state.sqlite"
            harness = build_harness(database)
            client, csrf, work = self._create_work(harness)
            namespace_data = client.get("/auth/session").json()["namespace"]
            namespace = Namespace.colleague("tenant-local", namespace_data["scope_id"])
            for trigger_class, no_op, key in (
                ("timer", True, "metric-noop"),
                ("event", False, "metric-unauthorized"),
            ):
                response = client.post(
                    "/runtime/triggers",
                    headers=self._headers(csrf),
                    json={
                        "work_id": work["work_id"],
                        "trigger_class": trigger_class,
                        "deterministic_noop": no_op,
                        "idempotency_key": key,
                    },
                )
                self.assertEqual(response.status_code, 201, response.text)
                if not no_op:
                    identifiers = StableHashIdentifier("p4-local")
                    harness.controller = P4RuntimeController(
                        store=harness.store,
                        studio_store=harness.store,
                        intelligence=GovernedObservedIntelligence(
                            inner=_UnauthorizedIntelligence(),
                            store=harness.store,
                            identifiers=identifiers,
                        ),
                        channel=ReferenceChannel(),
                        clock=harness.clock,
                        identifiers=identifiers,
                        digests=harness.authentication._digests,  # noqa: SLF001
                    )
                context = harness.controller.service_context(namespace)
                harness.controller.process_once(context)

            metrics = {
                item.metric: item for item in P4EvaluationService(harness.store).evaluate(namespace)
            }
            self.assertEqual(metrics["ai_initiated_rate"].numerator, 0)
            self.assertEqual(metrics["ai_initiated_rate"].denominator, 2)
            unauthorized = metrics["unauthorized_proposal_escape_rate"]
            self.assertEqual(unauthorized.status, "observed")
            self.assertEqual(unauthorized.denominator, 1)
            self.assertEqual(unauthorized.numerator, 0)
            snapshot = harness.store.studio_snapshot(namespace)
            self.assertEqual(snapshot.proposals, ())
            row = harness.store._connection.execute(  # noqa: SLF001
                "SELECT * FROM p4_proposal_candidate_observations"
            ).fetchone()
            self.assertEqual(row["namespace_scope_id"], namespace.scope_id)
            self.assertEqual(row["outcome"], "governance_rejected_before_proposal")
            self.assertNotIn("payload", row.keys())
            harness.store.close()

            restarted = build_harness(database)
            persisted = {
                item.metric: item
                for item in P4EvaluationService(restarted.store).evaluate(namespace)
            }
            self.assertEqual(
                persisted["unauthorized_proposal_escape_rate"].denominator,
                1,
            )
            restarted.store.close()

    def test_fault_injected_escape_increments_numerator_and_fails_metric_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-metric-escape-") as temp:
            harness = build_harness(Path(temp) / "state.sqlite")
            client, csrf, work = self._create_work(harness)
            trigger = client.post(
                "/runtime/triggers",
                headers=self._headers(csrf),
                json={
                    "work_id": work["work_id"],
                    "trigger_class": "event",
                    "deterministic_noop": False,
                    "idempotency_key": "fault-escape-trigger",
                },
            )
            self.assertEqual(trigger.status_code, 201, trigger.text)
            identifiers = StableHashIdentifier("p4-local")
            harness.controller = P4RuntimeController(
                store=harness.store,
                studio_store=harness.store,
                intelligence=_EscapingObservedIntelligence(harness, identifiers),
                channel=ReferenceChannel(),
                clock=harness.clock,
                identifiers=identifiers,
                digests=harness.authentication._digests,  # noqa: SLF001
            )
            namespace_data = client.get("/auth/session").json()["namespace"]
            namespace = Namespace.colleague("tenant-local", namespace_data["scope_id"])
            harness.controller.process_once(harness.controller.service_context(namespace))
            result = {
                item.metric: item for item in P4EvaluationService(harness.store).evaluate(namespace)
            }["unauthorized_proposal_escape_rate"]
            self.assertEqual(result.denominator, 1)
            self.assertEqual(result.numerator, 1)
            self.assertGreater(result.value or 0.0, 0.0)

            fault_client = TestClient(harness.app())
            session_cookie = client.cookies.get("dc_session")
            assert session_cookie is not None
            fault_client.cookies.set("dc_session", session_cookie)
            readout = fault_client.get("/evaluation/metrics")
            self.assertEqual(readout.status_code, 200, readout.text)
            self.assertEqual(readout.json()["gate_status"], "failed")
            harness.store.close()


if __name__ == "__main__":
    unittest.main()
