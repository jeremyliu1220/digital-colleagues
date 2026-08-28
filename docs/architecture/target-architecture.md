<!-- SPDX-License-Identifier: Apache-2.0 -->

# Target Architecture

## Architectural objective

The reference stack makes the primitives that turn a task agent into a persistent digital
colleague explicit. Frameworks and vendors remain replaceable at ports; identity,
authority, work, approvals, and causality remain stable domain concepts.

```text
React Studio
     |
FastAPI HTTP mappings (Pydantic at this edge only)
     |
Application services and governance policies
     |
Pure core: namespace, principals, Profile, Mandate, work, events,
           agenda, wake cycles, effect proposals, approvals, results
     |
Stable ports
     +-- SQLite repositories and outbox
     +-- deterministic intelligence provider
     +-- reference channel
     +-- clock, randomness, and identifier sources
```

The core is implemented with frozen standard-library dataclasses, Enums, and Protocols.
It does not import FastAPI, Pydantic, provider or channel SDKs, database implementations,
ORMs, or orchestration frameworks. Adapters translate their values into stable contracts.

## P2 actual boundary

P2 implements `core/` and `governance/` only. Namespace uses explicit tenant scope plus an
explicit colleague or principal scope. Principal kinds are disjoint durable values. The
core contains frozen, slotted standard-library dataclasses, Enums, immutable nested JSON
values, UTC validation, deterministic public serialization, lifecycle contracts, and
causal records. Governance contains pure functions that authorize an exact effect against
one Mandate revision and bind one durable human decision to one immutable proposal digest.

Architecture checks parse every core and governance module and reject framework, database,
provider, application, adapter, API, worker, wall-clock, environment, randomness, process,
and network dependencies. No P3 product directory exists.

## Future repository topology

P1 and later may introduce this layout; P0 does not create it:

```text
src/digital_colleagues/
  core/
  governance/
  application/
  adapters/
  api/
  worker/
studio/
migrations/
examples/
docs/
tests/
scripts/
artifacts/
.github/
```

## Authoritative concepts

### Namespace

Every persisted public record carries a complete namespace, including tenant scope and the
relevant colleague or principal scope. A single database file is never used as an implied
tenant boundary. All repository access receives namespace through a port contract.

### Principal

Human, model, and service principals are different durable kinds. A principal identifier
and role assignment are server-controlled. Human role IDs are `tenant_admin`,
`colleague_user`, and `auditor`. Model and service principals cannot change kind or author
a human approval decision.

### Profile and Mandate

Profile is descriptive presentation data. Mandate is revisioned authority: mission,
service relationship, responsibilities, capabilities, constraints, working context, and
effect boundaries. An identity card is a projection; it is not an authority source.

### Work and runtime

Finite work, dependencies, obligations, events, agenda items, wake cycles, proposals, and
outcomes use stable IDs and explicit lifecycle states. Time, randomness, IDs, and I/O are
injected. Restart must preserve enough state to resume without guessing.

### Effect and approval

The runtime proposes a typed, fully specified effect. HumanApprovalDecision references the
exact immutable proposal revision and a complete canonical proposal digest covering the
namespace, destination, action, payload integrity, safe projection, boundary and attempt
constraints, actor, causality, and time. It is authorized against a durable human
principal. Approval is not a generic permission to let the model fill in missing
parameters. Mandate boundary constraints use typed, exact comparison and unknown or
indeterminate constraints fail closed. Stale, expired, cross-namespace, replayed,
insufficient-role, or partially rebound decisions fail closed.

## Future application edge (P3 and later)

FastAPI is the application edge. Pydantic request and response models translate to and from
core contracts; Pydantic types never enter core. Mutation requests include an idempotency
key and the expected revision where concurrency matters. The server derives namespace,
principal, and roles from its session, never from caller-supplied authority fields.

Studio uses React, TypeScript, and Vite. It displays server-derived authorization and
revision data. UI hiding is not an authorization boundary.

## Future local persistence topology (P3)

v0.1 uses one `state.sqlite` through standard-library `sqlite3` with:

- WAL mode and foreign keys enabled on every connection;
- numbered migrations with immutable checksums;
- transactional repositories and an outbox behind stable ports;
- UTC timestamps, explicit string IDs, schema versions, and complete namespace columns;
- migration, backup, restore, and restart checks before release.

This is a local reference topology. It provides no claim of PostgreSQL compatibility,
distributed execution, high availability, production tenant isolation, or multi-region
operation. A future store must implement the same ports and earn separate evidence.

## Future reference adapters (P3)

The deterministic provider maps fixed inputs to inspectable reasoning outputs without
network access. The reference channel accepts typed effects and returns typed ActionResult
records without contacting a live provider. They define the required release path; vendor
adapters are optional and later.

## Future deployment topology (P4)

Docker Compose will eventually run API, worker, and Studio locally with a durable volume
for `state.sqlite`. API and Studio bind to `127.0.0.1` by default. Loopback binding reduces
exposure but is not authentication, encryption, sandboxing, or enterprise isolation.

## Causal audit chain

The minimum inspectable chain is:

```text
InputEvent -> WakeCycle -> AgendaItem -> Decision -> EffectProposal
           -> HumanApprovalDecision -> EffectAttempt -> ActionResult
```

Records include namespace, stable identifiers, relevant revisions, timestamps from an
injected clock, actor principal, correlation and causation identifiers, and schema version.
Sensitive payloads are represented by safe projections or digests, not copied blindly into
diagnostics.
