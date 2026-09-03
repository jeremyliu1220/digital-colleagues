# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from digital_colleagues.adapters.channel.reference import ReferenceChannel
from digital_colleagues.adapters.intelligence.deterministic import DeterministicIntelligence
from digital_colleagues.adapters.sqlite.p6_store import SQLiteP6Store
from digital_colleagues.adapters.system.deterministic import FixedClock, StableHashIdentifier
from digital_colleagues.api.p4_app import create_p4_app
from digital_colleagues.api.p5_app import install_p5_routes
from digital_colleagues.api.p6_app import install_p6_routes
from digital_colleagues.application.p4_contracts import InitialColleagueRequest
from digital_colleagues.application.p4_services import (
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
from digital_colleagues.application.p6_services import (
    P6AuditService,
    P6AuthenticationService,
    P6BuilderService,
    P6ChangeService,
    P6ColleagueService,
    P6DispatchAuthorizer,
    P6RuntimeController,
)
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.local.security import CredentialDigests
from tests.p4.fixtures import SequenceTokens
from tests.p5.fixtures import initial_colleague_body

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 6, 7, 8, 9, 10, tzinfo=UTC)
ORIGIN = "http://testserver"


@dataclass(slots=True)
class P6Harness:
    store: SQLiteP6Store
    clock: FixedClock
    tokens: SequenceTokens
    digests: CredentialDigests
    authentication: P6AuthenticationService
    colleagues: P6ColleagueService
    inner_colleagues: InitialColleagueService
    builder: P6BuilderService
    inner_builder: RevisionedColleagueBuilderService
    controller: P6RuntimeController
    changes: P6ChangeService
    audit: P6AuditService
    identifiers: StableHashIdentifier

    def app(self) -> FastAPI:
        app = create_p4_app(
            authentication=self.authentication,
            colleagues=self.colleagues,  # type: ignore[arg-type]
            runtime=self.controller,  # type: ignore[arg-type]
            store=self.store,
            studio_store=self.store,
            expected_origin=ORIGIN,
        )
        install_p5_routes(
            app,
            authentication=self.authentication,
            builder=self.builder,  # type: ignore[arg-type]
            p5_store=self.store,
            expected_origin=ORIGIN,
            evaluation=P4EvaluationService(self.store),
        )
        install_p6_routes(
            app,
            authentication=self.authentication,
            changes=self.changes,
            audit=self.audit,
            store=self.store,
            expected_origin=ORIGIN,
        )
        return app


def build_harness(database: Path, *, now: datetime = NOW) -> P6Harness:
    clock = FixedClock(now)
    store = SQLiteP6Store(database, migrations_path=ROOT / "migrations", clock=clock)
    tokens = SequenceTokens([])
    digests = CredentialDigests()
    identifiers = StableHashIdentifier("p6-local")
    authentication = P6AuthenticationService(
        store=store,
        clock=clock,
        tokens=tokens,
        digests=digests,
        identifiers=identifiers,
        tenant_id="tenant-local",
    )
    inner_colleagues = InitialColleagueService(
        store=store,
        runtime_store=store,
        identifiers=identifiers,
        clock=clock,
    )
    colleagues = P6ColleagueService(inner=inner_colleagues, authentication=authentication)
    inner_builder = RevisionedColleagueBuilderService(
        store=store,
        clock=clock,
        identifiers=identifiers,
    )
    builder = P6BuilderService(inner=inner_builder, authentication=authentication)
    governed = GovernedObservedIntelligence(
        inner=DeterministicIntelligence(), store=store, identifiers=identifiers
    )
    controller = P6RuntimeController(
        inner=P5RuntimeController(
            inner=P4RuntimeController(
                store=store,
                studio_store=store,
                intelligence=PolicyGovernedIntelligence(
                    inner=governed,
                    store=store,
                    identifiers=identifiers,
                    digests=digests,
                ),
                channel=ReferenceChannel(),
                clock=clock,
                identifiers=identifiers,
                digests=digests,
                dispatch_authorizer=P6DispatchAuthorizer(
                    p5=P5DispatchAuthorizer(store), store=store, clock=clock
                ),
            ),
            store=store,
            clock=clock,
            identifiers=identifiers,
        ),
        authentication=authentication,
    )
    changes = P6ChangeService(
        store=store,
        draft_store=store,
        builder=inner_builder,
        authentication=authentication,
        clock=clock,
        identifiers=identifiers,
        digests=digests,
    )
    audit = P6AuditService(
        store=store,
        authentication=authentication,
        clock=clock,
        identifiers=identifiers,
    )
    return P6Harness(
        store=store,
        clock=clock,
        tokens=tokens,
        digests=digests,
        authentication=authentication,
        colleagues=colleagues,
        inner_colleagues=inner_colleagues,
        builder=builder,
        inner_builder=inner_builder,
        controller=controller,
        changes=changes,
        audit=audit,
        identifiers=identifiers,
    )


def initial_request() -> InitialColleagueRequest:
    body = initial_colleague_body()
    return InitialColleagueRequest(
        display_name=cast(str, body["display_name"]),
        role_description=cast(str, body["role_description"]),
        service_relationship=cast(str, body["service_relationship"]),
        mission=cast(str, body["mission"]),
        timezone=cast(str, body["timezone"]),
        working_context=cast(str, body["working_context"]),
        working_hours=cast(str, body["working_hours"]),
        working_style=cast(str, body["working_style"]),
        responsibilities=tuple(cast(list[str], body["responsibilities"])),
        capabilities=tuple(cast(list[str], body["capabilities"])),
        constraints=tuple(cast(list[str], body["constraints"])),
        effect_kind=cast(str, body["effect_kind"]),
        destination_kind=cast(str, body["destination_kind"]),
        action=cast(str, body["action"]),
        effect_constraints=FrozenJsonObject.from_mapping(
            cast(dict[str, object], body["effect_constraints"])
        ),
        idempotency_key=cast(str, body["idempotency_key"]),
    )


def concurrent_http_posts(
    left: P6Harness,
    right: P6Harness,
    *,
    session_credential: str,
    csrf_token: str,
    paths: tuple[str, str],
    bodies: tuple[Mapping[str, object], Mapping[str, object]],
    action: str,
    idempotency_key: str,
) -> tuple[Response, Response]:
    """Force two independent HTTP clients through the same replay-miss window."""

    barrier = threading.Barrier(2)

    def synchronized(
        original: Callable[..., tuple[FrozenJsonObject | None, str]],
    ) -> Callable[..., tuple[FrozenJsonObject | None, str]]:
        def invoke(**kwargs: Any) -> tuple[FrozenJsonObject | None, str]:
            outcome = original(**kwargs)
            if (
                kwargs["action"] == action
                and kwargs["idempotency_key"] == idempotency_key
                and outcome[0] is None
            ):
                barrier.wait(timeout=5)
            return outcome

        return invoke

    clients = (TestClient(left.app()), TestClient(right.app()))
    headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf_token}
    for client in clients:
        client.cookies.set("dc_session", session_credential)

    def send(index: int) -> Response:
        return cast(
            Response,
            clients[index].post(paths[index], headers=headers, json=bodies[index]),
        )

    with (
        patch.object(
            left.authentication,
            "mutation_replay",
            side_effect=synchronized(left.authentication.mutation_replay),
        ),
        patch.object(
            right.authentication,
            "mutation_replay",
            side_effect=synchronized(right.authentication.mutation_replay),
        ),
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        futures = [executor.submit(send, index) for index in range(2)]
        return cast(
            tuple[Response, Response],
            tuple(future.result(timeout=15) for future in futures),
        )
