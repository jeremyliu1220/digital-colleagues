<!-- SPDX-License-Identifier: Apache-2.0 -->

# Contributing

Digital Colleagues welcomes focused contributions that preserve explicit authority,
identity, privacy, provenance, and milestone boundaries.

## Before opening a change

1. Read `AGENTS.md`, `docs/roadmap.md`, and the acceptance contract for the active
   milestone.
2. Use an issue for a material design change. Do not include credentials, personal data,
   private repository content, or live-provider evidence.
3. Confirm you have the right to submit every file. Follow
   `docs/licensing/contributing.md` for inbound licensing and third-party material.
4. Keep work inside the active milestone. A later feature waits until the prior gate has a
   repeatable command and evidence artifact.
5. For P12, read `docs/p12/acceptance.md` and `docs/p12/rebaseline-checklist.md`. The
   v4 acceptance file is immutable; implementation is restricted to its exact 40-path
   implementation allowlist and a pull request is not authorized until the complete local
   implementation gate passes. The rejected v1/v2 and superseded v3 refs stay immutable
   non-ancestors, and each transition follows the exact 21-stage authorization lifecycle.

## Local setup and checks

```bash
make check
```

Focused targets are listed in `make help` and documented in `docs/development.md`. They
use disposable workspaces so ignored dependencies and build products never bypass or
interfere with the strict public-boundary scan.

## Change expectations

- Add or update tests for behavior, policy, and regression fixes.
- Keep the pure core free from HTTP, validation-framework, provider, ORM, and
  orchestration imports when that package begins in P2.
- Use synthetic identifiers and deterministic fixtures.
- Add SPDX headers according to `docs/licensing/spdx-policy.md`.
- Update relevant architecture, ADR, risk, provenance, and acceptance records.
- Describe the claim boundary: say what the evidence establishes and what it does not.

## Pull requests

Keep pull requests reviewable and explain the hypothesis, experiment or change, result,
evidence, decision, and consequence where architectural judgment is involved. All CI gates
must pass. Maintainers may request a narrower change when provenance, rights, privacy, or
milestone scope is unclear.

P12 uses two distinct exact-head CI checkpoints: the complete implementation/correction
head before evidence, and the final summary-only candidate afterward. Contract-only pull
requests, merge commits, history rewrites, and evidence generated without an exact
single-use authorization receipt are rejected. Passing P12 does not authorize P13.

P12's portable history preserves 129 accepted gate identities as 124 included and five
ordered excluded gates over five isolated accepted-object checkouts. The literal 151-item
inventory is 5 setup + 124 included + 17 evidence anchors + 5 excluded. The exclusions are
`p8_compose_runtime`, `p8_golden_path`, `p10_compose_runtime`, `p10_quickstart`, and
`p10_remote_distribution`; each embeds a distinct immutable Darwin `passed` anchor while
its Ubuntu status remains `not_proven`. P12 governance may pass independently, but Linux
Public Pilot readiness stays `blocked` until P20-L0, the first and only blocking P20
portability sub-gate, passes.

By intentionally submitting a contribution for inclusion, you agree that it is provided
under the repository's Apache-2.0 inbound terms described in the contributor licensing
guidance. No CLA or DCO process is adopted at P1.
