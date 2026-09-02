# SPDX-License-Identifier: Apache-2.0

"""P6 local multi-user authentication, governance, and runtime services."""

from __future__ import annotations

from datetime import datetime, timedelta

from digital_colleagues.application.errors import (
    PermissionDeniedError,
    StaleConflictError,
    ValidationError,
)
from digital_colleagues.application.p4_contracts import (
    AuthenticatedSession,
    InitialColleagueRequest,
    SessionGrant,
    WorkAssignmentRequest,
)
from digital_colleagues.application.p4_ports import (
    CredentialDigestPort,
    SecretTokenPort,
)
from digital_colleagues.application.p4_services import (
    AuthenticationService,
    InitialColleagueService,
)
from digital_colleagues.application.p5_contracts import (
    ConfirmationResult,
    ConfirmDraftRequest,
    DraftUpdateRequest,
)
from digital_colleagues.application.p5_ports import P5PersistencePort
from digital_colleagues.application.p5_services import (
    P5DispatchAuthorizer,
    P5RuntimeController,
    RevisionedColleagueBuilderService,
)
from digital_colleagues.application.p6_contracts import (
    ChangeDecisionRequest,
    CredentialGrant,
    EnrollmentAuthorizationRequest,
    GovernanceSession,
    RecoveryAuthorizationRequest,
)
from digital_colleagues.application.p6_ports import GovernancePersistencePort
from digital_colleagues.application.ports import ClockPort, IdentifierPort
from digital_colleagues.core.authority import Mandate, Profile
from digital_colleagues.core.builder import ColleagueDraft
from digital_colleagues.core.effects import ApprovalChoice, EffectProposal, HumanApprovalDecision
from digital_colleagues.core.governance import (
    AuditExportQuery,
    AuditExportRecord,
    AuthorizationAction,
    ChangeDecision,
    ChangeKind,
    ChangeProposal,
    ChangeState,
    CredentialKind,
    CredentialState,
    GovernanceCredential,
    Membership,
    MembershipStatus,
    governance_change_digest,
)
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import HumanRole, Principal
from digital_colleagues.core.work import FiniteWork
from digital_colleagues.governance.rbac import action_matrix, authorize_action


def governance_action_matrix() -> dict[str, tuple[str, ...]]:
    """Expose the typed governance projection through the application boundary."""

    return action_matrix()


