<!-- SPDX-License-Identifier: Apache-2.0 -->

# P7 Optional Adapters Acceptance Contract

Status: fixed development contract. P7 may be described only as **development complete,
awaiting independent acceptance** after every gate below passes. This contract is fixed
before product, test, Compose, or evidence implementation and must not be deleted, weakened,
or rewritten to fit an implementation result.

## Baseline, branch, and historical boundary

P7 starts from the independently accepted P6 `main` baseline
`7e6f4c4dc50b675afb60b6e160fe4f15312dd6c8` on
`codex/p7-optional-adapters`. The fixed base must be the exact merge-base of the P7
acceptance, implementation, and evidence commits.

P0-P6 acceptance records, Golden Paths, artifacts, evidence, provenance receipts,
fingerprints, and migrations 001-007 remain byte-unchanged. P7 must not invoke historical
evidence collectors. It adds no migration 008. The repository Gate is ancestry- and
content-based so it can later pass on a fast-forward `main`; only the evidence writer
requires the exact development branch.

P7 adds one provider-neutral HTTP JSON intelligence adapter and one provider-neutral HTTP
JSON channel adapter behind the existing stable ports. They are explicitly optional,
default-disabled, stateless, and tested with a local loopback stub. P7 implements no named
provider integration, Semantic Memory, Skill system, shared knowledge, multi-person
collaboration platform, self-initiated autonomy, arbitrary tool execution, background
browsing, enterprise IAM, PostgreSQL, distributed execution, high availability, production
tenancy, encryption at rest, certification, production readiness, pilot readiness, or P8.

## Deterministic reference invariant

- With no P7 configuration, `DeterministicIntelligence` and `ReferenceChannel` remain the
  exact composition defaults.
- Installation, startup, `make check`, Compose, and the public Golden Path require no
  endpoint, credential, provider account, network access, or optional adapter.
- Existing canonical deterministic output, no-op, replay, restart, policy, RBAC, exact
  approval, dispatch, ambiguity, ActionResult, and audit behavior must not drift.
- The public Gate performs no external network call. P7 network tests permit only an
  explicitly enabled IP-literal loopback endpoint and mechanically reject external egress.
- A missing provider account can never skip a synthetic/offline test.

## Architecture and authority invariants

The dependency direction remains:

```text
Pure core <- application and governance -> stable ports
                                   <- intelligence adapters
                                   <- infrastructure and HTTP adapters
```

- HTTP clients, URL/TLS processing, credentials, environment access, and network I/O exist
  only in adapter/composition modules. Core, governance, application contracts, stable
  ports, SQLite, and HTTP mappings remain provider-neutral.
- Model output is untrusted finite data. The adapter rebuilds server-authoritative
  namespace, principals, IDs, UTC times, Mandate/policy bindings, proposal/effect IDs,
  validity, constraints, and idempotency from its trusted input.
- Unknown fields, authority-shaped fields, wrong types, incomplete namespace, digest or
  revision mismatch, and results outside the current Mandate fail closed.
- Neither a model response nor a channel acknowledgement creates a `HumanApprovalDecision`,
  changes authority, impersonates HUMAN, selects an adapter, or expands a Mandate/policy.
- Provider-created effects still traverse P5 policy, P6 RBAC, exact-effect approval by a
  current authorized HUMAN, and dispatch-time revalidation.

## Configuration and credential contract

- Modes use the exact allowlists `deterministic|http_json_v1` and
  `reference|http_json_v1`; no import path or class name is accepted.
- Selecting `http_json_v1` requires at startup a fixed endpoint, protocol
  `dc-http-json-v1`, credential-file path, positive connect/read/total timeouts, positive
  request/response byte limits, and bounded retry setting. Missing, unknown, malformed, or
  conflicting configuration fails closed before service construction.
- The endpoint cannot be derived from content, effect destination, model output, browser,
  Studio, or API input. HTTPS with normal certificate verification is mandatory outside
  tests. HTTP is accepted only for an explicitly enabled IP-literal loopback test endpoint.
