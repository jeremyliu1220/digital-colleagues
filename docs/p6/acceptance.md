<!-- SPDX-License-Identifier: Apache-2.0 -->

# P6 Governance Hardening Acceptance Contract

Status: fixed development contract. P6 may be described only as **development complete,
awaiting independent acceptance** after every gate below passes. This contract is fixed
before product, migration, API, Studio, or Compose implementation and must not be deleted,
weakened, or rewritten to fit an implementation result.

## Baseline, branch, and historical boundary

P6 starts from the accepted P5 `main` baseline
`f1dff72c3fb15b2fc7b3c7d989aa85e275cb31ac` on
`codex/p6-governance-hardening`. The fixed base must be an ancestor of the implementation
and evidence commits. P5 accepted implementation, evidence, and its post-merge repository
Gate hotfix remain in that ancestry.

P0-P5 acceptance records, Golden Paths, artifacts, evidence, receipts, fingerprints, and
migrations 001-006 remain unchanged. P6 must not rerun historical evidence collectors.
The general P6 repository Gate is ancestry- and content-based: it must pass on the P6
development branch, a later fast-forward `main`, and normal descendants. Only the P6
evidence collector requires the exact development branch and fixed base.

P6 adds local multi-user governance hardening: centralized typed RBAC, versioned
membership and session bindings, enrollment, operator recovery, authority-change approval,
approval expiry and revalidation, systematic namespace refusal, bounded audit export,
Studio governance views, additive migration 007, abuse cases, and synthetic/offline
evidence. It adds no provider, enterprise identity, production tenancy, memory, Skill,
shared-knowledge, collaboration, P7, or P8 feature.

## Architecture and authority invariants

The dependency direction remains:

```text
Pure core <- application and governance -> stable ports
                                   <- intelligence adapters
                                   <- infrastructure and HTTP adapters
```

- Pure core uses frozen standard-library dataclasses, Enums, and Protocols. FastAPI,
  Pydantic, SQLite, provider/channel SDKs, ORMs, orchestration frameworks, ambient time,
  entropy, identifiers, configuration, filesystem, process, and network access remain
  outside deterministic core and application policy.
- Pydantic remains confined to HTTP mapping in `api/`. Stores remain behind stable ports.
- Every persisted P6 record carries schema version, complete namespace, stable explicit
  ID, timezone-aware UTC times serialized with `Z`, revision/concurrency state, actor, and
  safe causal bindings.
- HUMAN, MODEL, and SERVICE principals are durable disjoint kinds. Only HUMAN principals
  can have canonical human roles. Kind conversion is forbidden.
- Profile, memory, Skill, model output, work history, and Studio state never grant
  authority. Mandate grants colleague authority; ColleaguePolicy narrows runtime
  governance; centralized RBAC and versioned membership constrain the caller.
- Request bodies never submit authoritative tenant, namespace, principal kind, principal
  ID, role, membership revision, session binding, server time, lifecycle state, generated
  ID, trusted digest, or consumed state.
- UI visibility is not authorization. Every endpoint, application service, and store
  mutation/list/read/export path rechecks action, kind, role, complete namespace, and
  current revision on the server.

## Typed RBAC action matrix

Authorization uses a single typed action enumeration and one explicit matrix. An
action-specific service may further narrow access; it may never broaden this matrix.
`tenant_admin` has tenant governance authority only inside the configured local tenant.
`colleague_user` and `auditor` require a current membership for the exact colleague
namespace. A tenant-wide membership is not inferred from a database file or session.

| Typed action | `tenant_admin` | `colleague_user` | `auditor` |
| --- | --- | --- | --- |
| Read own session/security status | Allow | Allow | Allow |
| Read colleague state in member scope | Allow | Allow | Allow |
| Read governance/change status in member scope | Allow | Deny | Allow |
| Assign finite work in member scope | Allow | Allow | Deny |
| Submit an allowed trigger in member scope | Allow | Allow | Deny |
| Request one bounded runtime cycle in member scope | Allow | Allow | Deny |
| Decide an exact effect in member scope | Allow | Allow | Deny |
| Create/edit/review/cancel an inert draft | Allow | Deny | Deny |
| Propose an authority/policy change | Allow | Deny | Deny |
| Approve/reject an authority/policy change | Allow, with separation | Deny | Deny |
| Apply an approved authority/policy change | Allow, exact approval only | Deny | Deny |
| Issue/revoke enrollment or recovery authority | Allow | Deny | Deny |
| Propose membership, role, or admin change | Allow | Deny | Deny |
| Approve/apply membership, role, or admin change | Allow, with separation | Deny | Deny |
| Read bounded audit export in member scope | Allow | Deny | Allow |
| Dispatch as HUMAN or access a HUMAN credential | Deny | Deny | Deny |

