-- SPDX-License-Identifier: Apache-2.0
ALTER TABLE p4_sessions
  ADD COLUMN role_revision INTEGER NOT NULL DEFAULT 1 CHECK (role_revision > 0);

ALTER TABLE p4_sessions
  ADD COLUMN membership_revision INTEGER NOT NULL DEFAULT 1 CHECK (membership_revision > 0);

ALTER TABLE p4_sessions
  ADD COLUMN revoked_reason TEXT;

CREATE TABLE p6_memberships (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'principal'),
  namespace_scope_id TEXT NOT NULL,
  membership_id TEXT NOT NULL,
  principal_record_type TEXT NOT NULL DEFAULT 'principal'
    CHECK (principal_record_type = 'principal'),
  principal_id TEXT NOT NULL,
  roles_json TEXT NOT NULL,
  colleague_scopes_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'revoked')),
  role_revision INTEGER NOT NULL CHECK (role_revision > 0),
  membership_revision INTEGER NOT NULL CHECK (membership_revision > 0),
  issued_by_principal_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, membership_id),
  UNIQUE (tenant_id, principal_id),
  FOREIGN KEY (
    tenant_id, namespace_scope, namespace_scope_id, principal_record_type, principal_id
  ) REFERENCES domain_records (
    tenant_id, namespace_scope, namespace_scope_id, record_type, record_id
  ) ON DELETE RESTRICT,
  CHECK (namespace_scope_id = principal_id)
);

CREATE TABLE p6_bootstrap_transitions (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'tenant'),
  namespace_scope_id TEXT NOT NULL CHECK (namespace_scope_id = ''),
  transition_id TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('available', 'consumed')),
  active_credential_id TEXT,
  consumed_principal_id TEXT,
  created_by_principal_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, transition_id)
);

CREATE TABLE p6_governance_credentials (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'tenant'),
  namespace_scope_id TEXT NOT NULL CHECK (namespace_scope_id = ''),
  credential_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('enrollment', 'recovery')),
  state TEXT NOT NULL CHECK (
    state IN ('authorized', 'retrieved', 'consumed', 'revoked', 'expired')
  ),
  token_digest TEXT,
  target_principal_id TEXT,
  target_role_revision INTEGER CHECK (
    target_role_revision IS NULL OR target_role_revision > 0
  ),
  target_membership_revision INTEGER CHECK (
    target_membership_revision IS NULL OR target_membership_revision > 0
  ),
  target_role TEXT CHECK (
    target_role IS NULL OR target_role IN ('tenant_admin', 'colleague_user', 'auditor')
  ),
  colleague_scopes_json TEXT NOT NULL,
  bootstrap_transition INTEGER NOT NULL CHECK (bootstrap_transition IN (0, 1)),
  change_decision_id TEXT,
  issued_by_principal_id TEXT NOT NULL,
  issued_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  retrieved_at TEXT,
  consumed_at TEXT,
  revoked_at TEXT,
  consumed_principal_id TEXT,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, credential_id),
  UNIQUE (token_digest),
  CHECK (expires_at > issued_at),
  CHECK (state != 'retrieved' OR (token_digest IS NOT NULL AND retrieved_at IS NOT NULL)),
  CHECK (state != 'consumed' OR consumed_at IS NOT NULL),
  CHECK (state != 'revoked' OR revoked_at IS NOT NULL),
  CHECK (kind != 'recovery' OR target_principal_id IS NOT NULL),
  CHECK (
    kind != 'recovery'
    OR (target_role_revision IS NOT NULL AND target_membership_revision IS NOT NULL)
  ),
  CHECK (
    kind != 'enrollment'
    OR (
      target_role IS NOT NULL
      AND target_role_revision IS NULL
      AND target_membership_revision IS NULL
    )
  )
);

CREATE TABLE p6_change_proposals (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope IN ('tenant', 'colleague')),
  namespace_scope_id TEXT NOT NULL,
  proposal_id TEXT NOT NULL,
  change_kind TEXT NOT NULL CHECK (
    change_kind IN ('draft', 'membership', 'admin_enrollment')
  ),
  target_id TEXT NOT NULL,
  target_revision INTEGER NOT NULL CHECK (target_revision > 0),
  canonical_digest TEXT NOT NULL,
  base_profile_revision INTEGER NOT NULL CHECK (base_profile_revision >= 0),
  base_mandate_revision INTEGER NOT NULL CHECK (base_mandate_revision >= 0),
  base_policy_revision INTEGER NOT NULL CHECK (base_policy_revision >= 0),
  proposed_role TEXT CHECK (
    proposed_role IS NULL OR proposed_role IN ('tenant_admin', 'colleague_user', 'auditor')
  ),
  proposed_status TEXT CHECK (
    proposed_status IS NULL OR proposed_status IN ('active', 'revoked')
  ),
  proposed_scopes_json TEXT NOT NULL,
  proposer_principal_id TEXT NOT NULL,
  proposer_role_revision INTEGER NOT NULL CHECK (proposer_role_revision > 0),
  proposer_membership_revision INTEGER NOT NULL CHECK (proposer_membership_revision > 0),
  issued_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  state TEXT NOT NULL CHECK (
    state IN ('pending', 'approved', 'rejected', 'expired', 'stale', 'applied')
  ),
  decision_id TEXT,
  consumed_at TEXT,
  idempotency_key TEXT NOT NULL,
  request_digest TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, proposal_id),
  UNIQUE (
    tenant_id, namespace_scope, namespace_scope_id,
    proposer_principal_id, idempotency_key
  ),
  CHECK (expires_at > issued_at),
  CHECK (namespace_scope != 'tenant' OR namespace_scope_id = ''),
  CHECK (state != 'applied' OR consumed_at IS NOT NULL)
);

