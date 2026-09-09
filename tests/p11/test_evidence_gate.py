# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.collect_p11_evidence import EXCLUSIONS, _preconditions, write_evidence
from scripts.p11_gate_support import BRANCH, CLAIM, STATUS, SUMMARY_PATH, GateError
from tests.p11.fixtures import ROOT


class EvidenceGateTests(unittest.TestCase):
    def test_claim_and_status_are_exactly_one_candidate_vocabulary(self) -> None:
        self.assertEqual(CLAIM, "p11_agent_package_multi_agent_lifecycle_candidate")
        self.assertEqual(STATUS, "development_complete_awaiting_independent_acceptance")

    def test_exclusions_keep_future_and_live_claims_out(self) -> None:
        self.assertIn("P12", EXCLUSIONS)
        self.assertIn("OpenAI live compatibility", EXCLUSIONS)
        self.assertIn("production readiness", EXCLUSIONS)

    def test_writer_creates_only_the_summary_path(self) -> None:
        with TemporaryDirectory() as value:
            root = Path(value)
            write_evidence(root, {"claim": CLAIM, "status": STATUS})
            files = [str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()]
            self.assertEqual(files, [SUMMARY_PATH])

    def test_preconditions_refuse_dirty_implementation_tree(self) -> None:
        def dirty_git(_: Path, *arguments: str) -> str:
            if arguments == ("branch", "--show-current"):
                return BRANCH
            if arguments == ("status", "--porcelain"):
                return " M tests/p11/test_evidence_gate.py"
            self.fail(f"unexpected git call after dirty state: {arguments}")

        with patch("scripts.collect_p11_evidence.git", side_effect=dirty_git):
            with self.assertRaises(GateError):
                _preconditions(ROOT)


if __name__ == "__main__":
    unittest.main()
