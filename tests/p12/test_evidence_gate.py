# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
import os
import ssl
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_p12_repository import SUMMARY_PATH, CommitRecord, P12GateError
from scripts.collect_p12_evidence import (
    CLAIM,
    NOT_EVALUATED,
    STATUS,
    canonical_json,
    implementation_range_digest,
    validate_authorization,
    write_evidence,
)
from scripts.run_p12_toolchain import (
    ROOT,
    ca_fallback_allowed,
    validate_package_inventory,
    write_preflight_receipt,
)


class EvidenceGateTests(unittest.TestCase):
    def _authorization(self, expiry: datetime) -> dict[str, object]:
        return {
            "schema_version": 1,
            "stage": "p12_evidence_authorization",
            "receipt_sha256": "a" * 64,
            "implementation_head": "b" * 40,
            "ci_run_id": 123,
            "expires_at": expiry.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        }

    def test_claim_and_status_are_narrow(self) -> None:
        self.assertEqual(CLAIM, "p12_public_pilot_continuity_rebaseline_candidate")
        self.assertEqual(STATUS, "development_complete_awaiting_independent_acceptance")
        self.assertIn("Public Pilot readiness", NOT_EVALUATED)

    def test_canonical_json_is_sorted_compact_utf8(self) -> None:
        self.assertEqual(canonical_json({"b": 1, "a": "臺"}), b'{"a":"\xe8\x87\xba","b":1}')

    def test_range_digest_is_order_sensitive_and_prefixed(self) -> None:
        first: CommitRecord = {
            "commit": "1",
            "parent": "0",
            "tree": "a",
            "changed_paths": ("a",),
        }
        second: CommitRecord = {
            "commit": "2",
            "parent": "1",
            "tree": "b",
            "changed_paths": ("b",),
        }
        digest = implementation_range_digest((first, second))
        self.assertTrue(digest.startswith("sha256:"))
        self.assertNotEqual(digest, implementation_range_digest((second, first)))

    def test_valid_unexpired_authorization_passes(self) -> None:
        now = datetime(2030, 1, 1, tzinfo=UTC)
        value = self._authorization(now + timedelta(minutes=10))
        result = validate_authorization(
            value,
            receipt_sha256="a" * 64,
            implementation_head="b" * 40,
            ci_run_id=123,
            now=now,
        )
        self.assertEqual(result["ci_run_id"], 123)

    def test_expired_authorization_fails_closed(self) -> None:
        now = datetime(2030, 1, 1, tzinfo=UTC)
        with self.assertRaises(P12GateError):
            validate_authorization(
                self._authorization(now),
                receipt_sha256="a" * 64,
                implementation_head="b" * 40,
                ci_run_id=123,
                now=now,
            )

    def test_authorization_for_another_head_fails_closed(self) -> None:
        now = datetime(2030, 1, 1, tzinfo=UTC)
        with self.assertRaises(P12GateError):
            validate_authorization(
                self._authorization(now + timedelta(minutes=10)),
                receipt_sha256="a" * 64,
                implementation_head="c" * 40,
                ci_run_id=123,
                now=now,
            )

    def test_writer_creates_only_summary(self) -> None:
        with TemporaryDirectory() as value:
            root = Path(value)
            write_evidence(root, {"schema_version": 1, "status": STATUS})
            files = [str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()]
        self.assertEqual(files, [SUMMARY_PATH])

    def test_writer_refuses_existing_summary(self) -> None:
        with TemporaryDirectory() as value:
            root = Path(value)
            write_evidence(root, {"schema_version": 1})
            with self.assertRaises(P12GateError):
                write_evidence(root, {"schema_version": 1})

    def test_preflight_receipt_is_canonical_mode_0600(self) -> None:
        with TemporaryDirectory() as value:
            directory = Path(value) / "receipt"
            directory.mkdir(mode=0o700)
            path, digest = write_preflight_receipt(directory, {"schema_version": 1})
            encoded = path.read_bytes()
            self.assertEqual(oct(os.stat(path).st_mode & 0o777), "0o600")
            self.assertEqual(hashlib.sha256(encoded).hexdigest(), digest)
            self.assertEqual(encoded, canonical_json(json.loads(encoded), newline=True))

    def test_preflight_receipt_refuses_nonempty_directory(self) -> None:
        with TemporaryDirectory() as value:
            directory = Path(value) / "receipt"
            directory.mkdir(mode=0o700)
            (directory / "existing").write_text("x", encoding="utf-8")
            with self.assertRaises(P12GateError):
                write_preflight_receipt(directory, {"schema_version": 1})

    def test_preflight_receipt_refuses_repository_path(self) -> None:
        with self.assertRaises(P12GateError):
            write_preflight_receipt(ROOT / "artifacts/p12/preflight", {"schema_version": 1})

    def test_exact_ghcr_inventory_passes(self) -> None:
        expected = [
            {
                "id": 1,
                "name": "sha256:" + "a" * 64,
                "tags": ["sha-example"],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        ]
        actual = [
            [
                {
                    "id": 1,
                    "name": expected[0]["name"],
                    "metadata": {"container": {"tags": ["sha-example"]}},
                    "created_at": expected[0]["created_at"],
                    "updated_at": expected[0]["updated_at"],
                }
            ]
        ]
        validate_package_inventory(actual, expected)

    def test_extra_ghcr_inventory_entry_fails_closed(self) -> None:
        with self.assertRaises(P12GateError):
            validate_package_inventory([], [{"id": 1}])

    def test_tls_ca_fallback_allows_only_certificate_failure(self) -> None:
        self.assertTrue(ca_fallback_allowed(ssl.SSLCertVerificationError(1, "certificate")))
        self.assertFalse(ca_fallback_allowed(TimeoutError("timeout")))

    def test_public_evidence_vocabulary_contains_no_live_claim(self) -> None:
        serialized = json.dumps({"claim": CLAIM, "not_evaluated": NOT_EVALUATED})
        self.assertNotIn("live_compatibility_passed", serialized)
        self.assertNotIn("production_ready", serialized)


if __name__ == "__main__":
    unittest.main()
