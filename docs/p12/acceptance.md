<!-- SPDX-License-Identifier: Apache-2.0 -->

# P12 Public Pilot Continuity Rebaseline Acceptance Contract

Status: replacement acceptance contract. This file is the complete, self-contained Change
Decision and immutable acceptance contract for the B+ Public Pilot continuity rebaseline.
It does not depend on a conversation record. If independently authorized, it is committed
alone as the first commit on the replacement P12 branch, with the exact accepted main
commit as its sole parent, and must thereafter remain byte-identical to that Git object.

This acceptance-contract commit authorizes no P12 governance implementation, correction,
evidence generation, push, pull request, merge, tag, GitHub Release, package or image
publication, signature, attestation, P13 work, or later milestone work. Every later
authorization named in this contract is independent and must be explicit.

## Normative language and claim vocabulary

The words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, and MAY are
normative. A condition that cannot be established exactly fails closed.

Evidence states are:

- passed: the fixed repeatable gate ran successfully against the identified object;
- failed: the gate ran and did not satisfy the contract;
- blocked: an exact prerequisite failed or is missing, so the gate did not proceed and no
  positive claim is permitted;
- not_evaluated: required access, environment, consent, or authorized evidence execution
  was unavailable, so no positive claim is permitted; and
- not_applicable: the contract explicitly makes the check inapplicable and records why.

Skipped, unavailable, inferred, partially observed, captured from another commit, or
manually asserted results are never passed. Static and synthetic evidence cannot establish
a live-provider, human-evaluation, reliability, security, privacy, production, or Public
Pilot claim.

## Rejected local-only acceptance attempt

The following exact object is a rejected local-only acceptance attempt and is not accepted
history:

| Field | Exact value |
| --- | --- |
| Local branch | codex/p12-public-pilot-continuity-rebaseline |
| Commit | 8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3 |
| Tree | 557a74e9174247483362bbbd15cd265113775d12 |
| Sole parent | c1562ea5201394d8a278f4b644daf4029cbb5bd4 |
| Acceptance path | docs/p12/acceptance.md |
| Acceptance blob | 26562d795980ec8d6d9ea36ff3fcc718b41c09e8 |
| Remote branch and pull request | absent at rejection |
| Implementation, evidence, merge, tag, Release, publication | none |

Its Git-form checks passed, but its content was rejected because it changed the approved
ProjectContinuationState vocabulary, conflated semantic-memory admission with
post-admission lifecycle, omitted the approved P14 Microsoft effect transports, and
drifted from the approved core-record contracts. It grants no implementation, correction,
evidence, remote-mutation, merge, release, publication, or later-milestone authority.

The rejected commit MUST NOT be an ancestor of this replacement contract. No
implementation commit, correction, CI result, evidence receipt, summary, acceptance or
publication may bind to it. Its local branch ref remains fixed at the exact rejected commit
and MUST NOT be amended, rebased, reset, moved or deleted without a separate project-owner
authorization.

## Change Decision

### Context

The accepted baseline is main commit
c1562ea5201394d8a278f4b644daf4029cbb5bd4 with tree
ae0f33263cfc7445fef69656ad9c5cb04d4a2d00. It includes the accepted local-first v0.1
control plane, the P9 productization planning boundary, the protected P10 Mac distribution,
the P11 declarative AgentPackage and deployment lifecycle, and the P11R current-CI
alignment. P11R main CI run 34451912586 passed current-ci and the bounded Compose smoke.
There are zero local tags, zero remote tags, and zero GitHub Releases at the P12 base.

The baseline already has explicit human, model, and service principal separation; revisioned
Mandate and Policy; finite work; durable events, timers, agendas, wake cycles, effect
proposals, human approval, action results, reconciliation, leases, fencing, optimistic
concurrency, replay protection, causal audit, a namespaced local SQLite store, a typed HTTP
edge, Studio, local governance, optional provider-neutral adapters, backup and restore,
P10 distribution, and P11 package and deployment governance.

It does not yet implement an OpenAI gateway, Microsoft 365 connection and source
foundations, durable project continuation, semantic memory, autonomous provider polling,
recurring schedules and heartbeats, raw-event correlation, startup recovery scanning,
bounded goal-driven proactivity, the Public Pilot project tracker, or a Public Pilot
release. Existing timers and restart behavior do not by themselves satisfy these future
contracts. Existing temporary provider context is not semantic memory. Multiple
ColleagueDeployments are not Agent collaboration.

The former P12 through P15 plan grouped provider, connector, automatic-effect, tracker, and
release work too early and did not provide independent gates for continuation, memory,
trigger recovery, and proactivity. The shared migration parser also needs a correction
before another migration is introduced.

### Decision

Adopt the B+ sequence, in this exact non-skippable order:

1. P12 — Public Pilot Continuity Rebaseline, governance only.
2. P13 — OpenAI Model Gateway, preceded by the parser-first correction gate.
3. P14 — Microsoft 365 Connector Foundation and explicit synchronization.
4. P15 — Durable Project Continuation.
5. P16 — Semantic Memory Lifecycle.
6. P17 — Trigger, Recurring Schedule, Heartbeat, Correlation, and Recovery.
7. P18 — Bounded Goal-driven Proactivity.
8. P19 — Built-in Public Pilot Project Tracker.
9. P20 — Always-on Public Pilot Release and private-live acceptance.

Continuation, Semantic Memory, Trigger and Recovery, and Proactivity remain four separate
gates at P15, P16, P17, and P18. Passing any phase authorizes neither the next phase nor
release work.

The decision fixes three product choices:

1. **Tiered Semantic Memory admission.** Model output, connector material, and external
   messages can only create candidates. Personal, confidential, externally asserted, or
   model-derived semantic memory requires an authorized HUMAN admission. A default-off
   deterministic SERVICE rule may auto-admit only non-sensitive derived facts from an
   already HUMAN-accepted source, without semantic expansion or conflict, under an exact
   policy revision.
2. **Conservative temporal semantics.** P17 recurring schedules skip nonexistent local
   times in a daylight-saving gap, choose only the earlier occurrence in a fold, and use a
   bounded catch-up window that emits at most the latest eligible missed occurrence.
3. **Single ownership of automatic effects.** AutomaticEffectAuthorization is introduced
   and accepted only by P18. P14 through P17 cannot create an automatic-effect authority
   path. Existing exact HumanApprovalDecision behavior remains authoritative until then.

P13 owns migration parser correction within its first implementation sub-gate; a separate
maintenance milestone is not added. P14, P15, and P17 have the strict responsibility split
fixed below.

### Alternatives considered

1. Keep the former P12 through P15 roadmap: rejected because it does not independently
   establish continuation, memory, triggers and recovery, and proactivity before the
   tracker and release.
2. Combine continuation, memory, trigger recovery, and proactivity in one gate: rejected
   because authority drift, restart correctness, retention, correlation, and autonomous
   wake failures could not be isolated or accepted independently.
3. Make all semantic-memory admission human-only: rejected as unnecessarily restrictive
   for exact, deterministic, non-sensitive derivations. Unrestricted service or model
   admission is also rejected because it would turn untrusted context into durable truth.
4. Introduce AutomaticEffectAuthorization with the connector or continuation phases:
   rejected because connectivity and resumption do not prove bounded autonomous action.
5. Use aggressive DST normalization or replay every missed occurrence: rejected because
   it can surprise users and amplify work or effects after downtime.
6. Let P15 correlate raw Outlook or Teams events: rejected because source normalization
   belongs to P14 and autonomous correlation belongs to P17.
7. Add a parser-maintenance milestone: rejected because the correction is a narrow,
   mandatory P13 sub-gate and must pass before migration 009 or gateway work.

### Consequences

- The Public Pilot roadmap grows from P9–P15 to P9–P20 without changing any accepted
  historical object.
- Connector source identity is accepted before external-reply continuation; durable
  continuation is accepted before memory; memory is accepted before autonomous recovery;
  proactivity is accepted before the tracker consumes it.
- More milestones and independent acceptances increase governance work, but reduce the
  blast radius of authority, persistence, correlation, retention, and autonomous-action
  defects.
- SQLite remains the only v0.2 reference store. Exactly-once claims are restricted to
  local transactional consumption; external providers remain effectively-once with
  idempotency, dedupe, and reconciliation.
- Private-live evidence is retained outside the public tree. Public artifacts contain only
  safe projections, fixed identities, counts, outcome classifications, and digests.

### Non-goals

This rebaseline does not authorize or claim self-created goals, shared memory, multi-Agent
collaboration, executable Skills, Skill learning, plugins as authority, arbitrary cron,
arbitrary browser, computer, shell, filesystem, hosted-tool, MCP, or code-execution
authority. It does not add PostgreSQL, distributed execution, high availability,
enterprise IAM, production tenancy, compliance certification, production security, or
production readiness.

P12 itself adds no runtime, core, application, port, adapter, API, CLI, Studio behavior,
database schema, migration, dependency, package, image, provider, connection, trigger,
memory, continuation, proactivity, tag, Release, or publication capability.

### Compatibility, migration, and forward supersession

Migrations 001 through 008 and their manifest entries remain immutable. Future migrations
are additive, default-off for new capability, and owned exactly once as fixed below.
Rollback means a verified backup restored under matching code; no destructive down
migration is designed or claimed.

This decision prospectively supersedes only the unimplemented roadmap assignments in the
P9 living documents and the affected forward-looking portions of ADRs 0003 and 0008. ADRs
0007 and 0010 remain valid and are not superseded. This decision does not rewrite any ADR,
its historical meaning, or any accepted result. ADR 0011, added during P12 implementation,
will record the precise prospective supersession and point to this fixed contract.

## Exact baseline and immutable historical identities

### P12 start identity

| Identity | Exact value |
| --- | --- |
| Accepted main and P12 base commit | c1562ea5201394d8a278f4b644daf4029cbb5bd4 |
| Base tree | ae0f33263cfc7445fef69656ad9c5cb04d4a2d00 |
| Required branch | codex/p12-public-pilot-continuity-rebaseline-v2 |
| P11R main CI | 34451912586; current-ci and bounded Compose smoke passed |
| Local tags at start | 0 |
| Remote tags at start | 0 |
| GitHub Releases at start | 0 |

Before replacement-branch creation, the checked-out v1 branch and HEAD MUST both remain
the exact rejected commit; its local ref MUST be unchanged; local main, origin/main and
remote main MUST all equal the exact base; the base tree MUST match; worktree, index and
untracked state MUST be empty; the local and remote v2 candidate branch MUST not exist; the
remote v1 branch and pull request MUST remain absent; local and remote tags and Releases
MUST be zero; there MUST be no unauthorized publication; and all protected P10 identities
MUST remain readable. Any mismatch fails closed before checkout, branch creation or file
modification.

### Repeatable acceptance-phase command oracle

The acceptance start uses the following repository- and remote-read-only verification
commands from the repository root. Each test and GitHub command exits zero, and the two
package-version responses must canonicalize exactly to the protected inventory in this
contract:

~~~sh
set -e
test "$(git symbolic-ref --quiet --short HEAD)" = "codex/p12-public-pilot-continuity-rebaseline"
test "$(git rev-parse HEAD)" = "8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3"
test "$(git rev-parse refs/heads/codex/p12-public-pilot-continuity-rebaseline)" = "8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3"
test "$(git rev-parse 8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3^)" = "c1562ea5201394d8a278f4b644daf4029cbb5bd4"
test "$(git rev-parse 8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3^{tree})" = "557a74e9174247483362bbbd15cd265113775d12"
test "$(git rev-parse 8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3:docs/p12/acceptance.md)" = "26562d795980ec8d6d9ea36ff3fcc718b41c09e8"
test "$(git rev-parse main)" = "c1562ea5201394d8a278f4b644daf4029cbb5bd4"
test "$(git rev-parse origin/main)" = "c1562ea5201394d8a278f4b644daf4029cbb5bd4"
test "$(git ls-remote --heads origin refs/heads/main | awk '{print $1}')" = "c1562ea5201394d8a278f4b644daf4029cbb5bd4"
test "$(git rev-parse c1562ea5201394d8a278f4b644daf4029cbb5bd4^{tree})" = "ae0f33263cfc7445fef69656ad9c5cb04d4a2d00"
test -z "$(git status --porcelain=v2 --untracked-files=all)"
test -z "$(git for-each-ref --format='%(refname)' refs/heads/codex/p12-public-pilot-continuity-rebaseline-v2)"
test -z "$(git ls-remote --heads origin refs/heads/codex/p12-public-pilot-continuity-rebaseline-v2)"
test -z "$(git ls-remote --heads origin refs/heads/codex/p12-public-pilot-continuity-rebaseline)"
test "$(gh pr list --repo jeremyliu1220/digital-colleagues --state all --head codex/p12-public-pilot-continuity-rebaseline --json number --jq 'length')" = "0"
test "$(gh pr list --repo jeremyliu1220/digital-colleagues --state all --head codex/p12-public-pilot-continuity-rebaseline-v2 --json number --jq 'length')" = "0"
test -z "$(git tag --list)"
test -z "$(git ls-remote --tags origin)"
test -z "$(gh release list --repo jeremyliu1220/digital-colleagues --limit 100)"
test "$(git ls-remote --heads origin refs/heads/codex/p10-mac-quickstart | awk '{print $1}')" = "4bef5629d450c6bb3940f606fc90194e008ee8fd"
gh auth status
for P12_P10_RUN_ID in 34202520699 34203006909 34204280131 34204837101 34205272328 34206039435 34235760264 34236719816 34237810474; do
  gh run view "$P12_P10_RUN_ID" --repo jeremyliu1220/digital-colleagues --json databaseId,headSha,headBranch,event,status,conclusion,workflowName,url || exit 1
done
gh api /users/jeremyliu1220/packages/container/digital-colleagues-runtime
gh api /users/jeremyliu1220/packages/container/digital-colleagues-studio
gh api --paginate /users/jeremyliu1220/packages/container/digital-colleagues-runtime/versions
gh api --paginate /users/jeremyliu1220/packages/container/digital-colleagues-studio/versions
PYTHONDONTWRITEBYTECODE=1 make p10-remote-distribution
~~~

The package comparison checks exact subject visibility, count, version IDs, manifest names,
tag mappings, created/updated timestamps and absence of additional entries. A successful
HTTP response without exact equality is a failure. gh authentication must provide the
read-only repository/Actions operations and demonstrated read:packages capability without
printing credentials. Every run response must canonicalize exactly to the source, status,
conclusion and lifecycle tables below; a readable ID with different fields is a failure.
The P10 distribution command may create, pull and remove only its task-owned transient
local Docker and OS-temporary state; it must report cleanup_residue_count 0 and leave the
repository, remote and pre-existing Docker state unchanged.

After all read-only checks pass, the only checkout and branch-creation commands are:

~~~sh
git switch main
test "$(git rev-parse HEAD)" = "c1562ea5201394d8a278f4b644daf4029cbb5bd4"
test -z "$(git status --porcelain=v2 --untracked-files=all)"
git switch -c codex/p12-public-pilot-continuity-rebaseline-v2 c1562ea5201394d8a278f4b644daf4029cbb5bd4
~~~

These commands change only the checked-out branch and create the new v2 ref. They do not
move or delete the rejected v1 ref.

The file is added through the repository editing boundary and the only commit command is
the ordinary non-amending commit of docs/p12/acceptance.md. No command in this phase
contacts a remote with write authority.

### Accepted history anchors

