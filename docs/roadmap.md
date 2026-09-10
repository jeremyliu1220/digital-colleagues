<!-- SPDX-License-Identifier: Apache-2.0 -->

# P0-P20 Roadmap

Each milestone stops at its gate. A later milestone must not begin automatically.

Current checkpoint:

- P0–P11R are accepted history. Local `main` and `origin/main` are fixed at the accepted
  P11R commit `c1562ea5201394d8a278f4b644daf4029cbb5bd4`, whose tree is
  `ae0f33263cfc7445fef69656ad9c5cb04d4a2d00`.
- Historical P0–P11R contracts, evidence, tests, receipts, provenance, and migrations
  001–008 remain immutable.
- P12 is a governance-only continuity rebaseline. Its immutable acceptance contract is
  `docs/p12/acceptance.md`; P12 adds no runtime, API, CLI, Studio, connector, schema,
  migration, dependency, distribution, or publication capability.
- P13–P20 remain ordered, independently accepted, and separately authorized. Completion
  of P12 does not start any of them.
- No Public Pilot, production readiness, production security, high availability,
  enterprise IAM, compliance, human evaluation, live-provider compatibility, or other
  later claim follows from this roadmap.

Rebaseline boundary:

- [ADR 0003](adr/0003-colleague-experience-and-post-v0.1-boundary.md) defines the
  colleague-experience capability model and the boundary between v0.1 and later work.
- [Colleague Experience Evaluation](product/colleague-experience-evaluation.md) defines
  P4–P6 scenarios, measurement points, and evidence classes without claiming a measured
  improvement.
- [Post-v0.1 Capability Outlook](product/post-v0.1-capability-outlook.md) records a
  gated sequence for deferred capabilities. It is an outlook, not a v0.1 commitment.

## P0 — Public planning and boundary gate

Create the product brief, Golden Path, maturity boundary, target architecture, threat and
privacy boundaries, licensing decisions, source-rights and third-party records, versioned
allowlist/denylist/scanner policy, provenance verification tools, P0 tests, and sanitized
source fingerprints. Do not initialize Git or migrate product code.

Exit: the repeatable P0 checks pass and `artifacts/p0/summary.json` claims only the
planning/public-boundary gate.

## P1 — Public repository scaffold

Create the formal Apache-2.0 `LICENSE`, `NOTICE`, contributor-facing licensing guidance,
README, community health files, Python and Studio scaffolds, continuous integration,
security policy, and development commands. Initialize and publish Git only with separate
operator authorization.

Exit: clean-room scaffold and policy checks pass; no product feature is implied.

## P2 — Core primitives

Migrate only verified allowlisted material with recorded transforms. Establish frozen core
contracts for namespace, identity, Mandate, work, events, agenda, wake cycles, effect
proposals, human principals, and exact approval decisions. Correct the research system's
coupling between colleague identity and human approver identity.

Exit: architecture, immutability, authority, and principal-separation tests pass.

Actual: P2 uses new implementations derived from public architecture documents and records
zero transformed source files. Frozen contracts and pure governance policies now cover
complete namespace, durable principals, Profile versus Mandate authority, finite work and
obligations, event/agenda/wake state, exact effect revisions, human-only approval, replay
refusal, and the minimum causal audit chain. No orchestration or persistence was added.

## P3 — Headless deterministic slice

Implement application services, stable ports, numbered and checksummed SQLite migrations,
WAL and foreign keys, one namespaced `state.sqlite`, deterministic provider, reference
channel, typed FastAPI mappings, restart recovery, and causal audit records.

Exit: the headless Golden Path is repeatable across restart.

Actual: framework-neutral services and ports coordinate an injectable, namespaced SQLite
store with WAL, foreign keys, checksummed migrations, optimistic revisions, immutable audit,
transactional replay/outbox state, leases, fencing, Agenda generations, bounded attention,
exact-effect revalidation, ambiguity reconciliation, a deterministic provider, synthetic
reference channel, typed FastAPI mappings, and fresh-instance restart tests. Additive migration
003 provides typed durable Timer occurrences and triggers with version-2 upgrade coverage.
Approval and event acceptance times are server-stamped; complete outbox bindings fail closed;
architecture allowlists are boundary-specific and assignment-alias aware; application no-op
policy bypasses intelligence and effects while recording a durable Decision. The P3 receipt
records only new implementations and zero transformed source files.

## P4 — Studio and five-minute Golden Path

