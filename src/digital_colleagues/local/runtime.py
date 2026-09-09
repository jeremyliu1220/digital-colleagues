# SPDX-License-Identifier: Apache-2.0

"""Composition root for the local P4 API, worker, and operator commands."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from digital_colleagues import API_TITLE, __version__
from digital_colleagues.adapters.package.github_attestation import (
    GitHubCliAttestationVerifier,
    UnavailableGitHubAttestationVerifier,
)
from digital_colleagues.adapters.sqlite.p11_store import SQLiteP11Store
from digital_colleagues.adapters.system.deterministic import StableHashIdentifier
from digital_colleagues.application.p4_services import (
    GovernedObservedIntelligence,
    InitialColleagueService,
    P4EvaluationService,
    P4RuntimeController,
)
from digital_colleagues.application.p5_services import (
    P5DispatchAuthorizer,
    P5RuntimeController,
    PolicyGovernedIntelligence,
    RevisionedColleagueBuilderService,
)
from digital_colleagues.application.p6_services import (
    P6AuditService,
    P6AuthenticationService,
    P6BuilderService,
    P6ChangeService,
    P6ColleagueService,
    P6DispatchAuthorizer,
    P6RuntimeController,
)
from digital_colleagues.application.p11_ports import GitHubAttestationVerificationPort
from digital_colleagues.application.p11_services import (
    P11DeploymentService,
    P11PackageService,
    P11RuntimeController,
)
from digital_colleagues.local.p7_adapters import build_selected_adapters
from digital_colleagues.local.security import (
    CredentialDigests,
    SecureTokenSource,
    UtcClock,
)


@dataclass(slots=True)
class LocalRuntime:
    state_directory: Path
    store: SQLiteP11Store
    clock: UtcClock
    digests: CredentialDigests
    authentication: P6AuthenticationService
    colleagues: P6ColleagueService
    builder: P6BuilderService
    controller: P11RuntimeController
    changes: P6ChangeService
    audit: P6AuditService
    packages: P11PackageService
    deployments: P11DeploymentService
    model_adapter_mode: str
    channel_adapter_mode: str

    def close(self) -> None:
        self.store.close()


def build_local_runtime(
    state_directory: Path,
    *,
    adapter_environment: Mapping[str, str] | None = None,
) -> LocalRuntime:
    # Fully parse adapter configuration and read credentials before creating a
    # state directory, opening SQLite, running migrations, or constructing services.
    intelligence, channel, selection = build_selected_adapters(adapter_environment or {})
    state_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    clock = UtcClock()
    store = SQLiteP11Store(
        state_directory / "state.sqlite",
        migrations_path=Path(__file__).resolve().parents[3] / "migrations",
        clock=clock,
    )
    try:
        digests = CredentialDigests()
        tokens = SecureTokenSource()
        identifiers = StableHashIdentifier("p4-local")
        authentication = P6AuthenticationService(
            store=store,
            clock=clock,
            tokens=tokens,
            digests=digests,
            identifiers=identifiers,
            tenant_id="tenant-local",
        )
        inner_colleagues = InitialColleagueService(
            store=store,
            runtime_store=store,
            identifiers=identifiers,
            clock=clock,
        )
        colleagues = P6ColleagueService(
            inner=inner_colleagues,
            authentication=authentication,
        )
        inner_builder = RevisionedColleagueBuilderService(
            store=store,
            clock=clock,
            identifiers=identifiers,
        )
        builder = P6BuilderService(inner=inner_builder, authentication=authentication)
        governed = GovernedObservedIntelligence(
            inner=intelligence,
            store=store,
            identifiers=identifiers,
        )
        inner_controller = P4RuntimeController(
            store=store,
            studio_store=store,
            intelligence=PolicyGovernedIntelligence(
                inner=governed,
                store=store,
                identifiers=identifiers,
                digests=digests,
            ),
            channel=channel,
            clock=clock,
            identifiers=identifiers,
            digests=digests,
            dispatch_authorizer=P6DispatchAuthorizer(
                p5=P5DispatchAuthorizer(store),
                store=store,
                clock=clock,
            ),
        )
        policy_controller = P5RuntimeController(
            inner=inner_controller,
            store=store,
            clock=clock,
            identifiers=identifiers,
        )
        p6_controller = P6RuntimeController(
            inner=policy_controller,
            authentication=authentication,
        )
        controller = P11RuntimeController(inner=p6_controller, store=store)
        changes = P6ChangeService(
            store=store,
            draft_store=store,
            builder=inner_builder,
            authentication=authentication,
            clock=clock,
            identifiers=identifiers,
            digests=digests,
        )
        audit = P6AuditService(
            store=store,
            authentication=authentication,
            clock=clock,
            identifiers=identifiers,
        )
        executable = (adapter_environment or {}).get("DC_GH_ATTESTATION_BINARY")
        trusted_root_file = (adapter_environment or {}).get("DC_GH_TRUSTED_ROOT_FILE")
        attestation: GitHubAttestationVerificationPort
        if executable is not None and trusted_root_file is not None:
            try:
                trusted_root = Path(trusted_root_file).read_bytes()
            except OSError as exc:
                raise ValueError("configured GitHub trusted root is unavailable") from exc
            attestation = GitHubCliAttestationVerifier(
                executable=executable,
                trusted_root=trusted_root,
                clock=clock.now,
            )
        else:
            attestation = UnavailableGitHubAttestationVerifier()
        packages = P11PackageService(
            store=store,
            authentication=authentication,
            attestation=attestation,
            clock=clock,
            identifiers=identifiers,
        )
        deployments = P11DeploymentService(
            store=store,
            authentication=authentication,
            clock=clock,
            identifiers=identifiers,
        )
    except Exception:
        store.close()
        raise
    return LocalRuntime(
        state_directory=state_directory,
        store=store,
        clock=clock,
        digests=digests,
        authentication=authentication,
        colleagues=colleagues,
        builder=builder,
        controller=controller,
        changes=changes,
        audit=audit,
        packages=packages,
        deployments=deployments,
        model_adapter_mode=selection.model_mode.value,
        channel_adapter_mode=selection.channel_mode.value,
    )


def build_app_from_environment() -> object:
    # Keep the headless runtime constructor importable without the HTTP edge.
    from digital_colleagues.api.p4_app import create_p4_app
    from digital_colleagues.api.p5_app import install_p5_routes
    from digital_colleagues.api.p6_app import install_p6_routes
    from digital_colleagues.api.p11_app import install_p11_routes

    state_directory = Path(os.environ.get("DC_STATE_DIR", "/state"))
    expected_origin = os.environ.get("DC_EXPECTED_ORIGIN", "http://127.0.0.1:4173")
    secure_cookie = os.environ.get("DC_SECURE_COOKIE", "0") == "1"
    runtime = build_local_runtime(state_directory, adapter_environment=os.environ)
    app = create_p4_app(
        authentication=runtime.authentication,
        colleagues=runtime.colleagues,  # type: ignore[arg-type]
        runtime=runtime.controller,  # type: ignore[arg-type]
        store=runtime.store,
        studio_store=runtime.store,
        expected_origin=expected_origin,
        secure_cookie=secure_cookie,
    )
    app.title = API_TITLE
    app.version = __version__
    install_p5_routes(
        app,
        authentication=runtime.authentication,
        builder=runtime.builder,  # type: ignore[arg-type]
        p5_store=runtime.store,
        expected_origin=expected_origin,
        evaluation=P4EvaluationService(runtime.store),
    )
    install_p6_routes(
        app,
        authentication=runtime.authentication,
        changes=runtime.changes,
        audit=runtime.audit,
        store=runtime.store,
        expected_origin=expected_origin,
        secure_cookie=secure_cookie,
    )
    install_p11_routes(
        app,
        authentication=runtime.authentication,
        packages=runtime.packages,
        deployments=runtime.deployments,
        expected_origin=expected_origin,
    )
    app.state.local_runtime = runtime
    return app
