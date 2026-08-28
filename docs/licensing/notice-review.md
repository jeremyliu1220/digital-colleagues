<!-- SPDX-License-Identifier: Apache-2.0 -->

# P1-P2 NOTICE Review

## Hypothesis

A concise root `NOTICE` can accurately cover the source tree through P2 if no copied or
vendored dependency material adds a mandatory attribution notice.

## Experiment

Review every direct P1 package recorded in `pyproject.toml` and `studio/package.json`, its
declared upstream license, whether its source is copied or vendored, and whether a required
NOTICE attribution is introduced into this source tree.

## Result and evidence

The direct Python build and development packages are MIT-licensed. Studio's direct
packages are MIT-licensed except TypeScript, which is Apache-2.0. P1 declares these as
package-manager dependencies and vendors none of their source, binaries, fonts, icons, or
media. Exact versions and review status are recorded in the third-party inventory and npm
transitives are fixed by `studio/package-lock.json`.

No reviewed direct package introduces third-party NOTICE text that must be copied into the
P1 source scaffold. The root `NOTICE` therefore contains the project identification and
collective copyright statement only.

## Decision and consequence

Accept the `NOTICE` as reviewed through the P2 source tree. P2 introduced only
project-authored new implementations based on public architecture documents, migrated no
parent source bytes, added no dependency, and left the Studio lockfile unchanged.
Generated Studio bundles and
future container or release distributions require a fresh transitive license and
attribution review before publication. P2 does not claim that a later distribution can
reuse this conclusion unchanged.
