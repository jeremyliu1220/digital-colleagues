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

## P8 release and operations topology

P8 adds an operator edge without changing core, governance, application ports, SQLite
schema, or adapter authority. The candidate is version `0.1.0` and consists of a normalized
source archive, Python wheel, built Studio archive with bundled dependency license texts,
deterministic supply-chain inventory, release manifest, and checksums. OCI images are
actual operational test output, not release artifacts or byte-reproducibility claims.

```text
clean accepted source commit
    +-- normalized source archive --> default deterministic Compose
    +-- Python wheel
    +-- built Studio + dependency license texts
    `-- inventory + release manifest + checksums

live WAL state -- SQLite online backup API --> private versioned backup
verified private backup -- stopped writers + atomic replacement --> restored state
state metadata -- strict allowlist + irreversible causal digests --> private diagnostics
```

Backup and restore validate the existing migration manifest and applied migration records;
P8 adds no migration 008. Replacement requires an explicit offline assertion and first
creates a verified rollback backup. Restore changes bytes, not authority rules: after
returning sessions, membership, approvals, authority, and audit to the backup instant, the
operator must rotate/revalidate them through existing P6 controls.

The first release has an explicit accepted-P7 transition boundary. P7 version `0.0.0`
predates release manifests, so a P8-authored source descriptor binds its immutable commit,
tree, timestamp, schema, and migration digest while recording the absent manifest. Actual
runtime evidence creates state with exact P7 code before P8 starts, backs it up, boots P8,
and restores it for verification with exact P7 code. The replaced P8 state receives its own
P8-bound rollback backup; source identities are never silently conflated.

The release builder uses two OS temporary workspaces and normalizes time, ordering,
ownership, modes, locale, timezone, gzip, tar, and wheel inputs. Runtime/build Python
packages are exact and hash-checked, npm packages use exact integrity records, Docker base
images use manifest digests, and CI Actions use commit IDs. This is local release-candidate
evidence, not production software-supply-chain assurance or a publication.

## P9 v0.2 Public Pilot planning boundary

P9 changes no runtime, Studio, Compose, adapter, operation, API, worker, schema, migration,
dependency, or version. It defines the planned P10-P15 architecture while the executable
baseline remains the unpublished `0.1.0` local reference candidate. The v0.2 plan is a
Public Pilot, not production-ready 1.0, HA, enterprise IAM, production tenancy, compliance,
production security, or production readiness.

The planned product composition extends the existing pure-core/application/ports direction:

```text
Admin Studio / future stable /api/v1 mappings
       |
Package and deployment application services ----> package provenance/trust ports
       |                                           `-- inert declarative artifacts
Existing governance and runtime services --------> model and connector ports
       |                                           +-- OpenAI semantic gateway
Pure core contracts                               `-- Microsoft 365 connectors
       |
