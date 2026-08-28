<!-- SPDX-License-Identifier: Apache-2.0 -->

# ADR 0002: v0.1 Stack and Local Authentication

- Status: Accepted for P0 design; implementation deferred
- Decision date: 2026-08-27
- Applies to: v0.1 local reference topology

## Context

v0.1 needs a narrow, deterministic local stack that demonstrates persistent-colleague
primitives without implying distributed production properties. Its browser surface also
needs real, durable human principals rather than a UI role selector.

## Technology decision

- Python 3.12 or newer.
- FastAPI at the application edge.
- React, TypeScript, and Vite for Studio.
- One local `state.sqlite` using standard-library `sqlite3`, WAL mode, foreign keys, and
  numbered migrations with immutable checksums.
- A deterministic intelligence provider and reference channel as the required path.
- Docker Compose as the local reference topology.
- Frozen standard-library dataclasses, Enums, and Protocols in core.
- Pydantic only for HTTP request and response mapping; it must not enter core.
- No ORM.

Every persisted record carries complete namespace and schema version. Store access is
isolated behind ports. A single SQLite file is only a v0.1 local reference topology and
does not establish PostgreSQL support, distributed operation, high availability,
production tenancy isolation, or production readiness.

## Local authentication decision

The local bootstrap, enrollment, session, and recovery design is normative:

1. API and Studio bind to `127.0.0.1` by default.
2. A first-run bootstrap token is generated with a cryptographically secure random source
   and contains at least 256 bits of entropy.
3. The bootstrap token is displayed exactly once. Only a cryptographic digest is stored.
4. It expires no later than ten minutes after issue and permits only one successful
   exchange. Consumption is atomic and replay is rejected.
5. It can create only the first durable `tenant_admin` human principal and a server-side
   Admin session.
6. The browser cannot submit, choose, or override its role, principal kind, or tenant
   authority. The server assigns them.
7. The server generates the session ID. The browser receives only an HttpOnly,
   SameSite=Strict cookie; HTTPS mode also sets Secure.
8. Every mutation validates Origin, a CSRF defense, replay protection, session expiry, the
   durable principal, principal kind, role, namespace, and action-specific authorization.
9. An Admin creates a User or Auditor by issuing a server-generated, scoped, short-lived,
   single-use enrollment token. The server fixes the resulting role; the browser cannot.
10. Admin, User, and Auditor are different durable human principals. A UI role switch or a
    caller-supplied role must never simulate them.
11. Session recovery or reissuance is available only to an operator executing a documented
    local procedure. It is not exposed as an unauthenticated browser or remote API flow.
12. MODEL and SERVICE principals can never convert to HUMAN and can never submit
    HumanApprovalDecision.
13. Canonical role IDs are `tenant_admin`, `colleague_user`, and `auditor`; Admin, User,
    and Auditor are display names only.
14. OIDC, SSO, and SCIM remain explicit production gaps. The local token flow must never be
    described as equivalent to enterprise identity and access management.

## Authorization and approval consequences

- Session state is server-side and maps to one durable principal.
- Mandate and effect authorization remain separate from UI affordances.
- Human approval binds to an exact immutable effect revision and a versioned canonical
  proposal digest covering all authoritative effect fields, plus namespace, expiry, and an
  authorized human principal. The payload retains a separate redaction-safe integrity
  digest.
- P2 Mandate boundary constraint parameters are typed and exact-match; unknown, missing,
  extra, conflicting, or wrong-type values fail closed.
- Idempotency and replay ledgers are persisted transactionally with mutations.
- Recovery actions produce audit records but do not weaken principal-kind invariants.

## Alternatives rejected for v0.1

- Caller-selected demo roles: they do not demonstrate durable authorization.
- Browser-stored bearer sessions: they unnecessarily expose session authority to script.
- ORM-managed persistence: it weakens the explicit migration and port experiment.
- A network model or provider as the required path: it makes the reference path
  nondeterministic and risks live-data leakage.
- Claims of production tenancy from a namespaced SQLite schema: namespace is necessary but
  not sufficient evidence of isolation.
