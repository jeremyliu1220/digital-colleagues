# SPDX-License-Identifier: Apache-2.0

"""P5 revisioned-builder workflows and deterministic runtime policy enforcement."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

from digital_colleagues.application.contracts import (
    IntelligenceRequest,
    SemanticDecision,
    SemanticOutcome,
)
from digital_colleagues.application.errors import (
    ConflictError,
    PermissionDeniedError,
    StaleConflictError,
    ValidationError,
)
from digital_colleagues.application.p4_contracts import (
    AuthenticatedSession,
    ServiceRuntimeContext,
)
from digital_colleagues.application.p4_ports import CredentialDigestPort
from digital_colleagues.application.p4_services import P4RuntimeController
from digital_colleagues.application.p5_contracts import (
    ConfirmationResult,
    ConfirmDraftRequest,
    DraftUpdateRequest,
    PolicyEdit,
)
from digital_colleagues.application.p5_ports import P5PersistencePort
from digital_colleagues.application.ports import ClockPort, IdentifierPort, IntelligencePort
from digital_colleagues.core.authority import EffectKind, Mandate, Profile
from digital_colleagues.core.builder import (
    ColleagueDraft,
    DefaultSource,
    DiffClassification,
    DiffSection,
    DraftDiffItem,
    DraftLifecycle,
    ExplicitDefault,
)
from digital_colleagues.core.common import FrozenJsonObject
from digital_colleagues.core.effects import ApprovalChoice, EffectProposal, HumanApprovalDecision
from digital_colleagues.core.policy import (
    ColleaguePolicy,
    DurableTriggerKind,
    EscalationCondition,
    InterruptionMode,
    NotificationMode,
    OutsideHoursOutcome,
    PolicyEnforcementRecord,
    PolicyOutcomeKind,
    PolicyRunState,
    PolicyStage,
    ProactivityMode,
    StopCondition,
    WakeBudget,
    WakeBudgetPeriod,
    Weekday,
    WeeklyWindow,
)
from digital_colleagues.core.principals import HumanRole, PrincipalKind
from digital_colleagues.core.runtime import Decision, DecisionKind
from digital_colleagues.core.serialization import contract_to_public_data
from digital_colleagues.governance.approvals import require_authoritative_human_role
from digital_colleagues.governance.policy import within_working_hours


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _public_mapping(value: object) -> dict[str, object]:
    mapped = contract_to_public_data(value)
    if not isinstance(mapped, dict):
        raise ValidationError("canonical contract mapping is unavailable")
    return mapped


def _wrapper(value: object) -> FrozenJsonObject:
    return FrozenJsonObject.from_mapping({"value": value})


def _profile_content(profile: Profile) -> dict[str, object]:
    data = _public_mapping(profile)
    return {key: data[key] for key in ("display_name", "description", "presentation")}


def _mandate_content(mandate: Mandate) -> dict[str, object]:
    data = _public_mapping(mandate)
    return {
        key: data[key]
        for key in (
            "mission",
            "service_relationship",
            "responsibilities",
            "capabilities",
            "constraints",
            "working_context",
            "effect_boundaries",
        )
    }


def _policy_content(policy: ColleaguePolicy) -> dict[str, object]:
    data = _public_mapping(policy)
    return {
        key: data[key]
        for key in (
            "mandate_id",
            "mandate_revision",
            "timezone",
            "weekly_windows",
            "allowed_triggers",
            "proactivity",
            "notification",
            "interruption",
            "wake_budget",
            "outside_hours",
            "stop_conditions",
            "escalation_conditions",
            "failure_limit",
            "run_state",
        )
    }


def _classify_set(before: tuple[str, ...], after: tuple[str, ...]) -> DiffClassification:
    left = set(before)
    right = set(after)
    if left == right:
        return DiffClassification.UNCHANGED
    if left < right:
        return DiffClassification.EXPANDED
    if right < left:
        return DiffClassification.NARROWED
    return DiffClassification.CHANGED


def _item(
    section: DiffSection,
    path: str,
    before: object,
    after: object,
    *,
    authoritative: bool,
    classification: DiffClassification | None = None,
) -> DraftDiffItem:
    resolved = classification
    if resolved is None:
        resolved = DiffClassification.UNCHANGED if before == after else DiffClassification.CHANGED
    return DraftDiffItem(
        section=section,
        path=path,
        classification=resolved,
        before=_wrapper(before),
        after=_wrapper(after),
        authoritative=authoritative,
    )


def _record_map(values: object, id_key: str) -> dict[str, object]:
    if not isinstance(values, list):
        raise ValidationError("canonical identified collection is invalid")
    result: dict[str, object] = {}
    for value in values:
        if not isinstance(value, dict) or not isinstance(value.get(id_key), str):
            raise ValidationError("canonical identified value is invalid")
        result[value[id_key]] = value
    return result


def _collection_diff(
    *,
    section: DiffSection,
    path: str,
    before: object,
    after: object,
    id_key: str,
) -> tuple[DraftDiffItem, ...]:
    previous = _record_map(before, id_key)
    proposed = _record_map(after, id_key)
    result: list[DraftDiffItem] = []
    for identifier in sorted(set(previous) | set(proposed)):
        old = previous.get(identifier)
        new = proposed.get(identifier)
        classification = (
            DiffClassification.ADDED
            if old is None
            else DiffClassification.REMOVED
            if new is None
            else DiffClassification.UNCHANGED
            if old == new
            else DiffClassification.CHANGED
        )
        result.append(
            _item(
                section,
                f"{path}.{identifier}",
                old,
                new,
                authoritative=True,
                classification=classification,
            )
        )
    return tuple(result)


def build_draft_diff(
    active_profile: Profile,
    active_mandate: Mandate,
    active_policy: ColleaguePolicy | None,
    proposed_profile: Profile,
    proposed_mandate: Mandate,
    proposed_policy: ColleaguePolicy,
) -> tuple[DraftDiffItem, ...]:
    profile_before = _profile_content(active_profile)
    profile_after = _profile_content(proposed_profile)
    mandate_before = _mandate_content(active_mandate)
    mandate_after = _mandate_content(proposed_mandate)
    policy_before = {} if active_policy is None else _policy_content(active_policy)
    policy_after = _policy_content(proposed_policy)
    items: list[DraftDiffItem] = []
    for key in ("display_name", "description", "presentation"):
        items.append(
            _item(
                DiffSection.PROFILE,
                key,
                profile_before[key],
                profile_after[key],
                authoritative=False,
            )
        )
    for key in ("mission", "service_relationship", "working_context"):
        items.append(
            _item(
                DiffSection.MANDATE,
                key,
                mandate_before[key],
                mandate_after[key],
                authoritative=True,
            )
        )
    for path, identifier in (
        ("responsibilities", "responsibility_id"),
        ("capabilities", "capability_id"),
        ("constraints", "constraint_id"),
        ("effect_boundaries", "boundary_id"),
    ):
        items.extend(
            _collection_diff(
                section=DiffSection.MANDATE,
                path=path,
                before=mandate_before[path],
                after=mandate_after[path],
                id_key=identifier,
            )
        )
    policy_fields = (
        "timezone",
        "weekly_windows",
        "proactivity",
        "notification",
        "interruption",
        "outside_hours",
        "failure_limit",
        "run_state",
    )
    for key in policy_fields:
        old = policy_before.get(key)
        new = policy_after[key]
        classification = None
        if key == "proactivity" and old is not None and old != new:
            classification = (
                DiffClassification.EXPANDED
                if new == ProactivityMode.BOUNDED.value
                else DiffClassification.NARROWED
            )
        if key == "run_state" and old is not None and old != new:
            classification = (
                DiffClassification.EXPANDED
                if new == PolicyRunState.ACTIVE.value
                else DiffClassification.NARROWED
            )
        items.append(
            _item(
                DiffSection.POLICY,
                key,
                old,
                new,
                authoritative=True,
                classification=classification,
            )
        )
    for key in ("allowed_triggers", "stop_conditions", "escalation_conditions"):
        old_raw = policy_before.get(key, [])
        new_raw = policy_after[key]
        if not isinstance(old_raw, list) or not isinstance(new_raw, list):
            raise ValidationError("canonical policy collection is invalid")
        old_values: tuple[str, ...] = tuple(str(item) for item in old_raw)
        new_values: tuple[str, ...] = tuple(str(item) for item in new_raw)
        classification = _classify_set(old_values, new_values)
        if key == "stop_conditions":
            classification = (
                DiffClassification.NARROWED
                if classification is DiffClassification.EXPANDED
                else DiffClassification.EXPANDED
                if classification is DiffClassification.NARROWED
                else classification
            )
        items.append(
            _item(
                DiffSection.POLICY,
                key,
                list(old_values),
                list(new_values),
                authoritative=True,
                classification=classification,
            )
        )
    old_budget = policy_before.get("wake_budget")
    new_budget = policy_after["wake_budget"]
    classification = None
    if isinstance(old_budget, dict) and isinstance(new_budget, dict):
        if old_budget.get("period") == new_budget.get("period"):
            old_limit = old_budget.get("limit")
            new_limit = new_budget.get("limit")
            if type(old_limit) is int and type(new_limit) is int and old_limit != new_limit:
                classification = (
                    DiffClassification.EXPANDED
                    if new_limit > old_limit
                    else DiffClassification.NARROWED
                )
    items.append(
        _item(
            DiffSection.POLICY,
            "wake_budget",
            old_budget,
            new_budget,
            authoritative=True,
            classification=classification,
        )
    )
    return tuple(items)


def _default_windows() -> tuple[WeeklyWindow, ...]:
    return tuple(WeeklyWindow(day, 0, 1_440) for day in Weekday)


_POLICY_DEFAULTS: dict[str, object] = {
    "timezone": "UTC",
    "weekly_windows": _default_windows(),
    "allowed_triggers": (DurableTriggerKind.EVENT, DurableTriggerKind.TIMER),
    "proactivity": ProactivityMode.BOUNDED,
    "notification": NotificationMode.ENABLED,
    "interruption": InterruptionMode.WORKING_HOURS_ONLY,
    "wake_limit": 24,
    "wake_period": WakeBudgetPeriod.DAY,
    "outside_hours": OutsideHoursOutcome.DEFER,
    "stop_conditions": (StopCondition.ADMIN_STOP,),
    "escalation_conditions": (EscalationCondition.BLOCKED_WORK,),
    "failure_limit": 3,
    "run_state": PolicyRunState.ACTIVE,
}


def _policy_edit_values(policy: ColleaguePolicy) -> dict[str, object]:
    return {
        "timezone": policy.timezone,
        "weekly_windows": policy.weekly_windows,
        "allowed_triggers": policy.allowed_triggers,
        "proactivity": policy.proactivity,
        "notification": policy.notification,
        "interruption": policy.interruption,
        "wake_limit": policy.wake_budget.limit,
        "wake_period": policy.wake_budget.period,
        "outside_hours": policy.outside_hours,
        "stop_conditions": policy.stop_conditions,
        "escalation_conditions": policy.escalation_conditions,
        "failure_limit": policy.failure_limit,
        "run_state": policy.run_state,
    }


def _explicit_default(path: str, value: object) -> ExplicitDefault:
    public = contract_to_public_data(value) if not isinstance(value, str | int) else value
    return ExplicitDefault(
        path=f"policy.{path}",
        value=_wrapper(public),
        source=DefaultSource.P5_SYSTEM_DEFAULT,
    )


def _policy_from_edit(
    *,
    namespace: object,
    policy_id: str,
    revision: int,
    mandate_id: str,
    mandate_revision: int,
    actor: object,
    occurred_at: object,
    edit: PolicyEdit | None,
    active_policy: ColleaguePolicy | None = None,
) -> tuple[ColleaguePolicy, tuple[ExplicitDefault, ...]]:
    from datetime import datetime

    from digital_colleagues.core.namespace import Namespace
    from digital_colleagues.core.principals import Principal

    if (
        not isinstance(namespace, Namespace)
        or not isinstance(actor, Principal)
        or not isinstance(occurred_at, datetime)
    ):
        raise ValidationError("server policy context is invalid")
    selected: dict[str, object] = {}
    defaults: list[ExplicitDefault] = []
    supplied_values = {
        "timezone": None if edit is None else edit.timezone,
        "weekly_windows": None if edit is None else edit.weekly_windows,
        "allowed_triggers": None if edit is None else edit.allowed_triggers,
        "proactivity": None if edit is None else edit.proactivity,
        "notification": None if edit is None else edit.notification,
        "interruption": None if edit is None else edit.interruption,
        "wake_limit": None if edit is None else edit.wake_limit,
        "wake_period": None if edit is None else edit.wake_period,
        "outside_hours": None if edit is None else edit.outside_hours,
        "stop_conditions": None if edit is None else edit.stop_conditions,
        "escalation_conditions": None if edit is None else edit.escalation_conditions,
        "failure_limit": None if edit is None else edit.failure_limit,
        "run_state": None if edit is None else edit.run_state,
    }
    active_values = None if active_policy is None else _policy_edit_values(active_policy)
    for field, default in _POLICY_DEFAULTS.items():
        supplied = supplied_values[field]
        if supplied is None:
            if active_values is None:
                selected[field] = default
                defaults.append(_explicit_default(field, default))
            else:
                selected[field] = active_values[field]
        else:
            selected[field] = supplied
    return (
        ColleaguePolicy(
            namespace=namespace,
            policy_id=policy_id,
            mandate_id=mandate_id,
            mandate_revision=mandate_revision,
            timezone=selected["timezone"],  # type: ignore[arg-type]
            weekly_windows=selected["weekly_windows"],  # type: ignore[arg-type]
            allowed_triggers=selected["allowed_triggers"],  # type: ignore[arg-type]
            proactivity=selected["proactivity"],  # type: ignore[arg-type]
            notification=selected["notification"],  # type: ignore[arg-type]
            interruption=selected["interruption"],  # type: ignore[arg-type]
            wake_budget=WakeBudget(
                selected["wake_limit"],  # type: ignore[arg-type]
                selected["wake_period"],  # type: ignore[arg-type]
            ),
            outside_hours=selected["outside_hours"],  # type: ignore[arg-type]
            stop_conditions=selected["stop_conditions"],  # type: ignore[arg-type]
            escalation_conditions=selected["escalation_conditions"],  # type: ignore[arg-type]
            failure_limit=selected["failure_limit"],  # type: ignore[arg-type]
            run_state=selected["run_state"],  # type: ignore[arg-type]
            revision=revision,
            issued_by=actor,
            effective_at=occurred_at,
        ),
        tuple(defaults),
    )


def _retain_matching_defaults(
    existing: ColleagueDraft,
    proposed_policy: ColleaguePolicy,
    generated: tuple[ExplicitDefault, ...],
) -> tuple[ExplicitDefault, ...]:
    proposed = _policy_edit_values(proposed_policy)
    candidates = {item.path: item for item in (*existing.explicit_defaults, *generated)}
    retained: list[ExplicitDefault] = []
    for field in _POLICY_DEFAULTS:
        path = f"policy.{field}"
        item = candidates.get(path)
        if item is not None and item.value == _explicit_default(field, proposed[field]).value:
            retained.append(item)
    return tuple(retained)


def _draft_digest(draft: ColleagueDraft) -> str:
    envelope = {
        "digest_schema_version": 1,
        "namespace": contract_to_public_data(draft.namespace),
        "draft_id": draft.draft_id,
        "draft_revision": draft.revision,
        "base_profile_id": draft.base_profile_id,
        "base_profile_revision": draft.base_profile_revision,
        "base_mandate_id": draft.base_mandate_id,
        "base_mandate_revision": draft.base_mandate_revision,
        "base_policy_id": draft.base_policy_id,
        "base_policy_revision": draft.base_policy_revision,
        "proposed_profile": contract_to_public_data(draft.proposed_profile),
        "proposed_mandate": contract_to_public_data(draft.proposed_mandate),
        "proposed_policy": contract_to_public_data(draft.proposed_policy),
        "explicit_defaults": [contract_to_public_data(item) for item in draft.explicit_defaults],
        "diff": [contract_to_public_data(item) for item in draft.diff],
    }
    return _sha256(_canonical_json(envelope))


def _with_digest(draft: ColleagueDraft) -> ColleagueDraft:
    provisional = replace(draft, canonical_digest="sha256:" + "0" * 64)
    return replace(provisional, canonical_digest=_draft_digest(provisional))


class RevisionedColleagueBuilderService:
    def __init__(
        self,
        *,
        store: P5PersistencePort,
        clock: ClockPort,
        identifiers: IdentifierPort,
    ) -> None:
        self._store = store
        self._clock = clock
        self._identifiers = identifiers

    @staticmethod
    def _require_admin(session: AuthenticatedSession) -> None:
        if session.principal.kind is not PrincipalKind.HUMAN:
            raise PermissionDeniedError("colleague draft requires a HUMAN principal")
        require_authoritative_human_role(
            session.principal,
            accepted_roles=frozenset({HumanRole.TENANT_ADMIN}),
        )
        if session.active_colleague_id is None:
            raise ValidationError("an active colleague is required")

    def _base_values(
        self, session: AuthenticatedSession
    ) -> tuple[Profile, Mandate, ColleaguePolicy | None]:
        self._require_admin(session)
        namespace = session.colleague_namespace()
        profile, mandate = self._store.active_configuration(namespace)
        return profile, mandate, self._store.get_active_policy(namespace)

    def create(self, *, session: AuthenticatedSession, idempotency_key: str) -> ColleagueDraft:
        self._require_admin(session)
        if not idempotency_key:
            raise ValidationError("draft idempotency key is required")
        profile, mandate, active_policy = self._base_values(session)
        now = self._clock.now()
        colleague_id = session.active_colleague_id
        assert colleague_id is not None
        draft_id = self._identifiers.derive("draft", colleague_id, idempotency_key)
        try:
            return self._store.get_draft(profile.namespace, draft_id)
        except Exception as error:
            from digital_colleagues.application.errors import NotFoundError

            if not isinstance(error, NotFoundError):
                raise
        proposed_profile = replace(
            profile,
            revision=profile.revision + 1,
            updated_by=session.principal,
            updated_at=now,
        )
        proposed_mandate = replace(
            mandate,
            revision=mandate.revision + 1,
            issued_by=session.principal,
            effective_at=now,
        )
        policy_id = self._identifiers.derive("policy", colleague_id)
        if active_policy is None:
            proposed_policy, defaults = _policy_from_edit(
                namespace=profile.namespace,
                policy_id=policy_id,
                revision=1,
                mandate_id=mandate.mandate_id,
                mandate_revision=mandate.revision,
                actor=session.principal,
                occurred_at=now,
                edit=None,
            )
        else:
            proposed_policy = replace(
                active_policy,
                revision=active_policy.revision + 1,
                issued_by=session.principal,
                effective_at=now,
            )
            defaults = ()
        diff = build_draft_diff(
            profile,
            mandate,
            active_policy,
            proposed_profile,
            proposed_mandate,
            proposed_policy,
        )
        correlation_id = self._identifiers.derive("correlation", draft_id)
        draft = ColleagueDraft(
            namespace=profile.namespace,
            draft_id=draft_id,
            revision=1,
            base_profile_id=profile.profile_id,
            base_profile_revision=profile.revision,
            base_mandate_id=mandate.mandate_id,
            base_mandate_revision=mandate.revision,
            base_policy_id=None if active_policy is None else active_policy.policy_id,
            base_policy_revision=0 if active_policy is None else active_policy.revision,
            proposed_profile=proposed_profile,
            proposed_mandate=proposed_mandate,
            proposed_policy=proposed_policy,
            explicit_defaults=defaults,
            diff=diff,
            canonical_digest="sha256:" + "0" * 64,
            state=DraftLifecycle.DRAFT,
            author=session.principal,
            created_at=now,
            updated_at=now,
            correlation_id=correlation_id,
            causation_id=mandate.mandate_id,
        )
        stored, _ = self._store.create_draft(_with_digest(draft))
        return stored

    def update(
        self,
        *,
        session: AuthenticatedSession,
        draft_id: str,
        request: DraftUpdateRequest,
    ) -> ColleagueDraft:
        profile, mandate, active_policy = self._base_values(session)
        existing = self._store.get_draft(profile.namespace, draft_id)
        if existing.revision != request.expected_draft_revision:
            raise StaleConflictError("draft revision is stale")
        if existing.state not in {DraftLifecycle.DRAFT, DraftLifecycle.REVIEWABLE}:
            raise StaleConflictError("terminal colleague draft cannot be updated")
        now = self._clock.now()
        proposed_profile = Profile(
            namespace=profile.namespace,
            profile_id=profile.profile_id,
            display_name=request.profile.display_name,
            description=request.profile.description,
            presentation=request.profile.presentation,
            revision=profile.revision + 1,
            updated_by=session.principal,
            updated_at=now,
        )
        proposed_mandate = Mandate(
            namespace=mandate.namespace,
            mandate_id=mandate.mandate_id,
            mission=request.mandate.mission,
            service_relationship=request.mandate.service_relationship,
            responsibilities=request.mandate.responsibilities,
            capabilities=request.mandate.capabilities,
            constraints=request.mandate.constraints,
            working_context=request.mandate.working_context,
            effect_boundaries=request.mandate.effect_boundaries,
            revision=mandate.revision + 1,
            issued_by=session.principal,
            effective_at=now,
        )
        mandate_changed = _mandate_content(mandate) != _mandate_content(proposed_mandate)
        policy_id = (
            self._identifiers.derive("policy", profile.namespace.scope_id or "missing")
            if active_policy is None
            else active_policy.policy_id
        )
        proposed_policy, defaults = _policy_from_edit(
            namespace=profile.namespace,
            policy_id=policy_id,
            revision=(0 if active_policy is None else active_policy.revision) + 1,
            mandate_id=mandate.mandate_id,
            mandate_revision=proposed_mandate.revision if mandate_changed else mandate.revision,
            actor=session.principal,
            occurred_at=now,
            edit=request.policy,
            active_policy=active_policy,
        )
        defaults = _retain_matching_defaults(existing, proposed_policy, defaults)
        diff = build_draft_diff(
            profile,
            mandate,
            active_policy,
            proposed_profile,
            proposed_mandate,
            proposed_policy,
        )
        if request.policy.explicit_resume:
            _, runtime_state = self._store.get_runtime_policy_state(profile.namespace)
            if runtime_state is not PolicyRunState.STOPPED:
                raise ValidationError("explicit resume requires a durable stopped runtime")
            diff = (
                *diff,
                _item(
                    DiffSection.POLICY,
                    "explicit_resume",
                    False,
                    True,
                    authoritative=True,
                    classification=DiffClassification.EXPANDED,
                ),
            )
        updated = ColleagueDraft(
            namespace=existing.namespace,
            draft_id=existing.draft_id,
            revision=existing.revision + 1,
            base_profile_id=existing.base_profile_id,
            base_profile_revision=existing.base_profile_revision,
            base_mandate_id=existing.base_mandate_id,
            base_mandate_revision=existing.base_mandate_revision,
            base_policy_id=existing.base_policy_id,
            base_policy_revision=existing.base_policy_revision,
            proposed_profile=proposed_profile,
            proposed_mandate=proposed_mandate,
            proposed_policy=proposed_policy,
            explicit_defaults=defaults,
            diff=diff,
            canonical_digest="sha256:" + "0" * 64,
            state=DraftLifecycle.DRAFT,
            author=existing.author,
            created_at=existing.created_at,
            updated_at=now,
            correlation_id=existing.correlation_id,
            causation_id=existing.causation_id,
        )
        return self._store.update_draft(
            _with_digest(updated),
            expected_revision=request.expected_draft_revision,
        )

    def review(
        self,
        *,
        session: AuthenticatedSession,
        draft_id: str,
        expected_revision: int,
    ) -> ColleagueDraft:
        self._require_admin(session)
        return self._store.review_draft(
            namespace=session.colleague_namespace(),
            draft_id=draft_id,
            expected_revision=expected_revision,
            actor=session.principal,
            occurred_at=self._clock.now(),
        )

    def cancel(
        self,
        *,
        session: AuthenticatedSession,
        draft_id: str,
        expected_revision: int,
    ) -> ColleagueDraft:
        self._require_admin(session)
        return self._store.cancel_draft(
            namespace=session.colleague_namespace(),
            draft_id=draft_id,
            expected_revision=expected_revision,
            actor=session.principal,
            occurred_at=self._clock.now(),
        )

    def confirm(
        self,
        *,
        session: AuthenticatedSession,
        draft_id: str,
        request: ConfirmDraftRequest,
        change_decision_id: str | None = None,
    ) -> ConfirmationResult:
        self._require_admin(session)
        binding = {
            "draft_id": draft_id,
            "expected_draft_revision": request.expected_draft_revision,
            "expected_base_profile_revision": request.expected_base_profile_revision,
            "expected_base_mandate_revision": request.expected_base_mandate_revision,
            "expected_base_policy_revision": request.expected_base_policy_revision,
            "expected_canonical_digest": request.expected_canonical_digest,
        }
        if change_decision_id is not None:
            binding["change_decision_id"] = change_decision_id
        request_digest = _sha256(_canonical_json(binding))
        return self._store.confirm_draft(
            namespace=session.colleague_namespace(),
            draft_id=draft_id,
            expected_draft_revision=request.expected_draft_revision,
            expected_base_profile_revision=request.expected_base_profile_revision,
            expected_base_mandate_revision=request.expected_base_mandate_revision,
            expected_base_policy_revision=request.expected_base_policy_revision,
            expected_canonical_digest=request.expected_canonical_digest,
            actor=session.principal,
            idempotency_key=request.idempotency_key,
            request_digest=request_digest,
            confirmation_id=self._identifiers.derive(
                "confirmation", draft_id, request.idempotency_key
            ),
            occurred_at=self._clock.now(),
            change_decision_id=change_decision_id,
        )


def _policy_record(
    *,
    store: P5PersistencePort,
    identifiers: IdentifierPort,
    digests: CredentialDigestPort,
    policy: ColleaguePolicy,
    request: IntelligenceRequest,
    outcome: PolicyOutcomeKind,
    stage: PolicyStage = PolicyStage.POST_MODEL,
) -> PolicyEnforcementRecord:
    record = PolicyEnforcementRecord(
        namespace=request.namespace,
        outcome_id=identifiers.derive(
            "policy-outcome", request.request_id, stage.value, outcome.value
        ),
        policy_id=policy.policy_id,
        policy_revision=policy.revision,
        mandate_id=policy.mandate_id,
        mandate_revision=policy.mandate_revision,
        stage=stage,
        outcome=outcome,
        trigger_class=(
            DurableTriggerKind.TIMER
            if request.wake_cycle.trigger_timer_occurrence_ids
            else DurableTriggerKind.EVENT
        ),
        source_id=request.wake_cycle.causation_id,
        actor=request.model_principal,
        correlation_id=request.agenda_item.correlation_id,
        causation_id=request.agenda_item.agenda_item_id,
        occurred_at=request.occurred_at,
        safe_projection=FrozenJsonObject.from_mapping(
            {"outcome": outcome.value, "stage": stage.value}
        ),
        payload_digest=digests.digest("policy-outcome", request.request_id),
    )
    store.record_policy_outcome(record)
    return record


class PolicyGovernedIntelligence:
    """Revalidate exact policy after model output and before proposal persistence."""

    def __init__(
        self,
        *,
        inner: IntelligencePort,
        store: P5PersistencePort,
        identifiers: IdentifierPort,
        digests: CredentialDigestPort,
    ) -> None:
        self._inner = inner
        self._store = store
        self._identifiers = identifiers
        self._digests = digests

    def _refuse(
        self,
        request: IntelligenceRequest,
        semantic: SemanticDecision,
        policy: ColleaguePolicy,
        outcome: PolicyOutcomeKind,
        *,
        stage: PolicyStage = PolicyStage.POST_MODEL,
    ) -> SemanticDecision:
        _policy_record(
            store=self._store,
            identifiers=self._identifiers,
            digests=self._digests,
            policy=policy,
            request=request,
            outcome=outcome,
            stage=stage,
        )
        decision = replace(
            semantic.decision,
            kind=DecisionKind.NO_ACTION,
            rationale=f"P5 policy produced {outcome.value} before proposal persistence.",
            proposed_effect_id=None,
            policy_id=policy.policy_id,
            policy_revision=policy.revision,
        )
        return SemanticDecision(SemanticOutcome.NO_OP, decision, None, semantic.request_id)

    def _refuse_before_model(
        self,
        request: IntelligenceRequest,
        policy: ColleaguePolicy,
        outcome: PolicyOutcomeKind,
    ) -> SemanticDecision:
        _policy_record(
            store=self._store,
            identifiers=self._identifiers,
            digests=self._digests,
            policy=policy,
            request=request,
            outcome=outcome,
            stage=PolicyStage.PRE_WAKE,
        )
        decision = Decision(
            namespace=request.namespace,
            decision_id=request.decision_id,
            wake_cycle_id=request.wake_cycle.wake_cycle_id,
            agenda_item_id=request.agenda_item.agenda_item_id,
            kind=DecisionKind.NO_ACTION,
            rationale=f"P5 policy produced {outcome.value} before model invocation.",
            proposed_effect_id=None,
            actor=request.model_principal,
            correlation_id=request.agenda_item.correlation_id,
            causation_id=request.agenda_item.agenda_item_id,
            occurred_at=request.occurred_at,
            revision=1,
            policy_id=policy.policy_id,
            policy_revision=policy.revision,
        )
        return SemanticDecision(SemanticOutcome.NO_OP, decision, None, request.request_id)

    def decide(self, request: IntelligenceRequest) -> SemanticDecision:
        policy, run_state = self._store.get_runtime_policy_state(request.namespace)
        if policy is None:
            if request.policy_id is None:
                return self._inner.decide(request)
            raise PermissionDeniedError("typed runtime policy disappeared")
        binding = (policy.policy_id, policy.revision)
        if binding != (request.policy_id, request.policy_revision):
            return self._refuse_before_model(request, policy, PolicyOutcomeKind.STALE_POLICY)
        if (policy.mandate_id, policy.mandate_revision) != (
            request.mandate.mandate_id,
            request.mandate.revision,
        ):
            return self._refuse_before_model(request, policy, PolicyOutcomeKind.STALE_POLICY)
        if run_state is PolicyRunState.STOPPED:
            return self._refuse_before_model(request, policy, PolicyOutcomeKind.STOPPED)
        semantic = self._inner.decide(request)
        policy, run_state = self._store.get_runtime_policy_state(request.namespace)
        if policy is None:
            raise PermissionDeniedError("typed runtime policy disappeared")
        binding = (policy.policy_id, policy.revision)
        if binding != (request.policy_id, request.policy_revision):
            return self._refuse(request, semantic, policy, PolicyOutcomeKind.STALE_POLICY)
        if (policy.mandate_id, policy.mandate_revision) != (
            request.mandate.mandate_id,
            request.mandate.revision,
        ):
            return self._refuse(request, semantic, policy, PolicyOutcomeKind.STALE_POLICY)
        if run_state is PolicyRunState.STOPPED:
            return self._refuse(request, semantic, policy, PolicyOutcomeKind.STOPPED)
        if semantic.proposal is None:
            _policy_record(
                store=self._store,
                identifiers=self._identifiers,
                digests=self._digests,
                policy=policy,
                request=request,
                outcome=PolicyOutcomeKind.ALLOWED,
            )
            return semantic
        if policy.proactivity is ProactivityMode.DISABLED:
            return self._refuse(request, semantic, policy, PolicyOutcomeKind.PROACTIVITY_SUPPRESSED)
        if (
            semantic.proposal.effect_kind is EffectKind.NOTIFICATION
            and policy.notification is NotificationMode.SUPPRESSED
        ):
            return self._refuse(
                request, semantic, policy, PolicyOutcomeKind.NOTIFICATION_SUPPRESSED
            )
        if policy.interruption is InterruptionMode.NEVER or (
            policy.interruption is InterruptionMode.WORKING_HOURS_ONLY
            and not within_working_hours(policy, request.occurred_at)
        ):
            return self._refuse(
                request, semantic, policy, PolicyOutcomeKind.INTERRUPTION_SUPPRESSED
            )
        proposal = replace(
            semantic.proposal,
            policy_id=policy.policy_id,
            policy_revision=policy.revision,
        )
        decision = replace(
            semantic.decision,
            policy_id=policy.policy_id,
            policy_revision=policy.revision,
        )
        _policy_record(
            store=self._store,
            identifiers=self._identifiers,
            digests=self._digests,
            policy=policy,
            request=request,
            outcome=PolicyOutcomeKind.ALLOWED,
        )
        return SemanticDecision(semantic.outcome, decision, proposal, semantic.request_id)


class P5DispatchAuthorizer:
    def __init__(self, store: P5PersistencePort) -> None:
        self._store = store

    def authorize(self, proposal: EffectProposal, approval: HumanApprovalDecision) -> None:
        del approval
        self._store.require_current_proposal_policy(proposal, stage=PolicyStage.DISPATCH)


class P5RuntimeController:
    """Policy-aware facade around the retained P4 deterministic runtime."""

    def __init__(
        self,
        *,
        inner: P4RuntimeController,
        store: P5PersistencePort,
        clock: ClockPort,
        identifiers: IdentifierPort,
    ) -> None:
        self._inner = inner
        self._store = store
        self._clock = clock
        self._identifiers = identifiers

    def service_context(self, namespace: object) -> ServiceRuntimeContext:
        from digital_colleagues.core.namespace import Namespace

        if not isinstance(namespace, Namespace):
            raise ValidationError("runtime namespace is invalid")
        return self._inner.service_context(namespace)

    def submit_trigger(
        self,
        *,
        session: AuthenticatedSession,
        work_id: str,
        trigger_class: str,
        deterministic_noop: bool,
        idempotency_key: str,
    ) -> dict[str, object]:
        namespace = session.colleague_namespace()
        try:
            kind = DurableTriggerKind(trigger_class)
        except ValueError as exc:
            raise ValidationError("trigger class must be event or timer") from exc
        policy = self._store.get_active_policy(namespace)
        if policy is None:
            correlation = self._inner.submit_trigger(
                session=session,
                work_id=work_id,
                trigger_class=trigger_class,
                deterministic_noop=deterministic_noop,
                idempotency_key=idempotency_key,
            )
            return {
                "accepted": True,
                "trigger_class": trigger_class,
                "correlation_id": correlation,
                "policy_status": "legacy_unconfirmed",
            }
        source_id = self._identifiers.derive(
            "event" if kind is DurableTriggerKind.EVENT else "occurrence",
            work_id,
            idempotency_key,
        )
        correlation_id = self._identifiers.derive("correlation", source_id)
        admission = self._store.admit_trigger(
            policy=policy,
            trigger_class=kind,
            source_id=source_id,
            occurrence_key=self._identifiers.derive("budget-occurrence", work_id, idempotency_key),
            actor=session.principal,
            correlation_id=correlation_id,
            causation_id=work_id,
            outcome_id=self._identifiers.derive("policy-outcome", source_id, "pre-wake"),
            escalation_id=self._identifiers.derive("escalation", source_id),
            occurred_at=self._clock.now(),
        )
        if admission.accepted:
            correlation_id = self._inner.submit_trigger(
                session=session,
                work_id=work_id,
                trigger_class=trigger_class,
                deterministic_noop=deterministic_noop,
                idempotency_key=idempotency_key,
                policy_id=policy.policy_id,
                policy_revision=policy.revision,
            )
        return {
            "accepted": admission.accepted,
            "trigger_class": trigger_class,
            "correlation_id": correlation_id,
            "policy_status": "confirmed",
            "policy_id": policy.policy_id,
            "policy_revision": policy.revision,
            "policy_outcome": admission.outcome.value,
            "budget_count": admission.budget_count,
            "budget_limit": admission.budget_limit,
            "escalation_id": (
                None if admission.escalation is None else admission.escalation.escalation_id
            ),
        }

    def process_once(self, context: ServiceRuntimeContext) -> dict[str, object]:
        return self._inner.process_once(context)

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
        if (proposal.policy_id, proposal.policy_revision) != (
            expected_policy_id,
            expected_policy_revision,
        ):
            raise ConflictError("exact proposal policy binding is stale")
        if proposal.policy_id is not None:
            self._store.require_current_proposal_policy(proposal, stage=PolicyStage.APPROVAL)
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
