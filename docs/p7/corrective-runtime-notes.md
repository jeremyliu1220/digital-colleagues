<!-- SPDX-License-Identifier: Apache-2.0 -->

# P7 Corrective Runtime Notes

These notes record the runtime decisions and failed deployment hypothesis from the second
independent P7 acceptance correction. They do not change the fixed P7 acceptance contract.

## Ambiguous headless recovery

The worker namespace scan includes due `ambiguous` outbox rows and expired
`ambiguous_claimed` rows. `still_unknown` remains ambiguous, schedules its next durable
reconciliation time in `next_attempt_at`, and records a bounded reconciliation count in
the existing `last_outcome` field. The two-second base delay doubles to a 30-second cap.
The durable effect `maximum_attempts` is also the reconciliation-call budget, with an
additional hard ceiling of eight calls. Reaching the budget leaves the effect durably
ambiguous but stops automatic reconciliation. No migration 008 is required.

The P3 `DispatchService` default remains a zero-delay compatibility path. The local P4/P7
headless controller explicitly selects the bounded two-second cadence. This preserves the
accepted deterministic reference test while preventing the 0.5-second worker loop from
making unbounded provider calls.

## Reconciliation lease boundary

Reconciliation validates the exact claim lease before provider I/O and again using fresh
authoritative clock readings after provider I/O and before finalization. SQLite atomically
checks state, owner, exact lease value, fencing token, and the full effect claim binding at
finalization. An expired claim creates no result or retry and remains recoverable by a new
claim; the new fencing token rejects the old owner.

## Post-submit HTTP classification

Only an exact HTTP 200 protocol response supplies a channel result. HTTP 401 and 403 remain
permanent authorization refusals. Redirects, HTTP 408, 429, other generic 4xx responses,
5xx responses, malformed or oversized responses, invalid content types, disconnects, and
read or total timeouts after submission are ambiguous. An unproven wire-level
`retryable_failure` is also ambiguous. None enters retry until reconciliation returns
`confirmed_absent`.

## Compose egress experiment and consequence

The first corrective topology attached the publisher directly to the internal bridge and
declared its host ports there. The actual Docker Compose Gate could not reach the control
health endpoint from the host: Docker's internal bridge blocked the published-port DNAT.
That hypothesis was rejected rather than weakening the route check.

The corrected topology keeps API, worker, Studio, stub, and operator in the stub's internal
network namespace. A minimal `p7-egress-guard` owns the loopback-only host ports and the
single publisher attachment. Before ingress starts, the guard removes every default route,
drops to UID 10001, and loses all effective capabilities. `p7-ingress` shares that guarded
namespace. The runtime Gate inspects `/proc/net/route`, Docker network attachments, the
guard process UID/capabilities, host API/Studio reachability, and cleanup for every service.

The actual Gate then recreates API and worker, makes no post-restart `/runtime/process`
call, and observes the worker-only sequence: `still_unknown`, `confirmed_absent`, and one
bounded effect retry.
