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

By intentionally submitting a contribution for inclusion, you agree that it is provided
under the repository's Apache-2.0 inbound terms described in the contributor licensing
guidance. No CLA or DCO process is adopted at P1.
