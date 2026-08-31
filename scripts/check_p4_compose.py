# SPDX-License-Identifier: Apache-2.0

"""Validate P4 Compose topology without claiming unavailable runtime evidence."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


class ComposeError(RuntimeError):
    """The Compose topology violates the local P4 contract."""


def _runtime_config(root: Path) -> tuple[str, str | None]:
    docker = shutil.which("docker")
    if docker is None:
        return "not_evaluated_no_container_engine", None
    completed = subprocess.run(
        [docker, "compose", "-f", str(root / "compose.yaml"), "config", "--quiet"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ComposeError("installed Compose rejected the topology")
    return "config_validated", "docker compose"


def check_compose(root: Path) -> dict[str, object]:
    compose = (root / "compose.yaml").read_text(encoding="utf-8")
    required = (
        "api:",
        "worker:",
        "studio:",
        "operator:",
        "state:/state",
        "volumes:\n  state:",
        "127.0.0.1:8000:8000",
        "127.0.0.1:4173:8080",
        "--host",
        "0.0.0.0",
        "healthcheck:",
        "profiles:",
        "- operator",
    )
    if any(item not in compose for item in required):
        raise ComposeError("required service, state, bind, health, or operator topology is missing")
    if "privileged: true" in compose or "/var/run/docker.sock" in compose:
        raise ComposeError("Compose grants an unsafe container capability")
    if any(item in compose.lower() for item in ("api_key", "provider_token", "password:")):
        raise ComposeError("Compose embeds a credential-like configuration")
    runtime_status, command = _runtime_config(root)
    return {
        "schema_version": 1,
        "gate": "p4_compose_clean",
        "services": ["api", "worker", "studio", "operator"],
        "host_bind": "127.0.0.1",
        "container_api_bind": "0.0.0.0",
        "container_studio_bind": "0.0.0.0",
        "durable_database": "single_state.sqlite_on_project_named_state_volume",
        "runtime_config_status": runtime_status,
        "runtime_command": command,
        "runtime_start_restart_stop": "not_evaluated"
        if command is None
        else "not_run_by_config_gate",
        "loopback_claim": "reduced_host_exposure_only",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the P4 Compose topology.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_compose(Path(arguments.root).resolve())
    except (OSError, ComposeError) as exc:
        print(f"P4 Compose check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
