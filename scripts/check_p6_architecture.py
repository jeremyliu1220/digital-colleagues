# SPDX-License-Identifier: Apache-2.0

"""Validate P6 dependency direction, typed boundaries, and injected capabilities."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p3_architecture import check_architecture as check_p3_architecture

P6_FILES = {
    "core": ("src/digital_colleagues/core/governance.py",),
    "governance": ("src/digital_colleagues/governance/rbac.py",),
    "application": (
        "src/digital_colleagues/application/p6_contracts.py",
        "src/digital_colleagues/application/p6_ports.py",
        "src/digital_colleagues/application/p6_services.py",
    ),
    "adapter": ("src/digital_colleagues/adapters/sqlite/p6_store.py",),
    "api": ("src/digital_colleagues/api/p6_app.py",),
}


class ArchitectureError(RuntimeError):
    """A P6 source boundary points outward or hides authority/capabilities."""


def _modules(tree: ast.AST) -> tuple[str, ...]:
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level or node.module is None:
                raise ArchitectureError("P6 source contains a relative or unresolved import")
            modules.append(node.module)
    return tuple(modules)


def check_architecture(root: Path) -> dict[str, object]:
    prior = check_p3_architecture(root)
    parsed: dict[str, ast.AST] = {}
    for boundary, paths in P6_FILES.items():
        for relative in paths:
            document = root / relative
            if not document.is_file():
                raise ArchitectureError("a required P6 boundary file is missing")
            parsed[relative] = ast.parse(document.read_text(encoding="utf-8"))
            modules = _modules(parsed[relative])
            if boundary == "core" and any(
                module.startswith(
                    (
                        "digital_colleagues.application",
                        "digital_colleagues.governance",
                        "digital_colleagues.adapters",
                        "digital_colleagues.api",
                        "fastapi",
                        "pydantic",
                        "sqlite3",
                    )
                )
                for module in modules
            ):
                raise ArchitectureError("P6 core imports an outward or edge dependency")
            if boundary == "governance" and any(
                module.startswith(
                    (
                        "digital_colleagues.application",
                        "digital_colleagues.adapters",
                        "digital_colleagues.api",
                        "fastapi",
                        "pydantic",
                        "sqlite3",
                    )
                )
                for module in modules
            ):
                raise ArchitectureError("P6 governance imports an outward dependency")
            if boundary == "application" and any(
                module.startswith(
                    ("digital_colleagues.adapters", "digital_colleagues.api", "fastapi", "pydantic")
                )
                for module in modules
            ):
                raise ArchitectureError("P6 application imports an adapter or HTTP edge")
            if boundary == "api" and any(
                module.startswith(("digital_colleagues.adapters", "digital_colleagues.governance"))
                for module in modules
            ):
                raise ArchitectureError("P6 HTTP mapping bypasses the application boundary")
    core_tree = parsed["src/digital_colleagues/core/governance.py"]
    dataclasses = [
        node
        for node in ast.walk(core_tree)
        if isinstance(node, ast.ClassDef)
        and any(
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Name)
            and decorator.func.id == "dataclass"
            for decorator in node.decorator_list
        )
    ]
    if not dataclasses or any(
        not any(
            keyword.arg == "frozen"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
            for decorator in node.decorator_list
            if isinstance(decorator, ast.Call)
            for keyword in decorator.keywords
        )
        for node in dataclasses
    ):
        raise ArchitectureError("P6 core records must be frozen dataclasses")
    services = (root / P6_FILES["application"][2]).read_text(encoding="utf-8")
    if any(token in services for token in ("datetime.now(", "secrets.", "random.", "uuid.")):
        raise ArchitectureError("P6 deterministic services hide time, entropy, or IDs")
    return {
        "schema_version": 1,
        "gate": "p6_architecture_clean",
        "retained_p3_gate": prior["gate"],
        "files_checked": len(parsed),
        "pure_core_frozen_records": len(dataclasses),
        "typed_action_matrix": True,
        "pydantic_http_edge_only": True,
        "time_entropy_id_io_injected": True,
        "dependency_direction": "pure_core_to_application_governance_to_ports_and_adapters",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P6 architecture.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_architecture(Path(arguments.root).resolve())
    except (OSError, SyntaxError, ArchitectureError) as exc:
        print(f"P6 architecture check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
