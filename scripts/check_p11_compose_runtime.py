# SPDX-License-Identifier: Apache-2.0

"""Exercise actual P11 package/deployment state, restart, enforcement, and cleanup."""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.cookiejar
import io
import json
import os
import platform
import secrets
import shutil
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p4_compose_runtime import (  # noqa: E402
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
from scripts.check_p6_compose_runtime import _expect_refusal, _operator  # noqa: E402


def _digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _package_archive() -> tuple[bytes, str]:
    content: dict[str, object] = {
        "prompts": {
            "en-US": "Perform one finite synthetic Compose operation.",
            "zh-TW": "執行一個有限的合成 Compose 操作。",
        },
        "requested_capabilities": ["notify_human"],
        "workflow": {"entrypoint": "done", "steps": [{"id": "done", "type": "complete"}]},
    }
    canonical_content = json.dumps(
        content, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    package = {
        "schema": "dc-agent/v1",
        "schema_version": 1,
        "metadata": {
            "package_id": "compose-agent",
            "version": "1.0.0",
            "runtime_api": "1",
            "display": {
                "en-US": {"name": "Compose Agent", "summary": "Synthetic runtime package."},
                "zh-TW": {"name": "Compose Agent", "summary": "合成 runtime 套件。"},
            },
        },
        "content": content,
        "content_digest": _digest(canonical_content),
    }
    encoded = json.dumps(
        package, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("agent.json", encoded)
    return output.getvalue(), _digest(encoded)


def _exact_package_path(record: dict[str, Any], action: str) -> str:
    package = cast(dict[str, Any], record["package"])
    metadata = cast(dict[str, Any], package["metadata"])
    return (
        f"/api/v1/agent-packages/{metadata['package_id']}/versions/"
        f"{metadata['version']}/{record['package_digest']}/{action}"
    )


def _read_list(opener: urllib.request.OpenerDirector, url: str) -> list[dict[str, Any]]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with opener.open(request, timeout=5) as response:
            value = json.loads(response.read())
    except (OSError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        raise ComposeRuntimeError("the P11 list response was unavailable") from exc
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ComposeRuntimeError("the P11 list response shape was invalid")
    return cast(list[dict[str, Any]], value)


def check_compose_runtime(root: Path) -> dict[str, object]:
    docker = shutil.which("docker")
    if docker is None:
        raise ComposeRuntimeError("Docker CLI is unavailable; P11 runtime remains not_evaluated")
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
    project = f"dc-p11-runtime-{os.getpid()}-{secrets.token_hex(4)}"
    result: dict[str, object] | None = None
    cleanup: dict[str, object] = {"passed": False}
    secrets_seen: list[str] = []
    started_at = _now()
    try:
        server = _run(
            [docker, "version", "--format", "{{.Server.Version}}"],
            root=root,
            environment=environment,
        ).stdout.strip()
        compose_version = _run(
            [docker, "compose", "version", "--short"], root=root, environment=environment
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
            raise ComposeRuntimeError("P11 Compose did not start exactly three runtime services")
        _compose(docker, project, ["build", "operator"], root=root, environment=environment)

        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        bootstrap = _operator(docker, project, root, environment, "bootstrap-token")
        secrets_seen.append(bootstrap)
        grant = _request(
            opener,
            api + "/auth/bootstrap/exchange",
            method="POST",
            headers={"Origin": origin},
            payload={"token": bootstrap},
        )
        csrf = cast(str, grant["csrf_token"])
        cookie = next((item.value for item in jar if item.name == "dc_session"), "")
        if not csrf or not cookie:
            raise ComposeRuntimeError("P11 Admin session binding was incomplete")
        secrets_seen.extend((csrf, cookie))
        headers = {"Origin": origin, "X-CSRF-Token": csrf}

        archive, package_digest = _package_archive()
        archive_digest = _digest(archive)
        archive_base64 = base64.b64encode(archive).decode("ascii")
        inspection = _request(
            opener,
            api + "/api/v1/agent-packages/validate",
            method="POST",
            payload={
                "archive_base64": archive_base64,
                "expected_archive_digest": archive_digest,
            },
        )
        if inspection.get("package_digest") != package_digest:
            raise ComposeRuntimeError("P11 Compose package canonical binding differed")
        package = _request(
            opener,
            api + "/api/v1/agent-packages",
            method="POST",
            headers=headers,
            payload={
                "archive_base64": archive_base64,
                "expected_archive_digest": archive_digest,
                "source": "local",
                "idempotency_key": "compose-register",
            },
        )
        if (
            package.get("trust_state") != "untrusted"
            or package.get("install_state") != "not_installed"
        ):
            raise ComposeRuntimeError("registration did not remain inert and untrusted")
        package = _request(
            opener,
            api + _exact_package_path(package, "trust"),
            method="POST",
            headers=headers,
            payload={"expected_revision": 1, "idempotency_key": "compose-trust"},
        )
        package = _request(
            opener,
            api + _exact_package_path(package, "install"),
            method="POST",
            headers=headers,
            payload={"expected_revision": 2, "idempotency_key": "compose-install"},
        )
        if package.get("install_state") != "installed":
            raise ComposeRuntimeError("P11 inert installation did not persist")

        draft = _request(
            opener,
            api + "/api/v1/deployment-drafts",
            method="POST",
            headers=headers,
            payload={
                "deployment_id": "compose-agent-one",
                "package_id": "compose-agent",
                "package_version": "1.0.0",
                "package_digest": package_digest,
                "display_name": "Compose Agent",
                "description": "Synthetic actual Compose deployment.",
                "mission": "Exercise finite local P11 lifecycle state.",
                "service_relationship": "Serves the isolated runtime Admin.",
                "granted_capabilities": ["notify_human"],
                "timezone": "UTC",
                "idempotency_key": "compose-create-draft",
            },
        )
        confirmation = {
            "deployment_id": "compose-agent-one",
            "expected_revision": 1,
            "expected_canonical_digest": draft["canonical_digest"],
            "idempotency_key": "compose-review",
        }
        draft = _request(
            opener,
            api + f"/api/v1/deployment-drafts/{draft['draft_id']}/review",
            method="POST",
            headers=headers,
            payload=confirmation,
        )
        confirmation.update({"expected_revision": 2, "idempotency_key": "compose-confirm"})
        deployment = _request(
            opener,
            api + f"/api/v1/deployment-drafts/{draft['draft_id']}/confirm",
            method="POST",
            headers=headers,
            payload=confirmation,
        )
        if deployment.get("lifecycle") != "draft":
            raise ComposeRuntimeError("confirmation incorrectly activated the deployment")
        activation = _request(
            opener,
            api + "/api/v1/deployments/compose-agent-one/lifecycle",
            method="POST",
            headers=headers,
            payload={
                "target": "active",
                "expected_revision": 1,
                "expected_package_digest": package_digest,
                "idempotency_key": "compose-activate",
            },
        )
        if activation.get("accepted") is not True or activation.get("active_count") != 1:
            raise ComposeRuntimeError("P11 activation result was incomplete")
        selected = _request(
            opener,
            api + "/api/v1/deployments/compose-agent-one/select",
            method="POST",
            headers=headers,
            payload={"idempotency_key": "compose-select"},
        )
        if selected.get("selected") is not True:
            raise ComposeRuntimeError("P11 exact deployment selection failed")
        work = _request(
            opener,
            api + "/work",
            method="POST",
            headers=headers,
            payload={
                "title": "P11 active-bound work",
                "description": "Synthetic work used only for lifecycle enforcement.",
                "responsibility_id": "package-work",
                "idempotency_key": "compose-work",
            },
        )["work"]
        _request(
            opener,
            api + "/api/v1/deployments/compose-agent-one/lifecycle",
            method="POST",
            headers=headers,
            payload={
                "target": "paused",
                "expected_revision": 2,
                "expected_package_digest": package_digest,
                "idempotency_key": "compose-pause",
            },
        )
        _expect_refusal(
            opener,
            api + "/runtime/triggers",
            method="POST",
            headers=headers,
            payload={
                "work_id": work["work_id"],
                "trigger_class": "event",
                "deterministic_noop": True,
                "idempotency_key": "compose-paused-trigger",
            },
        )

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
        if before_restart != _container_ids(docker, project, root=root, environment=environment):
            raise ComposeRuntimeError("P11 restart unexpectedly recreated containers")
        registry = _read_list(opener, api + "/api/v1/deployments")
        if len(registry) != 1 or registry[0].get("lifecycle") != "paused":
            raise ComposeRuntimeError("P11 registry lifecycle was not restart-durable")
        audit = _read_list(opener, api + "/api/v1/deployments/compose-agent-one/audit")
        if not any(row.get("action") == "lifecycle" for row in audit):
            raise ComposeRuntimeError("P11 causal lifecycle audit was incomplete")

        logs = _compose(
            docker,
            project,
            ["logs", "--no-color", "api", "worker", "studio"],
            root=root,
            environment=environment,
        )
        if any(secret and secret in logs.stdout + logs.stderr for secret in secrets_seen):
            raise ComposeRuntimeError("plaintext credential material appeared in P11 logs")
        _compose(
            docker,
            project,
            ["stop", "api", "worker", "studio"],
            root=root,
            environment=environment,
        )
        if _compose(
            docker,
            project,
            ["ps", "--status", "running", "--quiet"],
            root=root,
            environment=environment,
        ).stdout.split():
            raise ComposeRuntimeError("normal P11 Compose stop left a service running")
        result = {
            "schema_version": 1,
            "gate": "p11_compose_runtime",
            "status": "passed",
            "source_compose": True,
            "environment": {
                "docker_server_version": server,
                "compose_version": compose_version,
                "host": platform.system().lower(),
                "published_bind": "127.0.0.1",
            },
            "fresh_container_count": len(initial_ids),
            "migration_008_exercised": True,
            "package_flow": "validate_register_trust_install",
            "deployment_flow": "draft_review_confirm_activate_select_pause",
            "authenticated_runtime_persistence": True,
            "paused_runtime_refusal": True,
            "restart": "passed",
            "credential_log_leak_count": 0,
            "evidence_class": "local_runtime",
            "started_at": started_at,
        }
    finally:
        cleanup = _cleanup(docker, project, root=root, environment=environment)
    if not cleanup.get("passed"):
        raise ComposeRuntimeError("isolated P11 Compose cleanup was incomplete")
    if result is None:
        raise ComposeRuntimeError("the P11 Compose runtime result was not produced")
    result["ended_at"] = _now()
    result["cleanup"] = cleanup
    result["cleanup_residue_count"] = 0
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run actual P11 Compose runtime acceptance.")
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        result = check_compose_runtime(Path(args.root).resolve())
    except (OSError, ComposeRuntimeError) as exc:
        safe = str(exc).replace(str(Path(args.root).resolve()), "<project>")
        print(f"P11 Compose runtime check failed: {safe}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
