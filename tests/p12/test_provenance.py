# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import unittest
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from scripts.check_p12_provenance import HISTORY, P10_RUNS, P10_SETS, P10_SUBJECTS, check_provenance
from scripts.check_p12_repository import P12GateError

ROOT = Path(__file__).resolve().parents[2]


class ProvenanceTests(unittest.TestCase):
    def test_complete_receipt_passes(self) -> None:
        result = check_provenance(ROOT)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["covered_path_count"], 37)
        self.assertEqual(result["protected_p10_local_git_identity_count"], 8)

    def test_historical_anchor_set_is_exact(self) -> None:
        self.assertEqual(len(HISTORY), 6)
        self.assertEqual(HISTORY["p11r_final"], "c1562ea5201394d8a278f4b644daf4029cbb5bd4")

    def test_p10_subjects_are_fixed(self) -> None:
        self.assertEqual(len(P10_SUBJECTS), 2)
        self.assertTrue(
            all(subject.startswith("ghcr.io/jeremyliu1220/") for subject in P10_SUBJECTS)
        )

    def test_active_and_superseded_sets_are_both_protected(self) -> None:
        self.assertEqual(set(P10_SETS), {"active", "superseded"})
        self.assertEqual(P10_SETS["active"]["lifecycle"], "passed")
        self.assertEqual(
            P10_SETS["superseded"]["lifecycle"], "superseded_contract_noncompliant_source"
        )

    def test_all_nine_p10_runs_are_fixed(self) -> None:
        self.assertEqual(len(P10_RUNS), 9)
        self.assertEqual(P10_RUNS["34237810474"][1], "success")

    def test_receipt_rejects_missing_covered_path(self) -> None:
        self._mutated_receipt(lambda value: value["covered_paths"].pop())

    def test_receipt_rejects_source_read(self) -> None:
        self._mutated_receipt(
            lambda value: value.__setitem__("parent_research_working_tree_read", True)
        )

    def test_receipt_rejects_publication(self) -> None:
        self._mutated_receipt(lambda value: value["publication"].__setitem__("tags", True))

    def test_receipt_rejects_p10_lifecycle_drift(self) -> None:
        self._mutated_receipt(
            lambda value: value["p10_protected_publication"]["sets"]["superseded"].__setitem__(
                "lifecycle", "deleted"
            )
        )

    def test_receipt_rejects_local_absolute_path(self) -> None:
        local_path = str(Path("/", "Users", "example", "private"))
        self.assertEqual(local_path, "/" + "Users/example/private")
        self._mutated_receipt(lambda value: value.__setitem__("note", local_path))

    def _mutated_receipt(self, mutate: Callable[[dict[str, Any]], None]) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "provenance").mkdir()
            (root / "docs/p12").mkdir(parents=True)
            receipt = json.loads((ROOT / "provenance/p12-change-receipt.json").read_text())
            mutate(receipt)
            (root / "provenance/p12-change-receipt.json").write_text(
                json.dumps(receipt), encoding="utf-8"
            )
            (root / "docs/p12/acceptance.md").write_bytes(
                (ROOT / "docs/p12/acceptance.md").read_bytes()
            )
            with self.assertRaises(P12GateError):
                check_provenance(root)


if __name__ == "__main__":
    unittest.main()
