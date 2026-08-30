# SPDX-License-Identifier: Apache-2.0

PYTHON ?= python3

.PHONY: help bootstrap lint typecheck test build check boundary scaffold p2-repository p2-provenance p2-architecture p2-core p3-repository p3-provenance p3-architecture p3-migrations p3-persistence p3-runtime p3-golden evidence-p1 evidence-p2 evidence-p3 studio-dev

help:
	@echo "bootstrap    Resolve locked tools in an isolated temporary workspace"
	@echo "check        Run every current P3 local acceptance gate"
	@echo "lint         Run Python and Studio lint/format checks"
	@echo "typecheck    Run Python and Studio type checking"
	@echo "test         Run Python and Studio tests"
	@echo "build        Build the Studio static bundle in isolation"
	@echo "boundary     Scan public files with exact root .git admin handling"
	@echo "p2-repository Validate the current P2 repository boundary"
	@echo "p2-provenance Validate the P2 migration/new-implementation receipt"
	@echo "p2-architecture Validate pure dependency and determinism boundaries"
	@echo "p2-core      Validate required immutable public core contracts"
	@echo "p3-repository Validate the current P3 repository boundary"
	@echo "p3-provenance Validate complete P3 implementation provenance"
	@echo "p3-architecture Validate dependency and deterministic boundaries"
	@echo "p3-migrations Validate checksummed SQLite migrations and pragmas"
	@echo "p3-persistence Run focused persistence and outbox semantics"
	@echo "p3-runtime   Validate stable ports and typed runtime contracts"
	@echo "p3-golden    Run the synthetic restart Golden Path"
	@echo "evidence-p1  Run all gates and rebuild the P1 evidence summary"
	@echo "evidence-p2  Run all gates and atomically rebuild P2 evidence"
	@echo "evidence-p3  Run all gates and atomically write P3 evidence"
	@echo "studio-dev   Start an isolated preview of the static Studio shell"

bootstrap:
	$(PYTHON) -B -m scripts.run_p3_toolchain --scope bootstrap

lint:
	$(PYTHON) -B -m scripts.run_p3_toolchain --scope lint

typecheck:
	$(PYTHON) -B -m scripts.run_p3_toolchain --scope typecheck

test:
	$(PYTHON) -B -m scripts.run_p3_toolchain --scope test

build:
	$(PYTHON) -B -m scripts.run_p3_toolchain --scope build

check:
	$(PYTHON) -B -m scripts.run_p3_toolchain --scope all

boundary:
	$(PYTHON) -B scripts/check_public_boundary.py .

scaffold:
	$(PYTHON) -B scripts/check_p1_scaffold.py .

p2-repository:
	$(PYTHON) -B scripts/check_p2_repository.py .

p2-provenance:
	$(PYTHON) -B scripts/check_p2_provenance.py .

p2-architecture:
	$(PYTHON) -B scripts/check_p2_architecture.py .

p2-core:
	PYTHONPATH=src $(PYTHON) -B scripts/check_p2_core_contracts.py .

p3-repository:
	$(PYTHON) -B scripts/check_p3_repository.py .

p3-provenance:
	$(PYTHON) -B scripts/check_p3_provenance.py .

p3-architecture:
	$(PYTHON) -B scripts/check_p3_architecture.py .

p3-migrations:
	PYTHONPATH=src $(PYTHON) -B scripts/check_p3_migrations.py .

p3-persistence:
	PYTHONPATH=src $(PYTHON) -B scripts/check_p3_persistence.py

p3-runtime:
	PYTHONPATH=src $(PYTHON) -B scripts/check_p3_runtime_contracts.py .

p3-golden:
	PYTHONPATH=src $(PYTHON) -B scripts/check_p3_golden_path.py

evidence-p1:
	$(PYTHON) -B scripts/run_p1_toolchain.py --scope all --write-evidence

evidence-p2:
	$(PYTHON) -B -m scripts.run_p2_toolchain --scope all --write-evidence

evidence-p3:
	$(PYTHON) -B -m scripts.run_p3_toolchain --scope all --write-evidence

studio-dev:
	$(PYTHON) -B -m scripts.run_p3_toolchain --studio-dev
