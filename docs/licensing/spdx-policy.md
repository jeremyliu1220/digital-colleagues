<!-- SPDX-License-Identifier: Apache-2.0 -->

# SPDX Header Policy

## Default

Project-authored, copyrightable source and documentation uses:

```text
SPDX-License-Identifier: Apache-2.0
```

Use the comment form native to the file. Python, shell, YAML, TOML, and ignore files use a
line comment. Markdown uses an HTML comment. TypeScript, JavaScript, and CSS use a block or
line comment. A shebang remains the first line and the SPDX line follows it.

## Copyright text

Where a copyright line is needed, use the collective name `Digital Colleagues
contributors`; do not add personal contact data. Apache-2.0 does not require a copyright
line in every file.

## Formats without comments

JSON and other formats that do not permit comments are covered by the repository license
and `docs/licensing/file-map.json`. Do not make a data file invalid to insert a header.

## Migrated and third-party material

- Preserve applicable upstream copyright, attribution, and license notices.
- Add Apache-2.0 only when the rights review and compatibility decision permit it.
- Do not replace, delete, or collapse an upstream notice merely for consistency.
- If authorship, licensing, or notice obligations are unclear, stop migration and record
  the file as unresolved.
- Vendored, generated, fixture, example, and binary material is not broadly exempt. It
  requires an exact origin, version, license, notice treatment, and generated-file policy.

## Milestone boundary

P0 applied headers as a policy preview. P1 added the formal `LICENSE`, `NOTICE`,
contributor-facing guidance, and repository-wide file map. P2 keeps SPDX headers on all
new Python and Markdown files and records its commentless JSON receipt, evidence, and
historical fixture in the file map. Later milestones must update the map and notice review
when they add a new format, dependency, copied material, or distribution artifact.
