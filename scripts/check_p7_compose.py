# SPDX-License-Identifier: Apache-2.0

"""Validate deterministic default Compose and explicit P7 no-egress profile."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p6_compose import check_compose as check_p6_compose


class ComposeError(RuntimeError):
    """P7 default or optional Compose topology is incomplete."""


def _service_block(document: str, service: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(service)}:\n(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:\n|^networks:\n)",
        document,
    )
    if match is None:
        raise ComposeError(f"P7 Compose service is missing: {service}")
    return match.group(0)


def _assert_isolated_topology(document: str) -> None:
    shared = ("p7-api", "p7-worker", "p7-studio", "p7-operator")
    stub = _service_block(document, "p7-stub")
    if "\n    networks:\n      - p7-isolated\n" not in stub:
        raise ComposeError("P7 stub must attach only to the internal network")
    published = (
        '"127.0.0.1:${DC_P7_API_PORT:?set a temporary API port}:18000"',
        '"127.0.0.1:${DC_P7_STUDIO_PORT:?set a temporary Studio port}:18080"',
        '"127.0.0.1:${DC_P7_STUB_PORT:?set a temporary stub control port}:18091"',
    )
    if "\n    ports:\n" in stub:
        raise ComposeError("P7 stub unexpectedly owns a host-published port")
    guard = _service_block(document, "p7-egress-guard")
    if (
        "\n    networks:\n      - p7-isolated\n      - p7-published\n" not in guard
        or "scripts/p7_compose_network_guard.py" not in guard
        or "\n    cap_drop:\n      - ALL\n" not in guard
        or any(capability not in guard for capability in ("NET_ADMIN", "SETGID", "SETUID"))
        or "no-new-privileges:true" not in guard
    ):
        raise ComposeError("P7 published namespace route guard is incomplete")
    if "\n    ports:\n" not in guard or any(binding not in guard for binding in published):
        raise ComposeError("P7 published ports are not exact loopback-only bindings")
    for service in shared:
        block = _service_block(document, service)
        if "network_mode: service:p7-stub" not in block or "\n    networks:\n" in block:
            raise ComposeError(f"{service} escaped the isolated shared network namespace")
        if "\n    ports:\n" in block:
            raise ComposeError(f"{service} owns an unexpected published-port attachment")
    ingress = _service_block(document, "p7-ingress")
    if (
        "network_mode: service:p7-egress-guard" not in ingress
        or "\n    networks:\n" in ingress
        or "\n    ports:\n" in ingress
    ):
        raise ComposeError("p7-ingress escaped the guarded publisher namespace")
    adapter_gate = _service_block(document, "p7-adapter-gate")
    if "network_mode: none" not in adapter_gate:
        raise ComposeError("P7 auxiliary adapter Gate must have no network namespace")
    networks = document.split("\nnetworks:\n", 1)
    if len(networks) != 2:
        raise ComposeError("P7 isolated network declaration is missing")
    network_block = networks[1].split("\nvolumes:\n", 1)[0]
    if network_block.strip() != "p7-isolated:\n    internal: true\n  p7-published:":
        raise ComposeError("P7 Compose network declarations escaped the guarded topology")
    if "0.0.0.0:${DC_P7_" in document:
        raise ComposeError("P7 host publishing escaped loopback")


def check_compose(root: Path) -> dict[str, object]:
    prior = check_p6_compose(root)
    default = (root / "compose.yaml").read_text(encoding="utf-8")
    optional = (root / "compose.p7.yaml").read_text(encoding="utf-8")
    dockerfile = (root / "Dockerfile.p7").read_text(encoding="utf-8")
    dockerignore = (root / "Dockerfile.p7.dockerignore").read_text(encoding="utf-8")
    runtime = (root / "src/digital_colleagues/local/runtime.py").read_text(encoding="utf-8")
    selection = (root / "src/digital_colleagues/local/p7_adapters.py").read_text(encoding="utf-8")
    network_guard = (root / "scripts/p7_compose_network_guard.py").read_text(encoding="utf-8")
    if any(token in default for token in ("DC_MODEL_ENDPOINT", "DC_CHANNEL_ENDPOINT")):
        raise ComposeError("default Compose unexpectedly configures a network adapter")
    required = (
        "optional-adapters",
        "p7-adapter-gate",
        "p7-stub",
        "p7-api",
        "p7-worker",
        "p7-studio",
        "p7-ingress",
        "p7-egress-guard",
        "p7-operator",
        "Dockerfile.p7",
        ":/run/secrets/p7-credential:ro",
        "network_mode: none",
        "network_mode: service:p7-stub",
        "network_mode: service:p7-egress-guard",
        "internal: true",
        "DC_MODEL_ADAPTER: http_json_v1",
        "DC_CHANNEL_ADAPTER: http_json_v1",
        "read_only: true",
        'restart: "no"',
    )
    if any(token not in optional for token in required):
        raise ComposeError("P7 optional profile or credential boundary is incomplete")
    _assert_isolated_topology(optional)
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
    if any(
        token not in dockerfile + network_guard
        for token in (
            "iproute2",
            "default_route_count",
            '"route", "del", "default"',
            "os.setuid",
            "os.setgid",
        )
    ):
        raise ComposeError("P7 publisher route removal and privilege drop are incomplete")
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
        "adapter_gate_network": "internal_shared_loopback_namespace",
        "runtime_services": [
            "p7-api",
            "p7-egress-guard",
            "p7-ingress",
            "p7-studio",
            "p7-stub",
            "p7-worker",
        ],
        "host_ingress": "loopback_only_tcp_forwarder",
        "publisher_route_guard": "default_route_removed_before_ingress",
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
