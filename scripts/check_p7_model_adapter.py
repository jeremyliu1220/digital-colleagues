# SPDX-License-Identifier: Apache-2.0

"""Validate the strict provider-neutral P7 model adapter contract."""

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


def check_model_adapter(root: Path) -> dict[str, object]:
    tests = run_focused_tests(root, "tests.p7.test_model_adapter")
    return {
        "schema_version": 1,
        "gate": "p7_model_adapter_clean",
        "tests_run": tests,
        "protocol_version": "dc-http-json-v1",
        "finite_outcomes": ["escalation", "no_op", "proposal", "wait"],
        "server_authority_reconstructed": True,
        "authority_injection_refused": True,
        "raw_provider_body_persisted": False,
        "external_calls": 0,
        "evidence_class": "synthetic_offline",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P7 model adapter.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_model_adapter(Path(arguments.root).resolve())
    except (OSError, FocusedGateError) as exc:
        print(f"P7 model adapter check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
