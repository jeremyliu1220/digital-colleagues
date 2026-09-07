# SPDX-License-Identifier: Apache-2.0

"""Build the P10 bundle twice and compare every byte and mode."""

from __future__ import annotations

import hashlib
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_p10_candidate import build_bundle
from scripts.p10_gate_support import GateError, emit_main


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_reproducibility(root: Path) -> dict[str, object]:
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    runtime = "registry.invalid/digital-colleagues/runtime@sha256:" + "a" * 64
    studio = "registry.invalid/digital-colleagues/studio@sha256:" + "b" * 64
    with tempfile.TemporaryDirectory(prefix="dc-p10-repro-") as name:
        first, second = Path(name) / "first", Path(name) / "second"
        build_bundle(root, first, revision, runtime, studio)
        build_bundle(root, second, revision, runtime, studio)
        first_names = sorted(path.name for path in first.iterdir())
        second_names = sorted(path.name for path in second.iterdir())
        if first_names != second_names or len(first_names) != 6:
            raise GateError("bundle_inventory_not_reproducible")
        for member in first_names:
            a, b = first / member, second / member
            if _digest(a) != _digest(b) or stat.S_IMODE(a.stat().st_mode) != stat.S_IMODE(
                b.stat().st_mode
            ):
                raise GateError("bundle_bytes_not_reproducible")
    return {
        "schema_version": 1,
        "gate": "p10_reproducibility_clean",
        "build_count": 2,
        "artifact_count": 6,
        "mismatch_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    return emit_main(check_reproducibility, argv, __doc__)


if __name__ == "__main__":
    raise SystemExit(main())
