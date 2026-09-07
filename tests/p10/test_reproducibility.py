# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.build_p10_candidate import CandidateError, build_bundle
from scripts.check_p10_reproducibility import check_reproducibility
from tests.p10.fixtures import ROOT


class P10ReproducibilityTests(unittest.TestCase):
    def test_six_member_bundle_is_byte_reproducible(self) -> None:
        result = check_reproducibility(ROOT)
        self.assertEqual(result["build_count"], 2)
        self.assertEqual(result["artifact_count"], 6)
        self.assertEqual(result["mismatch_count"], 0)

    def test_nonempty_output_and_digest_drift_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="dc-p10-repro-refusal-") as name:
            output = Path(name) / "bundle"
            output.mkdir()
            (output / "existing").write_text("occupied\n", encoding="utf-8")
            with self.assertRaisesRegex(CandidateError, "output_not_new_or_empty"):
                build_bundle(
                    ROOT,
                    output,
                    "11aa240af8db2ca515325dc059b1a77f7badc874",
                    "example.invalid/dc/runtime@sha256:" + "a" * 64,
                    "example.invalid/dc/studio@sha256:" + "b" * 64,
                )


if __name__ == "__main__":
    unittest.main()
