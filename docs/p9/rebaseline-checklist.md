<!-- SPDX-License-Identifier: Apache-2.0 -->

# P9 Productization Rebaseline Checklist

Status: development checklist. Completion supports only **P9 development complete,
awaiting independent acceptance**. An independent acceptance task, scoped correction if
needed, final acceptance, fast-forward merge, and main verification remain required.

## Fixed contract and history

- [ ] Branch is `codex/p9-productization-rebaseline` from exact base
  `b093a4fa54bf30cef838c72222d1ae63c4eab9d9` with accepted P8 ancestor
  `0bb80ab187932fbad42fbf665b8310987609a1f5`.
- [ ] `docs/p9/acceptance.md` is the isolated first P9 commit and is byte-identical to
  `597403bc151da75499acea5bb00ee298e7e5a005`.
- [ ] P0-P8 acceptance, artifacts, evidence, receipts, fingerprints, and migrations are
  unchanged; migrations remain 001-007 and migration 008 is absent.
- [ ] The base-to-candidate changed-path set exactly equals the acceptance allowlist.
- [ ] Runtime, Studio, Compose, Dockerfiles, dependency/lock/version metadata, API/worker,
  operations, adapters, and SQLite schema have zero changes.

## Product and architecture

- [ ] v0.2 is consistently described as a Public Pilot plan; executable `0.1.0` remains
  an unpublished local reference candidate.
- [ ] AgentPackage, ColleagueDeployment, ExternalConnection, ConnectorGrant,
  AutomaticEffectAuthorization, SourceReference, and SourceCursor are defined exactly.
- [ ] AgentPackage is declarative and non-executable, cannot self-grant or self-activate,
  and is distinct from S4 Skill.
- [ ] External source context is temporary and distinct from S1 Semantic Memory.
- [ ] Ten deployments remain isolated and do not imply S3 shared knowledge or Agent
  collaboration.
- [ ] Package and external-event data flows fail closed on unknown/missing/stale/revoked,
  namespace/Agent mismatch, digest/schema mismatch, unbound resource, ambiguous authority,
  or budget overflow.
- [ ] `zh-TW`/`en-US`, legacy deployment migration, package upgrade/rollback, connector
  revocation, stable `/api/v1`, and retained `/p5`/`/p6` compatibility are fixed.
- [ ] Interface transition inventory assigns current Studio/runtime/API milestone residue
  to P10 without editing those files.

## Providers and effects

- [ ] External register contains only official OpenAI, Microsoft Learn, GitHub Docs, or
  Sigstore documentation with checked-at UTC, observed contract, owner, and evidence.
- [ ] `gpt-5.5`, Responses API, Structured Outputs, `store:false`, no tools, server
  authority reconstruction, budgets, errors, injection handling, and provenance are fixed.
- [ ] Per-Agent work/school identity, project multi-tenant and BYO single-tenant public
  clients, delegated device code, consent modes, mail delta, Teams polling, Planner ETag,
  SharePoint selected read-only, errors/retry/reconciliation/cursors are fixed.
- [ ] AutomaticEffectAuthorization is separate from HumanApprovalDecision and the
  auto/approval/deny decision table is complete.
- [ ] Self-reply, Agent loops, duplicate message/effect, replay, flooding, and prominent
  third-party delete permission are assigned to later gates.

## Secrets, privacy, and live evidence

- [ ] FileVault, `0700` secret directory, `0600` credential files, read-only mounts, and
  encrypted Linux volume rules are present.
- [ ] Keys/tokens are forbidden from environment, SQLite, audit, backup, diagnostics,
  logs, errors, command arguments, and public evidence.
- [ ] External body size, redaction, discard timing, and crash cleanup are defined.
- [ ] Evidence classes are limited to `static`, `synthetic_offline`, `loopback`,
  `live_private`, `human_evaluation`, and `not_evaluated`.
- [ ] OpenAI live, Microsoft 365 live, and human evaluation are `not_evaluated` at P9.
- [ ] P15 requires two M365 tenants, ten Agent accounts, an OpenAI project, both Entra App
  modes, user/Admin consent tests, real Outlook/Teams/Planner/SharePoint data, and private
  live storage; mock/stub/loopback cannot substitute.

## Gates and evidence

- [ ] P8 continuation protects accepted P8 bytes/provenance while allowing exactly the P9
  path set and rejecting rename/copy/type/dirty/incomplete bypasses.
- [ ] P9 repository, provenance, and rebaseline gates plus negative/abuse tests pass.
- [ ] `make p9-check` and `make check` run the retained P8 toolchain followed by P9 gates
  through the hash-locked temporary toolchain; no historical evidence writer runs.
- [ ] Test outcomes have positive counts and zero failures, errors, skips, expected
  failures, unexpected successes, boundary exceptions, drift, runtime changes, or residue.
- [ ] Implementation is committed and tree clean before `make evidence-p9`.
- [ ] `artifacts/p9/summary.json` is committed alone, contains only the scoped candidate
  claim, and final gates pass with a clean tree.

## Prohibited completion actions

- [ ] No merge, rebase, squash, amend, push, tag, publish, upload, Release, remote change,
  or P10-P15 work was performed.
- [ ] Final report says only P9 development complete and awaiting independent acceptance.
