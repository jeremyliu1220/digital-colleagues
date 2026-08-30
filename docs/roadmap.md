<!-- SPDX-License-Identifier: Apache-2.0 -->

# P0-P8 Roadmap

Each milestone stops at its gate. A later milestone must not begin automatically.

Current checkpoint: P3 work remains isolated on its milestone branch and awaits independent
acceptance. Accepted P0/P1/P2 artifacts remain unchanged; P4 has not started.

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
reference channel, typed FastAPI mappings, and fresh-instance restart tests. The P3 receipt
records only new implementations and zero transformed source files.

## P4 — Studio and five-minute Golden Path

Build React, TypeScript, and Vite Studio; Docker Compose; bootstrap authentication; the
colleague builder; work assignment; wake-cycle inspection; exact-effect approval; and
causal audit views.

Exit: a clean local environment completes the documented five-minute Golden Path.

## P5 — Revisioned colleague builder

Add draft lifecycle, identity cards, Mandate diffs, explicit defaults, responsibility and
capability editing, revision confirmation, and safe change workflows.

Exit: stale drafts and ambiguous authority changes are rejected and evidenced.

## P6 — Governance hardening

Harden RBAC, session recovery, enrollment, CSRF and replay defenses, approval expiry,
change approval, namespace tests, audit export, and abuse cases.

Exit: the documented local security test suite passes; production security is still not
claimed.

## P7 — Optional adapters

Add explicitly optional provider and channel adapters behind stable ports. Keep vendor
tests separate, prevent live data from entering public fixtures, and require separate live
acceptance.

Exit: reference behavior stays deterministic and optional adapter contracts pass.

## P8 — Release and operational readiness

Add upgrade/backup/restore guidance, migration rollback evidence, diagnostics redaction,
supply-chain inventory, release reproducibility, and public release checks.

Exit: v0.1 may be labeled a local reference release. Enterprise IAM, HA, distributed
operation, production tenancy, compliance, and real-provider pilot claims remain separate.
