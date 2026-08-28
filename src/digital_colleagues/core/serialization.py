# SPDX-License-Identifier: Apache-2.0

"""Deterministic public serialization for stable core contracts."""

from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum

from digital_colleagues.core.common import FrozenJsonObject, require_utc
from digital_colleagues.core.effects import EffectProposal
from digital_colleagues.core.errors import CoreInvariantError


def datetime_to_z(value: datetime) -> str:
    require_utc(value, "datetime")
    return value.isoformat(timespec="microseconds").removesuffix("+00:00") + "Z"


def datetime_from_z(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise CoreInvariantError("serialized datetime must use an ISO 8601 Z suffix")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CoreInvariantError("serialized datetime is invalid") from exc
    return require_utc(parsed, "datetime")


def contract_to_public_data(value: object) -> object:
    """Convert a contract to safe JSON data without exposing effect payload bytes."""

    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, datetime):
        return datetime_to_z(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, FrozenJsonObject):
        return {key: contract_to_public_data(item) for key, item in value.as_entries()}
    if isinstance(value, tuple):
        return [contract_to_public_data(item) for item in value]
    if isinstance(value, frozenset):
        return sorted(contract_to_public_data(item) for item in value)  # type: ignore[type-var]
    if is_dataclass(value) and not isinstance(value, type):
        sensitive_fields = {"payload"} if isinstance(value, EffectProposal) else set()
        return {
            field.name: contract_to_public_data(getattr(value, field.name))
            for field in fields(value)
            if field.name not in sensitive_fields and not field.name.startswith("_")
        }
    raise CoreInvariantError("unsupported public contract value")


def to_canonical_json(value: object) -> str:
    return json.dumps(
        contract_to_public_data(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
