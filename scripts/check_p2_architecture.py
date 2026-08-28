# SPDX-License-Identifier: Apache-2.0

"""Fail closed on P2 dependency, framework, I/O, and nondeterminism violations."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

FORBIDDEN_IMPORT_ROOTS = {
    "fastapi",
    "pydantic",
    "sqlite3",
    "sqlalchemy",
    "django",
    "flask",
    "openai",
    "langgraph",
    "temporalio",
    "dbos",
    "slack_sdk",
    "telegram",
}
FORBIDDEN_DETERMINISTIC_IMPORT_ROOTS = {
    "http",
    "os",
    "pathlib",
    "random",
    "secrets",
    "socket",
    "subprocess",
    "time",
    "urllib",
}
FORBIDDEN_PACKAGE_PREFIXES = (
    "digital_colleagues.application",
    "digital_colleagues.adapters",
    "digital_colleagues.api",
    "digital_colleagues.worker",
)
FORBIDDEN_CALLS = {
    "datetime.now",
    "datetime.utcnow",
    "date.today",
    "time.time",
    "time.monotonic",
    "os.getenv",
    "os.putenv",
    "open",
}
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

    for source_root in source_roots:
        boundary = source_root.name
        for document in sorted(source_root.rglob("*.py")):
            relative = document.relative_to(root).as_posix()
            files_checked += 1
            try:
                tree = ast.parse(document.read_text(encoding="utf-8"), filename=relative)
            except (OSError, UnicodeError, SyntaxError) as exc:
                raise ArchitectureError("a P2 source file is unreadable or invalid") from exc
            for node in ast.walk(tree):
                imported: tuple[str, ...] = ()
                if isinstance(node, ast.Import):
                    imported = tuple(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module is not None:
                    imported = (node.module,)
                for module in imported:
                    root_name = module.split(".", maxsplit=1)[0]
                    if root_name in FORBIDDEN_IMPORT_ROOTS:
                        forbidden_imports += 1
                        violations.append(f"{relative}:forbidden_import")
                    if root_name in FORBIDDEN_DETERMINISTIC_IMPORT_ROOTS:
                        forbidden_io_imports += 1
                        violations.append(f"{relative}:forbidden_deterministic_import")
                    if module.startswith(FORBIDDEN_PACKAGE_PREFIXES):
                        dependency_violations += 1
                        violations.append(f"{relative}:outward_dependency")
                    if boundary == "core" and module.startswith("digital_colleagues.governance"):
                        dependency_violations += 1
                        violations.append(f"{relative}:reverse_governance_dependency")
                if isinstance(node, ast.Call):
                    name = _qualified_name(node.func)
                    if name in FORBIDDEN_CALLS or (
                        name is not None
                        and name.startswith(("random.", "secrets.", "socket.", "subprocess."))
                    ):
                        nondeterministic_calls += 1
                        violations.append(f"{relative}:forbidden_deterministic_call")
                if isinstance(node, ast.Subscript):
                    name = _qualified_name(node.value)
                    if name == "os.environ":
                        nondeterministic_calls += 1
                        violations.append(f"{relative}:environment_read")

    present_p3_paths = sorted(path for path in FORBIDDEN_P3_PATHS if (root / path).exists())
    if present_p3_paths:
        violations.extend(f"{path}:p3_path_present" for path in present_p3_paths)
    if violations:
        raise ArchitectureError("P2 architecture violations: " + ", ".join(sorted(violations)))
    return {
        "schema_version": 1,
        "gate": "p2_architecture_clean",
        "files_checked": files_checked,
        "forbidden_imports": forbidden_imports,
        "forbidden_io_imports": forbidden_io_imports,
        "dependency_violations": dependency_violations,
        "nondeterministic_calls": nondeterministic_calls,
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
