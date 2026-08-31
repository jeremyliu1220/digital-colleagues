<!-- SPDX-License-Identifier: Apache-2.0 -->

# v0.1 Capability Matrix

The v0.1 boundary follows
[ADR 0003](../adr/0003-colleague-experience-and-post-v0.1-boundary.md). Evaluation terms
come from the [Colleague Experience Evaluation](colleague-experience-evaluation.md), and
deferred capabilities are described only as a non-committing
[Post-v0.1 Capability Outlook](post-v0.1-capability-outlook.md).

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
| Typed headless HTTP edge | Yes | P3 minimal mapping | Injected server context; P4 authentication explicitly absent |
| Local Studio and Compose Golden Path | Yes | P4 planned | Local UI, bootstrap authentication, builder, work, approval, and audit only |
| Wake reason and trigger-class views | Yes | P4 planned | Explain existing durable causality; do not infer authority |
| Exact-effect proposal inbox | Yes | P4 planned | Display and decide the exact `EffectProposal` revision; human approval remains required |
| Colleague-experience evaluation points | Yes | P4 planned | Classify synthetic, offline, human, and live-provider evidence; no improvement claim yet |
| Revisioned policy builder | Yes | P5 planned | Working hours, allowed triggers, proactivity, interruptions, budgets, stop, and escalation; Profile remains separate from Mandate |
| Semantic Memory | No | Post-v0.1 outlook only | Not a v0.1 commitment and never an authority source |
| Skill Learning or governed Skill system | No | Post-v0.1 outlook only | Requires an independent gate, provenance, permissions, versioning, and rollback |
| Shared knowledge or multi-person collaboration | No | Post-v0.1 outlook only | Requires namespace, ownership, authorization, revocation, and abuse testing |
| Self-initiated autonomy | No | Deferred beyond earlier post-v0.1 stages | Consider only after separately gated memory, proactivity, collaboration, and Skill work |
| Real model providers | Optional | P7 planned | Not required for the deterministic reference path; separate live-provider acceptance does not establish real-provider pilot readiness |
| Live chat or email providers | Optional | P7 planned | Not required for the deterministic reference path; live-provider acceptance remains separate and does not establish real-provider pilot readiness |
| PostgreSQL or distributed stores | No | Not implemented | Port seam only |
| High availability | No | Not claimed | Not designed or claimed in v0.1 |
| Production tenant isolation | No | Not claimed | Local reference topology only |
| OIDC, SSO, or SCIM | No | Not implemented | Explicit production gap |
| Encryption at rest | No | Not implemented | Explicit local deployment risk |
| Compliance certification | No | Not claimed | Not claimed |
