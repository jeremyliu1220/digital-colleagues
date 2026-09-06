<!-- SPDX-License-Identifier: Apache-2.0 -->

# ADR 0007: Declarative AgentPackage and ColleagueDeployment Model

- Status: Accepted for P9 planning; implementation deferred to P11
- Decision date: 2026-09-07
- Scope: v0.2 Public Pilot package and multi-Agent lifecycle contract

## Context

The accepted v0.1 reference stack has one namespaced colleague whose Profile, Mandate,
Policy, work, approval, effects, and audit are explicit. A Public Pilot needs repeatable
blueprints and multiple isolated instances without turning package material into executable
code, authority, S4 Skills, Semantic Memory, or Agent collaboration.

## Decision

### AgentPackage

An **AgentPackage** is a non-executable, versioned, digest-bound declarative blueprint. It
may contain only schema-valid metadata, `zh-TW` and `en-US` display content, prompts,
finite bounded workflow declarations, and requested capabilities. All package content is
untrusted data.

It cannot contain or trigger Python, Node, shell, binaries, browser automation, arbitrary
plugin code, dynamic import, `eval`, `exec`, or unbounded loops. It is not an S4 Skill and
does not create a Skill runtime, Skill Learning, or plugin system. It can request
capabilities but cannot authorize, install, activate, or expand itself, a Mandate, Policy,
ExternalConnection, ConnectorGrant, or approval.

Package sources are exactly:

1. official built-in;
2. local development package; or
3. GitHub Release artifact with a valid GitHub artifact attestation.

Attestation associates the exact artifact digest with source/build identity; it is not a
security judgment. An Admin must review signer, repository, workflow, digest, requested
capabilities, permission diff, and trust decision before inert installation. Archive and
content validation is bounded and fail closed.

### ColleagueDeployment

A **ColleagueDeployment** is a namespaced digital-colleague instance created from one exact
AgentPackage version and digest. It separately owns its Profile, Mandate, Policy,
lifecycle, ExternalConnections, ConnectorGrants, work, budgets, effects, and causal audit.
The reviewed deployment draft is inert until the Admin confirms its exact current
bindings.

One host may support no more than ten active deployments in the Public Pilot. This is a
lifecycle limit, not shared knowledge or collaboration. Cross-Agent reads, writes,
credentials, grants, effects, messaging, delegation, shared memory, and loops are denied by
default. Each record carries the complete deployment namespace.

### Lifecycle, compatibility, and i18n

Install does not activate. Upgrade always creates a new reviewed draft with capability and
permission differences; it never auto-applies. Rollback chooses an accepted, still-trusted
exact version. Digest mismatch, missing trust, stale version, revoked version, schema
mismatch, unknown capability, or ambiguous permission fails closed.

P11 converts the existing v0.1 single colleague to a legacy/manual ColleagueDeployment
without deleting, silently recreating, or weakening its Profile, Mandate, Policy, work,
approval, effect, or audit authority. Migration 008 is permitted no earlier than P11 and
only if an additive schema need exists; migrations 001-007 remain immutable. Database
rollback uses a verified backup with matching code, not a destructive down migration.

Localized display metadata and prompts may differ in language. Package schema, requested
capabilities, authority, permission semantics, digest binding, and fail-closed defaults are
identical across `zh-TW` and `en-US`. Missing translation cannot grant access.

### Planned package flow

```text
Package source -> bounded download/local selection -> digest
-> provenance/attestation verification -> archive/content safety validation
-> requested-capability inspection -> Admin trust decision -> inert installed package
-> reviewed deployment draft -> exact Mandate/Policy/ConnectorGrant binding
-> confirmed ColleagueDeployment
```

## Consequences

- Reusable configuration becomes inspectable without adding an executable extension
  boundary.
- Package provenance, package trust, runtime authority, and activation remain distinct.
- Multi-Agent hosting preserves independent authority and causality rather than implying
  shared knowledge or collaboration.
- P11 must prove finite schemas/workflows, exact digests, archive safety, trust/revocation,
  update/rollback, legacy migration, and isolation with negative/abuse tests.

## Rejected alternatives

- Executable package hooks, scripts, or arbitrary plugins: they would introduce code
  execution before an S4 gate.
- Package-requested capability as authority: it enables self-grant.
- Automatic update: it bypasses review of content and permission change.
- Shared namespace for ten Agents: it conflates hosting with collaboration.
- Reusing Skill terminology: it falsely implies executable S4 behavior.

## Claim boundary

P9 records this decision only. No parser, downloader, installer, Catalog, deployment
registry, multi-Agent runtime, migration, UI, or package execution is implemented or
accepted. P11 cannot start until P9 and P10 complete their required acceptance sequence.
