# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest

from scripts.check_p11_studio import check_studio
from tests.p11.fixtures import ROOT


class StudioTests(unittest.TestCase):
    def test_studio_gate_has_exact_locale_parity(self) -> None:
        result = check_studio(ROOT)
        self.assertEqual(result["locale_mismatch_count"], 0)
        self.assertEqual(result["placeholder_mismatch_count"], 0)

    def test_registry_has_live_result_announcement(self) -> None:
        source = (ROOT / "studio/src/AgentRegistry.tsx").read_text()
        self.assertIn('aria-live="polite"', source)

    def test_registry_keeps_permission_diff_visible(self) -> None:
        source = (ROOT / "studio/src/AgentRegistry.tsx").read_text()
        for field in ("requested", "granted", "not_granted", "admin_extra"):
            self.assertIn(field, source)

    def test_registry_controls_have_disabled_busy_states(self) -> None:
        source = (ROOT / "studio/src/AgentRegistry.tsx").read_text()
        self.assertGreaterEqual(source.count("disabled={Boolean(busy)"), 4)

    def test_registry_exposes_complete_separate_admin_workflow(self) -> None:
        source = (ROOT / "studio/src/AgentRegistry.tsx").read_text()
        for marker in (
            "/agent-packages/validate",
            "/agent-packages",
            "/deployment-drafts",
            '"review" | "confirm"',
            '"upgrade" | "rollback"',
            "/select",
            "/audit",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

    def test_registry_displays_exact_attestation_review_fields(self) -> None:
        source = (ROOT / "studio/src/AgentRegistry.tsx").read_text()
        for field in (
            "attestation.signer",
            "attestation.signer_digest",
            "attestation.repository",
            "attestation.workflow",
            "attestation.build_identity",
            "attestation.source_ref",
            "attestation.source_digest",
            "attestation.predicate_type",
            "attestation.verification",
            "attestation.artifact_digest",
            "archive_digest",
        ):
            self.assertIn(field, source)


if __name__ == "__main__":
    unittest.main()
