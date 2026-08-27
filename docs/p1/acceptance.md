<!-- SPDX-License-Identifier: Apache-2.0 -->

# P1 Public Repository Scaffold Acceptance Contract

## Required artifacts

P1 requires the formal Apache-2.0 `LICENSE`; reviewed `NOTICE`; contributor licensing and
third-party records; README and community health files; Python 3.12 package metadata; a
private React, TypeScript, and Vite Studio package with a lockfile; pinned CI actions;
local development commands; public-boundary CI; P1 tests; and a machine-readable summary.

## Acceptance conditions

1. The root license is byte-identical to the official Apache License 2.0 text, and the
   NOTICE review documents why no external attribution is copied into the P1 source tree.
2. README positions the project, states capability and maturity boundaries, explains the
   planned five-minute Golden Path, and labels it unavailable until P4.
3. CONTRIBUTING, SECURITY, Code of Conduct, SUPPORT, GOVERNANCE, issue forms, and the pull
   request template contain no personal contact data and route sensitive reports privately.
4. Python metadata requires 3.12+, exposes only an empty typed package boundary, and has no
   runtime dependency or P2 domain behavior.
5. Studio is private, lockfile-resolved, loopback-bound, linted, type-checked, tested, and
   buildable. Its static shell explicitly says runtime behavior begins after P1.
6. CI runs Python lint, format, strict type checking, and tests; Studio lint, format, type
   checking, tests, and build; the scaffold contract; and the public-boundary scanner.
7. The scanner excludes only the exact root `.git` administrative entry. It accepts a real
   metadata directory or a bounded single-line worktree pointer opened without following;
   it rejects malformed files, symlinks, and special types without revealing the pointer.
   Nested and similarly named paths remain in scope, and actual exact exceptions are
   reported.
8. A stdlib structured runner executes the full P0 and P1 unittest suite once. Passed P1
   evidence requires a positive test count and zero failures, errors, skips, expected
   failures, or unexpected successes. Scaffold, boundary, lint, type, Studio test, and
   build gates must also pass.
9. The automated evidence mechanically verifies the absence of a root `.git`
   administrative entry, P2 product paths, Python runtime dependencies, boundary findings,
   and boundary exceptions. Remote creation, commits, publication, migration provenance,
   parent working-tree use, and absence of live or personal material are not represented as
   mechanically proven; they require separate operator confirmation and remain labeled
   `not_evaluated_by_automated_evidence` in the artifact.
10. Evidence generation is a pre-Git milestone snapshot. If any root `.git` entry exists,
    `make evidence-p1` fails before verification and rechecks immediately before an atomic
    write; an existing passed artifact is not overwritten with a contradictory result.
11. `artifacts/p1/summary.json` claims only a clean-room public repository scaffold gate.

## Evidence claim classes

`results` and `mechanically_verified_boundaries` contain values derived from commands and
validated files. `non_mechanical_claims` contains explicit `not_evaluated` labels, not
booleans that resemble automated proof. The operator separately confirms the broader
no-remote, no-commit, no-publication, no-migration, and no-private-data conditions before
handoff.

## Repeatable gate

```bash
make check
make evidence-p1
```

CI runs the equivalent platform-independent commands. The fixed-revision source allowlist
gate remains a local P0 provenance check because a public checkout does not contain the
read-only parent source repository.

## Stop condition

After the P1 summary is rebuilt and these conditions pass, stop. Git initialization and
the first commit require separate operator approval. P2 product work also requires a new,
explicit milestone approval.