Build React, TypeScript, and Vite Studio; Docker Compose; bootstrap authentication; the
colleague builder; work assignment; wake-cycle inspection; exact-effect approval; and
causal audit views. Wake inspection must visualize the wake reason and trigger class.
Present `EffectProposal` records as a proposal inbox in which a human can inspect the exact
effect revision before approval. Add colleague-experience validation scenarios and
measurement points for resuming work, explaining wakes, handling proposals, avoiding
unnecessary interruptions, and completing finite work. Keep evidence classes explicit;
synthetic and offline evidence do not imply human or live-provider validation. Semantic
Memory is not part of P4.

Exit: a clean local environment completes the documented five-minute Golden Path, exposes
the causal wake and proposal chain, and produces appropriately classified evaluation
evidence without claiming that colleague experience has been proven to improve.

## P5 — Revisioned colleague builder

Add draft lifecycle, identity cards, Mandate diffs, explicit defaults, responsibility and
capability editing, revision confirmation, and safe change workflows. The revisioned builder
must cover working hours, allowed triggers, proactivity policy, notification and interruption
policy, wake budgets, and stop and escalation conditions. It must keep Profile preferences
descriptive and separate from Mandate permissions and prohibitions. Every change retains an
explicit revision, reviewable diff, confirmation, and stale-revision rejection.

Exit: stale drafts and ambiguous authority changes are rejected and evidenced.

Accepted result: P5 is accepted and merged. It implements inert Profile/Mandate/policy
drafts, explicit defaults, classified diffs, exact atomic confirmation, stale-race
evidence, migration 006, revision-bound deterministic policy enforcement, Studio review,
synthetic/offline metrics, and an isolated actual Compose Golden Path. Its historical
acceptance, artifacts, evidence, migration, and receipt remain unchanged. Acceptance does
not establish production readiness or colleague-experience improvement.

## P6 — Governance hardening

Harden RBAC, session recovery, enrollment, CSRF and replay defenses, approval expiry,
change approval, namespace tests, audit export, and abuse cases. Apply RBAC, namespace
scoping, change approval, expiry, replay protection, and abuse-case coverage to working-hour,
trigger, proactivity, notification, interruption, wake-budget, stop, and escalation policies.
Document security requirements for future Semantic Memory, Skills, and shared knowledge,
including provenance, authorization, versioning, revocation, rollback, and misuse risks,
without implementing capabilities that do not exist in v0.1.

Exit: the documented local security test suite passes; production security is still not
claimed.

Accepted result: P6 is accepted and merged. It implements typed local RBAC, versioned
membership and session authority, enrollment/recovery, two-person exact governance change,
approval expiry and revalidation, bounded audit export, abuse coverage, migration 007,
role-aware Studio views, and isolated Compose evidence. Historical P0–P6 records and
migrations remain unchanged. Acceptance does not establish enterprise IAM, production
security/privacy, tenancy isolation, compliance, or production readiness.

## P7 — Optional adapters

Add explicitly optional model, provider, and channel adapters behind stable ports. Keep
vendor tests separate, prevent live data from entering public fixtures, and require separate
live acceptance. The reference path remains deterministic. Semantic Memory is not required
for P7.

Exit: reference behavior stays deterministic and optional adapter contracts pass.

Accepted result: P7 is accepted and merged. It adds stateless provider-neutral HTTP JSON
model and channel adapters behind unchanged ports, strict startup opt-in, safe credential
files, bounded transport, ambiguity/reconciliation, loopback-only synthetic/offline
evidence, and no migration 008. Deterministic intelligence and the reference channel remain
the defaults. Acceptance establishes no named-provider compatibility, real delivery,
production reliability/privacy/security, pilot readiness, or production readiness.

## P8 — Release and operational readiness

Add upgrade/backup/restore guidance, migration rollback evidence, diagnostics redaction,
supply-chain inventory, release reproducibility, and public release checks.

Converge only the implemented v0.1 scope; do not add Semantic Memory, Skill Learning, or a
multi-person collaboration platform to the release milestone.

Exit: v0.1 may be labeled a local reference release. Enterprise IAM, HA, distributed
operation, production tenancy, compliance, real-provider pilot claims, Semantic Memory,
Skill Learning, shared knowledge, multi-person collaboration, and Self-initiated autonomy
remain separate.

