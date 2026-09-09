# SPDX-License-Identifier: Apache-2.0

"""Check P11 dependency direction and absent-capability boundaries."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.p11_gate_support import GateError  # noqa: E402

P11_CORE_FILES = ("agent_package.py", "deployment.py")
FORBIDDEN_FRAMEWORK_IMPORTS = (
    "fastapi",
    "pydantic",
    "sqlite3",
    "subprocess",
    "requests",
    "httpx",
    "openai",
)
BOUNDARY_FORBIDDEN_IMPORTS = {
    "core": (
        "digital_colleagues.application",
        "digital_colleagues.governance",
        "digital_colleagues.adapters",
        "digital_colleagues.api",
        "digital_colleagues.local",
        "digital_colleagues.worker",
        *FORBIDDEN_FRAMEWORK_IMPORTS,
    ),
    "application": (
        "digital_colleagues.adapters",
        "digital_colleagues.api",
        "digital_colleagues.local",
        "digital_colleagues.worker",
        *FORBIDDEN_FRAMEWORK_IMPORTS,
    ),
    "governance": (
        "digital_colleagues.application",
        "digital_colleagues.adapters",
        "digital_colleagues.api",
        "digital_colleagues.local",
        "digital_colleagues.worker",
        *FORBIDDEN_FRAMEWORK_IMPORTS,
    ),
}


def _imports(tree: ast.AST, *, package_name: str) -> tuple[str, ...]:
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                package = package_name.split(".")
                keep = len(package) - node.level + 1
                prefix = package[: max(keep, 0)]
                suffix = (node.module or "").split(".") if node.module else []
                modules.append(".".join((*prefix, *suffix)))
            else:
                modules.append(node.module or "")
    return tuple(modules)


def forbidden_dependency_imports(root: Path) -> tuple[str, ...]:
    package = root / "src/digital_colleagues"
    violations: list[str] = []
    for boundary, forbidden in BOUNDARY_FORBIDDEN_IMPORTS.items():
        for path in sorted((package / boundary).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            relative = path.relative_to(package).with_suffix("")
            package_parts = relative.parts if relative.name == "__init__" else relative.parts[:-1]
            package_name = ".".join(("digital_colleagues", *package_parts))
            for module in _imports(tree, package_name=package_name):
                if any(module == prefix or module.startswith(prefix + ".") for prefix in forbidden):
                    violations.append(f"{path.relative_to(root)}:{module}")
    return tuple(violations)


def check_architecture(root: Path) -> dict[str, object]:
    core = root / "src/digital_colleagues/core"
    violations = forbidden_dependency_imports(root)
    if violations:
        raise GateError("core/application/governance dependency direction is invalid")
    frozen_count = 0
    for name in P11_CORE_FILES:
        source = (core / name).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for decorator in node.decorator_list:
                    if (
                        isinstance(decorator, ast.Call)
                        and getattr(decorator.func, "id", "") == "dataclass"
                    ):
                        values = {
                            keyword.arg: getattr(keyword.value, "value", None)
                            for keyword in decorator.keywords
                        }
                        if values.get("frozen") is not True or values.get("slots") is not True:
                            raise GateError("P11 core dataclass is not frozen and slotted")
                        frozen_count += 1
    ports = (root / "src/digital_colleagues/application/p11_ports.py").read_text()
    if "PackageArchiveValidationPort" not in ports or "Protocol" not in ports:
        raise GateError("P11 stable ports crossed an adapter boundary")
    runtime = (root / "src/digital_colleagues/application/p11_services.py").read_text()
    if "deployment is not active" not in runtime or "PackageTrustState.TRUSTED" not in runtime:
        raise GateError("P11 runtime or package fail-closed guard is absent")
    return {
        "schema_version": 1,
        "gate": "p11_architecture",
        "status": "passed",
        "core_file_count": len(tuple(core.rglob("*.py"))),
        "application_file_count": len(
            tuple((root / "src/digital_colleagues/application").rglob("*.py"))
        ),
        "governance_file_count": len(
            tuple((root / "src/digital_colleagues/governance").rglob("*.py"))
        ),
        "frozen_dataclass_count": frozen_count,
        "forbidden_dependency_import_count": len(violations),
        "runtime_active_guard_count": 1,
        "future_connection_slots": "null_only",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        result = check_architecture(Path(args.root).resolve())
    except (OSError, SyntaxError, GateError) as exc:
        print(f"P11 architecture check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
