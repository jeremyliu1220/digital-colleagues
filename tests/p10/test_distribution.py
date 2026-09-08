# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import copy
import hashlib
import io
import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from scripts.check_p10_compose_runtime import validate_external_egress_probe
from scripts.check_p10_distribution import (
    DOCKER_DESKTOP_BUILDX,
    _docker_buildx_command,
    _remote_command_failure_category,
    _verify_anonymous_exact_digest_pulls,
    _verify_attestation,
    check_distribution,
    inspect_oci_layout,
    validate_activation_workflow,
    validate_final_workflow,
    validate_remote_policy,
    verify_compose_network_boundary,
    verify_manifest,
    verify_remote_fixture,
)
from scripts.p10_gate_support import (
    REMOTE_REPOSITORY,
    REMOTE_RESULT_KEYS,
    REMOTE_WORKFLOW_PATH,
    REMOTE_WORKFLOW_REF,
    RUNTIME_SUBJECT,
    GateError,
    load_json,
)
from tests.p10.fixtures import ROOT


class P10DistributionTests(unittest.TestCase):
    def _oci_fixture(
        self, path: Path, platforms: tuple[str, ...], *, corrupt: bool = False
    ) -> None:
        blobs: dict[str, bytes] = {}

        def descriptor(content: bytes, media_type: str) -> dict[str, object]:
            digest = hashlib.sha256(content).hexdigest()
            blobs[digest] = content
            return {"mediaType": media_type, "digest": f"sha256:{digest}", "size": len(content)}

        manifests: list[dict[str, object]] = []
        layer = descriptor(b"layer", "application/vnd.oci.image.layer.v1.tar+gzip")
        for architecture in platforms:
            config_value = {
                "architecture": architecture,
                "os": "linux",
                "config": {
                    "User": "10001:10001",
                    "Cmd": ["python", "uvicorn"],
                    "Labels": {
                        "org.opencontainers.image.title": "Digital Colleagues",
                        "org.opencontainers.image.version": "0.2.0-dev.0",
                        "org.opencontainers.image.revision": "a" * 40,
                        "org.opencontainers.image.licenses": "Apache-2.0",
                        "org.opencontainers.image.source": "accepted-p9-derived-p10",
                    },
                },
            }
            config = descriptor(
                json.dumps(config_value).encode(), "application/vnd.oci.image.config.v1+json"
            )
            manifest_value = {"schemaVersion": 2, "config": config, "layers": [layer]}
            manifest = descriptor(
                json.dumps(manifest_value).encode(), "application/vnd.oci.image.manifest.v1+json"
            )
            manifest["platform"] = {"os": "linux", "architecture": architecture}
            manifests.append(manifest)
        nested = descriptor(
            json.dumps({"schemaVersion": 2, "manifests": manifests}).encode(),
            "application/vnd.oci.image.index.v1+json",
        )
        index = json.dumps({"schemaVersion": 2, "manifests": [nested]}).encode()
        if corrupt:
            digest = next(iter(blobs))
            blobs[digest] = blobs[digest] + b"corrupt"
        with tarfile.open(path, "w") as archive:
            values = {
                "index.json": index,
                **{f"blobs/sha256/{key}": value for key, value in blobs.items()},
            }
            for name, content in values.items():
                info = tarfile.TarInfo(name)
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))

    def test_image_only_distribution_policy_passes(self) -> None:
        result = check_distribution(ROOT)
        policy = load_json(ROOT / "distribution/p10/verification-policy.json")
        self.assertEqual(result["compose_build_count"], 0)
        self.assertEqual(result["platforms"], ["linux/amd64", "linux/arm64"])
        self.assertEqual(result["remote_distribution_gate"], policy["lifecycle_state"])

    def test_mutable_missing_platform_and_remote_promotion_fail(self) -> None:
        template = load_json(ROOT / "distribution/p10/release-manifest.template.json")
        fixture = copy.deepcopy(template)
        fixture["template"] = False
        fixture["runtime_image"] = "example.invalid/dc/runtime:latest"
        fixture["studio_image"] = "example.invalid/dc/studio@sha256:" + "a" * 64
        with self.assertRaises(GateError):
            verify_manifest(fixture, template=False)
        fixture = copy.deepcopy(template)
        fixture["platforms"] = ["linux/arm64"]
        with self.assertRaises(GateError):
            verify_manifest(fixture, template=True)
        invalid_remote = (
            {"policy": "remote", "evidence_class": "synthetic_offline"},
            {"policy": "remote", "evidence_class": "remote"},
        )
        for invalid in invalid_remote:
            with self.subTest(remote=invalid), self.assertRaises(GateError):
                verify_remote_fixture(invalid)
        remote: dict[str, Any] = {
            "policy": "remote",
            "evidence_class": "remote_registry",
            "repository": REMOTE_REPOSITORY,
            "workflow": REMOTE_WORKFLOW_PATH,
            "workflow_ref": REMOTE_WORKFLOW_REF,
            "signer": (
                "https://github.com/jeremyliu1220/digital-colleagues/"
                ".github/workflows/ci.yml@refs/heads/codex/p10-mac-quickstart"
            ),
            "issuer": "https://token.actions.githubusercontent.com",
            "subject_name": RUNTIME_SUBJECT,
            "subject_digest": "sha256:" + "a" * 64,
            "source_revision": "b" * 40,
            "source_revision_annotation": "b" * 40,
            "platforms": ["linux/amd64", "linux/arm64"],
            "visibility": "public",
            "anonymous_pull": "passed",
            "signature_verified": True,
            "attestation_verified": True,
        }
        verify_remote_fixture(remote)
        for key, value in (
            ("repository", "wrong/repository"),
            ("workflow_ref", "refs/heads/main"),
            ("issuer", "https://issuer.invalid"),
            ("subject_digest", "sha256:" + "c" * 64),
            ("visibility", "private"),
            ("source_revision_annotation", "c" * 40),
        ):
            broken = copy.deepcopy(remote)
            broken[key] = value
            if key == "subject_digest":
                broken[key] = "wrong"
            with self.subTest(key=key), self.assertRaises(GateError):
                verify_remote_fixture(broken)

    def test_oci_missing_platform_and_digest_mismatch_fail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="dc-p10-oci-test-") as name:
            temporary = Path(name)
            missing = temporary / "runtime-missing.oci.tar"
            self._oci_fixture(missing, ("arm64",))
            with self.assertRaises(GateError):
                inspect_oci_layout(missing)
            corrupt = temporary / "runtime-corrupt.oci.tar"
            self._oci_fixture(corrupt, ("amd64", "arm64"), corrupt=True)
            with self.assertRaisesRegex(GateError, "digest_mismatch"):
                inspect_oci_layout(corrupt)

    def test_final_workflow_has_no_dispatch_or_remote_authority(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        validate_final_workflow(workflow)
        mutations = (
            ("trigger", "  pull_request:\n", "  pull_request_target:\n"),
            ("dispatch", "  push:\n", "  push:\n  workflow_dispatch:\n"),
            ("permission", "  contents: read\n", "  id-token: write\n"),
            ("remote-job", "jobs:\n", "jobs:\n  p10-verify:\n    runs-on: ubuntu-latest\n"),
        )
        for label, old, new in mutations:
            self.assertIn(old, workflow)
            with self.subTest(label=label), self.assertRaises(GateError):
                validate_final_workflow(workflow.replace(old, new, 1))

    def test_historical_activation_validator_rejects_unsafe_mutations(self) -> None:
        historical = subprocess.run(
            [
                "git",
                "show",
                "a003d540093df9a08437c47e9c8ff16970e5e645:.github/workflows/ci.yml",
            ],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        validate_activation_workflow(historical, "05e73ea23ac650edfae59fa409a770fdf967af3a")
        with self.assertRaises(GateError):
            validate_activation_workflow(
                historical.replace("packages: write", "packages: read"),
                "05e73ea23ac650edfae59fa409a770fdf967af3a",
            )

    def test_docker_desktop_buildx_is_selected_without_host_docker_config(self) -> None:
        with (
            patch("scripts.check_p10_distribution.platform.system", return_value="Darwin"),
            patch.object(Path, "is_file", return_value=True),
            patch("scripts.check_p10_distribution.os.access", return_value=True),
        ):
            self.assertEqual(_docker_buildx_command(), [str(DOCKER_DESKTOP_BUILDX)])

    def test_attestation_verifier_uses_one_exact_signer_policy(self) -> None:
        digest = "sha256:" + "1" * 64
        revision = "a" * 40
        captured: list[str] = []

        def run(command: list[str], **_: object) -> str:
            captured.extend(command)
            return json.dumps(
                [
                    {
                        "verificationResult": {
                            "statement": {
                                "subject": [
                                    {
                                        "name": RUNTIME_SUBJECT,
                                        "digest": {"sha256": digest.removeprefix("sha256:")},
                                    }
                                ]
                            }
                        }
                    }
                ]
            )

        with (
            patch("scripts.check_p10_distribution._remote_run", side_effect=run),
            patch(
                "scripts.check_p10_distribution._load_registry_attestation_bundle",
                return_value=(b"artifact", b"{}"),
            ),
        ):
            _verify_attestation(ROOT, Path("/tmp/gh"), RUNTIME_SUBJECT, digest, revision, {})
        self.assertIn("--cert-identity", captured)
        self.assertIn("--bundle", captured)
        self.assertIn("--signer-digest", captured)
        self.assertIn("--source-digest", captured)
        self.assertNotIn("--signer-repo", captured)
        self.assertNotIn("--signer-workflow", captured)

    def test_remote_command_failures_report_a_public_stage(self) -> None:
        self.assertEqual(
            _remote_command_failure_category(["docker", "buildx", "imagetools", "inspect"]),
            "remote_buildx_inspect_failed",
        )
        self.assertEqual(
            _remote_command_failure_category([str(DOCKER_DESKTOP_BUILDX), "imagetools", "inspect"]),
            "remote_buildx_inspect_failed",
        )
        self.assertEqual(
            _remote_command_failure_category(["docker", "pull", "subject@sha256:digest"]),
            "anonymous_exact_digest_pull_failed",
        )
        self.assertEqual(
            _remote_command_failure_category(
                ["docker", "image", "rm", "--force", "subject@sha256:digest"]
            ),
            "anonymous_exact_digest_pull_cleanup_failed",
        )
        self.assertEqual(
            _remote_command_failure_category(["/tmp/tools/cosign", "verify"]),
            "cosign_verification_failed",
        )
        self.assertEqual(
            _remote_command_failure_category(["/tmp/tools/gh", "attestation", "verify"]),
            "github_attestation_verification_failed",
        )

    def test_anonymous_platform_pulls_are_isolated_in_the_local_image_store(self) -> None:
        reference = "subject@sha256:digest"
        commands: list[list[str]] = []

        def run(command: list[str], **_: object) -> str:
            commands.append(command)
            return ""

        with patch("scripts.check_p10_distribution._remote_run", side_effect=run):
            _verify_anonymous_exact_digest_pulls(ROOT, reference, {})
        self.assertEqual(
            commands,
            [
                ["docker", "pull", "--platform", "linux/amd64", reference],
                ["docker", "image", "rm", "--force", reference],
                ["docker", "pull", "--platform", "linux/arm64", reference],
                ["docker", "image", "rm", "--force", reference],
            ],
        )

    def test_remote_policy_lifecycle_and_failure_states_fail_closed(self) -> None:
        policy = load_json(ROOT / "distribution/p10/verification-policy.json")
        self.assertEqual(validate_remote_policy(policy), policy["lifecycle_state"])
        pending = copy.deepcopy(policy)
        pending.update(
            {
                "lifecycle_state": "authorized_pending",
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
        )
        for key in REMOTE_RESULT_KEYS:
            pending[key] = "authorized_pending"
        self.assertEqual(validate_remote_policy(pending), "authorized_pending")
        revision = "a" * 40
        publication_run = "1001"
        verification_run = "1002"
        published = copy.deepcopy(pending)
        published.update(
            {
                "lifecycle_state": "published_pending_verification",
                "published_source_revision": revision,
                "publication_workflow_run_id": publication_run,
                "publication_workflow_run_url": (
                    f"https://github.com/{REMOTE_REPOSITORY}/actions/runs/{publication_run}"
                ),
                "runtime_digest": "sha256:" + "1" * 64,
                "studio_digest": "sha256:" + "2" * 64,
            }
        )
        for key in REMOTE_RESULT_KEYS:
            published[key] = "published_pending_verification"
        self.assertEqual(validate_remote_policy(published), "published_pending_verification")
        passed = copy.deepcopy(published)
        passed.update(
            {
                "lifecycle_state": "passed",
                "verification_workflow_run_id": verification_run,
                "verification_workflow_run_url": (
                    f"https://github.com/{REMOTE_REPOSITORY}/actions/runs/{verification_run}"
                ),
                "runtime_visibility": "public",
                "studio_visibility": "public",
                "anonymous_pull": "passed",
            }
        )
        for key in REMOTE_RESULT_KEYS:
            passed[key] = "passed"
        self.assertEqual(validate_remote_policy(passed), "passed")
        for key, value in (
            ("remote_repository", "wrong/repository"),
            ("runtime_digest", "sha256:" + "3" * 63),
            ("runtime_visibility", "private"),
            ("published_source_revision", "wrong"),
            ("remote_distribution_gate", "failed"),
        ):
            broken = copy.deepcopy(passed)
            broken[key] = value
            with self.subTest(key=key), self.assertRaises(GateError):
                validate_remote_policy(broken)

    def test_external_network_and_missing_probe_fail_closed(self) -> None:
        compose = (ROOT / "compose.p10.yaml").read_text(encoding="utf-8")
        verify_compose_network_boundary(compose)
        without_internal = compose.replace("    internal: true\n", "", 1)
        with self.assertRaisesRegex(GateError, "internal_network_definition"):
            verify_compose_network_boundary(without_internal)
        default_routed = compose.replace("    networks:\n      - p10-internal\n", "", 3).replace(
            "networks:\n  p10-internal:\n    internal: true\n", "networks:\n  default:\n"
        )
        with self.assertRaisesRegex(GateError, "internal_network_membership"):
            verify_compose_network_boundary(default_routed)
        externally_attached = compose.replace(
            "    networks:\n      - p10-internal\n",
            "    networks:\n      - p10-internal\n      - p10-loopback\n",
            1,
        )
        with self.assertRaisesRegex(GateError, "internal_network_membership"):
            verify_compose_network_boundary(externally_attached)
        with self.assertRaisesRegex(GateError, "probe_incomplete"):
            validate_external_egress_probe(
                {
                    "performed": False,
                    "control_reachable": True,
                    "internal_network_verified": True,
                    "service_network_count": 3,
                    "unexpected_connection_count": 0,
                }
            )
        with self.assertRaisesRegex(GateError, "unexpected_external_egress"):
            validate_external_egress_probe(
                {
                    "performed": True,
                    "control_reachable": True,
                    "internal_network_verified": True,
                    "service_network_count": 3,
                    "unexpected_connection_count": 1,
                }
            )


if __name__ == "__main__":
    unittest.main()
