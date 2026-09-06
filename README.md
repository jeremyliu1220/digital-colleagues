<!-- SPDX-License-Identifier: Apache-2.0 -->

# Digital Colleagues

**Build, govern, and run persistent AI coworkers.**

Digital Colleagues is an open-source, local-first control plane and reference stack for
making an AI coworker's identity, delegated authority, responsibilities, finite work,
approvals, effects, persistence, and audit causality explicit and testable.

> **Project status — P8 development complete, awaiting independent acceptance.** P7 passed
> independent acceptance and was fast-forward merged to `main` at the fixed P8 base
> `df47f8d075f7c0660ab5ed6035f8acfa3d3da4dc`. P8 `0.1.0` has passed its development
> gates but has not passed independent acceptance. No tag, GitHub Release, package, image, or formal
> release exists. Named-provider compatibility, live delivery, production readiness or
> security, distributed operation, measured human improvement, and an unmeasured
> five-minute limit are not claimed.

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

## Accepted P7 baseline and P8 contract

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
starts from that fixed baseline and defines release/operations convergence in its
[acceptance contract](docs/p8/acceptance.md), [operator guide](docs/p8/operations.md),
[release checklist](docs/p8/release-checklist.md), and
[release Golden Path](docs/p8/release-golden-path.md).

## P8 development verification

Prerequisites are Python 3.12+, Node.js 24.15.0, npm 11.12.1 through Corepack, Git, Make,
and Docker Engine/Compose for the required actual operational Gate.

```bash
make check
make studio-dev
```

`make check` resolves the hash-checked Python lock in an OS temporary workspace, runs Python
and Studio lint/type/test/build, the public boundary, accepted historical regressions, and
the current P8 repository, operations, backup/restore, diagnostics, supply-chain,
reproducibility, release, and Golden Path gates. Private databases, package environments,
candidate artifacts, backups, diagnostics, credentials, and build trees remain outside the
repository. `make p8-compose-runtime` and `make p8-golden` require an actual Docker runtime;
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
make p3-provenance
make p3-architecture
make p3-migrations
make p3-persistence
make p3-runtime
make p3-golden
make bootstrap
make evidence-p8
```

No public Gate requires provider credentials or live data. P7 uses only temporary synthetic
loopback credentials, while P8 default operations contact no provider. Do not put live
credentials, databases, backups, diagnostics, or data in this tree.
See [local development](docs/development.md) for exact commands and troubleshooting. The
accepted P0–P4 evidence remains historical and must not be rebuilt from the P5 tree.

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
tests/persistence/       SQLite migration, namespace, transaction, and fencing tests
tests/runtime/           Agenda, authorization, outbox, ambiguity, and crash tests
tests/api/               in-process typed FastAPI mapping tests
scripts/                 sanitized boundary and evidence tools
release/                 deterministic source-archive and supply-chain input policy
docs/                    product, architecture, policy, and milestones
provenance/              fixed-revision source and scanner manifests
artifacts/               machine-readable milestone summaries
```

The private parent research repository remains read-only. P0-P7 history, acceptance,
artifacts, evidence, migrations 001-007, fingerprints, and provenance receipts remain
unchanged. P8 starts from the accepted public P7 baseline and migrates no parent
working-tree content.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md), the [Code of Conduct](CODE_OF_CONDUCT.md), and
[contributor licensing guidance](docs/licensing/contributing.md) before proposing a
change. Report vulnerabilities through the private process in [SECURITY.md](SECURITY.md),
never through a public issue containing sensitive details.

## License

Licensed under the [Apache License, Version 2.0](LICENSE). Attribution information is in
[NOTICE](NOTICE), and the reviewed dependency record is in
[the third-party inventory](docs/licensing/third-party-inventory.md).