MODEL and SERVICE receive no human action from this table. A restricted SERVICE runtime
context may only consume accepted triggers and dispatch an independently approved exact
effect after current Mandate, policy, namespace, and approval revalidation. It never reads
or borrows a HUMAN session.

## Versioned membership and session binding

- A membership binds one durable HUMAN principal to the local tenant, an explicit set of
  colleague scopes (or the Admin tenant-governance scope), canonical roles, lifecycle
  status, role revision, membership revision, issuer, times, and causal record.
- A session records the role revision and membership revision observed at issuance. Every
  read and mutation resolves the durable principal and current membership, verifies exact
  binding equality, active status, credential/session expiry, and revocation, then applies
  the typed action matrix.
- Role or scope modification and membership revocation increment the corresponding
  revision and revoke existing sessions transactionally. A stale session cannot retain a
  previous privilege even when its credential and expiry would otherwise be valid.
- Not-found, unauthorized, guessed-ID, and cross-namespace outcomes use the same safe
  refusal category at an external boundary. Diagnostics must not disclose existence.

## Minimal second-Admin bootstrap transition

The first Admin cannot obtain a second approver through the ordinary two-person rule. P6
therefore permits exactly one narrowly bounded bootstrap transition per tenant:

1. It is available only when the original bootstrap is consumed, exactly one active
   `tenant_admin` HUMAN membership exists, no second-Admin transition has been consumed,
   and no other Admin enrollment is pending.
2. That sole Admin may authorize one fixed-role `tenant_admin` enrollment permit. The
   tenant, role, HUMAN kind, lifecycle, expiry ceiling, and non-wildcard local scope are
   server fixed. It cannot add any other role or modify an existing principal.
3. A local operator creates and retrieves the corresponding high-entropy plaintext token
   exactly once. Only its purpose-framed digest is persisted. The API and Studio see safe
   permit metadata, never the token.
4. Expiry or revocation before redemption closes that credential but does not consume the
   transition; a replacement remains possible only while the one-Admin invariant still
   holds. Successful atomic redemption creates exactly one new durable HUMAN Admin,
   consumes the credential and the transition irreversibly, and rotates into a new
   server-created session.
5. Issuance, operator retrieval, revocation, expiry, failed redemption, and successful
   consumption leave secret-free causal audit. Concurrent redemption has one winner.

After this transition is consumed, every Admin enrollment, role elevation, privileged
scope expansion, membership reactivation, or governance-authority change requires an
exact proposal and a different current Admin approver. The exception cannot recover an
Admin, replace a removed Admin, or become a permanent bootstrap backdoor.

## Enrollment credential lifecycle

- A current `tenant_admin` authorizes a permit with a server-fixed tenant, HUMAN kind,
  role, exact colleague scopes, issue time, expiry no later than ten minutes, lifecycle,
  and causal binding. Role elevation uses the change-approval flow before a permit can be
  activated, except for the one minimal transition above.
- Plaintext is generated by at least 256 bits of secure entropy and is available only from
  the explicit one-shot local operator boundary. Retrieval is atomic and once only. API,
  worker, Studio, logs, stderr, diagnostics, audit, evidence, and public artifacts receive
  no plaintext.
- Persistence contains only a purpose-framed digest. Redeeming the token atomically checks
  digest, permit, exact tenant/scope/role, retrieval, expiry, revocation, lifecycle, and
  consumption; creates a server-ID durable HUMAN principal and versioned membership;
  consumes the token; and issues a new server-ID digest-only session.
- Guessing, replay, expiry, revocation, wrong scope, cross-tenant use, role/kind injection,
  and concurrent consumption fail closed and create only safe causal evidence.

## Recovery and session rotation

- Recovery is authorized by a current Admin for one existing durable HUMAN principal and
  exact active membership. It is not an unauthenticated browser endpoint and cannot change
  tenant, principal kind, role, or scope.
