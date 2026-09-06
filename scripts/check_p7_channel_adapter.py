# SPDX-License-Identifier: Apache-2.0

"""Validate exact-effect, ambiguity, and reconciliation channel semantics."""

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


def check_channel_adapter(root: Path) -> dict[str, object]:
    tests = run_focused_tests(
        root,
        "tests.p7.test_channel_adapter",
        "tests.p7.test_runtime_integration.P7RuntimeIntegrationTests."
        "test_restart_reconciles_unknown_then_absent_before_bounded_retry",
        "tests.p7.test_runtime_integration.P7RuntimeIntegrationTests."
        "test_submitted_503_is_never_blindly_resent",
        "tests.p7.test_runtime_integration.P7RuntimeIntegrationTests."
        "test_all_uncertain_post_submit_failures_remain_ambiguous_without_retry",
        "tests.p7.test_runtime_integration.P7RuntimeIntegrationTests."
        "test_headless_worker_recovers_ambiguous_only_namespace_across_restart",
        "tests.p7.test_runtime_integration.P7RuntimeIntegrationTests."
        "test_still_unknown_reconciliation_uses_durable_backoff_and_stops_at_budget",
        "tests.p7.test_runtime_integration.P7RuntimeIntegrationTests."
        "test_reconciliation_lease_29_seconds_succeeds_and_31_seconds_fails_closed",
        "tests.p7.test_runtime_integration.P7RuntimeIntegrationTests."
        "test_expired_reconciliation_takeover_fences_old_owner_and_recovers",
        "tests.p7.test_runtime_integration.P7RuntimeIntegrationTests."
        "test_authority_change_during_reconciliation_cannot_create_retry",
        "tests.runtime.test_outbox_binding",
    )
    return {
        "schema_version": 1,
        "gate": "p7_channel_adapter_clean",
        "tests_run": tests,
        "protocol_version": "dc-http-json-v1",
        "outcomes": [
            "ambiguous",
            "known_not_executed",
            "permanent_failure",
            "retryable_failure",
            "succeeded",
        ],
        "reconciliation": ["confirmed_absent", "confirmed_applied", "still_unknown"],
        "post_submit_timeout": "ambiguous",
        "submitted_429_or_5xx": "ambiguous",
        "submitted_redirect_408_or_generic_4xx": "ambiguous",
        "unproven_retryable_wire_result": "ambiguous",
        "restart_binding_source": "durable_exact_effect",
        "restart_recovery_driver": "headless_worker",
        "reconciliation_backoff": "durable_exponential_bounded",
        "reconciliation_lease_finalization": "atomic",
        "blind_resend": False,
        "idempotency_rebinding_refused": True,
        "raw_provider_body_persisted": False,
        "external_calls": 0,
        "evidence_class": "synthetic_offline",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P7 channel adapter.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_channel_adapter(Path(arguments.root).resolve())
    except (OSError, FocusedGateError) as exc:
        print(f"P7 channel adapter check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