class P6AuthenticationService(AuthenticationService):
    """Require current membership on every session use and govern new credentials."""

    def __init__(
        self,
        *,
        store: GovernancePersistencePort,
        clock: ClockPort,
        tokens: SecretTokenPort,
        digests: CredentialDigestPort,
        identifiers: IdentifierPort,
        tenant_id: str,
        bootstrap_validity: timedelta = timedelta(minutes=10),
        session_validity: timedelta = timedelta(hours=8),
        credential_validity: timedelta = timedelta(minutes=10),
    ) -> None:
        if credential_validity <= timedelta(0) or credential_validity > timedelta(minutes=10):
            raise ValidationError("governance credential validity must be at most ten minutes")
        super().__init__(
            store=store,  # type: ignore[arg-type]
            clock=clock,
            tokens=tokens,
            digests=digests,
            tenant_id=tenant_id,
            bootstrap_validity=bootstrap_validity,
            session_validity=session_validity,
        )
        self._governance_store = store
        self._identifiers = identifiers
        self._credential_validity = credential_validity

    def now(self) -> datetime:
        return self._clock.now()

    def resolve(self, session_credential: str) -> AuthenticatedSession:
        if not session_credential:
            raise PermissionDeniedError("authenticated session is required")
        session, _ = self._governance_store.governed_session(
            credential_digest=self._digests.digest("session", session_credential),
            evaluated_at=self._clock.now(),
        )
        return session

    def authorize_mutation(
        self,
        *,
        session_credential: str,
        origin: str | None,
        csrf_token: str | None,
        expected_origin: str,
    ) -> AuthenticatedSession:
        session = self.resolve(session_credential)
        if origin != expected_origin or csrf_token is None:
            raise PermissionDeniedError("browser mutation defense was refused")
        actual = self._digests.digest("csrf-storage", csrf_token)
        if not self._digests.matches(session.csrf_digest, actual):
            raise PermissionDeniedError("browser mutation defense was refused")
        return session

    def authorize(
        self,
        *,
        session: AuthenticatedSession,
        action: AuthorizationAction,
        namespace: Namespace,
    ) -> Membership:
        current = self._governance_store.membership_for_principal(
            session.tenant_id, session.principal.principal_id
        )
        try:
            authorize_action(
                principal=session.principal,
                membership=current,
                action=action,
                namespace=namespace,
            )
        except (ValueError, RuntimeError) as exc:
            raise PermissionDeniedError("governance action was refused") from exc
        if (
            session.role_revision != current.role_revision
            or session.membership_revision != current.membership_revision
        ):
            raise PermissionDeniedError("session authority revision is stale")
        return current

    def bind_colleague(
        self, session: AuthenticatedSession, colleague_id: str
    ) -> AuthenticatedSession:
        namespace = Namespace.colleague(session.tenant_id, colleague_id)
        self.authorize(
            session=session,
            action=AuthorizationAction.READ_COLLEAGUE,
            namespace=namespace,
        )
        return self._store.set_active_colleague(
            session=session,
            colleague_id=colleague_id,
            occurred_at=self._clock.now(),
        )

    def authorize_enrollment(
        self,
        *,
        session: AuthenticatedSession,
        request: EnrollmentAuthorizationRequest,
    ) -> GovernanceCredential:
        membership = self.authorize(
            session=session,
            action=AuthorizationAction.MANAGE_CREDENTIAL,
            namespace=Namespace.tenant(session.tenant_id),
        )
        if request.role is HumanRole.TENANT_ADMIN:
            if request.colleague_ids != ("*",):
                raise ValidationError("Admin enrollment must use the fixed tenant scope")
        elif "*" in request.colleague_ids:
            raise ValidationError("non-Admin enrollment requires exact colleague scope")
        now = self._clock.now()
        credential_id = self._identifiers.derive(
            "credential", "enrollment", session.principal.principal_id, request.idempotency_key
        )
        bootstrap_transition = (
            request.role is HumanRole.TENANT_ADMIN and request.approved_change_decision_id is None
        )
        credential = GovernanceCredential(
            namespace=Namespace.tenant(session.tenant_id),
            credential_id=credential_id,
            kind=CredentialKind.ENROLLMENT,
            state=CredentialState.AUTHORIZED,
            target_principal_id=None,
            target_role_revision=None,
            target_membership_revision=None,
            target_role=request.role,
            colleague_ids=request.colleague_ids,
            bootstrap_transition=bootstrap_transition,
            issued_by_principal_id=session.principal.principal_id,
            issued_at=now,
            expires_at=now + self._credential_validity,
            change_decision_id=request.approved_change_decision_id,
            correlation_id=self._identifiers.derive("correlation", credential_id),
            causation_id=session.session_id,
        )
        return self._governance_store.authorize_enrollment(
            credential=credential, issuer_membership=membership
        )

    def authorize_recovery(
        self,
        *,
        session: AuthenticatedSession,
        request: RecoveryAuthorizationRequest,
    ) -> GovernanceCredential:
        issuer_membership = self.authorize(
            session=session,
            action=AuthorizationAction.MANAGE_CREDENTIAL,
            namespace=Namespace.tenant(session.tenant_id),
        )
        target = self._governance_store.membership_for_principal(
            session.tenant_id, request.principal_id
        )
        if target.status is not MembershipStatus.ACTIVE:
            raise PermissionDeniedError("recovery target was refused")
        now = self._clock.now()
        credential_id = self._identifiers.derive(
            "credential", "recovery", request.principal_id, request.idempotency_key
        )
        credential = GovernanceCredential(
            namespace=Namespace.tenant(session.tenant_id),
            credential_id=credential_id,
            kind=CredentialKind.RECOVERY,
            state=CredentialState.AUTHORIZED,
            target_principal_id=request.principal_id,
            target_role_revision=target.role_revision,
            target_membership_revision=target.membership_revision,
            target_role=None,
            colleague_ids=target.colleague_ids,
            bootstrap_transition=False,
            issued_by_principal_id=session.principal.principal_id,
            issued_at=now,
            expires_at=now + self._credential_validity,
            correlation_id=self._identifiers.derive("correlation", credential_id),
            causation_id=request.principal_id,
        )
        return self._governance_store.authorize_recovery(
            credential=credential, issuer_membership=issuer_membership
        )

    def retrieve_operator_credential(self, credential_id: str) -> str:
        plaintext = self._tokens.issue(32)
        retrieved = self._governance_store.claim_credential_secret(
            credential_id=credential_id,
            token_digest=self._digests.digest("governance-credential", plaintext),
            occurred_at=self._clock.now(),
        )
        if retrieved.state is not CredentialState.RETRIEVED:
            raise PermissionDeniedError("credential is expired or unavailable")
        return plaintext

    def exchange_enrollment(self, plaintext: str) -> CredentialGrant:
        if not plaintext:
            raise PermissionDeniedError("enrollment exchange was refused")
        now = self._clock.now()
        token_digest = self._digests.digest("governance-credential", plaintext)
        credential = self._governance_store.credential_by_digest(
            token_digest=token_digest, kind=CredentialKind.ENROLLMENT.value
        )
        if (
            credential.namespace.tenant_id != self._tenant_id
            or credential.state is not CredentialState.RETRIEVED
            or credential.target_role is None
        ):
            raise PermissionDeniedError("enrollment exchange was refused")
        if now >= credential.expires_at:
            self._governance_store.expire_credential(credential=credential, occurred_at=now)
            raise PermissionDeniedError("enrollment exchange was refused")
        principal_id = self._identifiers.derive("human", credential.credential_id)
        principal = Principal.human(
            tenant_id=self._tenant_id,
            principal_id=principal_id,
            roles=(credential.target_role,),
        )
        issuer = self._governance_store.get_principal(
            self._tenant_id, credential.issued_by_principal_id
        )
        membership = Membership(
            namespace=principal.namespace,
            membership_id=self._identifiers.derive("membership", principal_id),
            principal_id=principal_id,
            roles=principal.roles,
            colleague_ids=credential.colleague_ids,
            status=MembershipStatus.ACTIVE,
            role_revision=1,
            membership_revision=1,
            issued_by=issuer,
            created_at=now,
            updated_at=now,
            correlation_id=credential.correlation_id,
            causation_id=credential.credential_id,
        )
        session_credential = self._tokens.issue(32)
        csrf_token = self._digests.digest("csrf-token", session_credential).removeprefix("sha256:")
        active_colleague = (
            None if credential.colleague_ids == ("*",) else credential.colleague_ids[0]
        )
        session = AuthenticatedSession(
            tenant_id=self._tenant_id,
            session_id=self._identifiers.derive(
                "session", credential.credential_id, session_credential
            ),
            principal=principal,
            credential_digest=self._digests.digest("session", session_credential),
            csrf_digest=self._digests.digest("csrf-storage", csrf_token),
            active_colleague_id=active_colleague,
            created_at=now,
            expires_at=now + self._session_validity,
            role_revision=1,
            membership_revision=1,
        )
        consumed, stored_membership, stored_session = self._governance_store.consume_enrollment(
            token_digest=token_digest,
            principal=principal,
            membership=membership,
            session=session,
            occurred_at=now,
        )
        return CredentialGrant(
            credential=consumed,
            session_grant=SessionGrant(stored_session, session_credential, csrf_token),
            membership=stored_membership,
        )

    def exchange_recovery(self, plaintext: str) -> CredentialGrant:
        if not plaintext:
            raise PermissionDeniedError("recovery exchange was refused")
        now = self._clock.now()
        token_digest = self._digests.digest("governance-credential", plaintext)
        credential = self._governance_store.credential_by_digest(
            token_digest=token_digest, kind=CredentialKind.RECOVERY.value
        )
        if (
            credential.namespace.tenant_id != self._tenant_id
            or credential.state is not CredentialState.RETRIEVED
            or credential.target_principal_id is None
        ):
            raise PermissionDeniedError("recovery exchange was refused")
        if now >= credential.expires_at:
            self._governance_store.expire_credential(credential=credential, occurred_at=now)
            raise PermissionDeniedError("recovery exchange was refused")
        membership = self._governance_store.membership_for_principal(
            self._tenant_id, credential.target_principal_id
        )
        principal = self._governance_store.get_principal(
            self._tenant_id, credential.target_principal_id
        )
        session_credential = self._tokens.issue(32)
        csrf_token = self._digests.digest("csrf-token", session_credential).removeprefix("sha256:")
        session = AuthenticatedSession(
            tenant_id=self._tenant_id,
            session_id=self._identifiers.derive(
                "session", credential.credential_id, session_credential
            ),
            principal=principal,
            credential_digest=self._digests.digest("session", session_credential),
            csrf_digest=self._digests.digest("csrf-storage", csrf_token),
            active_colleague_id=(
                None if membership.colleague_ids == ("*",) else membership.colleague_ids[0]
            ),
            created_at=now,
            expires_at=now + self._session_validity,
            role_revision=membership.role_revision,
            membership_revision=membership.membership_revision,
        )
        consumed, stored_membership, stored_session = self._governance_store.consume_recovery(
            token_digest=token_digest,
            session=session,
            occurred_at=now,
        )
        return CredentialGrant(
            credential=consumed,
            session_grant=SessionGrant(stored_session, session_credential, csrf_token),
            membership=stored_membership,
        )

    def governance_session(self, session_credential: str) -> GovernanceSession:
        digest = self._digests.digest("session", session_credential)
        session, membership = self._governance_store.governed_session(
            credential_digest=digest, evaluated_at=self._clock.now()
        )
        return GovernanceSession(session, membership)


