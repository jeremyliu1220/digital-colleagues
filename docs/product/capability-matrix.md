<!-- SPDX-License-Identifier: Apache-2.0 -->

# v0.1 Capability Matrix

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
| Semantic memory | Partial | Not implemented | Explicit experimental boundary; not a release claim |
| Real model providers | No | Not implemented | Adapter work after the deterministic path |
| Live chat or email providers | No | Not implemented | Later adapter milestone and separate acceptance |
| PostgreSQL or distributed stores | No | Not implemented | Port seam only |
| High availability | No | Not claimed | Not designed or claimed in v0.1 |
| Production tenant isolation | No | Not claimed | Local reference topology only |
| OIDC, SSO, or SCIM | No | Not implemented | Explicit production gap |
| Encryption at rest | No | Not implemented | Explicit local deployment risk |
| Compliance certification | No | Not claimed | Not claimed |
