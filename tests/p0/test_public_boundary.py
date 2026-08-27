# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts.check_public_boundary import BoundaryError, Violation, main, scan_tree

PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY = json.loads(
    (PROJECT_ROOT / "provenance" / "scanner-policy.json").read_text(encoding="utf-8")
)
EXCEPTIONS = json.loads(
    (PROJECT_ROOT / "provenance" / "scanner-exceptions.json").read_text(encoding="utf-8")
)


class PublicBoundaryTests(unittest.TestCase):
    def scan_text(
        self,
        content: str,
        *,
        policy: dict[str, object] | None = None,
        exceptions: dict[str, object] | None = None,
    ) -> set[str]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "candidate.txt").write_text(content, encoding="utf-8")
            violations, _, _, _ = scan_tree(
                root,
                policy_document=policy or POLICY,
                exception_document=exceptions or EXCEPTIONS,
            )
        return {violation.rule_id for violation in violations}

    def test_current_project_is_clean_with_zero_exceptions(self) -> None:
        self.assertEqual(EXCEPTIONS["exceptions"], [])
        violations, file_count, total_bytes, exceptions_applied = scan_tree(
            PROJECT_ROOT,
            policy_document=POLICY,
            exception_document=EXCEPTIONS,
        )
        self.assertEqual(violations, [])
        self.assertGreater(file_count, 20)
        self.assertGreater(total_bytes, 1_000)
        self.assertEqual(exceptions_applied, 0)

    def test_excludes_root_git_directory_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".git").mkdir()
            (root / ".git" / "private-metadata").write_text(
                "person" + "@" + "example" + "." + "invalid", encoding="utf-8"
            )
            (root / ".github").mkdir()
            (root / ".github" / "workflow.yml").write_text("clean", encoding="utf-8")

            violations, file_count, _, _ = scan_tree(
                root,
                policy_document=POLICY,
                exception_document=EXCEPTIONS,
            )

        self.assertEqual(file_count, 1)
        self.assertEqual(violations, [])

    def test_valid_root_worktree_git_pointer_is_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".git").write_text(
                "gitdir: ../administrative/worktrees/example\n", encoding="utf-8"
            )
            (root / "public.txt").write_text("clean", encoding="utf-8")

            violations, file_count, _, _ = scan_tree(
                root,
                policy_document=POLICY,
                exception_document=EXCEPTIONS,
            )

        self.assertEqual(violations, [])
        self.assertEqual(file_count, 1)

    def test_malformed_root_git_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".git").write_text("arbitrary administrative content\n", encoding="utf-8")

            with self.assertRaisesRegex(
                BoundaryError, "the root Git administrative entry is invalid"
            ):
                scan_tree(
                    root,
                    policy_document=POLICY,
                    exception_document=EXCEPTIONS,
                )

    def test_root_git_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            os.symlink("administrative-target", root / ".git")

            with self.assertRaisesRegex(
                BoundaryError, "the root Git administrative entry is invalid"
            ):
                scan_tree(
                    root,
                    policy_document=POLICY,
                    exception_document=EXCEPTIONS,
                )

    def test_nested_git_path_remains_in_scan_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "nested" / ".git").mkdir(parents=True)
            (root / "nested" / ".git" / "public-file.txt").write_text(
                "person" + "@" + "example" + "." + "invalid", encoding="utf-8"
            )

            violations, file_count, _, _ = scan_tree(
                root,
                policy_document=POLICY,
                exception_document=EXCEPTIONS,
            )

        self.assertEqual(file_count, 1)
        self.assertEqual(
            violations,
            [Violation("nested/.git/public-file.txt", "EMAIL_ADDRESS")],
        )

    def test_worktree_pointer_path_is_never_reported(self) -> None:
        private_pointer = "/" + "Users" + "/" + "operator" + "/private-worktree"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".git").write_text(
                "gitdir: " + private_pointer + "\ninvalid-second-line\n", encoding="utf-8"
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main([str(root)])

        combined = stdout.getvalue() + stderr.getvalue()
        self.assertEqual(exit_code, 2)
        self.assertNotIn(private_pointer, combined)
        self.assertNotIn("private-worktree", combined)
        self.assertIn("root Git administrative entry is invalid", combined)

    def test_rejects_local_source_location(self) -> None:
        private_location = "/" + "Users" + "/" + "operator" + "/checkout"
        self.assertIn("LOCAL_PATH", self.scan_text(private_location))

    def test_rejects_contact_address(self) -> None:
        contact = "person" + "@" + "example" + "." + "invalid"
        self.assertIn("EMAIL_ADDRESS", self.scan_text(contact))

    def test_rejects_structured_personal_colleague_identifier(self) -> None:
        key = "colleague" + "_id"
        content = json.dumps({key: "personal-001"})
        self.assertIn("PERSONAL_IDENTIFIER", self.scan_text(content))

    def test_rejects_provider_identifier(self) -> None:
        provider_identifier = "T" + "12345678"
        self.assertIn("PROVIDER_IDENTIFIER", self.scan_text(provider_identifier))

    def test_rejects_credential_pattern(self) -> None:
        credential = "sk" + "-" + ("a" * 24)
        self.assertIn("CREDENTIAL_PATTERN", self.scan_text(credential))

    def test_rejects_private_key_marker(self) -> None:
        marker = "-----BEGIN " + "PRIVATE KEY-----"
        self.assertIn("PRIVATE_KEY", self.scan_text(marker))

    def test_rejects_structured_live_receipt(self) -> None:
        key = "live" + "_receipt"
        self.assertIn("LIVE_RECEIPT", self.scan_text(json.dumps({key: "value"})))

    def test_rejects_structured_personal_acceptance(self) -> None:
        key = "human" + "_acceptance"
        self.assertIn("PERSONAL_ACCEPTANCE", self.scan_text(json.dumps({key: True})))

    def test_rejects_known_private_marker_digest(self) -> None:
        marker = "private" + "-marker-for-test"
        policy = copy.deepcopy(POLICY)
        policy["known_private_marker_digests"] = [
            hashlib.sha256(marker.casefold().encode("utf-8")).hexdigest()
        ]
        self.assertIn("PERSONAL_IDENTIFIER", self.scan_text(marker, policy=policy))

    def test_exception_globs_are_forbidden(self) -> None:
        exception_document = {
            "schema_version": 1,
            "policy_version": "p0-v1",
            "exceptions": [
                {
                    "path": "docs/" + "*" + ".md",
                    "rule_id": "EMAIL_ADDRESS",
                    "digest": "sha256:" + ("0" * 64),
                    "reason": "This intentionally invalid broad exception is tested.",
                    "approved_by_role": "privacy_reviewer",
                }
            ],
        }
        with self.assertRaises(BoundaryError):
            self.scan_text("clean", exceptions=exception_document)

    def test_digest_bound_exception_is_exact_and_auditable(self) -> None:
        contact = "person" + "@" + "example" + "." + "invalid"
        digest = "sha256:" + hashlib.sha256(contact.encode("utf-8")).hexdigest()
        exception_document = {
            "schema_version": 1,
            "policy_version": "p0-v1",
            "exceptions": [
                {
                    "path": "candidate.txt",
                    "rule_id": "EMAIL_ADDRESS",
                    "digest": digest,
                    "reason": "Exact test-only exception demonstrates digest binding.",
                    "approved_by_role": "privacy_reviewer",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "candidate.txt").write_text(contact, encoding="utf-8")
            violations, _, _, exceptions_applied = scan_tree(
                root,
                policy_document=POLICY,
                exception_document=exception_document,
            )
        self.assertEqual(violations, [])
        self.assertEqual(exceptions_applied, 1)


if __name__ == "__main__":
    unittest.main()