Accepted result: P8 is accepted and fast-forward merged to `main` at
`0bb80ab187932fbad42fbf665b8310987609a1f5`. It builds an unpublished `0.1.0` local
reference candidate and implements WAL-consistent private backup, fail-closed restore,
allowlisted diagnostics, deterministic supply-chain inventory, double-build comparison,
public release checks, and actual default Compose operations. No tag has been created, and
nothing has been published, uploaded, or formally released. Acceptance establishes only a
v0.1 local reference release candidate, not production readiness, production security,
high availability, enterprise IAM, real-provider readiness, compliance, or any other
excluded capability. Human evaluation, live-provider evidence, and the unmeasured
five-minute target remain `not_evaluated`.

## Historical P9-P15 v0.2 Public Pilot sequence

The following phases are non-mergeable and non-skippable. Every phase must complete this
sequence before the next phase can be planned or started:

```text
development complete
-> independent acceptance
-> scoped correction when required
-> final acceptance
-> fast-forward merge
-> main verification
-> only then plan the next phase
```

Passing one phase never authorizes the next. v0.2 targets a Public Pilot, not production-
ready 1.0. The plan does not claim HA, enterprise IAM, production tenancy/security,
large-scale multi-tenancy, compliance certification, or production readiness.

## P9 — Productization Rebaseline

Create only v0.2 product/architecture/security documents, ADRs, the fixed acceptance
contract, governance gates, tests, provenance, and `static`/`synthetic_offline` evidence.
Define AgentPackage, ColleagueDeployment, ExternalConnection, ConnectorGrant,
AutomaticEffectAuthorization, SourceReference/SourceCursor, language, compatibility,
provider, privacy, and live-evidence boundaries. Inventory existing milestone-shaped
Studio/API metadata without editing runtime files.

Exit: P9 direct and aggregate gates pass from the exact base; P0-P8 history and migrations
001-007 remain byte-identical; migration 008 is absent; product/runtime change count is
zero; evidence claims only `p9_productization_rebaseline_candidate`; status is development
complete awaiting independent acceptance. P9 acceptance does not authorize P10.

## P10 — Mac Quickstart and Distribution

Add prebuilt, signed, attested multi-architecture GHCR images; `dc`
doctor/quickstart/up/down/status/backup/restore/update/uninstall; Application Support
layout; FileVault and secret boundaries; `zh-TW`/`en-US` translation-key foundation;
product metadata; and a deterministic measured five-minute Mac quickstart.

P10 owns removal of user-visible milestone branding and FastAPI product metadata. Existing
`/p5` and `/p6` routes remain compatibility surfaces. New v0.2 public APIs use stable
product vocabulary under `/api/v1` and require a separate alias/deprecation/removal
contract. P10 adds no AgentPackage lifecycle, OpenAI gateway, or Microsoft 365 connector.

Exit: signed/attested distribution and deterministic quickstart gates pass with secret and
compatibility boundaries; no P11+ capability is present.

Development checkpoint: P10 is isolated on `codex/p10-mac-quickstart` from exact accepted
P9 base `11aa240af8db2ca515325dc059b1a77f7badc874`. The local candidate passed its retained
P9, digest-bound OCI, Compose, and Mac quickstart gates. A later explicit authorization
fixes a one-time GHCR publication/signature/attestation workflow and independent read-only
verification lifecycle. Only complete `passed` evidence followed by workflow deactivation
may produce a remote distribution candidate for independent acceptance. This is not P10
acceptance or a Release; P11 does not start.

## P11 — Agent Package and Multi-Agent Lifecycle

Add the declarative non-executable `dc-agent/v1` schema; package
inspect/validate/install/upgrade/rollback/trust/revoke; GitHub artifact attestation and
explicit trust review; Catalog; deployment registry; no more than ten active Agents;
bounded declarative workflows; and migration of the single v0.1 colleague to a
legacy/manual ColleagueDeployment without authority loss.

An AgentPackage requests capabilities only and is not an S4 Skill. Updates create new
drafts and never auto-apply. Stale/revoked versions are refused. Migration 008 may first be
added here only if an additive schema need exists; migrations 001-007 remain immutable.
New schemas and APIs use stable product terms, not milestone names.

Exit: package safety/provenance/trust/update/rollback, legacy preservation, and ten-Agent
namespace/isolation gates pass. Multiple deployments do not establish S3 collaboration.

### Superseded P9 assignment: P12 — OpenAI Model Gateway

