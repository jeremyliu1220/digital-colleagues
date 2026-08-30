# SPDX-License-Identifier: Apache-2.0

"""Canonical private storage codec with construction-time invariant replay."""

from __future__ import annotations

import json
from dataclasses import Field, fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from digital_colleagues.application.errors import PersistenceError
from digital_colleagues.core.authority import (
    CapabilityGrant,
    Constraint,
    EffectBoundary,
    EffectKind,
    Mandate,
    Profile,
    ResponsibilityDefinition,
)
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.effects import (
    ActionResult,
    ActionResultState,
    ApprovalChoice,
    EffectAttempt,
    EffectAttemptState,
    EffectConstraints,
    EffectDestination,
    EffectProposal,
    EffectProposalState,
    HumanApprovalDecision,
)
from digital_colleagues.core.namespace import Namespace, NamespaceScope
from digital_colleagues.core.principals import HumanRole, Principal, PrincipalKind
from digital_colleagues.core.runtime import (
    AgendaItem,
    AgendaItemState,
    Decision,
    DecisionKind,
    InputEvent,
    InputEventState,
    WakeCycle,
    WakeCycleState,
)
from digital_colleagues.core.serialization import datetime_from_z, datetime_to_z
from digital_colleagues.core.work import (
    CompletionEvidence,
    FiniteWork,
    Obligation,
    ObligationState,
    Responsibility,
    ResponsibilityState,
    WorkState,
)

_DATACLASSES: tuple[type[object], ...] = (
    Namespace,
    Principal,
    ResponsibilityDefinition,
    CapabilityGrant,
    Constraint,
    EffectBoundary,
    Profile,
    Mandate,
    CompletionEvidence,
    FiniteWork,
    Responsibility,
    Obligation,
    InputEvent,
    WakeCycle,
    AgendaItem,
    Decision,
    EffectDestination,
    EffectConstraints,
    EffectProposal,
    HumanApprovalDecision,
    EffectAttempt,
    ActionResult,
)
_ENUMS: tuple[type[Enum], ...] = (
    NamespaceScope,
    PrincipalKind,
    HumanRole,
    EffectKind,
    WorkState,
    ResponsibilityState,
    ObligationState,
    InputEventState,
    WakeCycleState,
    AgendaItemState,
    DecisionKind,
    EffectProposalState,
    ApprovalChoice,
    EffectAttemptState,
    ActionResultState,
)
_DATACLASS_REGISTRY = {value.__name__: value for value in _DATACLASSES}
_ENUM_REGISTRY = {value.__name__: value for value in _ENUMS}


def _encode(value: object) -> object:
    if isinstance(value, datetime):
        return {"$datetime": datetime_to_z(value)}
    if isinstance(value, Enum):
        return {"$enum": type(value).__name__, "value": value.value}
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, FrozenJsonObject):
        return {"$frozen_json": [[key, _encode(item)] for key, item in value.as_entries()]}
    if isinstance(value, tuple):
        return {"$tuple": [_encode(item) for item in value]}
    if isinstance(value, frozenset):
        encoded = [_encode(item) for item in value]
        return {"$frozenset": sorted(encoded, key=lambda item: json.dumps(item, sort_keys=True))}
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "$dataclass": type(value).__name__,
            "fields": {field.name: _encode(getattr(value, field.name)) for field in fields(value)},
        }
    if isinstance(value, dict):
        return {key: _encode(item) for key, item in sorted(value.items())}
    raise PersistenceError("a durable record contains an unsupported value")


def _decode(value: object) -> object:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, list):
        return [_decode(item) for item in value]
    if not isinstance(value, dict):
        raise PersistenceError("a durable record has an invalid encoded shape")
    if set(value) == {"$datetime"}:
        raw = value["$datetime"]
        if not isinstance(raw, str):
            raise PersistenceError("a durable timestamp has an invalid shape")
        return datetime_from_z(raw)
    if set(value) == {"$enum", "value"}:
        enum_name = value["$enum"]
        raw = value["value"]
        if not isinstance(enum_name, str) or enum_name not in _ENUM_REGISTRY:
            raise PersistenceError("a durable enum type is unsupported")
        try:
            return _ENUM_REGISTRY[enum_name](raw)
        except (TypeError, ValueError) as exc:
            raise PersistenceError("a durable enum value is unsupported") from exc
    if set(value) == {"$frozen_json"}:
        raw_entries = value["$frozen_json"]
        if not isinstance(raw_entries, list):
            raise PersistenceError("a durable JSON object has an invalid shape")
        entries: list[tuple[str, object]] = []
        for entry in raw_entries:
            if not isinstance(entry, list) or len(entry) != 2 or not isinstance(entry[0], str):
                raise PersistenceError("a durable JSON entry has an invalid shape")
            entries.append((entry[0], _decode(entry[1])))
        return FrozenJsonObject(tuple(entries))
    if set(value) == {"$tuple"}:
        raw_items = value["$tuple"]
        if not isinstance(raw_items, list):
            raise PersistenceError("a durable tuple has an invalid shape")
        return tuple(_decode(item) for item in raw_items)
    if set(value) == {"$frozenset"}:
        raw_items = value["$frozenset"]
        if not isinstance(raw_items, list):
            raise PersistenceError("a durable set has an invalid shape")
        return frozenset(_decode(item) for item in raw_items)
    if set(value) == {"$dataclass", "fields"}:
        class_name = value["$dataclass"]
        raw_fields = value["fields"]
        if not isinstance(class_name, str) or class_name not in _DATACLASS_REGISTRY:
            raise PersistenceError("a durable dataclass type is unsupported")
        if not isinstance(raw_fields, dict):
            raise PersistenceError("a durable dataclass has invalid fields")
        cls = _DATACLASS_REGISTRY[class_name]
        declared: tuple[Field[Any], ...] = fields(cls)  # type: ignore[arg-type]
        if set(raw_fields) != {field.name for field in declared}:
            raise PersistenceError("a durable dataclass field set drifted")
        decoded = {name: _decode(item) for name, item in raw_fields.items()}
        kwargs = {field.name: decoded[field.name] for field in declared if field.init}
        try:
            instance = cls(**kwargs)
        except (TypeError, ValueError) as exc:
            raise PersistenceError("a durable record violates current invariants") from exc
        for field in declared:
            if not field.init and getattr(instance, field.name) != decoded[field.name]:
                raise PersistenceError("a durable computed integrity field drifted")
        return instance
    return {str(key): _decode(item) for key, item in value.items()}


def to_storage_json(value: object) -> str:
    return json.dumps(_encode(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def from_storage_json[T](value: str, expected: type[T]) -> T:
    try:
        decoded = _decode(json.loads(value))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise PersistenceError("a durable record contains invalid JSON") from exc
    if not isinstance(decoded, expected):
        raise PersistenceError("a durable record has the wrong contract type")
    return decoded
