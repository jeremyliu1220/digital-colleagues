# SPDX-License-Identifier: Apache-2.0

"""Validate additive P4 dependency, authority, and injected-capability boundaries."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p3_architecture import check_architecture as check_p3_architecture

POLICY_VERSION = "p4-session-derived-authority-and-edge-isolation-v1"
AUTHORITY_FIELDS = {
    "tenant",
    "tenant_id",
    "namespace",
    "namespace_scope",
    "namespace_scope_id",
    "principal",
    "principal_id",
    "principal_kind",
    "role",
    "roles",
    "session_id",
}


class ArchitectureError(RuntimeError):
    """P4 architecture violates a fixed dependency or authority boundary."""


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _request_fields(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    fields: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(
            (isinstance(base, ast.Name) and base.id == "_StrictMutation") for base in node.bases
        ):
            continue
        fields.update(
            statement.target.id
            for statement in node.body
            if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
        )
    return fields


def check_architecture(root: Path) -> dict[str, object]:
    prior = check_p3_architecture(root)
    violations: list[str] = []
    for directory in ("core", "governance", "application"):
        for path in (root / "src/digital_colleagues" / directory).glob("*.py"):
            imports = _imports(path)
            if imports & {"fastapi", "pydantic", "sqlite3"}:
                violations.append("edge_or_storage_dependency")
            if directory == "application" and any(
                item.startswith("digital_colleagues.adapters") for item in imports
            ):
                violations.append("application_adapter_dependency")
    for path in (root / "src/digital_colleagues").rglob("*.py"):
        imports = _imports(path)
        if any(item.startswith("pydantic") for item in imports):
            relative = path.relative_to(root).as_posix()
            if not relative.startswith("src/digital_colleagues/api/"):
                violations.append("pydantic_outside_http_edge")
    fields = _request_fields(root / "src/digital_colleagues/api/p4_app.py")
    if fields & AUTHORITY_FIELDS:
        violations.append("caller_authority_field")
    services = (root / "src/digital_colleagues/application/p4_services.py").read_text(
        encoding="utf-8"
    )
    for required in ("ClockPort", "IdentifierPort", "SecretTokenPort", "RequestPrincipalContext"):
        if required not in services:
            violations.append("missing_injected_capability")
    if violations:
        raise ArchitectureError("P4 architecture policy found a violation")
    return {
        "schema_version": 1,
        "gate": "p4_architecture_clean",
        "policy_version": POLICY_VERSION,
        "p3_policy_version": prior["policy_version"],
        "dependency_violations": 0,
        "pydantic_edge_leaks": 0,
        "caller_authority_fields": 0,
        "injected_capability_violations": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P4 architecture boundaries.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_architecture(Path(arguments.root).resolve())
    except (OSError, SyntaxError, ArchitectureError) as exc:
        print(f"P4 architecture check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