class P6ChangeService:
    def __init__(
        self,
        *,
        store: GovernancePersistencePort,
        draft_store: P5PersistencePort,
        builder: RevisionedColleagueBuilderService,
        authentication: P6AuthenticationService,
        clock: ClockPort,
        identifiers: IdentifierPort,
        digests: CredentialDigestPort,
        proposal_validity: timedelta = timedelta(minutes=30),
        decision_validity: timedelta = timedelta(minutes=15),
    ) -> None:
        self._store = store
        self._draft_store = draft_store
        self._builder = builder
        self._authentication = authentication
        self._clock = clock
        self._identifiers = identifiers
        self._digests = digests
        self._proposal_validity = proposal_validity
        self._decision_validity = decision_validity

    def propose_draft(
        self,
        *,
        session: AuthenticatedSession,
        draft_id: str,
        expected_revision: int,
        expected_digest: str,
        idempotency_key: str,
    ) -> ChangeProposal:
        namespace = session.colleague_namespace()
        membership = self._authentication.authorize(
            session=session,
            action=AuthorizationAction.PROPOSE_CHANGE,
            namespace=namespace,
        )
        draft = self._draft_store.get_draft(namespace, draft_id)
        if (
            draft.state.value != "reviewable"
            or draft.revision != expected_revision
            or draft.canonical_digest != expected_digest
        ):
            raise StaleConflictError("exact reviewable draft binding is stale")
        now = self._clock.now()
        proposal_id = self._identifiers.derive(
            "change", draft_id, str(draft.revision), idempotency_key
        )
        binding = f"{draft_id}:{draft.revision}:{draft.canonical_digest}"
        return self._store.create_change_proposal(
            ChangeProposal(
                namespace=namespace,
                proposal_id=proposal_id,
                change_kind=ChangeKind.DRAFT,
                target_id=draft_id,
                target_revision=draft.revision,
                canonical_digest=draft.canonical_digest,
                base_profile_revision=draft.base_profile_revision,
                base_mandate_revision=draft.base_mandate_revision,
                base_policy_revision=draft.base_policy_revision,
                proposed_role=None,
                proposed_status=None,
                proposed_colleague_ids=(),
                proposer_principal_id=session.principal.principal_id,
                proposer_role_revision=membership.role_revision,
                proposer_membership_revision=membership.membership_revision,
                issued_at=now,
                expires_at=now + self._proposal_validity,
                state=ChangeState.PENDING,
                idempotency_key=idempotency_key,
                request_digest=self._digests.digest("change:draft", binding),
                correlation_id=draft.correlation_id,
                causation_id=draft.draft_id,
            )
        )

    def propose_membership(
        self,
        *,
        session: AuthenticatedSession,
        target_principal_id: str,
        role: HumanRole,
        status: MembershipStatus,
        colleague_ids: tuple[str, ...],
        idempotency_key: str,
    ) -> ChangeProposal:
        namespace = Namespace.tenant(session.tenant_id)
        proposer = self._authentication.authorize(
            session=session,
            action=AuthorizationAction.PROPOSE_CHANGE,
            namespace=namespace,
        )
        target = self._store.membership_for_principal(session.tenant_id, target_principal_id)
        now = self._clock.now()
        digest = governance_change_digest(
            change_kind=ChangeKind.MEMBERSHIP,
            target_id=target_principal_id,
            target_revision=target.membership_revision,
            proposed_role=role,
            proposed_status=status,
            proposed_colleague_ids=colleague_ids,
        )
        proposal_id = self._identifiers.derive(
            "change", "membership", target_principal_id, idempotency_key
        )
        return self._store.create_change_proposal(
            ChangeProposal(
                namespace=namespace,
                proposal_id=proposal_id,
                change_kind=ChangeKind.MEMBERSHIP,
                target_id=target_principal_id,
                target_revision=target.membership_revision,
                canonical_digest=digest,
                base_profile_revision=0,
                base_mandate_revision=0,
                base_policy_revision=0,
                proposed_role=role,
                proposed_status=status,
                proposed_colleague_ids=colleague_ids,
                proposer_principal_id=session.principal.principal_id,
                proposer_role_revision=proposer.role_revision,
                proposer_membership_revision=proposer.membership_revision,
                issued_at=now,
                expires_at=now + self._proposal_validity,
                state=ChangeState.PENDING,
                idempotency_key=idempotency_key,
                request_digest=self._digests.digest("change:membership", digest),
                correlation_id=self._identifiers.derive("correlation", proposal_id),
                causation_id=target.membership_id,
            )
        )

    def propose_admin_enrollment(
        self, *, session: AuthenticatedSession, idempotency_key: str
    ) -> ChangeProposal:
        namespace = Namespace.tenant(session.tenant_id)
        proposer = self._authentication.authorize(
            session=session,
            action=AuthorizationAction.PROPOSE_CHANGE,
            namespace=namespace,
        )
        now = self._clock.now()
        target_id = self._identifiers.derive("enrollment", "admin", idempotency_key)
        digest = governance_change_digest(
            change_kind=ChangeKind.ADMIN_ENROLLMENT,
            target_id=target_id,
            target_revision=1,
            proposed_role=HumanRole.TENANT_ADMIN,
            proposed_status=MembershipStatus.ACTIVE,
            proposed_colleague_ids=("*",),
        )
        proposal_id = self._identifiers.derive("change", target_id, idempotency_key)
        return self._store.create_change_proposal(
            ChangeProposal(
                namespace=namespace,
                proposal_id=proposal_id,
                change_kind=ChangeKind.ADMIN_ENROLLMENT,
                target_id=target_id,
                target_revision=1,
                canonical_digest=digest,
                base_profile_revision=0,
                base_mandate_revision=0,
                base_policy_revision=0,
                proposed_role=HumanRole.TENANT_ADMIN,
                proposed_status=MembershipStatus.ACTIVE,
                proposed_colleague_ids=("*",),
                proposer_principal_id=session.principal.principal_id,
                proposer_role_revision=proposer.role_revision,
                proposer_membership_revision=proposer.membership_revision,
                issued_at=now,
                expires_at=now + self._proposal_validity,
                state=ChangeState.PENDING,
                idempotency_key=idempotency_key,
                request_digest=self._digests.digest("change:admin-enrollment", digest),
                correlation_id=self._identifiers.derive("correlation", proposal_id),
                causation_id=target_id,
            )
        )

    def decide(
        self,
        *,
        session: AuthenticatedSession,
        namespace: Namespace,
        proposal_id: str,
        request: ChangeDecisionRequest,
    ) -> tuple[ChangeProposal, ChangeDecision]:
        membership = self._authentication.authorize(
            session=session,
            action=AuthorizationAction.DECIDE_CHANGE,
            namespace=namespace,
        )
        proposal = self._store.get_change_proposal(namespace, proposal_id)
        now = self._clock.now()
        if now >= proposal.expires_at:
            self._store.expire_change_proposal(
                proposal=proposal, actor=session.principal, occurred_at=now
            )
            raise PermissionDeniedError("change proposal validity expired")
        if (
            proposal.revision != request.proposal_revision
            or proposal.canonical_digest != request.proposal_digest
        ):
            raise StaleConflictError("exact change proposal binding is stale")
        decision_id = self._identifiers.derive(
            "change-decision", proposal_id, request.idempotency_key
        )
        decision = ChangeDecision(
            namespace=namespace,
            decision_id=decision_id,
            proposal_id=proposal_id,
            proposal_revision=proposal.revision,
            proposal_digest=proposal.canonical_digest,
            choice=request.choice,
            approver_principal_id=session.principal.principal_id,
            approver_role_revision=membership.role_revision,
            approver_membership_revision=membership.membership_revision,
            occurred_at=now,
            valid_until=min(now + self._decision_validity, proposal.expires_at),
            idempotency_key=request.idempotency_key,
            request_digest=self._digests.digest(
                "change:decision",
                f"{proposal_id}:{proposal.revision}:{proposal.canonical_digest}:"
                f"{request.choice.value}",
            ),
            correlation_id=proposal.correlation_id,
            causation_id=proposal.proposal_id,
        )
        return self._store.decide_change(proposal=proposal, decision=decision)

    def apply_draft(
        self,
        *,
        session: AuthenticatedSession,
        namespace: Namespace,
        proposal_id: str,
        decision_id: str,
        idempotency_key: str,
    ) -> ConfirmationResult:
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.APPLY_CHANGE,
            namespace=namespace,
        )
        proposal = self._store.get_change_proposal(namespace, proposal_id)
        if proposal.change_kind is not ChangeKind.DRAFT:
            raise PermissionDeniedError("change proposal is not a draft change")
        try:
            return self._builder.confirm(
                session=session,
                draft_id=proposal.target_id,
                request=ConfirmDraftRequest(
                    expected_draft_revision=proposal.target_revision,
                    expected_base_profile_revision=proposal.base_profile_revision,
                    expected_base_mandate_revision=proposal.base_mandate_revision,
                    expected_base_policy_revision=proposal.base_policy_revision,
                    expected_canonical_digest=proposal.canonical_digest,
                    idempotency_key=idempotency_key,
                ),
                change_decision_id=decision_id,
            )
        except StaleConflictError:
            self._store.mark_change_proposal_stale(
                proposal=proposal,
                actor=session.principal,
                occurred_at=self._clock.now(),
            )
            raise

    def apply_membership(
        self,
        *,
        session: AuthenticatedSession,
        proposal_id: str,
        decision_id: str,
    ) -> Membership:
        namespace = Namespace.tenant(session.tenant_id)
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.APPLY_CHANGE,
            namespace=namespace,
        )
        proposal = self._store.get_change_proposal(namespace, proposal_id)
        target = self._store.membership_for_principal(session.tenant_id, proposal.target_id)
        expected_digest = governance_change_digest(
            change_kind=proposal.change_kind,
            target_id=target.principal_id,
            target_revision=target.membership_revision,
            proposed_role=proposal.proposed_role,
            proposed_status=proposal.proposed_status,
            proposed_colleague_ids=proposal.proposed_colleague_ids,
        )
        if proposal.state is ChangeState.APPROVED and (
            target.membership_revision != proposal.target_revision
            or expected_digest != proposal.canonical_digest
        ):
            self._store.mark_change_proposal_stale(
                proposal=proposal,
                actor=session.principal,
                occurred_at=self._clock.now(),
            )
            raise StaleConflictError("membership change target is stale")
        return self._store.apply_membership_change(
            proposal=proposal,
            decision_id=decision_id,
            actor=session.principal,
            occurred_at=self._clock.now(),
        )


