# SPDX-License-Identifier: Apache-2.0

"""Explicit tenant, colleague, and principal namespaces."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from digital_colleagues.core.common import require_stable_id
from digital_colleagues.core.errors import NamespaceMismatchError


class NamespaceScope(StrEnum):
    TENANT = "tenant"
    COLLEAGUE = "colleague"
    PRINCIPAL = "principal"


@dataclass(frozen=True, slots=True)
class Namespace:
    tenant_id: str
    scope: NamespaceScope
    scope_id: str | None = None

    def __post_init__(self) -> None:
        require_stable_id(self.tenant_id, "tenant_id")
        if not isinstance(self.scope, NamespaceScope):
            raise NamespaceMismatchError("namespace scope must be explicit")
        if self.scope is NamespaceScope.TENANT:
            if self.scope_id is not None:
                raise NamespaceMismatchError("tenant namespace cannot carry a scoped ID")
        elif self.scope_id is None:
            raise NamespaceMismatchError("scoped namespace requires a scope_id")
        else:
            require_stable_id(self.scope_id, "scope_id")

    @classmethod
    def tenant(cls, tenant_id: str) -> Namespace:
        return cls(tenant_id=tenant_id, scope=NamespaceScope.TENANT)

    @classmethod
    def colleague(cls, tenant_id: str, colleague_id: str) -> Namespace:
        return cls(
            tenant_id=tenant_id,
            scope=NamespaceScope.COLLEAGUE,
            scope_id=colleague_id,
        )

    @classmethod
    def principal(cls, tenant_id: str, principal_id: str) -> Namespace:
        return cls(
            tenant_id=tenant_id,
            scope=NamespaceScope.PRINCIPAL,
            scope_id=principal_id,
        )

    def require_colleague(self) -> None:
        if self.scope is not NamespaceScope.COLLEAGUE:
            raise NamespaceMismatchError("a complete colleague namespace is required")

    def require_principal(self, principal_id: str) -> None:
        if self.scope is not NamespaceScope.PRINCIPAL or self.scope_id != principal_id:
            raise NamespaceMismatchError("principal namespace does not match principal ID")

    def require_exact(self, other: Namespace) -> None:
        if self != other:
            raise NamespaceMismatchError("namespace mismatch")

    def require_same_tenant(self, other: Namespace) -> None:
        if self.tenant_id != other.tenant_id:
            raise NamespaceMismatchError("tenant namespace mismatch")
