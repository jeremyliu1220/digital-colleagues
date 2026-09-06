# SPDX-License-Identifier: Apache-2.0

"""Exercise the P8 candidate through actual deterministic Compose backup and restore."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import platform
import secrets
import shutil
import sys
import tempfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p4_compose_runtime import (
    ComposeRuntimeError,
    _cleanup,
    _compose,
    _container_ids,
    _now,
    _port,
    _request,
    _run,
    _wait_json,
    _wait_studio,
)
from scripts.check_p5_compose_runtime import _create_update_review
from scripts.p8_release_support import (
    ARTIFACT_NAMES,
    BASE_COMMIT,
    NODE_VERSION,
    NPM_VERSION,
    ReleaseError,
    _extract_source,
    _source_entries,
    build_candidate,
)
from scripts.p8_release_support import _run as _release_run

COLLEAGUE_FIELD = "colleague" + "_id"


def _credential_id(response: dict[str, Any]) -> str:
    credential = response.get("credential")
    if not isinstance(credential, dict) or not isinstance(credential.get("credential_id"), str):
        raise ComposeRuntimeError("governance permit lacked a safe identity")
    if any(key in credential for key in ("token", "token_digest", "plaintext")):
        raise ComposeRuntimeError("governance API returned credential material")
    return cast(str, credential["credential_id"])


def _operator(
    docker: str,
    project: str,
    root: Path,
    environment: dict[str, str],
    command: str,
    credential_id: str | None = None,
) -> str:
    arguments = [
        "run",
        "--rm",
        "--no-deps",
        "-T",
        "operator",
        "python",
        "-m",
        "digital_colleagues.local.operator",
        command,
    ]
    if credential_id is not None:
        arguments.extend(["--credential-id", credential_id])
    value = _compose(docker, project, arguments, root=root, environment=environment).stdout.strip()
    if not value:
        raise ComposeRuntimeError("operator boundary returned an empty result")
    return value


def _operations_command(
    docker: str,
    project: str,
    root: Path,
    environment: dict[str, str],
    arguments: list[str],
    *,
    running: bool,
) -> tuple[str, str]:
    prefix = ["exec", "-T", "api"] if running else ["run", "--rm", "--no-deps", "-T", "api"]
    completed = _compose(
        docker,
        project,
        [
            *prefix,
            "python",
            "-B",
            "-m",
            "digital_colleagues.operations",
            *arguments,
        ],
        root=root,
        environment=environment,
    )
    return completed.stdout, completed.stderr


def _operation_json(stdout: str, stderr: str) -> dict[str, Any]:
    for stream in (stdout, stderr):
        for line in reversed(stream.splitlines()):
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
    raise ComposeRuntimeError("operation command returned no JSON object")


def _write_override(path: Path, canaries: tuple[str, str, str]) -> None:
    credential, private_payload, local_marker = canaries
    path.write_text(
        "services:\n"
        "  api:\n"
        "    volumes:\n"
        "      - ${DC_P8_OPERATOR_DIR}:/operator\n"
        "    environment:\n"
        f"      DC_P8_CREDENTIAL_CANARY: {credential}\n"
        f"      DC_P8_PRIVATE_CANARY: {private_payload}\n"
        f"      DC_P8_PATH_CANARY: {local_marker}\n"
        "  worker:\n"
        "    environment:\n"
        f"      DC_P8_CREDENTIAL_CANARY: {credential}\n"
        f"      DC_P8_PRIVATE_CANARY: {private_payload}\n",
        encoding="utf-8",
    )


def _scan_bytes(paths: tuple[Path, ...], forbidden: tuple[str, ...]) -> None:
    for path in paths:
        if not path.is_file():
            raise ComposeRuntimeError("a required private runtime artifact is missing")
        content = path.read_bytes()
        if any(value.encode() in content for value in forbidden if value):
            raise ComposeRuntimeError("a runtime canary entered an artifact")


def _extract_accepted_p7(root: Path, destination: Path) -> None:
    if destination.exists():
        raise ComposeRuntimeError("accepted P7 extraction destination already exists")
    destination.mkdir()
    tree = _release_run(["git", "rev-parse", f"{BASE_COMMIT}^{{tree}}"], cwd=root).decode().strip()
    if tree != "4ebfc2bdfcd97e34256ec7a34ff58b0063c05ed7":
        raise ComposeRuntimeError("accepted P7 Git tree identity drifted")
    for relative, mode, object_id in _source_entries(root, BASE_COMMIT):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_release_run(["git", "cat-file", "blob", object_id], cwd=root))
        target.chmod(0o755 if mode == "100755" else 0o644)


def _private_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ComposeRuntimeError("private transition metadata was invalid") from exc
    if not isinstance(value, dict):
        raise ComposeRuntimeError("private transition metadata was invalid")
    return value


def _write_private_json(path: Path, value: dict[str, Any]) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _create_p7_fixture(p7_source: Path, database: Path, private_metadata: Path) -> None:
    sys.path.insert(0, str(p7_source))
    sys.path.insert(0, str(p7_source / "src"))
    from digital_colleagues import __version__
    from digital_colleagues.application.p4_contracts import WorkAssignmentRequest
    from digital_colleagues.application.p6_contracts import ChangeDecisionRequest
    from digital_colleagues.core.effects import ApprovalChoice
    from digital_colleagues.core.governance import ChangeChoice
    from digital_colleagues.core.principals import HumanRole
    from tests.p6.fixtures import build_harness, initial_request
    from tests.p6.test_authentication_rbac import bootstrap, enroll

    if __version__ != "0.0.0" or database.exists() or private_metadata.exists():
        raise ComposeRuntimeError("P7 fixture boundary was invalid")
    harness = build_harness(database, now=datetime.now(UTC))
    first_credential, first = bootstrap(harness)
    _, second = enroll(
        harness,
        issuer=first,
        role=HumanRole.TENANT_ADMIN,
        scopes=("*",),
        key="p8-upgrade-second-admin",
    )
    profile, _, _ = harness.colleagues.create(session=first.session, request=initial_request())
    colleague_id = profile.namespace.scope_id
    if colleague_id is None:
        raise ComposeRuntimeError("P7 fixture namespace was invalid")
    first_session = harness.authentication.bind_colleague(
        first.session,
        colleague_id,
        idempotency_key="p8-upgrade-first-bind",
    )
    second_session = harness.authentication.bind_colleague(
        second.session_grant.session,
        colleague_id,
        idempotency_key="p8-upgrade-second-bind",
    )
    draft = harness.inner_builder.create(
        session=first_session,
        idempotency_key="p8-upgrade-policy-draft",
    )
    reviewed = harness.inner_builder.review(
        session=first_session,
        draft_id=draft.draft_id,
        expected_revision=draft.revision,
    )
    proposed = harness.changes.propose_draft(
        session=first_session,
        draft_id=reviewed.draft_id,
        expected_revision=reviewed.revision,
        expected_digest=reviewed.canonical_digest,
        idempotency_key="p8-upgrade-policy-proposal",
    )
    _, decision = harness.changes.decide(
        session=second_session,
        namespace=profile.namespace,
        proposal_id=proposed.proposal_id,
        request=ChangeDecisionRequest(
            proposal_revision=proposed.revision,
            proposal_digest=proposed.canonical_digest,
            choice=ChangeChoice.APPROVE,
            idempotency_key="p8-upgrade-policy-approval",
        ),
    )
    harness.changes.apply_draft(
        session=first_session,
        namespace=profile.namespace,
        proposal_id=proposed.proposal_id,
        decision_id=decision.decision_id,
        idempotency_key="p8-upgrade-policy-confirm",
    )
    active_profile, active_mandate = harness.store.active_configuration(profile.namespace)
    work, _ = harness.colleagues.assign_work(
        session=first_session,
        request=WorkAssignmentRequest(
            title="P7 durable pre-upgrade work",
            description="Synthetic first-release transition fixture.",
            responsibility_id=active_mandate.responsibilities[0].responsibility_id,
            idempotency_key="p8-upgrade-work",
        ),
    )
    event_correlation = ""
    for trigger_class, no_op, key in (
        ("timer", True, "p8-upgrade-timer"),
        ("event", False, "p8-upgrade-event"),
    ):
        trigger = harness.controller.submit_trigger(
            session=first_session,
            work_id=work.work_id,
            trigger_class=trigger_class,
            deterministic_noop=no_op,
            idempotency_key=key,
        )
        if trigger_class == "event":
            if not isinstance(trigger, dict) or not isinstance(trigger.get("correlation_id"), str):
                raise ComposeRuntimeError("P7 fixture correlation was invalid")
            event_correlation = trigger["correlation_id"]
        harness.controller.process_once(
            harness.controller.service_context(active_profile.namespace)
        )
    snapshot = harness.store.studio_snapshot(active_profile.namespace)
    proposal = snapshot.proposals[0]
    harness.controller.decide_proposal(
        session=first_session,
        proposal=proposal,
        choice=ApprovalChoice.APPROVE,
        idempotency_key="p8-upgrade-effect-approval",
        expected_proposal_revision=proposal.revision,
        expected_payload_digest=proposal.payload_digest,
        expected_proposal_digest=proposal.proposal_digest,
        expected_mandate_id=proposal.mandate_id or "missing",
        expected_mandate_revision=proposal.mandate_revision or 1,
        expected_policy_id=proposal.policy_id,
        expected_policy_revision=proposal.policy_revision,
    )
    harness.controller.process_once(harness.controller.service_context(active_profile.namespace))
    health = harness.store.healthcheck()
    harness.store.close()
    if health.get("migration_count") != 7 or not event_correlation:
        raise ComposeRuntimeError("P7 fixture state was invalid")
    os.chmod(database, 0o600)
    _write_private_json(
        private_metadata,
        {
            "schema_version": 1,
            "source_version": "0.0.0",
            "source_commit": BASE_COMMIT,
            "migration_count": 7,
            COLLEAGUE_FIELD: colleague_id,
            "event_correlation": event_correlation,
            "session_credential": first_credential,
            "csrf_token": first.csrf_token,
        },
    )


def _host_operations(
    source: Path,
    environment: dict[str, str],
    arguments: list[str],
) -> dict[str, Any]:
    operation_environment = environment.copy()
    operation_environment["PYTHONPATH"] = str(source / "src")
    completed = _run(
        [sys.executable, "-B", "-m", "digital_colleagues.operations", *arguments],
        root=source,
        environment=operation_environment,
    )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ComposeRuntimeError("host operation returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise ComposeRuntimeError("host operation returned invalid JSON")
    return value


def _first_release_transition(
    *,
    docker: str,
    project: str,
    repository: Path,
    source: Path,
    temporary: Path,
    operator: Path,
    environment: dict[str, str],
    api_port: int,
    origin: str,
) -> dict[str, object]:
    transition_project = project + "-upgrade"
    p7_source = temporary / "accepted-p7-source"
    p7_database = operator / "accepted-p7-state.sqlite"
    private_metadata = operator / "accepted-p7-private.json"
    p7_binding = operator / "accepted-p7-source-binding.json"
    pre_upgrade = operator / "p7-pre-upgrade.tar.gz"
    p8_rollback = operator / "p8-transition-rollback.tar.gz"
    rollback_container = ""
    cleanup: dict[str, object] = {"passed": False}
    phase = "source_extraction"
    try:
        _extract_accepted_p7(repository, p7_source)
        binding = _host_operations(source, environment, ["accepted-p7-source-binding"])
        _write_private_json(p7_binding, binding)
        phase = "p7_fixture"
        fixture_environment = environment.copy()
        fixture_environment.update(
            {
                "PYTHONPATH": os.pathsep.join((str(p7_source / "src"), str(p7_source))),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        _run(
            [
                sys.executable,
                "-B",
                str(source / "scripts/check_p8_compose_runtime.py"),
                "--create-p7-fixture",
                "--p7-source",
                str(p7_source),
                "--database",
                str(p7_database),
                "--private-metadata",
                str(private_metadata),
            ],
            root=p7_source,
            environment=fixture_environment,
        )
        metadata = _private_json(private_metadata)
        if (
            set(metadata)
            != {
                "schema_version",
                "source_version",
                "source_commit",
                "migration_count",
                COLLEAGUE_FIELD,
                "event_correlation",
                "session_credential",
                "csrf_token",
            }
            or metadata.get("schema_version") != 1
            or metadata.get("source_version") != "0.0.0"
            or metadata.get("source_commit") != BASE_COMMIT
            or metadata.get("migration_count") != 7
            or any(
                not isinstance(metadata.get(key), str) or not metadata[key]
                for key in (
                    COLLEAGUE_FIELD,
                    "event_correlation",
                    "session_credential",
                    "csrf_token",
                )
            )
        ):
            raise ComposeRuntimeError("accepted P7 fixture binding was invalid")
        phase = "pre_upgrade_backup"
        backup_result = _host_operations(
            source,
            environment,
            [
                "backup",
                "--database",
                str(p7_database),
                "--backup",
                str(pre_upgrade),
                "--source-binding",
                str(p7_binding),
                "--migrations",
                str(p7_source / "migrations"),
            ],
        )
        verified = _host_operations(
            source,
            environment,
            [
                "verify-backup",
                "--backup",
                str(pre_upgrade),
                "--source-binding",
                str(p7_binding),
                "--migrations",
                str(p7_source / "migrations"),
            ],
        )
        if (
            backup_result.get("status") != "created"
            or verified.get("status") != "verified"
            or verified.get("source_version") != "0.0.0"
            or verified.get("source_commit") != BASE_COMMIT
        ):
            raise ComposeRuntimeError("accepted P7 pre-upgrade backup did not verify")
        p7_database.unlink()
        phase = "pre_start_restore"
        install_stdout, install_stderr = _operations_command(
            docker,
            transition_project,
            source,
            environment,
            [
                "restore",
                "--backup",
                "/operator/p7-pre-upgrade.tar.gz",
                "--database",
                "/state/state.sqlite",
                "--backup-source-binding",
                "/operator/accepted-p7-source-binding.json",
                "--migrations",
                "/app/migrations",
            ],
            running=False,
        )
        installed = _operation_json(install_stdout, install_stderr)
        if (
            installed.get("status") != "restored"
            or installed.get("restored_source_version") != "0.0.0"
            or installed.get("restored_source_commit") != BASE_COMMIT
        ):
            raise ComposeRuntimeError("P7 state was not installed before P8 startup")

        phase = "p8_start"
        _compose(
            docker,
            transition_project,
            ["up", "--build", "--detach", "api", "worker", "studio"],
            root=source,
            environment=environment,
        )
        api = f"http://127.0.0.1:{api_port}"
        opener = urllib.request.build_opener()
        health = _wait_json(opener, api + "/health")
        toolchain = _wait_json(opener, origin + "/build-toolchain.json")
        if health.get("status") != "ok" or toolchain != {
            "schema_version": 1,
            "node": NODE_VERSION,
            "npm": NPM_VERSION,
        }:
            raise ComposeRuntimeError("P8 first startup or container toolchain was invalid")
        cookie_header = "dc_session=" + cast(str, metadata["session_credential"])
        session = _request(opener, api + "/auth/session", headers={"Cookie": cookie_header})
        csrf = session.get("csrf_token")
        if not isinstance(csrf, str) or not csrf:
            raise ComposeRuntimeError("accepted P7 session did not survive P8 startup")
        headers = {"Cookie": cookie_header, "Origin": origin, "X-CSRF-Token": csrf}
        phase = "p8_state_validation"
        before_studio = _request(opener, api + "/studio/state", headers={"Cookie": cookie_header})
        before_p5 = _request(opener, api + "/p5/studio/state", headers={"Cookie": cookie_header})
        before_governance = _request(
            opener, api + "/governance/state", headers={"Cookie": cookie_header}
        )
        before_audit = _request(
            opener,
            api + "/audit/" + cast(str, metadata["event_correlation"]),
            headers={"Cookie": cookie_header},
        )
        wake_classes = {
            wake.get("trigger_class")
            for wake in before_studio.get("wakes", [])
            if isinstance(wake, dict)
        }
        if (
            not isinstance(before_p5.get("active"), dict)
            or not isinstance(before_governance.get("membership"), dict)
            or not before_governance.get("change_decisions")
            or not {"event", "timer"}.issubset(wake_classes)
            or not before_studio.get("proposals")
            or not before_studio.get("approvals")
            or not before_studio.get("results")
            or not before_audit.get("records")
        ):
            raise ComposeRuntimeError("P7 durable governance state did not survive upgrade")
        responsibility_id = before_studio["identity"]["mandate"]["responsibilities"][0][
            "responsibility_id"
        ]
        phase = "p8_mutation"
        _request(
            opener,
            api + "/work",
            method="POST",
            headers=headers,
            payload={
                "title": "P8 transition mutation",
                "description": "Must disappear when rolling back to the P7 backup.",
                "responsibility_id": responsibility_id,
                "idempotency_key": "p8-first-release-transition-mutation",
            },
        )
        if (
            _request(opener, api + "/studio/state", headers={"Cookie": cookie_header})
            == before_studio
        ):
            raise ComposeRuntimeError("P8 transition mutation was not observed")
        phase = "p8_stop_and_restore"
        _compose(
            docker,
            transition_project,
            ["stop", "api", "worker", "studio"],
            root=source,
            environment=environment,
        )
        restore_stdout, restore_stderr = _operations_command(
            docker,
            transition_project,
            source,
            environment,
            [
                "restore",
                "--backup",
                "/operator/p7-pre-upgrade.tar.gz",
                "--database",
                "/state/state.sqlite",
                "--backup-source-binding",
                "/operator/accepted-p7-source-binding.json",
                "--current-source-binding",
                "/operator/release-manifest.json",
                "--migrations",
                "/app/migrations",
                "--replace",
                "--offline-confirmed",
                "--rollback-backup",
                "/operator/p8-transition-rollback.tar.gz",
            ],
            running=False,
        )
        restored = _operation_json(restore_stdout, restore_stderr)
        rollback_stdout, rollback_stderr = _operations_command(
            docker,
            transition_project,
            source,
            environment,
            [
                "verify-backup",
                "--backup",
                "/operator/p8-transition-rollback.tar.gz",
                "--source-binding",
                "/operator/release-manifest.json",
                "--migrations",
                "/app/migrations",
            ],
            running=False,
        )
        if (
            restored.get("restored_source_version") != "0.0.0"
            or restored.get("replaced_source_version") != "0.1.0"
            or _operation_json(rollback_stdout, rollback_stderr).get("source_version") != "0.1.0"
        ):
            raise ComposeRuntimeError("cross-version rollback binding was invalid")

        phase = "p7_matching_runtime"
        rollback_port = _port()
        version = _compose(
            docker,
            transition_project,
            [
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "--volume",
                f"{p7_source}:/p7:ro",
                "--env",
                "PYTHONPATH=/p7/src",
                "api",
                "python",
                "-B",
                "-c",
                "import digital_colleagues; print(digital_colleagues.__version__)",
            ],
            root=source,
            environment=environment,
        ).stdout.strip()
        if version != "0.0.0":
            raise ComposeRuntimeError("matching accepted P7 code was not selected")
        launched = _compose(
            docker,
            transition_project,
            [
                "run",
                "--rm",
                "--no-deps",
                "--detach",
                "--publish",
                f"127.0.0.1:{rollback_port}:8000",
                "--volume",
                f"{p7_source}:/p7:ro",
                "--env",
                "PYTHONPATH=/p7/src",
                "api",
                "python",
                "-B",
                "-m",
                "uvicorn",
                "digital_colleagues.local.asgi:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
                "--no-access-log",
            ],
            root=source,
            environment=environment,
        )
        rollback_container = launched.stdout.strip()
        if not rollback_container:
            raise ComposeRuntimeError("matching accepted P7 runtime did not start")
        rollback_api = f"http://127.0.0.1:{rollback_port}"
        _wait_json(opener, rollback_api + "/health")
        phase = "rollback_state_validation"
        after_studio = _request(
            opener,
            rollback_api + "/studio/state",
            headers={"Cookie": cookie_header},
        )
        after_p5 = _request(
            opener,
            rollback_api + "/p5/studio/state",
            headers={"Cookie": cookie_header},
        )
        after_governance = _request(
            opener,
            rollback_api + "/governance/state",
            headers={"Cookie": cookie_header},
        )
        after_audit = _request(
            opener,
            rollback_api + "/audit/" + cast(str, metadata["event_correlation"]),
            headers={"Cookie": cookie_header},
        )
        if after_studio != before_studio or after_p5 != before_p5 or after_audit != before_audit:
            raise ComposeRuntimeError("matching P7 rollback state drifted")
        if {key: value for key, value in after_governance.items() if key != "generated_at"} != {
            key: value for key, value in before_governance.items() if key != "generated_at"
        }:
            raise ComposeRuntimeError("matching P7 rollback governance drifted")
        phase = "private_boundary_scan"
        forbidden = tuple(cast(str, metadata[key]) for key in ("session_credential", "csrf_token"))
        _scan_bytes((pre_upgrade, p8_rollback), forbidden)
        transition_logs = _compose(
            docker,
            transition_project,
            ["logs", "--no-color", "api", "worker", "studio"],
            root=source,
            environment=environment,
        )
        if any(value in transition_logs.stdout + transition_logs.stderr for value in forbidden):
            raise ComposeRuntimeError("P7 transition credential entered service logs")
        return {
            "schema_version": 1,
            "status": "passed",
            "source_class": "accepted_p7_git_object",
            "source_commit": BASE_COMMIT,
            "source_tree": "4ebfc2bdfcd97e34256ec7a34ff58b0063c05ed7",
            "source_version": "0.0.0",
            "source_release_manifest": "not_available_before_first_release",
            "target_version": "0.1.0",
            "pre_upgrade_backup": "created_and_verified_before_p8_service_start",
            "schema_migrations": list(range(1, 8)),
            "durable_governance_state": "preserved",
            "p8_mutation": "observed",
            "rollback_backup": "p8_source_bound_and_verified",
            "rollback_runtime": "exact_accepted_p7_git_object",
            "rollback_state_equal": True,
        }
    except ComposeRuntimeError as exc:
        raise ComposeRuntimeError(f"P7 to P8 transition failed at {phase}") from exc
    finally:
        if rollback_container:
            _run(
                [docker, "container", "rm", "--force", rollback_container],
                root=source,
                environment=environment,
                check=False,
            )
        cleanup = _cleanup(
            docker,
            transition_project,
            root=source,
            environment=environment,
        )
        for path in (p7_database, private_metadata, p7_binding, pre_upgrade, p8_rollback):
            path.unlink(missing_ok=True)
        if p7_source.exists():
            shutil.rmtree(p7_source)
        if not cleanup.get("passed"):
            raise ComposeRuntimeError("P7 to P8 transition cleanup failed")


def _exact_approval(
    opener: urllib.request.OpenerDirector,
    api: str,
    headers: dict[str, str],
    proposal: dict[str, Any],
) -> None:
    _request(
        opener,
        api + f"/proposals/{proposal['proposal_id']}/decision",
        method="POST",
        headers=headers,
        payload={
            "proposal_revision": proposal["revision"],
            "proposal_payload_digest": proposal["payload_digest"],
            "proposal_digest": proposal["proposal_digest"],
            "mandate_id": proposal["mandate_id"],
            "mandate_revision": proposal["mandate_revision"],
            "policy_id": proposal["policy_id"],
            "policy_revision": proposal["policy_revision"],
            "choice": "approve",
            "idempotency_key": "p8-exact-effect-approval",
        },
    )


def check_compose_runtime(root: Path) -> dict[str, object]:
    docker = shutil.which("docker")
    if docker is None:
        raise ComposeRuntimeError("Docker CLI unavailable; P8 runtime is not_evaluated")
    started_at = _now()
    project = f"dc-p8-runtime-{os.getpid()}-{secrets.token_hex(4)}"
    result: dict[str, object] | None = None
    cleanup: dict[str, object] = {"passed": False}
    private_cleanup = {
        "backup_files_remaining": 1,
        "credential_files_remaining": 1,
        "diagnostic_bundles_remaining": 1,
        "extracted_release_trees_remaining": 1,
        "build_workspaces_remaining": 1,
    }
    with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-compose-") as name:
        temporary = Path(name)
        candidate = temporary / "candidate"
        extracted = temporary / "extracted"
        operator = temporary / "operator-private"
        operator.mkdir(mode=0o700)
        environment = os.environ.copy()
        api_port = _port()
        studio_port = _port()
        while studio_port == api_port:
            studio_port = _port()
        origin = f"http://127.0.0.1:{studio_port}"
        environment.update(
            {
                "DC_API_PORT": str(api_port),
                "DC_STUDIO_PORT": str(studio_port),
                "DC_EXPECTED_ORIGIN": origin,
                "DC_P8_OPERATOR_DIR": str(operator),
                "COMPOSE_FILE": "compose.yaml:compose.p8.override.yaml",
            }
        )
        canaries = (
            "credential-" + secrets.token_hex(24),
            "private-payload-" + secrets.token_hex(24),
            str(temporary / ("local-" + secrets.token_hex(12))),
        )
        secret_values: list[str] = list(canaries)
        operation_output: list[str] = []
        source: Path | None = None
        try:
            server = _run(
                [docker, "version", "--format", "{{.Server.Version}}"],
                root=root,
                environment=environment,
            ).stdout.strip()
            compose_version = _run(
                [docker, "compose", "version", "--short"],
                root=root,
                environment=environment,
            ).stdout.strip()
            if not server or not compose_version:
                raise ComposeRuntimeError("Docker Engine or Compose version unavailable")
            candidate_result = build_candidate(root, candidate, python=Path(sys.executable))
            source_archive = candidate / ARTIFACT_NAMES[0]
            source = _extract_source(source_archive, extracted)
            _write_override(source / "compose.p8.override.yaml", canaries)
            release_manifest = operator / "release-manifest.json"
            shutil.copyfile(candidate / ARTIFACT_NAMES[4], release_manifest)
            os.chmod(release_manifest, 0o600)

            first_release_transition = _first_release_transition(
                docker=docker,
                project=project,
                repository=root,
                source=source,
                temporary=temporary,
                operator=operator,
                environment=environment,
                api_port=api_port,
                origin=origin,
            )

            _compose(
                docker,
                project,
                ["up", "--build", "--detach", "api", "worker", "studio"],
                root=source,
                environment=environment,
            )
            api = f"http://127.0.0.1:{api_port}"
            first_jar = http.cookiejar.CookieJar()
            first = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(first_jar))
            _wait_json(first, api + "/health")
            _wait_studio(origin)
            initial_ids = _container_ids(docker, project, root=source, environment=environment)
            _compose(docker, project, ["build", "operator"], root=source, environment=environment)

            bootstrap_token = _operator(docker, project, source, environment, "bootstrap-token")
            secret_values.append(bootstrap_token)
            first_session = _request(
                first,
                api + "/auth/bootstrap/exchange",
                method="POST",
                headers={"Origin": origin},
                payload={"token": bootstrap_token},
            )
            first_csrf = first_session.get("csrf_token")
            if not isinstance(first_csrf, str):
                raise ComposeRuntimeError("bootstrap exchange lacked CSRF binding")
            first_cookie = next(
                (cookie.value for cookie in first_jar if cookie.name == "dc_session"), ""
            )
            if not first_cookie:
                raise ComposeRuntimeError("bootstrap exchange lacked session cookie")
            secret_values.extend((first_csrf, first_cookie))
            first_headers = {"Origin": origin, "X-CSRF-Token": first_csrf}
            colleague = _request(
                first,
                api + "/colleagues",
                method="POST",
                headers=first_headers,
                payload={
                    "display_name": "P8 Runtime Atlas",
                    "role_description": "Synthetic release operations colleague",
                    "service_relationship": "Serves the isolated local operator",
                    "mission": "Exercise deterministic backup and restore",
                    "timezone": "UTC",
                    "working_context": "Synthetic P8 candidate state",
                    "working_hours": "display-only initial text",
                    "working_style": "Direct and inspectable",
                    "responsibilities": ["Own finite synthetic release work"],
                    "capabilities": ["Propose a reference message"],
                    "constraints": ["No external provider"],
                    "effect_kind": "reference_message",
                    "destination_kind": "reference_channel",
                    "action": "record_message",
                    "effect_constraints": {"network": False},
                    "idempotency_key": "p8-compose-colleague",
                },
            )
            namespace = cast(dict[str, Any], colleague["namespace"])
            colleague_id = cast(str, namespace["scope_id"])
            refreshed = _request(first, api + "/auth/session")
            first_csrf = cast(str, refreshed["csrf_token"])
            first_headers = {"Origin": origin, "X-CSRF-Token": first_csrf}
            secret_values.append(first_csrf)

            permit = _request(
                first,
                api + "/governance/enrollments/admins",
                method="POST",
                headers=first_headers,
                payload={"idempotency_key": "p8-second-admin"},
            )
            second_token = _operator(
                docker,
                project,
                source,
                environment,
                "enrollment-token",
                _credential_id(permit),
            )
            secret_values.append(second_token)
            second_jar = http.cookiejar.CookieJar()
            second = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(second_jar))
            second_session = _request(
                second,
                api + "/auth/enrollment/exchange",
                method="POST",
                headers={"Origin": origin},
                payload={"token": second_token},
            )
            second_csrf = cast(str, second_session["csrf_token"])
            second_cookie = next(
                (cookie.value for cookie in second_jar if cookie.name == "dc_session"), ""
            )
            if not second_cookie:
                raise ComposeRuntimeError("second Admin exchange lacked session cookie")
            secret_values.extend((second_csrf, second_cookie))
            second_headers = {"Origin": origin, "X-CSRF-Token": second_csrf}
            _request(
                second,
                api + "/governance/session/active-colleague",
                method="POST",
                headers=second_headers,
                payload={COLLEAGUE_FIELD: colleague_id, "idempotency_key": "p8-second-bind"},
            )

            draft = _create_update_review(
                first,
                api,
                first_headers,
                key="p8-policy",
                display_name="P8 Runtime Atlas governed",
                mission="Exercise deterministic governed restore",
                wake_limit=8,
            )
            proposed = cast(
                dict[str, Any],
                _request(
                    first,
                    api + f"/governance/drafts/{draft['draft_id']}/proposals",
                    method="POST",
                    headers=first_headers,
                    payload={
                        "draft_revision": draft["revision"],
                        "canonical_digest": draft["canonical_digest"],
                        "idempotency_key": "p8-change-proposal",
                    },
                )["proposal"],
            )
            decision = cast(
                dict[str, Any],
                _request(
                    second,
                    api + f"/governance/changes/colleague/{proposed['proposal_id']}/decision",
                    method="POST",
                    headers=second_headers,
                    payload={
                        "proposal_revision": proposed["revision"],
                        "proposal_digest": proposed["canonical_digest"],
                        "choice": "approve",
                        "idempotency_key": "p8-change-approval",
                    },
                )["decision"],
            )
            _request(
                first,
                api + f"/governance/changes/colleague/{proposed['proposal_id']}/apply",
                method="POST",
                headers=first_headers,
                payload={
                    "decision_id": decision["decision_id"],
                    "idempotency_key": "p8-change-apply",
                },
            )

            state = _request(first, api + "/studio/state")
            responsibility_id = state["identity"]["mandate"]["responsibilities"][0][
                "responsibility_id"
            ]
            work = cast(
                dict[str, Any],
                _request(
                    first,
                    api + "/work",
                    method="POST",
                    headers=first_headers,
                    payload={
                        "title": "P8 release finite work",
                        "description": "Persist one exact reference result.",
                        "responsibility_id": responsibility_id,
                        "idempotency_key": "p8-compose-work",
                    },
                )["work"],
            )
            for trigger_class, no_op, key in (
                ("timer", True, "p8-compose-timer"),
                ("event", False, "p8-compose-event"),
            ):
                trigger = _request(
                    first,
                    api + "/runtime/triggers",
                    method="POST",
                    headers=first_headers,
                    payload={
                        "work_id": work["work_id"],
                        "trigger_class": trigger_class,
                        "deterministic_noop": no_op,
                        "idempotency_key": key,
                    },
                )
                _request(
                    first,
                    api + "/runtime/process",
                    method="POST",
                    headers=first_headers,
                    payload={"idempotency_key": "process-" + key},
                )
                if trigger_class == "event":
                    event_correlation = cast(str, trigger["correlation_id"])
            state = _request(first, api + "/studio/state")
            proposal = cast(dict[str, Any], state["proposals"][0])
            _exact_approval(first, api, first_headers, proposal)
            _request(
                first,
                api + "/runtime/process",
                method="POST",
                headers=first_headers,
                payload={"idempotency_key": "p8-dispatch"},
            )
            before_studio = _request(first, api + "/studio/state")
            before_p5 = _request(first, api + "/p5/studio/state")
            before_governance = _request(first, api + "/governance/state")
            before_audit = _request(first, api + "/audit/" + event_correlation)
            p5_active = before_p5.get("active")
            wake_classes = {
                wake.get("trigger_class")
                for wake in before_studio.get("wakes", [])
                if isinstance(wake, dict)
            }
            if (
                not isinstance(p5_active, dict)
                or p5_active.get("policy") is None
                or len(before_studio.get("wakes", [])) < 2
                or not {"event", "timer"}.issubset(wake_classes)
                or len(before_studio.get("proposals", [])) < 1
                or len(before_studio.get("approvals", [])) < 1
                or len(before_studio.get("results", [])) < 1
            ):
                raise ComposeRuntimeError("synthetic durable P8 fixture is incomplete")
            required_audit = {
                "input_event",
                "wake_cycle",
                "agenda_item",
                "decision",
                "effect_proposal",
                "human_approval",
                "effect_attempt",
                "action_result",
            }
            if not required_audit.issubset(
                {item["record_type"] for item in before_audit["records"]}
            ):
                raise ComposeRuntimeError("P8 causal audit fixture is incomplete")

            backup = operator / "pre-upgrade.tar.gz"
            stdout, stderr = _operations_command(
                docker,
                project,
                source,
                environment,
                [
                    "backup",
                    "--database",
                    "/state/state.sqlite",
                    "--backup",
                    "/operator/pre-upgrade.tar.gz",
                    "--source-binding",
                    "/operator/release-manifest.json",
                    "--migrations",
                    "/app/migrations",
                ],
                running=True,
            )
            operation_output.extend((stdout, stderr))
            verified_stdout, verified_stderr = _operations_command(
                docker,
                project,
                source,
                environment,
                [
                    "verify-backup",
                    "--backup",
                    "/operator/pre-upgrade.tar.gz",
                    "--source-binding",
                    "/operator/release-manifest.json",
                    "--migrations",
                    "/app/migrations",
                ],
                running=True,
            )
            operation_output.extend((verified_stdout, verified_stderr))
            if (
                _operation_json(stdout, stderr)["status"] != "created"
                or _operation_json(verified_stdout, verified_stderr)["status"] != "verified"
            ):
                raise ComposeRuntimeError("online backup did not verify")

            _request(
                first,
                api + "/work",
                method="POST",
                headers=first_headers,
                payload={
                    "title": "P8 post-backup mutation",
                    "description": "This state must disappear after restore.",
                    "responsibility_id": responsibility_id,
                    "idempotency_key": "p8-post-backup-work",
                },
            )
            changed_state = _request(first, api + "/studio/state")
            if changed_state == before_studio:
                raise ComposeRuntimeError("post-backup state mutation did not occur")

            _compose(
                docker,
                project,
                ["stop", "api", "worker", "studio"],
                root=source,
                environment=environment,
            )
            restore_stdout, restore_stderr = _operations_command(
                docker,
                project,
                source,
                environment,
                [
                    "restore",
                    "--backup",
                    "/operator/pre-upgrade.tar.gz",
                    "--database",
                    "/state/state.sqlite",
                    "--backup-source-binding",
                    "/operator/release-manifest.json",
                    "--current-source-binding",
                    "/operator/release-manifest.json",
                    "--migrations",
                    "/app/migrations",
                    "--replace",
                    "--offline-confirmed",
                    "--rollback-backup",
                    "/operator/pre-restore-rollback.tar.gz",
                ],
                running=False,
            )
            operation_output.extend((restore_stdout, restore_stderr))
            if (
                _operation_json(restore_stdout, restore_stderr).get("rollback_backup_created")
                is not True
            ):
                raise ComposeRuntimeError("restore lacked a verified rollback backup")
            rollback_stdout, rollback_stderr = _operations_command(
                docker,
                project,
                source,
                environment,
                [
                    "verify-backup",
                    "--backup",
                    "/operator/pre-restore-rollback.tar.gz",
                    "--source-binding",
                    "/operator/release-manifest.json",
                    "--migrations",
                    "/app/migrations",
                ],
                running=False,
            )
            operation_output.extend((rollback_stdout, rollback_stderr))
            if _operation_json(rollback_stdout, rollback_stderr).get("status") != "verified":
                raise ComposeRuntimeError("rollback backup did not verify")
            _compose(
                docker,
                project,
                ["up", "--detach", "--force-recreate", "api", "worker", "studio"],
                root=source,
                environment=environment,
            )
            _wait_json(first, api + "/health")
            _wait_studio(origin)
            after_ids = _container_ids(docker, project, root=source, environment=environment)
            after_studio = _request(first, api + "/studio/state")
            after_p5 = _request(first, api + "/p5/studio/state")
            after_governance = _request(first, api + "/governance/state")
            after_audit = _request(first, api + "/audit/" + event_correlation)
            if after_studio != before_studio:
                raise ComposeRuntimeError("restored Studio durable state drifted")
            if after_p5 != before_p5:
                raise ComposeRuntimeError("restored P5 durable state drifted")
            before_governance_durable = {
                key: value for key, value in before_governance.items() if key != "generated_at"
            }
            after_governance_durable = {
                key: value for key, value in after_governance.items() if key != "generated_at"
            }
            if after_governance_durable != before_governance_durable:
                raise ComposeRuntimeError("restored governance durable state drifted")
            if after_audit != before_audit:
                raise ComposeRuntimeError("restored causal audit state drifted")
            if set(initial_ids) & set(after_ids):
                raise ComposeRuntimeError("restored restart reused a service container")

            _request(
                first,
                api + "/work",
                method="POST",
                headers=first_headers,
                payload={
                    "title": "P8 diagnostics canary state",
                    "description": " ".join(canaries),
                    "responsibility_id": responsibility_id,
                    "idempotency_key": "p8-diagnostics-canary-state",
                },
            )

            diagnostics = operator / "support-bundle.tar.gz"
            diagnostic_stdout, diagnostic_stderr = _operations_command(
                docker,
                project,
                source,
                environment,
                [
                    "diagnostics",
                    "--database",
                    "/state/state.sqlite",
                    "--output",
                    "/operator/support-bundle.tar.gz",
                    "--release-manifest",
                    "/operator/release-manifest.json",
                    "--migrations",
                    "/app/migrations",
                    "--causal-id",
                    event_correlation,
                ],
                running=True,
            )
            operation_output.extend((diagnostic_stdout, diagnostic_stderr))
            if _operation_json(diagnostic_stdout, diagnostic_stderr)["status"] != "created":
                raise ComposeRuntimeError("diagnostics bundle was not created")
            rollback = operator / "pre-restore-rollback.tar.gz"
            _scan_bytes(
                (backup, rollback),
                tuple(value for value in secret_values if value != canaries[1]),
            )
            _scan_bytes(
                (diagnostics, *tuple(candidate.iterdir())),
                tuple(secret_values),
            )
            logs = _compose(
                docker,
                project,
                ["logs", "--no-color", "api", "worker", "studio"],
                root=source,
                environment=environment,
            )
            combined = logs.stdout + logs.stderr + "".join(operation_output)
            if any(value and value in combined for value in secret_values):
                raise ComposeRuntimeError("credential or diagnostics canary entered output/logs")

            _compose(
                docker,
                project,
                ["stop", "api", "worker", "studio"],
                root=source,
                environment=environment,
            )
            running_ids = _compose(
                docker,
                project,
                ["ps", "--status", "running", "--quiet"],
                root=source,
                environment=environment,
            ).stdout.split()
            if running_ids:
                raise ComposeRuntimeError("normal P8 stop left a service running")
            result = {
                "schema_version": 1,
                "gate": "p8_compose_runtime_clean",
                "status": "passed",
                "command": "python3 -B scripts/check_p8_compose_runtime.py .",
                "environment": {
                    "docker_server_version": server,
                    "compose_version": compose_version,
                    "host": platform.system().lower(),
                    "published_bind": "127.0.0.1",
                },
                "started_at": started_at,
                "release_source_commit": candidate_result.source_commit,
                "release_artifact_count": len(candidate_result.artifacts),
                "first_release_transition": first_release_transition,
                "studio_build_toolchain": {
                    "host_node": NODE_VERSION,
                    "host_npm": NPM_VERSION,
                    "container_node": NODE_VERSION,
                    "container_npm": NPM_VERSION,
                    "container_build_asserted_and_runtime_metadata_verified": True,
                },
                "default_model": "deterministic",
                "default_channel": "reference",
                "external_provider_calls": 0,
                "health_and_authenticated_smoke": "passed",
                "durable_fixture": {
                    "namespace_identity": True,
                    "profile_mandate_policy_revisions": True,
                    "finite_work": True,
                    "event_timer_wake_agenda": True,
                    "proposal_approval_result": True,
                    "rbac_membership": True,
                    "causal_audit": True,
                },
                "online_backup": "wal_consistent_verified",
                "post_backup_mutation": "observed",
                "restore": "offline_validated_atomic",
                "rollback_backup": "created_and_verified",
                "fresh_restart_state_equal": True,
                "diagnostics_redaction": "canaries_absent",
                "credentials_absent_from_service_logs": True,
                "normal_stop": True,
                "evidence_class": "synthetic_offline",
                "human_evaluation": "not_evaluated",
                "live_provider_evidence": "not_evaluated",
                "five_minute_target": "not_evaluated",
            }
            for path in (backup, rollback, diagnostics, release_manifest):
                path.unlink()
            private_cleanup.update(
                {
                    "backup_files_remaining": len(tuple(operator.glob("*backup*")))
                    + len(tuple(operator.glob("*.tar.gz"))),
                    "credential_files_remaining": 0,
                    "diagnostic_bundles_remaining": len(tuple(operator.glob("*bundle*"))),
                }
            )
        except ReleaseError as exc:
            raise ComposeRuntimeError(str(exc)) from exc
        finally:
            if source is not None:
                cleanup = _cleanup(docker, project, root=source, environment=environment)
            if candidate.exists():
                shutil.rmtree(candidate)
            if extracted.exists():
                shutil.rmtree(extracted)
            private_cleanup["extracted_release_trees_remaining"] = int(extracted.exists())
            private_cleanup["build_workspaces_remaining"] = int(candidate.exists())
        if not cleanup.get("passed"):
            raise ComposeRuntimeError("P8 Compose container/network/volume cleanup failed")
        if any(private_cleanup.values()):
            raise ComposeRuntimeError("P8 private or build cleanup residue remained")
        if result is None:
            raise ComposeRuntimeError("P8 runtime result was not produced")
        result["ended_at"] = _now()
        result["cleanup"] = {**cleanup, **private_cleanup, "passed": True}
    return result


def main(argv: list[str] | None = None) -> int:
    effective_argv = sys.argv[1:] if argv is None else argv
    if effective_argv and effective_argv[0] == "--create-p7-fixture":
        fixture_parser = argparse.ArgumentParser(add_help=False)
        fixture_parser.add_argument("--create-p7-fixture", action="store_true")
        fixture_parser.add_argument("--p7-source", type=Path, required=True)
        fixture_parser.add_argument("--database", type=Path, required=True)
        fixture_parser.add_argument("--private-metadata", type=Path, required=True)
        fixture_arguments = fixture_parser.parse_args(effective_argv)
        try:
            _create_p7_fixture(
                fixture_arguments.p7_source,
                fixture_arguments.database,
                fixture_arguments.private_metadata,
            )
        except (OSError, ComposeRuntimeError, RuntimeError, ValueError):
            print("P7 upgrade fixture creation failed", file=sys.stderr)
            return 2
        return 0
    parser = argparse.ArgumentParser(description="Run actual P8 Compose operations acceptance.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(effective_argv)
    try:
        result = check_compose_runtime(Path(arguments.root).resolve())
    except (OSError, ComposeRuntimeError) as exc:
        safe = (
            str(exc)
            .replace(str(Path(arguments.root).resolve()), "<project>")
            .replace(str(Path.home()), "<home>")
        )
        print(f"P8 Compose runtime check failed: {safe}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
