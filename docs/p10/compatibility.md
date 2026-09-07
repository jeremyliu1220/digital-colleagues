<!-- SPDX-License-Identifier: Apache-2.0 -->

# P10 Metadata and Route Compatibility Inventory

## Stable metadata

- Product: `Digital Colleagues`
- API title: `Digital Colleagues Local API`
- Python/OpenAPI version: `0.2.0.dev0`
- Studio/display version: `0.2.0-dev.0`
- Maturity: `Public Pilot development candidate`

## Retained routes

P10 changes no handler, dependency, request/response schema, method, status code,
authorization, CSRF, replay, or namespace behavior. The composed local API retains these
37 route-method pairs (FastAPI's generated documentation routes are not product routes):

```text
GET  /audit/{correlation_id}
GET  /auth/session
GET  /colleagues/drafts
GET  /colleagues/drafts/{draft_id}
GET  /evaluation/metrics
GET  /governance/rbac
GET  /governance/state
GET  /health
GET  /p5/evaluation/metrics
GET  /p5/studio/state
GET  /studio/state
POST /auth/bootstrap/exchange
POST /auth/enrollment/exchange
POST /colleagues
POST /colleagues/drafts
POST /colleagues/drafts/{draft_id}/cancel
POST /colleagues/drafts/{draft_id}/confirm
POST /colleagues/drafts/{draft_id}/review
POST /colleagues/preview
POST /governance/admin-enrollments/proposals
POST /governance/audit/export
POST /governance/changes/{scope}/{proposal_id}/decision
POST /governance/changes/colleague/{proposal_id}/apply
POST /governance/changes/tenant/{proposal_id}/apply
POST /governance/credentials/{credential_id}/revoke
POST /governance/drafts/{draft_id}/proposals
POST /governance/enrollments/admins
POST /governance/enrollments/auditors
POST /governance/enrollments/users
POST /governance/memberships/proposals
POST /governance/recovery
POST /governance/session/active-colleague
POST /proposals/{proposal_id}/decision
POST /runtime/process
POST /runtime/triggers
POST /work
PUT  /colleagues/drafts/{draft_id}
```

The separate headless mapping retains `POST /events`, `POST
/proposals/{proposal_id}/approval`, and `GET /history/{correlation_id}`.

The `/p5` names are compatibility paths, not product vocabulary. Existing internal P3-P7
symbol/module names remain historical implementation detail. P10 adds no placeholder
`/api/v1` route. A future public API uses stable terms under `/api/v1`; aliasing,
deprecation, or removal requires a separate contract and compatibility gate.
