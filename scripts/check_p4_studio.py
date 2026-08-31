# SPDX-License-Identifier: Apache-2.0

"""Inspect the P4 Studio workflow and user-visible state contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIRED_ENDPOINTS = {
    "/auth/bootstrap/exchange",
    "/auth/session",
    "/colleagues/preview",
    "/colleagues",
    "/work",
    "/studio/state",
    "/runtime/triggers",
    "/runtime/process",
    "/decision",
    "/audit/",
}
REQUIRED_STATES = {
    "loading-state",
    "empty-state",
    "notice-success",
    "notice-rejection",
    "notice-stale",
    "fatal-state",
}
REQUIRED_CONCEPTS = {
    "Descriptive Profile",
    "Authoritative Mandate",
    "Exact revision to create",
    "Effect boundary",
    "Wake-cycle inspector",
    "Proposal inbox",
    "ACTIONRESULT",
    "Causal audit",
}


class StudioError(RuntimeError):
    """The Studio source does not expose the required P4 workflow."""


def check_studio(root: Path) -> dict[str, object]:
    app = (root / "studio/src/App.tsx").read_text(encoding="utf-8")
    styles = (root / "studio/src/styles.css").read_text(encoding="utf-8")
    tests = (root / "studio/src/App.test.tsx").read_text(encoding="utf-8")
    combined = app + styles + tests
    if any(item not in app for item in REQUIRED_ENDPOINTS):
        raise StudioError("Studio endpoint coverage is incomplete")
    if any(item not in combined for item in REQUIRED_STATES):
        raise StudioError("Studio state coverage is incomplete")
    if any(item not in app for item in REQUIRED_CONCEPTS):
        raise StudioError("Studio authority or causal view is incomplete")
    if "localStorage" in app or "sessionStorage" in app:
        raise StudioError("Studio attempts to simulate durable state in browser storage")
    if "<button" not in app or "<form" not in app or "onSubmit" not in app:
        raise StudioError("Studio primary controls are not native keyboard-operable controls")
    if "prefers-reduced-motion" not in styles or ":focus-visible" not in styles:
        raise StudioError("Studio motion or focus accessibility is incomplete")
    return {
        "schema_version": 1,
        "gate": "p4_studio_clean",
        "endpoint_count": len(REQUIRED_ENDPOINTS),
        "workflow_state_count": len(REQUIRED_STATES),
        "authority_and_causal_concept_count": len(REQUIRED_CONCEPTS),
        "browser_storage_persistence": False,
        "keyboard_native_controls": True,
        "reduced_motion": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the P4 Studio workflow.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_studio(Path(arguments.root).resolve())
    except (OSError, StudioError) as exc:
        print(f"P4 Studio check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
