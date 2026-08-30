# SPDX-License-Identifier: Apache-2.0

"""Fail closed on P2 dependency, capability, I/O, and nondeterminism violations."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

POLICY_VERSION = "p2-stdlib-internal-allowlist-v1"
ALLOWED_STDLIB_IMPORT_ROOTS = frozenset(
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
)
ALLOWED_INTERNAL_PREFIXES = {
    "core": ("digital_colleagues.core",),
    "governance": (
        "digital_colleagues.core",
        "digital_colleagues.governance",
    ),
}
FORBIDDEN_CAPABILITY_IMPORT_ROOTS = frozenset(
    {
        "aiohttp",
        "asyncio",
        "ctypes",
        "dbm",
        "fcntl",
        "ftplib",
        "glob",
        "http",
        "imaplib",
        "io",
        "multiprocessing",
        "openai",
        "os",
        "pathlib",
        "poplib",
        "random",
        "requests",
        "secrets",
        "shutil",
        "signal",
        "smtplib",
        "socket",
        "sqlite3",
        "subprocess",
        "tempfile",
        "threading",
        "time",
        "urllib",
        "uuid",
    }
)
FORBIDDEN_WALL_CLOCK_CALLS = frozenset(
    {
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
FORBIDDEN_P3_PATHS = {
    "compose.yaml",
    "docker-compose.yml",
    "migrations",
    "src/digital_colleagues/adapters",
    "src/digital_colleagues/api",
    "src/digital_colleagues/application",
    "src/digital_colleagues/worker",
}


class ArchitectureError(RuntimeError):
    """A sanitized P2 architecture validation failure."""


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


def _import_aliases(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for imported in node.names:
                local_name = imported.asname or imported.name.split(".", maxsplit=1)[0]
                aliases[local_name] = imported.name if imported.asname else local_name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
            for imported in node.names:
                if imported.name == "*":
                    continue
                aliases[imported.asname or imported.name] = f"{node.module}.{imported.name}"
    return aliases


def _resolved_name(node: ast.expr, aliases: dict[str, str]) -> str | None:
    name = _qualified_name(node)
    if name is None:
        return None
    root, separator, suffix = name.partition(".")
    canonical_root = aliases.get(root, root)
    return canonical_root + (separator + suffix if separator else "")


def _module_is_allowed(boundary: str, module: str) -> bool:
    root_name = module.split(".", maxsplit=1)[0]
    if root_name in ALLOWED_STDLIB_IMPORT_ROOTS:
        return True
    return any(
        module == prefix or module.startswith(prefix + ".")
        for prefix in ALLOWED_INTERNAL_PREFIXES[boundary]
    )


def _is_capability_call(name: str) -> bool:
    root_name = name.split(".", maxsplit=1)[0]
    return root_name in FORBIDDEN_CAPABILITY_IMPORT_ROOTS


def check_architecture(root: Path) -> dict[str, object]:
    source_roots = (
        root / "src/digital_colleagues/core",
        root / "src/digital_colleagues/governance",
    )
    if any(not path.is_dir() for path in source_roots):
        raise ArchitectureError("required P2 source boundary is unavailable")
    violations: list[str] = []
    files_checked = 0
    forbidden_imports = 0
    forbidden_io_imports = 0
    dependency_violations = 0
    nondeterministic_calls = 0
    unapproved_imports = 0
    alias_resolved_unsafe_calls = 0

    for source_root in source_roots:
        boundary = source_root.name
        for document in sorted(source_root.rglob("*.py")):
            relative = document.relative_to(root).as_posix()
            files_checked += 1
            try:
                tree = ast.parse(document.read_text(encoding="utf-8"), filename=relative)
            except (OSError, UnicodeError, SyntaxError) as exc:
                raise ArchitectureError("a P2 source file is unreadable or invalid") from exc
            aliases = _import_aliases(tree)
            for node in ast.walk(tree):
                imported: tuple[str, ...] = ()
                if isinstance(node, ast.Import):
                    imported = tuple(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    if node.level != 0 or node.module is None:
                        dependency_violations += 1
                        violations.append(f"{relative}:unresolved_relative_import")
                    else:
                        imported = (node.module,)
                        if any(imported_name.name == "*" for imported_name in node.names):
                            forbidden_imports += 1
                            unapproved_imports += 1
                            violations.append(f"{relative}:wildcard_import")
                for module in imported:
                    root_name = module.split(".", maxsplit=1)[0]
                    if not _module_is_allowed(boundary, module):
                        forbidden_imports += 1
                        unapproved_imports += 1
                        violations.append(f"{relative}:unapproved_import")
                    if root_name in FORBIDDEN_CAPABILITY_IMPORT_ROOTS:
                        forbidden_io_imports += 1
                        violations.append(f"{relative}:forbidden_capability_import")
                    if root_name == "digital_colleagues" and not any(
                        module == prefix or module.startswith(prefix + ".")
                        for prefix in ALLOWED_INTERNAL_PREFIXES[boundary]
                    ):
                        dependency_violations += 1
                        violation = (
                            "reverse_governance_dependency"
                            if boundary == "core"
                            and (
                                module == "digital_colleagues.governance"
                                or module.startswith("digital_colleagues.governance.")
                            )
                            else "outward_dependency"
                        )
                        violations.append(f"{relative}:{violation}")
                if isinstance(node, ast.Call):
                    raw_name = _qualified_name(node.func)
                    name = _resolved_name(node.func, aliases)
                    forbidden_call = (
                        name in FORBIDDEN_WALL_CLOCK_CALLS
                        or name in FORBIDDEN_BUILTIN_CALLS
                        or (name is not None and _is_capability_call(name))
                    )
                    if forbidden_call:
                        nondeterministic_calls += 1
                        if name != raw_name:
                            alias_resolved_unsafe_calls += 1
                        violations.append(f"{relative}:forbidden_deterministic_call")
                if isinstance(node, ast.Subscript):
                    raw_name = _qualified_name(node.value)
                    name = _resolved_name(node.value, aliases)
                    if name == "os.environ":
                        nondeterministic_calls += 1
                        if name != raw_name:
                            alias_resolved_unsafe_calls += 1
                        violations.append(f"{relative}:environment_read")

    present_p3_paths = sorted(path for path in FORBIDDEN_P3_PATHS if (root / path).exists())
    if present_p3_paths:
        violations.extend(f"{path}:p3_path_present" for path in present_p3_paths)
    if violations:
        raise ArchitectureError("P2 architecture violations: " + ", ".join(sorted(violations)))
    return {
        "schema_version": 2,
        "gate": "p2_architecture_clean",
        "policy_version": POLICY_VERSION,
        "files_checked": files_checked,
        "allowed_stdlib_import_root_count": len(ALLOWED_STDLIB_IMPORT_ROOTS),
        "forbidden_imports": forbidden_imports,
        "unapproved_imports": unapproved_imports,
        "forbidden_io_imports": forbidden_io_imports,
        "dependency_violations": dependency_violations,
        "nondeterministic_calls": nondeterministic_calls,
        "alias_resolved_unsafe_calls": alias_resolved_unsafe_calls,
        "p3_paths_present": len(present_p3_paths),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the P2 pure architecture boundary.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_architecture(Path(arguments.root))
    except ArchitectureError as exc:
        print(f"P2 architecture check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
