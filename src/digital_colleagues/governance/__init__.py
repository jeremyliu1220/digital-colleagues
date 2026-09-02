# SPDX-License-Identifier: Apache-2.0

"""Pure governance policies over stable core contracts."""

from digital_colleagues.governance.approvals import (
    ApprovalAuthorization,
    authorize_effect_proposal,
    authorize_human_approval,
    require_authoritative_human_role,
)
from digital_colleagues.governance.rbac import ROLE_ACTIONS, action_matrix, authorize_action

__all__ = [
    "ApprovalAuthorization",
    "authorize_effect_proposal",
    "authorize_human_approval",
    "require_authoritative_human_role",
    "ROLE_ACTIONS",
    "action_matrix",
    "authorize_action",
]