| Phase | Accepted or fixed identity | Tree or fixed content identity |
| --- | --- | --- |
| P8 | accepted commit 0bb80ab187932fbad42fbf665b8310987609a1f5 | accepted P0–P8 history anchor |
| P9 | final 11aa240af8db2ca515325dc059b1a77f7badc874 | tree a27cb6ce9f568b04083a88f7ba06f033235f4cbc |
| P9 acceptance | commit 597403bc151da75499acea5bb00ee298e7e5a005 | acceptance blob a9975fe5826bbfc9977e650047debb1d5dd2e714 |
| P9 evidence | fixed summary | summary blob 117b033f8f516dff269577ff28a8e51174e7f6a3 |
| P9 provenance | fixed receipt | receipt blob fbeada2a8d48c12ea811709b578f63116e267f8e |
| P10 | final 4bef5629d450c6bb3940f606fc90194e008ee8fd | tree 909b566b7ba9f7beb143cd0b29cf95fbd1178bbe |
| P10 acceptance | commit 99b0045bba48de8e4d44c10ce07d60ba20738a8b | acceptance blob c5ac3acd52a8732da617ce5d1d3a7e66e3671c80 |
| P10 implementation used by evidence | 0f7e15935d27549783480f1f55dbfcb036e49293 | summary blob a4c1a59fffec9c30160787a7bec584e228fb9f35 |
| P11 | final 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | tree 6d7c1b3053fefc1f3b14a4b39fde2d5adb641990 |
| P11 acceptance | commit b3963aadf4702b924e72dc1e7306799780eecfbd | acceptance blob 85f2a91b85d3ec223d4f458199913a3eadbaabe9 |
| P11 implementation used by evidence | fed27279f4e28ed5ec357eff10fd6019d64d6d85 | summary blob f9f58cd3094147f724a622a929eb98331af441a1 |
| P11 provenance | fixed receipt | receipt blob b7ce739aca9bdd6afffa1e6ae490e250bd9c9219 |
| P11R acceptance | commit 61d5c94e24157b93bc4b4bcca42b4d8d2eab8fec | tree 787af889c5ff88d5e22baeb1bc78ef36fd901727; acceptance blob 46e6244e06cfad64c10e21071959555dd29a49d3 |
| P11R implementation | 4a6df2db5c964b2bd6f052db6276dc303524230b | tree 0909a717081f307f79ae934b47348f5afb00e7bf |
| P11R final | c1562ea5201394d8a278f4b644daf4029cbb5bd4 | tree ae0f33263cfc7445fef69656ad9c5cb04d4a2d00; summary blob 30d4d3ac2360b165863c156b50628141141f13e9 |
| P11R provenance | fixed receipt | receipt blob cf06a3dbf9fd589a79daca5bc80e145d6c5def91 |

The table fixes verification anchors; it does not make summary artifacts authoritative
over their acceptance contracts or Git objects.

### Historical immutable versus living records

All accepted P0–P11R acceptance contracts, artifacts, evidence, receipts, provenance,
historical checkers, historical runners, accepted migrations, release inputs, and Git
objects are immutable. They MUST NOT be edited, regenerated, reinterpreted, or made to
claim a later result.

Only the exact living-document paths in the P12 allowlist may receive prospective status,
roadmap, architecture, security, privacy, capability, development, contribution, or
community-template updates. Those updates MUST preserve historical results and clearly
separate implemented, planned, not_evaluated, and excluded capability.

## Current gap analysis

The existing primitives are retained and reused, but they do not satisfy the new gates by
analogy. The exact gaps and owners are:

| Area | Accepted baseline that can be reused | Unimplemented gap | Owning proof |
| --- | --- | --- | --- |
| Durable continuation | Finite work, Agenda, WakeCycle, timer, lease, fence, outbox, ActionResult, reconciliation and restart persistence | No ProjectScope or continuation state machine, exact checkpoint, durable wait/question/next-action set, goal binding, explicit waiting-signal binding, mandatory boundary checkpoint, or blank-chat equivalence | P15 |
| Semantic Memory | Descriptive Profile, revisioned policy, audit digests and temporary bounded provider context | No candidate/admission distinction, classification, provenance citation, version, retention, conflict, correction, supersession, revocation, deletion watermark, bounded retrieval or retrieval digest | P16 |
| Trigger and recovery | Typed one-shot timer occurrence, Agenda wake, lease/fence and local restart recovery | No recurring schedule, heartbeat, autonomous connector polling, raw-event correlation, ambiguity quarantine, DST/catch-up contract, durable incomplete-state scan, host replacement or anti-entropy | P17 |
| Proactivity | Revisioned proactivity, working-hour, notification, interruption, wake-budget, stop and escalation policy fields | Policies are inert boundaries; there is no accepted goal-progress ledger, autonomous progress loop, bounded backoff, or AutomaticEffectAuthorization | P18 |
| Worker | Bounded local Agenda processing, SERVICE context, optimistic revision, lease and fence | Cannot recover the complete continuation set, poll providers autonomously, correlate replies, schedule recurrence, enforce mandatory checkpoints, or reconstruct bounded memory | P15, P17 and P18 |
| Store | One namespaced SQLite database, WAL, foreign keys, migrations 001–008, transactional replay/outbox and immutable audit | No tables or ports for 009–014 records; shared migration parser is not proven for trigger-body semicolons before the next migration | P13 through P18 |
| Model and connector adapters | Deterministic provider plus optional generic loopback HTTP JSON model/channel adapters | No named OpenAI Responses gateway, Microsoft connection/grant/source/cursor normalization, or live-provider acceptance | P13 and P14 |
| API | Typed HTTP mapping, session-derived authority, stable v0.2 package/deployment surfaces and historical compatibility routes | No current project/checkpoint/wait, memory lifecycle, schedule/correlation/recovery, proactivity proof or tracker operations | P15 through P19 |
| Studio | Local builder, revision review, work, wake, proposal, governance, package and deployment views | No continuation/recovery inspection, explicit wait binding, memory admission and citation, schedule/quarantine, progress/automatic-proof or complete bilingual tracker experience | P15 through P19 |
| Security | Disjoint principals, local RBAC, server-derived roles, two-person governance change, exact approval, replay defense, namespace and audit controls | No ExternalPartyReference rule, normalized-binding authority, memory abuse controls, raw-event quarantine, recovery-cursor distrust, or bounded automatic-effect proof | P14 through P18 |
| Privacy | Public-boundary scanner, safe diagnostics, credential-file boundary, payload digests and private evidence separation | No semantic-memory data lifecycle, provider-source minimization, deletion watermark, restore protection, or complete private-live retention and consent procedure | P14, P16 and P20 |
| Operations and release | P10 signed/attested images and Mac quickstart; backup, restore, update and diagnostics | No accepted always-on continuity profile, multi-day restart/recovery soak, ten-deployment private-live matrix, or Public Pilot release | P20 |

P12 corrects only the governance representation of these gaps. A planned record,
documented API, synthetic fixture, or checker does not make a gap implemented.

## P12 branch and commit topology

- The first P12 commit is acceptance-only. It adds only
  docs/p12/acceptance.md, has the exact base as its sole parent, and establishes
  P12_ACCEPTANCE_COMMIT and P12_ACCEPTANCE_BLOB.
- The acceptance file MUST remain byte-identical after that commit. No correction or
  evidence commit may touch it.
- After independent P12 governance implementation authorization, one or more allowlisted
  implementation commits MAY follow.
- If a local or exact-implementation-head gate exposes an in-scope defect, or an
  independent read-only review identifies one, one or more scoped-correction commits MAY
  follow under explicit correction authority. Each correction is append-only, identifies
  the failed gate or review finding and corrected earlier implementation commit, changes
  only the minimum allowlisted implementation or test surface needed for that defect, and
  MUST NOT change the acceptance file or summary.
- Every implementation and scoped-correction commit is single-parent and linearly descends
  from the preceding commit. Merge commits are forbidden.
- The complete ordered implementation and correction set ends at
  P12_FINAL_IMPLEMENTATION_HEAD. It includes every P12 commit after the acceptance commit
  and before the summary-only commit.
- The final P12 commit is summary-only. It adds only artifacts/p12/summary.json, has
  P12_FINAL_IMPLEMENTATION_HEAD as its sole parent, and is created only after evidence
  authorization and successful exact-implementation-head CI.
- No commit may follow the summary-only commit on the P12 candidate. A needed correction
  after it invalidates the candidate; the owner must make a new explicit decision without
  amend, rebase, squash, reset, force rewrite, or replacement of the existing objects.
- Amend, rebase, squash, force push, history rewrite, and merge commits are forbidden
  throughout the P12 branch.

The evidence summary MUST bind:

1. the acceptance commit and blob;
2. the ordered complete implementation and correction commit set;
3. for each set member, its exact commit, sole parent, tree, classification, and sorted
   changed paths;
4. the exact P12_FINAL_IMPLEMENTATION_HEAD and its tree;
5. the canonical implementation-range digest;
6. the exact implementation-head CI workflow, run ID, head SHA, conclusion, and required
   job results;
7. every local gate result, toolchain identity, preflight result, and safe evidence
   classification; and
8. the exact base-to-implementation changed-path set and protected-history checks.

The canonical implementation-range digest is sha256 followed by a colon and the lower-case
SHA-256 of UTF-8 canonical JSON. The top level is the ordered oldest-to-newest array of
objects described in item 3. Object keys and every changed-path array are lexicographically
sorted; JSON uses compact comma and colon separators, ensure_ascii false, Unicode NFC,
integer values only, UTC timestamps with Z where present, no non-finite values, and no
trailing newline. The summary commit is not a member of this digest.

The contract-only commit MUST NOT be pushed or used to open a standalone pull request.
Push and pull-request authorization occurs only after all authorized implementation and
local gates pass.

## Exact 39-path P12 changed-file allowlist

The complete base-to-final-candidate changed-path set MUST be exactly the following 39
paths. Every middle commit changes a permitted subset; the final candidate has no missing
or additional path. A rename, copy, delete, mode change, symlink, submodule, special file,
generated cache, or path outside this table fails closed. Existing files remain regular
files. New files are regular files with their ordinary repository text mode. Incidental
cleanup and unrelated reformatting are forbidden.

| # | Path | Necessity | Permitted change kind |
| ---: | --- | --- | --- |
| 1 | .github/ISSUE_TEMPLATE/feature_request.yml | Replace stale phase choices with the accepted P12–P20 planning boundary | Modify only milestone/status choices and matching explanatory copy |
| 2 | .github/pull_request_template.md | Require current contract, authorization, exact-head CI, evidence, and no-publication declarations | Modify governance checklist text only |
| 3 | .github/workflows/ci.yml | Move current CI from the P11R descendant boundary to the accepted P12 current gate | Modify CI policy and invocations only; retain triggers, pinned actions, least privilege, and no-publication behavior |
| 4 | AGENTS.md | Record accepted P0–P11R history and exact P12–P20 milestone discipline | Modify project-governance instructions only |
| 5 | CONTRIBUTING.md | Direct contributions to the current fixed contract and authorization sequence | Modify contribution and gate instructions only |
| 6 | Makefile | Add P12 targets and move the generic current-CI alias without changing historical target meaning | Add P12 target declarations, recipes and PHONY names; modify only the generic ci alias to delegate to p12-ci; preserve every P0–P11R target and recipe |
| 7 | README.md | State the accepted baseline, B+ roadmap boundary, commands, and claim limits | Modify status and usage documentation only |
| 8 | SECURITY.md | Align current security scope and future continuity threat boundary | Modify status and scope text only; retain reporting instructions |
| 9 | artifacts/p12/summary.json | Hold the authorized safe P12 evidence summary | Add only as the final summary-only commit; deterministic JSON evidence fields only |
| 10 | docs/adr/0011-public-pilot-continuity-rebaseline.md | Record the formal forward-looking Change Decision and supersession | Add one architecture decision record only |
| 11 | docs/architecture/target-architecture.md | Add the prospective P12–P20 component and dependency boundaries | Modify future architecture sections only |
| 12 | docs/development.md | Document current P12 gates, authorization, and evidence preflight | Modify development workflow text only |
| 13 | docs/p12/acceptance.md | Establish this immutable acceptance contract | Add only in the first acceptance-only commit; never modify afterward |
| 14 | docs/p12/rebaseline-checklist.md | Give reviewers repeatable P12 review and verification commands | Add documentation only |
| 15 | docs/product/capability-matrix.md | Correct current versus planned capability status | Modify status and cross-reference text only |
| 16 | docs/product/post-v0.1-capability-outlook.md | Map S1/S2 work to the gated roadmap while retaining S3/S4 deferral | Modify prospective outlook only |
| 17 | docs/product/v0.2-external-dependency-register.md | Reassign external dependencies, recheck points, and not_evaluated behavior | Modify planning/register entries only; no credentials or live data |
| 18 | docs/product/v0.2-public-pilot-capability-matrix.md | Replace former P12–P15 assignments with exact P12–P20 ownership and claims | Modify prospective matrix only |
| 19 | docs/product/v0.2-public-pilot-product-brief.md | Define the continuity, memory, trigger, proactivity, and Public Pilot boundary | Modify prospective product requirements only |
| 20 | docs/roadmap.md | Preserve accepted history and replace only the future sequence with P12–P20 | Modify current checkpoint and prospective roadmap only |
| 21 | docs/security/privacy-boundary.md | Add cross-reference and future continuity privacy constraints | Modify prospective privacy text only |
| 22 | docs/security/threat-model.md | Add cross-reference and future continuity threat constraints | Modify prospective threat text only |
| 23 | docs/security/v0.2-public-pilot-privacy-boundary.md | Fix data classes, retention, deletion, external content, and private-live boundaries | Modify prospective v0.2 privacy contract only |
| 24 | docs/security/v0.2-public-pilot-threat-model.md | Fix authority, injection, replay, correlation, schedule, recovery, and memory abuse controls | Modify prospective v0.2 threat contract only |
| 25 | provenance/p12-change-receipt.json | Bind non-self-referential base, contract, allowlist, zero-source and scoped-change provenance | Add deterministic safe provenance JSON only |
| 26 | scripts/check_p12_ci_policy.py | Enforce current workflow, pins, permissions, historical replay, and no-publication policy | Add deterministic read-only checker only |
| 27 | scripts/check_p12_migrations.py | Enforce immutable 001–008 identities, manifest, parser-first plan, and future ownership | Add deterministic read-only checker only |
| 28 | scripts/check_p12_provenance.py | Validate the P12 receipt, identities, allowlist, and zero source migration | Add deterministic read-only checker only |
| 29 | scripts/check_p12_rebaseline.py | Validate roadmap, decision, responsibility, authority, memory, recovery, and claim contracts | Add deterministic read-only checker only |
| 30 | scripts/check_p12_repository.py | Validate ancestry, topology, exact changed set, clean state, protected history, and no publication | Add deterministic read-only checker only |
| 31 | scripts/collect_p12_evidence.py | Produce only the authorized deterministic safe summary | Add evidence writer only; no network write or private/live material |
| 32 | scripts/run_p12_toolchain.py | Run the exact hash-locked P12 gate inventory in temporary locations | Add deterministic runner only |
| 33 | tests/p12/__init__.py | Define the P12 test package | Add empty or package-marker text only |
| 34 | tests/p12/test_ci_policy.py | Test fail-closed CI, pin, permission, historical replay, and no-publication rules | Add synthetic governance tests only |
| 35 | tests/p12/test_evidence_gate.py | Test evidence authorization, identity binding, complete commit set, and summary-only rules | Add synthetic governance tests only |
| 36 | tests/p12/test_migrations.py | Test immutable migrations, manifest identity, parser-first order, and unique future owners | Add synthetic governance tests only |
| 37 | tests/p12/test_provenance.py | Test receipt schema, exact identities, safe fields, and zero-source use | Add synthetic governance tests only |
| 38 | tests/p12/test_rebaseline.py | Test the complete B+ decision and milestone contracts | Add synthetic governance tests only |
| 39 | tests/p12/test_repository.py | Test exact path set, ancestry, topology, cleanliness, history protection, and negative cases | Add synthetic governance tests only |

The first acceptance commit changes only path 13. The summary-only final commit changes
only path 9. The implementation and any scoped-correction commits collectively provide
the other 37 paths.

## Architectural and data-contract boundary

The existing dependency direction remains:

~~~text
Pure core <- application and governance -> stable ports
                                   <- intelligence adapters
                                   <- infrastructure and HTTP adapters
~~~

Future core records are frozen standard-library dataclasses, Enums, and Protocols. Core
does not import FastAPI, Pydantic, provider or channel SDKs, database drivers other than
port definitions, ORMs, or orchestration frameworks. Pydantic remains restricted to HTTP
mapping. Provider-specific raw events remain in adapters and are not core records.

Every durable record carries a schema version and complete namespace. IDs are explicit
strings. Timestamps are timezone-aware UTC and serialize with Z. Time, randomness,
configuration, and I/O enter deterministic code through ports. Stores remain behind ports
while v0.2 continues to use one local state.sqlite.

### Core record set

The future milestone that owns each record must fix its complete schema and state machine
in that milestone's immutable acceptance contract. The following semantics are already
fixed:

