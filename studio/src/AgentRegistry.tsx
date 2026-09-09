// SPDX-License-Identifier: Apache-2.0

import { ChangeEvent, useCallback, useEffect, useState } from "react";

import { t } from "./i18n";

export type PackageRecord = {
  package: {
    metadata: {
      package_id: string;
      version: string;
      display: Record<string, { name: string }>;
    };
    content: { requested_capabilities: string[] };
  };
  package_digest: string;
  archive_digest: string;
  source: string;
  trust_state: string;
  install_state: string;
  attestation: null | {
    verification: string;
    artifact_digest: string;
    signer: string;
    signer_digest: string;
    repository: string;
    workflow: string;
    build_identity: string;
    source_ref: string;
    source_digest: string;
    predicate_type: string;
  };
  revision: number;
};

type Deployment = {
  deployment_id: string;
  package_id: string;
  package_version: string;
  package_digest: string;
  lifecycle: "draft" | "active" | "paused" | "blocked" | "retired";
  legacy_manual: boolean;
  legacy_policy_unconfirmed: boolean;
  revision: number;
};

type Draft = {
  namespace: { scope_id: string };
  draft_id: string;
  kind: string;
  canonical_digest: string;
  permission_diff: {
    requested: string[];
    granted: string[];
    admin_extra: string[];
    not_granted: string[];
  };
  state: string;
  revision: number;
};

type Inspection = {
  package: PackageRecord["package"];
  package_digest: string;
  archive_digest: string;
  compressed_size: number;
  uncompressed_size: number;
};

type LocalArchive = {
  archiveBase64: string;
  inspection: Inspection;
};

type AuditRecord = {
  action: string;
  result: string;
  record_type: string;
  record_id: string;
  record_revision: number;
  actor_principal_id: string;
  correlation_id: string;
  causation_id: string;
  occurred_at: string;
};

const CAPABILITY_OPTIONS = [
  "read_work",
  "manage_work",
  "propose_reference_message",
  "propose_internal_record",
  "notify_human",
  "read_audit",
] as const;

const EFFECT_CAPABILITIES = new Set([
  "propose_reference_message",
  "propose_internal_record",
  "notify_human",
]);

// eslint-disable-next-line react-refresh/only-export-components
export function deploymentDraftBody(
  record: PackageRecord,
  deploymentId: string,
  grantedCapabilities: string[],
  extraConfirmed: boolean,
  idempotencyKey: string,
) {
  const requested = new Set(record.package.content.requested_capabilities);
  const adminExtra = grantedCapabilities.filter(
    (value) => !requested.has(value),
  );
  if (
    !deploymentId.trim() ||
    grantedCapabilities.length === 0 ||
    !grantedCapabilities.some((value) => EFFECT_CAPABILITIES.has(value)) ||
    (adminExtra.length > 0 && !extraConfirmed)
  ) {
    throw new Error(t("registry.deployment_input_required"));
  }
  return {
    deployment_id: deploymentId.trim(),
    package_id: record.package.metadata.package_id,
    package_version: record.package.metadata.version,
    package_digest: record.package_digest,
    display_name:
      record.package.metadata.display["en-US"]?.name ||
      record.package.metadata.package_id,
    description: t("registry.default_description"),
    mission: t("registry.default_mission"),
    service_relationship: t("registry.default_relationship"),
    granted_capabilities: [...grantedCapabilities].sort(),
    timezone: "UTC",
    idempotency_key: idempotencyKey,
  };
}

export function AuthoritySelection({
  requested,
  granted,
  busy,
  extraConfirmed,
  onToggle,
  onConfirmExtra,
}: {
  requested: string[];
  granted: string[];
  busy: boolean;
  extraConfirmed: boolean;
  onToggle: (capability: string) => void;
  onConfirmExtra: (confirmed: boolean) => void;
}) {
  const requestedSet = new Set(requested);
  const adminExtra = granted.filter((value) => !requestedSet.has(value));
  return (
    <fieldset className="registry-authority" disabled={busy}>
      <legend>{t("registry.select_capabilities")}</legend>
      <p>{t("registry.select_capabilities_help")}</p>
      <div className="registry-capabilities">
        {CAPABILITY_OPTIONS.map((capability) => (
          <label key={capability}>
            <input
              type="checkbox"
              value={capability}
              checked={granted.includes(capability)}
              onChange={() => onToggle(capability)}
            />
            <span>{capability}</span>
            <small>
              {t(
                requestedSet.has(capability)
                  ? "registry.capability_requested"
                  : "registry.capability_not_requested",
              )}
            </small>
          </label>
        ))}
      </div>
      {!granted.some((value) => EFFECT_CAPABILITIES.has(value)) && (
        <p className="registry-authority-warning" role="status">
          {t("registry.effect_required")}
        </p>
      )}
      {adminExtra.length > 0 && (
        <div className="registry-extra-warning" role="alert">
          <strong>{t("registry.admin_extra")}</strong>
          <p>{adminExtra.join(" · ")}</p>
          <p>{t("registry.extra_warning")}</p>
          <label>
            <input
              type="checkbox"
              value="confirm_admin_extra"
              checked={extraConfirmed}
              onChange={(event) => onConfirmExtra(event.target.checked)}
            />
            {t("registry.confirm_extra")}
          </label>
        </div>
      )}
    </fieldset>
  );
}

