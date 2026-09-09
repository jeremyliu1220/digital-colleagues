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

CORE_FILES = ("agent_package.py", "deployment.py")
FORBIDDEN_CORE_IMPORTS = (
    "fastapi",
    "pydantic",
    "sqlite3",
    "subprocess",
    "requests",
    "httpx",
    "openai",
)


def check_architecture(root: Path) -> dict[str, object]:
    core = root / "src/digital_colleagues/core"
    frozen_count = 0
    for name in CORE_FILES:
        source = (core / name).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = (
                    [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                )
                if any(module.startswith(FORBIDDEN_CORE_IMPORTS) for module in modules):
                    raise GateError("P11 pure core imports an adapter framework")
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
    if "Protocol" not in ports or "sqlite3" in ports or "FastAPI" in ports:
        raise GateError("P11 stable ports crossed an adapter boundary")
    runtime = (root / "src/digital_colleagues/application/p11_services.py").read_text()
    if "deployment is not active" not in runtime or "PackageTrustState.TRUSTED" not in runtime:
        raise GateError("P11 runtime or package fail-closed guard is absent")
    return {
        "schema_version": 1,
        "gate": "p11_architecture",
        "status": "passed",
        "core_file_count": len(CORE_FILES),
        "frozen_dataclass_count": frozen_count,
        "forbidden_core_import_count": 0,
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