| Record | Owner | Required semantics |
| --- | --- | --- |
| ProjectScope | P15 | Exactly the deployment Namespace and project_id; a deployment-internal project identity dimension, never a new global namespace or authority container |
| ProjectContinuationState | P15 | Exactly active, waiting, needs_human, completed, or stopped; completed and stopped are terminal; holds the exact active authority/source bindings and current checkpoint reference |
| SessionCheckpoint | P15 | Immutable versioned recovery snapshot with reason, exact project-state revision, active authority/source revisions, open waits, questions, next actions, goal binding, causal links, lease fence, and only the MemoryRetrievalSet ID and digest, never a copied memory body |
| WaitingCondition | P15 | Exact kind human_decision, external_reply, timer_at, dependency, or effect_reconciliation; exact status open, satisfied, expired, cancelled, or ambiguous; explicit ANY/ALL grouping, deadline, exact predicates and one-time consumption |
| NormalizedExternalSignal | P14 | Bounded provider-neutral projection observed through P14 explicit sync or P17-authorized polling through the P14 port, with source identity, provider version, digest, and dedupe identity; no waiting match |
| NormalizedWaitingSignal | P15/P17 | Durable server-created binding of one exact NormalizedExternalSignal to one exact WaitingCondition ID and revision; an authorized HUMAN operation creates it before P17, and the correlation SERVICE may create it only after P17 acceptance |
| OpenQuestion | P15 | Exact question, intended authorized HUMAN audience or exact ExternalPartyReference responder, state, expiry, answer binding, and causal origin; an external answer is not approval |
| NextAction | P15 | Bounded proposed continuation step, prerequisites, responsible principal kind, due or next-check time, and state; not effect authority |
| ContinuationDecision | P15 | Deterministic continue, remain_waiting, request_human, stop, or complete decision with exact inputs and authority revision set |
| GoalBinding | P15 | HUMAN-accepted objective digest, success criteria, bounds, expiry, exact Mandate and Policy revisions, namespace and causal identity; P15 may persist it but it cannot create proactive triggers before P18 acceptance |
| ExternalPartyReference | P14 | Provider-scoped external identity reference and safe display projection; explicitly not a Principal and never HUMAN |
| MemoryCandidate | P16 | Proposed fact or preference with provenance, content digest, classification, confidence, scope, retention request, and proposer kind |
| MemoryAdmissionDecision | P16 | Exactly admit or reject for one candidate, with authorized actor or exact accepted SERVICE rule and Policy revision; never a HumanApprovalDecision |
| Post-admission lifecycle decision | P16 | Separate from admission; correction, supersession, revocation and deletion use distinct durable lifecycle decisions; MemoryLifecycleDecision is only a P12 non-normative working label and P16 fixes the exact name and schema |
| MemoryRecord and version | P16 | Immutable versions with exact lifecycle status active, superseded, revoked, deleted, or expired; admission lineage, scope, classification, citations, content digest, retention and expiry; no silent overwrite |
| MemoryRetrievalSet | P16 | Immutable bounded selection containing purpose, checkpoint ID/revision, as-of time, record ID/version, record/content digest, citation/source, inclusion order, exclusion reasons, and canonical retrieval-set ID/digest |
| MemoryConflict | P16 | Explicit competing claims and versions, quarantine state, resolution authority, and causal decision; no silent overwrite |
| RecurringSchedule | P17 | Revisioned timezone, local-time rule, horizon, next occurrence, pause/revoke state, budget binding, and conservative DST/catch-up policy |
| TriggerCorrelation | P17 | Exact status received, matched, ambiguous, consumed, or ignored; unique source occurrence, project/wait/checkpoint/wake mapping, dedupe, correlation and causation; only matched may enter one-time atomic consumption and ambiguous is quarantined |
| RecoveryScanCheckpoint | P17 | Host and scanner identity, schema and policy revisions, bounded partition/page cursor, watermark and completion metadata; optimization only, never truth |
| GoalProgressLedger | P18 | Bounded evidence of progress, no-progress count, next-check/backoff, escalation and stop state for one HUMAN-accepted goal |
| ProactivityState | P18 | Default-off policy binding, working-hour and wake budgets, notification/interruption state, exact goal, and latest revalidation |
| AutomaticEffectAuthorization | P18 | Exact low-risk effect revision and proofs under current Mandate, Policy, grant, goal, participant, resource, budget, and freshness boundaries |

ProjectScope contains only deployment Namespace and project_id. It is neither a new global
namespace nor a container for Mandate, Policy, Goal, membership, grant, participant or
resource authority. Exact active authority and source bindings belong to the revisioned
ProjectContinuationState and SessionCheckpoint and are revalidated on every continuation.

Authority-bearing inputs are identities and exact accepted revisions, never descriptive
text. Memory, provider content, model output, external messages, checkpoints, goals,
schedules, correlations, and next actions cannot become Mandate, Policy, Role,
ConnectorGrant, HumanApprovalDecision, or effect authority.

The accepted end-to-end causal shape is:

~~~text
ExternalEvent / Timer / Heartbeat / RecoveryScan
-> TriggerCorrelation
-> WaitingCondition evaluation
-> WakeCycle
-> load exact SessionCheckpoint
-> bounded MemoryRetrievalSet
-> ContinuationDecision
-> Decision / EffectProposal
-> AutomaticEffectAuthorization or HumanApprovalDecision
-> EffectAttempt / ActionResult / Reconciliation
-> new SessionCheckpoint
~~~

Earlier milestones stop at their owned boundary. Before P17, an explicit HUMAN operation
replaces autonomous TriggerCorrelation. Before P16, MemoryRetrievalSet is the canonical
empty set. Before P18, only HumanApprovalDecision can authorize an effect.

## P14, P15, and P17 responsibility matrix

| Concern | P14 — connector foundation | P15 — durable continuation | P17 — autonomous trigger and recovery |
| --- | --- | --- | --- |
| Connection and grant use | Validate existing ExternalConnection and exact ConnectorGrant for explicit operations | Store only exact authority and source revisions needed by a wait | Revalidate connection and grant before polling, matching, wake, continuation, and dispatch |
| Source identity | Own SourceReference, safe locator, provider item/version identity, and ExternalPartyReference | Reference P14 identities without redefining them | Consume P14 identities and versions during correlation |
| Cursor | Own provider SourceCursor for one explicit bounded pull | No provider cursor ownership | Own scheduling of autonomous pulls; use P14 cursor operations and separately own RecoveryScanCheckpoint |
| Ingestion mode | pull_once or authenticated HUMAN-requested explicit sync only | No provider polling or raw ingestion | Bounded autonomous polling under accepted schedules, budgets, working hours, and grants |
| Provider normalization | Parse raw Outlook, Teams, Planner, or selected SharePoint result into bounded NormalizedExternalSignal | Consume only a durable NormalizedWaitingSignal binding | Invoke P14 normalization through ports during autonomous polling |
| Provider dedupe | Own provider item ID, version or etag, and per-source replay/dedupe | Reject duplicate binding consumption transactionally | Preserve provider dedupe while adding correlation and wake dedupe |
| Raw-event correlation | Explicitly forbidden | Explicitly forbidden | Sole owner of raw-event-to-wait matching and TriggerCorrelation |
| Ambiguous event | Return normalized items without choosing a wait | Cannot choose among candidates | Quarantine zero-safe or multiple matches; never wake or guess |
| Exact wait binding | Does not bind to a wait | Own HUMAN explicit server-side binding and exact-ID consumption | Correlation SERVICE may create a binding only after P17 acceptance and exact-one matching |
| Wake | No autonomous wake | Resume only from an already stored exact binding or other explicit P15 input | Own event, timer, heartbeat, expiry, and recovery wake orchestration |
| Startup recovery | Connection/cursor state remains durable but does not launch work | Reconstruct one explicitly selected project from durable state | Own bounded full/incremental startup scans, claims, fencing, and recovery takeover |
| Outlook/Teams ingestion E2E | Explicit sync ends at a normalized signal and provider dedupe proof | Authenticated HUMAN binds that signal to an exact wait; restart and resume without raw matching | Full autonomous poll, raw correlation, ambiguity quarantine, wake, and startup recovery |
| Effect transport | Own HUMAN-approved Outlook existing-thread reply, Teams allowlisted-chat reply and Planner latest-ETag If-Match update adapters; SharePoint write is denied | Own no provider transport; persist only resulting effect/reconciliation references in checkpoints | Reuse P14 transport only; own no connector write primitive or automatic authorization |

P14 MUST NOT inspect waiting predicates, infer a project, create a
NormalizedWaitingSignal, or wake a project. P15 MUST NOT call raw provider APIs, inspect a
provider cursor, or correlate a raw event. P17 MUST use P14's source and normalization
ports and P15's exact waiting and checkpoint contracts rather than duplicating them.

Effect transport ownership is separate from raw-event correlation. P14 owns the bounded
Microsoft transport adapters and executes through them only from an exact current
HumanApprovalDecision. P17 adds no transport and still requires HumanApprovalDecision for
every effect. P18 alone may add AutomaticEffectAuthorization and must reuse the P14
transport, outbox, idempotency, ActionResult and reconciliation path. P19 is composition
only and cannot add, fork or repair a connector write primitive.

## Authority and identity boundary

Principal kinds remain disjoint HUMAN, MODEL, and SERVICE. Canonical human roles remain
tenant_admin, colleague_user, and auditor. A caller never submits an authoritative role;
the server derives current role and membership from authenticated session state and
revalidates the applicable namespace and revision.

Any former shorthand that combined HUMAN with Admin is replaced by both of the following:

- an authenticated HUMAN principal; and
- a server-verified current tenant_admin role, or the narrower applicable role explicitly
  authorized by the operation and policy.

Model, SERVICE, provider, connector, and caller-supplied data cannot impersonate that
principal or role.

ExternalPartyReference is not a Principal, is never HUMAN, carries no tenant role, and
cannot receive or exercise Mandate, Policy, Grant, Goal, memory admission, approval, or
effect authority. An external reply:

- cannot satisfy a human_decision WaitingCondition;
- cannot create HumanApprovalDecision;
- cannot create or revise GoalBinding, ProjectScope, Mandate, Policy, membership,
  ConnectorGrant, or AutomaticEffectAuthorization; and
- when its content would alter authority, goal, scope, participant, resource, retention,
  or effect boundaries, can only cause request_human.

A valid external reply may satisfy only an external_reply condition under the exact
source, party, thread or conversation, time, grant, and predicate boundaries accepted for
that wait.

Every mutation requires server-side authorization, namespace checks, expected revision or
equivalent concurrency controls, idempotency and replay defenses, and a causal audit event.
Authority is revalidated at candidate creation, admission or binding, wake, checkpoint
load, continuation decision, effect proposal, approval or automatic authorization,
dispatch, reconciliation, and every retry.

## NormalizedWaitingSignal binding contract

Before P17 is independently accepted, explicit binding can be created only through a
server-side operation requested by an authenticated, authorized HUMAN. The caller supplies
references to the exact normalized signal and exact WaitingCondition ID and expected
revision; the server loads and validates all authoritative objects and constructs the
binding. The HUMAN request does not submit an authoritative binding object.

Provider payloads, models, external parties, adapters, and arbitrary callers MUST NOT
directly submit a binding or place an authoritative binding in a nested request. A SERVICE
cannot create one before P17.

The durable binding records at least:

- binding ID, schema version, namespace, deployment and project;
- exact WaitingCondition ID and revision, checkpoint and project revisions;
- normalized signal ID, digest, source, provider item/version and dedupe identity;
- HUMAN actor ID and server-derived role for an explicit binding;
- ExternalConnection, ConnectorGrant, SourceReference and SourceCursor revisions where
  applicable;
- Mandate, Policy, GoalBinding and membership revisions;
- operation or correlation rule identity and revision;
- correlation and causation IDs;
- an idempotency key, replay nonce or equivalent consumed-once key;
- server-stamped creation time, status, consumer, and consumption revision.

P15 consumes only the stored binding ID. It atomically checks the exact waiting ID and
revision, current authority and project state, unconsumed status, and signal dedupe state.
A stale, expired, revoked, mismatched, ambiguous, duplicate, or already consumed binding
does not resume work.

After P17 acceptance, only the authorized correlation SERVICE may create a service binding,
and only when the exact accepted correlation rule yields exactly one current waiting match.
It must record the SERVICE actor, rule and source revisions and every field above. Zero or
multiple safe matches are quarantined. A later HUMAN may resolve a quarantine only through
a distinct authorized server operation with a new causal decision; no original record is
rewritten.

## Durable continuation contract

The roadmap separates project identity, project operational state, checkpoint state, and
semantic memory. ProjectScope contains only deployment Namespace and project_id.
ProjectContinuationState has exactly five values: active, waiting, needs_human, completed,
and stopped. Completed and stopped are terminal. Running and paused are invalid P15 values.
Exact active authority/source bindings belong to ProjectContinuationState and
SessionCheckpoint and are revalidated for every continuation.

P15 stores project identity, operational state and checkpoint state. Operational state
controls current work and waiting, and a SessionCheckpoint is a recovery boundary.
Semantic memory is stored only after P16 introduces it and is never a substitute for any
of them. A P18 proactivity pause changes only ProactivityState; if HUMAN direction is
needed, P18 uses the accepted P15 needs_human transition and checkpoint boundary rather
than adding a project state.

A continuation load begins from an exact ProjectContinuationState revision and current
SessionCheckpoint. It loads bounded open WaitingConditions, OpenQuestions, NextActions,
the exact GoalBinding, authority and policy revisions, outstanding effect and
reconciliation state, next checks, and the accepted bounded MemoryRetrievalSet when P16 is
available. It deterministically produces one of:

- continue under the exact current authority;
- remain_waiting without consuming a signal;
- request_human; or
- stop; or
- complete.

There is no implicit continue. Missing, corrupt, future-schema, inconsistent, authority-
drifted, retention-violating, or ambiguously correlated state fails closed to quarantine,
request_human, or stop according to the fixed state machine. It never fabricates a
checkpoint or silently drops a waiting project.

Deserialization rejects running, paused and every project-state value outside the exact
five-value vocabulary. WaitingCondition kind is exactly human_decision, external_reply,
timer_at, dependency, or effect_reconciliation. Status is exactly open, satisfied,
expired, cancelled, or ambiguous. Conditions support explicit ANY or ALL grouping, a
deadline and one-time atomic consumption. An external reply can satisfy only an eligible
external_reply condition and can never satisfy human_decision.

GoalBinding records a HUMAN-accepted objective digest, success criteria, bounds, expiry,
exact Mandate and Policy revisions, namespace and causal identity. P15 may persist and
resume it, but before P18 acceptance it cannot produce a proactive trigger. A model,
SERVICE, connector, external party or memory cannot create, broaden, renew or self-accept
a GoalBinding.

### Mandatory checkpoint boundaries

P15 MUST make checkpoints mandatory at all of these boundaries:

1. immediately before transition into waiting;
2. immediately before transition into needs_human;
3. after every state-changing decision commit;
4. after every effect result is durably recorded;
5. after reconciliation is durably recorded;
6. immediately before stop;
7. immediately before complete;
8. before lease release;
9. during graceful shutdown before ownership is released; and
10. during recovery takeover after a new owner obtains a strictly higher fence.

For a pre-transition boundary, a durable intent plus the recoverable preceding state is
written before the externally visible state transition. A state-changing decision and its
resulting checkpoint commit atomically. An effect result or reconciliation and its
checkpoint commit atomically; if an external response is known but the checkpoint cannot
commit, the durable state is checkpoint_pending and no new effect may dispatch.

A worker MUST NOT release a lease until its required checkpoint is durable. Graceful
shutdown stops acquiring work, drains or durably marks in-flight work, checkpoints each
owned project, and only then releases leases. Recovery takeover first claims the project
with a strictly greater fencing token, rejects the old owner, records the takeover
checkpoint and causal audit, and then decides whether work can continue. A stale owner
cannot checkpoint, consume a signal, decide, dispatch, reconcile, or release the new
owner's lease.

### Blank-chat recovery and retrieval digest

The mandatory P15 end-to-end recovery scenario terminates the original process and starts
a new process, worker, service graph, and session with an empty chat context. The new
process receives only the durable database, allowed private credential references, and
ordinary deployment configuration. It receives no conversation transcript, hidden prompt
state, in-memory cache, copied Python object, or manually reconstructed context.

