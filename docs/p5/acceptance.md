<!-- SPDX-License-Identifier: Apache-2.0 -->

# P5 Revisioned Colleague Builder Acceptance Contract

Status: fixed development contract. P5 may be described only as **development complete,
awaiting independent acceptance** after every gate below passes. This contract is fixed
before product, migration, API, runtime, or Studio implementation and must not be deleted,
weakened, or rewritten to fit an implementation result.

## Baseline and historical boundary

P5 starts from the accepted P4 `main` baseline
`259e5627c0a4d713934263efe18caf8c675a1669`. Its merge-base with `main` must remain that
commit. P0–P4 acceptance records, artifacts, evidence, receipts, fingerprints, and
migrations 001–005 remain unchanged. P5 does not rerun or rewrite historical evidence.

P5 adds revisioned colleague drafts, exact review and confirmation, typed working and
attention policy, deterministic enforcement, Studio editing, migration 006, and synthetic
offline evidence. It uses only the existing deterministic Event/Timer runtime and reference
channel. P5 does not add a provider, external effect, open-ended goal, Semantic Memory,
Skill, shared knowledge, collaboration platform, or Self-initiated autonomy.

## Architecture and authority invariants

The dependency direction remains:

```text
Pure core <- application and governance -> stable ports
                                   <- intelligence adapters
                                   <- infrastructure and HTTP adapters
```

- Pure core uses frozen standard-library dataclasses, Enums, and Protocols. FastAPI,
  Pydantic, SQLite, React, provider/channel SDKs, ORMs, orchestration frameworks, ambient
  time, randomness, environment, filesystem, process, and network access remain outside.
- Pydantic remains confined to HTTP mapping in `api/`. Application and governance depend
  on ports, not concrete adapters or HTTP types.
- Profile remains descriptive presentation and preference data. It never grants a
  permission, prohibition, trigger, budget, stop, escalation, approval, or effect.
- Mandate remains authoritative for mission, service relationship, responsibilities,
  capabilities, constraints, and effect boundaries.
- A separate revisioned `ColleaguePolicy`, normatively defined by ADR 0004 and bound to the
  same colleague namespace and active Mandate, governs working hours, allowed durable
  triggers, bounded proactivity, user-visible notification/interruption, wake budget, stop,
  and escalation. Policy cannot grant an effect absent from the Mandate.
- Identity cards and diffs are projections only. Memory, Skills, model output, work history,
  initial P4 free-form working-hours text, and UI state are never authority sources.
- Every wake, proposal, approval, dispatch, stop, and escalation names the exact Mandate
  and policy revision applied. Policy is revalidated after model output but before proposal
  persistence, and again before approval or dispatch.
- HUMAN, MODEL, and SERVICE principals remain durable disjoint kinds. Only a current local
  HUMAN `tenant_admin` session may create, edit, review, cancel, or confirm a P5 draft.
  MODEL and SERVICE principals cannot exercise that authority or author human approval.
  Complete change-approval hardening remains P6.

## Draft record and lifecycle gate

Every draft persists a complete colleague namespace; server-generated draft ID; monotonically
increasing content revision; base Profile, Mandate, and policy IDs/revisions; complete proposed
Profile, Mandate, and policy values; typed explicit defaults and sources; canonical diff;
canonical digest; lifecycle state; HUMAN author; server timestamps; schema version;
correlation ID; and causation ID.

The finite lifecycle is:

```text
draft -> reviewable -> confirmed
   |          |
   +----------+-> cancelled
              +-> stale
```

- Create produces revision 1 in `draft`. Every content update increments the revision
  exactly once and returns to `draft`. No update may lower, reuse, or skip the expected
  revision. Review validates the complete proposal and records `reviewable` without
  changing the reviewed content revision.
- Only the exact `reviewable` revision and digest can be confirmed. `confirmed`,
  `cancelled`, and `stale` are terminal. A terminal draft cannot be updated, reviewed,
  cancelled again, or applied.
- A draft is completely inert before successful confirmation: it does not change active
  Profile, Mandate, policy, worker context, runtime authorization, counters, stop state,
  proposal eligibility, or identity-card output.
- Calls never submit authoritative tenant, namespace, role, principal kind, actor ID,
  server time, lifecycle state, schema version, generated IDs, or trusted digest. The server
  derives them from the authenticated session and persisted state.
- Not found, validation, permission, stale conflict, idempotency conflict, and replay
  outcomes are stable and distinguishable without returning private payloads or database
  details.

