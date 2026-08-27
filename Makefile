# SPDX-License-Identifier: Apache-2.0

PYTHON ?= python3

.PHONY: help bootstrap lint typecheck test build check boundary scaffold evidence-p1 studio-dev

help:
	@echo "bootstrap    Resolve locked tools in an isolated temporary workspace"
	@echo "check        Run every P1 local acceptance gate"
	@echo "lint         Run Python and Studio lint/format checks"
	@echo "typecheck    Run Python and Studio type checking"
	@echo "test         Run Python and Studio tests"
	@echo "build        Build the Studio static bundle in isolation"
	@echo "boundary     Scan public files with exact root .git admin handling"
	@echo "evidence-p1  Run all gates and rebuild the P1 evidence summary"
	@echo "studio-dev   Start an isolated preview of the P1 Studio shell"

bootstrap:
	$(PYTHON) -B scripts/run_p1_toolchain.py --scope bootstrap

lint:
	$(PYTHON) -B scripts/run_p1_toolchain.py --scope lint

typecheck:
	$(PYTHON) -B scripts/run_p1_toolchain.py --scope typecheck

test:
	$(PYTHON) -B scripts/run_p1_toolchain.py --scope test

build:
	$(PYTHON) -B scripts/run_p1_toolchain.py --scope build

check:
	$(PYTHON) -B scripts/run_p1_toolchain.py --scope all

boundary:
	$(PYTHON) -B scripts/check_public_boundary.py .

scaffold:
	$(PYTHON) -B scripts/check_p1_scaffold.py .

evidence-p1:
	$(PYTHON) -B scripts/run_p1_toolchain.py --scope all --write-evidence

studio-dev:
	$(PYTHON) -B scripts/run_p1_toolchain.py --studio-dev
