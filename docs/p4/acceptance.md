<!-- SPDX-License-Identifier: Apache-2.0 -->

# P4 Studio and Five-Minute Golden Path Acceptance Contract

Status: fixed development contract. P4 may be described only as **development complete,
awaiting independent acceptance** after every gate below passes. This document is fixed
before product code, migration, Studio, or Compose changes and must not be weakened to fit
an implementation result.

## Baseline and scope

P4 starts from accepted P3 plus the Roadmap rebaseline at
`660a191b03472ab090fcc19c1e9fffda6b6ca9fd`. Historical P0–P3 acceptance records,
artifacts, evidence, receipts, fingerprints, and migrations 001–003 remain byte-unchanged.

P4 adds the local Docker Compose topology, one-time bootstrap authentication, a real
React/TypeScript/Vite Studio, initial colleague creation, finite-work assignment, restart
inspection, deterministic Event and Timer wakes, an exact-revision proposal inbox,
approve/reject, a reference ActionResult, safe causal audit views, and synthetic/offline
colleague-experience measurements. The required reference path uses no real model,
provider, account, credential, external effect, or network service.

## Architecture invariants

The dependency direction remains:

```text
Pure core <- application and governance -> stable ports
                                   <- intelligence adapters
                                   <- infrastructure and HTTP adapters
```

- Core remains frozen standard-library dataclasses, Enums, and Protocols. It cannot import
  FastAPI, Pydantic, SQLite, Docker, React, provider/channel SDKs, an ORM, or an
  orchestration framework.
- Pydantic remains confined to HTTP request/response mapping at `api/`.
- Application and governance use stable ports and do not import concrete adapters or HTTP
  types. Time, entropy, identifiers, configuration, and I/O remain injectable.
- Session-derived `RequestPrincipalContext` replaces P3's edge injection assumption for
  browser requests. Namespace, tenant, role, principal kind, session identity, and
  authoritative time never come from a mutation body.
- Every persisted P4 record has an explicit schema version and complete namespace. The
  single `state.sqlite` is behind ports and is not an implied tenant-isolation boundary.
- Any schema addition is migration 004 or later. Migrations 001–003 and their manifest
  entries remain unchanged.
- P2/P3 namespace, principal separation, exact-effect, typed-constraint, revision,
  replay, lease/fencing, ambiguity, outbox, causal-audit, and deterministic-path controls
  remain fail closed and retain regression coverage.

## Authentication and authorization gate

The gate passes only if all of the following are repeatably demonstrated:

1. First start uses a cryptographically secure entropy port to create a bootstrap token
   with at least 32 random bytes (256 bits), an expiry no later than ten minutes, and a
   server-stored digest. No directly usable plaintext credential is stored in SQLite.
2. Plaintext bootstrap authority is available to the local operator exactly once through
   the documented operator-only retrieval boundary. Retrieval is atomic. It is absent
   from API, worker, and Studio stdout/stderr and their persistent container logs; it is
   never copied to audit, safe projections, fixtures, evidence, or Git.
3. Exchange is atomic, short-lived, single-use, and replay-resistant. It creates only the
   first durable HUMAN principal with the canonical `tenant_admin` role and one
   server-generated Admin session. The server selects tenant, namespace, principal kind,
   role, principal ID, and session ID.
4. Session persistence stores only a secure session-credential digest. The browser gets
   only an HttpOnly, SameSite=Strict cookie; HTTPS mode also sets Secure. Session expiry is
   enforced server-side.
5. Every mutation validates the session and durable principal, expiry, exact configured
   Origin, CSRF token, namespace, principal kind, canonical role, idempotency/replay state,
   and action-specific authority. Missing, mismatched, injected, stale, duplicated,
   cross-namespace, and IDOR attempts fail closed.
6. MODEL and SERVICE principals remain disjoint from HUMAN principals, cannot convert to
   HUMAN, and cannot author `HumanApprovalDecision`.
7. Studio visibility is never treated as authorization. Direct requests receive the same
   server-side denial as hidden or disabled controls.

P4 implements only the first bootstrap Admin needed for the Golden Path. General
enrollment, session recovery, and complete RBAC hardening remain P6 work and are not
claimed.

## Studio and initial-colleague gate

Studio must expose keyboard-operable primary actions and recognizable loading, empty,
success, rejection, stale, and error states for the main workflow. It must include:

- bootstrap token exchange;
- initial colleague builder and exact revision-1 confirmation;
- separate descriptive Profile and authoritative Mandate review;
- identity card, authority summary, and exact effect-boundary review;
- finite-work assignment;
- restart recovery inspection;
- deterministic Event and Timer trigger/wake controls;
- wake-cycle inspector and proposal inbox;
- approve/reject bound to an exact immutable proposal revision and digest; and
- reference ActionResult and complete safe causal-audit views.

