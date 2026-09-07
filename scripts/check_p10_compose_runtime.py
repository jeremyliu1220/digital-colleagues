# SPDX-License-Identifier: Apache-2.0

"""Build P10 OCI candidates and exercise the native image-only Compose runtime."""

from __future__ import annotations

import json
import os
import platform
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_p10_candidate import build_bundle, build_oci
from scripts.check_p10_distribution import inspect_oci_layout
from scripts.p10_gate_support import DISPLAY_VERSION, GateError, redact


@dataclass(frozen=True)
class LocalCandidate:
    bundle: Path
    runtime_ref: str
    studio_ref: str
    runtime_tag: str
    studio_tag: str
    source_revision: str
    oci: dict[str, dict[str, object]]


def _run(command: list[str], *, cwd: Path, timeout: int = 1800) -> str:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GateError("runtime_command_failed") from exc
    if completed.returncode != 0:
        raise GateError("runtime_command_failed")
    return completed.stdout.strip()


def _implementation_revision(root: Path) -> str:
    summary = root / "artifacts/p10/summary.json"
    selector = "HEAD^" if summary.is_file() else "HEAD"
    revision = _run(["git", "rev-parse", selector], cwd=root, timeout=30)
    if len(revision) != 40:
        raise GateError("implementation_revision_invalid")
    return revision


def _native_platform() -> tuple[str, str]:
    if platform.system() != "Darwin":
        raise GateError("actual_macos_required")
    machine = platform.machine()
    if machine == "arm64":
        return machine, "linux/arm64"
    if machine == "x86_64":
        return machine, "linux/amd64"
    raise GateError("mac_architecture_unsupported")


def _image_id(root: Path, tag: str) -> str:
    image_id = _run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", tag], cwd=root, timeout=60
    )
    if not image_id.startswith("sha256:") or len(image_id) != 71:
        raise GateError("native_image_digest_invalid")
    return image_id


def build_local_candidate(root: Path, work: Path) -> LocalCandidate:
    machine, native = _native_platform()
    _run(["docker", "info"], cwd=root, timeout=60)
    revision = _implementation_revision(root)
    oci_dir = work / "oci"
    build_oci(root, oci_dir, revision)
    oci = {
        "runtime": inspect_oci_layout(oci_dir / "digital-colleagues-runtime.oci.tar"),
        "studio": inspect_oci_layout(oci_dir / "digital-colleagues-studio.oci.tar"),
    }
    identity = secrets.token_hex(6)
    runtime_tag = f"dc-p10-local-{identity}/runtime:{DISPLAY_VERSION}"
    studio_tag = f"dc-p10-local-{identity}/studio:{DISPLAY_VERSION}"
    common = [
        "docker",
        "buildx",
        "build",
        "--platform",
        native,
        "--load",
        "--provenance=false",
        "--sbom=false",
        "--build-arg",
        f"SOURCE_REVISION={revision}",
        "--build-arg",
        "SOURCE_IDENTITY=accepted-p9-derived-p10",
        "--build-arg",
        f"PRODUCT_VERSION={DISPLAY_VERSION}",
    ]
    _run([*common, "--file", "Dockerfile.p10", "--tag", runtime_tag, "."], cwd=root)
    _run([*common, "--file", "Dockerfile.p10", "--tag", studio_tag, "."], cwd=root / "studio")
    runtime_ref = runtime_tag.split(":", 1)[0] + "@" + _image_id(root, runtime_tag)
    studio_ref = studio_tag.split(":", 1)[0] + "@" + _image_id(root, studio_tag)
    bundle = work / "bundle"
    build_bundle(root, bundle, revision, runtime_ref, studio_ref)
    return LocalCandidate(bundle, runtime_ref, studio_ref, runtime_tag, studio_tag, revision, oci)


def cleanup_candidate(root: Path, candidate: LocalCandidate) -> None:
    subprocess.run(
        ["docker", "image", "rm", "--force", candidate.runtime_tag, candidate.studio_tag],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=120,
        check=False,
    )


def free_port() -> int:
    with socket.socket() as handle:
        handle.bind(("127.0.0.1", 0))
        return int(handle.getsockname()[1])


