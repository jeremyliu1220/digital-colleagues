<!-- SPDX-License-Identifier: Apache-2.0 -->

# P12 v4 Historical Platform Classification Rebaseline Checklist

This checklist is a review aid. `docs/p12/acceptance.md` is the immutable authority.

## Identity and topology

- [ ] Base is `c1562ea5201394d8a278f4b644daf4029cbb5bd4` with tree
  `ae0f33263cfc7445fef69656ad9c5cb04d4a2d00`.
- [ ] Branch is exactly `codex/p12-public-pilot-continuity-rebaseline-v4` and acceptance
  commit is `dbdb75b6afcd226059484ec536fec82532eb3613`, with sole parent equal to the base,
  tree `f8d0dad5c04253eefd24353f8c9afd965cf0d6ea`, and acceptance blob
  `b574bb350a83a36f9ad7f521514c7d58e97393d9`.
- [ ] `docs/p12/acceptance.md` remains 3844 lines, 382481 bytes, and SHA-256
  `f0159ea7d164a2b57c61d62e339798ea4ea568880934b571119c67ee781c2d45`.
- [ ] The rejected v1 ref remains `8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3`
  and the rejected v2 local/remote ref remains
  `8e08c3891dc8f761ada096c3f829ef31d3fbfd7c`. The superseded, not rejected, v3
  acceptance-only ref remains `e31bc733cbdd333648f2ce1c52ac9fe1fad83179`. All three
  remain immutable non-ancestors of every v4 commit.
- [ ] PR #14 is CLOSED at the exact accepted-base/v2-head identity with `mergedAt`,
  `mergeCommit`, and `autoMergeRequest` all null; its branch and two failed run attempts
  remain protected under the retention-aware oracle.
- [ ] Acceptance is byte-identical; implementation never creates or edits the summary.
- [ ] The implementation-head changed path set is exactly acceptance plus all 40
  implementation paths: 41 paths total. The final summary path is absent.
- [ ] All implementation commits are linear, single-parent, allowlisted, and nonempty.
- [ ] No amend, rebase, squash, reset, merge commit, or force rewrite occurred.
- [ ] The local checked-out v4 branch remains exact; the remote v4 branch and v4 PR remain
  absent until separately authorized. The protected dirty v3 WIP and its external snapshot
  remain unchanged. `main`, `origin/main`, GitHub main, tags, Releases, and protected P10
  identities do not drift.

## B+ contract coverage

- [ ] Roadmap order is exactly P12, P13, P14, P15, P16, P17, P18, P19, P20.
- [ ] ProjectScope is exactly deployment Namespace plus `project_id` and carries no authority.
- [ ] ProjectContinuationState is exactly `active`, `waiting`, `needs_human`, `completed`,
  and `stopped`; only the final two are terminal.
- [ ] WaitingCondition exact kinds/statuses, ANY/ALL, deadline, and once-only consumption
  are fixed; external replies never satisfy `human_decision`.
- [ ] GoalBinding has HUMAN objective digest, criteria, bounds, expiry, exact Mandate/Policy,
  namespace, and causality; no proactive trigger exists before P18.
- [ ] Memory admission is exactly `admit`/`reject`; later lifecycle is separate and memory
  never becomes HUMAN approval or authority.
- [ ] MemoryRecord has five exact lifecycle states and correction creates a new immutable
  version; MemoryRetrievalSet has complete bounded identity/digest fields.
- [ ] TriggerCorrelation has five exact states; ambiguity quarantines and only matched can
  be consumed once.
- [ ] P14/P15/P17 ingestion, binding, polling, correlation, wake, and recovery ownership is
  mechanically distinct.
- [ ] P14 owns the three HUMAN-approved Microsoft write transports; SharePoint is read-only.
- [ ] P18 alone adds AutomaticEffectAuthorization and reuses P14 transport machinery.
- [ ] P19 is composition-only and fails when a required transport is absent.
- [ ] Mandatory checkpoint boundaries and new-process empty-chat recovery are complete.
- [ ] RecoveryScanCheckpoint is optimization, never authoritative recovery truth.
- [ ] P13 parser-first ancestry blocks migration 009/Gateway/dependency/API/Studio work.
- [ ] Migrations 001-008 are immutable and 009-014 have exactly one owner each.

## CI, evidence, and claim boundary

- [ ] Exactly 136 P12 test IDs pass with no failure, error, skip, xfail, unexpected
  success, suppression, or substitution.
