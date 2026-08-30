-- SPDX-License-Identifier: Apache-2.0
CREATE INDEX idx_domain_correlation
  ON domain_records (tenant_id, namespace_scope, namespace_scope_id, correlation_id);

CREATE INDEX idx_audit_correlation
  ON audit_records (
    tenant_id, namespace_scope, namespace_scope_id, correlation_id, occurred_at, audit_id
  );

CREATE INDEX idx_trigger_claim
  ON triggers (
    tenant_id, namespace_scope, namespace_scope_id, state, due_at, lease_until, trigger_id
  );

CREATE INDEX idx_agenda_attention
  ON agenda_runtime (
    tenant_id, namespace_scope, namespace_scope_id,
    state, priority, starvation_count, due_at, agenda_item_id
  );

CREATE INDEX idx_outbox_claim
  ON outbox (
    tenant_id, namespace_scope, namespace_scope_id,
    state, next_attempt_at, lease_until, outbox_id
  );
