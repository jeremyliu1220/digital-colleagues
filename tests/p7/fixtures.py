# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import os
import socket
import threading
import time
from collections import deque
from dataclasses import dataclass, field, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from digital_colleagues.adapters.http_json.configuration import HttpJsonSettings
from digital_colleagues.adapters.http_json.errors import PROTOCOL_VERSION
from digital_colleagues.application.contracts import ChannelEffect, IntelligenceRequest
from digital_colleagues.core.effects import EffectAttemptState
from tests.core.fixtures import (
    EXPIRY,
    T3,
    agenda_item,
    effect_attempt,
    effect_proposal,
    mandate,
    model_principal,
    wake_cycle,
)

SYNTHETIC_CREDENTIAL = b"synthetic-loopback-credential"


@dataclass(frozen=True, slots=True)
class StubBehavior:
    status: int = 200
    document: dict[str, object] | None = None
    raw_body: bytes | None = None
    content_type: str = "application/json"
    delay_seconds: float = 0
    disconnect_after_read: bool = False


@dataclass(slots=True)
class StubState:
    behaviors: deque[StubBehavior] = field(default_factory=deque)
    requests: list[dict[str, Any]] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)


class QuietServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request: object, client_address: object) -> None:
        del request, client_address


class LoopbackStub:
    def __init__(self) -> None:
        state = StubState()

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                try:
                    parsed = json.loads(body)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    parsed = None
                with state.lock:
                    state.requests.append(
                        {
                            "body": body,
                            "document": parsed,
                            "idempotency_key": self.headers.get("Idempotency-Key"),
                            "protocol": self.headers.get("X-DC-Protocol"),
                            "authorization_present": bool(self.headers.get("Authorization")),
                            "path": self.path,
                        }
                    )
                    behavior = state.behaviors.popleft() if state.behaviors else StubBehavior()
                if behavior.disconnect_after_read:
                    try:
                        self.connection.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    self.connection.close()
                    return
                if behavior.delay_seconds:
                    time.sleep(behavior.delay_seconds)
                response = behavior.raw_body
                if response is None:
                    response = json.dumps(
                        behavior.document or {}, separators=(",", ":"), sort_keys=True
                    ).encode("utf-8")
                self.send_response(behavior.status)
                self.send_header("Content-Type", behavior.content_type)
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                try:
                    self.wfile.write(response)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, format: str, *args: object) -> None:
                del format, args

        self.state = state
        self.server = QuietServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.01),
            daemon=True,
        )

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}/v1/adapter"

    def __enter__(self) -> LoopbackStub:
        self.thread.start()
        return self

    def __exit__(self, *values: object) -> None:
        del values
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def enqueue(self, *behaviors: StubBehavior) -> None:
        with self.state.lock:
            self.state.behaviors.extend(behaviors)


def credential_file(directory: Path) -> Path:
    path = directory / "credential"
    path.write_bytes(SYNTHETIC_CREDENTIAL)
    path.chmod(0o400)
    return path


def settings(
    endpoint: str,
    credential: Path,
    *,
    connect_timeout: float = 1,
    read_timeout: float = 1,
    total_timeout: float = 2,
    maximum_request_bytes: int = 16_384,
    maximum_response_bytes: int = 16_384,
    retries: int = 0,
) -> HttpJsonSettings:
    return HttpJsonSettings(
        endpoint=endpoint,
        credential_file=credential,
        protocol_version=PROTOCOL_VERSION,
        connect_timeout_seconds=connect_timeout,
        read_timeout_seconds=read_timeout,
        total_timeout_seconds=total_timeout,
        maximum_request_bytes=maximum_request_bytes,
        maximum_response_bytes=maximum_response_bytes,
        maximum_pre_submit_retries=retries,
        allow_loopback_http=True,
    )


def intelligence_request() -> IntelligenceRequest:
    return IntelligenceRequest(
        namespace=agenda_item().namespace,
        request_id="request-p7",
        wake_cycle=wake_cycle(),
        agenda_item=agenda_item(),
        mandate=mandate(),
        model_principal=model_principal(),
        decision_id="decision-p7",
        proposal_id="proposal-p7",
        effect_idempotency_key="effect-p7",
        occurred_at=T3,
        proposal_valid_until=EXPIRY,
    )


def model_response(
    *,
    result_kind: str = "proposal",
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    if result_kind == "proposal":
        result: dict[str, object] = {
            "action": "deliver",
            "destination": {"kind": "reference-channel", "target": "synthetic-target"},
            "effect_kind": "reference_message",
            "payload": {"body": "synthetic optional adapter result"},
            "rationale": "Synthetic loopback response requests an exact effect.",
            "safe_projection": {"content_class": "synthetic_update"},
        }
    else:
        result = {"rationale": f"Synthetic {result_kind} response."}
    if extra:
        result.update(extra)
    return {
        "protocol_version": PROTOCOL_VERSION,
        "result": result,
        "result_kind": result_kind,
    }


def channel_response(
    result_kind: str,
    *,
    classification: str | None = None,
) -> dict[str, object]:
    classifications = {
        "succeeded": "applied",
        "known_not_executed": "not_executed",
        "retryable_failure": "retryable",
        "permanent_failure": "permanent",
        "ambiguous": "unknown",
        "confirmed_applied": "applied",
        "confirmed_absent": "absent",
        "still_unknown": "unknown",
    }
    return {
        "protocol_version": PROTOCOL_VERSION,
        "result": {"classification": classification or classifications[result_kind]},
        "result_kind": result_kind,
    }


def channel_effect() -> ChannelEffect:
    proposal = replace(
        effect_proposal(),
        mandate_id="mandate-alpha",
        mandate_revision=1,
    )
    attempt = replace(effect_attempt(), state=EffectAttemptState.STARTED)
    return ChannelEffect(proposal, attempt, proposal.constraints.idempotency_key)


def unused_loopback_endpoint() -> str:
    candidate = socket.socket()
    candidate.bind(("127.0.0.1", 0))
    port = candidate.getsockname()[1]
    candidate.close()
    return f"http://127.0.0.1:{port}/v1/adapter"


def environment(endpoint: str, credential: Path) -> dict[str, str]:
    return {
        "DC_CHANNEL_ADAPTER": "http_json_v1",
        "DC_CHANNEL_CREDENTIAL_FILE": os.fspath(credential),
        "DC_CHANNEL_ENDPOINT": endpoint,
        "DC_CHANNEL_PROTOCOL": PROTOCOL_VERSION,
        "DC_MODEL_ADAPTER": "http_json_v1",
        "DC_MODEL_CREDENTIAL_FILE": os.fspath(credential),
        "DC_MODEL_ENDPOINT": endpoint,
        "DC_MODEL_PROTOCOL": PROTOCOL_VERSION,
        "DC_P7_ALLOW_LOOPBACK_HTTP": "1",
        "DC_P7_CONNECT_TIMEOUT_SECONDS": "1",
        "DC_P7_MAX_PRE_SUBMIT_RETRIES": "0",
        "DC_P7_MAX_REQUEST_BYTES": "16384",
        "DC_P7_MAX_RESPONSE_BYTES": "16384",
        "DC_P7_READ_TIMEOUT_SECONDS": "1",
        "DC_P7_TOTAL_TIMEOUT_SECONDS": "2",
    }
