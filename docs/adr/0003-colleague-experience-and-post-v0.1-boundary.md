<!-- SPDX-License-Identifier: Apache-2.0 -->

# ADR 0003: Colleague Experience and Post-v0.1 Boundary

- Status: Accepted for Roadmap rebaseline
- Decision date: 2026-08-31
- Scope: P4–P8 planning and the post-v0.1 capability outlook

## Context

The product aims to make governed digital colleagues feel continuous, responsive, and easy
to supervise. That experience must not blur the boundaries among durable work state,
learned information, reusable capabilities, and granted authority. It also must not turn a
future product direction into an unsupported v0.1 commitment.

## Decision

We adopt three upper-level product capabilities for future planning:

1. **Memory and learning** — preserving, retrieving, correcting, and learning information
   or reusable behavior with explicit source and lifecycle controls.
2. **Proactive response** — responding to permitted events and pursuing bounded goals under
   explicit trigger, attention, interruption, stop, and escalation policies.
3. **Multi-person collaboration** — sharing and delegating work or knowledge across people
   and colleagues under namespace, ownership, and authorization controls.

These are a product model, not an implementation claim. The following concepts remain
distinct:

| Concept | Meaning | Authority rule | Roadmap boundary |
| --- | --- | --- | --- |
| Work state | Durable finite work, events, Agenda generations, WakeCycles, decisions, proposals, results, and causal audit | Constrained by the current Mandate and policy at every transition | Core v0.1 path |
| Semantic Memory | Sourced statements or representations retained for later retrieval, with correction and deletion semantics | Never grants permission or expands a Mandate | Post-v0.1 |
| Skill | A reusable behavior or executable capability with provenance, version, permissions, and rollback | May act only through separately granted capabilities and Mandate authority | Governed system is post-v0.1 |
| Mandate and policy | Explicit permissions, prohibitions, triggers, budgets, stop conditions, and escalation rules | The authoritative boundary for colleague behavior | Core governance boundary |

Memory and Skills must never become authority sources by themselves. Remembering that an
action occurred, learning a preference, or loading a Skill cannot grant permission to repeat
the action. Profile data remains descriptive; Mandate and policy remain authoritative.

v0.1 remains scoped to governance, durable finite work, exact-effect human approval, causal
audit, and a deterministic local reference path. P4–P6 may absorb only low-risk work that is
compatible with that scope: causal visualization, a proposal inbox, colleague-experience
measurement points, revisioned policy editing, and governance hardening.

Semantic Memory, Skill Learning, shared knowledge, multi-person collaboration, and
Self-initiated autonomy are post-v0.1 capabilities. Their presence in an outlook does not
make them required for P4–P8 or promised for a release.

The architecture remains vendor- and model-neutral. Optional models and providers stay
behind stable ports, and the deterministic reference path remains authoritative for public
acceptance. A model may assist with review, explanation, or recommendation, but model review
cannot replace formal human approval, authentication, authorization, or a Mandate change.

## Evidence and claims

Colleague-experience evidence must identify whether it is synthetic, offline, human, or
live-provider evidence. One class does not silently substitute for another. The current
planning sources contain no human-study sample size, baseline, or success threshold, so the
Roadmap does not claim that colleague experience has already improved.

Future capabilities require independent gates with an explicit permission model, versions,
sources, rollback, and abuse testing. This applies even when a preceding stage has passed.

## Consequences

- P4–P8 can improve visibility, configurability, and governance without importing Semantic
  Memory or open-ended autonomy.
- Evaluation can measure colleague-like behavior while keeping unsupported production,
  security, and human-outcome claims out of the public repository.
- Future memory, proactivity, collaboration, and Skill work must earn its own authority and
  safety acceptance rather than inheriting v0.1 approval.
- Model or provider choice cannot weaken exact-effect approval or audit requirements.

## Related documents

- [Roadmap](../roadmap.md)
- [Colleague Experience Evaluation](../product/colleague-experience-evaluation.md)
- [Post-v0.1 Capability Outlook](../product/post-v0.1-capability-outlook.md)
- [v0.1 Capability Matrix](../product/capability-matrix.md)
