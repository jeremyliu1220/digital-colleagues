# SPDX-License-Identifier: Apache-2.0

"""Fail closed on P3 dependency direction, edge leakage, and hidden nondeterminism."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

POLICY_VERSION = "p3-dependency-determinism-allowlist-v1"
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
STDLIB = frozenset(
    {
        "__future__",
        "argparse",
        "ast",
        "collections",
        "contextlib",
        "dataclasses",
        "datetime",
        "enum",
        "hashlib",
        "json",
        "math",
        "pathlib",
        "re",
        "sqlite3",
        "sys",
        "threading",
        "typing",
    }
)
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
        "poplib",
        "random",
        "requests",
        "secrets",
        "shutil",
        "smtplib",
        "socket",
        "subprocess",
        "tempfile",
        "time",
        "urllib",
        "uuid",
    }
)
FORBIDDEN_CALLS = frozenset(
    {
        "datetime.date.today",
        "datetime.datetime.now",
        "datetime.datetime.utcnow",
        "datetime.now",
        "datetime.utcnow",
        "open",
        "time.monotonic",
        "time.perf_counter",
        "time.time",
        "uuid.uuid1",
        "uuid.uuid4",
    }
)
EDGE_TYPES = frozenset({"fastapi", "pydantic", "sqlalchemy", "sqlmodel"})


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
    return aliases


def _resolve(node: ast.expr, aliases: dict[str, str]) -> str | None:
    name = _qualified_name(node)
    if name is None:
        return None
    root, separator, suffix = name.partition(".")
    resolved = aliases.get(root, root)
    return resolved + (separator + suffix if separator else "")


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
        "alias_resolved_unsafe_calls": 0,
        "stable_port_leaks": 0,
    }
    for boundary, relative_root in BOUNDARIES.items():
        for document in sorted((root / relative_root).rglob("*.py")):
            relative = document.relative_to(root).as_posix()
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
                        import_root in STDLIB
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
                    root_name = name.split(".", 1)[0] if name else ""
                    if name in FORBIDDEN_CALLS or root_name in FORBIDDEN_CAPABILITY_ROOTS:
                        counts["nondeterministic_calls"] += 1
                        if name != raw:
                            counts["alias_resolved_unsafe_calls"] += 1
                        violations.append(f"{relative}:hidden_nondeterministic_call")
            if boundary == "application" and document.name == "ports.py":
                text = document.read_text(encoding="utf-8").lower()
                leaked = tuple(
                    value for value in EDGE_TYPES | {"openai", "requests"} if value in text
                )
                if leaked:
                    counts["stable_port_leaks"] += len(leaked)
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