The initial builder accepts display name, role description, service relationship, mission,
timezone, initial working context, initial working hours, working style, responsibilities,
capabilities, constraints/scope, and exact effect boundaries. Before commit it distinguishes
Profile from Mandate, identifies the exact revision to be created, and shows the authority
and effect-boundary summary. Profile presentation and preferences never grant authority.

P4 working hours are only initial, displayed, explicitly confirmed data. P4 does not add a
general working-hours enforcement engine, generalized modification flow, revision diff,
draft lifecycle, stale-draft workflow, policy editor, wake budget, proactivity policy,
notification/interruption policy, or stop/escalation policy builder; those belong to P5.

## Finite work, restart, and causal-audit gate

- An authenticated, authorized durable HUMAN assigns finite work. Complete namespace,
  exact Mandate revision, responsibility, assignee, correlation, causation, timestamps,
  schema version, and optimistic revision persist in `state.sqlite`.
- After an actual Compose restart, a fresh API/worker/Studio topology over the same durable
  volume reads the same identity, Mandate, work, runtime state, and causal history. Browser
  local storage and in-memory reconstruction do not count as persistence evidence.
- Studio shows wake reason, Event versus Timer trigger class, trigger identity, Agenda
  generation and handled generation, WakeCycle, Decision, proposal or deterministic no-op,
  relevant revisions, safe times, correlation, and causation.
- An internal Heartbeat/Wake that ends in deterministic no-op creates no proposal and does
  not count as an AI-initiated interaction.
- The safe causal chain is inspectable as `InputEvent -> trigger/Agenda -> WakeCycle ->
  Decision -> EffectProposal -> HumanApprovalDecision -> EffectAttempt -> ActionResult`.
  Audit, UI diagnostics, logs, fixtures, and public evidence contain only safe projections
  or digests, never raw private payloads, credentials, or live-provider data.

## Proposal inbox and exact approval gate

Each inbox item displays exact proposal revision, complete proposal digest, payload
integrity digest, safe effect projection, destination kind, action, effect boundary,
Mandate ID/revision, actor, complete namespace, expiry, approval state, and causal origin.
It is a proposal, never an already-authorized action.

Approve and reject bind to the exact immutable revision and complete digests. Stale,
expired, replayed, cross-namespace, wrong-role, wrong-principal-kind, digest-mismatched,
Mandate-drifted, partially rebound, unknown-constraint, and incomplete-constraint requests
fail closed. Reject records the decision but creates no `EffectAttempt`, outbox dispatch, or
channel call. UI or model review cannot legalize an unauthorized proposal.

## Colleague-experience metric definitions

P4 provides deterministic synthetic/offline observation points and repeatable calculation
for re-brief turns, wrong-memory rate, AI-initiated rate, proactive suggestion acceptance
rate, unnecessary interruption rate, human intervention count, completion rate, and
unauthorized proposal escape rate.

- **AI-initiated rate** is eligible opportunities where an allowed trigger produces a
  user-visible suggestion, proposal, or notification before a new user prompt, divided by
  eligible opportunities. Internal Heartbeats/Wakes, deterministic no-ops, and processing
  with no user-visible output do not enter the numerator. The metric is reported with
  proactive suggestion acceptance and unnecessary interruption; higher is not inherently
  better. Internal handling may be reported separately as trigger-response rate.
- **Unauthorized proposal escape rate** has as numerator unauthorized candidates that
  nevertheless create an `EffectProposal`, reach the inbox, or progress further, and as
  denominator every evaluated unauthorized candidate/attempt. Correct governance
  refusals remain in the denominator and leave safe causal evidence. Target: zero.
- A zero denominator is reported as `not_applicable` with the numeric denominator and a
  reason. It is never represented as 0% success/failure or proof of improvement.

Every readout states scenario/policy versions, evidence class, numerator/count,
denominator, source, environment, exclusions, and safe causal references. Synthetic,
offline, human, and live-provider classes remain separable. The repository has no approved
human-study sample size, baseline, threshold, or live-provider acceptance, so P4 cannot
claim that colleague experience is proven or improved.

## Five-minute Golden Path gate

The documented path must cover, in order:

1. start the isolated Compose topology;
2. retrieve the bootstrap token once through the local operator boundary;
3. exchange it in Studio to create the first Admin session;
4. create and confirm the initial colleague;
5. assign finite work;
6. restart the stack at the documented checkpoint;
7. inspect recovered identity, Mandate, work, and history;
8. trigger a deterministic Event or Timer wake and inspect its reason/class;
9. inspect the exact proposal in the inbox;
10. approve or reject that exact revision;
11. read the reference ActionResult; and
12. inspect the full causal audit chain.

The operator guide defines prerequisites, reference environment, isolated project and
temporary volume/state, timing start and end, manual and automated steps, restart point,
repeatable command, success criteria, cleanup, and evidence class. A smoke test that does
not measure elapsed wall time establishes flow correctness only. A timing claim is allowed
only when evidence records the actual method, environment, start/end, manual steps, and
result; one environment is not a universal performance promise.

