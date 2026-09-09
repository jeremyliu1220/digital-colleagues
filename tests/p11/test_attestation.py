# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import subprocess
import unittest
from collections.abc import Mapping, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

from digital_colleagues.adapters.package.github_attestation import (
    GITHUB_ISSUER,
    PREDICATE_TYPE,
    GitHubCliAttestationVerifier,
    UnavailableGitHubAttestationVerifier,
)
from digital_colleagues.application.errors import ValidationError
from digital_colleagues.application.p11_contracts import (
    GitHubAttestationPolicy,
    PackageRegistrationRequest,
)
from digital_colleagues.core.agent_package import PackageSource
from digital_colleagues.core.deployment import PackageTrustState
from tests.p11.fixtures import NOW, build_harness, digest, package_archive

ARTIFACT = b"archive"
DIGEST = digest(ARTIFACT)
SOURCE_DIGEST = "sha256:" + "2" * 64
SIGNER_DIGEST = "sha256:" + "3" * 64


def policy() -> GitHubAttestationPolicy:
    return GitHubAttestationPolicy(
        repository="example/digital-colleague-package",
        signer_workflow="example/digital-colleague-package/.github/workflows/release.yml",
        signer_digest=SIGNER_DIGEST,
        source_ref="refs/tags/v1.0.0",
        source_digest=SOURCE_DIGEST,
        build_identity="release.yml@refs/tags/v1.0.0",
    )


def result(*, artifact_digest: str = DIGEST, **updates: object) -> bytes:
    certificate: dict[str, object] = {
        "issuer": GITHUB_ISSUER,
        "githubWorkflowRepository": policy().repository,
        "buildSignerURI": policy().signer_workflow,
        "buildSignerDigest": SIGNER_DIGEST,
        "sourceRepositoryRef": policy().source_ref,
        "sourceRepositoryDigest": SOURCE_DIGEST,
        "buildConfigURI": policy().build_identity,
        "runnerEnvironment": "github-hosted",
    }
    certificate.update(updates)
    value: dict[str, object] = {
        "attestation": {"bundle": "synthetic-offline"},
        "verificationResult": {
            "signature": {"certificate": certificate},
            "verifiedTimestamps": [
                {"type": "transparency-log", "timestamp": "2026-09-09T08:30:00Z"}
            ],
            "statement": {
                "subject": [
                    {
                        "name": "artifact.zip",
                        "digest": {"sha256": artifact_digest.removeprefix("sha256:")},
                    }
                ],
                "predicateType": PREDICATE_TYPE,
                "predicate": {"buildType": "synthetic-offline"},
            },
        },
    }
    return json.dumps([value]).encode()