## Canonical review, diff, and explicit defaults

The canonical draft digest is a versioned SHA-256 digest of deterministic canonical JSON
covering the complete namespace, draft ID/revision, all three base identities/revisions,
the full proposed values, explicit defaults with their source, and canonical diff. It never
trusts a caller-supplied digest. Maps are key-sorted, arrays whose order is semantic retain
order, set-like identified records are ordered by stable ID, and times use UTC `Z` form.

The review response includes the exact draft revision and digest, an active-only identity
card, a proposed identity-card preview clearly labeled inert, and before/after diffs split
into Profile, Mandate, and policy sections. Diffs classify each item as `added`, `removed`,
`changed`, `narrowed`, `expanded`, or `unchanged`; an authority change that cannot be
canonically classified is rejected rather than guessed. Profile edits never appear as an
authority expansion.

Every omitted optional policy setting receives a typed value plus a source of
`p5_system_default`; required authority values cannot be defaulted from blank text. Defaults
are persisted, visible in the diff and confirmation view, and become active only after the
Admin confirms. Unknown fields, empty authority strings, missing required values,
contradictory rules, unsupported enums, and ambiguous authority changes fail closed. P4
free-form working-hours data is preserved as legacy descriptive context and marked
`legacy_unconfirmed`; it is never parsed into P5 authority.

## Exact confirmation and atomic apply gate

Confirmation supplies only a draft ID, expected draft revision, expected base Profile
revision, expected base Mandate revision, expected base policy revision, expected canonical
digest, and idempotency key. In one `BEGIN IMMEDIATE` transaction the application:

1. resolves the current Admin session and complete namespace;
2. validates Origin, CSRF, expiry, HUMAN kind, `tenant_admin`, action authority, and replay;
3. loads the exact reviewable draft and re-computes its canonical digest;
4. compare-and-swaps all three active base revisions;
5. persists the new Profile and/or Mandate and policy revisions as one active snapshot;
6. marks the draft confirmed, invalidates authority-bound stale contexts when applicable,
   records safe causal audit and replay state, and commits.

Any mismatch rolls back the entire transaction. Profile and authority cannot partially
apply. There is no silent rebase, merge, last-write-wins, retry with new state, or automatic
overwrite. Two drafts from the same complete base can yield at most one success; the other
is durably marked stale with digest-only safe evidence. A successful replay with the same
idempotency key and request returns the original result; reuse of that key for different
content is a conflict. Authority-affecting changes make older proposals, approvals, and
worker contexts stale and they fail closed when used.

## Typed policy validation and deterministic semantics

### Working hours

- Policy stores an IANA timezone and non-empty typed weekly windows with weekday, local
  start minute, and local end minute. A window may cross midnight and is attributed to its
  start weekday. Zero-duration, invalid, duplicate, or overlapping weekly coverage and
  unknown timezones are rejected.
- Runtime converts an injected UTC instant through IANA timezone data before matching local
  wall-clock windows. Both folds during a DST rollback are governed identically; nonexistent
  local wall times are never synthesized. Cross-midnight coverage is deterministic.
- Outside working hours the configured finite outcome (`defer`, `no_op`, `stop`, or
  `escalate`) is persisted with a safe causal reason before proposal creation. It is never
  guessed and never presented as successful interaction.

### Allowed triggers and proactivity

- Allowed trigger kinds are limited to the existing durable `event` and `timer` classes.
  A disallowed class is rejected or produces a persisted governed no-op before wake or
  proposal creation.
- Proactivity governs only allowed durable triggers. `disabled` produces no user-visible
  suggestion, proposal, or notification. It cannot create goals, arbitrary schedules,
  background browsing, or self-initiated work.

### Notification and interruption

- Notification policy controls whether an otherwise eligible user-visible notification is
  emitted. Interruption policy controls whether an eligible user-visible output may
  interrupt now. Their outcomes are distinct from proposal suppression and effect
  permission.
- Suppression does not authorize an effect, hide exact-effect approval, remove audit, or
  count as successful interaction. P5 performs no real notification provider effect.

### Wake budget

- Policy stores a positive integer limit and a finite period (`hour`, `day`, or `week`).
  Durable namespaced UTC bucket counters count a unique accepted trigger occurrence at most
  once across restarts and duplicate delivery, regardless of Event/Timer class.
- Exhaustion is checked and incremented atomically before wake/proposal creation. It yields
  the configured governed refusal without another proposal. Restart, duplicate event,
  alternate trigger class, or replay cannot evade the budget.

