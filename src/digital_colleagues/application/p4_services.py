# SPDX-License-Identifier: Apache-2.0

"""P4 application services for local authentication and the initial Studio path."""

from __future__ import annotations

from datetime import timedelta

from digital_colleagues.application.contracts import (
    ApprovalRequest,
    InputEventRequest,
    RequestPrincipalContext,
    TimerScheduleRequest,
)
from digital_colleagues.application.errors import (
    ConflictError,
    PermissionDeniedError,
    ValidationError,
)
from digital_colleagues.application.p4_contracts import (
    AuthenticatedSession,
    BootstrapRecord,
    InitialColleagueRequest,
    MetricResult,
    MutationReplay,
    SessionGrant,
    WorkAssignmentRequest,
)
from digital_colleagues.application.p4_ports import (
    AuthenticationPersistencePort,
    CredentialDigestPort,
    SecretTokenPort,
    StudioPersistencePort,
)
from digital_colleagues.application.ports import (
    ClockPort,
    IdentifierPort,
    IntelligencePort,
    PersistencePort,
    ReferenceChannelPort,
    RuntimePersistencePort,
)
from digital_colleagues.application.services import (
    ApprovalService,
    DispatchService,
    EventService,
    TimerService,
    WakeService,
)
from digital_colleagues.core.authority import (
    CapabilityGrant,
    Constraint,
    EffectBoundary,
    EffectKind,
    Mandate,
    Profile,
    ResponsibilityDefinition,
)
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.effects import ApprovalChoice, EffectProposal, HumanApprovalDecision
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import HumanRole, Principal, PrincipalKind
from digital_colleagues.core.work import FiniteWork, WorkState
from digital_colleagues.governance.approvals import require_authoritative_human_role