Implement the OpenAI `gpt-5.5` Responses API gateway with Structured Outputs,
`store:false`, bounded input/output and usage/cost, connection lifecycle, prompt layering,
refusal/incomplete/schema-error handling, prompt-injection refusal, and model provenance.
Expose no function/hosted tools, MCP, browser/computer use, shell, connector credentials,
or execution authority. The server reconstructs every authoritative field.

Official OpenAI docs and actual project access are rechecked before development and every
live acceptance. An unavailable/incompatible model requires a Change Decision. No silent
substitution is allowed. Without actual project access, live acceptance is
`not_evaluated`. P12 executes no connector or external effect.

Exit: static/synthetic gateway contracts pass; private live compatibility passes only when
actual project access is available and separately stored.

### Superseded P9 assignment: P13 — Microsoft 365 Connector Foundation

Implement one dedicated delegated Microsoft 365 work/school identity per Agent; verified
project multi-tenant and BYO single-tenant public-client App modes; device-code flow;
user-consent/Admin-pre-consent/selected-resource lifecycle; Outlook per-folder delta;
Teams allowlisted bounded-date polling with message ID/etag dedupe and no public
webhook/relay; Planner read/write with ETag/`If-Match`; SharePoint selected-site/folder
read-only; and ExternalConnection/ConnectorGrant lifecycle.

Test Graph 401/403/429/5xx, refresh/revoke, throttling, ambiguity, retry,
reconciliation, restart cursor, cross-Agent/tenant denial, and bounded temporary source
context. Connector content is not S1 Semantic Memory. Without real tenants, named-provider
compatibility remains `not_evaluated`; mock/stub/loopback cannot substitute.

Exit: connector authority, cursor, minimization, and synthetic/loopback gates pass; private
live compatibility is reported only from real authorized tenants.

### Superseded P9 assignment: P14 — Built-in Project Tracker

Add the bilingual official `project-tracker` AgentPackage plus setup, deploy, health,
timeline, usage, and audit UI. Implement the exact effect outcomes
`auto_within_boundary`, `require_approval`, and `deny`, with durable
AutomaticEffectAuthorization separate from HumanApprovalDecision. The built-in does not
request `delete_task`; third-party deletion requests are separately prominent.

Prevent self-reply, Agent-to-Agent loops, duplicate messages/effects, replay, and
notification flooding. P14 adds no Semantic Memory, shared knowledge, Agent collaboration,
or executable Skill runtime.

Exit: end-to-end synthetic/loopback tracker, effect-policy, failure, restart, and audit
gates pass without live-provider overclaim.

### Superseded P9 assignment: P15 — Always-on and Public Pilot Release

Add Mac local and Linux/Mac mini always-on profiles, SSH-tunneled Studio, a ten-Agent
72-hour soak, live OpenAI/Microsoft 365 acceptance, human evaluation, and release
artifacts/SBOM/checksums/attestations.

Minimum private live prerequisites are two Microsoft 365 test tenants, ten dedicated Agent
test accounts, one usable OpenAI test project, one verified project multi-tenant Entra
public-client App, one BYO single-tenant App, delegated user-consent and Admin-consent test
capability, real Outlook/Teams/Planner/SharePoint test data, and private live-acceptance
storage outside the public tree. A mock, stub, or loopback cannot satisfy this live gate.

Exit: all static, synthetic, live-private, human-evaluation, security/privacy, soak,
distribution, and rollback requirements pass. Tag, push, publish, upload, or Release
creation still requires final live acceptance and separate explicit user authorization.

The preceding P12–P15 assignments are retained only as historical P9 planning context.
They are prospectively superseded by the accepted B+ P12–P20 sequence below; no accepted
P0–P11R history is changed.

## P12 — Public Pilot Continuity Rebaseline

Align the living product, architecture, security, roadmap, contribution, CI-governance,
and provenance records to the accepted B+ decision. Establish only contracts and tests
for the exact P12–P20 order, authority and identity boundaries, durable continuation,
Semantic Memory, trigger recovery, bounded proactivity, Microsoft transport ownership,
migration ownership, historical replay, evidence separation, and Public Pilot claims.

P12 changes no executable product behavior. It adds no migration and cannot create a
runtime, API, CLI, Studio, connector, dependency, distribution, evidence, Release, or
publication capability. The immutable acceptance contract is `docs/p12/acceptance.md`.

