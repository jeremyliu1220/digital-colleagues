# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
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
from digital_colleagues.application.p6_contracts import (
    ChangeDecisionRequest,
    EnrollmentAuthorizationRequest,
    RecoveryAuthorizationRequest,
)
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
from tests.p6.fixtures import (
    NOW,
    ORIGIN,
    ROOT,
    build_harness,
    concurrent_http_posts,
    initial_request,
)
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

    def test_cached_admin_replays_require_current_authority_after_formal_downgrade(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-replay-downgrade-") as name:
            harness = build_harness(Path(name) / "state.sqlite")
            first_cookie, first = bootstrap(harness)
            _, second = enroll(
                harness,
                issuer=first,
                role=HumanRole.TENANT_ADMIN,
                scopes=("*",),
                key="downgrade-second-admin",
            )
            third_proposal = harness.changes.propose_admin_enrollment(
                session=first.session,
                idempotency_key="downgrade-third-admin-proposal",
            )
            _, third_decision = harness.changes.decide(
                session=second.session_grant.session,
                namespace=third_proposal.namespace,
                proposal_id=third_proposal.proposal_id,
                request=ChangeDecisionRequest(
                    proposal_revision=third_proposal.revision,
                    proposal_digest=third_proposal.canonical_digest,
                    choice=ChangeChoice.APPROVE,
                    idempotency_key="downgrade-third-admin-decision",
                ),
            )
            _, third = enroll(
                harness,
                issuer=first,
                role=HumanRole.TENANT_ADMIN,
                scopes=("*",),
                key="downgrade-third-admin-enrollment",
                decision_id=third_decision.decision_id,
            )

            first_client = TestClient(harness.app())
            first_client.cookies.set("dc_session", first_cookie)
            first_headers = self.headers(first.csrf_token)
            enrollment_body = {
                "colleague_ids": ["colleague:alpha"],
                "idempotency_key": "downgrade-cached-enrollment",
            }
            enrollment_response = first_client.post(
                "/governance/enrollments/users",
                headers=first_headers,
                json=enrollment_body,
            )
            self.assertEqual(enrollment_response.status_code, 201, enrollment_response.text)
            enrollment_id = enrollment_response.json()["credential"]["credential_id"]
            enrollment_token = harness.authentication.retrieve_operator_credential(enrollment_id)
            user = harness.authentication.exchange_enrollment(enrollment_token)

            recovery_body = {
                "principal_id": user.membership.principal_id,
                "idempotency_key": "downgrade-cached-recovery",
            }
            recovery_response = first_client.post(
                "/governance/recovery", headers=first_headers, json=recovery_body
            )
            self.assertEqual(recovery_response.status_code, 201, recovery_response.text)

            disposable = harness.authentication.authorize_enrollment(
                session=first.session,
                request=EnrollmentAuthorizationRequest(
                    role=HumanRole.COLLEAGUE_USER,
                    colleague_ids=("colleague:alpha",),
                    idempotency_key="downgrade-disposable-credential",
                ),
            )
            revoke_path = f"/governance/credentials/{disposable.credential_id}/revoke"
            revoke_body = {"idempotency_key": "downgrade-cached-revoke"}
            revoke_response = first_client.post(
                revoke_path, headers=first_headers, json=revoke_body
            )
            self.assertEqual(revoke_response.status_code, 200, revoke_response.text)

            proposal_body = {
                "target_principal_id": user.membership.principal_id,
                "proposed_role": "auditor",
                "proposed_status": "active",
                "proposed_colleague_ids": ["colleague:alpha"],
                "idempotency_key": "downgrade-cached-proposal",
            }
            proposal_response = first_client.post(
                "/governance/memberships/proposals",
                headers=first_headers,
                json=proposal_body,
            )
            self.assertEqual(proposal_response.status_code, 201, proposal_response.text)

            applied_proposal = harness.changes.propose_membership(
                session=second.session_grant.session,
                target_principal_id=user.membership.principal_id,
                role=HumanRole.AUDITOR,
                status=MembershipStatus.ACTIVE,
                colleague_ids=("colleague:alpha",),
                idempotency_key="downgrade-applied-proposal",
            )
            decision_path = f"/governance/changes/tenant/{applied_proposal.proposal_id}/decision"
            decision_body = {
                "proposal_revision": applied_proposal.revision,
                "proposal_digest": applied_proposal.canonical_digest,
                "choice": "approve",
                "idempotency_key": "downgrade-cached-decision",
            }
            decision_response = first_client.post(
                decision_path, headers=first_headers, json=decision_body
            )
            self.assertEqual(decision_response.status_code, 201, decision_response.text)
            decision_id = decision_response.json()["decision"]["decision_id"]
            apply_path = f"/governance/changes/tenant/{applied_proposal.proposal_id}/apply"
            apply_body = {
                "decision_id": decision_id,
                "idempotency_key": "downgrade-cached-apply",
            }
            apply_response = first_client.post(apply_path, headers=first_headers, json=apply_body)
            self.assertEqual(apply_response.status_code, 200, apply_response.text)

            second_client = TestClient(harness.app())
            second_client.cookies.set("dc_session", second.session_grant.session_credential)
            current_admin_body = {
                "colleague_ids": ["colleague:beta"],
                "idempotency_key": "current-admin-replay",
            }
            current_admin_first = second_client.post(
                "/governance/enrollments/users",
                headers=self.headers(second.session_grant.csrf_token),
                json=current_admin_body,
            )
            current_admin_replay = second_client.post(
                "/governance/enrollments/users",
                headers=self.headers(second.session_grant.csrf_token),
                json=current_admin_body,
            )
            self.assertEqual(current_admin_first.status_code, 201, current_admin_first.text)
            self.assertEqual(current_admin_replay.status_code, 201, current_admin_replay.text)
            self.assertEqual(current_admin_replay.json(), current_admin_first.json())

            downgrade = harness.changes.propose_membership(
                session=third.session_grant.session,
                target_principal_id=first.session.principal.principal_id,
                role=HumanRole.AUDITOR,
                status=MembershipStatus.ACTIVE,
                colleague_ids=("colleague:alpha",),
                idempotency_key="formal-first-admin-downgrade",
            )
            _, downgrade_decision = harness.changes.decide(
                session=second.session_grant.session,
                namespace=downgrade.namespace,
                proposal_id=downgrade.proposal_id,
                request=ChangeDecisionRequest(
                    proposal_revision=downgrade.revision,
                    proposal_digest=downgrade.canonical_digest,
                    choice=ChangeChoice.APPROVE,
                    idempotency_key="formal-first-admin-downgrade-decision",
                ),
            )
            downgraded = harness.changes.apply_membership(
                session=third.session_grant.session,
                proposal_id=downgrade.proposal_id,
                decision_id=downgrade_decision.decision_id,
                idempotency_key="formal-first-admin-downgrade-apply",
            )
            self.assertEqual(downgraded.roles, (HumanRole.AUDITOR,))
            recovery = harness.authentication.authorize_recovery(
                session=second.session_grant.session,
                request=RecoveryAuthorizationRequest(
                    principal_id=first.session.principal.principal_id,
                    idempotency_key="downgraded-admin-recovery",
                ),
            )
            recovery_token = harness.authentication.retrieve_operator_credential(
                recovery.credential_id
            )
            recovered = harness.authentication.exchange_recovery(recovery_token)
            self.assertEqual(recovered.membership.roles, (HumanRole.AUDITOR,))
            downgraded_client = TestClient(harness.app())
            downgraded_client.cookies.set("dc_session", recovered.session_grant.session_credential)
            downgraded_headers = self.headers(recovered.session_grant.csrf_token)
            cached_requests = (
                ("/governance/enrollments/users", enrollment_body, enrollment_response.text),
                ("/governance/recovery", recovery_body, recovery_response.text),
                (revoke_path, revoke_body, revoke_response.text),
                (
                    "/governance/memberships/proposals",
                    proposal_body,
                    proposal_response.text,
                ),
                (decision_path, decision_body, decision_response.text),
                (apply_path, apply_body, apply_response.text),
            )
            for path, body, cached_text in cached_requests:
                refused = downgraded_client.post(path, headers=downgraded_headers, json=body)
                self.assertEqual(refused.status_code, 403, refused.text)
                self.assertNotEqual(refused.text, cached_text)
                for secret_metadata in (
                    enrollment_id,
                    recovery_response.json()["credential"]["credential_id"],
                    disposable.credential_id,
                    proposal_response.json()["proposal"]["proposal_id"],
                    decision_id,
                    user.membership.membership_id,
                ):
                    self.assertNotIn(secret_metadata, refused.text)
            harness.store.close()

    def test_cached_colleague_replay_fails_after_scope_change_and_revocation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-replay-scope-") as name:
            harness = build_harness(Path(name) / "state.sqlite")
            _, first = bootstrap(harness)
            _, second = enroll(
                harness,
                issuer=first,
                role=HumanRole.TENANT_ADMIN,
                scopes=("*",),
                key="scope-second-admin",
            )
            alpha, _, _ = harness.colleagues.create(
                session=first.session,
                request=replace(initial_request(), idempotency_key="scope-alpha-colleague"),
            )
            alpha_id = alpha.namespace.scope_id
            beta_id = "colleague:beta"
            assert alpha_id is not None
            _, auditor = enroll(
                harness,
                issuer=first,
                role=HumanRole.AUDITOR,
                scopes=(alpha_id,),
                key="scope-auditor",
            )
            alpha_client = TestClient(harness.app())
            alpha_client.cookies.set("dc_session", auditor.session_grant.session_credential)
            alpha_body = dict(
                colleague_id=alpha_id,
                idempotency_key="cached-alpha-colleague",
            )
            alpha_response = alpha_client.post(
                "/governance/session/active-colleague",
                headers=self.headers(auditor.session_grant.csrf_token),
                json=alpha_body,
            )
            self.assertEqual(alpha_response.status_code, 200, alpha_response.text)

            scope_change = harness.changes.propose_membership(
                session=first.session,
                target_principal_id=auditor.membership.principal_id,
                role=HumanRole.AUDITOR,
                status=MembershipStatus.ACTIVE,
                colleague_ids=(beta_id,),
                idempotency_key="formal-auditor-scope-change",
            )
            _, scope_decision = harness.changes.decide(
                session=second.session_grant.session,
                namespace=scope_change.namespace,
                proposal_id=scope_change.proposal_id,
                request=ChangeDecisionRequest(
                    proposal_revision=scope_change.revision,
                    proposal_digest=scope_change.canonical_digest,
                    choice=ChangeChoice.APPROVE,
                    idempotency_key="formal-auditor-scope-decision",
                ),
            )
            harness.changes.apply_membership(
                session=first.session,
                proposal_id=scope_change.proposal_id,
                decision_id=scope_decision.decision_id,
                idempotency_key="formal-auditor-scope-apply",
            )
            recovery = harness.authentication.authorize_recovery(
                session=first.session,
                request=RecoveryAuthorizationRequest(
                    principal_id=auditor.membership.principal_id,
                    idempotency_key="scope-change-recovery",
                ),
            )
            recovered_token = harness.authentication.retrieve_operator_credential(
                recovery.credential_id
            )
            recovered = harness.authentication.exchange_recovery(recovered_token)
            beta_client = TestClient(harness.app())
            beta_client.cookies.set("dc_session", recovered.session_grant.session_credential)
            old_alpha_replay = beta_client.post(
                "/governance/session/active-colleague",
                headers=self.headers(recovered.session_grant.csrf_token),
                json=alpha_body,
            )
            self.assertEqual(old_alpha_replay.status_code, 403, old_alpha_replay.text)
            self.assertNotIn(alpha_id, old_alpha_replay.text)

            _, revoked_auditor = enroll(
                harness,
                issuer=first,
                role=HumanRole.AUDITOR,
                scopes=(alpha_id,),
                key="revoked-replay-auditor",
            )
            revoked_client = TestClient(harness.app())
            revoked_client.cookies.set(
                "dc_session", revoked_auditor.session_grant.session_credential
            )
            revoked_body = dict(
                colleague_id=alpha_id,
                idempotency_key="cached-revoked-colleague",
            )
            cached_before_revocation = revoked_client.post(
                "/governance/session/active-colleague",
                headers=self.headers(revoked_auditor.session_grant.csrf_token),
                json=revoked_body,
            )
            self.assertEqual(
                cached_before_revocation.status_code,
                200,
                cached_before_revocation.text,
            )
            revoked = harness.changes.propose_membership(
                session=first.session,
                target_principal_id=revoked_auditor.membership.principal_id,
                role=HumanRole.AUDITOR,
                status=MembershipStatus.REVOKED,
                colleague_ids=(alpha_id,),
                idempotency_key="formal-auditor-revocation",
            )
            _, revoked_decision = harness.changes.decide(
                session=second.session_grant.session,
                namespace=revoked.namespace,
                proposal_id=revoked.proposal_id,
                request=ChangeDecisionRequest(
                    proposal_revision=revoked.revision,
                    proposal_digest=revoked.canonical_digest,
                    choice=ChangeChoice.APPROVE,
                    idempotency_key="formal-auditor-revocation-decision",
                ),
            )
            harness.changes.apply_membership(
                session=first.session,
                proposal_id=revoked.proposal_id,
                decision_id=revoked_decision.decision_id,
                idempotency_key="formal-auditor-revocation-apply",
            )
            revoked_replay = revoked_client.post(
                "/governance/session/active-colleague",
                headers=self.headers(revoked_auditor.session_grant.csrf_token),
                json=revoked_body,
            )
            self.assertEqual(revoked_replay.status_code, 403, revoked_replay.text)
            self.assertNotIn(alpha_id, revoked_replay.text)
            harness.store.close()

    def test_concurrent_http_governance_mutations_converge_and_survive_restart(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p6-governance-race-") as name:
            database = Path(name) / "state.sqlite"
            first_store = build_harness(database)
            first_cookie, first = bootstrap(first_store)
            _, second = enroll(
                first_store,
                issuer=first,
                role=HumanRole.TENANT_ADMIN,
                scopes=("*",),
                key="governance-race-second-admin",
            )
            _, user = enroll(
                first_store,
                issuer=first,
                role=HumanRole.COLLEAGUE_USER,
                scopes=("colleague:alpha",),
                key="governance-race-user",
            )
            second_store = build_harness(database)

            recovery_body = {
                "principal_id": user.membership.principal_id,
                "idempotency_key": "concurrent-http-recovery",
            }
            recovery_responses = concurrent_http_posts(
                first_store,
                second_store,
                session_credential=first_cookie,
                csrf_token=first.csrf_token,
                paths=("/governance/recovery", "/governance/recovery"),
                bodies=(recovery_body, recovery_body),
                action="p6:authorize-recovery",
                idempotency_key="concurrent-http-recovery",
            )
            self.assertEqual([response.status_code for response in recovery_responses], [201, 201])
            self.assertEqual(recovery_responses[0].json(), recovery_responses[1].json())
            recovery_id = recovery_responses[0].json()["credential"]["credential_id"]

            revoke_path = f"/governance/credentials/{recovery_id}/revoke"
            revoke_body = {"idempotency_key": "concurrent-http-revoke"}
            revoke_responses = concurrent_http_posts(
                first_store,
                second_store,
                session_credential=first_cookie,
                csrf_token=first.csrf_token,
                paths=(revoke_path, revoke_path),
                bodies=(revoke_body, revoke_body),
                action="p6:revoke-credential",
                idempotency_key="concurrent-http-revoke",
            )
            self.assertEqual([response.status_code for response in revoke_responses], [200, 200])
            self.assertEqual(revoke_responses[0].json(), revoke_responses[1].json())

            proposal_body = {
                "target_principal_id": user.membership.principal_id,
                "proposed_role": "auditor",
                "proposed_status": "active",
                "proposed_colleague_ids": ["colleague:alpha"],
                "idempotency_key": "concurrent-http-proposal",
            }
            proposal_responses = concurrent_http_posts(
                first_store,
                second_store,
                session_credential=first_cookie,
                csrf_token=first.csrf_token,
                paths=(
                    "/governance/memberships/proposals",
                    "/governance/memberships/proposals",
                ),
                bodies=(proposal_body, proposal_body),
                action="p6:propose-change",
                idempotency_key="concurrent-http-proposal",
            )
            self.assertEqual([response.status_code for response in proposal_responses], [201, 201])
            self.assertEqual(proposal_responses[0].json(), proposal_responses[1].json())
            proposal = proposal_responses[0].json()["proposal"]

            decision_path = f"/governance/changes/tenant/{proposal['proposal_id']}/decision"
            decision_body = {
                "proposal_revision": proposal["revision"],
                "proposal_digest": proposal["canonical_digest"],
                "choice": "approve",
                "idempotency_key": "concurrent-http-decision",
            }
            decision_responses = concurrent_http_posts(
                first_store,
                second_store,
                session_credential=second.session_grant.session_credential,
                csrf_token=second.session_grant.csrf_token,
                paths=(decision_path, decision_path),
                bodies=(decision_body, decision_body),
                action="p6:decide-change",
                idempotency_key="concurrent-http-decision",
            )
            self.assertEqual([response.status_code for response in decision_responses], [201, 201])
            self.assertEqual(decision_responses[0].json(), decision_responses[1].json())
            decision = decision_responses[0].json()["decision"]

            apply_path = f"/governance/changes/tenant/{proposal['proposal_id']}/apply"
            apply_body = {
                "decision_id": decision["decision_id"],
                "idempotency_key": "concurrent-http-apply",
            }
            apply_responses = concurrent_http_posts(
                first_store,
                second_store,
                session_credential=first_cookie,
                csrf_token=first.csrf_token,
                paths=(apply_path, apply_path),
                bodies=(apply_body, apply_body),
                action="p6:apply-change",
                idempotency_key="concurrent-http-apply",
            )
            self.assertEqual([response.status_code for response in apply_responses], [200, 200])
            self.assertEqual(apply_responses[0].json(), apply_responses[1].json())

            self.assertEqual(
                first_store.store._connection.execute(  # noqa: SLF001
                    "SELECT COUNT(*) FROM p6_governance_credentials WHERE credential_id = ?",
                    (recovery_id,),
                ).fetchone()[0],
                1,
            )
            audit_counts = dict(
                first_store.store._connection.execute(  # noqa: SLF001
                    "SELECT action, COUNT(*) FROM p6_governance_audit "
                    "WHERE action IN ('recovery_authorized', 'credential_revoked', "
                    "'change_proposed', 'change_decided', 'membership_changed') "
                    "GROUP BY action"
                ).fetchall()
            )
            self.assertEqual(
                audit_counts,
                {
                    "change_decided": 1,
                    "change_proposed": 1,
                    "credential_revoked": 1,
                    "membership_changed": 1,
                    "recovery_authorized": 1,
                },
            )
            self.assertEqual(
                first_store.store._connection.execute(  # noqa: SLF001
                    "SELECT COUNT(*) FROM p6_change_proposals WHERE proposal_id = ?",
                    (proposal["proposal_id"],),
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                first_store.store._connection.execute(  # noqa: SLF001
                    "SELECT COUNT(*) FROM p6_change_decisions WHERE decision_id = ?",
                    (decision["decision_id"],),
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                first_store.store.membership_for_principal(
                    "tenant-local", user.membership.principal_id
                ).membership_revision,
                2,
            )
            replay_keys = {
                "concurrent-http-recovery",
                "concurrent-http-revoke",
                "concurrent-http-proposal",
                "concurrent-http-decision",
                "concurrent-http-apply",
            }
            recorded_keys = {
                row[0]
                for row in first_store.store._connection.execute(  # noqa: SLF001
                    "SELECT idempotency_key FROM p4_mutation_replay "
                    "WHERE idempotency_key LIKE 'concurrent-http-%'"
                ).fetchall()
            }
            self.assertEqual(recorded_keys, replay_keys)
            originals = (
                recovery_responses[0].json(),
                revoke_responses[0].json(),
                proposal_responses[0].json(),
                decision_responses[0].json(),
                apply_responses[0].json(),
            )
            first_store.store.close()
            second_store.store.close()

            restarted = build_harness(database, now=NOW + timedelta(minutes=1))
            first_client = TestClient(restarted.app())
            first_client.cookies.set("dc_session", first_cookie)
            second_client = TestClient(restarted.app())
            second_client.cookies.set("dc_session", second.session_grant.session_credential)
            replays = (
                first_client.post(
                    "/governance/recovery",
                    headers=self.headers(first.csrf_token),
                    json=recovery_body,
                ),
                first_client.post(
                    revoke_path,
                    headers=self.headers(first.csrf_token),
                    json=revoke_body,
                ),
                first_client.post(
                    "/governance/memberships/proposals",
                    headers=self.headers(first.csrf_token),
                    json=proposal_body,
                ),
                second_client.post(
                    decision_path,
                    headers=self.headers(second.session_grant.csrf_token),
                    json=decision_body,
                ),
                first_client.post(
                    apply_path,
                    headers=self.headers(first.csrf_token),
                    json=apply_body,
                ),
            )
            self.assertEqual(
                [response.status_code for response in replays],
                [201, 200, 201, 201, 200],
            )
            self.assertEqual(tuple(response.json() for response in replays), originals)
            restarted.store.close()

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
