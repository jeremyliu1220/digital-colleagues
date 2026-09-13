# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import os
import ssl
import subprocess
import unittest
import urllib.error
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest import mock

from scripts.check_p12_repository import (
    ACCEPTANCE_COMMIT,
    BASE_COMMIT,
    BRANCH,
    SUMMARY_PATH,
    CommitRecord,
    P12GateError,
)
from scripts.collect_p12_evidence import (
    CLAIM,
    NOT_EVALUATED,
    PLATFORM_STATUS,
    STATUS,
    _consume_handoffs,
    _exact_json_equal,
    _external_file,
    _read_external_bytes,
    _validate_jobs,
    _validate_receipt_handoff,
    canonical_json,
    collect,
    implementation_range_digest,
    parse_json_unique,
    validate_authorization,
    write_evidence,
)
from scripts.run_p12_toolchain import (
    ENVELOPE_PREFIX,
    GATE_RESULT_MAX_BYTES,
    P12_TEST_IDS,
    ROOT,
    _emit,
    _load_gate_result,
    _safe,
    _stream_job_envelope,
    _write_safe_projection,
    ca_fallback_allowed,
    current_p11_test_ids,
    decode_ci_envelope_line,
    encode_ci_envelope,
    extract_ci_envelope,
    run_current_ci,
    run_p12_tests,
    validate_ci_envelope,
    validate_ci_envelope_pair,
    validate_live_v4_pr_metadata,
    validate_package_inventory,
    write_preflight_receipt,
)
from scripts.run_p12_toolchain import main as toolchain_main


class _IterationOnlyLog:
    """A log source that fails if an implementation tries to retain it wholesale."""

    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self._lines)

    def read(self, *_args: object, **_kwargs: object) -> bytes:
        raise AssertionError("the complete Actions log must not be read into memory")


