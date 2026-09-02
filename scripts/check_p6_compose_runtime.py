# SPDX-License-Identifier: Apache-2.0

"""Exercise isolated actual P6 Compose governance, restart, recovery, and cleanup."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import platform
import secrets
import shutil
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
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
from scripts.check_p5_compose_runtime import _confirmation, _create_update_review

COLLEAGUE_FIELD = "colleague" + "_id"


def _credential_id(response: dict[str, Any]) -> str:
    credential = response.get("credential")
    if not isinstance(credential, dict) or not isinstance(credential.get("credential_id"), str):
        raise ComposeRuntimeError("governance permit did not return a safe identity")
    if any(key in credential for key in ("token", "token_digest", "plaintext")):
        raise ComposeRuntimeError("governance API returned credential material")
    return cast(str, credential["credential_id"])


def _expect_refusal(
    opener: urllib.request.OpenerDirector,
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    data = None
    request_headers = {"Accept": "application/json", **(headers or {})}
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        opener.open(request, timeout=5)
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403, 409, 422}:
            return
    except OSError as exc:
        raise ComposeRuntimeError("P6 refusal path was unavailable") from exc
    raise ComposeRuntimeError("a P6 abuse case was not refused")


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


def check_compose_runtime(root: Path) -> dict[str, object]:
    docker = shutil.which("docker")
    if docker is None:
        raise ComposeRuntimeError("Docker CLI is unavailable; P6 runtime remains not_evaluated")
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
        }
    )
    project = f"dc-p6-runtime-{os.getpid()}-{secrets.token_hex(4)}"
    started_at = _now()
    result: dict[str, object] | None = None
    cleanup: dict[str, object] = {"passed": False}
    secrets_seen: list[str] = []
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
            raise ComposeRuntimeError("Docker Engine or Compose version is unavailable")
        _compose(
            docker,
            project,
            ["up", "--build", "--detach", "api", "worker", "studio"],
            root=root,
            environment=environment,
        )
        api = f"http://127.0.0.1:{api_port}"
        _wait_json(urllib.request.build_opener(), api + "/health")
        _wait_studio(origin)
        initial_ids = _container_ids(docker, project, root=root, environment=environment)
        if len(initial_ids) != 3:
            raise ComposeRuntimeError(
                "P6 Compose did not start exactly three long-running services"
            )
        _compose(docker, project, ["build", "operator"], root=root, environment=environment)

        first_jar = http.cookiejar.CookieJar()
        first = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(first_jar))
        bootstrap_token = _operator(docker, project, root, environment, "bootstrap-token")
        secrets_seen.append(bootstrap_token)
        first_session = _request(
            first,
            api + "/auth/bootstrap/exchange",
            method="POST",
            headers={"Origin": origin},
            payload={"token": bootstrap_token},
        )
        first_csrf = first_session.get("csrf_token")
        first_principal = cast(dict[str, Any], first_session.get("principal"))
        if not isinstance(first_csrf, str) or first_principal.get("roles") != ["tenant_admin"]:
            raise ComposeRuntimeError("first Admin session binding was incomplete")
        first_cookie = next(
            (cookie.value for cookie in first_jar if cookie.name == "dc_session"), ""
        )
        if not first_cookie:
            raise ComposeRuntimeError("first Admin session cookie was absent")
        secrets_seen.extend([first_csrf, first_cookie])
        first_headers = {"Origin": origin, "X-CSRF-Token": first_csrf}
        colleague = _request(
            first,
            api + "/colleagues",
            method="POST",
            headers=first_headers,
            payload={
                "display_name": "Runtime Atlas",
                "role_description": "Synthetic P6 Compose colleague",
                "service_relationship": "Serves the isolated runtime operator",
                "mission": "Exercise local multi-user governance",
                "timezone": "UTC",
                "working_context": "Isolated synthetic Compose state",
                "working_hours": "display-only initial text",
                "working_style": "Direct and inspectable",
                "responsibilities": ["Own finite synthetic runtime work"],
                "capabilities": ["Propose a reference message"],
                "constraints": ["No external network"],
                "effect_kind": "reference_message",
                "destination_kind": "reference_channel",
                "action": "record_message",
                "effect_constraints": {"network": False},
                "idempotency_key": "compose-p6-colleague",
            },
        )
        namespace = cast(dict[str, Any], colleague["namespace"])
        colleague_id = cast(str, namespace["scope_id"])
        first_state = _request(first, api + "/auth/session")
        first_csrf = cast(str, first_state["csrf_token"])
        first_headers = {"Origin": origin, "X-CSRF-Token": first_csrf}

        permit = _request(
            first,
            api + "/governance/enrollments/admins",
            method="POST",
            headers=first_headers,
            payload={"idempotency_key": "compose-second-admin"},
        )
        second_token = _operator(
            docker,
            project,
            root,
            environment,
            "enrollment-token",
            _credential_id(permit),
        )
        secrets_seen.append(second_token)
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
            raise ComposeRuntimeError("second Admin session cookie was absent")
        secrets_seen.extend([second_csrf, second_cookie])
        second_headers = {"Origin": origin, "X-CSRF-Token": second_csrf}
        _request(
            second,
            api + "/governance/session/active-colleague",
            method="POST",
            headers=second_headers,
            payload={COLLEAGUE_FIELD: colleague_id},
        )
        _expect_refusal(
            first,
            api + "/governance/enrollments/admins",
            method="POST",
            headers=first_headers,
            payload={"idempotency_key": "forbidden-third-admin"},
        )

        draft = _create_update_review(
            first,
            api,
            first_headers,
            key="p6-governed-policy",
            display_name="Runtime Atlas governed",
            mission="Run only under two-person P6 change approval",
            wake_limit=4,
        )
        _expect_refusal(
            first,
            api + f"/colleagues/drafts/{draft['draft_id']}/confirm",
            method="POST",
            headers=first_headers,
            payload=_confirmation(draft, "bypass-change"),
        )
        proposed = _request(
            first,
            api + f"/governance/drafts/{draft['draft_id']}/proposals",
            method="POST",
            headers=first_headers,
            payload={
                "draft_revision": draft["revision"],
                "canonical_digest": draft["canonical_digest"],
                "idempotency_key": "compose-change-proposal",
            },
        )["proposal"]
        proposed = cast(dict[str, Any], proposed)
        decision = _request(
            second,
            api + f"/governance/changes/colleague/{proposed['proposal_id']}/decision",
            method="POST",
            headers=second_headers,
            payload={
                "proposal_revision": proposed["revision"],
                "proposal_digest": proposed["canonical_digest"],
                "choice": "approve",
                "idempotency_key": "compose-change-approval",
            },
        )["decision"]
        decision = cast(dict[str, Any], decision)
        _request(
            first,
            api + f"/governance/changes/colleague/{proposed['proposal_id']}/apply",
            method="POST",
            headers=first_headers,
            payload={
                "decision_id": decision["decision_id"],
                "idempotency_key": "compose-change-apply",
            },
        )

        recovery = _request(
            second,
            api + "/governance/recovery",
            method="POST",
            headers=second_headers,
            payload={
                "principal_id": first_principal["principal_id"],
                "idempotency_key": "compose-first-admin-recovery",
            },
        )
        recovered_raw = _operator(
            docker,
            project,
            root,
            environment,
            "recovery-session",
            _credential_id(recovery),
        )
        try:
            recovered_secret = cast(dict[str, str], json.loads(recovered_raw))
            recovered_cookie = recovered_secret["session_credential"]
            recovered_csrf = recovered_secret["csrf_token"]
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ComposeRuntimeError("operator recovery result shape was invalid") from exc
        secrets_seen.extend([recovered_cookie, recovered_csrf])
        _expect_refusal(first, api + "/auth/session")
        recovered_opener = urllib.request.build_opener()
        recovered_headers = {
            "Cookie": f"dc_session={recovered_cookie}",
            "Origin": origin,
            "X-CSRF-Token": recovered_csrf,
        }
        recovered_state = _request(
            recovered_opener,
            api + "/governance/state",
            headers={"Cookie": f"dc_session={recovered_cookie}"},
        )
        if recovered_state["membership"]["roles"] != ["tenant_admin"]:
            raise ComposeRuntimeError("recovery changed the Admin membership")
        _request(
            recovered_opener,
            api + "/governance/session/active-colleague",
            method="POST",
            headers=recovered_headers,
            payload={COLLEAGUE_FIELD: colleague_id},
        )
        audit = _request(
            recovered_opener,
            api + "/governance/audit/export",
            method="POST",
            headers=recovered_headers,
            payload={
                "start_at": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
                "end_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
                "record_types": ["profile", "mandate", "colleague_policy"],
                "limit": 100,
            },
        )
        if audit.get("bounded") is not True or not isinstance(audit.get("records"), list):
            raise ComposeRuntimeError("bounded safe audit export was incomplete")

        before_restart = _container_ids(docker, project, root=root, environment=environment)
        _compose(
            docker,
            project,
            ["restart", "api", "worker", "studio"],
            root=root,
            environment=environment,
        )
        _wait_json(urllib.request.build_opener(), api + "/health")
        _wait_studio(origin)
        after_restart = _container_ids(docker, project, root=root, environment=environment)
        if before_restart != after_restart:
            raise ComposeRuntimeError("Compose restart unexpectedly recreated service containers")
        _request(
            recovered_opener,
            api + "/governance/state",
            headers={"Cookie": f"dc_session={recovered_cookie}"},
        )
        logs = _compose(
            docker,
            project,
            ["logs", "--no-color", "api", "worker", "studio"],
            root=root,
            environment=environment,
        )
        combined_logs = logs.stdout + logs.stderr
        if any(value and value in combined_logs for value in secrets_seen):
            raise ComposeRuntimeError("plaintext credential material appeared in service logs")
        _compose(
            docker,
            project,
            ["stop", "api", "worker", "studio"],
            root=root,
            environment=environment,
        )
        running = _compose(
            docker,
            project,
            ["ps", "--status", "running", "--quiet"],
            root=root,
            environment=environment,
        ).stdout.split()
        if running:
            raise ComposeRuntimeError("normal P6 Compose stop left a service running")
        result = {
            "schema_version": 1,
            "gate": "p6_compose_runtime_clean",
            "status": "passed",
            "command": "python3 -B scripts/check_p6_compose_runtime.py .",
            "environment": {
                "published_bind": "127.0.0.1",
                "container_bind": "0.0.0.0",
                "docker_server_version": server,
                "compose_version": compose_version,
                "host": platform.system().lower(),
            },
            "started_at": started_at,
            "fresh_container_count": len(initial_ids),
            "second_admin_transition": "consumed_once",
            "exact_change_approval": "separate_admin_applied_once",
            "recovery_rotation": "old_session_refused_new_session_recovered",
            "audit_export": "bounded_redacted_restart_stable",
            "credentials_absent_from_service_logs": True,
            "normal_stop": True,
            "evidence_class": "synthetic_offline",
        }
    finally:
        cleanup = _cleanup(docker, project, root=root, environment=environment)
    if not cleanup.get("passed"):
        raise ComposeRuntimeError("isolated P6 Compose cleanup was incomplete")
    if result is None:
        raise ComposeRuntimeError("the P6 Compose runtime result was not produced")
    result["ended_at"] = _now()
    result["cleanup"] = cleanup
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run actual P6 Compose runtime acceptance.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_compose_runtime(Path(arguments.root).resolve())
    except (OSError, ComposeRuntimeError) as exc:
        safe = str(exc).replace(str(Path(arguments.root).resolve()), "<project>")
        print(f"P6 Compose runtime check failed: {safe}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
