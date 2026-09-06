<!-- SPDX-License-Identifier: Apache-2.0 -->

# Local Development

## Prerequisites

- Python 3.12 or newer (`PYTHON=python3.13` may be passed to Make)
- Node.js 24.15.0
- Corepack with npm 11.12.1 from Studio's integrity-pinned `packageManager`
- Git and Make
- Docker Engine and Compose v2-compatible CLI for required P8 runtime gates

No provider account, live credential, parent checkout, or checked-in database is needed.
The default path uses deterministic intelligence, a synthetic reference channel, and OS
temporary SQLite files. P7 adapter regression tests use only a controlled loopback stub and
temporary opaque credentials. P8 release tests use temporary candidate, backup, restore,
diagnostic, container, network, and volume boundaries. Without actual Docker/Compose
execution the runtime result is `not_evaluated`, and P8 evidence/completion is blocked.

## Isolated tool workspace

```bash
make bootstrap
```

The command installs `requirements/p8.lock` with `pip --require-hashes` into a temporary
virtual environment, copies Studio to a temporary directory, runs environment checks, and
deletes both. It creates no repository `.venv`, `node_modules`, cache, database, coverage,
candidate, backup, diagnostics, or build output. Python runtime, development, and Hatchling
build packages are exact and hash-checked. Studio packages are exact and carry npm
integrity values. The Studio Docker build uses the exact `node:24.15.0-alpine` manifest
digest, checks Node/npm inside the build stage, invokes npm only through Corepack, and
generates matching bounded build-toolchain metadata in the served bundle. No Dockerfile
performs an OS package-manager install. The optional P7 publisher guard copies only the
version-asserted `ip` applet from the exact inventoried BusyBox build-stage image.

The current schema applies immutable migrations 001-007. P7 adapters are stateless and P8
adds no migration 008. Never edit an applied migration. A future schema change belongs to a
separately gated milestone and must add a numbered, checksummed migration.

## Verification

```bash
make check
make p8-compose-runtime
make p8-golden
```

`make check` runs the P9 aggregate in disposable workspaces. It first executes the complete
retained P8 toolchain, then the P9 governance gates. The retained P8 portion includes:

- Ruff lint/format and strict mypy for Python;
- full Python unittest with zero skips/failures/errors and required P0-P8 identities;
- Studio ESLint, Prettier, TypeScript, Vitest, and Vite build;
- zero-exception public-boundary scan;
- all 37 applicable P2-P7 current-tree core, architecture, migration, security, policy, Studio,
  Compose, adapter, and Golden Path regressions, plus the fixed P7 historical evidence
  identity, without running a historical evidence writer. The P2 development-stage
  architecture gate itself is historical because it intentionally rejects every P3+
  directory; its retained pure-core contract gate still runs against the current tree;
- P8 repository/provenance, operations, backup/restore, diagnostics, supply-chain,
  reproducibility, release, Compose runtime, and Golden Path gates; and
- Git whitespace, residue, immutable-input, claim-boundary, and cleanup checks.

Focused P8 targets are:

```bash
make p8-repository
make p8-provenance
make p8-operations
make p8-backup-restore
make p8-diagnostics
make p8-supply-chain
make p8-reproducibility
make p8-release
make p8-compose-runtime
make p8-golden
```

All earlier focused targets remain available. A P8 aggregate may evaluate an accepted
historical commit in a temporary checkout where current version, image pins, or provenance
would otherwise contradict an earlier milestone's fixed tree. This preserves original
historical semantics; it does not weaken or rebuild the old Gate.

## Release-candidate build

After the acceptance and implementation commits exist and the tree is clean:

```bash
python3 -B scripts/build_p8_release.py --output /operator/private/rc
```

The builder requires the exact fixed ancestry and version `0.1.0`. It uses normalized
metadata and produces only the six artifacts fixed in the
[P8 acceptance contract](p8/acceptance.md). It builds twice under
`make p8-reproducibility`; every declared artifact digest must match. Candidate output is
local and unpublished. OCI images are runtime test output, not byte-reproducible release
artifacts; their base digests and build inputs are nevertheless fixed and checked.

