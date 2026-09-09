<!-- SPDX-License-Identifier: Apache-2.0 -->

# P11 Agent Package and Multi-Agent Lifecycle Acceptance Contract

Status: fixed development contract. This file is the complete, immutable contract for
P11 development. It is committed alone as the first P11 commit and must remain
byte-identical to that Git object. It must never be amended, rebased, squashed,
force-rewritten, weakened, or changed to fit implementation results.

P11 may be described only as **implementation candidate complete; awaiting independent
acceptance** after every gate below passes. It may not be described as accepted, merged,
released, published, live-provider validated, production-secure, or production-ready.
P12 remains unauthorized.

## Exact baseline, branch, ancestry, and commit boundary

- Exact P11 base and independently accepted, fast-forward-merged P10 ancestor:
  `4bef5629d450c6bb3940f606fc90194e008ee8fd`.
- Exact development branch: `codex/p11-agent-packages`.
- Work begins only from a clean `main` whose `HEAD`, local `main`, and `origin/main` equal
  the exact base; GitHub's default branch is `main`; the local and remote P10 candidate
  trees equal the main tree; migration history contains 001-007 plus the manifest; and no
  local or remote P11 branch already exists.
- The acceptance-contract commit is the first P11 commit and contains only this file. Its
  complete SHA becomes `P11_ACCEPTANCE_COMMIT`. Every implementation and evidence commit
  descends from it, and this file remains byte-identical to that commit.
- Implementation commits contain every authorized path except
  `artifacts/p11/summary.json`. That final evidence file is committed alone after a clean,
  committed implementation passes all direct and aggregate gates.
- Rebase, reset, stash, force, amend, history rewriting, merge, push, tag, Release,
  publication, and P12 work are forbidden.

## Historical immutable boundary

All accepted P0-P10 history is immutable relative to the exact base. Every file under
`docs/p0` through `docs/p10`, `artifacts/p0` through `artifacts/p10`, every P0-P10
provenance receipt or fingerprint, the fixed source allowlist and rights records, existing
remote-distribution evidence, and existing published GHCR identities and digests remain
byte-identical. Historical evidence writers are not invoked.

Migrations `001_initial.sql` through `007_governance_hardening.sql` remain byte-identical.
The first seven entries of `migrations/manifest.json` retain their exact name, file, order,
and checksum; the manifest changes only by appending migration 008. The protected P10
runtime digest
`sha256:a5bb41bdb85bf7b5a75dc79967e26943c098b024b64fdd345f5b4c6f4688991d`
and Studio digest
`sha256:7791d80d9fa464bbd1574601deba5a30ca6d980dab8c8275c24c117fae81e4c9`
are never selected for mutation, republished, overwritten, or deleted.

Living top-level documents in the allowlist may record that P10 was accepted and merged
and that P11 is in development. They do not reinterpret historical evidence.

## Exact changed-file allowlist

The complete base-to-final-candidate changed path set is exactly the following 59 paths.
No glob or directory shorthand is implied. A missing or additional path, rename, copy,
delete, type change, traversal, symlink, hardlink, device, socket, FIFO, staged change,
unstaged change, or untracked entry fails closed.