Exit: the P12 implementation-head gates pass from the exact accepted P11R base with the
exact changed-path set, immutable history, exact-object P11R replay, complete provenance,
protected P10 identities, and zero publication. Evidence and final acceptance remain
separately authorized.

## P13 — Migration Parser Correction and OpenAI Model Gateway

The first implementation commit contains only the shared migration parser correction and
its related tests. Parser-scope correction commits may follow if required, but migration
009, Gateway, dependency, API, and Studio behavior remain forbidden until fresh and
upgrade paths for migrations 001–008, trigger-body parsing, rollback, and restart all pass.

After that independent sub-gate, add the bounded OpenAI Responses API Gateway with
Structured Outputs, `store:false`, refusal/incomplete/error handling, exact model
provenance, and no tool or effect authority. An unavailable or incompatible model requires
a Change Decision; no silent substitution is allowed.

Migration: P13 uniquely owns additive migration 009 for Gateway connection, model,
usage, and provenance state. Migrations 001–008 remain immutable.

Exit: the parser-first sub-gate and the separately accepted Gateway gate pass. Live
compatibility remains `not_evaluated` without a separately authorized real project.

## P14 — Microsoft 365 Connector Foundation

Own source identity, cursor, pull-once and explicit sync, provider dedupe, and bounded
Microsoft transports. Establish Outlook existing exact-thread reply, Teams allowlisted
existing-chat reply, and Planner latest-ETag `If-Match` conditional update; SharePoint
selected resources remain read-only. Every external write requires an existing exact,
current `HumanApprovalDecision` from an authorized HUMAN principal.

P14 reuses effect proposal, outbox, fencing, idempotency, `EffectAttempt`, `ActionResult`,
and reconciliation. It cannot create, infer, or accept `AutomaticEffectAuthorization`, and
does no raw-event correlation, `WaitingCondition` binding, wake, continuation, memory, or
proactivity.

Migration: P14 uniquely owns additive migration 010 for Microsoft connection, grant,
source identity, cursor, dedupe, and transport state.

Exit: delegated authority, bounded reads, all three HUMAN-approved write transports,
duplicate dispatch, ambiguous-outcome reconciliation, stale/revoked authority, Planner
409/412 and stale-ETag reproposal, and SharePoint write denial pass independently.

## P15 — Durable Project Continuation

Add `ProjectScope`, the exact five-value `ProjectContinuationState` (`active`, `waiting`,
`needs_human`, `completed`, `stopped`), `WaitingCondition`, `GoalBinding`, questions, next
actions, checkpoints, leases, and recovery takeover. `completed` and `stopped` are
terminal; `paused` belongs only to P18 `ProactivityState`.

P15 accepts only a `NormalizedWaitingSignal` carrying an exact `WaitingCondition` ID.
Before P17 acceptance, an explicit binding can be created only through a server-side
operation by an authorized HUMAN principal. P15 performs no raw-provider-event
correlation, polling, or provider dedupe.

Checkpoint durably before entering `waiting` or `needs_human`, after a state-changing
decision commit, after effect result or reconciliation, before `stopped` or `completed`,
and for lease release, graceful shutdown, and recovery takeover. A new process with an
empty chat context must reconstruct the same work state and memory retrieval-set digest
from durable state alone.

Migration: P15 uniquely owns additive migration 011 for the exact continuation state,
checkpoints, exact waiting kinds/statuses and ANY/ALL groups, deadlines, one-time
consumption, questions, actions, `GoalBinding`, and explicit signal binding.

Exit: normalized-signal, exact HUMAN binding, checkpoint, restart, lease, takeover, and
blank-chat recovery scenarios pass without raw-event correlation.

## P16 — Semantic Memory Lifecycle

Add tiered memory-candidate admission. `MemoryAdmissionDecision` has exactly `admit` and
`reject`; it never substitutes for `HumanApprovalDecision`. Correction, supersession,
revocation, deletion, and expiry are separate post-admission lifecycle decisions. The
P12 non-normative name `MemoryLifecycleDecision` does not fix P16's final type or schema.

`MemoryRecord` states are exactly `active`, `superseded`, `revoked`, `deleted`, and
`expired`; correction creates a new immutable version and silent overwrite is forbidden.
`MemoryRetrievalSet` is an immutable bounded selection with purpose, checkpoint identity
and revision, as-of time, record identity/version/content digest, citation/source,
inclusion order, exclusion reasons, and a canonical ID and digest. Checkpoints retain only
that ID and digest, not memory bodies.

