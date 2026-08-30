# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from digital_colleagues.adapters.system.deterministic import FixedClock
from digital_colleagues.api.app import create_app
from digital_colleagues.application.contracts import RequestPrincipalContext
from digital_colleagues.application.services import ApprovalService, EventService
from tests.p3.fixtures import T0, T2, T4, namespace, service, user
from tests.p3.scenario import PreparedScenario, prepare_proposal


def _app(scenario: PreparedScenario) -> Any:
    return create_app(
        event_service=EventService(scenario.store, scenario.identifiers, FixedClock(T0)),
        approval_service=ApprovalService(
            store=scenario.store,
            clock=FixedClock(T2),
            identifiers=scenario.identifiers,
            service_principal=service(),
        ),
        store=scenario.store,
        context_provider=lambda: RequestPrincipalContext(namespace(), user()),
    )


def authority_case() -> None:
    with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-api-") as temporary:
        scenario = prepare_proposal(Path(temporary) / "state.sqlite", identifier_namespace="api")
        app = _app(scenario)
        assert "p4_authentication_not_implemented" in app.state.authentication_boundary
        client = TestClient(app)
        event_body = {
            "event_id": "event-api",
            "event_type": "work_assigned",
            "safe_projection": {"work_id": "work-api", "priority": 10},
            "payload_digest": "sha256:" + ("2" * 64),
            "correlation_id": "correlation-api",
            "causation_id": None,
            "idempotency_key": "event-key-api",
        }
        created = client.post("/events", json=event_body)
        assert created.status_code == 201, created.text
        assert created.json()["created"] is True
        replayed = client.post("/events", json=event_body)
        assert replayed.status_code == 201
        assert replayed.json()["created"] is False
        for authority_field, value in (
            ("tenant_id", "tenant-other"),
            ("role", "tenant_admin"),
            ("principal_kind", "human"),
            ("occurred_at", T0.isoformat()),
        ):
            invalid = dict(event_body)
            invalid[authority_field] = value
            assert client.post("/events", json=invalid).status_code == 422
        scenario.store.close()


def approval_case() -> None:
    body: dict[str, object]
    with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-api-approval-") as temporary:
        scenario = prepare_proposal(
            Path(temporary) / "state.sqlite", identifier_namespace="api-approval"
        )
        client = TestClient(_app(scenario))
        proposal = scenario.proposal
        body = {
            "approval_decision_id": "approval-api",
            "proposal_revision": proposal.revision,
            "proposal_payload_digest": proposal.payload_digest,
            "proposal_digest": proposal.proposal_digest,
            "choice": "approve",
            "idempotency_key": "approval-key-api",
            "mandate_id": "mandate-synthetic",
            "expected_mandate_revision": 1,
        }
        response = client.post(f"/proposals/{proposal.proposal_id}/approval", json=body)
        assert response.status_code == 201, response.text
        assert response.json()["created"] is True
        assert response.json()["attempt_id"] is not None
        stored = scenario.store.get_approval(namespace(), "approval-api")
        assert stored.occurred_at == T2
        assert stored.valid_until < T4
        for temporal_field, value in (
            ("occurred_at", T2.isoformat()),
            ("valid_until", T4.isoformat()),
        ):
            invalid = dict(body)
            invalid[temporal_field] = value
            assert (
                client.post(f"/proposals/{proposal.proposal_id}/approval", json=invalid).status_code
                == 422
            )
        scenario.store.close()
    with tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-api-stale-") as temporary:
        stale = prepare_proposal(Path(temporary) / "state.sqlite", identifier_namespace="api-stale")
        stale_body = dict(body)
        stale_body["approval_decision_id"] = "approval-stale"
        stale_body["idempotency_key"] = "approval-key-stale"
        stale_body["expected_mandate_revision"] = 2
        response = TestClient(_app(stale)).post(
            f"/proposals/{stale.proposal.proposal_id}/approval",
            json=stale_body,
        )
        assert response.status_code == 409, response.text
        assert response.json()["detail"]["code"] == "invalid_contract"
        stale.store.close()


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments == ["authority"]:
        authority_case()
    elif arguments == ["approval"]:
        approval_case()
    else:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
