# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.check_p11r_repository import SUMMARY_PATH, P11RGateError
from scripts.collect_p11r_evidence import (
    CLAIM,
    STATUS,
    _successful_pr_run,
    _tree_digest,
    write_evidence,
)


class _Response:
    def __init__(self, value: object) -> None:
        self._stream = io.BytesIO(json.dumps(value).encode("utf-8"))

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._stream.read()


class EvidenceGateTests(unittest.TestCase):
    def test_claim_and_status_are_narrow_candidate_vocabulary(self) -> None:
        self.assertEqual(CLAIM, "p11r_post_p11_governance_and_ci_alignment_candidate")
        self.assertEqual(STATUS, "development_complete_awaiting_independent_acceptance")

    def test_tree_digest_is_deterministic_and_path_framed(self) -> None:
        with TemporaryDirectory() as value:
            root = Path(value)
            (root / "a").write_text("bc", encoding="utf-8")
            (root / "ab").write_text("c", encoding="utf-8")
            first = _tree_digest(root, ("a", "ab"))
            second = _tree_digest(root, ("a", "ab"))
            reversed_digest = _tree_digest(root, ("ab", "a"))
        self.assertEqual(first, second)
        self.assertNotEqual(first, reversed_digest)

    def test_writer_creates_only_the_summary_path(self) -> None:
        with TemporaryDirectory() as value:
            root = Path(value)
            write_evidence(root, {"schema_version": 1, "status": STATUS})
            files = [str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()]
            payload = json.loads((root / SUMMARY_PATH).read_text(encoding="utf-8"))
        self.assertEqual(files, [SUMMARY_PATH])
        self.assertEqual(payload["status"], STATUS)

    def test_successful_pr_run_is_bound_to_exact_head(self) -> None:
        head = "a" * 40
        payload = {
            "workflow_runs": [
                {
                    "id": 123,
                    "html_url": "https://github.com/example/project/actions/runs/123",
                    "head_sha": head,
                    "event": "pull_request",
                    "status": "completed",
                    "conclusion": "success",
                }
            ]
        }
        with patch("urllib.request.urlopen", return_value=_Response(payload)):
            result = _successful_pr_run(head)
        self.assertEqual(result["head_sha"], head)
        self.assertEqual(result["conclusion"], "success")

    def test_failed_pr_run_is_rejected(self) -> None:
        head = "b" * 40
        payload = {
            "workflow_runs": [
                {
                    "id": 124,
                    "html_url": "https://github.com/example/project/actions/runs/124",
                    "head_sha": head,
                    "event": "pull_request",
                    "status": "completed",
                    "conclusion": "failure",
                }
            ]
        }
        with patch("urllib.request.urlopen", return_value=_Response(payload)):
            with self.assertRaises(P11RGateError):
                _successful_pr_run(head)

    def test_wrong_head_pr_run_is_rejected(self) -> None:
        payload = {
            "workflow_runs": [
                {
                    "id": 125,
                    "html_url": "https://github.com/example/project/actions/runs/125",
                    "head_sha": "c" * 40,
                    "event": "pull_request",
                    "status": "completed",
                    "conclusion": "success",
                }
            ]
        }
        with patch("urllib.request.urlopen", return_value=_Response(payload)):
            with self.assertRaises(P11RGateError):
                _successful_pr_run("d" * 40)

    def test_duplicate_successful_pr_runs_are_rejected(self) -> None:
        head = "e" * 40
        run = {
            "id": 126,
            "html_url": "https://github.com/example/project/actions/runs/126",
            "head_sha": head,
            "event": "pull_request",
            "status": "completed",
            "conclusion": "success",
        }
        with patch("urllib.request.urlopen", return_value=_Response({"workflow_runs": [run, run]})):
            with self.assertRaises(P11RGateError):
                _successful_pr_run(head)

    def test_malformed_remote_response_is_rejected(self) -> None:
        with patch("urllib.request.urlopen", return_value=_Response({"unknown": []})):
            with self.assertRaises(P11RGateError):
                _successful_pr_run("f" * 40)


if __name__ == "__main__":
    unittest.main()
