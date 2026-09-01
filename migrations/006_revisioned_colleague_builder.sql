-- SPDX-License-Identifier: Apache-2.0
CREATE TABLE p5_colleague_drafts (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'colleague'),
  namespace_scope_id TEXT NOT NULL,
  draft_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  base_profile_revision INTEGER NOT NULL CHECK (base_profile_revision > 0),
  base_mandate_revision INTEGER NOT NULL CHECK (base_mandate_revision > 0),
  base_policy_revision INTEGER NOT NULL CHECK (base_policy_revision >= 0),
  state TEXT NOT NULL CHECK (
    state IN ('draft', 'reviewable', 'confirmed', 'cancelled', 'stale')
  ),
  canonical_digest TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  author_principal_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, draft_id)
);

CREATE TABLE p5_draft_confirmations (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'colleague'),
  namespace_scope_id TEXT NOT NULL,
  confirmation_id TEXT NOT NULL,
  draft_id TEXT NOT NULL,
  draft_revision INTEGER NOT NULL CHECK (draft_revision > 0),
  canonical_digest TEXT NOT NULL,
  profile_revision INTEGER NOT NULL CHECK (profile_revision > 0),
  mandate_revision INTEGER NOT NULL CHECK (mandate_revision > 0),
  policy_revision INTEGER NOT NULL CHECK (policy_revision > 0),
  idempotency_key TEXT NOT NULL,
  request_digest TEXT NOT NULL,
  result_json TEXT NOT NULL,
  actor_principal_id TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, confirmation_id),
  UNIQUE (tenant_id, namespace_scope, namespace_scope_id, idempotency_key),
  FOREIGN KEY (tenant_id, namespace_scope, namespace_scope_id, draft_id)
    REFERENCES p5_colleague_drafts (
      tenant_id, namespace_scope, namespace_scope_id, draft_id
    ) ON DELETE RESTRICT
);

CREATE TABLE p5_draft_audit (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'colleague'),
  namespace_scope_id TEXT NOT NULL,
  audit_id TEXT NOT NULL,
  draft_id TEXT NOT NULL,
  draft_revision INTEGER NOT NULL CHECK (draft_revision > 0),
  state TEXT NOT NULL CHECK (
    state IN ('draft', 'reviewable', 'confirmed', 'cancelled', 'stale')
  ),
  action TEXT NOT NULL CHECK (
    action IN ('created', 'updated', 'reviewed', 'confirmed', 'cancelled', 'stale_refused')
  ),
  actor_principal_id TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  payload_digest TEXT NOT NULL,
  safe_projection_json TEXT NOT NULL,
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, audit_id),
  FOREIGN KEY (tenant_id, namespace_scope, namespace_scope_id, draft_id)
    REFERENCES p5_colleague_drafts (
      tenant_id, namespace_scope, namespace_scope_id, draft_id
    ) ON DELETE RESTRICT
);

CREATE TABLE p5_policy_outcomes (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'colleague'),
  namespace_scope_id TEXT NOT NULL,
  outcome_id TEXT NOT NULL,
  policy_id TEXT NOT NULL,
  policy_revision INTEGER NOT NULL CHECK (policy_revision > 0),
  mandate_id TEXT NOT NULL,
  mandate_revision INTEGER NOT NULL CHECK (mandate_revision > 0),
  stage TEXT NOT NULL CHECK (
    stage IN ('trigger', 'pre_wake', 'post_model', 'approval', 'dispatch', 'stop', 'escalation')
  ),
  outcome TEXT NOT NULL,
  trigger_class TEXT,
  source_id TEXT,
  actor_principal_id TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  safe_projection_json TEXT NOT NULL,
  payload_digest TEXT NOT NULL,
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, outcome_id)
);

CREATE TABLE p5_wake_budget_counters (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'colleague'),
  namespace_scope_id TEXT NOT NULL,
  policy_id TEXT NOT NULL,
  policy_revision INTEGER NOT NULL CHECK (policy_revision > 0),
  period TEXT NOT NULL CHECK (period IN ('hour', 'day', 'week')),
  bucket_start TEXT NOT NULL,
  consumed_count INTEGER NOT NULL CHECK (consumed_count >= 0),
  updated_at TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (
    tenant_id, namespace_scope, namespace_scope_id,
    policy_id, policy_revision, period, bucket_start
  )
);

CREATE TABLE p5_wake_budget_consumptions (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'colleague'),
  namespace_scope_id TEXT NOT NULL,
  occurrence_key TEXT NOT NULL,
  policy_id TEXT NOT NULL,
  policy_revision INTEGER NOT NULL CHECK (policy_revision > 0),
  period TEXT NOT NULL CHECK (period IN ('hour', 'day', 'week')),
  bucket_start TEXT NOT NULL,
  trigger_class TEXT NOT NULL CHECK (trigger_class IN ('event', 'timer')),
  source_id TEXT NOT NULL,
  consumed_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, occurrence_key),
  FOREIGN KEY (
    tenant_id, namespace_scope, namespace_scope_id,
    policy_id, policy_revision, period, bucket_start
  ) REFERENCES p5_wake_budget_counters (
    tenant_id, namespace_scope, namespace_scope_id,
    policy_id, policy_revision, period, bucket_start
  ) ON DELETE RESTRICT
);

CREATE TABLE p5_run_states (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'colleague'),
  namespace_scope_id TEXT NOT NULL,
  policy_id TEXT NOT NULL,
  policy_revision INTEGER NOT NULL CHECK (policy_revision > 0),
  state TEXT NOT NULL CHECK (state IN ('active', 'stopped')),
  reason TEXT NOT NULL,
  actor_principal_id TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id)
);

CREATE TABLE p5_escalations (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'colleague'),
  namespace_scope_id TEXT NOT NULL,
  escalation_id TEXT NOT NULL,
  policy_id TEXT NOT NULL,
  policy_revision INTEGER NOT NULL CHECK (policy_revision > 0),
  condition TEXT NOT NULL CHECK (
    condition IN ('outside_hours', 'budget_exhausted', 'repeated_failure', 'blocked_work')
  ),
  status TEXT NOT NULL CHECK (status = 'open'),
  safe_summary TEXT NOT NULL,
  actor_principal_id TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, escalation_id)
);

CREATE INDEX idx_p5_drafts_state
  ON p5_colleague_drafts (
    tenant_id, namespace_scope, namespace_scope_id, state, updated_at, draft_id
  );

CREATE INDEX idx_p5_policy_outcomes_correlation
  ON p5_policy_outcomes (
    tenant_id, namespace_scope, namespace_scope_id, correlation_id, occurred_at
  );

CREATE INDEX idx_p5_draft_audit_correlation
  ON p5_draft_audit (
    tenant_id, namespace_scope, namespace_scope_id, correlation_id, occurred_at
  );

CREATE INDEX idx_p5_escalations_status
  ON p5_escalations (
    tenant_id, namespace_scope, namespace_scope_id, status, occurred_at
  );
