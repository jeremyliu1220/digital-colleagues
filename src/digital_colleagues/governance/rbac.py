# SPDX-License-Identifier: Apache-2.0

"""Central fail-closed P6 role/action and namespace authorization policy."""

from __future__ import annotations

from digital_colleagues.core.errors import AuthorizationError
from digital_colleagues.core.governance import (
    AuthorizationAction,
    Membership,
    MembershipStatus,
)
from digital_colleagues.core.namespace import Namespace
from digital_colleagues.core.principals import HumanRole, Principal, PrincipalKind

ROLE_ACTIONS: dict[HumanRole, frozenset[AuthorizationAction]] = {
    HumanRole.TENANT_ADMIN: frozenset(AuthorizationAction),
    HumanRole.COLLEAGUE_USER: frozenset(
        {
            AuthorizationAction.READ_SESSION_SECURITY,
            AuthorizationAction.READ_COLLEAGUE,
            AuthorizationAction.ASSIGN_WORK,
            AuthorizationAction.SUBMIT_TRIGGER,
            AuthorizationAction.PROCESS_RUNTIME,
            AuthorizationAction.DECIDE_EFFECT,
        }
    ),
    HumanRole.AUDITOR: frozenset(
        {
            AuthorizationAction.READ_SESSION_SECURITY,
            AuthorizationAction.READ_COLLEAGUE,
            AuthorizationAction.READ_GOVERNANCE,
            AuthorizationAction.EXPORT_AUDIT,
        }
    ),
}


def authorize_action(
    *,
    principal: Principal,
    membership: Membership,
    action: AuthorizationAction,
    namespace: Namespace,
) -> None:
    """Authorize one exact action using only durable current server records."""

    if principal.kind is not PrincipalKind.HUMAN:
        raise AuthorizationError("a human governance action requires a durable human")
    principal.namespace.require_exact(membership.namespace)
    namespace.require_same_tenant(principal.namespace)
    if membership.status is not MembershipStatus.ACTIVE:
        raise AuthorizationError("membership is not active")
    if membership.roles != principal.roles or membership.role_revision != principal.revision:
        raise AuthorizationError("principal role binding is stale")
    if not membership.allows_namespace(namespace):
        raise AuthorizationError("membership does not include the requested namespace")
    if not any(action in ROLE_ACTIONS.get(role, frozenset()) for role in membership.roles):
        raise AuthorizationError("role does not allow the requested action")


def action_matrix() -> dict[str, tuple[str, ...]]:
    """Return a deterministic public projection of the finite matrix."""

    return {
        role.value: tuple(sorted(action.value for action in actions))
        for role, actions in sorted(ROLE_ACTIONS.items(), key=lambda item: item[0].value)
    }