- URL userinfo, query, fragment, credential parameters, non-HTTP(S) scheme, and every
  redirect are rejected. No option disables TLS verification.
- Only the composition/adapter edge reads an operator-created regular credential file. The
  path is Git ignored, mounted read-only for Compose, and never emitted. Credential values
  never enter repository, SQLite, migrations, audit, evidence, stdout/stderr, logs, URLs,
  command lines, API/Studio, exceptions, or response bodies.
- Diagnostics expose only a finite category, protocol version, result classification, and
  irreversible digest. They never include raw response bodies, endpoints, credentials, or
  private request payloads.

## Versioned model wire contract

Canonical JSON uses UTF-8, sorted compact encoding, exact field sets, content type
`application/json`, and protocol `dc-http-json-v1`. The request contains only:

- protocol, request kind, schema version, request ID;
- a complete synthetic-safe namespace projection;
- wake/agenda IDs and trigger/work safe projection;
- current Mandate ID/revision and finite allowed effect boundaries;
- policy ID/revision when present; and
- a correlation/causation projection.

It excludes cookies, CSRF, bootstrap/enrollment/recovery/session credentials or digests,
audit exports, unrelated namespace data, and local paths.

A response contains exactly protocol, result kind, and a result object. `result_kind` is
one of `proposal`, `no_op`, `wait`, or `escalation`. Proposal data is limited to effect kind,
destination kind/target, action, payload, and safe projection. Other results carry a bounded
rationale and no effect. Server IDs, namespace, principal, times, approval, Mandate/policy
revision, validity, constraints, and idempotency fields are forbidden response authority.

Invalid JSON/UTF-8/content type, unknown or duplicate semantic fields, authority injection,
oversize, timeout, DNS/connect/TLS failure, 401, 403, 429, 5xx, redirect, and disconnect map
to typed safe adapter failure. Failure produces no proposal, approval, or channel call and
leaves only bounded causal failure state through the existing runtime boundary.

## Versioned channel and reconciliation wire contract

The channel adapter receives only an already exact-approved and dispatch-revalidated
`ChannelEffect`. Its canonical request binds protocol, request kind, schema version,
namespace, proposal/revision/digests, effect kind, immutable destination/action/payload/safe
projection/constraints, Mandate/policy revisions, attempt identity/number, and the existing
effect idempotency key. The same key is used in the provider idempotency header.

The response exact result is one of `succeeded`, `known_not_executed`,
`retryable_failure`, `permanent_failure`, or `ambiguous`, with only a bounded safe result
classification. A timeout or disconnect after submission is `ambiguous` and is never
blindly resent. HTTP 401/403 are permanent, 429/5xx before known acceptance are retryable,
and any uncertain post-submit condition is ambiguous.

Reconciliation binds the same effect key and canonical effect digest. It returns exactly
`confirmed_applied`, `confirmed_absent`, or `still_unknown`. Only reliable proof permits
`confirmed_absent`; lack of reconciliation support returns `still_unknown`. Only confirmed
absence can enter the existing bounded retry path, which again revalidates current policy,
authority, attempt limit, lease, and fencing. Idempotency-key rebinding fails closed.

ActionResult and audit persist only safe projection and digest through existing records;
raw provider response bodies and live receipts are not persisted.

## Runtime, abuse, and restart gate

A controlled IP-loopback stub must exercise startup, model and channel success, explicit
refusals, every response/failure category above, timeout/post-submit disconnect ambiguity,
reconciliation, exact approval, current Mandate/policy/RBAC revalidation, idempotency
rebinding, attempt bounds, lease/fencing, restart/replay, response-size bounds, log/error
redaction, and unexpected-egress prevention. Tests must prove provider output cannot approve,
select endpoints, change authority, or mutate an accepted effect.

