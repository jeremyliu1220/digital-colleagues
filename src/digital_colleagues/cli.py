# SPDX-License-Identifier: Apache-2.0

"""Bounded JSON CLI for local package checks and authenticated P11 operations."""

from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import NoReturn

from digital_colleagues.adapters.package.archive import ARCHIVE_MAX_BYTES
from digital_colleagues.application.p11_services import P11PackageService

STDIN_AUTH_MAX_BYTES = 8_192
HTTP_RESPONSE_MAX_BYTES = 1_048_576


def _fail(code: str) -> NoReturn:
    print(json.dumps({"error": {"code": code, "message": "request refused"}}, sort_keys=True))
    raise SystemExit(1)


def _archive(path: str) -> bytes:
    try:
        source = Path(path)
        if not source.is_file() or source.stat().st_size > ARCHIVE_MAX_BYTES:
            _fail("invalid_archive")
        value = source.read_bytes()
    except OSError:
        _fail("invalid_archive")
    if not value or len(value) > ARCHIVE_MAX_BYTES:
        _fail("invalid_archive")
    return value


def _auth() -> tuple[str, str]:
    value = sys.stdin.buffer.read(STDIN_AUTH_MAX_BYTES + 1)
    if not value or len(value) > STDIN_AUTH_MAX_BYTES:
        _fail("authentication_envelope_invalid")
    try:
        raw = json.loads(value.decode("utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError):
        _fail("authentication_envelope_invalid")
    if not isinstance(raw, dict) or set(raw) != {"session_cookie", "csrf_token"}:
        _fail("authentication_envelope_invalid")
    cookie = raw["session_cookie"]
    csrf = raw["csrf_token"]
    if not isinstance(cookie, str) or not 1 <= len(cookie) <= 512:
        _fail("authentication_envelope_invalid")
    if not isinstance(csrf, str) or not 1 <= len(csrf) <= 512:
        _fail("authentication_envelope_invalid")
    return cookie, csrf


def _request(
    *,
    base_url: str,
    origin: str,
    path: str,
    method: str,
    body: dict[str, object] | None,
) -> object:
    cookie, csrf = _auth()
    if (
        not base_url.startswith(("http://", "https://"))
        or not origin.startswith(("http://", "https://"))
        or len(base_url) > 512
        or len(origin) > 512
    ):
        _fail("invalid_server")
    encoded = None if body is None else json.dumps(body, separators=(",", ":")).encode()
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=encoded,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": f"dc_session={cookie}",
            "Origin": origin.rstrip("/"),
            "X-CSRF-Token": csrf,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read(HTTP_RESPONSE_MAX_BYTES + 1)
    except (OSError, urllib.error.HTTPError, urllib.error.URLError):
        _fail("remote_request_refused")
    if len(payload) > HTTP_RESPONSE_MAX_BYTES:
        _fail("remote_response_too_large")
    try:
        return json.loads(payload)
    except (UnicodeError, json.JSONDecodeError):
        _fail("remote_response_invalid")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dc", description="Digital Colleagues P11 CLI")
    subcommands = parser.add_subparsers(dest="command", required=True)
    local = subcommands.add_parser("package-check")
    local.add_argument("action", choices=("inspect", "validate"))
    local.add_argument("--archive", required=True)
    local.add_argument("--expected-digest")

    remote = subcommands.add_parser("api")
    remote.add_argument("--url", required=True)
    remote.add_argument("--origin")
    remote.add_argument(
        "action",
        choices=(
            "catalog",
            "packages",
            "register",
            "trust",
            "revoke",
            "install",
            "drafts",
            "create-draft",
            "review",
            "confirm",
            "deployments",
            "lifecycle",
            "upgrade",
            "rollback",
            "select",
            "audit",
        ),
    )
    remote.add_argument("--json", default="{}")
    remote.add_argument("--archive")
    remote.add_argument("--package-id")
    remote.add_argument("--version")
    remote.add_argument("--digest")
    remote.add_argument("--deployment-id")
    remote.add_argument("--draft-id")
    return parser


def _remote(arguments: argparse.Namespace) -> object:
    try:
        body = json.loads(arguments.json)
    except json.JSONDecodeError:
        _fail("invalid_json")
    if not isinstance(body, dict):
        _fail("invalid_json")
    action = arguments.action
    method = (
        "GET" if action in {"catalog", "packages", "drafts", "deployments", "audit"} else "POST"
    )
    paths = {
        "catalog": "/api/v1/catalog",
        "packages": "/api/v1/agent-packages",
        "register": "/api/v1/agent-packages",
        "drafts": "/api/v1/deployment-drafts",
        "create-draft": "/api/v1/deployment-drafts",
        "deployments": "/api/v1/deployments",
    }
    if action in {"trust", "revoke", "install"}:
        if not all((arguments.package_id, arguments.version, arguments.digest)):
            _fail("missing_exact_package_binding")
        path = (
            f"/api/v1/agent-packages/{arguments.package_id}/versions/"
            f"{arguments.version}/{arguments.digest}/{action}"
        )
    elif action in {"review", "confirm"}:
        if not arguments.draft_id:
            _fail("missing_draft_id")
        path = f"/api/v1/deployment-drafts/{arguments.draft_id}/{action}"
    elif action in {"lifecycle", "upgrade", "rollback", "select", "audit"}:
        if not arguments.deployment_id:
            _fail("missing_deployment_id")
        suffix = {
            "lifecycle": "lifecycle",
            "upgrade": "upgrade-drafts",
            "rollback": "rollback-drafts",
            "select": "select",
            "audit": "audit",
        }[action]
        path = f"/api/v1/deployments/{arguments.deployment_id}/{suffix}"
    else:
        path = paths[action]
    if action == "register":
        if not arguments.archive:
            _fail("invalid_archive")
        body["archive_base64"] = base64.b64encode(_archive(arguments.archive)).decode("ascii")
    return _request(
        base_url=arguments.url,
        origin=arguments.origin or arguments.url,
        path=path,
        method=method,
        body=None if method == "GET" else body,
    )


def main() -> int:
    arguments = _parser().parse_args()
    try:
        if arguments.command == "package-check":
            inspection = P11PackageService.inspect(
                _archive(arguments.archive),
                expected_archive_digest=arguments.expected_digest,
            )
            result: object = {
                "archive_digest": inspection.archive_digest,
                "package_digest": inspection.package_digest,
                "package_id": inspection.package.package_id,
                "version": inspection.package.version,
                "valid": True,
            }
        else:
            result = _remote(arguments)
    except SystemExit:
        raise
    except Exception:
        _fail("operation_refused")
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
