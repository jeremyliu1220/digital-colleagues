<!-- SPDX-License-Identifier: Apache-2.0 -->

# P3 Headless Deterministic Slice Acceptance Contract

## Scope

P3 implements the local, framework-neutral application layer, stable ports, checksummed
SQLite reference persistence, bounded wake and outbox services, deterministic intelligence,
a synthetic reference channel, and typed FastAPI mappings needed to execute the causal
chain from InputEvent through ActionResult without Studio, a real model, or a network
provider. P2 contracts and accepted P0/P1/P2 evidence remain historical and unchanged.

## Required artifacts

- Application contracts, ports, services, and a bounded headless worker under `src/`.
- Standard-library `sqlite3` persistence and canonical storage codec behind stable ports.
- Immutable `migrations/001_initial.sql` and `002_runtime_indexes.sql`, additive
  `003_timer_triggers.sql`, and their checksum manifest.
- Deterministic time, ID, intelligence, and reference-channel adapters.
- FastAPI/Pydantic request and response mappings with injected server request context.
- Synthetic persistence, runtime, API, adversarial architecture, and restart tests.
- Complete P3 provenance receipt; matching path-free parent fingerprints; P3 summary.
- Fail-closed repository, provenance, architecture, migration, persistence, runtime-contract,
  Golden Path, evidence, and aggregate toolchain scripts.

## Architecture rules

Core remains frozen standard-library values and cannot import application, governance,
FastAPI, Pydantic, SQLite, adapters, workers, providers, or hidden capabilities. Application
and stable ports may depend only on core, governance, and application contracts; they cannot
import concrete adapters or HTTP types. Pydantic and FastAPI are confined to `api/`. Stable
ports expose no ORM, provider, framework, filesystem-path, or database types. Each boundary
has its own standard-library allowlist; SQLite and filesystem I/O are confined to the
SQLite adapter. Policy `p3-boundary-specific-determinism-allowlist-v3` resolves import,
from-import, assigned-callable, attribute-chain, recursive rebinding, and statically safe
literal `getattr` aliases before capability checks. Dynamic import and execution through
`__import__`, `compile`, `eval`, `exec`, `input`, or `open` are forbidden directly and
through aliases. Literal `getattr` references to forbidden capabilities are rejected, and
unresolved dynamic `getattr` access fails closed. Architecture fixtures must make unknown
imports, reverse dependencies, edge-type leakage, wall-clock calls, UUID, randomness,
environment, filesystem, process, network, and dynamic capability access fail with nonzero
status while explicit deterministic code continues to pass.

## Persistence invariants

The injectable database path names one local `state.sqlite`; it is never an implied tenant
boundary. Every repository call receives an exact Namespace. Every P3 persisted table has
schema version plus tenant, scope, and scope-ID columns. Every connection enables WAL,
foreign keys, a bounded busy timeout, and numbered migrations. Migration filenames,
versions, content digests, and applied checksums are immutable; altered or future schema
metadata fails closed. Transactions combine domain records, optimistic revisions, immutable
audits, replay ledgers, approval consumption, attempts, and outbox changes. Tests use only
OS temporary databases. Runtime databases, WAL/SHM files, logs, caches, and build output are
forbidden from the public tree.

Migration 003 adds a typed, namespaced `timer_triggers` table without modifying migrations
001 or 002. A version-2 database upgrades in place while retaining durable records. Timer
occurrences have stable timer/occurrence IDs, injected UTC schedule time, explicit UTC due
time, replay identity, lease/fencing state, and a foreign key to the durable typed record.

## Authorization and replay invariants

Namespace, principal, kind, roles, accepted-event time, and approval decision time come from
durable server-side context, never request bodies. Approval validity is server policy capped
by proposal validity. Future-dated, expired, before-proposal, non-UTC, or overlong approval
authority fails closed. MODEL and SERVICE principals cannot become HUMAN or write
HumanApprovalDecision.
Approval and dispatch revalidate the current Mandate revision, exact Namespace, durable
human principal and canonical role, expiry, proposal revision, complete proposal and payload
digests, boundary and typed constraints, effect idempotency key, attempt ceiling, and replay
state. The claim, outbox row, proposal, approval, attempt, Mandate, principal, attempt limit,
correlation, and causation bindings must all agree exactly. Drift, tampering, stale revisions,
partial binding, unknown constraints, cross-scope
access, and wrong principals fail before the reference channel call. Event, approval,
effect, and proposal-revision replay identities are durable and transactional.

