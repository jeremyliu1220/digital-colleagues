<!-- SPDX-License-Identifier: Apache-2.0 -->

# Digital Colleagues

**Build, govern, and run persistent AI coworkers.**

Digital Colleagues is an open-source, local-first control plane and reference stack for
making an AI coworker's identity, delegated authority, responsibilities, finite work,
approvals, effects, persistence, and audit causality explicit and testable.

> **Project status — P3 headless deterministic slice.** A synthetic path now persists
> namespace, principals, Mandate, finite work, triggers, Agenda generations, decisions,
> exact approvals, outbox attempts, results, and safe causal audit records in an injectable
> local SQLite database. It survives fresh-instance restart and suppresses replay without
> Studio, real models, provider accounts, or network effects. Authentication, production
> security, distributed operation, and live-provider acceptance are not claimed.

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

## The five-minute Golden Path

The P3 headless Golden Path creates synthetic durable identity, authority, and work; runs a
bounded deterministic wake; approves one exact proposal as a durable human; records a
reference ActionResult; restarts with fresh instances; and proves byte-equivalent causal
history plus replay suppression. P4 will expose the five-minute path in Studio and add the
separately gated local authentication workflow. See
[the roadmap](docs/roadmap.md) and
[product brief](docs/product/v0.1-product-brief.md).

## Verify P3

Prerequisites are Python 3.12+, Node.js 22.12+, npm, and Make.

```bash
make check
make studio-dev
```

`make check` resolves the exact P3 lock in an OS temporary workspace, then runs Python and
Studio lint, type checks, tests and build plus the public-boundary, repository, provenance,
architecture, migration, persistence, runtime-contract, and restart Golden Path gates. All
test databases and package environments remain outside the repository. `make studio-dev`
still shows only the static P1/P2 shell; P3 intentionally has no Studio runtime workflow.

Useful focused commands:

```bash
make lint
make typecheck
make test
make build
make boundary
make p3-provenance
make p3-architecture
make p3-migrations
make p3-persistence
make p3-runtime
make p3-golden
make bootstrap
make evidence-p3
```

No command requires provider credentials or live data. Do not put either in this tree.
See [local development](docs/development.md) for exact commands and troubleshooting. The
accepted P0/P1/P2 evidence remains historical and must not be rebuilt from the P3 tree.

## Repository map

```text
src/digital_colleagues/  core, governance, P3 application, adapters, API, and worker
migrations/              numbered immutable-checksum SQLite schema
requirements/            exact P3 Python runtime/development lock
studio/                  React, TypeScript, and Vite shell
tests/p0/                planning and public-boundary regressions
tests/p1/                historical scaffold contracts and fixture boundary
tests/core/              synthetic P2 primitive and governance contracts
tests/architecture/      dependency, determinism, and milestone boundaries
tests/p2/                P2 evidence and summary gates
tests/p3/                restart Golden Path and synthetic fixtures
tests/persistence/       SQLite migration, namespace, transaction, and fencing tests
tests/runtime/           Agenda, authorization, outbox, ambiguity, and crash tests
tests/api/               in-process typed FastAPI mapping tests
scripts/                 sanitized boundary and evidence tools
docs/                    product, architecture, policy, and milestones
provenance/              fixed-revision source and scanner manifests
artifacts/               machine-readable milestone summaries
```

The private parent research repository remains read-only. P3 is a new implementation from
the public architecture documents; the P3 migration receipt records zero transformed source
files and covers the complete P3 implementation tree.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md), the [Code of Conduct](CODE_OF_CONDUCT.md), and
[contributor licensing guidance](docs/licensing/contributing.md) before proposing a
change. Report vulnerabilities through the private process in [SECURITY.md](SECURITY.md),
never through a public issue containing sensitive details.

## License

Licensed under the [Apache License, Version 2.0](LICENSE). Attribution information is in
[NOTICE](NOTICE), and the reviewed dependency record is in
[the third-party inventory](docs/licensing/third-party-inventory.md).
