# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_p3_architecture import BOUNDARIES, ArchitectureError, check_architecture


class P3ArchitectureTests(unittest.TestCase):
    def _fixture(self, content: str, *, boundary: str) -> Path:
        temporary = tempfile.TemporaryDirectory(prefix="digital-colleagues-p3-architecture-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for relative in BOUNDARIES.values():
            (root / relative).mkdir(parents=True)
        (root / BOUNDARIES[boundary] / "fixture.py").write_text(content, encoding="utf-8")
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


if __name__ == "__main__":
    unittest.main()