## Backup, restore, and diagnostics

Use the exact private operator flows in [P8 local operations](p8/operations.md). Online
backup is WAL-consistent; restore validates format/digest/schema/migrations before atomic
replacement; diagnostics emits one bounded allowlisted member. All state, backups,
rollback backups, diagnostic bundles, credentials, and extracted candidates belong outside
the repository with private permissions.

The first-release P7→P8 path is distinct from same-version P8 backup/restore. The runtime
Gate materializes the exact accepted P7 Git tree, creates P7 durable state with P7 code,
backs it up before P8 starts using the fixed non-release source descriptor, starts P8,
checks durable governance state, then restores and starts matching P7 code. P7 did not have
a release manifest; the descriptor records that fact instead of fabricating one.

## P7 credential and network boundary

Optional `http_json_v1` modes require explicit startup configuration, protocol, fixed HTTPS
endpoint, and an operator-created read-only credential file. Test-only HTTP requires an IP
loopback literal and explicit permission. Do not pass credentials on a command line, commit
them, place them in a URL/environment value, or include them in diagnostics. Browser,
Studio, and provider content cannot configure adapters. Default P8 release operations keep
deterministic intelligence and the reference channel and make zero provider calls.

## P8 evidence milestone

Only with a clean implementation commit after every direct/aggregate gate and actual
Docker cleanup passes, run:

```bash
make evidence-p8
```

The collector reruns the complete zero-exception P8 suite, records the real implementation
commit, candidate digests, double-build result, synthetic/offline evidence class, actual
Compose restore path and zero cleanup, then atomically writes only
`artifacts/p8/summary.json`. Its tree digest excludes exactly that summary. Commit the
summary alone and rerun the full final gates. P0-P7 evidence commands are forbidden.

The resulting status may say only **P8 development complete, awaiting independent
acceptance**. It is not a tag, publication, formal release, or production-readiness claim.
Human evaluation, live-provider acceptance, production properties, post-v0.1 capabilities,
and an unmeasured five-minute target remain excluded or `not_evaluated`.

## P9 Productization Rebaseline development

P9 adds documentation, fixed product/architecture/security decisions, governance gates,
tests, provenance, and static/synthetic evidence only. The executable version remains the
unpublished `0.1.0` local reference candidate. P9 does not edit runtime, Studio, Compose,
Docker, dependencies, API/worker/adapters/operations, migrations, or version metadata, and
does not start P10.

Focused commands are:

```bash
make p9-repository
make p9-provenance
make p9-rebaseline
make p9-test
make p9-check
```

`make p9-check` runs the retained P8 toolchain through the existing hash-locked temporary
Python and Studio workspaces, then the P9 repository, provenance, rebaseline, and P9 test
gates. `make check` delegates to the same P9 aggregate. Neither invokes evidence P0-P8.

Only after the fixed P9 acceptance contract and implementation are separate commits, the
branch is exact, and all direct/aggregate gates pass with a clean tree may the developer
run:

```bash
make evidence-p9
```

That command writes only `artifacts/p9/summary.json`, with `static` and
`synthetic_offline` evidence. OpenAI live, Microsoft 365 live, and human evaluation remain
`not_evaluated`. Commit the summary alone and rerun all final gates. The resulting claim is
only **P9 development complete, awaiting independent acceptance**; do not merge, push, tag,
publish, upload, create a Release, or begin P10.

## Authenticated Studio and HTTP boundaries

The accepted P4-P7 Golden Path uses authenticated FastAPI mappings, application services,
and a bounded worker. A server-side session derives `RequestPrincipalContext`; request
bodies cannot submit tenant, namespace, principal kind, role, membership, or session
authority. P6 adds accepted enrollment/recovery, versioned RBAC, two-person authority
change, approval revalidation, and bounded audit export. P7 optional adapters do not alter
those rules, and P8 restore requires revalidation because it returns authority and sessions
to the backup instant.

If a contributor independently creates a database, virtual environment, `node_modules`,
cache, coverage, candidate, backup, diagnostics, log, or build directory in the repository,
remove it before repository, release, and public-boundary gates.