class AuthenticationService:
    """Issue and consume strong local credentials without making them request authority."""

    def __init__(
        self,
        *,
        store: AuthenticationPersistencePort,
        clock: ClockPort,
        tokens: SecretTokenPort,
        digests: CredentialDigestPort,
        tenant_id: str,
        bootstrap_validity: timedelta = timedelta(minutes=10),
        session_validity: timedelta = timedelta(hours=8),
    ) -> None:
        if bootstrap_validity <= timedelta(0) or bootstrap_validity > timedelta(minutes=10):
            raise ValidationError("bootstrap validity must be positive and at most ten minutes")
        if session_validity <= timedelta(0):
            raise ValidationError("session validity must be positive")
        self._store = store
        self._clock = clock
        self._tokens = tokens
        self._digests = digests
        self._tenant_id = tenant_id
        self._bootstrap_validity = bootstrap_validity
        self._session_validity = session_validity

    def ensure_bootstrap(self) -> tuple[BootstrapRecord, str | None]:
        existing = self._store.get_bootstrap(self._tenant_id)
        if existing is not None:
            return existing, None
        now = self._clock.now()
        plaintext = self._tokens.issue(32)
        record = BootstrapRecord(
            tenant_id=self._tenant_id,
            credential_id="bootstrap-initial",
            token_digest=self._digests.digest("bootstrap", plaintext),
            issued_at=now,
            expires_at=now + self._bootstrap_validity,
            retrieved_at=None,
            consumed_at=None,
            revision=1,
        )
        if not self._store.create_bootstrap(record):
            resolved = self._store.get_bootstrap(self._tenant_id)
            if resolved is None:
                raise ConflictError("bootstrap issuance raced without durable state")
            return resolved, None
        return record, plaintext

    def claim_operator_retrieval(self, plaintext: str) -> BootstrapRecord:
        if not plaintext:
            raise ValidationError("bootstrap token is required")
        return self._store.claim_bootstrap_retrieval(
            tenant_id=self._tenant_id,
            token_digest=self._digests.digest("bootstrap", plaintext),
            occurred_at=self._clock.now(),
        )

    def exchange(self, plaintext: str) -> SessionGrant:
        if not plaintext:
            raise PermissionDeniedError("bootstrap exchange was refused")
        now = self._clock.now()
        bootstrap_digest = self._digests.digest("bootstrap", plaintext)
        session_credential = self._tokens.issue(32)
        csrf_token = self._digests.digest("csrf-token", session_credential).removeprefix("sha256:")
        session_digest = self._digests.digest("session", session_credential)
        principal_id = "human:" + bootstrap_digest.removeprefix("sha256:")[:32]
        session_id = "session:" + session_digest.removeprefix("sha256:")[:32]
        principal = Principal.human(
            tenant_id=self._tenant_id,
            principal_id=principal_id,
            roles=(HumanRole.TENANT_ADMIN,),
        )
        session = AuthenticatedSession(
            tenant_id=self._tenant_id,
            session_id=session_id,
            principal=principal,
            credential_digest=session_digest,
            csrf_digest=self._digests.digest("csrf-storage", csrf_token),
            created_at=now,
            expires_at=now + self._session_validity,
        )
        stored = self._store.consume_bootstrap(
            tenant_id=self._tenant_id,
            token_digest=bootstrap_digest,
            principal=principal,
            session=session,
            occurred_at=now,
        )
        return SessionGrant(stored, session_credential, csrf_token)

    def resolve(self, session_credential: str) -> AuthenticatedSession:
        if not session_credential:
            raise PermissionDeniedError("authenticated session is required")
        return self._store.get_session(
            credential_digest=self._digests.digest("session", session_credential),
            evaluated_at=self._clock.now(),
        )

    def csrf_for(self, session_credential: str) -> str:
        self.resolve(session_credential)
        return self._digests.digest("csrf-token", session_credential).removeprefix("sha256:")

    def authorize_mutation(
        self,
        *,
        session_credential: str,
        origin: str | None,
        csrf_token: str | None,
        expected_origin: str,
    ) -> AuthenticatedSession:
        session = self.resolve(session_credential)
        if origin != expected_origin:
            raise PermissionDeniedError("mutation Origin was refused")
        if csrf_token is None:
            raise PermissionDeniedError("mutation CSRF defense was refused")
        actual = self._digests.digest("csrf-storage", csrf_token)
        if not self._digests.matches(session.csrf_digest, actual):
            raise PermissionDeniedError("mutation CSRF defense was refused")
        require_authoritative_human_role(
            session.principal,
            accepted_roles=frozenset({HumanRole.TENANT_ADMIN}),
        )
        return session

    def bind_colleague(
        self, session: AuthenticatedSession, colleague_id: str
    ) -> AuthenticatedSession:
        if session.principal.kind is not PrincipalKind.HUMAN:
            raise PermissionDeniedError("colleague binding requires a human principal")
        require_authoritative_human_role(
            session.principal,
            accepted_roles=frozenset({HumanRole.TENANT_ADMIN}),
        )
        return self._store.set_active_colleague(
            session=session,
            colleague_id=colleague_id,
            occurred_at=self._clock.now(),
        )

    def mutation_replay(
        self,
        *,
        session: AuthenticatedSession,
        action: str,
        idempotency_key: str,
        request_binding: str,
    ) -> tuple[FrozenJsonObject | None, str]:
        request_digest = self._digests.digest(f"mutation:{action}", request_binding)
        replay = self._store.get_mutation_replay(
            session=session,
            action=action,
            idempotency_key=idempotency_key,
        )
        if replay is None:
            return None, request_digest
        if not self._digests.matches(replay.request_digest, request_digest):
            raise ConflictError("mutation idempotency key was rebound")
        return replay.result, request_digest

    def record_mutation(
        self,
        *,
        session: AuthenticatedSession,
        action: str,
        idempotency_key: str,
        request_digest: str,
        result: dict[str, object],
    ) -> None:
        self._store.record_mutation_replay(
            session=session,
            action=action,
            idempotency_key=idempotency_key,
            replay=MutationReplay(request_digest, FrozenJsonObject.from_mapping(result)),
            occurred_at=self._clock.now(),
        )


