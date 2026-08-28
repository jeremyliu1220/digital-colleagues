# SPDX-License-Identifier: Apache-2.0

"""Shared deterministic value validation and deep-freezing helpers."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

from digital_colleagues.core.errors import CoreInvariantError

SCHEMA_VERSION: Final = 1
_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._:-]{0,127}\Z")
_SHA256_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")


def require_text(value: str, field: str, *, maximum: int = 4_096) -> str:
    """Return a stripped non-empty bounded string."""

    if not isinstance(value, str):
        raise CoreInvariantError(f"{field} must be a string")
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise CoreInvariantError(f"{field} must be non-empty and bounded")
    return normalized


def require_stable_id(value: str, field: str) -> str:
    """Validate an explicit, storage-neutral stable string identifier."""

    if not isinstance(value, str) or _ID_PATTERN.fullmatch(value) is None:
        raise CoreInvariantError(f"{field} must be an explicit stable string ID")
    return value


def require_revision(value: int, field: str = "revision") -> int:
    if type(value) is not int or value < 1:
        raise CoreInvariantError(f"{field} must be a positive integer")
    return value


def require_schema_version(value: int) -> int:
    if value != SCHEMA_VERSION:
        raise CoreInvariantError("unsupported schema_version")
    return value


def require_digest(value: str, field: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise CoreInvariantError(f"{field} must be a lowercase SHA-256 digest")
    return value


def require_utc(value: datetime, field: str) -> datetime:
    """Reject naive or non-UTC authoritative timestamps."""

    if not isinstance(value, datetime) or value.tzinfo is None:
        raise CoreInvariantError(f"{field} must be timezone-aware UTC")
    try:
        offset = value.utcoffset()
    except (OverflowError, ValueError) as exc:
        raise CoreInvariantError(f"{field} must be timezone-aware UTC") from exc
    if offset != timedelta(0):
        raise CoreInvariantError(f"{field} must be UTC")
    return value


def freeze_strings(values: object, field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    """Copy an iterable of strings into an immutable tuple with no duplicates."""

    if isinstance(values, str):
        raise CoreInvariantError(f"{field} must be a collection of strings")
    if not isinstance(values, Iterable):
        raise CoreInvariantError(f"{field} must be a collection of strings")
    items: tuple[object, ...] = tuple(values)
    normalized_items: list[str] = []
    for item in items:
        if not isinstance(item, str):
            raise CoreInvariantError(f"{field} must contain only strings")
        normalized_items.append(require_text(item, field))
    normalized = tuple(normalized_items)
    if not allow_empty and not normalized:
        raise CoreInvariantError(f"{field} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise CoreInvariantError(f"{field} must not contain duplicates")
    return normalized


@dataclass(frozen=True, slots=True)
class FrozenJsonObject(Mapping[str, object]):
    """A sorted immutable JSON object whose nested collections are also immutable."""

    _entries: tuple[tuple[str, object], ...]

    def __post_init__(self) -> None:
        try:
            raw_entries = tuple(self._entries)
        except TypeError as exc:
            raise CoreInvariantError("JSON object entries must be a collection") from exc
        normalized: list[tuple[str, object]] = []
        for entry in raw_entries:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise CoreInvariantError("JSON object entries must be key-value pairs")
            key, value = entry
            normalized.append(
                (
                    require_text(key, "JSON object key", maximum=256),
                    freeze_json(value),
                )
            )
        normalized.sort(key=lambda item: item[0])
        if len({key for key, _ in normalized}) != len(normalized):
            raise CoreInvariantError("JSON object keys must be unique")
        object.__setattr__(self, "_entries", tuple(normalized))

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> FrozenJsonObject:
        return cls(tuple(values.items()))

    def __getitem__(self, key: str) -> object:
        for candidate, value in self._entries:
            if candidate == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (key for key, _ in self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def as_entries(self) -> tuple[tuple[str, object], ...]:
        return self._entries


def freeze_json(value: object) -> object:
    """Copy a JSON-compatible tree into canonical immutable values."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CoreInvariantError("JSON numbers must be finite")
        return value
    if isinstance(value, FrozenJsonObject):
        return value
    if isinstance(value, Mapping):
        return FrozenJsonObject.from_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(freeze_json(item) for item in value)
    raise CoreInvariantError("value must be JSON-compatible")
