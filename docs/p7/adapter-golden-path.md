<!-- SPDX-License-Identifier: Apache-2.0 -->

# P7 Optional Adapter Golden Path

This is a synthetic/offline contract path. It uses a controlled local loopback stub and
does not contact or claim compatibility with a live or named provider.

## Default-path checkpoint

Run the stack without P7 adapter configuration. The composition report must select
`DeterministicIntelligence` and `ReferenceChannel`; the accepted canonical proposal,
approval, dispatch, ActionResult, replay, restart, and causal-history behavior must match
the P6 reference path byte-for-byte where the accepted fixtures define bytes. No credential
file, endpoint, DNS lookup, or network provider is needed.

## Explicit loopback setup

The P7 runtime Gate, not a normal operator, creates all test material under an OS temporary
directory. It starts a bounded HTTP JSON stub on an unused loopback port and writes opaque
synthetic credentials to read-only temporary files. It selects the `http_json_v1` model and
channel modes, fixed loopback endpoints, protocol `dc-http-json-v1`, bounded sizes and
timeouts, and the explicit test-only loopback permission. No secret value is printed or
placed on a command line.

## Contract path

1. Build the optional adapters through the allowlisted composition root and confirm invalid
   modes, missing settings, URL userinfo/query/fragment, redirects, and non-loopback HTTP
   fail before serving.
2. Submit finite synthetic work and run one wake. The model request exposes only the
   canonical minimal work/agenda and effect-boundary projection. The stub returns one
   finite proposal result.
3. Confirm the adapter ignores no authority: it reconstructs every namespace, ID, actor,
   time, Mandate/policy revision, validity, and effect idempotency binding from the local
   `IntelligenceRequest`, then the existing governance layers revalidate the result.
4. Prove malformed, oversized, unknown-field, authority-injection, wrong-type, unknown
   outcome, 401/403, 429, 5xx, timeout, connect, DNS, TLS, redirect, and disconnect cases
   produce typed safe failures and no proposal, approval, or channel call.
5. Have a different authorized HUMAN approve the exact proposal. Dispatch revalidates the
   current Mandate, policy, role, membership, namespace, revision, expiry, digest,
   idempotency, lease, and fencing bindings before the channel adapter sees it.
6. Exercise channel success plus every finite failure class. Rebinding one idempotency key
   to different canonical effect bytes fails closed.
7. Disconnect after submission and confirm an `ambiguous` ActionResult is durable across a
   fresh runtime instance and is not resent. Reconciliation returns `still_unknown` until
   the stub can prove `confirmed_absent`; only then may the existing bounded, reauthorized
   retry path proceed.
8. Restart the API/worker path and prove deterministic replay and accepted exact-effect
   semantics remain unchanged. Scan diagnostics, API responses, logs, evidence, SQLite,
   and public files for absence of credential and raw private payload values.

## Isolated Compose checkpoint

`make p7-compose-runtime` creates a unique Compose project and temporary secret/stub
boundary, starts the optional profile, runs the checkpoints above, recreates the relevant
services, and shuts down normally. Its machine-readable result must report `passed`, no
skips, no unexpected external egress, no secret/log leakage, and zero remaining containers,
networks, volumes, temporary credentials, or stub processes. An unavailable Docker runtime
is `not_evaluated` and blocks P7 evidence.

## Evidence and stop condition

Run focused P7 gates, `git diff --check`, the public-boundary scan, `make check`, and the
actual Compose runtime before the implementation commit. With a clean tree, run
`make evidence-p7`, commit only `artifacts/p7/summary.json`, then repeat every final gate.
The summary classifies public results as synthetic/offline and records human and live
provider evidence as `not_evaluated`. Stop on `codex/p7-optional-adapters`; do not merge,
push, tag, release, rewrite commits, or begin P8.
