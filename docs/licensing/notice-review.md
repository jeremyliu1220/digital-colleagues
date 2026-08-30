<!-- SPDX-License-Identifier: Apache-2.0 -->

# P1-P3 NOTICE Review

## Hypothesis

A concise root `NOTICE` can accurately cover the source tree through P3 if no copied or
vendored dependency material adds a mandatory attribution notice.

## Experiment

Review every direct package recorded in `pyproject.toml`, `requirements/p3.lock`, and
`studio/package.json`, its
declared upstream license, whether its source is copied or vendored, and whether a required
NOTICE attribution is introduced into this source tree.

## Result and evidence

The direct Python packages use MIT except HTTPX, which declares BSD-3-Clause. Studio's
direct packages are MIT-licensed except TypeScript, which is Apache-2.0. Package-manager
dependencies vendor none of their source, binaries, fonts, icons, or media. Exact versions
and review status are recorded in the third-party inventory and npm transitives are fixed
by `studio/package-lock.json`.

P3 adds FastAPI 0.141.1 and Pydantic 2.13.5 under MIT plus HTTPX 0.28.1 under BSD-3-Clause.
Its exact lock transitives declare MIT, BSD-3-Clause, MPL-2.0, or PSF-2.0 metadata. No
dependency source, binary, certificate bundle, license text, font, icon, or media is copied
into the public source tree; temporary package installations are deleted after gates.

No reviewed direct package therefore introduces third-party NOTICE text that must be copied
into the source tree. The root `NOTICE` remains the project identification and collective
copyright statement only.

## Decision and consequence

Accept the `NOTICE` as reviewed through the P3 source tree. P3 introduces project-authored
new implementations based on public architecture documents, migrates no parent source
bytes, pins its Python graph, and leaves the Studio lockfile unchanged.
Generated Studio bundles and
future container or release distributions require a fresh transitive license and
attribution review before publication. P3 does not claim that a later distribution can
reuse this conclusion unchanged.
