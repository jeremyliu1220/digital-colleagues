# SPDX-License-Identifier: Apache-2.0

"""Build a local-only P10 OCI candidate or a verified quickstart bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PRODUCT_NAME = "Digital Colleagues"
PYTHON_VERSION = "0.2.0.dev0"
DISPLAY_VERSION = "0.2.0-dev.0"
MATURITY = "Public Pilot development candidate"
PROJECT_ID = "digital-colleagues-p10"
PLATFORMS = ("linux/amd64", "linux/arm64")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_REF_RE = re.compile(r"^[A-Za-z0-9._:-]+/[A-Za-z0-9._/-]+@sha256:[0-9a-f]{64}$")


class CandidateError(RuntimeError):
    """A local candidate could not be built without weakening the contract."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _run(command: list[str], *, cwd: Path) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1800,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CandidateError("candidate_command_failed") from exc
    return result.stdout.strip()


def _source_timestamp(root: Path, revision: str) -> str:
    value = _run(["git", "show", "-s", "--format=%cI", revision], cwd=root)
    try:
        parsed = datetime.fromisoformat(value).astimezone(UTC)
    except ValueError as exc:
        raise CandidateError("source_timestamp_invalid") from exc
    return parsed.isoformat().replace("+00:00", "Z")


def _require_output(output: Path) -> None:
    if output.exists():
        if output.is_symlink() or not output.is_dir() or any(output.iterdir()):
            raise CandidateError("output_not_new_or_empty")
    else:
        output.mkdir(mode=0o700, parents=True)
    output.chmod(0o700)


def _require_revision(root: Path, revision: str) -> None:
    if not COMMIT_RE.fullmatch(revision):
        raise CandidateError("source_revision_invalid")
    if _run(["git", "rev-parse", revision], cwd=root) != revision:
        raise CandidateError("source_revision_unavailable")


def build_oci(root: Path, output: Path, revision: str) -> dict[str, str]:
    """Create two local OCI layouts; this function never pushes or uploads."""

    _require_revision(root, revision)
    _require_output(output)
    common = [
        "docker",
        "buildx",
        "build",
        "--platform",
        ",".join(PLATFORMS),
        "--provenance=false",
        "--sbom=false",
        "--build-arg",
        f"SOURCE_REVISION={revision}",
        "--build-arg",
        "SOURCE_IDENTITY=accepted-p9-derived-p10",
        "--build-arg",
        f"PRODUCT_VERSION={DISPLAY_VERSION}",
    ]
    runtime = output / "digital-colleagues-runtime.oci.tar"
    studio = output / "digital-colleagues-studio.oci.tar"
    _run(
        common
        + [
            "--file",
            "Dockerfile.p10",
            "--tag",
            f"digital-colleagues/runtime:{DISPLAY_VERSION}",
            "--output",
            f"type=oci,dest={runtime}",
            ".",
        ],
        cwd=root,
    )
    _run(
        common
        + [
            "--file",
            "Dockerfile.p10",
            "--tag",
            f"digital-colleagues/studio:{DISPLAY_VERSION}",
            "--output",
            f"type=oci,dest={studio}",
            ".",
        ],
        cwd=root / "studio",
    )
    runtime.chmod(0o600)
    studio.chmod(0o600)
    return {"runtime": _sha256(runtime), "studio": _sha256(studio)}


def _valid_image_ref(value: str) -> bool:
    return bool(DIGEST_REF_RE.fullmatch(value)) and ":latest@" not in value


def build_bundle(
    root: Path,
    output: Path,
    revision: str,
    runtime_image: str,
    studio_image: str,
) -> dict[str, Any]:
    """Create a path-free distribution bundle from explicit digest references."""

    _require_revision(root, revision)
    if not _valid_image_ref(runtime_image) or not _valid_image_ref(studio_image):
        raise CandidateError("image_reference_invalid")
    _require_output(output)
    timestamp = _source_timestamp(root, revision)
    migration_digest = "sha256:" + _sha256(root / "migrations/manifest.json")
    policy = json.loads(
        (root / "distribution/p10/verification-policy.json").read_text(encoding="utf-8")
    )
    from scripts.check_p10_distribution import validate_remote_policy
    from scripts.p10_gate_support import REMOTE_RESULT_KEYS

    lifecycle = validate_remote_policy(policy)
    manifest = {
        "schema_version": 1,
        "distribution_format": "digital-colleagues-p10-bundle-v1",
        "template": False,
        "product_name": PRODUCT_NAME,
        "python_version": PYTHON_VERSION,
        "display_version": DISPLAY_VERSION,
        "maturity": MATURITY,
        "source_revision": revision,
        "compose_project": PROJECT_ID,
        "runtime_image": runtime_image,
        "studio_image": studio_image,
        "platforms": list(PLATFORMS),
        "schema_versions": list(range(1, 8)),
        "migration_008": "absent",
        **{key: lifecycle for key in REMOTE_RESULT_KEYS},
    }
    operation_binding = {
        "schema_version": 1,
        "release_version": PYTHON_VERSION,
        "source_commit": revision,
        "source_timestamp": timestamp,
        "migration_manifest_digest": migration_digest,
        "artifacts": {},
        "build_inputs": {"runtime_image": runtime_image, "studio_image": studio_image},
        "evidence_classes": [
            "local_oci",
            "synthetic_offline",
            *(["remote_registry"] if lifecycle == "passed" else []),
        ],
        "claim_exclusions": [
            "remote_distribution",
            "registry_signature_or_attestation",
            "production_readiness",
        ],
    }
    from scripts.check_p10_distribution import load_manifest, verify_manifest

    verify_manifest(manifest, template=False)
    members = {
        "dc": root / "dc",
        "compose.p10.yaml": root / "compose.p10.yaml",
        "verification-policy.json": root / "distribution/p10/verification-policy.json",
    }
    for name, source in members.items():
        if source.is_symlink() or not source.is_file():
            raise CandidateError("bundle_source_invalid")
        shutil.copyfile(source, output / name)
    (output / "manifest.json").write_bytes(_json_bytes(manifest))
    verify_manifest(load_manifest(output / "manifest.json"), template=False)
    (output / "operations-source-binding.json").write_bytes(_json_bytes(operation_binding))
    os.chmod(output / "dc", 0o755)
    for name in (
        "compose.p10.yaml",
        "verification-policy.json",
        "manifest.json",
        "operations-source-binding.json",
    ):
        os.chmod(output / name, 0o644)
    checksummed = (
        "compose.p10.yaml",
        "dc",
        "manifest.json",
        "operations-source-binding.json",
        "verification-policy.json",
    )
    lines = [f"{_sha256(output / name)}  {name}" for name in checksummed]
    (output / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(output / "SHA256SUMS", 0o644)
    for path in output.iterdir():
        mode = stat.S_IMODE(path.stat().st_mode)
        expected = 0o755 if path.name == "dc" else 0o644
        if mode != expected:
            raise CandidateError("bundle_mode_invalid")
    return {
        "schema_version": 1,
        "status": "built",
        "member_count": 6,
        "source_revision": revision,
        "platforms": list(PLATFORMS),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--build-oci", action="store_true")
    parser.add_argument("--runtime-image")
    parser.add_argument("--studio-image")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    try:
        if args.build_oci:
            result: object = build_oci(root, args.output, args.source_revision)
        else:
            if not args.runtime_image or not args.studio_image:
                raise CandidateError("image_reference_required")
            result = build_bundle(
                root,
                args.output,
                args.source_revision,
                args.runtime_image,
                args.studio_image,
            )
    except CandidateError as exc:
        print(json.dumps({"status": "failed", "category": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