class InitialColleagueService:
    def __init__(
        self,
        *,
        store: StudioPersistencePort,
        runtime_store: PersistencePort,
        identifiers: IdentifierPort,
        clock: ClockPort,
    ) -> None:
        self._store = store
        self._runtime_store = runtime_store
        self._identifiers = identifiers
        self._clock = clock

    @staticmethod
    def _require_admin(session: AuthenticatedSession) -> None:
        if session.principal.kind is not PrincipalKind.HUMAN:
            raise PermissionDeniedError("initial colleague mutation requires a human")
        require_authoritative_human_role(
            session.principal,
            accepted_roles=frozenset({HumanRole.TENANT_ADMIN}),
        )

    def create(
        self, *, session: AuthenticatedSession, request: InitialColleagueRequest
    ) -> tuple[Profile, Mandate, tuple[Principal, Principal]]:
        self._require_admin(session)
        if session.active_colleague_id is not None:
            raise ConflictError("P4 supports only the initial colleague creation flow")
        colleague_id = self._identifiers.derive(
            "colleague", session.principal.principal_id, request.idempotency_key
        )
        namespace = Namespace.colleague(session.tenant_id, colleague_id)
        now = self._clock.now()
        correlation_id = self._identifiers.derive("correlation", colleague_id, "initial")
        responsibilities = tuple(
            ResponsibilityDefinition(
                responsibility_id=self._identifiers.derive(
                    "responsibility", colleague_id, str(index)
                ),
                description=description,
                obligations=("Advance the explicitly assigned finite work.",),
                completion_conditions=("A typed reference ActionResult is recorded.",),
            )
            for index, description in enumerate(request.responsibilities, start=1)
        )
        capabilities = tuple(
            CapabilityGrant(
                capability_id=self._identifiers.derive("capability", colleague_id, str(index)),
                description=description,
            )
            for index, description in enumerate(request.capabilities, start=1)
        )
        constraints = tuple(
            Constraint(
                constraint_id=self._identifiers.derive("constraint", colleague_id, str(index)),
                description=description,
            )
            for index, description in enumerate(request.constraints, start=1)
        )
        boundary = EffectBoundary(
            boundary_id=self._identifiers.derive("boundary", colleague_id, "initial"),
            effect_kind=EffectKind(request.effect_kind),
            allowed_destination_kinds=(request.destination_kind,),
            allowed_actions=(request.action,),
            constraints=request.effect_constraints,
            human_approval_required=True,
        )
        profile = Profile(
            namespace=namespace,
            profile_id=self._identifiers.derive("profile", colleague_id),
            display_name=request.display_name,
            description=request.role_description,
            presentation=FrozenJsonObject.from_mapping(
                {
                    "working_style": request.working_style,
                    "authority_source": False,
                }
            ),
            revision=1,
            updated_by=session.principal,
            updated_at=now,
        )
        mandate = Mandate(
            namespace=namespace,
            mandate_id=self._identifiers.derive("mandate", colleague_id),
            mission=request.mission,
            service_relationship=request.service_relationship,
            responsibilities=responsibilities,
            capabilities=capabilities,
            constraints=constraints,
            working_context=FrozenJsonObject.from_mapping(
                {
                    "initial_context": request.working_context,
                    "initial_working_hours": request.working_hours,
                    "policy_enforcement": "not_implemented_p5",
                    "timezone": request.timezone,
                }
            ),
            effect_boundaries=(boundary,),
            revision=1,
            issued_by=session.principal,
            effective_at=now,
        )
        model = Principal.model(
            tenant_id=session.tenant_id,
            principal_id=self._identifiers.derive("model", colleague_id),
        )
        service = Principal.service(
            tenant_id=session.tenant_id,
            principal_id=self._identifiers.derive("service", colleague_id),
        )
        self._store.create_initial_colleague(
            namespace=namespace,
            profile=profile,
            mandate=mandate,
            runtime_principals=(model, service),
            actor=session.principal,
            correlation_id=correlation_id,
            occurred_at=now,
            idempotency_key=request.idempotency_key,
        )
        return profile, mandate, (model, service)

    def assign_work(
        self, *, session: AuthenticatedSession, request: WorkAssignmentRequest
    ) -> tuple[FiniteWork, bool]:
        self._require_admin(session)
        namespace = session.colleague_namespace()
        mandate_payloads = self._store.list_record_payloads(namespace, "mandate")
        if len(mandate_payloads) != 1:
            raise ConflictError("initial colleague must have exactly one Mandate")
        mandate = self._runtime_store.get_mandate(
            namespace,
            self._identifiers.derive("mandate", namespace.scope_id or "missing"),
        )
        if request.responsibility_id not in {
            item.responsibility_id for item in mandate.responsibilities
        }:
            raise PermissionDeniedError("work responsibility is outside the Mandate")
        model = self._store.first_principal(session.tenant_id, PrincipalKind.MODEL)
        now = self._clock.now()
        work_id = self._identifiers.derive(
            "work", namespace.scope_id or "missing", request.idempotency_key
        )
        correlation_id = self._identifiers.derive("correlation", work_id)
        work = FiniteWork(
            namespace=namespace,
            work_id=work_id,
            title=request.title,
            description=request.description,
            state=WorkState.READY,
            dependency_ids=(),
            responsibility_ids=(request.responsibility_id,),
            assignee_principal_id=model.principal_id,
            actor=session.principal,
            mandate_id=mandate.mandate_id,
            mandate_revision=mandate.revision,
            completion_evidence=(),
            correlation_id=correlation_id,
            causation_id=mandate.mandate_id,
            created_at=now,
            updated_at=now,
            revision=1,
        )
        return self._store.assign_work(work, idempotency_key=request.idempotency_key)

    @staticmethod
    def request_context(session: AuthenticatedSession) -> RequestPrincipalContext:
        return RequestPrincipalContext(session.colleague_namespace(), session.principal)


