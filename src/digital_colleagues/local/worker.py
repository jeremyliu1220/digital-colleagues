# SPDX-License-Identifier: Apache-2.0

"""Bounded local worker loop over durable pending namespaces."""

from __future__ import annotations

import os
import time
from collections.abc import Mapping
from pathlib import Path

from digital_colleagues.application.errors import ConflictError, PermissionDeniedError
from digital_colleagues.local.runtime import build_local_runtime


def run_once(state_directory: Path, *, adapter_environment: Mapping[str, str] | None = None) -> int:
    runtime = build_local_runtime(state_directory, adapter_environment=adapter_environment)
    try:
        processed = 0
        for namespace in runtime.store.pending_namespaces(runtime.clock.now()):
            if namespace.scope_id is None:
                continue
            try:
                context = runtime.controller.service_context(namespace)
                runtime.controller.process_once(context)
                processed += 1
            except (ConflictError, PermissionDeniedError):
                # A stale lease/fence or changed authority fails this namespace
                # closed without terminating the long-running worker.
                continue
        return processed
    finally:
        runtime.close()


def main() -> int:
    state_directory = Path(os.environ.get("DC_STATE_DIR", "/state"))
    once = os.environ.get("DC_WORKER_ONCE", "0") == "1"
    while True:
        run_once(state_directory, adapter_environment=os.environ)
        if once:
            return 0
        time.sleep(0.5)


if __name__ == "__main__":
    raise SystemExit(main())
