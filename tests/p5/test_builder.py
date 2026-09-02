# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import subprocess
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from fastapi.testclient import TestClient

from digital_colleagues.adapters.sqlite.p5_store import SQLiteP5Store
from digital_colleagues.adapters.system.deterministic import StableHashIdentifier
from digital_colleagues.application.errors import (
    NotFoundError,
    PermissionDeniedError,
    StaleConflictError,
)
from digital_colleagues.application.p4_services import AuthenticationService
from digital_colleagues.application.p5_contracts import ConfirmDraftRequest
from digital_colleagues.application.p5_services import RevisionedColleagueBuilderService
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import Principal
from digital_colleagues.local.security import CredentialDigests
from scripts import check_p4_repository as p4_repository_gate
from scripts import check_p5_repository as repository_gate
from scripts.collect_p5_evidence import REQUIRED_GATES, EvidenceError, write_p5_evidence
from scripts.run_p5_unittest_suite import REQUIRED_TEST_BOUNDARIES
from tests.p5.fixtures import (
    ROOT,
    P5Harness,
    build_harness,
    initial_colleague_body,
    update_body,
)

ORIGIN = {"Origin": "http://testserver"}


class P5BuilderTests(unittest.TestCase):
    def _bootstrap(self, harness: P5Harness) -> tuple[TestClient, str]:
        _, plaintext = harness.authentication.ensure_bootstrap()
        assert plaintext is not None
        harness.authentication.claim_operator_retrieval(plaintext)
        client = TestClient(harness.app())
        exchanged = client.post(
            "/auth/bootstrap/exchange",
            headers=ORIGIN,
            json={"token": plaintext},
        )
        self.assertEqual(exchanged.status_code, 201, exchanged.text)
        return client, exchanged.json()["csrf_token"]

    @staticmethod
    def _headers(csrf: str) -> dict[str, str]:
        return {**ORIGIN, "X-CSRF-Token": csrf}

    def _initial(self, harness: P5Harness) -> tuple[TestClient, str]:
        client, csrf = self._bootstrap(harness)
        created = client.post(
            "/colleagues",
            headers=self._headers(csrf),
            json=initial_colleague_body(),
        )
        self.assertEqual(created.status_code, 201, created.text)
        csrf = client.get("/auth/session").json()["csrf_token"]
        return client, csrf

    def _create_and_update(
        self,
        client: TestClient,
        csrf: str,
        *,
        create_key: str,
        update_key: str,
        display_name: str,
        mission: str,
        wake_limit: int = 8,
        run_state: str = "active",
    ) -> dict[str, object]:
        created = client.post(
            "/colleagues/drafts",
            headers=self._headers(csrf),
            json={"idempotency_key": create_key},
        )
        self.assertEqual(created.status_code, 201, created.text)
        draft = created.json()["draft"]
        updated = client.put(
            f"/colleagues/drafts/{draft['draft_id']}",
            headers=self._headers(csrf),
            json=update_body(
                draft,
                key=update_key,
                display_name=display_name,
                mission=mission,
                wake_limit=wake_limit,
                run_state=run_state,
            ),
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        return cast(dict[str, object], updated.json()["draft"])

    def _review(
        self, client: TestClient, csrf: str, draft: dict[str, object], key: str
    ) -> dict[str, object]:
        response = client.post(
            f"/colleagues/drafts/{draft['draft_id']}/review",
            headers=self._headers(csrf),
            json={"expected_draft_revision": draft["revision"], "idempotency_key": key},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return cast(dict[str, object], response.json()["draft"])

    @staticmethod
    def _confirm_body(draft: dict[str, object], key: str) -> dict[str, object]:
        return {
            "expected_draft_revision": draft["revision"],
            "expected_base_profile_revision": draft["base_profile_revision"],
            "expected_base_mandate_revision": draft["base_mandate_revision"],
            "expected_base_policy_revision": draft["base_policy_revision"],
            "expected_canonical_digest": draft["canonical_digest"],
            "idempotency_key": key,
        }

    def test_draft_is_inert_defaults_are_explicit_and_exact_confirmation_restarts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p5-builder-") as temporary:
            database = Path(temporary) / "state.sqlite"
            harness = build_harness(database)
            client, csrf = self._initial(harness)

            before = client.get("/p5/studio/state").json()
            self.assertEqual(before["active"]["policy_status"], "legacy_unconfirmed")
            self.assertIsNone(before["active"]["policy"])
            self.assertEqual(
                before["active"]["mandate"]["working_context"]["timezone"],
                "Asia/Taipei",
            )

            created = client.post(
                "/colleagues/drafts",
                headers=self._headers(csrf),
                json={"idempotency_key": "draft-defaults"},
            )
            self.assertEqual(created.status_code, 201, created.text)
            payload = created.json()
            draft = payload["draft"]
            defaults = {item["path"]: item for item in draft["explicit_defaults"]}
            self.assertEqual(defaults["policy.timezone"]["value"]["value"], "UTC")
            self.assertEqual(defaults["policy.wake_limit"]["value"]["value"], 24)
            self.assertTrue(payload["identity_card_preview"]["projection_only"])
            self.assertTrue(payload["identity_card_preview"]["inert_until_confirmation"])
            self.assertEqual(draft["base_policy_revision"], 0)
            self.assertEqual(draft["base_profile_id"], before["active"]["profile"]["profile_id"])
            self.assertEqual(draft["base_mandate_id"], before["active"]["mandate"]["mandate_id"])
            self.assertIsNone(draft["base_policy_id"])
            self.assertEqual(draft["proposed_policy"]["timezone"], "UTC")
            self.assertNotIn("free-form legacy", str(draft["proposed_policy"]))

            still_active = client.get("/p5/studio/state").json()["active"]
            self.assertEqual(still_active["profile_revision"], 1)
            self.assertEqual(still_active["mandate_revision"], 1)
            self.assertEqual(still_active["policy_revision"], 0)

            changed = client.put(
                f"/colleagues/drafts/{draft['draft_id']}",
                headers=self._headers(csrf),
                json=update_body(
                    draft,
                    key="update-defaults",
                    display_name="Atlas Prime",
                    mission="Complete the exact P5 synthetic task",
                    wake_limit=8,
                ),
            )
            self.assertEqual(changed.status_code, 200, changed.text)
            draft = changed.json()["draft"]
            self.assertEqual(draft["revision"], 2)
            self.assertTrue(draft["explicit_defaults"])
            diff = {(item["section"], item["path"]): item for item in draft["diff"]}
            self.assertFalse(diff[("profile", "display_name")]["authoritative"])
            self.assertEqual(diff[("profile", "display_name")]["classification"], "changed")
            self.assertTrue(diff[("mandate", "mission")]["authoritative"])
            self.assertEqual(diff[("policy", "wake_budget")]["classification"], "changed")
            self.assertEqual(client.get("/p5/studio/state").json()["active"], still_active)

            reviewed = self._review(client, csrf, draft, "review-defaults")
            self.assertEqual(reviewed["state"], "reviewable")
            wrong = self._confirm_body(reviewed, "confirm-wrong")
            wrong["expected_canonical_digest"] = "sha256:" + "0" * 64
            refused = client.post(
                f"/colleagues/drafts/{reviewed['draft_id']}/confirm",
                headers=self._headers(csrf),
                json=wrong,
            )
            self.assertEqual(refused.status_code, 409, refused.text)
            self.assertEqual(refused.json()["detail"]["code"], "StaleConflictError")

            exact = self._confirm_body(reviewed, "confirm-defaults")
            confirmed = client.post(
                f"/colleagues/drafts/{reviewed['draft_id']}/confirm",
                headers=self._headers(csrf),
                json=exact,
            )
            self.assertEqual(confirmed.status_code, 200, confirmed.text)
            result = confirmed.json()["confirmation"]
            self.assertEqual(
                (result["profile_revision"], result["mandate_revision"], result["policy_revision"]),
                (2, 2, 1),
            )
            replay = client.post(
                f"/colleagues/drafts/{reviewed['draft_id']}/confirm",
                headers=self._headers(csrf),
                json=exact,
            )
            self.assertEqual(replay.status_code, 200, replay.text)
            self.assertTrue(replay.json()["confirmation"]["replayed"])
            rebound = client.post(
                f"/colleagues/drafts/{reviewed['draft_id']}/confirm",
                headers=self._headers(csrf),
                json={**exact, "expected_canonical_digest": "sha256:" + "1" * 64},
            )
            self.assertEqual(rebound.status_code, 409, rebound.text)
            self.assertEqual(rebound.json()["detail"]["code"], "ReplayConflictError")

            audit = client.get(f"/audit/{reviewed['correlation_id']}")
            self.assertEqual(audit.status_code, 200, audit.text)
            record_types = {item["record_type"] for item in audit.json()["records"]}
            self.assertTrue({"colleague_draft", "draft_confirmation"}.issubset(record_types))

            cookie = client.cookies.get("dc_session")
            harness.store.close()
            restarted = build_harness(database)
            restarted_client = TestClient(restarted.app())
            assert cookie is not None
            restarted_client.cookies.set("dc_session", cookie)
            recovered = restarted_client.get("/p5/studio/state")
            self.assertEqual(recovered.status_code, 200, recovered.text)
            state = recovered.json()
            self.assertEqual(state["active"]["identity_card"]["display_name"], "Atlas Prime")
            self.assertEqual(state["active"]["policy"]["wake_budget"]["limit"], 8)
            self.assertEqual(state["drafts"][0]["draft"]["state"], "confirmed")
            restarted.store.close()

    def test_same_base_concurrency_is_atomic_and_second_draft_remains_stale(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p5-cas-") as temporary:
            database = Path(temporary) / "state.sqlite"
            harness = build_harness(database)
            client, csrf = self._initial(harness)
            first = self._create_and_update(
                client,
                csrf,
                create_key="draft-one",
                update_key="update-one",
                display_name="First winner",
                mission="Winner mission",
            )
            second = self._create_and_update(
                client,
                csrf,
                create_key="draft-two",
                update_key="update-two",
                display_name="Second loser",
                mission="Loser mission",
            )
            first = self._review(client, csrf, first, "review-one")
            second = self._review(client, csrf, second, "review-two")
            credential = client.cookies.get("dc_session")
            assert credential is not None
            session = harness.authentication.resolve(credential)
            harness.store.close()

            barrier = threading.Barrier(2)

            def concurrent_confirm(draft: dict[str, object], key: str) -> tuple[str, str]:
                store = SQLiteP5Store(
                    database,
                    migrations_path=ROOT / "migrations",
                    clock=harness.clock,
                )
                builder = RevisionedColleagueBuilderService(
                    store=store,
                    clock=harness.clock,
                    identifiers=StableHashIdentifier("p5-local"),
                )
                body = self._confirm_body(draft, key)
                request = ConfirmDraftRequest(
                    expected_draft_revision=cast(int, body["expected_draft_revision"]),
                    expected_base_profile_revision=cast(
                        int, body["expected_base_profile_revision"]
                    ),
                    expected_base_mandate_revision=cast(
                        int, body["expected_base_mandate_revision"]
                    ),
                    expected_base_policy_revision=cast(int, body["expected_base_policy_revision"]),
                    expected_canonical_digest=cast(str, body["expected_canonical_digest"]),
                    idempotency_key=cast(str, body["idempotency_key"]),
                )
                try:
                    barrier.wait()
                    builder.confirm(
                        session=session,
                        draft_id=cast(str, draft["draft_id"]),
                        request=request,
                    )
                    return cast(str, draft["draft_id"]), "confirmed"
                except StaleConflictError:
                    return cast(str, draft["draft_id"]), "stale"
                finally:
                    store.close()

            with ThreadPoolExecutor(max_workers=2) as executor:
                outcomes = dict(
                    executor.map(
                        lambda item: concurrent_confirm(*item),
                        ((first, "confirm-one"), (second, "confirm-two")),
                    )
                )
            self.assertEqual(set(outcomes.values()), {"confirmed", "stale"})
            recovered = SQLiteP5Store(
                database,
                migrations_path=ROOT / "migrations",
                clock=harness.clock,
            )
            state = recovered.p5_studio_snapshot(session.colleague_namespace())
            by_id = {item.draft_id: item.state.value for item in state.drafts}
            self.assertEqual(by_id, outcomes)
            self.assertIn(
                (state.profile.display_name, state.mandate.mission),
                {("First winner", "Winner mission"), ("Second loser", "Loser mission")},
            )
            recovered.close()

    def test_terminal_lifecycle_authority_input_and_mutation_guards_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p5-guards-") as temporary:
            harness = build_harness(Path(temporary) / "state.sqlite")
            client, csrf = self._initial(harness)
            created = client.post(
                "/colleagues/drafts",
                headers=self._headers(csrf),
                json={"idempotency_key": "cancelled"},
            ).json()["draft"]
            cancelled = client.post(
                f"/colleagues/drafts/{created['draft_id']}/cancel",
                headers=self._headers(csrf),
                json={"expected_draft_revision": 1, "idempotency_key": "cancel-it"},
            )
            self.assertEqual(cancelled.status_code, 200, cancelled.text)
            self.assertEqual(cancelled.json()["draft"]["state"], "cancelled")
            retry = client.put(
                f"/colleagues/drafts/{created['draft_id']}",
                headers=self._headers(csrf),
                json=update_body(created, key="update-cancelled"),
            )
            self.assertEqual(retry.status_code, 409, retry.text)
            self.assertEqual(retry.json()["detail"]["code"], "StaleConflictError")

            ambiguous = update_body(created, key="ambiguous")
            ambiguous["policy"]["authority_expression"] = "whatever the model decides"  # type: ignore[index]
            refused = client.put(
                f"/colleagues/drafts/{created['draft_id']}",
                headers=self._headers(csrf),
                json=ambiguous,
            )
            self.assertEqual(refused.status_code, 422, refused.text)
            injected = {**update_body(created, key="injected"), "tenant_id": "other"}
            self.assertEqual(
                client.put(
                    f"/colleagues/drafts/{created['draft_id']}",
                    headers=self._headers(csrf),
                    json=injected,
                ).status_code,
                422,
            )
            self.assertEqual(
                client.post(
                    "/colleagues/drafts",
                    headers=ORIGIN,
                    json={"idempotency_key": "missing-csrf"},
                ).status_code,
                403,
            )
            self.assertEqual(
                client.post(
                    "/colleagues/drafts",
                    headers={"Origin": "http://evil.invalid", "X-CSRF-Token": csrf},
                    json={"idempotency_key": "bad-origin"},
                ).status_code,
                403,
            )

            credential = client.cookies.get("dc_session")
            assert credential is not None
            admin_session = harness.authentication.resolve(credential)
            for principal in (
                Principal.model(tenant_id=admin_session.tenant_id, principal_id="model-p5"),
                Principal.service(tenant_id=admin_session.tenant_id, principal_id="service-p5"),
            ):
                with self.assertRaises(PermissionDeniedError):
                    harness.builder.create(
                        session=replace(admin_session, principal=principal),
                        idempotency_key=f"forbidden-{principal.kind.value}",
                    )
            with self.assertRaises(NotFoundError):
                harness.store.get_draft(
                    Namespace.colleague("tenant-other", "colleague-other"),
                    created["draft_id"],
                )

            expired_authentication = AuthenticationService(
                store=harness.store,
                clock=type(harness.clock)(harness.clock.now() + timedelta(hours=8)),
                tokens=harness.tokens,
                digests=CredentialDigests(),
                tenant_id=admin_session.tenant_id,
            )
            harness.authentication = expired_authentication
            expired_client = TestClient(harness.app())
            expired_client.cookies.set("dc_session", credential)
            self.assertEqual(expired_client.get("/colleagues/drafts").status_code, 403)
            harness.store.close()


def gate_git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def passing_p5_outcome() -> dict[str, Any]:
    test_ids = sorted(REQUIRED_TEST_BOUNDARIES)
    return {
        "tests_run": len(test_ids),
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "expected_failures": 0,
        "unexpected_successes": 0,
        "gate_passed": True,
        "test_ids": test_ids,
        "fault_boundaries": sorted(REQUIRED_TEST_BOUNDARIES.values()),
    }


class P5RepositoryGateTests(unittest.TestCase):
    def _commit(self, root: Path, message: str) -> str:
        gate_git(root, "add", ".")
        gate_git(
            root,
            "-c",
            "user.name=P5 Gate Test",
            "-c",
            "user.email=p5-gate.invalid",
            "commit",
            "-m",
            message,
        )
        return gate_git(root, "rev-parse", "HEAD")

    @staticmethod
    def _write(root: Path, relative: str, content: str) -> None:
        document = root / relative
        document.parent.mkdir(parents=True, exist_ok=True)
        document.write_text(content, encoding="utf-8")

    def repository(self) -> tuple[Path, dict[str, str]]:
        temporary = tempfile.TemporaryDirectory(prefix="p5-repository-gate-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        gate_git(root, "init", "--initial-branch=main")
        for relative in (
            "artifacts/p0/summary.json",
            "artifacts/p1/summary.json",
            "artifacts/p2/summary.json",
            "artifacts/p3/summary.json",
            "docs/p0/acceptance.md",
            "docs/p1/acceptance.md",
            "docs/p2/acceptance.md",
            "docs/p3/acceptance.md",
            "migrations/001_initial.sql",
            "migrations/002_runtime_indexes.sql",
            "migrations/003_timer_triggers.sql",
            "provenance/p3-migration-receipt.json",
        ):
            self._write(root, relative, f"historical {relative}\n")
        p4_historical_base = self._commit(root, "P0-P3 historical baseline")

        for relative in p4_repository_gate.ACCEPTED_P4_IMMUTABLE_PATHS:
            self._write(root, relative, f"accepted P4 {relative}\n")
        self._write(root, "compose.yaml", "services: {}\n")
        self._write(root, "required-p4.txt", "required P4\n")
        accepted_p4 = self._commit(root, "accepted P4")

        for relative in repository_gate.ACCEPTANCE_DOCUMENT_PATHS:
            self._write(root, relative, f"fixed P5 acceptance {relative}\n")
        p5_acceptance = self._commit(root, "fixed P5 acceptance")

        for relative in repository_gate.ACCEPTED_P5_IMMUTABLE_PATHS:
            document = root / relative
            if not document.exists():
                self._write(root, relative, f"accepted P5 {relative}\n")
        self._write(root, "required-p5.txt", "required P5\n")
        accepted_p5 = self._commit(root, "accepted P5")
        return root, {
            "p4_historical_base": p4_historical_base,
            "accepted_p4": accepted_p4,
            "p5_acceptance": p5_acceptance,
            "accepted_p5": accepted_p5,
        }

    def check(
        self,
        root: Path,
        commits: dict[str, str],
        *,
        accepted_p5: str | None = None,
    ) -> dict[str, object]:
        with (
            patch.object(
                p4_repository_gate,
                "BASE_COMMIT",
                commits["p4_historical_base"],
            ),
            patch.object(
                p4_repository_gate,
                "ACCEPTED_P4_COMMIT",
                commits["accepted_p4"],
            ),
            patch.object(
                p4_repository_gate,
                "REQUIRED_FILES",
                {"compose.yaml", "required-p4.txt"},
            ),
            patch.object(repository_gate, "BASE_COMMIT", commits["accepted_p4"]),
            patch.object(
                repository_gate,
                "ACCEPTANCE_COMMIT",
                commits["p5_acceptance"],
            ),
            patch.object(
                repository_gate,
                "ACCEPTED_P5_COMMIT",
                accepted_p5 or commits["accepted_p5"],
            ),
            patch.object(repository_gate, "REQUIRED_FILES", {"required-p5.txt"}),
        ):
            return repository_gate.check_repository(root)

    def test_accepted_p5_commit_on_main_passes(self) -> None:
        root, commits = self.repository()
        result = self.check(root, commits)
        self.assertEqual(result["branch"], "main")
        self.assertEqual(result["accepted_p5_commit"], commits["accepted_p5"])
        self.assertTrue(result["accepted_p5_ancestor"])

    def test_original_p5_development_branch_at_accepted_commit_passes(self) -> None:
        root, commits = self.repository()
        gate_git(root, "switch", "-c", repository_gate.BRANCH)
        result = self.check(root, commits)
        self.assertEqual(result["branch"], repository_gate.BRANCH)

    def test_normal_descendant_hotfix_branch_passes(self) -> None:
        root, commits = self.repository()
        gate_git(root, "switch", "-c", "codex/p5-post-merge-check")
        self._write(root, "hotfix.txt", "descendant\n")
        self._commit(root, "normal P5 descendant")
        result = self.check(root, commits)
        self.assertEqual(result["branch"], "codex/p5-post-merge-check")
        self.assertTrue(result["accepted_p5_ancestor"])

    def test_different_branch_name_with_accepted_ancestor_passes(self) -> None:
        root, commits = self.repository()
        gate_git(root, "switch", "-c", "codex/p6-governance-hardening")
        result = self.check(root, commits)
        self.assertEqual(result["branch"], "codex/p6-governance-hardening")

    def test_missing_accepted_p5_ancestor_fails_closed(self) -> None:
        root, commits = self.repository()
        gate_git(root, "switch", "-c", "unrelated", commits["p5_acceptance"])
        with self.assertRaisesRegex(repository_gate.RepositoryError, "not an ancestor"):
            self.check(root, commits)

    def test_unavailable_accepted_p5_commit_fails_closed(self) -> None:
        root, commits = self.repository()
        with self.assertRaisesRegex(repository_gate.RepositoryError, "commit is unavailable"):
            self.check(root, commits, accepted_p5="f" * 40)

    def test_accepted_p5_immutable_file_deletion_fails_closed(self) -> None:
        root, commits = self.repository()
        for relative in repository_gate.ACCEPTED_P5_IMMUTABLE_PATHS:
            with self.subTest(relative=relative):
                document = root / relative
                baseline = document.read_bytes()
                document.unlink()
                with self.assertRaisesRegex(
                    repository_gate.RepositoryError,
                    "immutable file is missing",
                ):
                    self.check(root, commits)
                document.write_bytes(baseline)

    def test_accepted_p5_immutable_file_modification_fails_closed(self) -> None:
        root, commits = self.repository()
        for relative in repository_gate.ACCEPTED_P5_IMMUTABLE_PATHS:
            with self.subTest(relative=relative):
                document = root / relative
                baseline = document.read_bytes()
                document.write_text("changed\n", encoding="utf-8")
                with self.assertRaisesRegex(
                    repository_gate.RepositoryError,
                    "immutable file changed",
                ):
                    self.check(root, commits)
                document.write_bytes(baseline)

    def test_fixed_acceptance_document_protections_remain_effective(self) -> None:
        root, commits = self.repository()
        for relative in repository_gate.ACCEPTANCE_DOCUMENT_PATHS:
            if relative in repository_gate.ACCEPTED_P5_IMMUTABLE_PATHS:
                continue
            with self.subTest(relative=relative):
                document = root / relative
                baseline = document.read_bytes()
                document.write_text("changed\n", encoding="utf-8")
                with self.assertRaisesRegex(
                    repository_gate.RepositoryError,
                    "acceptance document changed",
                ):
                    self.check(root, commits)
                document.unlink()
                with self.assertRaisesRegex(
                    repository_gate.RepositoryError,
                    "acceptance document is missing",
                ):
                    self.check(root, commits)
                document.write_bytes(baseline)

    def test_retained_p0_p4_immutable_protections_remain_effective(self) -> None:
        root, commits = self.repository()
        for relative in (
            "docs/p0/acceptance.md",
            "docs/p1/acceptance.md",
            "docs/p2/acceptance.md",
            "docs/p3/acceptance.md",
            "migrations/001_initial.sql",
            "migrations/002_runtime_indexes.sql",
            "migrations/003_timer_triggers.sql",
            *p4_repository_gate.ACCEPTED_P4_IMMUTABLE_PATHS,
        ):
            with self.subTest(relative=relative):
                document = root / relative
                baseline = document.read_bytes()
                document.write_text("changed\n", encoding="utf-8")
                with self.assertRaises(p4_repository_gate.RepositoryError):
                    self.check(root, commits)
                document.write_bytes(baseline)

    def test_runtime_credential_and_build_residue_still_fail_closed(self) -> None:
        for relative in ("state.sqlite", ".env", "build/output.js"):
            with self.subTest(relative=relative):
                root, commits = self.repository()
                self._write(root, relative, "residue\n")
                with self.assertRaisesRegex(
                    p4_repository_gate.RepositoryError,
                    "residue is present",
                ):
                    self.check(root, commits)

    def test_exact_repository_root_and_required_files_fail_closed(self) -> None:
        root, commits = self.repository()
        nested = root / "nested"
        nested.mkdir()
        with self.assertRaisesRegex(repository_gate.RepositoryError, "root is not exact"):
            self.check(nested, commits)
        (root / "required-p5.txt").unlink()
        with self.assertRaisesRegex(repository_gate.RepositoryError, "required P5 files"):
            self.check(root, commits)

    def test_real_hotfix_tree_is_an_accepted_p5_descendant(self) -> None:
        result = repository_gate.check_repository(ROOT)
        self.assertEqual(result["accepted_p5_commit"], repository_gate.ACCEPTED_P5_COMMIT)
        self.assertTrue(result["accepted_p5_ancestor"])


class P5EvidenceGuardTests(unittest.TestCase):
    def test_evidence_writer_retains_fixed_development_branch_and_base_guards(self) -> None:
        summary = json.loads((ROOT / "artifacts/p5/summary.json").read_text(encoding="utf-8"))
        results = summary["results"]
        with tempfile.TemporaryDirectory(prefix="p5-evidence-guard-") as temporary:
            evidence_path = Path(temporary) / "summary.json"
            for branch, merge_base in (
                ("main", repository_gate.BASE_COMMIT),
                ("codex/not-p5-acceptance", repository_gate.BASE_COMMIT),
                (repository_gate.BRANCH, "d" * 40),
            ):
                with self.subTest(branch=branch, merge_base=merge_base):
                    with self.assertRaisesRegex(EvidenceError, "branch or merge-base drifted"):
                        write_p5_evidence(
                            evidence_path=evidence_path,
                            results=results,
                            unittest_outcome=passing_p5_outcome(),
                            verified_gates=set(REQUIRED_GATES),
                            branch=branch,
                            implementation_commit="c" * 40,
                            merge_base=merge_base,
                            tree_digest="sha256:" + ("e" * 64),
                        )
            self.assertFalse(evidence_path.exists())

    def test_evidence_writer_retains_complete_gate_and_commit_shape_guards(self) -> None:
        summary = json.loads((ROOT / "artifacts/p5/summary.json").read_text(encoding="utf-8"))
        results = summary["results"]
        with tempfile.TemporaryDirectory(prefix="p5-evidence-completeness-") as temporary:
            evidence_path = Path(temporary) / "summary.json"
            with self.assertRaisesRegex(EvidenceError, "missing required mechanical gates"):
                write_p5_evidence(
                    evidence_path=evidence_path,
                    results=results,
                    unittest_outcome=passing_p5_outcome(),
                    verified_gates=set(),
                    branch=repository_gate.BRANCH,
                    implementation_commit="c" * 40,
                    merge_base=repository_gate.BASE_COMMIT,
                    tree_digest="sha256:" + ("e" * 64),
                )
            with self.assertRaisesRegex(EvidenceError, "not a real commit SHA"):
                write_p5_evidence(
                    evidence_path=evidence_path,
                    results=results,
                    unittest_outcome=passing_p5_outcome(),
                    verified_gates=set(REQUIRED_GATES),
                    branch=repository_gate.BRANCH,
                    implementation_commit="not-a-commit",
                    merge_base=repository_gate.BASE_COMMIT,
                    tree_digest="sha256:" + ("e" * 64),
                )
            self.assertFalse(evidence_path.exists())


if __name__ == "__main__":
    unittest.main()
