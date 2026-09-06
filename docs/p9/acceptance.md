<!-- SPDX-License-Identifier: Apache-2.0 -->

# P9 Productization Rebaseline Acceptance Contract

Status: fixed development contract. P9 may be described only as **development complete,
awaiting independent acceptance** after every gate below passes. It may not be described as
accepted, merged, released, published, production-ready, or live-provider validated. This
contract is fixed before all other P9 implementation, committed alone, and must not be
modified, amended, deleted, or rewritten to fit later results.

## Exact baseline, branch, and ancestry

- Exact P9 base: `b093a4fa54bf30cef838c72222d1ae63c4eab9d9`.
- Required accepted P8 ancestor: `0bb80ab187932fbad42fbf665b8310987609a1f5`.
- Exact development branch: `codex/p9-productization-rebaseline`.
- P9 begins only when the base is a clean `main` checkout, the accepted P8 commit is an
  ancestor, migrations contain only 001-007 plus `manifest.json`, the retained P8
  repository/provenance/public-boundary gates pass, and no prior P9 or v0.2 work exists.
- The acceptance-contract commit must be the first P9 commit and contain only this file.
  Its complete SHA becomes `P9_ACCEPTANCE_COMMIT`. All later P9 commits must descend from
  it, and this file must remain byte-identical to that Git object.

## Historical immutable boundary

P0-P8 accepted history is immutable. This includes every file under `docs/p0` through
`docs/p8`, `artifacts/p0` through `artifacts/p8`, and all P0-P8 evidence directories;
all P0-P8 acceptance records, summaries, receipts, fingerprints, and provenance records;
the source allowlist and rights confirmation; and migrations 001-007 with
`migrations/manifest.json`. P9 does not invoke or rebuild evidence P0-P8, read or migrate
the parent working tree, or reinterpret historical evidence classifications.

Migration 008 must be absent. P9 changes no runtime schema or runtime data. Existing
`0.1.0` data, colleague, Profile, Mandate, Policy, work, approval, and audit records remain
the future compatibility baseline.

## Exact P9 changed-file scope

The complete base-to-candidate path set must equal the following allowlist. Missing,
additional, renamed, copied, type-changed, staged, unstaged, untracked, traversing,
symlinked, or special-file paths fail closed.

```text
AGENTS.md
Makefile
README.md
SECURITY.md
artifacts/p9/summary.json
docs/adr/0007-declarative-agent-package-and-deployment-model.md
docs/adr/0008-external-identity-connections-and-automatic-authorization.md
docs/architecture/target-architecture.md
docs/development.md
docs/p9/acceptance.md
docs/p9/rebaseline-checklist.md
docs/product/capability-matrix.md
docs/product/post-v0.1-capability-outlook.md
docs/product/v0.2-external-dependency-register.md
docs/product/v0.2-public-pilot-capability-matrix.md
docs/product/v0.2-public-pilot-product-brief.md
docs/roadmap.md
docs/security/privacy-boundary.md
docs/security/threat-model.md
docs/security/v0.2-public-pilot-privacy-boundary.md
docs/security/v0.2-public-pilot-threat-model.md
provenance/p9-migration-receipt.json
scripts/check_p8_provenance.py
scripts/check_p8_repository.py
scripts/check_p9_provenance.py
scripts/check_p9_rebaseline.py
scripts/check_p9_repository.py
scripts/collect_p9_evidence.py
scripts/run_p9_toolchain.py
tests/p8/test_repository.py
tests/p9/__init__.py
tests/p9/fixtures.py
tests/p9/test_evidence_gate.py
tests/p9/test_rebaseline.py
tests/p9/test_repository.py
```

Only documentation, ADRs, acceptance/checklist material, governance gates, tests,
provenance, and synthetic/static evidence are allowed. The P8 gate continuation is limited
to `scripts/check_p8_repository.py`, `scripts/check_p8_provenance.py`, and
`tests/p8/test_repository.py`.

P9 must not change `src/digital_colleagues/**`, `studio/**`, Compose files, Dockerfiles,
requirements, locks, dependency inventory, `pyproject.toml`, `studio/package.json`, API
routes or FastAPI metadata, workers, schedulers, adapters, operations code, SQLite schema,
or migration files. It must not add package parsing/install, Catalog UI, multi-Agent
lifecycle, provider calls, OAuth/token storage, connectors, automatic-effect runtime,
executable Skills/plugins, Semantic Memory, Agent collaboration, GHCR images, distribution
CLI behavior, or release/publication automation.

