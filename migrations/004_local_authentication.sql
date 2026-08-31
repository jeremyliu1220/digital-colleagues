-- SPDX-License-Identifier: Apache-2.0
CREATE TABLE p4_bootstrap_credentials (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'tenant'),
  namespace_scope_id TEXT NOT NULL CHECK (namespace_scope_id = ''),
  credential_id TEXT NOT NULL,
  token_digest TEXT NOT NULL,
  issued_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  retrieved_at TEXT,
  consumed_at TEXT,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, credential_id),
  UNIQUE (token_digest),
  CHECK (expires_at > issued_at),
  CHECK (consumed_at IS NULL OR retrieved_at IS NOT NULL)
);

CREATE TABLE p4_sessions (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'principal'),
  namespace_scope_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  principal_record_type TEXT NOT NULL DEFAULT 'principal'
    CHECK (principal_record_type = 'principal'),
  principal_id TEXT NOT NULL,
  credential_digest TEXT NOT NULL,
  csrf_digest TEXT NOT NULL,
  active_colleague_id TEXT,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  revoked_at TEXT,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, session_id),
  UNIQUE (credential_digest),
  FOREIGN KEY (
    tenant_id, namespace_scope, namespace_scope_id, principal_record_type, principal_id
  ) REFERENCES domain_records (
    tenant_id, namespace_scope, namespace_scope_id, record_type, record_id
  ) ON DELETE RESTRICT,
  CHECK (namespace_scope_id = principal_id),
  CHECK (expires_at > created_at)
);

CREATE TABLE p4_mutation_replay (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'principal'),
  namespace_scope_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  action TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  request_digest TEXT NOT NULL,
  result_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (
    tenant_id, namespace_scope, namespace_scope_id, action, idempotency_key
  ),
  FOREIGN KEY (
    tenant_id, namespace_scope, namespace_scope_id, session_id
  ) REFERENCES p4_sessions (
    tenant_id, namespace_scope, namespace_scope_id, session_id
  ) ON DELETE RESTRICT
);

CREATE INDEX idx_p4_bootstrap_exchange
  ON p4_bootstrap_credentials (token_digest, expires_at, consumed_at);

CREATE INDEX idx_p4_session_lookup
  ON p4_sessions (credential_digest, expires_at, revoked_at);
