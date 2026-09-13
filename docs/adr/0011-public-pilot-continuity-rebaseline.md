<!-- SPDX-License-Identifier: Apache-2.0 -->

# ADR 0011: P12 v4 Historical Platform Classification Rebaseline

- Status: Accepted for P12 v4 governance implementation
- Decision date: 2026-09-11
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

This decision prospectively supersedes only the unimplemented P9 roadmap assignments and
the affected forward-looking portions of ADRs 0003 and 0008. ADRs 0007 and 0010 remain
valid. No ADR's historical meaning, accepted result, or executable object is rewritten.

P12 v1 and v2 are rejected and remain immutable non-ancestors of v4. V1 used
branch `codex/p12-public-pilot-continuity-rebaseline`, head
`8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3`, tree
`557a74e9174247483362bbbd15cd265113775d12`, and acceptance blob
`26562d795980ec8d6d9ea36ff3fcc718b41c09e8`; it was rejected for core-contract and
ownership drift before any remote branch, pull request, evidence, merge, or publication.

V2 used branch `codex/p12-public-pilot-continuity-rebaseline-v2`. Its acceptance commit is
`3639fa08ca44820bb922e0644095c9fb9c24d3e6`, acceptance tree is
`71c411660e0f7ff26e8ad1451acaa0ea26fa384b`, acceptance blob is
`50453e154cf642bc7b90644660e1d956b04f966a`, and acceptance file SHA-256 is
`be3ad1967a98c67ae34ad7c22c35a9ec1f637a780c930ae4e8349f126e64800b`. Its final head is
`8e08c3891dc8f761ada096c3f829ef31d3fbfd7c` with tree
`01ee7b08cc870a626698ac9a3fc46ec92bf0f4e0`. The exact v2 chain remains:

| Commit | Sole parent | Tree | Purpose |
| --- | --- | --- | --- |
| `3639fa08ca44820bb922e0644095c9fb9c24d3e6` | `c1562ea5201394d8a278f4b644daf4029cbb5bd4` | `71c411660e0f7ff26e8ad1451acaa0ea26fa384b` | acceptance-only v2 contract |
| `eb4dbc7e1cd1c1a1671f58441bb3e49d08e77a5e` | `3639fa08ca44820bb922e0644095c9fb9c24d3e6` | `42c05dea50cfe45b92a055c835e63045ec88a082` | living-document alignment |
| `5d0818ab9671dc023afd5ad23b6b0995e79ef68a` | `eb4dbc7e1cd1c1a1671f58441bb3e49d08e77a5e` | `99e0fd7a60df0584661d8e9162bf9dde1d0abf22` | governance gates and tests |
| `b255d79df2b435ba754b7afe450d0a45559ea72a` | `5d0818ab9671dc023afd5ad23b6b0995e79ef68a` | `d4517e99bb155353704726d8a11e22e935dfe7dc` | provenance integration |
| `fc145550b750c172899bc1497ff5fede387c07dc` | `b255d79df2b435ba754b7afe450d0a45559ea72a` | `0d4ec3cba2040d640e3adb8880c98a4525fa2207` | public-boundary fixture correction |
| `098ba1399f7146258027674d5d312966fbdfe037` | `fc145550b750c172899bc1497ff5fede387c07dc` | `f0f65517dea5b3292c6f3f87c8c10b90295487e8` | replay diagnostic propagation correction |
| `5722067571b70911c38b50ead23d198dcfbd4f20` | `098ba1399f7146258027674d5d312966fbdfe037` | `f66d1a7fada6db1a883c830f91ac6222983fa6c8` | installed-tool provisioning correction |
| `8e08c3891dc8f761ada096c3f829ef31d3fbfd7c` | `5722067571b70911c38b50ead23d198dcfbd4f20` | `01ee7b08cc870a626698ac9a3fc46ec92bf0f4e0` | import-order correction and final rejected v2 head |

Pull request `jeremyliu1220/digital-colleagues#14` remains exactly `CLOSED` without merge.
Its base is `main` at
`c1562ea5201394d8a278f4b644daf4029cbb5bd4`; its head is
`codex/p12-public-pilot-continuity-rebaseline-v2` at
`8e08c3891dc8f761ada096c3f829ef31d3fbfd7c`; and `mergedAt`, `mergeCommit`, and
`autoMergeRequest` are all null.

