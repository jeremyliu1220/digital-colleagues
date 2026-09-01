<!-- SPDX-License-Identifier: Apache-2.0 -->

# ADR 0004: Revisioned Colleague Policy Model

- Status: Accepted for P5 development
- Decision date: 2026-09-01
- Scope: P5 revisioned colleague builder and deterministic local runtime enforcement

## Context

The existing Profile is descriptive and the Mandate grants responsibilities, capabilities,
constraints, and effect boundaries. P5 must add working hours, durable trigger admission,
bounded proactivity, notification/interruption behavior, wake budgets, stops, and
escalations without turning Profile, legacy free-form text, model output, or Studio state
into authority. Every runtime use must identify the exact policy that applied, and a policy
change must make older authority-bound contexts stale.

Embedding these values in Profile would violate the authority boundary. Leaving them as
untyped Mandate JSON would permit hidden defaults, ambiguous interpretation, and weak
review. Treating each item as unrelated mutable settings would make exact confirmation,
atomic apply, causal binding, and stale rejection difficult to prove.

## Decision

P5 introduces a frozen, typed, independently revisioned `ColleaguePolicy`. It is an
authoritative value bound by complete namespace to one active Mandate. The active colleague
configuration consists of three explicit heads:

```text
Profile revision (descriptive)
Mandate revision (authority and effect boundary)
ColleaguePolicy revision -> exact Mandate ID/revision (runtime governance)
```

The policy cannot grant a responsibility, capability, or effect absent from its bound
Mandate. Every accepted trigger, wake, Decision, proposal, approval, dispatch, stop, and
escalation records or resolves both the exact Mandate and policy revision. Revalidation
occurs before wake/proposal, after model output before proposal persistence, and before
approval/dispatch. An authority-affecting head change makes older proposals, approvals,
and SERVICE runtime contexts stale.

One revisioned draft contains complete proposed values for Profile, Mandate, and policy,
their three base revisions, explicit defaults, a canonical classified diff, and a canonical
digest. Drafts are inert. One transactional compare-and-swap confirmation updates every
changed head or none, then records causal audit and replay state. Complete-base comparison
ensures that two same-base drafts cannot both succeed even when they edit different heads.

Policy fields use finite typed enums and values only:

- IANA timezone plus weekly local windows;
- allowed existing durable Event/Timer trigger kinds;
- bounded proactivity mode;
- notification and interruption modes;
- positive wake limit and finite UTC bucket period;
- outside-hours outcome;
- finite stop and escalation condition sets; and
- explicit active/stopped run state.

Weekly windows are local wall-clock policy. Runtime evaluates an injected UTC instant by
IANA conversion; a cross-midnight window spills into the next weekday, both DST rollback
folds follow the same local window, and nonexistent local instants are not fabricated.
Budget counters are durable, namespaced, restart-safe, and deduplicate trigger occurrence
identity across trigger classes.

Defaults are typed records with a versioned `p5_system_default` source and appear in review.
Unknown, missing, contradictory, blank, or unclassifiable authority input fails closed.
Legacy P4 free-form working-hours data remains descriptive and receives
`legacy_unconfirmed` policy status until an Admin confirms a typed P5 draft; it is never
parsed into authority.

Stop and escalation use finite conditions, not code or natural-language expressions.
Resume is an explicit reviewed and confirmed policy revision. Escalation creates safe local
state only; it is not approval, Mandate change, effect permission, or a real notification.

## Consequences

- Profile remains non-authoritative while runtime governance becomes typed, reviewable,
  persisted, auditable, and deterministic.
- Profile, Mandate, and policy can evolve independently, but one draft confirmation checks
  the complete active tuple and applies all changes atomically.
- Policy-only changes can stale authority-bound runtime records without pretending that
  descriptive Profile edits grant authority.
- Existing P4 colleagues remain compatible without guessing authority from legacy text.
- SQLite gains additive schema and counters behind ports; the one-file local reference
  remains neither a production tenant boundary nor a distributed-store claim.
- Notification/interruption policy governs visibility and timing only. It cannot weaken
  exact-effect approval or authorize a provider effect.

## Rejected alternatives

- **Store policy in Profile:** rejected because preferences and identity presentation are
  not grants.
- **Parse P4 working-hours text:** rejected because natural language is ambiguous and could
  silently create authority.
- **Use unversioned settings rows:** rejected because review, replay, causality, and stale
  rejection require exact immutable revisions.
- **Silently rebase concurrent drafts:** rejected because an Admin must confirm the exact
  content and authority diff shown.
- **Treat escalation as notification or approval:** rejected because it would cross the
  effect and human-approval boundaries.

## Claim boundary

This decision governs only the deterministic local reference runtime. It does not add
Semantic Memory, Skills, shared knowledge, Self-initiated autonomy, arbitrary scheduling,
real providers/channels, P6-complete governance, production tenancy, or production
readiness.

## Related documents

- [P5 acceptance contract](../p5/acceptance.md)
- [P5 Golden Path](../p5/golden-path.md)
- [Target architecture](../architecture/target-architecture.md)
- [ADR 0003](0003-colleague-experience-and-post-v0.1-boundary.md)
