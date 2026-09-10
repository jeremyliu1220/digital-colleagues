<!-- SPDX-License-Identifier: Apache-2.0 -->

# P11R local and CI operations

P11R aligns current-tree CI after accepted P11. It changes governance tooling only and
does not reopen P11 or authorize Roadmap rebaseline or P12.

Use `make p11r-test` for hash-locked Python quality, the literal 100-test current-tree P11
regression inventory, separately counted P11R tests, and exact Node/npm Studio quality.
Use `make p11-ci` or its stable alias `make ci` for branch-independent current CI. Neither
entry invokes the branch-bound P11 repository gate or the accepted P10/P11 aggregate.

Use `make p11r-compose-smoke` only for a separately required bounded Compose run. Pull
requests do not run Compose. Main-push CI runs it only after `current-ci` succeeds.

Use `make p11r-check` only from a clean, committed P11R candidate. It adds candidate
repository/provenance checks, one accepted-P11 exact-object replay in an OS temporary
checkout, and one bounded Compose smoke. The accepted replay uses commit
`7e5387f148f86b5c9b07820dd8b8f4e18e12dc38`, branch
`codex/p11-agent-packages`, and the original `make p11-check`; it never changes repository
refs or accepted objects.

Expected test groups are reported independently:

- accepted P11 exact-object suite: 101 tests;
- P11R current-tree P11 regression suite: 100 tests; and
- P11R governance suite: the exact actual count reported by its runner.

Node is read only from `.nvmrc` and is exactly `24.15.0`. Studio requires
`>=24.15.0 <25`; Corepack resolves the integrity-qualified npm `11.12.1` declaration in
`studio/package.json`. Python dependencies are installed with hashes from
`requirements/p8.lock` into an OS temporary virtual environment.

`make evidence-p11r` is a later, separately authorized operation. It requires a clean,
committed implementation and may write only `artifacts/p11r/summary.json`. Do not invoke it
during implementation. Push, pull request, merge, tag, Release, attestation, publication,
Roadmap rebaseline, and P12 each remain unauthorized until explicitly approved.
