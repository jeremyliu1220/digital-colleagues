# SPDX-License-Identifier: Apache-2.0

"""Controlled two-port HTTP stub for the isolated P7 Compose runtime gate."""

from __future__ import annotations

import json
import threading
from collections import Counter, deque
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

PROTOCOL = "dc-http-json-v1"


def _response(result_kind: str, classification: str) -> bytes:
    return json.dumps(
        {
            "protocol_version": PROTOCOL,
            "result_kind": result_kind,
            "result": {"classification": classification},
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


@dataclass(slots=True)
class State:
    behaviors: deque[str] = field(default_factory=deque)
    requests: list[dict[str, str | None]] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)


STATE = State()


class QuietServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request: object, client_address: object) -> None:
        del request, client_address


class ProviderHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            document: Any = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            document = None
        request_kind = document.get("request_kind") if isinstance(document, dict) else None
        with STATE.lock:
            behavior = STATE.behaviors.popleft() if STATE.behaviors else "unexpected"
            STATE.requests.append(
                {
                    "behavior": behavior,
                    "binding_digest": (
                        document.get("effect_binding_digest")
                        if isinstance(document, dict)
                        else None
                    ),
                    "effect_key": self.headers.get("Idempotency-Key"),
                    "request_kind": request_kind,
                }
            )
        status = 200
        if behavior == "model_proposal" and request_kind == "semantic_decision":
            body = json.dumps(
                {
                    "protocol_version": PROTOCOL,
                    "result_kind": "proposal",
                    "result": {
                        "action": "record_message",
                        "destination": {
                            "kind": "reference_channel",
                            "target": "synthetic-compose-target",
                        },
                        "effect_kind": "reference_message",
                        "payload": {"body": "synthetic P7 Compose effect"},
                        "rationale": "Synthetic P7 Compose proposal.",
                        "safe_projection": {"content_class": "synthetic_update"},
                    },
                },
                separators=(",", ":"),
                sort_keys=True,
            ).encode()
        elif behavior == "channel_503" and request_kind == "channel_effect":
            status = 503
            body = b"p7-private-provider-marker"
        elif behavior == "still_unknown" and request_kind == "channel_reconciliation":
            body = _response("still_unknown", "unknown")
        elif behavior == "confirmed_absent" and request_kind == "channel_reconciliation":
            body = _response("confirmed_absent", "absent")
        elif behavior == "succeeded" and request_kind == "channel_effect":
            body = _response("succeeded", "applied")
        else:
            status = 409
            body = b"controlled stub sequence refused"
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format: str, *args: object) -> None:
        del format, args


class ControlHandler(BaseHTTPRequestHandler):
    def _json(self, status: int, value: object) -> None:
        body = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json(200, {"status": "ready"})
            return
        if self.path != "/state":
            self._json(404, {"status": "refused"})
            return
        with STATE.lock:
            requests = [dict(item) for item in STATE.requests]
            pending = list(STATE.behaviors)
        counts = Counter(str(item["request_kind"]) for item in requests)
        self._json(
            200,
            {
                "counts": dict(sorted(counts.items())),
                "pending_behaviors": pending,
                "requests": requests,
            },
        )

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/enqueue":
            self._json(404, {"status": "refused"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            value: Any = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"status": "refused"})
            return
        allowed = {
            "channel_503",
            "confirmed_absent",
            "model_proposal",
            "still_unknown",
            "succeeded",
        }
        behaviors = value.get("behaviors") if isinstance(value, dict) else None
        if (
            not isinstance(behaviors, list)
            or not behaviors
            or any(not isinstance(item, str) or item not in allowed for item in behaviors)
        ):
            self._json(400, {"status": "refused"})
            return
        with STATE.lock:
            STATE.behaviors.extend(behaviors)
        self._json(200, {"enqueued": len(behaviors)})

    def log_message(self, format: str, *args: object) -> None:
        del format, args


def main() -> int:
    provider = QuietServer(("127.0.0.1", 8090), ProviderHandler)
    control = QuietServer(("0.0.0.0", 8091), ControlHandler)
    provider_thread = threading.Thread(target=provider.serve_forever, daemon=True)
    provider_thread.start()
    try:
        control.serve_forever()
    finally:
        control.server_close()
        provider.shutdown()
        provider.server_close()
        provider_thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
