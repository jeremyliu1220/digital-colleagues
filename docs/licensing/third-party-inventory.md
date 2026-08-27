<!-- SPDX-License-Identifier: Apache-2.0 -->

# Third-Party Dependency and Notice Inventory

## P1 distribution boundary

P1 copies or vendors no third-party source, binary, container image, font, icon, or media
asset. Package managers download development and build dependencies into ignored local
directories. The generated Studio bundle is verification output, is ignored, and is not
published by P1.

This inventory records declared metadata review; it is not legal advice or a substitute
for the release-level transitive and artifact review required by P8.

## Python direct packages

| Package | Version | Role | Declared license | P1 treatment |
| --- | --- | --- | --- | --- |
| Hatchling | 1.32.0 | PEP 517 build backend | MIT | Downloaded for builds; not vendored |
| Ruff | 0.16.4 | Development lint and format | MIT | Optional development dependency |
| mypy | 2.3.1 | Development type checking | MIT | Optional development dependency |

The Python package has no runtime dependency in P1.

## Studio direct packages

| Package | Version | Role | Declared license | P1 treatment |
| --- | --- | --- | --- | --- |
| React | 19.2.8 | Static Studio shell | MIT | Package-manager dependency |
| React DOM | 19.2.8 | Browser rendering | MIT | Package-manager dependency |
| TypeScript | 6.0.3 | Type checking | Apache-2.0 | Development dependency |
| Vite | 8.2.2 | Development and build tool | MIT | Development dependency |
| Vite React plugin | 6.1.0 | Vite React transform | MIT | Development dependency |
| Vitest | 4.1.11 | Studio tests | MIT | Development dependency |
| ESLint | 10.9.1 | Studio lint | MIT | Development dependency |
| ESLint JavaScript config | 10.0.1 | Base lint policy | MIT | Development dependency |
| typescript-eslint | 8.68.0 | Typed lint policy | MIT | Development dependency |
| React Hooks lint plugin | 7.1.1 | React lint policy | MIT | Development dependency |
| React Refresh lint plugin | 0.5.5 | Vite lint policy | MIT | Development dependency |
| globals | 17.11.0 | ESLint environment data | MIT | Development dependency |
| Prettier | 3.9.6 | Studio formatting | MIT | Development dependency |
| React type declarations | 19.2.18 | Type checking | MIT | Development dependency |
| React DOM type declarations | 19.2.5 | Type checking | MIT | Development dependency |

`studio/package-lock.json` contains 202 resolved package entries beyond the root package.
All carry declared license metadata: Apache-2.0 (16), BSD-2-Clause (6), BSD-3-Clause (2),
BlueOak-1.0.0 (1), CC-BY-4.0 (1), ISC (11), MIT (153), and MPL-2.0 (12). This automated
metadata census found no missing license field; it is not a source-text or release-bundle
legal conclusion.

## CI actions and operator tools

The CI workflow pins Actions Checkout v6, Setup Python v6, and Setup Node v6 to immutable
commit identifiers. Their repositories declare MIT licenses; the actions are fetched by
the CI operator and are not vendored in this tree. Python, Node.js, npm, Git, and Make are
external operator tools.

## NOTICE decision

The direct-package review found no external attribution that must be copied into the P1
source scaffold's NOTICE. The decision and its distribution limit are recorded in
`docs/licensing/notice-review.md`. Any copied material, generated distributable bundle,
container, optional adapter, or release archive triggers a fresh review.