```text
Makefile
README.md
artifacts/p11/summary.json
docs/adr/0010-agent-package-and-deployment-lifecycle.md
docs/architecture/target-architecture.md
docs/development.md
docs/p11/acceptance.md
docs/p11/compatibility.md
docs/p11/operations.md
docs/roadmap.md
docs/security/privacy-boundary.md
docs/security/threat-model.md
migrations/008_agent_packages_and_deployments.sql
migrations/manifest.json
provenance/p11-migration-receipt.json
pyproject.toml
scripts/check_p11_architecture.py
scripts/check_p11_compatibility.py
scripts/check_p11_compose_runtime.py
scripts/check_p11_migrations.py
scripts/check_p11_provenance.py
scripts/check_p11_repository.py
scripts/check_p11_studio.py
scripts/collect_p11_evidence.py
scripts/p11_gate_support.py
scripts/run_p11_toolchain.py
src/digital_colleagues/adapters/package/__init__.py
src/digital_colleagues/adapters/package/archive.py
src/digital_colleagues/adapters/package/github_attestation.py
src/digital_colleagues/adapters/sqlite/p11_store.py
src/digital_colleagues/api/p11_app.py
src/digital_colleagues/application/p11_contracts.py
src/digital_colleagues/application/p11_ports.py
src/digital_colleagues/application/p11_services.py
src/digital_colleagues/cli.py
src/digital_colleagues/core/agent_package.py
src/digital_colleagues/core/deployment.py
src/digital_colleagues/core/governance.py
src/digital_colleagues/governance/rbac.py
src/digital_colleagues/local/runtime.py
src/digital_colleagues/local/worker.py
studio/src/AgentRegistry.tsx
studio/src/App.test.tsx
studio/src/App.tsx
studio/src/locales/en-US.ts
studio/src/locales/zh-TW.ts
studio/src/studioContract.ts
studio/src/styles.css
tests/p11/__init__.py
tests/p11/fixtures.py
tests/p11/test_agent_package.py
tests/p11/test_api_cli.py
tests/p11/test_archive.py
tests/p11/test_attestation.py
tests/p11/test_evidence_gate.py
tests/p11/test_lifecycle.py
tests/p11/test_migrations.py
tests/p11/test_repository.py
tests/p11/test_studio.py
```

No path outside this list may be changed. If implementation requires one, development
stops for change control; this contract is not edited.

## `dc-agent/v1` schema and canonical digest contract

An AgentPackage is inert, non-executable, versioned, and digest-bound. Its UTF-8 JSON
object has exactly `schema`, `schema_version`, `metadata`, `content`, and
`content_digest`. `schema` is exactly `dc-agent/v1`; `schema_version` is integer `1`.

`metadata` has exactly `package_id`, `version`, `runtime_api`, and `display`:

- `package_id` is a stable lowercase ID; `version` is canonical `MAJOR.MINOR.PATCH` with
  no leading zero ambiguity; `runtime_api` is exactly `1`;
- `display` has exactly `en-US` and `zh-TW`; each has non-empty bounded `name` and
  `summary` fields and cannot affect schema, capability, permission, or authority.

`content` has exactly `prompts`, `requested_capabilities`, and `workflow`:

- `prompts` has exactly `en-US` and `zh-TW`, each inert UTF-8 text of at most 8,192
  characters; prompt/localized text is never interpreted as an instruction by a
  validator, installer, migration, gate, or runtime;
- `requested_capabilities` has at most 16 unique values selected only from
  `read_work`, `manage_work`, `propose_reference_message`, `propose_internal_record`,
  `notify_human`, and `read_audit`; a request is never a grant;
- `workflow` has exactly `entrypoint` and `steps`. It contains at most 32 nodes, at most
  two outgoing branches per node, maximum graph depth 8, and maximum traversed steps 16.
  All nodes are reachable from one entrypoint and every path terminates at `complete`.

Workflow step types and exact fields are:

| Type | Exact fields | Finite semantics |
| --- | --- | --- |
| `instruction` | `id`, `type`, `prompt`, `next` | Select inert prompt locale key `primary`, then advance |
| `condition` | `id`, `type`, `predicate`, `on_true`, `on_false` | Branch only on `work_is_pending`, `approval_is_required`, or `effect_is_allowed` |
| `propose_effect` | `id`, `type`, `effect_kind`, `next` | Declare only `reference_message`, `internal_record`, or `notification`; governance still decides |
| `complete` | `id`, `type` | Terminal node |

Loops, cycles, recursion, unreachable nodes, unknown steps/fields/predicates/effects,
self-modification, self-grant, cross-Agent targets, arbitrary commands/tools/plugins,
P12/P13 calls, and ungoverned effects fail closed. The complete canonical package is at
most 65,536 UTF-8 bytes.