async function request<T>(
  path: string,
  csrf: string,
  body?: object,
): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    method: body ? "POST" : "GET",
    credentials: "same-origin",
    headers: body
      ? { "Content-Type": "application/json", "X-CSRF-Token": csrf }
      : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const failure = (await response.json().catch(() => ({}))) as {
      detail?: { code?: string; message?: string };
    };
    throw new Error(
      failure.detail?.message ||
        failure.detail?.code ||
        `p11:${response.status}`,
    );
  }
  return (await response.json()) as T;
}

function key(prefix: string) {
  return `${prefix}-${Date.now()}-${crypto.getRandomValues(new Uint32Array(1))[0]}`;
}

export function AgentRegistry({
  csrf,
  canManage,
  initialPackages = [],
  initialDeployments = [],
}: {
  csrf: string;
  canManage: boolean;
  initialPackages?: PackageRecord[];
  initialDeployments?: Deployment[];
}) {
  const [packages, setPackages] = useState<PackageRecord[]>(initialPackages);
  const [deployments, setDeployments] =
    useState<Deployment[]>(initialDeployments);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [localArchive, setLocalArchive] = useState<LocalArchive | null>(null);
  const [deploymentId, setDeploymentId] = useState("");
  const [targetDigest, setTargetDigest] = useState("");
  const [grantedCapabilities, setGrantedCapabilities] = useState<string[]>([]);
  const [extraConfirmed, setExtraConfirmed] = useState(false);
  const [audit, setAudit] = useState<AuditRecord[]>([]);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const selectedPackage = packages.find(
    (record) =>
      record.package_digest === targetDigest &&
      record.trust_state === "trusted" &&
      record.install_state === "installed",
  );
  const selectedRequested =
    selectedPackage?.package.content.requested_capabilities ?? [];
  const selectedAdminExtra = grantedCapabilities.filter(
    (value) => !selectedRequested.includes(value),
  );
  const canCreateDraft = Boolean(
    !busy &&
    selectedPackage &&
    deploymentId.trim() &&
    grantedCapabilities.some((value) => EFFECT_CAPABILITIES.has(value)) &&
    (selectedAdminExtra.length === 0 || extraConfirmed),
  );

  const refresh = useCallback(async () => {
    const [nextPackages, nextDeployments, nextDrafts] = await Promise.all([
      request<PackageRecord[]>("/catalog", csrf),
      request<Deployment[]>("/deployments", csrf),
      request<Draft[]>("/deployment-drafts", csrf),
    ]);
    setPackages(nextPackages);
    setDeployments(nextDeployments);
    setDrafts(nextDrafts);
  }, [csrf]);

  useEffect(() => {
    const pending = window.setTimeout(() => {
      void refresh().catch(() => setNotice(t("registry.load_failed")));
    }, 0);
    return () => window.clearTimeout(pending);
  }, [refresh]);

  async function mutate(label: string, operation: () => Promise<unknown>) {
    setBusy(label);
    setNotice("");
    try {
      await operation();
      await refresh();
      setNotice(t("registry.completed", { operation: label }));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : t("registry.error"));
    } finally {
      setBusy("");
    }
  }

  async function packageAction(
    record: PackageRecord,
    action: "trust" | "revoke" | "install",
  ) {
    const metadata = record.package.metadata;
    const labels = {
      trust: t("registry.trust"),
      revoke: t("registry.revoke"),
      install: t("registry.install"),
    };
    await mutate(labels[action], () =>
      request(
        `/agent-packages/${metadata.package_id}/versions/${metadata.version}/${record.package_digest}/${action}`,
        csrf,
        { expected_revision: record.revision, idempotency_key: key(action) },
      ),
    );
  }

  async function lifecycle(deployment: Deployment, target: string) {
    const labels: Record<string, string> = {
      active: t("registry.activate"),
      paused: t("registry.pause"),
      blocked: t("registry.block"),
      retired: t("registry.retire"),
    };
    await mutate(labels[target] || t("common.operation_failed"), () =>
      request(`/deployments/${deployment.deployment_id}/lifecycle`, csrf, {
        target,
        expected_revision: deployment.revision,
        expected_package_digest: deployment.package_digest,
        idempotency_key: key(target),
      }),
    );
  }

  async function validateArchive(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || file.size > 131072) {
      setNotice(t("registry.validation_failed"));
      return;
    }
    setBusy(t("registry.validate"));
    setNotice("");
    try {
      const buffer = await file.arrayBuffer();
      const bytes = new Uint8Array(buffer);
      let binary = "";
      for (const value of bytes) binary += String.fromCharCode(value);
      const hash = await crypto.subtle.digest("SHA-256", buffer);
      const expected = `sha256:${Array.from(new Uint8Array(hash), (value) =>
        value.toString(16).padStart(2, "0"),
      ).join("")}`;
      const inspection = await request<Inspection>(
        "/agent-packages/validate",
        csrf,
        {
          archive_base64: btoa(binary),
          expected_archive_digest: expected,
        },
      );
      setLocalArchive({ archiveBase64: btoa(binary), inspection });
      setNotice(t("registry.validation_ready"));
    } catch (error) {
      setLocalArchive(null);
      setNotice(
        error instanceof Error
          ? `${t("registry.validation_failed")} ${error.message}`
          : t("registry.validation_failed"),
      );
    } finally {
      setBusy("");
    }
  }

  async function registerLocal() {
    if (!localArchive) return;
    await mutate(t("registry.register"), () =>
      request("/agent-packages", csrf, {
        archive_base64: localArchive.archiveBase64,
        expected_archive_digest: localArchive.inspection.archive_digest,
        source: "local",
        idempotency_key: key("register"),
      }),
    );
    setLocalArchive(null);
  }

  async function createDeployment() {
    if (!selectedPackage) {
      setNotice(t("registry.deployment_input_required"));
      return;
    }
    let body: ReturnType<typeof deploymentDraftBody>;
    try {
      body = deploymentDraftBody(
        selectedPackage,
        deploymentId,
        grantedCapabilities,
        extraConfirmed,
        key("create-draft"),
      );
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : t("registry.deployment_input_required"),
      );
      return;
    }
    await mutate(t("registry.create_draft"), () =>
      request("/deployment-drafts", csrf, body),
    );
    setDeploymentId("");
    setTargetDigest("");
    setGrantedCapabilities([]);
    setExtraConfirmed(false);
  }

  function toggleGrant(capability: string) {
    setGrantedCapabilities((current) =>
      current.includes(capability)
        ? current.filter((value) => value !== capability)
        : [...current, capability],
    );
    setExtraConfirmed(false);
  }

  async function draftAction(draft: Draft, action: "review" | "confirm") {
    const labels = {
      review: t("registry.review"),
      confirm: t("registry.confirm"),
    };
    await mutate(labels[action], () =>
      request(`/deployment-drafts/${draft.draft_id}/${action}`, csrf, {
        deployment_id: draft.namespace.scope_id,
        expected_revision: draft.revision,
        expected_canonical_digest: draft.canonical_digest,
        idempotency_key: key(action),
      }),
    );
  }

  async function rebinding(
    deployment: Deployment,
    action: "upgrade" | "rollback",
  ) {
    const selected = packages.find(
      (record) => record.package_digest === targetDigest,
    );
    if (!selected) {
      setNotice(t("registry.package_target_required"));
      return;
    }
    await mutate(
      action === "upgrade" ? t("registry.upgrade") : t("registry.rollback"),
      () =>
        request(
          `/deployments/${deployment.deployment_id}/${action}-drafts`,
          csrf,
          {
            package_id: selected.package.metadata.package_id,
            package_version: selected.package.metadata.version,
            package_digest: selected.package_digest,
            expected_deployment_revision: deployment.revision,
            idempotency_key: key(action),
          },
        ),
    );
  }

  async function selectDeployment(deployment: Deployment) {
    await mutate(t("registry.select"), () =>
      request(`/deployments/${deployment.deployment_id}/select`, csrf, {
        idempotency_key: key("select"),
      }),
    );
  }

  async function loadAudit(deployment: Deployment) {
    setBusy(t("registry.audit"));
    setNotice("");
    try {
      setAudit(
        await request<AuditRecord[]>(
          `/deployments/${deployment.deployment_id}/audit`,
          csrf,
        ),
      );
      setNotice(t("registry.audit_loaded"));
    } catch {
      setNotice(t("registry.refused"));
    } finally {
      setBusy("");
    }
  }

  return (
    <section
      className="workspace-view registry-view"
      aria-labelledby="registry-title"
    >
      <div className="view-heading">
        <div>
          <p className="section-kicker">{t("registry.kicker")}</p>
          <h1 id="registry-title">{t("registry.title")}</h1>
          <p>{t("registry.boundary")}</p>
        </div>
        <label className="registry-file">
          {t("registry.validate")}
          <input
            type="file"
            accept=".zip,application/zip"
            onChange={(event) => void validateArchive(event)}
          />
        </label>
      </div>
      <div className="registry-limit" role="status">
        {t("registry.active_limit", {
          count: deployments.filter((item) => item.lifecycle === "active")
            .length,
        })}
      </div>
      {localArchive && (
        <section
          className="registry-inspection"
          aria-labelledby="inspection-title"
        >
          <div>
            <h2 id="inspection-title">{t("registry.validation_result")}</h2>
            <strong>
              {localArchive.inspection.package.metadata.display["en-US"]?.name}{" "}
              · {localArchive.inspection.package.metadata.version}
            </strong>
            <p className="mono">{localArchive.inspection.package_digest}</p>
            <p>
              {t("registry.archive_sizes", {
                compressed: localArchive.inspection.compressed_size,
                uncompressed: localArchive.inspection.uncompressed_size,
              })}
            </p>
            <p>{t("registry.inert_notice")}</p>
          </div>
          {canManage && (
            <button
              disabled={Boolean(busy)}
              onClick={() => void registerLocal()}
            >
              {t("registry.register")}
            </button>
          )}
        </section>
      )}
      {canManage && (
        <section className="registry-compose" aria-labelledby="compose-title">
          <div>
            <h2 id="compose-title">{t("registry.compose")}</h2>
            <p>{t("registry.compose_help")}</p>
          </div>
          <label>
            {t("registry.deployment_id")}
            <input
              value={deploymentId}
              onChange={(event) => setDeploymentId(event.target.value)}
              maxLength={128}
              disabled={Boolean(busy)}
            />
          </label>
          <label>
            {t("registry.target_package")}
            <select
              value={targetDigest}
              onChange={(event) => {
                setTargetDigest(event.target.value);
                setGrantedCapabilities([]);
                setExtraConfirmed(false);
              }}
              disabled={Boolean(busy)}
            >
              <option value="">{t("registry.choose_package")}</option>
              {packages
                .filter(
                  (record) =>
                    record.trust_state === "trusted" &&
                    record.install_state === "installed",
                )
                .map((record) => (
                  <option
                    value={record.package_digest}
                    key={record.package_digest}
                  >
                    {record.package.metadata.package_id} ·{" "}
                    {record.package.metadata.version}
                  </option>
                ))}
            </select>
          </label>
          {selectedPackage && (
            <AuthoritySelection
              requested={selectedRequested}
              granted={grantedCapabilities}
              busy={Boolean(busy)}
              extraConfirmed={extraConfirmed}
              onToggle={toggleGrant}
              onConfirmExtra={setExtraConfirmed}
            />
          )}
          <button
            disabled={!canCreateDraft}
            onClick={() => void createDeployment()}
          >
            {t("registry.create_draft")}
          </button>
        </section>
      )}
      <div className="registry-columns">
        <section aria-labelledby="catalog-title">
          <h2 id="catalog-title">{t("registry.catalog")}</h2>
          {packages.length === 0 ? (
            <p>{t("registry.empty_catalog")}</p>
          ) : (
            <ol className="registry-list">
              {packages.map((record) => (
                <li
                  key={`${record.package.metadata.package_id}:${record.package_digest}`}
                >
                  <header>
                    <strong>
                      {record.package.metadata.display["en-US"]?.name}
                    </strong>
                    <span>{record.package.metadata.version}</span>
                  </header>
                  <p className="mono">{record.package_digest}</p>
                  <dl>
                    <dt>{t("registry.package_version")}</dt>
                    <dd>{record.package.metadata.version}</dd>
                    <dt>{t("registry.source")}</dt>
                    <dd>{record.source}</dd>
                    <dt>{t("registry.trust_state")}</dt>
                    <dd>{record.trust_state}</dd>
                    <dt>{t("registry.install_state")}</dt>
                    <dd>{record.install_state}</dd>
                    <dt>{t("registry.requested")}</dt>
                    <dd>
                      {record.package.content.requested_capabilities.join(
                        " · ",
                      )}
                    </dd>
                  </dl>
                  {record.attestation ? (
                    <section
                      className="registry-trust-review"
                      aria-label={t("registry.trust_review")}
                    >
                      <h3>{t("registry.provenance")}</h3>
                      <dl>
                        <dt>{t("registry.verification_result")}</dt>
                        <dd>{record.attestation.verification}</dd>
                        <dt>{t("registry.signer")}</dt>
                        <dd>{record.attestation.signer}</dd>
                        <dt>{t("registry.repository")}</dt>
                        <dd>{record.attestation.repository}</dd>
                        <dt>{t("registry.workflow")}</dt>
                        <dd>{record.attestation.workflow}</dd>
                        <dt>{t("registry.build_identity")}</dt>
                        <dd>{record.attestation.build_identity}</dd>
                        <dt>{t("registry.signer_digest")}</dt>
                        <dd className="mono">
                          {record.attestation.signer_digest}
                        </dd>
                        <dt>{t("registry.artifact_digest")}</dt>
                        <dd className="mono">
                          {record.attestation.artifact_digest}
                        </dd>
                        <dt>{t("registry.archive_digest")}</dt>
                        <dd className="mono">{record.archive_digest}</dd>
                        <dt>{t("registry.source_ref")}</dt>
                        <dd>{record.attestation.source_ref}</dd>
                        <dt>{t("registry.source_digest")}</dt>
                        <dd className="mono">
                          {record.attestation.source_digest}
                        </dd>
                        <dt>{t("registry.predicate_type")}</dt>
                        <dd>{record.attestation.predicate_type}</dd>
                      </dl>
                      <p className="registry-origin-warning">
                        {t("registry.attestation_origin_only")}
                      </p>
                      <p>{t("registry.trust_independent")}</p>
                      <p className="registry-authority-warning">
                        {deployments.some(
                          (deployment) =>
                            deployment.package_id ===
                              record.package.metadata.package_id &&
                            deployment.package_version ===
                              record.package.metadata.version &&
                            deployment.package_digest === record.package_digest,
                        )
                          ? t("registry.authority_bound")
                          : t("registry.authority_unbound")}
                      </p>
                    </section>
                  ) : (
                    <p>{t("registry.no_attestation")}</p>
                  )}
                  {canManage && (
                    <div className="registry-actions">
                      <button
                        disabled={
                          Boolean(busy) || record.trust_state !== "untrusted"
                        }
                        onClick={() => void packageAction(record, "trust")}
                      >
                        {t("registry.trust")}
                      </button>
                      <button
                        disabled={
                          Boolean(busy) || record.trust_state === "revoked"
                        }
                        onClick={() => void packageAction(record, "revoke")}
                      >
                        {t("registry.revoke")}
                      </button>
                      <button
                        disabled={
                          Boolean(busy) ||
                          record.trust_state !== "trusted" ||
                          record.install_state === "installed"
                        }
                        onClick={() => void packageAction(record, "install")}
                      >
                        {t("registry.install")}
                      </button>
                    </div>
                  )}
                </li>
              ))}
            </ol>
          )}
        </section>
        <section aria-labelledby="deployments-title">
          <h2 id="deployments-title">{t("registry.deployments")}</h2>
          {deployments.length === 0 ? (
            <p>{t("registry.empty_deployments")}</p>
          ) : (
            <ol className="registry-list">
              {deployments.map((deployment) => (
                <li key={deployment.deployment_id}>
                  <header>
                    <strong>{deployment.deployment_id}</strong>
                    <span>{deployment.lifecycle}</span>
                  </header>
                  <p>
                    {deployment.package_id} · {deployment.package_version}
                  </p>
                  <p className="mono">{deployment.package_digest}</p>
                  {deployment.legacy_policy_unconfirmed && (
                    <p>{t("registry.legacy_unconfirmed")}</p>
                  )}
                  <div className="registry-actions">
                    <button
                      disabled={Boolean(busy)}
                      onClick={() => void selectDeployment(deployment)}
                    >
                      {t("registry.select")}
                    </button>
                    <button
                      disabled={Boolean(busy)}
                      onClick={() => void loadAudit(deployment)}
                    >
                      {t("registry.audit")}
                    </button>
                  </div>
                  {canManage && deployment.lifecycle !== "retired" && (
                    <div className="registry-actions">
                      {deployment.lifecycle === "draft" && (
                        <button
                          disabled={Boolean(busy)}
                          onClick={() => void lifecycle(deployment, "active")}
                        >
                          {t("registry.activate")}
                        </button>
                      )}
                      {deployment.lifecycle === "active" && (
                        <button
                          disabled={Boolean(busy)}
                          onClick={() => void lifecycle(deployment, "paused")}
                        >
                          {t("registry.pause")}
                        </button>
                      )}
                      {deployment.lifecycle === "paused" && (
                        <button
                          disabled={Boolean(busy)}
                          onClick={() => void lifecycle(deployment, "active")}
                        >
                          {t("registry.activate")}
                        </button>
                      )}
                      {deployment.lifecycle === "paused" && (
                        <button
                          disabled={Boolean(busy)}
                          onClick={() => void lifecycle(deployment, "blocked")}
                        >
                          {t("registry.block")}
                        </button>
                      )}
                      {deployment.lifecycle === "blocked" && (
                        <button
                          disabled={Boolean(busy)}
                          onClick={() => void lifecycle(deployment, "paused")}
                        >
                          {t("registry.pause")}
                        </button>
                      )}
                      <button
                        disabled={Boolean(busy)}
                        onClick={() => void lifecycle(deployment, "retired")}
                      >
                        {t("registry.retire")}
                      </button>
                      <button
                        disabled={Boolean(busy) || !targetDigest}
                        onClick={() => void rebinding(deployment, "upgrade")}
                      >
                        {t("registry.upgrade")}
                      </button>
                      <button
                        disabled={Boolean(busy) || !targetDigest}
                        onClick={() => void rebinding(deployment, "rollback")}
                      >
                        {t("registry.rollback")}
                      </button>
                    </div>
                  )}
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
      <section aria-labelledby="drafts-title">
        <h2 id="drafts-title">{t("registry.drafts")}</h2>
        <p>{t("registry.draft_boundary")}</p>
        {drafts.map((draft) => (
          <article className="registry-diff" key={draft.draft_id}>
            <strong>
              {draft.kind} · {draft.state} · rev {draft.revision}
            </strong>
            <p className="mono">{draft.canonical_digest}</p>
            <dl>
              <dt>{t("registry.requested")}</dt>
              <dd>{draft.permission_diff.requested.join(" · ")}</dd>
              <dt>{t("registry.granted")}</dt>
              <dd>{draft.permission_diff.granted.join(" · ")}</dd>
              <dt>{t("registry.not_granted")}</dt>
              <dd>
                {draft.permission_diff.not_granted.join(" · ") ||
                  t("common.none")}
              </dd>
              <dt>{t("registry.admin_extra")}</dt>
              <dd>
                {draft.permission_diff.admin_extra.join(" · ") ||
                  t("common.none")}
              </dd>
            </dl>
            {canManage && (
              <div className="registry-actions">
                <button
                  disabled={Boolean(busy) || draft.state !== "draft"}
                  onClick={() => void draftAction(draft, "review")}
                >
                  {t("registry.review")}
                </button>
                <button
                  disabled={Boolean(busy) || draft.state !== "reviewed"}
                  onClick={() => void draftAction(draft, "confirm")}
                >
                  {t("registry.confirm")}
                </button>
              </div>
            )}
          </article>
        ))}
      </section>
      <section aria-labelledby="deployment-audit-title">
        <h2 id="deployment-audit-title">{t("registry.audit")}</h2>
        {audit.length === 0 ? (
          <p>{t("registry.empty_audit")}</p>
        ) : (
          <ol className="registry-list">
            {audit.map((record) => (
              <li
                key={`${record.causation_id}:${record.action}:${record.record_revision}`}
              >
                <header>
                  <strong>{record.action}</strong>
                  <span>{record.result}</span>
                </header>
                <p>
                  {record.record_type} · {record.record_id} · rev{" "}
                  {record.record_revision}
                </p>
                <p className="mono">
                  {record.actor_principal_id} · {record.correlation_id} ·{" "}
                  {record.causation_id}
                </p>
                <time>{record.occurred_at}</time>
              </li>
            ))}
          </ol>
        )}
      </section>
      <p className="sr-live" aria-live="polite">
        {busy || notice}
      </p>
    </section>
  );
}
