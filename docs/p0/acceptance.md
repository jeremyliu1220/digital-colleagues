<!-- SPDX-License-Identifier: Apache-2.0 -->

# P0 Acceptance Contract

## Required artifacts

P0 requires the root working rules and ignore policy; product, architecture, security,
research, roadmap, licensing, and ADR documents; versioned provenance manifests; three
read-only verification tools; P0 tests; and a machine-readable gate summary.

## Acceptance conditions

1. The product brief states the Golden Path and qualified maturity boundary.
2. ADR 0001 records Apache-2.0 intent, conditional source-rights confirmation, file-level
   unresolved handling, third-party inventory, and the P1 boundary for formal documents.
3. ADR 0002 records the approved stack and every local-authentication invariant.
4. The allowlist is pinned to the approved source revision and every entry has a verified
   digest, destination, classification, and required transform.
5. The denylist and refactor inventory prevent accidental migration outside the allowlist.
6. The public-boundary scanner uses explicit versioned rules and exact auditable
   exceptions, and rejects prohibited private or live material.
7. No persisted P0 output includes a local source location.
8. Before and after fingerprints match for the parent source tree excluding only the
   authorized `digital-colleagues` target subtree. The full parent status may show that
   subtree as newly untracked; no pre-existing source file may change.
9. The target has no `.git` directory, formal `LICENSE` or `NOTICE`, product source tree,
   Studio, migrations, Compose file, remote, publication, or migrated source content.
10. The summary status is exactly a planning/public-boundary gate and contains no product,
    security, production, compliance, or pilot attestation.

## Repeatable gate

```bash
python3 -m unittest discover -s tests/p0 -v
python3 scripts/check_public_boundary.py .
python3 scripts/verify_source_allowlist.py --source SOURCE_CHECKOUT --revision dea9a9accc82fbedd35deb7117dcb5173223cf44
```

The source fingerprint command is run before and after this gate. Its output is an
aggregate digest summary only; it includes the content state of existing untracked and
ignored entries but never emits their paths, content, link targets, or local checkout
location.

## P1 entry hardening revalidation

Before P1, the gate was revalidated on 2026-08-28 with 28 passing P0 tests, 33 scanned
public files, zero findings, zero applied exceptions, and 33 verified allowlist entries.
The scanner regression suite covers exact root `.git` administrative entry handling and
actual exception counts. It accepts a real metadata directory or a strictly validated
worktree pointer file, rejects malformed and symlink entries without revealing the
pointer, and keeps nested `.git` paths in scope. Fingerprint schema 2 aggregates the
content state of 0 existing
untracked and 9,365 existing ignored entries; the new before and after records match.

## Stop condition

After these conditions pass and the P0 summary is written, stop. P1 requires a new,
explicit approval.