The retained failed-run record is exact. Run `34542709145` is a `pull_request` / `CI` run at
head `fc145550b750c172899bc1497ff5fede387c07dc`; it has exactly attempt 1, which is
`completed` / `failure`. Run `34564478590` is a `pull_request` / `CI` run at the final v2
head; it has exactly attempts 1 and 2, both `completed` / `failure`. Attempt 1 was created
at `2026-09-11T05:03:14Z` and completed at `2026-09-11T05:06:34Z`; attempt 2 was created
at `2026-09-11T05:12:52Z` and completed at `2026-09-11T05:16:00Z`. Draft-time Actions
retention is 90 days, the maximum allowed is 90 days, and the conservative earliest normal
expiry boundary is `2026-12-10T05:03:14Z`.

Both final-head attempts reached the accepted P8 actual Compose boundary and failed safely
at `pre_start_restore`. V2's exact rejection classification is
`rejected_linux_historical_replay_contract_infeasible`. No v2 summary, evidence, merge,
tag, Release, or publication exists, and no failed attempt is reclassified.

V3 is not relabeled as rejected. It is a superseded immutable acceptance-only attempt on
branch `codex/p12-public-pilot-continuity-rebaseline-v3`, at commit
`e31bc733cbdd333648f2ce1c52ac9fe1fad83179`, tree
`1cdce2a41f84ee4243d04be781ad187eb5f5fab9`, and acceptance blob
`40c93a2aa8930c71e14fefac2053a10ed137af58`, with the accepted P11R base as sole parent.
Its acceptance file is 3488 lines and 232313 bytes with SHA-256
`6afddd55f4f8458c94dcd56b781e47fef66a06d954d4246aa3855b4daf2e0e3c`.
V3 created no implementation, correction, summary, remote branch, pull request, tag,
Release, or publication. Its one-exclusion model omitted the transitive P8 Golden Path and
three Darwin-dependent P10 gates, so it is preserved as a non-ancestor rather than amended.

P12 v4 starts directly from the same accepted base on
`codex/p12-public-pilot-continuity-rebaseline-v4`. Its immutable acceptance commit is
`dbdb75b6afcd226059484ec536fec82532eb3613`, tree
`f8d0dad5c04253eefd24353f8c9afd965cf0d6ea`, and acceptance blob
`b574bb350a83a36f9ad7f521514c7d58e97393d9`.

The v2 failure exposed a platform contract gap. Accepted P8 actual Compose evidence was
created on Darwin Docker Desktop. A GitHub Ubuntu host uses UID 1001 for the 0700 operator
directory and 0600 private files, while the immutable accepted container uses non-root
UID/GID 10001:10001. Native Linux therefore cannot traverse that bind. This is not a P12
governance failure and does not authorize a change to P8.

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

### Platform-scoped historical evidence

P12 v4 has three independent status dimensions:

- `p12_governance_result` may become `passed` on its own exact governance criteria;
- each of the five `ubuntu_historical_execution_status` values remains `not_proven`; and
- `linux_public_pilot_readiness` remains `blocked`.

The 129 accepted gate identities are independently derived as 124 included and five
excluded. GitHub-hosted `ubuntu-24.04` v4 CI uses five isolated exact-object checkouts and
a literal 151-item portable inventory: 5 setup items, 124 included acceptance gates, 17
evidence anchors, and 5 excluded acceptance gates. The exact ordered exclusions are:

1. `p8_compose_runtime`
2. `p8_golden_path`
3. `p10_compose_runtime`
4. `p10_quickstart`
5. `p10_remote_distribution`