Existing and future stores behind ports
```

AgentPackage is a non-executable, versioned, digest-bound declaration containing
schema-valid metadata, localized display text/prompts, bounded workflow declarations, and
requested capabilities. ColleagueDeployment is a separately namespaced instance created
from one exact package version/digest with its own Profile, Mandate, Policy, lifecycle,
connections, grants, work, budgets, effects, and audit. Package material is untrusted and
can request but never grant or activate authority. It is not an S4 Skill.

ExternalConnection authenticates one managed provider/application/account relationship but
grants no resource or action. ConnectorGrant is Admin-created, revisioned, and exact to a
resource/action within the current Mandate and Policy. SourceReference and SourceCursor
retain a safe locator/version/digest/cursor rather than full external bodies or Semantic
Memory. Multiple deployments remain isolated; they do not imply S3 shared knowledge,
delegation, messaging, collaboration, or shared memory.

AutomaticEffectAuthorization is a new planned durable non-human authorization path for an
effect proven to satisfy the exact low-risk policy, Mandate, Policy, ConnectorGrant,
source/data version, connection state, and budget. It is separate in schema, authoring,
consumption, and audit from HumanApprovalDecision. MODEL and SERVICE never author a human
decision.

### Planned package data flow

```text
Package source
-> bounded download/local selection
-> digest
-> provenance/attestation verification
-> archive/content safety validation
-> requested-capability inspection
-> Admin trust decision
-> inert installed package
-> reviewed deployment draft
-> exact Mandate/Policy/ConnectorGrant binding
-> confirmed ColleagueDeployment
```

Package sources are official built-in, local development, or GitHub Release artifacts with
valid GitHub artifact attestation. Attestation binds digest to source/build identity but is
not a safety result. Updates create new drafts; rollback selects an accepted still-trusted
exact version. Unknown schema/capability, executable content, digest mismatch, stale/revoked
trust, or ambiguous permission fails closed.

### Planned external-event data flow

```text
External event
-> ExternalConnection authentication
-> ConnectorGrant resource check
-> bounded source fetch
-> temporary source context
-> SourceReference/cursor/digest/safe projection
-> existing Event/Agenda/Wake/Decision path
-> exact EffectProposal
-> automatic-policy evaluation or Human approval
-> dispatch-time revalidation
-> effect attempt/result/reconciliation
-> causal audit
```

OpenAI is planned behind a P12 gateway using `gpt-5.5`, Responses API, Structured Outputs,
and explicit `store:false`. It receives no tools, credentials, or execution authority and
returns only a bounded semantic decision; the server reconstructs authoritative fields.

Microsoft 365 is planned behind P13 connectors with one delegated work/school account per
Agent, device-code public-client authentication, project multi-tenant and BYO single-tenant
App modes, explicit consent/configuration state, Outlook per-folder delta, Teams allowlisted
dated polling, Planner ETag/`If-Match`, and SharePoint selected read-only access. Bodies are
temporary context, not durable memory.

Every unknown, missing, stale, revoked, cross-namespace, cross-Agent, digest/schema
mismatch, unbound resource, ambiguous authority, or budget overflow fails closed.

### Interface transition inventory

P9 inventories and does not edit these compatibility surfaces:

- `studio/src/App.tsx` contains P6 local-governance/control-plane and under-verification
  copy. P10 owns product copy and translation keys.
- `src/digital_colleagues/local/runtime.py` sets a P7 FastAPI title and `0.0.0-p7` version.
  P10 owns product metadata.
- `src/digital_colleagues/api/app.py` and `p4_app.py` retain P3/P4 milestone metadata. P10
  owns product-facing correction.
- Existing `/p5` and `/p6` names are compatibility routes, not future product vocabulary.
  They remain until a separate deprecation contract. New v0.2 public APIs use stable terms
  under `/api/v1`; P11+ schemas/APIs do not expose milestone names.

P11 preserves v0.1 data by converting the single colleague to a legacy/manual deployment
without rebuilding authority. Migration 008 can first be considered in P11 only if an
additive schema need exists. Package upgrade is a new draft, connection revocation
invalidates grants and pending effects, and database rollback uses verified backup with
matching code rather than destructive down migration.

## P11 package and multi-deployment implementation boundary

P11 adds pure frozen `AgentPackage`, package trust, deployment draft, and lifecycle values;
application ports/services; a bounded archive and offline attestation adapter; additive
SQLite persistence; and strict HTTP/CLI/Studio mappings. Dependency direction remains
pure core toward application and stable ports, with SQLite, process, temporary storage,
and HTTP at adapters or composition edges.

Every deployment owns an exact colleague namespace and independently bound Profile,
Mandate, Policy, MODEL/SERVICE principals, work, approvals, effects, and audit. Package
requested capabilities are displayed against Mandate grants but cannot create them.
Only active lifecycle reaches retained runtime processing. A null reserved connection slot
is persisted; P11 implements no connector, collaboration, shared-memory, or Skill runtime.

## P10 Mac quickstart and distribution boundary

P10 changes only the local operator/distribution edge and product presentation. A root
POSIX-shell launcher verifies an immutable bundle and drives an image-only Compose topology
from exact digests. API, worker, and one-shot operations share a non-root runtime image;
Studio uses a separate image. Both local OCI indexes contain exactly `linux/amd64` and
`linux/arm64`. State is an explicit Application Support bind mount; Studio has no secret
mount. Existing application/core/store authority and migrations 001-007 are unchanged.

FileVault status and safe filesystem modes classify encrypted-storage readiness without
enabling FileVault or accepting a credential. The deterministic reference path remains
provider-free. Studio translation resources change presentation only; route/payload/schema
and authority behavior remain identical. Existing milestone-named routes remain compatible
while public metadata uses stable product terms.

A later operator authorization fixes one public GHCR repository identity, two image
subjects, one branch workflow identity, and one publication source revision. The temporary
publication job alone receives package/OIDC/attestation writes; the independent verifier
uses anonymous exact-digest registry access and read-only GitHub access. Passing evidence
is locked before those jobs are removed from the branch. The publication source revision
and later evidence implementation revision remain distinct. This can establish a remote
distribution candidate, not a formal Release, production supply-chain assurance, P10
acceptance, or authorization for P11.

## P12 B+ continuity rebaseline architecture

P12 changes architecture documentation and governance only. The executable architecture,
ports, migrations, API, Studio, worker, Compose topology, and dependencies remain the
accepted P11R baseline. Future work preserves the dependency direction and adds records at
their owning gates:

```text
P14 normalized sources and HUMAN-approved transports
       |                       P16 bounded semantic-memory selection
       v                                      |
P17 correlation/recovery -> P15 continuation + checkpoint
                                      |
                                      v
                         P18 bounded proactivity and automatic proof
                                      |
                                      v
                         P19 composition-only tracker -> P20 release gate
```

ProjectScope is only deployment Namespace plus `project_id`. Exact authority/source
revisions belong to ProjectContinuationState and SessionCheckpoint. The continuation
state machine is exactly `active`, `waiting`, `needs_human`, `completed`, and `stopped`;
P18 pause is a separate ProactivityState value.

P15 owns exact wait state and explicit HUMAN binding but never provider polling or raw
correlation. P17 invokes P14 source/normalization ports for bounded autonomous polling,
owns TriggerCorrelation, ambiguity quarantine, wake, and durable-truth recovery, and uses
RecoveryScanCheckpoint only as an optimization. P16 provides immutable bounded
MemoryRetrievalSet identities/digests; checkpoints never copy memory bodies.

P14 owns bounded Outlook existing-thread, Teams allowlisted-chat, and Planner latest-ETag
`If-Match` transport adapters. Each P14 write consumes an exact current
HumanApprovalDecision; SharePoint is read-only. P18 reuses the transports, outbox,
fencing, idempotency, EffectAttempt, ActionResult, and reconciliation, adding only
AutomaticEffectAuthorization. P19 cannot add a missing connector primitive.

Future migrations stay additive behind ports: P13 owns 009, P14 owns 010, P15 owns 011,
P16 owns 012, P17 owns 013, and P18 owns 014. Migrations 001-008 and their manifest remain
immutable. P19/P20 add no migration, and 015 has no owner.