## Product and maturity decision

P9 rebaselines planning toward **v0.2 Public Pilot**, not production-ready 1.0. The only
executable product remains the unpublished `0.1.0` local reference candidate. P9 changes
no Python, Studio, or runtime version and delivers no new runtime capability.

The v0.2 target supports Mac local and Linux/Mac mini always-on Docker profiles, with these
unverified targets: Studio starts within five minutes on a Mac with Docker Desktop and a
downloaded release; the first interactive Agent is deployed within fifteen minutes when
an OpenAI key, Entra App ID, and Microsoft 365 Agent account are ready; and one host
supports no more than ten active Agents. A sleeping or powered-off MacBook does not run a
purely local Agent. Studio is the Admin control plane; managers and colleagues primarily
interact through Outlook, Teams, and Planner.

P9-P15 do not claim high availability, enterprise IAM, production tenancy, large-scale
multi-tenancy, compliance certification, production security, or production readiness.

## Normative v0.2 concepts

- **AgentPackage** is a non-executable, versioned, digest-bound declarative blueprint. It
  may contain schema-valid metadata, localized `zh-TW` and `en-US` display text, prompts,
  bounded workflow declarations, and requested capabilities.
- **ColleagueDeployment** is a namespaced digital-colleague instance created from one exact
  AgentPackage version and digest. It has its own Profile, Mandate, Policy, lifecycle, and
  external bindings.
- **ExternalConnection** is a managed credential connection to one external
  provider/application/account. It does not authorize any resource or action by itself.
- **ConnectorGrant** is an Admin-created, revisioned, resource/action-specific governance
  binding. It limits an ExternalConnection to the current Mandate and Policy.
- **AutomaticEffectAuthorization** is a durable authorization record for an effect proven
  to satisfy the exact low-risk policy, Mandate, Policy, ConnectorGrant, source/data
  versions, and budget.
- **SourceReference** and **SourceCursor** are safe connector reference and cursor concepts.
  They are neither retained full source bodies nor Semantic Memory.

AgentPackage is not an S4 Skill. It cannot contain or trigger Python, Node, shell, binary,
browser automation, arbitrary plugin code, dynamic import, `eval`, `exec`, or unbounded
loops. A package can request capabilities only; it cannot authorize, install, activate, or
expand itself, a Mandate, Policy, ExternalConnection, ConnectorGrant, or approval state.

Package sources are limited to official built-ins, local development packages, and GitHub
Release artifacts with valid GitHub artifact attestation. Attestation binds artifact digest
to source/build identity; it is not a security verdict. Before install, the Admin sees the
signer, repository, workflow, digest, requested capabilities, permission diff, and explicit
trust decision. An update creates a new draft and never auto-applies. Rollback selects an
accepted, still-trusted exact version; stale or revoked versions are refused.

External source bodies from Outlook, Teams, Planner, or SharePoint are temporary context
for one evaluation. They do not create Semantic Memory, embeddings, long-term synthesized
facts, or a learning loop. Multiple ColleagueDeployments on a host do not create S3 shared
knowledge, cross-Agent access, delegation, messaging, collaboration, or shared memory.
Each Agent's namespace, work, credentials, connections, grants, budgets, effects, and audit
remain isolated. Cross-Agent access and Agent loops are denied by default.

## OpenAI planning boundary

The first planned model provider is the OpenAI API and the fixed initial candidate model is
`gpt-5.5`. P9 records only official static documentation and makes no OpenAI call. P12 must
recheck official documentation and actual project access before development and every live
acceptance. If the model is unavailable or incompatible, work stops for a Change Decision;
the model is not silently replaced.

P12 is planned to use the Responses API, Structured Outputs, and explicit `store:false`.
No function tools, hosted tools, MCP, browser/computer use, shell, connector credentials,
or direct execution authority are exposed to OpenAI. The model returns only a bounded,
schema-constrained semantic decision. Server code reconstructs and validates every
authoritative field. The model cannot change a Mandate, Policy, Connection, Grant, human
role, or approval. P12 must cover bounded input/output, usage/cost budgets, timeout/retry,
refusal/incomplete/schema errors, prompt layering, prompt-injection refusal, and model
provenance.