The recovered result MUST match the exact project ID and revision, continuation state,
checkpoint ID and revision, waiting IDs and revisions, open questions, next actions, goal
binding, authority and source revision set, outstanding effect/reconciliation state, next
check, and MemoryRetrievalSet ID and digest. The checkpoint never copies a semantic-memory
body. Before P16, the retrieval set is the canonical empty set and its
fixed digest; after P16, the same accepted bounded set and digest must be reconstructed
from durable records under the same query, policy, authority, and deletion watermark.

Canonical checkpoint and retrieval digests use sha256 followed by a colon and the
lower-case SHA-256 of UTF-8 compact canonical JSON: keys sorted lexicographically,
ensure_ascii false, strings normalized to Unicode NFC, timestamps normalized to UTC Z,
arrays in contract-defined deterministic order, integers rather than floating ranking
values, no non-finite numbers, and no trailing newline.

If current authority, policy, source, memory, correction, revocation, deletion, or
retention state legitimately changes, the digest must change and the continuation records
context_drift. It then recomputes retrieval and revalidates, remains waiting,
requests HUMAN review, or stops; it never presents a changed digest as the same recovered
state.

## Semantic Memory lifecycle contract

P16 separates MemoryCandidate, admit/reject MemoryAdmissionDecision, immutable
MemoryRecord versions, post-admission lifecycle decisions, MemoryRetrievalSet, and
MemoryConflict. A candidate is not retrievable memory. Admission does not grant authority.
MemoryAdmissionDecision has exactly the values admit and reject.

Correction, supersession, revocation and deletion are post-admission lifecycle operations.
They must use decisions distinct from MemoryAdmissionDecision. MemoryLifecycleDecision is
only a non-normative P12 working label; the exact type name, schema, actors, concurrency
rules and API representation are fixed by the future immutable P16 acceptance contract.
No admission, lifecycle or conflict decision is or may become HumanApprovalDecision.

### Admission tiers

| Candidate origin or class | Admission rule |
| --- | --- |
| Authenticated HUMAN, non-sensitive, within scope | Server-authorized HUMAN may admit with exact classification, scope, source, retention and revision |
| Personal or confidential | Authorized HUMAN admission is mandatory |
| Model-derived | Candidate only; authorized HUMAN admission is mandatory unless it meets the narrow deterministic SERVICE rule below |
| Connector or external-party assertion | Candidate only; authorized HUMAN admission is mandatory |
| Deterministic non-sensitive derivation from a HUMAN-accepted source | SERVICE auto-admission is default-off and permitted only by an exact accepted rule and Policy revision, with no semantic expansion, no conflict, complete provenance, and bounded retention |
| Restricted, credential, token, session, secret, raw attachment, or prohibited body | Reject; never persist as semantic memory |
| Operational checkpoint, wait, action, cursor, schedule, lease, or audit state | Store only in its operational subsystem; never admit as semantic memory merely for convenience |

Raw Email, Teams, SharePoint, or Planner bodies, attachments, credentials, tokens,
sessions, cookies, authorization headers, provider request or response dumps, and
unbounded prompts are forbidden from semantic-memory persistence and public evidence.
Only the minimum authorized safe projection or digest is retained.

### Classification, retention, and retrieval bounds

- Memory candidates expire after 7 days if not admitted.
- Non-sensitive admitted memory defaults to 90 days and cannot exceed 365 days without a
  new HUMAN admission.
- Personal memory defaults to 30 days and cannot exceed 90 days.
- Confidential memory defaults to 7 days and cannot exceed 30 days.
- Restricted material is rejected.
- Project-scoped memory expires no later than 30 days after project termination unless an
  authorized HUMAN re-admits an exact version under a new scope.
- A retrieval returns at most 12 records, at most 16 KiB of authorized projected content,
  and at most 3 records from one source.

Every record has namespace, scope, classification, source and citation identities, content
digest, confidence class, admission decision and revision, creator kind, retention,
expiry, version lineage, and exactly one lifecycle status: active, superseded, revoked,
deleted, or expired. Confidence is descriptive and never authority.

A MemoryRetrievalSet is an immutable bounded selection. It records purpose, exact
checkpoint identity and revision, as-of timestamp, every included record ID and version,
record and content digests, citation and source identity, deterministic inclusion order,
exclusion reasons, and a canonical retrieval-set ID and digest. A SessionCheckpoint stores
only that retrieval-set ID and digest and never copies the memory body.

Correction creates a new immutable version; silent overwrite is forbidden. Supersession
points to exact versions.
Conflicting claims enter MemoryConflict and are excluded from ordinary retrieval until an
authorized HUMAN resolution. A dedicated conflict-review view may show safe competing
citations, but cannot feed continuation, model context, memory derivation, or effect
decisions. Revocation immediately makes the affected version ineligible.
Deletion creates a durable tombstone and deletion watermark; content is removed according
to the private retention procedure while the minimum safe audit proof remains.

Backup restore or host replacement that lacks the current correction, revocation, or
deletion watermark fails closed and quarantines retrieval. A revoked, deleted, expired,
superseded, wrong-namespace, wrong-scope, unauthorized, conflicted, or stale-policy version
must not be returned. Retrieval revalidates current authority and retention at selection
and immediately before its use in a decision.

## Trigger, schedule, correlation, and recovery contract

P17 consumes the retained P3 one-shot timer primitive and owns recurring schedules,
heartbeat, connector-event polling, WaitingCondition expiry, TriggerCorrelation, wake
creation, and startup recovery. Every TriggerCorrelation has exactly one status:
received, matched, ambiguous, consumed, or ignored. It records a unique source occurrence,
the project, wait, checkpoint and wake mapping, dedupe identity, correlation and causation,
exact schedule or event and rule revisions, consumer state, and current authority and
policy revisions.

Only matched correlation may enter a one-time atomic consumption that produces consumed.
Ambiguous correlation is quarantined and produces no binding, wake or effect. Ignored is
terminal for the rejected occurrence and cannot later be consumed by mutation of the same
record.

### Schedule bounds and temporal semantics

- A recurring interval is no shorter than 5 minutes and no longer than 7 days.
- A heartbeat interval defaults to 60 minutes, is no shorter than 15 minutes, and is no
  longer than 24 hours.
- A schedule horizon is at most 365 days and must then be renewed by an authorized HUMAN.
- Arbitrary cron text is not accepted. The only schedule forms are interval, daily_local,
  weekly_local, and heartbeat; P17 fixes their exact typed schemas.
- The schedule stores its IANA timezone and local-time rule. Calculation is deterministic
  from injected time and timezone data.
- If a local wall time does not exist during a DST gap, that occurrence is skipped and
  audited; it is not shifted.
- If a local wall time occurs twice during a DST fold, only the earlier occurrence is
  eligible; the later duplicate is skipped and audited.
- A missed occurrence is eligible only within a 24-hour catch-up window. At most the
  latest eligible occurrence is emitted; all older eligible and ineligible occurrences
  are audited as skipped.
- Pause or revocation prevents new occurrences immediately. Resume does not replay skipped
  history beyond the same catch-up rule.

An occurrence and its local consumption are exactly-once only within the SQLite
transactional boundary. Provider observation and externally visible effects are
effectively-once: exact provider identity/version, dedupe, idempotency where supported,
outbox state, action result, and reconciliation are all required. No contract claims
provider-global exactly-once delivery.

### RecoveryScanCheckpoint is not authoritative

RecoveryScanCheckpoint is only a bounded-scan optimization. The authoritative recovery
truth is the durable set of:

- nonterminal ProjectContinuationState records;
- open, expired, or signaled WaitingConditions;
- active schedules and pending or unconsumed occurrences;
- accepted but unconsumed correlations and quarantined ambiguities;
- unresolved effect, ActionResult, reconciliation, checkpoint_pending, and transition-
  intent records;
- expired or abandoned leases and their fencing state; and
- current authority, revocation, retention, and deletion watermarks.

Startup recovery MUST reconstruct work from that durable truth. A missing, corrupt,
incompatible, future-schema, stale-policy, wrong-host, or regressed cursor triggers a
bounded full scan. Host replacement MUST work with no prior host cursor. Cursor loss MUST
not omit a project whose wait predates the cursor or whose provider has no recent event.

Incremental and full scans use stable partitions and page keys, deterministic ordering,
bounded page and cycle limits, and atomic page-result plus cursor advancement. A crash
after claiming or during a page cannot advance beyond uncommitted results. At least once
every 24 hours, a bounded anti-entropy scan begins from durable truth independently of the
incremental cursor.

Recovery first claims an eligible project with a new fencing token, then writes the
mandatory recovery-takeover checkpoint, then performs a ContinuationDecision. Scanning
cannot create a new project, goal, authority, grant, approval, memory, schedule, or effect.
Concurrent scanners use transactional claims and idempotent consumption so only one wins.

Required recovery tests include cursor deletion, corruption, schema mismatch, host
replacement, page-boundary crash, crash after claim, a waiting project with no recent
provider event, duplicate scan, concurrent workers, expired lease, checkpoint_pending,
and anti-entropy discovery.

## Bounded goal-driven proactivity and automatic effects

P18 is default-off. It operates only for an exact current GoalBinding that points to a
HUMAN-accepted goal. A model, SERVICE, provider, connector, external party, memory, or
recovery scan cannot create, broaden, renew, or self-accept a goal.

The GoalProgressLedger records bounded progress evidence and checks. No-progress behavior
uses 15 minutes, then 1 hour, then 4 hours. After the third consecutive no-progress check,
or earlier if policy requires, P18 moves only ProactivityState to paused and requests
HUMAN direction. ProjectContinuationState remains limited to active, waiting, needs_human,
completed, and stopped; it has no paused value. When HUMAN direction is required, P18 uses
the already accepted P15 transition to needs_human and performs the mandatory checkpoint.
A successful material-progress decision resets the backoff only when recorded against the
exact goal and checkpoint revision. Loops, wake counts, notifications, and interruptions
remain bounded by Mandate and Policy.

Working hours, wake budget, notification policy, interruption policy, stop conditions,
Mandate, Policy, GoalBinding, membership, connection, ConnectorGrant, participant and
resource scope are revalidated when scheduling, waking, loading a checkpoint, deciding,
proposing an effect, authorizing, dispatching, retrying, and reconciling. Drift cannot be
grandfathered by an earlier wake or memory.

P18 alone may introduce AutomaticEffectAuthorization. It is a separate durable type from
HumanApprovalDecision and cannot be synthesized from a prior approval. The only initial
eligible effect classes are:

- an internal email reply on an existing exact thread with unchanged accepted
  participants, no new recipient, no attachment, and content and sensitivity within the
  exact accepted policy;
- a message to an allowlisted existing Teams chat with unchanged participants, no new
  mention, no attachment, and content and sensitivity within policy; and
- an exact Planner update to a bound task using the latest observed etag and If-Match,
  within the accepted fields, project, plan, bucket, goal, and grant.

Any new recipient, participant, mention, attachment, external destination, resource,
thread, task, plan, field class, sensitivity increase, stale etag, ambiguous match,
authority drift, goal drift, budget excess, or unsupported effect requires an exact
HumanApprovalDecision or is denied. Provider conflict or 409/412 causes reread,
revalidation, and a new decision; it never retries under stale authorization.

AutomaticEffectAuthorization records the exact effect proposal and revision, content and
recipient/resource digests, deterministic rule and revision, every authority revision,
source freshness, budget use, goal, checkpoint, correlation and causation, creation and
expiry, dispatch consumer, ActionResult, and reconciliation. It is single-use and
replay-protected.

## Exact P12–P20 roadmap

### Gate discipline common to every phase

Each phase requires its own immutable acceptance contract and explicit project-owner
authorization. Its implementation, local evidence, remote CI, independent acceptance,
final acceptance, fast-forward merge, remote-main push, and remote closeout are separate
states. Passing one never starts the next.

Every future phase contract MUST fix its exact base, branch, changed-file set, commit
topology, migration ownership, tests, commands, evidence classifications, private-data
boundary, independent reviewer criteria, and prohibited capabilities before
implementation. It MUST retain earlier exact-object gates in an OS temporary checkout
rather than weaken historical checkers on a descendant.

The canonical aggregate exit command for each implementation phase is make pNN-ci, where
NN is the phase number. A phase may add separately named direct, migration, Compose,
private-live, or soak commands, but its immutable acceptance contract must fix them before
implementation. An aggregate success is valid only with positive exact test counts, zero
failures, errors, skips, expected failures, unexpected successes, suppressed failures, or
threshold substitutions, and no repository residue.

### P12 — Public Pilot Continuity Rebaseline

**Objective.** Convert this fixed decision into current living documentation, governance
gates, synthetic tests, provenance, and safe evidence without adding product behavior.

**Hard dependencies.** Exact accepted P11R main and this isolated acceptance commit.

**In scope and layer boundary.** Only the exact 39-path set above. Documentation may define
future core, application, port, adapter, API, and Studio contracts, but P12 changes none of
those runtime layers. New Python is restricted to repository, CI-policy, migration,
provenance, rebaseline and evidence governance.

**Migration.** None. Migrations 001–008 and the manifest remain byte-identical; migration
count remains eight.

**Security and privacy.** Static contract and negative synthetic tests only. No credential,
provider, personal, private-live, package, image, or network-write path.

**Repeatable exits.** Before any remote mutation, the exact implementation head runs:

~~~text
make p12-test
make p12-implementation-check
make p12-ci
make ci
~~~

Those four commands are read-only and summary-independent. After exact implementation-head
CI, the operator runs the read-only preflight:

~~~text
make p12-evidence-preflight
~~~

Only after explicit evidence authorization may the evidence writer run:

~~~text
make evidence-p12
~~~

It writes only artifacts/p12/summary.json. After the summary-only commit, the final
candidate runs the read-only final gate and generic current-CI alias:

~~~text
make p12-check
make ci
~~~

The final-candidate CI runs the same final mode and never invokes the preflight or writer.

**Independent acceptance.** Verify the fixed acceptance blob; exact base, ancestry and
variable linear commit topology; exact 39 paths and per-path restrictions; unchanged
history and migrations; complete B+ contracts; P10 protection; current CI transition;
safe provenance; exact implementation-head and final-candidate CI; and no publication.

**Evidence and claim.** static and synthetic_offline only. The maximum claim is
p12_public_pilot_continuity_rebaseline_candidate or, after acceptance,
p12_public_pilot_continuity_rebaseline_accepted. Neither is a product capability or Public
Pilot claim.

**Non-goals, size, and risk.** No product implementation or evidence from P13+. Estimated
gate size is medium governance work across 39 exact paths. Primary risks are inconsistent
living documents, accidental historical rewrite, a weak future contract, and current-CI
rules that cannot safely admit descendants.

### P13 — Migration parser correction and OpenAI Model Gateway

**Objective.** First prove the shared migration parser against immutable migrations
001–008, then implement a bounded OpenAI Responses API gateway.

**Hard dependencies.** Accepted and remotely closed P12. The parser sub-gate passes before
any gateway or migration-009 change.

**In scope and layer boundary.** Core receives only provider-neutral request, structured
result, usage, refusal and provenance values. Application owns prompt layering, limits,
policy checks, connection selection, retries and model decisions. Stable ports own model
invocation and usage recording. The OpenAI adapter owns transport and wire mapping. HTTP
and Studio may expose server-derived connection lifecycle, safe status, limits and usage;
they never accept authority from a model response.

The named initial provider contract is the OpenAI Responses API with Structured Outputs,
store false, explicit input/output/token/cost/time bounds, safe retry classes, refusal,
incomplete and schema-error handling, prompt-injection treatment, and exact model
provenance. The planning target is gpt-5.5; the exact executable model snapshot and cost
ceiling are fixed only by the P13 owner decision and immutable P13 acceptance contract.
No function tools, hosted tools, MCP, browser or computer use, shell, arbitrary file
access, connector credentials, or effect dispatch is exposed.

**Migration.** P13 uniquely owns additive migration 009,
model_connections_and_usage. It may store model connection metadata, safe credential
reference, usage, limit and provenance records. Secrets and provider bodies are not stored.

**Security and privacy.** Model output is untrusted data, never a HUMAN decision or
authority. Credential material stays in the private boundary. Public fixtures and evidence
are synthetic or safely projected. Usage and cost bounds fail closed.

**Evidence.** Parser evidence is local synthetic and precedes all gateway work. Gateway
contract evidence is deterministic and synthetic; named-provider compatibility remains
not_evaluated without separately authorized private-live access.

