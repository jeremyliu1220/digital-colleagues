# SPDX-License-Identifier: Apache-2.0

"""Consume one authorized P12 v4 preflight receipt and write the safe summary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import stat
import sys
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p12_historical_inventory import check_historical_inventory  # noqa: E402
from scripts.check_p12_provenance import (  # noqa: E402
    DARWIN_EVIDENCE_ANCHORS,
    check_provenance,
)
from scripts.check_p12_repository import (  # noqa: E402
    ACCEPTANCE_BLOB,
    ACCEPTANCE_COMMIT,
    ACCEPTANCE_SHA256,
    BASE_COMMIT,
    BASE_TREE,
    BRANCH,
    SUMMARY_PATH,
    CommitRecord,
    P12GateError,
    check_repository,
    commit_records,
    git,
)

CLAIM = "p12_v4_historical_platform_classification_candidate"
STATUS = "development_complete_awaiting_independent_acceptance"
NOT_EVALUATED = {
    "human_evaluation": "not_evaluated",
    "microsoft_365": "not_evaluated",
    "openai": "not_evaluated",
    "release": "not_evaluated",
    "soak": "not_evaluated",
}
PLATFORM_STATUS = {
    "linux_public_pilot_readiness": "blocked",
    "p12_governance_result": "passed",
    "ubuntu_historical_execution_status": "five_excluded_not_proven",
}
REPOSITORY = "jeremyliu1220/digital-colleagues"
EXCLUDED_GATE_IDS = (
    "p8_compose_runtime",
    "p8_golden_path",
    "p10_compose_runtime",
    "p10_quickstart",
    "p10_remote_distribution",
)
RECEIPT_KEYS = {
    "acceptance",
    "ca_verification",
    "ci",
    "cleanup_residue_count",
    "expires_at",
    "implementation",
    "inventory",
    "issued_at",
    "lifecycle",
    "nonce",
    "p10_protected_identity_digest",
    "p12_current_p10_registry_protection",
    "package_verification_digest",
    "platform_status",
    "publication_count",
    "repository",
    "schema",
}
AUTHORIZATION_KEYS = {
    "schema_version",
    "stage",
    "receipt_sha256",
    "implementation_head",
    "ci_run_id",
    "ci_run_attempt",
    "envelope_digests",
    "expires_at",
}
ENVELOPE_JOB_IDS = ("current-ci", "portable-history")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
SAFE_VALUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+() /:-]{0,127}\Z")
DIRECTORY_OPEN_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
FILE_READ_FLAGS = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC


def _inode(metadata: os.stat_result) -> tuple[int, int]:
    return metadata.st_dev, metadata.st_ino


def _file_snapshot(metadata: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


@dataclass
class _HeldExternalFile:
    path: Path
    name: str
    directory_path: Path
    directory_name: str
    file_fd: int
    directory_fd: int
    container_fd: int
    expected_mode: int
    file_snapshot: tuple[int, int, int, int, int, int, int]
    directory_identity: tuple[int, int]

    def __enter__(self) -> _HeldExternalFile:
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        for descriptor_name in ("file_fd", "directory_fd", "container_fd"):
            descriptor = getattr(self, descriptor_name)
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                setattr(self, descriptor_name, -1)


def _normalize_json(value: object) -> object:
    """Return the P12-CJ-1 value, rejecting unsupported JSON number/key forms."""

    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        raise P12GateError("P12-CJ-1 forbids floating-point numbers")
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize_json(item) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise P12GateError("P12-CJ-1 requires string object keys")
            canonical_key = unicodedata.normalize("NFC", key)
            if canonical_key in normalized:
                raise P12GateError("P12-CJ-1 normalized object keys collide")
            normalized[canonical_key] = _normalize_json(item)
        return normalized
    raise P12GateError("P12-CJ-1 value has an unsupported type")


def canonical_json(value: object, *, newline: bool = False) -> bytes:
    """Encode P12-CJ-1: normalized UTF-8, sorted, compact and integer-only."""

    encoded = json.dumps(
        _normalize_json(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return encoded + (b"\n" if newline else b"")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise P12GateError("P12 JSON contains a duplicate object key")
        value[key] = item
    return value


def parse_json_unique(encoded: bytes) -> object:
    if encoded.startswith(b"\xef\xbb\xbf"):
        raise P12GateError("P12 JSON must not contain a BOM")
    try:
        return json.loads(encoded.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise P12GateError("P12 JSON is malformed") from exc


def implementation_range(root: Path, head: str) -> tuple[CommitRecord, ...]:
    records = commit_records(root, BASE_COMMIT, head)
    if not records or records[0]["commit"] != ACCEPTANCE_COMMIT:
        raise P12GateError("P12 implementation range does not begin with acceptance")
    return records


def implementation_range_digest(records: tuple[CommitRecord, ...]) -> str:
    if not records or records[0]["commit"] != ACCEPTANCE_COMMIT:
        raise P12GateError("P12 canonical range omits the acceptance commit")
    canonical = {
        "schema": "digital-colleagues.p12-v4-commit-range.v1",
        "base_commit": BASE_COMMIT,
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "commits": list(records),
    }
    return f"sha256:{hashlib.sha256(canonical_json(canonical)).hexdigest()}"


def _external_file(root: Path, value: str, *, mode: int) -> _HeldExternalFile:
    path = Path(value)
    if not path.is_absolute():
        raise P12GateError("P12 evidence input must be an absolute path outside the repository")
    try:
        original_file = os.lstat(path)
        original_directory = os.lstat(path.parent)
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise P12GateError("P12 evidence input does not resolve") from exc
    resolved_root = root.resolve()
    if resolved == resolved_root or resolved_root in resolved.parents:
        raise P12GateError("P12 evidence input must be an absolute path outside the repository")
    if stat.S_ISLNK(original_file.st_mode) or not stat.S_ISREG(original_file.st_mode):
        raise P12GateError("P12 evidence input must be a regular non-symlink file")
    if original_file.st_nlink != 1:
        raise P12GateError("P12 evidence input must not have hard links")
    if stat.S_IMODE(original_file.st_mode) != mode:
        raise P12GateError("P12 evidence input mode is invalid")
    if (
        stat.S_ISLNK(original_directory.st_mode)
        or not stat.S_ISDIR(original_directory.st_mode)
        or stat.S_IMODE(original_directory.st_mode) != 0o700
    ):
        raise P12GateError("P12 evidence input directory mode is invalid")

    directory_path = resolved.parent
    container_path = directory_path.parent
    directory_name = directory_path.name
    if not directory_name:
        raise P12GateError("P12 evidence input directory is invalid")
    container_fd = -1
    directory_fd = -1
    file_fd = -1
    try:
        container_fd = os.open(container_path, DIRECTORY_OPEN_FLAGS)
        directory_fd = os.open(directory_name, DIRECTORY_OPEN_FLAGS, dir_fd=container_fd)
        file_fd = os.open(resolved.name, FILE_READ_FLAGS, dir_fd=directory_fd)
        directory_metadata = os.fstat(directory_fd)
        file_metadata = os.fstat(file_fd)
        mapped_directory = os.stat(directory_name, dir_fd=container_fd, follow_symlinks=False)
        mapped_file = os.stat(resolved.name, dir_fd=directory_fd, follow_symlinks=False)
        current_original_directory = os.lstat(path.parent)
        current_original_file = os.lstat(path)
        if (
            not stat.S_ISDIR(directory_metadata.st_mode)
            or stat.S_IMODE(directory_metadata.st_mode) != 0o700
            or _inode(directory_metadata) != _inode(original_directory)
            or _inode(directory_metadata) != _inode(mapped_directory)
            or _inode(directory_metadata) != _inode(current_original_directory)
        ):
            raise P12GateError("P12 evidence input directory identity changed")
        if (
            not stat.S_ISREG(file_metadata.st_mode)
            or stat.S_IMODE(file_metadata.st_mode) != mode
            or file_metadata.st_nlink != 1
            or _file_snapshot(file_metadata) != _file_snapshot(original_file)
            or _inode(file_metadata) != _inode(mapped_file)
            or _inode(file_metadata) != _inode(current_original_file)
        ):
            raise P12GateError("P12 evidence input file identity changed")
        return _HeldExternalFile(
            path=resolved,
            name=resolved.name,
            directory_path=directory_path,
            directory_name=directory_name,
            file_fd=file_fd,
            directory_fd=directory_fd,
            container_fd=container_fd,
            expected_mode=mode,
            file_snapshot=_file_snapshot(file_metadata),
            directory_identity=_inode(directory_metadata),
        )
    except (OSError, P12GateError) as exc:
        for descriptor in (file_fd, directory_fd, container_fd):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        if isinstance(exc, P12GateError):
            raise
        raise P12GateError("P12 evidence input cannot be opened safely") from exc


def _revalidate_external_file(value: _HeldExternalFile) -> os.stat_result:
    try:
        directory_metadata = os.fstat(value.directory_fd)
        file_metadata = os.fstat(value.file_fd)
        mapped_directory = os.stat(
            value.directory_name,
            dir_fd=value.container_fd,
            follow_symlinks=False,
        )
        mapped_file = os.stat(value.name, dir_fd=value.directory_fd, follow_symlinks=False)
    except OSError as exc:
        raise P12GateError("P12 evidence input identity is no longer available") from exc
    if (
        not stat.S_ISDIR(directory_metadata.st_mode)
        or stat.S_IMODE(directory_metadata.st_mode) != 0o700
        or _inode(directory_metadata) != value.directory_identity
        or _inode(mapped_directory) != value.directory_identity
    ):
        raise P12GateError("P12 evidence input directory identity changed")
    if (
        not stat.S_ISREG(file_metadata.st_mode)
        or stat.S_IMODE(file_metadata.st_mode) != value.expected_mode
        or file_metadata.st_nlink != 1
        or _file_snapshot(file_metadata) != value.file_snapshot
        or _file_snapshot(mapped_file) != value.file_snapshot
    ):
        raise P12GateError("P12 evidence input file identity changed")
    return file_metadata


def _read_external_bytes(value: _HeldExternalFile) -> bytes:
    before = _revalidate_external_file(value)
    try:
        os.lseek(value.file_fd, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        while True:
            chunk = os.read(value.file_fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
    except OSError as exc:
        raise P12GateError("P12 evidence input cannot be read") from exc
    encoded = b"".join(chunks)
    after = _revalidate_external_file(value)
    if _file_snapshot(after) != _file_snapshot(before) or len(encoded) != before.st_size:
        raise P12GateError("P12 evidence input changed while being read")
    return encoded


def _valid_digest(value: object) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def validate_authorization(
    value: object,
    *,
    receipt_sha256: str,
    implementation_head: str,
    ci_run_id: int,
    ci_run_attempt: int = 1,
    envelope_digests: dict[str, str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != AUTHORIZATION_KEYS:
        raise P12GateError("P12 evidence authorization shape is invalid")
    if (
        not isinstance(ci_run_id, int)
        or isinstance(ci_run_id, bool)
        or ci_run_id <= 0
        or not isinstance(ci_run_attempt, int)
        or isinstance(ci_run_attempt, bool)
        or ci_run_attempt <= 0
    ):
        raise P12GateError("P12 evidence authorization numeric identity is invalid")
    expected_envelopes = envelope_digests or {
        "current-ci": "a" * 64,
        "portable-history": "b" * 64,
    }
    supplied = value.get("envelope_digests")
    if (
        not _exact_int(value.get("schema_version"), 1)
        or value.get("stage") != "p12_evidence_authorization"
        or value.get("receipt_sha256") != receipt_sha256
        or value.get("implementation_head") != implementation_head
        or not _exact_int(value.get("ci_run_id"), ci_run_id)
        or not _exact_int(value.get("ci_run_attempt"), ci_run_attempt)
        or supplied != expected_envelopes
        or set(expected_envelopes) != set(ENVELOPE_JOB_IDS)
        or not all(_valid_digest(item) for item in expected_envelopes.values())
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
    if expiry.tzinfo is None or expiry <= current:
        raise P12GateError("P12 evidence authorization expired")
    return value


def _open_or_create_directory(parent_fd: int, name: str) -> tuple[int, bool]:
    created = False
    descriptor = -1
    try:
        try:
            os.mkdir(name, mode=0o755, dir_fd=parent_fd)
            created = True
        except FileExistsError:
            pass
        descriptor = os.open(name, DIRECTORY_OPEN_FLAGS, dir_fd=parent_fd)
        metadata = os.fstat(descriptor)
        mapped = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISDIR(metadata.st_mode) or _inode(metadata) != _inode(mapped):
            raise P12GateError("P12 summary parent directory identity is invalid")
        return descriptor, created
    except (OSError, P12GateError) as exc:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if created:
            try:
                os.rmdir(name, dir_fd=parent_fd)
            except OSError:
                pass
        if isinstance(exc, P12GateError):
            raise
        raise P12GateError("P12 summary parent directory is unavailable") from exc


def _write_all(descriptor: int, encoded: bytes) -> None:
    offset = 0
    while offset < len(encoded):
        try:
            written = os.write(descriptor, encoded[offset:])
        except OSError as exc:
            raise P12GateError("P12 summary temporary file write failed") from exc
        if written <= 0:
            raise P12GateError("P12 summary temporary file write was incomplete")
        offset += written


def _entry_metadata(directory_fd: int, name: str) -> os.stat_result | None:
    try:
        return os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def write_evidence(root: Path, summary: dict[str, object]) -> None:
    encoded = canonical_json(summary)
    parts = Path(SUMMARY_PATH).parts
    if parts != ("artifacts", "p12", "summary.json"):
        raise P12GateError("P12 summary path identity is invalid")
    try:
        resolved_root = root.resolve(strict=True)
        root_fd = os.open(resolved_root, DIRECTORY_OPEN_FLAGS)
    except (OSError, RuntimeError) as exc:
        raise P12GateError("P12 summary repository root is unavailable") from exc

    directory_fds = [root_fd]
    created_directories: list[tuple[int, str, int]] = []
    temporary_fd = -1
    temporary_name: str | None = None
    temporary_identity: tuple[int, int] | None = None
    published_identity: tuple[int, int] | None = None
    succeeded = False
    output_directory_fd = -1
    try:
        current_fd = root_fd
        for part in parts[:-1]:
            child_fd, created = _open_or_create_directory(current_fd, part)
            directory_fds.append(child_fd)
            if created:
                created_directories.append((current_fd, part, child_fd))
            current_fd = child_fd
        output_directory_fd = current_fd
        destination_name = parts[-1]
        if _entry_metadata(output_directory_fd, destination_name) is not None:
            raise P12GateError("P12 summary path already exists")

        temporary_name = f".p12-summary-{secrets.token_hex(16)}"
        temporary_fd = os.open(
            temporary_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=output_directory_fd,
        )
        temporary_identity = _inode(os.fstat(temporary_fd))
        os.fchmod(temporary_fd, 0o600)
        _write_all(temporary_fd, encoded)
        os.fsync(temporary_fd)
        temporary_metadata = os.fstat(temporary_fd)
        if (
            not stat.S_ISREG(temporary_metadata.st_mode)
            or stat.S_IMODE(temporary_metadata.st_mode) != 0o600
            or temporary_metadata.st_nlink != 1
            or temporary_metadata.st_size != len(encoded)
        ):
            raise P12GateError("P12 summary temporary file identity is invalid")

        try:
            os.link(
                temporary_name,
                destination_name,
                src_dir_fd=output_directory_fd,
                dst_dir_fd=output_directory_fd,
                follow_symlinks=False,
            )
        except FileExistsError as exc:
            raise P12GateError("P12 summary path already exists") from exc
        linked_metadata = _entry_metadata(output_directory_fd, destination_name)
        if linked_metadata is None:
            raise P12GateError("P12 summary publication did not create the destination")
        published_identity = temporary_identity
        mapped_temporary = _entry_metadata(output_directory_fd, temporary_name)
        if (
            mapped_temporary is None
            or _inode(mapped_temporary) != temporary_identity
            or _inode(linked_metadata) != temporary_identity
            or linked_metadata.st_nlink != 2
            or linked_metadata.st_size != len(encoded)
            or stat.S_IMODE(linked_metadata.st_mode) != 0o600
        ):
            raise P12GateError("P12 summary publication inode is invalid")

        os.unlink(temporary_name, dir_fd=output_directory_fd)
        temporary_name = None
        final_descriptor_metadata = os.fstat(temporary_fd)
        final_path_metadata = _entry_metadata(output_directory_fd, destination_name)
        if (
            final_path_metadata is None
            or _inode(final_descriptor_metadata) != temporary_identity
            or _inode(final_path_metadata) != temporary_identity
            or final_descriptor_metadata.st_nlink != 1
            or final_path_metadata.st_nlink != 1
            or final_path_metadata.st_size != len(encoded)
            or stat.S_IMODE(final_path_metadata.st_mode) != 0o600
        ):
            raise P12GateError("P12 summary final inode is invalid")
        os.fsync(output_directory_fd)
        durable_descriptor_metadata = os.fstat(temporary_fd)
        durable_path_metadata = _entry_metadata(output_directory_fd, destination_name)
        if (
            durable_path_metadata is None
            or _inode(durable_descriptor_metadata) != temporary_identity
            or _inode(durable_path_metadata) != temporary_identity
            or durable_descriptor_metadata.st_nlink != 1
            or durable_path_metadata.st_nlink != 1
            or durable_path_metadata.st_size != len(encoded)
            or stat.S_IMODE(durable_path_metadata.st_mode) != 0o600
        ):
            raise P12GateError("P12 summary durable inode is invalid")
        succeeded = True
    except OSError as exc:
        raise P12GateError("P12 summary file operation failed") from exc
    finally:
        if not succeeded and output_directory_fd >= 0:
            if published_identity is not None:
                try:
                    current = _entry_metadata(output_directory_fd, parts[-1])
                    if current is not None and _inode(current) == published_identity:
                        os.unlink(parts[-1], dir_fd=output_directory_fd)
                except OSError:
                    pass
            if temporary_name is not None and temporary_identity is not None:
                try:
                    current = _entry_metadata(output_directory_fd, temporary_name)
                    if current is not None and _inode(current) == temporary_identity:
                        os.unlink(temporary_name, dir_fd=output_directory_fd)
                except OSError:
                    pass
            try:
                os.fsync(output_directory_fd)
            except OSError:
                pass
        if temporary_fd >= 0:
            try:
                os.close(temporary_fd)
            except OSError:
                pass
        if not succeeded:
            for parent_fd, name, child_fd in reversed(created_directories):
                try:
                    if not os.listdir(child_fd):
                        os.rmdir(name, dir_fd=parent_fd)
                except OSError:
                    pass
        for descriptor in reversed(directory_fds):
            try:
                os.close(descriptor)
            except OSError:
                pass


def _sha256_prefixed(value: object) -> bool:
    return isinstance(value, str) and value.startswith("sha256:") and _valid_digest(value[7:])


def _exact_int(value: object, expected: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value == expected


def _exact_json_equal(value: object, expected: object) -> bool:
    try:
        return canonical_json(value) == canonical_json(expected)
    except P12GateError:
        return False


def _safe_observed_value(value: object) -> bool:
    if not isinstance(value, str) or SAFE_VALUE.fullmatch(value) is None:
        return False
    lowered = value.lower()
    return (
        not value.startswith(("/", "~"))
        and re.search(r"(?:^|[\s=:])(?:/|[A-Za-z]:/)|://", value) is None
        and not any(
            marker in value or marker in lowered
            for marker in (
                "/Users/",
                "/home/",
                ".codex/",
                "ghp_",
                "sk-",
                "dc_session=",
                "token",
                "bearer",
            )
        )
    )


def _parse_utc(value: object, *, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise P12GateError(f"P12 {label} timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise P12GateError(f"P12 {label} timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise P12GateError(f"P12 {label} timestamp is invalid")
    return parsed


def _validate_jobs(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) != 2:
        raise P12GateError("P12 receipt CI job inventory is invalid")
    identities = (
        ("current-ci", "Current P12 governance non-publishing verification"),
        ("portable-history", "Portable historical replay"),
    )
    environment_keys = {
        "architecture",
        "docker_compose_version",
        "docker_server_version",
        "node_version",
        "npm_version",
        "python_version",
        "runner_image_os",
        "runner_image_version",
        "runner_os",
    }
    for job, (job_id, job_name) in zip(value, identities, strict=True):
        if not isinstance(job, dict) or set(job) != {
            "envelope_sha256",
            "job_database_id",
            "job_id",
            "job_name",
            "observed_environment",
        }:
            raise P12GateError("P12 receipt CI job shape is invalid")
        environment = job.get("observed_environment")
        if (
            job.get("job_id") != job_id
            or job.get("job_name") != job_name
            or not _valid_digest(job.get("envelope_sha256"))
            or not isinstance(job.get("job_database_id"), int)
            or isinstance(job.get("job_database_id"), bool)
            or job["job_database_id"] <= 0
            or not isinstance(environment, dict)
            or set(environment) != environment_keys
            or any(not _safe_observed_value(item) for item in environment.values())
            or str(environment.get("runner_os", "")).casefold() != "linux"
        ):
            raise P12GateError("P12 receipt CI job identity is invalid")
    if value[0]["job_database_id"] == value[1]["job_database_id"]:
        raise P12GateError("P12 receipt CI jobs share a database identity")
    if value[0]["envelope_sha256"] == value[1]["envelope_sha256"]:
        raise P12GateError("P12 receipt CI jobs share an envelope digest")
    return value


def _validate_excluded_results(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) != len(EXCLUDED_GATE_IDS):
        raise P12GateError("P12 excluded-result inventory is invalid")
    reasons = {
        "p8_compose_runtime": "linux_host_uid_private_bind_incompatible_with_container_uid_10001",
        "p8_golden_path": "transitively_invokes_excluded_p8_compose_runtime",
        "p10_compose_runtime": "immutable_darwin_guard_actual_macos_required",
        "p10_quickstart": "immutable_darwin_only_local_candidate_and_macos_result",
        "p10_remote_distribution": "immutable_remote_gate_includes_darwin_quickstart_and_macos_result",
    }
    for result, gate_id in zip(value, EXCLUDED_GATE_IDS, strict=True):
        if not isinstance(result, dict) or set(result) != {
            "gate_id",
            "item_type",
            "result",
            "exit_status",
            "platform_result",
            "embedded_anchor",
        }:
            raise P12GateError("P12 excluded result shape is invalid")
        platform = result.get("platform_result")
        expected_platform = {
            "replay_platform": "ubuntu-24.04",
            "ubuntu_historical_execution_status": "not_proven",
            "disposition": "excluded_acceptance_gate",
            "linux_public_pilot_readiness": "blocked",
            "executor_result": "not_run_platform_excluded",
            "exit_status": None,
            "reason": reasons[gate_id],
        }
        expected_anchor = {"gate_id": gate_id, **DARWIN_EVIDENCE_ANCHORS[gate_id]}
        if (
            result.get("gate_id") != gate_id
            or result.get("item_type") != "excluded_acceptance_gate"
            or result.get("result") != "not_run_platform_excluded"
            or result.get("exit_status") is not None
            or not _exact_json_equal(platform, expected_platform)
            or not _exact_json_equal(result.get("embedded_anchor"), expected_anchor)
        ):
            raise P12GateError("P12 excluded result identity is invalid")
    return value


def _inventory_item_results(root: Path, excluded: list[dict[str, Any]]) -> list[dict[str, Any]]:
    inventory_path = root / "docs/p12/portable-historical-inventory.json"
    inventory = parse_json_unique(inventory_path.read_bytes())
    if not isinstance(inventory, list) or len(inventory) != 151:
        raise P12GateError("P12 portable inventory cannot produce summary results")
    excluded_by_id = {item["gate_id"]: item for item in excluded}
    results: list[dict[str, Any]] = []
    for item in inventory:
        if not isinstance(item, dict) or not isinstance(item.get("gate_id"), str):
            raise P12GateError("P12 portable inventory item is invalid")
        gate_id = item["gate_id"]
        item_type = item.get("item_type")
        if item_type in {"setup", "included_acceptance_gate"}:
            result = {
                "gate_id": gate_id,
                "item_type": item_type,
                "result": "passed",
                "exit_status": 0,
            }
        elif item_type == "evidence_anchor":
            result = {
                "gate_id": gate_id,
                "item_type": item_type,
                "result": "identity_verified",
                "exit_status": None,
            }
        elif item_type == "excluded_acceptance_gate" and gate_id in excluded_by_id:
            result = excluded_by_id[gate_id]
        else:
            raise P12GateError("P12 portable inventory result classification is invalid")
        results.append(result)
    return results


def validate_preflight_receipt(
    root: Path,
    value: object,
    *,
    head: str,
    tree: str,
    records: tuple[CommitRecord, ...],
    now: datetime | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != RECEIPT_KEYS:
        raise P12GateError("P12 v4 preflight receipt shape is invalid")
    if (
        value.get("schema") != "digital-colleagues.p12-v4-evidence-preflight-receipt.v1"
        or value.get("repository") != REPOSITORY
        or value.get("lifecycle") != "pending_consumption"
        or not _exact_int(value.get("cleanup_residue_count"), 0)
        or not _exact_int(value.get("publication_count"), 0)
        or value.get("platform_status") != PLATFORM_STATUS
        or not isinstance(value.get("nonce"), str)
        or SHA256_RE.fullmatch(value["nonce"]) is None
        or not _sha256_prefixed(value.get("p10_protected_identity_digest"))
        or not _sha256_prefixed(value.get("package_verification_digest"))
    ):
        raise P12GateError("P12 v4 preflight receipt identity is invalid")
    current = now or datetime.now(UTC)
    issued = _parse_utc(value.get("issued_at"), label="receipt issue")
    expires = _parse_utc(value.get("expires_at"), label="receipt expiry")
    if issued > current or expires <= current or expires <= issued:
        raise P12GateError("P12 v4 preflight receipt lifecycle window is invalid")
    if value.get("acceptance") != {"blob": ACCEPTANCE_BLOB, "commit": ACCEPTANCE_COMMIT}:
        raise P12GateError("P12 receipt acceptance binding is invalid")
    implementation = value.get("implementation")
    ordered_commits = [record["commit"] for record in records]
    if implementation != {
        "head": head,
        "ordered_commits": ordered_commits,
        "range_digest": implementation_range_digest(records),
        "tree": tree,
    }:
        raise P12GateError("P12 receipt implementation range is invalid")
    ci = value.get("ci")
    if not isinstance(ci, dict) or set(ci) != {
        "base_ref",
        "base_sha",
        "event",
        "head_branch",
        "head_sha",
        "jobs",
        "pull_request_number",
        "run_attempt",
        "run_id",
        "workflow_path",
    }:
        raise P12GateError("P12 receipt CI shape is invalid")
    if (
        ci.get("base_ref") != "main"
        or ci.get("base_sha") != BASE_COMMIT
        or ci.get("event") != "pull_request"
        or ci.get("head_branch") != BRANCH
        or ci.get("head_sha") != head
        or ci.get("workflow_path") != ".github/workflows/ci.yml"
        or any(
            not isinstance(ci.get(key), int) or isinstance(ci.get(key), bool) or ci[key] <= 0
            for key in ("pull_request_number", "run_attempt", "run_id")
        )
    ):
        raise P12GateError("P12 receipt CI identity is invalid")
    _validate_jobs(ci.get("jobs"))
    inventory = value.get("inventory")
    inventory_keys = {
        "blob",
        "digest",
        "evidence_anchor_count",
        "excluded_acceptance_gate_count",
        "excluded_gate_ids",
        "excluded_results",
        "included_acceptance_gate_count",
        "item_results_digest",
        "passed_acceptance_gate_count",
        "path",
        "setup_count",
        "sha256",
        "skip_count",
        "total_item_count",
    }
    if not isinstance(inventory, dict) or set(inventory) != inventory_keys:
        raise P12GateError("P12 receipt inventory shape is invalid")
    inventory_path = root / "docs/p12/portable-historical-inventory.json"
    inventory_bytes = inventory_path.read_bytes()
    inventory_sha = hashlib.sha256(inventory_bytes).hexdigest()
    if (
        inventory.get("path") != "docs/p12/portable-historical-inventory.json"
        or inventory.get("blob") != git(root, "rev-parse", f"HEAD:{inventory['path']}")
        or inventory.get("sha256") != inventory_sha
        or inventory.get("digest") != f"sha256:{inventory_sha}"
        or not _exact_int(inventory.get("setup_count"), 5)
        or not _exact_int(inventory.get("included_acceptance_gate_count"), 124)
        or not _exact_int(inventory.get("evidence_anchor_count"), 17)
        or not _exact_int(inventory.get("excluded_acceptance_gate_count"), 5)
        or not _exact_int(inventory.get("total_item_count"), 151)
        or not _exact_int(inventory.get("passed_acceptance_gate_count"), 124)
        or not _exact_int(inventory.get("skip_count"), 0)
        or inventory.get("excluded_gate_ids") != list(EXCLUDED_GATE_IDS)
        or not _sha256_prefixed(inventory.get("item_results_digest"))
    ):
        raise P12GateError("P12 receipt inventory identity is invalid")
    excluded = _validate_excluded_results(inventory.get("excluded_results"))
    item_results = _inventory_item_results(root, excluded)
    expected_result_digest = f"sha256:{hashlib.sha256(canonical_json(item_results)).hexdigest()}"
    if inventory.get("item_results_digest") != expected_result_digest:
        raise P12GateError("P12 receipt item-result digest is invalid")
    ca = value.get("ca_verification")
    if not isinstance(ca, dict) or set(ca) != {
        "bundle_sha256",
        "certifi_version",
        "class",
        "status",
    }:
        raise P12GateError("P12 receipt CA verification shape is invalid")
    expected_bundle = (
        None
        if ca.get("class") == "system_default"
        else "9cc2a774b5198dcff14d9be1e66091f538975d867ce029a96bce15a55dfd730f"
    )
    if (
        ca.get("class") not in {"system_default", "locked_certifi"}
        or ca.get("bundle_sha256") != expected_bundle
        or ca.get("certifi_version") != "2026.7.22"
        or ca.get("status") != "passed"
    ):
        raise P12GateError("P12 receipt CA verification identity is invalid")
    registry = value.get("p12_current_p10_registry_protection")
    if (
        not isinstance(registry, dict)
        or set(registry) != {"result_digest", "status"}
        or registry.get("status") != "passed"
        or not _sha256_prefixed(registry.get("result_digest"))
    ):
        raise P12GateError("P12 receipt P10 registry protection is invalid")
    serialized = canonical_json(value).decode("utf-8")
    if any(marker in serialized for marker in ("/Users/", "/home/", ".codex/", "ghp_", "sk-")):
        raise P12GateError("P12 receipt contains local or credential material")
    return value


def build_summary(
    root: Path,
    *,
    receipt: dict[str, Any],
    receipt_sha256: str,
    records: tuple[CommitRecord, ...],
) -> dict[str, object]:
    head = git(root, "rev-parse", "HEAD")
    ci = receipt["ci"]
    inventory = dict(receipt["inventory"])
    excluded = _validate_excluded_results(inventory["excluded_results"])
    inventory["item_results"] = _inventory_item_results(root, excluded)
    return {
        "acceptance": {
            "blob": ACCEPTANCE_BLOB,
            "commit": ACCEPTANCE_COMMIT,
            "file_sha256": ACCEPTANCE_SHA256,
        },
        "base_commit": BASE_COMMIT,
        "base_tree": BASE_TREE,
        "ci_implementation_head": {
            "event": ci["event"],
            "head_sha": ci["head_sha"],
            "jobs": ci["jobs"],
            "pull_request_number": ci["pull_request_number"],
            "run_attempt": ci["run_attempt"],
            "run_id": ci["run_id"],
            "workflow_path": ci["workflow_path"],
        },
        "claim": CLAIM,
        "evidence_preflight_receipt_sha256": receipt_sha256,
        "implementation": {
            "head": head,
            "ordered_commits": [record["commit"] for record in records],
            "range_digest": implementation_range_digest(records),
            "tree": git(root, "rev-parse", "HEAD^{tree}"),
        },
        "inventory": inventory,
        "live_evidence": dict(NOT_EVALUATED),
        "migration_count": 8,
        "p10_protected_identity_digest": receipt["p10_protected_identity_digest"],
        "p12_current_p10_registry_protection": receipt["p12_current_p10_registry_protection"],
        "platform_status": dict(PLATFORM_STATUS),
        "publication_count": 0,
        "repository": REPOSITORY,
        "residue_count": 0,
        "schema": "digital-colleagues.p12-v4-summary.v1",
        "source_migration_count": 0,
        "test_counts": {"historical_python": 616, "p12_governance": 136},
    }


def _load_canonical_bytes(encoded: bytes, *, newline: bool) -> object:
    payload = encoded[:-1] if newline and encoded.endswith(b"\n") else encoded
    value = parse_json_unique(payload)
    if canonical_json(value, newline=newline) != encoded:
        raise P12GateError("P12 evidence input is not canonical P12-CJ-1")
    return value


def _load_canonical_file(path: Path, *, newline: bool) -> object:
    try:
        encoded = path.read_bytes()
    except OSError as exc:
        raise P12GateError("P12 evidence input cannot be read") from exc
    return _load_canonical_bytes(encoded, newline=newline)


def validate_summary(root: Path) -> dict[str, Any]:
    try:
        encoded = (root / SUMMARY_PATH).read_bytes()
        value = parse_json_unique(encoded)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise P12GateError("P12 summary JSON is invalid") from exc
    if canonical_json(value) != encoded:
        raise P12GateError("P12 summary is not canonical P12-CJ-1")
    if not isinstance(value, dict):
        raise P12GateError("P12 summary shape is invalid")
    implementation_head = git(root, "rev-parse", "HEAD^")
    records = implementation_range(root, implementation_head)
    expected_keys = {
        "acceptance",
        "base_commit",
        "base_tree",
        "ci_implementation_head",
        "claim",
        "evidence_preflight_receipt_sha256",
        "implementation",
        "inventory",
        "live_evidence",
        "migration_count",
        "p10_protected_identity_digest",
        "p12_current_p10_registry_protection",
        "platform_status",
        "publication_count",
        "repository",
        "residue_count",
        "schema",
        "source_migration_count",
        "test_counts",
    }
    if (
        set(value) != expected_keys
        or value.get("schema") != "digital-colleagues.p12-v4-summary.v1"
        or value.get("claim") != CLAIM
        or value.get("base_commit") != BASE_COMMIT
        or value.get("base_tree") != BASE_TREE
        or not _exact_json_equal(
            value.get("acceptance"),
            {
                "blob": ACCEPTANCE_BLOB,
                "commit": ACCEPTANCE_COMMIT,
                "file_sha256": ACCEPTANCE_SHA256,
            },
        )
        or not _exact_json_equal(
            value.get("implementation"),
            {
                "head": implementation_head,
                "ordered_commits": [record["commit"] for record in records],
                "range_digest": implementation_range_digest(records),
                "tree": git(root, "rev-parse", f"{implementation_head}^{{tree}}"),
            },
        )
        or not _exact_json_equal(value.get("live_evidence"), NOT_EVALUATED)
        or not _exact_json_equal(value.get("platform_status"), PLATFORM_STATUS)
        or not _exact_int(value.get("migration_count"), 8)
        or not _exact_int(value.get("source_migration_count"), 0)
        or not _exact_int(value.get("publication_count"), 0)
        or not _exact_int(value.get("residue_count"), 0)
        or value.get("repository") != REPOSITORY
        or not _valid_digest(value.get("evidence_preflight_receipt_sha256"))
        or not _sha256_prefixed(value.get("p10_protected_identity_digest"))
    ):
        raise P12GateError("P12 committed summary identity or topology is invalid")
    test_counts = value.get("test_counts")
    if (
        not isinstance(test_counts, dict)
        or set(test_counts) != {"historical_python", "p12_governance"}
        or not _exact_int(test_counts.get("historical_python"), 616)
        or not _exact_int(test_counts.get("p12_governance"), 136)
    ):
        raise P12GateError("P12 committed summary test counts are invalid")
    ci = value.get("ci_implementation_head")
    if (
        not isinstance(ci, dict)
        or set(ci)
        != {
            "event",
            "head_sha",
            "jobs",
            "pull_request_number",
            "run_attempt",
            "run_id",
            "workflow_path",
        }
        or ci.get("event") != "pull_request"
        or ci.get("head_sha") != implementation_head
        or ci.get("workflow_path") != ".github/workflows/ci.yml"
        or any(
            not isinstance(ci.get(key), int) or isinstance(ci.get(key), bool) or ci[key] <= 0
            for key in ("pull_request_number", "run_attempt", "run_id")
        )
    ):
        raise P12GateError("P12 committed summary CI identity is invalid")
    _validate_jobs(ci.get("jobs"))
    registry = value.get("p12_current_p10_registry_protection")
    if (
        not isinstance(registry, dict)
        or set(registry) != {"result_digest", "status"}
        or registry.get("status") != "passed"
        or not _sha256_prefixed(registry.get("result_digest"))
    ):
        raise P12GateError("P12 committed summary registry result is invalid")
    inventory = value.get("inventory")
    if not isinstance(inventory, dict) or set(inventory) != {
        "blob",
        "digest",
        "evidence_anchor_count",
        "excluded_acceptance_gate_count",
        "excluded_gate_ids",
        "excluded_results",
        "included_acceptance_gate_count",
        "item_results",
        "item_results_digest",
        "passed_acceptance_gate_count",
        "path",
        "setup_count",
        "sha256",
        "skip_count",
        "total_item_count",
    }:
        raise P12GateError("P12 committed summary inventory shape is invalid")
    inventory_path = "docs/p12/portable-historical-inventory.json"
    inventory_bytes = (root / inventory_path).read_bytes()
    inventory_sha = hashlib.sha256(inventory_bytes).hexdigest()
    excluded = _validate_excluded_results(inventory.get("excluded_results"))
    expected_results = _inventory_item_results(root, excluded)
    if (
        inventory.get("path") != inventory_path
        or inventory.get("blob")
        != git(root, "rev-parse", f"{implementation_head}:{inventory_path}")
        or inventory.get("sha256") != inventory_sha
        or inventory.get("digest") != f"sha256:{inventory_sha}"
        or not _exact_int(inventory.get("setup_count"), 5)
        or not _exact_int(inventory.get("included_acceptance_gate_count"), 124)
        or not _exact_int(inventory.get("evidence_anchor_count"), 17)
        or not _exact_int(inventory.get("excluded_acceptance_gate_count"), 5)
        or not _exact_int(inventory.get("total_item_count"), 151)
        or not _exact_int(inventory.get("passed_acceptance_gate_count"), 124)
        or not _exact_int(inventory.get("skip_count"), 0)
        or inventory.get("excluded_gate_ids") != list(EXCLUDED_GATE_IDS)
        or not _exact_json_equal(inventory.get("item_results"), expected_results)
        or inventory.get("item_results_digest")
        != f"sha256:{hashlib.sha256(canonical_json(expected_results)).hexdigest()}"
    ):
        raise P12GateError("P12 committed summary inventory identity is invalid")
    serialized = canonical_json(value).decode("utf-8")
    if any(
        marker in serialized
        for marker in ("/Users/", "/home/", ".codex/", "ghp_", "sk-", "dc_session=")
    ):
        raise P12GateError("P12 committed summary contains local or credential material")
    return value


def _validate_receipt_handoff(receipt: _HeldExternalFile) -> None:
    try:
        _revalidate_external_file(receipt)
        entries = tuple(os.listdir(receipt.directory_fd))
        _revalidate_external_file(receipt)
    except OSError as exc:
        raise P12GateError("P12 one-use receipt directory is unavailable") from exc
    if len(entries) != 1 or entries[0] != receipt.name:
        raise P12GateError("P12 one-use receipt directory is not exclusive")


def _consume_receipt(receipt: _HeldExternalFile) -> None:
    _consume_handoffs(receipt)


def _consume_handoffs(*paths: _HeldExternalFile) -> None:
    """Best-effort consume every validated one-use input before summary writing."""

    failed = False
    for path in paths:
        try:
            _validate_receipt_handoff(path)
            os.unlink(path.name, dir_fd=path.directory_fd)
            metadata = os.fstat(path.file_fd)
            if _inode(metadata) != path.file_snapshot[:2] or metadata.st_nlink != 0:
                raise P12GateError("P12 one-use handoff inode retained a link")
            if _entry_metadata(path.directory_fd, path.name) is not None:
                raise P12GateError("P12 one-use handoff name survived consumption")
        except (OSError, P12GateError):
            failed = True
    for path in paths:
        try:
            if os.listdir(path.directory_fd):
                raise P12GateError("P12 one-use handoff directory is not empty")
            directory_metadata = os.fstat(path.directory_fd)
            mapped_directory = os.stat(
                path.directory_name,
                dir_fd=path.container_fd,
                follow_symlinks=False,
            )
            if (
                _inode(directory_metadata) != path.directory_identity
                or _inode(mapped_directory) != path.directory_identity
                or stat.S_IMODE(directory_metadata.st_mode) != 0o700
            ):
                raise P12GateError("P12 one-use handoff directory identity changed")
            os.rmdir(path.directory_name, dir_fd=path.container_fd)
            try:
                os.stat(
                    path.directory_name,
                    dir_fd=path.container_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                pass
            else:
                raise P12GateError("P12 one-use handoff directory survived consumption")
        except (OSError, P12GateError):
            failed = True
    if failed:
        raise P12GateError("P12 one-use handoff consumption failed")


def _receipt_envelope_digests(receipt: dict[str, Any]) -> dict[str, str]:
    ci = receipt.get("ci")
    jobs = ci.get("jobs") if isinstance(ci, dict) else None
    validated = _validate_jobs(jobs)
    return {str(job["job_id"]): str(job["envelope_sha256"]) for job in validated}


def collect(
    root: Path, *, receipt_value: str, expected_digest: str, authorization_value: str
) -> None:
    with (
        _external_file(root, receipt_value, mode=0o600) as receipt_path,
        _external_file(root, authorization_value, mode=0o600) as authorization_path,
    ):
        if _inode(os.fstat(receipt_path.file_fd)) == _inode(os.fstat(authorization_path.file_fd)):
            raise P12GateError("P12 receipt and authorization must be distinct files")
        _validate_receipt_handoff(receipt_path)
        _validate_receipt_handoff(authorization_path)
        try:
            if git(root, "branch", "--show-current") != BRANCH:
                raise P12GateError("P12 evidence writer branch identity is invalid")
            check_repository(root, mode="implementation")
            check_historical_inventory(root)
            check_provenance(root)
            encoded = _read_external_bytes(receipt_path)
            authorization_encoded = _read_external_bytes(authorization_path)
            actual_digest = hashlib.sha256(encoded).hexdigest()
            if actual_digest != expected_digest or not _valid_digest(expected_digest):
                raise P12GateError("P12 preflight receipt digest is invalid")
            receipt = _load_canonical_bytes(encoded, newline=False)
            head = git(root, "rev-parse", "HEAD")
            tree = git(root, "rev-parse", "HEAD^{tree}")
            if SHA_RE.fullmatch(head) is None:
                raise P12GateError("P12 implementation head identity is invalid")
            records = implementation_range(root, head)
            receipt = validate_preflight_receipt(
                root,
                receipt,
                head=head,
                tree=tree,
                records=records,
            )
            ci = receipt["ci"]
            envelope_digests = _receipt_envelope_digests(receipt)
            authorization = _load_canonical_bytes(authorization_encoded, newline=False)
            validate_authorization(
                authorization,
                receipt_sha256=actual_digest,
                implementation_head=head,
                ci_run_id=ci["run_id"],
                ci_run_attempt=ci["run_attempt"],
                envelope_digests=envelope_digests,
            )
            summary = build_summary(
                root,
                receipt=receipt,
                receipt_sha256=actual_digest,
                records=records,
            )
        finally:
            _consume_handoffs(receipt_path, authorization_path)
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