Each excluded result is `not_run_platform_excluded` with null exit status and embeds its
own immutable Darwin anchor with `anchor_platform = darwin`, `anchor_historical_status = passed`,
and `purpose = immutable_platform_scoped_identity_only`. Those five anchors are independent
validation data inside the excluded rows, not additional inventory items. Each embedded-anchor
metadata `canonicalization` field remains the contract-required literal `P12-CJ-1`. The five
float-bearing selected composites use the exact Appendix C legacy anchor canonicalization:
UTF-8, sorted keys, separators `(",", ":")`, `ensure_ascii=false`, `allow_nan=false`, and no
terminal newline. That byte algorithm is distinct from the integer-only general P12-CJ-1
encoder. Bytes and Anchor SHA-256 bind those exact canonical bytes:

| Gate | Source commit | Source tree | Summary path / blob / file SHA-256 | Exact selection | Bytes | Anchor SHA-256 |
| --- | --- | --- | --- | --- | ---: | --- |
| `p8_compose_runtime` | `0bb80ab187932fbad42fbf665b8310987609a1f5` | `311eb777c3d17a9a3722a16c394b9913c283b416` | `artifacts/p8/summary.json` / `964406b20e9fc1e98b8eeda3c24bf3f22f226768` / `78905893f9a06bf6b5361c76a8e152dbe8de2ec53d1aede84fca2f7ce1b5921b` | `result = p8_summary["compose_runtime"]` | 2348 | `a2acd8e3f935d9c520f58e76b8384514e596e59f94f7bb62e1881ce9183c9bbd` |
| `p8_golden_path` | `0bb80ab187932fbad42fbf665b8310987609a1f5` | `311eb777c3d17a9a3722a16c394b9913c283b416` | `artifacts/p8/summary.json` / `964406b20e9fc1e98b8eeda3c24bf3f22f226768` / `78905893f9a06bf6b5361c76a8e152dbe8de2ec53d1aede84fca2f7ce1b5921b` | `result = p8_summary["golden_path"]` | 2034 | `c1f1f8148cd3b0184d92720e862bbadfe7e330fd4087b7eb03190400d6742f44` |
| `p10_compose_runtime` | `4bef5629d450c6bb3940f606fc90194e008ee8fd` | `909b566b7ba9f7beb143cd0b29cf95fbd1178bbe` | `artifacts/p10/summary.json` / `a4c1a59fffec9c30160787a7bec584e228fb9f35` / `876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae` | `result = p10_summary["compose_runtime"]` | 476 | `4f6f5de0a92d2aa3bea1ab80ad94b869a4fd1cbe5f459804eea3cd86377e137b` |
| `p10_quickstart` | `4bef5629d450c6bb3940f606fc90194e008ee8fd` | `909b566b7ba9f7beb143cd0b29cf95fbd1178bbe` | `artifacts/p10/summary.json` / `a4c1a59fffec9c30160787a7bec584e228fb9f35` / `876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae` | `result = p10_summary["quickstart"]` | 874 | `75c18fadb57dd93914a8f99996857af22c2da8c82c504582b9eaa412c1f00c1b` |
| `p10_remote_distribution` | `4bef5629d450c6bb3940f606fc90194e008ee8fd` | `909b566b7ba9f7beb143cd0b29cf95fbd1178bbe` | `artifacts/p10/summary.json` / `a4c1a59fffec9c30160787a7bec584e228fb9f35` / `876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae` | `result = {"distribution": p10_summary["remote_distribution"], "quickstart": p10_summary["remote_quickstart"]}` | 2538 | `4383d540c4cd95f62db32aaadc1dfdf8e027eb0bd81b9909c4a0dda9a3d06c78` |

The five proofs remain distinct. P8 Compose requires its selected gate/status and
`environment.host = darwin`; P8 Golden Path requires its own gate/status plus the exact
direct Compose call and the same summary's Compose host. P10 Compose binds verified-gate
membership, aggregate pass, the Darwin guard, and arm64 architecture. P10 Quickstart also
binds `actual_macos = true` and `platform_class = macos/arm64`. P10 Remote Distribution
binds its outer gate, remote assertions, and the remote quickstart's exact macOS fields;
its anchor contains only the `distribution` and `quickstart` result keys.

The P8 environment records `darwin`, Docker server `29.7.2`, and Compose `5.4.0`; none of
these anchors is relabeled as native-Linux or cross-platform evidence.

