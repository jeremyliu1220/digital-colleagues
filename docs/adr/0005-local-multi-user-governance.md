<!-- SPDX-License-Identifier: Apache-2.0 -->

# ADR 0005: Local Multi-User Governance

- Status: Accepted for P6 development
- Decision date: 2026-09-02
- Scope: P6 local authentication, authorization, change approval, and audit export

## Context

P4 established one digest-authenticated local Admin and P5 added inert revisioned
Profile/Mandate/policy drafts. That is insufficient for multi-user governance: a session
could retain a changed role, a single Admin cannot satisfy proposer/approver separation,
recovery could become a durable backdoor, and P5 confirmation lets the same Admin propose
and apply authority. P6 needs a narrow local mechanism that is explicit, restart-safe, and
testable without implying enterprise IAM or production isolation.

## Decision

### Central typed authorization

P6 defines a finite typed action enumeration and one role-action matrix. All HTTP,
application, and store boundaries require a current durable HUMAN principal, canonical
role, complete namespace, versioned membership, and action. `tenant_admin` manages local
governance within the configured tenant; `colleague_user` interacts and may decide exact
effects only in explicit colleague membership scope; `auditor` has scoped read and bounded
export only. MODEL and SERVICE have no human action and cannot hold a human role.

Membership is durable and independently revisioned. A session binds the role and
membership revisions current at issuance. Every request resolves durable state and rejects
expiry, revocation, or revision drift. Role/scope change revokes old sessions in the same
transaction. Browser input and UI state never supply authority.

### Bootstrap transition to two-person governance

Ordinary Admin creation and role elevation require a proposal from one Admin and approval
from another. A tenant initially has only one Admin, so this rule otherwise deadlocks.

We allow one exceptional, auditable transition: while exactly one active Admin exists and
the transition is unused, that Admin can authorize one fixed `tenant_admin` HUMAN
enrollment. A local operator generates/retrieves its short-lived token exactly once; only a
purpose-framed digest persists. Atomic redemption creates exactly one distinct Admin and
irreversibly consumes the transition. An expired or revoked unredeemed credential may be
replaced only while the one-Admin invariant remains true. The transition cannot recover an
Admin, modify an existing principal, add another role, or operate after its one success.

This is the minimum authority expansion needed to make subsequent two-person governance
possible. Every later Admin enrollment, elevation, privileged scope expansion,
reactivation, or governance-authority change uses exact proposer/approver separation.

### Enrollment and recovery

An Admin authorizes a scoped permit, but no HTTP response contains a plaintext credential.
The one-shot local operator boundary creates and claims at least 256 bits of entropy against
that permit; persistence receives only its digest. Tokens are short-lived, revocable,
single-use, purpose/tenant/role/scope bound, and atomically consumed. The server generates
principal and session IDs and fixes HUMAN kind, role, and membership.

Recovery is likewise Admin-authorized and operator-delivered for one existing active HUMAN
principal and exact membership revision. It cannot alter role or scope. Redemption revokes
all old sessions, consumes the token, and creates a new server session credential and CSRF
binding, preventing fixation. It cannot reactivate a revoked membership or become a
permanent bootstrap route.

### Exact change approval

Mandate, effect boundary, responsibility, capability, constraint, and every
ColleaguePolicy change moves from a reviewed inert draft to an exact change proposal. The
proposal binds its complete namespace, draft/revision/digest, three base heads,
proposer/revisions, current Mandate/policy, issue/expiry, and causal record. A different
current Admin approves or rejects. Apply revalidates every binding and atomically consumes
the decision while updating authority; stale, expired, replayed, cross-namespace,
digest-mismatched, or revoked authority fails closed.

A canonical Profile-only descriptive diff may omit second-person approval only when all
authority, policy, role, membership, and scope heads are proven unchanged. Unknown or mixed
changes require approval. Change approval is never effect approval, and exact-effect
approval never authorizes a governance change.

### Effect approval and export

Effect proposals and human decisions have bounded expiry and are revalidated both when
decided and immediately before dispatch against current Mandate, policy, role, membership,
namespace, digest, and replay state. The worker never receives HUMAN session authority.

Audit export is a separate scoped read action for Admin and Auditor. It requires explicit
UTC bounds, record-type allowlist, and a maximum limit, uses deterministic ordering and a
versioned schema, and returns only safe causal fields and digests. The export action is
audited without recursively adding itself to that response.

## Consequences

- The first transition is visibly exceptional and permanently closes after the second
  Admin exists; normal governance is then two-person for authority expansion.
- Role and scope revocation take effect on existing sessions without waiting for session
  expiry.
- Plaintext enrollment/recovery credentials never traverse browser-facing APIs or durable
  state, at the cost of a required local operator step.
- A reviewed P5 draft remains inert until its exact P6 decision is separately approved and
  applied.
- SQLite `BEGIN IMMEDIATE` transactions and optimistic revisions provide one-host atomic
  semantics only; they do not prove distributed consistency or production tenant isolation.

## Rejected alternatives

- **Permanent single-Admin override:** rejected because it defeats proposer/approver
  separation after bootstrap.
- **Self-approved second Admin through the normal change flow:** rejected because it hides
  the bootstrap exception and falsely claims two-person approval.
- **Return enrollment/recovery tokens from HTTP:** rejected because it crosses the explicit
  local operator delivery boundary and increases credential exposure.
- **Long-lived recovery secret:** rejected because it becomes a second bootstrap backdoor.
- **Session-cached roles without revision checks:** rejected because revocation would not be
  immediate.
- **Treat Studio confirmation or model review as approval:** rejected because neither is a
  separate authenticated human authority.
- **Unbounded database export:** rejected because namespace and private-data exposure would
  be difficult to constrain or audit.

## Claim and future-capability boundary

This is a local deterministic reference decision. It does not add or claim OIDC, SSO,
SCIM, MFA, email/SMS recovery, enterprise IAM, production tenancy/security/privacy,
encryption at rest, compliance, distributed execution, high availability, or production
readiness.

Future Semantic Memory, Skills, and shared knowledge require independent provenance,
authorization, namespace/ownership, versioning, revocation/correction, rollback, and abuse
testing. None may grant authority from remembered content, learned behavior, work history,
or descriptive Profile data. P6 documents these requirements but implements no such
capability.

## Related documents

- [P6 acceptance contract](../p6/acceptance.md)
- [P6 security Golden Path](../p6/security-golden-path.md)
- [ADR 0002](0002-technology-stack-and-local-authentication.md)
- [ADR 0004](0004-revisioned-colleague-policy-model.md)
- [Target architecture](../architecture/target-architecture.md)
- [Threat model](../security/threat-model.md)
