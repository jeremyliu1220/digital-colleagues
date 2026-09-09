# SPDX-License-Identifier: Apache-2.0

"""Bounded ZIP validation without extracting untrusted package content."""

from __future__ import annotations

import io
import json
import stat
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Final

from digital_colleagues.application.errors import ValidationError
from digital_colleagues.application.p11_contracts import PackageInspection
from digital_colleagues.core.agent_package import (
    AgentPackage,
    agent_package_from_mapping,
    canonical_json_bytes,
    sha256_digest,
)
from digital_colleagues.core.errors import CoreInvariantError

ARCHIVE_MAX_BYTES: Final = 131_072
ARCHIVE_MAX_MEMBERS: Final = 4
ARCHIVE_MAX_MEMBER_BYTES: Final = 131_072
ARCHIVE_MAX_TOTAL_BYTES: Final = 131_072
ARCHIVE_MAX_RATIO: Final = 20
ARCHIVE_MAX_DEPTH: Final = 2
PACKAGE_MEMBER: Final = "agent.json"


@dataclass(frozen=True, slots=True)
class ValidatedPackageArchive:
    package: AgentPackage
    archive_digest: str
    package_digest: str
    compressed_size: int
    uncompressed_size: int


class PackageArchiveValidator:
    """Application-port implementation for bounded inert ZIP validation."""

    def validate(
        self,
        archive: bytes,
        *,
        expected_archive_digest: str | None = None,
    ) -> PackageInspection:
        validated = validate_package_archive(
            archive,
            expected_archive_digest=expected_archive_digest,
        )
        return PackageInspection(
            package=validated.package,
            package_digest=validated.package_digest,
            archive_digest=validated.archive_digest,
            compressed_size=validated.compressed_size,
            uncompressed_size=validated.uncompressed_size,
        )


def _pairs(values: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in values:
        if key in result:
            raise ValidationError("package JSON contains a duplicate key")
        result[key] = value
    return result


def _parse_json(value: bytes) -> object:
    try:
        text = value.decode("utf-8", errors="strict")
        return json.loads(
            text, object_pairs_hook=_pairs, parse_constant=lambda _: _invalid_number()
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError("agent.json is not strict UTF-8 JSON") from exc


def _invalid_number() -> object:
    raise ValidationError("package JSON number is unsupported")


def _safe_member(info: zipfile.ZipInfo) -> None:
    name = info.filename
    if not name or "\\" in name or "\x00" in name:
        raise ValidationError("archive member path is invalid")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValidationError("archive member path traversal is forbidden")
    if len(path.parts) > ARCHIVE_MAX_DEPTH:
        raise ValidationError("archive nesting exceeds the fixed bound")
    if any(part.startswith(".") for part in path.parts):
        raise ValidationError("hidden archive payload is forbidden")
    if info.flag_bits & 0x1 or info.comment:
        raise ValidationError("encrypted or commented archive member is forbidden")
    unix_mode = (info.external_attr >> 16) & 0xFFFF
    file_type = stat.S_IFMT(unix_mode)
    if info.is_dir() or file_type not in {0, stat.S_IFREG}:
        raise ValidationError("archive links and special files are forbidden")
    if info.file_size < 0 or info.file_size > ARCHIVE_MAX_MEMBER_BYTES:
        raise ValidationError("archive member exceeds the fixed size bound")
    if info.compress_size < 0:
        raise ValidationError("archive compressed size is invalid")
    if info.file_size and info.compress_size == 0:
        raise ValidationError("archive compression ratio is invalid")
    if info.compress_size and info.file_size > info.compress_size * ARCHIVE_MAX_RATIO:
        raise ValidationError("archive compression ratio exceeds the fixed bound")


def validate_package_archive(
    archive: bytes,
    *,
    expected_archive_digest: str | None = None,
) -> ValidatedPackageArchive:
    """Validate an exact one-file package archive without generic extraction."""

    if not isinstance(archive, bytes) or not archive or len(archive) > ARCHIVE_MAX_BYTES:
        raise ValidationError("package archive is empty or exceeds the fixed bound")
    archive_digest = sha256_digest(archive)
    if expected_archive_digest is not None and archive_digest != expected_archive_digest:
        raise ValidationError("package archive digest does not match the expected value")
    try:
        with zipfile.ZipFile(io.BytesIO(archive), mode="r") as package_zip:
            if package_zip.comment:
                raise ValidationError("archive comments are forbidden")
            members = package_zip.infolist()
            if not 1 <= len(members) <= ARCHIVE_MAX_MEMBERS:
                raise ValidationError("archive file count is outside the fixed bound")
            names: set[str] = set()
            folded: set[str] = set()
            total = 0
            for info in members:
                _safe_member(info)
                normalized = info.filename
                collision = normalized.casefold()
                if normalized in names or collision in folded:
                    raise ValidationError("archive contains duplicate or case-colliding members")
                names.add(normalized)
                folded.add(collision)
                total += info.file_size
                if total > ARCHIVE_MAX_TOTAL_BYTES:
                    raise ValidationError("archive total content exceeds the fixed bound")
            if names != {PACKAGE_MEMBER}:
                raise ValidationError("archive must contain only agent.json")
            info = members[0]
            with package_zip.open(info, mode="r") as source:
                content = source.read(ARCHIVE_MAX_MEMBER_BYTES + 1)
            if len(content) != info.file_size or len(content) > ARCHIVE_MAX_MEMBER_BYTES:
                raise ValidationError("archive member read exceeded its declared bound")
    except (zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, OSError) as exc:
        raise ValidationError("package archive is invalid") from exc
    parsed = _parse_json(content)
    try:
        package = agent_package_from_mapping(parsed)
        if content != canonical_json_bytes(package.to_data()):
            raise ValidationError("agent.json is not the canonical package encoding")
    except CoreInvariantError as exc:
        raise ValidationError("AgentPackage schema validation failed") from exc
    return ValidatedPackageArchive(
        package=package,
        archive_digest=archive_digest,
        package_digest=package.package_digest,
        compressed_size=len(archive),
        uncompressed_size=len(content),
    )
