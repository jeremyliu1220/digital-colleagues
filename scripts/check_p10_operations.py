# SPDX-License-Identifier: Apache-2.0

"""Validate the finite P10 operator CLI and P8-compatible operation binding."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_p10_candidate import build_bundle
from scripts.p10_gate_support import GateError, emit_main

COMMANDS = {
    "doctor",
    "quickstart",
    "up",
    "down",
    "status",
    "backup",
    "restore",
    "update",
    "uninstall",
}


def check_operations(root: Path) -> dict[str, object]:
    launcher = (root / "dc").read_text(encoding="utf-8")
    match = re.search(r"commands: ([^']+)'", launcher)
    if match is None or set(match.group(1).split()) != COMMANDS:
        raise GateError("operator_command_inventory_invalid")
    syntax = subprocess.run(
        ["/bin/sh", "-n", str(root / "dc")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if syntax.returncode != 0:
        raise GateError("launcher_shell_syntax_invalid")
    help_result = subprocess.run(
        [str(root / "dc"), "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if help_result.returncode != 0 or not COMMANDS.issubset(set(help_result.stdout.split())):
        raise GateError("launcher_help_invalid")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    reference = "registry.invalid/digital-colleagues/runtime@sha256:" + "1" * 64
    studio = "registry.invalid/digital-colleagues/studio@sha256:" + "2" * 64
    with tempfile.TemporaryDirectory(prefix="dc-p10-operations-") as name:
        output = Path(name) / "bundle"
        result = build_bundle(root, output, revision, reference, studio)
        if result["member_count"] != 6:
            raise GateError("bundle_member_count_invalid")
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        if manifest["runtime_image"] != reference:
            raise GateError("operation_release_binding_invalid")
    for marker in (
        "--no-build --pull never",
        "services_must_be_stopped",
        "verify-backup",
        "remote_distribution_authorization_required",
        "--purge-data",
    ):
        if marker not in launcher:
            raise GateError("operation_safety_control_missing")
    return {
        "schema_version": 1,
        "gate": "p10_operations_clean",
        "command_count": len(COMMANDS),
        "bundle_member_count": 6,
        "unsafe_operation_count": 0,
        "remote_update_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    return emit_main(check_operations, argv, __doc__)


if __name__ == "__main__":
    raise SystemExit(main())
