<!-- SPDX-License-Identifier: Apache-2.0 -->

# Local Development

## Prerequisites

- Python 3.12 or newer (`PYTHON=python3.13` may be passed to Make when appropriate)
- Node.js 22.12 or newer
- npm 11 or a compatible npm that honors the committed lockfile
- Make

No provider account, credential, database, container runtime, or parent source checkout is
needed for P2 development.

## Isolated tool workspace

```bash
make bootstrap
```

This resolves the exact direct Python development packages and the Studio lockfile in an
operating-system temporary directory, validates the environment, and removes it. It does
not create `.venv`, `node_modules`, cache, or build output in the repository. It does not
initialize Git or contact a product provider.

## Verification

```bash
make check
```

The aggregate command creates the same disposable workspace and runs the equivalent of:

```bash
ruff check src scripts tests
ruff format --check src scripts tests
mypy src scripts tests
python -B scripts/run_unittest_suite.py --start-directory tests --top-level-directory .
npm --prefix studio run lint
npm --prefix studio run format:check
npm --prefix studio run typecheck
npm --prefix studio test
npm --prefix studio run build
python -B scripts/check_public_boundary.py .
python -B scripts/check_p2_repository.py .
python -B scripts/check_p2_provenance.py .
python -B scripts/check_p2_architecture.py .
PYTHONPATH=src python -B scripts/check_p2_core_contracts.py .
```

Rebuild P2 evidence only after all of those pass:

```bash
make evidence-p2
```

The evidence command requires the `codex/*` task branch to derive from the accepted P1
baseline, requires zero remotes, and uses the structured unittest outcome from the one test
execution. Any missing gate, failure, error, skip, expected failure, unexpected success,
or malformed output blocks the atomic artifact update. Claims that cannot be checked from
the public tree stay explicitly unevaluated. `make evidence-p1` is historical and must not
be run on the P2 tree.

## Studio shell

```bash
make studio-dev
```

Vite binds to `127.0.0.1` from a disposable copy. Restart the command to pick up source
edits. The shell is a static positioning view. It reports the P2 core milestone but has no
API, authentication, stored state, provider integration, or product workflow. Runtime
orchestration begins in P3.

Every check removes its temporary environment. `.venv`, `node_modules`, caches, coverage,
and build output must not be treated as public evidence if a contributor creates them by
other means; remove them before running the direct boundary command.
