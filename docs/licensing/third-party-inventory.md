<!-- SPDX-License-Identifier: Apache-2.0 -->

# Third-Party Dependency and Release Inventory

## P8 release-candidate boundary

P8 reviews the actual unpublished `0.1.0` local reference candidate rather than only the
P3 source tree. The six candidate files are a normalized public source archive, the
project-authored Python wheel, a built Studio archive, deterministic machine-readable
supply-chain inventory, release manifest, and checksums. P8 does not publish packages,
images, archives, tags, or releases.

The machine source of truth is `release/supply-chain-inputs.json` plus
`requirements/p8.lock`, `studio/package-lock.json`, Dockerfiles, and CI. The generated
`digital-colleagues-sbom-0.1.0.json` contains one deterministically sorted record per
Python/npm dependency, build backend, OCI base, GitHub Action, and release/operator tool.
Each applicable record carries version, immutable content/reference, declared license,
artifact inclusion, and attribution treatment. `make p8-supply-chain` fails on drift,
missing metadata, mutable critical references, or unresolved treatment.

This is a review of declared upstream metadata and distribution treatment, not legal
advice, a source-code legal audit, a vulnerability assessment, or a conclusion about every
package or base-image obligation in a future distribution.

## Python graph and build backend

`requirements/p8.lock` contains 27 exact packages and permits only recorded wheel SHA-256
values for the supported P8 gate environments. It covers direct runtime FastAPI and
Pydantic, runtime Uvicorn, direct development HTTPX/mypy/Ruff, the Hatchling 1.32.0 build
backend, and every resolved transitive. License metadata counts are:

| Declared license | Packages |
| --- | ---: |
| MIT | 16 |
| BSD-3-Clause | 6 |
| MPL-2.0 | 2 |
| Apache-2.0 | 1 |
| Apache-2.0 OR BSD-2-Clause | 1 |
| PSF-2.0 | 1 |

The Python wheel contains Digital Colleagues package code and its project licensing
metadata; it does not vendor these package-manager dependencies. The source archive carries
the lock/inventory metadata, not installed dependency code. Local operational images
install the hash-checked graph, but P8 does not distribute or publish those images.

## Studio graph and bundled output

`studio/package-lock.json` lockfile version 3 contains 202 package entries beyond the root.
Every entry has an exact version, npm SHA-512 integrity value, and declared license:

| Declared license | Packages |
| --- | ---: |
| MIT | 153 |
| Apache-2.0 | 16 |
| MPL-2.0 | 12 |
| ISC | 11 |
| BSD-2-Clause | 6 |
| BSD-3-Clause | 2 |
| BlueOak-1.0.0 | 1 |
| CC-BY-4.0 | 1 |

Only React 19.2.8, React DOM 19.2.8, and Scheduler 0.27.0 are production graph entries
bundled into the built Studio output; all three declare MIT. The release builder reads each
installed package's `LICENSE` and adds the exact text to
`THIRD_PARTY_LICENSES.txt` inside the Studio archive. Missing, special, or undecodable
license files fail the release Gate. The other 199 entries are build/development inputs and
are not copied as package trees into the candidate.

## OCI bases, CI Actions, and release tools

Operational Dockerfiles pin manifest-list digests for:

| Base reference | Immutable manifest-list digest | Use |
| --- | --- | --- |
| `python:3.13-slim` | `sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285` | API, worker, operator, gates |
| `node:24-alpine` | `sha256:e67514e5d0f6c46656005e1b693b2ec9d52e80b641307de684d4a015ba7a4eaf` | Studio build stage |
| `nginx:1.29-alpine` | `sha256:5616878291a2eed594aee8db4dade5878cf7edcb475e59193904b198d9b830de` | Studio runtime stage |

These image references and their upstream-project license labels appear in the inventory;
the labels are not a full census of every OS package in an image. P8 exercises the images
locally and does not publish them. Raw image byte reproducibility is not claimed.

CI uses Actions Checkout v6, Setup Python v6, and Setup Node v6 at exact 40-character
commits, all declaring MIT. P8 does not vendor the Actions. The release inventory also
records external Python, Node 24.15.0, integrity-pinned npm 11.12.1/Corepack, Git, Make,
Docker, and Compose operator boundaries. Hatchling itself is Python hash-locked.

## NOTICE and stop decision

The root Apache-2.0 `LICENSE` is unchanged. The root `NOTICE` remains the project
identification/collective copyright notice; it is not used as a substitute for dependency
license texts. The only dependency bytes intentionally distributed in a P8 candidate are
the built Studio production graph, whose installed license texts are placed inside that
archive. Python dependencies, CI Actions, build-only npm packages, and OCI images are not
published by P8.

The P8 supply-chain Gate records zero unresolved declared-license and attribution-treatment
entries for this exact candidate boundary. A later package repository, image push, hosted
bundle, copied asset, font, named-provider adapter, or changed dependency/base must trigger
a fresh review; this record cannot be promoted to a general legal conclusion.
