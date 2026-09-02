// SPDX-License-Identifier: Apache-2.0

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Phase = "checking" | "bootstrap" | "builder" | "workspace";
type View =
  | "identity"
  | "builder"
  | "work"
  | "wake"
  | "proposals"
  | "audit"
  | "governance";
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

const navigation: { id: View; label: string; index: string }[] = [
  { id: "identity", label: "Identity & authority", index: "01" },
  { id: "builder", label: "Revisioned builder", index: "02" },
  { id: "work", label: "Finite work", index: "03" },
  { id: "wake", label: "Wake cycles", index: "04" },
  { id: "proposals", label: "Proposal inbox", index: "05" },
  { id: "audit", label: "Causal audit", index: "06" },
  { id: "governance", label: "Governance & access", index: "07" },
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
      body.detail?.message || `Request failed (${response.status})`,
    );
    error.name = body.detail?.code || `HTTP_${response.status}`;
    throw error;
  }
  return (await response.json()) as T;
}

function Notice({ kind, message }: { kind: NoticeKind; message: string }) {
  return (
    <div className={`notice notice-${kind}`} role="status" tabIndex={-1}>
      <span>{kind}</span>
      <p>{message}</p>
    </div>
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
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Bootstrap exchange failed",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="entry-screen">
      <header className="entry-brand">
        <span className="brand-mark">DC</span>
        <div>
          <strong>Digital Colleagues</strong>
          <span>P6 local governance control plane</span>
        </div>
      </header>
      <section className="entry-composition" aria-labelledby="bootstrap-title">
        <div className="entry-index" aria-hidden="true">
          01 / AUTHORITY
        </div>
        <div className="entry-copy">
          <p className="eyebrow">One-time operator handoff</p>
          <h1 id="bootstrap-title">Establish the first durable human.</h1>
          <p>
            Exchange the token retrieved by the local operator. The server fixes
            tenant, HUMAN principal kind, and <code>tenant_admin</code>{" "}
            authority.
          </p>
          <form onSubmit={(event) => void submit(event)} className="token-form">
            <label htmlFor="bootstrap-token">Bootstrap token</label>
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
                {busy ? "Exchanging…" : "Create Admin session"}
              </button>
            </div>
          </form>
          {sessionNotice && <Notice kind="revoked" message={sessionNotice} />}
          {error && <Notice kind="rejection" message={error} />}
          <p className="boundary-copy">
            Loopback reduces host exposure. It is not authentication,
            encryption, sandboxing, or production isolation.
          </p>
        </div>
        <div
          className="entry-ledger"
          aria-label="Bootstrap security properties"
        >
          {[
            ["256+", "bits of entropy"],
            ["01", "successful exchange"],
            ["≤10m", "bootstrap lifetime"],
            ["HTTP", "only session cookie"],
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
    } catch (cause) {
      setNotice({
        kind: "error",
        message: cause instanceof Error ? cause.message : "Preview failed",
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
        message: "Exact Profile and Mandate revision 1 created.",
      });
      await onCreated();
    } catch (cause) {
      const error =
        cause instanceof Error ? cause : new Error("Creation failed");
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
          <span className="brand-mark">DC</span>
          <div>
            <strong>Initial colleague</strong>
            <span>revision 1 · one-time flow</span>
          </div>
        </div>
        <span className="step-count">
          {review ? "REVIEW" : "DEFINE"} / CONFIRM
        </span>
      </header>
      {!review ? (
        <form
          className="builder-grid"
          onSubmit={(event) => void continueToReview(event)}
        >
          <section aria-labelledby="profile-heading">
            <p className="section-kicker">Descriptive Profile</p>
            <h1 id="profile-heading">How this colleague appears.</h1>
            <p className="section-note">
              Profile describes. It never grants authority.
            </p>
            <label>
              Display name
              <input
                value={data.display_name}
                onChange={(e) => update("display_name", e.target.value)}
                required
              />
            </label>
            <label>
              Role description
              <textarea
                value={data.role_description}
                onChange={(e) => update("role_description", e.target.value)}
                required
              />
            </label>
            <label>
              Working style
              <textarea
                value={data.working_style}
                onChange={(e) => update("working_style", e.target.value)}
                required
              />
            </label>
          </section>
          <section aria-labelledby="mandate-heading">
            <p className="section-kicker authority-kicker">
              Authoritative Mandate
            </p>
            <h2 id="mandate-heading">What this colleague may and must do.</h2>
            <div className="form-columns">
              <label>
                Serves
                <textarea
                  value={data.service_relationship}
                  onChange={(e) =>
                    update("service_relationship", e.target.value)
                  }
                  required
                />
              </label>
              <label>
                Mission
                <textarea
                  value={data.mission}
                  onChange={(e) => update("mission", e.target.value)}
                  required
                />
              </label>
              <label>
                Timezone
                <input
                  value={data.timezone}
                  onChange={(e) => update("timezone", e.target.value)}
                  required
                />
              </label>
              <label>
                Initial working hours
                <input
                  value={data.working_hours}
                  onChange={(e) => update("working_hours", e.target.value)}
                  required
                />
              </label>
              <label>
                Initial context
                <textarea
                  value={data.working_context}
                  onChange={(e) => update("working_context", e.target.value)}
                  required
                />
              </label>
              <label>
                Responsibilities
                <textarea
                  value={data.responsibilities}
                  onChange={(e) => update("responsibilities", e.target.value)}
                  required
                />
              </label>
              <label>
                Capabilities
                <textarea
                  value={data.capabilities}
                  onChange={(e) => update("capabilities", e.target.value)}
                  required
                />
              </label>
              <label>
                Constraints & scope
                <textarea
                  value={data.constraints}
                  onChange={(e) => update("constraints", e.target.value)}
                  required
                />
              </label>
              <label>
                Destination kind
                <input
                  value={data.destination_kind}
                  onChange={(e) => update("destination_kind", e.target.value)}
                  required
                />
              </label>
              <label>
                Exact action
                <input
                  value={data.action}
                  onChange={(e) => update("action", e.target.value)}
                  required
                />
              </label>
            </div>
            <button className="primary-action" type="submit" disabled={busy}>
              {busy ? "Preparing review…" : "Review exact revision"}
            </button>
          </section>
        </form>
      ) : (
        <section className="authority-review" aria-labelledby="review-heading">
          <p className="section-kicker">Exact revision to create</p>
          <h1 id="review-heading">
            Profile is presentation. Mandate is authority.
          </h1>
          <div className="review-columns">
            <div>
              <span className="review-type descriptive">DESCRIPTIVE</span>
              <h2>{data.display_name}</h2>
              <p>{data.role_description}</p>
              <dl>
                <dt>Working style</dt>
                <dd>{data.working_style}</dd>
              </dl>
            </div>
            <div>
              <span className="review-type authoritative">
                AUTHORITATIVE · REVISION 1
              </span>
              <h2>{data.mission}</h2>
              <dl>
                <dt>Service relationship</dt>
                <dd>{data.service_relationship}</dd>
                <dt>Responsibility</dt>
                <dd>{data.responsibilities}</dd>
                <dt>Capability</dt>
                <dd>{data.capabilities}</dd>
                <dt>Constraint</dt>
                <dd>{data.constraints}</dd>
                <dt>Effect boundary</dt>
                <dd>
                  {data.destination_kind} → {data.action} · human approval
                  required
                </dd>
                <dt>Working-hours boundary</dt>
                <dd>
                  Legacy display data only; P5 typed policy requires a separate
                  revisioned confirmation.
                </dd>
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
              Back to definition
            </button>
            <button
              className="primary-action"
              onClick={() => void confirm()}
              disabled={busy}
            >
              {busy ? "Committing…" : "Confirm exact revision 1"}
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
      setNotice({ kind: "success", message: `${label} completed.` });
    } catch (cause) {
      const error =
        cause instanceof Error ? cause : new Error(`${label} failed`);
      setNotice({ kind: noticeFor(error), message: error.message });
    } finally {
      setBusy("");
    }
  }

  async function createDraft() {
    await operation("Draft creation", async () => {
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
    await operation("Draft update", async () => {
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
      target === "review" ? "Review binding" : "Draft cancellation",
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
            message: "Draft cancelled. Active authority was not changed.",
          });
      },
    );
  }

  async function confirm() {
    if (!selected) return;
    const draft = selected.draft;
    await operation("Exact revision confirmation", async () => {
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
          <p className="section-kicker">Revisioned colleague builder</p>
          <h1 id="revision-builder-title">Change authority safely.</h1>
          <p>
            Drafts are inert until an Admin confirms the exact revision and
            canonical digest shown here.
          </p>
        </div>
        <button
          className="primary-action"
          onClick={() => void createDraft()}
          disabled={!!busy}
        >
          Create revisioned draft
        </button>
      </div>

      {notice && <Notice {...notice} />}
      {busy && <Notice kind="success" message={`Loading · ${busy}`} />}

      <div className="revision-ledger" aria-label="Active revision ledger">
        <div>
          <span>PROFILE</span>
          <strong>REV {active?.profile_revision ?? "—"}</strong>
          <small>Descriptive only</small>
        </div>
        <div>
          <span>MANDATE</span>
          <strong>REV {active?.mandate_revision ?? "—"}</strong>
          <small>Authority source</small>
        </div>
        <div>
          <span>POLICY</span>
          <strong>REV {active?.policy_revision ?? "—"}</strong>
          <small>{active?.policy_status.replaceAll("_", " ")}</small>
        </div>
        <div>
          <span>RUNTIME</span>
          <strong>{p5.runtime_policy?.run_state || "LEGACY"}</strong>
          <small>{p5.runtime_policy?.budget_count || 0} wakes in bucket</small>
        </div>
      </div>

      {active?.policy_status === "legacy_unconfirmed" && (
        <Notice
          kind="validation"
          message="Legacy P4 working-hours text is display data only. P5 will not infer typed authority from it."
        />
      )}

      <div className="draft-index" aria-label="Draft history">
        <header>
          <span>DRAFT HISTORY</span>
          <strong>{drafts.length.toString().padStart(2, "0")}</strong>
        </header>
        {drafts.length === 0 ? (
          <div className="empty-state">
            <span>EMPTY</span>
            <h2>No colleague revisions drafted.</h2>
            <p>
              Create a draft to review Profile, Mandate, and policy
              independently.
            </p>
          </div>
        ) : (
          <div
            className="draft-tabs"
            role="tablist"
            aria-label="Colleague drafts"
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
                <strong>Draft rev {item.draft.revision}</strong>
                <small>
                  base {item.draft.base_profile_revision}/
                  {item.draft.base_mandate_revision}/
                  {item.draft.base_policy_revision}
                </small>
              </button>
            ))}
          </div>
        )}
      </div>

      {draft && edit && draft.state === "draft" && (
        <form className="revision-form" onSubmit={(event) => void save(event)}>
          <section>
            <span className="review-type descriptive">DESCRIPTIVE PROFILE</span>
            <h2>Presentation</h2>
            <label>
              Display name
              <input
                value={edit.displayName}
                onChange={(event) =>
                  setEdit({ ...edit, displayName: event.target.value })
                }
                required
              />
            </label>
            <label>
              Description
              <textarea
                value={edit.description}
                onChange={(event) =>
                  setEdit({ ...edit, description: event.target.value })
                }
                required
              />
            </label>
            <p className="section-note">
              Profile never grants runtime permission.
            </p>
          </section>
          <section>
            <span className="review-type authoritative">
              AUTHORITATIVE MANDATE
            </span>
            <h2>Responsibilities & capabilities</h2>
            <label>
              Mission
              <textarea
                value={edit.mission}
                onChange={(event) =>
                  setEdit({ ...edit, mission: event.target.value })
                }
                required
              />
            </label>
            <label>
              Service relationship
              <textarea
                value={edit.serviceRelationship}
                onChange={(event) =>
                  setEdit({ ...edit, serviceRelationship: event.target.value })
                }
                required
              />
            </label>
            <label>
              Responsibilities · one per line
              <textarea
                value={edit.responsibilities}
                onChange={(event) =>
                  setEdit({ ...edit, responsibilities: event.target.value })
                }
                required
              />
            </label>
            <label>
              Capabilities · one per line
              <textarea
                value={edit.capabilities}
                onChange={(event) =>
                  setEdit({ ...edit, capabilities: event.target.value })
                }
                required
              />
            </label>
            <label>
              Constraints · one per line
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
            <span className="review-type authoritative">TYPED POLICY</span>
            <h2>Wake & interruption controls</h2>
            <div className="policy-fields">
              <label>
                IANA timezone
                <input
                  value={edit.timezone}
                  onChange={(event) =>
                    setEdit({ ...edit, timezone: event.target.value })
                  }
                  required
                />
              </label>
              <label>
                Wake limit
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
                ["Proactivity", "proactivity", ["bounded", "disabled"]],
                ["Notification", "notification", ["enabled", "suppressed"]],
                [
                  "Interruption",
                  "interruption",
                  ["allowed", "working_hours_only", "never"],
                ],
                [
                  "Outside hours",
                  "outsideHours",
                  ["defer", "no_op", "stop", "escalate"],
                ],
                ["Run state", "runState", ["active", "stopped"]],
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
              <legend>Allowed durable triggers</legend>
              {[
                ["event", "Event"],
                ["timer", "Timer"],
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
                Explicitly resume this stopped runtime with the reviewed
                applicable policy revision
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
              Cancel draft
            </button>
            <button type="submit" className="quiet-action" disabled={!!busy}>
              Save as next draft revision
            </button>
            <button
              type="button"
              className="primary-action"
              onClick={() => void transition("review")}
              disabled={!!busy}
            >
              Review exact revision
            </button>
          </footer>
        </form>
      )}

      {draft && draft.state !== "draft" && (
        <section className="exact-review" aria-label="Exact draft review">
          <header>
            <div>
              <span className={`state-label state-${draft.state}`}>
                {draft.state}
              </span>
              <h2>Draft revision {draft.revision}</h2>
              <p>
                Base Profile {draft.base_profile_revision} · Mandate{" "}
                {draft.base_mandate_revision} · Policy{" "}
                {draft.base_policy_revision}
              </p>
            </div>
            <code>{draft.canonical_digest}</code>
          </header>
          {draft.state === "reviewable" && (
            <Notice
              kind="validation"
              message="Confirm binds to this exact draft revision, all three base revisions, and this digest."
            />
          )}
          {draft.state === "cancelled" && (
            <Notice
              kind="cancelled"
              message="Cancelled draft is terminal and remains inert."
            />
          )}
          {draft.state === "stale" && (
            <Notice
              kind="stale"
              message="A base revision changed. This draft cannot be rebased, retried, or confirmed."
            />
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
              <span>EXPLICIT DEFAULTS · CONFIRMED ONLY WITH THIS DRAFT</span>
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
                Cancel draft
              </button>
              <button
                className="primary-action"
                onClick={() => void confirm()}
                disabled={!!busy}
              >
                Confirm exact revision & digest
              </button>
            </div>
          )}
        </section>
      )}

      {!!p5.runtime_policy?.escalations.length && (
        <section className="escalation-ledger" aria-label="Policy escalations">
          <span>SAFE ESCALATION RECORDS</span>
          {p5.runtime_policy.escalations.map((item) => (
            <div key={item.escalation_id}>
              <strong>{item.condition}</strong>
              <p>{item.safe_summary}</p>
              <small>
                No approval, authority change, or external notification was
                created.
              </small>
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
        message: `${label} completed and durable state refreshed.`,
      });
    } catch (cause) {
      const error =
        cause instanceof Error ? cause : new Error(`${label} failed`);
      setNotice({
        kind: error.name === "ConflictError" ? "stale" : "rejection",
        message: error.message,
      });
    } finally {
      setBusy("");
    }
  }

  async function assign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await mutate("Work assignment", async () => {
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
      `${triggerClass === "timer" ? "Timer" : "Event"} wake`,
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
      `${choice === "approve" ? "Approval" : "Rejection"} of exact revision`,
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
    setBusy("Audit inspection");
    try {
      setAudit(await api(`/audit/${correlationId}`));
      setView("audit");
    } catch (cause) {
      setNotice({
        kind: "error",
        message:
          cause instanceof Error ? cause.message : "Audit inspection failed",
      });
    } finally {
      setBusy("");
    }
  }

  async function authorizeScopedEnrollment(role: "colleague_user" | "auditor") {
    if (!session.namespace?.scope_id) return;
    await mutate(`Authorize ${role} enrollment`, async () => {
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
    });
  }

  async function authorizeRecovery() {
    await mutate("Authorize recovery", async () => {
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
    await mutate(`${choice} exact governance change`, async () => {
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
    });
  }

  async function exportAudit() {
    const end = new Date();
    const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);
    await mutate("Bounded audit export", async () => {
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
          <span className="brand-mark">DC</span>
          <div>
            <strong>Digital Colleagues</strong>
            <span>Local reference · P6 governance</span>
          </div>
        </div>
        <div className="runtime-status">
          <span className="status-dot" aria-hidden="true" />
          <div>
            <strong>Durable runtime</strong>
            <span>{session.namespace?.scope_id}</span>
          </div>
        </div>
        <div className="principal-chip">
          <span>HUMAN</span>
          <strong>{roles.join(" · ")}</strong>
        </div>
      </header>
      <aside className="workspace-nav" aria-label="Golden Path navigation">
        <p className="nav-label">Golden Path</p>
        {visibleNavigation.map((item) => (
          <button
            key={item.id}
            className={view === item.id ? "active" : ""}
            onClick={() => setView(item.id)}
          >
            <span>{item.index}</span>
            {item.label}
            {item.id === "proposals" && pending.length > 0 && (
              <em>{pending.length}</em>
            )}
          </button>
        ))}
        <div className="nav-boundary">
          <span>SYNTHETIC / OFFLINE</span>
          <p>No live model or provider effect.</p>
        </div>
      </aside>
      <main className="workspace-main" key={view}>
        {notice && <Notice {...notice} />}
        {view === "identity" && state.identity && (
          <section className="workspace-view" aria-labelledby="identity-title">
            <div className="view-heading">
              <div>
                <p className="section-kicker">Identity & authority</p>
                <h1 id="identity-title">{profile?.display_name}</h1>
                <p>{profile?.description}</p>
              </div>
              <span className="revision-stamp">
                MANDATE · REV {state.identity.exact_revision}
              </span>
            </div>
            <div className="identity-ledger">
              <article>
                <span className="review-type descriptive">
                  DESCRIPTIVE PROFILE
                </span>
                <h2>Presentation</h2>
                <dl>
                  <dt>Working style</dt>
                  <dd>{profile?.presentation.working_style}</dd>
                  <dt>Authority source</dt>
                  <dd>No — Profile preferences do not grant permission.</dd>
                </dl>
              </article>
              <article>
                <span className="review-type authoritative">
                  AUTHORITATIVE MANDATE
                </span>
                <h2>{mandate?.mission}</h2>
                <dl>
                  <dt>Serves</dt>
                  <dd>{mandate?.service_relationship}</dd>
                  <dt>Responsibilities</dt>
                  <dd>
                    {mandate?.responsibilities
                      .map((item) => item.description)
                      .join(", ")}
                  </dd>
                  <dt>Capabilities</dt>
                  <dd>
                    {mandate?.capabilities
                      .map((item) => item.description)
                      .join(", ")}
                  </dd>
                  <dt>Constraints</dt>
                  <dd>
                    {mandate?.constraints
                      .map((item) => item.description)
                      .join(", ")}
                  </dd>
                </dl>
              </article>
            </div>
            <div className="effect-line">
              <span>EXACT EFFECT BOUNDARY</span>
              <strong>{mandate?.effect_boundaries[0]?.effect_kind}</strong>
              <span>
                {mandate?.effect_boundaries[0]?.allowed_destination_kinds[0]} →{" "}
                {mandate?.effect_boundaries[0]?.allowed_actions[0]}
              </span>
              <em>Human approval required</em>
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
                <p className="section-kicker">Finite work</p>
                <h1 id="work-title">Durable assignment</h1>
                <p>
                  Work binds to this namespace, responsibility, assignee, and
                  exact Mandate revision.
                </p>
              </div>
              <button
                className="quiet-action"
                onClick={() =>
                  void mutate("Restart recovery inspection", refresh)
                }
                disabled={!!busy}
              >
                Inspect recovered state
              </button>
            </div>
            {work.length === 0 ? (
              <div className="empty-state">
                <span>EMPTY</span>
                <h2>No finite work assigned.</h2>
                <p>Create the one bounded item used by the reference path.</p>
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
                      <dt>Mandate</dt>
                      <dd>
                        {item.mandate_id} · rev {item.mandate_revision}
                      </dd>
                      <dt>Correlation</dt>
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
                  Work title
                  <input
                    name="title"
                    defaultValue="Prepare one deterministic work update"
                    required
                  />
                </label>
                <label>
                  Definition of done
                  <textarea
                    name="description"
                    defaultValue="Produce one exact reference ActionResult after human review."
                    required
                  />
                </label>
                <button className="primary-action" disabled={!!busy}>
                  {busy || "Assign finite work"}
                </button>
              </form>
            )}
          </section>
        )}
        {view === "wake" && canInteract && (
          <section className="workspace-view" aria-labelledby="wake-title">
            <div className="view-heading">
              <div>
                <p className="section-kicker">Wake-cycle inspector</p>
                <h1 id="wake-title">Why did it wake?</h1>
                <p>
                  Event and Timer remain semantically distinct. Internal no-op
                  cycles never become proposals.
                </p>
              </div>
              <div className="button-cluster">
                <button
                  onClick={() => void trigger("event")}
                  disabled={!work.length || !!busy}
                >
                  Trigger Event
                </button>
                <button
                  onClick={() => void trigger("timer")}
                  disabled={!work.length || !!busy}
                >
                  Trigger Timer
                </button>
                <button
                  onClick={() => void trigger("event", true)}
                  disabled={!work.length || !!busy}
                >
                  Test no-op
                </button>
              </div>
            </div>
            {!state.wakes?.length ? (
              <div className="empty-state">
                <span>EMPTY</span>
                <h2>No wake cycles yet.</h2>
                <p>Assign work, then trigger an Event or Timer.</p>
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
                        {wake.decision?.rationale ||
                          "Pending deterministic decision"}
                      </p>
                      <div className="generation-line">
                        <span>Agenda {wake.agenda_generation}</span>
                        <span>Handled {wake.handled_generation}</span>
                        <span>{wake.decision?.kind || "pending"}</span>
                      </div>
                    </div>
                    <button
                      className="text-action"
                      onClick={() => void inspectAudit(wake.correlation_id)}
                    >
                      Trace causality →
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
                <p className="section-kicker">Proposal inbox</p>
                <h1 id="proposal-title">Exact effects awaiting a human.</h1>
                <p>
                  A proposal is not authorization. Decisions bind to every
                  immutable field shown here.
                </p>
              </div>
              <span className="inbox-count">
                {pending.length.toString().padStart(2, "0")} PENDING
              </span>
            </div>
            {proposals.length === 0 ? (
              <div className="empty-state">
                <span>EMPTY</span>
                <h2>No effect proposals.</h2>
                <p>A deterministic no-op stays here: absent by design.</p>
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
                      <strong>REV {proposal.revision}</strong>
                    </header>
                    <div className="effect-projection">
                      <span>SAFE EFFECT PROJECTION</span>
                      <code>{JSON.stringify(proposal.safe_projection)}</code>
                    </div>
                    <dl className="proposal-bindings">
                      <dt>Proposal digest</dt>
                      <dd>{proposal.proposal_digest}</dd>
                      <dt>Payload integrity</dt>
                      <dd>{proposal.payload_digest}</dd>
                      <dt>Effect boundary</dt>
                      <dd>{proposal.effect_boundary}</dd>
                      <dt>Mandate</dt>
                      <dd>
                        {proposal.mandate_id} · rev {proposal.mandate_revision}
                      </dd>
                      <dt>Policy</dt>
                      <dd>
                        {proposal.policy_id
                          ? `${proposal.policy_id} · rev ${proposal.policy_revision}`
                          : "legacy unconfirmed"}
                      </dd>
                      <dt>Actor</dt>
                      <dd>
                        {proposal.actor.kind} / {proposal.actor.principal_id}
                      </dd>
                      <dt>Namespace</dt>
                      <dd>
                        {proposal.namespace.tenant_id} /{" "}
                        {proposal.namespace.scope_id}
                      </dd>
                      <dt>Expiry</dt>
                      <dd>{proposal.expires_at}</dd>
                      <dt>Causal source</dt>
                      <dd>{proposal.causation_id}</dd>
                    </dl>
                    {proposal.approval_status === "pending" && (
                      <footer>
                        <button
                          className="reject-action"
                          onClick={() => void decide(proposal, "reject")}
                          disabled={!!busy}
                        >
                          Reject exact revision
                        </button>
                        <button
                          className="primary-action"
                          onClick={() => void decide(proposal, "approve")}
                          disabled={!!busy}
                        >
                          Approve exact revision
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
                <p className="section-kicker">Causal audit</p>
                <h1 id="audit-title">From input to result.</h1>
                <p>
                  Only safe projections and digests cross this inspection
                  boundary.
                </p>
              </div>
              {state.results && state.results.length > 0 && (
                <span className="result-stamp">
                  ACTIONRESULT · {state.results.length}
                </span>
              )}
            </div>
            {!audit ? (
              <div className="empty-state">
                <span>SELECT A TRACE</span>
                <h2>Choose a wake cycle or work correlation.</h2>
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
                  <span>CORRELATION</span>
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
                        <dt>Revision</dt>
                        <dd>{record.record_revision}</dd>
                        <dt>Actor</dt>
                        <dd>{record.actor_principal_id}</dd>
                        <dt>Causation</dt>
                        <dd>{record.causation_id || "root"}</dd>
                        <dt>Safe projection</dt>
                        <dd>
                          <code>{JSON.stringify(record.safe_projection)}</code>
                        </dd>
                        <dt>Digest</dt>
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
                <p className="section-kicker">Governance & access</p>
                <h1 id="governance-title">Current authority, never cached.</h1>
                <p>
                  Server-side RBAC binds every action to a durable HUMAN,
                  namespace, role revision, and membership revision.
                </p>
              </div>
              <span className="revision-stamp">
                SESSION · REV {governance.session.revision}
              </span>
            </div>

            <div className="identity-ledger governance-ledger">
              <article>
                <span className="review-type authoritative">
                  SESSION BINDING
                </span>
                <h2>{governance.membership.status}</h2>
                <dl>
                  <dt>Principal</dt>
                  <dd>{governance.membership.principal_id}</dd>
                  <dt>Role revision</dt>
                  <dd>{governance.session.role_revision}</dd>
                  <dt>Membership revision</dt>
                  <dd>{governance.session.membership_revision}</dd>
                  <dt>Session expiry</dt>
                  <dd>{governance.session.expires_at}</dd>
                  <dt>Colleague scope</dt>
                  <dd>{governance.membership.colleague_ids.join(", ")}</dd>
                </dl>
              </article>
              <article>
                <span className="review-type descriptive">
                  CREDENTIAL LIFECYCLE
                </span>
                <h2>
                  {isAdmin && governance.bootstrap_transition_state
                    ? `Second Admin transition: ${governance.bootstrap_transition_state}`
                    : "Credential status in exact colleague scope"}
                </h2>
                <p>
                  Enrollment and recovery plaintext is retrieved once at the
                  local operator boundary. Studio receives status only.
                </p>
                {governance.credentials.length === 0 ? (
                  <p className="read-only-note">
                    No credential lifecycle records are visible in this role and
                    namespace.
                  </p>
                ) : (
                  <ol className="credential-status-list">
                    {governance.credentials.map((credential) => (
                      <li key={credential.credential_id}>
                        <span>{credential.kind}</span>
                        <strong>{credential.state}</strong>
                        <small>
                          rev {credential.revision} · expires{" "}
                          {credential.expires_at}
                        </small>
                        {credential.kind === "recovery" && (
                          <small>
                            target authority rev{" "}
                            {credential.target_role_revision}/
                            {credential.target_membership_revision}
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
                      Authorize scoped User enrollment
                    </button>
                    <button
                      type="button"
                      onClick={() => void authorizeScopedEnrollment("auditor")}
                      disabled={!!busy}
                    >
                      Authorize scoped Auditor enrollment
                    </button>
                    <button
                      type="button"
                      onClick={() => void authorizeRecovery()}
                      disabled={!!busy}
                    >
                      Authorize recovery credential
                    </button>
                  </div>
                )}
              </article>
            </div>

            <section className="governance-section">
              <span className="review-type authoritative">
                PENDING CHANGE APPROVALS
              </span>
              {governance.change_proposals.length === 0 ? (
                <p>No change proposals are visible in this authorized scope.</p>
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
                          <strong>EXACT REV {proposal.target_revision}</strong>
                        </header>
                        <dl className="proposal-bindings">
                          <dt>Canonical digest</dt>
                          <dd>{proposal.canonical_digest}</dd>
                          <dt>Proposer</dt>
                          <dd>{proposal.proposer_principal_id}</dd>
                          <dt>Approver</dt>
                          <dd>
                            {decision?.approver_principal_id ||
                              "separate Admin required"}
                          </dd>
                          <dt>Expiry</dt>
                          <dd>{proposal.expires_at}</dd>
                          <dt>Refused / stale reason</dt>
                          <dd>
                            {proposal.state === "stale" ||
                            proposal.state === "expired"
                              ? `Exact ${proposal.state} binding cannot apply.`
                              : "none"}
                          </dd>
                        </dl>
                        {!!reviewedDiff?.length && (
                          <div
                            className="diff-list"
                            aria-label="Reviewed exact diff"
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
                              Reject exact change
                            </button>
                            <button
                              type="button"
                              className="primary-action"
                              onClick={() =>
                                void decideChange(proposal, "approve")
                              }
                            >
                              Approve exact change
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
              <span className="review-type descriptive">SAFE AUDIT EXPORT</span>
              <p>
                Deterministically ordered, redacted safe projections; bounded to
                100 records in the active colleague namespace. Private payload
                content remains absent.
              </p>
              {canExport && (
                <button
                  type="button"
                  className="primary-action"
                  onClick={() => void exportAudit()}
                  disabled={!!busy}
                >
                  Export bounded safe audit
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
                        <dt>Actor</dt>
                        <dd>{record.actor_principal_id}</dd>
                        <dt>Causation</dt>
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
            ? `WORKING · ${busy.toUpperCase()}`
            : "READY · KEYBOARD OPERABLE"}
        </span>
        <span>P6 under verification · independent acceptance required</span>
      </footer>
    </div>
  );
}

export function App() {
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
            setSessionNotice(
              "Existing session expired, was revoked, or its role/membership binding changed. Use an Admin-authorized local recovery session.",
            );
          }
          setPhase("bootstrap");
        }
      });
    return () => {
      active = false;
    };
  }, [establish]);

  if (fatal)
    return (
      <main className="fatal-state">
        <span>ERROR STATE</span>
        <h1>The local control plane is unavailable.</h1>
        <p>{fatal}</p>
        <button onClick={() => window.location.reload()}>
          Retry connection
        </button>
      </main>
    );
  if (phase === "checking")
    return (
      <main className="loading-state" aria-live="polite">
        <span className="loading-mark">DC</span>
        <p>Loading durable state…</p>
      </main>
    );
  if (phase === "bootstrap")
    return (
      <Bootstrap
        sessionNotice={sessionNotice}
        onReady={(resolved) => {
          void establish(resolved).catch((cause) => setFatal(String(cause)));
        }}
      />
    );
  if (!session || !governance) return null;
  if (phase === "builder")
    return (
      <Builder
        csrf={session.csrf_token}
        onCreated={async () => {
          const resolved = await api<Session>("/auth/session");
          setSession(resolved);
          await loadState();
        }}
      />
    );
  return (
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
  );
}
