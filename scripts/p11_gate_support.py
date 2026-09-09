# SPDX-License-Identifier: Apache-2.0

"""Shared immutable identities and fail-closed helpers for P11 gates."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

BASE_COMMIT = "4bef5629d450c6bb3940f606fc90194e008ee8fd"
ACCEPTANCE_COMMIT = "b3963aadf4702b924e72dc1e7306799780eecfbd"
PRIOR_EVIDENCE_COMMIT = "54c411e594659bf83fec56f538a11d1ea3b6e523"
PRIOR_SUMMARY_BLOB = "da0d602d323689cd1f40393e475dfedc5147eaa5"
BRANCH = "codex/p11-agent-packages"
SUMMARY_PATH = "artifacts/p11/summary.json"
CLAIM = "p11_agent_package_multi_agent_lifecycle_candidate"
STATUS = "development_complete_awaiting_independent_acceptance"
P10_RUNTIME_DIGEST = "sha256:a5bb41bdb85bf7b5a75dc79967e26943c098b024b64fdd345f5b4c6f4688991d"
P10_STUDIO_DIGEST = "sha256:7791d80d9fa464bbd1574601deba5a30ca6d980dab8c8275c24c117fae81e4c9"
EVIDENCE_CLASSES = ("static", "synthetic_offline", "local_runtime", "not_evaluated")


class GateError(RuntimeError):
    """A P11 contract boundary failed closed."""


def git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise GateError("git identity check failed")
    return completed.stdout.strip()


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GateError("required JSON is unavailable or invalid") from exc


def acceptance_paths(root: Path) -> tuple[str, ...]:
    text = (root / "docs/p11/acceptance.md").read_text(encoding="utf-8")
    marker = "## Exact changed-file allowlist"
    try:
        section = text.split(marker, 1)[1]
        block = section.split("```text", 1)[1].split("```", 1)[0]
    except IndexError as exc:
        raise GateError("P11 path allowlist is unavailable") from exc
    paths = tuple(line.strip() for line in block.splitlines() if line.strip())
    if len(paths) != 59 or len(paths) != len(set(paths)) or tuple(sorted(paths)) != paths:
        raise GateError("P11 path allowlist identity is invalid")
    return paths


def public_tree_digest(root: Path, paths: tuple[str, ...]) -> str:
    framed = hashlib.sha256()
    for relative in paths:
        if relative == SUMMARY_PATH:
            continue
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise GateError("P11 implementation path is absent or not a regular file")
        encoded = relative.encode()
        content = path.read_bytes()
        framed.update(len(encoded).to_bytes(8, "big"))
        framed.update(encoded)
        framed.update(len(content).to_bytes(8, "big"))
        framed.update(content)
    return "sha256:" + framed.hexdigest()


def candidate_diff_check(
    root: Path,
    *,
    base: str = ACCEPTANCE_COMMIT,
    head: str = "HEAD",
) -> dict[str, object]:
    revision_range = f"{base}...{head}"
    completed = subprocess.run(
        ["git", "diff", "--check", revision_range],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise GateError("candidate implementation/evidence diff check failed")
    return {
        "status": "passed",
        "failure_count": 0,
        "range": revision_range,
    }
