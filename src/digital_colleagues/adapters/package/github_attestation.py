# SPDX-License-Identifier: Apache-2.0

"""Offline, policy-bound GitHub CLI artifact-attestation verification adapter."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from digital_colleagues.application.errors import ValidationError
from digital_colleagues.application.p11_contracts import GitHubAttestationPolicy
from digital_colleagues.core.agent_package import sha256_digest
from digital_colleagues.core.deployment import (
    AttestationVerification,
    GitHubAttestation,
)

PREDICATE_TYPE: Final = "https://slsa.dev/provenance/v1"
GITHUB_ISSUER: Final = "https://token.actions.githubusercontent.com"
ATTESTATION_OUTPUT_MAX_BYTES: Final = 262_144
ATTESTATION_INPUT_MAX_BYTES: Final = 262_144

Runner = Callable[..., subprocess.CompletedProcess[bytes]]


class UnavailableGitHubAttestationVerifier:
    """Fail closed when an operator has not configured offline verification."""

    def verify(self, **_: object) -> GitHubAttestation:
        raise ValidationError("GitHub attestation verification is unavailable")


class GitHubCliAttestationVerifier:
    """Invoke only `gh attestation verify` with an offline bundle and trusted root."""

    def __init__(
        self,
        *,
        executable: str,
        trusted_root: bytes,
        clock: Callable[[], datetime] | None = None,
        runner: Runner = subprocess.run,
        timeout_seconds: int = 20,
    ) -> None:
        if not executable or any(character in executable for character in "\x00\r\n"):
            raise ValueError("GitHub CLI executable configuration is invalid")
        if not trusted_root or len(trusted_root) > ATTESTATION_INPUT_MAX_BYTES:
            raise ValueError("trusted root is empty or exceeds the fixed bound")
        if not 1 <= timeout_seconds <= 60:
            raise ValueError("attestation timeout is outside the fixed bound")
        self._executable = executable
        self._trusted_root = bytes(trusted_root)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._runner = runner
        self._timeout = timeout_seconds

    @staticmethod
    def _field(value: Mapping[str, object], field: str) -> str:
        candidate = value.get(field)
        if not isinstance(candidate, str) or not candidate or len(candidate) > 512:
            raise ValidationError("attestation result is malformed")
        return candidate

    @staticmethod
    def _object(value: Mapping[str, object], field: str) -> Mapping[str, object]:
        candidate = value.get(field)
        if not isinstance(candidate, dict):
            raise ValidationError("attestation result is malformed")
        return candidate

    @classmethod
    def _verified_result(
        cls,
        stdout: bytes,
        *,
        artifact_digest: str,
        policy: GitHubAttestationPolicy,
    ) -> Mapping[str, object]:
        if not stdout or len(stdout) > ATTESTATION_OUTPUT_MAX_BYTES:
            raise ValidationError("attestation result is empty or exceeds the fixed bound")
        try:
            decoded = json.loads(stdout.decode("utf-8", errors="strict"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValidationError("attestation result is malformed") from exc
        if not isinstance(decoded, list) or len(decoded) != 1 or not isinstance(decoded[0], dict):
            raise ValidationError("attestation result does not contain one exact subject")
        result = decoded[0]
        verification = cls._object(result, "verificationResult")
        signature = cls._object(verification, "signature")
        certificate = cls._object(signature, "certificate")
        statement = cls._object(verification, "statement")
        timestamps = verification.get("verifiedTimestamps")
        subjects = statement.get("subject")
        if (
            not isinstance(timestamps, list)
            or not timestamps
            or not isinstance(subjects, list)
            or len(subjects) != 1
            or not isinstance(subjects[0], dict)
        ):
            raise ValidationError("attestation result lacks verified time or exact subject")
        subject = subjects[0]
        subject_digest = cls._object(subject, "digest")
        if subject_digest.get("sha256") != artifact_digest.removeprefix("sha256:"):
            raise ValidationError("attestation result does not bind the exact artifact")
        expected = {
            "issuer": GITHUB_ISSUER,
            "githubWorkflowRepository": policy.repository,
            "buildSignerURI": policy.signer_workflow,
            "buildSignerDigest": policy.signer_digest,
            "sourceRepositoryRef": policy.source_ref,
            "sourceRepositoryDigest": policy.source_digest,
            "buildConfigURI": policy.build_identity,
            "runnerEnvironment": "github-hosted",
        }
        for field, wanted in expected.items():
            if cls._field(certificate, field) != wanted:
                raise ValidationError("attestation result does not match operator policy")
        if cls._field(statement, "predicateType") != PREDICATE_TYPE:
            raise ValidationError("attestation predicate does not match operator policy")
        return certificate

    def verify(
        self,
        *,
        artifact: bytes,
        artifact_digest: str,
        bundle: bytes,
        policy: GitHubAttestationPolicy,
    ) -> GitHubAttestation:
        if (
            not artifact
            or len(artifact) > ATTESTATION_INPUT_MAX_BYTES
            or not bundle
            or len(bundle) > ATTESTATION_INPUT_MAX_BYTES
            or sha256_digest(artifact) != artifact_digest
        ):
            raise ValidationError("attestation inputs are empty or exceed fixed bounds")
        with tempfile.TemporaryDirectory(prefix="dc-p11-attestation-") as temporary:
            root = Path(temporary)
            artifact_path = root / "artifact.zip"
            bundle_path = root / "bundle.json"
            trusted_root_path = root / "trusted-root.json"
            artifact_path.write_bytes(artifact)
            bundle_path.write_bytes(bundle)
            trusted_root_path.write_bytes(self._trusted_root)
            command: Sequence[str] = (
                self._executable,
                "attestation",
                "verify",
                str(artifact_path),
                "--repo",
                policy.repository,
                "--signer-repo",
                policy.repository,
                "--bundle",
                str(bundle_path),
                "--custom-trusted-root",
                str(trusted_root_path),
                "--signer-workflow",
                policy.signer_workflow,
                "--signer-digest",
                policy.signer_digest,
                "--source-ref",
                policy.source_ref,
                "--source-digest",
                policy.source_digest,
                "--predicate-type",
                PREDICATE_TYPE,
                "--cert-oidc-issuer",
                GITHUB_ISSUER,
                "--deny-self-hosted-runners",
                "--format",
                "json",
            )
            try:
                completed = self._runner(
                    command,
                    input=b"",
                    capture_output=True,
                    timeout=self._timeout,
                    check=False,
                    env={"PATH": os.environ.get("PATH", ""), "NO_COLOR": "1"},
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise ValidationError("GitHub attestation verification failed") from exc
        if completed.returncode != 0:
            raise ValidationError("GitHub attestation verification failed")
        result = self._verified_result(
            completed.stdout,
            artifact_digest=artifact_digest,
            policy=policy,
        )
        return GitHubAttestation(
            verification=AttestationVerification.VERIFIED,
            artifact_digest=artifact_digest,
            signer=self._field(result, "buildSignerURI"),
            repository=policy.repository,
            workflow=policy.signer_workflow,
            build_identity=policy.build_identity,
            source_ref=policy.source_ref,
            source_digest=policy.source_digest,
            predicate_type=PREDICATE_TYPE,
            verified_at=self._clock(),
        )
