# SPDX-License-Identifier: Apache-2.0

"""Safe, finite failure vocabulary for optional HTTP JSON adapters."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum

PROTOCOL_VERSION = "dc-http-json-v1"


class AdapterFailureCategory(StrEnum):
    INVALID_CONFIGURATION = "invalid_configuration"
    INVALID_RESPONSE = "invalid_response"
    AUTHORITY_INJECTION = "authority_injection"
    OVERSIZED_REQUEST = "oversized_request"
    OVERSIZED_RESPONSE = "oversized_response"
    TIMEOUT = "timeout"
    DNS_FAILURE = "dns_failure"
    CONNECT_FAILURE = "connect_failure"
    TLS_FAILURE = "tls_failure"
    DISCONNECTED = "disconnected"
    UNAUTHORIZED = "unauthorized"
    RATE_LIMITED = "rate_limited"
    SERVER_FAILURE = "server_failure"
    REDIRECT_REFUSED = "redirect_refused"
    HTTP_FAILURE = "http_failure"


def safe_digest(category: AdapterFailureCategory, result_class: str) -> str:
    encoded = json.dumps(
        {
            "category": category.value,
            "protocol_version": PROTOCOL_VERSION,
            "result_class": result_class,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


class AdapterFailure(RuntimeError):
    """An adapter failure whose string form contains no endpoint, body, or credential."""

    def __init__(
        self,
        category: AdapterFailureCategory,
        *,
        result_class: str,
        after_submit: bool = False,
    ) -> None:
        self.category = category
        self.protocol_version = PROTOCOL_VERSION
        self.result_class = result_class
        self.after_submit = after_submit
        self.diagnostic_digest = safe_digest(category, result_class)
        super().__init__(
            "optional adapter failure "
            f"category={category.value} protocol={PROTOCOL_VERSION} "
            f"result={result_class} digest={self.diagnostic_digest}"
        )
