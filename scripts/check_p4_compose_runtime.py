# SPDX-License-Identifier: Apache-2.0

"""Exercise the isolated P4 Compose start/recreate/recovery/stop acceptance path."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import platform
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ComposeRuntimeError(RuntimeError):
    """The actual Compose runtime acceptance path failed safely."""


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _run(
    command: list[str],
    *,
    root: Path,
    environment: dict[str, str],
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and completed.returncode != 0:
        raise ComposeRuntimeError("a container-runtime command failed")
    return completed


def _compose(
    docker: str,
    project: str,
    arguments: list[str],
    *,
    root: Path,
    environment: dict[str, str],
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return _run(
        [docker, "compose", "--project-name", project, *arguments],
        root=root,
        environment=environment,
        check=check,
    )


def _request(
    opener: urllib.request.OpenerDirector,
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    data = None
    request_headers = {"Accept": "application/json", **(headers or {})}
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        url,
        data=data,
        headers=request_headers,
        method=method,
    )
    try:
        with opener.open(request, timeout=5) as response:
            value = json.loads(response.read())
    except (OSError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        raise ComposeRuntimeError("the synthetic HTTP workflow was refused") from exc
    if not isinstance(value, dict):
        raise ComposeRuntimeError("the synthetic HTTP response was not an object")
    return value


def _wait_json(
    opener: urllib.request.OpenerDirector,
    url: str,
    *,
    predicate: Any | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = _request(opener, url)
            if predicate is None or predicate(value):
                return value
        except ComposeRuntimeError:
            pass
        time.sleep(0.5)
    raise ComposeRuntimeError("a synthetic runtime checkpoint timed out")


def _wait_studio(url: str, *, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:  # noqa: S310
                if response.status == 200 and response.read(256):
                    return
        except OSError:
            pass
        time.sleep(0.5)
    raise ComposeRuntimeError("Studio did not become reachable")


def _container_ids(
    docker: str,
    project: str,
    *,
    root: Path,
    environment: dict[str, str],
) -> tuple[str, ...]:
    output = _compose(
        docker,
        project,
        ["ps", "--quiet", "api", "worker", "studio"],
        root=root,
        environment=environment,
    ).stdout
    values = tuple(sorted(line.strip() for line in output.splitlines() if line.strip()))
    if len(values) != 3:
        raise ComposeRuntimeError("the expected long-running containers are not present")
    return values


def _cleanup(
    docker: str,
    project: str,
    *,
    root: Path,
    environment: dict[str, str],
) -> dict[str, object]:
    down = _compose(
        docker,
        project,
        ["down", "--volumes", "--remove-orphans", "--timeout", "10"],
        root=root,
        environment=environment,
        check=False,
    )
    containers = _run(
        [
            docker,
            "ps",
            "--all",
            "--quiet",
            "--filter",
            f"label=com.docker.compose.project={project}",
        ],
        root=root,
        environment=environment,
        check=False,
    ).stdout.split()
    networks = _run(
        [
            docker,
            "network",
            "ls",
            "--quiet",
            "--filter",
            f"label=com.docker.compose.project={project}",
        ],
        root=root,
        environment=environment,
        check=False,
    ).stdout.split()
    volumes = _run(
        [
            docker,
            "volume",
            "ls",
            "--quiet",
            "--filter",
            f"label=com.docker.compose.project={project}",
        ],
        root=root,
        environment=environment,
        check=False,
    ).stdout.split()
    return {
        "down_exit_code": down.returncode,
        "containers_remaining": len(containers),
        "networks_remaining": len(networks),
        "volumes_remaining": len(volumes),
        "passed": down.returncode == 0 and not containers and not networks and not volumes,
    }


def check_compose_runtime(root: Path) -> dict[str, object]:
    docker = shutil.which("docker")
    if docker is None:
        raise ComposeRuntimeError("Docker CLI is unavailable; runtime remains not_evaluated")
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
    project = f"dc-p4-runtime-{os.getpid()}-{secrets.token_hex(4)}"
    started_at = _now()
    cleanup: dict[str, object] = {"passed": False}
    normal_stop = False
    result: dict[str, object] | None = None
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
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
        api = f"http://127.0.0.1:{api_port}"
        _wait_json(opener, api + "/health")
        _wait_studio(origin)
        first_ids = _container_ids(docker, project, root=root, environment=environment)

        _compose(
            docker,
            project,
            ["build", "operator"],
            root=root,
            environment=environment,
        )
        operator = _compose(
            docker,
            project,
            ["run", "--rm", "--no-deps", "-T", "operator"],
            root=root,
            environment=environment,
        )
        token = operator.stdout.strip()
        if "\n" in token or len(token) < 32:
            raise ComposeRuntimeError("operator bootstrap retrieval returned an invalid shape")
        exchanged = _request(
            opener,
            api + "/auth/bootstrap/exchange",
            method="POST",
            payload={"token": token},
            headers={"Origin": origin},
        )
        csrf = exchanged.get("csrf_token")
        if not isinstance(csrf, str) or len(csrf) < 32:
            raise ComposeRuntimeError("bootstrap exchange did not return a CSRF binding")
        session_credentials = [cookie.value for cookie in cookie_jar if cookie.name == "dc_session"]
        if len(session_credentials) != 1:
            raise ComposeRuntimeError("bootstrap exchange did not create one session cookie")
        session_credential = session_credentials[0]
        if not isinstance(session_credential, str):
            raise ComposeRuntimeError("session cookie value was invalid")
        mutation_headers = {"Origin": origin, "X-CSRF-Token": csrf}
        colleague = _request(
            opener,
            api + "/colleagues",
            method="POST",
            headers=mutation_headers,
            payload={
                "display_name": "Runtime Atlas",
                "role_description": "Synthetic Compose acceptance colleague",
                "service_relationship": "Serves the isolated runtime operator",
                "mission": "Complete one finite deterministic reference task",
                "timezone": "UTC",
                "working_context": "Isolated synthetic Compose state",
                "working_hours": "09:00-17:00; initial data only",
                "working_style": "Direct and inspectable",
                "responsibilities": ["Own finite synthetic runtime work"],
                "capabilities": ["Propose a reference message"],
                "constraints": ["No external network"],
                "effect_kind": "reference_message",
                "destination_kind": "reference_channel",
                "action": "record_message",
                "effect_constraints": {"network": False},
                "idempotency_key": "compose-initial-colleague",
            },
        )
        before = _request(opener, api + "/studio/state")
        responsibility_id = before["identity"]["mandate"]["responsibilities"][0][
            "responsibility_id"
        ]
        work_response = _request(
            opener,
            api + "/work",
            method="POST",
            headers=mutation_headers,
            payload={
                "title": "Compose restart work",
                "description": "Verify durable recovery and exact-effect completion.",
                "responsibility_id": responsibility_id,
                "idempotency_key": "compose-work",
            },
        )
        work = work_response["work"]
        before = _request(opener, api + "/studio/state")
        before_audit = _request(opener, api + "/audit/" + work["correlation_id"])

        _compose(
            docker,
            project,
            ["stop", "api", "worker", "studio"],
            root=root,
            environment=environment,
        )
        _compose(
            docker,
            project,
            ["up", "--detach", "--force-recreate", "api", "worker", "studio"],
            root=root,
            environment=environment,
        )
        _wait_json(opener, api + "/health")
        _wait_studio(origin)
        second_ids = _container_ids(docker, project, root=root, environment=environment)
        if set(first_ids) & set(second_ids):
            raise ComposeRuntimeError("restart checkpoint did not create fresh containers")
        recovered_session = _request(opener, api + "/auth/session")
        csrf = recovered_session.get("csrf_token")
        if not isinstance(csrf, str):
            raise ComposeRuntimeError("recovered session lost its CSRF binding")
        mutation_headers = {"Origin": origin, "X-CSRF-Token": csrf}
        recovered = _request(opener, api + "/studio/state")
        recovered_audit = _request(opener, api + "/audit/" + work["correlation_id"])
        if (
            recovered["identity"] != before["identity"]
            or recovered["work"] != before["work"]
            or recovered_audit != before_audit
            or recovered.get("state") != "ready"
        ):
            raise ComposeRuntimeError("durable identity, Mandate, work, or history did not recover")

        trigger = _request(
            opener,
            api + "/runtime/triggers",
            method="POST",
            headers=mutation_headers,
            payload={
                "work_id": work["work_id"],
                "trigger_class": "event",
                "deterministic_noop": False,
                "idempotency_key": "compose-trigger",
            },
        )
        state = _wait_json(
            opener,
            api + "/studio/state",
            predicate=lambda value: bool(value.get("proposals")),
        )
        proposal = state["proposals"][0]
        _request(
            opener,
            api + f"/proposals/{proposal['proposal_id']}/decision",
            method="POST",
            headers=mutation_headers,
            payload={
                "proposal_revision": proposal["revision"],
                "proposal_payload_digest": proposal["payload_digest"],
                "proposal_digest": proposal["proposal_digest"],
                "mandate_id": proposal["mandate_id"],
                "mandate_revision": proposal["mandate_revision"],
                "choice": "approve",
                "idempotency_key": "compose-approval",
            },
        )
        finished = _wait_json(
            opener,
            api + "/studio/state",
            predicate=lambda value: bool(value.get("results")),
        )
        audit = _request(opener, api + "/audit/" + trigger["correlation_id"])
        record_types = {item["record_type"] for item in audit["records"]}
        required = {
            "input_event",
            "wake_cycle",
            "agenda_item",
            "decision",
            "effect_proposal",
            "human_approval",
            "effect_attempt",
            "action_result",
        }
        if not required.issubset(record_types) or not finished["results"]:
            raise ComposeRuntimeError(
                "the exact approval, ActionResult, or causal chain is incomplete"
            )
        attempts_before_rejection = len(finished["attempts"])
        results_before_rejection = len(finished["results"])
        rejection_trigger = _request(
            opener,
            api + "/runtime/triggers",
            method="POST",
            headers=mutation_headers,
            payload={
                "work_id": work["work_id"],
                "trigger_class": "event",
                "deterministic_noop": False,
                "idempotency_key": "compose-rejection-trigger",
            },
        )
        rejection_state = _wait_json(
            opener,
            api + "/studio/state",
            predicate=lambda value: len(value.get("proposals", [])) >= 2,
        )
        rejection_proposal = next(
            item
            for item in rejection_state["proposals"]
            if item["proposal_id"] != proposal["proposal_id"]
        )
        _request(
            opener,
            api + f"/proposals/{rejection_proposal['proposal_id']}/decision",
            method="POST",
            headers=mutation_headers,
            payload={
                "proposal_revision": rejection_proposal["revision"],
                "proposal_payload_digest": rejection_proposal["payload_digest"],
                "proposal_digest": rejection_proposal["proposal_digest"],
                "mandate_id": rejection_proposal["mandate_id"],
                "mandate_revision": rejection_proposal["mandate_revision"],
                "choice": "reject",
                "idempotency_key": "compose-rejection",
            },
        )
        rejected_state = _wait_json(
            opener,
            api + "/studio/state",
            predicate=lambda value: len(value.get("approvals", [])) >= 2,
        )
        rejection_audit = _request(opener, api + "/audit/" + rejection_trigger["correlation_id"])
        rejection_types = {item["record_type"] for item in rejection_audit["records"]}
        if (
            len(rejected_state["attempts"]) != attempts_before_rejection
            or len(rejected_state["results"]) != results_before_rejection
            or "human_approval" not in rejection_types
            or "effect_attempt" in rejection_types
            or "action_result" in rejection_types
        ):
            raise ComposeRuntimeError("exact rejection created or dispatched an effect")
        metrics = _request(opener, api + "/evaluation/metrics")
        if metrics.get("gate_status") != "passed":
            raise ComposeRuntimeError("the operational metric escape gate failed")
        logs = _compose(
            docker,
            project,
            ["logs", "--no-color", "api", "worker", "studio"],
            root=root,
            environment=environment,
        )
        combined_logs = logs.stdout + logs.stderr
        if any(secret in combined_logs for secret in (token, session_credential, csrf)):
            raise ComposeRuntimeError("a plaintext credential appeared in persistent service logs")

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
        normal_stop = not running
        if not normal_stop:
            raise ComposeRuntimeError("normal Compose stop left a service running")
        result = {
            "schema_version": 1,
            "gate": "p4_compose_runtime_clean",
            "status": "passed",
            "runtime_start_restart_stop": "passed",
            "command": "python3 -B scripts/check_p4_compose_runtime.py .",
            "compose_actions": [
                "up --build --detach api worker studio",
                "build operator",
                "run --rm --no-deps -T operator",
                "stop api worker studio",
                "up --detach --force-recreate api worker studio",
                "stop api worker studio",
                "down --volumes --remove-orphans",
            ],
            "compose_project": project,
            "environment": {
                "api_host_port": api_port,
                "docker_server_version": server,
                "compose_version": compose_version,
                "host": platform.system().lower(),
                "python": platform.python_version(),
                "published_bind": "127.0.0.1",
                "studio_host_port": studio_port,
            },
            "started_at": started_at,
            "restart_checkpoint": "after_finite_work_before_trigger",
            "fresh_containers_after_checkpoint": True,
            "durable_recovery": {
                "identity": True,
                "mandate": colleague["mandate_id"]
                == recovered["identity"]["mandate"]["mandate_id"],
                "work": work["work_id"] == recovered["work"][0]["work_id"],
                "runtime_state": True,
                "causal_history": recovered_audit == before_audit,
            },
            "exact_approval_rejection_control": {
                "exact_approval": True,
                "exact_rejection": True,
                "action_result": True,
                "causal_audit": True,
            },
            "credentials_absent_from_service_logs": True,
            "state_volume": "isolated_project_scoped_temporary_volume",
            "metric_observations": {item["metric"]: item for item in metrics["metrics"]},
            "normal_stop": normal_stop,
            "synthetic_only": True,
            "five_minute_objective": "not_evaluated",
        }
    finally:
        cleanup = _cleanup(docker, project, root=root, environment=environment)
    if not cleanup.get("passed"):
        raise ComposeRuntimeError("isolated Compose cleanup was incomplete")
    if result is None:
        raise ComposeRuntimeError("the runtime result was not produced")
    result["ended_at"] = _now()
    result["cleanup"] = cleanup
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run actual P4 Compose runtime acceptance.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_compose_runtime(Path(arguments.root).resolve())
    except (OSError, ComposeRuntimeError) as exc:
        print(f"P4 Compose runtime check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
