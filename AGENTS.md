<!-- SPDX-License-Identifier: Apache-2.0 -->

# AGENTS.md

## Mission

Digital Colleagues is an open-source, local-first control plane and reference stack for
building persistent AI coworkers. The project must make authority, identity, work,
approvals, effects, persistence, and audit causality explicit and testable.

## Source of truth

Before changing the project, read in order:

1. `docs/product/v0.1-product-brief.md`
2. `docs/architecture/target-architecture.md`
3. `docs/security/threat-model.md` and `docs/security/privacy-boundary.md`
4. `docs/roadmap.md`
5. relevant ADRs, milestone acceptance records, and provenance manifests

Conversation is not project memory. Material decisions and experiment results must be
recorded in the project.

## Milestone discipline

- Work only in P0 through P8 order.
- Do not begin the next milestone until the current milestone's documented gate passes.
- An exit criterion requires a repeatable command and an evidence artifact.
- A failed hypothesis stays in the record with its consequence.
- P0 contains planning documents, provenance and public-boundary tools, and P0 tests only.
- P0 must not initialize Git, create a remote, push, publish, migrate product code, or
  create P1 artifacts such as `LICENSE`, `NOTICE`, contributor licensing files, product
  packages, Studio, migrations, or Docker Compose.
- P1 may create repository policy, packaging, Studio shell, development, and CI scaffold
  only. It must not add P2 core primitives, migrations, application services, adapters,
  APIs, workers, Compose topology, or migrated source content.

## Source repository boundary

The parent research repository is read-only. Its fixed review revision is
`dea9a9accc82fbedd35deb7117dcb5173223cf44`.

- Read source content only through the versioned allowlist and the fixed revision.
- A runtime `--source` argument may locate a local checkout, but its absolute location
  must never be persisted or echoed in output, diagnostics, snapshots, or errors.
- Never copy current working-tree content, raw evidence, live-provider material, personal
  acceptance material, credentials, provider identifiers, or local configuration.
- Every future migrated file must have an allowlist entry, verified digest, destination,
  classification, and required transform before it is written here.
- If ownership or relicensing rights are uncertain, stop that file's migration and add it
  to the unresolved rights inventory. Do not infer permission.
- Do not create links from this project to a local source checkout.

## Architecture rules

The dependency direction is:

```text
Pure core <- application and governance -> stable ports
                                   <- intelligence adapters
                                   <- infrastructure and HTTP adapters
```

- Core uses frozen standard-library dataclasses, Enums, and Protocols.
- Core must not import FastAPI, Pydantic, provider SDKs, channel SDKs, database drivers
  other than port definitions, ORMs, or orchestration frameworks.
- Pydantic is restricted to HTTP mapping at the application edge.
- Persisted records carry a schema version and complete namespace.
- IDs are explicit strings; timestamps are timezone-aware UTC and serialize with `Z`.
- Deterministic code receives time, randomness, configuration, and I/O through ports.
- Stores remain behind ports even while v0.1 uses one local `state.sqlite`.
- Do not claim PostgreSQL, distributed execution, high availability, production tenancy,
  enterprise IAM, security certification, or production readiness without a later gate.

## Security and identity rules

- Human, model, and service principals are distinct durable kinds.
- Canonical human roles are `tenant_admin`, `colleague_user`, and `auditor`.
- Callers never submit authoritative roles.
- Model and service principals never become human principals and never submit a human
  approval decision.
- Mutations require server-side authorization, namespace checks, concurrency controls,
  replay defenses, and audit events.
- Secrets, personal identifiers, live receipts, and personal acceptance data are forbidden
  from the public tree.

## Licensing

The intended public license is Apache-2.0. During P0, ADR 0001 and the source-rights
record govern preparation. The formal license, notice, and contributor-facing license
documents are P1 work and must not be created early.

## Verification

Run the P0 gate from the project root:

```bash
python3 -m unittest discover -s tests/p0 -v
python3 scripts/check_public_boundary.py .
python3 scripts/verify_source_allowlist.py --source SOURCE_CHECKOUT --revision dea9a9accc82fbedd35deb7117dcb5173223cf44
```

The fingerprint tool is run immediately before and after P0 against the parent source,
excluding only this authorized target subtree. It aggregates status, tracked changes, and
the content state of existing untracked and ignored entries without emitting their paths
or content. A matching fingerprint shows that P0 did not modify the pre-existing
parent-source state; it is not product or security evidence.
