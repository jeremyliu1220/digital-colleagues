<!-- SPDX-License-Identifier: Apache-2.0 -->

# P12 v4 Historical Platform Classification Rebaseline Acceptance Contract

Status: proposed immutable acceptance contract drafted repository-external during canonical
Stage 2. This file is complete and self-contained. It does not depend on a conversation,
the rejected or superseded v1/v2/v3 contract text, or access to a planning attachment. If
Stage 3 independently validates these exact bytes and later stages are separately
authorized, Stage 6 installs this file alone as `docs/p12/acceptance.md` in the first commit
on the P12 v4 replacement branch, with the exact accepted main commit as sole parent. The
committed file then remains byte-identical for the lifetime of the P12 v4 attempt.

This text incorporates the approved repository-external Change Decision / Blueprint with
these fixed source identities:

| Field | Exact value |
| --- | --- |
| Source name | `p12-v4-historical-platform-classification-change-decision-blueprint.md` |
| Line count | 1183 |
| Byte count | 223853 |
| SHA-256 | `7f58f95e7f33f65348162754017da828a9db6272d0d2cec22dd7b91ace0a8263` |
| Prospective Git blob | `854cd5691cfca94edfc1ffc1ed6a73e44a074667` |

The Blueprint identity is a design provenance anchor only. It is not a repository runtime
dependency, evidence artifact, authority source, or substitute for any clause below. Once
established, the committed acceptance contract alone is the immutable P12 v4 acceptance
source of truth.

Drafting this file completes only canonical Stage 2. It authorizes no Stage 3 validation,
WIP snapshot, Git worktree, branch, commit, implementation, correction, evidence operation,
push, pull request, CI run, merge, tag, Release, publication, P13 work, or remote mutation.
Every later stage and every state-changing action requires its own explicit project-owner
authorization.

## Normative language and claim vocabulary

The words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, and MAY are
normative. A condition that cannot be established exactly fails closed.

Evidence and evaluation states are:

- `passed`: the fixed repeatable gate executed successfully against the exact identified
  object on the stated platform;
- `failed`: the gate executed and did not satisfy the contract;
- `blocked`: an exact prerequisite or readiness condition is unsatisfied, so no positive
  claim is permitted;
- `not_proven`: the platform-scoped historical gate was intentionally not executed on the
  stated platform because faithful execution is impossible under the immutable accepted
  object; it is neither success nor failure evidence for that platform;
- `not_evaluated`: required access, environment, consent, or authorized evidence execution
  was unavailable, so no positive claim is permitted; and
- `not_applicable`: this contract explicitly makes a check inapplicable and records why.

`not_run_platform_excluded` is an executor result for a statically classified excluded
inventory item. It MUST carry a null exit status and platform-qualified `not_proven`; it is
not `passed`, `skipped`, `waived`, `equivalent`, `accepted_by_analogy`, or a replacement
result. Skipped, unavailable, inferred, partially observed, captured from another commit,
or manually asserted results are never passed. Static and synthetic evidence cannot
establish a live-provider, HUMAN-evaluation, reliability, security, privacy, production,
or Public Pilot claim.

## Preserved rejected and superseded v1, v2, and v3 attempts

P12 v1 and v2 are rejected immutable attempts. P12 v3 is a superseded immutable
established acceptance-only attempt that never became an accepted final P12
implementation or closeout. None authorizes publication, and none may be used as the base
or an ancestor of P12 v4. The v3 acceptance commit remains immutable established history
of that superseded attempt; it is not relabeled as a rejected v1/v2 acceptance.

### Rejected v1 local-only attempt

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
drifted from the approved core-record contracts.

### Rejected v2 Linux-historical-replay-infeasible attempt

| Field | Exact value |
| --- | --- |
| Branch | codex/p12-public-pilot-continuity-rebaseline-v2 |
| Acceptance commit | 3639fa08ca44820bb922e0644095c9fb9c24d3e6 |
| Acceptance tree | 71c411660e0f7ff26e8ad1451acaa0ea26fa384b |
| Acceptance blob | 50453e154cf642bc7b90644660e1d956b04f966a |
| Acceptance file SHA-256 | be3ad1967a98c67ae34ad7c22c35a9ec1f637a780c930ae4e8349f126e64800b |
| Final v2 candidate HEAD | 8e08c3891dc8f761ada096c3f829ef31d3fbfd7c |
| Final v2 candidate tree | 01ee7b08cc870a626698ac9a3fc46ec92bf0f4e0 |
| Pull request | jeremyliu1220/digital-colleagues#14; CLOSED without merge; mergedAt null; mergeCommit null; autoMergeRequest null |
| Earlier failed workflow run | 34542709145; head fc145550b750c172899bc1497ff5fede387c07dc; pull_request / CI; attempt 1; completed/failure; no reclassification |
| Final-head failed workflow run | 34564478590; exact final v2 candidate head above; pull_request / CI; attempts 1 and 2; both completed/failure |
| Attempt 1 lifecycle | created 2026-09-11T05:03:14Z; completed/updated 2026-09-11T05:06:34Z |
| Attempt 2 lifecycle | created 2026-09-11T05:12:52Z; completed/updated 2026-09-11T05:16:00Z |
| Draft-time Actions retention | 90 days; maximum allowed 90 days |
| Conservative earliest normal-expiry boundary | 2026-12-10T05:03:14Z; attempt-1 created_at plus 90 days; actual removal may occur later |
| Safe failure boundary | accepted P8 actual Compose runtime, pre_start_restore |
| Summary, evidence, merge, tag, Release, publication | none |
| Rejection classification | rejected_linux_historical_replay_contract_infeasible |

The v2 implementation was governance-only. Run 34542709145 attempt 1 remains a recorded
historical-replay failure without reclassification. Both attempts of final-head run
34564478590 reached the
accepted-P8 actual Compose path and failed because the GitHub Ubuntu host UID 1001 owns a
0700 operator directory and 0600 private files while the immutable container runs as
UID/GID 10001:10001. Native Linux bind-mount permissions therefore prevent the container
from reading and writing the accepted private-state mount. Accepted P8 suppresses the
container stdout and stderr at that boundary, so an outer log tail cannot recover the
discarded error. This is a contract/platform infeasibility, not proof that P12 governance
logic failed and not permission to change accepted P8.

The exact v2 commit chain is preserved:

| Commit | Sole parent | Tree | Purpose |
| --- | --- | --- | --- |
| 3639fa08ca44820bb922e0644095c9fb9c24d3e6 | c1562ea5201394d8a278f4b644daf4029cbb5bd4 | 71c411660e0f7ff26e8ad1451acaa0ea26fa384b | acceptance-only v2 contract |
| eb4dbc7e1cd1c1a1671f58441bb3e49d08e77a5e | 3639fa08ca44820bb922e0644095c9fb9c24d3e6 | 42c05dea50cfe45b92a055c835e63045ec88a082 | living-document alignment |
| 5d0818ab9671dc023afd5ad23b6b0995e79ef68a | eb4dbc7e1cd1c1a1671f58441bb3e49d08e77a5e | 99e0fd7a60df0584661d8e9162bf9dde1d0abf22 | governance gates and tests |
| b255d79df2b435ba754b7afe450d0a45559ea72a | 5d0818ab9671dc023afd5ad23b6b0995e79ef68a | d4517e99bb155353704726d8a11e22e935dfe7dc | provenance integration |
| fc145550b750c172899bc1497ff5fede387c07dc | b255d79df2b435ba754b7afe450d0a45559ea72a | 0d4ec3cba2040d640e3adb8880c98a4525fa2207 | public-boundary fixture correction |
| 098ba1399f7146258027674d5d312966fbdfe037 | fc145550b750c172899bc1497ff5fede387c07dc | f0f65517dea5b3292c6f3f87c8c10b90295487e8 | replay diagnostic propagation correction |
| 5722067571b70911c38b50ead23d198dcfbd4f20 | 098ba1399f7146258027674d5d312966fbdfe037 | f66d1a7fada6db1a883c830f91ac6222983fa6c8 | installed-tool provisioning correction |
| 8e08c3891dc8f761ada096c3f829ef31d3fbfd7c | 5722067571b70911c38b50ead23d198dcfbd4f20 | 01ee7b08cc870a626698ac9a3fc46ec92bf0f4e0 | import-order correction and final rejected v2 head |

Both rejected branch refs and all listed Git objects MUST remain unchanged. Neither v1 nor v2 may be an ancestor of the P12 v4 acceptance commit, any v4
implementation/correction commit, or the v4 summary. No v4 CI result, evidence receipt,
summary, acceptance, publication, or claim may bind to a rejected acceptance blob.

The future v4 acceptance, ADR, and provenance receipt permanently preserve the safe v2 identities
and failure summaries above. GitHub Actions logs and API objects are subject to normal
retention and are not required to remain live-readable forever. During Stage 3 draft
validation, Stage 6 acceptance establishment, Stage 7 post-commit verification, Stage 17
independent acceptance, and Stage 21 remote closeout, each retained run MUST be verified
read-only: run 34542709145 has exactly attempt 1 at head fc145550b750c172899bc1497ff5fede387c07dc and run 34564478590 has exactly attempts 1 and 2 at head
8e08c3891dc8f761ada096c3f829ef31d3fbfd7c, with every named attempt
completed/failure and no reclassification. At those same checkpoints, the field-complete
PR oracle must establish the exact CLOSED-without-merge state and independently require mergedAt, mergeCommit and
autoMergeRequest all null; CLOSED alone is insufficient. Before Stage 21 P12 closeout, deliberate
deletion, alteration, reclassification, a second attempt of run 34542709145, a third
attempt of run 34564478590, or any non-null merge/auto-merge field fails closed. After
closeout, ordinary retention expiry is not repository history
drift. Git objects, the v2 branch, and PR #14 closed-without-merge metadata remain
protected independently of log retention.

Retention-window verification uses duplicate-key-rejecting parsing of the current run
resources and the exact attempt resources below; it never selects latest, reruns, or
downloads a full log merely to preserve identity:

~~~text
/repos/jeremyliu1220/digital-colleagues/actions/runs/34542709145
/repos/jeremyliu1220/digital-colleagues/actions/runs/34542709145/attempts/1
/repos/jeremyliu1220/digital-colleagues/actions/runs/34564478590
/repos/jeremyliu1220/digital-colleagues/actions/runs/34564478590/attempts/1
/repos/jeremyliu1220/digital-colleagues/actions/runs/34564478590/attempts/2
~~~

The current resources must report `run_attempt` 1 and 2 respectively, proving no extra
attempt. After Stage 21 closeout, normal provider retention loss of those API/log objects
does not invalidate repository history; the fixed identities and safe summaries remain.

### Superseded v3 acceptance-only attempt

| Field | Exact value |
| --- | --- |
| Local branch | `codex/p12-public-pilot-continuity-rebaseline-v3` |
| Acceptance commit | `e31bc733cbdd333648f2ce1c52ac9fe1fad83179` |
| Acceptance tree | `1cdce2a41f84ee4243d04be781ad187eb5f5fab9` |
| Sole parent | `c1562ea5201394d8a278f4b644daf4029cbb5bd4` |
| Acceptance path | `docs/p12/acceptance.md` |
| Acceptance blob | `40c93a2aa8930c71e14fefac2053a10ed137af58` |
| Acceptance file lines / bytes | `3488` / `232313` |
| Acceptance file SHA-256 | `6afddd55f4f8458c94dcd56b781e47fef66a06d954d4246aa3855b4daf2e0e3c` |
| Implementation/correction/summary commits | none |
| Remote v3 branch and v3 pull request | absent |
| Tag, Release, publication | none |

The v3 contract classified only `p8_compose_runtime` as excluded from Ubuntu replay. The
complete 129-gate call-graph audit fixed below established four additional immutable
platform-specific leaves: transitive `p8_golden_path` and the three Darwin-only P10 gates
`p10_compose_runtime`, `p10_quickstart`, and `p10_remote_distribution`. The v3 contract is
therefore not implementable as written and is superseded without amendment, reset, or
history rewrite.

The 40 uncommitted implementation-path changes currently present in the dirty v3 primary
worktree are not v3 history, evidence, or an accepted result. Their exact planning-time
identity is fixed below solely for preservation. They may enter v4 only after canonical
Stages 4, 5, 7, and 8 complete and Stage 9 separately authorizes approved per-file reuse or
correction. The v3 ref, commit, tree, and acceptance blob remain immutable regardless of
future WIP disposition.

All v1, v2, and v3 Git objects and refs MUST remain readable and unchanged. Each must be a
non-ancestor of every v4 commit. The v2 remote branch remains at its exact rejected head;
PR #14 remains CLOSED without merge, with `mergedAt`, `mergeCommit`, and
`autoMergeRequest` all null. State `CLOSED` alone never proves the no-merge boundary.

## Change Decision

### Decision

P12 v4 SHALL use platform-scoped historical replay. A standard GitHub-hosted `ubuntu-24.04` runner executes every accepted historical acceptance gate that can be run faithfully from its immutable object on that platform. It does not execute five exact Darwin-dependent gates:

1. `p8_compose_runtime`
2. `p8_golden_path`
3. `p10_compose_runtime`
4. `p10_quickstart`
5. `p10_remote_distribution`

Those five remain accepted historical gate identities. Their Ubuntu replay status is `not_proven`; they are not deleted, passed, skipped, waived, tolerated, or replaced. Their immutable Darwin evidence remains separately anchored and cannot be promoted into Linux proof.

P12 governance may pass while the five Ubuntu evaluations remain `not_proven` and Linux Public Pilot readiness remains `blocked`. P20-L0 is the first and only future blocking sub-gate that owns resolution of Linux host/container UID, private bind-mount, backup/restore, local quickstart, and remote-distribution quickstart portability. P20-L0 does not reorder P13 through P20 and does not authorize migration 015 or product work during P12.

### Unchanged B+ roadmap and product decisions

| Order | Milestone |
| ---: | --- |
| 1 | P12 — Public Pilot Continuity Rebaseline |
| 2 | P13 — Migration Parser Correction and OpenAI Model Gateway |
| 3 | P14 — Microsoft 365 Connector Foundation |
| 4 | P15 — Durable Project Continuation |
| 5 | P16 — Semantic Memory Lifecycle |
| 6 | P17 — Trigger, Recurring Schedule, Heartbeat, Correlation, and Recovery |
| 7 | P18 — Bounded Goal-driven Proactivity |
| 8 | P19 — Built-in Public Pilot Project Tracker |
| 9 | P20 — Always-on Public Pilot Release; P20-L0 is its first blocking implementation sub-gate |

The platform-classification decision changes none of the accepted B+ product semantics. Continuation, Memory, Trigger, and Proactivity remain independent gates. Memory admission remains tiered and distinct from post-admission lifecycle. P14 owns bounded HUMAN-approved Microsoft write transports, P15 owns normalized exact-wait binding and continuation, and P17 owns autonomous polling/correlation/wake/recovery. P18 alone may create `AutomaticEffectAuthorization`; P19 composes accepted transports and cannot build missing connector primitives. Mandatory checkpoints, blank-chat durable recovery, non-authoritative recovery cursors, conservative DST/catch-up semantics, parser-first P13 sequencing, migrations 001–008 immutability and 009–014 ownership remain unchanged. Migration 015, runtime/schema/provider behavior, publication, and P13 implementation remain unauthorized.

### Why v3 is superseded

P12 v3 fixed a one-gate exclusion model. Exact call-graph audit proved that model incomplete: P8 Golden Path directly executes P8 actual Compose, and three accepted P10 gates require or assert Darwin semantics. Because the v3 acceptance text is immutable, implementation cannot correct its inventory, envelope, evidence, or summary semantics without violating the accepted contract. A replacement acceptance attempt is therefore required.

### Governance consequences

- The portable replay universe remains the exact 129 accepted gate identities; classification changes, identity does not.
- The typed inventory remains 151 rows. Five embedded Darwin composite anchors are validation data inside excluded rows, not new inventory items.
- Current P12 registry protection is a separate evidence-preflight result and never substitutes for accepted `p10_remote_distribution`.
- No public-PR workflow may use a persistent or general self-hosted runner.
- No accepted object may be patched, intercepted, monkey-patched, platform-spoofed, or selectively suppressed by the host OS.

## Exact baseline, branch, and drafting-time repository state

| Field | Exact value |
| --- | --- |
| Repository | `jeremyliu1220/digital-colleagues` |
| Exact accepted base / local main / origin/main / GitHub main | `c1562ea5201394d8a278f4b644daf4029cbb5bd4` |
| Exact accepted base tree | `ae0f33263cfc7445fef69656ad9c5cb04d4a2d00` |
| Future v4 branch | `codex/p12-public-pilot-continuity-rebaseline-v4` |
| Current primary-worktree branch | `codex/p12-public-pilot-continuity-rebaseline-v3` |
| Current primary-worktree HEAD | `e31bc733cbdd333648f2ce1c52ac9fe1fad83179` |
| Current primary-worktree tree | `1cdce2a41f84ee4243d04be781ad187eb5f5fab9` |
| Current staged / ignored counts | `0` / `0` |
| Current tracked-modified / untracked WIP counts | `20` / `20` |
| Current WIP framed SHA-256 | `79816a61e89f86b27f876986f1c06de50ee6d1c72caa95989ae5447c584059f1` |
| P12 summary | absent |
| Local/remote tags / GitHub Releases | `0` / `0` / `0` |
| Remote v4 branch and v4 PR | absent |

P12 v4 starts directly from the exact accepted base. The v4 branch MUST be created only in
a separately authorized Stage 6 independent temporary Git worktree; nobody may switch the
dirty v3 primary worktree. The v4 acceptance commit has the exact base as sole parent.
The v1, v2, and v3 attempt commits are separate sibling lines and MUST NOT be ancestors of
v4. No graft, replace ref, merge, cherry-pick recreation, or other ancestry indirection is
permitted.

The drafting-time WIP and remote facts are observations protected by this contract, not
P12 evidence. A later unrelated third-party state change is not silently accepted: every
stage oracle re-reads the relevant identity and fails closed unless the project owner has
separately authorized that exact transition.

## P12 v4 commit topology

The only permitted P12 v4 history is:

~~~text
c1562ea5201394d8a278f4b644daf4029cbb5bd4  exact accepted base
  \
   v1 rejected attempt (preserved; never a v4 ancestor)
  \
   v2 rejected attempt and closed PR #14 (preserved; never a v4 ancestor)
  \
   v3 superseded acceptance-only attempt (preserved; never a v4 ancestor)
  \
   v4 acceptance-only commit
     -> one or more v4 implementation/scoped-correction commits
       -> exact P12_FINAL_IMPLEMENTATION_HEAD
         -> summary-only evidence commit
~~~

1. Stage 6 creates the first v4 commit. It adds only `docs/p12/acceptance.md`, has the exact
   accepted base as sole parent, and establishes dynamic reviewed values
   `P12_V4_ACCEPTANCE_COMMIT` and `P12_V4_ACCEPTANCE_BLOB`.
2. The acceptance file remains byte-identical thereafter. No implementation, correction,
   evidence, or summary commit may modify it.
3. Stage 9 may authorize one or more linear, ordinary, single-parent implementation or
   scoped-correction commits on only the 40 implementation paths.
4. A scoped correction always requires new project-owner authority, cites the exact failed
   gate or review finding, is append-only, and changes only the minimum authorized
   implementation/test paths. It cannot modify acceptance or summary.
5. `P12_FINAL_IMPLEMENTATION_HEAD` is the last clean implementation/correction commit. Its
   ancestry above the acceptance commit is the complete ordered implementation/correction
   set. The canonical range digest frames each commit SHA, sole parent, tree, ordered
   changed paths/status/mode, and commit-message digest in ancestry order.
6. Stage 12 CI binds the exact final implementation head and tree. An ancestor, recreated
   tree, merge SHA, PR merge ref, or branch name is insufficient.
7. Stage 13 read-only preflight and Stage 14 evidence/summary require distinct later
   authorizations. Stage 14 adds only `artifacts/p12/summary.json`, with the exact final
   implementation head as sole parent, and produces the final commit in the chain.
8. The summary binds the complete ordered implementation/correction set and range digest,
   exact Stage 12 run/attempt/jobs/envelope digests, complete portable inventory result,
   five Darwin anchor identities, and P12-owned registry result.
9. Stage 15 push and Stage 16 exact final-candidate PR CI require later authority. No commit
   may follow the summary-only commit.
10. Merge commits, amend, rebase, squash, reset, force update, force-with-lease, graft,
    replace refs, cherry-pick recreation, and every history rewrite are forbidden.
11. The acceptance-only commit is never pushed or used to open a standalone PR.
12. At the acceptance commit the base-to-head path set is exactly one. At the final
    implementation head it is exactly 41: acceptance plus 40 implementation paths. At the
    final candidate it is exactly all 42 allowlisted paths.

A rename, copy, delete, mode change, symlink, submodule, special file, or path outside the
allowlist fails closed.

The canonical range object has schema `digital-colleagues.p12-v4-commit-range.v1` and
exact keys `schema`, `base_commit`, `acceptance_commit`, and `commits`. `commits` contains
the acceptance commit followed by every implementation/scoped-correction commit in
first-parent ancestry order through `P12_FINAL_IMPLEMENTATION_HEAD`. Each element has
exact keys `commit`, `parent`, `tree`, `message_sha256`, and `changes`; `changes` is sorted
by raw UTF-8 path bytes and each entry has exact keys `path`, `status`, `old_mode`, and
`new_mode`, using null where Git has no old object. The range object is P12-CJ-1 canonical
JSON. `range_digest` is `sha256:` followed by the lowercase SHA-256 of those exact bytes.
Missing, extra, reordered, merge-parent, non-allowlisted, acceptance-modifying, or
summary-bearing entries fail closed.

## Exact 42-path allowlist and protected WIP lifecycle

The repository allowlist remains exactly 42 paths: immutable `docs/p12/acceptance.md`, the following 40 implementation paths, and final summary-only `artifacts/p12/summary.json`. Write ownership is exclusive: stage 6 may add only `docs/p12/acceptance.md`; stage 9 may change only the 40 implementation/scoped-correction paths and may never change acceptance or summary; stage 14 may add only `artifacts/p12/summary.json`, after which no later commit is allowed. No other stage may write an allowlisted path. No runtime, `src/**`, Studio source, schema, migration, dependency, lock, Compose/runtime configuration, historical checker/test/evidence/provenance, or distribution/P10 path is allowed.

### Exact allowlist

| Phase | Exact path | Allowed change class |
| --- | --- | --- |
| Acceptance-only | `docs/p12/acceptance.md` | New immutable v4 contract only |
| Implementation | `.github/ISSUE_TEMPLATE/feature_request.yml` | Present P12-P20 and portability-risk boundaries accurately; Governance choices/copy only |
| Implementation | `.github/pull_request_template.md` | Require platform claims, exact inventory, CI, evidence, and no-publication declarations; Checklist text only |
| Implementation | `.github/workflows/ci.yml` | Establish exact current/portable Ubuntu jobs; Canonical CI policy/invocations only; pinned read-only actions |
| Implementation | `AGENTS.md` | Record v4 milestone and v1/v2/v3 immutable-history discipline; Project-governance instructions only |
| Implementation | `CONTRIBUTING.md` | Direct contributors to v4 contract and platform boundary; Contribution/gate instructions only |
| Implementation | `Makefile` | Add v4 current/portable targets and current `ci` alias; P12 targets/recipes/PHONY and generic alias only; P0-P11R targets unchanged |
| Implementation | `README.md` | State v4 governance status and Linux claim boundary; Status/usage documentation only |
| Implementation | `SECURITY.md` | Expose the known Linux private-bind portability risk; Security status/scope text only |
| Implementation | `docs/adr/0011-public-pilot-continuity-rebaseline.md` | Record v4 decision and v1/v2/v3 rejection or supersession without rewriting history; One prospective ADR only |
| Implementation | `docs/architecture/target-architecture.md` | Record platform-scoped history and P20 forward portability boundary; Prospective architecture text only |
| Implementation | `docs/development.md` | Document v4 target graph and evidence process; Development workflow text only |
| Implementation | `docs/p12/portable-historical-inventory.json` | Canonical machine-readable included/excluded historical leaf inventory; Add deterministic policy JSON only; never evidence or private output |
| Implementation | `docs/p12/rebaseline-checklist.md` | Give reviewers repeatable v4 verification commands; Documentation only |
| Implementation | `docs/product/capability-matrix.md` | Prevent Linux runtime overclaim; Status/cross-reference text only |
| Implementation | `docs/product/post-v0.1-capability-outlook.md` | Carry portability risk to P20 without reordering phases; Prospective outlook only |
| Implementation | `docs/product/v0.2-external-dependency-register.md` | Record GitHub-hosted Ubuntu and platform-evidence constraints; Planning/register entries only |
| Implementation | `docs/product/v0.2-public-pilot-capability-matrix.md` | Mark Linux runtime and Public Pilot readiness blocked; Prospective matrix only |
| Implementation | `docs/product/v0.2-public-pilot-product-brief.md` | Define truthful supported-host and claim boundary; Prospective requirements only |
| Implementation | `docs/roadmap.md` | Preserve P12-P20 order and add P20 entry sub-gate; Current checkpoint/prospective roadmap only |
| Implementation | `docs/security/privacy-boundary.md` | Cross-reference private bind-mount portability risk; Prospective privacy text only |
| Implementation | `docs/security/threat-model.md` | Cross-reference UID/ownership and runner risks; Prospective threat text only |
| Implementation | `docs/security/v0.2-public-pilot-privacy-boundary.md` | Fix Linux private-state and evidence boundary; Prospective v0.2 privacy contract only |
| Implementation | `docs/security/v0.2-public-pilot-threat-model.md` | Fix bind ownership, self-hosted runner, and claim-laundering controls; Prospective v0.2 threat contract only |
| Implementation | `provenance/p12-change-receipt.json` | Bind base, v4 contract, 42 paths, inventory, and zero-source use; Deterministic safe provenance JSON only |
| Implementation | `scripts/check_p12_ci_policy.py` | Enforce exact two-job Ubuntu policy and zero publication; Deterministic read-only checker only |
| Implementation | `scripts/check_p12_historical_inventory.py` | Validate objects, commands, five exact exclusions, results, and platform claims; New deterministic read-only checker only |
| Implementation | `scripts/check_p12_migrations.py` | Enforce immutable 001-008 and 009-014 owners; Deterministic read-only checker only |
| Implementation | `scripts/check_p12_provenance.py` | Validate v4 receipt, allowlist, inventory, and zero source migration; Deterministic read-only checker only |
| Implementation | `scripts/check_p12_rebaseline.py` | Validate B+ decisions plus platform risk/owner; Deterministic read-only checker only |
| Implementation | `scripts/check_p12_repository.py` | Validate topology, 42 paths, v1/v2/v3 preservation, and no publication; Deterministic read-only checker only |
| Implementation | `scripts/collect_p12_evidence.py` | Produce only authorized v4 safe summary; Evidence writer only; no network write/private data |
| Implementation | `scripts/run_p12_toolchain.py` | Run current gates and exact portable history in OS temporary locations; Deterministic runner only; no accepted-object edits or wrapper interception |
| Implementation | `tests/p12/__init__.py` | Define P12 test package; Empty/package marker only |
| Implementation | `tests/p12/test_ci_policy.py` | Test workflow pins, jobs, permissions, platform claims, no publication; Synthetic governance tests only |
| Implementation | `tests/p12/test_evidence_gate.py` | Test evidence topology and Linux blocked status; Synthetic governance tests only |
| Implementation | `tests/p12/test_historical_inventory.py` | Test exact inventory and exclusion fail-closed behavior; New synthetic governance tests only |
| Implementation | `tests/p12/test_migrations.py` | Test immutable migrations and future ownership; Synthetic governance tests only |
| Implementation | `tests/p12/test_provenance.py` | Test exact identities and safe receipt; Synthetic governance tests only |
| Implementation | `tests/p12/test_rebaseline.py` | Test complete B+ decision and portability owner; Synthetic governance tests only |
| Implementation | `tests/p12/test_repository.py` | Test exact paths, non-ancestry, preservation, cleanliness, and negatives; Synthetic governance tests only |
| Summary-only | `artifacts/p12/summary.json` | Canonical authorized evidence summary only |

### WIP preservation, content-bearing snapshot, reuse, and cleanup barrier

The current 40 files remain untouched during planning. They are not evidence, a commit, an accepted v3 result, or presumptively reusable. Appendix D is only the planning-time identity manifest: it contains no preserved file bodies and satisfies neither Stage 4 nor Stage 5. A focused test count does not authorize reuse. Every stage number below refers only to the canonical 21-stage lifecycle in this contract; this section does not define an alternative order.

Stages 1–3 complete Blueprint review, repository-external acceptance drafting, and independent acceptance-draft pre-commit validation before any WIP snapshot is created. Stage 4 then creates one content-bearing snapshot in a repository-external directory whose mode is exactly 0700. That snapshot contains:

- the complete original bytes of all and only the 40 WIP files under a safe relative-path-preserving payload root;
- each file's `tracked_modified` or `untracked` class, exact repository-relative path, Git mode, byte size, and lowercase SHA-256;
- the existing canonical overall framed digest, using the sorted UTF-8 framing `path NUL mode NUL decimal-size NUL lowercase-file-sha256 LF`;
- a unique-key canonical UTF-8 JSON snapshot manifest with no BOM or terminal newline, sorted object keys, separators `(",", ":")`, `ensure_ascii=false`, `allow_nan=false`, source branch/HEAD/tree, exact 40-entry metadata, and the overall framed digest; and
- a separately recorded lowercase SHA-256 of the exact manifest bytes.

The exact snapshot layout is a `payload/` tree plus `snapshot-manifest.json` and
`snapshot-manifest.sha256`. The directory and payload tree are mode 0700; manifest,
checksum, and payload regular files are mode 0600. Narrow snapshot-storage modes never
replace each entry's recorded Git mode. `snapshot-manifest.json` is P12-CJ-1 canonical
UTF-8 JSON with no terminal newline and this closed logical schema:

~~~json
{
  "entries": [
    {
      "byte_size": 1,
      "class": "tracked_modified",
      "mode": "100644",
      "path": "repository/relative/path",
      "sha256": "<64 lowercase hex>"
    }
  ],
  "entry_count": 40,
  "framed_sha256": "79816a61e89f86b27f876986f1c06de50ee6d1c72caa95989ae5447c584059f1",
  "framing": "path NUL mode NUL decimal-size NUL lowercase-file-sha256 LF",
  "schema": "digital-colleagues.p12-v4-wip-snapshot.v1",
  "source_branch": "codex/p12-public-pilot-continuity-rebaseline-v3",
  "source_head": "e31bc733cbdd333648f2ce1c52ac9fe1fad83179",
  "source_repository": "jeremyliu1220/digital-colleagues",
  "source_tree": "1cdce2a41f84ee4243d04be781ad187eb5f5fab9"
}
~~~

The `entries` array contains exactly the Appendix D paths in UTF-8 bytewise path order and
uses each appendix class, mode, byte size, and digest exactly. The checksum file contains
the lowercase SHA-256 of the exact manifest bytes followed by one LF. Snapshot payload
files are regular, non-symlink files and retain byte identity. Path validation rejects
absolute paths, `..`, aliases, duplicates, case-collisions, extra or missing payloads,
symlinks, devices, sockets, and every path outside the exact 40-item set. The snapshot is
recoverable: a verifier can materialize every preserved original byte into a new scratch
directory solely from the snapshot payload and manifest, without consulting or changing
the dirty worktree.

Stage 4 changes no repository file, index entry, Git ref, commit, branch, worktree selection, or remote state. It does not stage, stash, reset, clean, switch, delete, overwrite, or reinterpret the dirty v3 WIP.

