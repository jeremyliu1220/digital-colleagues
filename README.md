<!-- SPDX-License-Identifier: Apache-2.0 -->

# Digital Colleagues

**Build, govern, and run persistent AI coworkers.**

Digital Colleagues is an open-source, local-first control plane and reference stack for
making an AI coworker's identity, delegated authority, responsibilities, finite work,
approvals, effects, persistence, and audit causality explicit and testable.

> **Project status — P11R is accepted and remote-closed on `main` at
> `c1562ea5201394d8a278f4b644daf4029cbb5bd4`.** P12 is an isolated governance-only
> Public Pilot Continuity Rebaseline under its immutable
> [acceptance contract](docs/p12/acceptance.md). It adds no runtime, API, CLI, Studio,
> schema, migration, provider, connector, memory, trigger, proactivity, release, or
> publication capability. P10 is the sole protected historical publication; no tag or
> GitHub Release exists. Named-provider, private-live, HUMAN-evaluation, soak, and Public
> Pilot results remain `not_evaluated` until their owning P13-P20 gates pass.

## What makes a digital colleague different?

An assistant answers a request. A task agent completes a bounded goal. A digital colleague
operates under a durable, revisable mandate: it owns ongoing responsibilities, resumes work
across restarts, proposes exact effects within delegated authority, and leaves an
inspectable causal record.

The reference stack is designed around these boundaries:

| Explicit primitive | Intended answer |
| --- | --- |
| Identity and namespace | Who is acting, and for whom? |
| Revisioned Mandate | What may and must this colleague do? |
| Durable work and wake cycles | What continues across process restarts? |
| Exact effect and human approval | What precise action was authorized, by which human? |
| Causal audit chain | Why did this result happen? |

The target is a local deterministic reference implementation—not enterprise IAM,
production tenancy isolation, high availability, compliance certification, or a hosted
service.

## Accepted P8 main baseline and historical contract

P5 retained the accepted P4 local Compose and Studio path and added an inert, revisioned
Profile/Mandate/policy draft. A local Admin reviews explicit defaults and a classified
before/after diff, confirms the exact base revisions and digest, and then exercises
working-hours, trigger, proactivity, notification/interruption, wake-budget, stop, resume,
escalation, stale-draft, and stale-proposal behavior. See the
[P5 operator guide](docs/p5/golden-path.md). P6 adds accepted local multi-user governance,
two-person authority changes, recovery, approval revalidation, and bounded audit export.
P7 adds accepted, explicitly optional provider-neutral HTTP JSON adapters behind the same
ports while retaining deterministic/reference defaults. Its public evidence is only an
offline loopback contract and proves no named-provider compatibility or real delivery. P8
started from that fixed baseline and converged release/operations readiness under its
fixed historical [acceptance contract](docs/p8/acceptance.md),
[operator guide](docs/p8/operations.md), [release checklist](docs/p8/release-checklist.md),
and [release Golden Path](docs/p8/release-golden-path.md). The accepted P0–P8 artifacts,
evidence, acceptance contracts, receipts, and migrations remain historical and unchanged.

## P10 development verification

Prerequisites are Python 3.12+, Node.js 24.15.0, npm 11.12.1 through Corepack, Git, Make,
and Docker Engine/Compose for the required actual operational Gate.

```bash
make check
make studio-dev
```

`make check` first checks out exact accepted P9 object
`11aa240af8db2ca515325dc059b1a77f7badc874` in an OS-temporary clone and runs its complete
retained `make check`, then runs the P10 repository, provenance, distribution, security,
operations, i18n, compatibility, reproducibility, local OCI/runtime, actual Mac quickstart,
evidence, and negative/abuse gates. The retained run still covers Python and Studio
lint/type/test/build, the public boundary, historical regressions, and P8 repository,
operations, backup/restore, diagnostics, supply-chain, reproducibility, release, Compose,
and Golden Path gates. Private databases, package environments, candidate artifacts,
backups, diagnostics, credentials, and build trees remain outside the repository.
`make p8-compose-runtime` and `make p8-golden` require an actual Docker runtime;
`not_evaluated` blocks P8 evidence.

Useful focused commands:

