# SPDX-License-Identifier: Apache-2.0

PYTHON ?= python3

.PHONY: help bootstrap lint typecheck test build check boundary scaffold p2-repository p2-provenance p2-architecture p2-core p3-repository p3-provenance p3-architecture p3-migrations p3-persistence p3-runtime p3-golden p4-repository p4-provenance p4-architecture p4-migrations p4-authentication p4-studio p4-compose p4-compose-runtime p4-golden p5-repository p5-provenance p5-architecture p5-migrations p5-builder p5-policy p5-studio p5-compose p5-compose-runtime p5-golden p6-repository p6-provenance p6-architecture p6-migrations p6-authentication p6-rbac p6-change-approval p6-effect-approval p6-audit-export p6-abuse p6-studio p6-compose p6-compose-runtime p6-golden p7-repository p7-provenance p7-architecture p7-model-adapter p7-channel-adapter p7-configuration p7-abuse p7-compose p7-compose-runtime p7-golden p8-repository p8-provenance p8-operations p8-backup-restore p8-diagnostics p8-supply-chain p8-reproducibility p8-release p8-compose-runtime p8-golden p9-repository p9-provenance p9-rebaseline p9-test p9-check p10-repository p10-provenance p10-distribution p10-security p10-operations p10-i18n p10-compatibility p10-reproducibility p10-compose-runtime p10-quickstart p10-test p10-check p10-ci evidence-p1 evidence-p2 evidence-p3 evidence-p4 evidence-p5 evidence-p6 evidence-p7 evidence-p8 evidence-p9 evidence-p10 studio-dev

help:
	@echo "bootstrap    Resolve locked tools in an isolated temporary workspace"
	@echo "check        Run retained P9 at its accepted object, then every P10 Gate"
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
	@echo "p6-repository Validate trusted P6 ancestry and immutable acceptance"
	@echo "p6-provenance Validate complete P6 implementation provenance"
	@echo "p6-architecture Validate P6 dependencies and injected capabilities"
	@echo "p6-migrations Validate migration 007 fresh and version-6 upgrade"
	@echo "p6-authentication Validate enrollment, recovery, and session governance"
	@echo "p6-rbac      Validate typed RBAC and namespace enforcement"
	@echo "p6-change-approval Validate two-person exact governance changes"
	@echo "p6-effect-approval Validate dispatch-time exact-effect authority"
	@echo "p6-audit-export Validate bounded authorized redacted export"
	@echo "p6-abuse     Validate P6 abuse-case refusals"
	@echo "p6-studio    Validate role-aware governance surfaces"
	@echo "p6-compose   Validate static local P6 topology"
	@echo "p6-compose-runtime Run actual P6 restart/recovery/cleanup Gate"
	@echo "p6-golden    Run the synthetic/offline P6 security Golden Path"
	@echo "p7-repository Validate trusted P7 ancestry and immutable acceptance"
	@echo "p7-provenance Validate complete P7 implementation provenance"
	@echo "p7-architecture Validate P7 dependencies and adapter-edge capabilities"
	@echo "p7-model-adapter Validate the provider-neutral model wire contract"
	@echo "p7-channel-adapter Validate exact-effect channel and reconciliation"
	@echo "p7-configuration Validate explicit opt-in, endpoint, and credential bounds"
	@echo "p7-abuse     Validate P7 adapter abuse-case refusals"
	@echo "p7-compose   Validate deterministic default and optional profile"
	@echo "p7-compose-runtime Run actual no-egress P7 adapter and retained P6 runtime"
	@echo "p7-golden    Run the synthetic/offline P7 adapter Golden Path"
	@echo "p8-repository Validate trusted P8 ancestry, history, files, and residue"
	@echo "p8-provenance Validate complete P8 implementation provenance"
	@echo "p8-operations Validate private operator and rollback semantics"
	@echo "p8-backup-restore Validate WAL-safe backup and atomic restore"
	@echo "p8-diagnostics Validate bounded redacted diagnostics"
	@echo "p8-supply-chain Validate locks, image/action pins, SBOM, and NOTICE"
	@echo "p8-reproducibility Build twice and compare all six candidate files"
	@echo "p8-release   Build and validate the exact release-candidate set"
	@echo "p8-compose-runtime Run actual candidate backup/restore/cleanup Gate"
	@echo "p8-golden    Run the P8 release and operational Golden Path"
	@echo "p9-repository Validate exact P9 history, paths, migrations, and clean tree"
	@echo "p9-provenance Validate complete P9 governance provenance"
	@echo "p9-rebaseline Validate fixed P9-P15 productization decisions"
	@echo "p9-test      Run focused P9 negative and abuse tests"
	@echo "p9-check     Run retained P8 toolchain, then all P9 gates and tests"
	@echo "p10-check    Run retained P9 and all static, OCI, Mac runtime, and timing gates"
	@echo "p10-quickstart Build once, then measure three actual clean Mac quickstarts"
	@echo "p10-compose-runtime Exercise native digest-only Compose start and restart"
	@echo "evidence-p10 Rerun all P10 gates and atomically write the final summary"
	@echo "evidence-p1  Run all gates and rebuild the P1 evidence summary"
	@echo "evidence-p2  Run all gates and atomically rebuild P2 evidence"
	@echo "evidence-p3  Run all gates and atomically write P3 evidence"
	@echo "evidence-p4  Run all gates and atomically write P4 evidence"
	@echo "evidence-p5  Run all gates and atomically write P5 evidence"
	@echo "evidence-p6  Run all gates and atomically write P6 evidence"
	@echo "evidence-p7  Run all gates and atomically write P7 evidence"
	@echo "evidence-p8  Run all gates and atomically write P8 evidence"
	@echo "evidence-p9  Run all gates and atomically write P9 evidence"
	@echo "studio-dev   Start an isolated preview of the static Studio shell"

