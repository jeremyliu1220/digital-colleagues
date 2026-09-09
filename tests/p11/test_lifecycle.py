# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from digital_colleagues.adapters.sqlite.p11_store import SQLiteP11Store
from digital_colleagues.adapters.system.deterministic import FixedClock
from digital_colleagues.application.errors import (
    ApplicationError,
    NotFoundError,
    PermissionDeniedError,
    ReplayConflictError,
    StaleConflictError,
)
from digital_colleagues.application.p11_contracts import (
    DeploymentCreationRequest,
    ExactDraftConfirmation,
    ExactLifecycleRequest,
    ExactRebindingRequest,
    PackageRegistrationRequest,
)
from digital_colleagues.core.agent_package import PackageSource
from digital_colleagues.core.deployment import (
    ColleagueDeployment,
    DeploymentDraftKind,
    DeploymentLifecycle,
    PackageInstallState,
    PackageTrustState,
)
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import Principal
from tests.p11.fixtures import (
    NOW,
    ROOT,
    Harness,
    build_harness,
    digest,
    package_archive,
    register_ready,
    valid_package,
)


def confirmed(harness: Harness, deployment_id: str, package_digest: str) -> ColleagueDeployment:
    draft = harness.deployments.create_draft(
        session=harness.session,
        request=DeploymentCreationRequest(
            deployment_id=deployment_id,
            package_id="fixture-agent",
            package_version="1.0.0",
            package_digest=package_digest,
            display_name=deployment_id,
            description="Synthetic bounded deployment.",
            mission="Complete finite synthetic work.",
            service_relationship="Serves the test Admin.",
            granted_capabilities=("notify_human",),
            timezone="UTC",
            idempotency_key=f"create-{deployment_id}",
        ),
    )
    draft = harness.deployments.review(
        session=harness.session,
        deployment_id=deployment_id,
        draft_id=draft.draft_id,
        request=ExactDraftConfirmation(1, draft.canonical_digest, f"review-{deployment_id}"),
    )
    return harness.deployments.confirm(
        session=harness.session,
        deployment_id=deployment_id,
        draft_id=draft.draft_id,
        request=ExactDraftConfirmation(2, draft.canonical_digest, f"confirm-{deployment_id}"),
    )


class LifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.harness = build_harness(Path(self.temporary.name) / "state.sqlite")
        self.package = register_ready(self.harness)

    def tearDown(self) -> None:
        self.harness.store.close()
        self.temporary.cleanup()

    def test_install_does_not_create_or_activate_deployment(self) -> None:
        self.assertEqual(self.harness.store.list_deployments("tenant-local"), ())

    def test_register_trust_and_install_are_three_distinct_states(self) -> None:
        archive = package_archive(valid_package(package_id="state-agent"))
        registered = self.harness.packages.register(
            session=self.harness.session,
            request=PackageRegistrationRequest(
                archive=archive,
                source=PackageSource.LOCAL,
                expected_archive_digest=digest(archive),
            ),
            idempotency_key="register-state-agent",
        )
        self.assertEqual(
            (registered.trust_state, registered.install_state),
            (PackageTrustState.UNTRUSTED, PackageInstallState.NOT_INSTALLED),
        )
        trusted = self.harness.packages.trust(
            session=self.harness.session,
            package_id="state-agent",
            version="1.0.0",
            digest=registered.package_digest,
            expected_revision=1,
            idempotency_key="trust-state-agent",
        )
        replayed = self.harness.packages.trust(
            session=self.harness.session,
            package_id="state-agent",
            version="1.0.0",
            digest=registered.package_digest,
            expected_revision=1,
            idempotency_key="trust-state-agent",
        )
        self.assertEqual((trusted.revision, replayed.revision), (2, 2))
        installed = self.harness.packages.install(
            session=self.harness.session,
            package_id="state-agent",
            version="1.0.0",
            digest=registered.package_digest,
            expected_revision=2,
            idempotency_key="install-state-agent",
        )
        self.assertEqual(installed.install_state, PackageInstallState.INSTALLED)
        self.assertEqual(self.harness.store.list_deployments("tenant-local"), ())

    def test_confirmation_leaves_deployment_in_draft(self) -> None:
        deployment = confirmed(self.harness, "agent-one", self.package.package_digest)
        self.assertEqual(deployment.lifecycle, DeploymentLifecycle.DRAFT)

    def test_draft_review_and_confirmation_replay_exactly(self) -> None:
        draft = self.harness.deployments.create_draft(
            session=self.harness.session,
            request=DeploymentCreationRequest(
                deployment_id="agent-replay",
                package_id="fixture-agent",
                package_version="1.0.0",
                package_digest=self.package.package_digest,
                display_name="Replay Agent",
                description="Synthetic replay test.",
                mission="Confirm exact idempotency.",
                service_relationship="Serves the test Admin.",
                granted_capabilities=("notify_human",),
                timezone="UTC",
                idempotency_key="create-replay",
            ),
        )
        request = ExactDraftConfirmation(1, draft.canonical_digest, "review-replay")
        reviewed = self.harness.deployments.review(
            session=self.harness.session,
            deployment_id="agent-replay",
            draft_id=draft.draft_id,
            request=request,
        )
        replayed = self.harness.deployments.review(
            session=self.harness.session,
            deployment_id="agent-replay",
            draft_id=draft.draft_id,
            request=request,
        )
        self.assertEqual((reviewed.revision, replayed.revision), (2, 2))
        confirmation = ExactDraftConfirmation(2, draft.canonical_digest, "confirm-replay")
        first = self.harness.deployments.confirm(
            session=self.harness.session,
            deployment_id="agent-replay",
            draft_id=draft.draft_id,
            request=confirmation,
        )
        second = self.harness.deployments.confirm(
            session=self.harness.session,
            deployment_id="agent-replay",
            draft_id=draft.draft_id,
            request=confirmation,
        )
        self.assertEqual(first, second)

    def test_distinct_activation_and_pause_transitions(self) -> None:
        deployment = confirmed(self.harness, "agent-one", self.package.package_digest)
        active = self.harness.deployments.transition(
            session=self.harness.session,
            deployment_id="agent-one",
            request=ExactLifecycleRequest("active", 1, deployment.package_digest, "activate-one"),
        ).deployment
        paused = self.harness.deployments.transition(
            session=self.harness.session,
            deployment_id="agent-one",
            request=ExactLifecycleRequest("paused", 2, deployment.package_digest, "pause-one"),
        ).deployment
        self.assertEqual(
            (active.lifecycle, paused.lifecycle),
            (DeploymentLifecycle.ACTIVE, DeploymentLifecycle.PAUSED),
        )

    def test_illegal_draft_to_paused_transition_fails_closed(self) -> None:
        deployment = confirmed(self.harness, "agent-one", self.package.package_digest)
        with self.assertRaises(PermissionDeniedError):
            self.harness.deployments.transition(
                session=self.harness.session,
                deployment_id="agent-one",
                request=ExactLifecycleRequest(
                    "paused", 1, deployment.package_digest, "bad-transition"
                ),
            )

    def test_replay_rebinding_fails_closed(self) -> None:
        deployment = confirmed(self.harness, "agent-one", self.package.package_digest)
        self.harness.deployments.transition(
            session=self.harness.session,
            deployment_id="agent-one",
            request=ExactLifecycleRequest("active", 1, deployment.package_digest, "same-key"),
        )
        with self.assertRaises(ReplayConflictError):
            self.harness.deployments.transition(
                session=self.harness.session,
                deployment_id="agent-one",
                request=ExactLifecycleRequest("retired", 2, deployment.package_digest, "same-key"),
            )

    def test_stale_revision_and_digest_fail_closed(self) -> None:
        deployment = confirmed(self.harness, "agent-stale", self.package.package_digest)
        for request in (
            ExactLifecycleRequest("active", 2, deployment.package_digest, "stale-revision"),
            ExactLifecycleRequest("active", 1, "sha256:" + "0" * 64, "stale-digest"),
        ):
            with self.subTest(request=request), self.assertRaises(StaleConflictError):
                self.harness.deployments.transition(
                    session=self.harness.session,
                    deployment_id="agent-stale",
                    request=request,
                )

    def test_revocation_blocks_active_exact_binding(self) -> None:
        deployment = confirmed(self.harness, "agent-one", self.package.package_digest)
        self.harness.deployments.transition(
            session=self.harness.session,
            deployment_id="agent-one",
            request=ExactLifecycleRequest("active", 1, deployment.package_digest, "activate-one"),
        )
        revoked = self.harness.packages.revoke(
            session=self.harness.session,
            package_id="fixture-agent",
            version="1.0.0",
            digest=self.package.package_digest,
            expected_revision=3,
            idempotency_key="revoke-one",
        )
        current = self.harness.store.get_deployment(deployment.namespace)
        self.assertEqual(
            (revoked.trust_state.value, current.lifecycle.value), ("revoked", "blocked")
        )

    def test_only_active_deployment_is_runtime_eligible(self) -> None:
        deployment = confirmed(self.harness, "agent-one", self.package.package_digest)
        self.assertFalse(self.harness.store.deployment_is_active(deployment.namespace))
        self.harness.deployments.transition(
            session=self.harness.session,
            deployment_id="agent-one",
            request=ExactLifecycleRequest("active", 1, deployment.package_digest, "activate-one"),
        )
        self.assertTrue(self.harness.store.deployment_is_active(deployment.namespace))

    def test_upgrade_and_rollback_require_review_and_separate_activation(self) -> None:
        version_two = register_ready(self.harness, version="2.0.0")
        original = confirmed(self.harness, "agent-upgrade", self.package.package_digest)
        upgrade = self.harness.deployments.rebinding_draft(
            session=self.harness.session,
            deployment_id="agent-upgrade",
            request=ExactRebindingRequest(
                "fixture-agent",
                "2.0.0",
                version_two.package_digest,
                original.revision,
                "upgrade-two",
            ),
            kind=DeploymentDraftKind.UPGRADE,
        )
        self.assertEqual(
            self.harness.store.get_deployment(original.namespace).package_digest,
            self.package.package_digest,
        )
        self.assertTrue(upgrade.permission_diff["requested"])
        reviewed = self.harness.deployments.review(
            session=self.harness.session,
            deployment_id="agent-upgrade",
            draft_id=upgrade.draft_id,
            request=ExactDraftConfirmation(1, upgrade.canonical_digest, "review-upgrade"),
        )
        upgraded = self.harness.deployments.confirm(
            session=self.harness.session,
            deployment_id="agent-upgrade",
            draft_id=upgrade.draft_id,
            request=ExactDraftConfirmation(2, reviewed.canonical_digest, "confirm-upgrade"),
        )
        self.assertEqual(
            (upgraded.package_digest, upgraded.lifecycle),
            (version_two.package_digest, DeploymentLifecycle.DRAFT),
        )
        rollback = self.harness.deployments.rebinding_draft(
            session=self.harness.session,
            deployment_id="agent-upgrade",
            request=ExactRebindingRequest(
                "fixture-agent",
                "1.0.0",
                self.package.package_digest,
                upgraded.revision,
                "rollback-one",
            ),
            kind=DeploymentDraftKind.ROLLBACK,
        )
        rollback = self.harness.deployments.review(
            session=self.harness.session,
            deployment_id="agent-upgrade",
            draft_id=rollback.draft_id,
            request=ExactDraftConfirmation(1, rollback.canonical_digest, "review-rollback"),
        )
        rolled_back = self.harness.deployments.confirm(
            session=self.harness.session,
            deployment_id="agent-upgrade",
            draft_id=rollback.draft_id,
            request=ExactDraftConfirmation(2, rollback.canonical_digest, "confirm-rollback"),
        )
        self.assertEqual(
            (rolled_back.package_digest, rolled_back.lifecycle),
            (self.package.package_digest, DeploymentLifecycle.DRAFT),
        )

    def test_revoked_and_stale_rollback_targets_fail_closed(self) -> None:
        version_two = register_ready(self.harness, version="2.0.0")
        original = confirmed(self.harness, "agent-rollback", self.package.package_digest)
        upgrade = self.harness.deployments.rebinding_draft(
            session=self.harness.session,
            deployment_id="agent-rollback",
            request=ExactRebindingRequest(
                "fixture-agent",
                "2.0.0",
                version_two.package_digest,
                original.revision,
                "prepare-upgrade",
            ),
            kind=DeploymentDraftKind.UPGRADE,
        )
        upgrade = self.harness.deployments.review(
            session=self.harness.session,
            deployment_id="agent-rollback",
            draft_id=upgrade.draft_id,
            request=ExactDraftConfirmation(1, upgrade.canonical_digest, "review-prepare"),
        )
        upgraded = self.harness.deployments.confirm(
            session=self.harness.session,
            deployment_id="agent-rollback",
            draft_id=upgrade.draft_id,
            request=ExactDraftConfirmation(2, upgrade.canonical_digest, "confirm-prepare"),
        )
        self.harness.packages.revoke(
            session=self.harness.session,
            package_id="fixture-agent",
            version="1.0.0",
            digest=self.package.package_digest,
            expected_revision=3,
            idempotency_key="revoke-rollback-target",
        )
        with self.assertRaises(PermissionDeniedError):
            self.harness.deployments.rebinding_draft(
                session=self.harness.session,
                deployment_id="agent-rollback",
                request=ExactRebindingRequest(
                    "fixture-agent",
                    "1.0.0",
                    self.package.package_digest,
                    upgraded.revision,
                    "revoked-rollback",
                ),
                kind=DeploymentDraftKind.ROLLBACK,
            )
        with self.assertRaises(StaleConflictError):
            self.harness.deployments.rebinding_draft(
                session=self.harness.session,
                deployment_id="agent-rollback",
                request=ExactRebindingRequest(
                    "fixture-agent",
                    "2.0.0",
                    version_two.package_digest,
                    upgraded.revision + 1,
                    "stale-upgrade",
                ),
                kind=DeploymentDraftKind.UPGRADE,
            )

    def test_model_cannot_self_activate_and_namespaces_do_not_alias(self) -> None:
        deployment = confirmed(self.harness, "agent-isolated", self.package.package_digest)
        model_session = replace(
            self.harness.session,
            principal=Principal.model(tenant_id="tenant-local", principal_id="untrusted-model"),
        )
        with self.assertRaises(ApplicationError):
            self.harness.deployments.transition(
                session=model_session,
                deployment_id="agent-isolated",
                request=ExactLifecycleRequest(
                    "active", 1, deployment.package_digest, "model-self-activate"
                ),
            )
        with self.assertRaises(NotFoundError):
            self.harness.store.get_deployment(
                Namespace.colleague("tenant-local", "different-agent")
            )
        with self.assertRaises(NotFoundError):
            self.harness.store.get_package(
                "different-tenant", "fixture-agent", "1.0.0", self.package.package_digest
            )

    def test_lifecycle_audit_has_exact_actor_and_causality(self) -> None:
        deployment = confirmed(self.harness, "agent-audit", self.package.package_digest)
        self.harness.deployments.transition(
            session=self.harness.session,
            deployment_id="agent-audit",
            request=ExactLifecycleRequest("active", 1, deployment.package_digest, "activate-audit"),
        )
        audit = self.harness.deployments.audit(
            session=self.harness.session, deployment_id="agent-audit"
        )
        lifecycle = next(record for record in audit if record["action"] == "lifecycle")
        self.assertEqual(lifecycle["actor_kind"], "human")
        self.assertEqual(
            lifecycle["actor_principal_id"], self.harness.session.principal.principal_id
        )
        self.assertTrue(str(lifecycle["correlation_id"]))
        self.assertTrue(str(lifecycle["causation_id"]))

    def test_selection_is_replay_safe_and_audited_in_its_transaction(self) -> None:
        confirmed(self.harness, "agent-select", self.package.package_digest)
        selected = self.harness.deployments.select(
            session=self.harness.session,
            deployment_id="agent-select",
            idempotency_key="select-agent",
        )
        replayed = self.harness.deployments.select(
            session=self.harness.session,
            deployment_id="agent-select",
            idempotency_key="select-agent",
        )
        self.assertEqual(selected, replayed)
        audit = self.harness.deployments.audit(
            session=selected,
            deployment_id="agent-select",
        )
        selection = [record for record in audit if record["action"] == "deployment_selected"]
        self.assertEqual(len(selection), 1)
        self.assertEqual(
            selection[0]["actor_principal_id"], self.harness.session.principal.principal_id
        )

    def test_tenth_succeeds_and_eleventh_is_audited_refusal(self) -> None:
        results = []
        for index in range(1, 12):
            deployment_id = f"agent-{index}"
            deployment = confirmed(self.harness, deployment_id, self.package.package_digest)
            results.append(
                self.harness.deployments.transition(
                    session=self.harness.session,
                    deployment_id=deployment_id,
                    request=ExactLifecycleRequest(
                        "active", 1, deployment.package_digest, f"activate-{index}"
                    ),
                )
            )
        self.assertTrue(results[9].accepted)
        self.assertEqual(results[9].active_count, 10)
        self.assertFalse(results[10].accepted)
        self.assertEqual(results[10].result, "active_deployment_limit_reached")
        replayed = self.harness.deployments.transition(
            session=self.harness.session,
            deployment_id="agent-11",
            request=ExactLifecycleRequest("active", 1, self.package.package_digest, "activate-11"),
        )
        self.assertFalse(replayed.accepted)
        self.assertEqual(replayed.result, "active_deployment_limit_reached")

    def test_concurrent_activation_cannot_exceed_ten(self) -> None:
        deployments = [
            confirmed(self.harness, f"race-{index}", self.package.package_digest)
            for index in range(1, 12)
        ]
        stores = [
            SQLiteP11Store(
                Path(self.temporary.name) / "state.sqlite",
                migrations_path=ROOT / "migrations",
                clock=FixedClock(NOW),
            )
            for _ in deployments
        ]

        def activate(index: int) -> bool:
            deployment = deployments[index]
            return (
                stores[index]
                .transition_deployment(
                    namespace=deployment.namespace,
                    target="active",
                    actor=self.harness.session.principal,
                    expected_revision=1,
                    expected_package_digest=deployment.package_digest,
                    idempotency_key=f"race-{index}",
                    request_digest="sha256:" + f"{index + 1:064x}",
                    occurred_at=NOW,
                    correlation_id=f"race-correlation-{index}",
                    causation_id=f"race-causation-{index}",
                )
                .accepted
            )

        try:
            with ThreadPoolExecutor(max_workers=11) as executor:
                accepted = list(executor.map(activate, range(11)))
        finally:
            for store in stores:
                store.close()
        self.assertEqual(sum(accepted), 10)
        self.assertEqual(
            sum(
                deployment.lifecycle is DeploymentLifecycle.ACTIVE
                for deployment in self.harness.store.list_deployments("tenant-local")
            ),
            10,
        )


if __name__ == "__main__":
    unittest.main()
