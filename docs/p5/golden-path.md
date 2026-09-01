<!-- SPDX-License-Identifier: Apache-2.0 -->

# P5 Revisioned Builder Golden Path

Status: fixed development contract; actual isolated Compose runtime evidence is required.

This path exercises only synthetic/offline P5 behavior over the deterministic provider and
reference channel. It uses no real model, account, provider, credential, network effect,
human-study data, or live-provider evidence. Loopback publishing reduces host exposure; it
is not authentication, encryption, sandboxing, tenant isolation, or production security.

## Prerequisites and isolated runtime

Run from the repository root with Docker Engine and Compose v2, Python 3.12+, Node.js
22.12+, npm, Make, and two unused loopback ports. The automated actual runtime Gate is:

```bash
make p5-compose-runtime
```

It generates a unique non-personal project name, chooses unused loopback ports, creates a
project-scoped temporary `state` volume, builds and starts API/worker/Studio, executes the
steps below with synthetic data, force-recreates long-running containers over the same
volume, stops normally, scans service logs for in-memory credentials, and removes the
project containers, network, and volume in a guaranteed cleanup path.

The faster fresh-instance semantic path is:

```bash
make p5-golden
```

It reconstructs store, application, and HTTP instances over one temporary SQLite file
outside the repository. It is not a substitute for the actual Compose Gate.

## Admin and active baseline

1. Start the clean topology and retrieve bootstrap authority exactly once through the
   local operator process. Keep the plaintext token only in process memory.
2. Exchange it for the server-created HUMAN `tenant_admin` session and session-bound CSRF
   value. Confirm cookie, Origin, expiry, and namespace enforcement.
3. Create the accepted P4 initial colleague or load a legacy P4 colleague. Its active
   identity card must show only confirmed Profile/Mandate state. Its free-form working
   hours must be labeled `legacy_unconfirmed`, not interpreted as typed policy.

## Draft, review, and exact apply

4. Create revisioned draft A from the active Profile, Mandate, and policy bases. Record the
   server draft ID, revision 1, three base revisions, author, correlation, and causation.
   Confirm the active identity card and runtime are unchanged.
5. Edit descriptive Profile fields separately from responsibilities, capabilities, effect
   authority, and every policy section. Confirm the content revision increases and unknown
   or ambiguous authority input is rejected without changing active state.
6. Set an IANA timezone and typed weekly windows, allowed Event/Timer triggers, bounded
   proactivity, notification/interruption rules, wake limit and period, stop conditions,
   escalation conditions, and explicit run state. Leave at least one optional field omitted
   so the typed `p5_system_default` and its source are visible.
7. Review draft A. Inspect its exact revision and canonical digest; active-only identity
   card; inert proposed preview; Profile, Mandate, and policy before/after sections; and
   added, removed, changed, narrowed, expanded, and unchanged classifications where
   applicable. Verify every explicit default appears.
8. Confirm using exactly the displayed draft revision, three base revisions, digest, and a
   new idempotency key. Verify Profile and changed authority revisions increment as defined,
   active identity reflects only the confirmed state, safe causal audit exists, and exact
   replay returns the same result while different-content key reuse conflicts.

## Restart and policy enforcement

9. Create accepted Event and Timer occurrences and consume budget deterministically. Stop
   and force-recreate API, worker, and Studio while preserving the isolated volume. Verify
   active state, draft history, exact revisions/digest, run state, escalation history,
   deduplication ledger, and budget counters recover from SQLite.
10. Exercise an in-hours allowed trigger and inspect the exact Mandate/policy revision on
    wake, Decision, proposal, approval, dispatch, result, and audit. Exercise cross-midnight
    and DST-fold timestamps with injected UTC instants.
11. Exercise outside-hours handling, disallowed Event/Timer class, disabled proactivity,
    notification suppression, interruption suppression, budget exhaustion, duplicate
    occurrence delivery, and alternate-class budget evasion. Confirm governed defer/no-op/
    refusal outcomes are distinct, restart-safe, and create no unauthorized proposal.
12. Trigger a typed stop condition. Verify subsequent wake/proposal refusal survives
    restart. Use a separately reviewed and confirmed Admin draft to make the explicit
    revisioned resume change; confirm no implicit resume occurred.
13. Trigger a typed escalation condition. Inspect its visible safe record and causal
    references, and verify it created no approval, Mandate change, provider effect, or
    expanded permission.

## Concurrency and stale authority

14. Create drafts B and C from the same complete active base. Review both. Confirm B, then
    attempt C with its exact old bases and digest. B must apply atomically; C must become
    terminal `stale` with safe evidence and no partial Profile/Mandate/policy write. Studio
    must not auto-rebase, retry, or overwrite C.
15. Before another authority change, create an exact proposal and approval plus capture a
    restricted SERVICE runtime context. Confirm an authority-affecting draft. Reuse of the
    old proposal, approval, or runtime context must fail closed before approval/dispatch,
    with the reference channel uncalled.

## Metrics, audit, and cleanup

16. Inspect the full safe chain, including draft create/update/review/confirm, policy
    refusal, budget counter, stop/resume, escalation, wake, proposal, approval, dispatch,
    and ActionResult. Private payloads and credentials must be absent.
17. Read revision-bound metrics. Internal wake/no-op is outside the AI-initiated numerator;
    working-hours defer, suppression, and budget refusal are not successful interactions;
    evaluator-uncovered interruption is `not_evaluated`; zero denominators are
    `not_applicable` with a reason; unauthorized proposal escape rate remains zero.
18. Stop services normally, then remove the isolated containers, network, and volume. Check
    that no SQLite/WAL/SHM, log, credential, build, container, network, or volume residue
    remains in the repository or named Compose project.

## Success and claim boundary

Success requires exact draft confirmation, atomic active revision change, restart recovery,
deterministic enforcement of every P5 policy, one-success/one-stale concurrent drafts,
stale old authority contexts, complete safe audit, actual Compose execution, and zero
cleanup residue. Evidence is synthetic/offline only. It does not establish the manual
five-minute objective, colleague-experience improvement, human usefulness, live-provider
behavior, production security/privacy, compliance, availability, or production readiness.
