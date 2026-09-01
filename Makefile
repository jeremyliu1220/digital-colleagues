# SPDX-License-Identifier: Apache-2.0

PYTHON ?= python3

.PHONY: help bootstrap lint typecheck test build check boundary scaffold p2-repository p2-provenance p2-architecture p2-core p3-repository p3-provenance p3-architecture p3-migrations p3-persistence p3-runtime p3-golden p4-repository p4-provenance p4-architecture p4-migrations p4-authentication p4-studio p4-compose p4-compose-runtime p4-golden p5-repository p5-provenance p5-architecture p5-migrations p5-builder p5-policy p5-studio p5-compose p5-compose-runtime p5-golden evidence-p1 evidence-p2 evidence-p3 evidence-p4 evidence-p5 studio-dev

help:
	@echo "bootstrap    Resolve locked tools in an isolated temporary workspace"
	@echo "check        Run every current P5 gate plus retained P0-P4 regressions"
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
	@echo "p4-repository Validate P4 history and residue boundaries"
	@echo "p4-provenance Validate complete P4 change provenance"
	@echo "p4-architecture Validate P4 dependencies and authority mapping"
	@echo "p4-migrations Validate additive migrations 004-005 and retained migrations"
	@echo "p4-authentication Validate bootstrap and session controls"
	@echo "p4-studio    Validate the authenticated Studio workflow"
	@echo "p4-compose   Validate static local Compose topology and config"
	@echo "p4-compose-runtime Run isolated actual start/recreate/recovery/stop Gate"
	@echo "p4-golden    Run the authenticated fresh-instance Golden Path"
	@echo "p5-repository Validate the fixed P5 branch, base, files, and residue"
	@echo "p5-provenance Validate complete P5 implementation provenance"
	@echo "p5-architecture Validate P5 dependencies, authority, and determinism"
	@echo "p5-migrations Validate migration 006 fresh and version-5 upgrade"
	@echo "p5-builder   Validate revisioned draft lifecycle and exact confirmation"
	@echo "p5-policy    Validate typed policy enforcement and restart semantics"
	@echo "p5-studio    Validate the revisioned Studio workflow and states"
	@echo "p5-compose   Validate static local P5 topology and composition root"
	@echo "p5-compose-runtime Run actual isolated P5 start/restart/fault/cleanup Gate"
	@echo "p5-golden    Run the authenticated P5 builder and policy Golden Path"
	@echo "evidence-p1  Run all gates and rebuild the P1 evidence summary"
	@echo "evidence-p2  Run all gates and atomically rebuild P2 evidence"
	@echo "evidence-p3  Run all gates and atomically write P3 evidence"
	@echo "evidence-p4  Run all gates and atomically write P4 evidence"
	@echo "evidence-p5  Run all gates and atomically write P5 evidence"
	@echo "studio-dev   Start an isolated preview of the static Studio shell"

bootstrap:
	$(PYTHON) -B -m scripts.run_p5_toolchain --scope bootstrap

lint:
	$(PYTHON) -B -m scripts.run_p5_toolchain --scope lint

typecheck:
	$(PYTHON) -B -m scripts.run_p5_toolchain --scope typecheck

test:
	$(PYTHON) -B -m scripts.run_p5_toolchain --scope test

build:
	$(PYTHON) -B -m scripts.run_p5_toolchain --scope build

check:
	$(PYTHON) -B -m scripts.run_p5_toolchain --scope all

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

p4-repository:
	$(PYTHON) -B scripts/check_p4_repository.py .

p4-provenance:
	$(PYTHON) -B scripts/check_p4_provenance.py .

p4-architecture:
	$(PYTHON) -B scripts/check_p4_architecture.py .

p4-migrations:
	PYTHONPATH=src $(PYTHON) -B scripts/check_p4_migrations.py .

p4-authentication:
	PYTHONPATH=src $(PYTHON) -B scripts/check_p4_authentication.py .

p4-studio:
	$(PYTHON) -B scripts/check_p4_studio.py .

p4-compose:
	$(PYTHON) -B scripts/check_p4_compose.py .

p4-compose-runtime:
	$(PYTHON) -B scripts/check_p4_compose_runtime.py .

p4-golden:
	PYTHONPATH=src $(PYTHON) -B scripts/check_p4_golden_path.py

p5-repository:
	$(PYTHON) -B scripts/check_p5_repository.py .

p5-provenance:
	$(PYTHON) -B scripts/check_p5_provenance.py .

p5-architecture:
	$(PYTHON) -B scripts/check_p5_architecture.py .

p5-migrations:
	PYTHONPATH=src $(PYTHON) -B scripts/check_p5_migrations.py .

p5-builder:
	$(PYTHON) -B -m scripts.run_p5_toolchain --scope builder

p5-policy:
	$(PYTHON) -B -m scripts.run_p5_toolchain --scope policy

p5-studio:
	$(PYTHON) -B scripts/check_p5_studio.py .

p5-compose:
	$(PYTHON) -B scripts/check_p5_compose.py .

p5-compose-runtime:
	$(PYTHON) -B scripts/check_p5_compose_runtime.py .

p5-golden:
	$(PYTHON) -B -m scripts.run_p5_toolchain --scope golden

evidence-p1:
	$(PYTHON) -B scripts/run_p1_toolchain.py --scope all --write-evidence

evidence-p2:
	$(PYTHON) -B -m scripts.run_p2_toolchain --scope all --write-evidence

evidence-p3:
	$(PYTHON) -B -m scripts.run_p3_toolchain --scope all --write-evidence

evidence-p4:
	$(PYTHON) -B -m scripts.run_p4_toolchain --scope all --write-evidence

evidence-p5:
	$(PYTHON) -B -m scripts.run_p5_toolchain --scope all --write-evidence

studio-dev:
	$(PYTHON) -B -m scripts.run_p5_toolchain --studio-dev