### Stop and explicit resume

- Stop conditions are a finite typed set: Admin stop, budget exhaustion when configured,
  repeated deterministic failure threshold, or finite-work terminal state. No arbitrary
  code or natural-language expression is executable policy.
- A durable stopped state rejects new wakes and proposals while retaining history. Resume
  requires an explicit authorized and confirmed policy revision that removes the applicable
  condition or sets the typed run state to active. Nothing resumes implicitly.

### Escalation

- Escalation conditions are a finite typed set: outside-hours escalation, budget
  exhaustion, repeated deterministic failure threshold, or explicit blocked-work state.
- A match creates a visible, namespaced, restart-safe, safe causal escalation record and
  Studio state. Escalation is not approval, a Mandate change, effect authorization, or an
  external notification and cannot expand authority.

## Persistence and migration gate

Additive `migrations/006_revisioned_colleague_builder.sql` adds only P5 schema. Migrations
001–005 and their manifest identities remain unchanged. Migration 006 and the manifest
checksum are immutable once evidence is generated. A P5 provenance receipt records new
public-document-based implementations and zero transformed source files unless an
allowlisted digest-verified migration is separately authorized.

Fresh schema creation and an actual version-5 upgrade produce the same schema and preserve
all earlier records. Every P5 row carries schema version, complete namespace, server UTC
timestamps, and optimistic revisions. Drafts, diffs, confirmations, active policy,
namespaced budget counters, run/stop state, escalation evidence, safe audit, and replay
state survive reconstruction over the same SQLite file. WAL, foreign keys, busy handling,
transaction rollback, and stable store ports remain enforced. P5 makes no rollback,
distributed-store, or production-migration claim.

Legacy P4 colleagues remain loadable with their accepted behavior and an explicit
`legacy_unconfirmed` policy status. They acquire typed P5 authority only through a reviewed
and confirmed draft; no migration or runtime fallback parses P4 text.

## HTTP and Studio gate

Typed HTTP mappings expose create, update, review, confirm, and cancel operations plus
active/draft retrieval. Every mutation enforces the P4 cookie session, exact Origin, CSRF,
session expiry, role/kind, namespace, expected revision, and idempotency controls on the
server. Request models reject unknown fields and caller authority. Error responses expose
stable safe categories only.

Studio visibly separates descriptive Profile from authoritative Mandate and policy. It
shows active, base, and draft revisions, the exact canonical digest, active identity card,
inert preview, before/after diff, authority expansion/narrowing/removal/addition, and every
explicit default. Confirmation binds the values currently displayed. Primary actions are
keyboard-operable. Loading, empty, success, validation, permission, stale, idempotency
conflict, cancelled, and generic error states are mechanically covered. Studio never
auto-rebases, auto-retries, or overwrites a stale draft, and the active identity card never
includes unconfirmed state.

## Runtime and evaluation gate

Policy is enforced before wake/proposal, after deterministic model output but before
proposal persistence, and before approval/dispatch. Existing namespace, exact-effect,
human-approval, replay, stale-Mandate, transactional outbox, ambiguity, restart, restricted
SERVICE context, reference-channel, and safe-causal-audit behavior retains regression
coverage. Unauthorized proposal escape rate remains targeted at zero.

Metric observations bind to the exact Mandate and policy revision. AI-initiated numerator
counts only a user-visible suggestion, proposal, or notification before a new user prompt;
internal wake/no-op does not count. Working-hours defer, notification suppression, proposal
suppression, and budget refusal remain distinct governed outcomes and are not successful
interactions. Unnecessary interruption is `observed` only with a durable evaluator
observation; eligible uncovered cases are `not_evaluated`. Zero denominators report
`not_applicable`, denominator zero, and a reason. Synthetic, offline, human, and
live-provider evidence remain separate; no human or live-provider evidence is fabricated.

## Compose Golden Path gate

The documented [P5 Golden Path](golden-path.md) and automated tests must cover:

1. isolated clean Compose start and Admin bootstrap;
2. existing or new colleague load and revisioned draft creation;
3. separate Profile and authority edits, identity preview, complete diff, and defaults;
4. exact revision/digest confirmation and revision increments;
5. actual container recreate with active state, draft history, and counters recovered;
6. working-hours, trigger, proactivity, interruption, and budget outcomes;
7. durable stop, explicit resume, and escalation without authority expansion;
8. same-base concurrent drafts with one apply and one stale refusal;
9. old proposal, approval, and runtime-context refusal after authority change;
10. complete safe causal audit, normal stop, and zero container/network/volume residue.

