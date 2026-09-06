# SPDX-License-Identifier: Apache-2.0

"""Run the actual optional-adapter service topology and retained P6 runtime gate."""

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

from scripts.check_p4_compose_runtime import (  # noqa: E402
    ComposeRuntimeError,
    _cleanup,
    _compose,
    _now,
    _port,
    _request,
    _run,
    _wait_json,
    _wait_studio,
)
from scripts.check_p6_compose_runtime import check_compose_runtime as check_p6_runtime  # noqa: E402

RUNTIME_SERVICES = ("p7-stub", "p7-api", "p7-worker", "p7-studio")
SERVICES = (*RUNTIME_SERVICES, "p7-egress-guard", "p7-ingress")


def _default_route_count(route_table: str) -> int:
    routes = 0
    for line in route_table.splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 8 and fields[1] == "00000000" and fields[7] == "00000000":
            routes += 1
    return routes


def _service_route_report(
    docker: str,
    project: str,
    files: list[str],
    *,
    root: Path,
    environment: dict[str, str],
) -> dict[str, dict[str, object]]:
    report: dict[str, dict[str, object]] = {}
    for service in SERVICES:
        route = _compose(
            docker,
            project,
            [*files, "exec", "-T", service, "cat", "/proc/net/route"],
            root=root,
            environment=environment,
        ).stdout
        default_routes = _default_route_count(route)
        if default_routes:
            raise ComposeRuntimeError(f"{service} has an external default route")
        container_id = _ids(
            docker,
            project,
            files,
            root=root,
            environment=environment,
            services=(service,),
        )[0]
        inspection = _run(
            [
                docker,
                "inspect",
                "--format",
                "{{json .NetworkSettings.Networks}}",
                container_id,
            ],
            root=root,
            environment=environment,
        ).stdout
        try:
            attachments = json.loads(inspection)
        except json.JSONDecodeError:
            raise ComposeRuntimeError("P7 container network inspection was invalid") from None
        if not isinstance(attachments, dict):
            raise ComposeRuntimeError("P7 container network attachments were invalid")
        non_internal: list[str] = []
        attachment_labels: list[str] = []
        for network_name in attachments:
            network_label = next(
                (
                    label
                    for label in ("p7-isolated", "p7-published")
                    if str(network_name).endswith("_" + label)
                ),
                None,
            )
            if network_label is None:
                raise ComposeRuntimeError("P7 container has an unexpected network attachment")
            attachment_labels.append(network_label)
            internal = _run(
                [
                    docker,
                    "network",
                    "inspect",
                    "--format",
                    "{{json .Internal}}",
                    str(network_name),
                ],
                root=root,
                environment=environment,
            ).stdout.strip()
            if internal != "true":
                non_internal.append(network_label)
        if non_internal and service != "p7-egress-guard":
            raise ComposeRuntimeError(f"{service} attached to a non-internal network")
        report[service] = {
            "default_routes": default_routes,
            "network_attachments": sorted(attachment_labels),
            "non_internal_attachments": sorted(non_internal),
            "route_status": "no_external_default_route",
        }
    if not report["p7-stub"]["network_attachments"]:
        raise ComposeRuntimeError("P7 isolated runtime network attachment was not observable")
    guard_external = report["p7-egress-guard"]["non_internal_attachments"]
    if not isinstance(guard_external, list) or len(guard_external) != 1:
        raise ComposeRuntimeError("P7 publisher route guard attachment is incomplete")
    guard_status = _compose(
        docker,
        project,
        [*files, "exec", "-T", "p7-egress-guard", "cat", "/proc/1/status"],
        root=root,
        environment=environment,
    ).stdout
    status_fields = {
        line.split(":", 1)[0]: line.split(":", 1)[1].strip()
        for line in guard_status.splitlines()
        if ":" in line
    }
    uid_values = status_fields.get("Uid", "").split()
    if (
        len(uid_values) != 4
        or uid_values[1] != "10001"
        or status_fields.get("CapEff") != "0000000000000000"
    ):
        raise ComposeRuntimeError("P7 publisher guard retained privilege after route removal")
    report["p7-egress-guard"]["runtime_uid"] = 10001
    report["p7-egress-guard"]["effective_capabilities"] = 0
    return report


