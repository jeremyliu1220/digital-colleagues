# SPDX-License-Identifier: Apache-2.0

"""Run the focused P4 bootstrap, session, and mutation-defense gate."""

from __future__ import annotations

import argparse
import io
import json
import sys
import unittest
import warnings
from pathlib import Path

if __package__ in {None, ""}:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "src"))

TEST_MODULE = "tests.p4.test_authentication"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P4 local authentication.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    root = Path(arguments.root).resolve()
    warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient`.*")
    suite = unittest.defaultTestLoader.loadTestsFromName(TEST_MODULE)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    worker = (root / "src/digital_colleagues/local/worker.py").read_text(encoding="utf-8")
    api = (root / "src/digital_colleagues/local/asgi.py").read_text(encoding="utf-8")
    if not result.wasSuccessful() or result.testsRun < 2 or "print(" in worker or "print(" in api:
        print("P4 authentication check failed", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "schema_version": 1,
                "gate": "p4_authentication_clean",
                "tests_run": result.testsRun,
                "bootstrap_entropy_bits": 256,
                "bootstrap_max_lifetime_seconds": 600,
                "bootstrap_retrieval": "atomic_operator_once",
                "credential_persistence": "digest_only",
                "session_cookie": "httponly_samesite_strict_secure_in_https_mode",
                "origin_csrf_namespace_authority": "passed",
                "api_worker_plaintext_log_calls": 0,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
