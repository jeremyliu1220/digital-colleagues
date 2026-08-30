-- SPDX-License-Identifier: Apache-2.0
CREATE TABLE timer_triggers (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL,
  namespace_scope_id TEXT NOT NULL,
  trigger_id TEXT NOT NULL,
  trigger_kind TEXT NOT NULL DEFAULT 'timer' CHECK (trigger_kind = 'timer'),
  occurrence_record_type TEXT NOT NULL DEFAULT 'timer_occurrence'
    CHECK (occurrence_record_type = 'timer_occurrence'),
  occurrence_id TEXT NOT NULL,
  timer_id TEXT NOT NULL,
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
  UNIQUE (tenant_id, namespace_scope, namespace_scope_id, occurrence_id),
  FOREIGN KEY (
    tenant_id, namespace_scope, namespace_scope_id,
    occurrence_record_type, occurrence_id
  ) REFERENCES domain_records (
    tenant_id, namespace_scope, namespace_scope_id, record_type, record_id
  ) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX idx_timer_trigger_claim
  ON timer_triggers (
    tenant_id, namespace_scope, namespace_scope_id,
    state, due_at, lease_until, trigger_id
  );
