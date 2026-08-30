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
- Path-free `artifacts/p2/parent-fingerprint-before.json` and
  `artifacts/p2/parent-fingerprint-after.json` for the adjacent P2 reverification-fix
  cycle only.
- Updated architecture, capability, roadmap, maturity, development, licensing, and
  provenance documentation.

## Architecture boundary

Core uses an explicit allowlist of standard-library modules needed by the current contracts
and may import only `digital_colleagues.core` internally. Governance uses the same stdlib
allowlist and may import only core or governance. Every unlisted import fails closed,
including previously unknown third-party packages. Import aliases are resolved before
checking calls. Wall-clock reads, UUID or other randomness, environment access, filesystem
and temporary-file I/O, process execution, network capabilities, reverse core-to-governance
dependencies, and unresolved relative imports are forbidden. Deterministic hashing, JSON
serialization, datetime value validation, enums, dataclasses, typing, math, regex, and
collections remain allowed. P2 does not create application orchestration, adapters, APIs,
workers, persistence, or migrations.

## Provenance requirements

The parent research repository remains read-only. Source content may be read only from the
fixed revision through a digest-verified allowlist entry and only after rights and notice
review. Every transformed item requires a sanitized receipt containing only approved
fields. Code derived solely from public architecture documents is recorded as a new
implementation and is not represented as a migration.

For this correction cycle, the existing path-free fingerprint tool is run immediately
before and after work against fixed source revision
`dea9a9accc82fbedd35deb7117dcb5173223cf44`, excluding only the repository-relative
`digital-colleagues` subtree. Stored fingerprints contain only an exact approved schema of
aggregate counts and digests. The evidence collector requires both artifacts to be byte-
equivalent as JSON values and rejects missing, extra, malformed, broader-scope, wrong-
revision, or mismatched evidence before replacing the summary. These adjacent snapshots do
not reconstruct the historical interval from the P1 baseline through prior P2 commits;
that interval remains explicitly `not_evaluated` because no contemporaneous pair exists.

## Acceptance tests

The P2 suite must cover deep nested immutability, equality, deterministic serialization,
schema versions, explicit string identifiers, UTC-only time, `Z` round trips, complete
namespace checks, disjoint principal kinds, canonical server-controlled human roles,
Profile versus Mandate authority, revisioned authority diffs, finite-work dependencies,
responsibilities and obligations, causal event/agenda/wake records, fully specified exact
effects, human-only approval, revision and namespace binding, stale/wrong proposal refusal,
replayed-decision refusal, complete-proposal digest binding, typed boundary-constraint
enforcement, and direct-construction invariants for every exported dataclass.

`EffectProposal.proposal_digest` is a SHA-256 digest over a versioned canonical JSON
envelope. The envelope includes the contract schema version, complete namespace, proposal
ID and revision, decision ID, effect kind, destination kind and target, action, payload
digest, safe projection, boundary ID, effect idempotency key, validity limit, maximum
attempts, typed constraint parameters, proposal state, complete actor identity, correlation
and causation IDs, and occurrence time. The digest never contains itself. The independent
`payload_digest` remains available without exposing payload bytes. Both
`HumanApprovalDecision` and `ApprovalAuthorization` carry and validate both digests.

P2 boundary constraints use a deliberately minimal typed schema. `network` is the only
recognized constraint and its value must be an actual boolean. A proposal's constraint
keys, types, and values must exactly match the authoritative boundary. Empty, missing,
extra, unknown, wrong-type, or conflicting constraints fail closed. A boundary requiring
human approval accepts only `pending_approval`; a boundary that does not require it accepts
only `approved`, so `human_approval_required` always changes the policy outcome.

Architecture tests must reject forbidden imports, reverse dependencies, wall-clock reads,
randomness, environment access, and filesystem, database, or network I/O in deterministic
core and governance code. Adversarial CLI fixtures specifically cover an unapproved
`requests` import, `uuid.uuid4`, `tempfile`, aliased `datetime.now` and `utcnow`, process and
network modules, and the reverse core-to-governance dependency; every fixture must return a
nonzero checker result. Serialization tests must prove that sensitive effect payloads are
not emitted by the safe public projection.

The full unittest result must contain a positive test count and zero failures, errors,
skips, expected failures, and unexpected successes.

## Repeatable commands

```bash
python3 -B -m unittest discover -s tests -v
python3 -B scripts/check_public_boundary.py .
python3 -B scripts/check_p2_architecture.py .
PYTHONPATH=src python3 -B scripts/check_p2_core_contracts.py .
python3 -B scripts/fingerprint_source_tree.py \
  --source <parent-repository> \
  --revision dea9a9accc82fbedd35deb7117dcb5173223cf44 \
  --exclude-relative digital-colleagues
make check
make evidence-p2
```

`make check` is the current-tree P2 gate. P1 stage-absence assertions remain preserved as
historical fixture tests and are not applied to the P2 working tree. `make evidence-p1`
must not be run or used to rewrite the accepted P1 artifact.

## Evidence claim classes

Mechanical results are populated only from validated command results. Repository policy,
core architecture, contract shape, immutability, namespace, principal separation,
complete-effect binding, constraint enforcement, direct-construction invariants, authority
and approval, architecture allowlist enforcement, adjacent parent-worktree stability,
serialization, Studio scaffold, and unittest counts may be marked passed only after their
gates succeed. The core checker must perform negative mutation, replay, namespace, role,
constraint, and constructor probes before returning those results. The adjacent parent
result is narrowly scoped to this correction cycle; historical P1-to-prior-P2 parent
stability, parent-worktree non-use, human review, publication, production security, privacy
effectiveness, and production readiness remain explicit `not_evaluated` claims.

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
