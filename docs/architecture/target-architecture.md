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
           revisioned policy/drafts, agenda, wake cycles, proposals,
           approvals, results
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

## P3 actual boundary

P3 keeps P2 `core/` and `governance/` pure and adds `application/` contracts, stable ports,
and services; `adapters/` for SQLite, deterministic intelligence, the reference channel,
clock, IDs, and entropy; a minimal `api/` mapping edge; and a bounded `worker/` facade.
Core runtime values receive additive Mandate binding, typed Event and Timer occurrences,
Agenda generation, wake fencing, and typed ambiguous outcomes. Application imports no
concrete adapter, filesystem implementation, database type, or HTTP type.

The SQLite adapter stores private contract JSON through a construction-replaying codec;
computed proposal and payload digests are rechecked on load. Domain rows, audit, replay,
Event triggers, separate Timer triggers, Agenda runtime, and outbox rows carry explicit
namespace and schema columns.
Application methods group state, audit, replay, approval consumption, attempts, and outbox
updates in `BEGIN IMMEDIATE` transactions with optimistic revisions. This store is a local
semantic reference, not a tenant-isolation or availability claim.

Architecture policy `p3-boundary-specific-determinism-allowlist-v6` parses all boundaries
with boundary-specific import allowlists. Core cannot depend outward; application cannot
import infrastructure; Pydantic/FastAPI cannot leave
`api/`; deterministic boundaries reject hidden wall clock, UUID, randomness, environment,
filesystem, process, network, dynamic import, and dynamic execution capabilities. Import
aliases, assigned callable aliases, and literal `getattr` references are resolved
transitively, so rebinding `datetime.now`, `open`, `sqlite3.connect`, `__import__`, `eval`, or
`exec` cannot bypass the gate. Reflective `__dict__` and `__getattribute__` attribute chains,
reflection-derived subscripts, and `vars`, `globals`, or `locals` entry points are rejected;
unresolved dynamic reflection fails closed. All double-underscore Attributes are rejected by
default, with an exact qualified-name exception only for frozen-dataclass calls to
`object.__setattr__`. Explicit `__builtins__` Name access is forbidden in every AST context,
regardless of subsequent attribute, call, alias, or subscript syntax. Explicit safe literal
`getattr`, ordinary data subscripts, and ordinary `dict.get` remain permitted. Stable ports
reject concrete connection, Path, ORM, edge, and provider types.

## Repository topology

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
injected. TimerOccurrence remains semantically distinct from InputEvent, with stable
timer/occurrence identity and an explicit due time. Restart must preserve enough state to
resume without guessing.

### Effect and approval

The runtime proposes a typed, fully specified effect. HumanApprovalDecision references the
exact immutable proposal revision and a complete canonical proposal digest covering the
namespace, destination, action, payload integrity, safe projection, boundary and attempt
constraints, actor, causality, and time. It is authorized against a durable human
principal. Approval is not a generic permission to let the model fill in missing
parameters. Mandate boundary constraints use typed, exact comparison and unknown or
indeterminate constraints fail closed. Stale, expired, cross-namespace, replayed,
insufficient-role, or partially rebound decisions fail closed.

## P3 application edge

FastAPI is the application edge. Pydantic request and response models translate to and from
core contracts; Pydantic types never enter core. Mutation requests include an idempotency
key and the expected revision where concurrency matters. The server derives namespace,
principal, roles, durable event acceptance time, approval time, and bounded approval validity,
never from caller-supplied authority or temporal fields.

P3 injects a RequestPrincipalContext into the mapping edge; it does not implement or claim
the P4 session, bootstrap, enrollment, Origin, or CSRF boundary. Studio remains a static
shell. UI hiding is never an authorization boundary.

## P3 local persistence topology

v0.1 uses one `state.sqlite` through standard-library `sqlite3` with:

- WAL mode and foreign keys enabled on every connection;
- numbered migrations with immutable checksums; migration 003 adds Timer triggers while 001
  and 002 remain byte-immutable, and version-2 databases upgrade in place;
- transactional repositories and an outbox behind stable ports;
- UTC timestamps, explicit string IDs, schema versions, and complete namespace columns;
- semantically distinct durable Event/Timer triggers, Agenda generation checkpoints, leases
  and fencing;
- immutable safe audit, replay ledger, attempt/result records, and transactional outbox;
- restart checks with all product/store instances reconstructed over the same temporary file.

This is a local reference topology. It provides no claim of PostgreSQL compatibility,
distributed execution, high availability, production tenant isolation, or multi-region
operation. A future store must implement the same ports and earn separate evidence.

## P3 reference adapters

The deterministic provider maps canonical requests to inspectable semantic decisions
without network, environment, hidden time, or randomness. The reference channel accepts a
complete typed effect and returns success, known-not-executed, retryable, permanent, or
ambiguous results without contacting a live provider. Reconciliation distinguishes
confirmed-applied, confirmed-absent, and still-unknown; only confirmed absence can retry.
Pure application policy resolves explicit deterministic no-ops before this provider and
durably records their Decision without producing an effect.

## P4 local deployment topology

Docker Compose runs API, worker, and Studio locally with one durable volume for
`state.sqlite`; an operator profile provides the one-time bootstrap retrieval boundary.
Published API and Studio ports bind to `127.0.0.1`. Inside the topology, API and Studio
listen on `0.0.0.0` so Compose networking works. Loopback publishing reduces host exposure
but is not authentication, encryption, sandboxing, production tenant isolation, or a
production-security control.

