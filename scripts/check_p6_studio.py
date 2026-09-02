# SPDX-License-Identifier: Apache-2.0

"""Validate P6 role-aware governance surfaces without treating UI as authority."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p5_studio import check_studio as check_p5_studio


class StudioError(RuntimeError):
    """The P6 Studio governance state or safety explanation is incomplete."""


def check_studio(root: Path) -> dict[str, object]:
    prior = check_p5_studio(root)
    app = (root / "studio/src/App.tsx").read_text(encoding="utf-8")
    contract = (root / "studio/src/studioContract.ts").read_text(encoding="utf-8")
    tests = (root / "studio/src/App.test.tsx").read_text(encoding="utf-8")
    required = (
        "Governance & access",
        "SESSION BINDING",
        "Role revision",
        "Membership revision",
        "CREDENTIAL LIFECYCLE",
        "credential-status-list",
        "Second Admin transition",
        "PENDING CHANGE APPROVALS",
        "Canonical digest",
        "Proposer",
        "Approver",
        "Expiry",
        "Refused / stale reason",
        "Reviewed exact diff",
        "SAFE AUDIT EXPORT",
        "Export bounded safe audit",
        "Private payload",
        "isAdmin",
        "visibleNavigation",
        "canExport",
        "Existing session expired",
        "/governance/state",
    )
    if any(value not in app for value in required):
        raise StudioError("a required P6 governance state or role control is missing")
    for value in (
        "Enrollment status without plaintext",
        "Recovery status without plaintext",
        "Separate proposer and approver",
        "read-only",
        "revoked",
        "expired",
    ):
        if value not in contract or value not in tests:
            raise StudioError("P6 Studio contract or test coverage is incomplete")
    if "P6 under verification · independent acceptance required" not in app:
        raise StudioError("P6 Studio claim boundary is not explicit")
    return {
        "schema_version": 1,
        "gate": "p6_studio_clean",
        "retained_p5_gate": prior["gate"],
        "role_aware_controls": True,
        "server_authorization_required": True,
        "session_role_membership_revision_visible": True,
        "credential_plaintext_visible": False,
        "exact_change_state_visible": True,
        "bounded_audit_export": True,
        "revoked_expired_read_only_states": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P6 Studio governance surfaces.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_studio(Path(arguments.root).resolve())
    except (OSError, StudioError) as exc:
        print(f"P6 Studio check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
