# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.fingerprint_source_tree import (
    DEFAULT_SOURCE_REVISION,
    FingerprintError,
    _fingerprint_worktree_entries,
    fingerprint_source_tree,
)


class SourceFingerprintTests(unittest.TestCase):
    def test_untracked_and_ignored_content_changes_affect_aggregate_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "untracked.txt").write_text("first value", encoding="utf-8")
            (root / "ignored.bin").write_bytes(b"ignored-first")
            untracked_before = _fingerprint_worktree_entries(root, b"untracked.txt\0")
            ignored_before = _fingerprint_worktree_entries(root, b"ignored.bin\0")

            (root / "untracked.txt").write_text("second value", encoding="utf-8")
            (root / "ignored.bin").write_bytes(b"ignored-second")
            untracked_after = _fingerprint_worktree_entries(root, b"untracked.txt\0")
            ignored_after = _fingerprint_worktree_entries(root, b"ignored.bin\0")

        self.assertEqual(untracked_before[0], 1)
        self.assertEqual(ignored_before[0], 1)
        self.assertNotEqual(untracked_before[1], untracked_after[1])
        self.assertNotEqual(ignored_before[1], ignored_after[1])

    def test_fingerprint_output_contains_only_aggregate_worktree_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "untracked.txt").write_text("private-test-value", encoding="utf-8")
            (root / "ignored.bin").write_bytes(b"private-ignored-value")

            def fake_git(_source: Path, *arguments: str) -> bytes:
                if arguments[:2] == ("cat-file", "-e"):
                    return b""
                if arguments == ("rev-parse", "HEAD"):
                    return (b"a" * 40) + b"\n"
                if arguments[0] == "status":
                    return b"? untracked.txt\0! ignored.bin\0"
                if arguments[0] == "diff":
                    return b""
                if arguments[0] == "ls-files" and "--ignored" in arguments:
                    return b"ignored.bin\0"
                if arguments[0] == "ls-files":
                    return b"untracked.txt\0"
                raise AssertionError("unexpected Git invocation")

            with patch("scripts.fingerprint_source_tree._git", side_effect=fake_git):
                result = fingerprint_source_tree(
                    root,
                    source_label="public-source-label",
                    source_revision=DEFAULT_SOURCE_REVISION,
                    excluded_subtree="authorized-target",
                )

        serialized = json.dumps(result, sort_keys=True)
        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["untracked_entry_count"], 1)
        self.assertEqual(result["ignored_entry_count"], 1)
        self.assertNotIn("untracked.txt", serialized)
        self.assertNotIn("ignored.bin", serialized)
        self.assertNotIn("private-test-value", serialized)
        self.assertNotIn("private-ignored-value", serialized)

    def test_unsafe_entry_error_does_not_echo_the_entry(self) -> None:
        unsafe = b"../sensitive-name"
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(FingerprintError) as raised:
                _fingerprint_worktree_entries(Path(temporary), unsafe + b"\0")
        self.assertEqual(str(raised.exception), "source worktree enumeration was unsafe")
        self.assertNotIn("sensitive-name", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