Distinct Event and Timer triggers and Agenda claims carry durable leases and monotonically
increasing fencing tokens. A Timer cannot be claimed before its due time; replay cannot add
a duplicate occurrence, trigger, or Agenda generation.
Agenda coalescing retains every cause and uses generation/handled-generation checkpoints, so
a new cause arriving during a claim stays pending after the old decision commits. Attention
ordering is deterministic; a persisted starvation counter advances lower-priority work.
Wake work is bounded by item and decision counts. No pending Agenda means no intelligence
call. An explicit deterministic no-op is recognized by pure application policy before the
intelligence port, commits a durable typed Decision, completes the Agenda generation, and
creates no proposal, approval, attempt, outbox, or channel call. Other decisions are typed,
side-effect free, stable-request-id outputs and never dispatch an effect directly.

The outbox claims durably, creates explicit attempt/result records, and has a bounded attempt
limit. Successful, known-not-executed, retryable, permanent, and ambiguous results are typed.
An uncertain call becomes AMBIGUOUS and is never blindly dispatched. Reconciliation may
confirm applied, confirm absent, or remain unknown; only confirmed absence creates a bounded
retry with a new EffectAttempt. Crash fixtures cover transaction rollback, claimed-lease
takeover, pre-channel dispatch recovery, post-channel ambiguity, and post-finalize replay
suppression with fresh store instances.

## Restart Golden Path

The required synthetic test creates durable principals, Profile, Mandate, and finite work;
submits InputEvent; claims a trigger; materializes AgendaItem; obtains deterministic Decision
and EffectProposal; records exact HUMAN approval; atomically creates EffectAttempt and outbox;
records the reference ActionResult; and reads the safe causal audit chain. It then closes all
store/service instances, creates fresh instances over the same temporary database, verifies
every durable identity and record, replays the event, approval, effect key, and dispatch,
and proves no duplicate state or channel call. Canonical observable history bytes must match
before and after restart.

## Repeatable commands

```bash
git diff --check
python3 -B -m unittest discover -s tests -v
python3 -B scripts/check_public_boundary.py .
python3 -B scripts/check_p3_repository.py .
python3 -B scripts/check_p3_provenance.py .
python3 -B scripts/check_p3_architecture.py .
PYTHONPATH=src python3 -B scripts/check_p3_migrations.py .
PYTHONPATH=src python3 -B scripts/check_p3_persistence.py
PYTHONPATH=src python3 -B scripts/check_p3_runtime_contracts.py .
PYTHONPATH=src python3 -B scripts/check_p3_golden_path.py
make check
make evidence-p3
make check
```

`make check` is the current P3 gate. P1 and P2 stage-absence assertions remain historical
fixtures and are not applied to the P3 tree. `make evidence-p1` and `make evidence-p2` must
not be executed or used to rewrite accepted artifacts.

## Evidence claim classes

Mechanical evidence may claim only repository hygiene, P3 provenance coverage, dependency
direction, deterministic-capability exclusion, migration identity and SQLite pragmas,
namespaced local persistence semantics, transaction rollback, optimistic revision checks,
exact-effect and complete outbox binding, server-controlled approval time, replay suppression,
Event/Timer trigger and Agenda/outbox lease and fencing semantics, application-layer no-op,
ambiguity reconciliation, boundary-specific alias rejection, typed HTTP mapping, complete
zero-exception unittest
counts, adjacent P3 parent-fingerprint equality, restart recovery, and byte-equivalent
synthetic output. The collector records required test IDs and fault boundaries, P2 base and
merge-base, the implementation commit tested, the later evidence commit target, migration
and policy versions, receipt digest, and a public-tree digest that excludes only the P3
summary itself.

Human review, historical parent state outside the adjacent P3 pair, production security or
privacy effectiveness, real-provider delivery, publication, distributed execution,
PostgreSQL compatibility, HA, enterprise IAM, production tenancy, compliance, and production
readiness remain `not_evaluated` or explicit exclusions.

## Explicit exclusions

P3 does not implement P4 browser bootstrap or enrollment, sessions, CSRF/Origin controls,
Studio workflows, Docker Compose, live providers, real accounts or messages, semantic
memory, skill learning, enterprise world models, PostgreSQL, distributed scheduling, HA,
backup/restore release evidence, or production security and compliance claims. The FastAPI
edge accepts an injected server-derived RequestPrincipalContext; it does not pretend that
P4 authentication exists.

## Stop condition

P3 stops only after all direct gates, full unittest, `make check`, a clean implementation
commit, matching after fingerprint, `make evidence-p3`, the evidence commit, a second
`make check`, public-boundary scan, evidence/public-tree digest verification, and clean Git
status succeed. Stop on the P3 branch. Do not merge, push, tag, release, open a PR, or start
P4.
