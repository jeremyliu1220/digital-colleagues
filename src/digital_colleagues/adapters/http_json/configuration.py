# SPDX-License-Identifier: Apache-2.0

"""Fail-closed startup configuration for optional HTTP JSON adapters."""

from __future__ import annotations

import ipaddress
import math
import stat
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from urllib.parse import SplitResult, urlsplit

from digital_colleagues.adapters.http_json.errors import (
    PROTOCOL_VERSION,
    AdapterFailure,
    AdapterFailureCategory,
)

MAX_CREDENTIAL_BYTES = 4_096
_MODEL_KEYS = {
    "DC_MODEL_ADAPTER",
    "DC_MODEL_CREDENTIAL_FILE",
    "DC_MODEL_ENDPOINT",
    "DC_MODEL_PROTOCOL",
}
_CHANNEL_KEYS = {
    "DC_CHANNEL_ADAPTER",
    "DC_CHANNEL_CREDENTIAL_FILE",
    "DC_CHANNEL_ENDPOINT",
    "DC_CHANNEL_PROTOCOL",
}
_COMMON_KEYS = {
    "DC_P7_ALLOW_LOOPBACK_HTTP",
    "DC_P7_CONNECT_TIMEOUT_SECONDS",
    "DC_P7_MAX_PRE_SUBMIT_RETRIES",
    "DC_P7_MAX_REQUEST_BYTES",
    "DC_P7_MAX_RESPONSE_BYTES",
    "DC_P7_READ_TIMEOUT_SECONDS",
    "DC_P7_TOTAL_TIMEOUT_SECONDS",
}


class AdapterMode(StrEnum):
    DETERMINISTIC = "deterministic"
    REFERENCE = "reference"
    HTTP_JSON_V1 = "http_json_v1"


def _configuration_failure() -> AdapterFailure:
    return AdapterFailure(
        AdapterFailureCategory.INVALID_CONFIGURATION,
        result_class="startup_refused",
    )


def _positive_number(value: str | None, *, upper: float) -> float:
    if value is None:
        raise _configuration_failure()
    try:
        parsed = float(value)
    except ValueError:
        raise _configuration_failure() from None
    if not math.isfinite(parsed) or parsed <= 0 or parsed > upper:
        raise _configuration_failure()
    return parsed


def _positive_integer(value: str | None, *, upper: int, allow_zero: bool = False) -> int:
    if value is None:
        raise _configuration_failure()
    try:
        parsed = int(value)
    except ValueError:
        raise _configuration_failure() from None
    minimum = 0 if allow_zero else 1
    if str(parsed) != value or not minimum <= parsed <= upper:
        raise _configuration_failure()
    return parsed


def _validate_endpoint(value: str, *, allow_loopback_http: bool) -> SplitResult:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise _configuration_failure() from None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or (port is not None and not 1 <= port <= 65_535)
        or not parsed.path.startswith("/")
        or parsed.path.startswith("//")
    ):
        raise _configuration_failure()
    if parsed.scheme == "http":
        try:
            host = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            raise _configuration_failure() from None
        if not allow_loopback_http or not host.is_loopback:
            raise _configuration_failure()
    return parsed


@dataclass(frozen=True, slots=True)
class HttpJsonSettings:
    endpoint: str = field(repr=False)
    credential_file: Path = field(repr=False)
    protocol_version: str
    connect_timeout_seconds: float
    read_timeout_seconds: float
    total_timeout_seconds: float
    maximum_request_bytes: int
    maximum_response_bytes: int
    maximum_pre_submit_retries: int
    allow_loopback_http: bool = False
    parsed_endpoint: SplitResult = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.protocol_version != PROTOCOL_VERSION:
            raise _configuration_failure()
        if (
            type(self.connect_timeout_seconds) not in {float, int}
            or type(self.read_timeout_seconds) not in {float, int}
            or type(self.total_timeout_seconds) not in {float, int}
            or not 0 < self.connect_timeout_seconds <= 30
            or not 0 < self.read_timeout_seconds <= 60
            or not 0 < self.total_timeout_seconds <= 120
            or self.total_timeout_seconds < self.connect_timeout_seconds
            or type(self.maximum_request_bytes) is not int
            or not 256 <= self.maximum_request_bytes <= 1_048_576
            or type(self.maximum_response_bytes) is not int
            or not 256 <= self.maximum_response_bytes <= 1_048_576
            or type(self.maximum_pre_submit_retries) is not int
            or not 0 <= self.maximum_pre_submit_retries <= 1
            or type(self.allow_loopback_http) is not bool
        ):
            raise _configuration_failure()
        parsed = _validate_endpoint(
            self.endpoint,
            allow_loopback_http=self.allow_loopback_http,
        )
        object.__setattr__(self, "parsed_endpoint", parsed)
        try:
            status = self.credential_file.lstat()
        except OSError:
            raise _configuration_failure() from None
        if (
            not stat.S_ISREG(status.st_mode)
            or stat.S_ISLNK(status.st_mode)
            or status.st_size < 1
            or status.st_size > MAX_CREDENTIAL_BYTES
            or status.st_mode & 0o222
        ):
            raise _configuration_failure()

    def read_credential(self) -> bytes:
        try:
            status = self.credential_file.lstat()
            value = self.credential_file.read_bytes()
        except OSError:
            raise _configuration_failure() from None
        if (
            not stat.S_ISREG(status.st_mode)
            or stat.S_ISLNK(status.st_mode)
            or status.st_mode & 0o222
            or not value
            or len(value) > MAX_CREDENTIAL_BYTES
            or b"\x00" in value
        ):
            raise _configuration_failure()
        return value


