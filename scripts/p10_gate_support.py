# SPDX-License-Identifier: Apache-2.0

"""Shared fixed identities and fail-closed helpers for P10 gates."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, cast

BASE_COMMIT = "11aa240af8db2ca515325dc059b1a77f7badc874"
ACCEPTED_P8_COMMIT = "0bb80ab187932fbad42fbf665b8310987609a1f5"
ACCEPTANCE_COMMIT = "99b0045bba48de8e4d44c10ce07d60ba20738a8b"
BRANCH = "codex/p10-mac-quickstart"
ACCEPTANCE_PATH = "docs/p10/acceptance.md"
SUMMARY_PATH = "artifacts/p10/summary.json"
PRODUCT_NAME = "Digital Colleagues"
PYTHON_VERSION = "0.2.0.dev0"
DISPLAY_VERSION = "0.2.0-dev.0"
MATURITY = "Public Pilot development candidate"
API_TITLE = "Digital Colleagues Local API"
PLATFORMS = ("linux/amd64", "linux/arm64")
MIGRATIONS = (
    "001_initial.sql",
    "002_runtime_indexes.sql",
    "003_timer_triggers.sql",
    "004_local_authentication.sql",
    "005_evaluation_observations.sql",
    "006_revisioned_colleague_builder.sql",
    "007_governance_hardening.sql",
    "manifest.json",
)
REMOTE_STATES = {
    "ghcr_publication": "not_evaluated",
    "registry_image_signature": "not_evaluated",
    "registry_attestation": "not_evaluated",
    "remote_distribution_gate": "authorization_required",
}
OFFICIAL_URLS = (
    "https://docs.docker.com/build/building/multi-platform/",
    "https://docs.github.com/en/actions/concepts/security/artifact-attestations",
    "https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations",
    "https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry",
    "https://docs.sigstore.dev/cosign/signing/signing_with_containers/",
    "https://developer.apple.com/documentation/foundation/url/applicationsupportdirectory",
    "https://support.apple.com/en-gb/guide/deployment/dep0a2cb7686/web",
)

P10_ALLOWED_PATHS = frozenset(
    {
        ".github/workflows/ci.yml",
        "Dockerfile.p10",
        "Dockerfile.p10.dockerignore",
        "Makefile",
        "README.md",
        "SECURITY.md",
        "SUPPORT.md",
        "compose.p10.yaml",
        "dc",
        "distribution/p10/release-manifest.template.json",
        "distribution/p10/verification-policy.json",
        "docs/adr/0009-mac-quickstart-and-distribution.md",
        "docs/architecture/target-architecture.md",
        "docs/development.md",
        ACCEPTANCE_PATH,
        "docs/p10/compatibility.md",
        "docs/p10/distribution.md",
        "docs/p10/operations.md",
        "docs/roadmap.md",
        "docs/security/privacy-boundary.md",
        "docs/security/threat-model.md",
        "provenance/p10-migration-receipt.json",
        "pyproject.toml",
        "scripts/build_p10_candidate.py",
        "scripts/check_p10_compatibility.py",
        "scripts/check_p10_compose_runtime.py",
        "scripts/check_p10_distribution.py",
        "scripts/check_p10_evidence.py",
        "scripts/check_p10_i18n.py",
        "scripts/check_p10_operations.py",
        "scripts/check_p10_provenance.py",
        "scripts/check_p10_quickstart.py",
        "scripts/check_p10_repository.py",
        "scripts/check_p10_reproducibility.py",
        "scripts/check_p10_security.py",
        "scripts/collect_p10_evidence.py",
        "scripts/p10_gate_support.py",
        "scripts/run_p10_toolchain.py",
        "src/digital_colleagues/__init__.py",
        "src/digital_colleagues/api/app.py",
        "src/digital_colleagues/api/p4_app.py",
        "src/digital_colleagues/local/runtime.py",
        "studio/Dockerfile.p10",
        "studio/package-lock.json",
        "studio/package.json",
        "studio/src/App.test.tsx",
        "studio/src/App.tsx",
        "studio/src/i18n.ts",
        "studio/src/locales/en-US.ts",
        "studio/src/locales/zh-TW.ts",
        "studio/src/studioContract.ts",
        "tests/p10/__init__.py",
        "tests/p10/fixtures.py",
        "tests/p10/test_compatibility.py",
        "tests/p10/test_distribution.py",
        "tests/p10/test_evidence_gate.py",
        "tests/p10/test_i18n.py",
        "tests/p10/test_operations.py",
        "tests/p10/test_repository.py",
        "tests/p10/test_reproducibility.py",
        "tests/p10/test_security.py",
        SUMMARY_PATH,
    }
)
IMPLEMENTATION_PATHS = P10_ALLOWED_PATHS - {SUMMARY_PATH}
DIGEST_REF = re.compile(r"^[A-Za-z0-9._:-]+/[A-Za-z0-9._/-]+@sha256:[0-9a-f]{64}$")
UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


class GateError(RuntimeError):
    """A P10 contract invariant failed."""


def git(root: Path, *arguments: str, binary: bool = False) -> str | bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=not binary,
        check=False,
    )
    if completed.returncode != 0:
        raise GateError("git_inspection_failed")
    return cast(str | bytes, completed.stdout)


def safe_relative(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise GateError("unsafe_path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise GateError("unsafe_path")
    return value


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GateError("invalid_json") from exc
    if not isinstance(value, dict):
        raise GateError("invalid_json_shape")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while block := handle.read(1024 * 1024):
                digest.update(block)
    except OSError as exc:
        raise GateError("file_digest_failed") from exc
    return "sha256:" + digest.hexdigest()


def tree_digest(root: Path, paths: set[str] | frozenset[str]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(paths):
        content = git(root, "show", f"HEAD:{relative}", binary=True)
        assert isinstance(content, bytes)
        for item in (relative.encode(), hashlib.sha256(content).digest()):
            digest.update(len(item).to_bytes(8, "big"))
            digest.update(item)
    return "sha256:" + digest.hexdigest()


def valid_digest_ref(value: object) -> bool:
    return (
        isinstance(value, str)
        and DIGEST_REF.fullmatch(value) is not None
        and ":latest@" not in value
    )


def redact(message: object, root: Path) -> str:
    text = str(message)
    for value in (str(root.resolve()), str(Path.home()), "/.codex/attachments/"):
        if value:
            text = text.replace(value, "<redacted>")
    return text


def emit_main(checker: Any, argv: list[str] | None, description: str) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    root = Path(arguments.root).resolve()
    try:
        result = checker(root)
    except (GateError, OSError, ValueError) as exc:
        print(
            json.dumps({"status": "failed", "category": redact(exc, root)}, sort_keys=True),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