## Microsoft 365 planning boundary

Each Agent uses one dedicated Microsoft 365 work/school account. The two planned App modes
are a project-operated verified multi-tenant public client and an enterprise-provided
single-tenant public client App ID. Authentication uses delegated OAuth device-code
public-client flow and records ordinary user consent, Admin pre-consent, and selected-
resource configuration separately.

Outlook uses a per-folder mail delta cursor. Teams has no public webhook or cloud relay; it
polls only Admin-allowlisted chats using a bounded date window and deduplicates message ID
and etag. Planner is read/write and sends the latest ETag through `If-Match`; 409, 412, or a
stale ETag causes reread and reevaluation, never overwrite. SharePoint is read-only and
limited to a selected site/folder; unbound or out-of-selection resources are refused.

Later gates test Graph 401/403/429/5xx, refresh/revocation, throttling, ambiguous sends,
bounded retry, reconciliation, and restart cursors. Mock, stub, and loopback evidence cannot
be named Microsoft 365 compatibility.

## Automatic-effect decision table

Automatic execution is eligible only for a routine reply in an existing internal email
thread or existing allowlisted Teams chat when all original participants are unchanged,
the scope is same-tenant, and there is no attachment or new mention; or for a Planner
action whose plan, task, fields, assignee, data version, Mandate, Policy, and ConnectorGrant
all match exactly.

Approval is required for a new recipient, new chat, external domain, attachment, new
mention, cross-tenant message, or any effect with ambiguous authority, binding, version, or
risk. An effect is denied or fails closed when it exceeds Mandate, Policy, or ConnectorGrant;
uses stale data, ETag, or revision; uses a revoked/expired connection; exceeds a budget or
rate limit; crosses Agent or tenant boundaries; attempts capability self-grant; or cannot
prove the automatic boundary.

AutomaticEffectAuthorization and HumanApprovalDecision are different durable records with
different authoring rules and audit semantics. MODEL and SERVICE principals never author a
HumanApprovalDecision. The built-in project tracker does not request `delete_task` by
default; any third-party package requesting deletion must display it separately and
prominently. Later designs prevent self-reply, Agent-to-Agent loops, duplicate messages,
duplicate effects, replay, and notification flooding.

## Security, privacy, and language contracts

Mac live mode checks FileVault. Secret directories use mode `0700`; credential files use
mode `0600`; necessary services receive secrets only through read-only file mounts. Keys
and tokens must not enter environment variables, SQLite, audit, backups, diagnostics,
logs, errors, command arguments, or public evidence. Always-on Linux requires an
operator-provided encrypted volume. If storage encryption cannot be proven, live readiness
is `not_evaluated` or live mode is blocked.

The public tree contains no real account, tenant, endpoint, message/document content,
provider receipt, live acceptance, personal data, or credential. Durable connector state
normally contains SourceReference, etag, digest, cursor, safe projection, and causal record,
not full email, Teams message, or SharePoint document bodies. Future temporary source
processing must define bounded size, redaction, discard timing, and crash cleanup.

`zh-TW` and `en-US` are the first v0.2 product languages beginning in P10. P9 defines only
the i18n contract. Localized metadata and prompts never alter capability, authority, schema,
permission meaning, or fail-closed defaults. A missing translation cannot broaden access.

## Ordered P9-P15 contract

The roadmap must retain complete accepted P0-P8 history and add these non-mergeable,
non-skippable phases in exact order:

1. **P9 — Productization Rebaseline:** documents, ADRs, acceptance contracts, governance
   gates, tests, and evidence only; no product capability.
2. **P10 — Mac Quickstart and Distribution:** prebuilt signed/attested multi-architecture
   GHCR images; `dc` doctor/quickstart/up/down/status/backup/restore/update/uninstall;
   Application Support, FileVault, secret boundary, i18n foundation, product metadata, and
   deterministic five-minute quickstart. No AgentPackage lifecycle, OpenAI gateway, or
   Microsoft 365 connectors.
3. **P11 — Agent Package and Multi-Agent Lifecycle:** `dc-agent/v1`, package
   inspect/validate/install/upgrade/rollback/trust/revoke, GitHub attestation, Catalog,
   deployment registry, ten active Agents, bounded declarative workflows, and legacy v0.1
   deployment migration. Migration 008 may first appear here only if schema work requires
   it; migrations 001-007 remain immutable.
