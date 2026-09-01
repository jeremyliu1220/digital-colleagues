-- SPDX-License-Identifier: Apache-2.0
CREATE TABLE p4_metric_observations (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'colleague'),
  namespace_scope_id TEXT NOT NULL,
  observation_id TEXT NOT NULL,
  metric TEXT NOT NULL CHECK (
    metric IN (
      'rebrief_turns',
      'wrong_memory_rate',
      'unnecessary_interruption_rate',
      'human_intervention_count'
    )
  ),
  value INTEGER NOT NULL CHECK (value >= 0),
  opportunity_id TEXT NOT NULL,
  source TEXT NOT NULL,
  evidence_class TEXT NOT NULL CHECK (evidence_class IN ('synthetic', 'offline')),
  scenario_version TEXT NOT NULL,
  policy_version TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, observation_id),
  UNIQUE (
    tenant_id, namespace_scope, namespace_scope_id,
    metric, opportunity_id, source
  ),
  CHECK (
    metric NOT IN ('wrong_memory_rate', 'unnecessary_interruption_rate')
    OR value IN (0, 1)
  )
);

CREATE TABLE p4_proposal_candidate_observations (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  tenant_id TEXT NOT NULL,
  namespace_scope TEXT NOT NULL CHECK (namespace_scope = 'colleague'),
  namespace_scope_id TEXT NOT NULL,
  observation_id TEXT NOT NULL,
  candidate_id TEXT NOT NULL,
  boundary_id TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK (outcome = 'governance_rejected_before_proposal'),
  source TEXT NOT NULL,
  evidence_class TEXT NOT NULL CHECK (evidence_class = 'synthetic'),
  scenario_version TEXT NOT NULL,
  policy_version TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision > 0),
  PRIMARY KEY (tenant_id, namespace_scope, namespace_scope_id, observation_id),
  UNIQUE (tenant_id, namespace_scope, namespace_scope_id, candidate_id)
);

CREATE INDEX idx_p4_metric_observation_readout
  ON p4_metric_observations (
    tenant_id, namespace_scope, namespace_scope_id, metric, observed_at
  );

CREATE INDEX idx_p4_proposal_candidate_escape
  ON p4_proposal_candidate_observations (
    tenant_id, namespace_scope, namespace_scope_id, candidate_id
  );