At Stage 5, an independent verifier reads the snapshot directory itself. It verifies directory mode 0700, manifest checksum and canonical form, exact item set and classes, safe paths, regular-file/non-symlink status, and then recomputes every byte size and per-file SHA-256 from the 40 saved payloads. It reconstructs the framing from those recomputed payload results and requires the overall digest to equal both the manifest value and `79816a61e89f86b27f876986f1c06de50ee6d1c72caa95989ae5447c584059f1`. Re-reading the dirty worktree may detect drift but can never substitute for validating the snapshot's actual bytes. A manifest-only archive, metadata-only fingerprint, or digest list is not a valid snapshot.

The verifier emits outside the repository a mode-0600 P12-CJ-1 receipt with schema
`digital-colleagues.p12-v4-wip-snapshot-verification.v1`, exact manifest SHA-256, the
framed SHA-256, `entry_count = 40`, `verified_from_saved_payloads = true`, zero missing,
extra, duplicate, unsafe, symlink, and digest-mismatch counts, verifier timestamp, and
`status = passed`. It stores no Git credential or absolute repository path. A receipt
derived only from the dirty worktree, or one missing any saved-payload recomputation,
fails closed.

Stage 6 uses a separate temporary Git worktree at the exact accepted base to establish the v4 branch and acceptance-only commit; Stage 7 independently verifies it. Only at Stage 8 may reviewers perform the 40-path, file-by-file, read-only reuse review against the immutable v4 acceptance contract and the verified snapshot. The external review record uses schema `digital-colleagues.p12-v4-wip-reuse-review.v1`, binds the snapshot manifest and verification-receipt SHA-256 values, and contains exactly 40 path-ordered entries with path, snapshot file SHA-256, disposition `reuse_exact`, `correct_before_reuse`, or `reject`, safe rationale code, and reviewer identity class. It records one disposition per path and never authorizes a bulk copy. Only Stage 9 governance implementation authorization permits explicitly approved bytes or scoped corrections to enter linear allowlisted v4 commits; v3-only assumptions such as 128/1, a singular exclusion field, self-derived completeness, incomplete envelope semantics, incomplete subprocess isolation, or incomplete one-use receipt validation must be corrected or rejected. Stage 10 runs the required local formal gates on the clean committed v4 implementation head.

Dirty-v3 cleanup is a separate maintenance action outside the v4 promotion-stage numbering and is never required to advance the v4 chain. It may occur only when all five conditions hold:

1. the content-bearing snapshot has passed independent stage 5 verification;
2. the stage 8 per-file reuse review is complete for all 40 paths;
3. every approved item has been migrated into v4 under stage 9 authority;
4. the v4 implementation commits and stage 10 local formal verification are complete; and
5. the project owner has separately and explicitly authorized the exact cleanup operation and targets.

Until all five conditions hold, nobody may switch, stash, reset, clean, delete, overwrite, restore, or otherwise disturb the dirty v3 WIP. Snapshot creation or verification alone never authorizes cleanup, and cleanup never authorizes any later v4 stage.

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

Every P13-P19 acceptance, evidence, and closeout record MUST carry the exact ordered
five-gate Ubuntu `not_proven` mapping for `p8_compose_runtime`, `p8_golden_path`,
`p10_compose_runtime`, `p10_quickstart`, and `p10_remote_distribution`, together with
`linux_public_pilot_readiness = blocked`. Passing one of those phases cannot change any
historical platform status, claim Linux runtime compatibility, or pre-accept P20-L0. This
carry-forward rule does not make an otherwise passing P13-P19 mechanism gate failed or
blocked; the three status dimensions remain independent.

### P12 — Historical Platform Classification and Public Pilot Continuity Rebaseline

**Objective.** Convert this complete decision into current living documentation,
governance gates, synthetic tests, provenance, a literal portable historical inventory,
safe CI-result envelopes, and safe evidence machinery without adding product behavior.
Preserve five accepted Darwin results as immutable platform-scoped anchors, classify the
same five historical gates as Ubuntu `not_proven`, and keep Linux Public Pilot readiness
blocked.

**Hard dependencies.** Exact accepted P11R main, this isolated v4 acceptance commit, and
preserved non-ancestor v1/v2/v3 attempts.

**In scope and layer boundary.** Only the exact 42-path set in this contract. Documentation
may define future core, application, port, adapter, API, and Studio contracts, but P12
changes none of those runtime layers. New Python is restricted to repository, CI policy,
historical inventory, migration, provenance, rebaseline, evidence governance, and
deterministic toolchain execution.

**Migration.** None. Migrations 001–008 and the manifest remain byte-identical; migration
count remains eight.

**Security and privacy.** Static contract, deterministic historical execution, and
negative synthetic tests only. No credential, provider, personal, private-live, package,
image, or network-write path. Public CI uses only GitHub-hosted `ubuntu-24.04` with
`contents: read` and no secrets, OIDC, write permission, artifact transport, or
publication.

**Repeatable local exits.** Before any remote mutation, the exact implementation head runs
these commands from a clean v4 worktree with `PYTHONDONTWRITEBYTECODE=1`:

~~~text
make p12-test
make p12-current-ci
make p12-portable-history
make p12-implementation-check
make p12-ci
make ci
~~~

Each command runs at most once as a formal gate. The aggregate is non-recursive.
`p12-portable-history` executes all 151 typed items and 124 included acceptance gates. It
classifies exactly five excluded acceptance gates and does not invoke accepted
P11R/P11/P10/P9 aggregates or P8 `--scope all`.

**Exact implementation-head CI.** A separately authorized Stage 11 candidate push creates
or updates one pull request to main. Stage 12 requires exactly two successful jobs on the
exact implementation head:

1. `Current P12 governance non-publishing verification`; and
2. `Portable historical replay`.

Both use `ubuntu-24.04` and each emits exactly one canonical safe P12 v4 pull-request
envelope. The bounded main-only current P11R Compose smoke is skipped on pull requests and
is neither accepted P8/P10 Linux evidence nor a substitute for an excluded gate.

**Evidence handoff.** Stage 13 read-only preflight obtains the two Stage 12 envelopes from
the exact completed run, attempt, and jobs; verifies marker, schema, canonical bytes,
digests, identities, platform/count/set bindings, and GH/GHCR/TLS/locked-package/P10
checks; and creates only one mode-0600 external one-use receipt under a mode-0700 temporary
directory. Only Stage 14 may consume it to run `make evidence-p12` and create the
summary-only commit.

**Final candidate.** The summary-only descendant runs `make p12-check` and `make ci`.
Stage 15 separately authorizes its push; Stage 16 exact final-candidate pull-request CI
repeats both required jobs and envelopes. Stages 17 and 18 bind that later run externally
because the immutable summary cannot contain a future run identity.

**Independent acceptance.** Verify the immutable acceptance blob; exact base and sole
parent; v1/v2/v3 non-ancestry and preservation; linear implementation/correction topology;
exact 42 paths; all 151 typed items; independently derived 129 = 124 disjoint-union 5 set
oracle; all historical entrypoints; unchanged history/migrations; complete B+ contracts;
P10 protection; both exact-head PR CIs and envelopes; platform status separation; safe
provenance; zero residue; and zero publication.

**Evidence and claim.** Static, `synthetic_offline`, and `portable_historical` only. The
maximum claim is `p12_v4_historical_platform_classification_candidate` or, only after
Stage 18, `p12_v4_historical_platform_classification_accepted`. P12 governance may pass.
All five Ubuntu historical statuses remain `not_proven`, and Linux Public Pilot readiness
remains `blocked`. P12 is not a product-capability, Linux-runtime-compatibility, or Public
Pilot claim.

**Non-goals, size, and risk.** No product implementation, accepted-object modification, or
P13+ evidence. Primary risks are inventory omission, accidental sixth exclusion,
historical module shadowing, environment leakage, log-envelope ambiguity, status
conflation, WIP contamination, and unsafe transition authority.

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

**Blocking first implementation sub-gate: P20-L0 — Linux Private-State, Compose,
and Quickstart Portability.** P12 owns truthful classification and propagation of the
risk, not the runtime fix. P20-L0 is the sole future owner for standard-Linux proof of the
forward equivalents of P8 actual Compose, P8 Golden Path, P10 Compose runtime, P10 local
quickstart, and P10 remote-distribution quickstart. It never modifies or relabels the
accepted P8/P10 objects or Darwin evidence. P13 through P19 carry the unresolved risk and
cannot claim it passed. P20-L0
occurs before any P20 private-live E2E, 72-hour soak, release candidate,
supported-Linux-host claim or publication preparation. It does not add a milestone,
reorder P13-P20, authorize a core capability, or pre-authorize a migration. The future
P20 contract must put the fix in its first implementation commit or first separately
reviewable chain and forbid all later P20 implementation until P20-L0 passes.

P20-L0 has these exact exit criteria:

1. Only current P20-authorized operator/Compose/runtime integration may change; accepted
   P8 and P10 objects, checkers, runners, summaries, evidence, and every protected
   historical identity remain immutable.
2. The complete forward release transition, backup, restore, restart, rollback, cleanup
   and durable-state-equality path passes on a standard GitHub-hosted Ubuntu runner or an
   equivalently clean, ephemeral, owner-approved standard Linux environment. Persistent
   general self-hosted public-PR execution is forbidden.
3. The host operator UID differs from container UID 10001.
4. Containers remain non-root; private directories remain 0700 and private files 0600.
   chmod 777, broad group/world access, privileged execution and root fallback are
   forbidden.
5. A least-privilege portable handoff moves backup/restore material across the boundary
   without depending on Darwin ownership translation.
6. Fresh, restart, upgrade, restore, rollback and replacement named-volume paths verify
   expected UID/GID, modes and read/write boundaries.
7. Wrong owner or mode, symlink, traversal, stale backup, corrupt digest, missing source
   binding, mismatched code, concurrent restore, partial copy and interrupted transition
   fail closed.
8. Logs remain bounded and redacted and contain no private body, credential, provider
   payload, personal data or private absolute path.
9. The forward implementation passes a separately authorized Darwin regression; Darwin
   and Linux results remain separately labeled.
10. Task-owned containers, networks, volumes and temporary files are removed after both
    success and failure; repository residue is zero.
11. Evidence binds exact commit/tree, OS/image, architecture, Docker/Compose, UID/GID,
    commands, counts, cleanup and result without reinterpreting P8 evidence.
12. Migration count remains fourteen. A schema need stops P20 and returns to the owner;
    migration 015 remains unauthorized.

The minimum tests include positive Linux and Darwin transitions, mismatched identity,
named-volume first-use and reuse, every adversarial case above, and cleanup. Passing P20-L0
proves the forward current runtime only on its tested Linux platform. It never changes the
accepted P8 historical platform label.

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

## P12 v4 CI governance transition

The accepted P10, P11 and P11R workflows, runners, checkers, tests, acceptance records and
evidence remain reproducible only on their exact objects and are never edited. P12 v4
changes the living workflow and adds a P12-owned literal portable inventory. It does not
change, copy-and-relax, monkey-patch, intercept or reinterpret accepted historical code.

### Exact target graph

| Target | Sole behavior |
| --- | --- |
| `make p12-test` | Run the exact 136-test P12 v4 governance inventory only |
| `make p12-current-ci` | Run current-tree P12 quality, static, policy, provenance, repository, migration, boundary, cleanup and no-publication gates |
| `make p12-portable-history` | Execute the canonical 151-item portable inventory on exact accepted objects and return one safe structured result |
| `make p12-implementation-check` | Require summary absent, exact v4 topology, 41-path implementation-head set, v1/v2/v3 preservation and all 40 implementation paths |
| `make p12-ci` | Aggregate current-ci then portable-history; derive implementation or final_candidate mode from committed topology and summary presence |
| `make ci` | One-way alias to p12-ci only |
| `make p12-evidence-preflight` | Perform the separately authorized read-only CI-envelope, GitHub, GHCR, TLS, lock, package and P10 preflight |
| `make evidence-p12` | Consume one authorized receipt and write only artifacts/p12/summary.json |
| `make p12-check` | Validate summary-only tip, exact 42 paths, committed evidence, platform statuses and all read-only final gates |

No P12 script may call `make ci` or another P12 aggregate recursively. No v4 command may
invoke accepted `make p11r-check`, `make p11-check`, `make p10-check`,
`make p9-check`, accepted P8 `--scope all`, or an equivalent indirect call graph. Each
would reintroduce the five platform-excluded leaves or repeat predecessor setup.
Appendix A is the sole historical-execution source of truth.

### Canonical GitHub-hosted workflow

The living workflow path is exactly `.github/workflows/ci.yml`. Its triggers are exactly
`pull_request` to `main` and `push` to `main`. Top-level permissions are exactly
`contents: read`; job-level permissions are absent. Concurrency cancellation is false.
`workflow_dispatch`, `schedule`, `pull_request_target`, `workflow_call`,
`repository_dispatch` and every other trigger are forbidden.

Every job uses the contracted runner family `ubuntu-24.04`. `ubuntu-latest` and
`self-hosted` are forbidden. The label identifies a runner family, not a fixed patch image,
so each required job independently records the observed exact environment.

The exact external-action inventory is nine invocations:

| Job ID | Job name | Action | Exact immutable ref | Count |
| --- | --- | --- | --- | ---: |
| current-ci | Current P12 governance non-publishing verification | actions/checkout | d23441a48e516b6c34aea4fa41551a30e30af803 | 1 |
| current-ci | same | actions/setup-python | ece7cb06caefa5fff74198d8649806c4678c61a1 | 1 |
| current-ci | same | actions/setup-node | 249970729cb0ef3589644e2896645e5dc5ba9c38 | 1 |
| portable-history | Portable historical replay | actions/checkout | d23441a48e516b6c34aea4fa41551a30e30af803 | 1 |
| portable-history | same | actions/setup-python | ece7cb06caefa5fff74198d8649806c4678c61a1 | 1 |
| portable-history | same | actions/setup-node | 249970729cb0ef3589644e2896645e5dc5ba9c38 | 1 |
| portable-history | same | sigstore/cosign-installer | 6f9f17788090df1f26f669e9d70d6ae9567deba6 | 1 |
| main-compose-smoke | Bounded current P11R Compose smoke | actions/checkout | d23441a48e516b6c34aea4fa41551a30e30af803 | 1 |
| main-compose-smoke | same | actions/setup-python | ece7cb06caefa5fff74198d8649806c4678c61a1 | 1 |

Checkout uses `fetch-depth: 0`, `persist-credentials: false` and the exact pull-request
head SHA or exact main push SHA. Python is exactly 3.12 and uses
`requirements/p8.lock` as the cache-dependency path. Node comes only from the exact
`.nvmrc`, npm caching binds `studio/package-lock.json`, and Corepack is enabled. The
portable-history job installs Cosign release `v3.0.6`. A mutable action ref, different
action count, different version or second installer fails closed.

The required PR jobs are:

| Job ID | Exact display name | Timeout | Gate | Envelope kind |
| --- | --- | ---: | --- | --- |
| current-ci | Current P12 governance non-publishing verification | 45 minutes | make p12-current-ci | current_governance |
| portable-history | Portable historical replay | 180 minutes | make p12-portable-history | portable_history |

The current job's 45-minute limit covers the bounded current 136-test/static/quality set
and its cleanup. The historical job has a 9,900-second executor deadline, leaving 15
minutes inside the 180-minute job limit for envelope emission and fail-closed cleanup.
`main-compose-smoke` runs only for a push to `refs/heads/main` after both required jobs. It
has 30 minutes and invokes only `make p11r-compose-smoke`. It is skipped on pull_request
and explicitly is not accepted P8 actual Compose or Linux portability evidence.

Every external action is pinned above. The workflow contains no secret context,
`GITHUB_TOKEN` exposure, generated authentication, OIDC, package write, artifact upload,
login, signing, attestation, publication or remote mutation.

### Required observed environment identity

Each required job records all fields below from its own process, never from the other job:

| Field | Required source and rule |
| --- | --- |
| runner_os | nonempty `RUNNER_OS`; must identify Linux |
| runner_image_os | nonempty `ImageOS` |
| runner_image_version | nonempty `ImageVersion` |
| architecture | nonempty `RUNNER_ARCH` |
| docker_server_version | exact safe output of `docker version --format '{{.Server.Version}}'` |
| docker_compose_version | exact safe output of `docker compose version --short` |
| python_version | normalized exact output of `python3 --version` |
| node_version | normalized exact output of `node --version` |
| npm_version | normalized exact output of `npm --version` |

A generic `runner_platform: linux`, a workflow label alone, an empty field, a value copied
from another job, or a value not bound to the envelope digest is insufficient.

Every observed value is stripped of one terminal newline and must be 1-128 printable ASCII
bytes matching `[A-Za-z0-9][A-Za-z0-9._+() /:-]{0,127}`. Control characters, shell
fragments, an absolute path, credential-shaped content or a second line fails closed.

### Portable executor resource and timeout contract

Objects execute strictly P8, P9, P10, P11 and P11R. Each exact milestone object receives
exactly one OS-temporary checkout, at most one hash-locked Python environment, and at most
one required npm workspace. P9 has no npm workspace. All leaves for one object reuse only
that object's environment.

Different objects never share a Python module cache, `sys.path`, venv, npm workspace,
checkout, Docker project, writable cache, output directory or mutable state. Historical
code loads only in an independent subprocess whose executable, working directory and
module search path point to the verified exact checkout. Before every Python leaf the
child verifies the relative module/file and blob. Resolving a current-tree same-name
module, external module or different blob fails closed. The parent never imports a
historical `scripts.*` module.

Every leaf retains its own gate ID, command/function identity, start/end time, integer exit
status, structured result and safe failure category. Environment reuse cannot batch,
merge, infer, omit or hide a leaf result. Failure stops that object; later leaves are
`not_run_due_to_prior_failure`, never passed. After each object, all task-owned process
groups, checkout, venv, npm workspace, containers, networks, volumes and temporary output
are removed and zero residue is proved before the next object.

The per-object limits, inclusive of setup, leaves and cleanup, are:

| Object | Limit |
| --- | ---: |
| P8 | 45 minutes |
| P9 | 15 minutes |
| P10 | 50 minutes |
| P11 | 30 minutes |
| P11R | 25 minutes |

Each operation uses the smaller of its own limit and remaining object time: checkout/ref
120 seconds; venv plus hash-locked install 600 seconds; npm workspace plus locked install
600 seconds; static leaf 300 seconds; Python lint/type/test 900 seconds; Studio
lint/type/test/build 600 seconds; reproducibility/release/Compose/quickstart 1,200 seconds;
and read-only remote-distribution 1,200 seconds. A timeout kills the exact child process
group, performs bounded cleanup, records failure and stops. No retry or unbounded wait is
permitted.

Child environments copy the current process and set exactly
`PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1` and
`P10_REMOTE_USE_INSTALLED_TOOLS=1` in addition to the minimal object-scoped paths. They do
not dump the environment or emit credentials, authorization headers, private paths,
provider payloads or private output.

### CI result envelope protocol

Each qualifying required job emits exactly one canonical safe result envelope. The marker
line is the only CI-to-evidence transport; workflow artifacts are forbidden.

The literal marker prefix is the token below followed by exactly one ASCII SPACE byte
(`0x20`); the code line omits that terminal byte to satisfy repository whitespace rules:
~~~text
P12_V4_RESULT_ENVELOPE_V1
~~~

The complete logical line is:

~~~text
P12_V4_RESULT_ENVELOPE_V1 <base64url-no-padding(P12-CJ-1 JSON)> sha256=<64-lowercase-hex>
~~~

A downloaded GitHub job log may prepend only its ordinary UTC timestamp token. The parser
accepts exactly this anchored expression and nothing else:

~~~text
^(?:[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,9})?Z )?P12_V4_RESULT_ENVELOPE_V1 ([A-Za-z0-9_-]+) sha256=([0-9a-f]{64})\r?$
~~~

The marker literal MUST occur nowhere else in emitted log output. The workflow invokes an
emitter in `scripts/run_p12_toolchain.py` by name; it does not inline or echo the marker.
Exactly one matching line per required job is mandatory. Zero, two or more, a partial
marker, an ANSI-prefixed line, extra suffix, whitespace change or unsupported timestamp
form fails closed.

Each required job creates one mode-0700 directory below RUNNER_TEMP, passes its unique
mode-0600 gate-result path through `P12_JSON_OUTPUT` to its exact make target, captures the
integer target status, and invokes exactly once:

~~~text
python3 -B scripts/run_p12_toolchain.py --scope emit-ci-envelope --job-kind <current_governance|portable_history> --gate-result <job-temp>/gate.json --gate-exit-status <integer>
~~~

The emitter obtains dynamic repository, workflow, event, PR and Git identities only from
standard GitHub runner inputs, the event payload and the checked-out Git object. It opens
`GITHUB_EVENT_PATH` read-only, parses one JSON document while rejecting duplicate keys at
every depth, and rejects a missing, non-regular, symlinked, malformed or non-object
payload. No caller CLI argument or arbitrary custom environment value may supply,
override or repair any of these identity fields.

For `pull_request`, the authoritative payload fields are
`pull_request.number`, `pull_request.head.ref`, `pull_request.head.sha`,
`pull_request.base.ref`, `pull_request.base.sha` and `repository.full_name`. The emitter
requires a positive PR number, repository `jeremyliu1220/digital-colleagues`, base branch
`main`, base SHA c1562ea5201394d8a278f4b644daf4029cbb5bd4, head branch
`codex/p12-public-pilot-continuity-rebaseline-v4`, and a 40-character lowercase head SHA.
It also requires `git rev-parse HEAD` to equal the
payload head SHA and requires `GITHUB_HEAD_REF` and `GITHUB_BASE_REF` to equal the payload
head and base refs respectively. A pull-request merge ref checked out in place of the
exact head commit is rejected.

For the separately authorized `push` closeout run, the emitter requires payload `ref` to
be `refs/heads/main`; payload `after`, `GITHUB_SHA` and `git rev-parse HEAD` must be the
same 40-character lowercase SHA. The envelope head branch is `main`, while `base_ref`,
`base_sha` and `pull_request_number` are all null. A deleted push, non-main ref, merge
checkout substitution or caller-provided base/PR value is rejected.

For both events, `GITHUB_WORKFLOW` must be exactly `CI`. The emitter parses
`GITHUB_WORKFLOW_REF` as an exact repository/workflow-path prefix plus Git ref; its prefix
must be exactly
`jeremyliu1220/digital-colleagues/.github/workflows/ci.yml@`, its suffix must be a
nonempty standard GitHub ref consistent with the event, and the parsed repository and
workflow path become the envelope values. `GITHUB_REPOSITORY` must equal both that parsed
repository and `repository.full_name`. `GITHUB_EVENT_NAME` must equal the parsed payload
variant. `GITHUB_RUN_ID`, `GITHUB_RUN_ATTEMPT`, `GITHUB_JOB` and
`GITHUB_EVENT_NAME` remain standard GitHub runner inputs and are later cross-checked
against attempt-specific REST run/job data. `RUNNER_OS`, `RUNNER_ARCH`, `ImageOS` and
`ImageVersion` are likewise standard observed-environment inputs. Job kind, `GITHUB_JOB`
and display name are a closed mapping, not arbitrary caller text.

This prohibition on environment indirection applies to unapproved or overrideable
identity indirection. It does not prohibit the contract-listed `P12_JSON_OUTPUT` result
path or the standard GitHub runner identity inputs named above; those inputs are allowed
only in their exact, bounded roles and remain subject to payload, Git and REST
cross-checks. After emitting once, the workflow removes the job directory and exits with
the captured target status. The emitter cannot suppress or replace a nonzero result. No
shell trap or `if: always()` path may invoke it twice.

P12-CJ-1 canonical JSON is UTF-8 without BOM or trailing newline; objects use unique keys
sorted by Unicode code-point order; separators are comma and colon without whitespace;
strings are Unicode NFC and use JSON escaping with `ensure_ascii=false`; arrays use the
contract-defined order; numbers are base-10 integers only; booleans and null are JSON
literals; floating, exponent, NaN and infinity values are forbidden. Parsing rejects
duplicate keys before canonicalization. Re-encoding must be byte-identical.

The decoded canonical envelope is at most 32,768 bytes. The unpadded base64url token is at
most 43,691 ASCII bytes and the complete marker line is at most 43,850 bytes. Oversize,
invalid alphabet, padding, undecodable UTF-8, noncanonical JSON or a digest other than the
lower-case SHA-256 of the exact decoded canonical bytes fails closed.

The exact schema name is `digital-colleagues.p12-v4-ci-result-envelope.v1`. Additional,
missing or renamed keys fail closed. The logical schema is:

~~~json
{
  "base_ref": "main",
  "base_sha": "<40 lowercase hex>",
  "cleanup_residue_count": 0,
  "contracted_runner_family": "ubuntu-24.04",
  "event": "pull_request",
  "gate": {
    "error_count": 0,
    "failure_count": 0,
    "gate_id": "p12_current_ci",
    "result_digest": "sha256:<64 lowercase hex>",
    "skip_count": 0,
    "status": "passed",
    "test_count": 136,
    "test_count_semantics": "p12_governance_unittest_methods"
  },
  "head_branch": "codex/p12-public-pilot-continuity-rebaseline-v4",
  "head_sha": "<40 lowercase hex>",
  "inventory": {
    "evidence_anchor_count": 17,
    "excluded_acceptance_gate_count": 5,
    "excluded_gate_ids": [
      "p8_compose_runtime",
      "p8_golden_path",
      "p10_compose_runtime",
      "p10_quickstart",
      "p10_remote_distribution"
    ],
    "execution_status": "bound_not_executed_by_this_job",
    "included_acceptance_gate_count": 124,
    "inventory_blob": "<40 lowercase hex>",
    "inventory_digest": "sha256:<64 lowercase hex>",
    "inventory_path": "docs/p12/portable-historical-inventory.json",
    "inventory_sha256": "<64 lowercase hex>",
    "item_results": [],
    "item_results_digest": "sha256:<64 lowercase hex>",
    "passed_acceptance_gate_count": null,
    "skip_count": 0,
    "setup_count": 5,
    "total_item_count": 151
  },
  "job_id": "current-ci",
  "job_name": "Current P12 governance non-publishing verification",
  "observed_environment": {
    "architecture": "<nonempty safe exact value>",
    "docker_compose_version": "<nonempty safe exact value>",
    "docker_server_version": "<nonempty safe exact value>",
    "node_version": "<nonempty safe exact value>",
    "npm_version": "<nonempty safe exact value>",
    "python_version": "<nonempty safe exact value>",
    "runner_image_os": "<nonempty safe exact value>",
    "runner_image_version": "<nonempty safe exact value>",
    "runner_os": "<nonempty safe exact value>"
  },
  "p12_current_p10_registry_protection": {
    "reason": "evidence_preflight_only",
    "status": "not_evaluated"
  },
  "platform_status": {
    "linux_public_pilot_readiness": "blocked",
    "p12_governance_result": "passed",
    "ubuntu_historical_execution_status": {
      "p10_compose_runtime": "not_proven",
      "p10_quickstart": "not_proven",
      "p10_remote_distribution": "not_proven",
      "p8_compose_runtime": "not_proven",
      "p8_golden_path": "not_proven"
    }
  },
  "publication_count": 0,
  "pull_request_number": 1,
  "repository": "jeremyliu1220/digital-colleagues",
  "run_attempt": 1,
  "run_id": 123456789,
  "schema": "digital-colleagues.p12-v4-ci-result-envelope.v1",
  "workflow_name": "CI",
  "workflow_path": ".github/workflows/ci.yml"
}
~~~

The example shows types and allowed variants; canonical bytes sort every key. For
`current-ci`, job name is exactly `Current P12 governance non-publishing verification`,
gate ID is `p12_current_ci`, test count is 136, test semantics is
`p12_governance_unittest_methods`, inventory execution status is
`bound_not_executed_by_this_job`, `item_results` is the empty array, and its digest is the
P12-CJ-1 digest of that empty array. Its `passed_acceptance_gate_count` is null because it
does not execute the inventory, and its `skip_count` is zero. For `portable-history`, job name is exactly
`Portable historical replay`, gate ID is
`p12_portable_historical_replay`, historical Python test count is 616, semantics is
`historical_python_unittest_cases`, inventory execution status is `passed`, and
`item_results` contains exactly 151 compact objects in canonical manifest order. Setup,
included, and evidence-anchor result objects have exactly `gate_id`, `item_type`, `result`,
and `exit_status`. Included acceptance gates require result `passed` and integer exit
status 0; setup requires `passed` and 0; evidence anchors require `identity_verified` and
null. Each of the five excluded objects has exactly those four keys plus
`platform_result` and `embedded_anchor`; its outer result is
`not_run_platform_excluded` and its outer exit status is null. The portable result fixes
`passed_acceptance_gate_count = 124` and `skip_count = 0`. Its `item_results_digest` is the
P12-CJ-1 SHA-256 of that exact array. The
historical count is 308 + 32 + 39 + 101 + 100 + 36; Studio results remain individual leaf
results and are not miscounted as Python unittest cases.

Every excluded `platform_result` is a closed object with exactly
`replay_platform`, `ubuntu_historical_execution_status`, `disposition`,
`linux_public_pilot_readiness`, `executor_result`, `exit_status`, and `reason`.
The first six values are respectively `ubuntu-24.04`, `not_proven`,
`excluded_acceptance_gate`, `blocked`, `not_run_platform_excluded`, and null. Exact reason
tokens are:

| Gate ID | Exact reason |
| --- | --- |
| `p8_compose_runtime` | `linux_host_uid_private_bind_incompatible_with_container_uid_10001` |
| `p8_golden_path` | `transitively_invokes_excluded_p8_compose_runtime` |
| `p10_compose_runtime` | `immutable_darwin_guard_actual_macos_required` |
| `p10_quickstart` | `immutable_darwin_only_local_candidate_and_macos_result` |
| `p10_remote_distribution` | `immutable_remote_gate_includes_darwin_quickstart_and_macos_result` |

Every `embedded_anchor` is a closed object with exactly `gate_id`, `anchor_platform`,
`anchor_historical_status`, `purpose`, `source_commit`, `source_tree`, `source_path`,
`source_blob`, `source_file_sha256`, `selection`, `canonicalization`, `canonical_bytes`,
and `canonical_sha256`. `anchor_platform` is `darwin`, `anchor_historical_status` is
`passed`, `purpose` is `immutable_platform_scoped_identity_only`, and `canonicalization`
is `P12-CJ-1`. Appendix C fixes every remaining exact value. The embedded object is
verification metadata inside its excluded item; it is not one of the 17
`evidence_anchor` inventory rows and cannot increase the total above 151.

For a pull_request envelope, repository, PR number, head branch/SHA and base ref/SHA are
the exact event-payload values after the runner/Git cross-checks above; `head_branch` is
`codex/p12-public-pilot-continuity-rebaseline-v4` and `pull_request_number` is the same positive integer later obtained from the
attempt-specific run API. For the later push-to-main closeout run only, event is `push`,
head_branch is `main`, head_sha is the identical payload-after/GITHUB_SHA/checked-out-HEAD
value, and base_ref, base_sha and pull_request_number are null. Both variants require
workflow_name `CI` and workflow_path `.github/workflows/ci.yml` derived as specified
above. Stage 13 evidence preflight accepts only the `pull_request` variant for the exact Stage 12 implementation-head run. Stage 17 and Stage 18 validate the separate Stage 16 final-candidate pull-request envelopes. Only Stage 21 consumes the two `push` variants emitted by the exact CI run triggered by the authorized Stage 20 remote-main push; a candidate-branch push or pull-request envelope cannot substitute.

