# SPDX-License-Identifier: Apache-2.0

"""Validate P5 dependency, authority, typed-policy, and determinism boundaries."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p4_architecture import check_architecture as check_p4_architecture

POLICY_VERSION = "p5-revisioned-colleague-policy-v1"
P5_MODULES = (
    "src/digital_colleagues/core/builder.py",
    "src/digital_colleagues/core/policy.py",
    "src/digital_colleagues/governance/policy.py",
    "src/digital_colleagues/application/p5_contracts.py",
    "src/digital_colleagues/application/p5_ports.py",
    "src/digital_colleagues/application/p5_services.py",
    "src/digital_colleagues/adapters/sqlite/p5_store.py",
    "src/digital_colleagues/api/p5_app.py",
)
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
    "canonical_digest",
    "issued_by",
    "effective_at",
    "created_at",
    "updated_at",
}


class ArchitectureError(RuntimeError):
    """P5 architecture violates a fixed dependency, authority, or policy boundary."""


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())


def _imports(tree: ast.AST) -> set[str]:
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def _strict_fields(tree: ast.Module) -> set[str]:
    fields: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(
            isinstance(base, ast.Name) and base.id == "_StrictMutation" for base in node.bases
        ):
            continue
        fields.update(
            statement.target.id
            for statement in node.body
            if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
        )
    return fields


def check_architecture(root: Path) -> dict[str, object]:
    prior = check_p4_architecture(root)
    missing = [relative for relative in P5_MODULES if not (root / relative).is_file()]
    if missing:
        raise ArchitectureError("a required P5 architecture module is missing")
    violations: list[str] = []
    inspected = 0
    for relative in P5_MODULES:
        path = root / relative
        tree = _tree(path)
        imports = _imports(tree)
        inspected += 1
        if "/core/" in relative or "/governance/" in relative:
            if imports & {"fastapi", "pydantic", "sqlite3"}:
                violations.append("pure_policy_edge_dependency")
            if any(
                item.startswith(
                    (
                        "digital_colleagues.adapters",
                        "digital_colleagues.api",
                        "digital_colleagues.application",
                    )
                )
                for item in imports
            ):
                violations.append("pure_policy_inward_dependency")
        if "/application/" in relative:
            if imports & {"fastapi", "pydantic", "sqlite3"}:
                violations.append("application_edge_dependency")
            if any(item.startswith("digital_colleagues.adapters") for item in imports):
                violations.append("application_adapter_dependency")
        if relative.endswith("p5_services.py"):
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id in {"eval", "exec", "getattr", "setattr", "compile"}:
                        violations.append("dynamic_policy_interpretation")
                if isinstance(node, ast.Attribute) and node.attr in {"now", "utcnow", "random"}:
                    if isinstance(node.value, ast.Name) and node.value.id in {
                        "datetime",
                        "random",
                        "secrets",
                    }:
                        violations.append("ambient_determinism_source")
    api_tree = _tree(root / "src/digital_colleagues/api/p5_app.py")
    if _strict_fields(api_tree) & AUTHORITY_FIELDS:
        violations.append("caller_authority_field")
    for path in (root / "src/digital_colleagues").rglob("*.py"):
        if any(item.startswith("pydantic") for item in _imports(_tree(path))):
            if not path.relative_to(root).as_posix().startswith("src/digital_colleagues/api/"):
                violations.append("pydantic_outside_http_edge")
    service = (root / "src/digital_colleagues/application/p5_services.py").read_text(
        encoding="utf-8"
    )
    store = (root / "src/digital_colleagues/adapters/sqlite/p5_store.py").read_text(
        encoding="utf-8"
    )
    for required in (
        "ClockPort",
        "IdentifierPort",
        "P5PersistencePort",
        "expected_canonical_digest",
        "PolicyGovernedIntelligence",
        "P5DispatchAuthorizer",
    ):
        if required not in service:
            violations.append("missing_injected_or_exact_binding")
    for required in (
        "with self._transaction()",
        "base_profile_revision",
        "base_mandate_revision",
        "base_policy_revision",
    ):
        if required not in store:
            violations.append("missing_atomic_cas_binding")
    if violations:
        raise ArchitectureError("P5 architecture policy found a violation")
    return {
        "schema_version": 1,
        "gate": "p5_architecture_clean",
        "policy_version": POLICY_VERSION,
        "p4_policy_version": prior["policy_version"],
        "p5_module_count": inspected,
        "dependency_violations": 0,
        "caller_authority_fields": 0,
        "dynamic_policy_interpretation": 0,
        "ambient_determinism_sources": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P5 architecture boundaries.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_architecture(Path(arguments.root).resolve())
    except (OSError, SyntaxError, ArchitectureError) as exc:
        print(f"P5 architecture check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