CREATE TABLE p6_change_decisions (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope IN ('tenant', 'colleague')),
  namespace_scope_id TEXT NOT NULL,
  decision_id TEXT NOT NULL,
  proposal_id TEXT NOT NULL,
  proposal_revision INTEGER NOT NULL CHECK (proposal_revision > 0),
  proposal_digest TEXT NOT NULL,
  choice TEXT NOT NULL CHECK (choice IN ('approve', 'reject')),
  approver_principal_id TEXT NOT NULL,
  approver_role_revision INTEGER NOT NULL CHECK (approver_role_revision > 0),
  approver_membership_revision INTEGER NOT NULL CHECK (approver_membership_revision > 0),
  occurred_at TEXT NOT NULL,
  valid_until TEXT NOT NULL,
  consumed_at TEXT,
  idempotency_key TEXT NOT NULL,
  request_digest TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, decision_id),
  UNIQUE (tenant_id, namespace_scope, namespace_scope_id, proposal_id),
  UNIQUE (
    tenant_id, namespace_scope, namespace_scope_id,
    approver_principal_id, idempotency_key
  ),
  FOREIGN KEY (
    tenant_id, namespace_scope, namespace_scope_id, proposal_id
  ) REFERENCES p6_change_proposals (
    tenant_id, namespace_scope, namespace_scope_id, proposal_id
  ) ON DELETE RESTRICT,
  CHECK (valid_until >= occurred_at)
);

CREATE TABLE p6_effect_approval_bindings (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'colleague'),
  namespace_scope_id TEXT NOT NULL,
  approval_decision_id TEXT NOT NULL,
  principal_id TEXT NOT NULL,
  principal_revision INTEGER NOT NULL CHECK (principal_revision > 0),
  role_revision INTEGER NOT NULL CHECK (role_revision > 0),
  membership_revision INTEGER NOT NULL CHECK (membership_revision > 0),
  proposal_id TEXT NOT NULL,
  proposal_revision INTEGER NOT NULL CHECK (proposal_revision > 0),
  proposal_digest TEXT NOT NULL,
  valid_until TEXT NOT NULL,
  consumed_at TEXT,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (
    tenant_id, namespace_scope, namespace_scope_id, approval_decision_id
  )
);

CREATE TABLE p6_governance_audit (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (
    namespace_scope IN ('tenant', 'colleague', 'principal')
  ),
  namespace_scope_id TEXT NOT NULL,
  audit_id TEXT NOT NULL,
  record_type TEXT NOT NULL,
  record_id TEXT NOT NULL,
  record_revision INTEGER NOT NULL CHECK (record_revision > 0),
  action TEXT NOT NULL,
  result TEXT NOT NULL,
  actor_principal_id TEXT NOT NULL,
  actor_kind TEXT NOT NULL CHECK (actor_kind IN ('human', 'model', 'service')),
  authority_revision TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  safe_digest TEXT NOT NULL,
  safe_projection_json TEXT NOT NULL,
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, audit_id),
  UNIQUE (
    tenant_id, namespace_scope, namespace_scope_id,
    record_type, record_id, record_revision, action
  ),
  CHECK (namespace_scope != 'tenant' OR namespace_scope_id = '')
);

CREATE INDEX idx_p6_membership_principal
  ON p6_memberships (tenant_id, principal_id, status, membership_revision);

CREATE INDEX idx_p6_credential_lookup
  ON p6_governance_credentials (token_digest, state, expires_at);

CREATE INDEX idx_p6_change_status
  ON p6_change_proposals (
    tenant_id, namespace_scope, namespace_scope_id, state, expires_at, proposal_id
  );

CREATE INDEX idx_p6_audit_export
  ON p6_governance_audit (
    tenant_id, namespace_scope, namespace_scope_id, occurred_at, record_type, record_id
  );
