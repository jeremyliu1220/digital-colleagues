<!-- SPDX-License-Identifier: Apache-2.0 -->

# v0.1 Capability Matrix

| Capability | v0.1 target | Boundary |
| --- | --- | --- |
| Colleague registry | Yes | Namespaced local reference |
| Profile and Mandate | Yes | Profile is descriptive; Mandate is authoritative |
| Responsibilities and finite work | Yes | Persisted and revisioned |
| Event, Agenda, and WakeCycle | Yes | Deterministic reference behavior first |
| Human roles | Yes | `tenant_admin`, `colleague_user`, `auditor` |
| Human/model/service principal separation | Yes | Durable types; no conversion to human |
| Exact-effect human approval | Yes | Revision, expiry, replay, role, and namespace checks |
| Reference channel and ActionResult | Yes | No external provider needed |
| Audit causality | Yes | Input through result, with stable identifiers |
| Single `state.sqlite` | Yes | Local topology only; complete namespace on every record |
| Semantic memory | Partial | Explicit experimental boundary; not a release claim |
| Real model providers | No | Adapter work after the deterministic path |
| Live chat or email providers | No | Later adapter milestone and separate acceptance |
| PostgreSQL or distributed stores | No | Port seam only |
| High availability | No | Not designed or claimed in v0.1 |
| Production tenant isolation | No | Local reference topology only |
| OIDC, SSO, or SCIM | No | Explicit production gap |
| Encryption at rest | No | Explicit local deployment risk |
| Compliance certification | No | Not claimed |
