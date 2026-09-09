-- SPDX-License-Identifier: Apache-2.0
CREATE TABLE p11_package_versions (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'tenant'),
  namespace_scope_id TEXT NOT NULL CHECK (namespace_scope_id = ''),
  package_id TEXT NOT NULL,
  package_version TEXT NOT NULL,
  package_digest TEXT NOT NULL,
  archive_digest TEXT NOT NULL,
  package_json TEXT NOT NULL,
  source TEXT NOT NULL CHECK (source IN ('official_builtin', 'local', 'github_release')),
  trust_state TEXT NOT NULL CHECK (
    trust_state IN ('untrusted', 'trusted', 'revoked', 'legacy_preserved')
  ),
  install_state TEXT NOT NULL CHECK (install_state IN ('not_installed', 'installed')),
  attestation_json TEXT,
  created_by_principal_id TEXT NOT NULL,
  created_by_kind TEXT NOT NULL CHECK (created_by_kind IN ('human', 'service')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (tenant_id, package_id, package_version, package_digest)
);

CREATE TABLE p11_package_trust_decisions (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  decision_id TEXT NOT NULL,
  package_id TEXT NOT NULL,
  package_version TEXT NOT NULL,
  package_digest TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('trusted', 'revoked')),
  actor_principal_id TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  PRIMARY KEY (tenant_id, decision_id),
  FOREIGN KEY (tenant_id, package_id, package_version, package_digest)
    REFERENCES p11_package_versions (
      tenant_id, package_id, package_version, package_digest
    ) ON DELETE RESTRICT
);

CREATE TABLE p11_deployment_drafts (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'colleague'),
  namespace_scope_id TEXT NOT NULL,
  draft_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('create', 'upgrade', 'rollback')),
  package_id TEXT NOT NULL,
  package_version TEXT NOT NULL,
  package_digest TEXT NOT NULL,
  profile_json TEXT NOT NULL,
  mandate_json TEXT NOT NULL,
  policy_json TEXT NOT NULL,
  base_deployment_revision INTEGER NOT NULL CHECK (base_deployment_revision >= 0),
  permission_diff_json TEXT NOT NULL,
  canonical_digest TEXT NOT NULL,
  state TEXT NOT NULL CHECK (
    state IN ('draft', 'reviewed', 'confirmed', 'stale', 'cancelled')
  ),
  author_principal_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, draft_id),
  FOREIGN KEY (tenant_id, package_id, package_version, package_digest)
    REFERENCES p11_package_versions (
      tenant_id, package_id, package_version, package_digest
    ) ON DELETE RESTRICT
);

CREATE TABLE p11_colleague_deployments (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'colleague'),
  namespace_scope_id TEXT NOT NULL,
  deployment_id TEXT NOT NULL,
  package_id TEXT NOT NULL,
  package_version TEXT NOT NULL,
  package_digest TEXT NOT NULL,
  profile_id TEXT NOT NULL,
  profile_revision INTEGER NOT NULL CHECK (profile_revision > 0),
  mandate_id TEXT NOT NULL,
  mandate_revision INTEGER NOT NULL CHECK (mandate_revision > 0),
  policy_id TEXT,
  policy_revision INTEGER CHECK (policy_revision IS NULL OR policy_revision > 0),
  lifecycle TEXT NOT NULL CHECK (lifecycle IN ('draft', 'active', 'paused', 'blocked', 'retired')),
  execution_host_id TEXT NOT NULL CHECK (execution_host_id = 'local'),
  active_slot INTEGER CHECK (active_slot IS NULL OR active_slot BETWEEN 1 AND 10),
  legacy_manual INTEGER NOT NULL CHECK (legacy_manual IN (0, 1)),
  legacy_policy_unconfirmed INTEGER NOT NULL CHECK (legacy_policy_unconfirmed IN (0, 1)),
  future_connection_slot TEXT CHECK (future_connection_slot IS NULL),
  updated_by_principal_id TEXT NOT NULL,
  updated_by_kind TEXT NOT NULL CHECK (updated_by_kind IN ('human', 'service')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, deployment_id),
  UNIQUE (tenant_id, deployment_id),
  UNIQUE (execution_host_id, active_slot),
  CHECK (namespace_scope_id = deployment_id),
  CHECK ((policy_id IS NULL) = (policy_revision IS NULL)),
  CHECK (legacy_policy_unconfirmed = 0 OR legacy_manual = 1),
  CHECK ((lifecycle = 'active') = (active_slot IS NOT NULL)),
  FOREIGN KEY (tenant_id, package_id, package_version, package_digest)
    REFERENCES p11_package_versions (
      tenant_id, package_id, package_version, package_digest
    ) ON DELETE RESTRICT
);

