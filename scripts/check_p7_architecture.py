# SPDX-License-Identifier: Apache-2.0

"""Validate P7 adapter-edge capabilities and retained provider-neutral boundaries."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p6_architecture import check_architecture as check_p6_architecture
from scripts.check_p6_repository import BASE_COMMIT as P6_DEVELOPMENT_BASE

P7_BASE = "7e6f4c4dc50b675afb60b6e160fe4f15312dd6c8"
PURE_PREFIXES = (
    "src/digital_colleagues/core/",
    "src/digital_colleagues/governance/",
    "src/digital_colleagues/application/",
)
NETWORK_ROOTS = {
    "aiohttp",
    "http",
    "requests",
    "socket",
    "ssl",
    "urllib",
}
PROVIDER_ROOTS = {"anthropic", "boto3", "google", "microsoft", "openai", "slack_sdk"}
NETWORK_FILES = {
    "src/digital_colleagues/adapters/http_json/configuration.py",
    "src/digital_colleagues/adapters/http_json/transport.py",
}
STABLE_CONTRACTS = {
    "src/digital_colleagues/application/contracts.py",
    "src/digital_colleagues/core",
    "src/digital_colleagues/governance",
}
CORRECTIVE_APPLICATION_FILES = {
    "src/digital_colleagues/application/errors.py",
    "src/digital_colleagues/application/p4_ports.py",
    "src/digital_colleagues/application/p4_services.py",
    "src/digital_colleagues/application/ports.py",
    "src/digital_colleagues/application/services.py",
}


class ArchitectureError(RuntimeError):
    """P7 leaked a provider, network, or dynamic capability across the adapter edge."""


def _modules(tree: ast.AST) -> tuple[str, ...]:
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level or node.module is None:
                raise ArchitectureError("P7 source contains relative or unresolved import")
            modules.append(node.module)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"__import__", "eval", "exec"}:
                raise ArchitectureError("P7 source contains dynamic loading or execution")
    return tuple(modules)


def _unchanged(root: Path, relative: str) -> bool:
    completed = subprocess.run(
        ["git", "diff", "--quiet", P7_BASE, "--", relative],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def check_architecture(root: Path) -> dict[str, object]:
    prior = check_p6_architecture(root)
    if P6_DEVELOPMENT_BASE == P7_BASE:
        raise ArchitectureError("P7 and historical P6 development bases were conflated")
    parsed = 0
    network_files: set[str] = set()
    for document in sorted((root / "src/digital_colleagues").rglob("*.py")):
        relative = document.relative_to(root).as_posix()
        tree = ast.parse(document.read_text(encoding="utf-8"), filename=relative)
        parsed += 1
        modules = _modules(tree)
        roots = {module.split(".", 1)[0] for module in modules}
        if roots & PROVIDER_ROOTS:
            raise ArchitectureError("P7 source imports a named-provider SDK")
        if any(relative.startswith(prefix) for prefix in PURE_PREFIXES):
            if roots & NETWORK_ROOTS or any(
                module.startswith("digital_colleagues.adapters") for module in modules
            ):
                raise ArchitectureError("pure/application source imports an adapter capability")
        if roots & NETWORK_ROOTS:
            network_files.add(relative)
            if relative not in NETWORK_FILES:
                raise ArchitectureError("network capability escaped the P7 adapter edge")
        if relative.startswith("src/digital_colleagues/adapters/http_json/") and "os" in roots:
            raise ArchitectureError("HTTP adapter reads ambient environment directly")
        if relative.startswith(PURE_PREFIXES) and roots & {"fastapi", "pydantic", "sqlite3"}:
            raise ArchitectureError("P7 pure boundary imports an HTTP or database edge")
    if network_files != NETWORK_FILES:
        raise ArchitectureError("P7 bounded network transport files are incomplete")
    if any(not _unchanged(root, relative) for relative in STABLE_CONTRACTS):
        raise ArchitectureError("P7 changed a stable core/application/governance contract")
    changed_application = {
        document.relative_to(root).as_posix()
        for document in (root / "src/digital_colleagues/application").glob("*.py")
        if not _unchanged(root, document.relative_to(root).as_posix())
    }
    if changed_application - CORRECTIVE_APPLICATION_FILES:
        raise ArchitectureError("P7 corrective application changes escaped their finite allowlist")
    if not _unchanged(root, "migrations"):
        raise ArchitectureError("P7 added or changed a migration")
    runtime = (root / "src/digital_colleagues/local/runtime.py").read_text(encoding="utf-8")
    composition = (root / "src/digital_colleagues/local/p7_adapters.py").read_text(encoding="utf-8")
    if any(
        token not in runtime + composition
        for token in (
            "DeterministicIntelligence",
            "ReferenceChannel",
            "HttpJsonIntelligence",
            "HttpJsonChannel",
            "build_selected_adapters",
        )
    ):
        raise ArchitectureError("P7 explicit composition root is incomplete")
    ports = (root / "src/digital_colleagues/application/ports.py").read_text(encoding="utf-8")
    services = (root / "src/digital_colleagues/application/services.py").read_text(encoding="utf-8")
    if any(
        token not in ports + services
        for token in (
            "binding_digest",
            "ExternalAdapterError",
            "adapter_failure_committed",
            "bundle.proposal.proposal_digest",
        )
    ):
        raise ArchitectureError("P7 recovery or durable adapter failure contract is incomplete")
    return {
        "schema_version": 1,
        "gate": "p7_architecture_clean",
        "retained_p6_gate": prior["gate"],
        "files_checked": parsed,
        "network_capability_files": sorted(network_files),
        "provider_sdk_imports": 0,
        "dynamic_imports": 0,
        "stable_contract_drift": 0,
        "backward_compatible_reconciliation_binding": True,
        "bounded_durable_adapter_failure": True,
        "corrective_application_files": sorted(changed_application),
        "migration_008": False,
        "configuration_at_composition_edge": True,
        "dependency_direction": "pure_core_to_application_governance_to_ports_and_adapters",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P7 architecture.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_architecture(Path(arguments.root).resolve())
    except (OSError, SyntaxError, ArchitectureError) as exc:
        print(f"P7 architecture check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
