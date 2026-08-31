# SPDX-License-Identifier: Apache-2.0

"""One-shot local operator commands; plaintext output never enters service logs."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from digital_colleagues.local.runtime import build_local_runtime
from digital_colleagues.local.security import retrieve_bootstrap_for_operator


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Digital Colleagues local operator boundary")
    parser.add_argument("command", choices=("bootstrap-token",))
    parser.add_argument(
        "--state-directory",
        default=os.environ.get("DC_STATE_DIR", "/state"),
    )
    arguments = parser.parse_args(argv)
    runtime = build_local_runtime(Path(arguments.state_directory))
    try:
        plaintext = retrieve_bootstrap_for_operator(runtime.authentication)
        sys.stdout.write(plaintext + "\n")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"operator command failed: {exc}", file=sys.stderr)
        return 2
    finally:
        runtime.close()


if __name__ == "__main__":
    raise SystemExit(main())
