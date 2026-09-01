# SPDX-License-Identifier: Apache-2.0

"""Validate the static P5 Compose topology and P5 composition root."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p4_compose import check_compose as check_p4_compose


class ComposeError(RuntimeError):
    """The P5 local topology or composition root is incomplete."""


def check_compose(root: Path) -> dict[str, object]:
    prior = check_p4_compose(root)
    runtime = (root / "src/digital_colleagues/local/runtime.py").read_text(encoding="utf-8")
    required = (
        "SQLiteP5Store",
        "RevisionedColleagueBuilderService",
        "PolicyGovernedIntelligence",
        "P5DispatchAuthorizer",
        "P5RuntimeController",
        "install_p5_routes",
    )
    if any(value not in runtime for value in required):
        raise ComposeError("the local composition root does not wire the complete P5 path")
    return {
        "schema_version": 1,
        "gate": "p5_compose_static_clean",
        "p4_topology_gate": prior["gate"],
        "services": prior["services"],
        "host_bind": prior["host_bind"],
        "state_volume": "project_scoped_single_state_sqlite",
        "p5_composition_root": True,
        "runtime_config_status": prior["runtime_config_status"],
        "actual_runtime_gate": "separate_required",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate static P5 Compose topology.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_compose(Path(arguments.root).resolve())
    except (OSError, ComposeError) as exc:
        print(f"P5 Compose check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
