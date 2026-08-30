# SPDX-License-Identifier: Apache-2.0

"""Explicit deterministic time, ID, and entropy adapters for tests and examples."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from digital_colleagues.core.common import require_stable_id, require_utc


@dataclass(frozen=True, slots=True)
class FixedClock:
    value: datetime

    def __post_init__(self) -> None:
        require_utc(self.value, "fixed clock value")

    def now(self) -> datetime:
        return self.value


@dataclass(frozen=True, slots=True)
class StableHashIdentifier:
    namespace: str = "p3"

    def __post_init__(self) -> None:
        require_stable_id(self.namespace, "identifier namespace")

    def derive(self, kind: str, *parts: str) -> str:
        require_stable_id(kind, "identifier kind")
        if not parts or any(not isinstance(part, str) or not part for part in parts):
            raise ValueError("identifier derivation requires explicit non-empty parts")
        framed = hashlib.sha256()
        for value in (self.namespace, kind, *parts):
            encoded = value.encode("utf-8")
            framed.update(len(encoded).to_bytes(8, "big"))
            framed.update(encoded)
        return f"{kind}:{framed.hexdigest()[:32]}"


@dataclass(frozen=True, slots=True)
class FixedEntropy:
    value: bytes

    def token_bytes(self, length: int) -> bytes:
        if type(length) is not int or length < 1 or len(self.value) < length:
            raise ValueError("requested entropy length is unavailable")
        return bytes(self.value[:length])