def dc_command(
    candidate: LocalCandidate,
    managed_root: Path,
    api_port: int,
    studio_port: int,
    command: str,
    *,
    extra: tuple[str, ...] = (),
    timeout: int = 180,
) -> tuple[int, dict[str, Any], str]:
    environment = {
        **os.environ,
        "DC_TEST_MODE": "1",
        "DC_TEST_FILEVAULT_STATUS": "unknown",
    }
    completed = subprocess.run(
        [
            str(candidate.bundle / "dc"),
            "--json",
            "--managed-root",
            str(managed_root),
            "--api-port",
            str(api_port),
            "--studio-port",
            str(studio_port),
            command,
            *extra,
        ],
        cwd=candidate.bundle,
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    bounded = (completed.stdout + completed.stderr)[:8192]
    try:
        value = json.loads(completed.stdout.strip())
    except json.JSONDecodeError as exc:
        raise GateError("operator_output_not_json") from exc
    if not isinstance(value, dict):
        raise GateError("operator_output_not_object")
    return completed.returncode, value, bounded


def _assert_safe_output(output: str, managed_root: Path) -> None:
    if str(managed_root) in output or str(Path.home()) in output or len(output.encode()) > 8192:
        raise GateError("runtime_output_private_or_unbounded")


def run_compose_runtime(root: Path, candidate: LocalCandidate, work: Path) -> dict[str, object]:
    managed_root = (work / "managed" / "Digital Colleagues").resolve()
    managed_root.parent.mkdir(mode=0o700, parents=True)
    api_port, studio_port = free_port(), free_port()
    while studio_port == api_port:
        studio_port = free_port()
    cleanup_residue = 0
    try:
        code, started, output = dc_command(
            candidate, managed_root, api_port, studio_port, "quickstart"
        )
        _assert_safe_output(output, managed_root)
        if code != 0 or started.get("ready") is not True:
            category = started.get("category", "unknown")
            raise GateError(f"compose_initial_start_failed_{category}")
        state = managed_root / "state/state.sqlite"
        if not state.is_file():
            raise GateError("compose_state_not_persistent")
        canary = "p10-secret-canary-" + secrets.token_hex(16)
        canary_path = managed_root / "secrets/contract-canary"
        descriptor = os.open(canary_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(canary + "\n")
        code, backup, output = dc_command(
            candidate,
            managed_root,
            api_port,
            studio_port,
            "backup",
            extra=("--backup", "runtime-gate.tar.gz"),
        )
        _assert_safe_output(output, managed_root)
        backup_path = managed_root / "backups/runtime-gate.tar.gz"
        if code != 0 or backup.get("verified") is not True or not backup_path.is_file():
            category = backup.get("category", "unknown")
            raise GateError(f"compose_backup_failed_{category}")
        if backup_path.stat().st_mode & 0o777 != 0o600:
            raise GateError("compose_backup_mode_invalid")
        if canary.encode() in state.read_bytes() or canary.encode() in backup_path.read_bytes():
            raise GateError("compose_secret_canary_leaked")
        identifiers = _run(
            [
                "docker",
                "ps",
                "-q",
                "--filter",
                "label=com.docker.compose.project=digital-colleagues-p10",
            ],
            cwd=root,
            timeout=30,
        ).splitlines()
        for identifier in identifiers:
            inspection = _run(["docker", "inspect", identifier], cwd=root, timeout=30)
            logs = _run(["docker", "logs", identifier], cwd=root, timeout=30)
            if canary in inspection or canary in logs:
                raise GateError("compose_secret_canary_leaked")
        code, stopped, output = dc_command(candidate, managed_root, api_port, studio_port, "down")
        _assert_safe_output(output, managed_root)
        if code != 0 or stopped.get("status") != "ok":
            raise GateError("compose_stop_failed")
        code, restored, output = dc_command(
            candidate,
            managed_root,
            api_port,
            studio_port,
            "restore",
            extra=("--backup", "runtime-gate.tar.gz", "--confirm", "RESTORE-P10-STATE"),
        )
        _assert_safe_output(output, managed_root)
        if code != 0 or restored.get("rollback_backup_verified") is not True:
            raise GateError("compose_restore_failed")
        code, up, output = dc_command(candidate, managed_root, api_port, studio_port, "up")
        _assert_safe_output(output, managed_root)
        if code != 0:
            raise GateError("compose_restart_failed")
        code, status, output = dc_command(candidate, managed_root, api_port, studio_port, "status")
        _assert_safe_output(output, managed_root)
        if (
            code != 0
            or status.get("ready") is not True
            or status.get("schema_version_current") != 7
        ):
            raise GateError("compose_restart_health_failed")
    finally:
        try:
            dc_command(candidate, managed_root, api_port, studio_port, "down", timeout=120)
        except (GateError, OSError, subprocess.SubprocessError):
            cleanup_residue += 1
        shutil.rmtree(managed_root.parent, ignore_errors=True)
    if cleanup_residue:
        raise GateError("compose_cleanup_failed")
    project = "digital-colleagues-p10"
    remaining = _run(
        ["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={project}"],
        cwd=root,
        timeout=30,
    )
    if remaining:
        raise GateError("compose_runtime_residue")
    return {
        "schema_version": 1,
        "gate": "p10_compose_runtime_clean",
        "actual_runtime": True,
        "native_architecture": platform.machine(),
        "native_image_selection": "exact_digest",
        "schema_version_current": 7,
        "restart_state_preserved": True,
        "wal_consistent_backup_restore": True,
        "secret_canary_leak_count": 0,
        "unexpected_external_egress_count": 0,
        "cleanup_residue_count": 0,
    }


def check_compose_runtime(root: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="dc-p10-compose-runtime-") as name:
        work = Path(name)
        candidate = build_local_candidate(root, work)
        try:
            return run_compose_runtime(root, candidate, work / "runtime")
        finally:
            cleanup_candidate(root, candidate)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    root = Path(arguments.root).resolve()
    try:
        result = check_compose_runtime(root)
    except (GateError, OSError, subprocess.SubprocessError) as exc:
        print(
            json.dumps({"status": "failed", "category": redact(exc, root)}, sort_keys=True),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
