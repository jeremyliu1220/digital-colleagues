<!-- SPDX-License-Identifier: Apache-2.0 -->

# Local Development

## Prerequisites

- Python 3.12 or newer (`PYTHON=python3.13` may be passed to Make)
- Node.js 22.12 or newer
- npm 11 or a compatible npm that honors the committed lockfile
- Git and Make
- Docker Engine with Compose v2 only for an actual container Golden Path

No provider account, live credential, parent checkout, or checked-in database is needed.
The default path uses deterministic intelligence, a synthetic reference channel, and OS
temporary SQLite files. P7 adapter contract tests use only a controlled loopback stub and
temporary opaque credentials. Without Docker, static checks still run, but required actual
P7 container evidence is `not_evaluated` and P7 completion is blocked.

## Isolated tool workspace

```bash
make bootstrap
```

The command installs `requirements/p4.lock` into a temporary virtual environment, copies
Studio to a temporary directory, runs environment checks, and deletes both. It creates no
repository `.venv`, `node_modules`, cache, database, coverage, or build output. Direct
runtime and development dependencies are exactly pinned in `pyproject.toml`; the lock also
pins resolved transitives.

The current schema applies migrations 001–007. Migration 007 adds P6 local governance
state; migrations 001–006 remain byte-immutable. P7 adapters are stateless and add no
migration 008.
Never edit an applied migration; add the next numbered file and checksum instead.

## P7 credential and network boundary

The normal composition root accepts only allowlisted default modes. Optional
`http_json_v1` modes require an explicit startup configuration, protocol version, fixed
HTTPS endpoint, and operator-created read-only credential file. Test-only HTTP also
requires explicit permission and an IP-literal loopback host. Do not pass credentials on a
command line, commit them, or place them in a URL or environment variable. Browser and
Studio inputs cannot configure adapters.

Public P7 gates make no external call. They create an isolated loopback stub and temporary
credential files, then delete them. Live-provider acceptance is separate, explicitly
authorized, non-public work and is not part of `make check` or P7 evidence.

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
`p5-compose`, `p5-compose-runtime`, and `p5-golden`, plus every P6 target documented in
`make help`. P7 adds `p7-repository`, `p7-provenance`, `p7-architecture`,
`p7-model-adapter`, `p7-channel-adapter`, `p7-configuration`, `p7-abuse`, `p7-compose`,
`p7-compose-runtime`, and `p7-golden`. Static/config validation and the Docker-required
actual runtime Gate remain separate. Earlier targets remain available as regression gates.
The literal full unittest command can bootstrap its API-test dependencies into an OS
temporary environment when FastAPI is not installed in the invoking interpreter; no test
is skipped.

## Evidence milestone

After P7 implementation, tests, docs, provenance, and gates are committed with a clean
tree, run:

```bash
make evidence-p7
```

The collector reruns retained P0–P6 gates plus the complete zero-exception P7 suite. It
requires the authorized P7 branch and accepted P6 base, records the real tested
implementation commit, synthetic/offline evidence class, successful actual Compose runtime
and cleanup, and atomically writes `artifacts/p7/summary.json`. Its public-tree digest
excludes only that summary to avoid self-hashing. Commit it separately, then rerun focused
P7 gates, `make check`, the public-boundary scan, and actual runtime. Historical evidence
commands P0–P6 are forbidden.

Required P3 test identities include complete outbox field binding, server-controlled approval
time, boundary/alias bypass rejection, version-2 Timer upgrade and Timer restart semantics,
and application-layer deterministic no-op behavior. A missing identity, skip, or nonzero test
outcome prevents evidence replacement.

## Authenticated Studio and HTTP boundaries

The accepted P4-P6 Golden Path is exercised through the authenticated FastAPI mapping, application
services, and bounded worker facade. A server-side session derives
`RequestPrincipalContext`; request bodies cannot submit tenant, namespace, principal kind,
role, or session authority. See [the operator guide](p4/golden-path.md) for the one-time
token retrieval and isolated Compose workflow. P6 adds accepted enrollment, recovery,
versioned RBAC, two-person change approval, and bounded audit export. P7 adapters do not
alter these boundaries.

Every check removes its temporary environment. If a contributor independently creates a
runtime database, `.venv`, `node_modules`, cache, coverage, log, or build directory inside
the repository, remove it before running the repository and public-boundary gates.
