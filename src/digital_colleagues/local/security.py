# SPDX-License-Identifier: Apache-2.0

"""Cryptographic and operator-file adapters confined to the local composition boundary."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from digital_colleagues.application.p4_services import AuthenticationService


@dataclass(frozen=True, slots=True)
class UtcClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class SecureTokenSource:
    def issue(self, byte_count: int) -> str:
        if type(byte_count) is not int or byte_count < 32:
            raise ValueError("credential entropy must be at least 256 bits")
        return secrets.token_urlsafe(byte_count)


@dataclass(frozen=True, slots=True)
class CredentialDigests:
    def digest(self, purpose: str, plaintext: str) -> str:
        if not purpose or not plaintext:
            raise ValueError("credential digest input is incomplete")
        framed = hashlib.sha256()
        encoded_purpose = purpose.encode("utf-8")
        encoded_plaintext = plaintext.encode("utf-8")
        framed.update(len(encoded_purpose).to_bytes(8, "big"))
        framed.update(encoded_purpose)
        framed.update(len(encoded_plaintext).to_bytes(8, "big"))
        framed.update(encoded_plaintext)
        return "sha256:" + framed.hexdigest()

    def matches(self, expected: str, actual: str) -> bool:
        return hmac.compare_digest(expected, actual)


def retrieve_bootstrap_for_operator(authentication: AuthenticationService) -> str:
    """Create and atomically claim plaintext entirely inside the one-shot process."""

    _, plaintext = authentication.ensure_bootstrap()
    if plaintext is None:
        raise RuntimeError("bootstrap token is unavailable or was already initialized")
    authentication.claim_operator_retrieval(plaintext)
    return plaintext
