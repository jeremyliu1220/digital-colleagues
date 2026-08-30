# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class FastAPIEdgeTests(unittest.TestCase):
    _temporary: tempfile.TemporaryDirectory[str] | None = None
    _python = Path(sys.executable)

    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = None
        if importlib.util.find_spec("fastapi") is not None:
            cls._python = Path(sys.executable)
            return
        cls._temporary = tempfile.TemporaryDirectory(
            prefix="digital-colleagues-p3-api-dependencies-"
        )
        environment = Path(cls._temporary.name) / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
        cls._python = environment / "bin" / "python"
        subprocess.run(
            [
                str(cls._python),
                "-m",
                "pip",
                "--disable-pip-version-check",
                "install",
                "-r",
                str(ROOT / "requirements/p3.lock"),
            ],
            stdout=subprocess.DEVNULL,
            check=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._temporary is not None:
            cls._temporary.cleanup()

    def _run_case(self, case: str) -> None:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        completed = subprocess.run(
            [str(self._python), "-B", "-m", "tests.api.edge_cases", case],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_in_process_mapping_derives_authority_and_rejects_caller_authority_fields(self) -> None:
        self._run_case("authority")

    def test_exact_approval_mapping_uses_expected_revision_and_stable_errors(self) -> None:
        self._run_case("approval")


if __name__ == "__main__":
    unittest.main()