bootstrap:
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope bootstrap

lint:
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope lint

typecheck:
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope typecheck

test:
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope test

build:
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope build

check:
	$(PYTHON) -B -m scripts.run_p10_toolchain --scope all

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

p6-repository:
	$(PYTHON) -B -m scripts.run_p6_toolchain --scope repository

p6-provenance:
	$(PYTHON) -B -m scripts.run_p6_toolchain --scope provenance

p6-architecture:
	$(PYTHON) -B -m scripts.run_p6_toolchain --scope architecture

p6-migrations:
	$(PYTHON) -B -m scripts.run_p6_toolchain --scope migrations

p6-authentication:
	$(PYTHON) -B -m scripts.run_p6_toolchain --scope authentication

p6-rbac:
	$(PYTHON) -B -m scripts.run_p6_toolchain --scope rbac

p6-change-approval:
	$(PYTHON) -B -m scripts.run_p6_toolchain --scope change-approval

p6-effect-approval:
	$(PYTHON) -B -m scripts.run_p6_toolchain --scope effect-approval

p6-audit-export:
	$(PYTHON) -B -m scripts.run_p6_toolchain --scope audit-export

p6-abuse:
	$(PYTHON) -B -m scripts.run_p6_toolchain --scope abuse

p6-studio:
	$(PYTHON) -B -m scripts.run_p6_toolchain --scope studio

p6-compose:
	$(PYTHON) -B -m scripts.run_p6_toolchain --scope compose

p6-compose-runtime:
	$(PYTHON) -B scripts/check_p6_compose_runtime.py .

p6-golden:
	$(PYTHON) -B -m scripts.run_p6_toolchain --scope golden

p7-repository:
	$(PYTHON) -B -m scripts.run_p7_toolchain --scope repository

p7-provenance:
	$(PYTHON) -B -m scripts.run_p7_toolchain --scope provenance

p7-architecture:
	$(PYTHON) -B -m scripts.run_p7_toolchain --scope architecture

p7-model-adapter:
	$(PYTHON) -B -m scripts.run_p7_toolchain --scope model-adapter

