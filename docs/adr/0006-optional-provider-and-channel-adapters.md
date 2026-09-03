<!-- SPDX-License-Identifier: Apache-2.0 -->

# ADR 0006: Optional Provider and Channel Adapters

- Status: Accepted for P7 development
- Decision date: 2026-09-03
- Scope: P7 provider-neutral HTTP JSON adapters and local composition

## Context

The accepted P6 stack has stable intelligence and channel ports, exact-effect approval,
dispatch-time authority revalidation, bounded attempts, ambiguity handling, and durable
replay. P7 needs to prove that network adapters can implement those ports without making a
network provider part of the reference path or allowing an untrusted response to become an
authority source. A generic HTTP transport is not evidence of compatibility with any named
model, chat, or email provider.

## Decision

P7 adds two stateless, provider-neutral adapters at the composition edge:

- `http_json_v1` intelligence maps a minimal canonical request to a finite semantic result;
- `http_json_v1` channel maps an already approved `ChannelEffect` to finite delivery and
  reconciliation results.

The default allowlisted modes remain `deterministic` and `reference`. Network modes require
an explicit operator opt-in plus a fixed endpoint, protocol version `dc-http-json-v1`, and
a readable credential file. Configuration is process-startup-only. Browser requests,
Studio, model output, effect destinations, and provider responses cannot select a mode,
endpoint, credential, redirect, or transport policy.

The implementation uses the Python standard-library HTTP client. No provider SDK or new
runtime dependency is introduced. HTTPS with certificate verification is required outside
tests. Plain HTTP is allowed only when the endpoint hostname is an IP loopback literal and
the explicit test-only loopback permission is enabled. URL userinfo, fragments, query
strings, non-HTTP(S) schemes, redirects, and endpoints outside that rule fail closed.

Credentials are opaque bytes read only by the adapter construction edge from an
operator-created, Git-ignored file. They are placed only in an authorization header for the
fixed request. They do not enter request bodies, SQLite, audit, evidence, exceptions,
diagnostics, URLs, command arguments, Studio, or API responses. Environment injection of
credential values is not supported by the public P7 composition root.

Every request and response is strict JSON with exact fields, a protocol version, bounded
bytes, bounded connect/read/total time, and at most one retry before request bytes may have
been accepted. Redirects are refused. Errors reduce to a finite safe category, protocol
version, result class, and digest; raw bodies, endpoints, credentials, and private payloads
are never reflected.

Model responses contain only one of `proposal`, `no_op`, `wait`, or `escalation` and the
minimal semantic fields for that result. The adapter reconstructs `Decision`,
`EffectProposal`, namespace, actors, identifiers, timestamps, Mandate/policy revisions,
destination constraints, proposal validity, and idempotency from the server request. Any
unknown field, authority-shaped field, wrong type, invalid JSON, oversized body, or result
outside the current Mandate fails closed. A model response never creates an approval,
changes membership, or invokes a channel.

Channel requests carry the complete approved effect binding and the existing effect
idempotency key. Provider output cannot change destination, action, payload, constraints,
namespace, proposal, Mandate, policy, approval, attempt, lease, or fencing bindings. The
finite outcomes are `succeeded`, `known_not_executed`, `retryable_failure`,
`permanent_failure`, and `ambiguous`. A timeout or disconnect after request submission is
`ambiguous`, so it is never blindly retried. Reconciliation returns only
`confirmed_applied`, `confirmed_absent`, or `still_unknown`; only confirmed absence permits
the existing bounded retry path. The adapter defaults to `still_unknown` if reliable
reconciliation is not configured by the contract.

## Runtime and evidence boundary

Public tests and `make check` use synthetic data and an isolated loopback stub. The stub is
not a live provider. An isolated Compose runtime profile supplies temporary read-only
credential files and a loopback-only stub, exercises success, refusal, ambiguity,
reconciliation, restart/replay, log redaction, and cleanup, then proves zero containers,
networks, volumes, credential files, and stub processes remain.

Live-provider acceptance is a separately authorized, separately stored, non-public
procedure. P7 public evidence records human evaluation and live-provider evidence as
`not_evaluated`. Passing P7 supports only the claim that optional adapter contracts passed;
it does not support named-provider compatibility, real delivery, production reliability,
privacy, security, pilot readiness, or production readiness.

## Consequences

- The deterministic and reference adapters remain the install, test, Compose, and Golden
  Path defaults.
- Network and credential capabilities stay outside core, governance, application policy,
  and stable ports.
- Existing P5/P6 policy, RBAC, exact approval, dispatch revalidation, replay, attempt,
  fencing, ActionResult, and audit semantics remain authoritative.
- P7 is stateless and adds no migration 008.
- Supporting a named provider later requires its own contract mapping and live acceptance.

## Rejected alternatives

- Dynamic import paths or operator-supplied class names: they create an arbitrary-code
  loading boundary.
- Provider SDKs in core/application: they reverse the dependency direction.
- Endpoint selection from content or effect destination: it permits SSRF and authority
  confusion.
- Automatic redirects or TLS-disable flags: they weaken the fixed trust boundary.
- Provider acknowledgements as approval: they conflate execution evidence with HUMAN
  authority.
- Blind retry after timeout: it can duplicate an ambiguous external effect.

## Related documents

- [P7 acceptance contract](../p7/acceptance.md)
- [P7 adapter Golden Path](../p7/adapter-golden-path.md)
- [Target architecture](../architecture/target-architecture.md)
- [Threat model](../security/threat-model.md)
- [Privacy boundary](../security/privacy-boundary.md)
