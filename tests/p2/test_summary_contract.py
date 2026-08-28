# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class P2SummaryContractTests(unittest.TestCase):
    def test_summary_is_scoped_to_p2_and_never_claims_p3(self) -> None:
        summary = json.loads(
            (PROJECT_ROOT / "artifacts/p2/summary.json").read_text(encoding="utf-8")
        )
        self.assertEqual(summary["milestone"], "P2")
        self.assertIn(summary["status"], {"review_required", "passed"})
        self.assertEqual(summary["claim_scope"], "P2 framework-independent core primitives only.")
        if summary["status"] == "review_required":
            return
        self.assertEqual(summary["results"]["unittest"]["skipped"], 0)
        self.assertEqual(summary["migration"]["transformed_migration_count"], 0)
        self.assertIn("P3 application orchestration", summary["not_evidence_for"])


if __name__ == "__main__":
    unittest.main()
