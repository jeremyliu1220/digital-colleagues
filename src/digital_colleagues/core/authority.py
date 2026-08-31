# SPDX-License-Identifier: Apache-2.0

"""Descriptive profiles and revisioned authoritative mandates."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from digital_colleagues.core.common import (
    SCHEMA_VERSION,
    FrozenJsonObject,
    freeze_strings,
    require_revision,
    require_schema_version,
    require_stable_id,
    require_text,
    require_utc,
)
from digital_colleagues.core.errors import AuthorizationError, CoreInvariantError
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import Principal, PrincipalKind


@dataclass(frozen=True, slots=True)
class Profile:
    """Descriptive presentation data; never an authority source."""

    namespace: Namespace
    profile_id: str
    display_name: str
    description: str
    presentation: FrozenJsonObject
    revision: int
    updated_by: Principal
    updated_at: datetime
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.namespace.require_colleague()
        require_stable_id(self.profile_id, "profile_id")
        object.__setattr__(self, "display_name", require_text(self.display_name, "display_name"))
        object.__setattr__(self, "description", require_text(self.description, "description"))
        if not isinstance(self.presentation, FrozenJsonObject):
            raise CoreInvariantError("presentation must be a deeply immutable JSON object")
        require_revision(self.revision)
        self.namespace.require_same_tenant(self.updated_by.namespace)
        require_utc(self.updated_at, "updated_at")


@dataclass(frozen=True, slots=True)
class ResponsibilityDefinition:
    responsibility_id: str
    description: str
    obligations: tuple[str, ...]
    completion_conditions: tuple[str, ...]

    def __post_init__(self) -> None:
        require_stable_id(self.responsibility_id, "responsibility_id")
        object.__setattr__(self, "description", require_text(self.description, "description"))
        object.__setattr__(
            self,
            "obligations",
            freeze_strings(self.obligations, "obligations", allow_empty=False),
        )
        object.__setattr__(
            self,
            "completion_conditions",
            freeze_strings(
                self.completion_conditions,
                "completion_conditions",
                allow_empty=False,
            ),
        )


@dataclass(frozen=True, slots=True)
class CapabilityGrant:
    capability_id: str
    description: str

    def __post_init__(self) -> None:
        require_stable_id(self.capability_id, "capability_id")
        object.__setattr__(self, "description", require_text(self.description, "description"))


@dataclass(frozen=True, slots=True)
class Constraint:
    constraint_id: str
    description: str

    def __post_init__(self) -> None:
        require_stable_id(self.constraint_id, "constraint_id")
        object.__setattr__(self, "description", require_text(self.description, "description"))


class EffectKind(StrEnum):
    REFERENCE_MESSAGE = "reference_message"
    INTERNAL_RECORD = "internal_record"
    NOTIFICATION = "notification"


@dataclass(frozen=True, slots=True)
class EffectBoundary:
    boundary_id: str
    effect_kind: EffectKind
    allowed_destination_kinds: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    constraints: FrozenJsonObject
    human_approval_required: bool = True

    def __post_init__(self) -> None:
        require_stable_id(self.boundary_id, "boundary_id")
        if not isinstance(self.effect_kind, EffectKind):
            raise CoreInvariantError("effect kind must be explicit")
        object.__setattr__(
            self,
            "allowed_destination_kinds",
            freeze_strings(
                self.allowed_destination_kinds,
                "allowed_destination_kinds",
                allow_empty=False,
            ),
        )
        object.__setattr__(
            self,
            "allowed_actions",
            freeze_strings(self.allowed_actions, "allowed_actions", allow_empty=False),
        )
        if not isinstance(self.constraints, FrozenJsonObject):
            raise CoreInvariantError("effect boundary constraints must be immutable")
        if type(self.human_approval_required) is not bool:
            raise CoreInvariantError("human_approval_required must be boolean")


def _record_identifier(record: object) -> str | None:
    if isinstance(record, ResponsibilityDefinition):
        return record.responsibility_id
    if isinstance(record, CapabilityGrant):
        return record.capability_id
    if isinstance(record, Constraint):
        return record.constraint_id
    if isinstance(record, EffectBoundary):
        return record.boundary_id
    return None


def _freeze_unique_records(values: object, field: str) -> tuple[object, ...]:
    if not isinstance(values, Iterable):
        raise CoreInvariantError(f"{field} must be a collection")
    records: tuple[object, ...] = tuple(values)
    if not records:
        raise CoreInvariantError(f"{field} must not be empty")
    identifiers = tuple(_record_identifier(record) for record in records)
    if any(not isinstance(identifier, str) for identifier in identifiers):
        raise CoreInvariantError(f"{field} contains an invalid record")
    if len(identifiers) != len(set(identifiers)):
        raise CoreInvariantError(f"{field} must have unique IDs")
    return records


@dataclass(frozen=True, slots=True)
class Mandate:
    """The sole authoritative colleague grant in the P2 core."""

    namespace: Namespace
    mandate_id: str
    mission: str
    service_relationship: str
    responsibilities: tuple[ResponsibilityDefinition, ...]
    capabilities: tuple[CapabilityGrant, ...]
    constraints: tuple[Constraint, ...]
    working_context: FrozenJsonObject
    effect_boundaries: tuple[EffectBoundary, ...]
    revision: int
    issued_by: Principal
    effective_at: datetime
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.namespace.require_colleague()
        require_stable_id(self.mandate_id, "mandate_id")
        object.__setattr__(self, "mission", require_text(self.mission, "mission"))
        object.__setattr__(
            self,
            "service_relationship",
            require_text(self.service_relationship, "service_relationship"),
        )
        responsibilities = _freeze_unique_records(self.responsibilities, "responsibilities")
        capabilities = _freeze_unique_records(self.capabilities, "capabilities")
        constraints = _freeze_unique_records(self.constraints, "constraints")
        effect_boundaries = _freeze_unique_records(self.effect_boundaries, "effect_boundaries")
        if not all(isinstance(value, ResponsibilityDefinition) for value in responsibilities):
            raise CoreInvariantError("responsibilities contain an invalid record")
        if not all(isinstance(value, CapabilityGrant) for value in capabilities):
            raise CoreInvariantError("capabilities contain an invalid record")
        if not all(isinstance(value, Constraint) for value in constraints):
            raise CoreInvariantError("constraints contain an invalid record")
        if not all(isinstance(value, EffectBoundary) for value in effect_boundaries):
            raise CoreInvariantError("effect_boundaries contain an invalid record")
        object.__setattr__(self, "responsibilities", responsibilities)
        object.__setattr__(self, "capabilities", capabilities)
        object.__setattr__(self, "constraints", constraints)
        object.__setattr__(self, "effect_boundaries", effect_boundaries)
        if not isinstance(self.working_context, FrozenJsonObject):
            raise CoreInvariantError("working_context must be deeply immutable")
        require_revision(self.revision)
        if self.issued_by.kind is not PrincipalKind.HUMAN:
            raise AuthorizationError("an authoritative Mandate must be issued by a human")
        self.namespace.require_same_tenant(self.issued_by.namespace)
        require_utc(self.effective_at, "effective_at")


@dataclass(frozen=True, slots=True)
class IdentityCard:
    """A one-way display projection with no authority semantics."""

    namespace: Namespace
    profile_id: str
    profile_revision: int
    display_name: str
    description: str
    mandate_id: str
    mandate_revision: int
    mission: str
    responsibility_summaries: tuple[str, ...]
    capability_summaries: tuple[str, ...]
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        if not isinstance(self.namespace, Namespace):
            raise CoreInvariantError("identity card namespace must be explicit")
        self.namespace.require_colleague()
        require_stable_id(self.profile_id, "profile_id")
        require_revision(self.profile_revision, "profile_revision")
        object.__setattr__(self, "display_name", require_text(self.display_name, "display_name"))
        object.__setattr__(self, "description", require_text(self.description, "description"))
        require_stable_id(self.mandate_id, "mandate_id")
        require_revision(self.mandate_revision, "mandate_revision")
        object.__setattr__(self, "mission", require_text(self.mission, "mission"))
        object.__setattr__(
            self,
            "responsibility_summaries",
            freeze_strings(
                self.responsibility_summaries,
                "responsibility_summaries",
                allow_empty=False,
            ),
        )
        object.__setattr__(
            self,
            "capability_summaries",
            freeze_strings(
                self.capability_summaries,
                "capability_summaries",
                allow_empty=False,
            ),
        )


def project_identity_card(profile: Profile, mandate: Mandate) -> IdentityCard:
    profile.namespace.require_exact(mandate.namespace)
    return IdentityCard(
        namespace=mandate.namespace,
        profile_id=profile.profile_id,
        profile_revision=profile.revision,
        display_name=profile.display_name,
        description=profile.description,
        mandate_id=mandate.mandate_id,
        mandate_revision=mandate.revision,
        mission=mandate.mission,
        responsibility_summaries=tuple(item.description for item in mandate.responsibilities),
        capability_summaries=tuple(item.description for item in mandate.capabilities),
    )


@dataclass(frozen=True, slots=True)
class MandateAuthorityDiff:
    namespace: Namespace
    mandate_id: str
    from_revision: int
    to_revision: int
    mission_changed: bool
    service_relationship_changed: bool
    working_context_changed: bool
    added_responsibility_ids: tuple[str, ...]
    removed_responsibility_ids: tuple[str, ...]
    changed_responsibility_ids: tuple[str, ...]
    added_capability_ids: tuple[str, ...]
    removed_capability_ids: tuple[str, ...]
    changed_capability_ids: tuple[str, ...]
    added_constraint_ids: tuple[str, ...]
    removed_constraint_ids: tuple[str, ...]
    changed_constraint_ids: tuple[str, ...]
    added_effect_boundary_ids: tuple[str, ...]
    removed_effect_boundary_ids: tuple[str, ...]
    changed_effect_boundary_ids: tuple[str, ...]
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        if not isinstance(self.namespace, Namespace):
            raise CoreInvariantError("authority diff namespace must be explicit")
        self.namespace.require_colleague()
        require_stable_id(self.mandate_id, "mandate_id")
        require_revision(self.from_revision, "from_revision")
        require_revision(self.to_revision, "to_revision")
        if self.to_revision <= self.from_revision:
            raise CoreInvariantError("authority diff requires an increasing revision")
        for field_name, value in (
            ("mission_changed", self.mission_changed),
            ("service_relationship_changed", self.service_relationship_changed),
            ("working_context_changed", self.working_context_changed),
        ):
            if type(value) is not bool:
                raise CoreInvariantError(f"{field_name} must be boolean")
        diff_fields = (
            (
                "responsibility",
                (
                    ("added_responsibility_ids", self.added_responsibility_ids),
                    ("removed_responsibility_ids", self.removed_responsibility_ids),
                    ("changed_responsibility_ids", self.changed_responsibility_ids),
                ),
            ),
            (
                "capability",
                (
                    ("added_capability_ids", self.added_capability_ids),
                    ("removed_capability_ids", self.removed_capability_ids),
                    ("changed_capability_ids", self.changed_capability_ids),
                ),
            ),
            (
                "constraint",
                (
                    ("added_constraint_ids", self.added_constraint_ids),
                    ("removed_constraint_ids", self.removed_constraint_ids),
                    ("changed_constraint_ids", self.changed_constraint_ids),
                ),
            ),
            (
                "effect_boundary",
                (
                    ("added_effect_boundary_ids", self.added_effect_boundary_ids),
                    ("removed_effect_boundary_ids", self.removed_effect_boundary_ids),
                    ("changed_effect_boundary_ids", self.changed_effect_boundary_ids),
                ),
            ),
        )
        for prefix, fields_and_values in diff_fields:
            groups: list[tuple[str, ...]] = []
            for field_name, raw_identifiers in fields_and_values:
                identifiers = freeze_strings(raw_identifiers, field_name)
                for identifier in identifiers:
                    require_stable_id(identifier, field_name)
                object.__setattr__(self, field_name, identifiers)
                groups.append(identifiers)
            if any(
                set(left) & set(right)
                for left, right in (
                    (groups[0], groups[1]),
                    (groups[0], groups[2]),
                    (groups[1], groups[2]),
                )
            ):
                raise CoreInvariantError(f"{prefix} diff categories must be disjoint")


def _records_by_id(records: tuple[object, ...]) -> dict[str, object]:
    records_by_id: dict[str, object] = {}
    for record in records:
        identifier = _record_identifier(record)
        if identifier is None:
            raise CoreInvariantError("authority diff contains an invalid record")
        records_by_id[identifier] = record
    return records_by_id


def _record_diff(
    before: tuple[object, ...], after: tuple[object, ...]
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    before_by_id = _records_by_id(before)
    after_by_id = _records_by_id(after)
    added = tuple(sorted(after_by_id.keys() - before_by_id.keys()))
    removed = tuple(sorted(before_by_id.keys() - after_by_id.keys()))
    changed = tuple(
        sorted(
            identifier
            for identifier in before_by_id.keys() & after_by_id.keys()
            if before_by_id[identifier] != after_by_id[identifier]
        )
    )
    return added, removed, changed


def diff_mandate_authority(before: Mandate, after: Mandate) -> MandateAuthorityDiff:
    before.namespace.require_exact(after.namespace)
    if before.mandate_id != after.mandate_id:
        raise CoreInvariantError("authority diff requires the same mandate ID")
    if after.revision <= before.revision:
        raise CoreInvariantError("authority diff requires a newer Mandate revision")
    responsibility = _record_diff(before.responsibilities, after.responsibilities)
    capability = _record_diff(before.capabilities, after.capabilities)
    constraint = _record_diff(before.constraints, after.constraints)
    boundary = _record_diff(before.effect_boundaries, after.effect_boundaries)
    return MandateAuthorityDiff(
        namespace=before.namespace,
        mandate_id=before.mandate_id,
        from_revision=before.revision,
        to_revision=after.revision,
        mission_changed=before.mission != after.mission,
        service_relationship_changed=(before.service_relationship != after.service_relationship),
        working_context_changed=before.working_context != after.working_context,
        added_responsibility_ids=responsibility[0],
        removed_responsibility_ids=responsibility[1],
        changed_responsibility_ids=responsibility[2],
        added_capability_ids=capability[0],
        removed_capability_ids=capability[1],
        changed_capability_ids=capability[2],
        added_constraint_ids=constraint[0],
        removed_constraint_ids=constraint[1],
        changed_constraint_ids=constraint[2],
        added_effect_boundary_ids=boundary[0],
        removed_effect_boundary_ids=boundary[1],
        changed_effect_boundary_ids=boundary[2],
    )
