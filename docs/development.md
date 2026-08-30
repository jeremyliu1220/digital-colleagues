<!-- SPDX-License-Identifier: Apache-2.0 -->

# Local Development

## Prerequisites

- Python 3.12 or newer (`PYTHON=python3.13` may be passed to Make)
- Node.js 22.12 or newer
- npm 11 or a compatible npm that honors the committed lockfile
- Git and Make

No provider account, credential, container runtime, parent checkout, or checked-in database
is needed. P3 tests use a synthetic reference channel and OS temporary SQLite files.

## Isolated tool workspace

```bash
make bootstrap
```

The command installs `requirements/p3.lock` into a temporary virtual environment, copies
Studio to a temporary directory, runs environment checks, and deletes both. It creates no
repository `.venv`, `node_modules`, cache, database, coverage, or build output. Direct
runtime and development dependencies are exactly pinned in `pyproject.toml`; the lock also
pins resolved transitives.

The current schema applies migrations 001, 002, and additive Timer migration 003. Never edit
an applied migration; add the next numbered file and checksum instead. Timer tests use an
injected clock to exercise not-due, due, lease takeover, restart, replay, and namespace
isolation without sleeping.

## Verification

```bash
make check
```

The aggregate gate runs the equivalent of:

```bash
ruff check src scripts tests
ruff format --check src scripts tests
mypy src scripts tests
python -B scripts/run_p3_unittest_suite.py --start-directory tests --top-level-directory .
npm --prefix studio run lint
npm --prefix studio run format:check
npm --prefix studio run typecheck
npm --prefix studio test
npm --prefix studio run build
python -B scripts/check_public_boundary.py .
python -B scripts/check_p3_repository.py .
python -B scripts/check_p3_provenance.py .
python -B scripts/check_p3_architecture.py .
PYTHONPATH=src python -B scripts/check_p3_migrations.py .
PYTHONPATH=src python -B scripts/check_p3_persistence.py
PYTHONPATH=src python -B scripts/check_p3_runtime_contracts.py .
PYTHONPATH=src python -B scripts/check_p3_golden_path.py
```

Focused Make targets are `boundary`, `p3-repository`, `p3-provenance`,
`p3-architecture`, `p3-migrations`, `p3-persistence`, `p3-runtime`, and `p3-golden`.
The literal full unittest command can bootstrap its API-test dependencies into an OS
temporary environment when FastAPI is not installed in the invoking interpreter; no test
is skipped.

## Evidence milestone

After all implementation, tests, docs, fingerprints, and gates are committed with a clean
tree, run:

```bash
make evidence-p3
```

The collector reruns every P3 gate and the complete zero-exception suite once. It refuses
to overwrite a passed summary after any failure; verifies required test IDs and fault
boundaries; requires the P3 branch to merge-base at the accepted P2 SHA; requires no remote;
compares the exact parent-fingerprint objects; records the tested implementation commit;
and atomically writes `artifacts/p3/summary.json`. Its public-tree digest excludes only that
summary to avoid self-hashing. Commit the summary separately, then rerun `make check` and
the public-boundary scan. Historical `make evidence-p1` and `make evidence-p2` are forbidden.

Required P3 test identities include complete outbox field binding, server-controlled approval
time, boundary/alias bypass rejection, version-2 Timer upgrade and Timer restart semantics,
and application-layer deterministic no-op behavior. A missing identity, skip, or nonzero test
outcome prevents evidence replacement.

## Headless and HTTP boundaries

The Golden Path is exercised through application services and the bounded worker facade.
FastAPI tests use an in-process client and an injected server-side RequestPrincipalContext;
no public network interface is bound. P3 does not implement the P4 bootstrap, enrollment,
session, CSRF, Origin, or Studio workflows. `make studio-dev` remains an isolated preview of
the static shell and must not be read as a P3 product UI.

Every check removes its temporary environment. If a contributor independently creates a
runtime database, `.venv`, `node_modules`, cache, coverage, log, or build directory inside
the repository, remove it before running the repository and public-boundary gates.