**Repeatable exits.** The parser-only sub-gate runs these direct commands without a
Makefile change in the first implementation commit:

~~~sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests/p13 -p 'test_migration_parser_gate.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.persistence.test_sqlite_semantics tests.runtime.test_p3_runtime tests.runtime.test_timer_runtime tests.runtime.test_outbox_binding tests.p8.test_backup_restore tests.p11.test_migrations tests.p11.test_lifecycle -v
~~~

P13 acceptance fixes the literal test-ID inventory behind those commands and may only add
coverage, not weaken or omit the semantic cases below. After the parser sub-gate passes,
make p13-ci is the aggregate. A separately authorized private-live command may evaluate
OpenAI and records not_evaluated when required access is absent.

**Independent acceptance.** Review parser-first ancestry, immutable 001–008 behavior,
migration 009 ownership, structured-output refusal and malformed response cases, limits,
provenance, credential redaction, model/HUMAN separation, deterministic fallback, and
private-live classification.

**Non-goals, size, and risk.** No Microsoft 365 connector, continuation, semantic memory,
autonomous polling, trigger correlation, proactivity, or effect authority. Estimated gate
size is small for the isolated parser sub-gate and medium-to-large for the gateway. Primary
risks are parser regression, API drift, credential leakage, prompt injection, cost overrun,
and overstated named-provider compatibility.

### P14 — Microsoft 365 Connector Foundation

**Objective.** Establish authenticated connection and exact grants, bounded explicit
source synchronization and provider dedupe, and the fixed HUMAN-approved Microsoft write
transports.

**Hard dependencies.** Accepted and remotely closed P13.

**In scope and layer boundary.** Core owns provider-neutral ExternalConnection metadata,
ConnectorGrant, SourceReference, SourceCursor, ExternalPartyReference, and
NormalizedExternalSignal. Application owns authenticated HUMAN-requested pull_once and
explicit sync, grant and scope validation, bounded normalization, cursor advancement,
provider dedupe, and dispatch through an exact existing HumanApprovalDecision. Stable
ports separate connection, source pull, safe credential resolution and effect transport.
Microsoft Graph adapters own Outlook, Teams, Planner and selected SharePoint wire formats.
HTTP and Studio expose exact connection/grant/source state, explicit sync and safe
HUMAN-approved effect status.

P14 establishes and accepts exactly these bounded write transports:

- an Outlook reply on an existing exact thread;
- a reply to an allowlisted existing Teams chat; and
- a Planner conditional update using the latest observed ETag with If-Match.

Outlook and Teams preserve the accepted participant, recipient, thread or chat, attachment
and mention boundaries. Planner 409/412 or a stale ETag causes reread, revalidation and a
new proposal and decision; it never overwrites. SharePoint remains selected-resource
read-only, and every SharePoint write is denied.

Every P14 external write requires a pre-existing, exact and current
HumanApprovalDecision. Before dispatch, P14 revalidates namespace, Mandate, Policy,
membership, ConnectorGrant, participant and resource scope, proposal revision and provider
data version. It reuses the existing EffectProposal, outbox, fencing, idempotency,
EffectAttempt, ActionResult and reconciliation contracts. P14 MUST NOT create, infer or
accept AutomaticEffectAuthorization.

**Migration.** P14 uniquely owns additive migration 010,
connector_sources_and_cursors, covering connection/grant metadata, source identity,
cursor, external-party reference and provider dedupe. The Microsoft transports reuse the
accepted effect/outbox persistence and do not reserve or move a P18 authority field.

**Security and privacy.** ExternalConnection authenticates but grants no resource or action
authority. ConnectorGrant is server-created by an authorized HUMAN under current Mandate
and Policy but is not an effect decision. Raw provider bodies, attachments, credentials
and tokens stay outside public evidence and semantic memory.

**Evidence.** Synthetic provider fixtures and local explicit-sync integration are
required. P14 Outlook/Teams ingestion E2Es stop after normalized signal and dedupe proof.
Separate P14 effect E2Es prove HUMAN-approved Outlook existing-thread reply, Teams
allowlisted-chat reply and Planner latest-ETag If-Match update; duplicate dispatch refusal;
ambiguous outcome and reconciliation; revoked or stale authority refusal; Planner 409/412
and stale-ETag reread followed by a new proposal and decision; and SharePoint write denial.
Private-live Outlook, Teams, Planner and SharePoint checks are separate and not_evaluated
without consent and access.

**Repeatable exit.** make p14-ci plus any separately authorized private-live connector
command fixed by P14 acceptance.

**Independent acceptance.** Validate exact resource grants, source identity, cursor
restart, pull bounds, provider dedupe, safe projection, stale/revoked grant refusal,
ExternalPartyReference non-principal semantics, exact HumanApprovalDecision binding, the
three bounded write transports, duplicate-dispatch prevention, ambiguous-result
reconciliation, stale/revoked authority refusal, Planner conflict reread/redecision,
SharePoint write denial, and the absence of raw correlation, WaitingCondition binding,
wake, continuation, memory, proactivity and AutomaticEffectAuthorization.

**Non-goals, size, and risk.** No autonomous polling, raw-event correlation,
WaitingCondition matching or binding, NormalizedWaitingSignal creation, wake,
continuation, memory, proactivity, or AutomaticEffectAuthorization. No connector write
exists outside the three fixed transports. Estimated gate size is large. Primary risks are
OAuth and Graph mode differences, scope excess, cursor drift, provider data leakage, false
dedupe, duplicate delivery, ambiguous result and stale conditional update.

### P15 — Durable Project Continuation

**Objective.** Persist and recover exact project work state across sessions and process
restarts without relying on chat history.

**Hard dependencies.** Accepted and remotely closed P14.

**In scope and layer boundary.** Core owns ProjectScope, ProjectContinuationState,
SessionCheckpoint, WaitingCondition, NormalizedWaitingSignal, OpenQuestion, NextAction,
ContinuationDecision and GoalBinding. Application owns state transitions, mandatory
checkpointing, explicit HUMAN binding, exact-ID signal consumption, resume and authority
drift handling. Stable ports expose transactional continuation and checkpoint stores.
SQLite implements them. HTTP and Studio expose safe project, wait, question, action,
checkpoint and HUMAN explicit-resume operations.

**Migration.** P15 uniquely owns additive migration 011,
project_continuation_and_checkpoints.

**Security and privacy.** All transitions are namespace- and revision-bound. Only
server-constructed explicit binding from an authorized HUMAN is accepted. Checkpoints
retain safe identifiers, projections and digests, not raw provider content or chat.

**Evidence.** Synthetic and local SQLite/HTTP/Studio restart E2Es are required. The
blank-chat recovery contract and every mandatory checkpoint boundary are hard gates.
Outlook/Teams E2Es use a P14 normalized signal and HUMAN exact-ID binding; they do not
perform raw correlation.

**Repeatable exit.** make p15-ci.

**Independent acceptance.** Validate every state transition and crash point, lease/fence
behavior, exact signal consumption, authority drift, no duplicate resume or effect,
checkpoint completeness, and new-process empty-chat equivalence including retrieval
digest.

**Non-goals, size, and risk.** No semantic memory beyond canonical empty retrieval,
autonomous polling, raw-event correlation, recurring schedule, recovery scanning,
proactivity, or automatic effects. Estimated gate size is large. Primary risks are
partial checkpoints, split-brain continuation, stale authority, duplicate effects, and
hidden dependence on process or chat state.

### P16 — Semantic Memory Lifecycle

**Objective.** Add scoped, provenance-bearing, retained and revocable semantic memory
without converting context into authority.

**Hard dependencies.** Accepted and remotely closed P15.

**In scope and layer boundary.** Core owns candidate, admission decision, record/version,
retrieval set and conflict. Application owns classification, tiered admission, correction,
supersession, conflict, revocation, deletion and bounded retrieval. Ports isolate storage
and any future index; SQLite is authoritative. An optional intelligence adapter may rank
only an already authorized candidate set and cannot admit or expand it. HTTP and Studio
expose HUMAN review, provenance, lifecycle controls and safe retrieval inspection.

**Migration.** P16 uniquely owns additive migration 012,
semantic_memory_lifecycle.

**Security and privacy.** The admission, retention, retrieval and deletion contract above
is mandatory. Raw provider content and secrets are prohibited. Authority and deletion
watermarks are revalidated on every retrieval and recovery.

**Evidence.** Synthetic/local admission and retrieval tests; correction, conflict,
revocation, deletion, expiry, restore-watermark, scope and authority negative cases; and
the non-empty blank-chat recovery digest.

**Repeatable exit.** make p16-ci.

**Independent acceptance.** Validate tiered admission, all numeric bounds, deterministic
retrieval digest, no authority conversion, lifecycle and tombstones, backup/restore
failure closed, safe Studio/API projection, and no unauthorized raw content.

**Non-goals, size, and risk.** No shared or cross-tenant memory, self-learning, Skill
learning, autonomous triggers, proactivity, or arbitrary embeddings claim. Estimated gate
size is large. Primary risks are sensitive retention, stale retrieval after deletion,
cross-scope leakage, unverifiable citations, and memory becoming implicit authority.

### P17 — Trigger, Recurring Schedule, Heartbeat, Correlation, and Recovery

**Objective.** Add bounded autonomous observation and wake while safely reconstructing
durable incomplete work.

**Hard dependencies.** Accepted and remotely closed P16.

**In scope and layer boundary.** Core owns typed RecurringSchedule,
TriggerCorrelation, occurrence and RecoveryScanCheckpoint contracts. Application owns
bounded poll scheduling, DST and catch-up evaluation, raw-event correlation, ambiguity
quarantine, exact binding creation by the correlation SERVICE, wake, startup scan,
anti-entropy and takeover. Ports expose time, timezone, poll, schedule, correlation and
recovery stores. P14 adapters still own provider wire parsing. HTTP and Studio expose
schedule review, pause/revoke, quarantine, recovery and causal wake state.

**Migration.** P17 uniquely owns additive migration 013,
trigger_correlation_and_recovery.

**Security and privacy.** Default-off autonomous polling, exact grant/scope revalidation,
working-hour and wake budgets, replay protection, fencing, quarantine, no raw public
evidence, and cursor-not-truth rules are mandatory.

**Evidence.** Deterministic timezone fixtures, local multi-worker crash/restart tests,
synthetic connector events and private-live Outlook/Teams autonomous E2Es. Missing
private-live access is not_evaluated and blocks the corresponding live claim.

**Repeatable exit.** make p17-ci plus the separately authorized private-live correlation
command fixed by P17 acceptance.

**Independent acceptance.** Validate temporal bounds, DST gap/fold, catch-up, pause and
revoke, duplicate/late/out-of-order events, exact-one matching, ambiguity quarantine,
provider and wake dedupe, cursor loss, host replacement, full and anti-entropy scans,
multi-worker fencing, and causal audit.

**Non-goals, size, and risk.** No self-created goal, unbounded loop, arbitrary cron,
automatic effect, or tracker behavior. Estimated gate size is extra-large. Primary risks
are duplicate wake/effect, missed old waits, bad DST behavior, false correlation,
split-brain recovery, and provider throttling.

### P18 — Bounded Goal-driven Proactivity

**Objective.** Let a colleague make bounded progress checks on one HUMAN-accepted goal and
introduce the only automatic-effect authorization path.

**Hard dependencies.** Accepted and remotely closed P17.

**In scope and layer boundary.** Core owns GoalProgressLedger, ProactivityState and
AutomaticEffectAuthorization. Application owns progress evaluation, no-progress backoff,
escalation, budgets, policy revalidation and exact automatic authorization. With respect
to external effects, P18 adds only AutomaticEffectAuthorization and its low-risk
eligibility and causal proof. It reuses the P14-accepted Outlook, Teams and Planner
transports and the accepted outbox, idempotency, ActionResult and reconciliation path
unchanged. P18 MUST NOT add, fork, replace, repair or otherwise complete a connector write
adapter. Adapters gain no authority. HTTP and Studio expose goal binding, progress,
budgets, automatic-authorization proof, ProactivityState pause/stop and HUMAN escalation.

**Migration.** P18 uniquely owns additive migration 014,
goal_proactivity_and_automatic_effect_authorization.

**Security and privacy.** Default-off; exact HUMAN goal; no model approval; single-use
authorization; narrow initial effect allowlist; full revalidation and causal proof; HUMAN
approval or denial outside it.

**Evidence.** Deterministic/local progress and backoff tests, synthetic low-risk and abuse
effects through the already accepted P14 transports, crash/retry/reconciliation tests,
proof that no new connector adapter exists, and separately authorized private-live
effects.

**Repeatable exit.** make p18-ci plus any private-live effect command fixed by P18
acceptance.

**Independent acceptance.** Validate no self-goals, bounded wakes and loops, the
15-minute/1-hour/4-hour escalation, working hours and interruption policy, exact automatic
proof, stale-drift refusal, external-effect idempotency and reconciliation, and unchanged
HumanApprovalDecision semantics. Acceptance also proves exact reuse of P14 transports,
outbox, idempotency, ActionResult and reconciliation and the absence of any new, forked,
replacement or repaired connector write adapter.

**Non-goals, size, and risk.** No connector transport implementation, general autonomy,
arbitrary effects, new participants, attachments, unbound resources, collaboration, or
Skills. Estimated gate size is
extra-large. Primary risks are self-expansion, notification harm, automatic misdelivery,
stale authorization, loops, and false progress.

### P19 — Built-in Public Pilot Project Tracker

**Objective.** Deliver the bilingual project-tracker experience by consuming only accepted
platform primitives.

**Hard dependencies.** Accepted and remotely closed P18.

**In scope and layer boundary.** A declarative non-executable AgentPackage and
ColleagueDeployment compose only the accepted P13 model, P14 sources and transports, P15
continuation, P16 memory, P17 triggers and P18 proactivity and authorization primitives.
Application orchestration cannot bypass those services. Existing stable ports and adapters
are reused. If any required Outlook, Teams or Planner transport is absent, the P19 gate
fails. P19 MUST NOT add, repair, fork, bypass or otherwise complete a connector write
primitive. API and Studio present zh-TW and en-US project status, waits, questions, next
actions, memory citations, trigger causality, progress and effect decisions.

**Migration.** None. The tracker consumes migrations 009–014 and may not add 015.

**Security and privacy.** Exact package trust, deployment, Mandate, Policy, goal, grant,
participant and resource boundaries. No delete_task default. Automatic, HUMAN-approved
and denied outcomes remain visibly distinct.

**Evidence.** Synthetic/local end-to-end tracker flows and separately authorized private-
live model and M365 scenarios. Language keys have identical authority meaning.

**Repeatable exit.** make p19-ci plus any private-live tracker command fixed by P19
acceptance.

**Independent acceptance.** Verify that the tracker is only a consumer; no primitive or
connector transport is added, repaired, bypassed, forked or completed; a missing required
transport fails the gate; bilingual behavior is semantically equal; every decision and
effect is causal; restart and memory behavior use accepted contracts; and private-live
claims are exact.

**Non-goals, size, and risk.** No connector write implementation, new primitive,
migration, self-goal, collaboration, Skill, or release. Estimated gate size is
medium-to-large. Primary risks are application
bypass, confusing automatic versus HUMAN action, translation drift, and overclaiming from
synthetic demos.

### P20 — Always-on Public Pilot Release

**Objective.** Converge the accepted P13–P19 capability into an operable, recoverable
Public Pilot and evaluate the complete private-live path.

**Hard dependencies.** Accepted and remotely closed P19, explicit private-live access and
consent, and a separate P20 release/publication contract.

**In scope and layer boundary.** Always-on operator profiles for the supported Mac and
Linux reference hosts, health and bounded restart, backup/restore/update/rollback,
diagnostics, release candidate assembly, documentation, and complete cross-layer E2E. No
new primitive is introduced merely to pass release.

**Migration.** None. Migration count remains fourteen. A schema need stops P20 and
requires a new owner decision; migration 015 is not pre-authorized.

**Security and privacy.** Private-live evidence uses consented non-public environments
with exactly two Microsoft 365 test tenants, ten dedicated Agent test accounts, one usable
OpenAI test project, one verified project-operated multi-tenant Entra public-client App,
one enterprise-provided BYO single-tenant public-client App, delegated user-consent and
Admin-consent test capability, and actual Outlook, Teams, Planner and selected SharePoint
test data. Private evidence storage remains outside the public tree.

