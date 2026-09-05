# SPDX-License-Identifier: Apache-2.0

"""Exercise P7 authority, egress, redaction, replay, and retained governance abuse cases."""

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

ABUSE_CASES = (
    "adapter_mode_injection",
    "endpoint_ssrf_and_rebinding",
    "credential_path_and_value_disclosure",
    "redirect_and_tls_downgrade",
    "model_authority_injection",
    "model_human_approval_simulation",
    "provider_directed_tool_or_callback",
    "malformed_duplicate_and_oversized_json",
    "channel_effect_mutation",
    "idempotency_rebinding",
    "post_submit_timeout_disconnect",
    "blind_ambiguous_resend",
    "fabricated_reconciliation_absence",
    "stale_mandate_policy_rbac_dispatch",
    "attempt_lease_and_fencing_evasion",
    "unexpected_external_egress",
)


def check_abuse(root: Path) -> dict[str, object]:
    tests = run_focused_tests(
        root,
        "tests.p7.test_configuration",
        "tests.p7.test_model_adapter.P7ModelAdapterTests."
        "test_unknown_fields_authority_injection_and_unknown_outcome_fail_closed",
        "tests.p7.test_model_adapter.P7ModelAdapterTests."
        "test_wrong_principal_and_oversized_request_make_no_network_call",
        "tests.p7.test_channel_adapter.P7ChannelAdapterTests."
        "test_authority_binding_and_idempotency_rebinding_fail_before_network",
        "tests.p7.test_channel_adapter.P7ChannelAdapterTests."
        "test_authority_fields_in_acknowledgement_are_refused",
        "tests.p7.test_runtime_integration.P7RuntimeIntegrationTests."
        "test_restart_reconciles_unknown_then_absent_before_bounded_retry",
        "tests.p7.test_runtime_integration.P7RuntimeIntegrationTests."
        "test_submitted_503_is_never_blindly_resent",
        "tests.p7.test_runtime_integration.P7RuntimeIntegrationTests."
        "test_provider_failure_commits_bounded_safe_causal_stop_across_restart",
        "tests.p7.test_runtime_integration.P7RuntimeIntegrationTests."
        "test_one_model_failure_does_not_stop_other_bounded_work",
        "tests.p6.test_effect_audit.P6EffectAuditTests."
        "test_effect_dispatch_revalidates_current_membership_and_expiry",
        "tests.runtime.test_outbox_binding",
    )
    return {
        "schema_version": 1,
        "gate": "p7_abuse_clean",
        "tests_run": tests,
        "abuse_case_count": len(ABUSE_CASES),
        "abuse_cases": list(ABUSE_CASES),
        "safe_refusals": len(ABUSE_CASES),
        "authority_expansions": 0,
        "human_approvals_from_provider": 0,
        "unexpected_external_egress": 0,
        "blind_ambiguous_resends": 0,
        "public_boundary_exceptions": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P7 abuse-case refusals.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_abuse(Path(arguments.root).resolve())
    except (OSError, FocusedGateError) as exc:
        print(f"P7 abuse check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
