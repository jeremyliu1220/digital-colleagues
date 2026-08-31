# SPDX-License-Identifier: Apache-2.0

"""Composition root for the local P4 API, worker, and operator commands."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from digital_colleagues.adapters.channel.reference import ReferenceChannel
from digital_colleagues.adapters.intelligence.deterministic import DeterministicIntelligence
from digital_colleagues.adapters.sqlite.p4_store import SQLiteP4Store
from digital_colleagues.adapters.system.deterministic import StableHashIdentifier
from digital_colleagues.api.p4_app import create_p4_app
from digital_colleagues.application.p4_services import (
    AuthenticationService,
    InitialColleagueService,
    P4RuntimeController,
)
from digital_colleagues.local.security import (
    CredentialDigests,
    SecureTokenSource,
    UtcClock,
)


@dataclass(slots=True)
class LocalRuntime:
    state_directory: Path
    store: SQLiteP4Store
    clock: UtcClock
    digests: CredentialDigests
    authentication: AuthenticationService
    colleagues: InitialColleagueService
    controller: P4RuntimeController

    def close(self) -> None:
        self.store.close()


def build_local_runtime(state_directory: Path) -> LocalRuntime:
    state_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    clock = UtcClock()
    store = SQLiteP4Store(
        state_directory / "state.sqlite",
        migrations_path=Path(__file__).resolve().parents[3] / "migrations",
        clock=clock,
    )
    digests = CredentialDigests()
    tokens = SecureTokenSource()
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
    return LocalRuntime(
        state_directory=state_directory,
        store=store,
        clock=clock,
        digests=digests,
        authentication=authentication,
        colleagues=colleagues,
        controller=controller,
    )


def build_app_from_environment() -> object:
    state_directory = Path(os.environ.get("DC_STATE_DIR", "/state"))
    expected_origin = os.environ.get("DC_EXPECTED_ORIGIN", "http://127.0.0.1:4173")
    secure_cookie = os.environ.get("DC_SECURE_COOKIE", "0") == "1"
    runtime = build_local_runtime(state_directory)
    app = create_p4_app(
        authentication=runtime.authentication,
        colleagues=runtime.colleagues,
        runtime=runtime.controller,
        store=runtime.store,
        studio_store=runtime.store,
        expected_origin=expected_origin,
        secure_cookie=secure_cookie,
    )
    app.state.local_runtime = runtime
    return app
