<!-- SPDX-License-Identifier: Apache-2.0 -->

# Local Reference Threat Model

## Scope and claim boundary

This model defines requirements for the v0.1 local reference topology. P5 mechanically
tested the local P4 bootstrap/session boundary plus revisioned draft, policy, namespace,
authority, replay, deterministic execution, SQLite, outbox, and safe-audit controls. P6 is
required to test typed RBAC, versioned membership, enrollment/recovery, proposer/approver
separation, approval expiry, scoped export, and abuse cases. Until its Gate passes those
are requirements, not verified controls. Neither milestone establishes product security or
privacy effectiveness. Encryption at rest,
OIDC, SSO, SCIM, distributed isolation, and high availability remain gaps.

## Assets

- Durable human, model, and service identities and role assignments.
- Revisioned Profile, Mandate, colleague policy, draft, and confirmation records.
- Work, events, agenda, wake-cycle, proposal, approval, and result records.
- Sessions, bootstrap and enrollment credentials, and recovery authority.
- Namespaced SQLite state, migrations, audit records, and exports.
- Source provenance and the public/private data boundary.

## Trust boundaries

- Browser and Studio input is untrusted.
- Model output and provider content is untrusted data, never authority.
- HTTP mappings validate shape but do not grant authorization.
- Application and governance services enforce session, role, namespace, revision, expiry,
  and replay rules.
- SQLite and local volumes are operator-controlled but are not encrypted by v0.1.
- Optional provider and channel adapters cross a network and privacy boundary.
- Build dependencies and containers cross a software supply-chain boundary.

## Threats and required controls

| Threat | Required v0.1 control |
| --- | --- |
| Caller-supplied role or tenant | Derive both from the server-side session; reject authority fields |
| Model self-approval | Principal-kind invariant and human-only approval authoring |
| Human identity simulated by service identity | Durable disjoint principal kinds; no kind conversion |
| Prompt injection expands authority | Mandate and policy checks after model output; typed exact effects |
| Draft silently changes active authority | Inert draft state; exact digest/base confirmation; atomic three-head compare-and-swap |
| Concurrent draft overwrites newer authority | One-winner compare-and-swap; durable terminal stale evidence; no auto-rebase |
| Hidden or ambiguous policy default expands authority | Typed visible defaults and classified diff; unknown fields and invalid combinations fail closed |
| Restart or alternate trigger evades wake budget | Namespaced policy-revision counter plus unique occurrence consumption in one transaction |
| Policy revision retroactively authorizes old work | Exact Mandate/policy binding and revalidation before proposal, approval, and dispatch |
| Stop or escalation becomes an effect | Finite typed conditions; durable local state/record only; explicit revisioned resume |
| Insecure direct object reference | Namespace every record and every repository query |
| Stale or partially rebound approval | Expected revision plus complete canonical proposal-digest checks |
| Duplicate mutation or approval | Idempotency key, one-time consumption, and replay ledger |
| Ambiguous effect | Persist AMBIGUOUS, prohibit blind resend, reconcile applied/absent/unknown, retry only confirmed absence |
| Session theft or fixation | Server-generated session ID, digest-safe storage, expiry, strict cookie policy |
| Background worker borrows human authority | Namespace-bound SERVICE runtime context; worker never reads or reuses HUMAN sessions |
| Cross-site mutation | Origin validation and CSRF defense on every mutation |
| Bootstrap credential disclosure | Strong random value, one display, digest-only storage, short expiry, one use |
| Enrollment privilege escalation | Admin-issued scoped token; server selects durable role |
| One-Admin bootstrap deadlock | One fixed, audited second-Admin transition; closes permanently after atomic success |
| Self-approved authority change | Exact proposal and a different current Admin approver; revalidate again at apply |
| Recovery becomes a backdoor | Admin-authorized one-use operator credential; no role/scope change; rotate and revoke sessions |
| Revoked role retained by session | Session binds current role/membership revisions; every request re-resolves and compares |
| Approval outlives authority | Proposal/decision expiry and dispatch-time Mandate/policy/role/membership revalidation |
| Audit export leaks or escalates | Admin/Auditor only, exact scope, explicit bounds/limit, deterministic safe schema and redaction |
| Audit tampering or gaps | P3 transactional immutable safe audit rows; local operator tampering remains possible |
| Unsupported zero-valued evaluation claim | Durable evaluator/governance observations; eligible unobserved scenarios remain not evaluated |
| Outbox double delivery | Transactional claim/lease/fence, idempotent effect key, attempt/result records, bounded retry |
| New cause during Agenda claim | Durable generation and handled-generation retain and requeue the later cause |
| Stale worker checkpoint | Monotonic fencing token and owner checks reject the stale checkpoint |
| Path or diagnostic disclosure | Public-boundary scanner and sanitized error handling |
| Credential committed to source | Scanner rules, ignored local configuration, CI gate in P1 |
| Live data used as public fixture | Explicit denylist and separate live acceptance storage |
| Dependency compromise | Locked dependencies, license review, provenance, and release inventory in later gates |
| Local denial of service | Input limits, bounded wake work, SQLite busy handling, and operator recovery |

## Authentication requirements

The normative local authentication decision is ADR 0002. P4 implements the first-Admin
subset: one-time local bootstrap retrieval, digest-only short-lived bootstrap state,
atomic exchange, server-created HUMAN `tenant_admin` and session, strict cookie behavior,
session expiry, Origin and CSRF validation, namespace derivation, role injection refusal,
and principal-kind separation. General enrollment, session recovery, and complete RBAC
hardening have a fixed P6 contract. They remain unverified until the P6 security Gate and
evidence pass.

## Residual risks

- A local operator with filesystem access can read or alter unencrypted state.
- Malware in the same user context can bypass assumptions made by loopback binding.
- Browser compromise can act within a valid session.
- The deterministic provider does not validate the safety of real model output.
- A reference channel does not validate real provider delivery or privacy behavior.
- One SQLite writer and one-host Compose topology do not provide availability guarantees.

These are explicit limitations, not deferred claims.
