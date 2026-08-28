<!-- SPDX-License-Identifier: Apache-2.0 -->

# Fixed-Revision Source Inventory

## Review basis

- Source label: `digital-colleague-runtime-research`
- Fixed revision: `dea9a9accc82fbedd35deb7117dcb5173223cf44`
- Selection unit: individual repository-relative file
- P0 action: classify and hash only; copy nothing

The allowlist is `provenance/source-allowlist.json`. An entry is a candidate for later
transformation, not permission to copy it during P0 and not proof of ownership.

## Allowlisted families

The 33 entries cover stable contract concepts, pure domain primitives, deterministic
runtime reference logic, core behavior tests, runtime behavior tests, and architecture
tests. Every entry requires package renaming, license and rights review, de-identification,
namespace review, and adaptation to the new architecture before later introduction.

## Refactor-required families

These source areas may inform a clean implementation but are not currently allowlisted for
direct migration:

| Source family | Required redesign |
| --- | --- |
| Domain actions and execution contracts | Bind approval to a durable human principal and exact immutable effect revision |
| Human input adapters | Remove colleague-as-approver coupling and caller-derived authority |
| Trace contracts | Replace framework- or source-specific trace shapes with public causal audit contracts |
| Application colleague services | Split large services, use typed results, and enforce namespace and revision at boundaries |
| Guided onboarding | Remove hard-coded relationships and working hours; use explicit draft defaults and Admin confirmation |
| Local identity and channel services | Implement normative bootstrap, enrollment, session, and principal-kind rules |
| SQLite adapters | Consolidate into one namespaced database behind ports with numbered checksummed migrations |
| Command-line surfaces | Replace research and operator assumptions with the public Golden Path |

No file in this table may be migrated until a later milestone adds an individual digest-
verified allowlist entry and resolves its named redesign.

## Excluded families

The versioned denylist is `provenance/source-denylist.json`. It excludes local state,
secrets, raw evidence, live-provider and personal acceptance material, research evaluation
and scenario machinery, internal operator material, internal colleague skills, spike code,
milestone collectors, legacy demos, and the current working tree.

Reference or synthetic receipts cannot substitute for live provider evidence, and neither
class is imported in P0.

## P2 selection outcome

P2 selected no allowlisted source file for transformation and read no source content. The
14 product files under `core/` and `governance/` are new implementations based on the
public product, architecture, security, and ADR documents. The machine-readable receipt
therefore has zero transformed entries and does not fabricate source digests or transforms.

## Unresolved rights

No source content was introduced through P2, so no copied file is awaiting a notice
decision. Any later file with unclear authorship, third-party content, or relicensing scope
must be added to the unresolved section of the rights record and remain unmigrated.