On a failed gate, the same exact schema uses `gate.status: failed`, the real nonzero
failure/error counts and partial executed test count, and
`platform_status.p12_governance_result: failed`; portable inventory execution status is
`failed` if that job owned the failure. Its failing executed item records `failed` and the
real nonzero exit status; unexecuted later items record `not_run_due_to_prior_failure` and
null. The immutable inventory bindings and Linux/Darwin
classifications do not change. The workflow job concludes failure. Evidence preflight
rejects a failed envelope even when its digest and identities are valid.

`job_id` is the immutable workflow job key exposed by `GITHUB_JOB`, not the REST database
ID. Evidence preflight separately obtains the numeric `job_database_id` from the
attempt-specific jobs API and binds it to the selected log and envelope digest.

The inventory blob, file SHA and digest are computed from the exact committed manifest at
`head_sha`. Both envelopes MUST contain identical inventory bindings and counts. The
current job verifies the committed manifest and binds it without claiming execution. The
portable job additionally proves every executed result. The inventory digest is
`sha256:` plus P12-CJ-1 SHA-256 over the manifest. The manifest's exact blob and digest,
which cannot exist before the implementation commit, become immutable dynamic identities
through the exact head and both matching envelopes; the committed provenance receipt and
summary bind them. A branch, working-tree or caller-supplied value is forbidden.

The gate result digest is computed from a separately canonical safe gate-result object
written in an OS-temporary mode-0700 directory. The envelope contains no local path,
credential, token, authorization header, certificate, environment dump, raw Actions log,
provider payload, private container output, personal identifier or private evidence.

The gate step always writes an integer status and safe result before envelope emission.
Envelope emission runs exactly once after cleanup, including when the gate failed. A final
enforcement step exits with the original nonzero gate status, so envelope transport never
turns a failed gate into a successful job. If checkout or infrastructure failure prevents
emission, the missing envelope makes the run ineligible for evidence. Evidence preflight
accepts only completed runs and successful required jobs whose envelopes say passed.

### Current workflow no-publication oracle

Workflow checkout, gate and envelope steps cannot expose or consume a secret. The exact
workflow contains no `secrets` context, `github.token`, credential helper response,
authorization header, registry login, `docker push`, build-push with push true, Cosign
sign/attest, `gh release`, `git push`, `git tag`, package publish/upload,
`actions/upload-artifact`, `actions/download-artifact` or equivalent remote mutation.

The CI-policy checker parses exact YAML structure and shell commands rather than trusting
substring absence. It requires all action pins, counts, job IDs/names, runner labels,
timeouts, permissions, events, exact-head checkout, gate commands, envelope finalization,
original-status enforcement and zero-publication rules. Aliases, nested shell,
unapproved or caller-overrideable identity indirection, mutable actions, condition
bypasses and tolerated failures are rejected. The only permitted environment-mediated
values are the contract-listed `P12_JSON_OUTPUT` result path and the named standard GitHub
runner identity inputs, each consumed only under the exact payload/Git/REST cross-checks
defined above; this narrow permission is not a general environment-indirection exception.

The accepted P11R phase-specific tag sentinel remains byte-identical and replays only on
its exact object through the portable inventory. P12's current checker independently
requires zero tags and zero Releases. No P12-P19 result authorizes a future tag,
publication or a relaxation of those checks.

### Exact P12 v4 governance test inventory

P12 retains exactly 136 unique unittest method IDs. Existing methods are renamed or expanded with subtests; no required assertion is removed to preserve the count.

- Historical inventory tests fix 5/124/17/5/151, exact ordered exclusions, independent set derivation, five embedded anchors, 19 nullable entrypoints, 110 required entrypoints, recursion rejection, cleanup, and bounded resources.
- Evidence tests cover exact pull-request and push-to-main envelopes, reject candidate-push substitution and any pre-merge push-envelope requirement, and cover the one-use receipt, both jobs' observed environments, committed inventory identities, all 151 summary item results, current P10 registry protection, platform-qualified summary fields, and malformed/missing/duplicate/reordered/forged/wrong-platform/wrong-count/wrong-set/claim-overreach cases.
- Rebaseline tests preserve all B+ product decisions, P12–P20 order, P20-L0 ownership, and the three independent status dimensions.
- Repository/provenance tests preserve the exact 42 paths, immutable acceptance, v1/v2/v3 refs and absence/presence rules, both rejected-v2 run records, PR #14 boundary, protected P10 identities, and zero publication. Existing test methods gain subtests for the exact 21-stage order, content-bearing snapshot manifest/payload recomputation, rejection of worktree-only verification, five-condition cleanup barrier, exact fast-forward/main refspec/indirect-merge PR/retained-v4-branch closeout oracles, and separate final acceptance/local-merge/remote-push/closeout authorities; the unique method count remains 136.

The historical Python count remains exactly 616:

| Suite | Tests |
| --- | ---: |
| P8 current historical suite | 308 |
| P9 | 32 |
| P10 | 39 |
| P11 | 101 |
| P11R selected current-P11 tests | 100 |
| P11R governance tests | 36 |
| Total | 616 |

The P11R 100-test selection excludes only `tests.p11.test_repository.RepositoryTests.test_repository_gate_accepts_exact_development_scope`, the exact development-only repository acceptance test fixed by its accepted contract. None of the five platform exclusions is a Python unittest leaf, so reclassification does not change 616.

#### Prospective exact 136 P12 test IDs

The following method identities are fixed for v4. Renamed methods carry expanded subtests; their replacement does not add or remove a method.

~~~text
tests.p12.test_ci_policy.CiPolicyTests.test_exact_canonical_workflow_passes
tests.p12.test_ci_policy.CiPolicyTests.test_pull_request_target_is_rejected
tests.p12.test_ci_policy.CiPolicyTests.test_workflow_dispatch_is_rejected
tests.p12.test_ci_policy.CiPolicyTests.test_workflow_call_is_rejected
tests.p12.test_ci_policy.CiPolicyTests.test_schedule_is_rejected
tests.p12.test_ci_policy.CiPolicyTests.test_write_permission_is_rejected
tests.p12.test_ci_policy.CiPolicyTests.test_oidc_permission_is_rejected
tests.p12.test_ci_policy.CiPolicyTests.test_secret_context_is_rejected
tests.p12.test_ci_policy.CiPolicyTests.test_mutable_action_reference_is_rejected
tests.p12.test_ci_policy.CiPolicyTests.test_persisted_checkout_credentials_are_rejected
tests.p12.test_ci_policy.CiPolicyTests.test_direct_node_version_is_rejected
tests.p12.test_ci_policy.CiPolicyTests.test_wrong_node_file_content_is_rejected
tests.p12.test_ci_policy.CiPolicyTests.test_package_manager_integrity_drift_is_rejected
tests.p12.test_ci_policy.CiPolicyTests.test_historical_gate_is_not_current_ci
tests.p12.test_ci_policy.CiPolicyTests.test_evidence_preflight_is_rejected_in_ci
tests.p12.test_ci_policy.CiPolicyTests.test_publication_command_is_rejected
tests.p12.test_ci_policy.CiPolicyTests.test_compose_without_main_push_condition_is_rejected
tests.p12.test_ci_policy.CiPolicyTests.test_ubuntu_2404_is_exact
tests.p12.test_ci_policy.CiPolicyTests.test_two_required_jobs_are_exact
tests.p12.test_ci_policy.CiPolicyTests.test_action_inventory_is_exact
tests.p12.test_ci_policy.CiPolicyTests.test_portable_timeout_contract_is_exact
tests.p12.test_ci_policy.CiPolicyTests.test_artifact_transport_is_rejected
tests.p12.test_evidence_gate.EvidenceGateTests.test_claim_and_status_are_narrow
tests.p12.test_evidence_gate.EvidenceGateTests.test_canonical_json_is_sorted_compact_utf8
tests.p12.test_evidence_gate.EvidenceGateTests.test_range_digest_is_order_sensitive_and_prefixed
tests.p12.test_evidence_gate.EvidenceGateTests.test_valid_unexpired_authorization_passes
tests.p12.test_evidence_gate.EvidenceGateTests.test_expired_authorization_fails_closed
tests.p12.test_evidence_gate.EvidenceGateTests.test_authorization_for_another_head_fails_closed
tests.p12.test_evidence_gate.EvidenceGateTests.test_writer_creates_only_summary
tests.p12.test_evidence_gate.EvidenceGateTests.test_writer_refuses_existing_summary
tests.p12.test_evidence_gate.EvidenceGateTests.test_preflight_receipt_is_canonical_mode_0600
tests.p12.test_evidence_gate.EvidenceGateTests.test_preflight_receipt_refuses_nonempty_directory
tests.p12.test_evidence_gate.EvidenceGateTests.test_preflight_receipt_refuses_repository_path
tests.p12.test_evidence_gate.EvidenceGateTests.test_exact_ghcr_inventory_passes
tests.p12.test_evidence_gate.EvidenceGateTests.test_extra_ghcr_inventory_entry_fails_closed
tests.p12.test_evidence_gate.EvidenceGateTests.test_tls_ca_fallback_allows_only_certificate_failure
tests.p12.test_evidence_gate.EvidenceGateTests.test_public_evidence_vocabulary_contains_no_live_claim
tests.p12.test_evidence_gate.EvidenceGateTests.test_exact_two_ci_envelopes_pass
tests.p12.test_evidence_gate.EvidenceGateTests.test_forged_marker_fails_closed
tests.p12.test_evidence_gate.EvidenceGateTests.test_duplicate_envelope_fails_closed
tests.p12.test_evidence_gate.EvidenceGateTests.test_wrong_job_fails_closed
tests.p12.test_evidence_gate.EvidenceGateTests.test_wrong_attempt_fails_closed
tests.p12.test_evidence_gate.EvidenceGateTests.test_truncated_log_fails_closed
tests.p12.test_evidence_gate.EvidenceGateTests.test_unbound_dynamic_field_fails_closed
tests.p12.test_evidence_gate.EvidenceGateTests.test_missing_malformed_or_digest_mismatch_fails_closed
tests.p12.test_evidence_gate.EvidenceGateTests.test_wrong_run_or_head_fails_closed
tests.p12.test_evidence_gate.EvidenceGateTests.test_full_actions_log_retention_fails_closed
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_canonical_inventory_passes
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_typed_counts_are_exact
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_exact_five_platform_exclusions
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_gate_set_difference_is_exact
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_p8_bootstrap_is_setup_only
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_anchors_are_not_gate_results
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_per_object_resource_limits
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_cross_object_state_is_rejected
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_historical_subprocess_is_required
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_current_tree_module_shadowing_is_rejected
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_module_blob_mismatch_is_rejected
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_leaf_results_remain_individual
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_recursive_aggregate_is_rejected
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_object_cleanup_precedes_next_setup
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_timeout_values_are_exact
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_missing_gate_fails_closed
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_extra_exclusion_fails_closed
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_dynamic_membership_fails_closed
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_entrypoint_identity_is_exact
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_five_embedded_darwin_anchors_are_platform_scoped
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_linux_claim_laundering_fails_closed
tests.p12.test_historical_inventory.HistoricalInventoryTests.test_zero_residue_is_required
tests.p12.test_migrations.MigrationTests.test_exact_current_migration_gate_passes
tests.p12.test_migrations.MigrationTests.test_manifest_identity_is_exact
tests.p12.test_migrations.MigrationTests.test_migrations_one_through_eight_are_exact
tests.p12.test_migrations.MigrationTests.test_future_owners_are_exact
tests.p12.test_migrations.MigrationTests.test_migration_009_owner_drift_fails_closed
tests.p12.test_migrations.MigrationTests.test_migration_011_owner_drift_fails_closed
tests.p12.test_migrations.MigrationTests.test_migration_012_owner_drift_fails_closed
tests.p12.test_migrations.MigrationTests.test_migration_013_owner_drift_fails_closed
tests.p12.test_migrations.MigrationTests.test_migration_014_owner_drift_fails_closed
tests.p12.test_migrations.MigrationTests.test_migration_015_cannot_gain_an_owner
tests.p12.test_provenance.ProvenanceTests.test_complete_receipt_passes
tests.p12.test_provenance.ProvenanceTests.test_historical_anchor_set_is_exact
tests.p12.test_provenance.ProvenanceTests.test_p10_subjects_are_fixed
tests.p12.test_provenance.ProvenanceTests.test_active_and_superseded_sets_are_both_protected
tests.p12.test_provenance.ProvenanceTests.test_all_nine_p10_runs_are_fixed
tests.p12.test_provenance.ProvenanceTests.test_receipt_rejects_missing_covered_path
tests.p12.test_provenance.ProvenanceTests.test_receipt_rejects_source_read
tests.p12.test_provenance.ProvenanceTests.test_receipt_rejects_publication
tests.p12.test_provenance.ProvenanceTests.test_receipt_rejects_p10_lifecycle_drift
tests.p12.test_provenance.ProvenanceTests.test_receipt_rejects_local_absolute_path
tests.p12.test_provenance.ProvenanceTests.test_rejected_attempt_chains_and_run_summaries_are_exact
tests.p12.test_provenance.ProvenanceTests.test_blueprint_source_identity_is_exact
tests.p12.test_rebaseline.RebaselineTests.test_complete_living_rebaseline_passes
tests.p12.test_rebaseline.RebaselineTests.test_exact_living_document_inventory
tests.p12.test_rebaseline.RebaselineTests.test_exact_p12_through_p20_titles
tests.p12.test_rebaseline.RebaselineTests.test_exact_core_record_contract_passes
tests.p12.test_rebaseline.RebaselineTests.test_project_scope_authority_expansion_fails_closed
tests.p12.test_rebaseline.RebaselineTests.test_project_running_state_fails_closed
tests.p12.test_rebaseline.RebaselineTests.test_waiting_kind_rename_fails_closed
tests.p12.test_rebaseline.RebaselineTests.test_goal_binding_owner_drift_fails_closed
tests.p12.test_rebaseline.RebaselineTests.test_memory_admission_lifecycle_expansion_fails_closed
tests.p12.test_rebaseline.RebaselineTests.test_memory_record_silent_overwrite_fails_closed
tests.p12.test_rebaseline.RebaselineTests.test_trigger_correlation_status_expansion_fails_closed
tests.p12.test_rebaseline.RebaselineTests.test_automatic_authorization_owner_drift_fails_closed
tests.p12.test_rebaseline.RebaselineTests.test_current_roadmap_order_passes
tests.p12.test_rebaseline.RebaselineTests.test_swapped_roadmap_phase_fails_closed
tests.p12.test_rebaseline.RebaselineTests.test_renamed_roadmap_owner_fails_closed
tests.p12.test_rebaseline.RebaselineTests.test_adr_has_all_core_contract_markers
tests.p12.test_rebaseline.RebaselineTests.test_missing_core_marker_fails_closed
tests.p12.test_rebaseline.RebaselineTests.test_governance_only_claim_boundary_passes
tests.p12.test_rebaseline.RebaselineTests.test_runtime_overclaim_fails_closed
tests.p12.test_rebaseline.RebaselineTests.test_public_pilot_overclaim_fails_closed
tests.p12.test_rebaseline.RebaselineTests.test_all_four_future_gates_are_independent
tests.p12.test_rebaseline.RebaselineTests.test_three_platform_status_dimensions_are_independent
tests.p12.test_rebaseline.RebaselineTests.test_five_darwin_evidence_bindings_are_platform_scoped
tests.p12.test_rebaseline.RebaselineTests.test_p20_l0_is_first_blocking_subgate
tests.p12.test_rebaseline.RebaselineTests.test_p20_l0_does_not_reorder_p13_through_p20
tests.p12.test_repository.RepositoryTests.test_acceptance_allowlist_has_exactly_forty_two_paths
tests.p12.test_repository.RepositoryTests.test_implementation_allowlist_has_exactly_forty_paths
tests.p12.test_repository.RepositoryTests.test_implementation_changed_set_has_exactly_forty_one_paths
tests.p12.test_repository.RepositoryTests.test_final_changed_set_has_exactly_forty_two_paths
tests.p12.test_repository.RepositoryTests.test_acceptance_commit_parent_tree_and_blob_are_exact
tests.p12.test_repository.RepositoryTests.test_acceptance_working_file_identity_is_exact
tests.p12.test_repository.RepositoryTests.test_acceptance_commit_changes_only_contract
tests.p12.test_repository.RepositoryTests.test_implementation_path_set_validates
tests.p12.test_repository.RepositoryTests.test_final_path_set_validates
tests.p12.test_repository.RepositoryTests.test_missing_implementation_path_fails_closed
tests.p12.test_repository.RepositoryTests.test_unexpected_path_fails_closed
tests.p12.test_repository.RepositoryTests.test_summary_is_required_only_for_final
tests.p12.test_repository.RepositoryTests.test_makefile_change_is_exactly_bounded
tests.p12.test_repository.RepositoryTests.test_preexisting_makefile_recipe_drift_fails_closed
tests.p12.test_repository.RepositoryTests.test_generic_ci_alias_must_point_only_to_p12
tests.p12.test_repository.RepositoryTests.test_new_makefile_target_set_is_exact
tests.p12.test_repository.RepositoryTests.test_v1_v2_v3_refs_are_preserved
tests.p12.test_repository.RepositoryTests.test_v1_v2_v3_are_not_v4_ancestors
tests.p12.test_repository.RepositoryTests.test_attempt_ref_presence_and_absence_are_exact
tests.p12.test_repository.RepositoryTests.test_pr14_close_without_merge_boundary_is_exact
~~~

### Required negative tests

- Reject Darwin `passed` promoted to Ubuntu/Linux passed.
- Reject Ubuntu `not_proven` written into the Darwin anchor.
- Reject merged cross-platform status or any missing platform qualifier.
- Reject missing, duplicate, reordered, extra, or wrong exclusion ID.
- Reject an embedded anchor counted as a new inventory row, 22 evidence anchors, total 156, duplicate anchors, or an excluded row retyped as evidence anchor.
- Reject a missing, additional, renamed, or wrong platform-result key, wrong exact reason token, or missing embedded-anchor key.
- Reject wrong composite keys, source pointers, gate ID, bytes, digest, canonicalization, or a complete-function-return substitution for P10 remote.
- Reject fabricated entrypoint blobs, forbidden non-null entrypoints, missing required entrypoints, wrong mode/blob/callable, or current-tree module shadowing.
- Reject recursive aggregate calls, cross-object module/cache/workspace reuse, missing cleanup, unbounded timeout, dynamic inventory membership, or a predecessor result whose canonical object/result digest is missing or mismatched.
- Reject excluded rows in passed/skip counts, a P12 pass changing Linux readiness, or a current registry result impersonating historical replay.
- Reject envelope marker/schema/digest/identity failures, wrong event/job/run/attempt/head/base, retained full logs, artifact transport, credentials, write permissions, OIDC, or publication.
- Reject a receipt or summary with a missing, extra, duplicate, renamed, reordered, noncanonical, or mismatched field; a consumed, expired, or wrong-head receipt; or any summary that treats current P10 registry protection as `p10_remote_distribution`.
- Reject metadata-only WIP snapshots, missing or altered payload bytes, unsafe/duplicate/extra paths, manifest checksum or framed-digest drift, verification sourced only from the dirty worktree, and cleanup before every five-condition barrier predicate holds.
- Reject a missing, combined, renamed, or reordered stage; implicit next-stage authority; combined final acceptance/merge/push/closeout authority; a candidate-branch envelope substituted for push-to-main; a push-to-main envelope required at any stage 1–20; or an envelope not emitted by the exact CI run triggered by the authorized stage 20 remote-main push.
- Reject Stage 19 non-fast-forward or merge-commit integration, any Stage 20 refspec other than the single ordinary main-to-main push, a Stage 21 run not caused by that exact push, a missing/failed main Compose smoke, an indirect-merge PR whose merge OID is not the final candidate, non-null auto-merge, or deletion/movement of the retained v4 branch.

## Evidence-before-write read-only preflight

The evidence preflight runs after exact implementation-head CI succeeds and before any
evidence-generation authorization. It is read-only, writes only inside OS temporary
directories, performs no repository or remote mutation, and leaves worktree, index,
untracked files, credential stores, environment overrides, caches and Docker state
unchanged. Any missing capability, identity mismatch, unsafe output, or ambiguous result
fails closed before the evidence writer can run.

The operator supplies the exact P12_FINAL_IMPLEMENTATION_HEAD, an explicit positive
numeric CI run ID, an explicit positive run attempt, and a newly created OS-temporary
receipt directory outside the repository. The preflight MUST NOT select latest, infer a
run from a branch, default to the newest attempt, accept a URL in place of numeric
identity, or follow a moving ref. The implementation provides
make p12-evidence-preflight with the ordered checks below.

### Exact CI-envelope retrieval and parsing

The preflight first verifies active read-only gh authentication without printing a token
or changing authentication state. It creates one OS-temporary working directory outside
the repository with mode 0700, files with mode 0600 and umask 077. It sets no persistent
environment override. The exact read operations are equivalent to:

~~~sh
set -e
test "$P12_CI_RUN_ID" -gt 0
test "$P12_CI_RUN_ATTEMPT" -gt 0
test "${#P12_FINAL_IMPLEMENTATION_HEAD}" -eq 40
umask 077
P12_PREFLIGHT_TEMP="$(mktemp -d "${TMPDIR:-/tmp}/dc-p12-v4-preflight.XXXXXX")"
chmod 700 "$P12_PREFLIGHT_TEMP"
gh api "/repos/jeremyliu1220/digital-colleagues/actions/runs/${P12_CI_RUN_ID}/attempts/${P12_CI_RUN_ATTEMPT}" \
  > "$P12_PREFLIGHT_TEMP/run.json"
gh api --paginate --slurp \
  "/repos/jeremyliu1220/digital-colleagues/actions/runs/${P12_CI_RUN_ID}/attempts/${P12_CI_RUN_ATTEMPT}/jobs?per_page=100" \
  > "$P12_PREFLIGHT_TEMP/job-pages.json"
~~~

The implementation invokes those exact REST resources through gh; it does not scrape the
Actions web UI. It parses both JSON responses with duplicate-key rejection. The run
response must be one completed successful `pull_request` run whose `repository.full_name`
is `jeremyliu1220/digital-colleagues`, name is `CI`, path is
`.github/workflows/ci.yml`, ID and attempt equal the two explicit inputs, head SHA equals
`P12_FINAL_IMPLEMENTATION_HEAD`, and head branch is
`codex/p12-public-pilot-continuity-rebaseline-v4`. Its `pull_requests`
array must contain exactly one entry whose number, head ref/SHA, base ref `main`, base SHA
c1562ea5201394d8a278f4b644daf4029cbb5bd4 and repository identities agree with the run
and envelope. The live PR must carry those same identities, be open and satisfy the exact
null merge/auto-merge oracle below. A run response with an empty, duplicate or ambiguous
PR association fails closed.

The parser rejects duplicate JSON keys and flattens only the pages' jobs arrays. It
selects exactly one completed successful job for each exact display name:

1. Current P12 governance non-publishing verification; and
2. Portable historical replay.

No prefix, suffix, case-folded or matrix-expanded match is permitted. Each selected job
must belong to the exact run and attempt and have a distinct positive numeric REST job
database ID. Missing or duplicate required names, an extra job with the same workflow
job identity, wrong status/conclusion, wrong run URL or an ambiguous page result fails
closed.

For each selected numeric job database ID, and only after selection, the preflight performs
exactly one streaming read of the job-log endpoint. It never writes the complete log to a
file:

~~~sh
set -o pipefail
gh api \
  "/repos/jeremyliu1220/digital-colleagues/actions/jobs/${P12_JOB_DATABASE_ID}/logs" |
  PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_p12_toolchain.py \
    --scope extract-ci-envelope \
    --run-id "$P12_CI_RUN_ID" \
    --attempt "$P12_CI_RUN_ATTEMPT" \
    --job-database-id "$P12_JOB_DATABASE_ID" \
    --expected-job-id "$P12_EXPECTED_JOB_ID" \
    --expected-job-name "$P12_EXPECTED_JOB_NAME" \
    --head-sha "$P12_FINAL_IMPLEMENTATION_HEAD" \
    --safe-output "$P12_PREFLIGHT_TEMP/envelope-${P12_JOB_DATABASE_ID}.json"
~~~

The stream is never printed or copied. The parser scans it once for the anchored envelope expression,
requires exactly one match, decodes unpadded base64url, enforces the 32,768-byte payload
and 43,850-byte line bounds, rejects duplicate keys, re-canonicalizes with P12-CJ-1,
requires byte equality, and verifies the marker digest. It then requires the exact schema
and key set and cross-checks every run, attempt, PR number, job-key, job-name, event,
head branch/SHA, base ref/SHA, repository, workflow name and workflow path value against
the attempt-specific REST data and local exact Git object. Since the jobs REST schema does
not expose the `GITHUB_JOB` key directly, the job-key cross-check is the contract's closed
one-to-one mapping from `current-ci` or `portable-history` to its exact REST display name;
any unmapped key/name pair fails closed. Run ID, attempt, event, workflow name/path,
repository, head and PR/base data come directly from the selected run response. No CLI
argument can make a conflicting envelope value authoritative.

The two envelopes must agree on repository, workflow, run, attempt, event, head, base,
runner family, inventory path/blob/file SHA/digest/counts, the ordered five-item exclusion
set, all platform statuses, the exact registry-protection placeholder, and zero
publication. Their observed image/tool values are independently bound
and need not be identical. The current envelope must say
bound_not_executed_by_this_job; the portable envelope must say passed. Both gate statuses
and both selected REST conclusions must be success/passed.

Both CI envelopes contain exactly
`p12_current_p10_registry_protection = {"reason":"evidence_preflight_only","status":"not_evaluated"}`.
CI has no registry credential or `read:packages` proof and cannot change that result. Only
Stage 13 may produce an authenticated read-only result under the same P12-owned name for
the one-use receipt and summary. It never replaces, satisfies, or impersonates the
excluded accepted gate `p10_remote_distribution`.

The preflight computes the portable manifest blob from
P12_FINAL_IMPLEMENTATION_HEAD:docs/p12/portable-historical-inventory.json, obtains those
exact committed bytes, verifies regular-file mode 100644 and no symlink, applies P12-CJ-1,
and compares blob, file SHA and inventory digest to both envelopes. No value may come from
a branch tip, working-tree-only file, caller input or one envelope alone.

Missing, duplicate, truncated, malformed, oversized, forged-marker, invalid-base64,
noncanonical, digest-mismatched, wrong-job, wrong-run, wrong-attempt, wrong-head,
wrong-workflow, wrong-event or dynamically unbound envelopes fail closed. A download,
transport, pagination, parse or deletion failure is indeterminate and cannot authorize
evidence. No retry is implicit; another attempt requires owner direction.

Immediately after safe fields and envelope digests are placed in the one-use receipt, the
ephemeral run/job JSON and extracted safe projections are removed with the exact temporary
directory. A complete job log is never stored. No log or complete envelope is copied to
the repository, receipt, summary, provenance, console, cache or retained artifact. The
receipt and summary retain only approved safe fields and the two sha256 envelope digests.

### GitHub and GHCR access

1. Confirm an active gh authentication context for the exact repository and required
   read-only repository, pull-request and Actions-run operations. Do not log in, refresh,
   change scopes, write configuration, print a token, or display authorization headers.
2. Confirm read:packages capability. A printed scope claim alone is insufficient: the
   preflight must successfully perform a read-only manifest lookup for every exact
   protected active and superseded GHCR digest below and verify subject and digest.
3. Confirm the attempt-specific run, job records and two canonical envelopes satisfy the
   preceding retrieval contract. Branch name, latest-run status, another attempt, a
   successful run for another commit, or a digest not recomputed from canonical envelope
   bytes is insufficient.
4. Sanitize output to repository, workflow/run numeric identity, commit/digest, safe
   capability result and status. Never persist a token, authorization header, credential
   helper response, personal account identifier, or provider payload.

The authenticated result is named only `p12_current_p10_registry_protection` and uses
schema `digital-colleagues.p12-v4-current-p10-registry-protection.v1`. Its closed result
binds repository, the two exact GHCR subjects, active and superseded source commits and
digests, lifecycle labels, all nine historical run identities, each subject's exact
14-version/four-tag canonical inventory digest, signature/attestation/bundle verification,
`publication_count = 0`, and `status = passed`. Its `result_digest` is P12-CJ-1 SHA-256.
It contains no historical quickstart status and cannot be named, interpreted, or counted
as `p10_remote_distribution`; that accepted gate remains an excluded Ubuntu item with its
own Darwin anchor.

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
implementation head/tree, explicit workflow/run/attempt/PR/event, the two workflow job
keys, exact display names and numeric REST job database IDs, each envelope SHA-256, the
approved safe envelope fields, each observed runner/image/architecture/tool identity,
portable inventory path/blob/file SHA/digest/counts, the ordered five-item exclusion set,
five excluded result/reason/anchor objects, the three separate platform/governance
statuses, the P12-owned registry-protection result, protected GHCR inventory, pyproject and lock identities,
normalized package results, CA class and digest, timestamp, single-use nonce,
preflight-environment cleanup before receipt creation, and receipt lifecycle
pending_consumption. It does not contain the encoded or decoded complete envelope, full
Actions log, secret, token, credential, private/live payload, personal account identity,
absolute CA path or certificate content.

The receipt schema is exactly `digital-colleagues.p12-v4-evidence-preflight-receipt.v1`.
Its closed top-level key set and logical types are:

~~~json
{
  "acceptance": {
    "blob": "<40 lowercase hex>",
    "commit": "<40 lowercase hex>"
  },
  "ca_verification": {
    "bundle_sha256": "<64 lowercase hex or null>",
    "certifi_version": "2026.7.22",
    "class": "system_default",
    "status": "passed"
  },
  "ci": {
    "base_ref": "main",
    "base_sha": "c1562ea5201394d8a278f4b644daf4029cbb5bd4",
    "event": "pull_request",
    "head_branch": "codex/p12-public-pilot-continuity-rebaseline-v4",
    "head_sha": "<P12_FINAL_IMPLEMENTATION_HEAD>",
    "jobs": [
      {
        "envelope_sha256": "<64 lowercase hex>",
        "job_database_id": 1,
        "job_id": "current-ci",
        "job_name": "Current P12 governance non-publishing verification",
        "observed_environment": {
          "architecture": "<nonempty safe exact value>",
          "docker_compose_version": "<nonempty safe exact value>",
          "docker_server_version": "<nonempty safe exact value>",
          "node_version": "<nonempty safe exact value>",
          "npm_version": "<nonempty safe exact value>",
          "python_version": "<nonempty safe exact value>",
          "runner_image_os": "<nonempty safe exact value>",
          "runner_image_version": "<nonempty safe exact value>",
          "runner_os": "<nonempty safe exact value>"
        }
      },
      {
        "envelope_sha256": "<64 lowercase hex>",
        "job_database_id": 2,
        "job_id": "portable-history",
        "job_name": "Portable historical replay",
        "observed_environment": {
          "architecture": "<nonempty safe exact value>",
          "docker_compose_version": "<nonempty safe exact value>",
          "docker_server_version": "<nonempty safe exact value>",
          "node_version": "<nonempty safe exact value>",
          "npm_version": "<nonempty safe exact value>",
          "python_version": "<nonempty safe exact value>",
          "runner_image_os": "<nonempty safe exact value>",
          "runner_image_version": "<nonempty safe exact value>",
          "runner_os": "<nonempty safe exact value>"
        }
      }
    ],
    "pull_request_number": 1,
    "run_attempt": 1,
    "run_id": 1,
    "workflow_path": ".github/workflows/ci.yml"
  },
  "cleanup_residue_count": 0,
  "expires_at": "<UTC Z timestamp>",
  "implementation": {
    "head": "<40 lowercase hex>",
    "ordered_commits": ["<40 lowercase hex>"],
    "range_digest": "sha256:<64 lowercase hex>",
    "tree": "<40 lowercase hex>"
  },
  "inventory": {
    "blob": "<40 lowercase hex>",
    "digest": "sha256:<64 lowercase hex>",
    "evidence_anchor_count": 17,
    "excluded_acceptance_gate_count": 5,
    "excluded_gate_ids": [
      "p8_compose_runtime",
      "p8_golden_path",
      "p10_compose_runtime",
      "p10_quickstart",
      "p10_remote_distribution"
    ],
    "excluded_results": ["<five closed platform-result plus embedded-anchor objects>"],
    "included_acceptance_gate_count": 124,
    "item_results_digest": "sha256:<64 lowercase hex>",
    "passed_acceptance_gate_count": 124,
    "path": "docs/p12/portable-historical-inventory.json",
    "setup_count": 5,
    "sha256": "<64 lowercase hex>",
    "skip_count": 0,
    "total_item_count": 151
  },
  "issued_at": "<UTC Z timestamp>",
  "lifecycle": "pending_consumption",
  "nonce": "<32-byte random lowercase hex>",
  "p10_protected_identity_digest": "sha256:<64 lowercase hex>",
  "p12_current_p10_registry_protection": {
    "result_digest": "sha256:<64 lowercase hex>",
    "status": "passed"
  },
  "package_verification_digest": "sha256:<64 lowercase hex>",
  "platform_status": {
    "linux_public_pilot_readiness": "blocked",
    "p12_governance_result": "passed",
    "ubuntu_historical_execution_status": "five_excluded_not_proven"
  },
  "publication_count": 0,
  "repository": "jeremyliu1220/digital-colleagues",
  "schema": "digital-colleagues.p12-v4-evidence-preflight-receipt.v1"
}
~~~

