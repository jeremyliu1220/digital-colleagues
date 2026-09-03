# SPDX-License-Identifier: Apache-2.0

"""Validate deterministic default Compose and explicit P7 no-egress profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p6_compose import check_compose as check_p6_compose


class ComposeError(RuntimeError):
    """P7 default or optional Compose topology is incomplete."""


def check_compose(root: Path) -> dict[str, object]:
    prior = check_p6_compose(root)
    default = (root / "compose.yaml").read_text(encoding="utf-8")
    optional = (root / "compose.p7.yaml").read_text(encoding="utf-8")
    dockerfile = (root / "Dockerfile.p7").read_text(encoding="utf-8")
    dockerignore = (root / "Dockerfile.p7.dockerignore").read_text(encoding="utf-8")
    runtime = (root / "src/digital_colleagues/local/runtime.py").read_text(encoding="utf-8")
    selection = (root / "src/digital_colleagues/local/p7_adapters.py").read_text(encoding="utf-8")
    if any(token in default for token in ("DC_MODEL_ENDPOINT", "DC_CHANNEL_ENDPOINT")):
        raise ComposeError("default Compose unexpectedly configures a network adapter")
    required = (
        "optional-adapters",
        "p7-adapter-gate",
        "Dockerfile.p7",
        ":/run/secrets/p7-credential:ro",
        "network_mode: none",
        "read_only: true",
        'restart: "no"',
    )
    if any(token not in optional for token in required):
        raise ComposeError("P7 optional profile or credential boundary is incomplete")
    if any(
        token not in runtime + selection + dockerfile
        for token in (
            "build_selected_adapters",
            "DeterministicIntelligence",
            "ReferenceChannel",
            "HttpJsonIntelligence",
            "HttpJsonChannel",
            "check_p7_container_runtime.py",
        )
    ):
        raise ComposeError("P7 composition root or container Gate is incomplete")
    ignored = set(dockerignore.splitlines())
    if not {".git", "artifacts", "provenance", ".env*"}.issubset(ignored) or "tests" in ignored:
        raise ComposeError("P7 container context is not safely limited with tests available")
    lowered = optional.lower()
    if any(token in lowered for token in ("api_key:", "bearer ", "password:", "token:")):
        raise ComposeError("P7 Compose contains credential-shaped configuration")
    return {
        "schema_version": 1,
        "gate": "p7_compose_static_clean",
        "retained_p6_gate": prior["gate"],
        "default_model": "deterministic",
        "default_channel": "reference",
        "default_network_provider": False,
        "optional_profile": "optional-adapters",
        "credential_mount": "read_only",
        "adapter_gate_network": "none_with_process_local_loopback",
        "published_bind": "127.0.0.1",
        "actual_runtime_gate": "separate_required",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate static P7 Compose topology.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_compose(Path(arguments.root).resolve())
    except (OSError, ComposeError) as exc:
        print(f"P7 Compose check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