def _one_shot_route_count(
    docker: str,
    project: str,
    files: list[str],
    *,
    root: Path,
    environment: dict[str, str],
    service: str,
) -> int:
    probe = (
        "from pathlib import Path; lines=Path('/proc/net/route').read_text().splitlines()[1:]; "
        "print(sum(len(f)>=8 and f[1]=='00000000' and f[7]=='00000000' "
        "for f in (line.split() for line in lines)))"
    )
    completed = _compose(
        docker,
        project,
        [*files, "run", "--rm", "--no-deps", "-T", service, "python", "-c", probe],
        root=root,
        environment=environment,
    )
    try:
        return int(completed.stdout.strip())
    except ValueError:
        raise ComposeRuntimeError("P7 one-shot route inspection was invalid") from None


def _ids(
    docker: str,
    project: str,
    files: list[str],
    *,
    root: Path,
    environment: dict[str, str],
    services: tuple[str, ...],
) -> tuple[str, ...]:
    output = _compose(
        docker,
        project,
        [*files, "ps", "--all", "--quiet", *services],
        root=root,
        environment=environment,
    ).stdout
    values = tuple(line.strip() for line in output.splitlines() if line.strip())
    if len(values) != len(services):
        raise ComposeRuntimeError("the optional adapter service topology is incomplete")
    return values


def _enqueue(
    opener: urllib.request.OpenerDirector,
    control: str,
    *behaviors: str,
) -> None:
    result = _request(
        opener,
        control + "/enqueue",
        method="POST",
        payload={"behaviors": list(behaviors)},
    )
    if result.get("enqueued") != len(behaviors):
        raise ComposeRuntimeError("controlled P7 stub refused its finite behavior queue")


def _operator_token(
    docker: str,
    project: str,
    files: list[str],
    *,
    root: Path,
    environment: dict[str, str],
) -> str:
    completed = _compose(
        docker,
        project,
        [*files, "run", "--rm", "-T", "p7-operator"],
        root=root,
        environment=environment,
    )
    token = completed.stdout.strip()
    if "\n" in token or len(token) < 32:
        raise ComposeRuntimeError("P7 operator returned an invalid bootstrap boundary")
    return token


def _state_counts(state: dict[str, Any]) -> tuple[int, int, int]:
    attempts = state.get("attempts")
    results = state.get("results")
    proposals = state.get("proposals")
    if (
        not isinstance(attempts, list)
        or not isinstance(results, list)
        or not isinstance(proposals, list)
    ):
        raise ComposeRuntimeError("P7 Studio state has an invalid runtime shape")
    return len(attempts), len(results), len(proposals)


