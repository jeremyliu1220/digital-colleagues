# SPDX-License-Identifier: Apache-2.0

PYTHON ?= python3

.PHONY: help bootstrap lint typecheck test build check boundary scaffold p2-repository p2-provenance p2-architecture p2-core evidence-p1 evidence-p2 studio-dev

help:
	@echo "bootstrap    Resolve locked tools in an isolated temporary workspace"
	@echo "check        Run every current P2 local acceptance gate"
	@echo "lint         Run Python and Studio lint/format checks"
	@echo "typecheck    Run Python and Studio type checking"
	@echo "test         Run Python and Studio tests"
	@echo "build        Build the Studio static bundle in isolation"
	@echo "boundary     Scan public files with exact root .git admin handling"
	@echo "p2-repository Validate the current P2 repository boundary"
	@echo "p2-provenance Validate the P2 migration/new-implementation receipt"
	@echo "p2-architecture Validate pure dependency and determinism boundaries"
	@echo "p2-core      Validate required immutable public core contracts"
	@echo "evidence-p1  Run all gates and rebuild the P1 evidence summary"
	@echo "evidence-p2  Run all gates and atomically rebuild P2 evidence"
	@echo "studio-dev   Start an isolated preview of the static Studio shell"

bootstrap:
	$(PYTHON) -B -m scripts.run_p2_toolchain --scope bootstrap

lint:
	$(PYTHON) -B -m scripts.run_p2_toolchain --scope lint

typecheck:
	$(PYTHON) -B -m scripts.run_p2_toolchain --scope typecheck

test:
	$(PYTHON) -B -m scripts.run_p2_toolchain --scope test

build:
	$(PYTHON) -B -m scripts.run_p2_toolchain --scope build

check:
	$(PYTHON) -B -m scripts.run_p2_toolchain --scope all

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

evidence-p1:
	$(PYTHON) -B scripts/run_p1_toolchain.py --scope all --write-evidence

evidence-p2:
	$(PYTHON) -B -m scripts.run_p2_toolchain --scope all --write-evidence

studio-dev:
	$(PYTHON) -B -m scripts.run_p2_toolchain --studio-dev