class P6BuilderService:
    def __init__(
        self,
        *,
        inner: RevisionedColleagueBuilderService,
        authentication: P6AuthenticationService,
    ) -> None:
        self._inner = inner
        self._authentication = authentication

    def _authorize(self, session: AuthenticatedSession) -> None:
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.MANAGE_DRAFT,
            namespace=session.colleague_namespace(),
        )

    def create(self, *, session: AuthenticatedSession, idempotency_key: str) -> ColleagueDraft:
        self._authorize(session)
        return self._inner.create(session=session, idempotency_key=idempotency_key)

    def update(
        self,
        *,
        session: AuthenticatedSession,
        draft_id: str,
        request: DraftUpdateRequest,
    ) -> ColleagueDraft:
        self._authorize(session)
        return self._inner.update(session=session, draft_id=draft_id, request=request)

    def review(
        self, *, session: AuthenticatedSession, draft_id: str, expected_revision: int
    ) -> ColleagueDraft:
        self._authorize(session)
        return self._inner.review(
            session=session, draft_id=draft_id, expected_revision=expected_revision
        )

    def cancel(
        self, *, session: AuthenticatedSession, draft_id: str, expected_revision: int
    ) -> ColleagueDraft:
        self._authorize(session)
        return self._inner.cancel(
            session=session, draft_id=draft_id, expected_revision=expected_revision
        )

    def confirm(
        self,
        *,
        session: AuthenticatedSession,
        draft_id: str,
        request: ConfirmDraftRequest,
        change_decision_id: str | None = None,
    ) -> ConfirmationResult:
        self._authorize(session)
        return self._inner.confirm(
            session=session,
            draft_id=draft_id,
            request=request,
            change_decision_id=change_decision_id,
        )


