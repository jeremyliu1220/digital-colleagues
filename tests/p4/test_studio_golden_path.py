# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from tests.p4.fixtures import P4Harness, build_harness, initial_colleague_body

ORIGIN = {"Origin": "http://testserver"}


class P4StudioGoldenPathTests(unittest.TestCase):
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
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=strict", cookie)
        self.assertNotIn("secure", cookie)
        return client, response.json()["csrf_token"]

    @staticmethod
    def _headers(csrf: str) -> dict[str, str]:
        return {**ORIGIN, "X-CSRF-Token": csrf}

    def test_authenticated_studio_golden_path_restart_and_causal_chain(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-golden-") as temporary:
            database = Path(temporary) / "state.sqlite"
            harness = build_harness(database)
            client, csrf = self._bootstrap(harness)

            injected = {**initial_colleague_body(), "role": "auditor"}
            self.assertEqual(
                client.post("/colleagues", headers=self._headers(csrf), json=injected).status_code,
                422,
            )
            self.assertEqual(
                client.post(
                    "/colleagues", headers=ORIGIN, json=initial_colleague_body()
                ).status_code,
                403,
            )
            preview = client.post(
                "/colleagues/preview",
                headers=self._headers(csrf),
                json=initial_colleague_body(),
            )
            self.assertEqual(preview.status_code, 200, preview.text)
            self.assertFalse(preview.json()["profile"]["authoritative"])
            self.assertTrue(preview.json()["mandate"]["authoritative"])
            self.assertEqual(preview.json()["mandate"]["exact_revision"], 1)
            created = client.post(
                "/colleagues",
                headers=self._headers(csrf),
                json=initial_colleague_body(),
            )
            self.assertEqual(created.status_code, 201, created.text)
            self.assertEqual(
                client.post(
                    "/colleagues",
                    headers=self._headers(csrf),
                    json=initial_colleague_body(),
                ).status_code,
                409,
            )
            session = client.get("/auth/session")
            self.assertIsNotNone(session.json()["namespace"])
            csrf = session.json()["csrf_token"]

            state = client.get("/studio/state").json()
            mandate = state["identity"]["mandate"]
            self.assertEqual(mandate["revision"], 1)
            self.assertEqual(
                mandate["working_context"]["policy_enforcement"],
                "not_implemented_p5",
            )
            responsibility_id = mandate["responsibilities"][0]["responsibility_id"]
            assigned = client.post(
                "/work",
                headers=self._headers(csrf),
                json={
                    "title": "Prepare one deterministic update",
                    "description": "Complete after a typed reference result.",
                    "responsibility_id": responsibility_id,
                    "idempotency_key": "work-key",
                },
            )
            self.assertEqual(assigned.status_code, 201, assigned.text)
            work_id = assigned.json()["work"]["work_id"]
            duplicate_work = client.post(
                "/work",
                headers=self._headers(csrf),
                json={
                    "title": "Prepare one deterministic update",
                    "description": "Complete after a typed reference result.",
                    "responsibility_id": responsibility_id,
                    "idempotency_key": "work-key",
                },
            )
            self.assertEqual(duplicate_work.status_code, 201, duplicate_work.text)
            self.assertFalse(duplicate_work.json()["created"])
            self.assertEqual(duplicate_work.json()["work"]["work_id"], work_id)

            session_cookie = client.cookies.get("dc_session")
            harness.store.close()
            restarted = build_harness(database)
            restarted_client = TestClient(restarted.app())
            assert session_cookie is not None
            restarted_client.cookies.set("dc_session", session_cookie)
            recovered_session = restarted_client.get("/auth/session")
            self.assertEqual(recovered_session.status_code, 200, recovered_session.text)
            csrf = recovered_session.json()["csrf_token"]
            recovered = restarted_client.get("/studio/state").json()
            self.assertEqual(recovered["identity"]["mandate"]["revision"], 1)
            self.assertEqual(recovered["work"][0]["work_id"], work_id)

            trigger = restarted_client.post(
                "/runtime/triggers",
                headers=self._headers(csrf),
                json={
                    "work_id": work_id,
                    "trigger_class": "event",
                    "deterministic_noop": False,
                    "idempotency_key": "event-trigger-key",
                },
            )
            self.assertEqual(trigger.status_code, 201, trigger.text)
            correlation_id = trigger.json()["correlation_id"]
            processed = restarted_client.post(
                "/runtime/process",
                headers=self._headers(csrf),
                json={"idempotency_key": "process-key"},
            )
            self.assertEqual(processed.status_code, 200, processed.text)
            replayed_process = restarted_client.post(
                "/runtime/process",
                headers=self._headers(csrf),
                json={"idempotency_key": "process-key"},
            )
            self.assertEqual(replayed_process.json(), processed.json())
            proposal = restarted_client.get("/studio/state").json()["proposals"][0]
            self.assertEqual(proposal["revision"], 1)
            self.assertEqual(proposal["destination"]["kind"], "reference_channel")

            stale = {
                "proposal_revision": proposal["revision"] + 1,
                "proposal_payload_digest": proposal["payload_digest"],
                "proposal_digest": proposal["proposal_digest"],
                "mandate_id": proposal["mandate_id"],
                "mandate_revision": proposal["mandate_revision"],
                "choice": "approve",
                "idempotency_key": "stale-approval-key",
            }
            self.assertEqual(
                restarted_client.post(
                    f"/proposals/{proposal['proposal_id']}/decision",
                    headers=self._headers(csrf),
                    json=stale,
                ).status_code,
                409,
            )
            wrong_digest = {
                **stale,
                "proposal_revision": 1,
                "proposal_payload_digest": "sha256:" + ("0" * 64),
                "idempotency_key": "wrong-digest-key",
            }
            self.assertEqual(
                restarted_client.post(
                    f"/proposals/{proposal['proposal_id']}/decision",
                    headers=self._headers(csrf),
                    json=wrong_digest,
                ).status_code,
                409,
            )
            mandate_drift = {
                **stale,
                "proposal_revision": 1,
                "mandate_revision": proposal["mandate_revision"] + 1,
                "idempotency_key": "mandate-drift-key",
            }
            self.assertEqual(
                restarted_client.post(
                    f"/proposals/{proposal['proposal_id']}/decision",
                    headers=self._headers(csrf),
                    json=mandate_drift,
                ).status_code,
                409,
            )
            partial = {key: value for key, value in stale.items() if key != "proposal_digest"}
            self.assertEqual(
                restarted_client.post(
                    f"/proposals/{proposal['proposal_id']}/decision",
                    headers=self._headers(csrf),
                    json=partial,
                ).status_code,
                422,
            )
            self.assertEqual(
                restarted_client.post(
                    "/proposals/proposal:other-namespace/decision",
                    headers=self._headers(csrf),
                    json={**stale, "proposal_revision": 1},
                ).status_code,
                404,
            )
            exact = {**stale, "proposal_revision": 1, "idempotency_key": "approval-key"}
            approved = restarted_client.post(
                f"/proposals/{proposal['proposal_id']}/decision",
                headers=self._headers(csrf),
                json=exact,
            )
            self.assertEqual(approved.status_code, 201, approved.text)
            self.assertIsNotNone(approved.json()["attempt_id"])
            self.assertEqual(
                restarted_client.post(
                    f"/proposals/{proposal['proposal_id']}/decision",
                    headers=self._headers(csrf),
                    json=exact,
                ).status_code,
                409,
            )
            dispatch = restarted_client.post(
                "/runtime/process",
                headers=self._headers(csrf),
                json={"idempotency_key": "dispatch-key"},
            )
            self.assertTrue(dispatch.json()["dispatched"])
            final_state = restarted_client.get("/studio/state").json()
            self.assertEqual(final_state["wakes"][0]["trigger_class"], "event")
            self.assertEqual(final_state["wakes"][0]["handled_generation"], 1)
            self.assertEqual(len(final_state["results"]), 1)
            audit = restarted_client.get(f"/audit/{correlation_id}").json()["records"]
            record_types = {item["record_type"] for item in audit}
            self.assertTrue(
                {
                    "input_event",
                    "wake_cycle",
                    "agenda_item",
                    "decision",
                    "effect_proposal",
                    "human_approval",
                    "effect_attempt",
                    "action_result",
                }.issubset(record_types)
            )
            restarted.store.close()

    def test_timer_noop_metrics_and_reject_create_no_effect_attempt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p4-states-") as temporary:
            harness = build_harness(Path(temporary) / "state.sqlite")
            client, csrf = self._bootstrap(harness)
            client.post("/colleagues", headers=self._headers(csrf), json=initial_colleague_body())
            csrf = client.get("/auth/session").json()["csrf_token"]
            state = client.get("/studio/state").json()
            responsibility_id = state["identity"]["mandate"]["responsibilities"][0][
                "responsibility_id"
            ]
            work = client.post(
                "/work",
                headers=self._headers(csrf),
                json={
                    "title": "Synthetic timer work",
                    "description": "Exercise Timer and no-op paths.",
                    "responsibility_id": responsibility_id,
                    "idempotency_key": "work-timer-key",
                },
            ).json()["work"]
            for trigger_class, no_op, key in (
                ("timer", True, "timer-noop-key"),
                ("event", False, "event-proposal-key"),
            ):
                accepted = client.post(
                    "/runtime/triggers",
                    headers=self._headers(csrf),
                    json={
                        "work_id": work["work_id"],
                        "trigger_class": trigger_class,
                        "deterministic_noop": no_op,
                        "idempotency_key": key,
                    },
                )
                self.assertEqual(accepted.status_code, 201, accepted.text)
                client.post(
                    "/runtime/process",
                    headers=self._headers(csrf),
                    json={"idempotency_key": "process-" + key},
                )
            state = client.get("/studio/state").json()
            self.assertEqual({item["trigger_class"] for item in state["wakes"]}, {"event", "timer"})
            self.assertEqual(len(state["proposals"]), 1)
            proposal = state["proposals"][0]
            rejected = client.post(
                f"/proposals/{proposal['proposal_id']}/decision",
                headers=self._headers(csrf),
                json={
                    "proposal_revision": proposal["revision"],
                    "proposal_payload_digest": proposal["payload_digest"],
                    "proposal_digest": proposal["proposal_digest"],
                    "mandate_id": proposal["mandate_id"],
                    "mandate_revision": proposal["mandate_revision"],
                    "choice": "reject",
                    "idempotency_key": "reject-key",
                },
            )
            self.assertEqual(rejected.status_code, 201, rejected.text)
            self.assertIsNone(rejected.json()["attempt_id"])
            after = client.get("/studio/state").json()
            self.assertEqual(after["attempts"], [])
            metrics_response = client.get("/evaluation/metrics")
            self.assertEqual(metrics_response.status_code, 200, metrics_response.text)
            metrics = metrics_response.json()["metrics"]
            by_name = {item["metric"]: item for item in metrics}
            self.assertEqual(by_name["ai_initiated_rate"]["numerator"], 1)
            self.assertEqual(by_name["ai_initiated_rate"]["denominator"], 2)
            self.assertEqual(
                by_name["unauthorized_proposal_escape_rate"]["status"],
                "not_applicable",
            )
            harness.store.close()


if __name__ == "__main__":
    unittest.main()
