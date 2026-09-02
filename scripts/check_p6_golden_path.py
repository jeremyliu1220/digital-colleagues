# SPDX-License-Identifier: Apache-2.0

"""Run the fresh-instance synthetic/offline P6 security Golden Path."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "src"))

from scripts.check_p6_abuse import (  # noqa: E402
    observe_unauthorized_proposal_escape,
    require_zero_unauthorized_escape,
)
from scripts.p6_gate_support import FocusedGateError, run_focused_tests  # noqa: E402


def check_golden_path(root: Path) -> dict[str, object]:
    tests = run_focused_tests(
        root,
        "tests.p6.test_authentication_rbac",
        "tests.p6.test_change_approval",
        "tests.p6.test_effect_audit",
        "tests.p6.test_migrations",
    )
    unauthorized_metric = observe_unauthorized_proposal_escape()
    require_zero_unauthorized_escape(unauthorized_metric)
    return {
        "schema_version": 1,
        "gate": "p6_security_golden_path_clean",
        "tests_run": tests,
        "evidence_class": "synthetic_offline",
        "fresh_instance": True,
        "second_admin_bootstrap_transition": "single_auditable_consumed",
        "enrollment_recovery_restart": "passed",
        "two_person_exact_change": "passed",
        "exact_effect_dispatch_revalidation": "passed",
        "audit_export_redaction": "passed",
        "ai_initiated_rate": {
            "status": "not_applicable",
            "denominator": 0,
            "reason": "security fixture has no eligible user-visible autonomous opportunity",
        },
        "unauthorized_proposal_escape_rate": unauthorized_metric,
        "human_evaluation": "not_evaluated",
        "live_provider_evidence": "not_evaluated",
        "production_security": "not_claimed",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the P6 security Golden Path.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_golden_path(Path(arguments.root).resolve())
    except (OSError, FocusedGateError) as exc:
        print(f"P6 Golden Path check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
