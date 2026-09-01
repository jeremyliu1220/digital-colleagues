# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from digital_colleagues.adapters.sqlite.p4_store import SQLiteP4Store
from digital_colleagues.application.errors import NotFoundError, PermissionDeniedError
from digital_colleagues.application.p4_contracts import (
    AuthenticatedSession,
    InitialColleagueRequest,
)
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.effects import ApprovalChoice
from digital_colleagues.core.errors import AuthorizationError
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.local.worker import run_once
from tests.p4.fixtures import P4Harness, build_harness, initial_colleague_body

ORIGIN = {"Origin": "http://testserver"}


class P4WorkerAuthorityTests(unittest.TestCase):
    @staticmethod
    def _headers(csrf: str) -> dict[str, str]:
        return {**ORIGIN, "X-CSRF-Token": csrf}

    def _durable_trigger(
        self, state_directory: Path
    ) -> tuple[P4Harness, TestClient, str, Namespace]:
        harness = build_harness(state_directory / "state.sqlite")
        _, plaintext = harness.authentication.ensure_bootstrap()
        assert plaintext is not None
        harness.authentication.claim_operator_retrieval(plaintext)
        client = TestClient(harness.app())
        exchanged = client.post(
            "/auth/bootstrap/exchange", headers=ORIGIN, json={"token": plaintext}
        )
        csrf = exchanged.json()["csrf_token"]
        client.post(
            "/colleagues",
            headers=self._headers(csrf),
            json=initial_colleague_body(),
        )
        session = client.get("/auth/session").json()
        csrf = session["csrf_token"]
        namespace = Namespace.colleague("tenant-local", session["namespace"]["scope_id"])
        state = client.get("/studio/state").json()
        responsibility_id = state["identity"]["mandate"]["responsibilities"][0]["responsibility_id"]
        work = client.post(
            "/work",
            headers=self._headers(csrf),
            json={
                "title": "Worker authority work",
                "description": "A pre-authorized durable trigger must survive session loss.",
                "responsibility_id": responsibility_id,
                "idempotency_key": "worker-authority-work",
            },
        ).json()["work"]
        trigger = client.post(
            "/runtime/triggers",
            headers=self._headers(csrf),
            json={
                "work_id": work["work_id"],
                "trigger_class": "event",
                "deterministic_noop": False,
                "idempotency_key": "worker-authority-trigger",
            },
        )
        self.assertEqual(trigger.status_code, 201, trigger.text)
        return harness, client, csrf, namespace

    def test_worker_uses_restricted_service_context_after_human_session_revocation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-worker-") as temp:
            state_directory = Path(temp)
            harness, _, _, namespace = self._durable_trigger(state_directory)
            harness.store._connection.execute(  # noqa: SLF001
                "UPDATE p4_sessions SET revoked_at = expires_at, revision = revision + 1"
            )
            harness.store._connection.commit()  # noqa: SLF001
            harness.store.close()

            with patch.object(
                SQLiteP4Store,
                "get_session",
                side_effect=AssertionError("worker read a human session credential"),
            ):
                self.assertEqual(run_once(state_directory), 1)

            restarted = build_harness(state_directory / "state.sqlite")
            snapshot = restarted.store.studio_snapshot(namespace)
            self.assertEqual(len(snapshot.proposals), 1)
            self.assertEqual(snapshot.decisions[0].actor.kind.value, "model")
            self.assertEqual(snapshot.wakes[0].actor.kind.value, "service")
            restarted.store.close()

    def test_no_session_grants_no_mandate_or_approval_authority(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-worker-no-session-") as temp:
            state_directory = Path(temp)
            harness, _, _, namespace = self._durable_trigger(state_directory)
            context = harness.controller.service_context(namespace)
            harness.controller.process_once(context)
            proposal = harness.store.studio_snapshot(namespace).proposals[0]
            harness.store._connection.execute("DELETE FROM p4_mutation_replay")  # noqa: SLF001
            harness.store._connection.execute("DELETE FROM p4_sessions")  # noqa: SLF001
            harness.store._connection.commit()  # noqa: SLF001

            service_session = AuthenticatedSession(
                tenant_id=namespace.tenant_id,
                session_id="session:service-forgery",
                principal=context.service_principal,
                credential_digest="sha256:" + ("1" * 64),
                csrf_digest="sha256:" + ("2" * 64),
                active_colleague_id=namespace.scope_id,
                created_at=harness.clock.now(),
                expires_at=proposal.constraints.valid_until,
            )
            request_body = initial_colleague_body()
            with self.assertRaises(PermissionDeniedError):
                harness.colleagues.create(
                    session=service_session,
                    request=InitialColleagueRequest(
                        display_name=str(request_body["display_name"]),
                        role_description=str(request_body["role_description"]),
                        service_relationship=str(request_body["service_relationship"]),
                        mission=str(request_body["mission"]),
                        timezone=str(request_body["timezone"]),
                        working_context=str(request_body["working_context"]),
                        working_hours=str(request_body["working_hours"]),
                        working_style=str(request_body["working_style"]),
                        responsibilities=("Own finite synthetic work",),
                        capabilities=("Propose a reference message",),
                        constraints=("No external network",),
                        effect_kind=str(request_body["effect_kind"]),
                        destination_kind=str(request_body["destination_kind"]),
                        action=str(request_body["action"]),
                        effect_constraints=FrozenJsonObject.from_mapping({"network": False}),
                        idempotency_key="service-mandate-forgery",
                    ),
                )
            with self.assertRaises(AuthorizationError):
                harness.controller.decide_proposal(
                    session=service_session,
                    proposal=proposal,
                    choice=ApprovalChoice.APPROVE,
                    idempotency_key="service-approval-forgery",
                    expected_proposal_revision=proposal.revision,
                    expected_payload_digest=proposal.payload_digest,
                    expected_proposal_digest=proposal.proposal_digest,
                    expected_mandate_id=proposal.mandate_id or "missing",
                    expected_mandate_revision=proposal.mandate_revision or 1,
                )
            self.assertEqual(run_once(state_directory), 0)
            harness.store.close()

    def test_runtime_context_rejects_stale_kind_and_namespace_crossover(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-runtime-context-") as temp:
            harness, _, _, namespace = self._durable_trigger(Path(temp))
            context = harness.controller.service_context(namespace)
            with self.assertRaises(PermissionDeniedError):
                harness.controller.process_once(
                    replace(context, mandate_revision=context.mandate_revision + 1)
                )
            with self.assertRaises(NotFoundError):
                harness.controller.service_context(
                    Namespace.colleague("tenant-other", namespace.scope_id or "missing")
                )
            with self.assertRaises(ValueError):
                replace(context, service_principal=context.model_principal)
            harness.store.close()


if __name__ == "__main__":
    unittest.main()
