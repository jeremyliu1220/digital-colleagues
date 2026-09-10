<!-- SPDX-License-Identifier: Apache-2.0 -->

# ADR 0011: Public Pilot Continuity Rebaseline

- Status: Accepted for P12 governance implementation
- Decision date: 2026-09-10
- Scope: prospective P12-P20 roadmap, contracts, authority, evidence, and ownership
- Normative contract: `docs/p12/acceptance.md`

## Context

P11R closed the accepted P0-P11R line at commit
`c1562ea5201394d8a278f4b644daf4029cbb5bd4`. The original P9 plan did not give durable
project continuation, semantic memory, autonomous trigger recovery, and bounded
goal-driven proactivity independent gates. It also placed connector transport and
automatic authorization too close together to prove their authority boundaries.

The Public Pilot roadmap therefore needs a forward-only Change Decision. Accepted history
and executable behavior stay unchanged. P12 records governance, tests, provenance, and CI
policy only; it does not implement any future record or provider capability.

## Decision

The exact non-skippable order is:

1. P12 — Public Pilot Continuity Rebaseline.
2. P13 — migration parser correction, then OpenAI Model Gateway.
3. P14 — Microsoft 365 Connector Foundation.
4. P15 — Durable Project Continuation.
5. P16 — Semantic Memory Lifecycle.
6. P17 — Trigger, Recurring Schedule, Heartbeat, Correlation, and Recovery.
7. P18 — Bounded Goal-driven Proactivity.
8. P19 — Built-in Public Pilot Project Tracker.
9. P20 — Always-on Public Pilot Release.

Every phase has an immutable acceptance contract, implementation authorization, local
gate, exact-head CI, independent acceptance, final acceptance, fast-forward merge, main
push, and remote closeout. Passing one phase never starts the next.

### Product decisions

The product is a local-first Public Pilot rather than production-ready 1.0. P20 retains
the two-Microsoft-tenant, ten-account, ten-deployment, two-App-mode, HUMAN evaluation, and
72-hour soak boundary. Named-provider and private-live results remain `not_evaluated`
until the owning gate has actual authorized access.

Semantic memory uses tiered admission. `MemoryAdmissionDecision` has only `admit` and
`reject`. Correction, supersession, revocation, deletion, and expiry are post-admission
lifecycle. `MemoryLifecycleDecision` is only a P12 working label; P16 fixes the exact type
name and schema. No memory decision is a `HumanApprovalDecision` or authority source.

Recurring time is conservative: a DST gap skips the occurrence, a fold admits only the
earlier occurrence, and catch-up emits at most the latest occurrence within 24 hours.
Arbitrary cron and provider-global exactly-once claims are excluded.

### Authority and identity

HUMAN, MODEL, and SERVICE principals remain disjoint. Canonical HUMAN roles are
`tenant_admin`, `colleague_user`, and `auditor`, derived and revalidated server-side.
`ExternalPartyReference` is not a Principal and is never HUMAN. An external reply cannot
satisfy `human_decision`, create `HumanApprovalDecision`, or expand authority, goal, scope,
participant, resource, or retention bounds; such content can only request HUMAN review.

`ProjectScope` contains exactly deployment Namespace and `project_id`. It is not a global
namespace or an authority container. Active Mandate, Policy, Goal, membership, grant, and
source revisions belong to continuation/checkpoint state and are revalidated each time.

`GoalBinding` contains the HUMAN-accepted objective digest, success criteria, bounds,
expiry, exact Mandate and Policy revisions, namespace, and causal identity. Model,
SERVICE, connector, external party, and memory cannot create, broaden, renew, or
self-accept it. P15 may persist it; only P18 may use it for proactive triggers.

### Continuation, waiting, and recovery

`ProjectContinuationState` has exactly `active`, `waiting`, `needs_human`, `completed`, and
`stopped`; the final two are terminal. `running` and `paused` are invalid. P18 pause belongs
only to `ProactivityState`, and HUMAN direction uses the P15 `needs_human` transition.

`WaitingCondition.kind` is exactly `human_decision`, `external_reply`, `timer_at`,
`dependency`, or `effect_reconciliation`. Status is exactly `open`, `satisfied`,
`expired`, `cancelled`, or `ambiguous`. Conditions have explicit ANY/ALL grouping,
deadline, exact predicates, and one-time atomic consumption.

P15 checkpoints are mandatory before waiting or needs-HUMAN transitions, after each
state-changing decision, after effect result and reconciliation, before stop/complete and
lease release, during graceful shutdown, and during fenced recovery takeover. A new
process with an empty chat context must reconstruct the same continuation state and
`MemoryRetrievalSet` ID/digest from durable state alone.

`RecoveryScanCheckpoint` is only a bounded-scan optimization. Durable nonterminal
projects, waits, schedules, occurrences, correlations, effects, reconciliations,
checkpoint intents, leases, fences, and authority/watermarks are truth. Cursor loss or host
replacement triggers a bounded full scan and cannot omit an old waiting project.

### Memory and trigger records