- A recovery permit is short-lived, revocable, single-use, purpose-scoped, and safe to
  inspect. Its at-least-256-bit plaintext credential is generated/retrieved once through
  the local operator boundary; only a digest persists.
- Redemption verifies principal and membership revisions, namespace, expiry, revocation,
  retrieval, and unused state atomically. It revokes all prior sessions for the principal,
  consumes the recovery credential, and issues a new server-created session ID,
  credential, and CSRF binding. This prevents fixation and stale-session reuse.
- A recovered session still undergoes every-request membership and role revision checks.
  Recovery cannot reactivate a revoked membership, restore an old role, or serve as a
  reusable bootstrap path.
- Guessing, replay, cross-namespace use, wrong principal, concurrent redemption, and expiry
  leave a bounded, credential-free causal audit.

P6 does not implement or claim email/SMS recovery, OIDC, SSO, SCIM, MFA, enterprise IAM,
or remote operator recovery.

## Authority and policy change approval

An authority-affecting draft is inert after P5 review. P6 separates proposing, deciding,
and applying it:

```text
reviewable draft -> exact change proposal -> approved/rejected/expired/stale
                 -> exact one-time apply -> applied
```

- A change proposal binds complete namespace, server proposal ID/revision, exact draft ID
  and revision, three base heads, canonical draft digest, proposer principal ID, proposer
  role/membership revisions, proposed Profile/Mandate/policy revisions, current Mandate and
  policy revisions, issue time, expiry no later than thirty minutes, correlation,
  causation, schema version, and optimistic revision.
- Mandate mission, service relationship, responsibilities, capabilities, constraints,
  effect boundaries, and every ColleaguePolicy field require this flow. Working hours,
  triggers, proactivity, notification, interruption, wake budget, run state, stop, resume,
  and escalation are authority-affecting.
- Profile-only descriptive changes may use the same proposal record for audit but require
  no second approval only when the canonical classified diff proves that Mandate, policy,
  role, membership, and scope are unchanged. Unknown or mixed diffs require approval.
- A current, durable HUMAN `tenant_admin` in the exact namespace may decide. The approver
  must differ from the proposer and must have current role/membership revisions at decision
  and apply time. Model review, Studio confirmation, effect approval, or operator access is
  not change approval.
- Approval and rejection are exact-revision decisions with a bounded expiry. Rejection is
  terminal. Expiry and stale outcomes persist. Approval does not apply content by itself.
- Apply rechecks proposer/approver separation, both principals and revisions, namespace,
  draft lifecycle, draft revision/digest, all three current base heads, proposal/decision
  expiry, idempotency binding, and unconsumed state in one transaction. Success consumes
  the decision and proposal, applies all changed heads or membership authority atomically,
  invalidates older authority-bound contexts, and records safe audit.
- Stale, expired, replayed, cross-namespace, digest-mismatched, partially rebound, revoked,
  or already consumed proposals/decisions fail closed. A decision authorizes only the
  reviewed exact revision and grants no future authority.

## Exact-effect approval hardening

Change approval never constitutes effect approval. Existing exact-effect invariants remain
and gain the following requirements:

- EffectProposal and HumanApprovalDecision each have an explicit bounded expiry.
- Decision time and dispatch time revalidate complete namespace, proposal revision and
  canonical digest, payload digest, Mandate ID/revision, policy ID/revision, current HUMAN
  approver kind/role/membership revisions, and one-time consumption.
- Revocation, role/scope revision, Mandate/policy revision, proposal expiry, decision
  expiry, cross-namespace rebinding, digest mismatch, or replay prevents dispatch.
- Decision and dispatch idempotency bind a key to one canonical request. Reuse for another
  payload is a conflict. Ambiguous effects are never blindly resent.
- Worker/SERVICE contexts carry no HUMAN session or credential and cannot author a human
  decision. `colleague_user` may decide only exact effects inside current member scope;
  `auditor` cannot decide or dispatch.

## HTTP, CSRF, Origin, idempotency, and IDOR rules

- Every browser mutation requires a current server session, exact configured Origin,
  session-bound CSRF value, typed action authorization, complete current membership,
  request-size limits, and transactionally persisted idempotency/replay binding.
- Missing or wrong Origin/CSRF, alternate endpoints, namespace omission, partial namespace
  rebinding, caller authority fields, or a key rebound to different canonical input fail
  closed before mutation.