The example's positive integers and dynamic digests are exact runtime types, not default
values. `jobs` order is exactly current-ci then portable-history. `excluded_results`
contains the five objects in `excluded_gate_ids` order and uses the closed schemas above.
Each job's `observed_environment` is the complete safe nine-field projection from that
job's exact Stage 12 envelope. Inventory `path`, `blob`, `sha256`, and `digest` bind the
same committed manifest independently checked in both envelopes.
The receipt requires 124 passed included gates, zero skipped gates, zero cleanup residue,
and zero publication; an excluded item is never included in either count.
The CA class is `system_default` with null bundle digest or `locked_certifi` with the exact
bundle digest. Additional, missing, reordered, duplicated, or renamed keys fail closed.

`implementation.ordered_commits` is the complete ancestry-ordered range beginning with
the v4 acceptance-only commit and ending with the exact final implementation/correction
HEAD, with no omission, duplicate, merge, summary commit, or commit outside that range.
The nonce is exactly 32 random bytes encoded as 64 lowercase hexadecimal characters.

The preflight does not create artifacts/p12/summary.json. The later evidence authorization
MUST explicitly name the receipt SHA-256, exact implementation head, numeric CI run ID,
numeric run attempt, both envelope digests and an expiration for that authorization. The
evidence writer receives an explicit receipt
path and expected digest, requires a regular non-symlink mode-0600 file outside the
repository, re-hashes and parses canonical JSON, verifies the named authorization, head,
tree, run, attempt, job/envelope bindings and still-current read-only identities, and
consumes the nonce once. It never
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

## Appendix A — Normative complete 129-gate platform portability audit

### Audit method and completeness rule

For each accepted identity, the audit binds its milestone commit and tree, exact command or P12-owned verification operation, command kind, nullable entrypoint identity, important transitive calls, result/platform semantics, and disposition. Source inspection covers `platform.system`, `sys.platform`, `os.uname`, Darwin/macOS/Linux tokens, architecture checks, Docker-host assumptions, recursive aggregates, and hard-coded result claims. In the two tables, the exact grammar metavariable `<pN-python>` means the executable in that exact object's sole hash-locked Python environment, and `<pN-temp>` means that object's private mode-0700 OS-temporary root; neither is HTML, a caller-supplied path, an environment override, or permission to reuse another object's executable or temporary state.

The audit is fail closed. A sixth excluded gate, an object/blob mismatch, a fabricated entrypoint, or an unresolved reachable platform branch invalidates this decision. The completed audit found exactly the five exclusions above and no sixth.

Entrypoint rules are exact:

- 12 `python_module`, three `git`, and four `predecessor_result` gates have `entrypoint = null`.
- 89 `python_script` gates bind an exact script path, mode, blob, and callable.
- 20 `npm_script` gates bind the exact `package.json` path, mode, blob, and script-name callable; no independent script blob is invented.
- One `python_function` gate binds the exact module path, mode, blob, and function callable.
- The accepted-gate universe therefore has 19 null and 110 non-null entrypoints.

### Exact object chain

| Object | Commit | Tree | Accepted gate count | Included | Excluded |
| --- | --- | --- | ---: | ---: | ---: |
| P8 | `0bb80ab187932fbad42fbf665b8310987609a1f5` | `311eb777c3d17a9a3722a16c394b9913c283b416` | 58 | 56 | 2 |
| P9 | `11aa240af8db2ca515325dc059b1a77f7badc874` | `a27cb6ce9f568b04083a88f7ba06f033235f4cbc` | 7 | 7 | 0 |
| P10 | `4bef5629d450c6bb3940f606fc90194e008ee8fd` | `909b566b7ba9f7beb143cd0b29cf95fbd1178bbe` | 24 | 21 | 3 |
| P11 | `7e5387f148f86b5c9b07820dd8b8f4e18e12dc38` | `6d7c1b3053fefc1f3b14a4b39fde2d5adb641990` | 19 | 19 | 0 |
| P11R | `c1562ea5201394d8a278f4b644daf4029cbb5bd4` | `ae0f33263cfc7445fef69656ad9c5cb04d4a2d00` | 21 | 21 | 0 |
| Total | — | — | 129 | 124 | 5 |

### Exact five-gate root-cause evidence

| Gate | Exact evidence and call chain | Ubuntu conclusion |
| --- | --- | --- |
| `p8_compose_runtime` | Blob `e8e3f496d7bde9c5eb2859d1d87e1b8532b60467`; `main` lines 1436–1469 calls `check_compose_runtime` line 1459/definition line 816. It creates a host operator directory mode 0700 at lines 831–836, bind-mounts it at `/operator` via lines 127–143, creates private mode-0600 files at lines 179–184 and 340, then performs container restore at lines 493–511. Dockerfile blob `722eddd28d27ee3f45d7b10c47915a60a8bf2496` fixes `USER 10001:10001` at lines 17–22. | Native Ubuntu runner-owned private paths cannot be traversed/read by container UID 10001; exact execution is `not_proven`, not skipped or passed. |
| `p8_golden_path` | Blob `d5f38a86baa02583ee2ec1639c3163954a188399`; `main` lines 67–86 calls `check_golden_path` line 72; definition lines 21–31 directly calls `check_compose_runtime(root)` at line 23 and requires runtime plus cleanup passed. | It necessarily re-enters the same non-portable actual Compose path and is a distinct excluded gate with a distinct anchor. |
| `p10_compose_runtime` | Blob `44cf5504f0728e571cfeaa2e33d75c8b58bec738`; `main` lines 478–498 → `check` 468–475 → `build_local_candidate` 87–122 → `_native_platform` 67–75. | Non-Darwin raises `actual_macos_required`; Ubuntu execution cannot pass faithfully. |
| `p10_quickstart` | Blob `6b352a180683969deed9b396b9b94b4488232411`; `main` 222–247 → `check_quickstart` 168–175 → Darwin-only `build_local_candidate`. Result construction lines 135–165 asserts `actual_macos: true` and `platform_class: macos/<machine>`. | Ubuntu necessarily fails before trials or would misstate platform evidence. |
| `p10_remote_distribution` | Same quickstart blob; flag dispatch lines 231–235 → `check_remote_distribution` 178–219 → registry verification in distribution blob `a4687649f3ab6e64f13c41015527f17265b1130a` lines 1329–1417 → one `run_quickstart_trials` call at lines 202–208 → its internal three-trial loop at line 78. Bundle `dc` blob `e9368d5d648a20b71d41399df247ec41476ab696` lines 390–403 requires Darwin and macOS tools; its quickstart result asserts macOS. | The accepted gate is a combined registry-plus-Darwin-quickstart gate, not a read-only registry check. Ubuntu classification is excluded and `not_proven`. |

### Audit rows

| # | Gate ID | Object / exact commit | Command kind | Exact command or verification operation | Entrypoint path / callable / mode / blob | Important transitive calls | Platform classification | Disposition | Decision evidence | Accepted platform anchor |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | p8_ruff_lint | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_module | \<p8-python\> -m ruff check src scripts tests | null | Locked Python module invocation; no repository script entrypoint and no reachable historical aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the exact P8 Ruff lint leaf. | none; exact Ubuntu replay remains authoritative |
| 2 | p8_ruff_format | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_module | \<p8-python\> -m ruff format --check src scripts tests | null | Locked Python module invocation; no repository script entrypoint and no reachable historical aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the exact P8 Ruff format leaf. | none; exact Ubuntu replay remains authoritative |
| 3 | p8_mypy_strict | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_module | \<p8-python\> -m mypy src scripts tests | null | Locked Python module invocation; no repository script entrypoint and no reachable historical aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the exact P8 strict Mypy leaf. | none; exact Ubuntu replay remains authoritative |
| 4 | p8_python_unittest | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/run_p8_unittest_suite.py --start-directory tests --top-level-directory . --json-output \<p8-temp\>/p8-unittest.json | scripts/run_p8_unittest_suite.py#main / 100644 / 35d0ef6a88025ef5bc10925009e044c6a84025c8 | Generic unittest discovery/runner; P8 tests import only helper parsing from runtime checker and do not invoke actual Compose | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Run the exact P8 Python unittest leaf without batching it. | none; exact Ubuntu replay remains authoritative |
| 5 | p8_studio_eslint | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | npm_script | corepack npm run lint | studio/package.json#lint / 100644 / f7aac57ff88ce1b7f779c3b3f63fdf7b79b6c916 | studio/package.json script lint → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P8 Studio lint leaf separately. | none; exact Ubuntu replay remains authoritative |
| 6 | p8_studio_prettier | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | npm_script | corepack npm run format:check | studio/package.json#format:check / 100644 / f7aac57ff88ce1b7f779c3b3f63fdf7b79b6c916 | studio/package.json script format:check → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P8 Studio format:check leaf separately. | none; exact Ubuntu replay remains authoritative |
| 7 | p8_studio_typescript | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | npm_script | corepack npm run typecheck | studio/package.json#typecheck / 100644 / f7aac57ff88ce1b7f779c3b3f63fdf7b79b6c916 | studio/package.json script typecheck → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P8 Studio typecheck leaf separately. | none; exact Ubuntu replay remains authoritative |
| 8 | p8_studio_vitest | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | npm_script | corepack npm test -- --reporter=json --outputFile=\<p8-temp\>/studio-vitest.json | studio/package.json#test / 100644 / f7aac57ff88ce1b7f779c3b3f63fdf7b79b6c916 | studio/package.json script test → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the exact accepted P8 Vitest result as its own leaf. | none; exact Ubuntu replay remains authoritative |
| 9 | p8_studio_vite_build | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | npm_script | corepack npm run build | studio/package.json#build / 100644 / f7aac57ff88ce1b7f779c3b3f63fdf7b79b6c916 | studio/package.json script build → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P8 Studio build leaf separately. | none; exact Ubuntu replay remains authoritative |
| 10 | p8_repository | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p8_repository.py . | scripts/check_p8_repository.py#main / 100644 / 097b8078ba391062ac83bf44ab6cbd1bc14493f1 | scripts/check_p8_repository.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Exact repository identity | none; exact Ubuntu replay remains authoritative |
| 11 | p8_provenance | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p8_provenance.py . | scripts/check_p8_provenance.py#main / 100644 / 576831f10c9f9729299dec8276cfccbb993dde4a | scripts/check_p8_provenance.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Exact provenance identity | none; exact Ubuntu replay remains authoritative |
| 12 | p8_operations | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p8_operations.py . | scripts/check_p8_operations.py#main / 100644 / 694d75f8ecb9be367493d42b581d627abbd03491 | scripts/check_p8_operations.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Static/operator contract | none; exact Ubuntu replay remains authoritative |
| 13 | p8_backup_restore | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p8_backup_restore.py . | scripts/check_p8_backup_restore.py#main / 100644 / 5badb7f63b774c822dc5d5ed406b4e1eecc386fa | scripts/check_p8_backup_restore.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Portable static/synthetic backup semantics | none; exact Ubuntu replay remains authoritative |
| 14 | p8_diagnostics | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p8_diagnostics.py . | scripts/check_p8_diagnostics.py#main / 100644 / 382397c88eb7f160af7c5d694d4a509476b2909f | scripts/check_p8_diagnostics.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Safe diagnostic contract | none; exact Ubuntu replay remains authoritative |
| 15 | p8_supply_chain | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p8_supply_chain.py . | scripts/check_p8_supply_chain.py#main / 100644 / cd2ceb94d838e3f3879a78517ad7cce84361bfed | scripts/check_p8_supply_chain.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Dependency/input identities | none; exact Ubuntu replay remains authoritative |
| 16 | p8_reproducibility | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p8_reproducibility.py . | scripts/check_p8_reproducibility.py#main / 100644 / 72eb4312018c6fdc665921837e58a24f86b3b36a | scripts/check_p8_reproducibility.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Deterministic build comparison | none; exact Ubuntu replay remains authoritative |
| 17 | p8_release | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p8_release.py . | scripts/check_p8_release.py#main / 100644 / 19763335f7920429b1ad40be5b7ad96675bef0b5 | scripts/check_p8_release.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Release artifact contract | none; exact Ubuntu replay remains authoritative |
| 18 | p2_core_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p2_core_contracts.py . | scripts/check_p2_core_contracts.py#main / 100644 / 3343498dd780c42acf2245e348368ce6c8d2b37c | scripts/check_p2_core_contracts.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 19 | p3_architecture_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p3_architecture.py . | scripts/check_p3_architecture.py#main / 100644 / 6305a93830769c0e179f1c824850a42d1240abe1 | scripts/check_p3_architecture.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 20 | p3_migrations_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p3_migrations.py . | scripts/check_p3_migrations.py#main / 100644 / 91fecea248d055a661c3da0dcafeb723062e794e | scripts/check_p3_migrations.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 21 | p3_persistence_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p3_persistence.py . | scripts/check_p3_persistence.py#main / 100644 / 40b5e115a650fb92cdeb752a6e46b6d879d19ba4 | scripts/check_p3_persistence.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 22 | p3_runtime_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p3_runtime_contracts.py . | scripts/check_p3_runtime_contracts.py#main / 100644 / 4b50ecba4a52d6cf05a38e5a2b4da608e60a89c9 | scripts/check_p3_runtime_contracts.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 23 | p3_golden_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p3_golden_path.py . | scripts/check_p3_golden_path.py#main / 100644 / 470fb9d415e2c9874c3c1b29878d12d9b095a432 | scripts/check_p3_golden_path.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 24 | p4_architecture_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p4_architecture.py . | scripts/check_p4_architecture.py#main / 100644 / a4da981f34d3d422f3d92653ec00c43cc1e29d97 | scripts/check_p4_architecture.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 25 | p4_migrations_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p4_migrations.py . | scripts/check_p4_migrations.py#main / 100644 / d05ae05cfd6fee4b1e6f29fe745e4d1b535513d5 | scripts/check_p4_migrations.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 26 | p4_authentication_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p4_authentication.py . | scripts/check_p4_authentication.py#main / 100644 / 97d1e8157fc02be14548fc1b873d4b408bcbb995 | scripts/check_p4_authentication.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 27 | p4_studio_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p4_studio.py . | scripts/check_p4_studio.py#main / 100644 / 827c11a15b43f093eb898b5c8efe779f5909c475 | scripts/check_p4_studio.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 28 | p4_compose_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p4_compose.py . | scripts/check_p4_compose.py#main / 100644 / 2e23588b0113aa1eecb47679c5f0348bed2d9234 | scripts/check_p4_compose.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 29 | p4_golden_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p4_golden_path.py . | scripts/check_p4_golden_path.py#main / 100644 / 7e215b9744cf70de9cd4e8076b5d8d6e14525514 | scripts/check_p4_golden_path.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 30 | p5_architecture_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p5_architecture.py . | scripts/check_p5_architecture.py#main / 100644 / b82a1c3f05f5a010ae89ae3c4f1637759c5413c2 | scripts/check_p5_architecture.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 31 | p5_migrations_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p5_migrations.py . | scripts/check_p5_migrations.py#main / 100644 / 1186a334bf446d7713e5ec2824a79bfc3e2f5ad4 | scripts/check_p5_migrations.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 32 | p5_builder_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p5_builder.py . | scripts/check_p5_builder.py#main / 100644 / 94e9de8a0c85f7970d2a0b9d3bccc9beb3ef16d3 | scripts/check_p5_builder.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 33 | p5_policy_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p5_policy.py . | scripts/check_p5_policy.py#main / 100644 / 955e90a89c8b1560784db14caf4c3c1f9f2326df | scripts/check_p5_policy.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 34 | p5_studio_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p5_studio.py . | scripts/check_p5_studio.py#main / 100644 / 7e119453c466de532bd3511d0dc7bbaf7ad9b920 | scripts/check_p5_studio.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 35 | p5_compose_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p5_compose.py . | scripts/check_p5_compose.py#main / 100644 / 4a2d4448bc00d1ea358c7e8a08f00d3a06752a31 | scripts/check_p5_compose.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 36 | p5_golden_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p5_golden_path.py . | scripts/check_p5_golden_path.py#main / 100644 / 2488d2bdc5c68b464d620c096cb9799854f1a254 | scripts/check_p5_golden_path.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 37 | p6_architecture_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p6_architecture.py . | scripts/check_p6_architecture.py#main / 100644 / 5e4eb3f1f29560847476b5178e8200b5c12b9fa9 | scripts/check_p6_architecture.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 38 | p6_migrations_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p6_migrations.py . | scripts/check_p6_migrations.py#main / 100644 / b40171620a15f54cb4eda4e68214cc0da0d8a453 | scripts/check_p6_migrations.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 39 | p6_authentication_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p6_authentication.py . | scripts/check_p6_authentication.py#main / 100644 / bafd28cf374d0cd642b97858d6d6a8729b2e8f23 | scripts/check_p6_authentication.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 40 | p6_rbac_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p6_rbac.py . | scripts/check_p6_rbac.py#main / 100644 / dac61082e6ad9bcd0565b0dff81cb05f6ef8dffe | scripts/check_p6_rbac.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 41 | p6_change_approval_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p6_change_approval.py . | scripts/check_p6_change_approval.py#main / 100644 / 2d700b49c3a20993b33001fe1b0c233b4d3f910a | scripts/check_p6_change_approval.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 42 | p6_effect_approval_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p6_effect_approval.py . | scripts/check_p6_effect_approval.py#main / 100644 / 98cccb76aa86bec56b6187d380deea879ccd7fbe | scripts/check_p6_effect_approval.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 43 | p6_audit_export_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p6_audit_export.py . | scripts/check_p6_audit_export.py#main / 100644 / f67bcb5632ddd58cd4574381ad450ff07c10137b | scripts/check_p6_audit_export.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 44 | p6_abuse_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p6_abuse.py . | scripts/check_p6_abuse.py#main / 100644 / abe3d255ea073bf643c5dea069e5e11c740f34fd | scripts/check_p6_abuse.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 45 | p6_studio_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p6_studio.py . | scripts/check_p6_studio.py#main / 100644 / 053f300fbfa3f32ecb84e5299a76ac5975501312 | scripts/check_p6_studio.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 46 | p6_compose_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p6_compose.py . | scripts/check_p6_compose.py#main / 100644 / e83e69e99a7e2e477abda883ced68179e07e5366 | scripts/check_p6_compose.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 47 | p6_golden_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p6_golden_path.py . | scripts/check_p6_golden_path.py#main / 100644 / af64539cc5549c2f8f2a1c58be685e38d63143bc | scripts/check_p6_golden_path.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 48 | p7_architecture_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p7_architecture.py . | scripts/check_p7_architecture.py#main / 100644 / 148f9671542a0669731fd3e703de4cdb547e0abf | scripts/check_p7_architecture.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 49 | p7_model_adapter_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p7_model_adapter.py . | scripts/check_p7_model_adapter.py#main / 100644 / bf9d9bfda708d42ef3dc2ffb786d3b6b84cfe2df | scripts/check_p7_model_adapter.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 50 | p7_channel_adapter_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p7_channel_adapter.py . | scripts/check_p7_channel_adapter.py#main / 100644 / f601ff5faa6ca2a90e99039af67cb87d6dbd1d6f | scripts/check_p7_channel_adapter.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 51 | p7_configuration_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p7_configuration.py . | scripts/check_p7_configuration.py#main / 100644 / ecf21611975848a275104bf2b20a94e87ebfbf70 | scripts/check_p7_configuration.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 52 | p7_abuse_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p7_abuse.py . | scripts/check_p7_abuse.py#main / 100644 / 38470a0a876957980bd08bdc731be7cf25339bf3 | scripts/check_p7_abuse.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 53 | p7_compose_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p7_compose.py . | scripts/check_p7_compose.py#main / 100644 / 854b7214798fccfd929f464fcb05faf63bd92187 | scripts/check_p7_compose.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 54 | p7_golden_current_tree | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p7_golden_path.py . | scripts/check_p7_golden_path.py#main / 100644 / 8a819094259acc56380a2ab01b09d9bb15dac9ca | scripts/check_p7_golden_path.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain this accepted P2-P7 current-tree leaf from the P8 aggregate. | none; exact Ubuntu replay remains authoritative |
| 55 | p8_public_boundary | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_public_boundary.py . | scripts/check_public_boundary.py#main / 100644 / 35f6cb4e729987b2c0b18cf8981f328e72445297 | scripts/check_public_boundary.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the P8 public-boundary leaf as an individual result. | none; exact Ubuntu replay remains authoritative |
| 56 | p8_git_diff_check | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | git | git diff --check | null | Direct Git builtin; no repository callable | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P8 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the P8 committed-diff whitespace leaf. | none; exact Ubuntu replay remains authoritative |
| 57 | p8_compose_runtime | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p8_compose_runtime.py . | scripts/check_p8_compose_runtime.py#main / 100644 / e8e3f496d7bde9c5eb2859d1d87e1b8532b60467 | main:1436–1469 → check_compose_runtime:816 → _first_release_transition:377 → pre_start_restore:493–511; host 0700/0600 bind enters UID 10001 container | ubuntu-24.04: not_proven; accepted evidence: Darwin | excluded_acceptance_gate | Native-Linux UID/bind mismatch and exact private-file path; embedded p8_compose_runtime Darwin anchor | p8_compose_runtime_darwin_composite_anchor |
| 58 | p8_golden_path | P8 / 0bb80ab187932fbad42fbf665b8310987609a1f5 | python_script | \<p8-python\> -B scripts/check_p8_golden_path.py . | scripts/check_p8_golden_path.py#main / 100644 / d5f38a86baa02583ee2ec1639c3163954a188399 | main:67–86 → check_golden_path:21–31 → check_compose_runtime at line 23; runtime and cleanup are mandatory | ubuntu-24.04: not_proven; accepted evidence: Darwin | excluded_acceptance_gate | Direct transitive call to excluded P8 Compose; embedded independent p8_golden_path Darwin anchor | p8_golden_path_darwin_composite_anchor |
| 59 | p9_retained_p8_portable | P9 / 11aa240af8db2ca515325dc059b1a77f7badc874 | predecessor_result | verify exact completed P8 portable result and inventory digest | null | P12-owned assertion of completed P8 portable result, corrected 56/2 partition, ordered exclusions, and digest; accepted recursive P9 runner is not invoked | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P9 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Bind P9 to the completed P8 portable layer without rerun. | none; exact Ubuntu replay remains authoritative |
| 60 | p9_repository | P9 / 11aa240af8db2ca515325dc059b1a77f7badc874 | python_script | \<p9-python\> -B scripts/check_p9_repository.py . | scripts/check_p9_repository.py#main / 100644 / ccc048673bc14b02c63cbf91e93a978adf481ad0 | scripts/check_p9_repository.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P9 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Exact P9 repository identity | none; exact Ubuntu replay remains authoritative |
| 61 | p9_provenance | P9 / 11aa240af8db2ca515325dc059b1a77f7badc874 | python_script | \<p9-python\> -B scripts/check_p9_provenance.py . | scripts/check_p9_provenance.py#main / 100644 / f1922e74cad974809ced823c4b780d7c7e5fd85e | scripts/check_p9_provenance.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P9 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Exact P9 provenance identity | none; exact Ubuntu replay remains authoritative |
| 62 | p9_rebaseline | P9 / 11aa240af8db2ca515325dc059b1a77f7badc874 | python_script | \<p9-python\> -B scripts/check_p9_rebaseline.py . | scripts/check_p9_rebaseline.py#main / 100644 / e07f55736ffd25fbe1add7458b0b6e72c409316f | scripts/check_p9_rebaseline.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P9 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Exact P9 rebaseline contract | none; exact Ubuntu replay remains authoritative |
| 63 | p9_test | P9 / 11aa240af8db2ca515325dc059b1a77f7badc874 | python_script | \<p9-python\> -B scripts/run_p8_unittest_suite.py --start-directory tests/p9 --top-level-directory . --json-output \<p9-temp\>/p9-unittest.json | scripts/run_p8_unittest_suite.py#main / 100644 / 35d0ef6a88025ef5bc10925009e044c6a84025c8 | Generic unittest discovery limited to tests/p9; no historical aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P9 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Run the exact 32-test P9 suite as one counted historical leaf. | none; exact Ubuntu replay remains authoritative |
| 64 | p9_public_boundary | P9 / 11aa240af8db2ca515325dc059b1a77f7badc874 | python_script | \<p9-python\> -B scripts/check_public_boundary.py . | scripts/check_public_boundary.py#main / 100644 / 35f6cb4e729987b2c0b18cf8981f328e72445297 | scripts/check_public_boundary.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P9 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the P9 public-boundary leaf. | none; exact Ubuntu replay remains authoritative |
| 65 | p9_git_diff_check | P9 / 11aa240af8db2ca515325dc059b1a77f7badc874 | git | git diff --check | null | Direct Git builtin; no repository callable | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P9 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the P9 committed-diff whitespace leaf. | none; exact Ubuntu replay remains authoritative |
| 66 | p10_retained_p9_portable | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | predecessor_result | verify exact completed P9 portable result and inventory digest | null | P12-owned assertion of completed P9 portable result and digest; no recursive aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Bind P10 to the completed P9 portable layer without rerun. | none; exact Ubuntu replay remains authoritative |
| 67 | p10_ruff_lint | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | python_module | \<p10-python\> -m ruff check src scripts tests | null | Locked Python module invocation; no repository script entrypoint and no reachable historical aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the exact P10 Ruff lint leaf. | none; exact Ubuntu replay remains authoritative |
| 68 | p10_ruff_format | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | python_module | \<p10-python\> -m ruff format --check src scripts tests | null | Locked Python module invocation; no repository script entrypoint and no reachable historical aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the exact P10 Ruff format leaf. | none; exact Ubuntu replay remains authoritative |
| 69 | p10_mypy_strict | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | python_module | \<p10-python\> -m mypy src scripts tests | null | Locked Python module invocation; no repository script entrypoint and no reachable historical aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the exact P10 strict Mypy leaf. | none; exact Ubuntu replay remains authoritative |
| 70 | p10_unittest | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | python_script | \<p10-python\> -B scripts/run_p8_unittest_suite.py --start-directory tests/p10 --top-level-directory . --json-output \<p10-temp\>/p10-unittest.json | scripts/run_p8_unittest_suite.py#main / 100644 / 35d0ef6a88025ef5bc10925009e044c6a84025c8 | Generic unittest discovery limited to tests/p10; Darwin branches are mocked/conditional and no runtime gate is invoked | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Run the exact P10 Python unittest leaf without batching it. | none; exact Ubuntu replay remains authoritative |
| 71 | p10_studio_eslint | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | npm_script | corepack npm run lint | studio/package.json#lint / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | studio/package.json script lint → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P10 Studio lint leaf separately. | none; exact Ubuntu replay remains authoritative |
| 72 | p10_studio_prettier | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | npm_script | corepack npm run format:check | studio/package.json#format:check / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | studio/package.json script format:check → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P10 Studio format:check leaf separately. | none; exact Ubuntu replay remains authoritative |
| 73 | p10_studio_typescript | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | npm_script | corepack npm run typecheck | studio/package.json#typecheck / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | studio/package.json script typecheck → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P10 Studio typecheck leaf separately. | none; exact Ubuntu replay remains authoritative |
| 74 | p10_studio_vitest | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | npm_script | corepack npm test -- --run | studio/package.json#test / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | studio/package.json script test → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P10 Studio test leaf separately. | none; exact Ubuntu replay remains authoritative |
| 75 | p10_studio_vite_build | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | npm_script | corepack npm run build | studio/package.json#build / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | studio/package.json script build → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P10 Studio build leaf separately. | none; exact Ubuntu replay remains authoritative |
| 76 | p10_repository | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | python_script | \<p10-python\> -B scripts/check_p10_repository.py . | scripts/check_p10_repository.py#main / 100644 / 6db14ae002894c14204734c564ee827dc0465835 | scripts/check_p10_repository.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Exact P10 repository identity | none; exact Ubuntu replay remains authoritative |
| 77 | p10_provenance | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | python_script | \<p10-python\> -B scripts/check_p10_provenance.py . | scripts/check_p10_provenance.py#main / 100644 / 51a2163866a1cd1aebf37c69f0de3abd35ad3f33 | scripts/check_p10_provenance.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Exact P10 provenance identity | none; exact Ubuntu replay remains authoritative |
| 78 | p10_distribution | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | python_script | \<p10-python\> -B scripts/check_p10_distribution.py . | scripts/check_p10_distribution.py#main / 100644 / a4687649f3ab6e64f13c41015527f17265b1130a | Default CLI reaches static distribution validation only; remote installer, pull, and Darwin quickstart helpers are unreachable | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; P10 distribution contract | none; exact Ubuntu replay remains authoritative |
| 79 | p10_security | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | python_script | \<p10-python\> -B scripts/check_p10_security.py . | scripts/check_p10_security.py#main / 100644 / aa0ce7c10f0a3bde84270521830f54c7156f2657 | Static source/mode inspection only; FileVault/macOS commands are not executed | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; P10 security boundary | none; exact Ubuntu replay remains authoritative |
| 80 | p10_operations | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | python_script | \<p10-python\> -B scripts/check_p10_operations.py . | scripts/check_p10_operations.py#main / 100644 / 64173d44dab2c4fd646ed5a4e72278dcd329bd9c | Builds bundle and invokes launcher --help; exits before macOS doctor/runtime checks | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; P10 operations contract | none; exact Ubuntu replay remains authoritative |
| 81 | p10_i18n | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | python_script | \<p10-python\> -B scripts/check_p10_i18n.py . | scripts/check_p10_i18n.py#main / 100644 / 5ae8590ee118191de99108f08809faa01b74abcc | scripts/check_p10_i18n.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; P10 language contract | none; exact Ubuntu replay remains authoritative |
| 82 | p10_compatibility | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | python_script | \<p10-python\> -B scripts/check_p10_compatibility.py . | scripts/check_p10_compatibility.py#main / 100644 / 3d1a5c85409aa5a3741c8a7ea6365c9814184209 | scripts/check_p10_compatibility.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; P10 compatibility contract | none; exact Ubuntu replay remains authoritative |
| 83 | p10_reproducibility | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | python_script | \<p10-python\> -B scripts/check_p10_reproducibility.py . | scripts/check_p10_reproducibility.py#main / 100644 / 50f766427755c650795e04b0bc92c69927840fef | scripts/check_p10_reproducibility.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; P10 reproducibility contract | none; exact Ubuntu replay remains authoritative |
| 84 | p10_public_boundary | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | python_script | \<p10-python\> -B scripts/check_public_boundary.py . | scripts/check_public_boundary.py#main / 100644 / 35f6cb4e729987b2c0b18cf8981f328e72445297 | scripts/check_public_boundary.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the P10 public-boundary leaf. | none; exact Ubuntu replay remains authoritative |
| 85 | p10_git_diff_check | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | git | git diff --check | null | Direct Git builtin; no repository callable | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the P10 committed-diff whitespace leaf. | none; exact Ubuntu replay remains authoritative |
| 86 | p10_evidence | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | python_script | \<p10-python\> -B scripts/check_p10_evidence.py . | scripts/check_p10_evidence.py#main / 100644 / 0d8079d60b8459eccc71e62af3b70fd4bc4eb591 | Validates immutable accepted summary/object identities; it does not execute a host runtime | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P10 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Verify the accepted P10 evidence identity without rewriting it. | none; exact Ubuntu replay remains authoritative |
| 87 | p10_compose_runtime | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | python_script | \<p10-python\> -B scripts/check_p10_compose_runtime.py . | scripts/check_p10_compose_runtime.py#main / 100644 / 44cf5504f0728e571cfeaa2e33d75c8b58bec738 | main:478–498 → check:468–475 → build_local_candidate:87–122 → _native_platform:67–75 | ubuntu-24.04: not_proven; accepted evidence: Darwin | excluded_acceptance_gate | Non-Darwin deterministically raises actual_macos_required; embedded P10 Compose Darwin anchor | p10_compose_runtime_darwin_composite_anchor |
| 88 | p10_quickstart | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | python_script | \<p10-python\> -B scripts/check_p10_quickstart.py . | scripts/check_p10_quickstart.py#main / 100644 / 6b352a180683969deed9b396b9b94b4488232411 | main:222–247 → check_quickstart:168–175 → build_local_candidate → _native_platform; result constructor asserts macOS | ubuntu-24.04: not_proven; accepted evidence: Darwin | excluded_acceptance_gate | Darwin-only build and hard-coded macOS result claim; embedded P10 Quickstart Darwin anchor | p10_quickstart_darwin_composite_anchor |
| 89 | p10_remote_distribution | P10 / 4bef5629d450c6bb3940f606fc90194e008ee8fd | python_script | \<p10-python\> -B scripts/check_p10_quickstart.py . --remote-distribution | scripts/check_p10_quickstart.py#main / 100644 / 6b352a180683969deed9b396b9b94b4488232411 | main --remote-distribution:231–235 → check_remote_distribution:178–219 → verify_remote_distribution → build_bundle → one run_quickstart_trials call:202–208 → internal three-trial loop:78 → dc doctor_checks | ubuntu-24.04: not_proven; accepted evidence: Darwin | excluded_acceptance_gate | Combined remote verification plus Darwin quickstart; embedded two-selected-subresults Darwin anchor | p10_remote_distribution_darwin_composite_anchor |
| 90 | p11_retained_p10_portable | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | predecessor_result | verify exact completed P10 portable result and inventory digest | null | P12-owned assertion of completed P10 portable 21/3 result and digest; accepted recursive make check is not invoked | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Bind P11 to the completed P10 portable layer without rerun. | none; exact Ubuntu replay remains authoritative |
| 91 | p11_ruff_lint | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | python_module | \<p11-python\> -m ruff check src scripts tests | null | Locked Python module invocation; no repository script entrypoint and no reachable historical aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the exact P11 Ruff lint leaf. | none; exact Ubuntu replay remains authoritative |
| 92 | p11_ruff_format | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | python_module | \<p11-python\> -m ruff format --check src scripts tests | null | Locked Python module invocation; no repository script entrypoint and no reachable historical aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the exact P11 Ruff format leaf. | none; exact Ubuntu replay remains authoritative |
| 93 | p11_mypy_strict | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | python_module | \<p11-python\> -m mypy src scripts tests | null | Locked Python module invocation; no repository script entrypoint and no reachable historical aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the exact P11 strict Mypy leaf. | none; exact Ubuntu replay remains authoritative |
| 94 | p11_unittest | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | python_script | \<p11-python\> -B scripts/run_p8_unittest_suite.py --start-directory tests/p11 --top-level-directory . --json-output \<p11-temp\>/p11-unittest.json | scripts/run_p8_unittest_suite.py#main / 100644 / 35d0ef6a88025ef5bc10925009e044c6a84025c8 | Generic unittest discovery limited to tests/p11; no P8/P10 aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Run the exact P11 Python unittest leaf without batching it. | none; exact Ubuntu replay remains authoritative |
| 95 | p11_studio_eslint | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | npm_script | corepack npm run lint | studio/package.json#lint / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | studio/package.json script lint → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P11 Studio lint leaf separately. | none; exact Ubuntu replay remains authoritative |
| 96 | p11_studio_prettier | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | npm_script | corepack npm run format:check | studio/package.json#format:check / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | studio/package.json script format:check → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P11 Studio format:check leaf separately. | none; exact Ubuntu replay remains authoritative |
| 97 | p11_studio_typescript | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | npm_script | corepack npm run typecheck | studio/package.json#typecheck / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | studio/package.json script typecheck → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P11 Studio typecheck leaf separately. | none; exact Ubuntu replay remains authoritative |
| 98 | p11_studio_vitest | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | npm_script | corepack npm test -- --run | studio/package.json#test / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | studio/package.json script test → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P11 Studio test leaf separately. | none; exact Ubuntu replay remains authoritative |
| 99 | p11_studio_vite_build | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | npm_script | corepack npm run build | studio/package.json#build / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | studio/package.json script build → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P11 Studio build leaf separately. | none; exact Ubuntu replay remains authoritative |
| 100 | p11_repository | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | python_script | \<p11-python\> -B scripts/check_p11_repository.py . | scripts/check_p11_repository.py#main / 100644 / f8537817378b7265071112250d8fadeaa134a616 | scripts/check_p11_repository.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Exact P11 repository identity | none; exact Ubuntu replay remains authoritative |
| 101 | p11_provenance | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | python_script | \<p11-python\> -B scripts/check_p11_provenance.py . | scripts/check_p11_provenance.py#main / 100644 / fb3c7aaaf935388bfcf8e46f5d8e816f927bea8b | scripts/check_p11_provenance.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Exact P11 provenance identity | none; exact Ubuntu replay remains authoritative |
| 102 | p11_architecture | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | python_script | \<p11-python\> -B scripts/check_p11_architecture.py . | scripts/check_p11_architecture.py#main / 100644 / 82a9d85f4ec7d0d2761d7b312f317df88cbbbbe1 | scripts/check_p11_architecture.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; P11 architecture boundary | none; exact Ubuntu replay remains authoritative |
| 103 | p11_migrations | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | python_script | \<p11-python\> -B scripts/check_p11_migrations.py . | scripts/check_p11_migrations.py#main / 100644 / 75076416c8e5aa82517c35166ea3d3a99e2642d7 | scripts/check_p11_migrations.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; P11 migration boundary | none; exact Ubuntu replay remains authoritative |
| 104 | p11_compatibility | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | python_script | \<p11-python\> -B scripts/check_p11_compatibility.py . | scripts/check_p11_compatibility.py#main / 100644 / 369517b0b95043cb0349af124eaed27e98746f9e | scripts/check_p11_compatibility.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; P11 compatibility boundary | none; exact Ubuntu replay remains authoritative |
| 105 | p11_studio | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | python_script | \<p11-python\> -B scripts/check_p11_studio.py . | scripts/check_p11_studio.py#main / 100644 / f152f82baaf7f830f88bc5c72d19a87dd7c4589f | scripts/check_p11_studio.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; P11 Studio contract | none; exact Ubuntu replay remains authoritative |
| 106 | p11_public_boundary | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | python_script | \<p11-python\> -B scripts/check_public_boundary.py . | scripts/check_public_boundary.py#main / 100644 / 35f6cb4e729987b2c0b18cf8981f328e72445297 | scripts/check_public_boundary.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; P11 public boundary | none; exact Ubuntu replay remains authoritative |
| 107 | p11_candidate_diff | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | python_function | scripts.p11_gate_support.candidate_diff_check(.) | scripts/p11_gate_support.py#candidate_diff_check / 100644 / 02024443d0f8399e3168eef5abd8601873c2f39a | Exact function candidate_diff_check in scripts/p11_gate_support.py; no recursive aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Invoke the exact unmodified P11 candidate diff function in a subprocess. | none; exact Ubuntu replay remains authoritative |
| 108 | p11_compose_runtime | P11 / 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38 | python_script | \<p11-python\> -B scripts/check_p11_compose_runtime.py . | scripts/check_p11_compose_runtime.py#main / 100644 / 61486f133fe2279eebfa2d19ed8144a4f8fdb85c | Exact P11 Compose path uses named state volume, generic Docker Engine/Compose, no Darwin guard, and emits observed host dynamically | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11 tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the accepted portable P11 Compose leaf and zero cleanup. | none; exact Ubuntu replay remains authoritative |
| 109 | p11r_retained_p11_portable | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | predecessor_result | verify exact completed P11 portable result and inventory digest | null | P12-owned assertion of completed P11 portable result and digest; accepted recursive make p11-check is not invoked | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Bind P11R to the completed P11 portable layer without rerun. | none; exact Ubuntu replay remains authoritative |
| 110 | p11r_ruff_lint | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | python_module | \<p11r-python\> -m ruff check src scripts tests | null | Locked Python module invocation; no repository script entrypoint and no reachable historical aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the exact P11R Ruff lint leaf. | none; exact Ubuntu replay remains authoritative |
| 111 | p11r_ruff_format | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | python_module | \<p11r-python\> -m ruff format --check src scripts tests | null | Locked Python module invocation; no repository script entrypoint and no reachable historical aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the exact P11R Ruff format leaf. | none; exact Ubuntu replay remains authoritative |
| 112 | p11r_mypy_strict | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | python_module | \<p11r-python\> -m mypy src scripts tests | null | Locked Python module invocation; no repository script entrypoint and no reachable historical aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the exact P11R strict Mypy leaf. | none; exact Ubuntu replay remains authoritative |
| 113 | p11r_current_p11_tests | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | python_script | \<p11r-python\> -B -m scripts.run_p11r_toolchain --scope current-tests --json-output \<p11r-temp\>/current-p11.json | scripts/run_p11r_toolchain.py#main:current-tests / 100644 / 599f2328a03db9216ed2fdc1b1a1af919834800a | Exact current-tests dispatch selects 100 accepted P11 tests and does not fall through to scope all | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Run the exact 100-test branch-independent P11 regression leaf. | none; exact Ubuntu replay remains authoritative |
| 114 | p11r_governance_tests | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | python_script | \<p11r-python\> -B -m scripts.run_p11r_toolchain --scope p11r-tests --json-output \<p11r-temp\>/p11r.json | scripts/run_p11r_toolchain.py#main:p11r-tests / 100644 / 599f2328a03db9216ed2fdc1b1a1af919834800a | Exact p11r-tests dispatch selects 36 governance tests and does not fall through to scope all | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Run the exact 36-test P11R governance leaf separately. | none; exact Ubuntu replay remains authoritative |
| 115 | p11r_studio_eslint | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | npm_script | corepack npm run lint | studio/package.json#lint / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | studio/package.json script lint → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P11R Studio lint leaf separately. | none; exact Ubuntu replay remains authoritative |
| 116 | p11r_studio_prettier | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | npm_script | corepack npm run format:check | studio/package.json#format:check / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | studio/package.json script format:check → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P11R Studio format:check leaf separately. | none; exact Ubuntu replay remains authoritative |
| 117 | p11r_studio_typescript | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | npm_script | corepack npm run typecheck | studio/package.json#typecheck / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | studio/package.json script typecheck → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P11R Studio typecheck leaf separately. | none; exact Ubuntu replay remains authoritative |
| 118 | p11r_studio_vitest | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | npm_script | corepack npm test -- --run | studio/package.json#test / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | studio/package.json script test → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P11R Studio test leaf separately. | none; exact Ubuntu replay remains authoritative |
| 119 | p11r_studio_vite_build | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | npm_script | corepack npm run build | studio/package.json#build / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | studio/package.json script build → locked npm toolchain; no reachable platform guard | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Execute the P11R Studio build leaf separately. | none; exact Ubuntu replay remains authoritative |
| 120 | p11r_architecture | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | python_script | \<p11r-python\> -B scripts/check_p11_architecture.py . | scripts/check_p11_architecture.py#main / 100644 / 82a9d85f4ec7d0d2761d7b312f317df88cbbbbe1 | scripts/check_p11_architecture.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; P11R P11 architecture leaf | none; exact Ubuntu replay remains authoritative |
| 121 | p11r_migrations | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | python_script | \<p11r-python\> -B scripts/check_p11_migrations.py . | scripts/check_p11_migrations.py#main / 100644 / 75076416c8e5aa82517c35166ea3d3a99e2642d7 | scripts/check_p11_migrations.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; P11R P11 migration leaf | none; exact Ubuntu replay remains authoritative |
| 122 | p11r_compatibility | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | python_script | \<p11r-python\> -B scripts/check_p11_compatibility.py . | scripts/check_p11_compatibility.py#main / 100644 / 369517b0b95043cb0349af124eaed27e98746f9e | scripts/check_p11_compatibility.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; P11R P11 compatibility leaf | none; exact Ubuntu replay remains authoritative |
| 123 | p11r_studio_contract | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | python_script | \<p11r-python\> -B scripts/check_p11_studio.py . | scripts/check_p11_studio.py#main / 100644 / f152f82baaf7f830f88bc5c72d19a87dd7c4589f | scripts/check_p11_studio.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; P11R P11 Studio leaf | none; exact Ubuntu replay remains authoritative |
| 124 | p11r_ci_policy | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | python_script | \<p11r-python\> -B scripts/check_p11r_ci_policy.py . | scripts/check_p11r_ci_policy.py#main / 100644 / ce0bbf7f3e18062d6d77f1d16e303376c58df2f4 | scripts/check_p11r_ci_policy.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Exact P11R CI policy | none; exact Ubuntu replay remains authoritative |
| 125 | p11r_repository_ci | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | python_script | \<p11r-python\> -B scripts/check_p11r_repository.py . --mode ci | scripts/check_p11r_repository.py#main / 100644 / e684975be4b651c3f731bd30b1cf09f89046978e | scripts/check_p11r_repository.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Branch-independent P11R repository CI mode | none; exact Ubuntu replay remains authoritative |
| 126 | p11r_provenance | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | python_script | \<p11r-python\> -B scripts/check_p11r_provenance.py . | scripts/check_p11r_provenance.py#main / 100644 / 51673c267cef7c16836f588d72cad60bed32c995 | scripts/check_p11r_provenance.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Exact P11R provenance | none; exact Ubuntu replay remains authoritative |
| 127 | p11r_public_boundary | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | python_script | \<p11r-python\> -B scripts/check_public_boundary.py . | scripts/check_public_boundary.py#main / 100644 / 35f6cb4e729987b2c0b18cf8981f328e72445297 | scripts/check_public_boundary.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; P11R public boundary | none; exact Ubuntu replay remains authoritative |
| 128 | p11r_candidate_repository | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | python_script | \<p11r-python\> -B scripts/check_p11r_repository.py . --mode candidate | scripts/check_p11r_repository.py#main / 100644 / e684975be4b651c3f731bd30b1cf09f89046978e | scripts/check_p11r_repository.py#main; exact reachable call graph reviewed, with no Darwin-only guard or excluded aggregate | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; P11R candidate repository mode | none; exact Ubuntu replay remains authoritative |
| 129 | p11r_compose_runtime | P11R / c1562ea5201394d8a278f4b644daf4029cbb5bd4 | python_script | \<p11r-python\> -B scripts/check_p11_compose_runtime.py . | scripts/check_p11_compose_runtime.py#main / 100644 / 61486f133fe2279eebfa2d19ed8144a4f8fdb85c | Same exact P11 Compose blob; named volume, no Darwin guard, observed host emitted dynamically | ubuntu-24.04 portable candidate; exact replay required | included_acceptance_gate | Exact manifest command and P11R tree identity verified; path/mode/blob and reachable platform/call graph reviewed; Retain the bounded accepted P11R Compose leaf and zero cleanup. | none; exact Ubuntu replay remains authoritative |