class P6ColleagueService:
    def __init__(
        self,
        *,
        inner: InitialColleagueService,
        authentication: P6AuthenticationService,
    ) -> None:
        self._inner = inner
        self._authentication = authentication

    def create(
        self, *, session: AuthenticatedSession, request: InitialColleagueRequest
    ) -> tuple[Profile, Mandate, tuple[Principal, ...]]:
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.MANAGE_DRAFT,
            namespace=Namespace.tenant(session.tenant_id),
        )
        return self._inner.create(session=session, request=request)

    def assign_work(
        self, *, session: AuthenticatedSession, request: WorkAssignmentRequest
    ) -> tuple[FiniteWork, bool]:
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.ASSIGN_WORK,
            namespace=session.colleague_namespace(),
        )
        return self._inner.assign_work(session=session, request=request)


class P6RuntimeController:
    def __init__(
        self,
        *,
        inner: P5RuntimeController,
        authentication: P6AuthenticationService,
    ) -> None:
        self._inner = inner
        self._authentication = authentication

    def service_context(self, namespace: object) -> object:
        return self._inner.service_context(namespace)

    def submit_trigger(self, *, session: AuthenticatedSession, **values: object) -> object:
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.SUBMIT_TRIGGER,
            namespace=session.colleague_namespace(),
        )
        return self._inner.submit_trigger(session=session, **values)  # type: ignore[arg-type]

    def process_once(self, context: object) -> dict[str, object]:
        return self._inner.process_once(context)  # type: ignore[arg-type]

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
        expected_policy_id: str | None,
        expected_policy_revision: int | None,
    ) -> tuple[HumanApprovalDecision, str | None, bool]:
        self._authentication.authorize(
            session=session,
            action=AuthorizationAction.DECIDE_EFFECT,
            namespace=proposal.namespace,
        )
        return self._inner.decide_proposal(
            session=session,
            proposal=proposal,
            choice=choice,
            idempotency_key=idempotency_key,
            expected_proposal_revision=expected_proposal_revision,
            expected_payload_digest=expected_payload_digest,
            expected_proposal_digest=expected_proposal_digest,
            expected_mandate_id=expected_mandate_id,
            expected_mandate_revision=expected_mandate_revision,
            expected_policy_id=expected_policy_id,
            expected_policy_revision=expected_policy_revision,
        )


