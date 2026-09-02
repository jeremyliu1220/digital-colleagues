# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI

from digital_colleagues.adapters.channel.reference import ReferenceChannel
from digital_colleagues.adapters.intelligence.deterministic import DeterministicIntelligence
from digital_colleagues.adapters.sqlite.p5_store import SQLiteP5Store
from digital_colleagues.adapters.system.deterministic import FixedClock, StableHashIdentifier
from digital_colleagues.api.p4_app import create_p4_app
from digital_colleagues.api.p5_app import install_p5_routes
from digital_colleagues.application.p4_services import (
    AuthenticationService,
    GovernedObservedIntelligence,
    InitialColleagueService,
    P4EvaluationService,
    P4RuntimeController,
)
from digital_colleagues.application.p5_services import (
    P5DispatchAuthorizer,
    P5RuntimeController,
    PolicyGovernedIntelligence,
    RevisionedColleagueBuilderService,
)
from digital_colleagues.local.security import CredentialDigests
from tests.p4.fixtures import SequenceTokens

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 4, 5, 6, 7, 8, tzinfo=UTC)


@dataclass(slots=True)
class P5Harness:
    store: SQLiteP5Store
    clock: FixedClock
    tokens: SequenceTokens
    authentication: AuthenticationService
    colleagues: InitialColleagueService
    builder: RevisionedColleagueBuilderService
    controller: P5RuntimeController
    channel: ReferenceChannel
    intelligence: DeterministicIntelligence

    def app(self) -> FastAPI:
        app = create_p4_app(
            authentication=self.authentication,
            colleagues=self.colleagues,
            runtime=self.controller,  # type: ignore[arg-type]
            store=self.store,
            studio_store=self.store,
            expected_origin="http://testserver",
        )
        install_p5_routes(
            app,
            authentication=self.authentication,
            builder=self.builder,
            p5_store=self.store,
            expected_origin="http://testserver",
            evaluation=P4EvaluationService(self.store),
        )
        return app


def build_harness(database: Path, *, now: datetime = NOW) -> P5Harness:
    clock = FixedClock(now)
    store = SQLiteP5Store(database, migrations_path=ROOT / "migrations", clock=clock)
    tokens = SequenceTokens([])
    digests = CredentialDigests()
    identifiers = StableHashIdentifier("p5-local")
    authentication = AuthenticationService(
        store=store,
        clock=clock,
        tokens=tokens,
        digests=digests,
        tenant_id="tenant-local",
    )
    colleagues = InitialColleagueService(
        store=store,
        runtime_store=store,
        identifiers=identifiers,
        clock=clock,
    )
    builder = RevisionedColleagueBuilderService(
        store=store,
        clock=clock,
        identifiers=identifiers,
    )
    channel = ReferenceChannel()
    intelligence = DeterministicIntelligence()
    governed = GovernedObservedIntelligence(
        inner=intelligence,
        store=store,
        identifiers=identifiers,
    )
    inner = P4RuntimeController(
        store=store,
        studio_store=store,
        intelligence=PolicyGovernedIntelligence(
            inner=governed,
            store=store,
            identifiers=identifiers,
            digests=digests,
        ),
        channel=channel,
        clock=clock,
        identifiers=identifiers,
        digests=digests,
        dispatch_authorizer=P5DispatchAuthorizer(store),
    )
    controller = P5RuntimeController(
        inner=inner,
        store=store,
        clock=clock,
        identifiers=identifiers,
    )
    return P5Harness(
        store,
        clock,
        tokens,
        authentication,
        colleagues,
        builder,
        controller,
        channel,
        intelligence,
    )


def initial_colleague_body() -> dict[str, object]:
    return {
        "display_name": "Atlas",
        "role_description": "Synthetic operations colleague",
        "service_relationship": "Serves the synthetic local operator",
        "mission": "Complete one finite reference task",
        "timezone": "Asia/Taipei",
        "working_context": "Synthetic offline context",
        "working_hours": "free-form legacy text that P5 must not parse",
        "working_style": "Direct and inspectable",
        "responsibilities": ["Own finite synthetic work"],
        "capabilities": ["Propose a reference message"],
        "constraints": ["No external network"],
        "effect_kind": "reference_message",
        "destination_kind": "reference_channel",
        "action": "record_message",
        "effect_constraints": {"network": False},
        "idempotency_key": "initial-colleague-key",
    }


def explicit_policy(*, wake_limit: int = 8, run_state: str = "active") -> dict[str, object]:
    return {
        "timezone": "UTC",
        "weekly_windows": [
            {"weekday": day, "start_minute": 0, "end_minute": 1440}
            for day in (
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            )
        ],
        "allowed_triggers": ["event", "timer"],
        "proactivity": "bounded",
        "notification": "enabled",
        "interruption": "allowed",
        "wake_limit": wake_limit,
        "wake_period": "day",
        "outside_hours": "defer",
        "stop_conditions": ["admin_stop", "budget_exhausted"],
        "escalation_conditions": ["budget_exhausted", "blocked_work"],
        "failure_limit": 3,
        "run_state": run_state,
    }


def update_body(
    draft: dict[str, object],
    *,
    key: str,
    display_name: str | None = None,
    mission: str | None = None,
    wake_limit: int = 8,
    run_state: str = "active",
) -> dict[str, object]:
    proposed_profile = draft["proposed_profile"]
    proposed_mandate = draft["proposed_mandate"]
    assert isinstance(proposed_profile, dict)
    assert isinstance(proposed_mandate, dict)
    return {
        "profile": {
            "display_name": display_name or proposed_profile["display_name"],
            "description": proposed_profile["description"],
            "presentation": proposed_profile["presentation"],
        },
        "mandate": {
            "mission": mission or proposed_mandate["mission"],
            "service_relationship": proposed_mandate["service_relationship"],
            "responsibilities": proposed_mandate["responsibilities"],
            "capabilities": proposed_mandate["capabilities"],
            "constraints": proposed_mandate["constraints"],
            "working_context": proposed_mandate["working_context"],
            "effect_boundaries": proposed_mandate["effect_boundaries"],
        },
        "policy": explicit_policy(wake_limit=wake_limit, run_state=run_state),
        "expected_draft_revision": draft["revision"],
        "idempotency_key": key,
    }
