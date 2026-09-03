# SPDX-License-Identifier: Apache-2.0

"""Run actual P7 no-egress adapter Compose plus retained P6 runtime acceptance."""

from __future__ import annotations

import argparse
import json
import os
import platform
import secrets
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p4_compose_runtime import (  # noqa: E402
    ComposeRuntimeError,
    _cleanup,
    _compose,
    _now,
    _run,
)
from scripts.check_p6_compose_runtime import check_compose_runtime as check_p6_runtime  # noqa: E402


def check_compose_runtime(root: Path) -> dict[str, object]:
    docker = shutil.which("docker")
    if docker is None:
        raise ComposeRuntimeError("Docker CLI is unavailable; P7 runtime remains not_evaluated")
    environment = os.environ.copy()
    project = f"dc-p7-runtime-{os.getpid()}-{secrets.token_hex(4)}"
    started_at = _now()
    cleanup: dict[str, object] = {"passed": False}
    container_result: dict[str, Any] | None = None
    credential_path: Path | None = None
    credential_value = secrets.token_bytes(32)
    retained = check_p6_runtime(root)
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
            credential_path = Path(temporary) / "credential"
            credential_path.write_bytes(credential_value)
            credential_path.chmod(0o444)
            environment["DC_P7_CREDENTIAL_FILE"] = os.fspath(credential_path)
            files = [
                "-f",
                os.fspath(root / "compose.yaml"),
                "-f",
                os.fspath(root / "compose.p7.yaml"),
                "--profile",
                "optional-adapters",
            ]
            _compose(
                docker,
                project,
                [*files, "build", "p7-adapter-gate"],
                root=root,
                environment=environment,
            )
            completed = _compose(
                docker,
                project,
                [*files, "run", "--rm", "--no-deps", "-T", "p7-adapter-gate"],
                root=root,
                environment=environment,
            )
            combined = completed.stdout.encode() + completed.stderr.encode()
            if credential_value in combined:
                raise ComposeRuntimeError("P7 credential appeared in container output")
            try:
                parsed: Any = json.loads(completed.stdout)
            except json.JSONDecodeError:
                raise ComposeRuntimeError("P7 container result was not JSON") from None
            if not isinstance(parsed, dict):
                raise ComposeRuntimeError("P7 container result was not an object")
            container_result = parsed
            unittest_result = parsed.get("unittest")
            if (
                parsed.get("status") != "passed"
                or parsed.get("gate") != "p7_container_runtime_clean"
                or parsed.get("default_routes") != 0
                or parsed.get("unexpected_external_egress") != 0
                or parsed.get("stub_processes_remaining") != 0
                or not isinstance(unittest_result, dict)
                or unittest_result.get("gate_passed") is not True
                or any(
                    unittest_result.get(key) != 0
                    for key in (
                        "failures",
                        "errors",
                        "skipped",
                        "expected_failures",
                        "unexpected_successes",
                    )
                )
            ):
                raise ComposeRuntimeError("P7 container Gate was incomplete")
        if credential_path.exists():
            raise ComposeRuntimeError("temporary P7 credential file remained after runtime")
    finally:
        cleanup = _cleanup(docker, project, root=root, environment=environment)
    if not cleanup.get("passed"):
        raise ComposeRuntimeError("isolated P7 Compose cleanup was incomplete")
    if container_result is None:
        raise ComposeRuntimeError("P7 container result was not produced")
    retained_cleanup = retained.get("cleanup")
    if not isinstance(retained_cleanup, dict) or retained_cleanup.get("passed") is not True:
        raise ComposeRuntimeError("retained P6 Compose runtime cleanup was incomplete")
    cleanup.update(
        {
            "credential_files_remaining": 0,
            "stub_processes_remaining": 0,
        }
    )
    return {
        "schema_version": 1,
        "gate": "p7_compose_runtime_clean",
        "status": "passed",
        "command": "python3 -B scripts/check_p7_compose_runtime.py .",
        "environment": {
            "container_network": "none_with_process_local_loopback",
            "docker_server_version": server,
            "compose_version": compose_version,
            "host": platform.system().lower(),
        },
        "started_at": started_at,
        "ended_at": _now(),
        "default_path": "deterministic_reference",
        "adapter_protocol": "dc-http-json-v1",
        "adapter_container": container_result,
        "retained_p6_runtime": {
            "gate": retained.get("gate"),
            "status": retained.get("status"),
            "exact_change_approval": retained.get("exact_change_approval"),
            "recovery_rotation": retained.get("recovery_rotation"),
            "cleanup": retained_cleanup,
        },
        "startup": "explicit_optional_profile",
        "success_and_refusal_paths": "passed",
        "timeout_disconnect": "ambiguous_no_blind_resend",
        "restart_replay": "durable_still_unknown",
        "exact_effect_approval": "retained_and_exercised",
        "credentials_absent_from_output": True,
        "unexpected_external_egress": 0,
        "normal_stop": True,
        "cleanup": cleanup,
        "evidence_class": "synthetic_offline",
        "live_provider_evidence": "not_evaluated",
    }


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
