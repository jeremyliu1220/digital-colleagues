<!-- SPDX-License-Identifier: Apache-2.0 -->

# Digital Colleagues

**Build, govern, and run persistent AI coworkers.**

Digital Colleagues is an open-source, local-first control plane and reference stack for
making an AI coworker's identity, delegated authority, responsibilities, finite work,
approvals, effects, persistence, and audit causality explicit and testable.

> **Project status — P2 core primitives.** Framework-independent immutable contracts now
> make namespace, principals, Mandate authority, finite work, wake records, exact effects,
> human approvals, replay semantics, and causal audit links explicit. Persistence,
> application orchestration, APIs, authentication, and effect execution do not exist yet;
> security effectiveness, production readiness, and live-provider acceptance are not
> claimed.

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

The planned v0.1 demonstration will let a reviewer start the local topology, create and
confirm a colleague Mandate, assign finite work, restart, run a deterministic wake cycle,
review an exact proposed effect, approve or reject it as an authorized human, and inspect
the complete causal chain. It will require no real model or messaging provider.

That product path is intentionally unavailable in P2. P3 adds the headless deterministic
slice, and P4 makes the complete five-minute path available in Studio. See
[the roadmap](docs/roadmap.md) and
[product brief](docs/product/v0.1-product-brief.md).

## Verify P2 in five minutes

Prerequisites are Python 3.12+, Node.js 22.12+, npm, and Make.

```bash
make check
make studio-dev
```

`make check` resolves the pinned tools in an isolated temporary workspace, then runs lint,
type checking, tests, a Studio production build, public-boundary and provenance checks,
and the P2 repository, architecture, and core-contract gates. The repository itself stays
free of `.venv`, `node_modules`, and build output so every public file can be scanned. The
final command starts an isolated copy of the static Studio shell on Vite's loopback
development address; restart it after editing source. It has no API integration yet.

Useful focused commands:

```bash
make lint
make typecheck
make test
make build
make boundary
make p2-provenance
make p2-architecture
make p2-core
make bootstrap
make evidence-p2
```

No command requires provider credentials or live data. Do not put either in this tree.
See [local development](docs/development.md) for exact commands and troubleshooting. The
accepted P1 evidence remains historical and must not be rebuilt from the P2 tree.

## Repository map

```text
src/digital_colleagues/  P2 immutable core and pure governance policies
studio/                  React, TypeScript, and Vite shell
tests/p0/                planning and public-boundary regressions
tests/p1/                historical scaffold contracts and fixture boundary
tests/core/              synthetic P2 primitive and governance contracts
tests/architecture/      dependency, determinism, and milestone boundaries
tests/p2/                P2 evidence and summary gates
scripts/                 sanitized boundary and evidence tools
docs/                    product, architecture, policy, and milestones
provenance/              fixed-revision source and scanner manifests
artifacts/               machine-readable milestone summaries
```

The private parent research repository remains read-only. P2 core is a new implementation
from the public architecture documents; the P2 migration receipt records zero transformed
source files.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md), the [Code of Conduct](CODE_OF_CONDUCT.md), and
[contributor licensing guidance](docs/licensing/contributing.md) before proposing a
change. Report vulnerabilities through the private process in [SECURITY.md](SECURITY.md),
never through a public issue containing sensitive details.

## License

Licensed under the [Apache License, Version 2.0](LICENSE). Attribution information is in
[NOTICE](NOTICE), and the reviewed dependency record is in
[the third-party inventory](docs/licensing/third-party-inventory.md).
