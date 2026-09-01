<!-- SPDX-License-Identifier: Apache-2.0 -->

# P0-P8 Roadmap

Each milestone stops at its gate. A later milestone must not begin automatically.

Current checkpoint:

- P4 has been accepted and fast-forward merged into `main`.
- The P4 post-merge Gate hotfix has been merged.
- The accepted `main` baseline is
  `259e5627c0a4d713934263efe18caf8c675a1669`.
- Historical P0–P4 acceptance, artifacts, evidence, receipts, and migrations remain
  unchanged.
- P5 starts from that baseline and has not been accepted or merged.

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

## P7 — Optional adapters

Add explicitly optional model, provider, and channel adapters behind stable ports. Keep
vendor tests separate, prevent live data from entering public fixtures, and require separate
live acceptance. The reference path remains deterministic. Semantic Memory is not required
for P7.

Exit: reference behavior stays deterministic and optional adapter contracts pass.

## P8 — Release and operational readiness

Add upgrade/backup/restore guidance, migration rollback evidence, diagnostics redaction,
supply-chain inventory, release reproducibility, and public release checks.

Converge only the implemented v0.1 scope; do not add Semantic Memory, Skill Learning, or a
multi-person collaboration platform to the release milestone.

Exit: v0.1 may be labeled a local reference release. Enterprise IAM, HA, distributed
operation, production tenancy, compliance, real-provider pilot claims, Semantic Memory,
Skill Learning, shared knowledge, multi-person collaboration, and Self-initiated autonomy
remain separate.

## Post-v0.1 outlook

The non-committing [Post-v0.1 Capability Outlook](product/post-v0.1-capability-outlook.md)
orders separately gated exploration as S1 memory-loop closure, S2 memory autonomy and
bounded goal-driven proactivity, S3 knowledge decentralization and multi-person
collaboration, and S4 a governed Skill system. Self-initiated autonomy may be considered
only after those stages; none of these capabilities is required for the v0.1 P4–P8 gates.
