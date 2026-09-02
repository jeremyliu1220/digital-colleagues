# SPDX-License-Identifier: Apache-2.0

"""Validate the static loopback-only P6 Compose and composition root."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p4_compose import check_compose as check_p4_compose


class ComposeError(RuntimeError):
    """P6 local topology or governance composition is incomplete."""


def check_compose(root: Path) -> dict[str, object]:
    prior = check_p4_compose(root)
    runtime = (root / "src/digital_colleagues/local/runtime.py").read_text(encoding="utf-8")
    operator = (root / "src/digital_colleagues/local/operator.py").read_text(encoding="utf-8")
    compose = (root / "compose.yaml").read_text(encoding="utf-8")
    required_runtime = (
        "SQLiteP6Store",
        "P6AuthenticationService",
        "P6ColleagueService",
        "P6BuilderService",
        "P6RuntimeController",
        "P6DispatchAuthorizer",
        "P6ChangeService",
        "P6AuditService",
        "install_p6_routes",
    )
    if any(value not in runtime for value in required_runtime):
        raise ComposeError("P6 local composition root is incomplete")
    if any(
        value not in operator
        for value in ("bootstrap-token", "enrollment-token", "recovery-session")
    ):
        raise ComposeError("one-shot local operator credential boundary is incomplete")
    if compose.count("state:/state") != 3 or '"127.0.0.1:${DC_API_PORT' not in compose:
        raise ComposeError("P6 topology drifted from one state volume or loopback publishing")
    if "--no-access-log" not in compose:
        raise ComposeError("API access logging could expose credential paths")
    return {
        "schema_version": 1,
        "gate": "p6_compose_static_clean",
        "retained_p4_gate": prior["gate"],
        "services": prior["services"],
        "host_bind": "127.0.0.1",
        "container_bind": "0.0.0.0",
        "state_volume": "one_project_scoped_state_sqlite",
        "deterministic_provider_reference_channel": True,
        "p6_composition_root": True,
        "plaintext_service_logging": False,
        "actual_runtime_gate": "separate_required",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate static P6 Compose topology.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_compose(Path(arguments.root).resolve())
    except (OSError, ComposeError) as exc:
        print(f"P6 Compose check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
