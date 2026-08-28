<!-- SPDX-License-Identifier: Apache-2.0 -->

# Local Reference Threat Model

## Scope and claim boundary

This model defines design requirements for the v0.1 local reference topology. P0 records
requirements only; it does not establish that an implementation is secure. Loopback
binding and local tokens are not enterprise IAM. Encryption at rest, OIDC, SSO, SCIM,
distributed isolation, and high availability remain gaps.

## Assets

- Durable human, model, and service identities and role assignments.
- Revisioned Mandates and responsibility assignments.
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
| Insecure direct object reference | Namespace every record and every repository query |
| Stale or partially rebound approval | Expected revision plus complete canonical proposal-digest checks |
| Duplicate mutation or approval | Idempotency key, one-time consumption, and replay ledger |
| Ambiguous effect | Fail closed until destination, action, payload, and typed Mandate constraints are exact |
| Session theft or fixation | Server-generated session ID, digest-safe storage, expiry, strict cookie policy |
| Cross-site mutation | Origin validation and CSRF defense on every mutation |
| Bootstrap credential disclosure | Strong random value, one display, digest-only storage, short expiry, one use |
| Enrollment privilege escalation | Admin-issued scoped token; server selects durable role |
| Audit tampering or gaps | Transactional causal records and append-oriented audit controls |
| Outbox double delivery | Transactional claim, idempotent effect key, attempt and result records |
| Path or diagnostic disclosure | Public-boundary scanner and sanitized error handling |
| Credential committed to source | Scanner rules, ignored local configuration, CI gate in P1 |
| Live data used as public fixture | Explicit denylist and separate live acceptance storage |
| Dependency compromise | Locked dependencies, license review, provenance, and release inventory in later gates |
| Local denial of service | Input limits, bounded wake work, SQLite busy handling, and operator recovery |

## Authentication requirements

The normative local authentication decision is ADR 0002. Tests in later milestones must
cover one-time bootstrap and enrollment, role injection, session expiry, Origin and CSRF,
replay, namespace crossover, stale revisions, principal-kind separation, and local-only
recovery.

## Residual risks

- A local operator with filesystem access can read or alter unencrypted state.
- Malware in the same user context can bypass assumptions made by loopback binding.
- Browser compromise can act within a valid session.
- The deterministic provider does not validate the safety of real model output.
- A reference channel does not validate real provider delivery or privacy behavior.
- One SQLite writer and one-host Compose topology do not provide availability guarantees.

These are explicit limitations, not deferred claims.