- Every P4/P5/P6 endpoint and direct service/store path has negative tests for cross-tenant,
  cross-colleague, cross-principal, guessed IDs, wrong role, wrong kind, stale revisions,
  list/read/export leakage, and namespace omission. Store APIs accept an explicit complete
  namespace or authenticated governance scope; no unscoped convenience query may bypass it.

## Bounded audit export

- Only a current `tenant_admin` or `auditor` may export within exact authorized namespace.
  Export is read-only and never grants mutation, approval, dispatch, or wider discovery.
- The versioned export schema uses deterministic ordering by `(occurred_at, record_type,
  record_id, revision)` and an explicit inclusive UTC range, record-type allowlist, and
  positive limit no greater than 500. An omitted or unbounded range/limit is refused.
- Each row contains only schema version, complete namespace, safe actor kind/ID, action or
  record type, record ID/revision, result, correlation/causation, relevant authority
  revisions, safe digest, and UTC time. Private payloads remain absent.
- Credentials, tokens, cookies, CSRF, private payloads, local absolute paths, provider IDs,
  raw diagnostics, and live identifiers are forbidden. Export itself creates a safe audit
  event without recursively including itself in the response.
- Repeating the same bounded query over unchanged pre-export rows is deterministic across
  restart. Cross-scope, guessed-ID, unauthorized-role, and oversized export attempts fail
  without revealing existence.

## Persistence and migration gate

Additive `migrations/007_governance_hardening.sql` adds only P6 schema for credential
digests/lifecycle, versioned membership and role binding, session rotation/revocation,
exact change proposal/decision/consumption, governance audit, and export metadata.
Migrations 001-006 and their manifest identities remain unchanged.

Fresh schema creation and an actual version-6 upgrade produce the same schema and preserve
all earlier records. Migration checksum, WAL, foreign keys, reconstruction, transaction
rollback, concurrent credential consumption, concurrent/stale change decisions, and
failure-without-partial-authority-update are required. P6 makes no production migration,
backup, encryption-at-rest, distributed-store, or availability claim.

## Studio and local Compose gate

Studio clearly displays enrollment/recovery permit state; current session, role and
membership revisions; pending authority changes; exact revision/digest/diff; proposer,
approver, expiry and stale/refused reason; role-appropriate read-only/action controls; and
bounded audit export results. Revoked authority and expired sessions produce explicit safe
states. Direct-request tests prove hidden controls are not authorization.

Compose retains API, worker, Studio, operator-only credential retrieval, one durable
`state.sqlite` volume, deterministic provider, and reference channel. Published ports bind
only to `127.0.0.1`; container services may listen on `0.0.0.0` for Compose networking.
The actual Gate uses a unique project and volume, restarts services, exercises recovery,
scans logs for credential absence, stops normally, and proves zero container, network, and
volume residue.

## Abuse-case gate

Mechanical API and direct-service/store coverage must refuse and safely evidence:

- caller-supplied role, tenant, namespace, principal, kind, revision, or authoritative time;
- MODEL/SERVICE impersonation of HUMAN and Auditor/User elevation;
- proposer self-approval and role/Admin elevation without exact change approval;
- enrollment/recovery guessing, replay, expiry, revocation, wrong scope, and concurrent use;
- session fixation, old-session reuse, and continued use after role/membership revocation;
- missing CSRF, wrong Origin, alternate endpoint, namespace switch, and idempotency rebinding;
- cross-tenant, cross-colleague, cross-principal, guessed-ID, list/read/export IDOR;
- stale, expired, replayed, consumed, cross-namespace, and digest-mismatched change approval;
- stale, expired, replayed, consumed, cross-namespace, and digest-mismatched effect approval;
- old proposal/SERVICE context after Mandate, policy, role, or membership revision;
- audit-export escalation, leakage, missing bounds, and excess limit;
- secrets/private data in logs, errors, evidence, or public artifacts;
- restart/concurrency/rollback partial grants; and
- notification flooding, wake-budget evasion, and trigger amplification, which remain
  refused by the P5 revision-bound policy.

## Evaluation and claim boundary

P6 adds governance scenarios and measurement points only. Synthetic, offline, human, and
live-provider evidence remain distinct and one cannot substitute for another.

AI-initiated rate counts allowed-trigger opportunities that produce a user-visible
suggestion, proposal, or notification before a new user prompt. Internal wake/no-op does
not enter the numerator. Unauthorized proposal escape rate divides violating candidates
that nevertheless create a proposal, reach the inbox, or proceed further by every
evaluated violating candidate/attempt. Correct refusals remain in the denominator with safe
causal evidence. A zero denominator is `not_applicable` with denominator and reason, never
0% success.