The runtime Gate uses a unique synthetic project name, unused loopback host ports, its own
temporary project-scoped volume, and reliable `finally` cleanup. Plaintext bootstrap,
session, or CSRF values never enter API, worker, Studio logs, public evidence, or Git.

## Required mechanical coverage

P5 tests, scripts, and collectors cover at least draft immutability/lifecycle; exact
revision/digest review and confirmation; concurrent stale drafts; atomic Profile/Mandate/
policy apply; Profile non-authority; defaults and ambiguous authority refusal; policy
validation; working hours including cross-midnight and DST; allowed/disallowed triggers;
disabled proactivity; notification/interruption suppression; durable budget/restart and
evasion; stop/resume; non-authorizing escalation; stale proposal/approval/context;
MODEL/SERVICE refusal; tenant/namespace crossover; P4 session, Origin, CSRF, expiry, replay,
and idempotency; migration 006 fresh/upgrade/checksum; SQLite reconstruction; Studio states
and keyboard operation; actual Compose runtime; public boundary, architecture, provenance,
residue, P4 immutability, and all P0–P4 regressions.

## Repeatable commands

```bash
git diff --check
python3 -B scripts/check_public_boundary.py .
python3 -B scripts/check_p4_repository.py .
python3 -B scripts/check_p5_repository.py .
python3 -B scripts/check_p5_provenance.py .
python3 -B scripts/check_p5_architecture.py .
PYTHONPATH=src python3 -B scripts/check_p5_migrations.py .
PYTHONPATH=src python3 -B scripts/check_p5_builder.py .
PYTHONPATH=src python3 -B scripts/check_p5_policy.py .
python3 -B scripts/check_p5_studio.py .
python3 -B scripts/check_p5_compose.py .
python3 -B scripts/check_p5_compose_runtime.py .
PYTHONPATH=src python3 -B scripts/check_p5_golden_path.py
make check
make evidence-p5
make check
make p5-compose-runtime
git diff --check
```

Corresponding Make targets are `p5-repository`, `p5-provenance`, `p5-architecture`,
`p5-migrations`, `p5-builder`, `p5-policy`, `p5-studio`, `p5-compose`,
`p5-compose-runtime`, `p5-golden`, and `evidence-p5`. `make check` is the complete P5
aggregate and retains every applicable P0–P4 gate. Historical evidence targets
`evidence-p0` through `evidence-p4` must not run.

## Evidence contract

Only after the acceptance and implementation commits exist and every direct Gate passes,
`make evidence-p5` may atomically create `artifacts/p5/summary.json`. It records branch,
base, merge-base, real implementation commit, subsequent evidence-commit target,
public-tree digest excluding exactly the P5 summary, migration identities, test identities
and results, retained P0–P4 and focused P5 results, actual Compose runtime and cleanup,
stale-draft and ambiguous-authority fault evidence, policy outcomes, revision-bound metric
status/denominator/source, evidence classes, claim limits, and explicit exclusions.

Evidence requires zero failures, errors, skips, and unexpected successes; zero
public-boundary exceptions; an actual Docker runtime; and zero cleanup residue. The
summary is committed separately, then all gates, actual Compose runtime, public boundary,
P4 immutability, history, and residue checks run again. No future commit SHA is invented.

## Explicit exclusions and prohibited claims

P5 does not implement or claim Semantic Memory, Skill Learning, a governed Skill system,
shared knowledge, a multi-person collaboration platform, Self-initiated autonomy, arbitrary
goal generation or scheduling, background browsing, real models/providers/channels, OIDC,
SSO, SCIM, general enrollment/session recovery, P6-complete RBAC or multi-party change
approval, PostgreSQL, distributed execution, high availability, encryption at rest,
production tenancy/security/privacy/compliance, P7 adapters, P8 release readiness, or
production readiness.

Passing development gates permits only the statement **P5 development complete, awaiting
independent acceptance**. It does not mean accepted, merged, production-ready, five-minute
complete, human validated, live-provider validated, or proven to improve colleague
experience.

## Stop condition

Stop on `codex/p5-revisioned-colleague-builder` only after the fixed acceptance commit,
implementation commit, and separate evidence commit exist; direct and aggregate gates and
the final actual Compose runtime pass; P0–P4 history/evidence and migrations 001–005 are
unchanged; cleanup and public-tree residue are zero; and index/worktree are clean. Do not
merge, push, tag, release, delete a branch, rewrite history, or begin P6.
