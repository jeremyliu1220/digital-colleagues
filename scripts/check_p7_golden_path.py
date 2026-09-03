# SPDX-License-Identifier: Apache-2.0

"""Run the synthetic/offline P7 optional-adapter Golden Path."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "src"))

from scripts.check_p7_repository import BASE_COMMIT  # noqa: E402
from scripts.p7_gate_support import FocusedGateError, run_focused_tests  # noqa: E402

REFERENCE_FILES = (
    "src/digital_colleagues/adapters/intelligence/deterministic.py",
    "src/digital_colleagues/adapters/channel/reference.py",
)


def _digest(root: Path) -> str:
    aggregate = hashlib.sha256()
    for relative in REFERENCE_FILES:
        value = (root / relative).read_bytes()
        aggregate.update(len(relative.encode()).to_bytes(8, "big"))
        aggregate.update(relative.encode())
        aggregate.update(hashlib.sha256(value).digest())
    return "sha256:" + aggregate.hexdigest()


def _base_digest(root: Path) -> str:
    import subprocess

    aggregate = hashlib.sha256()
    for relative in REFERENCE_FILES:
        completed = subprocess.run(
            ["git", "show", f"{BASE_COMMIT}:{relative}"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if completed.returncode != 0:
            raise FocusedGateError("accepted deterministic reference source is unavailable")
        aggregate.update(len(relative.encode()).to_bytes(8, "big"))
        aggregate.update(relative.encode())
        aggregate.update(hashlib.sha256(completed.stdout).digest())
    return "sha256:" + aggregate.hexdigest()


def check_golden_path(root: Path) -> dict[str, object]:
    current = _digest(root)
    accepted = _base_digest(root)
    if current != accepted:
        raise FocusedGateError("accepted deterministic reference adapters drifted")
    tests = run_focused_tests(root, "tests.p7.test_runtime_integration")
    return {
        "schema_version": 1,
        "gate": "p7_golden_path_clean",
        "tests_run": tests,
        "protocol_version": "dc-http-json-v1",
        "default_model": "DeterministicIntelligence",
        "default_channel": "ReferenceChannel",
        "deterministic_reference_digest": current,
        "deterministic_reference_unchanged": True,
        "optional_adapter_contracts": "passed",
        "exact_effect_approval": "required",
        "ambiguous_blind_resend": False,
        "restart_reconciliation": "still_unknown_without_binding",
        "external_calls": 0,
        "evidence_class": "synthetic_offline",
        "human_evaluation": "not_evaluated",
        "live_provider_evidence": "not_evaluated",
        "claim": "optional_adapter_contracts_passed",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run P7 optional-adapter Golden Path.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_golden_path(Path(arguments.root).resolve())
    except (OSError, FocusedGateError) as exc:
        print(f"P7 Golden Path check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
