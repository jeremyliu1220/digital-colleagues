# SPDX-License-Identifier: Apache-2.0

"""Validate the typed P6 role/action matrix and namespace refusal cases."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "src"))

from digital_colleagues.core.governance import AuthorizationAction  # noqa: E402
from digital_colleagues.core.principals import HumanRole  # noqa: E402
from digital_colleagues.governance.rbac import ROLE_ACTIONS  # noqa: E402
from scripts.p6_gate_support import FocusedGateError, run_focused_tests  # noqa: E402


class RbacError(RuntimeError):
    """The P6 role/action matrix is incomplete or mutable at the edge."""


def check_rbac(root: Path) -> dict[str, object]:
    if set(ROLE_ACTIONS) != set(HumanRole):
        raise RbacError("canonical human role coverage is incomplete")
    admin = ROLE_ACTIONS[HumanRole.TENANT_ADMIN]
    user = ROLE_ACTIONS[HumanRole.COLLEAGUE_USER]
    auditor = ROLE_ACTIONS[HumanRole.AUDITOR]
    if admin != frozenset(AuthorizationAction):
        raise RbacError("Admin action coverage drifted")
    if any(
        action in user
        for action in {
            AuthorizationAction.MANAGE_CREDENTIAL,
            AuthorizationAction.MANAGE_MEMBERSHIP,
            AuthorizationAction.MANAGE_DRAFT,
            AuthorizationAction.EXPORT_AUDIT,
        }
    ):
        raise RbacError("User received governance authority")
    if auditor != frozenset(
        {
            AuthorizationAction.READ_SESSION_SECURITY,
            AuthorizationAction.READ_COLLEAGUE,
            AuthorizationAction.READ_GOVERNANCE,
            AuthorizationAction.EXPORT_AUDIT,
        }
    ):
        raise RbacError("Auditor is not exactly read/export only")
    tests = run_focused_tests(
        root,
        "tests.p6.test_authentication_rbac.P6AuthenticationRbacTests."
        "test_scoped_roles_matrix_api_authority_injection_and_idor_fail_closed",
        "tests.p6.test_authentication_rbac.P6AuthenticationRbacTests."
        "test_role_and_membership_revisions_are_checked_on_every_session_use",
    )
    return {
        "schema_version": 1,
        "gate": "p6_rbac_namespace_clean",
        "tests_run": tests,
        "role_count": len(ROLE_ACTIONS),
        "action_count": len(AuthorizationAction),
        "human_only_roles": True,
        "server_side_namespace_checks": True,
        "auditor_read_export_only": True,
        "alternate_endpoint_bypass_refused": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P6 RBAC and namespace scope.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_rbac(Path(arguments.root).resolve())
    except (OSError, FocusedGateError, RbacError) as exc:
        print(f"P6 RBAC check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
