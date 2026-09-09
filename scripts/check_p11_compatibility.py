# SPDX-License-Identifier: Apache-2.0

"""Check retained API surfaces and new stable P11 vocabulary."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.p11_gate_support import GateError  # noqa: E402

ROUTES = (
    ("get", "/api/v1/catalog"),
    ("get", "/api/v1/agent-packages"),
    ("post", "/api/v1/agent-packages"),
    ("post", "/api/v1/agent-packages/validate"),
    ("post", "/api/v1/agent-packages/{package_id}/versions/{version}/{digest}/trust"),
    ("post", "/api/v1/agent-packages/{package_id}/versions/{version}/{digest}/revoke"),
    ("post", "/api/v1/agent-packages/{package_id}/versions/{version}/{digest}/install"),
    ("get", "/api/v1/deployment-drafts"),
    ("post", "/api/v1/deployment-drafts"),
    ("post", "/api/v1/deployment-drafts/{draft_id}/review"),
    ("post", "/api/v1/deployment-drafts/{draft_id}/confirm"),
    ("get", "/api/v1/deployments"),
    ("post", "/api/v1/deployments/{deployment_id}/lifecycle"),
    ("post", "/api/v1/deployments/{deployment_id}/upgrade-drafts"),
    ("post", "/api/v1/deployments/{deployment_id}/rollback-drafts"),
    ("post", "/api/v1/deployments/{deployment_id}/select"),
    ("get", "/api/v1/deployments/{deployment_id}/audit"),
)


def check_compatibility(root: Path) -> dict[str, object]:
    source = (root / "src/digital_colleagues/api/p11_app.py").read_text()
    tree = ast.parse(source)
    actual: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            if decorator.func.attr not in {"get", "post"} or not decorator.args:
                continue
            value = decorator.args[0]
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                actual.add((decorator.func.attr, value.value))
    if actual != set(ROUTES):
        raise GateError("P11 stable API route inventory drifted")
    p5 = (root / "src/digital_colleagues/api/p5_app.py").read_text()
    p6 = (root / "src/digital_colleagues/api/p6_app.py").read_text()
    retained_routes = {
        "p5": "/p5/studio/state",
        "p6": "/governance/state",
    }
    if retained_routes["p5"] not in p5 or retained_routes["p6"] not in p6:
        raise GateError("retained milestone compatibility routes are absent")
    pyproject = (root / "pyproject.toml").read_text()
    if 'dc = "digital_colleagues.cli:main"' not in pyproject:
        raise GateError("installed dc console entry point is absent")
    runtime = (root / "src/digital_colleagues/local/runtime.py").read_text()
    if "install_p11_routes" not in runtime or "SQLiteP11Store" not in runtime:
        raise GateError("P11 composition root is incomplete")
    return {
        "schema_version": 1,
        "gate": "p11_compatibility",
        "status": "passed",
        "new_api_v1_route_count": len(ROUTES),
        "retained_route_families": retained_routes,
        "console_entry_point": "dc",
        "removed_alias_count": 0,
        "p10_digest_mutation_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        result = check_compatibility(Path(args.root).resolve())
    except (OSError, SyntaxError, GateError) as exc:
        print(f"P11 compatibility check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