def check_compose_runtime(root: Path) -> dict[str, object]:
    docker = shutil.which("docker")
    if docker is None:
        raise ComposeRuntimeError("Docker CLI is unavailable; P7 runtime remains not_evaluated")
    retained = check_p6_runtime(root)
    environment = os.environ.copy()
    api_port, studio_port, stub_port = _port(), _port(), _port()
    while len({api_port, studio_port, stub_port}) != 3:
        api_port, studio_port, stub_port = _port(), _port(), _port()
    origin = f"http://127.0.0.1:{studio_port}"
    api = f"http://127.0.0.1:{api_port}"
    control = f"http://127.0.0.1:{stub_port}"
    environment.update(
        {
            "DC_P7_API_PORT": str(api_port),
            "DC_P7_STUDIO_PORT": str(studio_port),
            "DC_P7_STUB_PORT": str(stub_port),
        }
    )
    project = f"dc-p7-runtime-{os.getpid()}-{secrets.token_hex(4)}"
    files = [
        "-f",
        os.fspath(root / "compose.yaml"),
        "-f",
        os.fspath(root / "compose.p7.yaml"),
        "--profile",
        "optional-adapters",
    ]
    started_at = _now()
    cleanup: dict[str, object] = {"passed": False}
    result: dict[str, object] | None = None
    credential_value = "p7-synthetic-credential-" + secrets.token_hex(16)
    private_marker = "p7-private-provider-marker"
    secrets_seen: list[str] = [credential_value, private_marker]
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
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-compose-") as temporary:
            credential = Path(temporary) / "credential"
            credential.write_text(credential_value, encoding="utf-8")
            credential.chmod(0o444)
            environment["DC_P7_CREDENTIAL_FILE"] = os.fspath(credential)
            _compose(
                docker,
                project,
                [*files, "build", "p7-adapter-gate", *SERVICES, "p7-operator"],
                root=root,
                environment=environment,
            )
            gate = _compose(
                docker,
                project,
                [*files, "run", "--rm", "--no-deps", "-T", "p7-adapter-gate"],
                root=root,
                environment=environment,
            )
            if credential_value in gate.stdout + gate.stderr:
                raise ComposeRuntimeError("P7 credential appeared in auxiliary gate output")
            try:
                gate_result: Any = json.loads(gate.stdout)
            except json.JSONDecodeError:
                raise ComposeRuntimeError(
                    "auxiliary P7 container gate returned invalid JSON"
                ) from None
            if not isinstance(gate_result, dict) or gate_result.get("status") != "passed":
                raise ComposeRuntimeError("auxiliary P7 container gate did not pass")

            _compose(
                docker,
                project,
                [*files, "up", "--detach", *SERVICES],
                root=root,
                environment=environment,
            )
            plain = urllib.request.build_opener()
            _wait_json(plain, control + "/health")
            _wait_json(plain, api + "/health")
            _wait_studio(origin)
            initial_ids = _ids(
                docker,
                project,
                files,
                root=root,
                environment=environment,
                services=SERVICES,
            )
            service_routes = _service_route_report(
                docker,
                project,
                files,
                root=root,
                environment=environment,
            )
            operator_default_routes = _one_shot_route_count(
                docker,
                project,
                files,
                root=root,
                environment=environment,
                service="p7-operator",
            )
            if operator_default_routes:
                raise ComposeRuntimeError("p7-operator has an external default route")
            service_routes["p7-operator"] = {
                "default_routes": operator_default_routes,
                "network_attachments": ["shared:p7-stub"],
                "non_internal_attachments": [],
                "route_status": "no_external_default_route",
            }
            service_routes["p7-adapter-gate"] = {
                "default_routes": gate_result.get("default_routes"),
                "network_attachments": [],
                "non_internal_attachments": [],
                "route_status": "network_mode_none",
            }
            _compose(
                docker,
                project,
                [*files, "stop", "p7-worker"],
                root=root,
                environment=environment,
            )

            jar = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
            bootstrap = _operator_token(
                docker,
                project,
                files,
                root=root,
                environment=environment,
            )
            secrets_seen.append(bootstrap)
            session = _request(
                opener,
                api + "/auth/bootstrap/exchange",
                method="POST",
                headers={"Origin": origin},
                payload={"token": bootstrap},
            )
            csrf = session.get("csrf_token")
            if not isinstance(csrf, str) or len(csrf) < 32:
                raise ComposeRuntimeError("P7 bootstrap exchange lost its CSRF binding")
            cookie = next((item.value for item in jar if item.name == "dc_session"), "")
            if not cookie:
                raise ComposeRuntimeError("P7 bootstrap exchange lost its session binding")
            secrets_seen.extend((csrf, cookie))
            headers = {"Origin": origin, "X-CSRF-Token": csrf}
            _request(
                opener,
                api + "/colleagues",
                method="POST",
                headers=headers,
                payload={
                    "display_name": "P7 Runtime Atlas",
                    "role_description": "Synthetic optional adapter colleague",
                    "service_relationship": "Serves the isolated P7 runtime operator",
                    "mission": "Exercise exact optional adapter recovery",
                    "timezone": "UTC",
                    "working_context": "Synthetic isolated P7 state",
                    "working_hours": "09:00-17:00; initial data only",
                    "working_style": "Direct and inspectable",
                    "responsibilities": ["Own finite synthetic adapter work"],
                    "capabilities": ["Propose a reference message"],
                    "constraints": ["No external network"],
                    "effect_kind": "reference_message",
                    "destination_kind": "reference_channel",
                    "action": "record_message",
                    "effect_constraints": {"network": False},
                    "idempotency_key": "p7-compose-colleague",
                },
            )
            state = _request(opener, api + "/studio/state")
            responsibility_id = cast(dict[str, Any], state["identity"])["mandate"][
                "responsibilities"
            ][0]["responsibility_id"]
            work = cast(
                dict[str, Any],
                _request(
                    opener,
                    api + "/work",
                    method="POST",
                    headers=headers,
                    payload={
                        "title": "P7 optional adapter restart work",
                        "description": "Verify durable ambiguity reconciliation.",
                        "responsibility_id": responsibility_id,
                        "idempotency_key": "p7-compose-work",
                    },
                )["work"],
            )
            _enqueue(plain, control, "model_proposal")
            trigger = _request(
                opener,
                api + "/runtime/triggers",
                method="POST",
                headers=headers,
                payload={
                    "work_id": work["work_id"],
                    "trigger_class": "event",
                    "deterministic_noop": False,
                    "idempotency_key": "p7-compose-trigger",
                },
            )
            produced = _request(
                opener,
                api + "/runtime/process",
                method="POST",
                headers=headers,
                payload={"idempotency_key": "p7-compose-model-process"},
            )
            if produced.get("decisions") != 1:
                raise ComposeRuntimeError("optional model did not produce one durable proposal")
            state = _request(opener, api + "/studio/state")
            proposal = cast(list[dict[str, Any]], state["proposals"])[0]
            _enqueue(plain, control, "channel_503")
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
                    "idempotency_key": "p7-compose-approval",
                },
            )
            ambiguous = _request(
                opener,
                api + "/runtime/process",
                method="POST",
                headers=headers,
                payload={"idempotency_key": "p7-compose-dispatch"},
            )
            if ambiguous.get("dispatched") is not True:
                raise ComposeRuntimeError("P7 channel 503 did not finalize an ambiguous attempt")
            state = _request(opener, api + "/studio/state")
            if _state_counts(state) != (1, 1, 1):
                raise ComposeRuntimeError("ambiguous dispatch created an unexpected retry")

            before_recreate = _ids(
                docker,
                project,
                files,
                root=root,
                environment=environment,
                services=("p7-api", "p7-worker"),
            )
            _compose(
                docker,
                project,
                [*files, "stop", "p7-api", "p7-worker"],
                root=root,
                environment=environment,
            )
            _enqueue(plain, control, "still_unknown")
            _compose(
                docker,
                project,
                [*files, "up", "--detach", "--force-recreate", "p7-api", "p7-worker"],
                root=root,
                environment=environment,
            )
            _wait_json(plain, api + "/health")
            after_recreate = _ids(
                docker,
                project,
                files,
                root=root,
                environment=environment,
                services=("p7-api", "p7-worker"),
            )
            if set(before_recreate) & set(after_recreate):
                raise ComposeRuntimeError("P7 API/worker checkpoint did not recreate containers")
            unknown_stub = _wait_json(
                plain,
                control + "/state",
                predicate=lambda value: value.get("counts", {}).get("channel_reconciliation") == 1,
            )
            unknown_requests = unknown_stub.get("requests")
            if not isinstance(unknown_requests, list) or len(unknown_requests) != 3:
                raise ComposeRuntimeError(
                    "restarted worker did not perform exactly one unknown reconciliation"
                )
            state = _request(opener, api + "/studio/state")
            if _state_counts(state) != (1, 1, 1):
                raise ComposeRuntimeError("still-unknown reconciliation resent the effect")

            _enqueue(plain, control, "confirmed_absent", "succeeded")
            final_state = _wait_json(
                opener,
                api + "/studio/state",
                predicate=lambda value: (
                    len(value.get("attempts", [])) == 2
                    and any(item.get("state") == "succeeded" for item in value.get("results", []))
                ),
            )
            attempts, results, proposals = _state_counts(final_state)
            if (attempts, results, proposals) != (2, 3, 1):
                raise ComposeRuntimeError("confirmed absence did not produce one bounded retry")
            stub_state = _request(plain, control + "/state")
            requests = stub_state.get("requests")
            expected_sequence = [
                "semantic_decision",
                "channel_effect",
                "channel_reconciliation",
                "channel_reconciliation",
                "channel_effect",
            ]
            if (
                not isinstance(requests, list)
                or [item.get("request_kind") for item in requests] != expected_sequence
                or stub_state.get("pending_behaviors") != []
            ):
                raise ComposeRuntimeError("P7 stub observed a duplicate or reordered provider call")
            reconciliations = [
                item for item in requests if item.get("request_kind") == "channel_reconciliation"
            ]
            effect_key = next(
                item.get("effect_key")
                for item in requests
                if item.get("request_kind") == "channel_effect"
            )
            if any(
                item.get("effect_key") != effect_key
                or item.get("binding_digest") != proposal["proposal_digest"]
                for item in reconciliations
            ):
                raise ComposeRuntimeError(
                    "restart reconciliation lost the durable exact-effect binding"
                )

            final_service_routes = _service_route_report(
                docker,
                project,
                files,
                root=root,
                environment=environment,
            )
            for service, route_result in final_service_routes.items():
                if route_result != service_routes[service]:
                    raise ComposeRuntimeError(f"{service} route changed during worker recovery")
            logs = _compose(
                docker,
                project,
                [*files, "logs", "--no-color", *SERVICES],
                root=root,
                environment=environment,
            )
            combined_logs = logs.stdout + logs.stderr
            if any(secret and secret in combined_logs for secret in secrets_seen):
                raise ComposeRuntimeError(
                    "credential or private provider material appeared in logs"
                )
            audit = _request(opener, api + "/audit/" + cast(str, trigger["correlation_id"]))
            safe_runtime_output = json.dumps(
                {"audit": audit, "state": final_state, "stub": stub_state},
                separators=(",", ":"),
                sort_keys=True,
            )
            if any(secret and secret in safe_runtime_output for secret in secrets_seen):
                raise ComposeRuntimeError("credential or private material escaped runtime output")
            record_types = {item["record_type"] for item in audit.get("records", [])}
            required = {
                "action_result",
                "agenda_item",
                "decision",
                "effect_attempt",
                "effect_proposal",
                "human_approval",
                "input_event",
                "wake_cycle",
            }
            if not required.issubset(record_types):
                raise ComposeRuntimeError("P7 exact causal chain is incomplete")
            _compose(
                docker,
                project,
                [*files, "stop", *SERVICES],
                root=root,
                environment=environment,
            )
            running = _compose(
                docker,
                project,
                [*files, "ps", "--status", "running", "--quiet"],
                root=root,
                environment=environment,
            ).stdout.split()
            if running:
                raise ComposeRuntimeError("normal P7 Compose stop left a service running")
            if not credential.exists():
                raise ComposeRuntimeError(
                    "temporary credential boundary disappeared before cleanup"
                )
            result = {
                "schema_version": 1,
                "gate": "p7_compose_runtime_clean",
                "status": "passed",
                "command": "python3 -B scripts/check_p7_compose_runtime.py .",
                "environment": {
                    "container_network": "internal_shared_loopback_namespace",
                    "docker_server_version": server,
                    "compose_version": compose_version,
                    "host": platform.system().lower(),
                    "published_bind": "127.0.0.1",
                },
                "started_at": started_at,
                "default_path": "deterministic_reference_retained",
                "optional_topology": list(RUNTIME_SERVICES),
                "loopback_ingress": "host_only_tcp_forwarder",
                "initial_service_count": len(initial_ids),
                "fresh_service_recreate_count": len(after_recreate),
                "provider_request_sequence": expected_sequence,
                "restart_reconciliation": "still_unknown_then_confirmed_absent",
                "recovery_driver": "recreated_headless_worker",
                "runtime_process_calls_after_restart": 0,
                "bounded_effect_attempts": attempts,
                "credentials_absent_from_service_logs": True,
                "unexpected_external_egress": 0,
                "service_routes": service_routes,
                "normal_stop": True,
                "auxiliary_container_gate": gate_result.get("gate"),
                "evidence_class": "synthetic_offline",
                "live_provider_evidence": "not_evaluated",
                "human_acceptance_evidence": "not_evaluated",
            }
        if credential.exists():
            raise ComposeRuntimeError("temporary P7 credential remained after runtime")
    finally:
        cleanup = _cleanup(docker, project, root=root, environment=environment)
    if not cleanup.get("passed"):
        raise ComposeRuntimeError("isolated P7 Compose cleanup was incomplete")
    if result is None:
        raise ComposeRuntimeError("P7 Compose runtime result was not produced")
    retained_cleanup = retained.get("cleanup")
    if not isinstance(retained_cleanup, dict) or retained_cleanup.get("passed") is not True:
        raise ComposeRuntimeError("retained P6 Compose runtime cleanup was incomplete")
    cleanup.update({"credential_files_remaining": 0, "stub_processes_remaining": 0})
    result["retained_p6_runtime"] = {
        "gate": retained.get("gate"),
        "status": retained.get("status"),
        "cleanup": retained_cleanup,
    }
    result["ended_at"] = _now()
    result["cleanup"] = cleanup
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run actual P7 Compose runtime acceptance.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_compose_runtime(Path(arguments.root).resolve())
    except (OSError, ComposeRuntimeError) as exc:
        safe = str(exc).replace(str(Path(arguments.root).resolve()), "<project>")
        print(f"P7 Compose runtime check failed: {safe}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
