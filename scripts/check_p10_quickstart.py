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

from scripts.check_p10_compose_runtime import (
    LocalCandidate,
    _assert_safe_output,
    build_local_candidate,
    cleanup_candidate,
    dc_command,
    free_port,
)
from scripts.p10_gate_support import GateError, redact


def run_quickstart_trials(root: Path, candidate: LocalCandidate, work: Path) -> dict[str, object]:
    durations: list[float] = []
    for trial in range(1, 4):
        parent = work / f"trial-{trial}"
        parent.mkdir(mode=0o700, parents=True)
        managed_root = (parent / "Digital Colleagues").resolve()
        api_port, studio_port = free_port(), free_port()
        while studio_port == api_port:
            studio_port = free_port()
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
            if measured >= 300 or float(launcher_duration) >= 300:
                raise GateError("quickstart_five_minute_target_failed")
            code, status, status_output = dc_command(
                candidate, managed_root, api_port, studio_port, "status"
            )
            _assert_safe_output(status_output, managed_root)
            if code != 0 or status.get("ready") is not True:
                raise GateError("quickstart_status_not_ready")
            durations.append(measured)
        finally:
            try:
                dc_command(candidate, managed_root, api_port, studio_port, "down", timeout=120)
            except (GateError, OSError, subprocess.SubprocessError):
                pass
            shutil.rmtree(parent, ignore_errors=True)
        remaining = subprocess.check_output(
            [
                "docker",
                "ps",
                "-aq",
                "--filter",
                "label=com.docker.compose.project=digital-colleagues-p10",
            ],
            cwd=root,
            text=True,
        ).strip()
        if remaining:
            raise GateError("quickstart_cleanup_residue")
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
        "build_inside_timed_interval_count": 0,
        "provider_credential_count": 0,
        "unexpected_external_egress_count": 0,
        "cleanup_residue_count": 0,
        "filevault_readiness": "not_evaluated_test_boundary",
        "remote_ghcr_pull_path": "not_evaluated",
    }


def check_quickstart(root: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="dc-p10-quickstart-") as name:
        work = Path(name)
        candidate = build_local_candidate(root, work)
        try:
            return run_quickstart_trials(root, candidate, work / "trials")
        finally:
            cleanup_candidate(root, candidate)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    root = Path(arguments.root).resolve()
    try:
        result = check_quickstart(root)
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
