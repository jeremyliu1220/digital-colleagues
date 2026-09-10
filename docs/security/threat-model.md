<!-- SPDX-License-Identifier: Apache-2.0 -->

# Local Reference Threat Model

## Scope and claim boundary

This model defines requirements for the v0.1 local reference topology. P6 mechanically
tested the local bootstrap/session boundary, revisioned policy, typed RBAC, versioned
membership, enrollment/recovery, proposer/approver separation, approval expiry, scoped
export, namespace/abuse refusal, deterministic execution, SQLite, outbox, and safe audit.
P7 adds contract tests for explicitly optional HTTP JSON adapters using a controlled
loopback stub. Passing either milestone does not establish product security or privacy
effectiveness. Encryption at rest, OIDC, SSO, SCIM, distributed isolation, named-provider
compatibility, and high availability remain gaps.

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
| Adapter mode injection | Exact startup allowlists; browser, Studio, model, and API input cannot select an adapter |
| SSRF or endpoint rebinding | Fixed operator endpoint; HTTPS required except explicit IP-loopback tests; no content-derived URL |
| Credential disclosure at adapter edge | Read-only opaque file, adapter-only access, no value in URL/body/log/error/audit/evidence |
| Redirect or TLS downgrade | Redirects refused; certificate verification always enabled; no disable flag |
| Provider authority injection | Strict response field set; reconstruct every authoritative binding server-side; post-model policy check |
| Provider-directed execution | Finite semantic JSON only; no tool execution, callback, code, browsing, or dynamic import |
| Oversized or malformed provider response | Bounded byte read, exact JSON types/fields/content type, typed safe failure |
| Retry duplicates an uncertain effect | Post-submit timeout/disconnect is ambiguous; no blind retry; reconcile before retry |
| Provider rebinds idempotency | Existing effect key binds canonical effect digest; conflicts fail closed |
| External egress during public tests | Explicit IP-literal loopback allowlist plus negative socket/endpoint tests |
| WAL-inconsistent backup | SQLite online backup API plus snapshot integrity and applied-migration validation |
| Malicious or corrupted backup | Exact archive members, bounded reads, no generic extraction, digest/integrity/schema/manifest validation |
| Restore overwrites valid state | Default-new destination; explicit offline replacement; verified rollback backup; atomic install |
| Restored stale authority or sessions | Documented mandatory session rotation and membership/approval/authority revalidation |
| Diagnostic disclosure | Versioned field allowlist, finite errors, irreversible causal digests, and secret/path/private canaries |
| Mutable release dependency | Python hashes, npm integrity, OCI manifest digests, Action commits, inventory drift gate |
| First-release source confusion | Exact accepted-P7 commit/tree/version descriptor, pre-start backup, separate restored/replaced source bindings, matching-code rollback |
| Host/container toolchain drift | Exact Node/npm execution checks in host and Docker build paths plus runtime-served bounded metadata |
| Release archive includes private residue | Git-object allowlist plus database/backup/log/cache/path/private-data scans |
| Reproducibility overclaim | Byte comparison only for six declared artifacts; OCI claim limited to immutable inputs/content/runtime |

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
- The loopback P7 stub does not validate a named provider's protocol, retention, delivery,
  reliability, privacy, security, or future behavior.
- An operator who enables an adapter chooses an external disclosure boundary; P7 reduces
  fields and validates responses but cannot control a remote service.
- One SQLite writer and one-host Compose topology do not provide availability guarantees.
- Local backups and diagnostic bundles are unencrypted private files whose storage,
  transfer, retention, snapshots, and secure deletion remain operator responsibilities.
- Restoring a valid old backup can intentionally restore revoked or expired historical
  security state; P8 requires rotation/revalidation but cannot determine current real-world
  authority.
- Declared dependency license metadata and local inventory checks are not legal advice or
  a complete third-party security assessment.

These are explicit limitations, not deferred claims.

## v0.2 planning continuation