p7-channel-adapter:
	$(PYTHON) -B -m scripts.run_p7_toolchain --scope channel-adapter

p7-configuration:
	$(PYTHON) -B -m scripts.run_p7_toolchain --scope configuration

p7-abuse:
	$(PYTHON) -B -m scripts.run_p7_toolchain --scope abuse

p7-compose:
	$(PYTHON) -B -m scripts.run_p7_toolchain --scope compose

p7-compose-runtime:
	$(PYTHON) -B scripts/check_p7_compose_runtime.py .

p7-golden:
	$(PYTHON) -B -m scripts.run_p7_toolchain --scope golden

p8-repository:
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope repository

p8-provenance:
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope provenance

p8-operations:
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope operations

p8-backup-restore:
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope backup-restore

p8-diagnostics:
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope diagnostics

p8-supply-chain:
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope supply-chain

p8-reproducibility:
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope reproducibility

p8-release:
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope release

p8-compose-runtime:
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope compose-runtime

p8-golden:
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope golden

p9-repository:
	$(PYTHON) -B -m scripts.run_p9_toolchain --scope repository

p9-provenance:
	$(PYTHON) -B -m scripts.run_p9_toolchain --scope provenance

p9-rebaseline:
	$(PYTHON) -B -m scripts.run_p9_toolchain --scope rebaseline

p9-test:
	$(PYTHON) -B -m scripts.run_p9_toolchain --scope test

p9-check:
	$(PYTHON) -B -m scripts.run_p9_toolchain --scope all

p10-repository:
	$(PYTHON) -B scripts/check_p10_repository.py .

p10-provenance:
	$(PYTHON) -B scripts/check_p10_provenance.py .

p10-distribution:
	$(PYTHON) -B scripts/check_p10_distribution.py .

p10-security:
	$(PYTHON) -B scripts/check_p10_security.py .

p10-operations:
	$(PYTHON) -B scripts/check_p10_operations.py .

p10-i18n:
	$(PYTHON) -B scripts/check_p10_i18n.py .

p10-compatibility:
	$(PYTHON) -B scripts/check_p10_compatibility.py .

p10-reproducibility:
	$(PYTHON) -B scripts/check_p10_reproducibility.py .

p10-compose-runtime:
	$(PYTHON) -B -m scripts.run_p10_toolchain --scope compose-runtime

p10-quickstart:
	$(PYTHON) -B -m scripts.run_p10_toolchain --scope quickstart

p10-test:
	$(PYTHON) -B -m scripts.run_p10_toolchain --scope test

p10-check:
	$(PYTHON) -B -m scripts.run_p10_toolchain --scope all

p10-ci:
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope lint
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope typecheck
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope build
	$(PYTHON) -B scripts/check_p10_distribution.py .
	$(PYTHON) -B scripts/check_p10_security.py .
	$(PYTHON) -B scripts/check_p10_operations.py .
	$(PYTHON) -B scripts/check_p10_i18n.py .
	$(PYTHON) -B scripts/check_p10_compatibility.py .
	$(PYTHON) -B scripts/check_p10_reproducibility.py .
	$(PYTHON) -B -m unittest tests.p10.test_distribution tests.p10.test_security tests.p10.test_operations tests.p10.test_i18n tests.p10.test_compatibility tests.p10.test_reproducibility -v

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

evidence-p6:
	$(PYTHON) -B -m scripts.run_p6_toolchain --scope all --write-evidence

evidence-p7:
	$(PYTHON) -B -m scripts.run_p7_toolchain --scope all --write-evidence

evidence-p8:
	$(PYTHON) -B -m scripts.run_p8_toolchain --scope all --write-evidence

evidence-p9:
	$(PYTHON) -B -m scripts.run_p9_toolchain --scope all --write-evidence

evidence-p10:
	$(PYTHON) -B -m scripts.run_p10_toolchain --scope all --write-evidence

studio-dev:
	$(PYTHON) -B -m scripts.run_p5_toolchain --studio-dev
