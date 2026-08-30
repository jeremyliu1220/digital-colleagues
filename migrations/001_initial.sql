-- SPDX-License-Identifier: Apache-2.0
CREATE TABLE domain_records (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL,
  namespace_scope_id TEXT NOT NULL,
  record_type TEXT NOT NULL,
  record_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  immutable INTEGER NOT NULL CHECK (immutable IN (0, 1)),
  payload_json TEXT NOT NULL,
  actor_principal_id TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT,
  occurred_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, record_type, record_id)
);

CREATE TABLE audit_records (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL,
  namespace_scope_id TEXT NOT NULL,
  audit_id TEXT NOT NULL,
  record_type TEXT NOT NULL,
  record_id TEXT NOT NULL,
  record_revision INTEGER NOT NULL CHECK (record_revision > 0),
  actor_principal_id TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT,
  occurred_at TEXT NOT NULL,
  payload_digest TEXT NOT NULL,
  safe_projection_json TEXT NOT NULL,
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, audit_id),
  UNIQUE (
    tenant_id, namespace_scope, namespace_scope_id,
    record_type, record_id, record_revision
  ),
  FOREIGN KEY (
    tenant_id, namespace_scope, namespace_scope_id, record_type, record_id
  ) REFERENCES domain_records (
    tenant_id, namespace_scope, namespace_scope_id, record_type, record_id
  ) ON DELETE RESTRICT
);

CREATE TABLE replay_ledger (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL,
  namespace_scope_id TEXT NOT NULL,
  ledger_kind TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  record_type TEXT NOT NULL,
  record_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (
    tenant_id, namespace_scope, namespace_scope_id, ledger_kind, idempotency_key
  ),
  FOREIGN KEY (
    tenant_id, namespace_scope, namespace_scope_id, record_type, record_id
  ) REFERENCES domain_records (
    tenant_id, namespace_scope, namespace_scope_id, record_type, record_id
  ) ON DELETE RESTRICT
);

CREATE TABLE triggers (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL,
  namespace_scope_id TEXT NOT NULL,
  trigger_id TEXT NOT NULL,
  trigger_kind TEXT NOT NULL,
  event_record_type TEXT NOT NULL DEFAULT 'input_event'
    CHECK (event_record_type = 'input_event'),
  event_id TEXT NOT NULL,
  due_at TEXT NOT NULL,
  state TEXT NOT NULL,
  lease_owner TEXT,
  lease_until TEXT,
  fencing_token INTEGER NOT NULL DEFAULT 0 CHECK (fencing_token >= 0),
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  actor_principal_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, trigger_id),
  UNIQUE (tenant_id, namespace_scope, namespace_scope_id, event_id),
  FOREIGN KEY (
    tenant_id, namespace_scope, namespace_scope_id, event_record_type, event_id
  ) REFERENCES domain_records (
    tenant_id, namespace_scope, namespace_scope_id, record_type, record_id
  ) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE agenda_runtime (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL,
  namespace_scope_id TEXT NOT NULL,
  agenda_item_id TEXT NOT NULL,
  source_key TEXT NOT NULL,
  generation INTEGER NOT NULL CHECK (generation > 0),
  handled_generation INTEGER NOT NULL DEFAULT 0 CHECK (handled_generation >= 0),
  cause_ids_json TEXT NOT NULL,
  state TEXT NOT NULL,
  priority INTEGER NOT NULL,
  due_at TEXT,
  lease_owner TEXT,
  lease_until TEXT,
  fencing_token INTEGER NOT NULL DEFAULT 0 CHECK (fencing_token >= 0),
  starvation_count INTEGER NOT NULL DEFAULT 0 CHECK (starvation_count >= 0),
  current_wake_cycle_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, agenda_item_id),
  UNIQUE (tenant_id, namespace_scope, namespace_scope_id, source_key)
);

CREATE TABLE outbox (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL,
  namespace_scope_id TEXT NOT NULL,
  outbox_id TEXT NOT NULL,
  proposal_id TEXT NOT NULL,
  approval_decision_id TEXT NOT NULL,
  attempt_record_type TEXT NOT NULL DEFAULT 'effect_attempt'
    CHECK (attempt_record_type = 'effect_attempt'),
  effect_attempt_id TEXT NOT NULL,
  effect_idempotency_key TEXT NOT NULL,
  state TEXT NOT NULL,
  attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
  maximum_attempts INTEGER NOT NULL CHECK (maximum_attempts > 0),
  next_attempt_at TEXT NOT NULL,
  lease_owner TEXT,
  lease_until TEXT,
  fencing_token INTEGER NOT NULL DEFAULT 0 CHECK (fencing_token >= 0),
  last_outcome TEXT,
  actor_principal_id TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, outbox_id),
  UNIQUE (
    tenant_id, namespace_scope, namespace_scope_id, effect_idempotency_key
  ),
  FOREIGN KEY (
    tenant_id, namespace_scope, namespace_scope_id,
    attempt_record_type, effect_attempt_id
  ) REFERENCES domain_records (
    tenant_id, namespace_scope, namespace_scope_id, record_type, record_id
  ) ON DELETE RESTRICT
);