CREATE TABLE p11_deployment_package_history (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  deployment_id TEXT NOT NULL,
  sequence INTEGER NOT NULL CHECK (sequence > 0),
  package_id TEXT NOT NULL,
  package_version TEXT NOT NULL,
  package_digest TEXT NOT NULL,
  accepted_at TEXT NOT NULL,
  actor_principal_id TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  PRIMARY KEY (tenant_id, deployment_id, sequence),
  UNIQUE (tenant_id, deployment_id, package_id, package_version, package_digest),
  FOREIGN KEY (tenant_id, deployment_id)
    REFERENCES p11_colleague_deployments (tenant_id, deployment_id) ON DELETE RESTRICT,
  FOREIGN KEY (tenant_id, package_id, package_version, package_digest)
    REFERENCES p11_package_versions (
      tenant_id, package_id, package_version, package_digest
    ) ON DELETE RESTRICT
);

CREATE TABLE p11_operation_replay (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope IN ('tenant', 'colleague')),
  namespace_scope_id TEXT NOT NULL,
  operation TEXT NOT NULL,
  actor_principal_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  request_digest TEXT NOT NULL,
  result_json TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  PRIMARY KEY (
    tenant_id, namespace_scope, namespace_scope_id,
    operation, actor_principal_id, idempotency_key
  )
);

CREATE TABLE p11_causal_audit (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (
    namespace_scope IN ('tenant', 'colleague')
  ),
  namespace_scope_id TEXT NOT NULL,
  audit_id TEXT NOT NULL,
  action TEXT NOT NULL,
  result TEXT NOT NULL,
  record_type TEXT NOT NULL,
  record_id TEXT NOT NULL,
  record_revision INTEGER NOT NULL CHECK (record_revision > 0),
  actor_principal_id TEXT NOT NULL,
  actor_kind TEXT NOT NULL CHECK (actor_kind IN ('human', 'service')),
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  safe_projection_json TEXT NOT NULL,
  payload_digest TEXT NOT NULL,
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, audit_id)
);

CREATE TRIGGER p11_active_limit_insert
BEFORE INSERT ON p11_colleague_deployments
WHEN NEW.lifecycle = 'active'
BEGIN
  SELECT CASE WHEN (
    SELECT COUNT(*) FROM p11_colleague_deployments
    WHERE execution_host_id = NEW.execution_host_id
      AND lifecycle = 'active'
  ) >= 10 THEN RAISE(ABORT, 'active_deployment_limit_reached') END;
END;

CREATE TRIGGER p11_active_limit_update
BEFORE UPDATE OF lifecycle ON p11_colleague_deployments
WHEN NEW.lifecycle = 'active' AND OLD.lifecycle != 'active'
BEGIN
  SELECT CASE WHEN (
    SELECT COUNT(*) FROM p11_colleague_deployments
    WHERE execution_host_id = NEW.execution_host_id
      AND lifecycle = 'active'
  ) >= 10 THEN RAISE(ABORT, 'active_deployment_limit_reached') END;
END;

CREATE INDEX idx_p11_package_catalog
  ON p11_package_versions (tenant_id, package_id, package_version, updated_at);
CREATE INDEX idx_p11_deployment_lifecycle
  ON p11_colleague_deployments (tenant_id, execution_host_id, lifecycle, deployment_id);
CREATE INDEX idx_p11_draft_state
  ON p11_deployment_drafts (tenant_id, namespace_scope_id, state, updated_at);
CREATE INDEX idx_p11_audit_lookup
  ON p11_causal_audit (tenant_id, namespace_scope_id, occurred_at, action);