Passing P6 cannot claim colleague-experience improvement, human validation, live-provider
readiness, production security/privacy, compliance, enterprise tenancy/IAM, high
availability, distributed execution, or production readiness.

Future Semantic Memory, Skills, and shared knowledge require independent provenance,
authorization, versioning, correction/revocation, rollback, namespace/ownership, and abuse
testing. They can never become authority sources. P6 documents this requirement and creates
no domain model, table, API, UI, or feature flag for those capabilities.

## Required repeatable gates

```bash
git diff --check
python3 -B scripts/check_public_boundary.py .
python3 -B scripts/check_p6_repository.py .
python3 -B scripts/check_p6_provenance.py .
python3 -B scripts/check_p6_architecture.py .
PYTHONPATH=src python3 -B scripts/check_p6_migrations.py .
PYTHONPATH=src python3 -B scripts/check_p6_authentication.py .
PYTHONPATH=src python3 -B scripts/check_p6_rbac.py .
PYTHONPATH=src python3 -B scripts/check_p6_change_approval.py .
PYTHONPATH=src python3 -B scripts/check_p6_effect_approval.py .
PYTHONPATH=src python3 -B scripts/check_p6_audit_export.py .
PYTHONPATH=src python3 -B scripts/check_p6_abuse.py .
python3 -B scripts/check_p6_studio.py .
python3 -B scripts/check_p6_compose.py .
python3 -B scripts/check_p6_compose_runtime.py .
PYTHONPATH=src python3 -B scripts/check_p6_golden_path.py
python3 -B scripts/run_p6_unittest_suite.py --start-directory tests --top-level-directory .
make check
make p6-compose-runtime
```

Corresponding Make targets are `p6-repository`, `p6-provenance`, `p6-architecture`,
`p6-migrations`, `p6-authentication`, `p6-rbac`, `p6-change-approval`,
`p6-effect-approval`, `p6-audit-export`, `p6-abuse`, `p6-studio`, `p6-compose`,
`p6-compose-runtime`, `p6-golden`, and `evidence-p6`. `make check` retains all applicable
P0-P5 regressions. Evidence targets P0-P5 must not run.

Every test aggregate must report zero failures, errors, skips, and unexpected successes.
Public-boundary exceptions must be zero. Docker runtime is mandatory for completion; an
unavailable runtime is `not_evaluated` and blocks evidence and the completion statement.

## Evidence contract

Only after the acceptance and implementation commits exist, the tree is clean, and every
direct and aggregate Gate passes may `make evidence-p6` atomically create
`artifacts/p6/summary.json`. It records fixed base/branch, merge-base, real implementation
commit, evidence-target binding, public-tree digest excluding exactly the summary,
migration 007 digest, gate and test identities/results, actual Compose restart and cleanup,
RBAC and credential lifecycle outcomes, change/effect refusal outcomes, audit export
redaction/bounds, abuse results, evidence classes, and claim exclusions.

The collector must refuse `main`, a wrong branch/base, missing trusted commits, dirty state,
incomplete Gate, unavailable Docker, nonzero test outcome/skip/exception/residue, or drift in
historical immutable files. It writes no credential, cookie, CSRF, private payload, absolute
path, or live identifier. The summary is committed separately; all Gates, public boundary,
and actual Compose runtime run again afterward. No future commit SHA is invented.

## Explicit exclusions and stop condition

P6 does not implement Semantic Memory, Skill Learning or a governed Skill system, shared
knowledge, a multi-person collaboration platform, Self-initiated autonomy, real
models/providers/channels, OIDC, SSO, SCIM, email/SMS enrollment or recovery, MFA,
PostgreSQL, distributed execution, high availability, production tenancy, encryption at
rest, production readiness/security certification/compliance, P7, or P8.

Stop only after the fixed acceptance commit, implementation commit, and separate evidence
commit exist; every focused and aggregate Gate and final actual Compose runtime passes;
cleanup is zero; P0-P5 history/evidence/receipts and migrations 001-006 are unchanged; no
out-of-scope file exists; and index/worktree are clean. Do not merge, push, tag, release,
delete the branch, rewrite reviewed commits, or begin P7.
