<!-- SPDX-License-Identifier: Apache-2.0 -->

# Third-Party Dependency and Notice Inventory

## P3 distribution boundary

P3 copies or vendors no third-party source, binary, container image, font, icon, or media
asset. Package managers install the exact P3 lock only into OS temporary directories. The
generated Studio bundle and API-test environments are verification output, are deleted,
and are not published. P3 adds FastAPI and Pydantic as direct runtime dependencies and
HTTPX as an in-process test dependency. It changes neither the Studio lockfile nor its
reviewed dependency set.

This inventory records declared metadata review; it is not legal advice or a substitute
for the release-level transitive and artifact review required by P8.

## Python direct packages

| Package | Version | Role | Declared license | P3 treatment |
| --- | --- | --- | --- | --- |
| Hatchling | 1.32.0 | PEP 517 build backend | MIT | Downloaded for builds; not vendored |
| FastAPI | 0.141.1 | Typed HTTP mapping edge | MIT | Runtime package-manager dependency; not vendored |
| Pydantic | 2.13.5 | HTTP request/response shape mapping | MIT | Runtime package-manager dependency; confined to API edge |
| HTTPX | 0.28.1 | In-process FastAPI test client transport | BSD-3-Clause | Development dependency; no live-provider traffic |
| Ruff | 0.16.4 | Development lint and format | MIT | Optional development dependency |
| mypy | 2.3.1 | Development type checking | MIT | Optional development dependency |

`requirements/p3.lock` resolves 20 exact Python packages: MIT (13), BSD-3-Clause (4),
MPL-2.0 (2), and PSF-2.0 (1). The MPL packages are Certifi and Pathspec; the PSF package is
Typing Extensions. This is a metadata and source-tree boundary review, not a release bundle
or transitive source-text legal conclusion. P3 vendors none of these packages.

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

The P3 direct-package review found no external attribution that must be copied into this
project-authored source tree's NOTICE because dependency material is neither copied nor
vendored. The decision and its distribution limit are recorded in
`docs/licensing/notice-review.md`. Any copied material, generated distributable bundle,
container, optional adapter, or release archive triggers a fresh review.