```bash
make lint
make typecheck
make test
make build
make boundary
make p4-repository
make p4-provenance
make p4-architecture
make p4-migrations
make p4-authentication
make p4-studio
make p4-compose
make p4-compose-runtime
make p4-golden
make p5-repository
make p5-provenance
make p5-architecture
make p5-migrations
make p5-builder
make p5-policy
make p5-studio
make p5-compose
make p5-compose-runtime
make p5-golden
make p6-repository
make p6-provenance
make p6-architecture
make p6-migrations
make p6-authentication
make p6-rbac
make p6-change-approval
make p6-effect-approval
make p6-audit-export
make p6-abuse
make p6-studio
make p6-compose
make p6-compose-runtime
make p6-golden
make p7-repository
make p7-provenance
make p7-architecture
make p7-model-adapter
make p7-channel-adapter
make p7-configuration
make p7-abuse
make p7-compose
make p7-compose-runtime
make p7-golden
make p8-repository
make p8-provenance
make p8-operations
make p8-backup-restore
make p8-diagnostics
make p8-supply-chain
make p8-reproducibility
make p8-release
make p8-compose-runtime
make p8-golden
make p9-repository
make p9-provenance
make p9-rebaseline
make p9-test
make p9-check
make p10-compose-runtime
make p10-quickstart
make p10-remote-distribution
make p10-check
make p3-provenance
make p3-architecture
make p3-migrations
make p3-persistence
make p3-runtime
make p3-golden
make bootstrap
make evidence-p9
```

No public Gate requires provider credentials or live data. P7 uses only temporary synthetic
loopback credentials, while P8 default operations contact no provider. Do not put live
credentials, databases, backups, diagnostics, or data in this tree.
See [local development](docs/development.md) for exact commands and troubleshooting. The
accepted P0–P8 evidence remains historical and must not be rebuilt from this tree.

## Repository map

```text
src/digital_colleagues/  core, governance, application, adapters, API, worker, and local composition
migrations/              numbered immutable-checksum SQLite schema
requirements/            exact milestone Python runtime/development locks
studio/                  authenticated React, TypeScript, and Vite local control interface
tests/p0/                planning and public-boundary regressions
tests/p1/                historical scaffold contracts and fixture boundary
tests/core/              synthetic P2 primitive and governance contracts
tests/architecture/      dependency, determinism, and milestone boundaries
tests/p2/                P2 evidence and summary gates
tests/p3/                restart Golden Path and synthetic fixtures
tests/p4/                authentication, metrics, Studio API, and recovery fixtures
tests/p5/                revisioned builder, typed policy, migration, and recovery fixtures
tests/p6/                local RBAC, recovery, change approval, export, and abuse fixtures
tests/p7/                offline optional-adapter contracts, configuration, and abuse fixtures
tests/p8/                release, backup/restore, diagnostics, inventory, and operations fixtures
tests/p9/                productization rebaseline governance, negative, and evidence fixtures
tests/p10/               Mac distribution, operator, i18n, compatibility, abuse, and evidence fixtures
tests/p11/               AgentPackage, deployment, migration, API, Studio, and lifecycle fixtures
tests/p11r/              accepted post-P11 current-CI alignment governance fixtures
tests/p12/               Public Pilot Continuity Rebaseline governance and negative fixtures
tests/persistence/       SQLite migration, namespace, transaction, and fencing tests
tests/runtime/           Agenda, authorization, outbox, ambiguity, and crash tests
tests/api/               in-process typed FastAPI mapping tests
scripts/                 sanitized boundary and evidence tools
release/                 deterministic source-archive and supply-chain input policy
docs/                    product, architecture, policy, and milestones
provenance/              fixed-revision source and scanner manifests
artifacts/               machine-readable milestone summaries
```

The private parent research repository remains read-only. P0-P8 history, acceptance,
artifacts, evidence, migrations 001-007, fingerprints, and provenance receipts remain
unchanged. P8 started from the accepted public P7 baseline and migrated no parent
working-tree content.

## Historical P9 Public Pilot planning boundary

P9 defined the original future product objects and P9-P15 delivery proposal in the
[v0.2 product brief](docs/product/v0.2-public-pilot-product-brief.md),
[v0.2 capability matrix](docs/product/v0.2-public-pilot-capability-matrix.md),
[external dependency register](docs/product/v0.2-external-dependency-register.md), and
[Roadmap](docs/roadmap.md).

AgentPackage is a non-executable, versioned, digest-bound declaration that requests but
never grants capabilities; it is not an S4 Skill. ColleagueDeployment is an isolated
namespaced instance, not shared knowledge or Agent collaboration. ExternalConnection
authenticates but grants nothing; an Admin-created ConnectorGrant binds exact resources and
actions to the current Mandate and Policy. AutomaticEffectAuthorization is a durable
low-risk policy record separate from HumanApprovalDecision. External source content is
temporary context, not Semantic Memory.