`MemoryRecord` versions are immutable and have exactly `active`, `superseded`, `revoked`,
`deleted`, or `expired` lifecycle status. Correction creates a new version; silent
overwrite is forbidden. `MemoryRetrievalSet` is immutable and bounded and records purpose,
checkpoint identity/revision, as-of time, record ID/version and digests, citations/sources,
inclusion order, exclusions, and canonical ID/digest. Checkpoints store only that ID and
digest, not a memory body.

`TriggerCorrelation` status is exactly `received`, `matched`, `ambiguous`, `consumed`, or
`ignored`. It binds a unique source occurrence to project/wait/checkpoint/wake, dedupe,
correlation, and causation. Only `matched` enters atomic one-time consumption;
`ambiguous` is quarantined.

Before P17, a `NormalizedWaitingSignal` binding can be created only through an authorized
HUMAN server-side operation naming one exact WaitingCondition ID/revision. After P17 is
accepted, an authorized correlation SERVICE may create it only after exact-one matching.
Provider, model, external party, adapter, and caller cannot submit authoritative binding.

### P14, P15, P17, P18, and P19 ownership

P14 owns connection/grant use, source identity, `SourceCursor`, bounded `pull_once` or
HUMAN-requested explicit sync, provider normalization/dedupe, and three transports:
Outlook existing exact-thread reply, Teams allowlisted existing-chat reply, and Planner
latest-ETag `If-Match` update. Every P14 external write requires an exact current
`HumanApprovalDecision`. SharePoint stays selected-resource read-only.

P15 consumes only a durable normalized signal already bound to an exact wait. It does not
poll or correlate raw provider events. P17 owns autonomous polling, raw-event correlation,
ambiguity quarantine, binding by the correlation SERVICE, wake, and startup recovery.

P18 alone adds `AutomaticEffectAuthorization` and its low-risk proof. It reuses P14's
accepted transports, outbox, fencing, idempotency, `EffectAttempt`, `ActionResult`, and
reconciliation without adding or forking a connector adapter. P19 only composes accepted
P13-P18 primitives; a missing required transport fails its gate.

### Parser and migrations

P13's first implementation commit contains only the shared migration parser and related
tests. Parser-scope correction commits may follow, but migration 009, dependency, Gateway,
API, and Studio work wait until fresh/upgrade 001-008, trigger-body, rollback, restart, and
retained regressions all pass.

Migrations 001-008 and their manifest remain immutable. Sole future owners are P13 for
009, P14 for 010, P15 for 011, P16 for 012, P17 for 013, and P18 for 014. P19 and P20 add
no migration; 015 has no owner.

### P12 governance and evidence

P12 has an immutable acceptance-only first commit, one or more linear single-parent
implementation/scoped-correction commits, and—only after exact implementation-head CI and
separate evidence authorization—a summary-only final commit. No amend, rebase, squash,
force rewrite, or merge commit is permitted. Exact implementation-head CI and exact
final-candidate CI are distinct.

Evidence preflight is read-only. It binds explicit GitHub authentication/capability,
numeric CI run, exact head, protected GHCR identities, exact `pyproject.toml` and
hash-locked requirements identities, PEP 440 comparisons using
`importlib.metadata.version()` and `packaging.version.Version`, and certificate-verified
TLS. An accepted hash-locked certifi bundle is allowed only after default CA verification
fails and its version, file type, non-symlink status, wheel hash, and bundle SHA-256 pass.
No insecure fallback, secret, certificate content, or absolute CA path is public evidence.

P10's active and superseded publication source commits, digests, discovery tags, versions,
timestamps, signatures, attestations, lifecycle, and nine run identities are permanently
protected. They cannot be overwritten, retagged, republished, deleted, or relabeled.

## Consequences

- Continuation, memory, trigger/recovery, and proactivity each receive an independent gate.
- Transport mechanics precede and remain separate from automatic-effect authority.
- Recovery and memory remain explicit, bounded, revisioned, and non-authoritative.
- P12 can prove planning coherence and future enforcement without introducing behavior.
- P20 remains the sole gate that may establish a Public Pilot claim, and publication still
  requires separate authorization.

## Rejected alternatives

- Treating a recovery cursor as truth: it can omit old waiting work after loss or host
  replacement.
- Adding `running` or `paused` to project continuation: it changes the P15 state machine;
  pause belongs to P18 proactivity.
- Combining admission and memory lifecycle: it obscures immutable history and authority.
- Letting P15 correlate raw events or P19 build missing transports: it moves ownership and
  defeats independent gates.
- Creating automatic authorization in P14: it conflates transport with authority.
- Rewriting or deleting the rejected local v1 acceptance attempt: it would erase the
  discrepancy record.

## Claim boundary

P12 establishes only the accepted B+ governance representation, deterministic checkers,
synthetic negative tests, provenance, and current-CI transition. All future records,
transports, model/provider calls, migrations 009-014, runtime behavior, private-live
evidence, HUMAN evaluation, soak, release, and Public Pilot readiness remain unimplemented
and `not_evaluated` until their owning gates pass.
