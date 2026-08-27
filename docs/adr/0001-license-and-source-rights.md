<!-- SPDX-License-Identifier: Apache-2.0 -->

# ADR 0001: Apache-2.0 Intent and Source-Rights Boundary

- Status: Accepted; P1 formal documents completed
- Decision date: 2026-08-27
- Applies to: Digital Colleagues public project preparation

## Context

The project is prepared from architectural research in a private parent repository. A
public project needs an explicit outbound license, file-level provenance, and a rule for
material whose ownership or relicensing rights are not established. P0 must not copy
source code or prematurely create the formal public license and notice files.

The project owner confirmed that, to the extent of rights they hold, allowlist-selected,
transformed, and de-identified source results may be included in the new project and
published under Apache License 2.0.

## Decision

1. The intended outbound license is Apache License 2.0.
2. The confirmation applies only to source material that:
   - appears in the versioned allowlist;
   - is read from revision `dea9a9accc82fbedd35deb7117dcb5173223cf44`;
   - matches its recorded SHA-256 digest;
   - receives its recorded transformation and de-identification; and
   - is within the rights held by the confirming project owner.
3. An allowlist entry is eligibility for later review, not a license conclusion and not
   authorization to migrate during P0.
4. If a file includes third-party content, unclear authorship, an incompatible notice, or
   any other reason to doubt public or relicensing rights, migration of that file stops.
   The file is recorded as unresolved and remains outside the public project until a human
   rights review resolves it. Permission is never inferred from repository access.
5. Every later migrated file retains applicable original notices and receives the SPDX
   treatment defined in `docs/licensing/spdx-policy.md`.
6. `docs/licensing/third-party-inventory.md` records both P0 tools and provisional future
   dependencies. A dependency must be verified against the selected version before it is
   adopted. Notice obligations are resolved in P1 and updated with each lockfile change.
7. P0 creates no formal `LICENSE`, `NOTICE`, contributor license agreement, developer
   certificate declaration, or contributor-facing licensing guide. Those are P1 artifacts
   and require their own review.

## Rights confirmation record

`provenance/source-rights-confirmation.json` is the machine-readable record. It contains no
personal contact information and does not expand the confirmation beyond the conditions
above.

## Consequences

- P0 can plan and verify future provenance without copying source content.
- File-level rights uncertainty blocks that file, not the obligation to record it.
- The public repository cannot be described as fully Apache-2.0 licensed until the formal
  P1 documents exist and all introduced third-party obligations are reviewed.
- No contributor licensing mechanism is selected by this ADR.

## P1 outcome

P1 added the official Apache License 2.0 text, a reviewed project NOTICE, and
contributor-facing inbound-equals-outbound guidance. It adopted neither a CLA nor DCO
sign-off. No allowlisted source was migrated, no unresolved material was introduced, and
future copied, bundled, or release material still requires file- and distribution-level
rights and notice review.
