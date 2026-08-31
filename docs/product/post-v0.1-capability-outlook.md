<!-- SPDX-License-Identifier: Apache-2.0 -->

# Post-v0.1 Capability Outlook

Status: non-committing outlook. These stages are not v0.1 requirements, release promises, or
authorization to begin implementation.

## Boundary and sequencing

The accepted v0.1 direction remains governance, persistent finite work, exact-effect human
approval, causal audit, and a deterministic local reference path. Post-v0.1 exploration may
proceed only in the following order, with a separate decision to start and accept every
stage:

1. S1 — Memory loop closure
2. S2 — Memory autonomy and bounded goal-driven proactivity
3. S3 — Knowledge decentralization and multi-person collaboration
4. S4 — Governed Skill system
5. Only then, consideration of Self-initiated autonomy

Passing one stage does not authorize the next. Every stage needs an independent Gate, an
explicit permission model, versioned inputs and behavior, attributable sources, rollback or
revocation, and misuse and abuse testing. Memory and Skills never grant authority; the
current Mandate and policy remain authoritative.

## S1 — Memory loop closure

Scope: close the capture, retrieval, citation, correction, supersession, retention, deletion,
and feedback loop for Semantic Memory. Keep work state separate from remembered statements
and require sources for retained claims.

- **Independent Gate:** demonstrate source-preserving retrieval, correction and deletion,
  stale-memory refusal, and no authority expansion.
- **Permission model:** define who may capture, read, correct, share, retain, and delete each
  memory within its namespace.
- **Versions and sources:** version memory records, extraction or synthesis rules, source
  references, and corrections; surface conflicts rather than silently merging them.
- **Rollback:** support revocation, deletion, restoration to a prior accepted version where
  policy permits, and re-indexing without retaining revoked content.
- **Abuse tests:** cover poisoning, source spoofing, cross-namespace retrieval, retention
  bypass, deletion failure, prompt injection, and attempts to turn memory into permission.

## S2 — Memory autonomy and bounded goal-driven proactivity

Scope: permit explicitly bounded use of accepted memory to pursue human-granted goals under
allowed triggers, working hours, attention budgets, notification policies, stop conditions,
and escalation rules.

- **Independent Gate:** show that proactive behavior is explainable, budgeted, stoppable,
  interruptible, and unable to invent a goal or permission.
- **Permission model:** bind each goal, trigger class, channel, resource, budget, and escalation
  path to a current Mandate and policy revision.
- **Versions and sources:** version goals, policies, derived plans, memory inputs, and model or
  rule configurations used for each initiated action.
- **Rollback:** pause or revoke a goal, restore a prior policy revision, cancel pending work,
  and invalidate proposals produced under superseded authority.
- **Abuse tests:** cover notification flooding, budget evasion, trigger amplification, stale
  goals, hidden escalation, coercive suggestions, unauthorized proposals, and stop failure.

## S3 — Knowledge decentralization and multi-person collaboration

Scope: introduce governed ownership, delegation, and sharing of knowledge and work across
multiple people, colleagues, and namespaces. This is not a v0.1 collaboration-platform
commitment.

- **Independent Gate:** prove that ownership, delegation, conflict handling, attribution,
  revocation, and namespace isolation remain inspectable end to end.
- **Permission model:** define owner, steward, contributor, reader, delegate, approver, and
  auditor capabilities without converting a colleague or service into a human principal.
- **Versions and sources:** version shared knowledge, grants, delegations, merges, corrections,
  and contributor attribution.
- **Rollback:** revoke access or delegation, restore prior knowledge versions, unwind pending
  shares, and preserve an audit-safe tombstone without leaking removed content.
- **Abuse tests:** cover confused deputy behavior, unauthorized resharing, collusion, privilege
  escalation, cross-tenant inference, attribution removal, conflicting edits, and replayed
  delegation.

## S4 — Governed Skill system

Scope: add discoverable, installable, versioned Skills only after memory and collaboration
boundaries are proven. Skill Learning, if ever proposed, remains subordinate to the same
Gate and cannot silently publish or activate learned behavior.

- **Independent Gate:** demonstrate provenance verification, explicit installation and
  activation, capability confinement, reproducibility, disablement, and safe removal.
- **Permission model:** separate permission to inspect, install, activate, invoke, update, and
  publish a Skill; execution remains bounded by the caller's Mandate and policy.
- **Versions and sources:** pin Skill packages, manifests, dependencies, generated behavior,
  training or derivation sources, and compatibility declarations.
- **Rollback:** disable or uninstall a Skill, restore a known version, revoke capabilities,
  and invalidate work or proposals that depend on an unaccepted revision.
- **Abuse tests:** cover malicious packages, dependency substitution, capability escalation,
  data exfiltration, self-modification, provenance laundering, unsafe updates, and attempts to
  use a Skill as authority.

## Later consideration — Self-initiated autonomy

Self-initiated autonomy may be considered only after S1–S4 have independently passed and a
new product, governance, and threat decision explicitly defines its purpose and boundaries.
It requires its own Gate, permission model, versioning, attributable sources, rollback,
shutdown and escalation controls, and adversarial abuse testing. It is not implied by bounded
event response, proactive suggestions, model review, or any earlier stage.

All stages remain vendor- and model-neutral. Model-assisted review may inform a human, but it
cannot substitute for formal human approval, authorization, or an accepted Mandate revision.