## Appendix B — Normative canonical v4 inventory and set oracle

### Counts

| Item type | Exact count |
| --- | ---: |
| `setup` | 5 |
| `included_acceptance_gate` | 124 |
| `evidence_anchor` | 17 |
| `excluded_acceptance_gate` | 5 |
| Total | 151 |

The canonical count object fixes `setup_count = 5`, `included_acceptance_gate_count = 124`, `evidence_anchor_count = 17`, `excluded_acceptance_gate_count = 5`, and `total_item_count = 151`. The five embedded Darwin composite anchors live inside the five excluded items. They are not additional `evidence_anchor` rows. The total must never become 156, the evidence-anchor count must never become 22, and no excluded gate may be retyped as an evidence anchor.

Across the accepted-gate universe, exactly 19 entrypoints are null and 110 are non-null.
Across all 151 typed inventory rows, exactly 41 entrypoints are null: those 19 gate rows,
five setup rows, and 17 evidence-anchor rows. The remaining 110 are the same non-null
accepted-gate entrypoints verified in Appendix A. No implementation may fabricate a blob
for a Git operation, Python module invocation, predecessor-result operation, setup, or
evidence anchor merely to avoid null.

The ordered exclusion field is exactly:

~~~json
{
  "excluded_gate_ids": [
    "p8_compose_runtime",
    "p8_golden_path",
    "p10_compose_runtime",
    "p10_quickstart",
    "p10_remote_distribution"
  ]
}
~~~

The singular field `excluded_gate_id` is forbidden.

### Formal completeness oracle

~~~text
accepted_gate_set
  = portable_included_acceptance_gate_set
    disjoint-union excluded_acceptance_gate_set

|accepted_gate_set| = 129
|portable_included_acceptance_gate_set| = 124
|excluded_acceptance_gate_set| = 5

accepted_gate_set - portable_included_acceptance_gate_set
  = [
      p8_compose_runtime,
      p8_golden_path,
      p10_compose_runtime,
      p10_quickstart,
      p10_remote_distribution
    ]
~~~

The accepted set must be derived independently from exact historical contracts/runners, not from the same item classification used to derive the included set. Literal command scanning is insufficient: the oracle must account for transitive calls such as P8 Golden Path and recursive predecessor aggregates.

### Executor resource model

- Each exact milestone object receives one OS-temporary checkout, at most one hash-locked Python environment, and at most one required npm workspace.
- All leaf gates for one object share only that object's locked environment.
- Different objects never share module caches, `sys.path`, workspaces, checkouts, or mutable state.
- Historical modules load only in independent subprocesses whose working directory and import path point to the exact checkout. Module file and blob identities are checked before use.
- Every leaf retains its own gate ID, command/function identity, exit status, and result. Batching cannot combine or hide leaf results.
- A completed object's checkout, environment, npm workspace, Docker/container/network/volume state, and temporary files are removed before the next object starts.
- Recursive aggregates that would reintroduce excluded gates are forbidden.
- Setup sublimits are checkout 120 seconds, hash-locked Python installation 600, and required npm installation 600. Per-object stage deadlines, each covering that object's setup, all leaf gates, and cleanup, are P8 2700 seconds, P9 900, P10 3000, P11 1800, and P11R 1500: an exact sequential executor hard deadline of 9900 seconds (165 minutes). The portable-history job fixes `timeout-minutes: 180`, leaving 900 seconds for canonical result serialization and final fail-closed cleanup. These bounds reflect the 308-test plus Studio-heavy P8 stage, the small 32-test/no-npm P9 stage, the remote/tool-heavy P10 stage, and the 101-test P11 and 100+36-test P11R stages; no wait is unbounded.

Each completed object produces one P12-CJ-1 canonical object result with exact keys
`schema`, `object`, `commit`, `tree`, `inventory_digest`, `ordered_item_results`,
`cleanup_residue_count`, and `status`. The schema is
`digital-colleagues.p12-v4-portable-object-result.v1`; `ordered_item_results` contains all
and only that object's typed inventory items in manifest order, including excluded and
anchor records, without batching. `object_result_digest` is `sha256:` plus the lowercase
SHA-256 of the exact canonical bytes. Each `predecessor_result` operation verifies the
immediately preceding object's exact object-result bytes and digest, `status = passed`,
zero cleanup residue, the same complete inventory digest, and its exact included/excluded
partition. It never re-executes a predecessor aggregate. A digest over prose, a subset,
the current tree, or a caller-supplied result fails closed.

### Complete 151-row typed inventory