Default Compose retains API, worker, Studio, operator, one state volume, deterministic
intelligence, and reference channel. Optional adapters require an explicit profile/config
and temporary read-only credential mount. Published API and Studio ports remain on
`127.0.0.1`; container services may listen on `0.0.0.0` internally. No Compose file contains
a real endpoint, credential, provider ID, account, or sample secret.

The actual isolated Compose Gate must start the optional topology and stub, exercise the
contract, recreate services, prove ambiguous replay/reconciliation behavior, scan logs for
secret/private-data absence, stop normally, and report zero remaining containers, networks,
volumes, temporary credentials, and stub processes. Docker unavailable is `not_evaluated`
and blocks P7 evidence and completion.

## Public/live evidence separation

Public fixtures and `artifacts/p7/summary.json` contain only synthetic/offline values and
safe digests. Provider/account/workspace/conversation/message identifiers, live payloads,
live receipts, personal data, and private acceptance results are forbidden. Human evaluation
and live-provider evidence must both be recorded as `not_evaluated`.

Live acceptance requires separate authorization, named-provider contract work, execution,
and non-public storage. Loopback evidence never becomes live evidence. Passing this Gate
supports only **optional adapter contracts passed** and no named-provider compatibility,
delivery, reliability, privacy, security, production, or pilot claim.

## Required repeatable gates

```bash
git diff --check
python3 -B scripts/check_public_boundary.py .
python3 -B scripts/check_p7_repository.py .
python3 -B scripts/check_p7_provenance.py .
python3 -B scripts/check_p7_architecture.py .
PYTHONPATH=src python3 -B scripts/check_p7_model_adapter.py .
PYTHONPATH=src python3 -B scripts/check_p7_channel_adapter.py .
PYTHONPATH=src python3 -B scripts/check_p7_configuration.py .
PYTHONPATH=src python3 -B scripts/check_p7_abuse.py .
python3 -B scripts/check_p7_compose.py .
python3 -B scripts/check_p7_compose_runtime.py .
PYTHONPATH=src python3 -B scripts/check_p7_golden_path.py
python3 -B scripts/run_p7_unittest_suite.py --start-directory tests --top-level-directory .
make check
make p7-compose-runtime
```

Corresponding Make targets are `p7-repository`, `p7-provenance`, `p7-architecture`,
`p7-model-adapter`, `p7-channel-adapter`, `p7-configuration`, `p7-abuse`, `p7-compose`,
`p7-compose-runtime`, `p7-golden`, and `evidence-p7`. `make check` retains every applicable
P0-P6 regression. Historical evidence targets P0-P6 must not run.

Every aggregate reports zero failures, errors, skips, expected failures, and unexpected
successes. Public-boundary exceptions and runtime cleanup residue are zero.

## Provenance and evidence contract

The P7 provenance receipt covers every changed or added implementation file, classifies all
as new implementation based on public documents and accepted P6 code, and records zero
transformed parent-source entries. No parent working tree, raw evidence, credential, live
provider material, or private acceptance material may be read or copied.

Only after the acceptance and implementation commits exist, every direct/aggregate Gate
passes, Docker runtime is evaluated, and the tree is clean may `make evidence-p7` atomically
write `artifacts/p7/summary.json`. The writer rejects `main`, wrong branch/base/merge-base,
dirty state, missing trusted commits, historical drift, fabricated SHA, missing/failed/skipped
Gate, cleanup residue, live/private content, or unevaluated runtime. It records the real
acceptance and implementation SHAs, fixed base, merge-base, test identities and counts,
synthetic/offline class, deterministic regression, runtime and cleanup, and explicit human
and live-provider `not_evaluated` results. Its tree digest excludes exactly the summary.

Commit the summary alone, then rerun `git diff --check`, public boundary, focused P7 gates,
`make check`, and `make p7-compose-runtime`. Stop with a clean index/worktree on
`codex/p7-optional-adapters`. Do not merge, push, tag, release, rebase, squash, amend, delete
the branch, rewrite acceptance, or start P8.
