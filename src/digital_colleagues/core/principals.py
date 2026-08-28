# SPDX-License-Identifier: Apache-2.0

"""Durable and disjoint human, model, and service principals."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from digital_colleagues.core.common import (
    SCHEMA_VERSION,
    freeze_strings,
    require_revision,
    require_schema_version,
    require_stable_id,
)
from digital_colleagues.core.errors import CoreInvariantError
from digital_colleagues.core.namespace import Namespace


class PrincipalKind(StrEnum):
    HUMAN = "human"
    MODEL = "model"
    SERVICE = "service"


class HumanRole(StrEnum):
    TENANT_ADMIN = "tenant_admin"
    COLLEAGUE_USER = "colleague_user"
    AUDITOR = "auditor"


CANONICAL_HUMAN_ROLE_IDS = frozenset(role.value for role in HumanRole)


@dataclass(frozen=True, slots=True)
class Principal:
    namespace: Namespace
    principal_id: str
    kind: PrincipalKind
    roles: tuple[HumanRole, ...] = ()
    revision: int = 1
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_schema_version(self.schema_version)
        require_stable_id(self.principal_id, "principal_id")
        self.namespace.require_principal(self.principal_id)
        if not isinstance(self.kind, PrincipalKind):
            raise CoreInvariantError("principal kind must be explicit")
        frozen_roles = tuple(self.roles)
        if len(frozen_roles) != len(set(frozen_roles)):
            raise CoreInvariantError("principal roles must not contain duplicates")
        if any(not isinstance(role, HumanRole) for role in frozen_roles):
            raise CoreInvariantError("human roles must use canonical system role IDs")
        if self.kind is not PrincipalKind.HUMAN and frozen_roles:
            raise CoreInvariantError("model and service principals cannot have human roles")
        object.__setattr__(self, "roles", frozen_roles)
        require_revision(self.revision)

    @classmethod
    def human(
        cls,
        *,
        tenant_id: str,
        principal_id: str,
        roles: tuple[HumanRole, ...],
        revision: int = 1,
    ) -> Principal:
        return cls(
            namespace=Namespace.principal(tenant_id, principal_id),
            principal_id=principal_id,
            kind=PrincipalKind.HUMAN,
            roles=roles,
            revision=revision,
        )

    @classmethod
    def model(cls, *, tenant_id: str, principal_id: str, revision: int = 1) -> Principal:
        return cls(
            namespace=Namespace.principal(tenant_id, principal_id),
            principal_id=principal_id,
            kind=PrincipalKind.MODEL,
            revision=revision,
        )

    @classmethod
    def service(cls, *, tenant_id: str, principal_id: str, revision: int = 1) -> Principal:
        return cls(
            namespace=Namespace.principal(tenant_id, principal_id),
            principal_id=principal_id,
            kind=PrincipalKind.SERVICE,
            revision=revision,
        )


def canonical_role_ids(values: object) -> tuple[str, ...]:
    """Validate role identifiers without treating them as authoritative assignments."""

    role_ids = freeze_strings(values, "role IDs")
    if any(role_id not in CANONICAL_HUMAN_ROLE_IDS for role_id in role_ids):
        raise CoreInvariantError("unknown human role ID")
    return role_ids
