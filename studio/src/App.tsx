// SPDX-License-Identifier: Apache-2.0

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Phase = "checking" | "bootstrap" | "builder" | "workspace";
type View = "identity" | "work" | "wake" | "proposals" | "audit";
type NoticeKind = "success" | "rejection" | "stale" | "error";

type Session = {
  authenticated: boolean;
  csrf_token: string;
  namespace: { tenant_id: string; scope: string; scope_id: string } | null;
  principal: { principal_id: string; kind: string; roles: string[] };
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

type NamedDefinition = { description: string; responsibility_id?: string };
type ProfileData = {
  display_name: string;
  description: string;
  presentation: { working_style: string; authority_source: boolean };
};
type EffectBoundaryData = {
  effect_kind: string;
  allowed_destination_kinds: string[];
  allowed_actions: string[];
};
type MandateData = {
  mission: string;
  service_relationship: string;
  responsibilities: NamedDefinition[];
  capabilities: NamedDefinition[];
  constraints: NamedDefinition[];
  effect_boundaries: EffectBoundaryData[];
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
  { id: "work", label: "Finite work", index: "02" },
  { id: "wake", label: "Wake cycles", index: "03" },
  { id: "proposals", label: "Proposal inbox", index: "04" },
  { id: "audit", label: "Causal audit", index: "05" },
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

function Bootstrap({ onReady }: { onReady: (session: Session) => void }) {
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
          <span>P4 local control plane</span>
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
                  Initial confirmed data only; enforcement is not implemented in
                  P4.
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

function Workspace({
  session,
  state,
  csrf,
  refresh,
}: {
  session: Session;
  state: State;
  csrf: string;
  refresh: () => Promise<void>;
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
  const work = state.work || [];
  const proposals = state.proposals || [];
  const pending = proposals.filter(
    (proposal) => proposal.approval_status === "pending",
  );
  const profile = state.identity?.profile;
  const mandate = state.identity?.mandate;

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
        await refresh();
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

  return (
    <div className="workspace-shell">
      <header className="workspace-header">
        <div className="brand-lockup">
          <span className="brand-mark">DC</span>
          <div>
            <strong>Digital Colleagues</strong>
            <span>Local reference · P4</span>
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
          <strong>tenant_admin</strong>
        </div>
      </header>
      <aside className="workspace-nav" aria-label="Golden Path navigation">
        <p className="nav-label">Golden Path</p>
        {navigation.map((item) => (
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
        {view === "work" && (
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
        {view === "wake" && (
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
        {view === "proposals" && (
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
        {view === "audit" && (
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
      </main>
      <footer className="workspace-footer">
        <span>
          {busy
            ? `WORKING · ${busy.toUpperCase()}`
            : "READY · KEYBOARD OPERABLE"}
        </span>
        <span>Development complete, awaiting independent acceptance</span>
      </footer>
    </div>
  );
}

export function App() {
  const [phase, setPhase] = useState<Phase>("checking");
  const [session, setSession] = useState<Session | null>(null);
  const [state, setState] = useState<State>({ state: "empty" });
  const [fatal, setFatal] = useState("");

  const loadState = useCallback(async () => {
    const next = await api<State>("/studio/state");
    setState(next);
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
      .catch(() => {
        if (active) setPhase("bootstrap");
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
        onReady={(resolved) => {
          void establish(resolved).catch((cause) => setFatal(String(cause)));
        }}
      />
    );
  if (!session) return null;
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
      csrf={session.csrf_token}
      refresh={loadState}
    />
  );
}
