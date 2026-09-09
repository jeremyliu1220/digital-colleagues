// SPDX-License-Identifier: Apache-2.0

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { initialLocale, setLocale, t, type Locale } from "./i18n";
import type { TranslationKey } from "./locales/en-US";
import { AgentRegistry } from "./AgentRegistry";

type Phase = "checking" | "bootstrap" | "builder" | "workspace";
type View =
  | "identity"
  | "builder"
  | "work"
  | "wake"
  | "proposals"
  | "audit"
  | "governance"
  | "registry";
type NoticeKind =
  | "success"
  | "validation"
  | "permission"
  | "rejection"
  | "stale"
  | "conflict"
  | "cancelled"
  | "revoked"
  | "error";

type Session = {
  authenticated: boolean;
  csrf_token: string;
  namespace: { tenant_id: string; scope: string; scope_id: string } | null;
  principal: {
    principal_id: string;
    kind: string;
    roles: string[];
    role_revision?: number;
  };
  membership_revision?: number;
  session_revision?: number;
};

type GovernanceCredential = {
  credential_id: string;
  kind: "enrollment" | "recovery";
  state: "authorized" | "retrieved" | "consumed" | "revoked" | "expired";
  target_principal_id: string | null;
  target_role_revision: number | null;
  target_membership_revision: number | null;
  target_role: string | null;
  colleague_ids: string[];
  bootstrap_transition: boolean;
  issued_at: string;
  expires_at: string;
  revision: number;
};

type GovernanceProposal = {
  proposal_id: string;
  change_kind: "draft" | "membership" | "admin_enrollment";
  target_id: string;
  target_revision: number;
  canonical_digest: string;
  proposer_principal_id: string;
  issued_at: string;
  expires_at: string;
  state: "pending" | "approved" | "rejected" | "expired" | "stale" | "applied";
  decision_id: string | null;
  revision: number;
};

type GovernanceDecision = {
  decision_id: string;
  proposal_id: string;
  proposal_revision: number;
  proposal_digest: string;
  choice: "approve" | "reject";
  approver_principal_id: string;
  valid_until: string;
  consumed_at: string | null;
  revision: number;
};

type GovernanceState = {
  state: "ready";
  session: {
    session_id: string;
    revision: number;
    role_revision: number;
    membership_revision: number;
    expires_at: string;
  };
  membership: {
    principal_id: string;
    roles: string[];
    colleague_ids: string[];
    status: string;
    role_revision: number;
    membership_revision: number;
    revision: number;
  };
  bootstrap_transition_state?: "available" | "consumed";
  credentials: GovernanceCredential[];
  change_proposals: GovernanceProposal[];
  change_decisions: GovernanceDecision[];
  generated_at: string;
};

type ExportRecord = {
  record_type: string;
  record_id: string;
  record_revision: number;
  action: string;
  result: string;
  actor_principal_id: string;
  authority_revision: string;
  correlation_id: string;
  causation_id: string;
  occurred_at: string;
  safe_digest: string;
  safe_projection: Record<string, unknown>;
};

type Work = {
  work_id: string;
  title: string;
  description: string;
  state: string;
  responsibility_ids: string[];
  correlation_id: string;
  mandate_id: string;
  mandate_revision: number;
  policy_id: string | null;
  policy_revision: number | null;
};

type Proposal = {
  proposal_id: string;
  revision: number;
  proposal_digest: string;
  payload_digest: string;
  safe_projection: Record<string, unknown>;
  destination: { kind: string; target: string };
  action: string;
  effect_kind: string;
  effect_boundary: string;
  constraint_parameters: Record<string, unknown>;
  mandate_id: string;
  mandate_revision: number;
  policy_id: string | null;
  policy_revision: number | null;
  actor: { principal_id: string; kind: string };
  namespace: { tenant_id: string; scope: string; scope_id: string };
  expires_at: string;
  approval_status: string;
  correlation_id: string;
  causation_id: string;
};

type Wake = {
  wake_cycle_id: string;
  wake_reason: string;
  trigger_class: "event" | "timer";
  trigger_identity: string;
  agenda_item_id: string;
  agenda_generation: number;
  handled_generation: number;
  correlation_id: string;
  causation_id: string;
  occurred_at: string;
  revision: number;
  decision: null | {
    decision_id: string;
    kind: string;
    rationale: string;
    proposal_id: string | null;
  };
};

type ResponsibilityData = {
  responsibility_id: string;
  description: string;
  obligations: string[];
  completion_conditions: string[];
};
type CapabilityData = { capability_id: string; description: string };
type ConstraintData = { constraint_id: string; description: string };
type ProfileData = {
  display_name: string;
  description: string;
  presentation: { working_style: string; authority_source: boolean };
};
type EffectBoundaryData = {
  boundary_id: string;
  effect_kind: string;
  allowed_destination_kinds: string[];
  allowed_actions: string[];
  constraints: Record<string, unknown>;
  human_approval_required: boolean;
};
type MandateData = {
  mandate_id: string;
  mission: string;
  service_relationship: string;
  responsibilities: ResponsibilityData[];
  capabilities: CapabilityData[];
  constraints: ConstraintData[];
  working_context: Record<string, unknown>;
  effect_boundaries: EffectBoundaryData[];
  revision: number;
};
type AuditRecord = {
  audit_id: string;
  record_type: string;
  record_id: string;
  record_revision: number;
  actor_principal_id: string;
  causation_id: string | null;
  occurred_at: string;
  safe_projection: Record<string, unknown>;
  payload_digest: string;
};

type State = {
  state: "empty" | "ready";
  identity?: {
    profile: ProfileData;
    mandate: MandateData;
    exact_revision: number;
    authority_summary: {
      profile_is_authority: boolean;
      responsibility_count: number;
      capability_count: number;
      constraint_count: number;
      effect_boundaries: EffectBoundaryData[];
    };
  };
  work?: Work[];
  wakes?: Wake[];
  proposals?: Proposal[];
  approvals?: Record<string, unknown>[];
  attempts?: Record<string, unknown>[];
  results?: Record<string, unknown>[];
};

type PolicyData = {
  policy_id: string;
  mandate_id: string;
  mandate_revision: number;
  timezone: string;
  weekly_windows: {
    weekday: string;
    start_minute: number;
    end_minute: number;
  }[];
  allowed_triggers: string[];
  proactivity: string;
  notification: string;
  interruption: string;
  wake_budget: { limit: number; period: string };
  outside_hours: string;
  stop_conditions: string[];
  escalation_conditions: string[];
  failure_limit: number;
  run_state: string;
  revision: number;
};

type DiffData = {
  section: "profile" | "mandate" | "policy";
  path: string;
  classification:
    "added" | "removed" | "changed" | "narrowed" | "expanded" | "unchanged";
  before: { value: unknown };
  after: { value: unknown };
  authoritative: boolean;
};

type DraftData = {
  draft_id: string;
  revision: number;
  base_profile_revision: number;
  base_mandate_revision: number;
  base_policy_revision: number;
  proposed_profile: ProfileData & { profile_id: string; revision: number };
  proposed_mandate: MandateData;
  proposed_policy: PolicyData;
  explicit_defaults: {
    path: string;
    value: { value: unknown };
    source: string;
  }[];
  diff: DiffData[];
  canonical_digest: string;
  state: "draft" | "reviewable" | "confirmed" | "cancelled" | "stale";
};

type DraftEnvelope = {
  draft: DraftData;
  identity_card_preview: Record<string, unknown> & {
    projection_only: boolean;
    active: boolean;
    inert_until_confirmation: boolean;
  };
  review_binding: Record<string, unknown>;
};

type P5State = {
  state: "empty" | "ready";
  active?: {
    identity_card: Record<string, unknown>;
    profile: ProfileData & { profile_id: string; revision: number };
    mandate: MandateData;
    policy: PolicyData | null;
    policy_status: "confirmed" | "legacy_unconfirmed";
    profile_revision: number;
    mandate_revision: number;
    policy_revision: number;
  };
  drafts?: DraftEnvelope[];
  runtime_policy?: {
    budget_count: number;
    run_state: string | null;
    outcomes: { outcome: string; stage: string; policy_revision: number }[];
    escalations: {
      escalation_id: string;
      condition: string;
      safe_summary: string;
    }[];
  };
};

type BuilderData = {
  display_name: string;
  role_description: string;
  service_relationship: string;
  mission: string;
  timezone: string;
  working_context: string;
  working_hours: string;
  working_style: string;
  responsibilities: string;
  capabilities: string;
  constraints: string;
  destination_kind: string;
  action: string;
};

const initialBuilder: BuilderData = {
  display_name: "Atlas",
  role_description: "Operations colleague for finite, reviewable work",
  service_relationship: "Serves the local operator in this reference namespace",
  mission:
    "Advance assigned finite work and propose one exact reference effect",
  timezone: "UTC",
  working_context: "Synthetic local reference work only",
  working_hours: "09:00–17:00; initial display data, not an enforced policy",
  working_style: "Concise, explicit about uncertainty, and easy to supervise",
  responsibilities: "Own assigned finite work",
  capabilities: "Propose a synthetic reference message",
  constraints: "No external network or live-provider effect",
  destination_kind: "reference_channel",
  action: "record_message",
};

