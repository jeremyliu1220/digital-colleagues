# SPDX-License-Identifier: Apache-2.0

"""Validate P10 digest-only distribution and local OCI layout contracts."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
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
    REMOTE_LIFECYCLE_STATES,
    REMOTE_OIDC_ISSUER,
    REMOTE_REPOSITORY,
    REMOTE_RESULT_KEYS,
    REMOTE_SIGNER_IDENTITY,
    REMOTE_STATES,
    REMOTE_WORKFLOW_PATH,
    REMOTE_WORKFLOW_REF,
    RUNTIME_SUBJECT,
    STUDIO_SUBJECT,
    GateError,
    emit_main,
    load_json,
    valid_digest_ref,
)

FORBIDDEN_FINAL_WORKFLOW = (
    "workflow_dispatch:",
    "docker push",
    "build-push-action",
    "upload-artifact",
    "attest-build-provenance",
    "cosign sign",
    "gh release",
    "packages: write",
    "id-token: write",
    "attestations: read",
    "attestations: write",
)
ACTION_PINS = {
    "actions/checkout": "d23441a48e516b6c34aea4fa41551a30e30af803",
    "docker/setup-qemu-action": "1f40c72289eff860ee54a304f1438e3cff362e0a",
    "docker/setup-buildx-action": "37fe631027851001ddb9b187196cc803df7f5f0e",
    "docker/login-action": "dbcb813823bdd20940b903addbd779551569679f",
    "docker/build-push-action": "53b7df96c91f9c12dcc8a07bcb9ccacbed38856a",
    "sigstore/cosign-installer": "6f9f17788090df1f26f669e9d70d6ae9567deba6",
    "actions/attest": "1e69f48acb82d1966a394da916b4c1698aa569d6",
}
POLICY_KEYS = {
    "schema_version",
    "policy_id",
    "lifecycle_state",
    "required_product_name",
    "required_python_version",
    "required_display_version",
    "required_maturity",
    "required_platforms",
    "runtime_selection",
    "remote_repository",
    "remote_workflow_path",
    "remote_workflow_ref",
    "remote_signer",
    "remote_issuer",
    "published_source_revision",
    "publication_workflow_run_id",
    "publication_workflow_run_url",
    "verification_workflow_run_id",
    "verification_workflow_run_url",
    "runtime_subject",
    "runtime_digest",
    "runtime_visibility",
    "studio_subject",
    "studio_digest",
    "studio_visibility",
    "anonymous_pull",
    *REMOTE_RESULT_KEYS,
    "synthetic_fixture_may_satisfy_remote_gate",
}
PENDING_POLICY = {
    "published_source_revision": "workflow_dispatch_candidate_sha",
    "publication_workflow_run_id": "pending",
    "publication_workflow_run_url": "pending",
    "verification_workflow_run_id": "pending",
    "verification_workflow_run_url": "pending",
    "runtime_digest": "pending",
    "runtime_visibility": "pending",
    "studio_digest": "pending",
    "studio_visibility": "pending",
    "anonymous_pull": "pending",
}
GH_VERSION = "2.100.0"
GH_ARCHIVE_DIGESTS = {
    "arm64": "45f9a62da2f6e641a7fad57e2ce39656dfd7ef331372d80a2a2aed65abb01642",
    "x86_64": "fcd7799e85eb575f3c7d2b1679bfbfedaefa1269d4bc7d096b51e10939b4812b",
}
COSIGN_VERSION = "v3.0.6"
COSIGN_DIGESTS = {
    "arm64": "5fadd012ae6381a6a29ff86a7d39aa873878852f1073fc90b15995961ecfb084",
    "x86_64": "4c3e7af8372d3ca3296e62fa56f23fcbb5721cc6ac1827900d398f110d7cd280",
}
DOCKER_DESKTOP_BUILDX = Path(
    "/Applications/Docker.app/Contents/Resources/cli-plugins/docker-buildx"
)
OCI_INDEX_ACCEPT = (
    "application/vnd.oci.image.index.v1+json,"
    "application/vnd.docker.distribution.manifest.list.v2+json,"
    "application/vnd.oci.image.manifest.v1+json,"
    "application/vnd.docker.distribution.manifest.v2+json"
)
OCI_MANIFEST_ACCEPT = (
    "application/vnd.oci.image.manifest.v1+json,"
    "application/vnd.docker.distribution.manifest.v2+json"
)
SIGSTORE_BUNDLE_TYPE = "application/vnd.dev.sigstore.bundle.v0.3+json"
MANIFEST_KEYS = {
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
    *REMOTE_RESULT_KEYS,
}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise GateError("manifest_duplicate_field")
        value[key] = item
    return value


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except GateError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GateError("manifest_json_invalid") from exc
    if not isinstance(value, dict):
        raise GateError("manifest_shape_invalid")
    return value


def _valid_run(policy: dict[str, Any], prefix: str) -> bool:
    run_id = policy.get(f"{prefix}_workflow_run_id")
    run_url = policy.get(f"{prefix}_workflow_run_url")
    return (
        isinstance(run_id, str)
        and re.fullmatch(r"[1-9][0-9]*", run_id) is not None
        and run_url == f"https://github.com/{REMOTE_REPOSITORY}/actions/runs/{run_id}"
    )


def validate_remote_policy(policy: dict[str, Any]) -> str:
    if set(policy) != POLICY_KEYS:
        raise GateError("remote_policy_shape_invalid")
    lifecycle = policy.get("lifecycle_state")
    if not isinstance(lifecycle, str) or lifecycle not in REMOTE_LIFECYCLE_STATES:
        raise GateError("remote_lifecycle_invalid")
    fixed = {
        "schema_version": 2,
        "policy_id": "digital-colleagues-p10-remote-distribution-v2",
        "required_product_name": PRODUCT_NAME,
        "required_python_version": PYTHON_VERSION,
        "required_display_version": DISPLAY_VERSION,
        "required_maturity": MATURITY,
        "required_platforms": list(PLATFORMS),
        "runtime_selection": "exact_digest_only",
        "remote_repository": REMOTE_REPOSITORY,
        "remote_workflow_path": REMOTE_WORKFLOW_PATH,
        "remote_workflow_ref": REMOTE_WORKFLOW_REF,
        "remote_signer": REMOTE_SIGNER_IDENTITY,
        "remote_issuer": REMOTE_OIDC_ISSUER,
        "runtime_subject": RUNTIME_SUBJECT,
        "studio_subject": STUDIO_SUBJECT,
        "synthetic_fixture_may_satisfy_remote_gate": False,
    }
    if any(policy.get(key) != value for key, value in fixed.items()) or any(
        policy.get(key) != lifecycle for key in REMOTE_RESULT_KEYS
    ):
        raise GateError("remote_policy_identity_or_result_invalid")
    if lifecycle == "authorized_pending":
        if any(policy.get(key) != value for key, value in PENDING_POLICY.items()):
            raise GateError("authorized_pending_policy_invalid")
        return lifecycle
    revision = policy.get("published_source_revision")
    runtime_digest = policy.get("runtime_digest")
    studio_digest = policy.get("studio_digest")
    if (
        not isinstance(revision, str)
        or re.fullmatch(r"[0-9a-f]{40}", revision) is None
        or not isinstance(runtime_digest, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", runtime_digest) is None
        or not isinstance(studio_digest, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", studio_digest) is None
        or runtime_digest == studio_digest
        or not _valid_run(policy, "publication")
    ):
        raise GateError("published_remote_identity_invalid")
    if lifecycle == "published_pending_verification":
        pending = {
            "verification_workflow_run_id": "pending",
            "verification_workflow_run_url": "pending",
            "runtime_visibility": "pending",
            "studio_visibility": "pending",
            "anonymous_pull": "pending",
        }
        if any(policy.get(key) != value for key, value in pending.items()):
            raise GateError("published_pending_policy_invalid")
        return lifecycle
    if (
        not _valid_run(policy, "verification")
        or policy["publication_workflow_run_id"] == policy["verification_workflow_run_id"]
        or policy.get("runtime_visibility") != "public"
        or policy.get("studio_visibility") != "public"
        or policy.get("anonymous_pull") != "passed"
    ):
        raise GateError("passed_remote_policy_invalid")
    return lifecycle


def _job_block(workflow: str, job: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(job)}:\n(?P<body>.*?)(?=^  [a-z0-9][a-z0-9-]*:\n|\Z)",
        workflow,
    )
    if match is None:
        raise GateError("workflow_job_missing")
    return match.group(0)


def _validate_action_pins(workflow: str) -> None:
    references = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", workflow)
    if not references or any(
        "@" not in reference or re.fullmatch(r"[0-9a-f]{40}", reference.rsplit("@", 1)[1]) is None
        for reference in references
    ):
        raise GateError("workflow_action_not_immutable")


def validate_activation_workflow(workflow: str) -> None:
    _validate_action_pins(workflow)
    if "pull_request_target:" in workflow or ":latest" in workflow:
        raise GateError("workflow_unsafe_trigger_or_tag")
    for action, pin in ACTION_PINS.items():
        if f"uses: {action}@{pin}" not in workflow:
            raise GateError("workflow_action_pin_missing")
    for field in ("operation:", "confirm:", "candidate_sha:", "runtime_digest:", "studio_digest:"):
        if field not in workflow:
            raise GateError("workflow_dispatch_input_missing")
    publish = _job_block(workflow, "p10-publish")
    verify = _job_block(workflow, "p10-verify")
    guard = _job_block(workflow, "p10-dispatch-guard")
    public = _job_block(workflow, "p10-public-gate")
    conditions = (
        "github.event_name == 'workflow_dispatch'",
        "github.repository == 'jeremyliu1220/digital-colleagues'",
        "github.ref == 'refs/heads/codex/p10-mac-quickstart'",
        "inputs.candidate_sha == github.sha",
        "inputs.operation == 'publish'",
        "inputs.confirm == 'PUBLISH-P10-CANDIDATE'",
    )
    if any(value not in publish for value in conditions):
        raise GateError("workflow_publish_condition_invalid")
    if (
        "permissions:\n      contents: read\n      packages: write\n      id-token: write\n"
        "      attestations: write\n      artifact-metadata: write\n" not in publish
    ):
        raise GateError("workflow_publish_permissions_invalid")
    without_publish = workflow.replace(publish, "")
    if any(
        marker in without_publish
        for marker in (
            "packages: write",
            "id-token: write",
            "attestations: write",
            "artifact-metadata: write",
            "docker/login-action",
            "docker/build-push-action",
            "actions/attest@",
            "cosign sign",
        )
    ):
        raise GateError("workflow_write_authority_outside_publish")
    required_publish = (
        "context: .",
        "file: Dockerfile.p10",
        "context: studio",
        "file: studio/Dockerfile.p10",
        "platforms: linux/amd64,linux/arm64",
        "provenance: false",
        "sbom: false",
        "DISPLAY_TAG: sha-${{ github.sha }}",
        "SOURCE_IDENTITY=https://github.com/jeremyliu1220/digital-colleagues",
        "org.opencontainers.image.source=https://github.com/jeremyliu1220/digital-colleagues",
        "org.opencontainers.image.revision=${{ github.sha }}",
        "source_revision=$GITHUB_SHA",
        "subject-name: ${{ env.RUNTIME_SUBJECT }}",
        "subject-name: ${{ env.STUDIO_SUBJECT }}",
        "push-to-registry: true",
        "create-storage-record: false",
    )
    if any(value not in publish for value in required_publish):
        raise GateError("workflow_publish_contract_missing")
    if (
        publish.count("docker/build-push-action@") != 2
        or publish.count("actions/attest@") != 2
        or publish.count("source_revision=$GITHUB_SHA") != 2
    ):
        raise GateError("workflow_publish_step_count_invalid")
    if (
        "permissions:\n      contents: read\n" not in verify
        or "      attestations: read\n" not in verify
        or any(
            marker in verify
            for marker in (
                "packages: write",
                "id-token: write",
                "attestations: write",
                "artifact-metadata: write",
                "docker/login-action",
            )
        )
        or "scripts/check_p10_distribution.py --remote-from-env" not in verify
        or "P10_REMOTE_DOCKER_CONFIG" not in verify
    ):
        raise GateError("workflow_verify_not_read_only")
    if (
        "inputs.operation == 'verify'" not in verify
        or "inputs.confirm == 'VERIFY-P10-CANDIDATE'" not in verify
        or "inputs.candidate_sha == '05e73ea23ac650edfae59fa409a770fdf967af3a'" not in verify
        or "github.sha == '05e73ea23ac650edfae59fa409a770fdf967af3a'" not in publish
        or "PUBLISHED_SOURCE_SHA: 05e73ea23ac650edfae59fa409a770fdf967af3a" not in guard
        or 'test "$GITHUB_SHA" = "$PUBLISHED_SOURCE_SHA"' not in guard
        or 'test "$CANDIDATE_SHA" = "$PUBLISHED_SOURCE_SHA"' not in guard
        or 'test "$GITHUB_REPOSITORY" = "jeremyliu1220/digital-colleagues"' not in guard
        or 'test "$GITHUB_REF" = "refs/heads/codex/p10-mac-quickstart"' not in guard
        or "github.event_name != 'workflow_dispatch'" not in public
    ):
        raise GateError("workflow_dispatch_guard_invalid")
    if any(
        marker in workflow.lower()
        for marker in ("upload-artifact", "gh release", "git tag", "write-all")
    ):
        raise GateError("workflow_forbidden_mutation")


def validate_final_workflow(workflow: str) -> None:
    _validate_action_pins(workflow)
    lowered = workflow.lower()
    if "pull_request_target:" in lowered or any(
        marker in lowered for marker in FORBIDDEN_FINAL_WORKFLOW
    ):
        raise GateError("final_workflow_publication_authority_present")
    if any(
        marker in workflow
        for marker in (
            "p10-publish:",
            "p10-verify:",
            "p10-dispatch-guard:",
            "PUBLISH-P10-CANDIDATE",
            "VERIFY-P10-CANDIDATE",
        )
    ):
        raise GateError("final_workflow_remote_job_present")
    jobs = workflow.split("\njobs:\n", 1)
    if (
        len(jobs) != 2
        or "permissions:\n  contents: read\n" not in workflow
        or re.findall(r"(?m)^  ([a-z0-9][a-z0-9-]*):\n", jobs[1]) != ["p10-public-gate"]
    ):
        raise GateError("final_workflow_read_only_shape_invalid")


def verify_manifest(value: dict[str, Any], *, template: bool) -> None:
    if (
        set(value) != MANIFEST_KEYS
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or not isinstance(value["distribution_format"], str)
        or value["distribution_format"] != "digital-colleagues-p10-bundle-v1"
    ):
        raise GateError("manifest_shape_invalid")
    if (
        type(value["template"]) is not bool
        or value["template"] is not template
        or not all(
            isinstance(value[key], str)
            for key in (
                "product_name",
                "python_version",
                "display_version",
                "maturity",
                "source_revision",
                "compose_project",
                "runtime_image",
                "studio_image",
                "migration_008",
                *REMOTE_RESULT_KEYS,
            )
        )
        or value["product_name"] != PRODUCT_NAME
        or value["python_version"] != PYTHON_VERSION
        or value["display_version"] != DISPLAY_VERSION
        or value["maturity"] != MATURITY
    ):
        raise GateError("manifest_metadata_invalid")
    if (
        not isinstance(value["platforms"], list)
        or not all(isinstance(item, str) for item in value["platforms"])
        or value["platforms"] != list(PLATFORMS)
        or not isinstance(value["schema_versions"], list)
        or not all(type(item) is int for item in value["schema_versions"])
        or value["schema_versions"] != list(range(1, 8))
        or value["migration_008"] != "absent"
    ):
        raise GateError("manifest_platform_or_schema_invalid")
    if value["compose_project"] != "digital-colleagues-p10":
        raise GateError("manifest_compose_identity_invalid")
    lifecycle = value["remote_distribution_gate"]
    if lifecycle not in REMOTE_LIFECYCLE_STATES or any(
        value[key] != lifecycle for key in REMOTE_RESULT_KEYS
    ):
        raise GateError("remote_lifecycle_state_invalid")
    if template:
        if (
            value["source_revision"] != "IMPLEMENTATION_COMMIT_REQUIRED"
            or value["runtime_image"]
            != "LOCAL_REGISTRY_REQUIRED/digital-colleagues/runtime@sha256:EXACT_DIGEST_REQUIRED"
            or value["studio_image"]
            != "LOCAL_REGISTRY_REQUIRED/digital-colleagues/studio@sha256:EXACT_DIGEST_REQUIRED"
        ):
            raise GateError("manifest_template_placeholder_invalid")
    elif (
        re.fullmatch(r"[0-9a-f]{40}", value["source_revision"]) is None
        or not valid_digest_ref(value["runtime_image"])
        or not valid_digest_ref(value["studio_image"])
    ):
        raise GateError("manifest_image_or_revision_invalid")


def verify_compose_network_boundary(compose: str) -> None:
    def service_block(service: str) -> str:
        match = re.search(
            rf"(?ms)^  {re.escape(service)}:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:\n|^networks:\n|\Z)",
            compose,
        )
        if match is None:
            raise GateError("compose_service_missing")
        return match.group("body")

    for service in ("api", "worker", "studio"):
        block = service_block(service)
        network = re.search(r"(?m)^    networks:\n(?P<body>(?:      - [^\n]+\n)+)", block)
        if network is None or network.group("body") != "      - p10-internal\n":
            raise GateError("compose_internal_network_membership_invalid")
    gateway = service_block("gateway")
    gateway_network = re.search(r"(?m)^    networks:\n(?P<body>(?:      - [^\n]+\n)+)", gateway)
    if (
        gateway_network is None
        or gateway_network.group("body") != "      - p10-internal\n      - p10-loopback\n"
        or "127.0.0.1:${DC_API_PORT" not in gateway
        or "127.0.0.1:${DC_STUDIO_PORT" not in gateway
        or "    volumes:\n" in gateway
        or "    environment:\n" in gateway
    ):
        raise GateError("compose_loopback_gateway_boundary_invalid")
    operator = service_block("operator")
    if "    network_mode: none\n" not in operator or "    networks:\n" in operator:
        raise GateError("compose_operator_network_boundary_invalid")
    match = re.search(r"(?ms)^networks:\n(?P<body>.*)\Z", compose)
    if (
        match is None
        or match.group("body").strip() != "p10-internal:\n    internal: true\n  p10-loopback:"
    ):
        raise GateError("compose_internal_network_definition_invalid")


def verify_remote_fixture(value: dict[str, Any]) -> None:
    """Validate the shape of externally obtained, exact remote evidence."""

    policy = value.get("policy")
    if policy != "remote" or value.get("evidence_class") == "synthetic_offline":
        raise GateError("synthetic_or_unresolved_remote_candidate")
    expected = {
        "repository": REMOTE_REPOSITORY,
        "workflow": REMOTE_WORKFLOW_PATH,
        "workflow_ref": REMOTE_WORKFLOW_REF,
        "signer": REMOTE_SIGNER_IDENTITY,
        "issuer": REMOTE_OIDC_ISSUER,
        "visibility": "public",
        "anonymous_pull": "passed",
    }
    if any(value.get(key) != expected_value for key, expected_value in expected.items()):
        raise GateError("remote_identity_or_visibility_invalid")
    if (
        value.get("subject_name") not in {RUNTIME_SUBJECT, STUDIO_SUBJECT}
        or not isinstance(value.get("subject_digest"), str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", value["subject_digest"]) is None
        or not isinstance(value.get("source_revision"), str)
        or re.fullmatch(r"[0-9a-f]{40}", value["source_revision"]) is None
        or value.get("source_revision_annotation") != value["source_revision"]
        or value.get("platforms") != list(PLATFORMS)
        or value.get("signature_verified") is not True
        or value.get("attestation_verified") is not True
    ):
        raise GateError("remote_verification_incomplete")


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


def _curl_https_request(
    url: str,
    headers: dict[str, str],
    *,
    method: str,
    maximum_bytes: int,
) -> tuple[int, bytes, dict[str, str]]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise urllib.error.URLError("invalid_https_url")
    for key, value in headers.items():
        if any(character in key + value for character in ("\r", "\n")):
            raise urllib.error.URLError("invalid_https_header")
    with tempfile.TemporaryDirectory(prefix="dc-p10-https-") as name:
        work = Path(name)
        header_path = work / "headers"
        body_path = work / "body"
        command = [
            "/usr/bin/curl",
            "--silent",
            "--show-error",
            "--location",
            "--proto",
            "=https",
            "--max-time",
            "60",
            "--dump-header",
            str(header_path),
            "--output",
            str(body_path),
            "--write-out",
            "%{http_code}",
            "--config",
            "-",
        ]
        if method == "HEAD":
            command.append("--head")
        elif method == "GET":
            command.extend(["--max-filesize", str(maximum_bytes)])
        else:
            raise urllib.error.URLError("invalid_https_method")
        command.append(url)
        config_lines = []
        for key, value in headers.items():
            escaped = f"{key}: {value}".replace("\\", "\\\\").replace('"', '\\"')
            config_lines.append(f'header = "{escaped}"')
        try:
            completed = subprocess.run(
                command,
                input="\n".join(config_lines) + "\n",
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=70,
                check=False,
            )
            status_text = completed.stdout.strip()
            if completed.returncode != 0 or re.fullmatch(r"[1-5][0-9]{2}", status_text) is None:
                raise urllib.error.URLError("system_https_request_failed")
            content = b"" if method == "HEAD" else body_path.read_bytes()
            raw_headers = header_path.read_bytes()
        except (OSError, subprocess.SubprocessError) as exc:
            raise urllib.error.URLError("system_https_request_failed") from exc
    if len(content) > maximum_bytes:
        raise urllib.error.URLError("system_https_response_oversized")
    blocks = [
        block
        for block in re.split(rb"\r?\n\r?\n", raw_headers.strip())
        if block.startswith(b"HTTP/")
    ]
    if not blocks:
        raise urllib.error.URLError("system_https_headers_invalid")
    response_headers: dict[str, str] = {}
    for line in blocks[-1].splitlines()[1:]:
        if b":" not in line:
            continue
        header_key, header_value = line.split(b":", 1)
        response_headers[header_key.decode("ascii", "strict").lower()] = header_value.decode(
            "latin-1", "strict"
        ).strip()
    return int(status_text), content, response_headers


def _https_request(
    url: str,
    headers: dict[str, str] | None = None,
    *,
    method: str = "GET",
    maximum_bytes: int,
) -> tuple[int, bytes, dict[str, str]]:
    request_headers = headers or {}
    if platform.system() == "Darwin":
        return _curl_https_request(
            url,
            request_headers,
            method=method,
            maximum_bytes=maximum_bytes,
        )
    request = urllib.request.Request(url, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content = b"" if method == "HEAD" else response.read(maximum_bytes + 1)
            response_headers = {key.lower(): value for key, value in response.headers.items()}
            status = response.status
    except urllib.error.HTTPError as exc:
        content = b"" if method == "HEAD" else exc.read(maximum_bytes + 1)
        response_headers = {key.lower(): value for key, value in exc.headers.items()}
        status = exc.code
    if len(content) > maximum_bytes:
        raise urllib.error.URLError("https_response_oversized")
    return status, content, response_headers


def _download(url: str, maximum_bytes: int) -> bytes:
    try:
        status, content, _ = _https_request(url, maximum_bytes=maximum_bytes)
    except (OSError, urllib.error.URLError) as exc:
        raise GateError("verification_tool_download_failed") from exc
    if status != 200 or not content:
        raise GateError("verification_tool_download_invalid")
    return content


def _install_verification_tools(work: Path) -> tuple[Path, Path]:
    if os.environ.get("P10_REMOTE_USE_INSTALLED_TOOLS") == "1":
        found_gh = shutil.which("gh")
        found_cosign = shutil.which("cosign")
        if found_gh is None or found_cosign is None:
            raise GateError("installed_verification_tool_missing")
        return Path(found_gh), Path(found_cosign)
    if platform.system() != "Darwin" or platform.machine() not in GH_ARCHIVE_DIGESTS:
        raise GateError("verification_tool_platform_unsupported")
    machine = platform.machine()
    archive_arch = "arm64" if machine == "arm64" else "amd64"
    work.mkdir(mode=0o700, parents=True)
    gh_archive_name = f"gh_{GH_VERSION}_macOS_{archive_arch}.zip"
    gh_archive = _download(
        f"https://github.com/cli/cli/releases/download/v{GH_VERSION}/{gh_archive_name}",
        64 * 1024 * 1024,
    )
    if hashlib.sha256(gh_archive).hexdigest() != GH_ARCHIVE_DIGESTS[machine]:
        raise GateError("github_cli_digest_invalid")
    archive_path = work / gh_archive_name
    archive_path.write_bytes(gh_archive)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = [
                name
                for name in archive.namelist()
                if re.fullmatch(rf"gh_{re.escape(GH_VERSION)}_macOS_{archive_arch}/bin/gh", name)
            ]
            if len(members) != 1:
                raise GateError("github_cli_archive_invalid")
            gh_content = archive.read(members[0])
    except (OSError, zipfile.BadZipFile) as exc:
        raise GateError("github_cli_archive_invalid") from exc
    gh_path = work / "gh"
    gh_path.write_bytes(gh_content)
    gh_path.chmod(0o700)
    cosign_name = f"cosign-darwin-{archive_arch}"
    cosign_content = _download(
        f"https://github.com/sigstore/cosign/releases/download/{COSIGN_VERSION}/{cosign_name}",
        256 * 1024 * 1024,
    )
    if hashlib.sha256(cosign_content).hexdigest() != COSIGN_DIGESTS[machine]:
        raise GateError("cosign_digest_invalid")
    cosign_path = work / "cosign"
    cosign_path.write_bytes(cosign_content)
    cosign_path.chmod(0o700)
    archive_path.unlink()
    return gh_path, cosign_path


def _remote_run(
    command: list[str],
    *,
    root: Path,
    environment: dict[str, str],
    timeout: int = 1200,
) -> str:
    category = _remote_command_failure_category(command)
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GateError(category) from exc
    if completed.returncode != 0:
        raise GateError(category)
    return completed.stdout


def _remote_command_failure_category(command: list[str]) -> str:
    if command[:3] == ["docker", "buildx", "imagetools"] or (
        command and Path(command[0]).name == "docker-buildx" and command[1:2] == ["imagetools"]
    ):
        return "remote_buildx_inspect_failed"
    if command[:2] == ["docker", "pull"]:
        return "anonymous_exact_digest_pull_failed"
    if command[:3] == ["docker", "image", "rm"]:
        return "anonymous_exact_digest_pull_cleanup_failed"
    executable = Path(command[0]).name if command else ""
    if executable == "cosign":
        return "cosign_verification_failed"
    if executable == "gh":
        return "github_attestation_verification_failed"
    return "remote_verification_command_failed"


def _docker_buildx_command() -> list[str]:
    if (
        platform.system() == "Darwin"
        and DOCKER_DESKTOP_BUILDX.is_file()
        and os.access(DOCKER_DESKTOP_BUILDX, os.X_OK)
    ):
        return [str(DOCKER_DESKTOP_BUILDX)]
    return ["docker", "buildx"]


def _verify_anonymous_exact_digest_pulls(
    root: Path,
    reference: str,
    environment: dict[str, str],
) -> None:
    # A classic Docker image store cannot retain two platform variants under
    # one index digest. Remove only the just-pulled public reference before
    # selecting the next platform; the registry operation remains anonymous
    # and exact-digest bound.
    for target in PLATFORMS:
        _remote_run(
            ["docker", "pull", "--platform", target, reference],
            root=root,
            environment=environment,
        )
        _remote_run(
            ["docker", "image", "rm", "--force", reference],
            root=root,
            environment=environment,
        )


def _bearer_challenge(headers: Any) -> tuple[str, str, str]:
    value = headers.get("www-authenticate", "")
    match = re.fullmatch(r'Bearer realm="([^"]+)",service="([^"]+)",scope="([^"]+)"', value)
    if match is None or not match.group(1).startswith("https://ghcr.io/"):
        raise GateError("anonymous_registry_challenge_invalid")
    return match.group(1), match.group(2), match.group(3)


def _registry_exchange(subject: str, digest: str) -> tuple[str, bytes]:
    repository = subject.removeprefix("ghcr.io/")
    url = f"https://ghcr.io/v2/{repository}/manifests/{digest}"
    headers = {"Accept": OCI_INDEX_ACCEPT}
    try:
        status, raw_index, response_headers = _https_request(
            url, headers, maximum_bytes=8 * 1024 * 1024
        )
    except (OSError, urllib.error.URLError) as exc:
        raise GateError("anonymous_registry_manifest_unavailable") from exc
    if status == 200:
        return "", raw_index
    if status != 401:
        raise GateError("anonymous_registry_manifest_unavailable")
    realm, service, scope = _bearer_challenge(response_headers)
    token_url = realm + "?" + urllib.parse.urlencode({"service": service, "scope": scope})
    try:
        token_status, token_content, _ = _https_request(token_url, maximum_bytes=1024 * 1024)
        if token_status != 200:
            raise urllib.error.URLError("anonymous_registry_token_status_invalid")
        token_value = json.loads(token_content)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise GateError("anonymous_registry_token_failed") from exc
    token = token_value.get("token") if isinstance(token_value, dict) else None
    if not isinstance(token, str) or not token:
        raise GateError("anonymous_registry_token_invalid")
    try:
        manifest_status, raw_index, _ = _https_request(
            url,
            {**headers, "Authorization": f"Bearer {token}"},
            maximum_bytes=8 * 1024 * 1024,
        )
    except (OSError, urllib.error.URLError) as exc:
        raise GateError("anonymous_registry_manifest_unavailable") from exc
    if manifest_status != 200:
        raise GateError("anonymous_registry_manifest_unavailable")
    return token, raw_index


def _registry_object(
    subject: str,
    path: str,
    token: str,
    *,
    method: str = "GET",
    maximum_bytes: int = 8 * 1024 * 1024,
    accept: str = OCI_MANIFEST_ACCEPT,
) -> tuple[bytes, Any]:
    repository = subject.removeprefix("ghcr.io/")
    headers = {"Accept": accept}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        status, content, response_headers = _https_request(
            f"https://ghcr.io/v2/{repository}/{path}",
            headers,
            method=method,
            maximum_bytes=maximum_bytes,
        )
    except (OSError, urllib.error.URLError) as exc:
        raise GateError("anonymous_registry_object_unavailable") from exc
    if status != 200:
        raise GateError("anonymous_registry_object_unavailable")
    return content, response_headers


def _sha256_matches(content: bytes, digest: str) -> bool:
    return "sha256:" + hashlib.sha256(content).hexdigest() == digest


def _verify_registry_subject(
    root: Path,
    subject: str,
    digest: str,
    source_revision: str,
    environment: dict[str, str],
) -> dict[str, object]:
    reference = f"{subject}@{digest}"
    buildx_raw = _remote_run(
        [*_docker_buildx_command(), "imagetools", "inspect", "--raw", reference],
        root=root,
        environment=environment,
    )
    try:
        buildx_index = json.loads(buildx_raw)
    except json.JSONDecodeError as exc:
        raise GateError("buildx_remote_index_invalid") from exc
    token, raw_index = _registry_exchange(subject, digest)
    if not _sha256_matches(raw_index, digest):
        raise GateError("remote_index_digest_mismatch")
    try:
        index = json.loads(raw_index)
    except json.JSONDecodeError as exc:
        raise GateError("remote_index_invalid") from exc
    if buildx_index != index:
        raise GateError("buildx_registry_index_disagreement")
    manifests = index.get("manifests") if isinstance(index, dict) else None
    if not isinstance(manifests, list) or len(manifests) != 2:
        raise GateError("remote_index_manifest_count_invalid")
    platforms: list[str] = []
    config_count = 0
    layer_count = 0
    title = "Digital Colleagues Studio" if subject == STUDIO_SUBJECT else "Digital Colleagues"
    for descriptor in manifests:
        if not isinstance(descriptor, dict):
            raise GateError("remote_manifest_descriptor_invalid")
        child_digest = descriptor.get("digest")
        platform_value = descriptor.get("platform")
        if (
            not isinstance(child_digest, str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", child_digest) is None
            or not isinstance(platform_value, dict)
            or platform_value.get("os") != "linux"
            or platform_value.get("architecture") not in {"amd64", "arm64"}
            or set(platform_value) != {"architecture", "os"}
        ):
            raise GateError("remote_platform_descriptor_invalid")
        platforms.append(f"linux/{platform_value['architecture']}")
        raw_manifest, _ = _registry_object(subject, f"manifests/{child_digest}", token)
        if not _sha256_matches(raw_manifest, child_digest):
            raise GateError("remote_manifest_digest_mismatch")
        try:
            manifest = json.loads(raw_manifest)
        except json.JSONDecodeError as exc:
            raise GateError("remote_manifest_invalid") from exc
        config = manifest.get("config") if isinstance(manifest, dict) else None
        layers = manifest.get("layers") if isinstance(manifest, dict) else None
        if not isinstance(config, dict) or not isinstance(layers, list) or not layers:
            raise GateError("remote_manifest_content_invalid")
        config_digest = config.get("digest")
        if not isinstance(config_digest, str):
            raise GateError("remote_config_descriptor_invalid")
        raw_config, _ = _registry_object(subject, f"blobs/{config_digest}", token)
        if not _sha256_matches(raw_config, config_digest):
            raise GateError("remote_config_digest_mismatch")
        try:
            config_value = json.loads(raw_config)
        except json.JSONDecodeError as exc:
            raise GateError("remote_config_invalid") from exc
        labels = (
            config_value.get("config", {}).get("Labels") if isinstance(config_value, dict) else None
        )
        expected_labels = {
            "org.opencontainers.image.title": title,
            "org.opencontainers.image.version": DISPLAY_VERSION,
            "org.opencontainers.image.revision": source_revision,
            "org.opencontainers.image.licenses": "Apache-2.0",
            "org.opencontainers.image.source": f"https://github.com/{REMOTE_REPOSITORY}",
        }
        if not isinstance(labels, dict) or any(
            labels.get(key) != value for key, value in expected_labels.items()
        ):
            raise GateError("remote_config_label_invalid")
        if (
            subject == RUNTIME_SUBJECT
            and config_value.get("config", {}).get("User") != "10001:10001"
        ):
            raise GateError("remote_runtime_user_invalid")
        config_count += 1
        for layer in layers:
            layer_digest = layer.get("digest") if isinstance(layer, dict) else None
            if (
                not isinstance(layer_digest, str)
                or re.fullmatch(r"sha256:[0-9a-f]{64}", layer_digest) is None
            ):
                raise GateError("remote_layer_descriptor_invalid")
            _, headers = _registry_object(
                subject, f"blobs/{layer_digest}", token, method="HEAD", maximum_bytes=0
            )
            response_digest = headers.get("docker-content-digest")
            if response_digest is not None and response_digest != layer_digest:
                raise GateError("remote_layer_digest_mismatch")
            layer_count += 1
    if sorted(platforms) != sorted(PLATFORMS) or config_count != 2 or layer_count < 2:
        raise GateError("remote_platform_or_blob_set_invalid")
    _verify_anonymous_exact_digest_pulls(root, reference, environment)
    machine = platform.machine()
    if platform.system() == "Darwin" and machine in {"arm64", "x86_64"}:
        native = "linux/arm64" if machine == "arm64" else "linux/amd64"
        _remote_run(
            ["docker", "pull", "--platform", native, reference],
            root=root,
            environment=environment,
        )
    return {
        "subject": subject,
        "digest": digest,
        "platforms": sorted(platforms),
        "config_count": config_count,
        "layer_count": layer_count,
        "anonymous_exact_digest_pull": "passed",
    }


def _verify_cosign(
    root: Path,
    cosign: Path,
    subject: str,
    digest: str,
    source_revision: str,
    environment: dict[str, str],
) -> None:
    output = _remote_run(
        [
            str(cosign),
            "verify",
            "--certificate-identity",
            REMOTE_SIGNER_IDENTITY,
            "--certificate-oidc-issuer",
            REMOTE_OIDC_ISSUER,
            "-a",
            f"source_revision={source_revision}",
            "--output",
            "json",
            f"{subject}@{digest}",
        ],
        root=root,
        environment=environment,
    )
    try:
        signatures = json.loads(output)
    except json.JSONDecodeError as exc:
        raise GateError("cosign_verification_output_invalid") from exc
    if not isinstance(signatures, list) or not signatures:
        raise GateError("cosign_signature_missing")
    for signature in signatures:
        if (
            not isinstance(signature, dict)
            or signature.get("critical", {}).get("image", {}).get("docker-manifest-digest")
            != digest
            or signature.get("optional", {}).get("source_revision") != source_revision
        ):
            raise GateError("cosign_signature_claim_invalid")


def _load_registry_attestation_bundle(subject: str, digest: str) -> tuple[bytes, bytes]:
    token, raw_index = _registry_exchange(subject, digest)
    if not _sha256_matches(raw_index, digest):
        raise GateError("attestation_artifact_digest_mismatch")
    attestation_tag = digest.replace(":", "-", 1)
    raw_referrer_index, _ = _registry_object(
        subject,
        f"manifests/{attestation_tag}",
        token,
        accept=OCI_INDEX_ACCEPT,
    )
    try:
        referrer_index = json.loads(raw_referrer_index)
    except json.JSONDecodeError as exc:
        raise GateError("attestation_referrer_index_invalid") from exc
    descriptors = referrer_index.get("manifests") if isinstance(referrer_index, dict) else None
    bundle_descriptors = (
        [
            item
            for item in descriptors
            if isinstance(item, dict) and item.get("artifactType") == SIGSTORE_BUNDLE_TYPE
        ]
        if isinstance(descriptors, list)
        else []
    )
    if len(bundle_descriptors) != 1:
        raise GateError("attestation_referrer_descriptor_invalid")
    artifact_digest = bundle_descriptors[0].get("digest")
    if (
        not isinstance(artifact_digest, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", artifact_digest) is None
    ):
        raise GateError("attestation_referrer_digest_invalid")
    raw_artifact_manifest, _ = _registry_object(
        subject,
        f"manifests/{artifact_digest}",
        token,
        accept=OCI_MANIFEST_ACCEPT,
    )
    if not _sha256_matches(raw_artifact_manifest, artifact_digest):
        raise GateError("attestation_referrer_digest_mismatch")
    try:
        artifact_manifest = json.loads(raw_artifact_manifest)
    except json.JSONDecodeError as exc:
        raise GateError("attestation_referrer_manifest_invalid") from exc
    layers = artifact_manifest.get("layers") if isinstance(artifact_manifest, dict) else None
    subject_descriptor = (
        artifact_manifest.get("subject") if isinstance(artifact_manifest, dict) else None
    )
    if (
        not isinstance(artifact_manifest, dict)
        or artifact_manifest.get("artifactType") != SIGSTORE_BUNDLE_TYPE
        or not isinstance(subject_descriptor, dict)
        or subject_descriptor.get("digest") != digest
        or not isinstance(layers, list)
        or len(layers) != 1
    ):
        raise GateError("attestation_referrer_manifest_invalid")
    layer = layers[0]
    layer_digest = layer.get("digest") if isinstance(layer, dict) else None
    layer_size = layer.get("size") if isinstance(layer, dict) else None
    if (
        not isinstance(layer_digest, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", layer_digest) is None
        or layer.get("mediaType") != SIGSTORE_BUNDLE_TYPE
        or type(layer_size) is not int
        or layer_size <= 0
        or layer_size > 2 * 1024 * 1024
    ):
        raise GateError("attestation_bundle_descriptor_invalid")
    bundle, _ = _registry_object(
        subject,
        f"blobs/{layer_digest}",
        token,
        maximum_bytes=2 * 1024 * 1024,
    )
    if len(bundle) != layer_size or not _sha256_matches(bundle, layer_digest):
        raise GateError("attestation_bundle_digest_mismatch")
    try:
        bundle_value = json.loads(bundle)
    except json.JSONDecodeError as exc:
        raise GateError("attestation_bundle_invalid") from exc
    if not isinstance(bundle_value, dict):
        raise GateError("attestation_bundle_invalid")
    return raw_index, bundle


def _verify_attestation(
    root: Path,
    gh: Path,
    subject: str,
    digest: str,
    source_revision: str,
    environment: dict[str, str],
) -> None:
    artifact, bundle = _load_registry_attestation_bundle(subject, digest)
    with tempfile.TemporaryDirectory(prefix="dc-p10-attestation-") as name:
        work = Path(name)
        artifact_path = work / "artifact.index.json"
        bundle_path = work / "attestation.bundle.json"
        artifact_path.write_bytes(artifact)
        bundle_path.write_bytes(bundle)
        artifact_path.chmod(0o600)
        bundle_path.chmod(0o600)
        output = _remote_run(
            [
                str(gh),
                "attestation",
                "verify",
                str(artifact_path),
                "-R",
                REMOTE_REPOSITORY,
                "--bundle",
                str(bundle_path),
                "--signer-digest",
                source_revision,
                "--source-ref",
                REMOTE_WORKFLOW_REF,
                "--source-digest",
                source_revision,
                "--cert-identity",
                REMOTE_SIGNER_IDENTITY,
                "--cert-oidc-issuer",
                REMOTE_OIDC_ISSUER,
                "--deny-self-hosted-runners",
                "--predicate-type",
                "https://slsa.dev/provenance/v1",
                "--format",
                "json",
            ],
            root=root,
            environment=environment,
        )
    try:
        attestations = json.loads(output)
    except json.JSONDecodeError as exc:
        raise GateError("attestation_verification_output_invalid") from exc
    if not isinstance(attestations, list) or not attestations:
        raise GateError("attestation_missing")
    matched = 0
    for attestation in attestations:
        statement = (
            attestation.get("verificationResult", {}).get("statement")
            if isinstance(attestation, dict)
            else None
        )
        subjects = statement.get("subject") if isinstance(statement, dict) else None
        if not isinstance(subjects, list):
            raise GateError("attestation_subject_invalid")
        for item in subjects:
            if (
                isinstance(item, dict)
                and item.get("name") == subject
                and item.get("digest") == {"sha256": digest.removeprefix("sha256:")}
            ):
                matched += 1
    if matched < 1:
        raise GateError("attestation_subject_mismatch")


def verify_remote_distribution(
    root: Path,
    policy: dict[str, Any],
    work: Path,
    *,
    source_revision: str | None = None,
    runtime_digest: str | None = None,
    studio_digest: str | None = None,
) -> dict[str, object]:
    lifecycle = validate_remote_policy(policy)
    if lifecycle == "authorized_pending":
        revision = source_revision
        runtime = runtime_digest
        studio = studio_digest
    elif lifecycle == "passed":
        revision = policy["published_source_revision"]
        runtime = policy["runtime_digest"]
        studio = policy["studio_digest"]
        if any(value is not None for value in (source_revision, runtime_digest, studio_digest)):
            raise GateError("locked_policy_override_forbidden")
    else:
        raise GateError("remote_verification_lifecycle_invalid")
    if (
        not isinstance(revision, str)
        or re.fullmatch(r"[0-9a-f]{40}", revision) is None
        or not isinstance(runtime, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", runtime) is None
        or not isinstance(studio, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", studio) is None
        or runtime == studio
    ):
        raise GateError("remote_verification_input_invalid")
    docker_config = Path(os.environ.get("P10_REMOTE_DOCKER_CONFIG", work / "docker"))
    if docker_config.exists():
        if docker_config.is_symlink() or not docker_config.is_dir():
            raise GateError("anonymous_docker_config_invalid")
    else:
        docker_config.mkdir(mode=0o700, parents=True)
    config = docker_config / "config.json"
    if not config.exists():
        config.write_text('{"auths":{}}\n', encoding="utf-8")
        config.chmod(0o600)
    try:
        config_value = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError("anonymous_docker_config_invalid") from exc
    if config_value != {"auths": {}} or stat.S_IMODE(config.stat().st_mode) & 0o077:
        raise GateError("anonymous_docker_credentials_present")
    environment = os.environ.copy()
    environment.pop("DOCKER_AUTH_CONFIG", None)
    environment["DOCKER_CONFIG"] = str(docker_config)
    gh, cosign = _install_verification_tools(work / "tools")
    images: dict[str, dict[str, object]] = {}
    for name, subject, digest in (
        ("runtime", RUNTIME_SUBJECT, runtime),
        ("studio", STUDIO_SUBJECT, studio),
    ):
        image = _verify_registry_subject(root, subject, digest, revision, environment)
        _verify_cosign(root, cosign, subject, digest, revision, environment)
        _verify_attestation(root, gh, subject, digest, revision, environment)
        image.update(
            {
                "cosign_identity": REMOTE_SIGNER_IDENTITY,
                "cosign_issuer": REMOTE_OIDC_ISSUER,
                "source_revision_annotation": revision,
                "signature": "passed",
                "github_attestation": "passed",
            }
        )
        images[name] = image
    return {
        "schema_version": 1,
        "gate": "p10_remote_distribution_clean",
        "repository": REMOTE_REPOSITORY,
        "workflow": REMOTE_WORKFLOW_PATH,
        "workflow_ref": REMOTE_WORKFLOW_REF,
        "published_source_revision": revision,
        "runtime": images["runtime"],
        "studio": images["studio"],
        "public_visibility": "passed",
        "anonymous_pull": "passed",
        **REMOTE_STATES,
    }


def check_distribution(root: Path) -> dict[str, object]:
    template = load_manifest(root / "distribution/p10/release-manifest.template.json")
    verify_manifest(template, template=True)
    policy = load_json(root / "distribution/p10/verification-policy.json")
    lifecycle = validate_remote_policy(policy)
    if any(template.get(key) != lifecycle for key in REMOTE_RESULT_KEYS):
        raise GateError("manifest_policy_lifecycle_mismatch")
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
    verify_compose_network_boundary(compose)
    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    if lifecycle in {"authorized_pending", "published_pending_verification"}:
        validate_activation_workflow(workflow)
    else:
        validate_final_workflow(workflow)
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
        "lifecycle_state": lifecycle,
        "remote_repository": policy["remote_repository"],
        "remote_workflow_path": policy["remote_workflow_path"],
        "remote_workflow_ref": policy["remote_workflow_ref"],
        "remote_signer": policy["remote_signer"],
        "remote_issuer": policy["remote_issuer"],
        "published_source_revision": policy["published_source_revision"],
        "publication_workflow_run_id": policy["publication_workflow_run_id"],
        "publication_workflow_run_url": policy["publication_workflow_run_url"],
        "verification_workflow_run_id": policy["verification_workflow_run_id"],
        "verification_workflow_run_url": policy["verification_workflow_run_url"],
        "runtime_subject": policy["runtime_subject"],
        "runtime_digest": policy["runtime_digest"],
        "runtime_visibility": policy["runtime_visibility"],
        "studio_subject": policy["studio_subject"],
        "studio_digest": policy["studio_digest"],
        "studio_visibility": policy["studio_visibility"],
        "anonymous_pull": policy["anonymous_pull"],
        **{key: policy[key] for key in REMOTE_RESULT_KEYS},
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--remote-from-env", action="store_true")
    arguments = parser.parse_args(argv)
    root = Path(arguments.root).resolve()
    if not arguments.remote_from_env:
        return emit_main(check_distribution, [str(root)], __doc__)
    try:
        policy = load_json(root / "distribution/p10/verification-policy.json")
        with tempfile.TemporaryDirectory(prefix="dc-p10-remote-workflow-") as name:
            result = verify_remote_distribution(
                root,
                policy,
                Path(name),
                source_revision=os.environ.get("P10_REMOTE_PUBLICATION_SHA"),
                runtime_digest=os.environ.get("P10_REMOTE_RUNTIME_DIGEST"),
                studio_digest=os.environ.get("P10_REMOTE_STUDIO_DIGEST"),
            )
    except (GateError, OSError, subprocess.SubprocessError, ValueError) as exc:
        print(
            json.dumps({"status": "failed", "category": str(exc)}, sort_keys=True), file=sys.stderr
        )
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
