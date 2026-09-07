# SPDX-License-Identifier: Apache-2.0

"""Validate canonical metadata and the unchanged 40-pair HTTP route inventory."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.p10_gate_support import (
    API_TITLE,
    BASE_COMMIT,
    DISPLAY_VERSION,
    MATURITY,
    PRODUCT_NAME,
    PYTHON_VERSION,
    GateError,
    emit_main,
    git,
)

API_FILES = (
    "src/digital_colleagues/api/app.py",
    "src/digital_colleagues/api/p4_app.py",
    "src/digital_colleagues/api/p5_app.py",
    "src/digital_colleagues/api/p6_app.py",
)


def route_inventory(source: str) -> set[tuple[str, str]]:
    tree = ast.parse(source)
    routes: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            method = decorator.func.attr.upper()
            if (
                method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}
                or not decorator.args
            ):
                continue
            path = decorator.args[0]
            if isinstance(path, ast.Constant) and isinstance(path.value, str):
                routes.add((method, path.value))
    return routes


def check_compatibility(root: Path) -> dict[str, object]:
    init = (root / "src/digital_colleagues/__init__.py").read_text(encoding="utf-8")
    expected_assignments = {
        "PRODUCT_NAME": PRODUCT_NAME,
        "API_TITLE": API_TITLE,
        "MATURITY": MATURITY,
        "__version__": PYTHON_VERSION,
        "DISPLAY_VERSION": DISPLAY_VERSION,
    }
    namespace: dict[str, object] = {}
    exec(compile(init, "<metadata>", "exec"), {"__builtins__": {}}, namespace)
    if any(namespace.get(key) != value for key, value in expected_assignments.items()):
        raise GateError("canonical_metadata_invalid")
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    package = (root / "studio/package.json").read_text(encoding="utf-8")
    if (
        f'version = "{PYTHON_VERSION}"' not in pyproject
        or f'"version": "{DISPLAY_VERSION}"' not in package
    ):
        raise GateError("package_version_mapping_invalid")
    current: set[tuple[str, str]] = set()
    baseline: set[tuple[str, str]] = set()
    for relative in API_FILES:
        source = (root / relative).read_text(encoding="utf-8")
        before = git(root, "show", f"{BASE_COMMIT}:{relative}")
        assert isinstance(before, str)
        current |= route_inventory(source)
        baseline |= route_inventory(before)
    if current != baseline or len(current) != 40 or any(path == "/api/v1" for _, path in current):
        raise GateError("route_inventory_drift")
    diff = str(
        git(
            root,
            "diff",
            "--unified=0",
            BASE_COMMIT,
            "HEAD",
            "--",
            "src/digital_colleagues/api/app.py",
            "src/digital_colleagues/api/p4_app.py",
            "src/digital_colleagues/local/runtime.py",
        )
    )
    changed_lines = [
        line[1:]
        for line in diff.splitlines()
        if line[:1] in {"+", "-"} and not line.startswith(("+++", "---"))
    ]
    permitted = re.compile(
        r"^(?:from digital_colleagues import API_TITLE, __version__|\s*(?:app = FastAPI\(title=API_TITLE, version=__version__\)|app\.title = API_TITLE|app\.version = __version__|app = FastAPI\(title=\"Digital Colleagues P[347].*|app\.title = \"Digital Colleagues P7.*|app\.version = \"0\.0\.0-p7\"))$"
    )
    if any(not permitted.fullmatch(line) for line in changed_lines):
        raise GateError("api_semantic_change_outside_metadata")
    compatibility = (root / "docs/p10/compatibility.md").read_text(encoding="utf-8")
    if (
        "37 route-method pairs" not in compatibility
        or "separate headless mapping" not in compatibility
    ):
        raise GateError("compatibility_document_inventory_invalid")
    return {
        "schema_version": 1,
        "gate": "p10_compatibility_clean",
        "product_name": PRODUCT_NAME,
        "python_version": PYTHON_VERSION,
        "display_version": DISPLAY_VERSION,
        "api_title": API_TITLE,
        "route_method_pair_count": 40,
        "composed_route_method_pair_count": 37,
        "route_drift_count": 0,
        "migration_008": False,
    }


def main(argv: list[str] | None = None) -> int:
    return emit_main(check_compatibility, argv, __doc__)


if __name__ == "__main__":
    raise SystemExit(main())
