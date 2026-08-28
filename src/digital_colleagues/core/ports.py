# SPDX-License-Identifier: Apache-2.0

"""Stable injection protocols; P2 provides no implementations."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Return an externally supplied timezone-aware UTC timestamp."""


class IdentifierSource(Protocol):
    def next_id(self, kind: str) -> str:
        """Return an externally supplied stable string identifier."""


class EntropySource(Protocol):
    def token_bytes(self, length: int) -> bytes:
        """Return externally supplied entropy outside deterministic core policy."""
