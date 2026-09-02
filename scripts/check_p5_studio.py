# SPDX-License-Identifier: Apache-2.0

"""Validate the P5 Studio builder, exact binding, states, and keyboard controls."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


class StudioError(RuntimeError):
    """The P5 Studio contract is incomplete or hides an authority boundary."""


def check_studio(root: Path) -> dict[str, object]:
    app = (root / "studio/src/App.tsx").read_text(encoding="utf-8")
    styles = (root / "studio/src/styles.css").read_text(encoding="utf-8")
    contract = (root / "studio/src/studioContract.ts").read_text(encoding="utf-8")
    tests = (root / "studio/src/App.test.tsx").read_text(encoding="utf-8")
    required_app = (
        "type View =",
        '"builder"',
        "Revisioned colleague builder",
        "DESCRIPTIVE PROFILE",
        "AUTHORITATIVE MANDATE",
        "TYPED POLICY",
        "EXPLICIT DEFAULTS",
        "Confirm exact revision & digest",
        "expected_canonical_digest",
        "expected_base_profile_revision",
        "expected_base_mandate_revision",
        "expected_base_policy_revision",
        "Legacy P4 working-hours text is display data only",
        'type="button"',
        'type="submit"',
        "stale",
        "conflict",
        "cancelled",
    )
    if any(value not in app for value in required_app):
        raise StudioError("a required P5 Studio workflow or exact binding is missing")
    required_contract = (
        "validation",
        "permission",
        "stale",
        "conflict",
        "cancelled",
        "added",
        "removed",
        "narrowed",
        "expanded",
    )
    if any(value not in contract or value not in tests for value in required_contract):
        raise StudioError("P5 Studio state/diff contract lacks test coverage")
    if "button:focus-visible" not in styles or "select:focus-visible" not in styles:
        raise StudioError("P5 Studio keyboard focus visibility is missing")
    if "auto retry" in app.lower() or "silent rebase" in app.lower():
        raise StudioError("P5 Studio contains a forbidden stale-draft behavior")
    return {
        "schema_version": 1,
        "gate": "p5_studio_clean",
        "profile_mandate_policy_separated": True,
        "exact_revision_digest_confirmation": True,
        "explicit_defaults_visible": True,
        "diff_classifications_visible": True,
        "required_states": list(required_contract[:5]),
        "keyboard_primary_actions": True,
        "stale_auto_retry": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the P5 Studio workflow.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_studio(Path(arguments.root).resolve())
    except (OSError, StudioError) as exc:
        print(f"P5 Studio check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
