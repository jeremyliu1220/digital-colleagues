<!-- SPDX-License-Identifier: Apache-2.0 -->

# v0.1 Capability Matrix

The v0.1 boundary follows
[ADR 0003](../adr/0003-colleague-experience-and-post-v0.1-boundary.md). Evaluation terms
come from the [Colleague Experience Evaluation](colleague-experience-evaluation.md), and
deferred capabilities are described only as a non-committing
[Post-v0.1 Capability Outlook](post-v0.1-capability-outlook.md).

Current checkpoint: P8 passed independent acceptance and was fast-forward merged from
`codex/p8-release-readiness` to `main`. The accepted P8 commit is
`0bb80ab187932fbad42fbf665b8310987609a1f5`. Historical P0–P8 artifacts, evidence,
acceptance contracts, receipts, and migrations remain unchanged. The result is only a
**v0.1 local reference release candidate** for version `0.1.0`: no tag has been created,
and nothing has been published, uploaded, or formally released. It is not
production-ready and establishes no production security, high availability, enterprise
IAM, real-provider readiness,
compliance, or other excluded capability. Human evaluation, live-provider evidence, and
the unmeasured five-minute target remain `not_evaluated`. Post-v0.1 S1–S4 and Self-initiated
autonomy have not started and do not start automatically.

P9 now defines a documentation-only path toward a future v0.2 Public Pilot. It does not
change any implemented v0.1 status below. Planned v0.2 objects, phases, evidence, and claim
limits are in the [v0.2 capability matrix](v0.2-public-pilot-capability-matrix.md) and
[v0.2 product brief](v0.2-public-pilot-product-brief.md).

| Capability | v0.1 target | Current status | Boundary |
| --- | --- | --- | --- |
| Colleague registry | Yes | P3 headless persistence | Local namespaced SQLite reference only |
| Profile and Mandate | Yes | P3 persisted | Profile is descriptive; Mandate is authoritative and revisioned |
| Responsibilities and finite work | Yes | P3 persisted Golden Path | Finite synthetic work only in the current path |
| Event, Agenda, and WakeCycle | Yes | P3 bounded runtime | Durable triggers, generation coalescing, leases, fencing, restart |
| Human roles | Yes | P2 complete | `tenant_admin`, `colleague_user`, `auditor` only |
| Human/model/service principal separation | Yes | P2 complete | Durable disjoint kinds; no conversion to human |
| Exact-effect human approval | Yes | P3 transactional path | Revalidated before commit and dispatch; caller authority rejected |
| Reference channel and ActionResult | Yes | P3 synthetic adapter | No network, real provider, account, workspace, or message |
| Audit causality | Yes | P3 immutable safe records | Payload bytes become digests or safe projections in audit |
| Single `state.sqlite` | Yes | P3 implemented | Injectable path, WAL, foreign keys, immutable migration checksums |
| Typed headless HTTP edge | Yes | P4 accepted main baseline | Session-derived authority with Pydantic restricted to the HTTP mapping edge |
| Local Studio and Compose Golden Path | Yes | P4 accepted main baseline | Local UI, bootstrap Admin, builder, work, recovery, approval, and audit only |
| Wake reason and trigger-class views | Yes | P4 accepted main baseline | Explains existing durable Event/Timer causality and deterministic no-op; background work uses a restricted SERVICE context |
| Exact-effect proposal inbox | Yes | P4 accepted main baseline | Displays and decides the exact `EffectProposal` revision and digests; human approval remains required |
| Colleague-experience evaluation points | Yes | P4 accepted main baseline | Durable sources distinguish observed, not applicable, and not evaluated; five-minute and human-improvement claims remain unevaluated |
| Revisioned policy builder | Yes | P5 accepted main baseline | Inert exact-revision Profile/Mandate/policy drafts; typed deterministic working hours, triggers, proactivity, notification/interruption, budgets, stop, and escalation |
| Local multi-user governance | Yes | P6 accepted main baseline | Typed RBAC, enrollment/recovery, two-person authority change, approval expiry, scoped audit export, and abuse coverage; no enterprise-IAM or production-security claim |
| Semantic Memory | No | Post-v0.1 outlook only | Not a v0.1 commitment and never an authority source |
| Skill Learning or governed Skill system | No | Post-v0.1 outlook only | Requires an independent gate, provenance, permissions, versioning, and rollback |
| Shared knowledge or multi-person collaboration | No | Post-v0.1 outlook only | Requires namespace, ownership, authorization, revocation, and abuse testing |
| Self-initiated autonomy | No | Deferred beyond earlier post-v0.1 stages | Consider only after separately gated memory, proactivity, collaboration, and Skill work |
| Provider-neutral HTTP JSON model adapter | Optional | P7 accepted main baseline | Explicit opt-in behind stable port; offline loopback contract only; no named-provider claim |
| Provider-neutral HTTP JSON channel adapter | Optional | P7 accepted main baseline | Exact-approved effects, ambiguity/reconciliation, explicit opt-in; no live-delivery claim |
| Upgrade, backup, restore, and release rollback | Yes | P8 accepted main baseline | Local SQLite online backup, validated atomic restore, matching-code rollback; no down-migration or availability claim |
| Redacted support diagnostics | Yes | P8 accepted main baseline | Allowlisted bounded local bundle; no raw logs, audit export, state, credentials, private payload, or path |
| Reproducible release candidate | Yes | P8 accepted main baseline | Six unpublished `0.1.0` artifacts compared byte-for-byte; OCI claim limited to immutable inputs/content/runtime |
| Release supply-chain inventory | Yes | P8 accepted main baseline | Python, npm, build, OCI base, Actions, and tool metadata; declared-license review is not legal advice |
| Real model providers | Optional | Separate live acceptance `not_evaluated` | Not required for deterministic reference path; generic HTTP contract is not named-provider compatibility |
| Live chat or email providers | Optional | Separate live acceptance not evaluated | No named channel is implemented or claimed; live acceptance remains non-public and separate |
| PostgreSQL or distributed stores | No | Not implemented | Port seam only |
| High availability | No | Not claimed | Not designed or claimed in v0.1 |
| Production tenant isolation | No | Not claimed | Local reference topology only |
| OIDC, SSO, or SCIM | No | Not implemented | Explicit production gap |
| Encryption at rest | No | Not implemented | Explicit local deployment risk |
| Compliance certification | No | Not claimed | Not claimed |