4. **P12 — OpenAI Model Gateway:** Responses API, Structured Outputs, `store:false`, budget,
   connection lifecycle, prompt layering, and private live acceptance; no execution tools
   or connectors.
5. **P13 — Microsoft 365 Connector Foundation:** per-Agent delegated identity,
   project/BYO App modes, consent, Outlook delta, Teams polling, Planner ETag, SharePoint
   selected read-only access, and connection/grant lifecycle.
6. **P14 — Built-in Project Tracker:** bilingual official `project-tracker` package,
   setup/deploy/health/timeline/usage/audit UI, and `auto_within_boundary`,
   `require_approval`, `deny`; no Semantic Memory or Agent collaboration.
7. **P15 — Always-on and Public Pilot Release:** Mac local and Linux/Mac mini always-on
   profiles, SSH-tunneled Studio, ten-Agent 72-hour soak, live OpenAI/Microsoft 365/human
   evaluation, and release artifacts/SBOM/checksums/attestations. Tag, push, publish, upload,
   or Release creation requires final live acceptance plus separate user authorization.

Every phase follows: development complete, independent acceptance, scoped correction,
final acceptance, fast-forward merge, main verification, and only then planning for the
next phase. Passing P9 does not authorize P10.

## Compatibility and interface transition inventory

P9 documents but does not edit these current residues:

- `studio/src/App.tsx` contains P6 local-governance/control-plane and under-verification
  copy. P10 owns user-visible milestone-brand removal and translation keys.
- `src/digital_colleagues/local/runtime.py` sets the composed FastAPI title to P7 optional
  adapters and version to `0.0.0-p7`. P10 owns product metadata correction.
- `src/digital_colleagues/api/app.py` and `p4_app.py` contain P3/P4 milestone-shaped
  FastAPI metadata. P10 owns the product-facing metadata transition.
- Current `/p5` and `/p6` route naming is a compatibility surface, not new product API
  vocabulary. Existing routes remain until a separate alias/deprecation/removal contract.
  New v0.2 public APIs use stable product language under `/api/v1`; P11+ public schemas and
  APIs do not use milestone names.

P11 converts the existing single colleague to a legacy/manual ColleagueDeployment without
deleting or silently reconstructing authority. Package upgrade always creates a new draft.
Connector revocation invalidates related grants and pending effects. Database rollback uses
a verified backup with matching code, never a destructive down migration.

## Planned data flows and fail-closed rule

The package flow is:

```text
Package source -> bounded download/local selection -> digest
-> provenance/attestation verification -> archive/content safety validation
-> requested-capability inspection -> Admin trust decision -> inert installed package
-> reviewed deployment draft -> exact Mandate/Policy/ConnectorGrant binding
-> confirmed ColleagueDeployment
```

The external-event flow is:

```text
External event -> ExternalConnection authentication -> ConnectorGrant resource check
-> bounded source fetch -> temporary source context
-> SourceReference/cursor/digest/safe projection -> existing Event/Agenda/Wake/Decision path
-> exact EffectProposal -> automatic-policy evaluation or Human approval
-> dispatch-time revalidation -> effect attempt/result/reconciliation -> causal audit
```

Package content, provider output, localized prompts, external message/document content, and
UI state are untrusted data, never authority. Unknown, missing, stale, revoked,
cross-namespace, cross-Agent, digest-mismatched, schema-mismatched, unbound-resource,
ambiguous-authority, or over-budget input fails closed.

## Evidence classes and live prerequisites

New P9-P15 evidence uses only `static`, `synthetic_offline`, `loopback`, `live_private`,
`human_evaluation`, and `not_evaluated`. Lower evidence never substitutes for a higher
class. P9-P14 may use static, synthetic_offline, and explicitly labeled loopback evidence.
Without actual OpenAI project access, P12 live acceptance is `not_evaluated`. Without real
Microsoft 365 tenants, P13 named-provider compatibility is `not_evaluated`. P15 live gates
cannot use a mock, stub, or loopback substitute.

P15 minimum private live prerequisites are exactly:

- two Microsoft 365 test tenants;
- ten dedicated Agent test accounts;
- one usable OpenAI test project;
- one verified project multi-tenant Entra public-client App;
- one BYO single-tenant App;
- delegated user-consent and Admin-consent test capability;
- real Outlook, Teams, Planner, and SharePoint test data; and
- private live-acceptance storage outside the public tree.