| # | Item ID | Object | Item type | Command kind | Platform scope | Exact command or operation | Entrypoint | Timeout | Expected result / identity | Embedded anchor |
| ---: | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| 1 | p8_setup | P8 | setup | object_setup | portable_linux / p8 | create one exact-object checkout and isolated locked resources | null | 2700 | {"cleanup_residue_count":0,"npm_workspace":"one_locked","python_environment":"one_hash_locked","status":"passed"} | none |
| 2 | p8_accepted_p7_summary_anchor | P8 | evidence_anchor | identity_check | object_identity_all_platforms / p8 | verify df47f8d075f7c0660ab5ed6035f8acfa3d3da4dc:artifacts/p7/summary.json | null | 300 | {"anchor_commit":"df47f8d075f7c0660ab5ed6035f8acfa3d3da4dc","anchor_tree":"4ebfc2bdfcd97e34256ec7a34ff58b0063c05ed7","blob":"6ded4e77c45ec7e2886aa67dd59a32ab41e47c0e","json_expectations":{"claim":"optional_adapter_contracts_passed","status":"development_complete_awaiting_independent_acceptance"},"path":"artifacts/p7/summary.json","sha256":"799caaa90bb66465df55c243cdfdd5fb9ee68730dc9ab2ddd58cdbf79cbc01f5","status":"identity_verified"} | none |
| 3 | p8_acceptance_anchor | P8 | evidence_anchor | identity_check | object_identity_all_platforms / p8 | verify eeb13ca643d5b512faab93e2e762ef4558dab688:docs/p8/acceptance.md | null | 300 | {"anchor_commit":"eeb13ca643d5b512faab93e2e762ef4558dab688","anchor_tree":"5c807edd18fd7986a3c4fc2e8c5a9d28ba4ef6f1","blob":"6f36506b601c2ebf3bd4df5397f5acbde423bcca","path":"docs/p8/acceptance.md","sha256":"dd49f823569d51dede299ece002a053b2e3c8790e642f8014d59478bc6367732","status":"identity_verified"} | none |
| 4 | p8_summary_anchor | P8 | evidence_anchor | identity_check | darwin_historical_evidence_identity / p8 | verify 0bb80ab187932fbad42fbf665b8310987609a1f5:artifacts/p8/summary.json | null | 300 | {"anchor_commit":"0bb80ab187932fbad42fbf665b8310987609a1f5","anchor_tree":"311eb777c3d17a9a3722a16c394b9913c283b416","blob":"964406b20e9fc1e98b8eeda3c24bf3f22f226768","json_pointer_expectations":{"/claim":"v0_1_local_reference_release_candidate","/compose_runtime/environment/host":"darwin","/compose_runtime/status":"passed","/status":"development_complete_awaiting_independent_acceptance"},"path":"artifacts/p8/summary.json","sha256":"78905893f9a06bf6b5361c76a8e152dbe8de2ec53d1aede84fca2f7ce1b5921b","status":"identity_verified"} | none |
| 5 | p8_receipt_anchor | P8 | evidence_anchor | identity_check | object_identity_all_platforms / p8 | verify 0bb80ab187932fbad42fbf665b8310987609a1f5:provenance/p8-migration-receipt.json | null | 300 | {"anchor_commit":"0bb80ab187932fbad42fbf665b8310987609a1f5","anchor_tree":"311eb777c3d17a9a3722a16c394b9913c283b416","blob":"1b475cb999a8dffeaeb2e474059e5ff2476e6be1","path":"provenance/p8-migration-receipt.json","sha256":"c1c9a08a4c18783720a6a3fa0c8e0b5a3aa6d9cf91f5e0d465c31067141d21eb","status":"identity_verified"} | none |
| 6 | p8_python_lock_anchor | P8 | evidence_anchor | identity_check | object_identity_all_platforms / p8 | verify 0bb80ab187932fbad42fbf665b8310987609a1f5:requirements/p8.lock | null | 300 | {"anchor_commit":"0bb80ab187932fbad42fbf665b8310987609a1f5","anchor_tree":"311eb777c3d17a9a3722a16c394b9913c283b416","blob":"819980980ba87d1b7166af4b4b0da53ca4e4ac63","path":"requirements/p8.lock","sha256":"5afb5bc2f6bf2cfdc77d0457b92255f822d89cd3cd754ebb876741d7ee6430d0","status":"identity_verified"} | none |
| 7 | p8_npm_lock_anchor | P8 | evidence_anchor | identity_check | object_identity_all_platforms / p8 | verify 0bb80ab187932fbad42fbf665b8310987609a1f5:studio/package-lock.json | null | 300 | {"anchor_commit":"0bb80ab187932fbad42fbf665b8310987609a1f5","anchor_tree":"311eb777c3d17a9a3722a16c394b9913c283b416","blob":"ec0730513988e98adaf2d935885859ba1b58f7b9","path":"studio/package-lock.json","sha256":"1c0f4648743f99241f380cf96b4f971ec71bdc1ef7bcadbd558f55e68d6747fd","status":"identity_verified"} | none |
| 8 | p8_ruff_lint | P8 | included_acceptance_gate | python_module | portable_linux / p8 | \<p8-python\> -m ruff check src scripts tests | null | 900 | {"status":"passed"} | none |
| 9 | p8_ruff_format | P8 | included_acceptance_gate | python_module | portable_linux / p8 | \<p8-python\> -m ruff format --check src scripts tests | null | 900 | {"status":"passed"} | none |
| 10 | p8_mypy_strict | P8 | included_acceptance_gate | python_module | portable_linux / p8 | \<p8-python\> -m mypy src scripts tests | null | 900 | {"status":"passed"} | none |
| 11 | p8_python_unittest | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/run_p8_unittest_suite.py --start-directory tests --top-level-directory . --json-output \<p8-temp\>/p8-unittest.json | scripts/run_p8_unittest_suite.py#main / 100644 / 35d0ef6a88025ef5bc10925009e044c6a84025c8 | 900 | {"error_count":0,"failure_count":0,"skip_count":0,"status":"passed","test_count":308,"test_count_semantics":"historical_python_unittest_cases"} | none |
| 12 | p8_studio_eslint | P8 | included_acceptance_gate | npm_script | portable_linux / p8 | corepack npm run lint | studio/package.json#lint / 100644 / f7aac57ff88ce1b7f779c3b3f63fdf7b79b6c916 | 600 | {"status":"passed"} | none |
| 13 | p8_studio_prettier | P8 | included_acceptance_gate | npm_script | portable_linux / p8 | corepack npm run format:check | studio/package.json#format:check / 100644 / f7aac57ff88ce1b7f779c3b3f63fdf7b79b6c916 | 600 | {"status":"passed"} | none |
| 14 | p8_studio_typescript | P8 | included_acceptance_gate | npm_script | portable_linux / p8 | corepack npm run typecheck | studio/package.json#typecheck / 100644 / f7aac57ff88ce1b7f779c3b3f63fdf7b79b6c916 | 600 | {"status":"passed"} | none |
| 15 | p8_studio_vitest | P8 | included_acceptance_gate | npm_script | portable_linux / p8 | corepack npm test -- --reporter=json --outputFile=\<p8-temp\>/studio-vitest.json | studio/package.json#test / 100644 / f7aac57ff88ce1b7f779c3b3f63fdf7b79b6c916 | 600 | {"exception_count":0,"status":"passed"} | none |
| 16 | p8_studio_vite_build | P8 | included_acceptance_gate | npm_script | portable_linux / p8 | corepack npm run build | studio/package.json#build / 100644 / f7aac57ff88ce1b7f779c3b3f63fdf7b79b6c916 | 600 | {"status":"passed"} | none |
| 17 | p8_repository | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p8_repository.py . | scripts/check_p8_repository.py#main / 100644 / 097b8078ba391062ac83bf44ab6cbd1bc14493f1 | 300 | {"status":"passed"} | none |
| 18 | p8_provenance | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p8_provenance.py . | scripts/check_p8_provenance.py#main / 100644 / 576831f10c9f9729299dec8276cfccbb993dde4a | 300 | {"status":"passed"} | none |
| 19 | p8_operations | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p8_operations.py . | scripts/check_p8_operations.py#main / 100644 / 694d75f8ecb9be367493d42b581d627abbd03491 | 300 | {"status":"passed"} | none |
| 20 | p8_backup_restore | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p8_backup_restore.py . | scripts/check_p8_backup_restore.py#main / 100644 / 5badb7f63b774c822dc5d5ed406b4e1eecc386fa | 300 | {"status":"passed"} | none |
| 21 | p8_diagnostics | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p8_diagnostics.py . | scripts/check_p8_diagnostics.py#main / 100644 / 382397c88eb7f160af7c5d694d4a509476b2909f | 300 | {"status":"passed"} | none |
| 22 | p8_supply_chain | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p8_supply_chain.py . | scripts/check_p8_supply_chain.py#main / 100644 / cd2ceb94d838e3f3879a78517ad7cce84361bfed | 300 | {"status":"passed"} | none |
| 23 | p8_reproducibility | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p8_reproducibility.py . | scripts/check_p8_reproducibility.py#main / 100644 / 72eb4312018c6fdc665921837e58a24f86b3b36a | 1200 | {"status":"passed"} | none |
| 24 | p8_release | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p8_release.py . | scripts/check_p8_release.py#main / 100644 / 19763335f7920429b1ad40be5b7ad96675bef0b5 | 1200 | {"status":"passed"} | none |
| 25 | p2_core_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p2_core_contracts.py . | scripts/check_p2_core_contracts.py#main / 100644 / 3343498dd780c42acf2245e348368ce6c8d2b37c | 300 | {"status":"passed"} | none |
| 26 | p3_architecture_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p3_architecture.py . | scripts/check_p3_architecture.py#main / 100644 / 6305a93830769c0e179f1c824850a42d1240abe1 | 300 | {"status":"passed"} | none |
| 27 | p3_migrations_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p3_migrations.py . | scripts/check_p3_migrations.py#main / 100644 / 91fecea248d055a661c3da0dcafeb723062e794e | 300 | {"status":"passed"} | none |
| 28 | p3_persistence_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p3_persistence.py . | scripts/check_p3_persistence.py#main / 100644 / 40b5e115a650fb92cdeb752a6e46b6d879d19ba4 | 300 | {"status":"passed"} | none |
| 29 | p3_runtime_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p3_runtime_contracts.py . | scripts/check_p3_runtime_contracts.py#main / 100644 / 4b50ecba4a52d6cf05a38e5a2b4da608e60a89c9 | 300 | {"status":"passed"} | none |
| 30 | p3_golden_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p3_golden_path.py . | scripts/check_p3_golden_path.py#main / 100644 / 470fb9d415e2c9874c3c1b29878d12d9b095a432 | 300 | {"status":"passed"} | none |
| 31 | p4_architecture_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p4_architecture.py . | scripts/check_p4_architecture.py#main / 100644 / a4da981f34d3d422f3d92653ec00c43cc1e29d97 | 300 | {"status":"passed"} | none |
| 32 | p4_migrations_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p4_migrations.py . | scripts/check_p4_migrations.py#main / 100644 / d05ae05cfd6fee4b1e6f29fe745e4d1b535513d5 | 300 | {"status":"passed"} | none |
| 33 | p4_authentication_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p4_authentication.py . | scripts/check_p4_authentication.py#main / 100644 / 97d1e8157fc02be14548fc1b873d4b408bcbb995 | 300 | {"status":"passed"} | none |
| 34 | p4_studio_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p4_studio.py . | scripts/check_p4_studio.py#main / 100644 / 827c11a15b43f093eb898b5c8efe779f5909c475 | 300 | {"status":"passed"} | none |
| 35 | p4_compose_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p4_compose.py . | scripts/check_p4_compose.py#main / 100644 / 2e23588b0113aa1eecb47679c5f0348bed2d9234 | 300 | {"status":"passed"} | none |
| 36 | p4_golden_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p4_golden_path.py . | scripts/check_p4_golden_path.py#main / 100644 / 7e215b9744cf70de9cd4e8076b5d8d6e14525514 | 300 | {"status":"passed"} | none |
| 37 | p5_architecture_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p5_architecture.py . | scripts/check_p5_architecture.py#main / 100644 / b82a1c3f05f5a010ae89ae3c4f1637759c5413c2 | 300 | {"status":"passed"} | none |
| 38 | p5_migrations_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p5_migrations.py . | scripts/check_p5_migrations.py#main / 100644 / 1186a334bf446d7713e5ec2824a79bfc3e2f5ad4 | 300 | {"status":"passed"} | none |
| 39 | p5_builder_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p5_builder.py . | scripts/check_p5_builder.py#main / 100644 / 94e9de8a0c85f7970d2a0b9d3bccc9beb3ef16d3 | 300 | {"status":"passed"} | none |
| 40 | p5_policy_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p5_policy.py . | scripts/check_p5_policy.py#main / 100644 / 955e90a89c8b1560784db14caf4c3c1f9f2326df | 300 | {"status":"passed"} | none |
| 41 | p5_studio_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p5_studio.py . | scripts/check_p5_studio.py#main / 100644 / 7e119453c466de532bd3511d0dc7bbaf7ad9b920 | 300 | {"status":"passed"} | none |
| 42 | p5_compose_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p5_compose.py . | scripts/check_p5_compose.py#main / 100644 / 4a2d4448bc00d1ea358c7e8a08f00d3a06752a31 | 300 | {"status":"passed"} | none |
| 43 | p5_golden_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p5_golden_path.py . | scripts/check_p5_golden_path.py#main / 100644 / 2488d2bdc5c68b464d620c096cb9799854f1a254 | 300 | {"status":"passed"} | none |
| 44 | p6_architecture_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p6_architecture.py . | scripts/check_p6_architecture.py#main / 100644 / 5e4eb3f1f29560847476b5178e8200b5c12b9fa9 | 300 | {"status":"passed"} | none |
| 45 | p6_migrations_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p6_migrations.py . | scripts/check_p6_migrations.py#main / 100644 / b40171620a15f54cb4eda4e68214cc0da0d8a453 | 300 | {"status":"passed"} | none |
| 46 | p6_authentication_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p6_authentication.py . | scripts/check_p6_authentication.py#main / 100644 / bafd28cf374d0cd642b97858d6d6a8729b2e8f23 | 300 | {"status":"passed"} | none |
| 47 | p6_rbac_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p6_rbac.py . | scripts/check_p6_rbac.py#main / 100644 / dac61082e6ad9bcd0565b0dff81cb05f6ef8dffe | 300 | {"status":"passed"} | none |
| 48 | p6_change_approval_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p6_change_approval.py . | scripts/check_p6_change_approval.py#main / 100644 / 2d700b49c3a20993b33001fe1b0c233b4d3f910a | 300 | {"status":"passed"} | none |
| 49 | p6_effect_approval_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p6_effect_approval.py . | scripts/check_p6_effect_approval.py#main / 100644 / 98cccb76aa86bec56b6187d380deea879ccd7fbe | 300 | {"status":"passed"} | none |
| 50 | p6_audit_export_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p6_audit_export.py . | scripts/check_p6_audit_export.py#main / 100644 / f67bcb5632ddd58cd4574381ad450ff07c10137b | 300 | {"status":"passed"} | none |
| 51 | p6_abuse_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p6_abuse.py . | scripts/check_p6_abuse.py#main / 100644 / abe3d255ea073bf643c5dea069e5e11c740f34fd | 300 | {"status":"passed"} | none |
| 52 | p6_studio_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p6_studio.py . | scripts/check_p6_studio.py#main / 100644 / 053f300fbfa3f32ecb84e5299a76ac5975501312 | 300 | {"status":"passed"} | none |
| 53 | p6_compose_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p6_compose.py . | scripts/check_p6_compose.py#main / 100644 / e83e69e99a7e2e477abda883ced68179e07e5366 | 300 | {"status":"passed"} | none |
| 54 | p6_golden_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p6_golden_path.py . | scripts/check_p6_golden_path.py#main / 100644 / af64539cc5549c2f8f2a1c58be685e38d63143bc | 300 | {"status":"passed"} | none |
| 55 | p7_architecture_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p7_architecture.py . | scripts/check_p7_architecture.py#main / 100644 / 148f9671542a0669731fd3e703de4cdb547e0abf | 300 | {"status":"passed"} | none |
| 56 | p7_model_adapter_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p7_model_adapter.py . | scripts/check_p7_model_adapter.py#main / 100644 / bf9d9bfda708d42ef3dc2ffb786d3b6b84cfe2df | 300 | {"status":"passed"} | none |
| 57 | p7_channel_adapter_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p7_channel_adapter.py . | scripts/check_p7_channel_adapter.py#main / 100644 / f601ff5faa6ca2a90e99039af67cb87d6dbd1d6f | 300 | {"status":"passed"} | none |
| 58 | p7_configuration_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p7_configuration.py . | scripts/check_p7_configuration.py#main / 100644 / ecf21611975848a275104bf2b20a94e87ebfbf70 | 300 | {"status":"passed"} | none |
| 59 | p7_abuse_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p7_abuse.py . | scripts/check_p7_abuse.py#main / 100644 / 38470a0a876957980bd08bdc731be7cf25339bf3 | 300 | {"status":"passed"} | none |
| 60 | p7_compose_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p7_compose.py . | scripts/check_p7_compose.py#main / 100644 / 854b7214798fccfd929f464fcb05faf63bd92187 | 300 | {"status":"passed"} | none |
| 61 | p7_golden_current_tree | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_p7_golden_path.py . | scripts/check_p7_golden_path.py#main / 100644 / 8a819094259acc56380a2ab01b09d9bb15dac9ca | 300 | {"status":"passed"} | none |
| 62 | p8_public_boundary | P8 | included_acceptance_gate | python_script | portable_linux / p8 | \<p8-python\> -B scripts/check_public_boundary.py . | scripts/check_public_boundary.py#main / 100644 / 35f6cb4e729987b2c0b18cf8981f328e72445297 | 300 | {"status":"passed"} | none |
| 63 | p8_git_diff_check | P8 | included_acceptance_gate | git | portable_linux / p8 | git diff --check | null | 300 | {"status":"passed"} | none |
| 64 | p8_compose_runtime | P8 | excluded_acceptance_gate | python_script | replay=ubuntu-24.04; Ubuntu status=not_proven; Darwin anchor=passed / p8 | \<p8-python\> -B scripts/check_p8_compose_runtime.py . | scripts/check_p8_compose_runtime.py#main / 100644 / e8e3f496d7bde9c5eb2859d1d87e1b8532b60467 | 1200 | {"disposition":"excluded_acceptance_gate","executor_result":"not_run_platform_excluded","exit_status":null,"linux_public_pilot_readiness":"blocked","replay_platform":"ubuntu-24.04","ubuntu_historical_execution_status":"not_proven"} | anchor_platform=darwin; anchor_historical_status=passed; purpose=immutable_platform_scoped_identity_only; commit 0bb80ab187932fbad42fbf665b8310987609a1f5; tree 311eb777c3d17a9a3722a16c394b9913c283b416; artifacts/p8/summary.json; blob 964406b20e9fc1e98b8eeda3c24bf3f22f226768; file sha256 78905893f9a06bf6b5361c76a8e152dbe8de2ec53d1aede84fca2f7ce1b5921b; result=p8_summary["compose_runtime"]; canonical bytes=2348; sha256=a2acd8e3f935d9c520f58e76b8384514e596e59f94f7bb62e1881ce9183c9bbd; gate=p8_compose_runtime_clean; selected status=passed; environment.host=darwin |
| 65 | p8_golden_path | P8 | excluded_acceptance_gate | python_script | replay=ubuntu-24.04; Ubuntu status=not_proven; Darwin anchor=passed / p8 | \<p8-python\> -B scripts/check_p8_golden_path.py . | scripts/check_p8_golden_path.py#main / 100644 / d5f38a86baa02583ee2ec1639c3163954a188399 | 1200 | {"disposition":"excluded_acceptance_gate","executor_result":"not_run_platform_excluded","exit_status":null,"linux_public_pilot_readiness":"blocked","replay_platform":"ubuntu-24.04","ubuntu_historical_execution_status":"not_proven"} | anchor_platform=darwin; anchor_historical_status=passed; purpose=immutable_platform_scoped_identity_only; commit 0bb80ab187932fbad42fbf665b8310987609a1f5; tree 311eb777c3d17a9a3722a16c394b9913c283b416; artifacts/p8/summary.json; blob 964406b20e9fc1e98b8eeda3c24bf3f22f226768; file sha256 78905893f9a06bf6b5361c76a8e152dbe8de2ec53d1aede84fca2f7ce1b5921b; result=p8_summary["golden_path"]; canonical bytes=2034; sha256=c1f1f8148cd3b0184d92720e862bbadfe7e330fd4087b7eb03190400d6742f44; gate=p8_golden_path_clean; selected status=passed; Darwin via exact direct Compose call plus /compose_runtime/environment/host=darwin |
| 66 | p9_setup | P9 | setup | object_setup | portable_linux / p9 | create one exact-object checkout and isolated locked resources | null | 900 | {"cleanup_residue_count":0,"npm_workspace":"absent","python_environment":"one_hash_locked","status":"passed"} | none |
| 67 | p9_summary_anchor | P9 | evidence_anchor | identity_check | object_identity_all_platforms / p9 | verify 11aa240af8db2ca515325dc059b1a77f7badc874:artifacts/p9/summary.json | null | 300 | {"anchor_commit":"11aa240af8db2ca515325dc059b1a77f7badc874","anchor_tree":"a27cb6ce9f568b04083a88f7ba06f033235f4cbc","blob":"117b033f8f516dff269577ff28a8e51174e7f6a3","json_expectations":{"claim":"p9_productization_rebaseline_candidate","status":"development_complete_awaiting_independent_acceptance"},"path":"artifacts/p9/summary.json","sha256":"a8085fa1889db4baa50b5aad4a2b574f614bf6f15a3efbf947f9a528a709df1c","status":"identity_verified"} | none |
| 68 | p9_python_lock_anchor | P9 | evidence_anchor | identity_check | object_identity_all_platforms / p9 | verify 11aa240af8db2ca515325dc059b1a77f7badc874:requirements/p8.lock | null | 300 | {"anchor_commit":"11aa240af8db2ca515325dc059b1a77f7badc874","anchor_tree":"a27cb6ce9f568b04083a88f7ba06f033235f4cbc","blob":"819980980ba87d1b7166af4b4b0da53ca4e4ac63","path":"requirements/p8.lock","sha256":"5afb5bc2f6bf2cfdc77d0457b92255f822d89cd3cd754ebb876741d7ee6430d0","status":"identity_verified"} | none |
| 69 | p9_retained_p8_portable | P9 | included_acceptance_gate | predecessor_result | portable_linux / p9 | verify exact completed P8 portable result and inventory digest | null | 300 | {"predecessor_object":"P8","rerun_count":0,"status":"passed"} | none |
| 70 | p9_repository | P9 | included_acceptance_gate | python_script | portable_linux / p9 | \<p9-python\> -B scripts/check_p9_repository.py . | scripts/check_p9_repository.py#main / 100644 / ccc048673bc14b02c63cbf91e93a978adf481ad0 | 300 | {"status":"passed"} | none |
| 71 | p9_provenance | P9 | included_acceptance_gate | python_script | portable_linux / p9 | \<p9-python\> -B scripts/check_p9_provenance.py . | scripts/check_p9_provenance.py#main / 100644 / f1922e74cad974809ced823c4b780d7c7e5fd85e | 300 | {"status":"passed"} | none |
| 72 | p9_rebaseline | P9 | included_acceptance_gate | python_script | portable_linux / p9 | \<p9-python\> -B scripts/check_p9_rebaseline.py . | scripts/check_p9_rebaseline.py#main / 100644 / e07f55736ffd25fbe1add7458b0b6e72c409316f | 300 | {"status":"passed"} | none |
| 73 | p9_test | P9 | included_acceptance_gate | python_script | portable_linux / p9 | \<p9-python\> -B scripts/run_p8_unittest_suite.py --start-directory tests/p9 --top-level-directory . --json-output \<p9-temp\>/p9-unittest.json | scripts/run_p8_unittest_suite.py#main / 100644 / 35d0ef6a88025ef5bc10925009e044c6a84025c8 | 900 | {"error_count":0,"failure_count":0,"skip_count":0,"status":"passed","test_count":32,"test_count_semantics":"historical_python_unittest_cases"} | none |
| 74 | p9_public_boundary | P9 | included_acceptance_gate | python_script | portable_linux / p9 | \<p9-python\> -B scripts/check_public_boundary.py . | scripts/check_public_boundary.py#main / 100644 / 35f6cb4e729987b2c0b18cf8981f328e72445297 | 300 | {"status":"passed"} | none |
| 75 | p9_git_diff_check | P9 | included_acceptance_gate | git | portable_linux / p9 | git diff --check | null | 300 | {"status":"passed"} | none |
| 76 | p10_setup | P10 | setup | object_setup | portable_linux / p10 | create one exact-object checkout and isolated locked resources | null | 3000 | {"cleanup_residue_count":0,"npm_workspace":"one_locked","python_environment":"one_hash_locked","status":"passed"} | none |
| 77 | p10_summary_anchor | P10 | evidence_anchor | identity_check | object_identity_all_platforms / p10 | verify 4bef5629d450c6bb3940f606fc90194e008ee8fd:artifacts/p10/summary.json | null | 300 | {"anchor_commit":"4bef5629d450c6bb3940f606fc90194e008ee8fd","anchor_tree":"909b566b7ba9f7beb143cd0b29cf95fbd1178bbe","blob":"a4c1a59fffec9c30160787a7bec584e228fb9f35","json_expectations":{"claim":"p10_mac_quickstart_distribution_candidate","status":"remote_distribution_candidate_ready_for_independent_acceptance"},"path":"artifacts/p10/summary.json","sha256":"876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae","status":"identity_verified"} | none |
| 78 | p10_python_lock_anchor | P10 | evidence_anchor | identity_check | object_identity_all_platforms / p10 | verify 4bef5629d450c6bb3940f606fc90194e008ee8fd:requirements/p8.lock | null | 300 | {"anchor_commit":"4bef5629d450c6bb3940f606fc90194e008ee8fd","anchor_tree":"909b566b7ba9f7beb143cd0b29cf95fbd1178bbe","blob":"819980980ba87d1b7166af4b4b0da53ca4e4ac63","path":"requirements/p8.lock","sha256":"5afb5bc2f6bf2cfdc77d0457b92255f822d89cd3cd754ebb876741d7ee6430d0","status":"identity_verified"} | none |
| 79 | p10_npm_lock_anchor | P10 | evidence_anchor | identity_check | object_identity_all_platforms / p10 | verify 4bef5629d450c6bb3940f606fc90194e008ee8fd:studio/package-lock.json | null | 300 | {"anchor_commit":"4bef5629d450c6bb3940f606fc90194e008ee8fd","anchor_tree":"909b566b7ba9f7beb143cd0b29cf95fbd1178bbe","blob":"e1ca59eac16dec46a290aaf2c010b5fc9de9cd91","path":"studio/package-lock.json","sha256":"44dba55271fa10c3b7bea09aa333c98dbf868f6cc55a8e59776ca1464c067875","status":"identity_verified"} | none |
| 80 | p10_retained_p9_portable | P10 | included_acceptance_gate | predecessor_result | portable_linux / p10 | verify exact completed P9 portable result and inventory digest | null | 300 | {"predecessor_object":"P9","rerun_count":0,"status":"passed"} | none |
| 81 | p10_ruff_lint | P10 | included_acceptance_gate | python_module | portable_linux / p10 | \<p10-python\> -m ruff check src scripts tests | null | 900 | {"status":"passed"} | none |
| 82 | p10_ruff_format | P10 | included_acceptance_gate | python_module | portable_linux / p10 | \<p10-python\> -m ruff format --check src scripts tests | null | 900 | {"status":"passed"} | none |
| 83 | p10_mypy_strict | P10 | included_acceptance_gate | python_module | portable_linux / p10 | \<p10-python\> -m mypy src scripts tests | null | 900 | {"status":"passed"} | none |
| 84 | p10_unittest | P10 | included_acceptance_gate | python_script | portable_linux / p10 | \<p10-python\> -B scripts/run_p8_unittest_suite.py --start-directory tests/p10 --top-level-directory . --json-output \<p10-temp\>/p10-unittest.json | scripts/run_p8_unittest_suite.py#main / 100644 / 35d0ef6a88025ef5bc10925009e044c6a84025c8 | 900 | {"error_count":0,"failure_count":0,"skip_count":0,"status":"passed","test_count":39,"test_count_semantics":"historical_python_unittest_cases"} | none |
| 85 | p10_studio_eslint | P10 | included_acceptance_gate | npm_script | portable_linux / p10 | corepack npm run lint | studio/package.json#lint / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | 600 | {"status":"passed"} | none |
| 86 | p10_studio_prettier | P10 | included_acceptance_gate | npm_script | portable_linux / p10 | corepack npm run format:check | studio/package.json#format:check / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | 600 | {"status":"passed"} | none |
| 87 | p10_studio_typescript | P10 | included_acceptance_gate | npm_script | portable_linux / p10 | corepack npm run typecheck | studio/package.json#typecheck / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | 600 | {"status":"passed"} | none |
| 88 | p10_studio_vitest | P10 | included_acceptance_gate | npm_script | portable_linux / p10 | corepack npm test -- --run | studio/package.json#test / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | 600 | {"status":"passed"} | none |
| 89 | p10_studio_vite_build | P10 | included_acceptance_gate | npm_script | portable_linux / p10 | corepack npm run build | studio/package.json#build / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | 600 | {"status":"passed"} | none |
| 90 | p10_repository | P10 | included_acceptance_gate | python_script | portable_linux / p10 | \<p10-python\> -B scripts/check_p10_repository.py . | scripts/check_p10_repository.py#main / 100644 / 6db14ae002894c14204734c564ee827dc0465835 | 300 | {"status":"passed"} | none |
| 91 | p10_provenance | P10 | included_acceptance_gate | python_script | portable_linux / p10 | \<p10-python\> -B scripts/check_p10_provenance.py . | scripts/check_p10_provenance.py#main / 100644 / 51a2163866a1cd1aebf37c69f0de3abd35ad3f33 | 300 | {"status":"passed"} | none |
| 92 | p10_distribution | P10 | included_acceptance_gate | python_script | portable_linux / p10 | \<p10-python\> -B scripts/check_p10_distribution.py . | scripts/check_p10_distribution.py#main / 100644 / a4687649f3ab6e64f13c41015527f17265b1130a | 300 | {"status":"passed"} | none |
| 93 | p10_security | P10 | included_acceptance_gate | python_script | portable_linux / p10 | \<p10-python\> -B scripts/check_p10_security.py . | scripts/check_p10_security.py#main / 100644 / aa0ce7c10f0a3bde84270521830f54c7156f2657 | 300 | {"status":"passed"} | none |
| 94 | p10_operations | P10 | included_acceptance_gate | python_script | portable_linux / p10 | \<p10-python\> -B scripts/check_p10_operations.py . | scripts/check_p10_operations.py#main / 100644 / 64173d44dab2c4fd646ed5a4e72278dcd329bd9c | 300 | {"status":"passed"} | none |
| 95 | p10_i18n | P10 | included_acceptance_gate | python_script | portable_linux / p10 | \<p10-python\> -B scripts/check_p10_i18n.py . | scripts/check_p10_i18n.py#main / 100644 / 5ae8590ee118191de99108f08809faa01b74abcc | 300 | {"status":"passed"} | none |
| 96 | p10_compatibility | P10 | included_acceptance_gate | python_script | portable_linux / p10 | \<p10-python\> -B scripts/check_p10_compatibility.py . | scripts/check_p10_compatibility.py#main / 100644 / 3d1a5c85409aa5a3741c8a7ea6365c9814184209 | 300 | {"status":"passed"} | none |
| 97 | p10_reproducibility | P10 | included_acceptance_gate | python_script | portable_linux / p10 | \<p10-python\> -B scripts/check_p10_reproducibility.py . | scripts/check_p10_reproducibility.py#main / 100644 / 50f766427755c650795e04b0bc92c69927840fef | 1200 | {"status":"passed"} | none |
| 98 | p10_public_boundary | P10 | included_acceptance_gate | python_script | portable_linux / p10 | \<p10-python\> -B scripts/check_public_boundary.py . | scripts/check_public_boundary.py#main / 100644 / 35f6cb4e729987b2c0b18cf8981f328e72445297 | 300 | {"status":"passed"} | none |
| 99 | p10_git_diff_check | P10 | included_acceptance_gate | git | portable_linux / p10 | git diff --check | null | 300 | {"status":"passed"} | none |
| 100 | p10_evidence | P10 | included_acceptance_gate | python_script | portable_linux / p10 | \<p10-python\> -B scripts/check_p10_evidence.py . | scripts/check_p10_evidence.py#main / 100644 / 0d8079d60b8459eccc71e62af3b70fd4bc4eb591 | 300 | {"status":"passed"} | none |
| 101 | p10_compose_runtime | P10 | excluded_acceptance_gate | python_script | replay=ubuntu-24.04; Ubuntu status=not_proven; Darwin anchor=passed / p10 | \<p10-python\> -B scripts/check_p10_compose_runtime.py . | scripts/check_p10_compose_runtime.py#main / 100644 / 44cf5504f0728e571cfeaa2e33d75c8b58bec738 | 1200 | {"disposition":"excluded_acceptance_gate","executor_result":"not_run_platform_excluded","exit_status":null,"linux_public_pilot_readiness":"blocked","replay_platform":"ubuntu-24.04","ubuntu_historical_execution_status":"not_proven"} | anchor_platform=darwin; anchor_historical_status=passed; purpose=immutable_platform_scoped_identity_only; commit 4bef5629d450c6bb3940f606fc90194e008ee8fd; tree 909b566b7ba9f7beb143cd0b29cf95fbd1178bbe; artifacts/p10/summary.json; blob a4c1a59fffec9c30160787a7bec584e228fb9f35; file sha256 876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae; result=p10_summary["compose_runtime"]; canonical bytes=476; sha256=4f6f5de0a92d2aa3bea1ab80ad94b869a4fd1cbe5f459804eea3cd86377e137b; gate=p10_compose_runtime_clean; verified_gates membership; aggregate passed; exact Darwin guard; native_architecture=arm64 |
| 102 | p10_quickstart | P10 | excluded_acceptance_gate | python_script | replay=ubuntu-24.04; Ubuntu status=not_proven; Darwin anchor=passed / p10 | \<p10-python\> -B scripts/check_p10_quickstart.py . | scripts/check_p10_quickstart.py#main / 100644 / 6b352a180683969deed9b396b9b94b4488232411 | 1200 | {"disposition":"excluded_acceptance_gate","executor_result":"not_run_platform_excluded","exit_status":null,"linux_public_pilot_readiness":"blocked","replay_platform":"ubuntu-24.04","ubuntu_historical_execution_status":"not_proven"} | anchor_platform=darwin; anchor_historical_status=passed; purpose=immutable_platform_scoped_identity_only; commit 4bef5629d450c6bb3940f606fc90194e008ee8fd; tree 909b566b7ba9f7beb143cd0b29cf95fbd1178bbe; artifacts/p10/summary.json; blob a4c1a59fffec9c30160787a7bec584e228fb9f35; file sha256 876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae; result=p10_summary["quickstart"]; canonical bytes=874; sha256=75c18fadb57dd93914a8f99996857af22c2da8c82c504582b9eaa412c1f00c1b; gate=p10_quickstart_clean; verified_gates membership; aggregate passed; actual_macos=true; platform_class=macos/arm64 |
| 103 | p10_remote_distribution | P10 | excluded_acceptance_gate | python_script | replay=ubuntu-24.04; Ubuntu status=not_proven; Darwin anchor=passed / p10 | \<p10-python\> -B scripts/check_p10_quickstart.py . --remote-distribution | scripts/check_p10_quickstart.py#main / 100644 / 6b352a180683969deed9b396b9b94b4488232411 | 1200 | {"disposition":"excluded_acceptance_gate","executor_result":"not_run_platform_excluded","exit_status":null,"linux_public_pilot_readiness":"blocked","replay_platform":"ubuntu-24.04","ubuntu_historical_execution_status":"not_proven"} | anchor_platform=darwin; anchor_historical_status=passed; purpose=immutable_platform_scoped_identity_only; commit 4bef5629d450c6bb3940f606fc90194e008ee8fd; tree 909b566b7ba9f7beb143cd0b29cf95fbd1178bbe; artifacts/p10/summary.json; blob a4c1a59fffec9c30160787a7bec584e228fb9f35; file sha256 876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae; result={"distribution":p10_summary["remote_distribution"],"quickstart":p10_summary["remote_quickstart"]}; canonical bytes=2538; sha256=4383d540c4cd95f62db32aaadc1dfdf8e027eb0bd81b9909c4a0dda9a3d06c78; outer gate=p10_remote_distribution_and_quickstart_clean; verified_gates membership; aggregate passed; remote assertions passed; quickstart actual_macos=true and platform_class=macos/arm64 |
| 104 | p11_setup | P11 | setup | object_setup | portable_linux / p11 | create one exact-object checkout and isolated locked resources | null | 1800 | {"cleanup_residue_count":0,"npm_workspace":"one_locked","python_environment":"one_hash_locked","status":"passed"} | none |
| 105 | p11_summary_anchor | P11 | evidence_anchor | identity_check | object_identity_all_platforms / p11 | verify 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38:artifacts/p11/summary.json | null | 300 | {"anchor_commit":"7e5387f148f86b5c9b07820dd8b8f4e18e12dc38","anchor_tree":"6d7c1b3053fefc1f3b14a4b39fde2d5adb641990","blob":"f9f58cd3094147f724a622a929eb98331af441a1","json_expectations":{"claim":"p11_agent_package_multi_agent_lifecycle_candidate","status":"development_complete_awaiting_independent_acceptance"},"path":"artifacts/p11/summary.json","sha256":"5f8072da2027265d9ee1ac959607d905fa68e1e88802f45a4f9bcb918707c7c9","status":"identity_verified"} | none |
| 106 | p11_python_lock_anchor | P11 | evidence_anchor | identity_check | object_identity_all_platforms / p11 | verify 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38:requirements/p8.lock | null | 300 | {"anchor_commit":"7e5387f148f86b5c9b07820dd8b8f4e18e12dc38","anchor_tree":"6d7c1b3053fefc1f3b14a4b39fde2d5adb641990","blob":"819980980ba87d1b7166af4b4b0da53ca4e4ac63","path":"requirements/p8.lock","sha256":"5afb5bc2f6bf2cfdc77d0457b92255f822d89cd3cd754ebb876741d7ee6430d0","status":"identity_verified"} | none |
| 107 | p11_npm_lock_anchor | P11 | evidence_anchor | identity_check | object_identity_all_platforms / p11 | verify 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38:studio/package-lock.json | null | 300 | {"anchor_commit":"7e5387f148f86b5c9b07820dd8b8f4e18e12dc38","anchor_tree":"6d7c1b3053fefc1f3b14a4b39fde2d5adb641990","blob":"e1ca59eac16dec46a290aaf2c010b5fc9de9cd91","path":"studio/package-lock.json","sha256":"44dba55271fa10c3b7bea09aa333c98dbf868f6cc55a8e59776ca1464c067875","status":"identity_verified"} | none |
| 108 | p11_retained_p10_portable | P11 | included_acceptance_gate | predecessor_result | portable_linux / p11 | verify exact completed P10 portable result and inventory digest | null | 300 | {"predecessor_object":"P10","rerun_count":0,"status":"passed"} | none |
| 109 | p11_ruff_lint | P11 | included_acceptance_gate | python_module | portable_linux / p11 | \<p11-python\> -m ruff check src scripts tests | null | 900 | {"status":"passed"} | none |
| 110 | p11_ruff_format | P11 | included_acceptance_gate | python_module | portable_linux / p11 | \<p11-python\> -m ruff format --check src scripts tests | null | 900 | {"status":"passed"} | none |
| 111 | p11_mypy_strict | P11 | included_acceptance_gate | python_module | portable_linux / p11 | \<p11-python\> -m mypy src scripts tests | null | 900 | {"status":"passed"} | none |
| 112 | p11_unittest | P11 | included_acceptance_gate | python_script | portable_linux / p11 | \<p11-python\> -B scripts/run_p8_unittest_suite.py --start-directory tests/p11 --top-level-directory . --json-output \<p11-temp\>/p11-unittest.json | scripts/run_p8_unittest_suite.py#main / 100644 / 35d0ef6a88025ef5bc10925009e044c6a84025c8 | 900 | {"error_count":0,"failure_count":0,"skip_count":0,"status":"passed","test_count":101,"test_count_semantics":"historical_python_unittest_cases"} | none |
| 113 | p11_studio_eslint | P11 | included_acceptance_gate | npm_script | portable_linux / p11 | corepack npm run lint | studio/package.json#lint / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | 600 | {"status":"passed"} | none |
| 114 | p11_studio_prettier | P11 | included_acceptance_gate | npm_script | portable_linux / p11 | corepack npm run format:check | studio/package.json#format:check / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | 600 | {"status":"passed"} | none |
| 115 | p11_studio_typescript | P11 | included_acceptance_gate | npm_script | portable_linux / p11 | corepack npm run typecheck | studio/package.json#typecheck / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | 600 | {"status":"passed"} | none |
| 116 | p11_studio_vitest | P11 | included_acceptance_gate | npm_script | portable_linux / p11 | corepack npm test -- --run | studio/package.json#test / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | 600 | {"status":"passed"} | none |
| 117 | p11_studio_vite_build | P11 | included_acceptance_gate | npm_script | portable_linux / p11 | corepack npm run build | studio/package.json#build / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | 600 | {"status":"passed"} | none |
| 118 | p11_repository | P11 | included_acceptance_gate | python_script | portable_linux / p11 | \<p11-python\> -B scripts/check_p11_repository.py . | scripts/check_p11_repository.py#main / 100644 / f8537817378b7265071112250d8fadeaa134a616 | 300 | {"status":"passed"} | none |
| 119 | p11_provenance | P11 | included_acceptance_gate | python_script | portable_linux / p11 | \<p11-python\> -B scripts/check_p11_provenance.py . | scripts/check_p11_provenance.py#main / 100644 / fb3c7aaaf935388bfcf8e46f5d8e816f927bea8b | 300 | {"status":"passed"} | none |
| 120 | p11_architecture | P11 | included_acceptance_gate | python_script | portable_linux / p11 | \<p11-python\> -B scripts/check_p11_architecture.py . | scripts/check_p11_architecture.py#main / 100644 / 82a9d85f4ec7d0d2761d7b312f317df88cbbbbe1 | 300 | {"status":"passed"} | none |
| 121 | p11_migrations | P11 | included_acceptance_gate | python_script | portable_linux / p11 | \<p11-python\> -B scripts/check_p11_migrations.py . | scripts/check_p11_migrations.py#main / 100644 / 75076416c8e5aa82517c35166ea3d3a99e2642d7 | 300 | {"status":"passed"} | none |
| 122 | p11_compatibility | P11 | included_acceptance_gate | python_script | portable_linux / p11 | \<p11-python\> -B scripts/check_p11_compatibility.py . | scripts/check_p11_compatibility.py#main / 100644 / 369517b0b95043cb0349af124eaed27e98746f9e | 300 | {"status":"passed"} | none |
| 123 | p11_studio | P11 | included_acceptance_gate | python_script | portable_linux / p11 | \<p11-python\> -B scripts/check_p11_studio.py . | scripts/check_p11_studio.py#main / 100644 / f152f82baaf7f830f88bc5c72d19a87dd7c4589f | 300 | {"status":"passed"} | none |
| 124 | p11_public_boundary | P11 | included_acceptance_gate | python_script | portable_linux / p11 | \<p11-python\> -B scripts/check_public_boundary.py . | scripts/check_public_boundary.py#main / 100644 / 35f6cb4e729987b2c0b18cf8981f328e72445297 | 300 | {"status":"passed"} | none |
| 125 | p11_candidate_diff | P11 | included_acceptance_gate | python_function | portable_linux / p11 | scripts.p11_gate_support.candidate_diff_check(.) | scripts/p11_gate_support.py#candidate_diff_check / 100644 / 02024443d0f8399e3168eef5abd8601873c2f39a | 300 | {"status":"passed"} | none |
| 126 | p11_compose_runtime | P11 | included_acceptance_gate | python_script | portable_linux / p11 | \<p11-python\> -B scripts/check_p11_compose_runtime.py . | scripts/check_p11_compose_runtime.py#main / 100644 / 61486f133fe2279eebfa2d19ed8144a4f8fdb85c | 1200 | {"cleanup_residue_count":0,"status":"passed"} | none |
| 127 | p11r_setup | P11R | setup | object_setup | portable_linux / p11r | create one exact-object checkout and isolated locked resources | null | 1500 | {"cleanup_residue_count":0,"npm_workspace":"one_locked","python_environment":"one_hash_locked","status":"passed"} | none |
| 128 | p11r_summary_anchor | P11R | evidence_anchor | identity_check | object_identity_all_platforms / p11r | verify c1562ea5201394d8a278f4b644daf4029cbb5bd4:artifacts/p11r/summary.json | null | 300 | {"anchor_commit":"c1562ea5201394d8a278f4b644daf4029cbb5bd4","anchor_tree":"ae0f33263cfc7445fef69656ad9c5cb04d4a2d00","blob":"30d4d3ac2360b165863c156b50628141141f13e9","json_expectations":{"claim":"p11r_post_p11_governance_and_ci_alignment_candidate","status":"development_complete_awaiting_independent_acceptance"},"path":"artifacts/p11r/summary.json","sha256":"6d44960d9dc9035995acc36e4734648bc5bd67cc79c412192a790745d178084f","status":"identity_verified"} | none |
| 129 | p11r_python_lock_anchor | P11R | evidence_anchor | identity_check | object_identity_all_platforms / p11r | verify c1562ea5201394d8a278f4b644daf4029cbb5bd4:requirements/p8.lock | null | 300 | {"anchor_commit":"c1562ea5201394d8a278f4b644daf4029cbb5bd4","anchor_tree":"ae0f33263cfc7445fef69656ad9c5cb04d4a2d00","blob":"819980980ba87d1b7166af4b4b0da53ca4e4ac63","path":"requirements/p8.lock","sha256":"5afb5bc2f6bf2cfdc77d0457b92255f822d89cd3cd754ebb876741d7ee6430d0","status":"identity_verified"} | none |
| 130 | p11r_npm_lock_anchor | P11R | evidence_anchor | identity_check | object_identity_all_platforms / p11r | verify c1562ea5201394d8a278f4b644daf4029cbb5bd4:studio/package-lock.json | null | 300 | {"anchor_commit":"c1562ea5201394d8a278f4b644daf4029cbb5bd4","anchor_tree":"ae0f33263cfc7445fef69656ad9c5cb04d4a2d00","blob":"e1ca59eac16dec46a290aaf2c010b5fc9de9cd91","path":"studio/package-lock.json","sha256":"44dba55271fa10c3b7bea09aa333c98dbf868f6cc55a8e59776ca1464c067875","status":"identity_verified"} | none |
| 131 | p11r_retained_p11_portable | P11R | included_acceptance_gate | predecessor_result | portable_linux / p11r | verify exact completed P11 portable result and inventory digest | null | 300 | {"predecessor_object":"P11","rerun_count":0,"status":"passed"} | none |
| 132 | p11r_ruff_lint | P11R | included_acceptance_gate | python_module | portable_linux / p11r | \<p11r-python\> -m ruff check src scripts tests | null | 900 | {"status":"passed"} | none |
| 133 | p11r_ruff_format | P11R | included_acceptance_gate | python_module | portable_linux / p11r | \<p11r-python\> -m ruff format --check src scripts tests | null | 900 | {"status":"passed"} | none |
| 134 | p11r_mypy_strict | P11R | included_acceptance_gate | python_module | portable_linux / p11r | \<p11r-python\> -m mypy src scripts tests | null | 900 | {"status":"passed"} | none |
| 135 | p11r_current_p11_tests | P11R | included_acceptance_gate | python_script | portable_linux / p11r | \<p11r-python\> -B -m scripts.run_p11r_toolchain --scope current-tests --json-output \<p11r-temp\>/current-p11.json | scripts/run_p11r_toolchain.py#main:current-tests / 100644 / 599f2328a03db9216ed2fdc1b1a1af919834800a | 900 | {"error_count":0,"failure_count":0,"skip_count":0,"status":"passed","test_count":100,"test_count_semantics":"historical_python_unittest_cases"} | none |
| 136 | p11r_governance_tests | P11R | included_acceptance_gate | python_script | portable_linux / p11r | \<p11r-python\> -B -m scripts.run_p11r_toolchain --scope p11r-tests --json-output \<p11r-temp\>/p11r.json | scripts/run_p11r_toolchain.py#main:p11r-tests / 100644 / 599f2328a03db9216ed2fdc1b1a1af919834800a | 900 | {"error_count":0,"failure_count":0,"skip_count":0,"status":"passed","test_count":36,"test_count_semantics":"historical_python_unittest_cases"} | none |
| 137 | p11r_studio_eslint | P11R | included_acceptance_gate | npm_script | portable_linux / p11r | corepack npm run lint | studio/package.json#lint / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | 600 | {"status":"passed"} | none |
| 138 | p11r_studio_prettier | P11R | included_acceptance_gate | npm_script | portable_linux / p11r | corepack npm run format:check | studio/package.json#format:check / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | 600 | {"status":"passed"} | none |
| 139 | p11r_studio_typescript | P11R | included_acceptance_gate | npm_script | portable_linux / p11r | corepack npm run typecheck | studio/package.json#typecheck / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | 600 | {"status":"passed"} | none |
| 140 | p11r_studio_vitest | P11R | included_acceptance_gate | npm_script | portable_linux / p11r | corepack npm test -- --run | studio/package.json#test / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | 600 | {"status":"passed"} | none |
| 141 | p11r_studio_vite_build | P11R | included_acceptance_gate | npm_script | portable_linux / p11r | corepack npm run build | studio/package.json#build / 100644 / 7ea47041d96282f8c98690789dd5b40880969326 | 600 | {"status":"passed"} | none |
| 142 | p11r_architecture | P11R | included_acceptance_gate | python_script | portable_linux / p11r | \<p11r-python\> -B scripts/check_p11_architecture.py . | scripts/check_p11_architecture.py#main / 100644 / 82a9d85f4ec7d0d2761d7b312f317df88cbbbbe1 | 300 | {"status":"passed"} | none |
| 143 | p11r_migrations | P11R | included_acceptance_gate | python_script | portable_linux / p11r | \<p11r-python\> -B scripts/check_p11_migrations.py . | scripts/check_p11_migrations.py#main / 100644 / 75076416c8e5aa82517c35166ea3d3a99e2642d7 | 300 | {"status":"passed"} | none |
| 144 | p11r_compatibility | P11R | included_acceptance_gate | python_script | portable_linux / p11r | \<p11r-python\> -B scripts/check_p11_compatibility.py . | scripts/check_p11_compatibility.py#main / 100644 / 369517b0b95043cb0349af124eaed27e98746f9e | 300 | {"status":"passed"} | none |
| 145 | p11r_studio_contract | P11R | included_acceptance_gate | python_script | portable_linux / p11r | \<p11r-python\> -B scripts/check_p11_studio.py . | scripts/check_p11_studio.py#main / 100644 / f152f82baaf7f830f88bc5c72d19a87dd7c4589f | 300 | {"status":"passed"} | none |
| 146 | p11r_ci_policy | P11R | included_acceptance_gate | python_script | portable_linux / p11r | \<p11r-python\> -B scripts/check_p11r_ci_policy.py . | scripts/check_p11r_ci_policy.py#main / 100644 / ce0bbf7f3e18062d6d77f1d16e303376c58df2f4 | 300 | {"status":"passed"} | none |
| 147 | p11r_repository_ci | P11R | included_acceptance_gate | python_script | portable_linux / p11r | \<p11r-python\> -B scripts/check_p11r_repository.py . --mode ci | scripts/check_p11r_repository.py#main / 100644 / e684975be4b651c3f731bd30b1cf09f89046978e | 300 | {"status":"passed"} | none |
| 148 | p11r_provenance | P11R | included_acceptance_gate | python_script | portable_linux / p11r | \<p11r-python\> -B scripts/check_p11r_provenance.py . | scripts/check_p11r_provenance.py#main / 100644 / 51673c267cef7c16836f588d72cad60bed32c995 | 300 | {"status":"passed"} | none |
| 149 | p11r_public_boundary | P11R | included_acceptance_gate | python_script | portable_linux / p11r | \<p11r-python\> -B scripts/check_public_boundary.py . | scripts/check_public_boundary.py#main / 100644 / 35f6cb4e729987b2c0b18cf8981f328e72445297 | 300 | {"status":"passed"} | none |
| 150 | p11r_candidate_repository | P11R | included_acceptance_gate | python_script | portable_linux / p11r | \<p11r-python\> -B scripts/check_p11r_repository.py . --mode candidate | scripts/check_p11r_repository.py#main / 100644 / e684975be4b651c3f731bd30b1cf09f89046978e | 300 | {"status":"passed"} | none |
| 151 | p11r_compose_runtime | P11R | included_acceptance_gate | python_script | portable_linux / p11r | \<p11r-python\> -B scripts/check_p11_compose_runtime.py . | scripts/check_p11_compose_runtime.py#main / 100644 / 61486f133fe2279eebfa2d19ed8144a4f8fdb85c | 1200 | {"cleanup_residue_count":0,"status":"passed"} | none |