Canonical JSON uses UTF-8, lexicographically sorted object keys, original array order,
no insignificant whitespace, no NaN/infinity, no duplicate JSON keys, and no lossy
normalization. `content_digest` is SHA-256 over the canonical `content` object. The exact
package digest is SHA-256 over the canonical complete package including that content
digest. Every inspect, trust, install, deployment, upgrade, rollback, and audit binding
uses the exact package ID, version, and digest. Unknown schema/version/runtime API/field,
duplicate key, invalid Unicode, unsupported capability, content mismatch, caller expected
digest mismatch, or semantic ambiguity fails closed.

## Archive and source safety contract

The only archive format is ZIP with exactly one root regular file named `agent.json`.
The archive is at most 131,072 bytes compressed; at most four members are parsed before
the exact-member rule is applied; one member and total extracted content are each at most
131,072 bytes; compression ratio is at most 20:1; path depth is at most two; archive and
member comments, encryption, absolute paths, backslashes, traversal, empty names,
duplicates, Unicode/case collisions, symlinks, hardlinks, devices, sockets, FIFOs, other
special files, hidden entries, scripts, binaries, dynamic code/plugin declarations, and
additional payloads are rejected. `agent.json` bytes must equal its canonical JSON bytes.
No generic extraction is performed.

Package source classification is exactly `official_builtin`, `local`, or
`github_release`. Source does not imply trust. Local and official packages require the
same schema/content/archive validation and explicit Admin trust. A GitHub Release artifact
also requires successful server-side GitHub CLI attestation verification before it can be
registered. Failure or unavailable verification is not downgraded.

## GitHub attestation and trust boundary

GitHub verification uses a configured GitHub CLI plus an operator-controlled trusted-root
file and an offline attestation bundle. It invokes `gh attestation verify` with the exact
artifact, repository, signer workflow, signer digest, source ref, source digest, SLSA
provenance predicate, GitHub OIDC issuer, self-hosted-runner denial, bundle, custom trusted
root, and JSON output. It uses no GitHub credential and performs no login or remote write.
Output is bounded and parsed as untrusted JSON; failure, timeout, empty result, malformed
result, wrong subject digest, repository, workflow, signer/build identity, source, issuer,
or predicate fails closed and is sanitized.

An attestation proves origin only. It never means schema-valid, safe, trusted, installed,
confirmed, or active. Admin trust review shows signer, repository, workflow/build identity,
artifact digest, package version, requested capabilities, current Mandate/Policy
permission differences, verification result, and the explicit trust decision. Trust,
revocation, installation, deployment confirmation, and activation are distinct durable
states and causal audit events.

The implementation follows only GitHub's official artifact-attestation documentation and
GitHub CLI manual. Provenance records exact URLs, the `2026-09-09` check date, and the
observed basis. Public tests use deterministic synthetic/offline fixtures and never claim
live GitHub compatibility or create/publish an artifact.

## Package lifecycle, upgrade, rollback, and revocation

- Inspection and validation are non-mutating. Registration creates an inert untrusted,
  uninstalled exact version.
- Only a current `tenant_admin` HUMAN may trust, revoke, install, confirm, or mutate a
  deployment lifecycle. Callers never submit tenant, namespace, authoritative role,
  principal kind, actor, time, or audit authority.
- Installation requires exact current trust and remains inert. Install never creates a
  deployment or activates runtime.
- Revocation is durable and terminal for that trust revision. It does not impersonate a
  human approval or rebuild authority. Existing active deployments bound to the revoked
  digest become safely `blocked` with causal audit; no effect or replacement authority is
  created.
- Upgrade always creates a new inert draft bound to a different trusted, installed exact
  version/digest. It displays package content, workflow, requested-capability, current
  Mandate-capability, and exact Profile/Mandate/Policy binding differences. It does not
  modify the deployment until separate review and exact confirmation; confirmation leaves
  the upgraded deployment in `draft`, requiring a distinct activation.
- Rollback can target only an exact version/digest already present in that deployment's
  accepted binding history and still trusted and installed. It follows the same draft,
  review, confirmation, and separate activation sequence.
- Unknown, untrusted, revoked, uninstalled, digest-mismatched, stale, replay-rebound, or
  cross-tenant versions cannot be installed, confirmed, activated, upgraded, or rolled
  back. Destructive database down migration is unsupported; database rollback uses a
  verified backup with matching code.