Every live macOS host MUST report FileVault enabled before receiving credentials;
off, unknown, unverified, or synthetic status blocks live readiness. A live Linux host
requires equivalent operator-verified encrypted-volume readiness. Secret directories are
mode 0700, credential files are mode 0600, and service mounts are read-only. The project
does not enable encryption or handle a recovery key. Secrets, personal identifiers, raw
messages, attachments, tokens and live receipts never enter the public tree. Diagnostics
remain allowlisted and redacted.

**Evidence.** Ten active ColleagueDeployments run for the complete 72-hour soak. Evidence
also covers process and host restarts; wait/reply/resume; schedule/heartbeat; memory
correction/revocation/deletion; authority drift; automatic and HUMAN-approved effects;
backup/restore; update/rollback; and complete causal audit. A separately authorized HUMAN
evaluation uses a pre-accepted protocol, sample, baseline, success thresholds, consent and
private report; synthetic usability observations cannot replace it. Every unavailable
required environment or HUMAN-evaluation element remains not_evaluated and blocks the
Public Pilot claim.

**Repeatable exits.** make p20-ci, a separately authorized private-live E2E command, and a
separately authorized 72-hour soak command, all fixed by P20 acceptance before execution.

**Independent acceptance.** Review exact release inputs, every prior accepted contract,
private-live consent and safe projections, exact tenant/account/OpenAI/App-mode/data
inventory, encrypted-storage readiness, HUMAN evaluation, soak completeness, no duplicate
reply/effect, recovery, rollback, supported-host scope, release identities and public
claims. Tag, Release, signing, attestation, package/image publication and public
announcement each need their own explicit authorization after candidate acceptance.

**Non-goals, size, and risk.** No HA, enterprise IAM, production tenancy or security,
compliance, unlimited scale, collaboration, Skills, or production readiness. Estimated
gate size is large operational and evidence work. Primary risks are long-soak interruption,
private-data leakage, provider variability, incomplete environment coverage, host-specific
failure, and claim inflation.

## P13 parser-first correction chain

The current shared migration runner uses a delimiter split that is not sufficient for SQL
trigger bodies containing semicolons. The existing P11 store has a local complete-statement
approach, but that does not prove the shared runner used for all migrations. P13 corrects
the shared parser before any new schema.

The first P13 implementation commit MUST contain only:

- the shared migration parser implementation needed to correctly recognize complete SQL
  statements; and
- parser-related tests and fixtures that exercise the fixed gate.

It MUST NOT change a Makefile, CI workflow, dependency declaration or lock, migration,
manifest, gateway, model connection, usage/provenance schema, core or application API,
HTTP mapping, Studio behavior, documentation unrelated to the parser, or evidence summary.
The parser gate is therefore invoked directly by the exact two unittest commands above
and the literal inventory fixed in the P13 acceptance contract.

If the parser gate fails, one or more append-only parser-scope correction commits are
allowed. Until the parser gate passes in full, every correction remains limited to the
same shared parser and parser-related tests. It cannot add migration 009, Gateway,
dependency, API, or Studio behavior.

The parser sub-gate MUST prove all of the following using the immutable 001–008 inputs:

1. fresh migration from empty state through 008;
2. upgrade from every prefix 001 through 007 to 008, plus an already-008 no-op;
3. correct parsing and behavior of trigger bodies containing internal semicolons;
4. atomic rollback on syntax, checksum, injected mid-migration, and trigger-creation
   failure, with no partial schema or schema_migrations row;
5. restart and idempotent rerun after success and after a rolled-back failure;
6. exact schema_migrations version, name, checksum and applied-state behavior; and
7. all retained migration, store, backup and restore regression tests, including the
   runtime, timer, persistence, P11 AgentPackage/deployment lifecycle and P11 migration
   suites.

Only a distinct later P13 implementation commit after that complete pass may add migration
009, dependencies, model Gateway, API, or Studio work. The passing parser commit and any
parser corrections remain explicit ancestors and evidence members. The gate cannot be
relaxed, renamed away, skipped, or retroactively made to pass. A parser defect discovered
after migration-009 work begins stops the phase for a new project-owner decision; it is not
silently folded into unrelated gateway correction.

## Migration identity and ownership

The migration manifest at the base has Git blob
bfd142486041029bfcc1106ef6ffd4aeb125ed36 and file SHA-256
3ce53dd7d4e0e7cbc0e9cf4731d6001af8bab57861acfe55184e6f6ab685cc10.
The following SQL identities are immutable:

| Version and name | Git blob | File SHA-256 |
| --- | --- | --- |
| 001_initial.sql | c8758dd18f9dea402e368f93e4942a9da65edb60 | 9a9a9c031bd27072333ee30603bcd6c7e2f33f60e7920f3a69ff251836093c02 |
| 002_runtime_indexes.sql | 505485460ce443e80ef2177e2a07aab1218e022a | b0728e3e910e0f0921271b2121308518945968874a667c340d9dc007cbfea11f |
| 003_timer_triggers.sql | 0ff7035e489fda052c6d82c401e5db3b06e8203a | 98325116ff022277aee6ee9038083a3866e912c907d08afeb0da4c48f97d7e98 |
| 004_local_authentication.sql | edc24adb566568b397b30c88c610cd309f7666bb | dfe550129f32128eadc685cb54b70feed276ceb3274dbcbd76e214053d77e58b |
| 005_evaluation_observations.sql | 42612d8c47967707fb33b772bf414872f35b5ecc | 6649985cf92d9efd378b8b69447357193fdb98eead7d3d23f9bbec1db02b2a61 |
| 006_revisioned_colleague_builder.sql | 581e3ba9a75c15002c7bc513b69ea9a920771892 | 7909da4b0b3eb514222f1fd1068c19eb6e8b98d466a786b76c20ae7999e26bcd |
| 007_governance_hardening.sql | feb7b658c8e356bf0e717ce69e5896a7c6b00c34 | ba572b74ffe7d16ed09ffd58791d7bb23b875806996ec897b2e73c82a593cf9c |
| 008_agent_packages_and_deployments.sql | a20386ab196e1ab826a0c9a9770999b0e41cb8cf | e7c8b61c54393933e5e4fda06da4a06b11b2b2c1e38bec3163853e41136b0253 |

Future ownership is exact and non-overlapping:

| Migration | Sole owner | Additive purpose |
| --- | --- | --- |
| 009 | P13 | Model connections, usage limits/accounting, and model provenance |
| 010 | P14 | Connector grants, sources, cursors, external-party references, and provider dedupe |
| 011 | P15 | Exact five-value ProjectContinuationState; checkpoints; WaitingCondition exact kinds, statuses, ANY/ALL groups, deadlines and one-time consumption; questions; next actions; GoalBinding; and explicit signal binding |
| 012 | P16 | Semantic-memory candidates; admit/reject MemoryAdmissionDecision; immutable MemoryRecord versions; conflicts; separate post-admission correction, supersession, revocation and deletion lifecycle decisions; retention; revocation; and deletion watermarks, without fixing the lifecycle-decision type name or schema |
| 013 | P17 | TriggerCorrelation received, matched, ambiguous, consumed and ignored states; recurring schedules; occurrences; correlation mappings; quarantine; and recovery scan checkpoints |
| 014 | P18 | Goal progress, proactivity state, and AutomaticEffectAuthorization |
| 015 | No owner | Unauthorized; P19 and P20 add no migration |

Every future migration is numbered, checksummed, atomic and additive. Existing rows and
legacy projects retain their old behavior. New connections, continuation, memory,
schedules, proactivity and automatic effects default off and require explicit creation
under accepted authority. No milestone may reserve another phase's migration or move a
field merely to simplify implementation.

## Required end-to-end acceptance scenarios

Every scenario records namespace, principal and server-derived role, exact authority and
policy revisions, project and checkpoint revisions, trigger, correlation and causation,
lease and fence, decision, proposal or no-op, approval or automatic proof, attempt, result,
reconciliation, new checkpoint, and audit continuity. Public evidence contains safe
projections only.

1. **HUMAN decision across restart — P15.** Enter needs_human after the mandatory
   checkpoint, terminate the process, start with blank chat, accept an exact server-side
   HUMAN decision, resume once, and prove no model/SERVICE/external approval and no
   duplicate work.
2. **Outlook explicit reply ingestion — P14 plus P15.** P14 explicit sync creates a deduped normalized
   signal. An authorized HUMAN binds it to one external_reply wait. P15 restarts and
   consumes the exact binding once. Neither phase performs raw autonomous correlation.
3. **Teams explicit reply ingestion — P14 plus P15.** The same boundary is proven for an allowlisted
   chat and exact external-party/thread identity.
4. **HUMAN-approved Microsoft transports — P14.** Existing exact HumanApprovalDecision
   records drive an Outlook existing exact-thread reply, a Teams allowlisted existing-chat
   reply and a Planner latest-ETag If-Match conditional update through the accepted outbox,
   fencing, idempotency, EffectAttempt, ActionResult and reconciliation path. The scenario
   rejects duplicate dispatch, reconciles ambiguous outcomes, refuses revoked or stale
   authority, rereads Planner after 409/412 or stale ETag and requires a new proposal and
   decision, and proves that every SharePoint write is denied.
5. **Outlook autonomous reply — P17.** A bounded poll obtains a raw event through P14,
   exact-one correlation creates a SERVICE binding, a wake loads the checkpoint and
   resumes once. Revoked grant or changed wait remains waiting or requests HUMAN.
6. **Teams autonomous reply — P17.** Equivalent autonomous chat path with message/version
   dedupe, no new participant or mention authority, and restart recovery.
7. **Duplicate event — P14/P17.** Same provider item/version and replayed occurrence
   produce one normalized observation, one accepted correlation, one binding, one wake,
   one reply or effect, and audited duplicate refusal.
8. **Ambiguous event — P17.** Two possible waits yield quarantine, zero binding, zero wake
   and zero effect until a separately authorized HUMAN resolution.
9. **Late and out-of-order event — P17.** Current wait/source revisions and time bounds
   determine eligibility; stale or superseded events do not roll state backward.
10. **Schedule and heartbeat across restart — P17.** Timezone, next occurrence, budgets and
   dedupe survive process and host restart; DST gap/fold and catch-up produce the fixed
   conservative outcomes.
11. **Cursor loss and host replacement — P17.** Delete or corrupt RecoveryScanCheckpoint,
    start on a new host with no cursor, and rediscover every eligible durable incomplete
    project including an old waiting project with no recent provider event.
12. **Mandatory crash points — P15/P17.** Crash before and after each mandatory checkpoint,
    effect result, reconciliation, lease release, page commit and takeover. Recovery
    neither loses state nor repeats externally visible work.
13. **Memory correction — P16.** Corrected version supersedes the old one; restart
    retrieves only the accepted new version and a changed canonical digest.
14. **Memory revocation, deletion and expiry — P16.** Each becomes immediately
    unretrievable. A stale backup lacking the watermark quarantines instead of resurrecting
    content.
15. **Authority drift — P15–P18.** Revoke membership, Mandate, Policy, GoalBinding or
    ConnectorGrant after checkpoint, wake, proposal and authorization. Every later stage
    refuses continuation or dispatch and requests HUMAN or stops.
16. **No-progress backoff — P18.** Consecutive no-progress checks use 15 minutes, 1 hour
    and 4 hours, then pause only ProactivityState and escalate through the accepted P15
    needs_human transition and mandatory checkpoint, with no P15 paused state, unbounded
    wake or notification.
17. **Automatic-effect boundary — P18.** AutomaticEffectAuthorization runs the same P14
    Outlook, Teams and Planner transports and can pass only with every proof current. New
    participant, attachment, mention, resource or stale ETag requires HUMAN approval or
    denial. The test proves that P18 added no connector write adapter.
18. **Full tracker path — P19.** The bilingual tracker composes only accepted P13–P18
    primitives, survives restart, distinguishes automatic/HUMAN/denied outcomes and
    produces complete causal audit. A missing required transport fails the gate, and P19
    never implements, forks, bypasses or completes one.
19. **Private-live Public Pilot — P20.** New process and empty chat recover a real waiting
    Outlook or Teams project, bounded memory, schedule/heartbeat and goal progress;
    resume, effect, result, reconciliation and checkpoint occur once during the 72-hour
    environment.
20. **Self-reply and Agent-loop rejection — P14/P17/P18.** A message emitted by the same
    ColleagueDeployment cannot satisfy its own wait, and a message emitted by another
    managed Agent or ColleagueDeployment cannot create an Agent-to-Agent wake/reply loop.
    Exact sender principal, provider message and in-reply-to identities are deduped and
    quarantined or ignored with causal audit; they do not become an external-party answer,
    HUMAN decision, new goal, binding, wake or effect authority.

Failure to prove no duplicate reply, no duplicate effect, no waiting-project omission, or
complete causal audit blocks acceptance of the owning milestone.

## P12 CI governance transition

The accepted P10, P11 and P11R workflows, runners, checkers, tests, acceptance records and
evidence remain reproducible on their exact objects and are not edited. P12 may update the
living .github/workflows/ci.yml and Makefile only through the allowed changes above.

The P12 implementation must:

1. make ci delegate to the new branch-independent P12 current-tree gate;
2. use exact, literal current-tree test and checker inventories with positive exact counts;
3. preserve pinned GitHub Actions, least-privilege permissions, trusted lock files,
   no-publication behavior, and no credential output;
4. replay each required historical aggregate in an OS temporary checkout of its exact
   accepted object and contract-required ref layout;
5. never modify, import and weaken, monkey-patch, copy and relax, or redefine an accepted
   historical checker merely to make it pass on a descendant;
6. distinguish current-tree regression results from exact-object historical replay; and
7. leave the repository, Docker, caches and temporary state clean.

The target and runner graph is exact and non-recursive:

| Target | Sole behavior |
| --- | --- |
| make p12-test | Invoke scripts/run_p12_toolchain.py with scope test |
| make p12-implementation-check | Invoke the runner with scope implementation; require summary absent and the exact 38-path base-to-head set |
| make p12-ci | Invoke the runner with scope ci; derive implementation or final_candidate mode from committed Git topology and summary presence, never from a caller override |
| make ci | One-way alias to p12-ci only |
| make p12-evidence-preflight | Invoke the runner with scope evidence-preflight against an explicit implementation SHA and numeric CI run ID |
| make evidence-p12 | Invoke scripts/collect_p12_evidence.py with the explicitly authorized preflight receipt path and digest |
| make p12-check | Invoke the runner with scope final; require the summary-only tip, exact 39-path set and valid committed summary |

No P12 runner or checker may shell back to make ci or any p12 target. The implementation
mode requires this acceptance path plus all 37 implementation paths and forbids the
summary. The final_candidate mode requires all 39 paths, proves that the tip changes only
the summary, and validates the summary against its exact parent. The same scope ci command
therefore works on both exact remote CI heads without accepting an intermediate partial
tree.

Historical replay occurs once per aggregate run in an OS temporary checkout at exact
c1562ea5201394d8a278f4b644daf4029cbb5bd4 with the required ref layout. It invokes the
accepted make p11r-check there; that fixed aggregate already retains the earlier chain.
P12 does not recursively invoke each historical milestone or run accepted P11R directly
on a P12 descendant.

The final-candidate CI validates committed evidence and topology only. It MUST NOT execute
the operator-authenticated evidence preflight, evidence writer, gh login or refresh,
provider access, publication, or any command that changes repository or remote state.

### Current workflow no-publication oracle

The living workflow may trigger only on a pull_request whose base is main and a push to
main. workflow_dispatch, schedule, pull_request_target, workflow_call, repository_dispatch
and every other trigger are forbidden in P12. Top-level permissions are exactly
contents: read. A job cannot escalate permissions; packages, id-token, attestations,
artifact-metadata, actions, deployments, issues, pull-requests and contents write are
forbidden.

Every external action uses a complete immutable commit SHA. Checkout keeps
persist-credentials false and checks out the exact pull-request head SHA or exact main
push SHA. Secrets context, credential printing, generated authentication, Docker registry
login, docker push, build-push with push true, Cosign sign or attest, gh release, git push,
git tag, package publish/upload, workflow-artifact upload, and any equivalent publication
or remote mutation are forbidden. The checker uses exact syntax and negative fixtures,
not substring absence alone, to reject aliases, nested commands and permission or trigger
bypasses.