@dataclass(frozen=True, slots=True)
class AdapterSelection:
    model_mode: AdapterMode
    channel_mode: AdapterMode
    model: HttpJsonSettings | None = field(default=None, repr=False)
    channel: HttpJsonSettings | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.model_mode not in {AdapterMode.DETERMINISTIC, AdapterMode.HTTP_JSON_V1}:
            raise _configuration_failure()
        if self.channel_mode not in {AdapterMode.REFERENCE, AdapterMode.HTTP_JSON_V1}:
            raise _configuration_failure()
        if (self.model_mode is AdapterMode.HTTP_JSON_V1) != (self.model is not None):
            raise _configuration_failure()
        if (self.channel_mode is AdapterMode.HTTP_JSON_V1) != (self.channel is not None):
            raise _configuration_failure()


def _mode(value: str | None, *, default: AdapterMode, allowed: set[AdapterMode]) -> AdapterMode:
    try:
        mode = AdapterMode(value if value is not None else default.value)
    except ValueError:
        raise _configuration_failure() from None
    if mode not in allowed:
        raise _configuration_failure()
    return mode


def _settings(environment: Mapping[str, str], prefix: str) -> HttpJsonSettings:
    loopback_value = environment.get("DC_P7_ALLOW_LOOPBACK_HTTP")
    if loopback_value not in {None, "0", "1"}:
        raise _configuration_failure()
    allow_loopback = loopback_value == "1"
    endpoint = environment.get(f"DC_{prefix}_ENDPOINT")
    credential = environment.get(f"DC_{prefix}_CREDENTIAL_FILE")
    protocol = environment.get(f"DC_{prefix}_PROTOCOL")
    if endpoint is None or credential is None or protocol is None:
        raise _configuration_failure()
    return HttpJsonSettings(
        endpoint=endpoint,
        credential_file=Path(credential),
        protocol_version=protocol,
        connect_timeout_seconds=_positive_number(
            environment.get("DC_P7_CONNECT_TIMEOUT_SECONDS"), upper=30
        ),
        read_timeout_seconds=_positive_number(
            environment.get("DC_P7_READ_TIMEOUT_SECONDS"), upper=60
        ),
        total_timeout_seconds=_positive_number(
            environment.get("DC_P7_TOTAL_TIMEOUT_SECONDS"), upper=120
        ),
        maximum_request_bytes=_positive_integer(
            environment.get("DC_P7_MAX_REQUEST_BYTES"), upper=1_048_576
        ),
        maximum_response_bytes=_positive_integer(
            environment.get("DC_P7_MAX_RESPONSE_BYTES"), upper=1_048_576
        ),
        maximum_pre_submit_retries=_positive_integer(
            environment.get("DC_P7_MAX_PRE_SUBMIT_RETRIES"), upper=1, allow_zero=True
        ),
        allow_loopback_http=allow_loopback,
    )


def load_adapter_selection(environment: Mapping[str, str]) -> AdapterSelection:
    relevant_keys = {
        key
        for key in environment
        if key.startswith("DC_MODEL_") or key.startswith("DC_CHANNEL_") or key.startswith("DC_P7_")
    }
    if relevant_keys - _MODEL_KEYS - _CHANNEL_KEYS - _COMMON_KEYS:
        raise _configuration_failure()
    model_mode = _mode(
        environment.get("DC_MODEL_ADAPTER"),
        default=AdapterMode.DETERMINISTIC,
        allowed={AdapterMode.DETERMINISTIC, AdapterMode.HTTP_JSON_V1},
    )
    channel_mode = _mode(
        environment.get("DC_CHANNEL_ADAPTER"),
        default=AdapterMode.REFERENCE,
        allowed={AdapterMode.REFERENCE, AdapterMode.HTTP_JSON_V1},
    )
    model_settings = relevant_keys & (_MODEL_KEYS - {"DC_MODEL_ADAPTER"})
    channel_settings = relevant_keys & (_CHANNEL_KEYS - {"DC_CHANNEL_ADAPTER"})
    common_settings = relevant_keys & _COMMON_KEYS
    if (
        (model_mode is not AdapterMode.HTTP_JSON_V1 and model_settings)
        or (channel_mode is not AdapterMode.HTTP_JSON_V1 and channel_settings)
        or (
            model_mode is not AdapterMode.HTTP_JSON_V1
            and channel_mode is not AdapterMode.HTTP_JSON_V1
            and common_settings
        )
    ):
        raise _configuration_failure()
    return AdapterSelection(
        model_mode=model_mode,
        channel_mode=channel_mode,
        model=_settings(environment, "MODEL") if model_mode is AdapterMode.HTTP_JSON_V1 else None,
        channel=_settings(environment, "CHANNEL")
        if channel_mode is AdapterMode.HTTP_JSON_V1
        else None,
    )