Gate entrypoints are exactly 19 null and 110 non-null, while the complete inventory has
41 null entrypoints. Portable replay reports exactly 616 historical Python tests; the
current governance inventory has exactly 136 unique P12 test IDs. Setup, evidence anchors,
and platform exclusions never masquerade as passed Ubuntu gate executions. No recursive
P11R, P11, P10, P9, or accepted P8 all-scope aggregate may reintroduce an excluded leaf.

P20-L0, Linux Private-State Backup/Restore Portability, is the first and only blocking P20 portability
implementation sub-gate. It owns the forward fix and must pass before any P20 private-live
E2E, soak, release candidate, supported-Linux-host claim, or publication preparation.
It must preserve non-root containers and private 0700/0600 modes and prove a
least-privilege handoff with distinct host/container UIDs on an ephemeral standard Linux
environment. P12 only records and propagates this risk; P13-P19 carry the five Ubuntu
statuses and blocked Linux readiness without treating their own mechanism gates as failed.

### Product decisions

The product is a local-first Public Pilot rather than production-ready 1.0. P20 retains
the two-Microsoft-tenant, ten-account, ten-deployment, two-App-mode, HUMAN evaluation, and
72-hour soak boundary. Named-provider and private-live results remain `not_evaluated`
until the owning gate has actual authorized access.

Semantic memory uses tiered admission. Model output, connector material, and external
messages create candidates only. Personal, confidential, externally asserted, or
model-derived memory requires authorized HUMAN admission. A default-off deterministic
SERVICE rule may auto-admit only a non-sensitive derived fact from an already
HUMAN-accepted source, without semantic expansion or conflict, under an exact Policy
revision. `MemoryAdmissionDecision` has only `admit` and `reject`. Correction,
supersession, revocation, deletion, and expiry are post-admission lifecycle.
`MemoryLifecycleDecision` is only a P12 working label; P16 fixes the exact type name and
schema. No memory decision is a `HumanApprovalDecision` or authority source.

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

P12 v4 follows one exact 21-stage authorization lifecycle. Every stage requires a separate
project-owner decision and completing one never authorizes the next. It has an immutable
acceptance-only first commit, one or more linear single-parent
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

P12 v4 uses exactly two required pull-request jobs on `ubuntu-24.04`:
`Current P12 governance non-publishing verification` and `Portable historical replay`.
Each emits exactly one canonical
P12-CJ-1 result envelope for the exact checked-out head. CI has only `contents: read`, no
secret, OIDC, write permission, artifact transport, signature, attestation, or publication
path. Evidence preflight is a separate read-only, one-use-receipt boundary.

## Consequences

- Continuation, memory, trigger/recovery, and proactivity each receive an independent gate.
- Transport mechanics precede and remain separate from automatic-effect authority.
- Recovery and memory remain explicit, bounded, revisioned, and non-authoritative.
- P12 can prove planning coherence and future enforcement without introducing behavior.
- P20 remains the sole gate that may establish a Public Pilot claim, and publication still
  requires separate authorization.
- All five accepted Darwin anchors remain intact while the missing Ubuntu/Linux proofs are
  explicit and assigned once to P20-L0.
- Rejected v1/v2 and superseded v3 objects remain auditable and cannot become v4 ancestry
  or evidence.

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
- Treating the P8 Darwin result as Linux evidence, waiving the v2 failure, retrying until
  pass, broadening private permissions, using root, or hiding the leaf behind a recursive
  aggregate: each would launder a missing platform proof.
- Running public pull-request code on a persistent or general self-hosted runner: it adds
  credential, persistence, lateral-movement, and cache-poisoning risk without proving the
  standard Linux portability boundary.

## Claim boundary

P12 establishes only the accepted B+ governance representation, deterministic checkers,
synthetic negative tests, the exact portable historical inventory, provenance, and
current-CI transition. It may establish P12 governance while all five Ubuntu historical
evaluations remain `not_proven` and Linux Public Pilot readiness remains `blocked`. All future records,
transports, model/provider calls, migrations 009-014, runtime behavior, private-live
evidence, HUMAN evaluation, soak, release, and Public Pilot readiness remain unimplemented
and `not_evaluated` until their owning gates pass.
