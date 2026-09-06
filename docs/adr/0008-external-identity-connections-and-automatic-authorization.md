<!-- SPDX-License-Identifier: Apache-2.0 -->

# ADR 0008: External Identity, Connections, Grants, and Automatic Authorization

- Status: Accepted for P9 planning; implementation deferred to P12-P14
- Decision date: 2026-09-07
- Scope: v0.2 Public Pilot model/provider identity, connector authority, and low-risk effects

## Context

The v0.1 runtime requires exact HumanApprovalDecision for effects and keeps MODEL, SERVICE,
and HUMAN principals distinct. Public Pilot connectors need delegated external identity and
a narrow automatic path for routine low-risk effects. Authentication cannot be mistaken
for authorization, and automatic policy cannot be recorded as a fabricated human decision.

## Decision

### External identity and authority objects

An **ExternalConnection** is a managed credential connection to one external
provider/application/account. It proves an authentication relationship and lifecycle
state; it grants no resource or action.

A **ConnectorGrant** is an Admin-created, revisioned, resource/action-specific governance
binding. It references one ExternalConnection and is bounded by the exact current Mandate
and Policy. A connection is unusable outside its grants. Grant revision, connection state,
source/data version, namespace, action, resource, budget, and effect are revalidated before
dispatch. Revoking a connection invalidates its grants and pending effects.

A **SourceReference** records a safe external locator, version/etag/digest, and source class;
a **SourceCursor** records bounded incremental progress. Neither stores a full body by
default, becomes S1 Semantic Memory, or grants authority.

### OpenAI boundary

P12's first provider is OpenAI and its fixed candidate is `gpt-5.5`. It uses the Responses
API, Structured Outputs, and explicit `store:false`. It sends no function/hosted tool, MCP,
browser/computer use, shell, connector credential, or execution right. Model output is
untrusted finite semantic data; server code reconstructs namespace, principals, IDs, time,
Mandate/Policy/Grant/source versions, effect fields, and budget. The model cannot change
governance, roles, connections, grants, or approvals.

Inputs/outputs, usage/cost, timeout/retry, refusal/incomplete/schema errors, prompt layers,
prompt injection, and model provenance are bounded and auditable. P12 rechecks official
docs and actual project access. An incompatible model requires a Change Decision rather
than silent substitution.

### Microsoft 365 boundary

Each Agent uses one dedicated work/school account through delegated device-code public-
client OAuth. Supported App modes are a project-operated verified multi-tenant public
client and an enterprise-provided single-tenant public client App ID. User consent, Admin
pre-consent, and selected-resource configuration remain distinct.

Outlook uses one mail delta SourceCursor per allowed folder. Teams has no public webhook or
cloud relay; it polls only Admin-allowlisted chats using a bounded date window and message
ID/etag deduplication. Planner updates use the latest ETag with `If-Match`; 409, 412, or
stale ETag requires reread and reevaluation. SharePoint fetches selected site/folder content
read-only and refuses unbound resources. External bodies are bounded temporary context,
redacted as required, and discarded; they do not become Semantic Memory.

Graph 401/403/429/5xx, refresh/revoke, throttling, ambiguous sends, retry,
reconciliation, duplicate/replay handling, and restart cursors require later synthetic and
private live gates. Loopback does not establish named-provider compatibility.

### AutomaticEffectAuthorization

An **AutomaticEffectAuthorization** is a durable non-human record produced only when the
server proves that an exact effect satisfies the current low-risk policy, Mandate, Policy,
ConnectorGrant, source/data version, ETag/revision, connection state, participant/resource
set, and budget. It records the authoring SERVICE/rule identity and proof inputs. It is not
a HumanApprovalDecision.

`auto_within_boundary` is limited to:

- routine replies in an existing internal email thread or existing allowlisted Teams chat
  with exactly unchanged original participants, same tenant, no attachment, and no new
  mention; and
- exact Planner actions whose plan, task, fields, assignee, ETag/data version, Mandate,
  Policy, ConnectorGrant, and budget all match.

`require_approval` applies to a new recipient/chat, external domain, attachment, new
mention, cross-tenant message, or ambiguous authority, binding, version, or risk. `deny`
applies outside authority; with stale data/ETag/revision, revoked/expired connection,
budget/rate overflow, cross-Agent/cross-tenant access, capability self-grant, or any
unproved automatic condition.

AutomaticEffectAuthorization and HumanApprovalDecision have different schemas, authoring
rules, consumption rules, and audit event types. Only an authorized HUMAN can author the
latter; MODEL/SERVICE can never simulate one. Dispatch revalidates either exact authority
path. Self-reply, Agent-to-Agent loops, duplicate message/effect, replay, ambiguity, and
notification flooding fail closed or enter bounded reconciliation.

The built-in project tracker does not request `delete_task` by default. Any third-party
package requesting delete capability is shown as a separate prominent permission.

### Planned external-event flow

```text
External event -> ExternalConnection authentication -> ConnectorGrant resource check
-> bounded source fetch -> temporary source context
-> SourceReference/cursor/digest/safe projection -> existing Event/Agenda/Wake/Decision path
-> exact EffectProposal -> auto-policy evaluation or Human approval
-> dispatch-time revalidation -> effect attempt/result/reconciliation -> causal audit
```

All provider output, external content, localized prompts, package data, and UI state remain
untrusted. Unknown, missing, stale, revoked, cross-namespace, cross-Agent, digest/schema
mismatch, unbound resource, ambiguous authority, or budget overflow fails closed.

## Consequences

- Credential possession and resource/action authority are mechanically separate.
- Low-risk automation remains attributable without weakening human-approval identity.
- Existing exact-effect proposal, attempt, result, ambiguity, reconciliation, replay, and
  audit semantics remain the base rather than being bypassed.
- P12-P14 require independent static/synthetic/private-live gates in their fixed order.

## Rejected alternatives

- Treating OAuth scope or token possession as ConnectorGrant: too broad and unauditable.
- Recording an automatic rule as HumanApprovalDecision: identity falsification.
- Letting model output choose resource, authority, or dispatch configuration: confused
  deputy and prompt-injection risk.
- Public webhook/cloud relay for Teams: outside the fixed local-first boundary.
- Retaining external bodies as memory: starts S1 without its independent gate.
- Blind retry of ambiguous sends or stale Planner update: duplicate/overwrite risk.

## Claim boundary

P9 implements no OpenAI call, Graph call, OAuth flow, token storage, connection, grant,
source fetch, or automatic-effect runtime. Actual project, tenant, App, account, consent,
and provider behavior are `not_evaluated` until their private live gates.