class AttestationTests(unittest.TestCase):
    def verifier(
        self, stdout: bytes = result(), returncode: int = 0
    ) -> GitHubCliAttestationVerifier:
        def runner(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            self.assertIn("--deny-self-hosted-runners", command)
            self.assertIn("--custom-trusted-root", command)
            self.assertIn("--signer-repo", command)
            self.assertIn("--source-digest", command)
            environment = kwargs["env"]
            self.assertIsInstance(environment, Mapping)
            assert isinstance(environment, Mapping)
            self.assertEqual(set(environment), {"PATH", "NO_COLOR"})
            return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=b"")

        return GitHubCliAttestationVerifier(
            executable="gh",
            trusted_root=b"{}",
            clock=lambda: NOW,
            runner=runner,
        )

    def test_policy_bound_offline_verification_succeeds(self) -> None:
        verified = self.verifier().verify(
            artifact=ARTIFACT, artifact_digest=DIGEST, bundle=b"{}", policy=policy()
        )
        self.assertEqual(verified.artifact_digest, DIGEST)

    def test_wrong_subject_digest_fails_closed(self) -> None:
        with self.assertRaises(ValidationError):
            self.verifier(result(artifact_digest="sha256:" + "9" * 64)).verify(
                artifact=ARTIFACT, artifact_digest=DIGEST, bundle=b"{}", policy=policy()
            )

    def test_caller_digest_must_bind_the_exact_artifact_bytes(self) -> None:
        with self.assertRaises(ValidationError):
            self.verifier().verify(
                artifact=ARTIFACT,
                artifact_digest="sha256:" + "9" * 64,
                bundle=b"{}",
                policy=policy(),
            )

    def test_wrong_certificate_policy_fields_fail_closed(self) -> None:
        fields = (
            "githubWorkflowRepository",
            "buildSignerURI",
            "buildSignerDigest",
            "sourceRepositoryRef",
            "sourceRepositoryDigest",
            "buildConfigURI",
            "issuer",
        )
        for field in fields:
            with self.subTest(field=field), self.assertRaises(ValidationError):
                self.verifier(result(**{field: "wrong"})).verify(
                    artifact=ARTIFACT,
                    artifact_digest=DIGEST,
                    bundle=b"{}",
                    policy=policy(),
                )

    def test_self_hosted_attestation_fails_closed(self) -> None:
        with self.assertRaises(ValidationError):
            self.verifier(result(runnerEnvironment="self-hosted")).verify(
                artifact=ARTIFACT, artifact_digest=DIGEST, bundle=b"{}", policy=policy()
            )

    def test_malformed_output_fails_closed(self) -> None:
        with self.assertRaises(ValidationError):
            self.verifier(b"not-json").verify(
                artifact=ARTIFACT, artifact_digest=DIGEST, bundle=b"{}", policy=policy()
            )

    def test_nonzero_cli_exit_fails_closed(self) -> None:
        with self.assertRaises(ValidationError):
            self.verifier(returncode=1).verify(
                artifact=ARTIFACT, artifact_digest=DIGEST, bundle=b"{}", policy=policy()
            )

    def test_cli_timeout_fails_closed(self) -> None:
        def timeout_runner(
            command: Sequence[str], **kwargs: object
        ) -> subprocess.CompletedProcess[bytes]:
            del command, kwargs
            raise subprocess.TimeoutExpired("gh", 20)

        verifier = GitHubCliAttestationVerifier(
            executable="gh", trusted_root=b"{}", clock=lambda: NOW, runner=timeout_runner
        )
        with self.assertRaises(ValidationError):
            verifier.verify(
                artifact=ARTIFACT, artifact_digest=DIGEST, bundle=b"{}", policy=policy()
            )

    def test_unavailable_verifier_never_downgrades(self) -> None:
        with self.assertRaises(ValidationError):
            UnavailableGitHubAttestationVerifier().verify()

    def test_non_github_source_rejects_partial_attestation_configuration(self) -> None:
        archive = package_archive()
        with self.assertRaises(ValueError):
            PackageRegistrationRequest(
                archive=archive,
                source=PackageSource.LOCAL,
                expected_archive_digest=digest(archive),
                attestation_bundle=b"{}",
            )

    def test_verified_attestation_does_not_create_trust(self) -> None:
        archive = package_archive()
        verifier = self.verifier(result(artifact_digest=digest(archive)))
        with TemporaryDirectory() as value:
            harness = build_harness(Path(value) / "attestation.sqlite", attestation=verifier)
            try:
                record = harness.packages.register(
                    session=harness.session,
                    request=PackageRegistrationRequest(
                        archive=archive,
                        source=PackageSource.GITHUB_RELEASE,
                        expected_archive_digest=digest(archive),
                        attestation_bundle=b"{}",
                        github_policy=policy(),
                    ),
                    idempotency_key="github-registration",
                )
                self.assertIsNotNone(record.attestation)
                self.assertEqual(record.trust_state, PackageTrustState.UNTRUSTED)
            finally:
                harness.store.close()

    def test_registration_replay_does_not_repeat_external_verification(self) -> None:
        archive = package_archive()
        calls: list[Sequence[str]] = []

        def runner(command: Sequence[str], **_: object) -> subprocess.CompletedProcess[bytes]:
            calls.append(command)
            return subprocess.CompletedProcess(
                [],
                0,
                stdout=result(artifact_digest=digest(archive)),
                stderr=b"",
            )

        verifier = GitHubCliAttestationVerifier(
            executable="gh",
            trusted_root=b"{}",
            clock=lambda: NOW,
            runner=runner,
        )
        with TemporaryDirectory() as value:
            harness = build_harness(Path(value) / "replay.sqlite", attestation=verifier)
            try:
                request = PackageRegistrationRequest(
                    archive=archive,
                    source=PackageSource.GITHUB_RELEASE,
                    expected_archive_digest=digest(archive),
                    attestation_bundle=b"{}",
                    github_policy=policy(),
                )
                first = harness.packages.register(
                    session=harness.session,
                    request=request,
                    idempotency_key="github-replay",
                )
                second = harness.packages.register(
                    session=harness.session,
                    request=request,
                    idempotency_key="github-replay",
                )
                self.assertEqual(first, second)
                self.assertEqual(len(calls), 1)
            finally:
                harness.store.close()


if __name__ == "__main__":
    unittest.main()