Every mutation re-resolves current server-side membership, uses the exact namespace,
binds expected optimistic revisions and exact digests, has a stable idempotency key with
request-digest replay defense, and writes immutable causal audit in the same SQLite
transaction as its effect or refusal.

## ColleagueDeployment registry and ten-active limit

A ColleagueDeployment has a complete colleague namespace and binds one exact package ID,
version, and digest. It owns independent Profile, Mandate, Policy, lifecycle, work,
budgets, effects, approvals, audit causality, MODEL/SERVICE principals, and a null reserved
future connection/grant slot. P11 implements no connector lifecycle.

Lifecycle values are exactly `draft`, `active`, `paused`, `blocked`, and `retired`.
Allowed transitions are:

```text
draft -> active | retired
active -> paused | blocked | retired
paused -> active | blocked | retired
blocked -> paused | retired
retired -> no transition
```

Package revocation is the sole system safety transition and changes `active` to `blocked`.
All other transitions require exact Admin confirmation. Draft, paused, blocked, and
retired deployments do not count toward the active-host limit and cannot be processed by
the worker or runtime API. Only `active` counts. On execution host `local`, the tenth
active deployment succeeds and the eleventh returns the stable audited refusal
`active_deployment_limit_reached`. SQLite `BEGIN IMMEDIATE`, optimistic revision checks,
and database triggers serialize concurrent activation so a race cannot exceed ten.
Restart preserves registry rows, counts, package binding, lifecycle, and audit.

Catalog, registry, exact selection/switching, lifecycle state, package binding, limit
result, permission differences, and causal audit are inspectable. Multiple deployments
do not establish Agent collaboration, delegation, messaging, shared knowledge, shared
memory, or cross-Agent authority. Store, service, API, session selection, work, effect,
approval, and audit reads/writes require the exact deployment namespace; cross-tenant and
cross-Agent access is default deny.

## Legacy/manual preservation and migration 008

Migration 008 is required and is the sole new migration. It is additive and creates only
P11 package, trust, deployment-draft, deployment, accepted-binding-history, operation
replay, and causal-audit tables plus active-limit triggers and indexes. It does not alter
or delete an existing table, column, row, causal ID, audit row, or migration record.

For each pre-existing colleague Profile namespace, migration 008 deterministically creates
one active `legacy/manual` ColleagueDeployment and one fixed inert official built-in
compatibility package binding. The binding is a migration-preserved state, not a new Admin
trust decision and not authority. Existing Profile, Mandate, optional Policy, principals,
work, approvals, effects, replay, and audit remain in their original tables and retain
their exact IDs, bytes, revisions, actors, and causality. A missing legacy Policy remains
explicitly `legacy_unconfirmed`; none is synthesized. No capability, role, membership,
approval, effect boundary, or authority is reconstructed or expanded.

Fresh install, upgrades from representative P7/P8/P10 schema-7 databases, restart,
failure atomicity, applied-migration identity, idempotent repeated open, legacy record
identity, and schema version 8 are tested. A legacy count that would violate ten active
deployments aborts migration. Migration failure leaves schema version 7 and all prior data
intact. Rollback requires a verified schema-7 backup with matching code and never runs a
down migration.

## Stable API, CLI, Studio, and compatibility

New public routes use stable `/api/v1` vocabulary only:

```text
GET  /api/v1/catalog
GET  /api/v1/agent-packages
POST /api/v1/agent-packages
POST /api/v1/agent-packages/validate
POST /api/v1/agent-packages/{package_id}/versions/{version}/{digest}/trust
POST /api/v1/agent-packages/{package_id}/versions/{version}/{digest}/revoke
POST /api/v1/agent-packages/{package_id}/versions/{version}/{digest}/install
GET  /api/v1/deployment-drafts
POST /api/v1/deployment-drafts
POST /api/v1/deployment-drafts/{draft_id}/review
POST /api/v1/deployment-drafts/{draft_id}/confirm
GET  /api/v1/deployments
POST /api/v1/deployments/{deployment_id}/lifecycle
POST /api/v1/deployments/{deployment_id}/upgrade-drafts
POST /api/v1/deployments/{deployment_id}/rollback-drafts
POST /api/v1/deployments/{deployment_id}/select
GET  /api/v1/deployments/{deployment_id}/audit
```

