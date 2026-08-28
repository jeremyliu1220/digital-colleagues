<!-- SPDX-License-Identifier: Apache-2.0 -->

# v0.1 Capability Matrix

| Capability | v0.1 target | Current status | Boundary |
| --- | --- | --- | --- |
| Colleague registry | Yes | Contract only | Namespaced persistence begins in P3 |
| Profile and Mandate | Yes | P2 complete | Profile is descriptive; Mandate is authoritative |
| Responsibilities and finite work | Yes | P2 contracts complete | Persistence begins in P3 |
| Event, Agenda, and WakeCycle | Yes | P2 contracts complete | No worker or event loop |
| Human roles | Yes | P2 complete | `tenant_admin`, `colleague_user`, `auditor` only |
| Human/model/service principal separation | Yes | P2 complete | Durable disjoint kinds; no conversion to human |
| Exact-effect human approval | Yes | P2 pure policy complete | Complete canonical proposal digest, exact typed constraints, expiry, replay, role, and namespace checks |
| Reference channel and ActionResult | Yes | Result contract only | Channel execution begins in P3 |
| Audit causality | Yes | P2 contract chain complete | Persistence and inspection begin later |
| Single `state.sqlite` | Yes | Not implemented | P3 local topology only |
| Semantic memory | Partial | Not implemented | Explicit experimental boundary; not a release claim |
| Real model providers | No | Not implemented | Adapter work after the deterministic path |
| Live chat or email providers | No | Not implemented | Later adapter milestone and separate acceptance |
| PostgreSQL or distributed stores | No | Not implemented | Port seam only |
| High availability | No | Not claimed | Not designed or claimed in v0.1 |
| Production tenant isolation | No | Not claimed | Local reference topology only |
| OIDC, SSO, or SCIM | No | Not implemented | Explicit production gap |
| Encryption at rest | No | Not implemented | Explicit local deployment risk |
| Compliance certification | No | Not claimed | Not claimed |
