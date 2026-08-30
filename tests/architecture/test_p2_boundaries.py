# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from scripts.check_p2_architecture import ArchitectureError
from scripts.check_p2_architecture import check_architecture as check_p2_architecture
from scripts.check_p2_architecture import main as architecture_main
from scripts.check_p2_core_contracts import check_core_contracts
from scripts.check_p3_architecture import check_architecture as check_p3_architecture
from scripts.check_p3_provenance import check_provenance as check_p3_provenance
from scripts.check_p3_repository import check_repository as check_p3_repository

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class P2BoundaryTests(unittest.TestCase):
    def assert_architecture_cli_rejects(self, source: str, marker: str) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            core = root / "src/digital_colleagues/core"
            governance = root / "src/digital_colleagues/governance"
            core.mkdir(parents=True)
            governance.mkdir(parents=True)
            (core / "invalid.py").write_text(source, encoding="utf-8")
            (governance / "__init__.py").write_text("", encoding="utf-8")
            diagnostics = io.StringIO()
            with redirect_stderr(diagnostics):
                exit_code = architecture_main([str(root)])
            self.assertNotEqual(exit_code, 0)
            self.assertIn(marker, diagnostics.getvalue())

    def test_current_architecture_and_contract_gates_pass(self) -> None:
        architecture = check_p3_architecture(PROJECT_ROOT)
        contracts = check_core_contracts(PROJECT_ROOT)
        self.assertEqual(architecture["gate"], "p3_architecture_clean")
        self.assertEqual(
            architecture["policy_version"],
            "p3-dependency-determinism-allowlist-v1",
        )
        self.assertEqual(architecture["unapproved_imports"], 0)
        self.assertEqual(architecture["dependency_violations"], 0)
        self.assertEqual(architecture["edge_type_leaks"], 0)
        self.assertEqual(architecture["nondeterministic_imports"], 0)
        self.assertEqual(architecture["nondeterministic_calls"], 0)
        self.assertEqual(contracts["gate"], "p2_core_contracts_clean")
        self.assertEqual(contracts["complete_effect_binding"], "passed")
        self.assertEqual(contracts["constraint_enforcement"], "passed")
        self.assertEqual(contracts["direct_construction_invariants"], "passed")
        mutation_count = contracts["authoritative_effect_field_mutations_checked"]
        self.assertIsInstance(mutation_count, int)
        assert isinstance(mutation_count, int)
        self.assertGreaterEqual(mutation_count, 17)
        self.assertEqual(contracts["immutability"], "passed")

    def test_current_repository_and_provenance_gates_pass(self) -> None:
        repository = check_p3_repository(PROJECT_ROOT)
        provenance = check_p3_provenance(PROJECT_ROOT)
        self.assertEqual(repository["gate"], "p3_repository_clean")
        self.assertEqual(repository["historical_artifact_count"], 7)
        self.assertEqual(repository["runtime_residue_count"], 0)
        self.assertEqual(provenance["gate"], "p3_provenance_clean")
        self.assertEqual(provenance["transformed_migration_count"], 0)
        implementation_count = provenance["new_implementation_count"]
        self.assertIsInstance(implementation_count, int)
        assert isinstance(implementation_count, int)
        self.assertGreater(implementation_count, 0)

    def test_unapproved_third_party_import_exits_nonzero(self) -> None:
        self.assert_architecture_cli_rejects("import requests\n", "unapproved_import")

    def test_uuid_randomness_exits_nonzero(self) -> None:
        self.assert_architecture_cli_rejects(
            "from uuid import uuid4 as make_identifier\nVALUE = make_identifier()\n",
            "forbidden_deterministic_call",
        )

    def test_tempfile_filesystem_io_exits_nonzero(self) -> None:
        self.assert_architecture_cli_rejects(
            "import tempfile as temporary_files\nVALUE = temporary_files.NamedTemporaryFile()\n",
            "forbidden_capability_import",
        )

    def test_aliased_datetime_now_and_utcnow_exit_nonzero(self) -> None:
        fixtures = (
            "from datetime import datetime as Clock\nVALUE = Clock.now()\n",
            "from datetime import datetime as Clock\nVALUE = Clock.utcnow()\n",
            "import datetime as clock_module\nVALUE = clock_module.datetime.now()\n",
            "import datetime as clock_module\nVALUE = clock_module.now()\n",
            "import datetime as clock_module\nVALUE = clock_module.utcnow()\n",
        )
        for source in fixtures:
            with self.subTest(source=source):
                self.assert_architecture_cli_rejects(
                    source,
                    "forbidden_deterministic_call",
                )

    def test_environment_random_process_and_network_capabilities_exit_nonzero(self) -> None:
        fixtures = (
            "import os as operating_system\nVALUE = operating_system.environ['SYNTHETIC']\n",
            "import random as entropy\nVALUE = entropy.random()\n",
            "import subprocess as process\nVALUE = process.run(['synthetic'])\n",
            "import socket as network\nVALUE = network.socket()\n",
        )
        for source in fixtures:
            with self.subTest(source=source):
                self.assert_architecture_cli_rejects(
                    source,
                    "forbidden_capability_import",
                )

    def test_reverse_core_to_governance_dependency_exits_nonzero(self) -> None:
        self.assert_architecture_cli_rejects(
            "from digital_colleagues.governance import approvals\n",
            "reverse_governance_dependency",
        )

    def test_direct_api_also_raises_on_adversarial_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            core = root / "src/digital_colleagues/core"
            governance = root / "src/digital_colleagues/governance"
            core.mkdir(parents=True)
            governance.mkdir(parents=True)
            (core / "invalid.py").write_text("import requests\n", encoding="utf-8")
            (governance / "__init__.py").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ArchitectureError, "unapproved_import"):
                check_p2_architecture(root)


if __name__ == "__main__":
    unittest.main()