-- One inert compatibility package per tenant that already has a colleague Profile.
INSERT INTO p11_package_versions (
  schema_version, tenant_id, namespace_scope, namespace_scope_id,
  package_id, package_version, package_digest, archive_digest, package_json,
  source, trust_state, install_state, attestation_json,
  created_by_principal_id, created_by_kind, created_at, updated_at,
  correlation_id, causation_id, revision
)
SELECT
  1, profiles.tenant_id, 'tenant', '',
  'legacy-manual', '1.0.0',
  'sha256:060b07c809db61f98486d6feed53042ca7266fb916d4933dc6950ce1d35e23cd',
  'sha256:060b07c809db61f98486d6feed53042ca7266fb916d4933dc6950ce1d35e23cd',
  '{"content":{"prompts":{"en-US":"Preserved legacy/manual compatibility package.","zh-TW":"保留既有手動部署的相容套件。"},"requested_capabilities":["manage_work","read_work"],"workflow":{"entrypoint":"complete","steps":[{"id":"complete","type":"complete"}]}},"content_digest":"sha256:ab12b78f9e0d5d800498453e53a678164297500b6db8134a7f3eed6eb75ad6cb","metadata":{"display":{"en-US":{"name":"Legacy Manual","summary":"Preserved pre-P11 colleague deployment."},"zh-TW":{"name":"既有手動部署","summary":"保留 P11 之前的同事部署。"}},"package_id":"legacy-manual","runtime_api":"1","version":"1.0.0"},"schema":"dc-agent/v1","schema_version":1}',
  'official_builtin', 'legacy_preserved', 'installed', NULL,
  'p11-migration', 'service', MIN(profiles.occurred_at), MIN(profiles.occurred_at),
  'p11-migration', 'migration-008', 1
FROM domain_records AS profiles
WHERE profiles.namespace_scope = 'colleague' AND profiles.record_type = 'profile'
GROUP BY profiles.tenant_id;

-- Preserve every pre-P11 colleague as active without reconstructing authority.
INSERT INTO p11_colleague_deployments (
  schema_version, tenant_id, namespace_scope, namespace_scope_id, deployment_id,
  package_id, package_version, package_digest,
  profile_id, profile_revision, mandate_id, mandate_revision, policy_id, policy_revision,
  lifecycle, execution_host_id, active_slot, legacy_manual, legacy_policy_unconfirmed,
  future_connection_slot, updated_by_principal_id, updated_by_kind,
  created_at, updated_at, correlation_id, causation_id, revision
)
SELECT
  1, p.tenant_id, 'colleague', p.namespace_scope_id, p.namespace_scope_id,
  'legacy-manual', '1.0.0',
  'sha256:060b07c809db61f98486d6feed53042ca7266fb916d4933dc6950ce1d35e23cd',
  p.record_id, p.revision, m.record_id, m.revision, q.record_id, q.revision,
  'active', 'local',
  ROW_NUMBER() OVER (ORDER BY p.tenant_id, p.namespace_scope_id),
  1, CASE WHEN q.record_id IS NULL THEN 1 ELSE 0 END,
  NULL, 'p11-migration', 'service', p.occurred_at, p.occurred_at,
  'p11-migration', 'migration-008', 1
FROM domain_records AS p
JOIN domain_records AS m
  ON m.tenant_id = p.tenant_id
 AND m.namespace_scope = p.namespace_scope
 AND m.namespace_scope_id = p.namespace_scope_id
 AND m.record_type = 'mandate'
LEFT JOIN domain_records AS q
  ON q.tenant_id = p.tenant_id
 AND q.namespace_scope = p.namespace_scope
 AND q.namespace_scope_id = p.namespace_scope_id
 AND q.record_type = 'colleague_policy'
WHERE p.namespace_scope = 'colleague' AND p.record_type = 'profile';

INSERT INTO p11_deployment_package_history (
  schema_version, tenant_id, deployment_id, sequence,
  package_id, package_version, package_digest, accepted_at,
  actor_principal_id, correlation_id, causation_id
)
SELECT
  1, tenant_id, deployment_id, 1, package_id, package_version, package_digest,
  created_at, updated_by_principal_id, correlation_id, causation_id
FROM p11_colleague_deployments;

INSERT INTO p11_causal_audit (
  schema_version, tenant_id, namespace_scope, namespace_scope_id,
  audit_id, action, result, record_type, record_id, record_revision,
  actor_principal_id, actor_kind, correlation_id, causation_id, occurred_at,
  safe_projection_json, payload_digest
)
SELECT
  1, tenant_id, 'colleague', deployment_id,
  'migration-008:' || deployment_id, 'legacy_preserved', 'active',
  'colleague_deployment', deployment_id, 1, 'p11-migration', 'service',
  correlation_id, causation_id, created_at,
  '{"authority_reconstructed":false,"legacy_manual":true}',
  'sha256:8778c5158a089c0d3b3ebc329dde1aa80dff885275f0fe0b29c1b54c83aa0beb'
FROM p11_colleague_deployments;