HTTP Pydantic models exist only at the API edge and forbid extra fields. Mutation requests
require session cookie, exact Origin, CSRF, idempotency, expected revision where relevant,
server-side authorization, and sanitized finite errors. `/p5`, `/p6`, and every existing
route/method/schema remain compatible; no alias is removed.

The installed Python console entry point is named `dc`. It supports local package
inspection/validation and authenticated Catalog, trust/revoke/install, deployment draft,
review/confirm, lifecycle, upgrade/rollback, selection, limit, and audit operations.
Credentials and CSRF are read only from a bounded stdin authentication envelope, never
from arguments/environment/output. CLI output is stable JSON, bounded, path-free on
errors, and never supplies tenant, role, kind, actor, or time as authority.

Studio adds a Catalog and deployment registry using the existing translation-key
architecture. It displays validation failures, provenance/attestation, requested
capabilities and permission differences, explicit trust/revoke/install, draft review,
exact confirmation, activate/pause/block/retire, upgrade/rollback, safe deployment
selection, ten-active-limit refusal, and causal audit. `zh-TW` and `en-US` key sets and
placeholders are exactly equal. Missing/blank/mismatched translations fail the gate and
cannot change permission semantics. Controls have labels, keyboard operation, visible
focus, disabled/busy state, and `aria-live` error/result announcements.

The default source Compose topology builds the P11 code, applies migration 008, exercises
authenticated package/deployment operations, restarts API and worker, verifies persistence
and active-lifecycle enforcement, and then removes its unique containers, network, volume,
database, and build residue. P10 digest-bound distribution evidence is retained and is not
republished or selected as P11 runtime evidence.

## Architecture and forbidden capability boundary

Dependency direction remains pure core to application/governance and stable ports, then
infrastructure/HTTP adapters. Core uses frozen standard-library dataclasses, enums, and
protocols and imports no FastAPI, Pydantic, ORM, database driver, provider/channel SDK, or
orchestration framework. Pydantic remains at the HTTP edge. Stores stay behind ports.
Time, identifiers, configuration, process execution, temporary storage, and I/O are
injected. Persisted records include schema version and complete namespace. IDs are strings;
timestamps are timezone-aware UTC and serialize with `Z`.

P11 adds no OpenAI/model-provider integration; OAuth, Graph, Outlook, Teams, Planner, or
SharePoint connector; ExternalConnection or ConnectorGrant lifecycle; automatic effect
authorization; built-in project tracker; Semantic Memory, embedding, or learning;
executable Skill/plugin/browser/computer/shell runtime; Agent-to-Agent collaboration,
delegation, messaging, or shared knowledge; always-on/72-hour soak; production tenancy,
HA, enterprise IAM, compliance, security certification, or production-readiness claim;
or tag, Release, GHCR publication, signature/attestation publication, or v0.2 release.

## Provenance, evidence classes, and claim exclusions

`provenance/p11-migration-receipt.json` covers every changed implementation path except
the final summary, records its implementation basis and classification, records that the
parent research working tree was not read, and fixes source/transformed migration counts
at zero. It records official GitHub documentation URL, check date, and observed contract,
external dependency/license treatment, and absence of local absolute paths, credentials,
private identifiers, personal data, and live receipts.

P11 public evidence classes are exactly `static`, `synthetic_offline`, `local_runtime`,
and `not_evaluated`. Synthetic/offline GitHub fixtures are not live GitHub evidence.
OpenAI, Microsoft 365, named-provider compatibility, human evaluation, always-on behavior,
production security/privacy/readiness, HA, enterprise IAM, compliance, Agent collaboration,
Semantic Memory, Skill runtime, formal release/public pilot, and P12 are excluded.

The sole evidence claim is `p11_agent_package_multi_agent_lifecycle_candidate`; status is
`development_complete_awaiting_independent_acceptance`. Evidence never says P11 was
accepted or merged.

## Repeatable gates and test floor

Direct commands are:

