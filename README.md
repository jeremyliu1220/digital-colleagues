<!-- SPDX-License-Identifier: Apache-2.0 -->

# Digital Colleagues

**Build, govern, and run persistent AI coworkers.**

Digital Colleagues is an open-source, local-first control plane and reference stack for
making an AI coworker's identity, delegated authority, responsibilities, finite work,
approvals, effects, persistence, and audit causality explicit and testable.

> **Project status — P1 repository scaffold.** Packaging, Studio tooling, public-boundary
> checks, community policies, and CI exist. The runtime does not. No current screen or
> package demonstrates P2+ product behavior, security effectiveness, production readiness,
> or live-provider acceptance.

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

That product path is intentionally unavailable in P1. P2 adds core primitives, P3 adds the
headless deterministic slice, and P4 makes the complete five-minute path available in
Studio. See [the roadmap](docs/roadmap.md) and
[product brief](docs/product/v0.1-product-brief.md).

## Verify the scaffold in five minutes

Prerequisites are Python 3.12+, Node.js 22.12+, npm, and Make.

```bash
make check
make studio-dev
```

`make check` resolves the pinned tools in an isolated temporary workspace, then runs lint,
type checking, tests, a Studio production build, the P1 scaffold contract, and the
public-boundary gate. The repository itself stays free of `.venv`, `node_modules`, and
build output so every public file can be scanned. The final command starts an isolated
copy of the static Studio shell on Vite's loopback development address; restart it after
editing source. It has no API integration yet.

Useful focused commands:

```bash
make lint
make typecheck
make test
make build
make boundary
make bootstrap
make evidence-p1
```

No command requires provider credentials or live data. Do not put either in this tree.
See [local development](docs/development.md) for exact commands and troubleshooting.
P1 evidence is intentionally pre-Git and refuses to overwrite the milestone snapshot once
a root `.git` directory or validated worktree pointer exists.

## Repository map

```text
src/digital_colleagues/  Python package boundary; no P2 core yet
studio/                  React, TypeScript, and Vite shell
tests/p0/                planning and public-boundary regressions
tests/p1/                scaffold acceptance contracts
scripts/                 sanitized boundary and evidence tools
docs/                    product, architecture, policy, and milestones
provenance/              fixed-revision source and scanner manifests
artifacts/               machine-readable milestone summaries
```

The private parent research repository remains read-only. P1 was written as a clean-room
scaffold and contains no migrated parent working-tree content.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md), the [Code of Conduct](CODE_OF_CONDUCT.md), and
[contributor licensing guidance](docs/licensing/contributing.md) before proposing a
change. Report vulnerabilities through the private process in [SECURITY.md](SECURITY.md),
never through a public issue containing sensitive details.

## License

Licensed under the [Apache License, Version 2.0](LICENSE). Attribution information is in
[NOTICE](NOTICE), and the reviewed dependency record is in
[the third-party inventory](docs/licensing/third-party-inventory.md).
