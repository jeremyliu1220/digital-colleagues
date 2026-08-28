# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_p2_architecture import ArchitectureError, check_architecture
from scripts.check_p2_core_contracts import check_core_contracts
from scripts.check_p2_provenance import check_p2_provenance
from scripts.check_p2_repository import check_p2_repository

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class P2BoundaryTests(unittest.TestCase):
    def test_current_architecture_and_contract_gates_pass(self) -> None:
        architecture = check_architecture(PROJECT_ROOT)
        contracts = check_core_contracts(PROJECT_ROOT)
        self.assertEqual(architecture["gate"], "p2_architecture_clean")
        self.assertEqual(architecture["forbidden_imports"], 0)
        self.assertEqual(architecture["nondeterministic_calls"], 0)
        self.assertEqual(contracts["gate"], "p2_core_contracts_clean")
        self.assertEqual(contracts["immutability"], "passed")

    def test_current_repository_and_provenance_gates_pass(self) -> None:
        repository = check_p2_repository(PROJECT_ROOT)
        provenance = check_p2_provenance(PROJECT_ROOT)
        self.assertEqual(repository["gate"], "p2_repository_clean")
        self.assertTrue(repository["p1_historical_gate_preserved"])
        self.assertEqual(provenance["transformed_migration_count"], 0)
        implementation_count = provenance["new_implementation_count"]
        self.assertIsInstance(implementation_count, int)
        assert isinstance(implementation_count, int)
        self.assertGreater(implementation_count, 0)

    def test_core_forbidden_framework_import_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            core = root / "src/digital_colleagues/core"
            governance = root / "src/digital_colleagues/governance"
            core.mkdir(parents=True)
            governance.mkdir(parents=True)
            (core / "invalid.py").write_text("import fastapi\n", encoding="utf-8")
            (governance / "__init__.py").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ArchitectureError, "forbidden_import"):
                check_architecture(root)

    def test_wall_clock_environment_and_random_reads_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            core = root / "src/digital_colleagues/core"
            governance = root / "src/digital_colleagues/governance"
            core.mkdir(parents=True)
            governance.mkdir(parents=True)
            (core / "invalid.py").write_text(
                "from datetime import datetime\n"
                "import os\n"
                "import random\n"
                "VALUE = (datetime.now(), os.getenv('SYNTHETIC'), random.random())\n",
                encoding="utf-8",
            )
            (governance / "__init__.py").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ArchitectureError, "forbidden_deterministic_call"):
                check_architecture(root)

    def test_reverse_core_to_governance_dependency_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            core = root / "src/digital_colleagues/core"
            governance = root / "src/digital_colleagues/governance"
            core.mkdir(parents=True)
            governance.mkdir(parents=True)
            (core / "invalid.py").write_text(
                "from digital_colleagues.governance import approvals\n",
                encoding="utf-8",
            )
            (governance / "__init__.py").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ArchitectureError, "reverse_governance_dependency"):
                check_architecture(root)


if __name__ == "__main__":
    unittest.main()
