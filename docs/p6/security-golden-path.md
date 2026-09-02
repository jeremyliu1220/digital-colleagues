<!-- SPDX-License-Identifier: Apache-2.0 -->

# P6 Local Governance Security Golden Path

Status: fixed development contract; actual isolated Compose runtime and cleanup evidence
are required.

This path exercises synthetic/offline local governance over the deterministic provider and
reference channel. It uses no real identity provider, model, provider, account, credential,
network effect, personal record, human-study data, or live-provider evidence. Loopback
publishing reduces host exposure; it is not authentication, encryption, sandboxing,
production tenant isolation, or production security.

## Prerequisites and isolated runtime

Run from the repository root with Python 3.12+, Node.js 22.12+, npm, Make, Docker Engine,
Compose v2, and two unused loopback ports. The actual runtime Gate is:

```bash
make p6-compose-runtime
```

It uses a unique synthetic project, isolated temporary state volume, deterministic
fixtures, process-memory credentials, actual service restart/recreate, log scanning, normal
shutdown, and guaranteed removal of project containers, networks, and volumes. The faster
fresh-instance semantic path is:

```bash
make p6-golden
```

The fresh-instance path reconstructs application/store/API objects over one temporary
SQLite file outside the repository. It does not replace the Docker-required Gate.

## Bootstrap and the second Admin

1. Start a clean topology. Retrieve the first bootstrap credential once through the local
   operator command and exchange it from the exact configured Origin. Verify digest-only
   persistence, HUMAN `tenant_admin`, server-created principal/session IDs, strict cookie,
   CSRF, expiry, and replay refusal.
2. Inspect the sole Admin's membership and session role/membership revisions. Attempt
   caller role, tenant, namespace, principal, and kind injection; MODEL/SERVICE human-role
   simulation; guessed IDs; missing CSRF; and wrong Origin. All must fail without resource
   discovery or secret-bearing diagnostics.
3. Authorize the one permitted second-Admin bootstrap transition. Confirm the API and
   Studio return only safe permit metadata. Retrieve the enrollment plaintext once through
   the local operator boundary, redeem it concurrently, and prove exactly one success.
4. Verify the second durable HUMAN Admin has a distinct server ID/session, the enrollment
   credential and transition are consumed, replay fails, and no further exceptional Admin
   enrollment can occur. Expired/revoked pre-redemption replacement is separately tested
   without consuming or broadening the one transition.

## Enrollment, membership, and RBAC

5. With two Admins available, propose and approve scoped enrollment authority as required.
   Issue one `colleague_user` and one `auditor` permit with server-fixed tenant, HUMAN kind,
   role, colleague membership, expiry, and revisions. Retrieve tokens only through the
   operator boundary, then redeem them into separate durable principals and sessions.
6. Exercise the complete typed action matrix through API and direct service/store paths.
   The User may read and interact only in member colleague scope and may decide an exact
   effect there. The Auditor may read security/governance state and bounded audit export
   only. Only an Admin may manage identity, enrollment, recovery, drafts, Mandate, policy,
   membership, role, or authority-change workflows.
7. Attempt cross-tenant, cross-colleague, cross-principal, guessed-ID, omitted/partial
   namespace, wrong-role, wrong-kind, list/read/export, and alternate-endpoint access. Check
   that external refusals do not reveal whether a target exists and store queries cannot
   bypass the complete namespace.
8. Change or revoke a membership. Verify role and/or membership revision increments,
   current sessions are revoked, old sessions immediately lose access, and Studio shows a
   safe expired/revoked state rather than silently retaining UI authority.

## Recovery and session governance

9. An Admin authorizes recovery for the exact User principal and current membership.
   Retrieve the short-lived plaintext only through the operator boundary. Attempt guessing,
   wrong principal, cross-namespace, revoked/expired token, replay, and concurrent exchange.
10. Redeem the valid credential once. Verify all old sessions are revoked, a new server
    session ID/credential/CSRF binding is issued, fixation is impossible, role/scope did not
    change, and the recovery permit cannot reactivate a revoked membership.
11. Restart the stack and recheck active, expired, revoked, recovered, and stale-revision
    sessions against durable state. Verify no credential is present in API, worker, Studio,
    operator error, Compose log, database projection, public evidence, or audit output.

## Authority and policy change approval

12. Create and review an inert P5 draft that changes Mandate responsibility/capability/
    constraints/effect boundary and working-hour, trigger, proactivity, notification,
    interruption, budget, stop, resume, and escalation policy. Confirm active state and
    runtime authority remain unchanged.