## Appendix C — Platform-qualified accepted historical evidence

### Independent status dimensions

Every excluded item records all of the following without an unqualified historical-status alias:

~~~json
{
  "replay_platform": "ubuntu-24.04",
  "ubuntu_historical_execution_status": "not_proven",
  "disposition": "excluded_acceptance_gate",
  "linux_public_pilot_readiness": "blocked",
  "executor_result": "not_run_platform_excluded",
  "exit_status": null
}
~~~

Its embedded accepted anchor separately records:

~~~json
{
  "anchor_platform": "darwin",
  "anchor_historical_status": "passed",
  "purpose": "immutable_platform_scoped_identity_only"
}
~~~

P12 governance result is a third independent field and may be `passed`. A P12 pass cannot change either the Ubuntu evaluation or Linux readiness.

### Anchor canonicalization

Each embedded anchor selects immutable JSON subresults and wraps them as `{"gate_id": ..., "result": ...}`. Canonical bytes use UTF-8, sorted keys, separators `(",", ":")`, `ensure_ascii=false`, `allow_nan=false`, and no terminal newline.

| Gate | Source summary | Exact selection/construction | Bytes | Canonical SHA-256 |
| --- | --- | --- | ---: | --- |
| `p8_compose_runtime` | P8 blob `964406b20e9fc1e98b8eeda3c24bf3f22f226768`; file SHA-256 `78905893f9a06bf6b5361c76a8e152dbe8de2ec53d1aede84fca2f7ce1b5921b` | `result = p8_summary["compose_runtime"]` | 2348 | `a2acd8e3f935d9c520f58e76b8384514e596e59f94f7bb62e1881ce9183c9bbd` |
| `p8_golden_path` | Same immutable P8 summary | `result = p8_summary["golden_path"]` | 2034 | `c1f1f8148cd3b0184d92720e862bbadfe7e330fd4087b7eb03190400d6742f44` |
| `p10_compose_runtime` | P10 blob `a4c1a59fffec9c30160787a7bec584e228fb9f35`; file SHA-256 `876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae` | `result = p10_summary["compose_runtime"]` | 476 | `4f6f5de0a92d2aa3bea1ab80ad94b869a4fd1cbe5f459804eea3cd86377e137b` |
| `p10_quickstart` | Same immutable P10 summary | `result = p10_summary["quickstart"]` | 874 | `75c18fadb57dd93914a8f99996857af22c2da8c82c504582b9eaa412c1f00c1b` |
| `p10_remote_distribution` | Same immutable P10 summary | Exact two-selected-subresults construction below | 2538 | `4383d540c4cd95f62db32aaadc1dfdf8e027eb0bd81b9909c4a0dda9a3d06c78` |

The P10 remote construction is exactly:

~~~python
result = {
    "distribution": p10_summary["remote_distribution"],
    "quickstart": p10_summary["remote_quickstart"],
}
payload = {
    "gate_id": "p10_remote_distribution",
    "result": result,
}
~~~

The composite result keys are exactly `distribution` and `quickstart`. `remote_distribution` and `remote_quickstart` are source-summary keys only. This 2538-byte object is not the complete historical function return. The function's outer gate `p10_remote_distribution_and_quickstart_clean` is bound separately to the exact entrypoint and accepted status assertions; it is not injected into the composite.

### Gate-specific Darwin proof

- P8 Compose: `/compose_runtime/gate = p8_compose_runtime_clean`, `/compose_runtime/status = passed`, and `/compose_runtime/environment/host = darwin`.
- P8 Golden Path: `/golden_path/gate = p8_golden_path_clean` and `/golden_path/status = passed`; Darwin qualification is the exact direct call to Compose plus the same summary's Compose host, not a fabricated Golden Path platform scalar.
- P10 Compose: `verified_gates` contains `p10_compose_runtime`, aggregate status is passed, `_native_platform` rejects non-Darwin, and accepted architecture is arm64. The selected result has no invented generic status or OS field.
- P10 Quickstart: `verified_gates` membership and aggregate status prove acceptance; the selected result supplies `actual_macos = true` and `platform_class = macos/arm64`.
- P10 Remote: `verified_gates` contains `p10_remote_distribution`, aggregate status is passed, remote distribution and remote pull assertions passed, and remote quickstart supplies `actual_macos = true` and `platform_class = macos/arm64`.

## Appendix D — Exact protected 40-path WIP identity

| Class | Path | Mode | Bytes | SHA-256 |
| --- | --- | --- | ---: | --- |
| tracked modified | `.github/ISSUE_TEMPLATE/feature_request.yml` | 100644 | 1186 | 40d0c49b8fbc2db739b727f70ad36579003c17c79993e089815ad32430be02f4 |
| tracked modified | `.github/pull_request_template.md` | 100644 | 1733 | f522b233f07316df8bb3b0b4f165954e60c4832e95682c1abf58c109f299aec0 |
| tracked modified | `.github/workflows/ci.yml` | 100644 | 5312 | 8f5c929042a958acb38f7dfacbb2065587cbe5441f31c203bf4534759b7b0ae3 |
| tracked modified | `AGENTS.md` | 100644 | 6684 | 080da09f06b5fb277869c35488fffcab25361fbf7e4ac1d4e136dbf24d69f9ac |
| tracked modified | `CONTRIBUTING.md` | 100644 | 3067 | eccd2277f24d2dcf97c39935f7f6a22eacf51af0f8736348f914885eb0376159 |
| tracked modified | `Makefile` | 100644 | 18738 | 944e3c9557f24ced444d5c2e76c7c97ddfe8d9a40eba206e94d32367b1948626 |
| tracked modified | `README.md` | 100644 | 16979 | 9402f414acf4ffc4daee66f77769e203e490fd4702f575562a269a2d6766109f |
| tracked modified | `SECURITY.md` | 100644 | 5436 | 9f6b13e2467471e46c6d4757ee5412fe122e17ae2690706420f31378120e887d |
| untracked | `docs/adr/0011-public-pilot-continuity-rebaseline.md` | 100644 | 15823 | e6121fa5fe9e651af2dc6ec825284cd7a37b9861a5e37dfd46d8cabb1ad2229e |
| tracked modified | `docs/architecture/target-architecture.md` | 100644 | 30791 | 88670abcfe7f692a881c28d9215fa677b41c0346c130fd86dd06cbb9918c89a9 |
| tracked modified | `docs/development.md` | 100644 | 15968 | 15718a89fe64fa80d036addb54ea6c938d66a6dcd4109a2b15a2617fa37dcac1 |
| untracked | `docs/p12/portable-historical-inventory.json` | 100644 | 132968 | b7f4dfd8370278c0c7aec53217e1785fbac94cecd6317b01ed6322e343e39cf3 |
| untracked | `docs/p12/rebaseline-checklist.md` | 100644 | 6550 | bdff4a0f48c1b1c48452f8bb26a1b59cb433bdeee94c1c6974102cd4127aac48 |
| tracked modified | `docs/product/capability-matrix.md` | 100644 | 7685 | e275633a51c4844c478189da40ecabf97a020906de5f2a9f1d5b4508b7881ed1 |
| tracked modified | `docs/product/post-v0.1-capability-outlook.md` | 100644 | 7523 | 8e23e3515d2b7eb494f0021c527ca0f7d7acb1ead9bb2236947108ed5a6aff44 |
| tracked modified | `docs/product/v0.2-external-dependency-register.md` | 100644 | 5637 | dfba74bb4b31c45760f2b5d18f5a559fe2501e1c08ab45b5082dbac3c59bc326 |
| tracked modified | `docs/product/v0.2-public-pilot-capability-matrix.md` | 100644 | 5363 | bd0ba33aa4890d199e292e43bb1d3ae634f17a17c9e5fda4164904e364899a3b |
| tracked modified | `docs/product/v0.2-public-pilot-product-brief.md` | 100644 | 15088 | d90c6e2479de883cced5d85b3ddf07bedf1b63cc20b1477c39e5ea129dfcfbac |
| tracked modified | `docs/roadmap.md` | 100644 | 31322 | a107036e997080201543e2fe3ea3f37d008ce3eeecde51fb207b23047ec3bd7b |
| tracked modified | `docs/security/privacy-boundary.md` | 100644 | 17439 | 07470ac3c3375482f387ae2d32d888659a3f39c3a3fd6b4ad8a23eb7d2f3025f |
| tracked modified | `docs/security/threat-model.md` | 100644 | 16069 | 6e5aaf21cd128aa44a59da6ab9c27b9e7b695e7fb777fa2cfcbdbbfd52df2551 |
| tracked modified | `docs/security/v0.2-public-pilot-privacy-boundary.md` | 100644 | 8320 | 8ed7e9625777efb93d91b4258bd1f6b616be5184ffb89cf6309816d3617aa2e0 |
| tracked modified | `docs/security/v0.2-public-pilot-threat-model.md` | 100644 | 8991 | 478ae2d1740dc5340d3de530c344e66737918e334a5904ab7e6bc6373fa3a0e4 |
| untracked | `provenance/p12-change-receipt.json` | 100644 | 15556 | 5535317287207222b98f5e3b461b5e7d11997659ca9434edb37806b78e3aa60d |
| untracked | `scripts/check_p12_ci_policy.py` | 100644 | 25800 | dc669ba39cca5f78ccaaceeec0bf4a928dedbad22c28bb4b2613960de23a1489 |
| untracked | `scripts/check_p12_historical_inventory.py` | 100644 | 75790 | 47b7716066ba4866dec5e9d43da0e466ba6cfe96820676b2b8818a0dbc74d0a9 |
| untracked | `scripts/check_p12_migrations.py` | 100644 | 5707 | aa51ced8e583f1ce6073d02de27048035740c92d80692011be60043d7b450d9a |
| untracked | `scripts/check_p12_provenance.py` | 100644 | 19603 | ae16748b28d27bfc6e12d95352293a8a6e97a8071544294c12ebd065176af460 |
| untracked | `scripts/check_p12_rebaseline.py` | 100644 | 14480 | 449acf26f82cf110054c272cc2eb8c8df6da1a8b0c67bf8163d2bf57df18a0ce |
| untracked | `scripts/check_p12_repository.py` | 100644 | 18720 | 8fd677b3258c29f856c94c780cabdbb5646f8f0caf237a9b2e982bf3568406e6 |
| untracked | `scripts/collect_p12_evidence.py` | 100644 | 16869 | 5002dad62b246e8d02a7bcbca86ba4d6ea014be508e38eaf12d927e15e89c1c1 |
| untracked | `scripts/run_p12_toolchain.py` | 100644 | 111304 | fc225ed9242f53891e533f518288f07b0a175064d4e573c6ba2f6ef4aab19b34 |
| untracked | `tests/p12/__init__.py` | 100644 | 67 | 5a0b704c65318139ecdb86b937f563c86fd395b45da0161d0e7cf4586522de68 |
| untracked | `tests/p12/test_ci_policy.py` | 100644 | 10325 | aa301aa4e5210b440a898439492e08e2aee08c222540eb454d36388f2e008add |
| untracked | `tests/p12/test_evidence_gate.py` | 100644 | 22524 | fe5473d0aca4d6798bcece9931b16e3ee4fbee4c30eb5b14d12cb352eb97cce9 |
| untracked | `tests/p12/test_historical_inventory.py` | 100644 | 11162 | b979a0c20fedcf665a1befd3a9d8a7d7b6a9dd9fb89d1b34f28dbd9dc02dea22 |
| untracked | `tests/p12/test_migrations.py` | 100644 | 2752 | d5ce0eaaa529faa97407ed40caea9868a16e9b08bd8ba415732ff91810fe90b5 |
| untracked | `tests/p12/test_provenance.py` | 100644 | 4491 | 942aaca5344ecd04126020b6b7ed1e298aa67419adfc1f3c908b92ce16a29147 |
| untracked | `tests/p12/test_rebaseline.py` | 100644 | 8202 | 78ffffae7f7266ad2cea6de150ad9dbeb1d76f6c20dbe708b9b8227bfa4a45d3 |
| untracked | `tests/p12/test_repository.py` | 100644 | 8131 | 46f6d720069d9924e707f18a13870b66baafaaedb896250f3135ded2807a5659 |

## Canonical 21-stage authorization lifecycle

The following is the sole canonical order. This section, the coverage matrix, every
acceptance clause, and every phase oracle MUST use these numbers and names without
combining, reordering, or silently omitting a stage:

1. **Blueprint owner review:** review and accept only the exact repository-external Blueprint identified in this contract.
2. **Repository-external v4 acceptance drafting:** write one complete external acceptance draft; perform no Git operation.
3. **Independent acceptance-draft pre-commit validation:** validate the external draft's identities, 129/151 rows, counts, schemas, coverage, and prose.
4. **Content-bearing repository-external WIP snapshot:** under separate authority, preserve the exact 40-file bytes and canonical manifest in the mode-0700 external snapshot defined under the protected WIP lifecycle; perform no Git or remote mutation.
5. **Independent WIP snapshot verification:** recompute all 40 file identities and the overall framed digest from the snapshot payload bytes themselves.
6. **v4 branch and acceptance-only commit in an independent temporary Git worktree:** under separate Git-mutation authority, start `codex/p12-public-pilot-continuity-rebaseline-v4` directly from the exact accepted base and create only the acceptance commit with that base as sole parent.
7. **Independent post-commit verification:** verify acceptance byte identity, sole parent, non-ancestry, exact one-path change, clean v4 worktree, preserved v1/v2/v3 refs, and unchanged dirty v3 WIP.
8. **Per-file read-only WIP reuse review:** compare each of the 40 verified snapshot payloads with the immutable v4 contract and record a reuse, correction, or rejection disposition; do not write the v4 worktree.
9. **Governance implementation authorization and linear allowlisted commits:** separately authorize approved migration/correction work and one or more append-only, single-parent implementation/scoped-correction commits on only the 40 implementation paths; never modify acceptance or create the summary.
10. **Local formal gates:** from a clean committed implementation head, run every required focused, affected, aggregate, historical, repository, public-boundary, residue, and zero-publication gate exactly as this contract fixes them.
11. **Candidate push and PR authorization:** separately authorize the exact non-force candidate-branch push and creation or update of the one OPEN main-based pull request with auto-merge disabled; do not merge or create summary evidence.
12. **Exact implementation-head PR CI:** require both canonical pull-request jobs and envelopes on the exact implementation head; a candidate push cannot create or satisfy a push-to-main envelope.
13. **Evidence-preflight authorization:** only after exact stage 12 success, separately authorize the read-only completed-run/envelope, registry, TLS, lock, and package checks and the repository-external one-use receipt bound to the exact final implementation HEAD and complete ordered commit set.
14. **Evidence-generation and summary-only commit authorization:** separately authorize consumption of the exact one-use receipt, generation of only `artifacts/p12/summary.json`, and the final append-only summary-only commit whose sole parent is the exact final implementation HEAD and which binds the complete implementation/scoped-correction chain and range digest; no later commit is allowed.
15. **Final-candidate push / PR update authorization:** separately authorize the non-force push of the exact summary-bearing final candidate and update of the existing OPEN PR; auto-merge remains disabled and no merge occurs.
16. **Exact final-candidate CI:** require both canonical pull-request jobs and exact envelopes on the final-candidate head.
17. **Independent acceptance:** independently verify the immutable contract, full commit chain, both pull-request CI stages, evidence, summary, status separation, zero publication, and final-candidate identities; no push-to-main envelope exists or is required.
18. **Project-owner final acceptance:** the owner explicitly accepts or rejects the final candidate after independent acceptance; this decision does not merge or push.
19. **Local fast-forward-only merge authorization:** separately authorize only a non-rewriting, fast-forward-only update of local `main` to the exact accepted final candidate; no merge commit, remote mutation, tag, Release, or publication.
20. **Remote main push authorization:** separately authorize an ordinary non-force push of that exact local-main commit to remote `refs/heads/main`; candidate-branch pushes cannot substitute for it.
21. **Exact push-to-main CI envelope and remote closeout verification:** wait for and verify the workflow triggered by the exact stage 20 remote-main push, require the two required jobs' exact push-to-main envelopes and exact head, then verify remote main, refs, PR disposition, protected P10 identities, residue, zero tags/Releases/publication, and truthful claim boundaries.

Entry into every stage requires an explicit project-owner decision; completing or passing one stage never authorizes the next. In particular, stages 6, 9, 11, 14, 15, 19, and 20 each change Git or remote state and each requires its own stage-specific authorization. A substantive failure at stage 10 or 12 stops the chain; any correction requires renewed, scoped stage 9 authority, a new append-only correction commit, and fresh stage 10 through stage 12 progression as applicable. Stage 13 cannot begin until the exact final implementation HEAD has passed stage 12. No stage permits amend, rebase, squash, reset, merge commit, force push, retry-as-correctness, or history rewrite. Tag, Release, package/image publication, signature, attestation, and P13 remain outside all 21 stages unless separately authorized by their later owning milestone.

### Stage 19 local fast-forward-only merge oracle

The Stage 18 decision report fixes `P12_FINAL_CANDIDATE`, its tree, the exact v4 pull
request number, and the exact successful Stage 16 run and attempt. Stage 19 authority
MUST name those values. Before moving local `main`, the operator verifies the final
candidate is the unchanged summary-only tip; the v4 candidate branch, remote branch, and
pull-request head all equal it; that PR is OPEN with `mergedAt` and `mergeCommit` null and
`autoMergeRequest` null; the complete single-parent ancestry and 42-path set pass;
the candidate worktree is clean; and local `main`, `origin/main`, and GitHub main still
equal c1562ea5201394d8a278f4b644daf4029cbb5bd4. The v1/v2/v3 preservation, PR #14,
P10 identities, zero tags/Releases/publication, and any still-protected v3 WIP/snapshot
state also pass their current oracles.

Stage 19 creates a new mode-0700 OS-temporary Git worktree for local `main`, verifies its
HEAD is the exact accepted base, and performs exactly one equivalent of:

~~~sh
git merge --ff-only "$P12_FINAL_CANDIDATE"
~~~

This operation must create no commit. Local `main` must then equal the exact final
candidate and its exact tree, while the candidate branch is unchanged and
`origin/main`/GitHub main remain the accepted base. The temporary worktree is removed and
its residue is zero. No push, pull-request mutation, tag, Release, publication, evidence
rewrite, or primary-v3-worktree operation is permitted. A non-fast-forward, merge commit,
unexpected ref movement, dirty state, or inability to remove only the task-owned
temporary worktree fails closed.

### Stage 20 exact remote-main push oracle

Stage 20 requires a new authority naming the same exact final candidate. Its preflight
requires local `main` at that candidate, both remote-main observations still at the exact
accepted base, the local and remote v4 candidate branches and pull-request head at the
same final candidate, and every Stage 19 preservation and zero-publication predicate
unchanged. A read-only repository-settings check must report
`delete_branch_on_merge = false`; otherwise Stage 20 stops before the push so the retained
v4 branch cannot be deleted automatically. The only permitted remote mutation is one ordinary, non-force push with the
exact refspec:

~~~sh
git push origin refs/heads/main:refs/heads/main
~~~

`--force`, `--force-with-lease`, deletion, tag refspecs, additional refspecs, and every
history rewrite are forbidden. The push must report old remote main as
c1562ea5201394d8a278f4b644daf4029cbb5bd4 and new remote main as the exact final
candidate. Afterward local `main`, `origin/main`, and GitHub main all equal the final
candidate; the local and remote v4 candidate branches remain present and unchanged at the
same commit. No command closes, merges, edits, or deletes the pull request or branch.
GitHub's automatic pull-request reachability transition, if any, is verified only by
Stage 21. Stage 20 success authorizes no CI selection or closeout claim.

### Stage 21 push-to-main CI and remote closeout oracle

Stage 21 receives explicit positive `P12_MAIN_RUN_ID` and `P12_MAIN_RUN_ATTEMPT` values;
it never selects `latest` or infers an attempt from branch state. Attempt 1 is the initial
eligible attempt. A rerun, cancellation, or later attempt is a separate remote mutation
requiring explicit project-owner authority; it cannot be initiated by Stage 21 itself.
The attempt-specific REST run must be completed/success, workflow name `CI`, workflow
path `.github/workflows/ci.yml`, event `push`, head branch `main`, and head SHA the exact
final candidate. Repository identity is `jeremyliu1220/digital-colleagues`, and the run's
push identity must correspond to the Stage 20 old/new main transition rather than any
candidate-branch push.

The attempt-specific job set must contain exactly one completed/success instance of each
required job and exactly one bounded smoke job with these identities:

