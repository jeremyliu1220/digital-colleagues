# SPDX-License-Identifier: Apache-2.0

"""Validate P7 explicit opt-in, endpoint, credential, and bound settings."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "src"))

from scripts.p7_gate_support import FocusedGateError, run_focused_tests  # noqa: E402


def check_configuration(root: Path) -> dict[str, object]:
    tests = run_focused_tests(root, "tests.p7.test_configuration")
    return {
        "schema_version": 1,
        "gate": "p7_configuration_clean",
        "tests_run": tests,
        "model_modes": ["deterministic", "http_json_v1"],
        "channel_modes": ["http_json_v1", "reference"],
        "default_model": "deterministic",
        "default_channel": "reference",
        "dynamic_import": False,
        "tls_verification": True,
        "redirects": "refused",
        "loopback_http": "explicit_test_only",
        "credential_boundary": "read_only_file",
        "credential_environment_values": False,
        "validation_before_state_or_services": True,
        "later_construction_failure_closes_store": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P7 adapter configuration.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_configuration(Path(arguments.root).resolve())
    except (OSError, FocusedGateError) as exc:
        print(f"P7 configuration check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
