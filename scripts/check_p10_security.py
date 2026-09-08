# SPDX-License-Identifier: Apache-2.0

"""Validate P10 filesystem, FileVault, secret, output, and cleanup boundaries."""

from __future__ import annotations

import re
import stat
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.p10_gate_support import GateError, emit_main


def check_security(root: Path) -> dict[str, object]:
    launcher = root / "dc"
    text = launcher.read_text(encoding="utf-8")
    if stat.S_IMODE(launcher.stat().st_mode) != 0o755 or launcher.is_symlink():
        raise GateError("launcher_mode_invalid")
    forbidden = (
        "eval ",
        "source ",
        ". $",
        "env >",
        "printenv",
        "set -x",
        "docker compose build",
        "docker pull",
        "DC_TEST_MODE",
        "DC_TEST_FILEVAULT_STATUS",
    )
    if any(marker in text for marker in forbidden):
        raise GateError("unsafe_launcher_primitive")
    required = (
        "umask 077",
        "Library/Application Support/Digital Colleagues",
        "/usr/bin/fdesetup status",
        "chmod 700",
        "chmod 600",
        "managed-root-id",
        "release-identity",
        "DELETE-P10-DATA",
        "RESTORE-P10-STATE",
        "concurrent_invocation",
    )
    if any(marker not in text for marker in required):
        raise GateError("security_control_missing")
    if text.count("/usr/bin/fdesetup status") != 1:
        raise GateError("filevault_probe_boundary_invalid")
    if re.search(r"docker compose[^\n]*(?:\$\*|eval)", text):
        raise GateError("unbounded_compose_execution")
    compose = (root / "compose.p10.yaml").read_text(encoding="utf-8")
    studio = compose.split("\n  studio:", 1)[1].split("\n  operator:", 1)[0]
    if "secrets" in studio.lower() or "/state" in studio or "environment:" in studio:
        raise GateError("studio_secret_or_state_mount_forbidden")
    for secret_shape in (
        "OPENAI_API_KEY",
        "client_secret",
        "access_token",
        "refresh_token",
        "Bearer ",
    ):
        if secret_shape in compose:
            raise GateError("secret_material_in_compose")
    return {
        "schema_version": 1,
        "gate": "p10_security_clean",
        "secret_leak_count": 0,
        "unsafe_path_count": 0,
        "studio_secret_mount_count": 0,
        "filevault_probe": "contract_tested",
        "filevault_off_live_ready": False,
        "filevault_unknown_live_ready": False,
    }


def main(argv: list[str] | None = None) -> int:
    return emit_main(check_security, argv, __doc__)


if __name__ == "__main__":
    raise SystemExit(main())
