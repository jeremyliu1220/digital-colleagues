# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class PlanningContractTests(unittest.TestCase):
    def test_required_p0_artifacts_exist(self) -> None:
        required = {
            "AGENTS.md",
            ".gitignore",
            "docs/product/v0.1-product-brief.md",
            "docs/product/capability-matrix.md",
            "docs/architecture/target-architecture.md",
            "docs/security/threat-model.md",
            "docs/security/privacy-boundary.md",
            "docs/research/source-inventory.md",
            "docs/research/provenance.md",
            "docs/roadmap.md",
            "docs/p0/acceptance.md",
            "docs/adr/0001-license-and-source-rights.md",
            "docs/adr/0002-technology-stack-and-local-authentication.md",
            "docs/licensing/third-party-inventory.md",
            "docs/licensing/spdx-policy.md",
            "provenance/source-rights-confirmation.json",
            "provenance/source-allowlist.json",
            "provenance/source-denylist.json",
            "provenance/scanner-policy.json",
            "provenance/scanner-exceptions.json",
            "scripts/fingerprint_source_tree.py",
            "scripts/verify_source_allowlist.py",
            "scripts/check_public_boundary.py",
            "artifacts/p0/source-fingerprint-before.json",
            "artifacts/p0/source-fingerprint-after.json",
            "artifacts/p0/summary.json",
        }
        missing = sorted(item for item in required if not (PROJECT_ROOT / item).is_file())
        self.assertEqual(missing, [])

    def test_p1_does_not_create_p2_product_artifacts(self) -> None:
        forbidden = {
            "migrations",
            "compose.yaml",
            "docker-compose.yml",
            "src/digital_colleagues/core",
            "src/digital_colleagues/governance",
            "src/digital_colleagues/application",
            "src/digital_colleagues/adapters",
            "src/digital_colleagues/api",
            "src/digital_colleagues/worker",
        }
        present = sorted(item for item in forbidden if (PROJECT_ROOT / item).exists())
        self.assertEqual(present, [])

    def test_authentication_adr_contains_normative_invariants(self) -> None:
        text = (
            PROJECT_ROOT / "docs" / "adr" / "0002-technology-stack-and-local-authentication.md"
        ).read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        required_phrases = {
            "127.0.0.1",
            "at least 256 bits of entropy",
            "displayed exactly once",
            "ten minutes",
            "Only a cryptographic digest is stored",
            "tenant_admin",
            "colleague_user",
            "auditor",
            "HttpOnly",
            "SameSite=Strict",
            "HTTPS mode also sets Secure",
            "validates Origin",
            "CSRF",
            "replay",
            "single-use enrollment token",
            "operator executing a documented local procedure",
            "can never convert to HUMAN",
            "can never submit HumanApprovalDecision",
            "OIDC, SSO, and SCIM",
        }
        for phrase in required_phrases:
            self.assertIn(phrase, normalized)

    def test_source_fingerprints_match(self) -> None:
        before = json.loads(
            (PROJECT_ROOT / "artifacts" / "p0" / "source-fingerprint-before.json").read_text(
                encoding="utf-8"
            )
        )
        after = json.loads(
            (PROJECT_ROOT / "artifacts" / "p0" / "source-fingerprint-after.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(before, after)
        self.assertEqual(before["scope"], "parent_source_excluding_authorized_target_subtree")

    def test_summary_claim_is_strictly_limited(self) -> None:
        summary = json.loads(
            (PROJECT_ROOT / "artifacts" / "p0" / "summary.json").read_text(encoding="utf-8")
        )
        self.assertEqual(summary["gate"], "p0_planning_public_boundary")
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["claim_scope"], "Planning and public-boundary gate only.")
        self.assertEqual(summary["results"]["p0_tests"], {"passed": 28, "failed": 0})
        self.assertFalse(summary["boundaries"]["git_initialized"])
        self.assertIn("production readiness", summary["not_evidence_for"])
        self.assertIn("security effectiveness", summary["not_evidence_for"])
        self.assertFalse(summary["boundaries"]["p1_started"])

    def test_product_brief_limits_p0_claim(self) -> None:
        text = (PROJECT_ROOT / "docs" / "product" / "v0.1-product-brief.md").read_text(
            encoding="utf-8"
        )
        normalized = " ".join(text.split())
        self.assertIn("planning and public-boundary gate passed", normalized)
        self.assertIn("does not mean the product exists", normalized)
        self.assertIn("Production readiness | Not claimed", normalized)

    def test_comment_capable_files_have_spdx_headers(self) -> None:
        for document in PROJECT_ROOT.rglob("*"):
            if not document.is_file():
                continue
            relative = document.relative_to(PROJECT_ROOT)
            if relative.as_posix() == ".gitignore" or document.suffix in {".py", ".md"}:
                first_line = document.read_text(encoding="utf-8").splitlines()[0]
                self.assertIn("SPDX-License-Identifier: Apache-2.0", first_line, relative)


if __name__ == "__main__":
    unittest.main()