class P6DispatchAuthorizer:
    def __init__(
        self,
        *,
        p5: P5DispatchAuthorizer,
        store: GovernancePersistencePort,
        clock: ClockPort,
    ) -> None:
        self._p5 = p5
        self._store = store
        self._clock = clock

    def authorize(self, proposal: EffectProposal, approval: HumanApprovalDecision) -> None:
        self._p5.authorize(proposal, approval)
        self._store.require_current_effect_approval(
            namespace=proposal.namespace,
            approval_decision_id=approval.approval_decision_id,
            evaluated_at=self._clock.now(),
        )


class P6AuditService:
    def __init__(
        self,
        *,
        store: GovernancePersistencePort,
        authentication: P6AuthenticationService,
        clock: ClockPort,
        identifiers: IdentifierPort,
    ) -> None:
        self._store = store
        self._authentication = authentication
        self._clock = clock
        self._identifiers = identifiers

    def export(
        self, *, session: AuthenticatedSession, query: AuditExportQuery
    ) -> tuple[AuditExportRecord, ...]:
        membership = self._authentication.authorize(
            session=session,
            action=AuthorizationAction.EXPORT_AUDIT,
            namespace=query.namespace,
        )
        now = self._clock.now()
        audit_id = self._identifiers.derive(
            "export",
            session.principal.principal_id,
            str(query.start_at.timestamp()),
            str(query.end_at.timestamp()),
            str(query.limit),
            *query.record_types,
        )
        return self._store.audit_export(
            query=query,
            actor=session.principal,
            membership=membership,
            occurred_at=now,
            audit_id=audit_id,
        )