const navigation: { id: View; label: TranslationKey; index: string }[] = [
  { id: "identity", label: "nav.identity", index: "01" },
  { id: "builder", label: "nav.builder", index: "02" },
  { id: "work", label: "nav.work", index: "03" },
  { id: "wake", label: "nav.wake", index: "04" },
  { id: "proposals", label: "nav.proposals", index: "05" },
  { id: "audit", label: "nav.audit", index: "06" },
  { id: "governance", label: "nav.governance", index: "07" },
  { id: "registry", label: "nav.registry", index: "08" },
];

function randomKey(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function api<T>(
  path: string,
  options: RequestInit = {},
  csrfToken = "",
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  if (csrfToken) headers.set("X-CSRF-Token", csrfToken);
  const response = await fetch(`/api${path}`, {
    ...options,
    headers,
    credentials: "same-origin",
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as {
      detail?: { code?: string; message?: string };
    };
    const error = new Error(
      t("common.request_failed", { status: response.status }),
    );
    error.name = body.detail?.code || `HTTP_${response.status}`;
    throw error;
  }
  return (await response.json()) as T;
}

function Notice({ kind, message }: { kind: NoticeKind; message: string }) {
  const labels: Record<NoticeKind, TranslationKey> = {
    success: "notice.success",
    validation: "notice.validation",
    permission: "notice.permission",
    rejection: "notice.rejection",
    stale: "notice.stale",
    conflict: "notice.conflict",
    cancelled: "notice.cancelled",
    revoked: "notice.revoked",
    error: "notice.error",
  };
  return (
    <div className={`notice notice-${kind}`} role="status" tabIndex={-1}>
      <span>{t(labels[kind])}</span>
      <p>{message}</p>
    </div>
  );
}

function LanguagePicker({
  locale,
  change,
}: {
  locale: Locale;
  change: (locale: Locale) => void;
}) {
  return (
    <label className="locale-picker">
      {t("nav.language")}
      <select
        aria-label={t("nav.language")}
        value={locale}
        onChange={(event) => change(event.target.value as Locale)}
      >
        <option value="zh-TW">繁體中文</option>
        <option value="en-US">English</option>
      </select>
    </label>
  );
}

function Bootstrap({
  onReady,
  sessionNotice,
}: {
  onReady: (session: Session) => void;
  sessionNotice?: string;
}) {
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const session = await api<Session>("/auth/bootstrap/exchange", {
        method: "POST",
        body: JSON.stringify({ token }),
      });
      setToken("");
      onReady(session);
    } catch {
      setError(t("bootstrap.failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="entry-screen">
      <header className="entry-brand">
        <span className="brand-mark">{t("common.dc")}</span>
        <div>
          <strong>{t("product.name")}</strong>
          <span>{t("bootstrap.subtitle")}</span>
        </div>
      </header>
      <section className="entry-composition" aria-labelledby="bootstrap-title">
        <div className="entry-index" aria-hidden="true">
          {t("bootstrap.index")}
        </div>
        <div className="entry-copy">
          <p className="eyebrow">{t("bootstrap.eyebrow")}</p>
          <h1 id="bootstrap-title">{t("bootstrap.title")}</h1>
          <p>{t("bootstrap.explanation")}</p>
          <form onSubmit={(event) => void submit(event)} className="token-form">
            <label htmlFor="bootstrap-token">{t("bootstrap.token")}</label>
            <div>
              <input
                id="bootstrap-token"
                type="password"
                autoComplete="off"
                value={token}
                onChange={(event) => setToken(event.target.value)}
                required
                minLength={32}
                disabled={busy}
              />
              <button type="submit" disabled={busy}>
                {busy
                  ? t("bootstrap.exchanging")
                  : t("bootstrap.create_session")}
              </button>
            </div>
          </form>
          {sessionNotice && <Notice kind="revoked" message={sessionNotice} />}
          {error && <Notice kind="rejection" message={error} />}
          <p className="boundary-copy">{t("bootstrap.boundary")}</p>
        </div>
        <div className="entry-ledger" aria-label={t("bootstrap.security_aria")}>
          {[
            ["256+", t("bootstrap.entropy")],
            ["01", t("bootstrap.exchange")],
            ["≤10m", t("bootstrap.lifetime")],
            ["HTTP", t("bootstrap.cookie")],
          ].map(([value, label]) => (
            <div key={label}>
              <strong>{value}</strong>
              <span>{label}</span>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

function Builder({
  csrf,
  onCreated,
}: {
  csrf: string;
  onCreated: () => Promise<void>;
}) {
  const [data, setData] = useState(initialBuilder);
  const [review, setReview] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{
    kind: NoticeKind;
    message: string;
  } | null>(null);

  function update<K extends keyof BuilderData>(key: K, value: BuilderData[K]) {
    setData((current) => ({ ...current, [key]: value }));
  }

  const payload = useMemo(
    () => ({
      ...data,
      responsibilities: data.responsibilities.split("\n").filter(Boolean),
      capabilities: data.capabilities.split("\n").filter(Boolean),
      constraints: data.constraints.split("\n").filter(Boolean),
      effect_kind: "reference_message",
      effect_constraints: { network: false },
      idempotency_key: randomKey("initial-colleague"),
    }),
    [data],
  );

  async function continueToReview(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setNotice(null);
    try {
      await api(
        "/colleagues/preview",
        { method: "POST", body: JSON.stringify(payload) },
        csrf,
      );
      setReview(true);
    } catch {
      setNotice({
        kind: "error",
        message: t("builder.preview_failed"),
      });
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    setBusy(true);
    setNotice(null);
    try {
      await api(
        "/colleagues",
        { method: "POST", body: JSON.stringify(payload) },
        csrf,
      );
      setNotice({
        kind: "success",
        message: t("builder.created"),
      });
      await onCreated();
    } catch (cause) {
      const error =
        cause instanceof Error
          ? cause
          : new Error(t("builder.creation_failed"));
      setNotice({
        kind: error.name === "ConflictError" ? "stale" : "rejection",
        message: error.message,
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="builder-shell">
      <header className="builder-header">
        <div className="brand-lockup">
          <span className="brand-mark">{t("common.dc")}</span>
          <div>
            <strong>{t("builder.initial")}</strong>
            <span>{t("builder.initial_subtitle")}</span>
          </div>
        </div>
        <span className="step-count">
          {review ? t("builder.review") : t("builder.define")} /{" "}
          {t("builder.confirm")}
        </span>
      </header>
      {!review ? (
        <form
          className="builder-grid"
          onSubmit={(event) => void continueToReview(event)}
        >
          <section aria-labelledby="profile-heading">
            <p className="section-kicker">{t("builder.profile_kicker")}</p>
            <h1 id="profile-heading">{t("builder.profile_title")}</h1>
            <p className="section-note">{t("builder.profile_note")}</p>
            <label>
              {t("builder.display_name")}
              <input
                value={data.display_name}
                onChange={(e) => update("display_name", e.target.value)}
                required
              />
            </label>
            <label>
              {t("builder.role_description")}
              <textarea
                value={data.role_description}
                onChange={(e) => update("role_description", e.target.value)}
                required
              />
            </label>
            <label>
              {t("builder.working_style")}
              <textarea
                value={data.working_style}
                onChange={(e) => update("working_style", e.target.value)}
                required
              />
            </label>
          </section>
          <section aria-labelledby="mandate-heading">
            <p className="section-kicker authority-kicker">
              {t("builder.mandate_kicker")}
            </p>
            <h2 id="mandate-heading">{t("builder.mandate_title")}</h2>
            <div className="form-columns">
              <label>
                {t("builder.serves")}
                <textarea
                  value={data.service_relationship}
                  onChange={(e) =>
                    update("service_relationship", e.target.value)
                  }
                  required
                />
              </label>
              <label>
                {t("builder.mission")}
                <textarea
                  value={data.mission}
                  onChange={(e) => update("mission", e.target.value)}
                  required
                />
              </label>
              <label>
                {t("builder.timezone")}
                <input
                  value={data.timezone}
                  onChange={(e) => update("timezone", e.target.value)}
                  required
                />
              </label>
              <label>
                {t("builder.initial_hours")}
                <input
                  value={data.working_hours}
                  onChange={(e) => update("working_hours", e.target.value)}
                  required
                />
              </label>
              <label>
                {t("builder.initial_context")}
                <textarea
                  value={data.working_context}
                  onChange={(e) => update("working_context", e.target.value)}
                  required
                />
              </label>
              <label>
                {t("builder.responsibilities")}
                <textarea
                  value={data.responsibilities}
                  onChange={(e) => update("responsibilities", e.target.value)}
                  required
                />
              </label>
              <label>
                {t("builder.capabilities")}
                <textarea
                  value={data.capabilities}
                  onChange={(e) => update("capabilities", e.target.value)}
                  required
                />
              </label>
              <label>
                {t("builder.constraints_scope")}
                <textarea
                  value={data.constraints}
                  onChange={(e) => update("constraints", e.target.value)}
                  required
                />
              </label>
              <label>
                {t("builder.destination_kind")}
                <input
                  value={data.destination_kind}
                  onChange={(e) => update("destination_kind", e.target.value)}
                  required
                />
              </label>
              <label>
                {t("builder.exact_action")}
                <input
                  value={data.action}
                  onChange={(e) => update("action", e.target.value)}
                  required
                />
              </label>
            </div>
            <button className="primary-action" type="submit" disabled={busy}>
              {busy ? t("builder.preparing") : t("builder.review_exact")}
            </button>
          </section>
        </form>
      ) : (
        <section className="authority-review" aria-labelledby="review-heading">
          <p className="section-kicker">{t("builder.exact_kicker")}</p>
          <h1 id="review-heading">{t("builder.exact_title")}</h1>
          <div className="review-columns">
            <div>
              <span className="review-type descriptive">
                {t("builder.descriptive")}
              </span>
              <h2>{data.display_name}</h2>
              <p>{data.role_description}</p>
              <dl>
                <dt>{t("builder.working_style")}</dt>
                <dd>{data.working_style}</dd>
              </dl>
            </div>
            <div>
              <span className="review-type authoritative">
                {t("builder.authoritative_revision")}
              </span>
              <h2>{data.mission}</h2>
              <dl>
                <dt>{t("builder.service_relationship")}</dt>
                <dd>{data.service_relationship}</dd>
                <dt>{t("builder.responsibility")}</dt>
                <dd>{data.responsibilities}</dd>
                <dt>{t("builder.capability")}</dt>
                <dd>{data.capabilities}</dd>
                <dt>{t("builder.constraint")}</dt>
                <dd>{data.constraints}</dd>
                <dt>{t("builder.effect_boundary")}</dt>
                <dd>
                  {data.destination_kind} → {data.action} ·{" "}
                  {t("builder.human_approval_required")}
                </dd>
                <dt>{t("builder.hours_boundary")}</dt>
                <dd>{t("builder.legacy_hours")}</dd>
              </dl>
            </div>
          </div>
          {notice && <Notice {...notice} />}
          <div className="review-actions">
            <button
              className="quiet-action"
              onClick={() => setReview(false)}
              disabled={busy}
            >
              {t("builder.back")}
            </button>
            <button
              className="primary-action"
              onClick={() => void confirm()}
              disabled={busy}
            >
              {busy ? t("builder.committing") : t("builder.confirm_revision")}
            </button>
          </div>
        </section>
      )}
    </main>
  );
}

type RevisionEdit = {
  displayName: string;
  description: string;
  mission: string;
  serviceRelationship: string;
  responsibilities: string;
  capabilities: string;
  constraints: string;
  timezone: string;
  wakeLimit: number;
  wakePeriod: string;
  allowedTriggers: string[];
  proactivity: string;
  notification: string;
  interruption: string;
  outsideHours: string;
  runState: string;
  explicitResume: boolean;
};

function editFromDraft(draft: DraftData): RevisionEdit {
  return {
    displayName: draft.proposed_profile.display_name,
    description: draft.proposed_profile.description,
    mission: draft.proposed_mandate.mission,
    serviceRelationship: draft.proposed_mandate.service_relationship,
    responsibilities: draft.proposed_mandate.responsibilities
      .map((item) => item.description)
      .join("\n"),
    capabilities: draft.proposed_mandate.capabilities
      .map((item) => item.description)
      .join("\n"),
    constraints: draft.proposed_mandate.constraints
      .map((item) => item.description)
      .join("\n"),
    timezone: draft.proposed_policy.timezone,
    wakeLimit: draft.proposed_policy.wake_budget.limit,
    wakePeriod: draft.proposed_policy.wake_budget.period,
    allowedTriggers: draft.proposed_policy.allowed_triggers,
    proactivity: draft.proposed_policy.proactivity,
    notification: draft.proposed_policy.notification,
    interruption: draft.proposed_policy.interruption,
    outsideHours: draft.proposed_policy.outside_hours,
    runState: draft.proposed_policy.run_state,
    explicitResume: draft.diff.some(
      (item) =>
        item.section === "policy" &&
        item.path === "explicit_resume" &&
        item.after.value === true,
    ),
  };
}

function noticeFor(error: Error): NoticeKind {
  if (error.name === "ValidationError" || error.name === "HTTP_422")
    return "validation";
  if (error.name === "PermissionDeniedError" || error.name === "HTTP_403")
    return "permission";
  if (error.name === "ConflictError")
    return error.message.toLowerCase().includes("stale") ? "stale" : "conflict";
  return "error";
}

function lines(value: string) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function RevisionedBuilder({
  p5,
  csrf,
  refresh,
}: {
  p5: P5State;
  csrf: string;
  refresh: () => Promise<void>;
}) {
  const drafts = p5.drafts || [];
  const initialDraft = drafts.at(-1)?.draft;
  const [selectedId, setSelectedId] = useState(initialDraft?.draft_id || "");
  const selected =
    drafts.find((item) => item.draft.draft_id === selectedId) ||
    drafts.at(-1) ||
    null;
  const [edit, setEdit] = useState<RevisionEdit | null>(
    initialDraft?.state === "draft" ? editFromDraft(initialDraft) : null,
  );
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState<{
    kind: NoticeKind;
    message: string;
  } | null>(null);

  async function operation(label: string, action: () => Promise<void>) {
    setBusy(label);
    setNotice(null);
    try {
      await action();
      setNotice({
        kind: "success",
        message: t("common.completed", { operation: label }),
      });
    } catch (cause) {
      const error =
        cause instanceof Error
          ? cause
          : new Error(t("common.operation_failed"));
      setNotice({
        kind: noticeFor(error),
        message: t("common.operation_failed"),
      });
    } finally {
      setBusy("");
    }
  }

  async function createDraft() {
    await operation(t("operation.draft_create"), async () => {
      const response = await api<DraftEnvelope>(
        "/colleagues/drafts",
        {
          method: "POST",
          body: JSON.stringify({ idempotency_key: randomKey("draft") }),
        },
        csrf,
      );
      setSelectedId(response.draft.draft_id);
      setEdit(editFromDraft(response.draft));
      await refresh();
    });
  }

  function mappedDefinitions<T extends { description: string }>(
    values: string,
    current: T[],
    build: (description: string, index: number, item?: T) => object,
  ) {
    return lines(values).map((description, index) =>
      build(description, index, current[index]),
    );
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!selected || !edit) return;
    const draft = selected.draft;
    await operation(t("operation.draft_update"), async () => {
      const response = await api<DraftEnvelope>(
        `/colleagues/drafts/${draft.draft_id}`,
        {
          method: "PUT",
          body: JSON.stringify({
            profile: {
              display_name: edit.displayName,
              description: edit.description,
              presentation: draft.proposed_profile.presentation,
            },
            mandate: {
              mission: edit.mission,
              service_relationship: edit.serviceRelationship,
              responsibilities: mappedDefinitions(
                edit.responsibilities,
                draft.proposed_mandate.responsibilities,
                (description, index, current) => ({
                  responsibility_id:
                    current?.responsibility_id ||
                    `responsibility-ui-${index + 1}`,
                  description,
                  obligations: current?.obligations || [
                    "Own the named responsibility",
                  ],
                  completion_conditions: current?.completion_conditions || [
                    "The finite work reaches a terminal state",
                  ],
                }),
              ),
              capabilities: mappedDefinitions(
                edit.capabilities,
                draft.proposed_mandate.capabilities,
                (description, index, current) => ({
                  capability_id:
                    current?.capability_id || `capability-ui-${index + 1}`,
                  description,
                }),
              ),
              constraints: mappedDefinitions(
                edit.constraints,
                draft.proposed_mandate.constraints,
                (description, index, current) => ({
                  constraint_id:
                    current?.constraint_id || `constraint-ui-${index + 1}`,
                  description,
                }),
              ),
              working_context: draft.proposed_mandate.working_context,
              effect_boundaries: draft.proposed_mandate.effect_boundaries,
            },
            policy: {
              timezone: edit.timezone,
              weekly_windows: draft.proposed_policy.weekly_windows,
              allowed_triggers: edit.allowedTriggers,
              proactivity: edit.proactivity,
              notification: edit.notification,
              interruption: edit.interruption,
              wake_limit: edit.wakeLimit,
              wake_period: edit.wakePeriod,
              outside_hours: edit.outsideHours,
              stop_conditions: draft.proposed_policy.stop_conditions,
              escalation_conditions:
                draft.proposed_policy.escalation_conditions,
              failure_limit: draft.proposed_policy.failure_limit,
              run_state: edit.runState,
              explicit_resume: edit.explicitResume,
            },
            expected_draft_revision: draft.revision,
            idempotency_key: randomKey("update-draft"),
          }),
        },
        csrf,
      );
      setEdit(editFromDraft(response.draft));
      await refresh();
    });
  }

  async function transition(target: "review" | "cancel") {
    if (!selected) return;
    const draft = selected.draft;
    await operation(
      target === "review"
        ? t("operation.review_binding")
        : t("operation.draft_cancel"),
      async () => {
        await api(
          `/colleagues/drafts/${draft.draft_id}/${target}`,
          {
            method: "POST",
            body: JSON.stringify({
              expected_draft_revision: draft.revision,
              idempotency_key: randomKey(target),
            }),
          },
          csrf,
        );
        await refresh();
        if (target === "cancel")
          setNotice({
            kind: "cancelled",
            message: t("revision.cancelled_terminal"),
          });
      },
    );
  }

  async function confirm() {
    if (!selected) return;
    const draft = selected.draft;
    await operation(t("operation.revision_confirm"), async () => {
      await api(
        `/colleagues/drafts/${draft.draft_id}/confirm`,
        {
          method: "POST",
          body: JSON.stringify({
            expected_draft_revision: draft.revision,
            expected_base_profile_revision: draft.base_profile_revision,
            expected_base_mandate_revision: draft.base_mandate_revision,
            expected_base_policy_revision: draft.base_policy_revision,
            expected_canonical_digest: draft.canonical_digest,
            idempotency_key: randomKey("confirm-draft"),
          }),
        },
        csrf,
      );
      await refresh();
    });
  }

  function toggleTrigger(trigger: string) {
    if (!edit) return;
    const exists = edit.allowedTriggers.includes(trigger);
    const allowedTriggers = exists
      ? edit.allowedTriggers.filter((item) => item !== trigger)
      : [...edit.allowedTriggers, trigger];
    if (allowedTriggers.length) setEdit({ ...edit, allowedTriggers });
  }

  const active = p5.active;
  const draft = selected?.draft;
  const changed = draft?.diff.filter(
    (item) => item.classification !== "unchanged",
  );

  return (
    <section
      className="workspace-view revision-builder"
      aria-labelledby="revision-builder-title"
    >
      <div className="view-heading">
        <div>
          <p className="section-kicker">{t("revision.kicker")}</p>
          <h1 id="revision-builder-title">{t("revision.title")}</h1>
          <p>{t("revision.explanation")}</p>
        </div>
        <button
          className="primary-action"
          onClick={() => void createDraft()}
          disabled={!!busy}
        >
          {t("revision.create")}
        </button>
      </div>

      {notice && <Notice {...notice} />}
      {busy && (
        <Notice
          kind="success"
          message={t("common.loading", { operation: busy })}
        />
      )}

      <div className="revision-ledger" aria-label={t("revision.ledger_aria")}>
        <div>
          <span>{t("revision.profile")}</span>
          <strong>
            {t("common.revision", {
              revision: active?.profile_revision ?? "—",
            })}
          </strong>
          <small>{t("revision.descriptive_only")}</small>
        </div>
        <div>
          <span>{t("revision.mandate")}</span>
          <strong>
            {t("common.revision", {
              revision: active?.mandate_revision ?? "—",
            })}
          </strong>
          <small>{t("revision.authority_source")}</small>
        </div>
        <div>
          <span>{t("revision.policy")}</span>
          <strong>
            {t("common.revision", { revision: active?.policy_revision ?? "—" })}
          </strong>
          <small>{active?.policy_status.replaceAll("_", " ")}</small>
        </div>
        <div>
          <span>{t("revision.runtime")}</span>
          <strong>
            {p5.runtime_policy?.run_state || t("revision.legacy")}
          </strong>
          <small>
            {t("revision.wakes_bucket", {
              count: p5.runtime_policy?.budget_count || 0,
            })}
          </small>
        </div>
      </div>

      {active?.policy_status === "legacy_unconfirmed" && (
        <Notice kind="validation" message={t("builder.legacy_hours")} />
      )}

      <div className="draft-index" aria-label={t("revision.history_aria")}>
        <header>
          <span>{t("revision.history")}</span>
          <strong>{drafts.length.toString().padStart(2, "0")}</strong>
        </header>
        {drafts.length === 0 ? (
          <div className="empty-state">
            <span>{t("common.empty")}</span>
            <h2>{t("revision.none")}</h2>
            <p>{t("revision.none_help")}</p>
          </div>
        ) : (
          <div
            className="draft-tabs"
            role="tablist"
            aria-label={t("revision.tabs_aria")}
          >
            {drafts.map((item) => (
              <button
                key={item.draft.draft_id}
                role="tab"
                aria-selected={item.draft.draft_id === draft?.draft_id}
                onClick={() => {
                  setSelectedId(item.draft.draft_id);
                  setEdit(
                    item.draft.state === "draft"
                      ? editFromDraft(item.draft)
                      : null,
                  );
                }}
              >
                <span>{item.draft.state}</span>
                <strong>
                  {t("revision.draft_rev", { revision: item.draft.revision })}
                </strong>
                <small>
                  {t("revision.base", {
                    profile: item.draft.base_profile_revision,
                    mandate: item.draft.base_mandate_revision,
                    policy: item.draft.base_policy_revision,
                  })}
                </small>
              </button>
            ))}
          </div>
        )}
      </div>

      {draft && edit && draft.state === "draft" && (
        <form className="revision-form" onSubmit={(event) => void save(event)}>
          <section>
            <span className="review-type descriptive">
              {t("revision.descriptive_profile")}
            </span>
            <h2>{t("revision.presentation")}</h2>
            <label>
              {t("builder.display_name")}
              <input
                value={edit.displayName}
                onChange={(event) =>
                  setEdit({ ...edit, displayName: event.target.value })
                }
                required
              />
            </label>
            <label>
              {t("revision.description")}
              <textarea
                value={edit.description}
                onChange={(event) =>
                  setEdit({ ...edit, description: event.target.value })
                }
                required
              />
            </label>
            <p className="section-note">{t("revision.profile_permission")}</p>
          </section>
          <section>
            <span className="review-type authoritative">
              {t("revision.authoritative_mandate")}
            </span>
            <h2>{t("revision.responsibilities_capabilities")}</h2>
            <label>
              {t("builder.mission")}
              <textarea
                value={edit.mission}
                onChange={(event) =>
                  setEdit({ ...edit, mission: event.target.value })
                }
                required
              />
            </label>
            <label>
              {t("builder.service_relationship")}
              <textarea
                value={edit.serviceRelationship}
                onChange={(event) =>
                  setEdit({ ...edit, serviceRelationship: event.target.value })
                }
                required
              />
            </label>
            <label>
              {t("revision.one_per_line", {
                label: t("builder.responsibilities"),
              })}
              <textarea
                value={edit.responsibilities}
                onChange={(event) =>
                  setEdit({ ...edit, responsibilities: event.target.value })
                }
                required
              />
            </label>
            <label>
              {t("revision.one_per_line", { label: t("builder.capabilities") })}
              <textarea
                value={edit.capabilities}
                onChange={(event) =>
                  setEdit({ ...edit, capabilities: event.target.value })
                }
                required
              />
            </label>
            <label>
              {t("revision.one_per_line", {
                label: t("builder.constraints_scope"),
              })}
              <textarea
                value={edit.constraints}
                onChange={(event) =>
                  setEdit({ ...edit, constraints: event.target.value })
                }
                required
              />
            </label>
          </section>
          <section className="policy-editor">
            <span className="review-type authoritative">
              {t("revision.typed_policy")}
            </span>
            <h2>{t("revision.wake_controls")}</h2>
            <div className="policy-fields">
              <label>
                {t("revision.iana_timezone")}
                <input
                  value={edit.timezone}
                  onChange={(event) =>
                    setEdit({ ...edit, timezone: event.target.value })
                  }
                  required
                />
              </label>
              <label>
                {t("revision.wake_limit")}
                <input
                  type="number"
                  min="1"
                  max="10000"
                  value={edit.wakeLimit}
                  onChange={(event) =>
                    setEdit({ ...edit, wakeLimit: Number(event.target.value) })
                  }
                  required
                />
              </label>
              {[
                [
                  t("revision.proactivity"),
                  "proactivity",
                  ["bounded", "disabled"],
                ],
                [
                  t("revision.notification"),
                  "notification",
                  ["enabled", "suppressed"],
                ],
                [
                  t("revision.interruption"),
                  "interruption",
                  ["allowed", "working_hours_only", "never"],
                ],
                [
                  t("revision.outside_hours"),
                  "outsideHours",
                  ["defer", "no_op", "stop", "escalate"],
                ],
                [t("revision.run_state"), "runState", ["active", "stopped"]],
              ].map(([label, key, values]) => (
                <label key={key as string}>
                  {label as string}
                  <select
                    value={edit[key as keyof RevisionEdit] as string}
                    onChange={(event) =>
                      setEdit({ ...edit, [key as string]: event.target.value })
                    }
                  >
                    {(values as string[]).map((value) => (
                      <option key={value}>{value}</option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
            <fieldset>
              <legend>{t("revision.allowed_triggers")}</legend>
              {[
                ["event", t("revision.event")],
                ["timer", t("revision.timer")],
              ].map(([value, label]) => (
                <label key={value}>
                  <input
                    type="checkbox"
                    checked={edit.allowedTriggers.includes(value)}
                    onChange={() => toggleTrigger(value)}
                  />
                  {label}
                </label>
              ))}
            </fieldset>
            {p5.runtime_policy?.run_state === "stopped" && (
              <label>
                <input
                  type="checkbox"
                  checked={edit.explicitResume}
                  onChange={(event) =>
                    setEdit({ ...edit, explicitResume: event.target.checked })
                  }
                />
                {t("revision.explicit_resume")}
              </label>
            )}
          </section>
          <footer className="revision-actions">
            <button
              type="button"
              className="reject-action"
              onClick={() => void transition("cancel")}
              disabled={!!busy}
            >
              {t("revision.cancel")}
            </button>
            <button type="submit" className="quiet-action" disabled={!!busy}>
              {t("revision.save")}
            </button>
            <button
              type="button"
              className="primary-action"
              onClick={() => void transition("review")}
              disabled={!!busy}
            >
              {t("builder.review_exact")}
            </button>
          </footer>
        </form>
      )}

      {draft && draft.state !== "draft" && (
        <section
          className="exact-review"
          aria-label={t("revision.review_aria")}
        >
          <header>
            <div>
              <span className={`state-label state-${draft.state}`}>
                {draft.state}
              </span>
              <h2>
                {t("revision.draft_revision", { revision: draft.revision })}
              </h2>
              <p>
                {t("revision.base_revisions", {
                  profile: draft.base_profile_revision,
                  mandate: draft.base_mandate_revision,
                  policy: draft.base_policy_revision,
                })}
              </p>
            </div>
            <code>{draft.canonical_digest}</code>
          </header>
          {draft.state === "reviewable" && (
            <Notice kind="validation" message={t("revision.confirm_binding")} />
          )}
          {draft.state === "cancelled" && (
            <Notice
              kind="cancelled"
              message={t("revision.cancelled_terminal")}
            />
          )}
          {draft.state === "stale" && (
            <Notice kind="stale" message={t("revision.stale_terminal")} />
          )}
          <div className="diff-list">
            {(changed || []).map((item) => (
              <article
                key={`${item.section}-${item.path}`}
                className={`diff-${item.classification}`}
              >
                <div>
                  <span>{item.section}</span>
                  <strong>{item.path}</strong>
                </div>
                <em>{item.classification}</em>
                <code>{JSON.stringify(item.before.value)}</code>
                <span aria-hidden="true">→</span>
                <code>{JSON.stringify(item.after.value)}</code>
              </article>
            ))}
          </div>
          {draft.explicit_defaults.length > 0 && (
            <div className="default-list">
              <span>{t("revision.defaults")}</span>
              {draft.explicit_defaults.map((item) => (
                <div key={item.path}>
                  <strong>{item.path}</strong>
                  <code>{JSON.stringify(item.value.value)}</code>
                  <small>{item.source}</small>
                </div>
              ))}
            </div>
          )}
          {draft.state === "reviewable" && (
            <div className="revision-actions">
              <button
                className="reject-action"
                onClick={() => void transition("cancel")}
                disabled={!!busy}
              >
                {t("revision.cancel")}
              </button>
              <button
                className="primary-action"
                onClick={() => void confirm()}
                disabled={!!busy}
              >
                {t("revision.confirm_digest")}
              </button>
            </div>
          )}
        </section>
      )}

      {!!p5.runtime_policy?.escalations.length && (
        <section
          className="escalation-ledger"
          aria-label={t("revision.escalations_aria")}
        >
          <span>{t("revision.escalations")}</span>
          {p5.runtime_policy.escalations.map((item) => (
            <div key={item.escalation_id}>
              <strong>{item.condition}</strong>
              <p>{item.safe_summary}</p>
              <small>{t("revision.escalation_boundary")}</small>
            </div>
          ))}
        </section>
      )}
    </section>
  );
}

function Workspace({
  session,
  state,
  p5,
  governance,
  csrf,
  refresh,
  refreshP5,
  refreshGovernance,
}: {
  session: Session;
  state: State;
  p5: P5State;
  governance: GovernanceState;
  csrf: string;
  refresh: () => Promise<void>;
  refreshP5: () => Promise<void>;
  refreshGovernance: () => Promise<void>;
}) {
  const [view, setView] = useState<View>("identity");
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState<{
    kind: NoticeKind;
    message: string;
  } | null>(null);
  const [audit, setAudit] = useState<{
    correlation_id: string;
    records: AuditRecord[];
  } | null>(null);
  const [exported, setExported] = useState<ExportRecord[]>([]);
  const work = state.work || [];
  const proposals = state.proposals || [];
  const pending = proposals.filter(
    (proposal) => proposal.approval_status === "pending",
  );
  const profile = state.identity?.profile;
  const mandate = state.identity?.mandate;
  const roles = governance.membership.roles;
  const isAdmin = roles.includes("tenant_admin");
  const isUser = roles.includes("colleague_user");
  const isAuditor = roles.includes("auditor");
  const canInteract = isAdmin || isUser;
  const canExport = isAdmin || isAuditor;
  const visibleNavigation = navigation.filter((item) => {
    if (item.id === "builder") return isAdmin;
    if (["work", "wake", "proposals"].includes(item.id)) return canInteract;
    if (item.id === "audit") return canExport;
    return true;
  });
  const decisionsByProposal = new Map(
    governance.change_decisions.map((item) => [item.proposal_id, item]),
  );

  async function mutate(label: string, action: () => Promise<void>) {
    setBusy(label);
    setNotice(null);
    try {
      await action();
      setNotice({
        kind: "success",
        message: t("common.completed_refresh", { operation: label }),
      });
    } catch (cause) {
      const error =
        cause instanceof Error
          ? cause
          : new Error(t("common.operation_failed"));
      setNotice({
        kind: error.name === "ConflictError" ? "stale" : "rejection",
        message: t("common.operation_failed"),
      });
    } finally {
      setBusy("");
    }
  }

  async function assign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await mutate(t("operation.work_assign"), async () => {
      await api(
        "/work",
        {
          method: "POST",
          body: JSON.stringify({
            title: form.get("title"),
            description: form.get("description"),
            responsibility_id:
              mandate?.responsibilities?.[0]?.responsibility_id,
            idempotency_key: randomKey("work"),
          }),
        },
        csrf,
      );
      await refresh();
      setView("wake");
    });
  }

  async function trigger(
    triggerClass: "event" | "timer",
    deterministicNoop = false,
  ) {
    if (!work[0]) return;
    await mutate(
      triggerClass === "timer"
        ? t("operation.timer_wake")
        : t("operation.event_wake"),
      async () => {
        await api(
          "/runtime/triggers",
          {
            method: "POST",
            body: JSON.stringify({
              work_id: work[0].work_id,
              trigger_class: triggerClass,
              deterministic_noop: deterministicNoop,
              idempotency_key: randomKey(triggerClass),
            }),
          },
          csrf,
        );
        await api(
          "/runtime/process",
          {
            method: "POST",
            body: JSON.stringify({ idempotency_key: randomKey("process") }),
          },
          csrf,
        );
        await Promise.all([refresh(), refreshP5()]);
        setView(deterministicNoop ? "wake" : "proposals");
      },
    );
  }

  async function decide(proposal: Proposal, choice: "approve" | "reject") {
    await mutate(
      choice === "approve" ? t("operation.approval") : t("operation.rejection"),
      async () => {
        await api(
          `/proposals/${proposal.proposal_id}/decision`,
          {
            method: "POST",
            body: JSON.stringify({
              proposal_revision: proposal.revision,
              proposal_payload_digest: proposal.payload_digest,
              proposal_digest: proposal.proposal_digest,
              mandate_id: proposal.mandate_id,
              mandate_revision: proposal.mandate_revision,
              policy_id: proposal.policy_id,
              policy_revision: proposal.policy_revision,
              choice,
              idempotency_key: randomKey(choice),
            }),
          },
          csrf,
        );
        if (choice === "approve")
          await api(
            "/runtime/process",
            {
              method: "POST",
              body: JSON.stringify({ idempotency_key: randomKey("dispatch") }),
            },
            csrf,
          );
        await refresh();
        setView(choice === "approve" ? "audit" : "proposals");
      },
    );
  }

  async function inspectAudit(correlationId: string) {
    setBusy(t("operation.audit_inspect"));
    try {
      setAudit(await api(`/audit/${correlationId}`));
      setView("audit");
    } catch {
      setNotice({
        kind: "error",
        message: t("common.operation_failed"),
      });
    } finally {
      setBusy("");
    }
  }

  async function authorizeScopedEnrollment(role: "colleague_user" | "auditor") {
    if (!session.namespace?.scope_id) return;
    await mutate(
      role === "auditor"
        ? t("governance.enroll_auditor")
        : t("governance.enroll_user"),
      async () => {
        await api(
          `/governance/enrollments/${role === "auditor" ? "auditors" : "users"}`,
          {
            method: "POST",
            body: JSON.stringify({
              colleague_ids: [session.namespace?.scope_id],
              idempotency_key: randomKey(`enroll-${role}`),
            }),
          },
          csrf,
        );
        await refreshGovernance();
      },
    );
  }

  async function authorizeRecovery() {
    await mutate(t("operation.recovery_authorize"), async () => {
      await api(
        "/governance/recovery",
        {
          method: "POST",
          body: JSON.stringify({
            principal_id: governance.membership.principal_id,
            idempotency_key: randomKey("recovery"),
          }),
        },
        csrf,
      );
      await refreshGovernance();
    });
  }

  async function decideChange(
    proposal: GovernanceProposal,
    choice: "approve" | "reject",
  ) {
    const scope = proposal.change_kind === "draft" ? "colleague" : "tenant";
    await mutate(
      choice === "approve"
        ? t("governance.approve_change")
        : t("governance.reject_change"),
      async () => {
        await api(
          `/governance/changes/${scope}/${proposal.proposal_id}/decision`,
          {
            method: "POST",
            body: JSON.stringify({
              proposal_revision: proposal.revision,
              proposal_digest: proposal.canonical_digest,
              choice,
              idempotency_key: randomKey(`change-${choice}`),
            }),
          },
          csrf,
        );
        await refreshGovernance();
      },
    );
  }

  async function exportAudit() {
    const end = new Date();
    const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);
    await mutate(t("operation.audit_export"), async () => {
      const result = await api<{ records: ExportRecord[] }>(
        "/governance/audit/export",
        {
          method: "POST",
          body: JSON.stringify({
            start_at: start.toISOString(),
            end_at: end.toISOString(),
            record_types: [
              "profile",
              "mandate",
              "colleague_policy",
              "effect_proposal",
              "human_approval",
            ],
            limit: 100,
          }),
        },
        csrf,
      );
      setExported(result.records);
      await refreshGovernance();
    });
  }

  return (
    <div className="workspace-shell">
      <header className="workspace-header">
        <div className="brand-lockup">
          <span className="brand-mark">{t("common.dc")}</span>
          <div>
            <strong>{t("product.name")}</strong>
            <span>{t("runtime.subtitle")}</span>
          </div>
        </div>
        <div className="runtime-status">
          <span className="status-dot" aria-hidden="true" />
          <div>
            <strong>{t("runtime.durable")}</strong>
            <span>{session.namespace?.scope_id}</span>
          </div>
        </div>
        <div className="principal-chip">
          <span>{t("common.human")}</span>
          <strong>{roles.join(" · ")}</strong>
        </div>
      </header>
      <aside className="workspace-nav" aria-label={t("nav.aria")}>
        <p className="nav-label">{t("nav.label")}</p>
        {visibleNavigation.map((item) => (
          <button
            key={item.id}
            className={view === item.id ? "active" : ""}
            onClick={() => setView(item.id)}
          >
            <span>{item.index}</span>
            {t(item.label)}
            {item.id === "proposals" && pending.length > 0 && (
              <em>{pending.length}</em>
            )}
          </button>
        ))}
        <div className="nav-boundary">
          <span>{t("runtime.synthetic")}</span>
          <p>{t("runtime.no_live")}</p>
        </div>
      </aside>
      <main className="workspace-main" key={view}>
        {notice && <Notice {...notice} />}
        {view === "registry" && (
          <AgentRegistry csrf={csrf} canManage={isAdmin} />
        )}
        {view === "identity" && state.identity && (
          <section className="workspace-view" aria-labelledby="identity-title">
            <div className="view-heading">
              <div>
                <p className="section-kicker">{t("identity.kicker")}</p>
                <h1 id="identity-title">{profile?.display_name}</h1>
                <p>{profile?.description}</p>
              </div>
              <span className="revision-stamp">
                {t("identity.mandate_stamp", {
                  revision: state.identity.exact_revision,
                })}
              </span>
            </div>
            <div className="identity-ledger">
              <article>
                <span className="review-type descriptive">
                  {t("revision.descriptive_profile")}
                </span>
                <h2>{t("identity.presentation")}</h2>
                <dl>
                  <dt>{t("builder.working_style")}</dt>
                  <dd>{profile?.presentation.working_style}</dd>
                  <dt>{t("identity.authority_source")}</dt>
                  <dd>{t("identity.profile_not_authority")}</dd>
                </dl>
              </article>
              <article>
                <span className="review-type authoritative">
                  {t("revision.authoritative_mandate")}
                </span>
                <h2>{mandate?.mission}</h2>
                <dl>
                  <dt>{t("builder.serves")}</dt>
                  <dd>{mandate?.service_relationship}</dd>
                  <dt>{t("builder.responsibilities")}</dt>
                  <dd>
                    {mandate?.responsibilities
                      .map((item) => item.description)
                      .join(", ")}
                  </dd>
                  <dt>{t("builder.capabilities")}</dt>
                  <dd>
                    {mandate?.capabilities
                      .map((item) => item.description)
                      .join(", ")}
                  </dd>
                  <dt>{t("builder.constraints_scope")}</dt>
                  <dd>
                    {mandate?.constraints
                      .map((item) => item.description)
                      .join(", ")}
                  </dd>
                </dl>
              </article>
            </div>
            <div className="effect-line">
              <span>{t("identity.exact_effect")}</span>
              <strong>{mandate?.effect_boundaries[0]?.effect_kind}</strong>
              <span>
                {mandate?.effect_boundaries[0]?.allowed_destination_kinds[0]} →{" "}
                {mandate?.effect_boundaries[0]?.allowed_actions[0]}
              </span>
              <em>{t("identity.human_approval")}</em>
            </div>
          </section>
        )}
        {view === "builder" && isAdmin && (
          <RevisionedBuilder
            p5={p5}
            csrf={csrf}
            refresh={async () => {
              await Promise.all([refresh(), refreshP5()]);
            }}
          />
        )}
        {view === "work" && canInteract && (
          <section className="workspace-view" aria-labelledby="work-title">
            <div className="view-heading">
              <div>
                <p className="section-kicker">{t("work.kicker")}</p>
                <h1 id="work-title">{t("work.title")}</h1>
                <p>{t("work.explanation")}</p>
              </div>
              <button
                className="quiet-action"
                onClick={() =>
                  void mutate(t("operation.recovery_inspect"), refresh)
                }
                disabled={!!busy}
              >
                {t("work.inspect")}
              </button>
            </div>
            {work.length === 0 ? (
              <div className="empty-state">
                <span>{t("common.empty")}</span>
                <h2>{t("work.none")}</h2>
                <p>{t("work.none_help")}</p>
              </div>
            ) : (
              <ol className="work-list">
                {work.map((item) => (
                  <li key={item.work_id}>
                    <span className="state-label">{item.state}</span>
                    <div>
                      <h2>{item.title}</h2>
                      <p>{item.description}</p>
                    </div>
                    <dl>
                      <dt>{t("work.mandate")}</dt>
                      <dd>
                        {item.mandate_id} · rev {item.mandate_revision}
                      </dd>
                      <dt>{t("work.correlation")}</dt>
                      <dd>{item.correlation_id}</dd>
                    </dl>
                  </li>
                ))}
              </ol>
            )}
            {work.length === 0 && (
              <form
                className="work-form"
                onSubmit={(event) => void assign(event)}
              >
                <label>
                  {t("work.title_label")}
                  <input
                    name="title"
                    defaultValue="Prepare one deterministic work update"
                    required
                  />
                </label>
                <label>
                  {t("work.done")}
                  <textarea
                    name="description"
                    defaultValue="Produce one exact reference ActionResult after human review."
                    required
                  />
                </label>
                <button className="primary-action" disabled={!!busy}>
                  {busy || t("work.assign")}
                </button>
              </form>
            )}
          </section>
        )}
        {view === "wake" && canInteract && (
          <section className="workspace-view" aria-labelledby="wake-title">
            <div className="view-heading">
              <div>
                <p className="section-kicker">{t("wake.kicker")}</p>
                <h1 id="wake-title">{t("wake.title")}</h1>
                <p>{t("wake.explanation")}</p>
              </div>
              <div className="button-cluster">
                <button
                  onClick={() => void trigger("event")}
                  disabled={!work.length || !!busy}
                >
                  {t("wake.trigger_event")}
                </button>
                <button
                  onClick={() => void trigger("timer")}
                  disabled={!work.length || !!busy}
                >
                  {t("wake.trigger_timer")}
                </button>
                <button
                  onClick={() => void trigger("event", true)}
                  disabled={!work.length || !!busy}
                >
                  {t("wake.test_noop")}
                </button>
              </div>
            </div>
            {!state.wakes?.length ? (
              <div className="empty-state">
                <span>{t("common.empty")}</span>
                <h2>{t("wake.none")}</h2>
                <p>{t("wake.none_help")}</p>
              </div>
            ) : (
              <ol className="wake-timeline">
                {state.wakes.map((wake) => (
                  <li key={wake.wake_cycle_id}>
                    <div className={`trigger-glyph ${wake.trigger_class}`}>
                      {wake.trigger_class === "event" ? "E" : "T"}
                    </div>
                    <div>
                      <p className="mono-line">
                        {wake.trigger_class.toUpperCase()} ·{" "}
                        {wake.trigger_identity}
                      </p>
                      <h2>{wake.wake_reason}</h2>
                      <p>
                        {wake.decision?.rationale || t("wake.pending_decision")}
                      </p>
                      <div className="generation-line">
                        <span>
                          {t("wake.agenda", {
                            generation: wake.agenda_generation,
                          })}
                        </span>
                        <span>
                          {t("wake.handled", {
                            generation: wake.handled_generation,
                          })}
                        </span>
                        <span>{wake.decision?.kind || "pending"}</span>
                      </div>
                    </div>
                    <button
                      className="text-action"
                      onClick={() => void inspectAudit(wake.correlation_id)}
                    >
                      {t("wake.trace")}
                    </button>
                  </li>
                ))}
              </ol>
            )}
          </section>
        )}
        {view === "proposals" && canInteract && (
          <section className="workspace-view" aria-labelledby="proposal-title">
            <div className="view-heading">
              <div>
                <p className="section-kicker">{t("proposal.kicker")}</p>
                <h1 id="proposal-title">{t("proposal.title")}</h1>
                <p>{t("proposal.explanation")}</p>
              </div>
              <span className="inbox-count">
                {t("proposal.pending_count", {
                  count: pending.length.toString().padStart(2, "0"),
                })}
              </span>
            </div>
            {proposals.length === 0 ? (
              <div className="empty-state">
                <span>{t("common.empty")}</span>
                <h2>{t("proposal.none")}</h2>
                <p>{t("proposal.none_help")}</p>
              </div>
            ) : (
              <div className="proposal-list">
                {proposals.map((proposal) => (
                  <article className="proposal-item" key={proposal.proposal_id}>
                    <header>
                      <div>
                        <span className="state-label">
                          {proposal.approval_status}
                        </span>
                        <h2>{proposal.action}</h2>
                        <p>
                          {proposal.destination.kind} /{" "}
                          {proposal.destination.target}
                        </p>
                      </div>
                      <strong>
                        {t("common.revision", { revision: proposal.revision })}
                      </strong>
                    </header>
                    <div className="effect-projection">
                      <span>{t("proposal.safe_projection")}</span>
                      <code>{JSON.stringify(proposal.safe_projection)}</code>
                    </div>
                    <dl className="proposal-bindings">
                      <dt>{t("proposal.digest")}</dt>
                      <dd>{proposal.proposal_digest}</dd>
                      <dt>{t("proposal.payload")}</dt>
                      <dd>{proposal.payload_digest}</dd>
                      <dt>{t("builder.effect_boundary")}</dt>
                      <dd>{proposal.effect_boundary}</dd>
                      <dt>{t("work.mandate")}</dt>
                      <dd>
                        {proposal.mandate_id} · rev {proposal.mandate_revision}
                      </dd>
                      <dt>{t("proposal.policy")}</dt>
                      <dd>
                        {proposal.policy_id
                          ? `${proposal.policy_id} · rev ${proposal.policy_revision}`
                          : t("proposal.legacy_policy")}
                      </dd>
                      <dt>{t("proposal.actor")}</dt>
                      <dd>
                        {proposal.actor.kind} / {proposal.actor.principal_id}
                      </dd>
                      <dt>{t("proposal.namespace")}</dt>
                      <dd>
                        {proposal.namespace.tenant_id} /{" "}
                        {proposal.namespace.scope_id}
                      </dd>
                      <dt>{t("proposal.expiry")}</dt>
                      <dd>{proposal.expires_at}</dd>
                      <dt>{t("proposal.causal_source")}</dt>
                      <dd>{proposal.causation_id}</dd>
                    </dl>
                    {proposal.approval_status === "pending" && (
                      <footer>
                        <button
                          className="reject-action"
                          onClick={() => void decide(proposal, "reject")}
                          disabled={!!busy}
                        >
                          {t("proposal.reject")}
                        </button>
                        <button
                          className="primary-action"
                          onClick={() => void decide(proposal, "approve")}
                          disabled={!!busy}
                        >
                          {t("proposal.approve")}
                        </button>
                      </footer>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>
        )}
        {view === "audit" && canExport && (
          <section className="workspace-view" aria-labelledby="audit-title">
            <div className="view-heading">
              <div>
                <p className="section-kicker">{t("audit.kicker")}</p>
                <h1 id="audit-title">{t("audit.title")}</h1>
                <p>{t("audit.explanation")}</p>
              </div>
              {state.results && state.results.length > 0 && (
                <span className="result-stamp">
                  {t("audit.result_stamp", { count: state.results.length })}
                </span>
              )}
            </div>
            {!audit ? (
              <div className="empty-state">
                <span>{t("audit.select")}</span>
                <h2>{t("audit.choose")}</h2>
                <div className="trace-links">
                  {state.wakes?.map((wake) => (
                    <button
                      key={wake.correlation_id}
                      onClick={() => void inspectAudit(wake.correlation_id)}
                    >
                      {wake.trigger_class} · {wake.correlation_id}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="audit-chain">
                <div className="audit-correlation">
                  <span>{t("audit.correlation")}</span>
                  <strong>{audit.correlation_id}</strong>
                </div>
                <ol>
                  {audit.records.map((record) => (
                    <li key={record.audit_id}>
                      <span className="chain-dot" aria-hidden="true" />
                      <div>
                        <p>{record.record_type.replaceAll("_", " ")}</p>
                        <strong>{record.record_id}</strong>
                        <span>{record.occurred_at}</span>
                      </div>
                      <dl>
                        <dt>{t("audit.revision")}</dt>
                        <dd>{record.record_revision}</dd>
                        <dt>{t("audit.actor")}</dt>
                        <dd>{record.actor_principal_id}</dd>
                        <dt>{t("audit.causation")}</dt>
                        <dd>{record.causation_id || t("common.root")}</dd>
                        <dt>{t("audit.safe_projection")}</dt>
                        <dd>
                          <code>{JSON.stringify(record.safe_projection)}</code>
                        </dd>
                        <dt>{t("audit.digest")}</dt>
                        <dd>{record.payload_digest}</dd>
                      </dl>
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </section>
        )}
        {view === "governance" && (
          <section
            className="workspace-view governance-view"
            aria-labelledby="governance-title"
          >
            <div className="view-heading">
              <div>
                <p className="section-kicker">{t("governance.kicker")}</p>
                <h1 id="governance-title">{t("governance.title")}</h1>
                <p>{t("governance.explanation")}</p>
              </div>
              <span className="revision-stamp">
                {t("governance.session_stamp", {
                  revision: governance.session.revision,
                })}
              </span>
            </div>

            <div className="identity-ledger governance-ledger">
              <article>
                <span className="review-type authoritative">
                  {t("governance.session_binding")}
                </span>
                <h2>{governance.membership.status}</h2>
                <dl>
                  <dt>{t("governance.principal")}</dt>
                  <dd>{governance.membership.principal_id}</dd>
                  <dt>{t("governance.role_revision")}</dt>
                  <dd>{governance.session.role_revision}</dd>
                  <dt>{t("governance.membership_revision")}</dt>
                  <dd>{governance.session.membership_revision}</dd>
                  <dt>{t("governance.session_expiry")}</dt>
                  <dd>{governance.session.expires_at}</dd>
                  <dt>{t("governance.colleague_scope")}</dt>
                  <dd>{governance.membership.colleague_ids.join(", ")}</dd>
                </dl>
              </article>
              <article>
                <span className="review-type descriptive">
                  {t("governance.credentials")}
                </span>
                <h2>
                  {isAdmin && governance.bootstrap_transition_state
                    ? t("governance.second_admin", {
                        state: governance.bootstrap_transition_state,
                      })
                    : t("governance.credential_scope")}
                </h2>
                <p>{t("governance.credential_boundary")}</p>
                {governance.credentials.length === 0 ? (
                  <p className="read-only-note">
                    {t("governance.no_credentials")}
                  </p>
                ) : (
                  <ol className="credential-status-list">
                    {governance.credentials.map((credential) => (
                      <li key={credential.credential_id}>
                        <span>{credential.kind}</span>
                        <strong>{credential.state}</strong>
                        <small>
                          {t("governance.credential_detail", {
                            revision: credential.revision,
                            expires: credential.expires_at,
                          })}
                        </small>
                        {credential.kind === "recovery" && (
                          <small>
                            {t("governance.target_authority", {
                              role: credential.target_role_revision ?? "—",
                              membership:
                                credential.target_membership_revision ?? "—",
                            })}
                          </small>
                        )}
                      </li>
                    ))}
                  </ol>
                )}
                {isAdmin && (
                  <div className="button-cluster">
                    <button
                      type="button"
                      onClick={() =>
                        void authorizeScopedEnrollment("colleague_user")
                      }
                      disabled={!!busy}
                    >
                      {t("governance.enroll_user")}
                    </button>
                    <button
                      type="button"
                      onClick={() => void authorizeScopedEnrollment("auditor")}
                      disabled={!!busy}
                    >
                      {t("governance.enroll_auditor")}
                    </button>
                    <button
                      type="button"
                      onClick={() => void authorizeRecovery()}
                      disabled={!!busy}
                    >
                      {t("governance.authorize_recovery")}
                    </button>
                  </div>
                )}
              </article>
            </div>

            <section className="governance-section">
              <span className="review-type authoritative">
                {t("governance.pending_changes")}
              </span>
              {governance.change_proposals.length === 0 ? (
                <p>{t("governance.no_changes")}</p>
              ) : (
                <div className="proposal-list">
                  {governance.change_proposals.map((proposal) => {
                    const decision = decisionsByProposal.get(
                      proposal.proposal_id,
                    );
                    const reviewedDraft = p5.drafts?.find(
                      (item) => item.draft.draft_id === proposal.target_id,
                    )?.draft;
                    const reviewedDiff = reviewedDraft?.diff.filter(
                      (item) => item.classification !== "unchanged",
                    );
                    return (
                      <article
                        className="proposal-item"
                        key={proposal.proposal_id}
                      >
                        <header>
                          <div>
                            <span className="state-label">
                              {proposal.state}
                            </span>
                            <h2>{proposal.change_kind.replaceAll("_", " ")}</h2>
                          </div>
                          <strong>
                            {t("governance.exact_revision", {
                              revision: proposal.target_revision,
                            })}
                          </strong>
                        </header>
                        <dl className="proposal-bindings">
                          <dt>{t("governance.canonical_digest")}</dt>
                          <dd>{proposal.canonical_digest}</dd>
                          <dt>{t("governance.proposer")}</dt>
                          <dd>{proposal.proposer_principal_id}</dd>
                          <dt>{t("governance.approver")}</dt>
                          <dd>
                            {decision?.approver_principal_id ||
                              t("governance.separate_admin")}
                          </dd>
                          <dt>{t("proposal.expiry")}</dt>
                          <dd>{proposal.expires_at}</dd>
                          <dt>{t("governance.refused_reason")}</dt>
                          <dd>
                            {proposal.state === "stale" ||
                            proposal.state === "expired"
                              ? t("governance.cannot_apply", {
                                  state: proposal.state,
                                })
                              : t("common.none")}
                          </dd>
                        </dl>
                        {!!reviewedDiff?.length && (
                          <div
                            className="diff-list"
                            aria-label={t("governance.reviewed_diff_aria")}
                          >
                            {reviewedDiff.map((item) => (
                              <div
                                key={`${item.section}:${item.path}`}
                                className={`diff-${item.classification}`}
                              >
                                <span>{item.section}</span>
                                <strong>{item.path}</strong>
                                <em>{item.classification}</em>
                              </div>
                            ))}
                          </div>
                        )}
                        {isAdmin && proposal.state === "pending" && (
                          <footer>
                            <button
                              type="button"
                              className="reject-action"
                              onClick={() =>
                                void decideChange(proposal, "reject")
                              }
                            >
                              {t("governance.reject_change")}
                            </button>
                            <button
                              type="button"
                              className="primary-action"
                              onClick={() =>
                                void decideChange(proposal, "approve")
                              }
                            >
                              {t("governance.approve_change")}
                            </button>
                          </footer>
                        )}
                      </article>
                    );
                  })}
                </div>
              )}
            </section>

            <section className="governance-section">
              <span className="review-type descriptive">
                {t("governance.safe_export")}
              </span>
              <p>{t("governance.export_boundary")}</p>
              {canExport && (
                <button
                  type="button"
                  className="primary-action"
                  onClick={() => void exportAudit()}
                  disabled={!!busy}
                >
                  {t("governance.export")}
                </button>
              )}
              {exported.length > 0 && (
                <ol className="work-list">
                  {exported.map((record) => (
                    <li
                      key={`${record.record_type}:${record.record_id}:${record.record_revision}`}
                    >
                      <span className="state-label">{record.result}</span>
                      <div>
                        <h2>{record.record_type.replaceAll("_", " ")}</h2>
                        <p>{record.safe_digest}</p>
                      </div>
                      <dl>
                        <dt>{t("audit.actor")}</dt>
                        <dd>{record.actor_principal_id}</dd>
                        <dt>{t("audit.causation")}</dt>
                        <dd>{record.causation_id}</dd>
                      </dl>
                    </li>
                  ))}
                </ol>
              )}
            </section>
          </section>
        )}
      </main>
      <footer className="workspace-footer">
        <span>
          {busy
            ? t("footer.working", { operation: busy.toUpperCase() })
            : t("footer.ready")}
        </span>
        <span>{t("footer.boundary")}</span>
      </footer>
    </div>
  );
}

export function App() {
  const [locale, updateLocale] = useState<Locale>(() => {
    const selected = initialLocale();
    setLocale(selected);
    return selected;
  });
  const [phase, setPhase] = useState<Phase>("checking");
  const [session, setSession] = useState<Session | null>(null);
  const [state, setState] = useState<State>({ state: "empty" });
  const [p5, setP5] = useState<P5State>({ state: "empty" });
  const [governance, setGovernance] = useState<GovernanceState | null>(null);
  const [fatal, setFatal] = useState("");
  const [sessionNotice, setSessionNotice] = useState("");

  const loadP5State = useCallback(async () => {
    const next = await api<P5State>("/p5/studio/state");
    setP5(next);
  }, []);
  const loadGovernance = useCallback(async () => {
    const next = await api<GovernanceState>("/governance/state");
    setGovernance(next);
  }, []);
  const loadState = useCallback(async () => {
    const [next, nextP5, nextGovernance] = await Promise.all([
      api<State>("/studio/state"),
      api<P5State>("/p5/studio/state"),
      api<GovernanceState>("/governance/state"),
    ]);
    setState(next);
    setP5(nextP5);
    setGovernance(nextGovernance);
    setPhase(next.state === "empty" ? "builder" : "workspace");
  }, []);
  const establish = useCallback(
    async (resolved: Session) => {
      setSession(resolved);
      await loadState();
    },
    [loadState],
  );

  useEffect(() => {
    let active = true;
    api<Session>("/auth/session")
      .then(async (resolved) => {
        if (active) await establish(resolved);
      })
      .catch((cause) => {
        if (active) {
          if (
            cause instanceof Error &&
            !cause.message.toLowerCase().includes("authentication required")
          ) {
            setSessionNotice(t("session.changed"));
          }
          setPhase("bootstrap");
        }
      });
    return () => {
      active = false;
    };
  }, [establish]);

  const language = (
    <LanguagePicker
      locale={locale}
      change={(selected) => {
        setLocale(selected);
        updateLocale(selected);
      }}
    />
  );
  if (fatal)
    return (
      <>
        {language}
        <main className="fatal-state">
          <span>{t("error.state")}</span>
          <h1>{t("error.unavailable")}</h1>
          <p>{t("common.operation_failed")}</p>
          <button onClick={() => window.location.reload()}>
            {t("error.retry")}
          </button>
        </main>
      </>
    );
  if (phase === "checking")
    return (
      <>
        {language}
        <main className="loading-state" aria-live="polite">
          <span className="loading-mark">{t("common.dc")}</span>
          <p>{t("loading.state")}</p>
        </main>
      </>
    );
  if (phase === "bootstrap")
    return (
      <>
        {language}
        <Bootstrap
          sessionNotice={sessionNotice}
          onReady={(resolved) => {
            void establish(resolved).catch((cause) => setFatal(String(cause)));
          }}
        />
      </>
    );
  if (!session || !governance) return null;
  if (phase === "builder")
    return (
      <>
        {language}
        <Builder
          csrf={session.csrf_token}
          onCreated={async () => {
            const resolved = await api<Session>("/auth/session");
            setSession(resolved);
            await loadState();
          }}
        />
      </>
    );
  return (
    <>
      {language}
      <Workspace
        session={session}
        state={state}
        p5={p5}
        governance={governance}
        csrf={session.csrf_token}
        refresh={loadState}
        refreshP5={loadP5State}
        refreshGovernance={loadGovernance}
      />
    </>
  );
}