The [v0.2 Public Pilot threat model](v0.2-public-pilot-threat-model.md) adds future package,
multi-Agent, OpenAI, Microsoft 365, connection/grant, temporary-source, and automatic-
authorization requirements. P9 implements none of those capabilities. This v0.1 model and
all accepted P0-P8 statements remain unchanged in meaning; the v0.2 model cannot be cited
as evidence that a planned control exists or works.

## P10 local distribution additions

P10 adds contract-tested defenses for mutable image selection, bundle/manifest checksum
confusion, malicious manifest execution, unsafe Application Support roots, concurrent
operator mutation, path traversal and destructive purge, wrong file modes, secret mounts
into Studio, FileVault readiness overclaim, quickstart source builds, unbounded Docker
output, and synthetic attestation promotion. The launcher uses exact release/root/Compose
identities, digest-only images, a bounded lock, finite output/errors, and no `eval` or
manifest sourcing. FileVault is read-only readiness evidence, not encryption enforcement.

The separately authorized remote gate adds exact repository/ref/SHA dispatch guards,
publish-job-only package/OIDC/attestation writes, immutable action pins, digest-only image
selection, exact two-platform indexes, keyless signer/issuer/annotation verification,
GitHub provenance verification, public visibility, anonymous pulls, and final workflow
deactivation. Wrong identity, ref, revision, digest, visibility, signer, issuer,
annotation, permission, trigger, synthetic evidence, or mixed lifecycle state fails
closed.

These checks establish only the recorded public registry objects and repeatable remote Mac
quickstart path. They do not prove registry availability over time, dependency safety,
host security, production supply-chain security, formal release readiness, or production
readiness.

## P11 package and deployment threats

P11 treats ZIP structure, JSON, localization, prompts, workflow declarations,
capabilities, attestation output, CLI output, and package source labels as untrusted. Exact
bounds, canonical digests, duplicate/path/link/special-file rejection, a finite acyclic
workflow, offline policy-bound verification, and sanitized errors fail closed. Attestation
proves origin only and cannot grant trust, installation, authority, confirmation, or
activation.

Server-side current membership, exact tenant/colleague namespace, optimistic revision,
idempotency request digest, causal audit, `BEGIN IMMEDIATE`, active slots, and SQLite
triggers defend lifecycle mutation and activation races. Revocation blocks active exact
bindings. Inactive deployments cannot enter API or worker execution. P11 does not defend
an executable plugin runtime, connector lifecycle, Agent collaboration, shared memory,
provider behavior, or production deployment because those capabilities are absent.

## P12 B+ continuity planning threats

P12 implements no control below; it fixes future owners and negative requirements:

| Future threat | Required owner and control |
| --- | --- |
| External identity treated as HUMAN | P14-P18 keep ExternalPartyReference outside Principal and reject human approval or `human_decision` satisfaction |
| Project identity becomes authority | P15 limits ProjectScope to Namespace/project_id and revalidates exact authority/source revisions per continuation |
| Lost work at checkpoint boundary | P15 atomically checkpoints required transitions, decisions, effects, reconciliation, shutdown, release, and takeover |
| Hidden chat-state dependency | P15 reconstructs the same state and retrieval digest in a new process with empty chat context |
| Memory becomes authority or silent mutable state | P16 separates admit/reject from lifecycle, versions immutably, bounds retrieval, and enforces revocation/deletion watermarks |
| Raw reply wakes the wrong project | P17 owns exact correlation, quarantines ambiguity, and atomically consumes only matched occurrences once |
| Recovery cursor omits old work | P17 reconstructs from durable incomplete state and performs bounded full/anti-entropy scans after cursor loss or host replacement |
| Transport creates automatic authority | P14 writes only under exact current HUMAN approval; P18 alone adds AutomaticEffectAuthorization |
| Tracker repairs missing security primitive | P19 fails if a P13-P18 primitive or required P14 transport is absent |

These requirements remain `static`/`synthetic_offline` planning evidence until their owning
milestones pass. They establish no provider, security-effectiveness, or Public Pilot claim.