## Docker Compose gate

- Compose provides API, worker, and Studio services plus an operator-only bootstrap
  retrieval command. API, worker, and Studio share the one durable `state.sqlite` volume
  where required.
- Published host ports bind explicitly to `127.0.0.1`. Services listen on container
  network interfaces where service-to-service connectivity requires it; container
  loopback-only binding must not break the topology.
- A clean environment can start, stop normally, and recover after restart without real
  providers, accounts, credentials, or external network effects.
- Loopback is documented only as reduced host exposure, never authentication, encryption,
  sandboxing, production isolation, or production security.
- Compose checks and the Golden Path use a unique project name plus temporary state/volume
  and synthetic data. Cleanup removes containers, networks, and volumes.

## Required mechanical coverage

P4-specific tests, fixtures, scripts, and collectors must cover at least:

- bootstrap entropy, one-time operator retrieval, log absence, digest-only storage,
  expiry, atomic single use, replay refusal, server-assigned `tenant_admin`, role/tenant/
  principal-kind injection refusal, principal separation, server-generated session,
  session-digest persistence, cookie flags, expiry, Origin, CSRF, namespace crossover,
  IDOR, stale revision, and duplicate mutation;
- initial colleague creation, Profile/Mandate separation, P4 working-hours boundary,
  work assignment, fresh-instance and Compose restart recovery;
- Event/Timer trigger classes, wake reason, no-op proposal suppression, and no-op exclusion
  from AI-initiated rate;
- proposal inbox exact revision, approve, reject, stale/expired/replayed approval, digest
  mismatch, Mandate drift, ActionResult, and complete causal audit;
- unauthorized-candidate denominator inclusion and zero-denominator `not_applicable`;
- Studio workflow plus loading, empty, success, rejection, stale, error, and keyboard
  operation; Docker Compose config; isolated Golden Path smoke; public boundary; residue;
  architecture; migration identity; and all P0–P3 regressions.

## Repeatable commands

The focused and aggregate contract is:

```bash
git diff --check
python3 -B -m unittest discover -s tests -v
npm --prefix studio run lint
npm --prefix studio run format:check
npm --prefix studio run typecheck
npm --prefix studio test
npm --prefix studio run build
python3 -B scripts/check_public_boundary.py .
python3 -B scripts/check_p4_repository.py .
python3 -B scripts/check_p4_provenance.py .
python3 -B scripts/check_p4_architecture.py .
PYTHONPATH=src python3 -B scripts/check_p4_migrations.py .
PYTHONPATH=src python3 -B scripts/check_p4_authentication.py .
PYTHONPATH=src python3 -B scripts/check_p4_studio.py .
python3 -B scripts/check_p4_compose.py .
PYTHONPATH=src python3 -B scripts/check_p4_golden_path.py
make check
make evidence-p4
make check
```

`make check` is upgraded to the complete P4 aggregate gate and retains every applicable
P0–P3 regression. `make evidence-p0`, `make evidence-p1`, `make evidence-p2`, and
`make evidence-p3` must not run or rewrite accepted evidence.

## Evidence contract

`artifacts/p4/summary.json` records the base commit, real implementation commit, later
evidence-commit binding, migration and policy versions, required tests and actual results,
metric counts/denominators/`not_applicable` reasons, synthetic/offline evidence class,
public-tree digest excluding only the summary, explicit exclusions, and unevaluated claims.
P4 provenance records new public-document-based implementations and zero transformed source
unless a separately allowed, digest-verified migration is explicitly authorized.

Evidence is generated only after the acceptance and implementation commits exist. The
summary is committed separately, then `make check`, public-boundary, history-integrity, and
residue checks run again. No future SHA is invented.

## Explicit exclusions and claims not permitted

P4 does not implement or claim Semantic Memory, Skill Learning, a governed Skill system,
shared knowledge, multi-person collaboration, Self-initiated autonomy, P5 revisioned policy
building, generalized working-hours enforcement, P6-complete governance hardening, real
models/providers/channels, live-provider pilot readiness, OIDC, SSO, SCIM, PostgreSQL,
distributed execution, high availability, production tenant isolation, production
security/privacy, compliance, or production readiness.

P4 also cannot claim milestone acceptance, merge, measured human improvement, or a proven
five-minute limit unless the independently applicable evidence genuinely supports that
claim.

## Stop condition

Stop on `codex/p4-studio-golden-path` only after the acceptance contract commit,
implementation commit, and separate evidence commit exist; all direct gates and final
`make check` pass; public boundary and residue are clean; migrations 001–003 and all P0–P3
historical artifacts/evidence/receipts/fingerprints are unchanged; and the worktree and
index are clean. Do not merge, push, tag, release, delete the branch, or begin P5.
