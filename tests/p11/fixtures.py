# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from digital_colleagues.adapters.package.github_attestation import (
    UnavailableGitHubAttestationVerifier,
)
from digital_colleagues.adapters.sqlite.p11_store import SQLiteP11Store
from digital_colleagues.adapters.system.deterministic import FixedClock, StableHashIdentifier
from digital_colleagues.application.p4_contracts import AuthenticatedSession
from digital_colleagues.application.p6_services import P6AuthenticationService
from digital_colleagues.application.p11_contracts import PackageRegistrationRequest
from digital_colleagues.application.p11_ports import GitHubAttestationVerificationPort
from digital_colleagues.application.p11_services import (
    P11DeploymentService,
    P11PackageService,
)
from digital_colleagues.core.agent_package import PackageSource
from digital_colleagues.core.deployment import PackageRecord
from digital_colleagues.local.security import CredentialDigests
from tests.p4.fixtures import SequenceTokens

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 9, 9, 8, 30, tzinfo=UTC)


def valid_package(
    *,
    package_id: str = "fixture-agent",
    version: str = "1.0.0",
    capabilities: tuple[str, ...] = ("notify_human",),
    steps: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    content: dict[str, object] = {
        "prompts": {"en-US": "Perform finite work.", "zh-TW": "執行有限工作。"},
        "requested_capabilities": list(capabilities),
        "workflow": {
            "entrypoint": "done" if steps is None else str(steps[0]["id"]),
            "steps": [{"id": "done", "type": "complete"}] if steps is None else steps,
        },
    }
    content_digest = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(content, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
    )
    return {
        "schema": "dc-agent/v1",
        "schema_version": 1,
        "metadata": {
            "package_id": package_id,
            "version": version,
            "runtime_api": "1",
            "display": {
                "en-US": {"name": "Fixture Agent", "summary": "Synthetic package."},
                "zh-TW": {"name": "測試 Agent", "summary": "合成測試套件。"},
            },
        },
        "content": content,
        "content_digest": content_digest,
    }


def package_archive(
    package: dict[str, object] | None = None,
    *,
    member: str = "agent.json",
    compression: int = zipfile.ZIP_STORED,
    extras: tuple[tuple[str, bytes], ...] = (),
) -> bytes:
    output = io.BytesIO()
    manifest = valid_package() if package is None else package
    encoded = json.dumps(
        manifest,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    with zipfile.ZipFile(output, "w", compression=compression) as archive:
        archive.writestr(member, encoded)
        for name, value in extras:
            archive.writestr(name, value)
    return output.getvalue()


def digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


@dataclass(slots=True)
class Harness:
    store: SQLiteP11Store
    clock: FixedClock
    authentication: P6AuthenticationService
    packages: P11PackageService
    deployments: P11DeploymentService
    session: AuthenticatedSession
    credential: str
    csrf: str


def build_harness(
    database: Path,
    *,
    attestation: GitHubAttestationVerificationPort | None = None,
) -> Harness:
    clock = FixedClock(NOW)
    store = SQLiteP11Store(database, migrations_path=ROOT / "migrations", clock=clock)
    tokens = SequenceTokens([])
    digests = CredentialDigests()
    identifiers = StableHashIdentifier("p11-fixture")
    authentication = P6AuthenticationService(
        store=store,
        clock=clock,
        tokens=tokens,
        digests=digests,
        identifiers=identifiers,
        tenant_id="tenant-local",
    )
    _, plaintext = authentication.ensure_bootstrap()
    assert plaintext is not None
    authentication.claim_operator_retrieval(plaintext)
    grant = authentication.exchange(plaintext)
    packages = P11PackageService(
        store=store,
        authentication=authentication,
        attestation=attestation or UnavailableGitHubAttestationVerifier(),
        clock=clock,
        identifiers=identifiers,
    )
    deployments = P11DeploymentService(
        store=store,
        authentication=authentication,
        clock=clock,
        identifiers=identifiers,
    )
    return Harness(
        store,
        clock,
        authentication,
        packages,
        deployments,
        grant.session,
        grant.session_credential,
        grant.csrf_token,
    )


def register_ready(
    harness: Harness,
    *,
    package_id: str = "fixture-agent",
    version: str = "1.0.0",
) -> PackageRecord:
    archive = package_archive(valid_package(package_id=package_id, version=version))
    record = harness.packages.register(
        session=harness.session,
        request=PackageRegistrationRequest(
            archive=archive,
            source=PackageSource.LOCAL,
            expected_archive_digest=digest(archive),
        ),
        idempotency_key=f"register-{package_id}-{version.replace('.', '-')}",
    )
    record = harness.packages.trust(
        session=harness.session,
        package_id=package_id,
        version=version,
        digest=record.package_digest,
        expected_revision=record.revision,
        idempotency_key=f"trust-{package_id}-{version.replace('.', '-')}",
    )
    return harness.packages.install(
        session=harness.session,
        package_id=package_id,
        version=version,
        digest=record.package_digest,
        expected_revision=record.revision,
        idempotency_key=f"install-{package_id}-{version.replace('.', '-')}",
    )