- [ ] The accepted-gate universe is independently derived as exactly 129 identities: 124
  included plus 5 excluded; it is not inferred from the inventory classification under test.
- [ ] The canonical historical inventory has exactly 151 ordered items: 5 setup, 124
  included acceptance gates, 17 evidence anchors, and 5 excluded acceptance gates.
- [ ] `excluded_gate_ids` is exactly the ordered array `p8_compose_runtime`,
  `p8_golden_path`, `p10_compose_runtime`, `p10_quickstart`, and
  `p10_remote_distribution`.
- [ ] Gate-level entrypoints are exactly 19 null and 110 non-null; all 151 inventory rows
  contain exactly 41 null entrypoints.
- [ ] Each excluded row returns `not_run_platform_excluded` with null exit status and embeds
  its own independent immutable Darwin `passed` identity-only anchor; the five anchors do
  not increase the 151-item count.
- [ ] Exact P8, P9, P10, P11, and P11R objects use separate checkouts, at most one locked
  Python environment and required npm workspace per object, module paths, Docker projects,
  writable state, and bounded cleanup; P9 has no npm workspace.
- [ ] No recursive historical aggregate reintroduces any of the five excluded P8/P10
  gates.
- [ ] Portable replay reports exactly 616 historical Python tests; current governance
  reports exactly 136 unique P12 test IDs.
- [ ] Current workflow has only pull requests to main and pushes to main, `contents: read`,
  exactly nine immutable action invocations, exact-head checkout, and no publication path.
- [ ] Both required PR jobs use `ubuntu-24.04`, have exact names/timeouts, and emit exactly
  one canonical P12-CJ-1 envelope with marker, SHA-256, size, event-payload, Git, standard
  runner-input, observed-environment, and attempt-specific REST identity cross-checks.
- [ ] Public-boundary, provenance, migration, rebaseline, CI-policy, and repository checks pass.
- [ ] P10 active and superseded identities remain exactly readable and immutable.
- [ ] Local/remote tags and Releases are zero; no package/image/signature/attestation/publication occurs.
- [ ] P12 governance result, the five Ubuntu historical statuses (`not_proven`), and Linux
  Public Pilot readiness (`blocked`) remain three independent status dimensions.
- [ ] P20-L0 is the first and only blocking P20 portability sub-gate and P13-P19 cannot
  claim it passed.
- [ ] Evidence preflight has not run before its separate authorization.
- [ ] `artifacts/p12/summary.json` is absent before evidence authorization.
- [ ] Public output claims only P12 `static`/`synthetic_offline` governance and
  `portable_historical` verification results; all provider, private-live, HUMAN, soak,
  release, and Public Pilot results are `not_evaluated`.

## Canonical authorization lifecycle

The following 21 stages are distinct, ordered, and separately authorized; no row may be
combined with another or treated as implied by completion of its predecessor:

1. Blueprint owner review.
2. Repository-external v4 acceptance drafting.
3. Independent acceptance-draft pre-commit validation.
4. Content-bearing repository-external WIP snapshot.
5. Independent WIP snapshot verification.
6. v4 branch and acceptance-only commit in an independent temporary Git worktree.
7. Independent post-commit verification.
8. Per-file read-only WIP reuse review.
9. Governance implementation authorization and linear allowlisted commits.
10. Local formal gates.
11. Candidate push and PR authorization.
12. Exact implementation-head PR CI.
13. Evidence-preflight authorization.
14. Evidence-generation and summary-only commit authorization.
15. Final-candidate push / PR update authorization.
16. Exact final-candidate CI.
17. Independent acceptance.
18. Project-owner final acceptance.
19. Local fast-forward-only merge authorization.
20. Remote main push authorization.
21. Exact push-to-main CI envelope and remote closeout verification.

## Implementation-head commands

```bash
PYTHONDONTWRITEBYTECODE=1 make p12-test
PYTHONDONTWRITEBYTECODE=1 make p12-current-ci
PYTHONDONTWRITEBYTECODE=1 make p12-portable-history
PYTHONDONTWRITEBYTECODE=1 make p12-implementation-check
PYTHONDONTWRITEBYTECODE=1 make p12-ci
PYTHONDONTWRITEBYTECODE=1 make ci
```

Run each formal command at most once, in this order, only after the complete implementation
is committed and the repository is clean. A failure stops immediately: do not modify the
implementation, add a correction commit, or continue the sequence without new scoped
authorization. These commands authorize no evidence generation, push, pull request, merge,
tag, Release, publication, P13 work, or independent acceptance.
