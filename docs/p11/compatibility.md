<!-- SPDX-License-Identifier: Apache-2.0 -->

# P11 compatibility contract

P11 preserves every existing route, method, and schema from P10. New package and
deployment routes use only `/api/v1`; `/p5` and `/p6` remain compatibility surfaces. The
installed `dc` command adds a stable JSON edge without placing credentials or CSRF in
arguments, environment, or output.

Migration 008 appends to migrations 001–007. Fresh databases contain no fabricated
deployment. A database containing an existing Profile is upgraded to one active
`legacy/manual` deployment in the same namespace, with the exact Profile, Mandate,
optional Policy, principal, work, effect, approval, audit, and causality records retained.
Missing Policy remains `legacy_unconfirmed`. Repeated open is idempotent and a count above
the active limit aborts atomically at schema 7.

P10's published image digests and distribution evidence are historical inputs only. They
are not selected, overwritten, republished, or represented as P11 runtime evidence.
OpenAI, Microsoft 365, named-provider, always-on, and production compatibility remain
`not_evaluated`.
