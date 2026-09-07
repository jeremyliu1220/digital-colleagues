# SPDX-License-Identifier: Apache-2.0

"""Validate P10 digest-only distribution and local OCI layout contracts."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tarfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.p10_gate_support import (
    DISPLAY_VERSION,
    MATURITY,
    PLATFORMS,
    PRODUCT_NAME,
    PYTHON_VERSION,
    REMOTE_STATES,
    GateError,
    emit_main,
    load_json,
    valid_digest_ref,
)

FORBIDDEN_WORKFLOW = (
    "docker push",
    "build-push-action",
    "upload-artifact",
    "attest-build-provenance",
    "cosign sign",
    "gh release",
    "packages: write",
    "id-token: write",
    "attestations: write",
)


def verify_manifest(value: dict[str, Any], *, template: bool) -> None:
    required = {
        "schema_version",
        "distribution_format",
        "template",
        "product_name",
        "python_version",
        "display_version",
        "maturity",
        "source_revision",
        "compose_project",
        "runtime_image",
        "studio_image",
        "platforms",
        "schema_versions",
        "migration_008",
        *REMOTE_STATES,
    }
    if (
        set(value) != required
        or value["schema_version"] != 1
        or value["distribution_format"] != "digital-colleagues-p10-bundle-v1"
    ):
        raise GateError("manifest_shape_invalid")
    if (
        value["template"] is not template
        or value["product_name"] != PRODUCT_NAME
        or value["python_version"] != PYTHON_VERSION
        or value["display_version"] != DISPLAY_VERSION
        or value["maturity"] != MATURITY
    ):
        raise GateError("manifest_metadata_invalid")
    if (
        value["platforms"] != list(PLATFORMS)
        or value["schema_versions"] != list(range(1, 8))
        or value["migration_008"] != "absent"
    ):
        raise GateError("manifest_platform_or_schema_invalid")
    if any(value[key] != state for key, state in REMOTE_STATES.items()):
        raise GateError("remote_authorization_state_invalid")
    if not template and (
        not valid_digest_ref(value["runtime_image"]) or not valid_digest_ref(value["studio_image"])
    ):
        raise GateError("manifest_image_reference_invalid")


def verify_remote_fixture(value: dict[str, Any]) -> None:
    """Remote completion can never be supplied by the local synthetic fixture."""

    policy = value.get("policy")
    if policy != "remote" or value.get("evidence_class") == "synthetic_offline":
        raise GateError("synthetic_or_unresolved_remote_candidate")
    required = ("repository", "workflow", "signer", "subject_name", "subject_digest")
    if any(
        not isinstance(value.get(key), str) or value[key] in {"", "authorization_required"}
        for key in required
    ):
        raise GateError("remote_identity_unresolved")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", value["subject_digest"]):
        raise GateError("remote_digest_invalid")
    if value.get("signature_verified") is not True or value.get("attestation_verified") is not True:
        raise GateError("remote_verification_incomplete")
    raise GateError("remote_distribution_not_authorized_by_p10")


def inspect_oci_layout(path: Path) -> dict[str, object]:
    image_kind = "studio" if "studio" in path.name else "runtime"
    try:
        with tarfile.open(path, "r") as archive:
            names = set(archive.getnames())
            index_member = archive.extractfile("index.json")
            if index_member is None:
                raise GateError("oci_index_missing")
            index = json.load(index_member)
            manifests = index.get("manifests") if isinstance(index, dict) else None
            if not isinstance(manifests, list) or not manifests:
                raise GateError("oci_manifest_count_invalid")
            platforms: set[str] = set()
            checked: set[str] = set()
            image_manifest_count = 0
            config_count = 0
            queue = list(manifests)
            while queue:
                descriptor = queue.pop()
                digest = descriptor.get("digest")
                if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
                    raise GateError("oci_descriptor_digest_invalid")
                blob_name = "blobs/sha256/" + digest.removeprefix("sha256:")
                if blob_name not in names:
                    raise GateError("oci_blob_missing")
                member = archive.extractfile(blob_name)
                if member is None:
                    raise GateError("oci_blob_missing")
                content = member.read()
                if hashlib.sha256(content).hexdigest() != digest.removeprefix("sha256:"):
                    raise GateError("oci_blob_digest_mismatch")
                if digest in checked:
                    continue
                checked.add(digest)
                media_type = descriptor.get("mediaType", "")
                if isinstance(media_type, str) and ".layer." in media_type:
                    continue
                document = json.loads(content)
                if descriptor.get("_p10_config") is True:
                    config_count += 1
                    config = document.get("config") if isinstance(document, dict) else None
                    if not isinstance(config, dict):
                        raise GateError("oci_config_invalid")
                    labels = config.get("Labels")
                    title = (
                        "Digital Colleagues Studio"
                        if image_kind == "studio"
                        else "Digital Colleagues"
                    )
                    required_labels = {
                        "org.opencontainers.image.title": title,
                        "org.opencontainers.image.version": DISPLAY_VERSION,
                        "org.opencontainers.image.licenses": "Apache-2.0",
                        "org.opencontainers.image.source": "accepted-p9-derived-p10",
                    }
                    if not isinstance(labels, dict) or any(
                        labels.get(key) != value for key, value in required_labels.items()
                    ):
                        raise GateError("oci_config_label_invalid")
                    revision = labels.get("org.opencontainers.image.revision")
                    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
                        raise GateError("oci_config_revision_invalid")
                    if image_kind == "runtime":
                        command = config.get("Cmd")
                        if (
                            config.get("User") != "10001:10001"
                            or not isinstance(command, list)
                            or "uvicorn" not in command
                        ):
                            raise GateError("oci_runtime_content_invalid")
                    else:
                        command = config.get("Cmd")
                        if not isinstance(command, list) or "nginx" not in command:
                            raise GateError("oci_studio_content_invalid")
                platform = descriptor.get("platform")
                if (
                    isinstance(platform, dict)
                    and platform.get("os") == "linux"
                    and platform.get("architecture") in {"amd64", "arm64"}
                ):
                    platforms.add(f"linux/{platform['architecture']}")
                children = document.get("manifests") if isinstance(document, dict) else None
                if isinstance(children, list):
                    queue.extend(item for item in children if isinstance(item, dict))
                for key in ("config",):
                    child = document.get(key) if isinstance(document, dict) else None
                    if isinstance(child, dict) and isinstance(child.get("digest"), str):
                        config_descriptor = dict(child)
                        config_descriptor["_p10_config"] = True
                        queue.append(config_descriptor)
                layers = document.get("layers") if isinstance(document, dict) else None
                if isinstance(layers, list):
                    image_manifest_count += 1
                    queue.extend(item for item in layers if isinstance(item, dict))
            if platforms != set(PLATFORMS) or image_manifest_count != 2 or config_count != 2:
                raise GateError("oci_platform_set_invalid")
    except (OSError, tarfile.TarError, json.JSONDecodeError) as exc:
        raise GateError("oci_layout_invalid") from exc
    return {
        "platforms": sorted(platforms),
        "verified_blob_count": len(checked),
        "verified_config_count": config_count,
        "content_contract": image_kind,
    }


def check_distribution(root: Path) -> dict[str, object]:
    template = load_json(root / "distribution/p10/release-manifest.template.json")
    verify_manifest(template, template=True)
    policy = load_json(root / "distribution/p10/verification-policy.json")
    if policy.get("synthetic_fixture_may_satisfy_remote_gate") is not False or any(
        policy.get(key) != state for key, state in REMOTE_STATES.items()
    ):
        raise GateError("verification_policy_invalid")
    compose = (root / "compose.p10.yaml").read_text(encoding="utf-8")
    if re.search(r"(?m)^\s*build\s*:", compose) or "@sha256:" in compose or ":latest" in compose:
        raise GateError("compose_build_or_embedded_image_invalid")
    for marker in (
        "${DC_RUNTIME_IMAGE:?",
        "${DC_STUDIO_IMAGE:?",
        "127.0.0.1:",
        "read_only: true",
        "DC_STATE_DIR",
    ):
        if marker not in compose:
            raise GateError("compose_distribution_boundary_missing")
    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8").lower()
    if any(marker in workflow for marker in FORBIDDEN_WORKFLOW):
        raise GateError("workflow_publication_authority_forbidden")
    for dockerfile in (root / "Dockerfile.p10", root / "studio/Dockerfile.p10"):
        text = dockerfile.read_text(encoding="utf-8")
        if (
            not re.search(r"^FROM [^\s]+@sha256:[0-9a-f]{64}", text, re.MULTILINE)
            or "org.opencontainers.image.revision" not in text
        ):
            raise GateError("docker_base_or_label_invalid")
    return {
        "schema_version": 1,
        "gate": "p10_distribution_clean",
        "image_count": 2,
        "platforms": list(PLATFORMS),
        "compose_build_count": 0,
        "mutable_execution_reference_count": 0,
        **REMOTE_STATES,
    }


def main(argv: list[str] | None = None) -> int:
    return emit_main(check_distribution, argv, __doc__)


if __name__ == "__main__":
    raise SystemExit(main())
