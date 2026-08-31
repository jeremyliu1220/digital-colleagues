# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI

from digital_colleagues.adapters.channel.reference import ReferenceChannel
from digital_colleagues.adapters.intelligence.deterministic import DeterministicIntelligence
from digital_colleagues.adapters.sqlite.p4_store import SQLiteP4Store
from digital_colleagues.adapters.system.deterministic import FixedClock, StableHashIdentifier
from digital_colleagues.api.p4_app import create_p4_app
from digital_colleagues.application.p4_services import (
    AuthenticationService,
    InitialColleagueService,
    P4RuntimeController,
)
from digital_colleagues.local.security import CredentialDigests

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 4, 5, 6, 7, 8, tzinfo=UTC)


@dataclass(slots=True)
class SequenceTokens:
    calls: list[int]
    position: int = 0

    def issue(self, byte_count: int) -> str:
        self.calls.append(byte_count)
        self.position += 1
        framed = f"p4-runtime-fixture:{self.position}:{byte_count}".encode()
        return hashlib.sha256(framed).hexdigest()


@dataclass(slots=True)
class P4Harness:
    store: SQLiteP4Store
    clock: FixedClock
    tokens: SequenceTokens
    authentication: AuthenticationService
    colleagues: InitialColleagueService
    controller: P4RuntimeController

    def app(self, *, secure_cookie: bool = False) -> FastAPI:
        return create_p4_app(
            authentication=self.authentication,
            colleagues=self.colleagues,
            runtime=self.controller,
            store=self.store,
            studio_store=self.store,
            expected_origin="http://testserver",
            secure_cookie=secure_cookie,
        )


def build_harness(database: Path, *, now: datetime = NOW) -> P4Harness:
    clock = FixedClock(now)
    store = SQLiteP4Store(database, migrations_path=ROOT / "migrations", clock=clock)
    tokens = SequenceTokens([])
    digests = CredentialDigests()
    identifiers = StableHashIdentifier("p4-local")
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
    controller = P4RuntimeController(
        store=store,
        studio_store=store,
        intelligence=DeterministicIntelligence(),
        channel=ReferenceChannel(),
        clock=clock,
        identifiers=identifiers,
        digests=digests,
    )
    return P4Harness(store, clock, tokens, authentication, colleagues, controller)


def initial_colleague_body() -> dict[str, object]:
    return {
        "display_name": "Atlas",
        "role_description": "Synthetic operations colleague",
        "service_relationship": "Serves the synthetic local operator",
        "mission": "Complete one finite reference task",
        "timezone": "UTC",
        "working_context": "Synthetic offline context",
        "working_hours": "09:00-17:00; initial data only",
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