No person is asked to paste a credential into a conversation or repository.

## Required negative and abuse coverage

Tests must reject wrong base or missing P8 ancestry; wrong evidence branch; dirty staged,
unstaged, or untracked state; historical acceptance/artifact/receipt/migration drift;
migration 008; runtime, Studio, Compose, Docker, dependency, lock, or version changes;
incomplete or extra P9 paths; rename/copy/traversal/symlink/special-file bypass; local
absolute paths, credential shapes, private markers, or live identifiers; reordered,
merged, or missing P10-P15 phases; unsupported production/HA/enterprise-IAM/compliance
claims; mock/loopback promoted to `live_private`; executable AgentPackage or S4 Skill
conflation; capability self-grant or self-activation; source context represented as
persistent memory; multiple deployments represented as collaboration/shared knowledge;
AutomaticEffectAuthorization represented as HumanApprovalDecision; missing FileVault,
0700/0600/read-only-mount or no-environment/no-SQLite secret rules; incomplete P15 live
prerequisites; nonofficial external documentation; silent replacement of `gpt-5.5`;
acceptance-contract mutation after its commit; and evidence generation after any failure,
skip, dirty state, wrong branch, or uncommitted implementation.

The healthy candidate must pass with positive test counts and exactly zero failures,
errors, skips, expected failures, unexpected successes, public-boundary exceptions,
historical drift, product/runtime implementation changes, and cleanup residue.

## Repeatable gates

```bash
git status --short --branch
git diff --check
python3 -B scripts/check_public_boundary.py .
python3 -B scripts/check_p8_repository.py .
python3 -B scripts/check_p8_provenance.py .
python3 -B scripts/check_p9_repository.py .
python3 -B scripts/check_p9_provenance.py .
python3 -B scripts/check_p9_rebaseline.py .
PYTHONPATH=src python3 -B -m unittest discover -s tests/p9 -t . -v
make p9-check
make check
```

The repository hash-locked temporary toolchain runs the complete retained P8 regression
before P9 gates. No evidence P0-P8 writer is executed.

## Evidence-writer preconditions

`make evidence-p9` may run only when this contract has its isolated immutable commit; the
implementation has a later commit; HEAD is that committed implementation; branch and base
are exact; index/worktree are clean; every direct and aggregate gate passes with no skip;
P0-P8 bytes and migrations 001-007 are unchanged; migration 008 is absent; product/runtime
change and cleanup counts are zero; and OpenAI live, Microsoft 365 live, and human
evaluation are honestly `not_evaluated`.

`artifacts/p9/summary.json` is schema-versioned and records exact base, acceptance commit,
implementation commit, branch, static/synthetic_offline gates, and the three
`not_evaluated` live/human statuses. Its only claim is
`p9_productization_rebaseline_candidate`; its status is
`development_complete_awaiting_independent_acceptance`; it explicitly excludes runtime
implementation, release, production, and live claims. It contains no local path,
credential, account, tenant, private data, provider identifier, or live receipt. The
summary is committed alone and all final gates rerun.

## Stop conditions and claim boundary

Stop and request a Change Decision if this contract conflicts with necessary work or if
current official documentation contradicts a fixed model, API, OAuth, polling, ETag,
selected-resource, or attestation decision. The decision record must name the fixed
decision, official evidence, affected phases, security/privacy/API/schema/test impacts,
and recommendation. Do not silently change provider, model, OAuth flow, webhook/relay, or
permission mode.

Stop without cleanup, stash, reset, revert, or absorption if the exact baseline or branch
preconditions fail, historical drift appears, a forbidden path is required, a gate cannot
pass within P9 scope, or private/live material is detected.

Successful development supports only: **P9 development complete, awaiting independent
acceptance** and **P9 Productization Rebaseline candidate**. It does not establish P9
acceptance, v0.2 implementation, release/publication, live OpenAI or Microsoft 365
compatibility, human evaluation, production readiness/security/privacy, high availability,
enterprise IAM, production tenancy, compliance, or any P10-P15 capability. Development
must stop on the P9 branch with a clean tree; it must not merge, push, tag, publish, upload,
create a Release, or begin P10-P15.