```bash
git status --short --branch
git diff --check
python3 -B scripts/check_public_boundary.py .
python3 -B scripts/check_p11_repository.py .
python3 -B scripts/check_p11_provenance.py .
python3 -B scripts/check_p11_architecture.py .
python3 -B scripts/check_p11_migrations.py .
python3 -B scripts/check_p11_compatibility.py .
python3 -B scripts/check_p11_studio.py .
PYTHONPATH=src python3 -B -m unittest discover -s tests/p11 -t . -v
make p11-test
make p11-check
make check
```

`make p11-test` runs at least 40 named P11 tests. `make p11-check` materializes the exact
P10 Git object in an OS temporary clone, checks it out under its contract-required
`codex/p10-mac-quickstart` branch, runs its retained complete `make check`, then runs P11
Python lint/format/type, Studio lint/format/type/test/build, repository/provenance/
architecture/migration/compatibility/Studio/package/security/abuse tests, public-boundary,
diff, and actual source-Compose restart/cleanup gates. `make check` is the same P11
aggregate gate. The retained P10 repository/evidence checker is never run directly on the
P11 branch.

Tests cover valid/invalid schema, canonical serialization and digests, locale parity,
archive traversal/link/special/bomb/collision/code defenses, workflow bounds/cycles,
unknown fields/capabilities/versions, inspect/validate/register/trust/revoke/install,
GitHub verification successes and failures, attestation-not-trust, install-not-activation,
self-grant/self-activation, stale/replay/concurrency, upgrade draft and permission diff,
trusted rollback and revoked/stale refusal, legacy preservation, fresh/upgrade/restart/
failure/idempotency migration, tenth-active success and eleventh refusal, concurrent
activation, cross-tenant/cross-Agent denial, RBAC/namespace/CSRF/audit, API compatibility,
CLI secrecy, Studio i18n/lifecycle/error/accessibility, actual Compose persistence,
public-boundary/private-data scans, zero cleanup residue, P0-P10 and migrations 001-007
identity, and absence of P12+/S1-S4/production claims.

Every gate has positive counts and exactly zero failures, errors, skips, expected failures,
unexpected successes, historical drift, migration-prefix drift, secret/private/path leaks,
unexpected egress, and cleanup residue. `skip`, `xfail`, mock-only substitution for the
actual local/Compose path, lowered thresholds, and fabricated evidence are forbidden.
External attestation tests remain honestly deterministic `synthetic_offline`.

## Evidence writer preconditions and final commit

`make evidence-p11` may run only when the acceptance contract has its isolated immutable
commit; all implementation paths are committed in later commit(s); branch, ancestry,
history, migration prefix, index, tracked worktree, and untracked set are exact and clean;
all direct and aggregate gates exit zero with no skip; actual Compose passes and cleans up;
and no forbidden capability or private material exists.

The writer may create only `artifacts/p11/summary.json`. It records exact base,
merge-base, branch, acceptance and implementation commit(s), tree digest, all 59 paths,
migration 008 and 001-007 identity, tests and gate exit classes, package/workflow/archive
bounds, trust/attestation/lifecycle results, legacy and ten-active results, compatibility,
actual Compose persistence and zero residue, provenance, evidence classes, claim, status,
and exclusions. The file is committed alone as the final commit. Then complete
`make p11-check` and `make check` run again and the branch must be clean.

## Stop conditions and final wording

Stop without cleanup, stash, reset, revert, rebase, force, contract modification, or scope
absorption if baseline/branch/ancestry/cleanliness fails; this contract needs expansion or
weakening; an unlisted path is required; P0-P10 history or migrations 001-007 drift;
credential/login/remote write is needed; P12+/S1-S4 capability is needed; a gate requires
skip/mock substitution/weaker criteria/fabrication; non-executable bounded fail-closed
package behavior cannot be proven; legacy authority cannot be preserved; the ten-active
limit or namespace isolation cannot be reliable; official documentation conflicts with
this contract; private material would enter the public tree; or push/merge/tag/Release/
publication is required.

After all authorized work and gates pass, the exact conclusion is:

**P11 implementation candidate complete; awaiting independent acceptance.**