def _rate(metric: str, numerator: int, denominator: int, zero_reason: str) -> MetricResult:
    if denominator == 0:
        return MetricResult(metric, "not_applicable", None, 0, None, zero_reason)
    return MetricResult(metric, "observed", numerator, denominator, numerator / denominator, None)


def calculate_colleague_experience_metrics(counts: dict[str, int]) -> tuple[MetricResult, ...]:
    required = {
        "rebrief_turns",
        "resumptions_evaluated",
        "wrong_resumptions",
        "ai_eligible_opportunities",
        "ai_visible_outputs",
        "proactive_reviewed",
        "proactive_accepted",
        "ai_interactions_reviewed",
        "unnecessary_interruptions",
        "human_interventions",
        "scenarios_started",
        "scenarios_completed",
        "unauthorized_candidates",
        "unauthorized_escapes",
    }
    if set(counts) != required or any(
        type(value) is not int or value < 0 for value in counts.values()
    ):
        raise ValidationError("colleague-experience counts are incomplete or invalid")
    rebrief = (
        MetricResult(
            "rebrief_turns",
            "not_applicable",
            None,
            0,
            None,
            "no resumptions were evaluated",
        )
        if counts["resumptions_evaluated"] == 0
        else MetricResult(
            "rebrief_turns",
            "observed",
            counts["rebrief_turns"],
            counts["resumptions_evaluated"],
            float(counts["rebrief_turns"]),
            None,
        )
    )
    interventions = (
        MetricResult(
            "human_intervention_count",
            "not_applicable",
            None,
            0,
            None,
            "no finite-work scenarios were started",
        )
        if counts["scenarios_started"] == 0
        else MetricResult(
            "human_intervention_count",
            "observed",
            counts["human_interventions"],
            counts["scenarios_started"],
            float(counts["human_interventions"]),
            None,
        )
    )
    return (
        rebrief,
        _rate(
            "wrong_memory_rate",
            counts["wrong_resumptions"],
            counts["resumptions_evaluated"],
            "no resumptions were evaluated",
        ),
        _rate(
            "ai_initiated_rate",
            counts["ai_visible_outputs"],
            counts["ai_eligible_opportunities"],
            "no eligible allowed-trigger opportunities produced an observation",
        ),
        _rate(
            "proactive_suggestion_acceptance_rate",
            counts["proactive_accepted"],
            counts["proactive_reviewed"],
            "no proactive suggestions were reviewed",
        ),
        _rate(
            "unnecessary_interruption_rate",
            counts["unnecessary_interruptions"],
            counts["ai_interactions_reviewed"],
            "no AI-initiated interactions were reviewed",
        ),
        interventions,
        _rate(
            "completion_rate",
            counts["scenarios_completed"],
            counts["scenarios_started"],
            "no finite-work scenarios were started",
        ),
        _rate(
            "unauthorized_proposal_escape_rate",
            counts["unauthorized_escapes"],
            counts["unauthorized_candidates"],
            "no unauthorized proposal candidates were evaluated",
        ),
    )