13. Admin A creates an exact change proposal. Inspect complete namespace, draft/revision,
    three base heads, canonical digest, proposer and revision bindings, current Mandate/
    policy revisions, issue/expiry times, and safe diff. Self-approval by Admin A must fail.
14. Admin B approves the exact proposal. Attempt digest mismatch, cross-namespace binding,
    stale base, expired decision, revoked approver, idempotency rebinding, and replay. Each
    must fail without partial Profile/Mandate/policy mutation.
15. Apply the still-current approved revision once. Verify atomic three-head update,
    proposal/decision consumption, durable applied audit, stale old worker/effect contexts,
    and replay refusal. A separately rejected proposal never applies. Expired and stale
    outcomes remain durable and visible.
16. Exercise a Profile-only descriptive draft. It may follow the documented single-Admin
    apply path only when the canonical diff proves every authority, policy, membership,
    role, and scope head unchanged. Mixed or unclassifiable content fails closed.
17. Propose an Admin role elevation/scope expansion and prove it uses an equal-or-stronger
    two-person exact approval; the bootstrap exception is unavailable after consumption.

## Exact-effect and runtime hardening

18. Create an in-scope deterministic proposal as the scoped User. Inspect proposal expiry,
    complete digest, payload digest, Mandate/policy binding, namespace, and causal origin.
    Approve it with the User's exact current membership and dispatch once.
19. Create further proposals/approvals, then independently test proposal expiry, decision
    expiry, role revocation, membership scope change, Mandate revision, policy revision,
    namespace rebinding, digest mismatch, and replay before dispatch. The reference channel
    must remain uncalled for each refusal.
20. Verify change approval cannot dispatch an effect and effect approval cannot apply a
    draft or role change. Auditor, MODEL, and SERVICE approval attempts fail. Worker state
    contains no HUMAN session or credential. Ambiguous ActionResult remains non-resendable.
21. Re-run P5 notification-flooding, alternate-trigger budget-evasion, duplicate occurrence,
    and trigger-amplification cases. Correct refusals remain in the unauthorized-candidate
    denominator and no prohibited candidate reaches the proposal inbox.

## Audit export, restart, and rollback

22. As Admin and Auditor, request an exact-namespace export with explicit UTC bounds,
    allowlisted record types, and limit. Verify versioned schema, deterministic ordering,
    safe causal chain, actor, result, revisions, and digests. Repeat over unchanged
    pre-export rows after restart and compare output.
23. Attempt User export, cross-scope export, guessed namespace, omitted time bound, excessive
    limit, and unsupported record type. Verify safe refusal and no mutation authority.
    Search output for token, cookie, CSRF, credential digest, private payload, absolute
    path, provider identifier, and unredacted diagnostic shapes; all must be absent.
24. Run migration 007 on both a fresh database and a real version-6 database. Verify equal
    schema, preserved rows, manifest checksum, foreign keys, WAL, restart recovery,
    concurrent token consumption, concurrent/stale approval, and injected transactional
    failure with no partial grant.
25. Inspect safe audit for enrollment/recovery, session rotation/revocation, role/member
    change, proposal/decision/apply outcomes, effect refusal, export, and abuse cases. Audit
    contains only safe causal projections and never turns export into recursive unbounded
    data.

## Metrics, claims, and cleanup

26. Read revision-bound metrics. AI-initiated rate includes only an allowed trigger that
    produces a user-visible suggestion/proposal/notification before a new prompt. Internal
    wake/no-op is excluded. Unauthorized escape includes every tested violating candidate
    in the denominator, including correct refusals; its numerator must be zero. Zero
    denominators are `not_applicable` with a reason.
27. Confirm the evidence class is synthetic/offline and all human/live-provider outcomes
    remain unevaluated. No colleague-experience improvement, production security,
    enterprise IAM/tenancy, compliance, or readiness claim is emitted.
28. Stop normally and remove the isolated Compose project. Verify zero containers,
    networks, and volumes, plus no SQLite/WAL/SHM, log, credential, build, or runtime residue
    in the repository.

## Success and stop boundary

Success requires every step above, all focused Gates, full `make check`, a second actual
Compose runtime after evidence, zero tests skipped, zero public-boundary exceptions, and
zero cleanup residue. Docker unavailable or any runtime step not exercised is
`not_evaluated`, blocks evidence, and blocks the completion statement.

The result establishes only repeatable local synthetic/offline behavior. It does not
establish production security/privacy, human usefulness, provider behavior, enterprise
identity, distributed isolation, compliance, availability, or production readiness.
