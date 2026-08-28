<!-- SPDX-License-Identifier: Apache-2.0 -->

# P2 Core Primitives Acceptance Contract

## Scope

P2 establishes only framework-independent, deterministic, deeply immutable core contracts
and pure governance invariants for namespace, principals, authority, finite work, runtime
records, exact effects, human approval, replay rejection, and causal audit relationships.

## Required artifacts

- Frozen standard-library contracts under `src/digital_colleagues/core/`.
- Pure authorization and approval policies under `src/digital_colleagues/governance/`.
- Synthetic core, governance, serialization, architecture, and milestone tests.
- A P2 architecture checker and core-contract checker.
- A machine-readable migration receipt that distinguishes transformed source from new
  implementations.
- A fail-closed evidence collector and `artifacts/p2/summary.json`.
- Updated architecture, capability, roadmap, maturity, development, licensing, and
  provenance documentation.

## Architecture boundary

Core may use only the Python standard library and may not import application,
infrastructure, API, worker, database, provider, channel, HTTP-validation, or orchestration
framework code. Governance may depend on core; core may not depend on governance. P2 does
not create application orchestration, adapters, APIs, workers, persistence, or migrations.

## Provenance requirements

The parent research repository remains read-only. Source content may be read only from the
fixed revision through a digest-verified allowlist entry and only after rights and notice
review. Every transformed item requires a sanitized receipt containing only approved
fields. Code derived solely from public architecture documents is recorded as a new
implementation and is not represented as a migration.

## Acceptance tests

The P2 suite must cover deep nested immutability, equality, deterministic serialization,
schema versions, explicit string identifiers, UTC-only time, `Z` round trips, complete
namespace checks, disjoint principal kinds, canonical server-controlled human roles,
Profile versus Mandate authority, revisioned authority diffs, finite-work dependencies,
responsibilities and obligations, causal event/agenda/wake records, fully specified exact
effects, human-only approval, revision and namespace binding, stale/wrong proposal refusal,
and replayed-decision refusal.

Architecture tests must reject forbidden imports, reverse dependencies, wall-clock reads,
randomness, environment access, and filesystem, database, or network I/O in deterministic
core and governance code. Serialization tests must prove that sensitive effect payloads are
not emitted by the safe public projection.

The full unittest result must contain a positive test count and zero failures, errors,
skips, expected failures, and unexpected successes.

## Repeatable commands

```bash
python3 -B -m unittest discover -s tests -v
python3 -B scripts/check_public_boundary.py .
python3 -B scripts/check_p2_architecture.py .
PYTHONPATH=src python3 -B scripts/check_p2_core_contracts.py .
make check
make evidence-p2
```

`make check` is the current-tree P2 gate. P1 stage-absence assertions remain preserved as
historical fixture tests and are not applied to the P2 working tree. `make evidence-p1`
must not be run or used to rewrite the accepted P1 artifact.

## Evidence claim classes

Mechanical results are populated only from validated command results. Repository policy,
core architecture, contract shape, immutability, namespace, principal separation,
authority and approval, serialization, Studio scaffold, and unittest counts may be marked
passed only after their gates succeed. Human review, parent-worktree non-use, publication,
production security, privacy effectiveness, and production readiness remain explicit
`not_evaluated` claims.

## Stop condition

P2 is complete only after `make check`, `make evidence-p2`, a second `make check`, the
public-boundary scan, parent fingerprint comparison, repository hygiene inspection, and a
milestone commit all succeed; a final post-commit `make check` must also pass with a clean
worktree. Stop after P2 and do not begin P3.

## Explicit P3 exclusions

P2 excludes databases, migrations, repositories, FastAPI or Pydantic mappings, application
services, workers, event loops, provider or channel adapters, authentication, Studio
runtime controls, Docker Compose, restart orchestration, and real or deterministic effect
execution. These remain P3 or later work.