The originally planned first providers were OpenAI `gpt-5.5` through Responses API with Structured
Outputs and `store:false`, and delegated Microsoft 365 device-code connections for
Outlook, Teams, Planner, and selected read-only SharePoint. P9 made no provider call. The
accepted P12 Change Decision prospectively supersedes only the unimplemented P12-P15
assignments; the accepted P0-P11R history remains immutable.

## P10 Mac quickstart boundary

A downloaded candidate bundle needs only macOS and a running Docker Desktop:

```bash
./dc doctor
./dc quickstart
./dc status --json
```

The launcher uses prebuilt exact-digest images and an image-only Compose file. It creates
private `0700` directories below Application Support, keeps private files at `0600`, probes
FileVault without changing it, and accepts no provider credential. See the
[operator guide](docs/p10/operations.md), [distribution contract](docs/p10/distribution.md),
and [compatibility inventory](docs/p10/compatibility.md).

The separately authorized distribution gate uses only the two public exact-digest GHCR
subjects locked in `distribution/p10/verification-policy.json`. The display tag is never
an execution selector. `make p10-remote-distribution` re-verifies the two-platform indexes,
all referenced manifests/configs/layers, anonymous pulls, exact keyless identity/issuer/
annotation, GitHub provenance, a digest-bound bundle, and three clean Mac quickstarts.
This remains a candidate rather than a GitHub Release or P10 acceptance and makes no
provider compatibility, always-on, production security/privacy, or production-readiness
claim.
OpenAI live, Microsoft 365 live, and human evaluation remain `not_evaluated`; mock, stub,
or loopback evidence cannot establish live or named-provider compatibility.

Current P6/P7-branded Studio/API metadata and `/p5`/`/p6` route names remain unchanged in
P9. P10 owns user-facing product metadata and translation-key foundations; existing routes
remain compatibility surfaces until a separate deprecation contract. New v0.2 public APIs
will use stable product vocabulary under `/api/v1`.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md), the [Code of Conduct](CODE_OF_CONDUCT.md), and
[contributor licensing guidance](docs/licensing/contributing.md) before proposing a
change. Report vulnerabilities through the private process in [SECURITY.md](SECURITY.md),
never through a public issue containing sensitive details.

## License

Licensed under the [Apache License, Version 2.0](LICENSE). Attribution information is in
[NOTICE](NOTICE), and the reviewed dependency record is in
[the third-party inventory](docs/licensing/third-party-inventory.md).

## P11 agent packages and deployment registry

P11 development adds an inert, canonical `dc-agent/v1` package format and an independently
governed `ColleagueDeployment` registry. Package validation, provenance, Admin trust,
installation, draft review, exact confirmation, and activation are distinct. Package
requests never grant authority; Mandate, Policy, current membership, and existing effect
approval controls remain authoritative. At most ten deployments may be active on the
local host, and only active deployments reach the runtime.

See the fixed [P11 acceptance contract](docs/p11/acceptance.md),
[compatibility contract](docs/p11/compatibility.md), and
[local operations guide](docs/p11/operations.md), and accepted P11R current-CI alignment.
These are historical accepted results, not authority to implement a later capability.

## P12 Public Pilot Continuity Rebaseline

The exact forward sequence is P12 governance rebaseline, P13 migration parser plus OpenAI
Model Gateway, P14 Microsoft 365 Connector Foundation, P15 Durable Project Continuation,
P16 Semantic Memory Lifecycle, P17 Trigger/Schedule/Correlation/Recovery, P18 bounded
goal-driven proactivity, P19 the built-in bilingual project tracker, and P20 the always-on
Public Pilot release gate. Every phase is independently accepted and remote-closed before
the next begins.

P12 fixes these future contracts without implementing them: ProjectScope is only
deployment Namespace plus `project_id`; ProjectContinuationState has exactly `active`,
`waiting`, `needs_human`, `completed`, and `stopped`; waits have exact kinds/statuses and
one-time ANY/ALL consumption; GoalBinding is HUMAN-accepted and cannot proactively trigger
before P18; memory admission is only `admit`/`reject` and later lifecycle is separate;
recovery scans rebuild from durable incomplete state rather than trusting a cursor.

P14 owns bounded HUMAN-approved Outlook existing-thread, Teams allowlisted-chat, and
Planner latest-ETag `If-Match` write transports while SharePoint remains read-only. P18
alone adds AutomaticEffectAuthorization and reuses those transports. P19 only composes
accepted P13-P18 primitives. See [ADR 0011](docs/adr/0011-public-pilot-continuity-rebaseline.md)
and the [P12 checklist](docs/p12/rebaseline-checklist.md). Passing P12 establishes only a
static and `synthetic_offline` governance rebaseline and never a Public Pilot claim.
