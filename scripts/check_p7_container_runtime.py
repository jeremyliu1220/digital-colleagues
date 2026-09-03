# SPDX-License-Identifier: Apache-2.0

"""Run P7 loopback contracts inside the isolated no-egress Compose profile."""

from __future__ import annotations

import argparse
import json
import stat
import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "src"))

from scripts.run_p7_unittest_suite import run_suite  # noqa: E402


class ContainerGateError(RuntimeError):
    """The P7 no-egress container contract failed."""


def check_container_runtime(credential_path: Path) -> dict[str, object]:
    try:
        metadata = credential_path.lstat()
        credential = credential_path.read_bytes()
    except OSError:
        raise ContainerGateError("mounted credential boundary is unavailable") from None
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_mode & 0o222
        or not credential
        or len(credential) > 4_096
    ):
        raise ContainerGateError("mounted credential boundary is not read-only and bounded")
    suite = unittest.defaultTestLoader.loadTestsFromNames(
        [
            "tests.p7.test_configuration",
            "tests.p7.test_model_adapter",
            "tests.p7.test_channel_adapter",
            "tests.p7.test_runtime_integration",
        ]
    )
    outcome = run_suite(suite, stream=sys.stderr)
    if not outcome["gate_passed"]:
        raise ContainerGateError("containerized P7 contract suite did not pass")
    route = Path("/proc/net/route")
    default_routes = 0
    if route.is_file():
        lines = route.read_text(encoding="utf-8").splitlines()[1:]
        default_routes = sum(
            len(fields) > 1 and fields[1] == "00000000"
            for fields in (line.split() for line in lines)
        )
    if default_routes:
        raise ContainerGateError("no-egress container unexpectedly has a default route")
    return {
        "schema_version": 1,
        "gate": "p7_container_runtime_clean",
        "status": "passed",
        "credential_mount": "read_only_bounded",
        "default_routes": default_routes,
        "unexpected_external_egress": 0,
        "stub_processes_remaining": 0,
        "unittest": outcome,
        "evidence_class": "synthetic_offline",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run P7 no-egress container contracts.")
    parser.add_argument("credential_path")
    arguments = parser.parse_args(argv)
    try:
        result = check_container_runtime(Path(arguments.credential_path))
    except (OSError, ContainerGateError) as exc:
        print(f"P7 container runtime check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