Migration: P16 uniquely owns additive migration 012 for candidates, admit/reject,
immutable records and versions, conflicts, separate lifecycle, retention, revocation,
deletion watermarks, and retrieval sets.

Exit: independent Continuation and Memory gates pass, including negative authority,
versioning, retention, revocation, deletion, bounded retrieval, and restart cases.

## P17 — Trigger, Recurring Schedule, Heartbeat, Correlation, and Recovery

Own autonomous bounded polling, raw-provider-event correlation, ambiguous quarantine,
wake, startup recovery, schedules, and heartbeat semantics. `TriggerCorrelation` states
are exactly `received`, `matched`, `ambiguous`, `consumed`, and `ignored`; only `matched`
can enter one-time atomic consumption and `ambiguous` is quarantined.

DST gap/fold and catch-up behavior is conservative and bounded. A
`RecoveryScanCheckpoint` cursor is only a bounded-scan optimization, never the source of
truth. Host replacement or cursor loss reconstructs from durable incomplete state without
missing a waiting project. After P17 acceptance, only the correlation service may create
an event-derived explicit `NormalizedWaitingSignal` binding, with actor, authority/source
revisions, correlation, causation, dedupe, and replay protection.

Migration: P17 uniquely owns additive migration 013 for schedule and occurrence records,
all five correlation states, quarantine, wake, recovery, and scan checkpoints.

Exit: independent Trigger gate passes Outlook and Teams raw-event correlation,
ambiguity/quarantine, DST/catch-up, one-time wake, restart, cursor loss, and host
replacement recovery scenarios.

## P18 — Bounded Goal-driven Proactivity

Own `ProactivityState` and the only creation of `AutomaticEffectAuthorization`, including
low-risk eligibility and proof. P18 reuses P14's accepted Microsoft transports, outbox,
idempotency, `ActionResult`, and reconciliation exactly; it cannot add, fork, replace, or
complete a connector write adapter.

P18 may pause only `ProactivityState`. If HUMAN direction is required, it uses P15's
existing transition to `needs_human` and mandatory checkpoint; it does not add `paused` to
`ProjectContinuationState`. Before P18 acceptance a `GoalBinding` cannot generate a
proactive trigger.

Migration: P18 uniquely owns additive migration 014 for proactivity and automatic-effect
authorization records. There is no migration 015 owner in this roadmap.

Exit: the independent Proactivity gate replays P14's three accepted transports under
bounded automatic authorization and proves eligibility, pause, denial, replay, stale
authority, reconciliation, and no-new-adapter behavior.

## P19 — Built-in Public Pilot Project Tracker

Build the bilingual project-tracker experience only by composing independently accepted
P13–P18 primitives. P19 owns no connector write primitive and no migration. If the
required Outlook, Teams, or Planner transport is absent, the gate fails; P19 cannot add,
fork, bypass, or finish one.

Exit: the composition-only tracker gate passes setup, continuation, memory, trigger,
proactivity, authority, audit, and failure cases, including required-transport absence.

## P20 — Always-on Public Pilot Release

Add separately accepted always-on profiles, private-live OpenAI and Microsoft evaluation,
human evaluation, recovery and soak evidence, distribution evidence, and the final Public
Pilot release boundary. P20 owns no migration; migration 015 is absent unless a future
owner-approved acceptance contract assigns it.

Exit: every required static, synthetic, private-live, human-evaluation, security/privacy,
soak, distribution, and rollback gate passes. Any tag, Release, upload, or publication
still requires explicit authorization. Until then Public Pilot readiness remains
`not_evaluated`.

## Post-v0.1 outlook

The non-committing [Post-v0.1 Capability Outlook](product/post-v0.1-capability-outlook.md)
orders separately gated exploration as S1 memory-loop closure, S2 memory autonomy and
bounded goal-driven proactivity, S3 knowledge decentralization and multi-person
collaboration, and S4 a governed Skill system. Self-initiated autonomy may be considered
only after those stages; none of these capabilities is required for the v0.1 P4–P8 gates.
S1–S4 and Self-initiated autonomy have not started, do not start automatically, and remain
uncommitted work behind independent future Gates.

P11 and the P11R CI-alignment correction are accepted history. The exact P12–P20 sequence
above prospectively realizes bounded parts of this outlook while preserving independent
Continuation, Memory, Trigger, and Proactivity gates. No later capability starts or gains
an acceptance claim merely because it appears in this roadmap.
