<!-- SPDX-License-Identifier: Apache-2.0 -->

# Local Development

## Prerequisites

- Python 3.12 or newer (`PYTHON=python3.13` may be passed to Make)
- Node.js 24.15.0
- Corepack with npm 11.12.1 from Studio's integrity-pinned `packageManager`
- Git and Make
- Docker Desktop with a running daemon, Compose v2+, and Buildx for P10 Mac gates

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

## P9 Productization Rebaseline history

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
only **P9 development complete, awaiting independent acceptance**. P10 begins only from
the exact accepted P9 object and its separately fixed contract.

## P10 Mac Quickstart and Distribution development

P10 uses a downloaded, checksum-bound bundle and separate digest-selected runtime and
Studio images. The host quickstart needs macOS, Docker Desktop, the bundle, and standard
macOS tools; it does not need host Python, Node, npm, Make, Git, jq, or a provider
credential. Development gates additionally use this repository's locked Python and Studio
toolchains.

Focused verification is available through:

```bash
make p10-repository
make p10-provenance
make p10-distribution
make p10-security
make p10-operations
make p10-i18n
make p10-compatibility
make p10-reproducibility
make p10-compose-runtime
make p10-quickstart
make p10-remote-distribution
make p10-test
make p10-check
```

`make p10-check` materializes the exact accepted P9 Git object in an OS-temporary clone
and runs its retained `make check`. It then checks current lint, types, Studio tests/build,
public boundary, P10 static gates, two complete multi-platform OCI layouts, an actual
native digest-only Compose restart, and three actual clean Mac quickstarts. Builds happen
before the timing interval. Every trial must report API, worker, Studio, and JSON status
ready in under 300 seconds, with cleanup complete and no provider credential.

After the separately authorized remote policy reaches `passed`,
`make p10-remote-distribution` verifies the locked public GHCR exact digests, signatures,
attestations, anonymous pulls, two-platform manifests/blobs, a digest-bound bundle, and
three clean Mac quickstarts below 60 seconds. GitHub CLI and Cosign are checksum-pinned in
an OS-temporary tool directory; a host install and GHCR credentials are not required.

The default private root is `~/Library/Application Support/Digital Colleagues`; see
[P10 operations](p10/operations.md). FileVault off or unknown blocks live readiness but
does not prevent the deterministic reference mode. Do not place a secret in environment,
Compose interpolation, an argument, SQLite, logs, diagnostics, Studio state, or evidence.

Only after a clean implementation commit, locked `passed` remote policy, deactivated
read-only workflow, and the complete local/remote aggregate pass may the developer run
`make evidence-p10`. It writes only `artifacts/p10/summary.json`; commit that file alone
and rerun `make check`. The summary records publication source and final evidence
implementation revisions separately. Do not tag, create a Release, merge, push main, or
begin P11.

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

## P11 development gate

P11 work is confined to `codex/p11-agent-packages` and the exact changed-path allowlist in
`docs/p11/acceptance.md`. The acceptance file is immutable at its isolated first commit.
Use `make p11-test` while developing and `make p11-check` before the implementation commit.
The aggregate first checks the exact P10 object in an OS-temporary worktree under its
required historical branch, then checks the current P11 candidate. Do not invoke the P10
repository/evidence checker directly against P11.

After all implementation paths are committed and the tree is clean, `make evidence-p11`
may write the sole final evidence file. Commit that file alone and rerun both aggregate
commands. Skips, xfails, expected failures, mock replacement of the actual Compose path,
and evidence editing are forbidden.

## P12 Public Pilot Continuity Rebaseline development

P12 starts at exact accepted P11R commit
`c1562ea5201394d8a278f4b644daf4029cbb5bd4` and is governed by the immutable
`docs/p12/acceptance.md`. It changes only the exact 39-path set: the acceptance-only first
commit, 37 implementation paths, and a separately authorized summary-only final commit.
P12 adds governance and no runtime, Studio behavior, schema, migration, dependency,
Compose, provider, connector, memory, trigger, proactivity, or publication capability.

The clean committed implementation head runs:

```bash
make p12-test
make p12-ci
make ci
make p12-implementation-check
```

`make ci` delegates only to `p12-ci`. The current gate uses exact P12 test/checker
inventories and replays accepted P11R with `make p11r-check` only inside an OS-temporary
checkout of its exact object and ref layout. Historical P0-P11R files and gates are never
edited or weakened on the descendant.

Evidence is a later authorization. `make p12-evidence-preflight` requires an explicit
implementation SHA, numeric exact-head PR CI run, and caller-owned OS-temporary receipt
directory. It verifies read-only GitHub/GHCR access, protected P10 identities, exact
hash-locked package declarations, PEP 440 installed versions, and certificate-verified TLS.
It writes no repository artifact. Only a later explicit authorization naming the receipt
digest, head, run, and expiry may invoke `make evidence-p12`; that writer may create only
`artifacts/p12/summary.json` and consumes the external receipt once.

Implementation failure on a clean committed head stops for scoped correction authority.
No contract edit, amend, rebase, squash, reset, merge commit, push, PR, evidence, tag,
Release, publication, or P13 work is implied by a local P12 gate.
