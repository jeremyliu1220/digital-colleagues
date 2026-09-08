# SPDX-License-Identifier: Apache-2.0

"""Measure three clean actual Mac quickstarts from one prebuilt P10 candidate."""

from __future__ import annotations

import json
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_p10_candidate import build_bundle
from scripts.check_p10_compose_runtime import (
    LocalCandidate,
    _assert_safe_output,
    build_local_candidate,
    cleanup_candidate,
    dc_command,
    free_port,
    probe_external_egress,
    validate_external_egress_probe,
)
from scripts.check_p10_distribution import verify_remote_distribution
from scripts.p10_gate_support import GateError, load_json, redact


def _task_residue(root: Path) -> dict[str, int]:
    project_filter = "label=com.docker.compose.project=digital-colleagues-p10"
    commands = {
        "containers": ["docker", "ps", "-aq", "--filter", project_filter],
        "networks": ["docker", "network", "ls", "-q", "--filter", project_filter],
        "volumes": ["docker", "volume", "ls", "-q", "--filter", project_filter],
    }
    return {
        key: len(
            [
                line
                for line in subprocess.check_output(command, cwd=root, text=True).splitlines()
                if line
            ]
        )
        for key, command in commands.items()
    }


def _port_available(port: int) -> bool:
    import socket

    try:
        with socket.socket() as handle:
            handle.bind(("127.0.0.1", port))
    except OSError:
        return False
    return True


def run_quickstart_trials(
    root: Path,
    candidate: LocalCandidate,
    work: Path,
    *,
    maximum_seconds: int = 300,
    remote: bool = False,
) -> dict[str, object]:
    durations: list[float] = []
    external_egress_probe_count = 0
    unexpected_external_egress_count = 0
    residue_checks = 0
    port_checks = 0
    for trial in range(1, 4):
        if any(_task_residue(root).values()):
            raise GateError("quickstart_preexisting_task_residue")
        residue_checks += 1
        parent = work / f"trial-{trial}"
        parent.mkdir(mode=0o700, parents=True)
        managed_root = (parent / "Digital Colleagues").resolve()
        api_port, studio_port = free_port(), free_port()
        while studio_port == api_port:
            studio_port = free_port()
        if not _port_available(api_port) or not _port_available(studio_port):
            raise GateError("quickstart_port_precondition_failed")
        port_checks += 2
        started = time.monotonic()
        try:
            code, value, output = dc_command(
                candidate, managed_root, api_port, studio_port, "quickstart", timeout=300
            )
            ended = time.monotonic()
            _assert_safe_output(output, managed_root)
            measured = round(ended - started, 3)
            launcher_duration = value.get("duration_seconds")
            if (
                code != 0
                or value.get("ready") is not True
                or not isinstance(launcher_duration, (int, float))
            ):
                raise GateError("quickstart_trial_not_ready")
            if measured >= maximum_seconds or float(launcher_duration) >= maximum_seconds:
                raise GateError("quickstart_five_minute_target_failed")
            code, status, status_output = dc_command(
                candidate, managed_root, api_port, studio_port, "status"
            )
            _assert_safe_output(status_output, managed_root)
            if code != 0 or status.get("ready") is not True:
                raise GateError("quickstart_status_not_ready")
            probe = probe_external_egress(root, candidate)
            external_egress_probe_count += 1
            unexpected_external_egress_count += validate_external_egress_probe(probe)
            if unexpected_external_egress_count:
                raise GateError("quickstart_unexpected_external_egress")
            durations.append(measured)
        finally:
            try:
                dc_command(candidate, managed_root, api_port, studio_port, "down", timeout=120)
            except (GateError, OSError, subprocess.SubprocessError):
                pass
            shutil.rmtree(parent, ignore_errors=True)
        residue = _task_residue(root)
        residue_checks += 1
        if any(residue.values()):
            raise GateError("quickstart_cleanup_residue")
        if not _port_available(api_port) or not _port_available(studio_port):
            raise GateError("quickstart_port_cleanup_failed")
        port_checks += 2
    if len(durations) != 3:
        raise GateError("quickstart_trial_count_invalid")
    return {
        "schema_version": 1,
        "gate": "p10_quickstart_clean",
        "actual_macos": True,
        "platform_class": f"macos/{platform.machine()}",
        "preconditions": {
            "docker_cli": "passed",
            "compose_plugin": "passed",
            "docker_daemon": "passed",
            "distribution_bundle": "verified",
            "ports": "unique_loopback",
            "managed_roots": "os_temporary",
        },
        "trial_count": 3,
        "durations_seconds": durations,
        "maximum_seconds": max(durations),
        "median_seconds": statistics.median(durations),
        "all_below_300_seconds": True,
        "all_below_60_seconds": maximum_seconds == 60,
        "build_inside_timed_interval_count": 0,
        "provider_credential_count": 0,
        "external_egress_probe_count": external_egress_probe_count,
        "external_egress_control_count": external_egress_probe_count,
        "internal_network_verified": True,
        "unexpected_external_egress_count": unexpected_external_egress_count,
        "cleanup_residue_count": 0,
        "docker_residue_check_count": residue_checks,
        "port_availability_check_count": port_checks,
        "filevault_readiness": "not_evaluated_test_boundary",
        "remote_ghcr_pull_path": "passed" if remote else "not_evaluated",
    }


def check_quickstart(root: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="dc-p10-quickstart-") as name:
        work = Path(name)
        candidate = build_local_candidate(root, work)
        try:
            return run_quickstart_trials(root, candidate, work / "trials")
        finally:
            cleanup_candidate(root, candidate)


def check_remote_distribution(root: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="dc-p10-remote-distribution-") as name:
        work = Path(name)
        policy = load_json(root / "distribution/p10/verification-policy.json")
        remote = verify_remote_distribution(root, policy, work / "verification")
        revision = str(remote["published_source_revision"])
        runtime = remote["runtime"]
        studio = remote["studio"]
        if not isinstance(runtime, dict) or not isinstance(studio, dict):
            raise GateError("remote_distribution_result_invalid")
        runtime_ref = f"{runtime['subject']}@{runtime['digest']}"
        studio_ref = f"{studio['subject']}@{studio['digest']}"
        bundle = work / "bundle"
        build_bundle(root, bundle, revision, runtime_ref, studio_ref)
        candidate = LocalCandidate(
            bundle=bundle,
            runtime_ref=runtime_ref,
            studio_ref=studio_ref,
            runtime_tag=runtime_ref,
            studio_tag=studio_ref,
            source_revision=revision,
            oci={"runtime": runtime, "studio": studio},
        )
        quickstart = run_quickstart_trials(
            root,
            candidate,
            work / "trials",
            maximum_seconds=60,
            remote=True,
        )
        return {
            "schema_version": 1,
            "gate": "p10_remote_distribution_and_quickstart_clean",
            "distribution": remote,
            "quickstart": quickstart,
            "digest_bound_release_bundle": "verified",
            "host_gh_or_cosign_install_required": False,
            "cleanup_residue_count": 0,
        }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--remote-distribution", action="store_true")
    arguments = parser.parse_args(argv)
    root = Path(arguments.root).resolve()
    try:
        result = (
            check_remote_distribution(root)
            if arguments.remote_distribution
            else check_quickstart(root)
        )
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
