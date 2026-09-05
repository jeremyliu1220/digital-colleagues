# SPDX-License-Identifier: Apache-2.0

"""Bounded standard-library HTTP transport with redirects disabled by construction."""

from __future__ import annotations

import base64
import http.client
import json
import socket
import ssl
import time
from dataclasses import dataclass
from typing import Any

from digital_colleagues.adapters.http_json.configuration import HttpJsonSettings
from digital_colleagues.adapters.http_json.errors import (
    PROTOCOL_VERSION,
    AdapterFailure,
    AdapterFailureCategory,
)


@dataclass(frozen=True, slots=True)
class HttpJsonResponse:
    status: int
    content_type: str
    body: bytes = b""


def canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise AdapterFailure(
            AdapterFailureCategory.INVALID_RESPONSE,
            result_class="non_json_value",
        ) from None


def _pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in values:
        if key in result:
            raise ValueError("duplicate")
        result[key] = value
    return result


def parse_json_object(body: bytes) -> dict[str, Any]:
    try:
        decoded = body.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("constant")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise AdapterFailure(
            AdapterFailureCategory.INVALID_RESPONSE,
            result_class="invalid_json",
        ) from None
    if not isinstance(value, dict):
        raise AdapterFailure(
            AdapterFailureCategory.INVALID_RESPONSE,
            result_class="non_object_json",
        )
    return value


def _network_failure(exc: BaseException, *, after_submit: bool) -> AdapterFailure:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        category = AdapterFailureCategory.TIMEOUT
    elif isinstance(exc, socket.gaierror):
        category = AdapterFailureCategory.DNS_FAILURE
    elif isinstance(exc, ssl.SSLError):
        category = AdapterFailureCategory.TLS_FAILURE
    elif after_submit and isinstance(
        exc,
        (
            BrokenPipeError,
            ConnectionAbortedError,
            ConnectionResetError,
            http.client.BadStatusLine,
            http.client.IncompleteRead,
            http.client.RemoteDisconnected,
        ),
    ):
        category = AdapterFailureCategory.DISCONNECTED
    else:
        category = AdapterFailureCategory.CONNECT_FAILURE
    return AdapterFailure(
        category,
        result_class="post_submit_unknown" if after_submit else "not_submitted",
        after_submit=after_submit,
    )


class HttpJsonTransport:
    def __init__(self, settings: HttpJsonSettings) -> None:
        self._settings = settings
        credential = settings.read_credential()
        self._authorization = "Bearer " + base64.urlsafe_b64encode(credential).decode("ascii")

    def post(self, payload: object, *, idempotency_key: str | None = None) -> HttpJsonResponse:
        body = canonical_json(payload)
        if len(body) > self._settings.maximum_request_bytes:
            raise AdapterFailure(
                AdapterFailureCategory.OVERSIZED_REQUEST,
                result_class="request_refused",
            )
        parsed = self._settings.parsed_endpoint
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        host = parsed.hostname
        assert host is not None
        headers = {
            "Accept": "application/json",
            "Authorization": self._authorization,
            "Content-Length": str(len(body)),
            "Content-Type": "application/json",
            "X-DC-Protocol": PROTOCOL_VERSION,
        }
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        started = time.monotonic()
        deadline = started + self._settings.total_timeout_seconds

        def remaining_timeout(*, read_bound: bool = False) -> float:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AdapterFailure(
                    AdapterFailureCategory.TIMEOUT,
                    result_class="total_deadline_exceeded",
                    after_submit=True,
                )
            if read_bound:
                return min(self._settings.read_timeout_seconds, remaining)
            return remaining

        connect_timeout = min(
            self._settings.connect_timeout_seconds,
            max(0.001, deadline - time.monotonic()),
        )
        connection: http.client.HTTPConnection
        if parsed.scheme == "https":
            connection = http.client.HTTPSConnection(
                host,
                port,
                timeout=connect_timeout,
                context=ssl.create_default_context(),
            )
        else:
            connection = http.client.HTTPConnection(
                host,
                port,
                timeout=connect_timeout,
            )
        try:
            try:
                connection.connect()
            except (OSError, http.client.HTTPException) as exc:
                raise _network_failure(exc, after_submit=False) from None
            if time.monotonic() >= deadline:
                raise AdapterFailure(
                    AdapterFailureCategory.TIMEOUT,
                    result_class="not_submitted",
                )
            if connection.sock is not None:
                connection.sock.settimeout(remaining_timeout(read_bound=True))
            try:
                connection.request("POST", parsed.path or "/", body=body, headers=headers)
                if connection.sock is not None:
                    connection.sock.settimeout(remaining_timeout(read_bound=True))
                response = connection.getresponse()
            except (OSError, http.client.HTTPException) as exc:
                raise _network_failure(exc, after_submit=True) from None
            status = response.status
            content_type = response.getheader("Content-Type", "")
            if 300 <= status <= 399:
                raise AdapterFailure(
                    AdapterFailureCategory.REDIRECT_REFUSED,
                    result_class="redirect_refused",
                    after_submit=True,
                )
            if status != 200:
                return HttpJsonResponse(status=status, content_type=content_type)
            try:
                chunks: list[bytes] = []
                received = 0
                limit = self._settings.maximum_response_bytes + 1
                while received < limit:
                    if connection.sock is not None:
                        connection.sock.settimeout(remaining_timeout(read_bound=True))
                    else:
                        remaining_timeout(read_bound=True)
                    chunk = response.read1(min(8_192, limit - received))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    received += len(chunk)
                response_body = b"".join(chunks)
            except (OSError, http.client.HTTPException) as exc:
                raise _network_failure(exc, after_submit=True) from None
            if len(response_body) > self._settings.maximum_response_bytes:
                raise AdapterFailure(
                    AdapterFailureCategory.OVERSIZED_RESPONSE,
                    result_class="response_refused",
                    after_submit=True,
                )
            return HttpJsonResponse(
                status=status,
                content_type=content_type,
                body=response_body,
            )
        finally:
            connection.close()
