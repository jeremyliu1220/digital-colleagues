# SPDX-License-Identifier: Apache-2.0

"""Pure P5 revisioned-builder records and review values."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from digital_colleagues.core.authority import Mandate, Profile
from digital_colleagues.core.common import (
    SCHEMA_VERSION,
    FrozenJsonObject,
    require_digest,
    require_revision,
    require_schema_version,
    require_stable_id,
    require_text,
    require_utc,
)
from digital_colleagues.core.errors import AuthorizationError, CoreInvariantError
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.policy import ColleaguePolicy
from digital_colleagues.core.principals import Principal, PrincipalKind


class DraftLifecycle(StrEnum):
    DRAFT = "draft"
    REVIEWABLE = "reviewable"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    STALE = "stale"


class DiffSection(StrEnum):
    PROFILE = "profile"
    MANDATE = "mandate"
    POLICY = "policy"


class DiffClassification(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"
    NARROWED = "narrowed"
    EXPANDED = "expanded"
    UNCHANGED = "unchanged"


class DefaultSource(StrEnum):
    P5_SYSTEM_DEFAULT = "p5_system_default"


@dataclass(frozen=True, slots=True)
class ExplicitDefault:
    path: str
    value: FrozenJsonObject
    source: DefaultSource = DefaultSource.P5_SYSTEM_DEFAULT

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", require_text(self.path, "default path", maximum=256))
        if not isinstance(self.value, FrozenJsonObject):
            raise CoreInvariantError("explicit default value must be immutable JSON")
        if not isinstance(self.source, DefaultSource):
            raise CoreInvariantError("explicit default source must be typed")


@dataclass(frozen=True, slots=True)
class DraftDiffItem:
    section: DiffSection
    path: str
    classification: DiffClassification
    before: FrozenJsonObject
    after: FrozenJsonObject
    authoritative: bool

    def __post_init__(self) -> None:
        if not isinstance(self.section, DiffSection):
            raise CoreInvariantError("diff section must be explicit")
        object.__setattr__(self, "path", require_text(self.path, "diff path", maximum=256))
        if not isinstance(self.classification, DiffClassification):
            raise CoreInvariantError("diff classification must be explicit")
        if not isinstance(self.before, FrozenJsonObject) or not isinstance(
            self.after, FrozenJsonObject
        ):
            raise CoreInvariantError("diff values must be immutable JSON wrappers")
        if type(self.authoritative) is not bool:
            raise CoreInvariantError("diff authority marker must be boolean")
        if self.section is DiffSection.PROFILE and self.authoritative:
            raise AuthorizationError("Profile diff cannot be authoritative")


@dataclass(frozen=True, slots=True)
class ColleagueDraft:
    namespace: Namespace
    draft_id: str
    revision: int
    base_profile_id: str
    base_profile_revision: int
    base_mandate_id: str
    base_mandate_revision: int
    base_policy_id: str | None
    base_policy_revision: int
    proposed_profile: Profile
    proposed_mandate: Mandate
    proposed_policy: ColleaguePolicy
    explicit_defaults: tuple[ExplicitDefault, ...]
    diff: tuple[DraftDiffItem, ...]
    canonical_digest: str
    state: DraftLifecycle
    author: Principal
    created_at: datetime
    updated_at: datetime
    correlation_id: str
    causation_id: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        self.namespace.require_colleague()
        require_stable_id(self.draft_id, "draft_id")
        require_revision(self.revision)
        require_stable_id(self.base_profile_id, "base_profile_id")
        require_revision(self.base_profile_revision, "base_profile_revision")
        require_stable_id(self.base_mandate_id, "base_mandate_id")
        require_revision(self.base_mandate_revision, "base_mandate_revision")
        if type(self.base_policy_revision) is not int or self.base_policy_revision < 0:
            raise CoreInvariantError("base_policy_revision must be a non-negative integer")
        if self.base_policy_id is None:
            if self.base_policy_revision != 0:
                raise CoreInvariantError("missing base policy ID requires revision zero")
        else:
            require_stable_id(self.base_policy_id, "base_policy_id")
            if self.base_policy_revision == 0:
                raise CoreInvariantError("a base policy ID requires a positive revision")
        self.namespace.require_exact(self.proposed_profile.namespace)
        self.namespace.require_exact(self.proposed_mandate.namespace)
        self.namespace.require_exact(self.proposed_policy.namespace)
        if self.proposed_profile.profile_id != self.base_profile_id:
            raise CoreInvariantError("proposed Profile must retain its base identity")
        if self.proposed_mandate.mandate_id != self.base_mandate_id:
            raise CoreInvariantError("proposed Mandate must retain its base identity")
        if (
            self.base_policy_id is not None
            and self.proposed_policy.policy_id != self.base_policy_id
        ):
            raise CoreInvariantError("proposed policy must retain its base identity")
        if self.proposed_profile.revision != self.base_profile_revision + 1:
            raise CoreInvariantError("proposed Profile revision must follow its base")
        if self.proposed_mandate.revision != self.base_mandate_revision + 1:
            raise CoreInvariantError("proposed Mandate revision must follow its base")
        if self.proposed_policy.revision != self.base_policy_revision + 1:
            raise CoreInvariantError("proposed policy revision must follow its base")
        defaults = tuple(self.explicit_defaults)
        diffs = tuple(self.diff)
        if not all(isinstance(item, ExplicitDefault) for item in defaults):
            raise CoreInvariantError("draft explicit defaults contain an invalid record")
        if not diffs or not all(isinstance(item, DraftDiffItem) for item in diffs):
            raise CoreInvariantError("draft diff must contain typed records")
        if len({item.path for item in defaults}) != len(defaults):
            raise CoreInvariantError("explicit default paths must be unique")
        if len({(item.section, item.path) for item in diffs}) != len(diffs):
            raise CoreInvariantError("draft diff paths must be unique within each section")
        object.__setattr__(self, "explicit_defaults", defaults)
        object.__setattr__(self, "diff", diffs)
        require_digest(self.canonical_digest, "canonical_digest")
        if not isinstance(self.state, DraftLifecycle):
            raise CoreInvariantError("draft lifecycle state must be explicit")
        if self.author.kind is not PrincipalKind.HUMAN:
            raise AuthorizationError("a colleague draft requires a human author")
        self.namespace.require_same_tenant(self.author.namespace)
        require_utc(self.created_at, "created_at")
        require_utc(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            raise CoreInvariantError("draft update cannot precede creation")
        require_stable_id(self.correlation_id, "correlation_id")
        require_stable_id(self.causation_id, "causation_id")