class EvidenceGateTests(unittest.TestCase):
    HEAD = "b" * 40
    RUN_ID = 123456789
    RUN_ATTEMPT = 2
    inventory_bytes: bytes
    inventory: list[dict[str, Any]]
    item_results: list[dict[str, object]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory_bytes = (ROOT / "docs/p12/portable-historical-inventory.json").read_bytes()
        parsed = parse_json_unique(cls.inventory_bytes)
        if not isinstance(parsed, list) or any(not isinstance(item, dict) for item in parsed):
            raise AssertionError("the P12 portable inventory fixture must be an array")
        cls.inventory = parsed
        cls.item_results = []
        for item in cls.inventory:
            item_type = item["item_type"]
            if item_type in {"setup", "included_acceptance_gate"}:
                result, status = "passed", 0
            elif item_type == "evidence_anchor":
                result, status = "identity_verified", None
            elif item_type == "excluded_acceptance_gate":
                result, status = "not_run_platform_excluded", None
            else:
                raise AssertionError("the P12 portable inventory fixture type is invalid")
            compact: dict[str, object] = {
                "gate_id": item["gate_id"],
                "item_type": item_type,
                "result": result,
                "exit_status": status,
            }
            if item_type == "excluded_acceptance_gate":
                compact["platform_result"] = {
                    **item["expected"],
                    "reason": item["reason"],
                }
                compact["embedded_anchor"] = item["embedded_anchor"]
            cls.item_results.append(compact)

    def _authorization(self, expiry: datetime) -> dict[str, object]:
        return {
            "schema_version": 1,
            "stage": "p12_evidence_authorization",
            "receipt_sha256": "a" * 64,
            "implementation_head": self.HEAD,
            "ci_run_id": self.RUN_ID,
            "ci_run_attempt": self.RUN_ATTEMPT,
            "envelope_digests": {
                "current-ci": "c" * 64,
                "portable-history": "d" * 64,
            },
            "expires_at": expiry.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        }

    def _envelope(self, job_id: str) -> dict[str, object]:
        portable = job_id == "portable-history"
        if job_id not in {"current-ci", "portable-history"}:
            raise AssertionError("unknown synthetic P12 job")
        item_results = copy.deepcopy(self.item_results) if portable else []
        inventory_digest = hashlib.sha256(canonical_json(self.inventory)).hexdigest()
        return {
            "base_ref": "main",
            "base_sha": BASE_COMMIT,
            "cleanup_residue_count": 0,
            "contracted_runner_family": "ubuntu-24.04",
            "event": "pull_request",
            "gate": {
                "error_count": 0,
                "failure_count": 0,
                "gate_id": ("p12_portable_historical_replay" if portable else "p12_current_ci"),
                "result_digest": "sha256:" + hashlib.sha256(job_id.encode()).hexdigest(),
                "skip_count": 0,
                "status": "passed",
                "test_count": 616 if portable else 136,
                "test_count_semantics": (
                    "historical_python_unittest_cases"
                    if portable
                    else "p12_governance_unittest_methods"
                ),
            },
            "head_branch": "codex/p12-public-pilot-continuity-rebaseline-v4",
            "head_sha": self.HEAD,
            "inventory": {
                "evidence_anchor_count": 17,
                "excluded_acceptance_gate_count": 5,
                "excluded_gate_ids": [
                    "p8_compose_runtime",
                    "p8_golden_path",
                    "p10_compose_runtime",
                    "p10_quickstart",
                    "p10_remote_distribution",
                ],
                "execution_status": "passed" if portable else "bound_not_executed_by_this_job",
                "included_acceptance_gate_count": 124,
                "inventory_blob": "e" * 40,
                "inventory_digest": f"sha256:{inventory_digest}",
                "inventory_path": "docs/p12/portable-historical-inventory.json",
                "inventory_sha256": hashlib.sha256(self.inventory_bytes).hexdigest(),
                "item_results": item_results,
                "item_results_digest": "sha256:"
                + hashlib.sha256(canonical_json(item_results)).hexdigest(),
                "passed_acceptance_gate_count": 124 if portable else None,
                "setup_count": 5,
                "skip_count": 0,
                "total_item_count": 151,
            },
            "job_id": job_id,
            "job_name": (
                "Portable historical replay"
                if portable
                else "Current P12 governance non-publishing verification"
            ),
            "observed_environment": {
                "architecture": "X64",
                "docker_compose_version": "v5.4.0",
                "docker_server_version": "29.7.2",
                "node_version": "v24.7.0",
                "npm_version": "11.5.1",
                "python_version": "Python 3.12.11",
                "runner_image_os": "ubuntu24",
                "runner_image_version": "20260907.1",
                "runner_os": "Linux",
            },
            "p12_current_p10_registry_protection": {
                "reason": "evidence_preflight_only",
                "status": "not_evaluated",
            },
            "platform_status": {
                "linux_public_pilot_readiness": "blocked",
                "p12_governance_result": "passed",
                "ubuntu_historical_execution_status": {
                    gate_id: "not_proven"
                    for gate_id in (
                        "p8_compose_runtime",
                        "p8_golden_path",
                        "p10_compose_runtime",
                        "p10_quickstart",
                        "p10_remote_distribution",
                    )
                },
            },
            "publication_count": 0,
            "pull_request_number": 15,
            "repository": "jeremyliu1220/digital-colleagues",
            "run_attempt": self.RUN_ATTEMPT,
            "run_id": self.RUN_ID,
            "schema": "digital-colleagues.p12-v4-ci-result-envelope.v1",
            "workflow_name": "CI",
            "workflow_path": ".github/workflows/ci.yml",
        }

    def _extract(self, envelope: dict[str, object], *, prefix: bytes = b"") -> dict[str, object]:
        line, _ = encode_ci_envelope(envelope)
        return extract_ci_envelope(
            io.BytesIO(prefix + line.encode("ascii") + b"\n"),
            run_id=self.RUN_ID,
            attempt=self.RUN_ATTEMPT,
            job_database_id=987,
            expected_job_id=str(envelope["job_id"]),
            expected_job_name=str(envelope["job_name"]),
            head_sha=self.HEAD,
        )

    def _refresh_item_digest(self, envelope: dict[str, object]) -> None:
        inventory = envelope.get("inventory")
        assert isinstance(inventory, dict)
        item_results = inventory.get("item_results")
        assert isinstance(item_results, list)
        inventory["item_results_digest"] = (
            "sha256:" + hashlib.sha256(canonical_json(item_results)).hexdigest()
        )

    def test_claim_and_status_are_narrow(self) -> None:
        self.assertEqual(CLAIM, "p12_v4_historical_platform_classification_candidate")
        self.assertEqual(STATUS, "development_complete_awaiting_independent_acceptance")
        self.assertEqual(
            NOT_EVALUATED,
            {
                "human_evaluation": "not_evaluated",
                "microsoft_365": "not_evaluated",
                "openai": "not_evaluated",
                "release": "not_evaluated",
                "soak": "not_evaluated",
            },
        )
        self.assertEqual(
            PLATFORM_STATUS["ubuntu_historical_execution_status"],
            "five_excluded_not_proven",
        )
        self.assertEqual(PLATFORM_STATUS["linux_public_pilot_readiness"], "blocked")

    def test_canonical_json_is_sorted_compact_utf8(self) -> None:
        self.assertEqual(
            canonical_json({"b": 1, "e\u0301": "臺"}),
            b'{"b":1,"\xc3\xa9":"\xe8\x87\xba"}',
        )
        self.assertFalse(canonical_json({"a": 1}).endswith(b"\n"))
        with self.assertRaises(P12GateError):
            canonical_json({"floating": 1.0})
        with self.assertRaises(P12GateError):
            parse_json_unique(b'{"a":1,"a":2}')
        self.assertFalse(_exact_json_equal({"exit_status": False}, {"exit_status": 0}))
        self.assertTrue(_exact_json_equal({"exit_status": 0}, {"exit_status": 0}))

    def test_range_digest_is_order_sensitive_and_prefixed(self) -> None:
        first: CommitRecord = {
            "commit": ACCEPTANCE_COMMIT,
            "parent": BASE_COMMIT,
            "tree": "a" * 40,
            "message_sha256": "b" * 64,
            "changes": [],
        }
        second: CommitRecord = {
            "commit": "c" * 40,
            "parent": ACCEPTANCE_COMMIT,
            "tree": "d" * 40,
            "message_sha256": "e" * 64,
            "changes": [],
        }
        digest = implementation_range_digest((first, second))
        self.assertTrue(digest.startswith("sha256:"))
        with self.assertRaises(P12GateError):
            implementation_range_digest((second, first))

    def test_valid_unexpired_authorization_passes(self) -> None:
        now = datetime(2030, 1, 1, tzinfo=UTC)
        authorization = self._authorization(now + timedelta(minutes=10))
        result = validate_authorization(
            authorization,
            receipt_sha256="a" * 64,
            implementation_head=self.HEAD,
            ci_run_id=self.RUN_ID,
            ci_run_attempt=self.RUN_ATTEMPT,
            envelope_digests={"current-ci": "c" * 64, "portable-history": "d" * 64},
            now=now,
        )
        self.assertEqual(result["ci_run_attempt"], self.RUN_ATTEMPT)
        for field in ("schema_version", "ci_run_id", "ci_run_attempt"):
            for boolean in (False, True):
                with self.subTest(field=field, boolean=boolean):
                    malformed = dict(authorization)
                    malformed[field] = boolean
                    run_id: int = self.RUN_ID
                    attempt: int = self.RUN_ATTEMPT
                    if field == "ci_run_id":
                        run_id = boolean
                    elif field == "ci_run_attempt":
                        attempt = boolean
                    with self.assertRaises(P12GateError):
                        validate_authorization(
                            malformed,
                            receipt_sha256="a" * 64,
                            implementation_head=self.HEAD,
                            ci_run_id=run_id,
                            ci_run_attempt=attempt,
                            envelope_digests={
                                "current-ci": "c" * 64,
                                "portable-history": "d" * 64,
                            },
                            now=now,
                        )

    def test_expired_authorization_fails_closed(self) -> None:
        now = datetime(2030, 1, 1, tzinfo=UTC)
        with self.assertRaises(P12GateError):
            validate_authorization(
                self._authorization(now),
                receipt_sha256="a" * 64,
                implementation_head=self.HEAD,
                ci_run_id=self.RUN_ID,
                ci_run_attempt=self.RUN_ATTEMPT,
                envelope_digests={"current-ci": "c" * 64, "portable-history": "d" * 64},
                now=now,
            )

    def test_authorization_for_another_head_fails_closed(self) -> None:
        now = datetime(2030, 1, 1, tzinfo=UTC)
        with self.assertRaises(P12GateError):
            validate_authorization(
                self._authorization(now + timedelta(minutes=10)),
                receipt_sha256="a" * 64,
                implementation_head="f" * 40,
                ci_run_id=self.RUN_ID,
                ci_run_attempt=self.RUN_ATTEMPT,
                envelope_digests={"current-ci": "c" * 64, "portable-history": "d" * 64},
                now=now,
            )

    def test_writer_creates_only_summary(self) -> None:
        with TemporaryDirectory() as value:
            root = Path(value)
            summary = {"schema_version": 1, "status": STATUS}
            write_evidence(root, summary)
            summary_path = root / SUMMARY_PATH
            encoded = summary_path.read_bytes()
            metadata = os.lstat(summary_path)
            files = sorted(
                str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()
            )
        self.assertEqual(files, [SUMMARY_PATH])
        self.assertEqual(encoded, canonical_json(summary))
        self.assertFalse(encoded.endswith(b"\n"))
        self.assertEqual(metadata.st_nlink, 1)
        self.assertEqual(metadata.st_mode & 0o777, 0o600)

        with TemporaryDirectory() as value:
            root = Path(value)
            summary = {"schema_version": 1, "status": STATUS}
            real_write = os.write
            write_count = 0

            def short_write(descriptor: int, encoded: bytes) -> int:
                nonlocal write_count
                write_count += 1
                if write_count == 1 and len(encoded) > 1:
                    return real_write(descriptor, encoded[:1])
                return real_write(descriptor, encoded)

            with mock.patch("scripts.collect_p12_evidence.os.write", side_effect=short_write):
                write_evidence(root, summary)
            self.assertGreater(write_count, 1)
            self.assertEqual((root / SUMMARY_PATH).read_bytes(), canonical_json(summary))

    def test_writer_refuses_existing_summary(self) -> None:
        with TemporaryDirectory() as value:
            root = Path(value)
            write_evidence(root, {"schema_version": 1})
            with self.assertRaises(P12GateError):
                write_evidence(root, {"schema_version": 1})

        with TemporaryDirectory() as value:
            handoff_root = Path(value)
            receipt_directory = handoff_root / "receipt"
            authorization_directory = handoff_root / "authorization"
            receipt_directory.mkdir(mode=0o700)
            authorization_directory.mkdir(mode=0o700)
            receipt = receipt_directory / "p12-preflight-receipt.json"
            authorization = authorization_directory / "authorization.json"
            receipt.write_bytes(canonical_json({"nonce": "a" * 64}))
            authorization.write_bytes(canonical_json({"stage": "p12_evidence_authorization"}))
            receipt.chmod(0o600)
            authorization.chmod(0o600)
            with (
                _external_file(ROOT, str(receipt), mode=0o600) as receipt_handoff,
                _external_file(ROOT, str(authorization), mode=0o600) as authorization_handoff,
            ):
                _validate_receipt_handoff(receipt_handoff)
                _validate_receipt_handoff(authorization_handoff)
                (authorization_directory / "extra").write_bytes(b"extra")
                with self.assertRaises(P12GateError):
                    _validate_receipt_handoff(authorization_handoff)
                (authorization_directory / "extra").unlink()
                _consume_handoffs(receipt_handoff, authorization_handoff)
            self.assertFalse(receipt.exists())
            self.assertFalse(receipt_directory.exists())
            self.assertFalse(authorization.exists())
            self.assertFalse(authorization_directory.exists())
            with self.assertRaises(P12GateError):
                _external_file(ROOT, str(receipt), mode=0o600)
            with self.assertRaises(P12GateError):
                _external_file(ROOT, str(authorization), mode=0o600)

            failed_receipt_directory = handoff_root / "failed-recheck-receipt"
            failed_authorization_directory = handoff_root / "failed-recheck-authorization"
            failed_receipt_directory.mkdir(mode=0o700)
            failed_authorization_directory.mkdir(mode=0o700)
            failed_receipt = failed_receipt_directory / "receipt.json"
            failed_authorization = failed_authorization_directory / "authorization.json"
            failed_receipt.write_bytes(canonical_json({"nonce": "b" * 64}))
            failed_authorization.write_bytes(canonical_json({"stage": "invalid"}))
            failed_receipt.chmod(0o600)
            failed_authorization.chmod(0o600)
            with (
                mock.patch("scripts.collect_p12_evidence.git", return_value=BRANCH),
                mock.patch("scripts.collect_p12_evidence.check_repository"),
                mock.patch("scripts.collect_p12_evidence.check_historical_inventory"),
                mock.patch("scripts.collect_p12_evidence.check_provenance"),
                self.assertRaises(P12GateError),
            ):
                collect(
                    ROOT,
                    receipt_value=str(failed_receipt),
                    expected_digest="0" * 64,
                    authorization_value=str(failed_authorization),
                )
            self.assertFalse(failed_receipt.exists())
            self.assertFalse(failed_receipt_directory.exists())
            self.assertFalse(failed_authorization.exists())
            self.assertFalse(failed_authorization_directory.exists())

            summary_root = handoff_root / "summary-root"
            summary_root.mkdir()
            with (
                mock.patch(
                    "scripts.collect_p12_evidence.os.write",
                    return_value=0,
                ),
                self.assertRaises(P12GateError),
            ):
                write_evidence(summary_root, {"schema_version": 1})
            self.assertFalse((summary_root / SUMMARY_PATH).exists())
            self.assertFalse(
                any(path.name.startswith(".p12-summary-") for path in summary_root.rglob("*"))
            )

            race_root = handoff_root / "race-root"
            race_root.mkdir()
            competitor = b"competitor"
            real_link = os.link
            real_write = os.write

            def race_link(
                source: str,
                destination: str,
                *,
                src_dir_fd: int | None = None,
                dst_dir_fd: int | None = None,
                follow_symlinks: bool = True,
            ) -> None:
                if dst_dir_fd is None:
                    raise AssertionError("destination directory descriptor is required")
                descriptor = os.open(
                    destination,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                    dir_fd=dst_dir_fd,
                )
                try:
                    self.assertEqual(real_write(descriptor, competitor), len(competitor))
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                real_link(
                    source,
                    destination,
                    src_dir_fd=src_dir_fd,
                    dst_dir_fd=dst_dir_fd,
                    follow_symlinks=follow_symlinks,
                )

            with (
                mock.patch("scripts.collect_p12_evidence.os.link", side_effect=race_link),
                self.assertRaises(P12GateError),
            ):
                write_evidence(race_root, {"schema_version": 1})
            race_summary = race_root / SUMMARY_PATH
            self.assertEqual(race_summary.read_bytes(), competitor)
            self.assertEqual(
                sorted(path.name for path in race_summary.parent.iterdir()),
                ["summary.json"],
            )

            symlink_root = handoff_root / "symlink-root"
            outside = handoff_root / "outside"
            (symlink_root / "artifacts").mkdir(parents=True)
            outside.mkdir()
            (symlink_root / "artifacts/p12").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(P12GateError):
                write_evidence(symlink_root, {"schema_version": 1})
            self.assertFalse((outside / "summary.json").exists())

    def test_preflight_receipt_is_canonical_mode_0600(self) -> None:
        receipt = {
            "acceptance": {},
            "ca_verification": {},
            "ci": {},
            "cleanup_residue_count": 0,
            "expires_at": "2030-01-01T01:00:00Z",
            "implementation": {},
            "inventory": {},
            "issued_at": "2030-01-01T00:00:00Z",
            "lifecycle": "pending_consumption",
            "nonce": "a" * 64,
            "p10_protected_identity_digest": "sha256:" + "b" * 64,
            "p12_current_p10_registry_protection": {},
            "package_verification_digest": "sha256:" + "c" * 64,
            "platform_status": dict(PLATFORM_STATUS),
            "publication_count": 0,
            "repository": "jeremyliu1220/digital-colleagues",
            "schema": "digital-colleagues.p12-v4-evidence-preflight-receipt.v1",
        }
        with TemporaryDirectory() as value:
            directory = Path(value) / "receipt"
            directory.mkdir(mode=0o700)
            path, digest = write_preflight_receipt(directory, receipt)
            encoded = path.read_bytes()
            self.assertEqual(oct(os.stat(path).st_mode & 0o777), "0o600")
            self.assertEqual(hashlib.sha256(encoded).hexdigest(), digest)
            self.assertEqual(encoded, canonical_json(json.loads(encoded)))
            self.assertFalse(encoded.endswith(b"\n"))
            self.assertEqual([entry.name for entry in directory.iterdir()], [path.name])
            with self.assertRaises(P12GateError):
                write_preflight_receipt(directory, receipt)
            self.assertEqual(path.read_bytes(), encoded)

        real_write = os.write

        def partial_write(descriptor: int, data: bytes) -> int:
            return real_write(descriptor, data[: max(1, len(data) // 2)])

        with TemporaryDirectory() as value:
            directory = Path(value) / "receipt"
            directory.mkdir(mode=0o700)
            with mock.patch(
                "scripts.run_p12_toolchain.os.write",
                side_effect=partial_write,
            ):
                path, _ = write_preflight_receipt(directory, receipt)
            self.assertEqual(path.read_bytes(), canonical_json(receipt))
        with TemporaryDirectory() as value:
            directory = Path(value) / "receipt"
            directory.mkdir(mode=0o700)
            with (
                mock.patch("scripts.run_p12_toolchain.os.write", return_value=0),
                self.assertRaises(OSError),
            ):
                write_preflight_receipt(directory, receipt)
            self.assertEqual(list(directory.iterdir()), [])
        for field, invalid in (
            ("lifecycle", "consumed"),
            ("cleanup_residue_count", False),
            ("publication_count", False),
        ):
            with self.subTest(field=field), TemporaryDirectory() as value:
                malformed = dict(receipt)
                malformed[field] = invalid
                directory = Path(value) / "receipt"
                directory.mkdir(mode=0o700)
                with self.assertRaises(P12GateError):
                    write_preflight_receipt(directory, malformed)
        with TemporaryDirectory() as value:
            malformed = {**receipt, "unexpected": None}
            directory = Path(value) / "receipt"
            directory.mkdir(mode=0o700)
            with self.assertRaises(P12GateError):
                write_preflight_receipt(directory, malformed)

    def test_preflight_receipt_refuses_nonempty_directory(self) -> None:
        with TemporaryDirectory() as value:
            directory = Path(value) / "receipt"
            directory.mkdir(mode=0o700)
            (directory / "existing").write_text("x", encoding="utf-8")
            with self.assertRaises(P12GateError):
                write_preflight_receipt(directory, {"schema_version": 1})

        with TemporaryDirectory() as value:
            root = Path(value)
            receipt_directory = root / "receipt-handoff"
            receipt_directory.mkdir(mode=0o700)
            receipt = receipt_directory / "p12-preflight-receipt.json"
            encoded = canonical_json({"nonce": "a" * 64})
            receipt.write_bytes(encoded)
            receipt.chmod(0o600)
            (receipt_directory / "extra").write_bytes(b"extra")
            with _external_file(ROOT, str(receipt), mode=0o600) as handoff:
                self.assertEqual(_read_external_bytes(handoff), encoded)
                with self.assertRaises(P12GateError):
                    _validate_receipt_handoff(handoff)

        with TemporaryDirectory() as value:
            root = Path(value)
            receipt_directory = root / "receipt-handoff"
            receipt_directory.mkdir(mode=0o700)
            receipt = receipt_directory / "p12-preflight-receipt.json"
            saved = receipt_directory / "saved.json"
            receipt.write_bytes(canonical_json({"nonce": "a" * 64}))
            receipt.chmod(0o600)
            with _external_file(ROOT, str(receipt), mode=0o600) as handoff:
                receipt.rename(saved)
                receipt.symlink_to(saved.name)
                with self.assertRaises(P12GateError):
                    _read_external_bytes(handoff)

        with TemporaryDirectory() as value:
            root = Path(value)
            receipt_directory = root / "receipt-handoff"
            link_directory = root / "hard-link"
            receipt_directory.mkdir(mode=0o700)
            link_directory.mkdir(mode=0o700)
            receipt = receipt_directory / "p12-preflight-receipt.json"
            receipt.write_bytes(canonical_json({"nonce": "a" * 64}))
            receipt.chmod(0o600)
            os.link(receipt, link_directory / "linked-receipt.json")
            with self.assertRaises(P12GateError):
                _external_file(ROOT, str(receipt), mode=0o600)

        with TemporaryDirectory() as value:
            root = Path(value)
            receipt_directory = root / "receipt-handoff"
            link_directory = root / "hard-link"
            receipt_directory.mkdir(mode=0o700)
            link_directory.mkdir(mode=0o700)
            receipt = receipt_directory / "p12-preflight-receipt.json"
            linked_receipt = link_directory / "linked-receipt.json"
            receipt.write_bytes(canonical_json({"nonce": "a" * 64}))
            receipt.chmod(0o600)
            with _external_file(ROOT, str(receipt), mode=0o600) as handoff:

                def link_after_validation(value: object) -> None:
                    self.assertIs(value, handoff)
                    _validate_receipt_handoff(handoff)
                    os.link(receipt, linked_receipt)

                with (
                    mock.patch(
                        "scripts.collect_p12_evidence._validate_receipt_handoff",
                        side_effect=link_after_validation,
                    ),
                    self.assertRaises(P12GateError),
                ):
                    _consume_handoffs(handoff)
            self.assertFalse(receipt.exists())
            self.assertTrue(linked_receipt.exists())

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
        expected = [
            {
                "id": 1,
                "name": "sha256:" + "a" * 64,
                "tags": [],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        ]
        extra = {
            "id": 2,
            "name": "sha256:" + "b" * 64,
            "metadata": {"container": {"tags": []}},
            "created_at": "2026-01-02T00:00:00Z",
            "updated_at": "2026-01-02T00:00:00Z",
        }
        with self.assertRaises(P12GateError):
            validate_package_inventory([[extra]], expected)

    def test_tls_ca_fallback_allows_only_certificate_failure(self) -> None:
        certificate_error = ssl.SSLCertVerificationError(1, "certificate")
        self.assertTrue(ca_fallback_allowed(certificate_error))
        self.assertTrue(ca_fallback_allowed(urllib.error.URLError(certificate_error)))
        self.assertFalse(ca_fallback_allowed(TimeoutError("timeout")))
        self.assertFalse(ca_fallback_allowed(urllib.error.URLError(TimeoutError("timeout"))))

    def test_public_evidence_vocabulary_contains_no_live_claim(self) -> None:
        serialized = json.dumps(
            {
                "claim": CLAIM,
                "not_evaluated": NOT_EVALUATED,
                "platform_status": PLATFORM_STATUS,
            }
        )
        self.assertNotIn("live_compatibility_passed", serialized)
        self.assertNotIn("production_ready", serialized)
        self.assertNotIn('"linux_public_pilot_readiness": "passed"', serialized)

    def test_exact_two_ci_envelopes_pass(self) -> None:
        live_pr = {
            "number": 15,
            "state": "OPEN",
            "baseRefName": "main",
            "baseRefOid": BASE_COMMIT,
            "headRefName": "codex/p12-public-pilot-continuity-rebaseline-v4",
            "headRefOid": self.HEAD,
            "autoMergeRequest": None,
            "mergedAt": None,
            "mergeCommit": None,
            "url": "https://github.com/jeremyliu1220/digital-colleagues/pull/15",
        }

        def validate_live_pr(value: object) -> str:
            return validate_live_v4_pr_metadata(
                value,
                number=15,
                head_ref="codex/p12-public-pilot-continuity-rebaseline-v4",
                head_sha=self.HEAD,
                base_ref="main",
                base_sha=BASE_COMMIT,
            )

        self.assertEqual(validate_live_pr(live_pr), "OPEN")
        for field in ("mergedAt", "mergeCommit", "autoMergeRequest"):
            with self.subTest(non_null_live_pr_field=field):
                malformed = dict(live_pr)
                malformed[field] = {"oid": "0" * 40} if field == "mergeCommit" else "non-null"
                with self.assertRaises(P12GateError):
                    validate_live_pr(malformed)
            with self.subTest(missing_live_pr_field=field):
                malformed = dict(live_pr)
                del malformed[field]
                with self.assertRaises(P12GateError):
                    validate_live_pr(malformed)
        for field, wrong_value in (
            ("number", 16),
            ("state", "CLOSED"),
            ("baseRefName", "not-main"),
            ("baseRefOid", "0" * 40),
            ("headRefName", "wrong-branch"),
            ("headRefOid", "0" * 40),
            ("url", "https://github.com/jeremyliu1220/digital-colleagues/pull/16"),
        ):
            with self.subTest(wrong_live_pr_identity=field):
                malformed = dict(live_pr)
                malformed[field] = wrong_value
                with self.assertRaises(P12GateError):
                    validate_live_pr(malformed)
        with self.assertRaises(P12GateError):
            validate_live_pr(dict(live_pr, unexpected=None))

        current = self._envelope("current-ci")
        portable = self._envelope("portable-history")
        pair = validate_ci_envelope_pair(current, portable)
        self.assertEqual(pair, {"status": "passed", "required_envelope_count": 2})
        unsafe_envelope = copy.deepcopy(current)
        unsafe_environment = unsafe_envelope["observed_environment"]
        assert isinstance(unsafe_environment, dict)
        unsafe_environment["python_version"] = "Python /private/tmp/alice"
        with self.assertRaises(P12GateError):
            validate_ci_envelope(unsafe_envelope)
        current_projection = self._extract(current, prefix=b"2026-09-11T01:02:03.123456789Z ")
        portable_projection = self._extract(portable)
        self.assertEqual(current_projection["job_id"], "current-ci")
        self.assertEqual(portable_projection["job_id"], "portable-history")
        self.assertRegex(str(current_projection["envelope_sha256"]), r"^[0-9a-f]{64}$")
        current_safe = current_projection.get("safe_projection")
        portable_safe = portable_projection.get("safe_projection")
        assert isinstance(current_safe, dict) and isinstance(portable_safe, dict)
        current_inventory = current_safe.get("inventory")
        portable_inventory = portable_safe.get("inventory")
        assert isinstance(current_inventory, dict) and isinstance(portable_inventory, dict)
        self.assertNotIn("item_results", current_inventory)
        self.assertEqual(current_inventory["excluded_results"], [])
        self.assertNotIn("item_results", portable_inventory)
        excluded = portable_inventory["excluded_results"]
        assert isinstance(excluded, list)
        self.assertEqual(len(excluded), 5)
        with TemporaryDirectory() as value:
            directory = Path(value) / "private"
            directory.mkdir(mode=0o700)
            projection_path = directory / "projection.json"
            projection_value: dict[str, object] = {"status": "passed"}
            _write_safe_projection(str(projection_path), projection_value)
            self.assertEqual(_load_gate_result(str(projection_path)), projection_value)
            projection_bytes = projection_path.read_bytes()
            with self.assertRaises(P12GateError):
                _write_safe_projection(str(projection_path), {"status": "replaced"})
            self.assertEqual(projection_path.read_bytes(), projection_bytes)

            gate_path = directory / "gate.json"
            gate_path.touch(mode=0o600)
            gate_path.chmod(0o600)
            _emit({"status": "passed"}, str(gate_path))
            self.assertEqual(_load_gate_result(str(gate_path)), {"status": "passed"})
            with self.assertRaises(P12GateError):
                _emit({"status": "replaced"}, str(gate_path))
            self.assertEqual(_load_gate_result(str(gate_path)), {"status": "passed"})

            short_path = directory / "short.json"
            short_path.touch(mode=0o600)
            short_path.chmod(0o600)
            with (
                mock.patch("scripts.run_p12_toolchain.os.write", return_value=0),
                self.assertRaises(OSError),
            ):
                _emit({"status": "failed"}, str(short_path))
            self.assertEqual(short_path.read_bytes(), b"")

            target = directory / "target.json"
            target.write_bytes(b"sentinel")
            target.chmod(0o600)
            symlink_output = directory / "symlink-output.json"
            symlink_output.symlink_to(target)
            with self.assertRaises(P12GateError):
                _emit({"status": "replaced"}, str(symlink_output))
            self.assertEqual(target.read_bytes(), b"sentinel")
        with (
            self.subTest(job_log_transport="exact_argv_and_direct_pipe"),
            TemporaryDirectory() as value,
        ):
            working = Path(value)
            destination = working / "envelope-987.json"
            destination.write_bytes(canonical_json({"status": "passed"}))
            destination.chmod(0o600)
            gh_stdout = io.BytesIO()
            gh_process = mock.Mock(stdout=gh_stdout)
            gh_process.wait.return_value = 0
            parser_process = mock.Mock()
            parser_process.wait.return_value = 0
            with mock.patch(
                "scripts.run_p12_toolchain.subprocess.Popen",
                side_effect=(gh_process, parser_process),
            ) as popen:
                streamed = _stream_job_envelope(
                    ROOT,
                    working,
                    run_id=self.RUN_ID,
                    attempt=self.RUN_ATTEMPT,
                    job={"id": 987},
                    job_id="current-ci",
                    job_name="Current P12 governance non-publishing verification",
                    head_sha=self.HEAD,
                )
            self.assertEqual(streamed, {"status": "passed"})
            self.assertFalse(destination.exists())
            self.assertEqual(popen.call_count, 2)
            gh_call, parser_call = popen.call_args_list
            self.assertEqual(
                gh_call.args[0],
                [
                    "gh",
                    "api",
                    "--allow-escape-sequences",
                    "/repos/jeremyliu1220/digital-colleagues/actions/jobs/987/logs",
                ],
            )
            self.assertEqual(
                [argument for argument in gh_call.args[0] if argument.startswith("--")],
                ["--allow-escape-sequences"],
            )
            self.assertEqual(gh_call.kwargs["stdout"], subprocess.PIPE)
            self.assertIs(parser_call.kwargs["stdin"], gh_stdout)
            self.assertEqual(parser_call.args[0][3:5], ["--scope", "extract-ci-envelope"])
        jobs = [
            {
                "envelope_sha256": character * 64,
                "job_database_id": index,
                "job_id": envelope["job_id"],
                "job_name": envelope["job_name"],
                "observed_environment": copy.deepcopy(envelope["observed_environment"]),
            }
            for index, (character, envelope) in enumerate(
                (("a", current), ("b", portable)), start=1
            )
        ]
        _validate_jobs(jobs)
        duplicate_digest_jobs = copy.deepcopy(jobs)
        duplicate_digest_jobs[1]["envelope_sha256"] = duplicate_digest_jobs[0]["envelope_sha256"]
        with self.assertRaises(P12GateError):
            _validate_jobs(duplicate_digest_jobs)
        malformed_jobs = copy.deepcopy(jobs)
        malformed_environment = malformed_jobs[0]["observed_environment"]
        assert isinstance(malformed_environment, dict)
        malformed_environment["runner_os"] = "not-linux"
        with self.assertRaises(P12GateError):
            _validate_jobs(malformed_jobs)
        malformed_jobs = copy.deepcopy(jobs)
        malformed_environment = malformed_jobs[0]["observed_environment"]
        assert isinstance(malformed_environment, dict)
        malformed_environment["python_version"] = "file:///etc/passwd"
        with self.assertRaises(P12GateError):
            _validate_jobs(malformed_jobs)

        push_pair = [self._envelope("current-ci"), self._envelope("portable-history")]
        for envelope in push_pair:
            envelope.update(
                {
                    "base_ref": None,
                    "base_sha": None,
                    "event": "push",
                    "head_branch": "main",
                    "pull_request_number": None,
                }
            )
        self.assertEqual(
            validate_ci_envelope_pair(push_pair[0], push_pair[1]),
            {"status": "passed", "required_envelope_count": 2},
        )
        push_pair[0]["head_branch"] = "codex/p12-public-pilot-continuity-rebaseline-v4"
        with self.assertRaises(P12GateError):
            validate_ci_envelope_pair(push_pair[0], push_pair[1])

    def test_forged_marker_fails_closed(self) -> None:
        line, _ = encode_ci_envelope(self._envelope("current-ci"))
        forged_digest = line[:-1] + ("0" if line[-1] != "0" else "1")
        cases = {
            "forged_digest": forged_digest.encode("ascii"),
            "ansi_prefixed": b"\x1b[32m" + line.encode("ascii"),
        }
        for name, marker in cases.items():
            with self.subTest(marker=name), self.assertRaises(P12GateError):
                extract_ci_envelope(
                    io.BytesIO(marker + b"\n"),
                    run_id=self.RUN_ID,
                    attempt=self.RUN_ATTEMPT,
                    job_database_id=987,
                    expected_job_id="current-ci",
                    expected_job_name="Current P12 governance non-publishing verification",
                    head_sha=self.HEAD,
                )

    def test_duplicate_envelope_fails_closed(self) -> None:
        envelope = self._envelope("current-ci")
        line, _ = encode_ci_envelope(envelope)
        log = io.BytesIO((line + "\n" + line + "\n").encode("ascii"))
        with self.assertRaises(P12GateError):
            extract_ci_envelope(
                log,
                run_id=self.RUN_ID,
                attempt=self.RUN_ATTEMPT,
                job_database_id=987,
                expected_job_id="current-ci",
                expected_job_name="Current P12 governance non-publishing verification",
                head_sha=self.HEAD,
            )

    def test_wrong_job_fails_closed(self) -> None:
        envelope = self._envelope("current-ci")
        line, _ = encode_ci_envelope(envelope)
        with self.assertRaises(P12GateError):
            extract_ci_envelope(
                io.BytesIO(line.encode("ascii") + b"\n"),
                run_id=self.RUN_ID,
                attempt=self.RUN_ATTEMPT,
                job_database_id=987,
                expected_job_id="portable-history",
                expected_job_name="Portable historical replay",
                head_sha=self.HEAD,
            )

    def test_wrong_attempt_fails_closed(self) -> None:
        envelope = self._envelope("current-ci")
        line, _ = encode_ci_envelope(envelope)
        with self.assertRaises(P12GateError):
            extract_ci_envelope(
                io.BytesIO(line.encode("ascii") + b"\n"),
                run_id=self.RUN_ID,
                attempt=self.RUN_ATTEMPT + 1,
                job_database_id=987,
                expected_job_id="current-ci",
                expected_job_name="Current P12 governance non-publishing verification",
                head_sha=self.HEAD,
            )

    def test_truncated_log_fails_closed(self) -> None:
        line, _ = encode_ci_envelope(self._envelope("current-ci"))
        truncated = line[: len(ENVELOPE_PREFIX) + 24].encode("ascii")
        with self.assertRaises(P12GateError):
            extract_ci_envelope(
                io.BytesIO(truncated),
                run_id=self.RUN_ID,
                attempt=self.RUN_ATTEMPT,
                job_database_id=987,
                expected_job_id="current-ci",
                expected_job_name="Current P12 governance non-publishing verification",
                head_sha=self.HEAD,
            )

    def test_unbound_dynamic_field_fails_closed(self) -> None:
        current = self._envelope("current-ci")
        for field, value in (
            ("pull_request_number", 16),
            ("run_id", self.RUN_ID + 1),
            ("head_sha", "f" * 40),
        ):
            with self.subTest(field=field):
                portable = self._envelope("portable-history")
                portable[field] = value
                with self.assertRaises(P12GateError):
                    validate_ci_envelope_pair(current, portable)
        for field, value in (
            ("cleanup_residue_count", False),
            ("publication_count", False),
        ):
            with self.subTest(field=field):
                envelope = self._envelope("current-ci")
                envelope[field] = value
                with self.assertRaises(P12GateError):
                    validate_ci_envelope(envelope)
        for field in (
            "setup_count",
            "included_acceptance_gate_count",
            "evidence_anchor_count",
            "excluded_acceptance_gate_count",
            "total_item_count",
            "skip_count",
        ):
            with self.subTest(inventory_field=field):
                envelope = self._envelope("portable-history")
                inventory = envelope.get("inventory")
                assert isinstance(inventory, dict)
                inventory[field] = False
                with self.assertRaises(P12GateError):
                    validate_ci_envelope(envelope)
        for value in ("Darwin", "Linux bearer token", "C:/private/tool"):
            with self.subTest(observed_runner=value):
                envelope = self._envelope("current-ci")
                observed = envelope.get("observed_environment")
                assert isinstance(observed, dict)
                observed["runner_os"] = value
                with self.assertRaises(P12GateError):
                    validate_ci_envelope(envelope)
        envelope = self._envelope("portable-history")
        inventory = envelope.get("inventory")
        assert isinstance(inventory, dict)
        item_results = inventory.get("item_results")
        assert isinstance(item_results, list) and isinstance(item_results[0], dict)
        item_results[0]["exit_status"] = False
        self._refresh_item_digest(envelope)
        with self.assertRaises(P12GateError):
            validate_ci_envelope(envelope)

    def test_missing_malformed_or_digest_mismatch_fails_closed(self) -> None:
        local_path = "/" + "Users" + "/private/account/.config"
        sensitive = (
            f"{local_path} credential=ghp_example Bearer-example {ENVELOPE_PREFIX}\nsecond-line"
        )
        self.assertEqual(_safe(sensitive), "bounded failure diagnostic withheld")
        diagnostic = io.StringIO()
        with (
            mock.patch(
                "scripts.run_p12_toolchain.run_current_ci",
                side_effect=OSError(sensitive),
            ),
            mock.patch("sys.stderr", new=diagnostic),
        ):
            self.assertEqual(toolchain_main(["--scope", "current-ci"]), 2)
        self.assertEqual(
            diagnostic.getvalue(),
            "P12 toolchain failed: bounded failure diagnostic withheld\n",
        )
        self.assertNotIn(local_path, diagnostic.getvalue())
        self.assertNotIn("ghp_example", diagnostic.getvalue())
        self.assertNotIn(ENVELOPE_PREFIX, diagnostic.getvalue())

        envelope = self._envelope("current-ci")
        line, _ = encode_ci_envelope(envelope)
        cases = {
            "missing": b"ordinary job output only\n",
            "malformed": f"{ENVELOPE_PREFIX} abc= sha256={'0' * 64}\n".encode("ascii"),
            "digest": (line[:-1] + ("0" if line[-1] != "0" else "1") + "\n").encode("ascii"),
        }
        noncanonical = json.dumps(envelope, ensure_ascii=False, sort_keys=True).encode("utf-8")
        token = base64.urlsafe_b64encode(noncanonical).rstrip(b"=").decode("ascii")
        cases["noncanonical"] = (
            f"{ENVELOPE_PREFIX} {token} sha256={hashlib.sha256(noncanonical).hexdigest()}\n"
        ).encode("ascii")
        for name, log in cases.items():
            with self.subTest(case=name), self.assertRaises(P12GateError):
                extract_ci_envelope(
                    io.BytesIO(log),
                    run_id=self.RUN_ID,
                    attempt=self.RUN_ATTEMPT,
                    job_database_id=987,
                    expected_job_id="current-ci",
                    expected_job_name="Current P12 governance non-publishing verification",
                    head_sha=self.HEAD,
                )

        for name, gh_status, parser_status in (
            ("transport", 1, 0),
            ("parser", 0, 1),
        ):
            with self.subTest(stream_failure=name), TemporaryDirectory() as value:
                working = Path(value)
                destination = working / "envelope-987.json"
                destination.write_bytes(canonical_json({"status": "passed"}))
                destination.chmod(0o600)
                gh_stdout = io.BytesIO()
                gh_process = mock.Mock(stdout=gh_stdout)
                gh_process.wait.return_value = gh_status
                parser_process = mock.Mock()
                parser_process.wait.return_value = parser_status
                with (
                    mock.patch(
                        "scripts.run_p12_toolchain.subprocess.Popen",
                        side_effect=(gh_process, parser_process),
                    ) as popen,
                    self.assertRaisesRegex(
                        P12GateError,
                        "P12 CI job-log transport or envelope extraction failed",
                    ),
                ):
                    _stream_job_envelope(
                        ROOT,
                        working,
                        run_id=self.RUN_ID,
                        attempt=self.RUN_ATTEMPT,
                        job={"id": 987},
                        job_id="current-ci",
                        job_name="Current P12 governance non-publishing verification",
                        head_sha=self.HEAD,
                    )
                self.assertEqual(popen.call_count, 2)
                self.assertIs(popen.call_args_list[1].kwargs["stdin"], gh_stdout)
                self.assertTrue(destination.exists())

        with TemporaryDirectory() as value:
            directory = Path(value) / "private"
            directory.mkdir(mode=0o700)
            regular = directory / "regular.json"
            regular.write_bytes(canonical_json({"status": "passed"}))
            regular.chmod(0o600)
            symlink = directory / "symlink.json"
            symlink.symlink_to(regular)
            with self.assertRaises(P12GateError):
                _load_gate_result(str(symlink))
            fifo = directory / "fifo.json"
            os.mkfifo(fifo, mode=0o600)
            with self.assertRaises(P12GateError):
                _load_gate_result(str(fifo))
            oversized = directory / "oversized.json"
            with oversized.open("wb") as stream:
                stream.truncate(GATE_RESULT_MAX_BYTES + 1)
            oversized.chmod(0o600)
            with self.assertRaises(P12GateError):
                _load_gate_result(str(oversized))

            outside = Path(value) / "outside"
            outside.mkdir(mode=0o700)
            linked_parent = Path(value) / "linked-parent"
            linked_parent.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(P12GateError):
                _write_safe_projection(
                    str(linked_parent / "projection.json"),
                    {"status": "passed"},
                )

        failing_suite = {
            "tests_run": len(P12_TEST_IDS),
            "failures": 1,
            "errors": 0,
            "skipped": 0,
            "expected_failures": 0,
            "unexpected_successes": 0,
            "gate_passed": False,
            "test_ids": sorted(P12_TEST_IDS),
            "fault_boundaries": [],
        }
        with mock.patch(
            "scripts.run_p12_toolchain.run_suite",
            return_value=failing_suite,
        ):
            p12_failure = run_p12_tests(ROOT, stream=io.StringIO())
        self.assertEqual(p12_failure["status"], "failed")
        self.assertEqual(p12_failure["tests_run"], 136)
        self.assertEqual(p12_failure["failures"], 1)

        p11_ids = current_p11_test_ids(ROOT)
        p11_success = {
            "tests_run": 100,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "expected_failures": 0,
            "unexpected_successes": 0,
            "gate_passed": True,
            "test_ids": sorted(p11_ids),
            "fault_boundaries": [],
            "status": "passed",
            "suite": "p12_current_tree_p11_regression",
            "inventory_count": 100,
        }

        def synthetic_gate_status(command: list[str], **_kwargs: object) -> int:
            if "--scope" not in command:
                return 0
            scope = command[command.index("--scope") + 1]
            output = Path(command[command.index("--json-output") + 1])
            if scope == "current-p11-tests":
                _emit(p11_success, str(output))
                return 0
            if scope == "p12-tests":
                _emit(p12_failure, str(output))
                return 1
            raise AssertionError("unexpected synthetic gate scope")

        with TemporaryDirectory() as value:
            with (
                mock.patch(
                    "scripts.run_p12_toolchain._prepare_python",
                    return_value=(Path("/synthetic/python"), {}),
                ),
                mock.patch(
                    "scripts.run_p12_toolchain._run_status",
                    side_effect=synthetic_gate_status,
                ),
                mock.patch("scripts.run_p12_toolchain.static_gates") as static_gates,
            ):
                current_failure = run_current_ci(ROOT, Path(value) / "current")
            static_gates.assert_not_called()
            self.assertEqual(current_failure["status"], "failed")
            self.assertEqual(current_failure["test_count"], 136)
            self.assertEqual(current_failure["failure_count"], 1)
            self.assertEqual(current_failure["error_count"], 0)
            self.assertNotIn(ENVELOPE_PREFIX, json.dumps(current_failure))

            output_directory = Path(value) / "output"
            output_directory.mkdir(mode=0o700)
            output_path = output_directory / "gate.json"
            output_path.touch(mode=0o600)
            output_path.chmod(0o600)
            with mock.patch(
                "scripts.run_p12_toolchain.run_current_ci",
                return_value=current_failure,
            ):
                self.assertEqual(
                    toolchain_main(
                        [
                            "--scope",
                            "current-ci",
                            "--json-output",
                            str(output_path),
                        ]
                    ),
                    1,
                )
            self.assertEqual(_load_gate_result(str(output_path)), current_failure)

            template = self._envelope("current-ci")
            identity_keys = (
                "repository",
                "workflow_name",
                "workflow_path",
                "run_id",
                "run_attempt",
                "event",
                "head_branch",
                "head_sha",
                "base_ref",
                "base_sha",
                "pull_request_number",
            )
            identity = {key: template[key] for key in identity_keys}
            template_inventory = template["inventory"]
            template_observed = template["observed_environment"]
            assert isinstance(template_inventory, dict)
            assert isinstance(template_observed, dict)
            binding_keys = (
                "setup_count",
                "included_acceptance_gate_count",
                "evidence_anchor_count",
                "excluded_acceptance_gate_count",
                "total_item_count",
                "excluded_gate_ids",
                "inventory_blob",
                "inventory_digest",
                "inventory_path",
                "inventory_sha256",
            )
            binding = {key: template_inventory[key] for key in binding_keys}
            emitted = io.StringIO()
            with (
                mock.patch.dict(os.environ, {"GITHUB_JOB": "current-ci"}),
                mock.patch(
                    "scripts.run_p12_toolchain._dynamic_identity",
                    return_value=identity,
                ),
                mock.patch(
                    "scripts.run_p12_toolchain.inventory_binding",
                    return_value=(binding, []),
                ),
                mock.patch(
                    "scripts.run_p12_toolchain.observed_environment",
                    return_value=template_observed,
                ),
                mock.patch("sys.stdout", new=emitted),
            ):
                self.assertEqual(
                    toolchain_main(
                        [
                            "--scope",
                            "emit-ci-envelope",
                            "--job-kind",
                            "current_governance",
                            "--gate-result",
                            str(output_path),
                            "--gate-exit-status",
                            "2",
                        ]
                    ),
                    0,
                )
            emitted_lines = emitted.getvalue().splitlines()
            self.assertEqual(len(emitted_lines), 1)
            self.assertEqual(emitted_lines[0].count(ENVELOPE_PREFIX), 1)
            failed_envelope, _ = decode_ci_envelope_line(emitted_lines[0].encode("ascii"))
            failed_gate = failed_envelope["gate"]
            failed_platform = failed_envelope["platform_status"]
            assert isinstance(failed_gate, dict)
            assert isinstance(failed_platform, dict)
            self.assertEqual(failed_gate["status"], "failed")
            self.assertEqual(failed_gate["test_count"], 136)
            self.assertEqual(failed_gate["failure_count"], 1)
            self.assertEqual(failed_platform["p12_governance_result"], "failed")

        with TemporaryDirectory() as value:
            with (
                mock.patch(
                    "scripts.run_p12_toolchain._prepare_python",
                    return_value=(Path("/synthetic/python"), {}),
                ),
                mock.patch("scripts.run_p12_toolchain._run_status", return_value=124),
                mock.patch("scripts.run_p12_toolchain.static_gates") as static_gates,
            ):
                timed_out = run_current_ci(ROOT, Path(value) / "current")
            static_gates.assert_not_called()
            self.assertEqual(timed_out["status"], "failed")
            self.assertEqual(timed_out["test_count"], 0)
            self.assertEqual(timed_out["failure_count"], 1)
            self.assertEqual(
                timed_out["tests"]["quality"]["failed_exit_status"],
                124,
            )

        def malformed_gate_status(command: list[str], **_kwargs: object) -> int:
            if "--scope" not in command:
                return 0
            output = Path(command[command.index("--json-output") + 1])
            _emit({"status": "passed", "suite": "wrong-suite"}, str(output))
            return 0

        def abnormal_gate_status(command: list[str], **_kwargs: object) -> int:
            return 2 if "--scope" in command else 0

        def missing_gate_result(command: list[str], **_kwargs: object) -> int:
            return 0

        for case, status_side_effect in (
            ("abnormal child status", abnormal_gate_status),
            ("malformed child result", malformed_gate_status),
            ("missing child result", missing_gate_result),
        ):
            with self.subTest(case=case), TemporaryDirectory() as value:
                with (
                    mock.patch(
                        "scripts.run_p12_toolchain._prepare_python",
                        return_value=(Path("/synthetic/python"), {}),
                    ),
                    mock.patch(
                        "scripts.run_p12_toolchain._run_status",
                        side_effect=status_side_effect,
                    ),
                    mock.patch("scripts.run_p12_toolchain.static_gates") as static_gates,
                ):
                    invalid_child = run_current_ci(ROOT, Path(value) / "current")
                static_gates.assert_not_called()
                self.assertEqual(invalid_child["status"], "failed")
                self.assertEqual(invalid_child["test_count"], 0)
                self.assertEqual(invalid_child["error_count"], 1)

        def missing_result_parent(command: list[str], **_kwargs: object) -> int:
            if "--scope" in command:
                output = Path(command[command.index("--json-output") + 1])
                output.parent.rmdir()
            return 0

        with TemporaryDirectory() as value:
            with (
                mock.patch(
                    "scripts.run_p12_toolchain._prepare_python",
                    return_value=(Path("/synthetic/python"), {}),
                ),
                mock.patch(
                    "scripts.run_p12_toolchain._run_status",
                    side_effect=missing_result_parent,
                ),
                mock.patch("scripts.run_p12_toolchain.static_gates") as static_gates,
            ):
                with self.assertRaises(P12GateError):
                    run_current_ci(ROOT, Path(value) / "current")
            static_gates.assert_not_called()

        mutations = []
        reordered_ids = self._envelope("portable-history")
        reordered_inventory = reordered_ids.get("inventory")
        assert isinstance(reordered_inventory, dict)
        excluded_ids = reordered_inventory.get("excluded_gate_ids")
        assert isinstance(excluded_ids, list)
        excluded_ids[0], excluded_ids[1] = excluded_ids[1], excluded_ids[0]
        mutations.append(("reordered exclusion IDs", reordered_ids))

        wrong_registry = self._envelope("portable-history")
        wrong_registry["p12_current_p10_registry_protection"] = {
            "result_digest": "sha256:" + "a" * 64,
            "status": "passed",
        }
        mutations.append(("registry result in CI", wrong_registry))

        wrong_platform = self._envelope("portable-history")
        platform = wrong_platform.get("platform_status")
        assert isinstance(platform, dict)
        ubuntu = platform.get("ubuntu_historical_execution_status")
        assert isinstance(ubuntu, dict)
        ubuntu["p8_compose_runtime"] = "passed"
        mutations.append(("Darwin result promoted to Ubuntu", wrong_platform))

        wrong_reason = self._envelope("portable-history")
        wrong_reason_inventory = wrong_reason.get("inventory")
        assert isinstance(wrong_reason_inventory, dict)
        wrong_reason_results = wrong_reason_inventory.get("item_results")
        assert isinstance(wrong_reason_results, list)
        excluded_result = next(
            result
            for result in wrong_reason_results
            if isinstance(result, dict) and result.get("gate_id") == "p8_compose_runtime"
        )
        platform_result = excluded_result.get("platform_result")
        assert isinstance(platform_result, dict)
        platform_result["reason"] = "wrong_reason"
        self._refresh_item_digest(wrong_reason)
        mutations.append(("wrong exclusion reason", wrong_reason))

        wrong_anchor = self._envelope("portable-history")
        wrong_anchor_inventory = wrong_anchor.get("inventory")
        assert isinstance(wrong_anchor_inventory, dict)
        wrong_anchor_results = wrong_anchor_inventory.get("item_results")
        assert isinstance(wrong_anchor_results, list)
        excluded_result = next(
            result
            for result in wrong_anchor_results
            if isinstance(result, dict) and result.get("gate_id") == "p10_remote_distribution"
        )
        embedded_anchor = excluded_result.get("embedded_anchor")
        assert isinstance(embedded_anchor, dict)
        embedded_anchor["canonical_sha256"] = "0" * 64
        self._refresh_item_digest(wrong_anchor)
        mutations.append(("wrong embedded anchor", wrong_anchor))

        for name, mutated in mutations:
            with self.subTest(envelope_case=name), self.assertRaises(P12GateError):
                validate_ci_envelope(mutated)

    def test_wrong_run_or_head_fails_closed(self) -> None:
        envelope = self._envelope("current-ci")
        line, _ = encode_ci_envelope(envelope)
        for run_id, head_sha in (
            (self.RUN_ID + 1, self.HEAD),
            (self.RUN_ID, "f" * 40),
        ):
            with self.subTest(run_id=run_id, head_sha=head_sha), self.assertRaises(P12GateError):
                extract_ci_envelope(
                    io.BytesIO(line.encode("ascii") + b"\n"),
                    run_id=run_id,
                    attempt=self.RUN_ATTEMPT,
                    job_database_id=987,
                    expected_job_id="current-ci",
                    expected_job_name="Current P12 governance non-publishing verification",
                    head_sha=head_sha,
                )

    def test_full_actions_log_retention_fails_closed(self) -> None:
        envelope = self._envelope("current-ci")
        line, _ = encode_ci_envelope(envelope)
        projection = extract_ci_envelope(
            _IterationOnlyLog([b"ordinary line\n", line.encode("ascii") + b"\n"]),
            run_id=self.RUN_ID,
            attempt=self.RUN_ATTEMPT,
            job_database_id=987,
            expected_job_id="current-ci",
            expected_job_name="Current P12 governance non-publishing verification",
            head_sha=self.HEAD,
        )
        self.assertNotIn("actions_log", projection)
        with TemporaryDirectory() as value:
            directory = Path(value) / "receipt"
            directory.mkdir(mode=0o700)
            with self.assertRaises(P12GateError):
                write_preflight_receipt(
                    directory,
                    {
                        "lifecycle": "pending_consumption",
                        "schema_version": 1,
                        "stage": "p12_evidence_preflight",
                        "full_actions_log": "forbidden retained log",
                    },
                )


if __name__ == "__main__":
    unittest.main()
