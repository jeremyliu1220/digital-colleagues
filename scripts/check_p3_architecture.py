# SPDX-License-Identifier: Apache-2.0

"""Fail closed on P3 dependency direction, edge leakage, and hidden nondeterminism."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

POLICY_VERSION = "p3-boundary-specific-determinism-allowlist-v6"
P5_OWNED_FILES = frozenset(
    {
        "src/digital_colleagues/adapters/sqlite/p5_store.py",
        "src/digital_colleagues/api/p5_app.py",
        "src/digital_colleagues/application/p5_contracts.py",
        "src/digital_colleagues/application/p5_ports.py",
        "src/digital_colleagues/application/p5_services.py",
        "src/digital_colleagues/core/builder.py",
        "src/digital_colleagues/core/policy.py",
        "src/digital_colleagues/governance/policy.py",
    }
)
P6_OWNED_FILES = frozenset(
    {
        "src/digital_colleagues/adapters/sqlite/p6_store.py",
        "src/digital_colleagues/api/p6_app.py",
        "src/digital_colleagues/application/p6_contracts.py",
        "src/digital_colleagues/application/p6_ports.py",
        "src/digital_colleagues/application/p6_services.py",
        "src/digital_colleagues/core/governance.py",
        "src/digital_colleagues/governance/rbac.py",
    }
)
BOUNDARIES = {
    "core": "src/digital_colleagues/core",
    "governance": "src/digital_colleagues/governance",
    "application": "src/digital_colleagues/application",
    "sqlite_adapter": "src/digital_colleagues/adapters/sqlite",
    "intelligence_adapter": "src/digital_colleagues/adapters/intelligence",
    "channel_adapter": "src/digital_colleagues/adapters/channel",
    "system_adapter": "src/digital_colleagues/adapters/system",
    "api": "src/digital_colleagues/api",
    "worker": "src/digital_colleagues/worker",
}
STDLIB_ALLOWED = {
    "core": frozenset(
        {
            "__future__",
            "collections",
            "dataclasses",
            "datetime",
            "enum",
            "hashlib",
            "json",
            "math",
            "re",
            "typing",
        }
    ),
    "governance": frozenset({"__future__", "dataclasses", "datetime"}),
    "application": frozenset({"__future__", "dataclasses", "datetime", "enum", "typing"}),
    "sqlite_adapter": frozenset(
        {
            "__future__",
            "collections",
            "contextlib",
            "dataclasses",
            "datetime",
            "enum",
            "hashlib",
            "json",
            "pathlib",
            "sqlite3",
            "threading",
            "typing",
        }
    ),
    "intelligence_adapter": frozenset({"__future__", "dataclasses"}),
    "channel_adapter": frozenset({"__future__", "dataclasses", "hashlib", "json"}),
    "system_adapter": frozenset({"__future__", "dataclasses", "datetime", "hashlib"}),
    "api": frozenset({"__future__", "collections", "typing"}),
    "worker": frozenset({"__future__", "dataclasses"}),
}
INTERNAL_ALLOWED = {
    "core": ("digital_colleagues.core",),
    "governance": ("digital_colleagues.core", "digital_colleagues.governance"),
    "application": (
        "digital_colleagues.application",
        "digital_colleagues.core",
        "digital_colleagues.governance",
    ),
    "sqlite_adapter": (
        "digital_colleagues.adapters.sqlite",
        "digital_colleagues.application",
        "digital_colleagues.core",
        "digital_colleagues.governance",
    ),
    "intelligence_adapter": (
        "digital_colleagues.adapters.intelligence",
        "digital_colleagues.application",
        "digital_colleagues.core",
    ),
    "channel_adapter": (
        "digital_colleagues.adapters.channel",
        "digital_colleagues.application",
        "digital_colleagues.core",
    ),
    "system_adapter": (
        "digital_colleagues.adapters.system",
        "digital_colleagues.application",
        "digital_colleagues.core",
    ),
    "api": (
        "digital_colleagues.api",
        "digital_colleagues.application",
        "digital_colleagues.core",
    ),
    "worker": (
        "digital_colleagues.worker",
        "digital_colleagues.application",
        "digital_colleagues.core",
    ),
}
THIRD_PARTY_ALLOWED = {"api": frozenset({"fastapi", "pydantic"})}
DETERMINISTIC_BOUNDARIES = frozenset(
    {
        "core",
        "governance",
        "application",
        "intelligence_adapter",
        "channel_adapter",
        "system_adapter",
    }
)
FORBIDDEN_CAPABILITY_ROOTS = frozenset(
    {
        "aiohttp",
        "asyncio",
        "ftplib",
        "glob",
        "http",
        "imaplib",
        "multiprocessing",
        "openai",
        "os",
        "pathlib",
        "poplib",
        "random",
        "requests",
        "secrets",
        "shutil",
        "smtplib",
        "socket",
        "sqlite3",
        "subprocess",
        "tempfile",
        "time",
        "urllib",
        "uuid",
    }
)
FORBIDDEN_BUILTIN_CALLS = frozenset(
    {
        "__import__",
        "compile",
        "eval",
        "exec",
        "input",
        "open",
    }
)
FORBIDDEN_CALLS = frozenset(
    {
        *(f"builtins.{name}" for name in FORBIDDEN_BUILTIN_CALLS),
        *FORBIDDEN_BUILTIN_CALLS,
        "datetime.date.today",
        "datetime.datetime.now",
        "datetime.datetime.utcnow",
        "datetime.now",
        "datetime.utcnow",
        "time.monotonic",
        "time.monotonic_ns",
        "time.perf_counter",
        "time.perf_counter_ns",
        "time.process_time",
        "time.process_time_ns",
        "time.time",
        "time.time_ns",
        "uuid.uuid1",
        "uuid.uuid4",
    }
)
GETATTR_CALLS = frozenset({"builtins.getattr", "getattr"})
REFLECTION_CALLS = frozenset(
    {
        "builtins.globals",
        "builtins.locals",
        "builtins.vars",
        "globals",
        "locals",
        "object.__getattribute__",
        "type.__getattribute__",
        "vars",
    }
)
ALLOWED_DUNDER_ATTRIBUTES = frozenset({"object.__setattr__"})
FORBIDDEN_REFLECTION_NAMES = frozenset({"__builtins__"})
REFLECTION_NAMESPACE = "<dynamic-reflection-namespace>"
STATIC_GETATTR_ROOTS = frozenset(
    {
        "builtins",
        *(root for allowed in STDLIB_ALLOWED.values() for root in allowed),
        *FORBIDDEN_CAPABILITY_ROOTS,
    }
)
EDGE_TYPES = frozenset({"fastapi", "pydantic", "sqlalchemy", "sqlmodel"})
STABLE_PORT_FORBIDDEN_TOKENS = frozenset(
    {
        "fastapi",
        "openai",
        "orm.session",
        "pathlib.path",
        "pydantic",
        "requests",
        "sqlalchemy",
        "sqlite3.connection",
        "sqlmodel",
    }
)
STABLE_PORT_FORBIDDEN_TYPE_NAMES = frozenset(
    {"BaseModel", "Connection", "FastAPI", "Path", "Session"}
)


class ArchitectureError(RuntimeError):
    """A P3 source boundary is incomplete or violated."""


def _qualified_name(node: ast.expr) -> str | None:
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return None


def _aliases(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                aliases[item.asname or item.name.split(".", 1)[0]] = item.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for item in node.names:
                if item.name != "*":
                    aliases[item.asname or item.name] = f"{node.module}.{item.name}"
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            targets: tuple[ast.expr, ...] = ()
            value: ast.expr | None = None
            if isinstance(node, ast.Assign):
                targets = tuple(node.targets)
                value = node.value
            elif isinstance(node, ast.AnnAssign):
                targets = (node.target,)
                value = node.value
            if value is None or not all(isinstance(target, ast.Name) for target in targets):
                continue
            resolved = _resolve(value, aliases)
            if resolved is None:
                continue
            for target in targets:
                assert isinstance(target, ast.Name)
                if target.id not in aliases:
                    aliases[target.id] = resolved
                    changed = True
    return aliases


def _resolve(node: ast.expr, aliases: dict[str, str]) -> str | None:
    name = _qualified_name(node)
    if name is not None:
        root, separator, suffix = name.partition(".")
        resolved = aliases.get(root, "builtins" if root == "__builtins__" else root)
        return resolved + (separator + suffix if separator else "")
    if isinstance(node, ast.Call):
        return (
            _literal_getattr_reference(node, aliases)
            or _literal_getattribute_reference(node, aliases)
            or _reflection_mapping_reference(node, aliases)
        )
    if isinstance(node, ast.Subscript):
        return _literal_subscript_reference(node, aliases)
    return None


def _literal_attribute(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.isidentifier():
        return node.value
    return None


def _static_attribute_reference(
    base_node: ast.expr, attribute_node: ast.expr, aliases: dict[str, str]
) -> str | None:
    attribute = _literal_attribute(attribute_node)
    if attribute is None or attribute.startswith("__"):
        return None
    base = _resolve(base_node, aliases)
    if base is None or base.split(".", 1)[0] not in STATIC_GETATTR_ROOTS:
        return None
    return f"{base}.{attribute}"


def _literal_getattr_reference(node: ast.Call, aliases: dict[str, str]) -> str | None:
    callee = _resolve(node.func, aliases)
    if callee not in GETATTR_CALLS or len(node.args) != 2 or node.keywords:
        return None
    return _static_attribute_reference(node.args[0], node.args[1], aliases)


def _literal_getattribute_reference(node: ast.Call, aliases: dict[str, str]) -> str | None:
    callee = _resolve(node.func, aliases)
    if callee in {"object.__getattribute__", "type.__getattribute__"}:
        if len(node.args) != 2 or node.keywords:
            return None
        return _static_attribute_reference(node.args[0], node.args[1], aliases)
    if callee is None or not callee.endswith(".__getattribute__"):
        return None
    if len(node.args) != 1 or node.keywords:
        return None
    attribute = _literal_attribute(node.args[0])
    if attribute is None or attribute.startswith("__"):
        return None
    return f"{callee.removesuffix('.__getattribute__')}.{attribute}"


def _reflection_mapping_reference(node: ast.Call, aliases: dict[str, str]) -> str | None:
    callee = _resolve(node.func, aliases)
    if callee in {"globals", "builtins.globals", "locals", "builtins.locals"}:
        return REFLECTION_NAMESPACE
    if callee not in {"vars", "builtins.vars"}:
        return None
    if len(node.args) != 1 or node.keywords:
        return REFLECTION_NAMESPACE
    base = _resolve(node.args[0], aliases)
    if base is None:
        return REFLECTION_NAMESPACE
    return f"{base}.__dict__"


def _literal_subscript_reference(node: ast.Subscript, aliases: dict[str, str]) -> str | None:
    key = _literal_attribute(node.slice)
    if key is None:
        return None
    base = _resolve(node.value, aliases)
    if base is None:
        return None
    if base == "builtins" or base.endswith(".__dict__"):
        namespace = base.removesuffix(".__dict__")
        return f"{namespace}.{key}"
    if base == REFLECTION_NAMESPACE or base.startswith(REFLECTION_NAMESPACE + "."):
        if key == "__builtins__":
            return "builtins"
        return f"{base}.{key}"
    return None


def _is_forbidden_reference(name: str | None) -> bool:
    if name is None:
        return False
    return name in FORBIDDEN_CALLS or name.split(".", 1)[0] in FORBIDDEN_CAPABILITY_ROOTS


def _is_dunder_attribute(attribute: str) -> bool:
    return len(attribute) > 4 and attribute.startswith("__") and attribute.endswith("__")


def _is_reflection_reference(name: str | None) -> bool:
    if name is None:
        return False
    return (
        name == REFLECTION_NAMESPACE
        or name.startswith(REFLECTION_NAMESPACE + ".")
        or (
            name not in ALLOWED_DUNDER_ATTRIBUTES
            and any(_is_dunder_attribute(part) for part in name.split("."))
        )
    )


def _internal_allowed(boundary: str, module: str) -> bool:
    return any(
        module == prefix or module.startswith(prefix + ".") for prefix in INTERNAL_ALLOWED[boundary]
    )


def check_architecture(root: Path) -> dict[str, object]:
    for relative in BOUNDARIES.values():
        if not (root / relative).is_dir():
            raise ArchitectureError("a required P3 source boundary is missing")
    violations: list[str] = []
    counts = {
        "files_checked": 0,
        "unapproved_imports": 0,
        "dependency_violations": 0,
        "edge_type_leaks": 0,
        "nondeterministic_imports": 0,
        "nondeterministic_calls": 0,
        "dynamic_capability_calls": 0,
        "reflection_capability_accesses": 0,
        "alias_resolved_unsafe_calls": 0,
        "stable_port_leaks": 0,
    }
    for boundary, relative_root in BOUNDARIES.items():
        for document in sorted((root / relative_root).rglob("*.py")):
            relative = document.relative_to(root).as_posix()
            if relative in P5_OWNED_FILES or relative in P6_OWNED_FILES:
                continue
            counts["files_checked"] += 1
            try:
                tree = ast.parse(document.read_text(encoding="utf-8"), filename=relative)
            except (OSError, UnicodeError, SyntaxError) as exc:
                raise ArchitectureError("a P3 source file is unreadable or invalid") from exc
            aliases = _aliases(tree)
            for node in ast.walk(tree):
                modules: tuple[str, ...] = ()
                if isinstance(node, ast.Import):
                    modules = tuple(item.name for item in node.names)
                elif isinstance(node, ast.ImportFrom):
                    if node.level != 0 or node.module is None:
                        counts["dependency_violations"] += 1
                        violations.append(f"{relative}:relative_or_unresolved_import")
                    else:
                        modules = (node.module,)
                        if any(item.name == "*" for item in node.names):
                            counts["unapproved_imports"] += 1
                            violations.append(f"{relative}:wildcard_import")
                for module in modules:
                    import_root = module.split(".", 1)[0]
                    allowed = (
                        import_root in STDLIB_ALLOWED[boundary]
                        or _internal_allowed(boundary, module)
                        or import_root in THIRD_PARTY_ALLOWED.get(boundary, frozenset())
                    )
                    if not allowed:
                        counts["unapproved_imports"] += 1
                        violations.append(f"{relative}:unapproved_import")
                    if import_root == "digital_colleagues" and not _internal_allowed(
                        boundary, module
                    ):
                        counts["dependency_violations"] += 1
                        violations.append(f"{relative}:outward_dependency")
                    if import_root in EDGE_TYPES and boundary != "api":
                        counts["edge_type_leaks"] += 1
                        violations.append(f"{relative}:edge_type_leak")
                    if (
                        boundary in DETERMINISTIC_BOUNDARIES
                        and import_root in FORBIDDEN_CAPABILITY_ROOTS
                    ):
                        counts["nondeterministic_imports"] += 1
                        violations.append(f"{relative}:hidden_capability_import")
                if isinstance(node, ast.Call) and boundary in DETERMINISTIC_BOUNDARIES:
                    raw = _qualified_name(node.func)
                    name = _resolve(node.func, aliases)
                    if _is_forbidden_reference(name):
                        counts["nondeterministic_calls"] += 1
                        if name != raw:
                            counts["alias_resolved_unsafe_calls"] += 1
                        violations.append(f"{relative}:hidden_nondeterministic_call")
                    if name in GETATTR_CALLS:
                        reference = _literal_getattr_reference(node, aliases)
                        if reference is None or _is_forbidden_reference(reference):
                            counts["dynamic_capability_calls"] += 1
                            if name != raw or reference is not None:
                                counts["alias_resolved_unsafe_calls"] += 1
                            violation = (
                                "unresolved_dynamic_getattr"
                                if reference is None
                                else "hidden_dynamic_capability"
                            )
                            violations.append(f"{relative}:{violation}")
                    if name in REFLECTION_CALLS:
                        counts["reflection_capability_accesses"] += 1
                        if name != raw:
                            counts["alias_resolved_unsafe_calls"] += 1
                        violations.append(f"{relative}:hidden_reflection_entry")
                if isinstance(node, ast.Attribute) and boundary in DETERMINISTIC_BOUNDARIES:
                    reference = _resolve(node, aliases)
                    if (
                        _is_dunder_attribute(node.attr)
                        and reference not in ALLOWED_DUNDER_ATTRIBUTES
                    ) or _is_reflection_reference(reference):
                        counts["reflection_capability_accesses"] += 1
                        violations.append(f"{relative}:hidden_reflection_attribute")
                if (
                    isinstance(node, ast.Name)
                    and boundary in DETERMINISTIC_BOUNDARIES
                    and node.id in FORBIDDEN_REFLECTION_NAMES
                ):
                    counts["reflection_capability_accesses"] += 1
                    violations.append(f"{relative}:hidden_builtins_namespace")
                if isinstance(node, ast.Subscript) and boundary in DETERMINISTIC_BOUNDARIES:
                    reference = _resolve(node, aliases)
                    base = _resolve(node.value, aliases)
                    if (
                        base == "builtins"
                        or _is_reflection_reference(base)
                        or _is_reflection_reference(reference)
                        or _is_forbidden_reference(reference)
                    ):
                        counts["reflection_capability_accesses"] += 1
                        if reference is not None:
                            counts["alias_resolved_unsafe_calls"] += 1
                        violations.append(f"{relative}:hidden_reflection_subscript")
            if boundary == "application" and document.name == "ports.py":
                text = document.read_text(encoding="utf-8").lower()
                leaked = tuple(value for value in STABLE_PORT_FORBIDDEN_TOKENS if value in text)
                leaked_types = {
                    node.id
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Name) and node.id in STABLE_PORT_FORBIDDEN_TYPE_NAMES
                }
                if leaked or leaked_types:
                    counts["stable_port_leaks"] += len(leaked) + len(leaked_types)
                    violations.append(f"{relative}:stable_port_concrete_type")
    if violations:
        raise ArchitectureError("; ".join(sorted(set(violations))))
    return {
        "schema_version": 1,
        "gate": "p3_architecture_clean",
        "policy_version": POLICY_VERSION,
        **counts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the P3 dependency architecture.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_architecture(Path(arguments.root))
    except ArchitectureError as exc:
        print(f"P3 architecture check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
