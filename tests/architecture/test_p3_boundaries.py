# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from scripts.check_p3_architecture import (
    BOUNDARIES,
    ArchitectureError,
    check_architecture,
)
from scripts.check_p3_architecture import main as architecture_main


class P3ArchitectureTests(unittest.TestCase):
    def _fixture(self, content: str, *, boundary: str, filename: str = "fixture.py") -> Path:
        temporary = tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-architecture-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for relative in BOUNDARIES.values():
            (root / relative).mkdir(parents=True)
        (root / BOUNDARIES[boundary] / filename).write_text(content, encoding="utf-8")
        return root

    def test_adversarial_unknown_import_alias_bypass_and_reverse_dependencies_fail(self) -> None:
        fixtures = (
            ("core", "import requests\n"),
            ("core", "from datetime import datetime as dt\nvalue = dt.now()\n"),
            ("core", "import digital_colleagues.application\n"),
            ("application", "import digital_colleagues.adapters.sqlite\n"),
            ("application", "from pydantic import BaseModel\n"),
            ("application", "import uuid as stable\nvalue = stable.uuid4()\n"),
        )
        for boundary, content in fixtures:
            with (
                self.subTest(boundary=boundary, content=content),
                self.assertRaises(ArchitectureError),
            ):
                check_architecture(self._fixture(content, boundary=boundary))

    def test_current_tree_satisfies_p3_dependency_and_determinism_policy(self) -> None:
        root = Path(__file__).resolve().parents[2]
        result = check_architecture(root)
        self.assertEqual(result["gate"], "p3_architecture_clean")
        self.assertEqual(
            result["policy_version"],
            "p3-boundary-specific-determinism-allowlist-v2",
        )
        for field in (
            "unapproved_imports",
            "dependency_violations",
            "edge_type_leaks",
            "nondeterministic_imports",
            "nondeterministic_calls",
            "alias_resolved_unsafe_calls",
            "stable_port_leaks",
        ):
            self.assertEqual(result[field], 0)

    def test_boundary_specific_allowlists_and_assigned_alias_bypasses_fail_cli_and_direct(
        self,
    ) -> None:
        fixtures = (
            ("core", "fixture.py", "import sqlite3\n"),
            ("application", "fixture.py", "import sqlite3\n"),
            (
                "application",
                "fixture.py",
                "from pathlib import Path\nVALUE = Path('x').read_text()\n",
            ),
            (
                "core",
                "fixture.py",
                "from datetime import datetime as dt\nClock = dt\nnow = Clock.now\nVALUE = now()\n",
            ),
            (
                "core",
                "fixture.py",
                "reader = open\nVALUE = reader('synthetic')\n",
            ),
            (
                "application",
                "fixture.py",
                "import sqlite3 as database\ndb = database.connect\nVALUE = db('synthetic')\n",
            ),
            (
                "application",
                "ports.py",
                "from __future__ import annotations\n"
                "def raw_connection(value: 'sqlite3.Connection') -> None:\n"
                "    del value\n",
            ),
        )
        for boundary, filename, content in fixtures:
            with self.subTest(boundary=boundary, filename=filename, content=content):
                root = self._fixture(content, boundary=boundary, filename=filename)
                with self.assertRaises(ArchitectureError):
                    check_architecture(root)
                diagnostics = io.StringIO()
                with redirect_stderr(diagnostics):
                    exit_code = architecture_main([str(root)])
                self.assertNotEqual(exit_code, 0)
                self.assertIn("P3 architecture check failed", diagnostics.getvalue())


if __name__ == "__main__":
    unittest.main()
