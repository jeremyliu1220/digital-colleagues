<!-- SPDX-License-Identifier: Apache-2.0 -->

# ADR 0010: AgentPackage and ColleagueDeployment lifecycle

Status: Accepted for P11 implementation candidate development on 2026-09-09. This is not
independent P11 acceptance and does not authorize P12.

## Context

The accepted stack has one retained colleague model but no portable inert package format,
package trust ledger, or explicit multi-deployment lifecycle. P11 must add those concepts
without converting descriptive package content into authority, weakening existing
Profile/Mandate/Policy rules, or introducing executable plugins and Agent collaboration.

## Decision

`dc-agent/v1` is canonical UTF-8 JSON inside a bounded one-member ZIP. It admits only
localized inert prompts, a finite requested-capability vocabulary, and an acyclic bounded
declarative workflow. The content and complete manifest have distinct SHA-256 bindings.
Archive inspection never extracts to a general filesystem path.

Registration, Admin trust, installation, deployment-draft review, exact confirmation, and
activation are separate durable operations. A package capability is always a request;
only a human-issued Mandate grants capability and only Policy plus the existing approval
boundary governs effects. GitHub attestation is offline origin evidence and never trust.

`ColleagueDeployment` owns one exact colleague namespace and package binding. Lifecycle is
limited to draft, active, paused, blocked, and retired. Only active deployments execute.
`BEGIN IMMEDIATE`, optimistic revisions, an active-slot constraint, and named SQLite
triggers cap the local execution host at ten active deployments. Revocation alone performs a
system safety transition from active to blocked.

Migration 008 is additive. Existing colleague namespaces receive one active
`legacy/manual` deployment and an inert built-in compatibility binding without changing
or reconstructing authority. An absent Policy remains `legacy_unconfirmed`.

## Consequences

P11 enables package and deployment lifecycle evaluation locally while deliberately adding
no connector grants, model provider, executable Skill runtime, Agent messaging,
collaboration, shared memory, release, or production-readiness claim. Database rollback
uses a verified schema-7 backup with matching code; no down migration exists.
