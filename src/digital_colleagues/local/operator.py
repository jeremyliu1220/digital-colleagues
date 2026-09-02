# SPDX-License-Identifier: Apache-2.0

"""One-shot local operator commands; plaintext output never enters service logs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from digital_colleagues.local.runtime import build_local_runtime
from digital_colleagues.local.security import retrieve_bootstrap_for_operator


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Digital Colleagues local operator boundary")
    parser.add_argument(
        "command",
        choices=("bootstrap-token", "enrollment-token", "recovery-session"),
    )
    parser.add_argument("--credential-id")
    parser.add_argument(
        "--state-directory",
        default=os.environ.get("DC_STATE_DIR", "/state"),
    )
    arguments = parser.parse_args(argv)
    runtime = build_local_runtime(Path(arguments.state_directory))
    try:
        if arguments.command == "bootstrap-token":
            plaintext = retrieve_bootstrap_for_operator(runtime.authentication)
            sys.stdout.write(plaintext + "\n")
        elif arguments.command == "enrollment-token":
            if not arguments.credential_id:
                raise ValueError("credential identity is required")
            plaintext = runtime.authentication.retrieve_operator_credential(arguments.credential_id)
            sys.stdout.write(plaintext + "\n")
        else:
            if not arguments.credential_id:
                raise ValueError("credential identity is required")
            plaintext = runtime.authentication.retrieve_operator_credential(arguments.credential_id)
            grant = runtime.authentication.exchange_recovery(plaintext)
            sys.stdout.write(
                json.dumps(
                    {
                        "session_credential": grant.session_grant.session_credential,
                        "csrf_token": grant.session_grant.csrf_token,
                        "session_id": grant.session_grant.session.session_id,
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n"
            )
        return 0
    except (OSError, RuntimeError, ValueError):
        print("operator command failed: request refused", file=sys.stderr)
        return 2
    finally:
        runtime.close()


if __name__ == "__main__":
    raise SystemExit(main())
