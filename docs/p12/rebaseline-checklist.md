<!-- SPDX-License-Identifier: Apache-2.0 -->

# P12 Public Pilot Continuity Rebaseline Checklist

This checklist is a review aid. `docs/p12/acceptance.md` is the immutable authority.

## Identity and topology

- [ ] Base is `c1562ea5201394d8a278f4b644daf4029cbb5bd4` with tree
  `ae0f33263cfc7445fef69656ad9c5cb04d4a2d00`.
- [ ] Acceptance commit is `3639fa08ca44820bb922e0644095c9fb9c24d3e6` and blob is
  `50453e154cf642bc7b90644660e1d956b04f966a`.
- [ ] The rejected v1 ref remains `8cd9aefe5422fd60cd6bd2724ad993528e3cd4a3`
  and is not an ancestor of the v2 candidate.
- [ ] Acceptance is byte-identical; implementation never creates or edits the summary.
- [ ] The changed path set is exactly acceptance plus all 37 implementation paths.
- [ ] All implementation commits are linear, single-parent, allowlisted, and nonempty.
- [ ] No amend, rebase, squash, reset, merge commit, or force rewrite occurred.

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

- [ ] `make p12-test`, `make p12-implementation-check`, `make p12-ci`, and `make ci` pass
  on the clean exact implementation head.
- [ ] Current workflow has only pull requests to main and pushes to main, `contents: read`,
  immutable action pins, exact-head checkout, and no publication path.
- [ ] Accepted P11R is replayed only in an OS-temporary exact-object checkout.
- [ ] Public-boundary, provenance, migration, rebaseline, CI-policy, and repository checks pass.
- [ ] P10 active and superseded identities remain exactly readable and immutable.
- [ ] Local/remote tags and Releases are zero; no package/image/signature/attestation/publication occurs.
- [ ] Evidence preflight has not run before its separate authorization.
- [ ] `artifacts/p12/summary.json` is absent before evidence authorization.
- [ ] Public output claims only P12 `static`/`synthetic_offline` governance results; all
  provider, private-live, HUMAN, soak, release, and Public Pilot results are `not_evaluated`.

## Implementation-head commands

```bash
make p12-test
make p12-ci
make ci
make p12-implementation-check
python3 -B scripts/check_public_boundary.py .
git diff --check 3639fa08ca44820bb922e0644095c9fb9c24d3e6..HEAD
git status --porcelain=v2 --untracked-files=all
```

These commands authorize no evidence generation, push, pull request, merge, tag, Release,
publication, P13 work, or independent acceptance.
