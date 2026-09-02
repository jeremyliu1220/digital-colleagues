# SPDX-License-Identifier: Apache-2.0

"""Exercise the P6 negative authorization and abuse-case inventory."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import cast

from fastapi.testclient import TestClient

if __package__ in {None, ""}:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "src"))

from digital_colleagues.adapters.channel.reference import ReferenceChannel  # noqa: E402
from digital_colleagues.adapters.intelligence.deterministic import (  # noqa: E402
    DeterministicIntelligence,
)
from digital_colleagues.adapters.system.deterministic import (  # noqa: E402
    StableHashIdentifier,
)
from digital_colleagues.application.contracts import (  # noqa: E402
    IntelligenceRequest,
    SemanticDecision,
)
from digital_colleagues.application.p4_contracts import (  # noqa: E402
    ProposalCandidateObservation,
)
from digital_colleagues.application.p4_ports import StudioPersistencePort  # noqa: E402
from digital_colleagues.application.p4_services import (  # noqa: E402
    METRIC_POLICY_VERSION,
    SCENARIO_VERSION,
    GovernedObservedIntelligence,
    P4EvaluationService,
    P4RuntimeController,
)
from digital_colleagues.application.ports import IdentifierPort  # noqa: E402
from digital_colleagues.core.namespace import Namespace  # noqa: E402
from scripts.p6_gate_support import FocusedGateError, run_focused_tests  # noqa: E402
from tests.p4.fixtures import build_harness, initial_colleague_body  # noqa: E402

ABUSE_CASES = (
    "caller_authority_injection",
    "model_service_human_impersonation",
    "auditor_user_elevation",
    "self_approval",
    "role_elevation_bypass",
    "credential_guess_replay_expiry_revocation_race",
    "session_fixation_and_stale_revision",
    "csrf_origin_cross_site",
    "idempotency_rebinding",
    "cross_tenant_colleague_principal_idor",
    "change_stale_expired_replay",
    "effect_stale_expired_replay",
    "audit_export_overreach_and_unbounded",
    "alternate_endpoint_bypass",
    "transaction_rollback_partial_grant",
    "p5_flood_budget_trigger_regression",
)


class _UnauthorizedIntelligence:
    def __init__(self) -> None:
        self._inner = DeterministicIntelligence()

    def decide(self, request: IntelligenceRequest) -> SemanticDecision:
        semantic = self._inner.decide(request)
        if semantic.proposal is None:
            raise FocusedGateError("unauthorized metric fixture produced no proposal candidate")
        return replace(
            semantic,
            proposal=replace(semantic.proposal, action="forbidden_action"),
        )


class _FaultEscapingIntelligence:
    """Fault injection that records evaluation but lets the candidate reach the inbox."""

    def __init__(self, *, store: StudioPersistencePort, identifiers: IdentifierPort) -> None:
        self._inner = _UnauthorizedIntelligence()
        self._store = store
        self._identifiers = identifiers

    def decide(self, request: IntelligenceRequest) -> SemanticDecision:
        semantic = self._inner.decide(request)
        assert semantic.proposal is not None
        proposal = semantic.proposal
        self._store.record_proposal_candidate_observation(
            ProposalCandidateObservation(
                namespace=request.namespace,
                observation_id=self._identifiers.derive(
                    "observation", proposal.proposal_id, "unauthorized"
                ),
                candidate_id=proposal.proposal_id,
                boundary_id=proposal.constraints.boundary_id,
                outcome="governance_rejected_before_proposal",
                source="governance.p6_fault_injection.v1",
                evidence_class="synthetic",
                scenario_version=SCENARIO_VERSION,
                policy_version=METRIC_POLICY_VERSION,
                correlation_id=proposal.correlation_id,
                causation_id=semantic.decision.agenda_item_id,
                observed_at=request.occurred_at,
            )
        )
        return semantic


def observe_unauthorized_proposal_escape(*, fault_escape: bool = False) -> dict[str, object]:
    """Measure one real durable candidate evaluation across a SQLite restart."""

    with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-abuse-metric-") as name:
        database = Path(name) / "state.sqlite"
        harness = build_harness(database)
        _, plaintext = harness.authentication.ensure_bootstrap()
        if plaintext is None:
            raise FocusedGateError("unauthorized metric bootstrap plaintext was absent")
        harness.authentication.claim_operator_retrieval(plaintext)
        client = TestClient(harness.app())
        exchanged = client.post(
            "/auth/bootstrap/exchange",
            headers={"Origin": "http://testserver"},
            json={"token": plaintext},
        )
        if exchanged.status_code != 201:
            raise FocusedGateError("unauthorized metric bootstrap exchange failed")
        csrf = cast(str, exchanged.json()["csrf_token"])
        headers = {"Origin": "http://testserver", "X-CSRF-Token": csrf}
        created = client.post("/colleagues", headers=headers, json=initial_colleague_body())
        if created.status_code != 201:
            raise FocusedGateError("unauthorized metric colleague setup failed")
        state = client.get("/studio/state")
        if state.status_code != 200:
            raise FocusedGateError("unauthorized metric Studio setup failed")
        responsibility_id = cast(
            str,
            state.json()["identity"]["mandate"]["responsibilities"][0]["responsibility_id"],
        )
        assigned = client.post(
            "/work",
            headers=headers,
            json={
                "title": "P6 unauthorized proposal observation",
                "description": "Synthetic candidate evaluated by the governance boundary.",
                "responsibility_id": responsibility_id,
                "idempotency_key": "p6-abuse-observed-work",
            },
        )
        if assigned.status_code != 201:
            raise FocusedGateError("unauthorized metric work setup failed")
        work_id = cast(str, assigned.json()["work"]["work_id"])
        triggered = client.post(
            "/runtime/triggers",
            headers=headers,
            json={
                "work_id": work_id,
                "trigger_class": "event",
                "deterministic_noop": False,
                "idempotency_key": "p6-abuse-observed-trigger",
            },
        )
        if triggered.status_code != 201:
            raise FocusedGateError("unauthorized metric trigger setup failed")
        namespace_data = client.get("/auth/session").json()["namespace"]
        namespace = Namespace.colleague(
            cast(str, namespace_data["tenant_id"]),
            cast(str, namespace_data["scope_id"]),
        )
        identifiers = StableHashIdentifier("p4-local")
        intelligence = (
            _FaultEscapingIntelligence(store=harness.store, identifiers=identifiers)
            if fault_escape
            else GovernedObservedIntelligence(
                inner=_UnauthorizedIntelligence(),
                store=harness.store,
                identifiers=identifiers,
            )
        )
        controller = P4RuntimeController(
            store=harness.store,
            studio_store=harness.store,
            intelligence=intelligence,
            channel=ReferenceChannel(),
            clock=harness.clock,
            identifiers=identifiers,
            digests=harness.authentication._digests,  # noqa: SLF001
        )
        controller.process_once(controller.service_context(namespace))
        harness.store.close()

        restarted = build_harness(database)
        try:
            result = next(
                item
                for item in P4EvaluationService(restarted.store).evaluate(namespace)
                if item.metric == "unauthorized_proposal_escape_rate"
            )
            observations = restarted.store.list_proposal_candidate_observations(namespace)
            escaped_ids = {
                item.proposal_id for item in restarted.store.studio_snapshot(namespace).proposals
            }
            attempts = [
                {
                    "observation_id": item.observation_id,
                    "candidate_id": item.candidate_id,
                    "boundary_id": item.boundary_id,
                    "outcome": item.outcome,
                    "source": item.source,
                    "correlation_id": item.correlation_id,
                    "causation_id": item.causation_id,
                    "escaped": item.candidate_id in escaped_ids,
                }
                for item in observations
            ]
        finally:
            restarted.store.close()
    return {
        "status": result.status,
        "numerator": result.numerator,
        "denominator": result.denominator,
        "rate": result.value,
        "reason": result.reason,
        "source": result.source,
        "safe_causal_references": list(result.safe_causal_references),
        "evaluated_attempts": attempts,
        "safe_refusal_count": sum(not cast(bool, item["escaped"]) for item in attempts),
        "evidence_class": result.evidence_class,
    }


def require_zero_unauthorized_escape(metric: dict[str, object]) -> None:
    denominator = metric.get("denominator")
    numerator = metric.get("numerator")
    attempts = metric.get("evaluated_attempts")
    references = metric.get("safe_causal_references")
    if (
        type(denominator) is not int
        or not isinstance(attempts, list)
        or not isinstance(references, list)
    ):
        raise FocusedGateError("unauthorized proposal metric shape is invalid")
    if denominator == 0:
        if (
            metric.get("status") != "not_applicable"
            or numerator is not None
            or metric.get("rate") is not None
            or not metric.get("reason")
            or attempts
        ):
            raise FocusedGateError("zero-denominator proposal metric is not honest")
        return
    escaped = sum(item.get("escaped") is True for item in attempts if isinstance(item, dict))
    if (
        metric.get("status") != "observed"
        or type(numerator) is not int
        or len(attempts) != denominator
        or escaped != numerator
        or metric.get("rate") != numerator / denominator
        or metric.get("safe_refusal_count") != denominator - numerator
        or len(references) != denominator
    ):
        raise FocusedGateError("unauthorized proposal metric is not observation-derived")
    if numerator != 0:
        raise FocusedGateError("an unauthorized proposal candidate escaped governance")


def check_abuse(root: Path) -> dict[str, object]:
    tests = run_focused_tests(
        root,
        "tests.p6.test_authentication_rbac",
        "tests.p6.test_change_approval",
        "tests.p6.test_effect_audit",
        "tests.p4.test_metrics.P4MetricTests."
        "test_noop_is_not_ai_visible_and_governance_rejection_is_durable",
        "tests.p4.test_metrics.P4MetricTests."
        "test_fault_injected_escape_increments_numerator_and_fails_metric_gate",
        "tests.p6.test_migrations.P6MigrationTests.test_failed_007_rolls_back_schema_and_migration_record",
        "tests.p5.test_policy.P5PolicyTests."
        "test_budget_is_restart_safe_duplicate_class_cannot_evade_and_stop_requires_revision",
    )
    metric = observe_unauthorized_proposal_escape()
    require_zero_unauthorized_escape(metric)
    return {
        "schema_version": 1,
        "gate": "p6_abuse_cases_clean",
        "tests_run": tests,
        "abuse_cases": list(ABUSE_CASES),
        "safe_refusal_count": metric["safe_refusal_count"],
        "credential_in_diagnostics": False,
        "unauthorized_proposal_escape_rate": metric,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P6 abuse cases.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_abuse(Path(arguments.root).resolve())
    except (OSError, FocusedGateError) as exc:
        print(f"P6 abuse check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