The accepted P11R repository gate intentionally rejects any tag that contains its
acceptance commit. Applied directly to all future descendants, that historical
phase-specific sentinel would reject a later authorized release tag. P12 MUST preserve the
P11R checker byte-identically and replay it only on the exact accepted P11R object. The
new P12 current checker independently requires zero tags and zero Releases for P12 and
continues to forbid all publication.

Before any future tag or Release, a later fixed acceptance contract, no earlier than P20,
must replace the current phase-local zero-descendant-tag rule with an exact allowlist for
one authorized release commit, tag name, target, annotated object, Release identity and
publication sequence. It must continue to reject every unlisted tag or Release and cannot
reinterpret a historical P11R result. No P12–P19 acceptance authorizes that transition or
a publication.

## Evidence-before-write read-only preflight

The evidence preflight runs after exact implementation-head CI succeeds and before any
evidence-generation authorization. It is read-only, writes only inside OS temporary
directories, performs no repository or remote mutation, and leaves worktree, index,
untracked files, credential stores, environment overrides, caches and Docker state
unchanged. Any missing capability, identity mismatch, unsafe output, or ambiguous result
fails closed before the evidence writer can run.

The operator supplies the exact P12_FINAL_IMPLEMENTATION_HEAD, an explicit numeric CI run
ID, and a newly created OS-temporary receipt directory outside the repository. The
preflight MUST NOT select latest, infer a run from a branch, accept a run URL in place of
its numeric identity, or follow a moving ref. The implementation provides
make p12-evidence-preflight with these ordered checks.

### GitHub and GHCR access

1. Confirm an active gh authentication context for the exact repository and required
   read-only repository, pull-request and Actions-run operations. Do not log in, refresh,
   change scopes, write configuration, print a token, or display authorization headers.
2. Confirm read:packages capability. A printed scope claim alone is insufficient: the
   preflight must successfully perform a read-only manifest lookup for every exact
   protected active and superseded GHCR digest below and verify subject and digest.
3. Confirm the explicitly supplied implementation-head workflow run exists in the exact
   repository, has the accepted workflow path, expected pull_request event and PR, head SHA
   exactly P12_FINAL_IMPLEMENTATION_HEAD, completed successfully, and has every required
   job conclusion. Branch name, latest-run status, or a successful run for another commit
   is insufficient.
4. Sanitize output to repository, workflow/run numeric identity, commit/digest, safe
   capability result and status. Never persist a token, authorization header, credential
   helper response, personal account identifier, or provider payload.

### Declared and installed Python versions

The fixed declaration sources are:

| Source | Exact identity | Purpose |
| --- | --- | --- |
| pyproject.toml | Git blob 77df2013d93d8b8b6d0441cccb44a127f9c88f07; file SHA-256 25683ddd04aa1f2abf21ae60d42a1a44bb7e198d721cfa6d452b8fb61483c15a | Direct project dependency names and PEP 508 specifiers |
| requirements/p8.lock | Git blob 819980980ba87d1b7166af4b4b0da53ca4e4ac63; file SHA-256 5afb5bc2f6bf2cfdc77d0457b92255f822d89cd3cd754ebb876741d7ee6430d0 | Hash-locked toolchain and transitive package pins |

The preflight MUST verify the exact path, Git blob, Git mode 100644, working-tree
regular-file and non-symlink status, and SHA-256 of both pyproject.toml and
requirements/p8.lock before reading declarations. It installs the accepted environment in
an OS temporary virtual environment using the equivalent of pip --isolated
--require-hashes --no-deps --no-cache-dir, with temporary cache/config locations. It does
not mutate a repository environment or use user/system package configuration.

Direct dependencies and their declared constraints are read from the project dependencies
in pyproject.toml. Toolchain and transitive locked dependencies, including certifi and
packaging, are read from the P12-accepted hash-locked requirements file. The preflight
MUST NOT require every checked package to exist in pyproject.toml.

Installed versions are obtained with importlib.metadata.version() executed by the exact
OS-temporary virtual-environment interpreter. Declared requirements are parsed as PEP 508
requirements, and every declared, locked and installed version is normalized and compared
with packaging.version.Version under PEP 440. Direct dependency versions must satisfy
their parsed project specifiers; locked dependencies must equal their normalized exact
pins. Lexical, substring, prefix, tuple, ad-hoc regular expression, or hand-written split
comparison is forbidden.

The following locked tool identities are additionally fixed:

| Package | Exact locked version | Accepted wheel hash |
| --- | --- | --- |
| certifi | 2026.7.22 | sha256:62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775 |
| packaging | 26.3 | sha256:d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c |

The installed certifi and packaging distributions must report exactly those PEP
440-normalized versions. Absence, duplicate ambiguity, an unparseable requirement, a
non-exact locked pin, a hash mismatch, or a specifier mismatch fails closed.

Version-comparison bootstrap is explicit: pip first verifies and installs the accepted
packaging wheel from the hash-locked file. Only then may that exact installed distribution
provide packaging.version.Version to compare its own reported version and every other
declared, locked and installed value. No unverified host packaging module establishes
trust.

### TLS certificate-authority handling

Certificate- and hostname-verified TLS to api.github.com and ghcr.io always uses the system
or runtime default certificate authorities first. If and only if that certificate-chain
verification fails for the same exact hostname, the preflight may retry that destination
using the certifi CA bundle from the exact hash-locked environment above. DNS, timeout,
authorization, registry-status, proxy, hostname, protocol, content, or any other failure
does not authorize a CA fallback.

Before the certifi fallback, the preflight MUST verify:

- requirements/p8.lock has the exact path, blob and SHA-256 fixed above;
- certifi is locked and installed at normalized version 2026.7.22;
- its accepted wheel hash is the exact value above;
- the resolved CA bundle is a regular file and not a symlink; and
- the bundle SHA-256 is exactly
  9cc2a774b5198dcff14d9be1e66091f538975d867ce029a96bce15a55dfd730f.

The retry may use only a certificate-verifying explicit SSL context with that bundle as
cafile, or SSL_CERT_FILE scoped to one subprocess and removed immediately afterward.
Hostname verification and certificate verification remain enabled. The following are
forbidden: --insecure, -k, unverified SSL contexts, disabling hostname verification,
global or persistent SSL_CERT_FILE, modification of system trust, arbitrary CA paths, and
any unverified fallback.

Public output and committed evidence MUST NOT contain an absolute CA path, certificate or
bundle content, token, credential, user/account path, or secret. It may record only
system_default or locked_certifi as the safe CA class, the locked certifi version, the
expected bundle SHA-256, the destination host class, and pass/fail status.

### Preflight receipt and authorized handoff

The successful preflight creates one canonical redacted receipt in the caller-provided
OS-temporary directory, never in the repository. The directory is mode 0700. The receipt
is atomically created as a regular non-symlink file with mode 0600 and canonical JSON; its
SHA-256 is printed with safe status. It binds exact repository, acceptance commit/blob,
implementation head/tree, explicit workflow/run/PR/event and required jobs, protected
GHCR inventory, pyproject and lock identities, normalized package results, CA class and
digest, timestamp, single-use nonce, preflight-environment cleanup before receipt
creation, and receipt lifecycle pending_consumption. It contains no secret, token,
credential, private/live payload, personal account identity, absolute CA path or
certificate content.

The preflight does not create artifacts/p12/summary.json. The later evidence authorization
MUST explicitly name the receipt SHA-256, exact implementation head, numeric CI run ID and
an expiration for that authorization. The evidence writer receives an explicit receipt
path and expected digest, requires a regular non-symlink mode-0600 file outside the
repository, re-hashes and parses canonical JSON, verifies the named authorization, head,
tree, run and still-current read-only identities, and consumes the nonce once. It never
accepts an environment boolean, copied console text, caller-supplied result fields,
latest-run lookup, or a receipt for another head.

The committed summary stores the receipt digest and safe fields but never its absolute
path. The writer removes the temporary receipt and directory before writing the summary
and records that cleanup as passed; a later summary write failure therefore requires a
fresh preflight. An unused receipt and environment are removed on explicit abandonment.
Any implementation/correction commit, CI rerun selection, receipt change, expired
authorization, identity drift, dirty repository, or failed recheck invalidates the handoff
and requires a fresh preflight and new evidence authorization.

## P10 complete protected publication identity

P10 is the sole authorized historical publication before P20. Both active and superseded
sets are permanently protected. The fixed GHCR subjects are:

~~~text
ghcr.io/jeremyliu1220/digital-colleagues-runtime
ghcr.io/jeremyliu1220/digital-colleagues-studio
~~~

The fixed remote verification identity is:

| Field | Exact value |
| --- | --- |
| GitHub repository | jeremyliu1220/digital-colleagues |
| Historical workflow | .github/workflows/ci.yml |
| Historical workflow ref | refs/heads/codex/p10-mac-quickstart |
| OIDC issuer | https://token.actions.githubusercontent.com |
| Certificate identity | https://github.com/jeremyliu1220/digital-colleagues/.github/workflows/ci.yml@refs/heads/codex/p10-mac-quickstart |
| Required platforms | linux/amd64 and linux/arm64 |

### Fixed Git and receipt identities

| Item | Exact identity |
| --- | --- |
| P10 final commit | 4bef5629d450c6bb3940f606fc90194e008ee8fd |
| P10 final tree | 909b566b7ba9f7beb143cd0b29cf95fbd1178bbe |
| P10 acceptance commit | 99b0045bba48de8e4d44c10ce07d60ba20738a8b |
| P10 acceptance blob | c5ac3acd52a8732da617ce5d1d3a7e66e3671c80 |
| P10 implementation used by evidence | 0f7e15935d27549783480f1f55dbfcb036e49293 |
| P10 summary blob | a4c1a59fffec9c30160787a7bec584e228fb9f35 |
| P10 receipt path | provenance/p10-migration-receipt.json |
| P10 receipt blob | 07565307a35902206ee7c80af66b2a02ab876b83 |
| P10 verification-policy blob | 02aff9c1f3bdd745a6fc479fed635f2f782c346a |
| P10 distribution-document blob | c55393db711f2db49169fbe35e45f5f5e227849a |

### Superseded protected publication set

| Field | Exact identity |
| --- | --- |
| Source commit and immutable GHCR discovery tag | 05e73ea23ac650edfae59fa409a770fdf967af3a; sha-05e73ea23ac650edfae59fa409a770fdf967af3a |
| Runtime digest | sha256:41567ba87a088944cf9a2c17b9b0f4359554c66b2ec1f6d52db46067e1ab9092 |
| Studio digest | sha256:b7dd4c2b35922ec31a9b38c15316283706a9aab0ffab2101a18f7bf106165f2e |
| Lifecycle | superseded_contract_noncompliant_source |
| Publication run | 34202520699; head 05e73ea23ac650edfae59fa409a770fdf967af3a; success |

The superseded verification history is also immutable:

| Verification run | Exact head | Historical outcome |
| --- | --- | --- |
| 34203006909 | 05e73ea23ac650edfae59fa409a770fdf967af3a | failed |
| 34204280131 | ddc04021f94ca888235c53f96ed64218de8c3e67 | failed |
| 34204837101 | ae714c128f844466c76811986c0605e39fce12cc | failed |
| 34205272328 | 76b278feedbb79b9a4c0d023e328911096fe57ae | failed |
| 34206039435 | a003d540093df9a08437c47e9c8ff16970e5e645 | technical verification succeeded; lifecycle remained superseded_contract_noncompliant_source |

### Active protected publication set

| Field | Exact identity |
| --- | --- |
| Source commit and immutable GHCR discovery tag | 62b226064d2597a4ca6a67f9f2c20a79a815732b; sha-62b226064d2597a4ca6a67f9f2c20a79a815732b |
| Runtime digest | sha256:a5bb41bdb85bf7b5a75dc79967e26943c098b024b64fdd345f5b4c6f4688991d |
| Studio digest | sha256:7791d80d9fa464bbd1574601deba5a30ca6d980dab8c8275c24c117fae81e4c9 |
| Set classification | active |
| Lifecycle | passed |
| Publication run | 34235760264; head 62b226064d2597a4ca6a67f9f2c20a79a815732b; success |
| Fail-closed verification | 34236719816; head d9fd27670a36f699bf299f6154afce180bea64cc; failed |
| Accepted verification | 34237810474; head cc4acd3bda3f4d2bdfee9392c7d0f85f90c07688; success |

### Exact P12-start GHCR inventory oracle

At P12 start each public subject has exactly 14 GitHub Packages versions and exactly four
tagged versions: the two GHCR source-discovery tags above and the two digest-derived
attestation-discovery tags below. The runtime newest created/updated timestamp is
2026-09-08T14:04:47Z; the Studio newest created/updated timestamp is
2026-09-08T14:06:17Z. The complete exact inventory is protected.

Runtime subject:

| Version ID | Manifest name | Exact tags, or none | Created/updated UTC |
| ---: | --- | --- | --- |
| 1223596354 | sha256:2dea0deee746cee825554cd0f54eb0bfd7ea98597a15e5f636964f8ecaebc727 | sha256-a5bb41bdb85bf7b5a75dc79967e26943c098b024b64fdd345f5b4c6f4688991d | 2026-09-08T14:04:47Z |
| 1223596303 | sha256:38e01b5e9ac7b62033208018a0d796033746c4f8a59a90cb9592ae21a1fdcdb6 | none | 2026-09-08T14:04:47Z |
| 1223596004 | sha256:c9292efc2728c71e96eac86d7e6ed003a2406328d262414508ddb79cb824e498 | none | 2026-09-08T14:04:43Z |
| 1223595963 | sha256:4ba4008c25fed2b5dd13d327cd9c908db72c3550e2a8c9ee59bd8057c09627cf | none | 2026-09-08T14:04:43Z |
| 1223595656 | sha256:a5bb41bdb85bf7b5a75dc79967e26943c098b024b64fdd345f5b4c6f4688991d | sha-62b226064d2597a4ca6a67f9f2c20a79a815732b | 2026-09-08T14:04:38Z |
| 1223595627 | sha256:81389bd2e8b66c0f3d3b231f2e53a0083d1fd48116c0c0e5f3d5239b50333f17 | none | 2026-09-08T14:04:38Z |
| 1223595581 | sha256:cf4ab5111ccf7ee4cec251d9bf0b338a7548d36dc0f57d6ea7c1090eb3196f4a | none | 2026-09-08T14:04:37Z |
| 1222058752 | sha256:a937250e86d42646c1ad32544f9a7f0d953bf3da781891cf189f209d8428c994 | sha256-41567ba87a088944cf9a2c17b9b0f4359554c66b2ec1f6d52db46067e1ab9092 | 2026-09-08T08:06:17Z |
| 1222058727 | sha256:ab004cc7647993acf9aba9c9a2aebb84c3088861bce5df4828906211339236ca | none | 2026-09-08T08:06:17Z |
| 1222058565 | sha256:f00db473ce44bcaed4c287f27e19e6d47c9be15f115bdf794b1dd7646fec4089 | none | 2026-09-08T08:06:14Z |
| 1222058542 | sha256:d3a6d093739a17a575f2a4e7aaf232653a8daecb0a44a1e73342918160f95398 | none | 2026-09-08T08:06:14Z |
| 1222058316 | sha256:41567ba87a088944cf9a2c17b9b0f4359554c66b2ec1f6d52db46067e1ab9092 | sha-05e73ea23ac650edfae59fa409a770fdf967af3a | 2026-09-08T08:06:10Z |
| 1222058301 | sha256:d80c62bbb6873dd9d3aa5706db24e6715d25633453f09dea55ab02c4d31e346d | none | 2026-09-08T08:06:10Z |
| 1222058289 | sha256:9388bfaa10eb794800f9c12186c44900e2f7332afdcbbafd94871706ead4bc95 | none | 2026-09-08T08:06:10Z |

Studio subject:

