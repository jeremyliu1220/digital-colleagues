<!-- SPDX-License-Identifier: Apache-2.0 -->

# Local Development

## Prerequisites

- Python 3.12 or newer (`PYTHON=python3.13` may be passed to Make)
- Node.js 22.12 or newer
- npm 11 or a compatible npm that honors the committed lockfile
- Git and Make
- Docker Engine with Compose v2 only for an actual container Golden Path

No provider account, live credential, parent checkout, or checked-in database is needed.
P5 tests use a synthetic reference channel and OS temporary SQLite files. Without Docker,
static Compose validation and fresh-instance local smoke still run, while container
start/restart/stop evidence is reported as not evaluated.

## Isolated tool workspace

```bash
make bootstrap
```

The command installs `requirements/p4.lock` into a temporary virtual environment, copies
Studio to a temporary directory, runs environment checks, and deletes both. It creates no
repository `.venv`, `node_modules`, cache, database, coverage, or build output. Direct
runtime and development dependencies are exactly pinned in `pyproject.toml`; the lock also
pins resolved transitives.

The current schema applies migrations 001–006. Migration 006 adds revisioned drafts,
confirmations, policy outcomes, durable budget counters, run state, and escalations;
migrations 001–005 remain byte-immutable.
Never edit an applied migration; add the next numbered file and checksum instead.

## Verification

```bash
make check
```

The aggregate gate runs the equivalent of:

```bash
ruff check src scripts tests
ruff format --check src scripts tests
mypy src scripts tests
python -B scripts/run_p5_unittest_suite.py --start-directory tests --top-level-directory .
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
python -B scripts/check_p4_repository.py .
python -B scripts/check_p4_provenance.py .
python -B scripts/check_p4_architecture.py .
PYTHONPATH=src python -B scripts/check_p4_migrations.py .
PYTHONPATH=src python -B scripts/check_p4_authentication.py .
python -B scripts/check_p4_studio.py .
python -B scripts/check_p4_compose.py .
python -B scripts/check_p4_compose_runtime.py .
PYTHONPATH=src python -B scripts/check_p4_golden_path.py
python -B scripts/check_p5_repository.py .
python -B scripts/check_p5_provenance.py .
python -B scripts/check_p5_architecture.py .
PYTHONPATH=src python -B scripts/check_p5_migrations.py .
python -B scripts/check_p5_builder.py .
python -B scripts/check_p5_policy.py .
python -B scripts/check_p5_studio.py .
python -B scripts/check_p5_compose.py .
PYTHONPATH=src python -B scripts/check_p5_golden_path.py
```

Focused Make targets include `boundary`, every retained P4 target, `p5-repository`,
`p5-provenance`, `p5-architecture`, `p5-migrations`, `p5-builder`, `p5-policy`, `p5-studio`,
`p5-compose`, `p5-compose-runtime`, and `p5-golden`. `p5-compose` is static/config
validation; `p5-compose-runtime` is the Docker-required actual runtime Gate. Earlier targets
remain available as regression gates.
The literal full unittest command can bootstrap its API-test dependencies into an OS
temporary environment when FastAPI is not installed in the invoking interpreter; no test
is skipped.

## Evidence milestone

After all implementation, tests, docs, fingerprints, and gates are committed with a clean
tree, run:

```bash
make evidence-p5
```

The collector reruns every retained P0–P4 gate plus the complete zero-exception suite.
It requires the authorized P5 branch and accepted P4 base, records the real tested
implementation commit, revision-bound metric sources and statuses, successful actual Compose
runtime and cleanup, and atomically writes `artifacts/p5/summary.json`. Its public-tree digest
excludes only that summary to avoid self-hashing. Commit it separately, then rerun
`make check` and the public-boundary scan. Historical evidence commands P0–P4 are forbidden.

Required P3 test identities include complete outbox field binding, server-controlled approval
time, boundary/alias bypass rejection, version-2 Timer upgrade and Timer restart semantics,
and application-layer deterministic no-op behavior. A missing identity, skip, or nonzero test
outcome prevents evidence replacement.

## Authenticated Studio and HTTP boundaries

The P4 Golden Path is exercised through the authenticated FastAPI mapping, application
services, and bounded worker facade. A server-side session derives
`RequestPrincipalContext`; request bodies cannot submit tenant, namespace, principal kind,
role, or session authority. See [the operator guide](p4/golden-path.md) for the one-time
token retrieval and isolated Compose workflow. P4 covers the first bootstrap Admin only;
general enrollment, recovery, and full RBAC hardening remain P6.

Every check removes its temporary environment. If a contributor independently creates a
runtime database, `.venv`, `node_modules`, cache, coverage, log, or build directory inside
the repository, remove it before running the repository and public-boundary gates.
