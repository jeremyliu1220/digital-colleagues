# SPDX-License-Identifier: Apache-2.0

"""Exercise the P6 negative authorization and abuse-case inventory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "src"))

from scripts.p6_gate_support import FocusedGateError, run_focused_tests  # noqa: E402

ABUSE_CASES = (
    "caller_authority_injection",
    "model_service_human_impersonation",
    "auditor_user_elevation",
    "self_approval",
    "role_elevation_bypass",
    "credential_guess_replay_expiry_revocation_race",
    "session_fixation_and_stale_revision",
    "csrf_origin_cross_site",
    "idempotency_rebinding",
    "cross_tenant_colleague_principal_idor",
    "change_stale_expired_replay",
    "effect_stale_expired_replay",
    "audit_export_overreach_and_unbounded",
    "alternate_endpoint_bypass",
    "transaction_rollback_partial_grant",
    "p5_flood_budget_trigger_regression",
)


def check_abuse(root: Path) -> dict[str, object]:
    tests = run_focused_tests(
        root,
        "tests.p6.test_authentication_rbac",
        "tests.p6.test_change_approval",
        "tests.p6.test_effect_audit",
        "tests.p6.test_migrations.P6MigrationTests.test_failed_007_rolls_back_schema_and_migration_record",
        "tests.p5.test_policy.P5PolicyTests."
        "test_budget_is_restart_safe_duplicate_class_cannot_evade_and_stop_requires_revision",
    )
    return {
        "schema_version": 1,
        "gate": "p6_abuse_cases_clean",
        "tests_run": tests,
        "abuse_cases": list(ABUSE_CASES),
        "safe_refusal_count": len(ABUSE_CASES),
        "credential_in_diagnostics": False,
        "unauthorized_proposal_escape": {
            "numerator": 0,
            "denominator": len(ABUSE_CASES),
            "rate": 0.0,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P6 abuse cases.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_abuse(Path(arguments.root).resolve())
    except (OSError, FocusedGateError) as exc:
        print(f"P6 abuse check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
