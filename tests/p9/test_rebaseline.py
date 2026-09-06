# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_p9_rebaseline import DOCUMENTS, RebaselineError, check_rebaseline
from tests.p9.fixtures import ROOT, copy_documents


def _replace(root: Path, relative: str, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"fixture marker is absent: {old}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def _replace_everywhere(root: Path, old: str, new: str) -> None:
    found = False
    for relative in DOCUMENTS:
        path = root / relative
        text = path.read_text(encoding="utf-8")
        if old in text:
            path.write_text(text.replace(old, new), encoding="utf-8")
            found = True
    if not found:
        raise AssertionError(f"fixture marker is absent: {old}")


class P9RebaselineTests(unittest.TestCase):
    def test_exact_documents_pass(self) -> None:
        result = check_rebaseline(ROOT)
        self.assertEqual(result["gate"], "p9_rebaseline_clean")
        self.assertEqual(result["phase_count"], 16)
        self.assertEqual(result["p9_through_p15_order"], "passed")
        self.assertEqual(result["product_runtime_implementation_change_count"], 0)
        self.assertEqual(result["openai_live"], "not_evaluated")
        self.assertEqual(result["microsoft_365_live"], "not_evaluated")
        self.assertEqual(result["human_evaluation"], "not_evaluated")

    def test_p10_through_p15_reorder_merge_or_missing_phase_is_rejected(self) -> None:
        mutations = (
            ("## P10 —", "## P12 —"),
            ("## P11 —", "## P11/P12 —"),
            ("## P15 —", "## Deferred P15 —"),
        )
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-phases-") as name:
            temporary = Path(name)
            for index, (old, new) in enumerate(mutations):
                with self.subTest(mutation=old):
                    root = copy_documents(temporary / str(index))
                    _replace(root, "docs/roadmap.md", old, new)
                    with self.assertRaisesRegex(RebaselineError, "reordered"):
                        check_rebaseline(root)

    def test_production_ha_enterprise_iam_and_compliance_overclaims_are_rejected(self) -> None:
        claims = (
            "v0.2 is production-ready.",
            "v0.2 supports high availability.",
            "v0.2 implements enterprise IAM.",
            "v0.2 is compliance-certified.",
        )
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-overclaim-") as name:
            temporary = Path(name)
            for index, claim in enumerate(claims):
                with self.subTest(claim=claim):
                    root = copy_documents(temporary / str(index))
                    path = root / "README.md"
                    path.write_text(
                        path.read_text(encoding="utf-8") + "\n" + claim + "\n", encoding="utf-8"
                    )
                    with self.assertRaisesRegex(RebaselineError, "unsafe"):
                        check_rebaseline(root)

    def test_mock_or_loopback_cannot_be_promoted_to_live_private(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-live-") as name:
            root = copy_documents(Path(name))
            path = root / "README.md"
            path.write_text(
                path.read_text(encoding="utf-8")
                + "\nMock or loopback counts as live_private acceptance.\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RebaselineError, "unsafe"):
                check_rebaseline(root)

    def test_package_self_grant_executable_skill_memory_and_collaboration_claims_fail(self) -> None:
        claims = (
            "AgentPackage is an executable S4 Skill.",
            "AgentPackage can self-grant authority.",
            "AgentPackage self-activates after installation.",
            "Source context is persistent Semantic Memory.",
            "Ten deployments enable S3 Agent collaboration.",
            "AutomaticEffectAuthorization is a HumanApprovalDecision.",
        )
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-abuse-") as name:
            temporary = Path(name)
            for index, claim in enumerate(claims):
                with self.subTest(claim=claim):
                    root = copy_documents(temporary / str(index))
                    path = root / "README.md"
                    path.write_text(
                        path.read_text(encoding="utf-8") + "\n" + claim + "\n", encoding="utf-8"
                    )
                    with self.assertRaisesRegex(RebaselineError, "unsafe"):
                        check_rebaseline(root)

    def test_secret_storage_controls_are_all_required(self) -> None:
        markers = (
            "FileVault",
            "`0700`",
            "`0600`",
            "read-only service mount",
            "environment",
            "SQLite",
        )
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-secrets-") as name:
            temporary = Path(name)
            for index, marker in enumerate(markers):
                with self.subTest(marker=marker):
                    root = copy_documents(temporary / str(index))
                    _replace_everywhere(root, marker, "REMOVED_CONTROL")
                    with self.assertRaisesRegex(RebaselineError, "privacy boundary"):
                        check_rebaseline(root)

    def test_p15_live_prerequisites_are_complete(self) -> None:
        markers = (
            "two Microsoft 365 test tenants",
            "ten dedicated Agent test accounts",
            "one usable OpenAI test project",
            "verified project multi-tenant Entra public-client App",
            "BYO single-tenant App",
            "user-consent",
            "Admin-consent",
        )
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-prerequisites-") as name:
            temporary = Path(name)
            for index, marker in enumerate(markers):
                with self.subTest(marker=marker):
                    root = copy_documents(temporary / str(index))
                    _replace_everywhere(root, marker, "REMOVED_PREREQUISITE")
                    with self.assertRaisesRegex(RebaselineError, "live prerequisites"):
                        check_rebaseline(root)

    def test_external_register_rejects_nonofficial_domain_and_silent_model_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-dependencies-") as name:
            temporary = Path(name)
            unofficial = copy_documents(temporary / "unofficial")
            path = unofficial / "docs/product/v0.2-external-dependency-register.md"
            path.write_text(
                path.read_text(encoding="utf-8") + "\nhttps://example.invalid/provider\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RebaselineError, "non-official"):
                check_rebaseline(unofficial)

            changed_model = copy_documents(temporary / "model")
            _replace(
                changed_model,
                "docs/product/v0.2-external-dependency-register.md",
                "gpt-5.5",
                "gpt-unapproved",
            )
            with self.assertRaises(RebaselineError):
                check_rebaseline(changed_model)

    def test_unapproved_evidence_class_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-evidence-class-") as name:
            root = copy_documents(Path(name))
            path = root / "docs/product/v0.2-public-pilot-capability-matrix.md"
            path.write_text(
                path.read_text(encoding="utf-8") + "\n| Invalid evidence | `production_live` |\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RebaselineError, "unapproved evidence class"):
                check_rebaseline(root)

    def test_local_path_credential_private_marker_and_live_identifier_are_rejected(self) -> None:
        values = (
            "/" + "Users/example/private/project",
            "sk" + "-examplecredential123456",
            "PRIVATE_LIVE_RECEIPT",
            "tenant_id=12345678-1234-1234-1234-123456789abc",
        )
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-private-") as name:
            temporary = Path(name)
            for index, value in enumerate(values):
                with self.subTest(value=value):
                    root = copy_documents(temporary / str(index))
                    path = root / "README.md"
                    path.write_text(
                        path.read_text(encoding="utf-8") + "\n" + value + "\n", encoding="utf-8"
                    )
                    with self.assertRaises(RebaselineError):
                        check_rebaseline(root)


if __name__ == "__main__":
    unittest.main()
