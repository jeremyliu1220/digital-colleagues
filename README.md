<!-- SPDX-License-Identifier: Apache-2.0 -->

# Digital Colleagues

**Build, govern, and run persistent AI coworkers.**

Digital Colleagues is an open-source, local-first control plane and reference stack for
making an AI coworker's identity, delegated authority, responsibilities, finite work,
approvals, effects, persistence, and audit causality explicit and testable.

> **Project status — P5 development complete, awaiting independent acceptance.** The
> revisioned colleague builder, typed policy enforcement, additive migration 006, and
> isolated Compose Golden Path are implemented on the P5 development branch. P5 is not
> accepted or merged. Real providers, production security, distributed operation, measured
> human improvement, and a proven five-minute limit are not claimed.

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

## The revisioned-builder Golden Path

P5 retains the accepted P4 local Compose and Studio path and adds an inert, revisioned
Profile/Mandate/policy draft. A local Admin reviews explicit defaults and a classified
before/after diff, confirms the exact base revisions and digest, and then exercises
working-hours, trigger, proactivity, notification/interruption, wake-budget, stop, resume,
escalation, stale-draft, and stale-proposal behavior. See the
[P5 operator guide](docs/p5/golden-path.md), [roadmap](docs/roadmap.md), and
[product brief](docs/product/v0.1-product-brief.md).

## Verify P5

Prerequisites are Python 3.12+, Node.js 22.12+, npm, and Make.

```bash
make check
make studio-dev
```

`make check` resolves the exact lock in an OS temporary workspace, then runs Python and
Studio lint, type checks, tests and build plus the public-boundary, repository, provenance,
architecture, migration, builder, policy, static Compose, Studio, and all retained P0–P4
regression gates. All test databases and package environments remain outside the repository.
The separate `make p5-compose-runtime` target requires Docker and performs the actual
isolated start/recreate/recovery/policy/dispatch/stop/cleanup Gate. Evidence generation
requires that runtime Gate to pass.

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
make p3-provenance
make p3-architecture
make p3-migrations
make p3-persistence
make p3-runtime
make p3-golden
make bootstrap
make evidence-p5
```

No command requires provider credentials or live data. Do not put either in this tree.
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
tests/persistence/       SQLite migration, namespace, transaction, and fencing tests
tests/runtime/           Agenda, authorization, outbox, ambiguity, and crash tests
tests/api/               in-process typed FastAPI mapping tests
scripts/                 sanitized boundary and evidence tools
docs/                    product, architecture, policy, and milestones
provenance/              fixed-revision source and scanner manifests
artifacts/               machine-readable milestone summaries
```

The private parent research repository remains read-only. P5 is new work from public
documents and the accepted public P4 implementation; its provenance receipt records zero
transformed source files and covers the complete P5 change inventory.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md), the [Code of Conduct](CODE_OF_CONDUCT.md), and
[contributor licensing guidance](docs/licensing/contributing.md) before proposing a
change. Report vulnerabilities through the private process in [SECURITY.md](SECURITY.md),
never through a public issue containing sensitive details.

## License

Licensed under the [Apache License, Version 2.0](LICENSE). Attribution information is in
[NOTICE](NOTICE), and the reviewed dependency record is in
[the third-party inventory](docs/licensing/third-party-inventory.md).