| Version ID | Manifest name | Exact tags, or none | Created/updated UTC |
| ---: | --- | --- | --- |
| 1223603770 | sha256:0a10ae8c48ff37b3d5c58dabcfc8519e2b9e1f7cd6a40792c217d4a19ccd0e95 | sha256-7791d80d9fa464bbd1574601deba5a30ca6d980dab8c8275c24c117fae81e4c9 | 2026-09-08T14:06:17Z |
| 1223603735 | sha256:cf10121213d11e57b004cc5b7b05a79c025815f1e3ae5f789f77756e8ef08c02 | none | 2026-09-08T14:06:17Z |
| 1223603457 | sha256:954a75ca58f3be43a1f3d4c2599f40be23b2bf9019c3475720140d20e769b733 | none | 2026-09-08T14:06:13Z |
| 1223603414 | sha256:e93c97a7f6cd829cb5037ddeb04b4150c53fa4838fcc55e39920b33775a9287a | none | 2026-09-08T14:06:13Z |
| 1223603070 | sha256:7791d80d9fa464bbd1574601deba5a30ca6d980dab8c8275c24c117fae81e4c9 | sha-62b226064d2597a4ca6a67f9f2c20a79a815732b | 2026-09-08T14:06:09Z |
| 1223603034 | sha256:382636e1a836dace37f08d65908acc20ddfd4027fd926509c75739c316b563ab | none | 2026-09-08T14:06:08Z |
| 1223602981 | sha256:ac7bd9d8d11ab90141853de41489dddf9cf8047271966a95008ceb29b438fff4 | none | 2026-09-08T14:06:08Z |
| 1222065029 | sha256:4033258fb21fb5dc212fd946588166d1b0a563b54b4943478d79b2e8931c49ec | sha256-b7dd4c2b35922ec31a9b38c15316283706a9aab0ffab2101a18f7bf106165f2e | 2026-09-08T08:07:52Z |
| 1222065003 | sha256:eaf013db7c08cbc6a9ba07e308a6aa2489b17afe92160712df74a43e120f8aa5 | none | 2026-09-08T08:07:51Z |
| 1222064852 | sha256:4b05fe4a65ade3a12787e8d4334c60febfc40200b00330f435386b57e00d2804 | none | 2026-09-08T08:07:49Z |
| 1222064826 | sha256:17929d49e629e4fdb04d8f4f2803fa58ec8f974cbe69da7150d6beb0c149cb22 | none | 2026-09-08T08:07:48Z |
| 1222064639 | sha256:b7dd4c2b35922ec31a9b38c15316283706a9aab0ffab2101a18f7bf106165f2e | sha-05e73ea23ac650edfae59fa409a770fdf967af3a | 2026-09-08T08:07:44Z |
| 1222064624 | sha256:5003141f6bc213290ec7a336b7c23c50881d8faddfdd5dfc2dd9765624406089 | none | 2026-09-08T08:07:44Z |
| 1222064604 | sha256:754868c189b1a94689d57c48c3dd845f8ebfa4660c99aeb7fbbd4d1e4e74a602 | none | 2026-09-08T08:07:44Z |

The start, evidence-preflight, final-candidate and remote-closeout checks canonicalize the
GitHub Packages API response and require these exact two 14-version sets, ID/name/tag
mappings and timestamps. An extra, missing, moved, renamed, retagged or updated version,
new tag, changed visibility, changed subject or unreadable object fails closed as an
unauthorized-publication or protected-identity violation.

The publication workflow identity for both sets is
.github/workflows/ci.yml on refs/heads/codex/p10-mac-quickstart, with the exact historical
run identities above. All nine fixed runs have workflowName CI, event workflow_dispatch,
status completed, and headBranch codex/p10-mac-quickstart; database ID, head SHA and
conclusion are exactly the table values. A technical success does not change a recorded
superseded lifecycle.

No phase may overwrite a manifest, move or reuse a protected GHCR discovery tag, retag a
protected digest, republish an existing set, or delete a package subject, package version,
index, platform manifest, config, layer, discovery tag, signature, attestation, bundle,
publication run or verification run. It may not replace a signature or attestation, alter
lifecycle, or present the superseded set as active. P12–P19 are entirely read-only toward
both sets. If P20 later receives publication authorization, every new image requires a new
source commit, new immutable GHCR discovery tag, new digest, new signature and attestation,
new run identities and a distinct lifecycle record; it cannot mutate these identities.

## P12 authorization stages

| Stage | Required input and authorization | Allowed action | Required output and stop |
| --- | --- | --- | --- |
| 1. Acceptance contract | Exact clean base and explicit acceptance-contract authorization | Create the exact branch, add only this file, make first single-parent commit | Report branch, base/tree, commit/blob, validations; stop for implementation authorization |
| 2. Governance implementation | Independent explicit authorization naming the fixed acceptance commit/blob | Add one or more allowlisted implementation commits; run local gates | No remote mutation; stop when local implementation head is clean and fully passing |
| 3. Scoped local correction | A failed in-scope gate or independently identified in-scope review defect, plus explicit scoped correction authority | Append minimum implementation/test correction commits; never acceptance or summary | Rerun all affected and aggregate local gates; retain every failed result, finding and commit |
| 4. Push and pull request | Explicit remote-mutation authorization after local gates | Push the complete implementation chain and open one PR containing contract plus implementation | Contract-only commit is never pushed as a standalone PR; no evidence summary yet |
| 5. Exact implementation-head CI | PR head exactly equals P12_FINAL_IMPLEMENTATION_HEAD | Run current and historical gates on that exact SHA | All required jobs succeed; failure returns to an explicitly authorized append-only correction loop |
| 6. Read-only evidence preflight | Exact successful implementation CI plus explicit implementation SHA and numeric run ID | Verify GH/GHCR, CI, TLS, package identities and create only the external temporary receipt | Report safe receipt digest and stop; no repository artifact |
| 7. Evidence authorization | Project owner reviews the exact head, numeric CI run and preflight receipt | Explicitly name receipt digest, head, run ID and authorization expiry | No command or mutation implied |
| 8. Evidence write | Valid unexpired evidence authorization and exact external receipt | Run make evidence-p12 and consume the receipt once | Produce only artifacts/p12/summary.json in the worktree |
| 9. Summary-only commit | Evidence output validates against the full implementation/correction set | Commit only artifacts/p12/summary.json with final implementation head as sole parent | Establish exact final candidate; no later commit |
| 10. Final-candidate push | Separate explicit remote-mutation authorization | Push the summary-only descendant without rewrite | Remote PR head equals exact final candidate |
| 11. Exact final-candidate CI | Remote head equals the summary commit | Run the complete current and historical gate on exact final SHA | All required jobs succeed; record run externally because the commit cannot recursively contain its own later run |
| 12. Independent acceptance | Exact contract, implementation set, both CI runs, summary, provenance and clean branch | Read-only independent review | Accept or reject exact final candidate; no correction after summary |
| 13. Final acceptance | Separate project-owner decision on the independently accepted exact candidate | Record authorization outside immutable candidate | No merge or push implied |
| 14. Fast-forward merge | Separate explicit local merge authorization | Fast-forward local main only from unchanged accepted base | Verify exact candidate/main identity and clean state |
| 15. Main push | Separate explicit remote-main authorization | Push exact fast-forward main | No tag, Release or publication |
| 16. Remote closeout | Exact remote-main CI and read-only remote checks | Verify main, tags, Releases, P10 identities and absence of publication | Close P12; only then may P13 acceptance planning be authorized |

Every correction commit and every remote mutation requires the applicable explicit scope;
no blanket authorization is inferred. A CI run for an ancestor, merge result, recreated
tree, or different SHA is not exact-head CI. Any new implementation or correction commit
invalidates the selected implementation-head CI result, preflight receipt and evidence
authorization; stages 5 through 7 must be repeated for the new exact head.

The summary binds exact implementation-head CI. Exact final-candidate CI necessarily
occurs after the immutable summary commit and is therefore bound by run ID and head SHA in
the independent acceptance and remote closeout record, not by rewriting the summary.

## P12 evidence, provenance, and claim boundary

The P12 receipt records only non-self-referential provenance inputs and coverage: exact
base, branch, acceptance commit/blob, exact path allowlist and classifications, zero
migrated source files, zero source-checkout reads during P12 implementation, immutable
migration identities, historical anchors and protected P10 identities. It does not claim
its own future blob, containing commit, final implementation head/tree, or complete range
digest. The summary and evidence checker compute and bind the committed receipt blob, the
ordered implementation/correction set, final implementation head/tree and range digest
after those Git objects exist. Absolute local paths, credentials, live payloads and
personal data are forbidden.

The P12 evidence writer is deterministic and may write only artifacts/p12/summary.json
after authorization. It consumes already completed local results, exact Git objects and
the exact implementation-head CI identity. It performs no live-provider call, remote
write, publication, login, credential change or historical evidence invocation.

The public summary may claim only:

- exact fixed contract and governance identities;
- complete P12 static and synthetic_offline gate results;
- unchanged product/runtime/schema/migration behavior;
- current-CI governance transition;
- zero source migration, zero private/live data and zero publication; and
- not_evaluated for every live OpenAI, Microsoft 365, human, soak or release result.

P13–P19 mechanism gates may be accepted on all of their required deterministic, synthetic
and local evidence while unavailable private-live results remain not_evaluated. P15 and
P16 still require their complete local restart and lifecycle E2Es; P17 and P18 still
require their complete deterministic and local multi-worker/effect mechanisms. No such
acceptance creates a named-provider, real-delivery, HUMAN-evaluation, soak, or Public Pilot
claim.

A Public Pilot claim is blocked until P20 proves every mandatory private-live environment,
the complete wait/reply/resume chain, blank-chat recovery, memory lifecycle, schedule and
recovery behavior, authority drift, bounded proactivity, effect/reconciliation safety,
72-hour ten-deployment soak, required HUMAN evaluation, encrypted-storage readiness,
operator recovery, safe evidence and release identity. Any not_evaluated item in that
mandatory set blocks the claim. No milestone claims production readiness.

## Decisions reserved for later project-owner authorization

The B+ sequence and contracts in this file are decided. The following are not delegated to
implementation:

- authorization to start P12 governance implementation;
- every P12 scoped correction that exceeds an already authorized minimum defect scope;
- P12 push/PR, evidence generation, final-candidate push, independent acceptance, final
  acceptance, fast-forward merge, main push and remote closeout;
- each P13–P20 acceptance contract and implementation start;
- the exact P13 OpenAI model snapshot, pricing/cost ceiling, connection mode and
  private-live account before named-provider evidence;
- P14/P20 Microsoft application modes, tenant/account inventory, consent, resource
  allowlists and private-live evidence boundary;
- any relaxation or change to the memory bounds, temporal semantics, initial automatic-
  effect allowlist, ten-deployment bound or 72-hour soak;
- any need for migration 015 or another schema owner;
- P20 version, release commit, tag, Release, signing, attestation, package/image
  publication and public announcement; and
- any claim of live compatibility, Public Pilot readiness, or a capability presently
  marked not_evaluated.

Within an independently authorized phase, implementers may choose ordinary internal names,
module factoring and algorithms only when they preserve every fixed public schema,
authority boundary, deterministic behavior, limit, allowlist, gate and evidence identity.
A choice that changes a contract, external behavior, security/privacy boundary, migration,
dependency, path set, evidence claim or authorization stage returns to the project owner.

## Acceptance-contract phase verification

Immediately after the acceptance-only commit, all of the following MUST pass:

1. the v2 commit has exactly one parent;
2. that sole parent is c1562ea5201394d8a278f4b644daf4029cbb5bd4;
3. the parent tree is ae0f33263cfc7445fef69656ad9c5cb04d4a2d00;
4. the v2 branch contains only the acceptance commit above the exact base, with no
   implementation or correction commit;
5. the changed-path set is exactly docs/p12/acceptance.md;
6. the acceptance blob and working-tree file are byte-identical;
7. git diff --check over the exact parent-to-commit range succeeds;
8. worktree, index and untracked state are clean;
9. the v1 local branch still points exactly to
   8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3 and has not been amended, reset, moved or
   deleted;
10. the v1 commit is not an ancestor of the v2 acceptance commit;
11. local main and origin/main remain the exact base;
12. both v1 and v2 remote candidate branches and pull requests remain absent;
13. local and remote tags remain zero and GitHub Releases remain zero;
14. no implementation, remote mutation or unauthorized publication occurred; and
15. the protected P10 active and superseded identities remain readable and unchanged.

With P12_ACCEPTANCE_COMMIT set by the reviewer to the exact reported 40-character commit,
the repeatable post-commit commands are:

~~~sh
set -e
test "$(git symbolic-ref --quiet --short HEAD)" = "codex/p12-public-pilot-continuity-rebaseline-v2"
test "$(git rev-parse HEAD)" = "$P12_ACCEPTANCE_COMMIT"
test "$(git rev-list --parents -n 1 HEAD | awk '{print NF}')" = "2"
test "$(git rev-parse HEAD^)" = "c1562ea5201394d8a278f4b644daf4029cbb5bd4"
test "$(git rev-list --count c1562ea5201394d8a278f4b644daf4029cbb5bd4..HEAD)" = "1"
test "$(git show -s --format=%T HEAD^)" = "ae0f33263cfc7445fef69656ad9c5cb04d4a2d00"
test "$(git rev-parse refs/heads/codex/p12-public-pilot-continuity-rebaseline)" = "8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3"
test "$(git rev-parse 8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3^)" = "c1562ea5201394d8a278f4b644daf4029cbb5bd4"
test "$(git rev-parse 8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3:docs/p12/acceptance.md)" = "26562d795980ec8d6d9ea36ff3fcc718b41c09e8"
if git merge-base --is-ancestor 8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3 "$P12_ACCEPTANCE_COMMIT"; then exit 1; fi
test "$(git diff-tree --no-commit-id --name-only -r HEAD)" = "docs/p12/acceptance.md"
test "$(git diff-tree --no-commit-id --name-status -r HEAD)" = "$(printf 'A\tdocs/p12/acceptance.md')"
test "$(git rev-parse HEAD:docs/p12/acceptance.md)" = "$(git hash-object docs/p12/acceptance.md)"
git diff --check HEAD^ HEAD
test -z "$(git status --porcelain=v2 --untracked-files=all)"
test "$(git rev-parse main)" = "c1562ea5201394d8a278f4b644daf4029cbb5bd4"
test "$(git rev-parse origin/main)" = "c1562ea5201394d8a278f4b644daf4029cbb5bd4"
test "$(git ls-remote --heads origin refs/heads/main | awk '{print $1}')" = "c1562ea5201394d8a278f4b644daf4029cbb5bd4"
test -z "$(git ls-remote --heads origin refs/heads/codex/p12-public-pilot-continuity-rebaseline)"
test -z "$(git ls-remote --heads origin refs/heads/codex/p12-public-pilot-continuity-rebaseline-v2)"
test "$(gh pr list --repo jeremyliu1220/digital-colleagues --state all --head codex/p12-public-pilot-continuity-rebaseline --json number --jq 'length')" = "0"
test "$(gh pr list --repo jeremyliu1220/digital-colleagues --state all --head codex/p12-public-pilot-continuity-rebaseline-v2 --json number --jq 'length')" = "0"
test -z "$(git tag --list)"
test -z "$(git ls-remote --tags origin)"
test -z "$(gh release list --repo jeremyliu1220/digital-colleagues --limit 100)"
test "$(git ls-remote --heads origin refs/heads/codex/p10-mac-quickstart | awk '{print $1}')" = "4bef5629d450c6bb3940f606fc90194e008ee8fd"
for P12_P10_RUN_ID in 34202520699 34203006909 34204280131 34204837101 34205272328 34206039435 34235760264 34236719816 34237810474; do
  gh run view "$P12_P10_RUN_ID" --repo jeremyliu1220/digital-colleagues --json databaseId,headSha,headBranch,event,status,conclusion,workflowName,url || exit 1
done
gh api /users/jeremyliu1220/packages/container/digital-colleagues-runtime
gh api /users/jeremyliu1220/packages/container/digital-colleagues-studio
gh api --paginate /users/jeremyliu1220/packages/container/digital-colleagues-runtime/versions
gh api --paginate /users/jeremyliu1220/packages/container/digital-colleagues-studio/versions
PYTHONDONTWRITEBYTECODE=1 make p10-remote-distribution
test -z "$(git status --porcelain=v2 --untracked-files=all)"
~~~

The package metadata and two version responses again require canonical exact equality to
the fixed subjects, public visibility and inventory, not merely exit zero. Every run
response must equal its fixed database ID, head SHA, branch, event, completed status,
conclusion and workflow name. The final status check is repeated after remote/P10
read-only verification to prove zero residue. Any post-commit mismatch stops without
amend, replacement commit, push, or implementation.

Success establishes only the immutable P12 acceptance contract and readiness to wait for
independent P12 governance implementation authorization.
