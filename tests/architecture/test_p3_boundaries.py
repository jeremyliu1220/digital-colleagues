# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts.check_p3_architecture import (
    BOUNDARIES,
    DETERMINISTIC_BOUNDARIES,
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

    def _assert_cli_and_direct_reject(self, content: str, *, boundary: str) -> None:
        root = self._fixture(content, boundary=boundary)
        with self.assertRaises(ArchitectureError):
            check_architecture(root)
        diagnostics = io.StringIO()
        with redirect_stderr(diagnostics):
            exit_code = architecture_main([str(root)])
        self.assertNotEqual(exit_code, 0)
        self.assertIn("P3 architecture check failed", diagnostics.getvalue())

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
            "p3-boundary-specific-determinism-allowlist-v3",
        )
        for field in (
            "unapproved_imports",
            "dependency_violations",
            "edge_type_leaks",
            "nondeterministic_imports",
            "nondeterministic_calls",
            "dynamic_capability_calls",
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

    def test_dynamic_builtin_calls_and_recursive_aliases_fail_cli_and_direct(self) -> None:
        direct_calls = (
            "__import__('sqlite3')",
            "compile('VALUE = 1', 'synthetic', 'exec')",
            "eval(\"__import__('sqlite3').connect(':memory:')\")",
            "exec(\"__import__('sqlite3').connect(':memory:')\")",
            "input('synthetic')",
            "open('synthetic')",
        )
        recursive_alias_calls = (
            ("__import__", "('sqlite3')"),
            ("compile", "('VALUE = 1', 'synthetic', 'exec')"),
            ("eval", "('1 + 1')"),
            ("exec", "('VALUE = 1')"),
            ("input", "('synthetic')"),
            ("open", "('synthetic')"),
        )
        for boundary in sorted(DETERMINISTIC_BOUNDARIES):
            with self.subTest(boundary=boundary, kind="direct_import"):
                self._assert_cli_and_direct_reject(
                    "DB = __import__('sqlite3')\n", boundary=boundary
                )
            exact_import_alias = "loader = __import__\nDB = loader('sqlite3')\n"
            with self.subTest(boundary=boundary, kind="assigned_import_alias"):
                self._assert_cli_and_direct_reject(exact_import_alias, boundary=boundary)
            for call in direct_calls:
                with self.subTest(boundary=boundary, kind="direct", call=call):
                    self._assert_cli_and_direct_reject(f"VALUE = {call}\n", boundary=boundary)
            for capability, arguments in recursive_alias_calls:
                content = (
                    f"first = {capability}\n"
                    "second = first\n"
                    "third = second\n"
                    f"VALUE = third{arguments}\n"
                )
                with self.subTest(boundary=boundary, kind="recursive_alias", call=capability):
                    self._assert_cli_and_direct_reject(content, boundary=boundary)

    def test_literal_and_unresolved_getattr_capabilities_fail_cli_and_direct(self) -> None:
        fixtures = (
            "from datetime import datetime\nclock = getattr(datetime, 'now')\nclock()\n",
            "from datetime import datetime\nclock = getattr(datetime, 'utcnow')\nclock()\n",
            "reader = getattr(__builtins__, 'open')\nreader('synthetic')\n",
            "loader = getattr(__builtins__, '__import__')\nloader('sqlite3')\n",
            "from datetime import date\nclock = getattr(date, 'today')\nclock()\n",
            "from datetime import datetime\nname = 'now'\nclock = getattr(datetime, name)\nclock()\n",
            "selector = getattr\nlookup = selector\nreader = lookup(__builtins__, 'open')\n"
            "reader('synthetic')\n",
        )
        for boundary in sorted(DETERMINISTIC_BOUNDARIES):
            for content in fixtures:
                with self.subTest(boundary=boundary, content=content):
                    self._assert_cli_and_direct_reject(content, boundary=boundary)

    def test_legal_deterministic_code_passes_cli_and_direct(self) -> None:
        content = "from __future__ import annotations\nVALUE = (1 + 2) * 3\n"
        for boundary in sorted(DETERMINISTIC_BOUNDARIES):
            with self.subTest(boundary=boundary):
                root = self._fixture(content, boundary=boundary)
                result = check_architecture(root)
                self.assertEqual(result["gate"], "p3_architecture_clean")
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(architecture_main([str(root)]), 0)
        safe_getattr = "import math\nROOT = getattr(math, 'sqrt')(9)\n"
        root = self._fixture(safe_getattr, boundary="core")
        self.assertEqual(check_architecture(root)["gate"], "p3_architecture_clean")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(architecture_main([str(root)]), 0)


if __name__ == "__main__":
    unittest.main()