P4 adds digest-only bootstrap/session persistence in numbered migration 004. The browser
receives a server-created HttpOnly, SameSite=Strict session cookie and a session-bound CSRF
value; mutations derive `RequestPrincipalContext` from the durable session and validate
Origin, namespace, principal kind, role, replay, and action-specific authority. Studio is
an untrusted presentation edge, not an authorization boundary.

Background processing never retrieves or reuses that HUMAN session. For each pending
durable colleague namespace, the worker reconstructs an exact `ServiceRuntimeContext` from
the namespace-derived MODEL and SERVICE principal IDs plus the current Mandate identity and
revision. The controller re-resolves that binding before every bounded cycle. This context
can process already accepted triggers and dispatch already approved effects; it cannot
create or revise a Mandate or author `HumanApprovalDecision`.

Additive migration 005 stores only namespaced, versioned evaluator observations and safe
pre-proposal governance-candidate evidence. Operational metrics join those observations to
durable work, trigger, proposal, approval, and result records. Eligible scenarios without
evaluator coverage remain `not_evaluated`; they are never converted into observed zeros.
Static Compose validation and the isolated actual start/recreate/recovery/stop Gate are
separate results.

## P5 revisioned builder and policy topology

P5 adds a pure frozen `ColleagueDraft` aggregate over complete proposed Profile, Mandate,
and independent `ColleaguePolicy` values. Profile remains descriptive. Mandate owns mission,
responsibility, capability, constraint, and effect authority. Policy is bound to one exact
Mandate revision and may narrow runtime timing and attention, but cannot grant an effect.
The active identity card remains a projection of confirmed Profile and Mandate only.

Draft create, update, review, cancel, and confirm flow through framework-neutral services
and a P5 persistence port. A canonical digest covers the complete proposed values, base
identities/revisions, typed defaults, and classified diff. Confirmation uses one SQLite
`BEGIN IMMEDIATE` compare-and-swap transaction across all three bases; same-base races leave
one confirmed draft and durable stale evidence for the loser. Migration 006 persists draft
history, confirmations, policy outcomes, budget consumption, run state, and escalation.

The runtime binds policy ID/revision to accepted triggers, wakes, agenda, decisions,
proposals, approvals, and dispatch. It checks the current policy before wake admission,
after deterministic model output and before proposal persistence, and before approval and
dispatch. Durable namespaced counters prevent restart, replay, duplicate-event, or alternate
trigger-class budget evasion. Typed stop state requires an explicit confirmed revision to
resume; escalation is a safe local record, not approval or an external effect.

## P6 accepted local governance topology

The fixed P6 contract adds a centralized typed action matrix, independently revisioned
HUMAN membership, and session bindings to the current role and membership revisions.
Every HTTP, application-service, and store boundary must re-resolve kind, action, complete
namespace, membership, and revisions. MODEL and SERVICE receive no human role; a restricted
SERVICE context continues to operate without a HUMAN session.

Enrollment and recovery use Admin-authorized permits plus a one-shot local operator
delivery boundary. Plaintext credentials are high-entropy, short-lived, single-use, and
never returned by the API or persisted; only purpose-framed digests are stored. Recovery
revokes old sessions and rotates the server-created session and CSRF binding.

Authority-affecting P5 drafts become exact change proposals bound to the draft revision and
digest, all three active base heads, proposer, revisions, namespace, and expiry. A different
current Admin decides, and apply revalidates and consumes that exact authority in one
transaction. One narrow, auditable second-Admin bootstrap transition resolves the initial
two-person deadlock and closes permanently after successful use.

Audit export is a bounded read port with explicit namespace, UTC range, record types,
limit, deterministic ordering, versioned safe records, and redaction. The P6 Gate passed
on the accepted `7e6f4c4dc50b675afb60b6e160fe4f15312dd6c8` baseline; this is still not a
production-security or tenant-isolation claim.

## P7 optional adapter topology

P7 keeps `DeterministicIntelligence` and `ReferenceChannel` as composition defaults and
adds allowlisted `http_json_v1` implementations behind the unchanged intelligence and
channel ports. The adapters are stateless. No migration 008 is added, and existing SQLite
proposal, approval, attempt, ActionResult, reconciliation, replay, policy, RBAC, lease, and
fencing records remain authoritative.

```text
unchanged application ports
        |                         default, network-free
        +-- intelligence -------- DeterministicIntelligence
        |       `-- opt-in ------- HTTP JSON model adapter --> fixed endpoint
        `-- channel ------------- ReferenceChannel
                `-- opt-in ------- HTTP JSON channel adapter -> fixed endpoint
```

Only adapter/composition modules may read startup environment, credential files, URLs, or
perform HTTP/TLS I/O. Exact mode allowlists prohibit dynamic imports. Network modes require
protocol `dc-http-json-v1`, a fixed validated endpoint, a read-only opaque credential file,
bounded connect/read/total timeouts, request/response byte limits, redirect refusal, and TLS
verification. Test-only HTTP is restricted to explicit IP-literal loopback.

The model wire response is an untrusted finite semantic projection. Server code reconstructs
namespace, principals, identifiers, time, Mandate/policy revisions, effect validity,
constraints, and idempotency before the existing policy layer revalidates it. The channel
adapter receives only an exact-approved, dispatch-revalidated `ChannelEffect`. Post-submit
uncertainty becomes `ambiguous`; reconciliation permits retry only for reliable
`confirmed_absent`, and otherwise returns `still_unknown`.

Public adapter evidence is synthetic/offline and uses an isolated loopback stub. It is not
named-provider or live-delivery evidence. Default Compose remains deterministic; an
explicit optional profile/config supplies the adapter selection and temporary read-only
credentials for the isolated P7 runtime Gate.

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
