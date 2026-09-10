# SPDX-License-Identifier: Apache-2.0

"""Consume authorized P12 preflight proof and write only the final safe summary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p12_provenance import RECEIPT_PATH  # noqa: E402
from scripts.check_p12_repository import (  # noqa: E402
    ACCEPTANCE_BLOB,
    ACCEPTANCE_COMMIT,
    BASE_COMMIT,
    BRANCH,
    SUMMARY_PATH,
    CommitRecord,
    P12GateError,
    check_repository,
    commit_records,
    git,
)

CLAIM = "p12_public_pilot_continuity_rebaseline_candidate"
STATUS = "development_complete_awaiting_independent_acceptance"
NOT_EVALUATED = (
    "OpenAI live compatibility",
    "Microsoft 365 live compatibility",
    "human evaluation",
    "72-hour soak",
    "Public Pilot readiness",
    "production readiness",
)


def canonical_json(value: object, *, newline: bool = False) -> bytes:
    normalized = unicodedata.normalize(
        "NFC", json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    return (normalized + ("\n" if newline else "")).encode("utf-8")


def implementation_range(root: Path, head: str) -> tuple[CommitRecord, ...]:
    return commit_records(root, ACCEPTANCE_COMMIT, head)


def implementation_range_digest(records: tuple[CommitRecord, ...]) -> str:
    canonical = [
        {
            "changed_paths": sorted(record["changed_paths"]),
            "classification": "implementation_or_scoped_correction",
            "commit": record["commit"],
            "parent": record["parent"],
            "tree": record["tree"],
        }
        for record in records
    ]
    return f"sha256:{hashlib.sha256(canonical_json(canonical)).hexdigest()}"


def _external_file(root: Path, value: str, *, mode: int) -> Path:
    path = Path(value)
    if not path.is_absolute() or root == path or root in path.parents:
        raise P12GateError("P12 evidence input must be an absolute path outside the repository")
    if path.is_symlink() or not path.exists() or not stat.S_ISREG(os.lstat(path).st_mode):
        raise P12GateError("P12 evidence input must be a regular non-symlink file")
    if stat.S_IMODE(os.stat(path).st_mode) != mode:
        raise P12GateError("P12 evidence input mode is invalid")
    return path


def validate_authorization(
    value: object,
    *,
    receipt_sha256: str,
    implementation_head: str,
    ci_run_id: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise P12GateError("P12 evidence authorization shape is invalid")
    if (
        value.get("schema_version") != 1
        or value.get("stage") != "p12_evidence_authorization"
        or value.get("receipt_sha256") != receipt_sha256
        or value.get("implementation_head") != implementation_head
        or value.get("ci_run_id") != ci_run_id
    ):
        raise P12GateError("P12 evidence authorization identity is invalid")
    expires = value.get("expires_at")
    if not isinstance(expires, str) or not expires.endswith("Z"):
        raise P12GateError("P12 evidence authorization expiry is invalid")
    try:
        expiry = datetime.fromisoformat(expires[:-1] + "+00:00")
    except ValueError as exc:
        raise P12GateError("P12 evidence authorization expiry is invalid") from exc
    current = now or datetime.now(UTC)
    if expiry <= current:
        raise P12GateError("P12 evidence authorization expired")
    return value


def write_evidence(root: Path, summary: dict[str, object]) -> None:
    destination = root / SUMMARY_PATH
    if destination.exists() or destination.is_symlink():
        raise P12GateError("P12 summary path already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=".p12-summary-", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, destination)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def build_summary(
    root: Path,
    *,
    receipt: dict[str, Any],
    receipt_sha256: str,
    records: tuple[CommitRecord, ...],
) -> dict[str, object]:
    head = git(root, "rev-parse", "HEAD")
    return {
        "schema_version": 1,
        "change": "P12",
        "claim": CLAIM,
        "status": STATUS,
        "branch": BRANCH,
        "base_commit": BASE_COMMIT,
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "acceptance_blob": ACCEPTANCE_BLOB,
        "final_implementation_head": head,
        "final_implementation_tree": git(root, "rev-parse", "HEAD^{tree}"),
        "implementation_commits": list(records),
        "implementation_range_digest": implementation_range_digest(records),
        "changed_paths": sorted(
            [
                line
                for line in git(root, "diff", "--name-only", BASE_COMMIT, "HEAD").splitlines()
                if line
            ]
            + [SUMMARY_PATH]
        ),
        "changed_path_count": 39,
        "implementation_head_ci": receipt["ci"],
        "preflight": {
            "receipt_sha256": receipt_sha256,
            "status": "passed",
            "receipt_consumed": True,
            "temporary_environment_cleanup": "passed",
            "github": receipt["github"],
            "ghcr": receipt["ghcr"],
            "python": receipt["python"],
            "tls": receipt["tls"],
        },
        "local_gates": receipt["local_gates"],
        "provenance": RECEIPT_PATH,
        "evidence_class": "static_and_synthetic_offline",
        "not_evaluated": list(NOT_EVALUATED),
        "change_counts": {
            "product_runtime_source": 0,
            "studio_product_behavior": 0,
            "database_schema": 0,
            "migration": 0,
        },
        "publication": {
            "tag": False,
            "release": False,
            "package_or_image": False,
            "signature_or_attestation": False,
            "remote_mutation": False,
        },
    }


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise P12GateError("P12 evidence input JSON is invalid") from exc


def validate_summary(root: Path) -> dict[str, Any]:
    value = _load_json(root / SUMMARY_PATH)
    if not isinstance(value, dict):
        raise P12GateError("P12 summary shape is invalid")
    implementation_head = git(root, "rev-parse", "HEAD^")
    records = implementation_range(root, implementation_head)
    expected_paths = sorted(
        line for line in git(root, "diff", "--name-only", BASE_COMMIT, "HEAD").splitlines() if line
    )
    if (
        value.get("schema_version") != 1
        or value.get("change") != "P12"
        or value.get("claim") != CLAIM
        or value.get("status") != STATUS
        or value.get("base_commit") != BASE_COMMIT
        or value.get("acceptance_commit") != ACCEPTANCE_COMMIT
        or value.get("acceptance_blob") != ACCEPTANCE_BLOB
        or value.get("final_implementation_head") != implementation_head
        or value.get("final_implementation_tree")
        != git(root, "rev-parse", f"{implementation_head}^{{tree}}")
        or value.get("implementation_commits") != list(records)
        or value.get("implementation_range_digest") != implementation_range_digest(records)
        or value.get("changed_paths") != expected_paths
        or value.get("changed_path_count") != 39
        or value.get("not_evaluated") != list(NOT_EVALUATED)
        or value.get("provenance") != RECEIPT_PATH
    ):
        raise P12GateError("P12 committed summary identity or topology is invalid")
    publication = value.get("publication")
    if not isinstance(publication, dict) or any(item is not False for item in publication.values()):
        raise P12GateError("P12 committed summary publication boundary is invalid")
    preflight = value.get("preflight")
    if (
        not isinstance(preflight, dict)
        or preflight.get("status") != "passed"
        or preflight.get("receipt_consumed") is not True
        or preflight.get("temporary_environment_cleanup") != "passed"
    ):
        raise P12GateError("P12 committed summary preflight binding is invalid")
    return value


def _consume_receipt(receipt: Path) -> None:
    parent = receipt.parent
    receipt.unlink()
    try:
        parent.rmdir()
    except OSError as exc:
        raise P12GateError("P12 preflight directory was not empty after receipt use") from exc


def collect(
    root: Path, *, receipt_value: str, expected_digest: str, authorization_value: str
) -> None:
    if git(root, "branch", "--show-current") != BRANCH:
        raise P12GateError("P12 evidence writer branch identity is invalid")
    check_repository(root, mode="implementation")
    receipt_path = _external_file(root, receipt_value, mode=0o600)
    authorization_path = _external_file(root, authorization_value, mode=0o600)
    encoded = receipt_path.read_bytes()
    actual_digest = hashlib.sha256(encoded).hexdigest()
    if (
        actual_digest != expected_digest
        or canonical_json(json.loads(encoded), newline=True) != encoded
    ):
        raise P12GateError("P12 preflight receipt digest or canonical form is invalid")
    receipt = _load_json(receipt_path)
    if not isinstance(receipt, dict) or receipt.get("lifecycle") != "pending_consumption":
        raise P12GateError("P12 preflight receipt lifecycle is invalid")
    head = git(root, "rev-parse", "HEAD")
    ci = receipt.get("ci")
    if not isinstance(ci, dict) or not isinstance(ci.get("run_id"), int):
        raise P12GateError("P12 preflight CI identity is invalid")
    if receipt.get("implementation_head") != head:
        raise P12GateError("P12 preflight receipt is for another implementation head")
    validate_authorization(
        _load_json(authorization_path),
        receipt_sha256=actual_digest,
        implementation_head=head,
        ci_run_id=ci["run_id"],
    )
    records = implementation_range(root, head)
    summary = build_summary(root, receipt=receipt, receipt_sha256=actual_digest, records=records)
    _consume_receipt(receipt_path)
    write_evidence(root, summary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--authorization", required=True)
    args = parser.parse_args(argv)
    try:
        collect(
            Path(__file__).resolve().parents[1],
            receipt_value=args.receipt,
            expected_digest=args.receipt_sha256,
            authorization_value=args.authorization,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, P12GateError) as exc:
        root = Path(__file__).resolve().parents[1]
        print(
            f"P12 evidence collection failed: {str(exc).replace(str(root), '<project>')}",
            file=sys.stderr,
        )
        return 2
    print(json.dumps({"status": "written", "path": SUMMARY_PATH}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
