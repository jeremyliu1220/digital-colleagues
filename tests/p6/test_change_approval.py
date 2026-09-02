# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import cast
from unittest.mock import patch

from fastapi.testclient import TestClient

from digital_colleagues.adapters.sqlite.p6_store import SQLiteP6Store
from digital_colleagues.adapters.system.deterministic import FixedClock
from digital_colleagues.application.errors import (
    ConflictError,
    PermissionDeniedError,
    ReplayConflictError,
    StaleConflictError,
)
from digital_colleagues.application.p4_contracts import InitialColleagueRequest
from digital_colleagues.application.p6_contracts import ChangeDecisionRequest
from digital_colleagues.application.p6_services import P6ChangeService
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.governance import (
    ChangeChoice,
    ChangeDecision,
    ChangeState,
    MembershipStatus,
)
from digital_colleagues.core.principals import HumanRole
from tests.p5.fixtures import initial_colleague_body, update_body
from tests.p6.fixtures import NOW, ORIGIN, ROOT, build_harness
from tests.p6.test_authentication_rbac import bootstrap, enroll


class P6ChangeApprovalTests(unittest.TestCase):
    @staticmethod
    def headers(csrf: str) -> dict[str, str]:
        return {"Origin": ORIGIN, "X-CSRF-Token": csrf}

    def test_authority_draft_requires_exact_other_admin_approval_and_is_single_use(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-change-") as name:
            harness = build_harness(Path(name) / "state.sqlite")
            first_cookie, first = bootstrap(harness)
            _, second = enroll(
                harness,
                issuer=first,
                role=HumanRole.TENANT_ADMIN,
                scopes=("*",),
                key="second-admin",
            )
            body = initial_colleague_body()
            profile, _, _ = harness.colleagues.create(
                session=first.session,
                request=InitialColleagueRequest(
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
                ),
            )
            colleague_id = profile.namespace.scope_id
            assert colleague_id is not None
            harness.authentication.bind_colleague(first.session, colleague_id)
            harness.authentication.bind_colleague(second.session_grant.session, colleague_id)
            first_client = TestClient(harness.app())
            second_client = TestClient(harness.app())
            first_client.cookies.set("dc_session", first_cookie)
            second_client.cookies.set("dc_session", second.session_grant.session_credential)
            first_headers = self.headers(first.csrf_token)
            second_headers = self.headers(second.session_grant.csrf_token)

            created = first_client.post(
                "/colleagues/drafts",
                headers=first_headers,
                json={"idempotency_key": "authority-draft"},
            )
            self.assertEqual(created.status_code, 201, created.text)
            draft = created.json()["draft"]
            changed = first_client.put(
                f"/colleagues/drafts/{draft['draft_id']}",
                headers=first_headers,
                json=update_body(
                    draft,
                    key="authority-update",
                    display_name="Atlas governed",
                    mission="Governed authority mission",
                ),
            )
            self.assertEqual(changed.status_code, 200, changed.text)
            draft = changed.json()["draft"]
            reviewed = first_client.post(
                f"/colleagues/drafts/{draft['draft_id']}/review",
                headers=first_headers,
                json={
                    "expected_draft_revision": draft["revision"],
                    "idempotency_key": "authority-review",
                },
            )
            self.assertEqual(reviewed.status_code, 200, reviewed.text)
            draft = reviewed.json()["draft"]
            confirmation = {
                "expected_draft_revision": draft["revision"],
                "expected_base_profile_revision": draft["base_profile_revision"],
                "expected_base_mandate_revision": draft["base_mandate_revision"],
                "expected_base_policy_revision": draft["base_policy_revision"],
                "expected_canonical_digest": draft["canonical_digest"],
                "idempotency_key": "bypass-confirmation",
            }
            bypass = first_client.post(
                f"/colleagues/drafts/{draft['draft_id']}/confirm",
                headers=first_headers,
                json=confirmation,
            )
            self.assertEqual(bypass.status_code, 403, bypass.text)

            proposed = first_client.post(
                f"/governance/drafts/{draft['draft_id']}/proposals",
                headers=first_headers,
                json={
                    "draft_revision": draft["revision"],
                    "canonical_digest": draft["canonical_digest"],
                    "idempotency_key": "propose-authority",
                },
            )
            self.assertEqual(proposed.status_code, 201, proposed.text)
            proposal = proposed.json()["proposal"]
            decision_body = {
                "proposal_revision": proposal["revision"],
                "proposal_digest": proposal["canonical_digest"],
                "choice": "approve",
                "idempotency_key": "approve-authority",
            }
            self_decision = first_client.post(
                f"/governance/changes/colleague/{proposal['proposal_id']}/decision",
                headers=first_headers,
                json=decision_body,
            )
            self.assertEqual(self_decision.status_code, 403, self_decision.text)
            decided = second_client.post(
                f"/governance/changes/colleague/{proposal['proposal_id']}/decision",
                headers=second_headers,
                json=decision_body,
            )
            self.assertEqual(decided.status_code, 201, decided.text)
            decision = decided.json()["decision"]
            applied = first_client.post(
                f"/governance/changes/colleague/{proposal['proposal_id']}/apply",
                headers=first_headers,
                json={
                    "decision_id": decision["decision_id"],
                    "idempotency_key": "apply-authority",
                },
            )
            self.assertEqual(applied.status_code, 200, applied.text)
            self.assertEqual(applied.json()["confirmation"]["mandate_revision"], 2)
            replay = first_client.post(
                f"/governance/changes/colleague/{proposal['proposal_id']}/apply",
                headers=first_headers,
                json={
                    "decision_id": decision["decision_id"],
                    "idempotency_key": "apply-again",
                },
            )
            self.assertIn(replay.status_code, {403, 409}, replay.text)

            # A later descriptive Profile-only change is distinguished and may apply directly.
            profile_draft = first_client.post(
                "/colleagues/drafts",
                headers=first_headers,
                json={"idempotency_key": "profile-draft"},
            ).json()["draft"]
            profile_changed = first_client.put(
                f"/colleagues/drafts/{profile_draft['draft_id']}",
                headers=first_headers,
                json=update_body(
                    profile_draft,
                    key="profile-update",
                    display_name="Atlas descriptive",
                    mission="Governed authority mission",
                ),
            )
            self.assertEqual(profile_changed.status_code, 200, profile_changed.text)
            profile_draft = profile_changed.json()["draft"]
            profile_review = first_client.post(
                f"/colleagues/drafts/{profile_draft['draft_id']}/review",
                headers=first_headers,
                json={
                    "expected_draft_revision": profile_draft["revision"],
                    "idempotency_key": "profile-review",
                },
            )
            self.assertEqual(profile_review.status_code, 200, profile_review.text)
            profile_draft = profile_review.json()["draft"]
            direct = first_client.post(
                f"/colleagues/drafts/{profile_draft['draft_id']}/confirm",
                headers=first_headers,
                json={
                    "expected_draft_revision": profile_draft["revision"],
                    "expected_base_profile_revision": profile_draft["base_profile_revision"],
                    "expected_base_mandate_revision": profile_draft["base_mandate_revision"],
                    "expected_base_policy_revision": profile_draft["base_policy_revision"],
                    "expected_canonical_digest": profile_draft["canonical_digest"],
                    "idempotency_key": "profile-confirm",
                },
            )
            self.assertEqual(direct.status_code, 200, direct.text)
            harness.store.close()

    def test_direct_change_workflow_separation_stale_binding_and_membership_revocation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-direct-change-") as name:
            harness = build_harness(Path(name) / "state.sqlite")
            first_cookie, first = bootstrap(harness)
            _, second = enroll(
                harness,
                issuer=first,
                role=HumanRole.TENANT_ADMIN,
                scopes=("*",),
                key="second-admin",
            )
            _, user = enroll(
                harness,
                issuer=first,
                role=HumanRole.COLLEAGUE_USER,
                scopes=("colleague:alpha",),
                key="user",
            )
            proposal = harness.changes.propose_membership(
                session=first.session,
                target_principal_id=user.membership.principal_id,
                role=HumanRole.AUDITOR,
                status=MembershipStatus.ACTIVE,
                colleague_ids=("colleague:alpha",),
                idempotency_key="user-to-auditor",
            )
            with self.assertRaises(PermissionDeniedError):
                harness.changes.decide(
                    session=first.session,
                    namespace=proposal.namespace,
                    proposal_id=proposal.proposal_id,
                    request=ChangeDecisionRequest(
                        proposal_revision=proposal.revision,
                        proposal_digest=proposal.canonical_digest,
                        choice=ChangeChoice.APPROVE,
                        idempotency_key="self-approval",
                    ),
                )
            with self.assertRaises(StaleConflictError):
                harness.changes.decide(
                    session=second.session_grant.session,
                    namespace=proposal.namespace,
                    proposal_id=proposal.proposal_id,
                    request=ChangeDecisionRequest(
                        proposal_revision=proposal.revision,
                        proposal_digest="sha256:" + "0" * 64,
                        choice=ChangeChoice.APPROVE,
                        idempotency_key="wrong-digest",
                    ),
                )
            approved, decision = harness.changes.decide(
                session=second.session_grant.session,
                namespace=proposal.namespace,
                proposal_id=proposal.proposal_id,
                request=ChangeDecisionRequest(
                    proposal_revision=proposal.revision,
                    proposal_digest=proposal.canonical_digest,
                    choice=ChangeChoice.APPROVE,
                    idempotency_key="approve-user-change",
                ),
            )
            self.assertEqual(approved.state, ChangeState.APPROVED)
            updated = harness.changes.apply_membership(
                session=first.session,
                proposal_id=proposal.proposal_id,
                decision_id=decision.decision_id,
                idempotency_key="apply-user-change",
            )
            self.assertEqual(updated.roles, (HumanRole.AUDITOR,))
            self.assertEqual(updated.membership_revision, 2)
            with self.assertRaises(PermissionDeniedError):
                harness.authentication.resolve(user.session_grant.session_credential)
            with self.assertRaises(PermissionDeniedError):
                harness.changes.apply_membership(
                    session=first.session,
                    proposal_id=proposal.proposal_id,
                    decision_id=decision.decision_id,
                    idempotency_key="apply-user-change-again",
                )

            api = TestClient(harness.app())
            api.cookies.set("dc_session", first_cookie)
            csrf = first.csrf_token
            injection = api.post(
                "/governance/memberships/proposals",
                headers=self.headers(csrf),
                json={
                    "target_principal_id": user.membership.principal_id,
                    "proposed_role": "tenant_admin",
                    "proposed_status": "active",
                    "proposed_colleague_ids": ["*"],
                    "idempotency_key": "role-elevation",
                    "tenant_id": "tenant-other",
                },
            )
            self.assertEqual(injection.status_code, 422, injection.text)
            harness.store.close()

    def test_change_replay_and_membership_apply_binding_survive_restart(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-change-replay-") as name:
            database = Path(name) / "state.sqlite"
            harness = build_harness(database)
            first_cookie, first = bootstrap(harness)
            _, second = enroll(
                harness,
                issuer=first,
                role=HumanRole.TENANT_ADMIN,
                scopes=("*",),
                key="change-replay-second-admin",
            )
            _, user = enroll(
                harness,
                issuer=first,
                role=HumanRole.COLLEAGUE_USER,
                scopes=("colleague:alpha",),
                key="change-replay-user",
            )
            proposal = harness.changes.propose_membership(
                session=first.session,
                target_principal_id=user.membership.principal_id,
                role=HumanRole.AUDITOR,
                status=MembershipStatus.ACTIVE,
                colleague_ids=("colleague:alpha",),
                idempotency_key="membership-proposal-replay",
            )
            harness.store.close()

            restarted = build_harness(database, now=NOW + timedelta(minutes=1))
            proposal_replay = restarted.changes.propose_membership(
                session=first.session,
                target_principal_id=user.membership.principal_id,
                role=HumanRole.AUDITOR,
                status=MembershipStatus.ACTIVE,
                colleague_ids=("colleague:alpha",),
                idempotency_key="membership-proposal-replay",
            )
            self.assertEqual(proposal_replay, proposal)
            with self.assertRaises(ReplayConflictError):
                restarted.changes.propose_membership(
                    session=first.session,
                    target_principal_id=user.membership.principal_id,
                    role=HumanRole.AUDITOR,
                    status=MembershipStatus.ACTIVE,
                    colleague_ids=("colleague:beta",),
                    idempotency_key="membership-proposal-replay",
                )
            client = TestClient(restarted.app())
            client.cookies.set("dc_session", first_cookie)
            headers = self.headers(first.csrf_token)
            proposal_body = {
                "target_principal_id": user.membership.principal_id,
                "proposed_role": "auditor",
                "proposed_status": "active",
                "proposed_colleague_ids": ["colleague:alpha"],
                "idempotency_key": "membership-proposal-replay",
            }
            api_proposal = client.post(
                "/governance/memberships/proposals",
                headers=headers,
                json=proposal_body,
            )
            self.assertEqual(api_proposal.status_code, 201, api_proposal.text)
            api_proposal_replay = client.post(
                "/governance/memberships/proposals",
                headers=headers,
                json=proposal_body,
            )
            self.assertEqual(api_proposal_replay.status_code, 201, api_proposal_replay.text)
            self.assertEqual(api_proposal_replay.json(), api_proposal.json())
            api_proposal_rebound = client.post(
                "/governance/memberships/proposals",
                headers=headers,
                json={**proposal_body, "proposed_colleague_ids": ["colleague:beta"]},
            )
            self.assertEqual(api_proposal_rebound.status_code, 409, api_proposal_rebound.text)
            decision_request = ChangeDecisionRequest(
                proposal_revision=proposal.revision,
                proposal_digest=proposal.canonical_digest,
                choice=ChangeChoice.APPROVE,
                idempotency_key="membership-decision-replay",
            )
            approved, decision = restarted.changes.decide(
                session=second.session_grant.session,
                namespace=proposal.namespace,
                proposal_id=proposal.proposal_id,
                request=decision_request,
            )
            approved_replay, decision_replay = restarted.changes.decide(
                session=second.session_grant.session,
                namespace=proposal.namespace,
                proposal_id=proposal.proposal_id,
                request=decision_request,
            )
            self.assertEqual(approved_replay, approved)
            self.assertEqual(decision_replay, decision)
            with self.assertRaises(ReplayConflictError):
                restarted.changes.decide(
                    session=second.session_grant.session,
                    namespace=proposal.namespace,
                    proposal_id=proposal.proposal_id,
                    request=ChangeDecisionRequest(
                        proposal_revision=proposal.revision,
                        proposal_digest=proposal.canonical_digest,
                        choice=ChangeChoice.REJECT,
                        idempotency_key="membership-decision-replay",
                    ),
                )
            second_client = TestClient(restarted.app())
            second_client.cookies.set("dc_session", second.session_grant.session_credential)
            second_headers = self.headers(second.session_grant.csrf_token)
            decision_body = {
                "proposal_revision": proposal.revision,
                "proposal_digest": proposal.canonical_digest,
                "choice": "approve",
                "idempotency_key": "membership-decision-replay",
            }
            api_decision = second_client.post(
                f"/governance/changes/tenant/{proposal.proposal_id}/decision",
                headers=second_headers,
                json=decision_body,
            )
            self.assertEqual(api_decision.status_code, 201, api_decision.text)
            api_decision_replay = second_client.post(
                f"/governance/changes/tenant/{proposal.proposal_id}/decision",
                headers=second_headers,
                json=decision_body,
            )
            self.assertEqual(api_decision_replay.status_code, 201, api_decision_replay.text)
            self.assertEqual(api_decision_replay.json(), api_decision.json())
            api_decision_rebound = second_client.post(
                f"/governance/changes/tenant/{proposal.proposal_id}/decision",
                headers=second_headers,
                json={**decision_body, "choice": "reject"},
            )
            self.assertEqual(api_decision_rebound.status_code, 409, api_decision_rebound.text)
            apply_body = {
                "decision_id": decision.decision_id,
                "idempotency_key": "membership-apply-replay",
            }
            applied = client.post(
                f"/governance/changes/tenant/{proposal.proposal_id}/apply",
                headers=headers,
                json=apply_body,
            )
            self.assertEqual(applied.status_code, 200, applied.text)
            first_result = applied.json()
            replayed = client.post(
                f"/governance/changes/tenant/{proposal.proposal_id}/apply",
                headers=headers,
                json=apply_body,
            )
            self.assertEqual(replayed.status_code, 200, replayed.text)
            self.assertEqual(replayed.json(), first_result)
            rebound = client.post(
                f"/governance/changes/tenant/{proposal.proposal_id}/apply",
                headers=headers,
                json={
                    "decision_id": "decision:other",
                    "idempotency_key": "membership-apply-replay",
                },
            )
            self.assertEqual(rebound.status_code, 409, rebound.text)
            self.assertEqual(
                restarted.store.membership_for_principal(
                    "tenant-local", user.membership.principal_id
                ).membership_revision,
                2,
            )
            binding = restarted.store._connection.execute(  # noqa: SLF001
                "SELECT idempotency_key, request_digest FROM p4_mutation_replay "
                "WHERE action = 'p6:apply-membership'"
            ).fetchone()
            self.assertEqual(binding["idempotency_key"], "membership-apply-replay")
            self.assertTrue(binding["request_digest"].startswith("sha256:"))
            self.assertEqual(
                restarted.store._connection.execute(  # noqa: SLF001
                    "SELECT COUNT(*) FROM p6_change_proposals"
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                restarted.store._connection.execute(  # noqa: SLF001
                    "SELECT COUNT(*) FROM p6_change_decisions"
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                restarted.store._connection.execute(  # noqa: SLF001
                    "SELECT COUNT(*) FROM p6_governance_audit WHERE action = 'membership_changed'"
                ).fetchone()[0],
                1,
            )
            restarted.store.close()

            final = build_harness(database, now=NOW + timedelta(minutes=2))
            final_client = TestClient(final.app())
            final_client.cookies.set("dc_session", first_cookie)
            after_restart = final_client.post(
                f"/governance/changes/tenant/{proposal.proposal_id}/apply",
                headers=headers,
                json=apply_body,
            )
            self.assertEqual(after_restart.status_code, 200, after_restart.text)
            self.assertEqual(after_restart.json(), first_result)
            self.assertEqual(
                final.store.membership_for_principal(
                    "tenant-local", user.membership.principal_id
                ).membership_revision,
                2,
            )
            self.assertEqual(
                final.store._connection.execute(  # noqa: SLF001
                    "SELECT COUNT(*) FROM p6_governance_audit WHERE action = 'membership_changed'"
                ).fetchone()[0],
                1,
            )
            final.store.close()

    def test_expired_and_rejected_changes_are_durable_terminal_refusals(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-terminal-") as name:
            harness = build_harness(Path(name) / "state.sqlite")
            _, first = bootstrap(harness)
            _, second = enroll(
                harness,
                issuer=first,
                role=HumanRole.TENANT_ADMIN,
                scopes=("*",),
                key="second-admin",
            )
            _, user = enroll(
                harness,
                issuer=first,
                role=HumanRole.COLLEAGUE_USER,
                scopes=("colleague:alpha",),
                key="user",
            )
            expired = harness.changes.propose_membership(
                session=first.session,
                target_principal_id=user.membership.principal_id,
                role=HumanRole.AUDITOR,
                status=MembershipStatus.ACTIVE,
                colleague_ids=("colleague:alpha",),
                idempotency_key="expires",
            )
            late_changes = P6ChangeService(
                store=harness.store,
                draft_store=harness.store,
                builder=harness.inner_builder,
                authentication=harness.authentication,
                clock=FixedClock(expired.expires_at),
                identifiers=harness.identifiers,
                digests=harness.digests,
            )
            with self.assertRaises(PermissionDeniedError):
                late_changes.decide(
                    session=second.session_grant.session,
                    namespace=expired.namespace,
                    proposal_id=expired.proposal_id,
                    request=ChangeDecisionRequest(
                        proposal_revision=expired.revision,
                        proposal_digest=expired.canonical_digest,
                        choice=ChangeChoice.APPROVE,
                        idempotency_key="too-late",
                    ),
                )
            self.assertEqual(
                harness.store.get_change_proposal(expired.namespace, expired.proposal_id).state,
                ChangeState.EXPIRED,
            )

            rejected = harness.changes.propose_membership(
                session=first.session,
                target_principal_id=user.membership.principal_id,
                role=HumanRole.AUDITOR,
                status=MembershipStatus.ACTIVE,
                colleague_ids=("colleague:alpha",),
                idempotency_key="rejected",
            )
            rejected, rejection = harness.changes.decide(
                session=second.session_grant.session,
                namespace=rejected.namespace,
                proposal_id=rejected.proposal_id,
                request=ChangeDecisionRequest(
                    proposal_revision=rejected.revision,
                    proposal_digest=rejected.canonical_digest,
                    choice=ChangeChoice.REJECT,
                    idempotency_key="reject-change",
                ),
            )
            self.assertEqual(rejected.state, ChangeState.REJECTED)
            with self.assertRaises(PermissionDeniedError):
                harness.changes.apply_membership(
                    session=first.session,
                    proposal_id=rejected.proposal_id,
                    decision_id=rejection.decision_id,
                    idempotency_key="apply-rejected-change",
                )

            first_candidate = harness.changes.propose_membership(
                session=first.session,
                target_principal_id=user.membership.principal_id,
                role=HumanRole.AUDITOR,
                status=MembershipStatus.ACTIVE,
                colleague_ids=("colleague:alpha",),
                idempotency_key="first-candidate",
            )
            stale_candidate = harness.changes.propose_membership(
                session=first.session,
                target_principal_id=user.membership.principal_id,
                role=HumanRole.AUDITOR,
                status=MembershipStatus.ACTIVE,
                colleague_ids=("colleague:alpha",),
                idempotency_key="stale-candidate",
            )
            first_candidate, first_decision = harness.changes.decide(
                session=second.session_grant.session,
                namespace=first_candidate.namespace,
                proposal_id=first_candidate.proposal_id,
                request=ChangeDecisionRequest(
                    proposal_revision=first_candidate.revision,
                    proposal_digest=first_candidate.canonical_digest,
                    choice=ChangeChoice.APPROVE,
                    idempotency_key="approve-first-candidate",
                ),
            )
            stale_candidate, stale_decision = harness.changes.decide(
                session=second.session_grant.session,
                namespace=stale_candidate.namespace,
                proposal_id=stale_candidate.proposal_id,
                request=ChangeDecisionRequest(
                    proposal_revision=stale_candidate.revision,
                    proposal_digest=stale_candidate.canonical_digest,
                    choice=ChangeChoice.APPROVE,
                    idempotency_key="approve-stale-candidate",
                ),
            )
            with patch.object(
                SQLiteP6Store,
                "_consume_change_rows",
                side_effect=RuntimeError("injected atomic rollback"),
            ):
                with self.assertRaisesRegex(RuntimeError, "injected atomic rollback"):
                    harness.changes.apply_membership(
                        session=first.session,
                        proposal_id=first_candidate.proposal_id,
                        decision_id=first_decision.decision_id,
                        idempotency_key="apply-first-candidate",
                    )
            rolled_back = harness.store.membership_for_principal(
                "tenant-local", user.membership.principal_id
            )
            self.assertEqual(rolled_back.roles, (HumanRole.COLLEAGUE_USER,))
            self.assertEqual(rolled_back.membership_revision, 1)
            self.assertEqual(
                harness.store.get_change_proposal(
                    first_candidate.namespace, first_candidate.proposal_id
                ).state,
                ChangeState.APPROVED,
            )

            harness.changes.apply_membership(
                session=first.session,
                proposal_id=first_candidate.proposal_id,
                decision_id=first_decision.decision_id,
                idempotency_key="apply-first-candidate",
            )
            with self.assertRaises(StaleConflictError):
                harness.changes.apply_membership(
                    session=first.session,
                    proposal_id=stale_candidate.proposal_id,
                    decision_id=stale_decision.decision_id,
                    idempotency_key="apply-stale-candidate",
                )
            self.assertEqual(
                harness.store.get_change_proposal(
                    stale_candidate.namespace, stale_candidate.proposal_id
                ).state,
                ChangeState.STALE,
            )
            harness.store.close()

    def test_concurrent_change_decisions_have_one_atomic_terminal_winner(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-change-race-") as name:
            database = Path(name) / "state.sqlite"
            harness = build_harness(database)
            _, first = bootstrap(harness)
            _, second = enroll(
                harness,
                issuer=first,
                role=HumanRole.TENANT_ADMIN,
                scopes=("*",),
                key="second-admin",
            )
            _, user = enroll(
                harness,
                issuer=first,
                role=HumanRole.COLLEAGUE_USER,
                scopes=("colleague:alpha",),
                key="user",
            )
            proposal = harness.changes.propose_membership(
                session=first.session,
                target_principal_id=user.membership.principal_id,
                role=HumanRole.AUDITOR,
                status=MembershipStatus.ACTIVE,
                colleague_ids=("colleague:alpha",),
                idempotency_key="concurrent-change",
            )
            approver = second.session_grant.session.principal
            membership = second.membership
            harness.store.close()
            barrier = threading.Barrier(2)

            def decide(index: int) -> str:
                store = SQLiteP6Store(
                    database,
                    migrations_path=ROOT / "migrations",
                    clock=FixedClock(NOW),
                )
                try:
                    stale = store.get_change_proposal(proposal.namespace, proposal.proposal_id)
                    key = f"concurrent-decision-{index}"
                    decision = ChangeDecision(
                        namespace=proposal.namespace,
                        decision_id=harness.identifiers.derive(
                            "change-decision", proposal.proposal_id, key
                        ),
                        proposal_id=proposal.proposal_id,
                        proposal_revision=proposal.revision,
                        proposal_digest=proposal.canonical_digest,
                        choice=(ChangeChoice.APPROVE if index == 1 else ChangeChoice.REJECT),
                        approver_principal_id=approver.principal_id,
                        approver_role_revision=membership.role_revision,
                        approver_membership_revision=membership.membership_revision,
                        occurred_at=NOW,
                        valid_until=NOW + timedelta(minutes=15),
                        idempotency_key=key,
                        request_digest=harness.digests.digest(
                            "change:decision", f"{proposal.proposal_id}:{index}"
                        ),
                        correlation_id=proposal.correlation_id,
                        causation_id=proposal.proposal_id,
                    )
                    barrier.wait()
                    decided, _ = store.decide_change(proposal=stale, decision=decision)
                    return decided.state.value
                except (ConflictError, StaleConflictError):
                    return "refused"
                finally:
                    store.close()

            with ThreadPoolExecutor(max_workers=2) as executor:
                outcomes = list(executor.map(decide, (1, 2)))
            self.assertEqual(outcomes.count("refused"), 1)
            self.assertEqual(sum(value in {"approved", "rejected"} for value in outcomes), 1)
            recovered = SQLiteP6Store(
                database,
                migrations_path=ROOT / "migrations",
                clock=FixedClock(NOW),
            )
            self.assertEqual(len(recovered.list_change_decisions(proposal.namespace)), 1)
            recovered.close()


if __name__ == "__main__":
    unittest.main()
