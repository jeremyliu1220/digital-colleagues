# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import copy
import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from scripts.check_p10_distribution import (
    check_distribution,
    inspect_oci_layout,
    verify_manifest,
    verify_remote_fixture,
)
from scripts.p10_gate_support import GateError, load_json
from tests.p10.fixtures import ROOT, copy_paths


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
        self.assertEqual(result["compose_build_count"], 0)
        self.assertEqual(result["platforms"], ["linux/amd64", "linux/arm64"])
        self.assertEqual(result["remote_distribution_gate"], "authorization_required")

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
        for remote in (
            {"policy": "remote", "evidence_class": "synthetic_offline"},
            {"policy": "remote", "evidence_class": "remote"},
            {
                "policy": "remote",
                "evidence_class": "remote",
                "repository": "fixed",
                "workflow": "fixed",
                "signer": "fixed",
                "subject_name": "fixed",
                "subject_digest": "sha256:" + "a" * 64,
                "signature_verified": True,
                "attestation_verified": True,
            },
        ):
            with self.subTest(remote=remote), self.assertRaises(GateError):
                verify_remote_fixture(remote)

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

    def test_publication_workflow_and_write_permissions_fail(self) -> None:
        paths = (
            ".github/workflows/ci.yml",
            "Dockerfile.p10",
            "studio/Dockerfile.p10",
            "compose.p10.yaml",
            "distribution/p10/release-manifest.template.json",
            "distribution/p10/verification-policy.json",
        )
        with tempfile.TemporaryDirectory(prefix="dc-p10-workflow-") as name:
            for label, marker in (
                ("push", "\n# docker push forbidden\n"),
                ("packages", "\n# packages: write\n"),
                ("upload", "\n# uses: actions/upload-artifact@fixed\n"),
            ):
                root = copy_paths(Path(name) / label, *paths)
                workflow = root / ".github/workflows/ci.yml"
                workflow.write_text(workflow.read_text(encoding="utf-8") + marker, encoding="utf-8")
                with self.subTest(label=label), self.assertRaisesRegex(GateError, "publication"):
                    check_distribution(root)


if __name__ == "__main__":
    unittest.main()