class P4RuntimeController:
    """One bounded deterministic cycle exposed to Studio and the local worker."""

    def __init__(
        self,
        *,
        store: RuntimePersistencePort,
        studio_store: StudioPersistencePort,
        intelligence: IntelligencePort,
        channel: ReferenceChannelPort,
        clock: ClockPort,
        identifiers: IdentifierPort,
        digests: CredentialDigestPort,
    ) -> None:
        self._store = store
        self._studio_store = studio_store
        self._intelligence = intelligence
        self._channel = channel
        self._clock = clock
        self._identifiers = identifiers
        self._digests = digests

    @staticmethod
    def _context(session: AuthenticatedSession) -> RequestPrincipalContext:
        require_authoritative_human_role(
            session.principal,
            accepted_roles=frozenset({HumanRole.TENANT_ADMIN}),
        )
        return RequestPrincipalContext(session.colleague_namespace(), session.principal)

    def _actors(self, session: AuthenticatedSession) -> tuple[Principal, Principal, str]:
        namespace = session.colleague_namespace()
        model = self._studio_store.first_principal(session.tenant_id, PrincipalKind.MODEL)
        service = self._studio_store.first_principal(session.tenant_id, PrincipalKind.SERVICE)
        mandate_id = self._identifiers.derive("mandate", namespace.scope_id or "missing")
        return model, service, mandate_id

    def submit_trigger(
        self,
        *,
        session: AuthenticatedSession,
        work_id: str,
        trigger_class: str,
        deterministic_noop: bool,
        idempotency_key: str,
    ) -> str:
        context = self._context(session)
        work = self._store.get_work(context.namespace, work_id)
        model, service, mandate_id = self._actors(session)
        del model, mandate_id
        event_id = self._identifiers.derive(
            "event" if trigger_class == "event" else "occurrence",
            work_id,
            idempotency_key,
        )
        correlation_id = self._identifiers.derive("correlation", event_id)
        title = ("noop:" if deterministic_noop else "wake:") + work.title
        safe_projection = FrozenJsonObject.from_mapping(
            {"priority": 700, "title": title, "work_id": work.work_id}
        )
        if trigger_class == "event":
            EventService(self._store, self._identifiers, self._clock).submit(
                context=context,
                request=InputEventRequest(
                    event_id=event_id,
                    event_type="work_assigned",
                    safe_projection=safe_projection,
                    payload_digest=self._digests.digest("event-payload", work.work_id),
                    correlation_id=correlation_id,
                    causation_id=work.work_id,
                ),
                idempotency_key=idempotency_key,
            )
        elif trigger_class == "timer":
            TimerService(
                self._store,
                self._identifiers,
                self._clock,
                service,
            ).schedule(
                namespace=context.namespace,
                request=TimerScheduleRequest(
                    timer_id=self._identifiers.derive("timer", work_id),
                    occurrence_id=event_id,
                    due_at=self._clock.now(),
                    safe_projection=safe_projection,
                    correlation_id=correlation_id,
                    causation_id=work.work_id,
                    idempotency_key=idempotency_key,
                ),
            )
        else:
            raise ValidationError("trigger class must be event or timer")
        return correlation_id

    def process_once(self, session: AuthenticatedSession) -> dict[str, object]:
        namespace = self._context(session).namespace
        model, service, mandate_id = self._actors(session)
        wake = WakeService(
            store=self._store,
            intelligence=self._intelligence,
            clock=self._clock,
            identifiers=self._identifiers,
            service_principal=service,
            model_principal=model,
            mandate_id=mandate_id,
            owner_id="worker:p4-local",
        )
        materialized = wake.materialize_next(namespace)
        result = wake.run(namespace)
        dispatched = DispatchService(
            store=self._store,
            channel=self._channel,
            clock=self._clock,
            identifiers=self._identifiers,
            result_actor=service,
            owner_id="worker:p4-dispatch",
            mandate_id=mandate_id,
        ).dispatch_once(namespace)
        return {
            "trigger_materialized": materialized is not None,
            "wake_selected": result.selected_count,
            "decisions": result.decision_count,
            "pending": result.pending_count,
            "dispatched": dispatched.dispatched,
            "action_result_id": dispatched.action_result_id,
        }

    def decide_proposal(
        self,
        *,
        session: AuthenticatedSession,
        proposal: EffectProposal,
        choice: ApprovalChoice,
        idempotency_key: str,
        expected_proposal_revision: int,
        expected_payload_digest: str,
        expected_proposal_digest: str,
        expected_mandate_id: str,
        expected_mandate_revision: int,
    ) -> tuple[HumanApprovalDecision, str | None, bool]:
        context = self._context(session)
        _, service, mandate_id = self._actors(session)
        if any(
            decision.proposal_id == proposal.proposal_id
            for decision in self._studio_store.studio_snapshot(context.namespace).approvals
        ):
            raise ConflictError("proposal decision replay was refused")
        if (
            proposal.revision != expected_proposal_revision
            or proposal.payload_digest != expected_payload_digest
            or proposal.proposal_digest != expected_proposal_digest
            or proposal.mandate_id != expected_mandate_id
            or proposal.mandate_revision != expected_mandate_revision
            or mandate_id != expected_mandate_id
        ):
            raise ConflictError("exact proposal or Mandate binding is stale")
        decision, attempt_id, created = ApprovalService(
            store=self._store,
            clock=self._clock,
            identifiers=self._identifiers,
            service_principal=service,
        ).decide(
            context=context,
            mandate_id=mandate_id,
            expected_mandate_revision=expected_mandate_revision,
            request=ApprovalRequest(
                approval_decision_id=self._identifiers.derive(
                    "approval", proposal.proposal_id, idempotency_key
                ),
                proposal_id=proposal.proposal_id,
                proposal_revision=proposal.revision,
                proposal_payload_digest=proposal.payload_digest,
                proposal_digest=proposal.proposal_digest,
                choice=choice,
                idempotency_key=idempotency_key,
            ),
        )
        if not created:
            raise ConflictError("proposal decision replay was refused")
        return decision, attempt_id, created
