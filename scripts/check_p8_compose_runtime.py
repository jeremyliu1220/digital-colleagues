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
    ReleaseError,
    _extract_source,
    build_candidate,
)

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
                    "--release-manifest",
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
                    "--release-manifest",
                    "/operator/release-manifest.json",
                    "--migrations",
                    "/app/migrations",
                ],
                running=True,
            )
            operation_output.extend((verified_stdout, verified_stderr))
            if (
                json.loads(stdout)["status"] != "created"
                or json.loads(verified_stdout)["status"] != "verified"
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
                    "--release-manifest",
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
            if json.loads(restore_stdout).get("rollback_backup_created") is not True:
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
                    "--release-manifest",
                    "/operator/release-manifest.json",
                    "--migrations",
                    "/app/migrations",
                ],
                running=False,
            )
            operation_output.extend((rollback_stdout, rollback_stderr))
            if json.loads(rollback_stdout).get("status") != "verified":
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
            if after_governance != before_governance:
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
            if json.loads(diagnostic_stdout)["status"] != "created":
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
    parser = argparse.ArgumentParser(description="Run actual P8 Compose operations acceptance.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
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