| Job ID | Exact display name | Required conclusion | Envelope |
| --- | --- | --- | --- |
| `current-ci` | `Current P12 governance non-publishing verification` | success | exactly one valid push variant |
| `portable-history` | `Portable historical replay` | success | exactly one valid push variant |
| `main-compose-smoke` | `Bounded current P11R Compose smoke` | success | none; it is not historical P8/P10 Linux evidence |

Both required-job envelopes are obtained once from their exact numeric job-log endpoints
and parsed with the same marker, bounds, canonicalization, digest, closed schema, and REST
cross-checks as the Stage 13 protocol. Each has event `push`, head branch `main`, exact
final-candidate head SHA, and null `base_ref`, `base_sha`, and `pull_request_number`.
Their inventory identities/counts, five platform-qualified excluded results, embedded
Darwin anchors, observed environment, zero residue, zero publication, and
evidence-preflight-only registry placeholder must agree exactly as required. The smoke
job emits no P12 envelope and cannot replace either required job. A missing, duplicate,
failed, skipped, cancelled, timed-out, neutral, or action-required job; a non-success
workflow conclusion; or a wrong run/attempt/head/event fails closed.

Because the Stage 20 fast-forward makes the exact pull-request head reachable from
`main`, the v4 pull request's closeout state is fixed as GitHub `MERGED` (REST state
`closed` with `merged = true`). Its `mergedAt` is non-null, `mergeCommit.oid` equals the
exact final candidate, and `autoMergeRequest` is null. `baseRefName` is `main`, live
`baseRefOid` and `headRefOid` both equal the final candidate, and `headRefName` remains
`codex/p12-public-pilot-continuity-rebaseline-v4`. The original accepted-base SHA remains
bound by the two Stage 16 pull-request envelopes. This hosting-service classification
does not create a Git merge commit: the repository ancestry must still prove the local
fast-forward and complete single-parent candidate chain. An OPEN, CLOSED-without-merge,
different merge OID, null mergedAt, non-null auto-merge request, or manually invoked
`gh pr merge`/`gh pr close` result fails closed.

The remote v4 branch is retained at the exact final candidate; branch deletion is not a
closeout action, and `delete_branch_on_merge` remains false. Remote main, local main,
origin/main, local/remote candidate and committed
summary identities are exact; v1/v2/v3 refs and non-ancestry records remain protected;
PR #14 remains CLOSED without merge; retained v2 failed-run history obeys its retention
rule; P10 active and superseded identities remain exact; worktree and task-owned
temporary/Docker residue are zero; and local/remote tags, Releases, new package/image
versions, signatures, attestations, publication, and unauthorized remote mutations are
zero. Closeout records P12 v4 governance acceptance independently from the five Ubuntu
`not_proven` statuses and `linux_public_pilot_readiness = blocked`. It cannot start P13
or P20-L0.

## P12 v4 evidence, provenance, and claim boundary

The P12 provenance receipt records only non-self-referential inputs and coverage: exact
base and branch; acceptance source/commit/blob; 42-path allowlist and classifications;
canonical inventory semantics and counts; exact accepted historical objects and P8 Darwin
and P10 Darwin anchor identities; safe rejected/superseded v1/v2/v3 identities and
retention-bounded run summary; zero migrated
source files; zero parent-source reads; immutable migrations; and protected P10 identities.
It does not claim its own future blob, containing commit, implementation head/tree, dynamic
inventory blob, CI run or range digest.

The summary and evidence checker compute and bind the committed receipt blob; ordered
implementation/correction set; final implementation head/tree and range digest; exact
implementation-head workflow run/attempt; both numeric REST job IDs, job keys/names and
envelope digests; approved safe envelope projections; observed per-job environment;
portable manifest blob/file SHA/digest and 5/124/17/5/151 counts; all 151 individual
typed results, including 124 passed acceptance gates, five platform-qualified excluded
results, and five immutable embedded Darwin identities; P10
protection; zero residue/publication; and the three separate statuses.

The deterministic writer may write only artifacts/p12/summary.json after authorization. It
consumes completed local results, exact Git objects and an exact unexpired one-use receipt.
It does not invoke historical gates, retrieve Actions logs, call a live provider, mutate a
remote, publish, log in or alter credentials. The summary contains neither a full envelope
nor a complete Actions log. It retains only approved safe fields and each envelope
SHA-256.

The summary schema is exactly `digital-colleagues.p12-v4-summary.v1`. Its closed logical
top-level shape is:

~~~json
{
  "acceptance": {
    "blob": "<40 lowercase hex>",
    "commit": "<40 lowercase hex>",
    "file_sha256": "<64 lowercase hex>"
  },
  "base_commit": "c1562ea5201394d8a278f4b644daf4029cbb5bd4",
  "base_tree": "ae0f33263cfc7445fef69656ad9c5cb04d4a2d00",
  "ci_implementation_head": {
    "event": "pull_request",
    "head_sha": "<P12_FINAL_IMPLEMENTATION_HEAD>",
    "jobs": [
      {
        "envelope_sha256": "<64 lowercase hex>",
        "job_database_id": 1,
        "job_id": "current-ci",
        "job_name": "Current P12 governance non-publishing verification",
        "observed_environment": {
          "architecture": "<nonempty safe exact value>",
          "docker_compose_version": "<nonempty safe exact value>",
          "docker_server_version": "<nonempty safe exact value>",
          "node_version": "<nonempty safe exact value>",
          "npm_version": "<nonempty safe exact value>",
          "python_version": "<nonempty safe exact value>",
          "runner_image_os": "<nonempty safe exact value>",
          "runner_image_version": "<nonempty safe exact value>",
          "runner_os": "<nonempty safe exact value>"
        }
      },
      {
        "envelope_sha256": "<64 lowercase hex>",
        "job_database_id": 2,
        "job_id": "portable-history",
        "job_name": "Portable historical replay",
        "observed_environment": {
          "architecture": "<nonempty safe exact value>",
          "docker_compose_version": "<nonempty safe exact value>",
          "docker_server_version": "<nonempty safe exact value>",
          "node_version": "<nonempty safe exact value>",
          "npm_version": "<nonempty safe exact value>",
          "python_version": "<nonempty safe exact value>",
          "runner_image_os": "<nonempty safe exact value>",
          "runner_image_version": "<nonempty safe exact value>",
          "runner_os": "<nonempty safe exact value>"
        }
      }
    ],
    "pull_request_number": 1,
    "run_attempt": 1,
    "run_id": 1,
    "workflow_path": ".github/workflows/ci.yml"
  },
  "claim": "p12_v4_historical_platform_classification_candidate",
  "evidence_preflight_receipt_sha256": "<64 lowercase hex>",
  "implementation": {
    "head": "<40 lowercase hex>",
    "ordered_commits": ["<40 lowercase hex>"],
    "range_digest": "sha256:<64 lowercase hex>",
    "tree": "<40 lowercase hex>"
  },
  "inventory": {
    "blob": "<40 lowercase hex>",
    "digest": "sha256:<64 lowercase hex>",
    "evidence_anchor_count": 17,
    "excluded_acceptance_gate_count": 5,
    "excluded_gate_ids": [
      "p8_compose_runtime",
      "p8_golden_path",
      "p10_compose_runtime",
      "p10_quickstart",
      "p10_remote_distribution"
    ],
    "excluded_results": ["<five closed platform-result plus embedded-anchor objects>"],
    "included_acceptance_gate_count": 124,
    "item_results": ["<exactly 151 closed typed result objects in manifest order>"],
    "item_results_digest": "sha256:<64 lowercase hex>",
    "passed_acceptance_gate_count": 124,
    "path": "docs/p12/portable-historical-inventory.json",
    "setup_count": 5,
    "sha256": "<64 lowercase hex>",
    "skip_count": 0,
    "total_item_count": 151
  },
  "live_evidence": {
    "human_evaluation": "not_evaluated",
    "microsoft_365": "not_evaluated",
    "openai": "not_evaluated",
    "release": "not_evaluated",
    "soak": "not_evaluated"
  },
  "migration_count": 8,
  "p10_protected_identity_digest": "sha256:<64 lowercase hex>",
  "p12_current_p10_registry_protection": {
    "result_digest": "sha256:<64 lowercase hex>",
    "status": "passed"
  },
  "platform_status": {
    "linux_public_pilot_readiness": "blocked",
    "p12_governance_result": "passed",
    "ubuntu_historical_execution_status": "five_excluded_not_proven"
  },
  "publication_count": 0,
  "repository": "jeremyliu1220/digital-colleagues",
  "residue_count": 0,
  "schema": "digital-colleagues.p12-v4-summary.v1",
  "source_migration_count": 0,
  "test_counts": {
    "historical_python": 616,
    "p12_governance": 136
  }
}
~~~

The placeholder forms denote required dynamic values of the shown type, not unresolved
design choices. The `jobs`, `item_results`, and `excluded_results` arrays use their fixed
orders. Each job retains the complete safe nine-field observed-environment projection
from its exact Stage 12 envelope. Inventory path/blob/file SHA/digest bind the exact
committed manifest. `item_results` contains exactly the 151 closed typed result objects
defined by the envelope protocol, including five embedded anchors inside their five
excluded rows; `excluded_results` is the ordered safe projection of those same five rows
and does not add inventory items. `implementation.ordered_commits` is the complete range
from the acceptance-only commit through the exact final implementation/correction HEAD.
The
summary contains Stage 12 implementation-head CI only; Stage 16 final-candidate CI and
Stage 21 push-to-main CI occur later and are bound by independent acceptance and closeout
without rewriting the summary. Additional, missing, duplicate, renamed, reordered, or
future-result fields fail closed.

The public summary may claim only:

- exact fixed contract, topology, provenance and governance identities;
- complete P12 current static and synthetic_offline gates;
- the exact 151-item portable-historical inventory result on `ubuntu-24.04`;
- unchanged product/runtime/schema/migration behavior;
- P12 v4 governance gate status passed and governance acceptance pending independent
  acceptance;
- five immutable accepted P8/P10 Darwin historical results as Darwin-scoped identity anchors;
- all five corresponding Ubuntu historical evaluations `not_proven`;
- Linux Public Pilot readiness blocked;
- zero source migration, zero private/live data, zero cleanup residue and zero publication;
  and
- not_evaluated for live OpenAI, Microsoft 365, HUMAN evaluation, soak and release results.

It MUST NOT say or imply that any accepted P8/P10 excluded gate passed on Linux, Darwin evidence is cross-platform, Linux runtime compatibility is proven, Public Pilot is ready, any excluded gate passed, a setup/anchor was an executed gate, or a failed v2 run was successful. P12
governance acceptance may later become passed without changing any Ubuntu historical
status or Linux readiness.

P13-P19 mechanism gates may be accepted on their complete required deterministic,
synthetic and local evidence, but they carry the Linux portability risk and cannot claim
it closed. P20 begins with P20-L0 and cannot start later implementation, live E2E, soak,
release or publication preparation until that sub-gate passes. A Public Pilot claim also
remains blocked until every mandatory P20 private-live, recovery, HUMAN evaluation,
encrypted-storage, ten-deployment 72-hour soak and release criterion passes. No milestone
claims production readiness.

## Closed decisions and later authorization boundary

Every semantic, schema, runner, timeout, count, path, inventory, exclusion, anchor,
evidence-handoff, claim-boundary, and authorization-stage decision needed for P12 v4 is
fixed by this contract. Open decisions: none.

Dynamic commit, blob, run, job, environment, inventory-file, and receipt identities are
facts derived by the exact algorithms and stage oracles fixed here. They are not design
choices, unresolved placeholders, or authority delegated to implementation.

Canonical Stage 2 drafting authorizes no later stage. Each Stage 3–21 transition requires
new, explicit project-owner authorization. In particular, the following are not authorized
by this text: independent draft validation; WIP snapshot creation or verification; v4
branch/acceptance establishment; post-commit verification; WIP reuse review; governance
implementation or correction; local formal gates; candidate push/PR; either PR CI;
evidence preflight; evidence generation or summary commit; final-candidate push; either
form of acceptance; local merge; remote-main push; push-to-main CI; or remote closeout.

P13–P20 acceptance and implementation each require their own future contracts and
explicit starts. Migration 015, live provider access, HUMAN evaluation, tag, Release,
signing, attestation, package/image publication, public announcement, and every Linux or
Public Pilot readiness claim remain unauthorized. An implementation convenience may not
change a fixed contract, external behavior, authority boundary, migration, dependency,
path, count, evidence claim, or stage.

## Requirement coverage matrix

| Requirement | Normative coverage | Machine-checkable proof | Test and negative coverage | Final line references |
| --- | --- | --- | --- | --- |
| Exact Blueprint provenance and Stage 2-only boundary | Introduction and closed authorization boundary | Fixed 1183/223853/source SHA/blob identity; later stages forbidden | Blueprint-identity drift and implicit-authority rejection | Lines 3–34 and 3658–3682 |
| Exact accepted base and v4 direct lineage | Exact baseline, commit topology, Stage 6/7 oracles | Sole-parent/base-tree/count/non-ancestry assertions | Wrong base, parent, tree, path, mode, blob, or ancestor fails | Lines 249–342 and 3765–3844 |
| v1/v2/v3 immutable preservation and non-ancestry | Preserved attempts, exact baseline, lifecycle, post-commit oracle | Exact local/remote presence, objects, branch tips and merge-base checks | Ref movement/deletion, ancestry, relabeling, or rejected-blob binding fails | Lines 62–204, 249–278, 3334–3363 and 3735–3844 |
| Both rejected-v2 CI records and PR #14 | v2 identity/retention section and Stage 3/7/17/21 checks | Runs 34542709145 and 34564478590 with exact heads/attempt sets; CLOSED-without-merge three-null oracle | Added rerun, deletion, reclassification, wrong head, merged PR, or auto-merge fails | Lines 88–169, 3416–3471, 3735–3760 and 3787–3844 |
| Complete B+ P12–P20 order and product decisions | Architectural/data contracts, responsibility matrix, roadmap and E2E | Exact record vocabularies, owners, migration rows and ordered milestone titles | Renamed/expanded state, authority drift, phase swap, or capability overclaim fails | Lines 468–1660 |
| Core ProjectScope, continuation, waiting, goal, memory, trigger and authority contracts | Core records through bounded proactivity | Exact enum/set/field/owner markers and durable recovery digests | Running/paused project state, scope authority, lifecycle conflation, external approval, or trigger drift fails | Lines 468–948 |
| P14/P15/P17 and P14/P18/P19 responsibility boundaries | Responsibility matrix, milestone contracts and E2E | Exact source/binding/correlation/transport/authorization owner assertions | Raw correlation in P14/P15, missing P14 transport, P18 adapter fork, or P19 primitive fails | Lines 550–654, 1124–1396 and 1582–1660 |
| Parser-first P13 and migrations 001–014 | Parser-first chain and migration ownership | First parser-only commit/sub-gate; immutable 001–008 and exact 009–014 owners | Early 009/Gateway/dependency/API/Studio change or owner drift fails | Lines 1502–1581 |
| 129 accepted gates and independent 124/5 set oracle | Appendix A audit and Appendix B completeness oracle | 129 unique exact rows; independent accepted set equals disjoint 124 plus 5 | Missing/extra/overlap/self-derived membership or sixth exclusion fails | Lines 2815–3068 |
| Exact five Ubuntu exclusions and no sixth | Change Decision, audit rows, inventory rows and set difference | Ordered IDs and exact excluded dispositions at both independent layers | Pass/skip/waiver/replacement, missing/reordered/extra ID, or recursive re-entry fails | Lines 205–248, 2842–3224 |
| Complete 151 typed items and 5/124/17/5/151 | Appendix B count object and row table | Sequential unique 151 rows and exact type cardinalities | 156/22 counts, retyping, duplicate, missing or extra item fails | Lines 2986–3224 |
| Five platform-qualified excluded results | Vocabulary, envelope closed shape and Appendix C | Per-gate Ubuntu not_proven/excluded/blocked plus Darwin passed anchor | Missing qualifier, cross-platform merge, promotion, or back-write fails | Lines 35–61, 1808–2075 and 3225–3288 |
| Five embedded Darwin composite anchors | Envelope schema, excluded inventory rows and Appendix C | Exact source object/path/blob/file SHA/selection/bytes/digest for each gate | Wrong source/selection/key/bytes/digest, duplicate anchor, or inventory-count inflation fails | Lines 1974–2032, 3069–3288 |
| P10 remote exact two-selected-subresults mapping | Appendix C construction | Outer gate_id with result keys only `distribution` and `quickstart`; 2538 bytes and exact SHA | Source-key leakage, complete-return substitution, wrong outer key, or digest drift fails | Lines 3254–3280 |
| 19 gate-level null, 110 non-null and inventory 41 null entrypoints | Appendix A entrypoint rules/rows and Appendix B counts/rows | Exact command kind, command/operation, nullable path/mode/blob/callable and Git-object checks | Fabricated blob, forbidden null/non-null, wrong mode/callable, or current-tree shadowing fails | Lines 2817–2985 and 2988–3224 |
| ubuntu-24.04, per-object isolation, timeouts and cleanup | CI runner/executor contract and Appendix B executor model | One checkout/environment/workspace per object; 9900-second hard deadline; zero residue | ubuntu-latest/self-hosted, cross-object state, recursive aggregate, retry or unbounded wait fails | Lines 1661–1807 and 3046–3068 |
| Exactly 616 historical Python tests | Test strategy and portable envelope semantics | 308+32+39+101+100+36 with zero failures/errors/skips | Count substitution, excluded-leaf miscount, suppression, or incomplete suite fails | Lines 1993–2007 and 2099–2121 |
| Exactly two required PR jobs | Canonical workflow and P12 exit | Exact job keys/names/actions/runner/timeouts and two envelopes | Missing/duplicate/matrix-expanded job, mutable action, wrong name or extra required job fails | Lines 979–1064 and 1688–1738 |
| PR and push envelope marker/schema/canonicalization/identity | CI result-envelope protocol and read-only retrieval | One marker per required job; 32,768-byte P12-CJ-1 payload; payload/Git/runner/REST cross-binding | Forged/duplicate/truncated/noncanonical/digest-mismatched/wrong-event/job/run/attempt/head/base fails | Lines 1808–2075, 2299–2410 and 3416–3445 |
| P12-owned registry protection only in preflight | CI placeholder, Stage 13 result and protected P10 section | CI value fixed not_evaluated/evidence_preflight_only; authenticated result has distinct schema/name | Registry result impersonating p10_remote_distribution or any CI registry claim fails | Lines 1948–2051, 2354–2436 and 2678–2814 |
| One-use receipt closed schema and handoff | Evidence preflight and Stage 13–14 boundary | Exact jobs/environments, manifest identities, five results, counts, nonce, expiry, zero residue/publication | Missing/extra/reordered field, wrong head/run/receipt, reuse, expiry, or dirty state fails | Lines 2283–2677 |
| Summary-only tip and complete 151-result evidence | Commit/evidence topology and closed summary schema | Summary alone changes final path; binds full commit range, Stage 12 envelopes, manifest and 151 ordered results | Missing result, receipt/range mismatch, future-run field, post-summary commit, or overclaim fails | Lines 279–342 and 3472–3657 |
| Two exact-head PR CIs | P12 roadmap, lifecycle and evidence topology | Stage 12 implementation-head and Stage 16 final-candidate runs each require both exact envelopes | Ancestor/recreated tree/merge-ref/latest-run substitution or missing job fails | Lines 997–1042, 3334–3363 and 3472–3657 |
| Three independent status dimensions and Linux readiness blocked | Change Decision, Appendix C and claim boundary | Governance may pass; five Ubuntu statuses remain not_proven; Linux readiness remains blocked | Status laundering, coupled status update, Linux/Pilot overclaim, or Darwin promotion fails | Lines 205–248, 3225–3288 and 3472–3657 |
| P20-L0 sole future owner | Carry-forward rule and exact P20 contract | P20-L0 first blocking sub-gate covers five forward equivalents while accepted P8/P10 stay immutable | P13–P19 owner drift, order change, root/chmod workaround, or premature readiness fails | Lines 951–978 and 1397–1501 |
| Exact 42-path allowlist and phase write ownership | Commit topology and exact allowlist | One acceptance, 40 implementation/correction and one summary path; 1/41/42 path counts | Extra/missing path, wrong phase, acceptance edit, early summary, runtime/schema/dependency change fails | Lines 279–393 |
| Content-bearing snapshot and independent saved-byte verification | Protected WIP lifecycle and Appendix D | Exact 40 payload bytes, canonical manifest/checksum/framed digest and Stage 5 saved-byte rehash | Metadata-only/worktree-only verification, unsafe path, symlink, altered payload or digest drift fails | Lines 394–467 and 3289–3333 |
| Per-file reuse and five-condition cleanup barrier | Protected WIP lifecycle and Stages 8–10 | 40 dispositions bound to verified snapshot; all five cleanup predicates required | Bulk reuse, missing disposition, premature stash/reset/clean/switch/delete or snapshot-only cleanup fails | Lines 394–467 and 3334–3363 |
| Exact unique 21-stage lifecycle | Canonical authorization lifecycle | Unique ordered stage numbers/names; explicit owner authority per transition | Missing/combined/renamed/reordered stage or implicit next-stage authority fails | Lines 3334–3363 |
| Separate final acceptance, local FF merge, remote push and closeout | Stages 17–21 and detailed Stage 19–21 oracles | Stage 19 local ff only; Stage 20 one main refspec; Stage 21 exact push run/jobs/envelopes | Merge commit/force/additional ref, candidate-push substitution, premature push envelope or combined authority fails | Lines 3334–3471 |
| Exact Stage 19–21 PR/branch closeout | Detailed closeout oracles | GitHub indirect MERGED state, exact final-candidate merge OID, null auto-merge and retained v4 branch | OPEN/closed-unmerged/wrong merge OID, auto-merge, deleted branch or failed smoke fails | Lines 3364–3471 |
| Exact 136 unittest method IDs and negative coverage | Governance test inventory and required negative cases | 136 unique fully qualified method IDs with fixed class counts and expanded subtests | Any ID/count drift or omitted platform/inventory/envelope/WIP/lifecycle negative fails | Lines 2099–2282 |
| Complete protected P10 Git/runs/GHCR inventories | P10 protected publication identity | Exact subjects, commits/blobs, nine runs, active/superseded digests and two 14-version/four-tag inventories | Overwrite/retag/republish/delete/lifecycle/inventory drift or unreadable identity fails | Lines 2678–2814 |
| Zero publication and fail-closed boundary | Workflow, preflight, claim, lifecycle and closeout oracles | contents:read, no secret/OIDC/write/artifact transport, zero tags/Releases/package changes/residue | Retry-as-correctness, ignored exit, manual evidence, publication or unsafe fallback fails | Lines 1661–2075, 2283–2814 and 3334–3682 |
| Stage 3 pre-commit and Stage 7 post-commit checks | Acceptance-establishment oracles | Exact external identity, dirty-WIP preservation, acceptance subject/mode/blob/parent/path and remote absence | Any state/identity/count/whitespace/path/ref/run/P10 mismatch stops before next stage | Lines 3723–3844 |

## Acceptance-contract drafting, pre-commit, and post-commit oracles

### Stage 2 author self-check

Draft production MUST verify this document has every required heading; 129 sequential
unique audit rows; 151 sequential unique inventory rows; exact 5/124/17/5/151 types;
exactly five ordered exclusions; five distinct embedded anchors; 42 unique allowlisted
paths; 40 WIP rows; 136 unique unittest method IDs; 21 unique stages in order; paired
Markdown fences; structurally consistent tables; zero trailing ASCII space/tab; no private
absolute path; no conversation dependency; and no unresolved drafting placeholder or decision.
This author self-check is not Stage 3 independent validation and cannot authorize Stage 4.

### Stage 3 independent acceptance-draft pre-commit oracle

Stage 3 is separately authorized and entirely read-only. The independent reviewer MUST:

1. bind the separately reported line count, byte count, SHA-256, and prospective Git blob
   of the exact external draft and independently repeat the Stage 2 structural checks;
2. verify the approved Blueprint source identity fixed in the introduction;
3. verify the primary worktree remains on v3 HEAD
   `e31bc733cbdd333648f2ce1c52ac9fe1fad83179`, tree
   `1cdce2a41f84ee4243d04be781ad187eb5f5fab9`, with acceptance blob
   `40c93a2aa8930c71e14fefac2053a10ed137af58`;
4. verify the exact Appendix D 40-path WIP: 20 tracked modified, 20 untracked, zero
   staged, zero ignored, and framed SHA-256
   `79816a61e89f86b27f876986f1c06de50ee6d1c72caa95989ae5447c584059f1`;
5. verify v1/v2/v3 refs and objects exactly, local/remote v4 refs and v4 PR absent, and
   v1/v2/v3 non-ancestry relative to the accepted base sibling topology;
6. verify local main, origin/main, and GitHub main are the exact accepted base;
7. verify the v2 remote branch remains at its exact head and PR #14 is CLOSED with exact
   base/head and `mergedAt`, `mergeCommit`, and `autoMergeRequest` all null;
8. if retained, verify run `34542709145` has exactly attempt 1 at head
   `fc145550b750c172899bc1497ff5fede387c07dc` and run `34564478590` has exactly
   attempts 1 and 2 at head `8e08c3891dc8f761ada096c3f829ef31d3fbfd7c`; all three named
   attempts remain completed/failure, with no additional attempt or reclassification;
9. verify summary absent, local/remote tags and Releases zero, no v3/v4 remote branch or
   PR, and no unauthorized publication; and
10. execute the complete read-only P10 Git/run/GHCR identity oracle.

Stage 3 MUST NOT create the Stage 4 snapshot, touch the WIP, create a Git worktree, branch,
commit, ref, PR, run, evidence, or remote state. A mismatch stops the lifecycle.

### Stage 6 acceptance-only establishment oracle

Stage 6 may begin only after separately authorized Stage 4 created the content-bearing
snapshot, Stage 5 independently verified it from saved bytes, and the owner separately
authorized Stage 6 against the exact Stage 3-approved draft identity. Stage 6 MUST:

1. leave the dirty v3 primary worktree completely untouched;
2. create one mode-0700 OS-temporary directory and an independent Git worktree at the
   exact accepted base;
3. create `codex/p12-public-pilot-continuity-rebaseline-v4` directly from that base only
   after confirming local/remote v4 branch and PR absence;
4. install the owner-approved external draft byte-identically as
   `docs/p12/acceptance.md`;
5. verify `cmp`, line/byte counts, SHA-256, prospective blob, mode 100644, and
   `git diff --cached --check` before commit;
6. stage only `docs/p12/acceptance.md`; and
7. create one ordinary single-parent commit with message
   `docs: establish P12 v4 acceptance contract`.

It MUST NOT import a WIP byte, switch the primary worktree, or perform any push, PR, CI,
evidence, summary, tag, Release, publication, cleanup, or Stage 8 review.

### Stage 7 independent post-commit oracle

With `P12_V4_ACCEPTANCE_COMMIT`, `P12_V4_ACCEPTANCE_BLOB`, and the externally reviewed
draft identity supplied by the Stage 6 report, Stage 7 independently requires:

~~~sh
set -e
test "$(git symbolic-ref --quiet --short HEAD)" = "codex/p12-public-pilot-continuity-rebaseline-v4"
test "$(git rev-parse HEAD)" = "$P12_V4_ACCEPTANCE_COMMIT"
test "$(git rev-list --parents -n 1 HEAD | awk '{print NF}')" = "2"
test "$(git rev-parse HEAD^)" = "c1562ea5201394d8a278f4b644daf4029cbb5bd4"
test "$(git show -s --format=%T HEAD^)" = "ae0f33263cfc7445fef69656ad9c5cb04d4a2d00"
test "$(git rev-list --count c1562ea5201394d8a278f4b644daf4029cbb5bd4..HEAD)" = "1"
test "$(git show -s --format=%s HEAD)" = "docs: establish P12 v4 acceptance contract"
test "$(git diff-tree --no-commit-id --name-status -r HEAD)" = "$(printf 'A\tdocs/p12/acceptance.md')"
test "$(git rev-parse HEAD:docs/p12/acceptance.md)" = "$P12_V4_ACCEPTANCE_BLOB"
test "$(git ls-tree HEAD docs/p12/acceptance.md | awk '{print $1\" \"$2\" \"$3}')" = "100644 blob $P12_V4_ACCEPTANCE_BLOB"
git diff --check HEAD^ HEAD
worktree_state="$(git status --porcelain=v2 --untracked-files=all --ignored=matching)" || exit $?
test -z "$worktree_state"
test ! -e artifacts/p12/summary.json
test "$(git rev-parse refs/heads/codex/p12-public-pilot-continuity-rebaseline)" = "8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3"
test "$(git rev-parse refs/heads/codex/p12-public-pilot-continuity-rebaseline-v2)" = "8e08c3891dc8f761ada096c3f829ef31d3fbfd7c"
test "$(git rev-parse refs/heads/codex/p12-public-pilot-continuity-rebaseline-v3)" = "e31bc733cbdd333648f2ce1c52ac9fe1fad83179"
if git merge-base --is-ancestor 8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3 "$P12_V4_ACCEPTANCE_COMMIT"; then exit 1; fi
if git merge-base --is-ancestor 8e08c3891dc8f761ada096c3f829ef31d3fbfd7c "$P12_V4_ACCEPTANCE_COMMIT"; then exit 1; fi
if git merge-base --is-ancestor e31bc733cbdd333648f2ce1c52ac9fe1fad83179 "$P12_V4_ACCEPTANCE_COMMIT"; then exit 1; fi
test "$(git rev-parse main)" = "c1562ea5201394d8a278f4b644daf4029cbb5bd4"
test "$(git rev-parse origin/main)" = "c1562ea5201394d8a278f4b644daf4029cbb5bd4"
test "$(git ls-remote --heads origin refs/heads/main | awk '{print $1}')" = "c1562ea5201394d8a278f4b644daf4029cbb5bd4"
remote_v1="$(git ls-remote --heads origin refs/heads/codex/p12-public-pilot-continuity-rebaseline)" || exit $?
test -z "$remote_v1"
test "$(git ls-remote --heads origin refs/heads/codex/p12-public-pilot-continuity-rebaseline-v2 | awk '{print $1}')" = "8e08c3891dc8f761ada096c3f829ef31d3fbfd7c"
remote_v3="$(git ls-remote --heads origin refs/heads/codex/p12-public-pilot-continuity-rebaseline-v3)" || exit $?
test -z "$remote_v3"
remote_v4="$(git ls-remote --heads origin refs/heads/codex/p12-public-pilot-continuity-rebaseline-v4)" || exit $?
test -z "$remote_v4"
test "$(gh pr list --repo jeremyliu1220/digital-colleagues --state all --head codex/p12-public-pilot-continuity-rebaseline-v4 --json number --jq 'length')" = "0"
local_tags="$(git tag --list)" || exit $?
test -z "$local_tags"
remote_tags="$(git ls-remote --tags origin)" || exit $?
test -z "$remote_tags"
test "$(gh release list --repo jeremyliu1220/digital-colleagues --limit 100 --json tagName --jq 'length')" = "0"
replace_refs="$(git replace -l)" || exit $?
test -z "$replace_refs"
~~~

The reviewer separately proves committed bytes equal the exact approved external draft,
checks the primary dirty v3 worktree and verified snapshot against Appendix D and the
framed digest, checks the field-complete CLOSED-without-merge PR #14 JSON, and reads the
retention-aware exact run endpoints. If retained, run 34542709145 must expose only attempt
1 at its fixed head, while run 34564478590 must expose only attempts 1 and 2 at its fixed
head; all remain completed/failure without reclassification. The reviewer also verifies
every protected P10 identity. Remote v4
branch/PR, summary, tags, Releases, publication, and repository residue remain absent.

Stage 7 success establishes only the immutable acceptance commit. It does not authorize
Stage 8 WIP review or any later stage.
