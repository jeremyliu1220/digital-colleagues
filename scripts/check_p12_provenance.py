# SPDX-License-Identifier: Apache-2.0

"""Validate exact P12 v4 provenance and protected historical identities."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p12_historical_inventory import check_historical_inventory  # noqa: E402
from scripts.check_p12_migrations import MANIFEST, MIGRATIONS, OWNERS  # noqa: E402
from scripts.check_p12_repository import (  # noqa: E402
    ACCEPTANCE_BLOB,
    ACCEPTANCE_COMMIT,
    ACCEPTANCE_SHA256,
    ACCEPTANCE_TREE,
    BASE_COMMIT,
    BASE_TREE,
    BRANCH,
    REJECTED_V1_COMMIT,
    REJECTED_V2_ACCEPTANCE_BLOB,
    REJECTED_V2_ACCEPTANCE_SHA256,
    REJECTED_V2_COMMIT,
    SUPERSEDED_V3_ACCEPTANCE_BLOB,
    SUPERSEDED_V3_ACCEPTANCE_BYTE_COUNT,
    SUPERSEDED_V3_ACCEPTANCE_LINE_COUNT,
    SUPERSEDED_V3_ACCEPTANCE_SHA256,
    SUPERSEDED_V3_COMMIT,
    P12GateError,
    acceptance_paths,
    git,
    implementation_paths,
    raw_blob_bytes,
)

RECEIPT_PATH = "provenance/p12-change-receipt.json"
BLUEPRINT_SOURCE: dict[str, object] = {
    "name": "p12-v4-historical-platform-classification-change-decision-blueprint.md",
    "line_count": 1183,
    "byte_count": 223853,
    "sha256": "7f58f95e7f33f65348162754017da828a9db6272d0d2cec22dd7b91ace0a8263",
    "git_blob": "854cd5691cfca94edfc1ffc1ed6a73e44a074667",
    "repository_evidence": False,
}

PORTABLE_OBJECTS: dict[str, dict[str, str]] = {
    "P8": {
        "commit": "0bb80ab187932fbad42fbf665b8310987609a1f5",
        "tree": "311eb777c3d17a9a3722a16c394b9913c283b416",
        "branch": "codex/p8-release-readiness",
    },
    "P9": {
        "commit": "11aa240af8db2ca515325dc059b1a77f7badc874",
        "tree": "a27cb6ce9f568b04083a88f7ba06f033235f4cbc",
        "branch": "codex/p9-productization-rebaseline",
    },
    "P10": {
        "commit": "4bef5629d450c6bb3940f606fc90194e008ee8fd",
        "tree": "909b566b7ba9f7beb143cd0b29cf95fbd1178bbe",
        "branch": "codex/p10-mac-quickstart",
    },
    "P11": {
        "commit": "7e5387f148f86b5c9b07820dd8b8f4e18e12dc38",
        "tree": "6d7c1b3053fefc1f3b14a4b39fde2d5adb641990",
        "branch": "codex/p11-agent-packages",
    },
    "P11R": {
        "commit": BASE_COMMIT,
        "tree": BASE_TREE,
        "branch": "codex/p11r-ci-alignment",
    },
}

HISTORY: dict[str, str] = {
    "p8_final": PORTABLE_OBJECTS["P8"]["commit"],
    "p9_final": PORTABLE_OBJECTS["P9"]["commit"],
    "p10_final": PORTABLE_OBJECTS["P10"]["commit"],
    "p11_final": PORTABLE_OBJECTS["P11"]["commit"],
    "p11r_acceptance": "61d5c94e24157b93bc4b4bcca42b4d8d2eab8fec",
    "p11r_implementation": "4a6df2db5c964b2bd6f052db6276dc303524230b",
    "p11r_final": BASE_COMMIT,
}

EXCLUDED_GATE_IDS = (
    "p8_compose_runtime",
    "p8_golden_path",
    "p10_compose_runtime",
    "p10_quickstart",
    "p10_remote_distribution",
)

DARWIN_EVIDENCE_ANCHORS: dict[str, dict[str, object]] = {
    "p8_compose_runtime": {
        "source_commit": PORTABLE_OBJECTS["P8"]["commit"],
        "source_tree": PORTABLE_OBJECTS["P8"]["tree"],
        "source_path": "artifacts/p8/summary.json",
        "source_blob": "964406b20e9fc1e98b8eeda3c24bf3f22f226768",
        "source_file_sha256": "78905893f9a06bf6b5361c76a8e152dbe8de2ec53d1aede84fca2f7ce1b5921b",
        "selection": 'result = p8_summary["compose_runtime"]',
        "canonicalization": "P12-CJ-1",
        "canonical_bytes": 2348,
        "canonical_sha256": "a2acd8e3f935d9c520f58e76b8384514e596e59f94f7bb62e1881ce9183c9bbd",
        "anchor_platform": "darwin",
        "anchor_historical_status": "passed",
        "purpose": "immutable_platform_scoped_identity_only",
    },
    "p8_golden_path": {
        "source_commit": PORTABLE_OBJECTS["P8"]["commit"],
        "source_tree": PORTABLE_OBJECTS["P8"]["tree"],
        "source_path": "artifacts/p8/summary.json",
        "source_blob": "964406b20e9fc1e98b8eeda3c24bf3f22f226768",
        "source_file_sha256": "78905893f9a06bf6b5361c76a8e152dbe8de2ec53d1aede84fca2f7ce1b5921b",
        "selection": 'result = p8_summary["golden_path"]',
        "canonicalization": "P12-CJ-1",
        "canonical_bytes": 2034,
        "canonical_sha256": "c1f1f8148cd3b0184d92720e862bbadfe7e330fd4087b7eb03190400d6742f44",
        "anchor_platform": "darwin",
        "anchor_historical_status": "passed",
        "purpose": "immutable_platform_scoped_identity_only",
    },
    "p10_compose_runtime": {
        "source_commit": PORTABLE_OBJECTS["P10"]["commit"],
        "source_tree": PORTABLE_OBJECTS["P10"]["tree"],
        "source_path": "artifacts/p10/summary.json",
        "source_blob": "a4c1a59fffec9c30160787a7bec584e228fb9f35",
        "source_file_sha256": "876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae",
        "selection": 'result = p10_summary["compose_runtime"]',
        "canonicalization": "P12-CJ-1",
        "canonical_bytes": 476,
        "canonical_sha256": "4f6f5de0a92d2aa3bea1ab80ad94b869a4fd1cbe5f459804eea3cd86377e137b",
        "anchor_platform": "darwin",
        "anchor_historical_status": "passed",
        "purpose": "immutable_platform_scoped_identity_only",
    },
    "p10_quickstart": {
        "source_commit": PORTABLE_OBJECTS["P10"]["commit"],
        "source_tree": PORTABLE_OBJECTS["P10"]["tree"],
        "source_path": "artifacts/p10/summary.json",
        "source_blob": "a4c1a59fffec9c30160787a7bec584e228fb9f35",
        "source_file_sha256": "876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae",
        "selection": 'result = p10_summary["quickstart"]',
        "canonicalization": "P12-CJ-1",
        "canonical_bytes": 874,
        "canonical_sha256": "75c18fadb57dd93914a8f99996857af22c2da8c82c504582b9eaa412c1f00c1b",
        "anchor_platform": "darwin",
        "anchor_historical_status": "passed",
        "purpose": "immutable_platform_scoped_identity_only",
    },
    "p10_remote_distribution": {
        "source_commit": PORTABLE_OBJECTS["P10"]["commit"],
        "source_tree": PORTABLE_OBJECTS["P10"]["tree"],
        "source_path": "artifacts/p10/summary.json",
        "source_blob": "a4c1a59fffec9c30160787a7bec584e228fb9f35",
        "source_file_sha256": "876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae",
        "selection": 'result = {"distribution":p10_summary["remote_distribution"],"quickstart":p10_summary["remote_quickstart"]}',
        "canonicalization": "P12-CJ-1",
        "canonical_bytes": 2538,
        "canonical_sha256": "4383d540c4cd95f62db32aaadc1dfdf8e027eb0bd81b9909c4a0dda9a3d06c78",
        "anchor_platform": "darwin",
        "anchor_historical_status": "passed",
        "purpose": "immutable_platform_scoped_identity_only",
    },
}

REJECTED_ATTEMPTS: dict[str, dict[str, Any]] = {
    "v1": {
        "branch": "codex/p12-public-pilot-continuity-rebaseline",
        "commit": REJECTED_V1_COMMIT,
        "tree": "557a74e9174247483362bbbd15cd265113775d12",
        "sole_parent": BASE_COMMIT,
        "acceptance_blob": "26562d795980ec8d6d9ea36ff3fcc718b41c09e8",
        "remote_branch": "absent_at_rejection",
        "implementation_count": 0,
        "publication_count": 0,
    },
    "v2": {
        "branch": "codex/p12-public-pilot-continuity-rebaseline-v2",
        "acceptance_commit": "3639fa08ca44820bb922e0644095c9fb9c24d3e6",
        "acceptance_tree": "71c411660e0f7ff26e8ad1451acaa0ea26fa384b",
        "acceptance_blob": "50453e154cf642bc7b90644660e1d956b04f966a",
        "acceptance_sha256": "be3ad1967a98c67ae34ad7c22c35a9ec1f637a780c930ae4e8349f126e64800b",
        "final_commit": REJECTED_V2_COMMIT,
        "final_tree": "01ee7b08cc870a626698ac9a3fc46ec92bf0f4e0",
        "pull_request": {
            "number": 14,
            "state": "CLOSED",
            "base_ref": "main",
            "base_sha": BASE_COMMIT,
            "head_ref": "codex/p12-public-pilot-continuity-rebaseline-v2",
            "head_sha": REJECTED_V2_COMMIT,
            "merged_at": None,
            "merge_commit": None,
            "auto_merge_request": None,
        },
        "rejection": "rejected_linux_historical_replay_contract_infeasible",
        "commit_chain": [
            {
                "commit": "3639fa08ca44820bb922e0644095c9fb9c24d3e6",
                "parent": BASE_COMMIT,
                "tree": "71c411660e0f7ff26e8ad1451acaa0ea26fa384b",
            },
            {
                "commit": "eb4dbc7e1cd1c1a1671f58441bb3e49d08e77a5e",
                "parent": "3639fa08ca44820bb922e0644095c9fb9c24d3e6",
                "tree": "42c05dea50cfe45b92a055c835e63045ec88a082",
            },
            {
                "commit": "5d0818ab9671dc023afd5ad23b6b0995e79ef68a",
                "parent": "eb4dbc7e1cd1c1a1671f58441bb3e49d08e77a5e",
                "tree": "99e0fd7a60df0584661d8e9162bf9dde1d0abf22",
            },
            {
                "commit": "b255d79df2b435ba754b7afe450d0a45559ea72a",
                "parent": "5d0818ab9671dc023afd5ad23b6b0995e79ef68a",
                "tree": "d4517e99bb155353704726d8a11e22e935dfe7dc",
            },
            {
                "commit": "fc145550b750c172899bc1497ff5fede387c07dc",
                "parent": "b255d79df2b435ba754b7afe450d0a45559ea72a",
                "tree": "0d4ec3cba2040d640e3adb8880c98a4525fa2207",
            },
            {
                "commit": "098ba1399f7146258027674d5d312966fbdfe037",
                "parent": "fc145550b750c172899bc1497ff5fede387c07dc",
                "tree": "f0f65517dea5b3292c6f3f87c8c10b90295487e8",
            },
            {
                "commit": "5722067571b70911c38b50ead23d198dcfbd4f20",
                "parent": "098ba1399f7146258027674d5d312966fbdfe037",
                "tree": "f66d1a7fada6db1a883c830f91ac6222983fa6c8",
            },
            {
                "commit": REJECTED_V2_COMMIT,
                "parent": "5722067571b70911c38b50ead23d198dcfbd4f20",
                "tree": "01ee7b08cc870a626698ac9a3fc46ec92bf0f4e0",
            },
        ],
        "failed_runs": [
            {
                "run_id": 34542709145,
                "event": "pull_request",
                "workflow": "CI",
                "head": "fc145550b750c172899bc1497ff5fede387c07dc",
                "current_attempt": 1,
                "attempts": [{"attempt": 1, "status": "completed", "conclusion": "failure"}],
            },
            {
                "run_id": 34564478590,
                "event": "pull_request",
                "workflow": "CI",
                "head": REJECTED_V2_COMMIT,
                "current_attempt": 2,
                "attempts": [
                    {
                        "attempt": 1,
                        "status": "completed",
                        "conclusion": "failure",
                        "created_at": "2026-09-11T05:03:14Z",
                        "completed_at": "2026-09-11T05:06:34Z",
                    },
                    {
                        "attempt": 2,
                        "status": "completed",
                        "conclusion": "failure",
                        "created_at": "2026-09-11T05:12:52Z",
                        "completed_at": "2026-09-11T05:16:00Z",
                    },
                ],
            },
        ],
        "retention_days": 90,
        "earliest_normal_expiry": "2026-12-10T05:03:14Z",
        "safe_failure_boundary": "accepted_p8_actual_compose_pre_start_restore",
        "summary_count": 0,
        "publication_count": 0,
    },
    "v3": {
        "classification": "superseded_acceptance_only",
        "branch": "codex/p12-public-pilot-continuity-rebaseline-v3",
        "commit": SUPERSEDED_V3_COMMIT,
        "tree": "1cdce2a41f84ee4243d04be781ad187eb5f5fab9",
        "sole_parent": BASE_COMMIT,
        "acceptance_blob": "40c93a2aa8930c71e14fefac2053a10ed137af58",
        "acceptance_sha256": "6afddd55f4f8458c94dcd56b781e47fef66a06d954d4246aa3855b4daf2e0e3c",
        "acceptance_line_count": 3488,
        "acceptance_byte_count": 232313,
        "remote_branch": "absent",
        "pull_request": "absent",
        "implementation_count": 0,
        "publication_count": 0,
    },
}

STAGE10_FAILURE_DIAGNOSTICS: dict[str, dict[str, Any]] = {
    "d1_python312_lock_probe": {
        "classification": "material_failed_experiment",
        "diagnostic_python": "3.12.14",
        "platform": {"os": "Darwin", "architecture": "arm64"},
        "p8_commit": PORTABLE_OBJECTS["P8"]["commit"],
        "p8_tree": PORTABLE_OBJECTS["P8"]["tree"],
        "python_lock": {
            "path": "requirements/p8.lock",
            "blob": "819980980ba87d1b7166af4b4b0da53ca4e4ac63",
            "sha256": "5afb5bc2f6bf2cfdc77d0457b92255f822d89cd3cd754ebb876741d7ee6430d0",
        },
        "npm_lock": {
            "path": "studio/package-lock.json",
            "blob": "ec0730513988e98adaf2d935885859ba1b58f7b9",
        },
        "failure_step": "hash_locked_pip_dependency_install",
        "package": "librt==0.15.0",
        "selected_wheel": "librt-0.15.0-cp312-cp312-macosx_11_0_arm64.whl",
        "lock_allowed_sha256": ("234d8d394721fa0d786af15ebf1f3fb7f3ed82fd1cd0cde45c2f247b5d4281d2"),
        "observed_wheel_sha256": (
            "71599e011ac880e8e45d46047d714871894c7d4ab6f25626f8d4f89da21f368d"
        ),
        "unittest_leaf_executed": False,
        "consequence": (
            "Python 3.12 hypothesis was not evaluated because the accepted lock does not "
            "support the selected macOS arm64 wheel"
        ),
        "accepted_lock_modified_or_relaxed": False,
        "stage10_retry": False,
        "raw_logs_retained": False,
        "summary_count": 0,
        "evidence_count": 0,
        "publication_count": 0,
        "remote_mutation_count": 0,
    },
    "d2_python313_npm_residue_reproduction": {
        "classification": "material_failed_experiment",
        "formal_gate": "p12-portable-history",
        "leaf_gate": "p8_python_unittest",
        "p8_commit": PORTABLE_OBJECTS["P8"]["commit"],
        "p8_tree": PORTABLE_OBJECTS["P8"]["tree"],
        "runner": {
            "path": "scripts/run_p8_unittest_suite.py",
            "blob": "35d0ef6a88025ef5bc10925009e044c6a84025c8",
        },
        "python_lock": {
            "path": "requirements/p8.lock",
            "blob": "819980980ba87d1b7166af4b4b0da53ca4e4ac63",
            "sha256": "5afb5bc2f6bf2cfdc77d0457b92255f822d89cd3cd754ebb876741d7ee6430d0",
        },
        "npm_lock": {
            "path": "studio/package-lock.json",
            "blob": "ec0730513988e98adaf2d935885859ba1b58f7b9",
        },
        "platform": {"os": "Darwin", "architecture": "arm64"},
        "diagnostic_python": "3.13.5",
        "python_setup": "hash_locked",
        "npm_setup": "exact_locked",
        "counts": {"tests": 308, "failures": 3, "errors": 6, "skips": 0},
        "exit_status": 1,
        "failure_ids": [
            (
                "tests.p0.test_planning_contract.PlanningContractTests."
                "test_comment_capable_files_have_spdx_headers"
            ),
            (
                "tests.p0.test_public_boundary.PublicBoundaryTests."
                "test_current_project_is_clean_with_zero_exceptions"
            ),
            (
                "tests.p1.test_repository_scaffold.RepositoryScaffoldTests."
                "test_comment_capable_p1_files_have_spdx_headers"
            ),
        ],
        "error_ids": [
            (
                "tests.architecture.test_p2_boundaries.P2BoundaryTests."
                "test_current_repository_and_provenance_gates_pass"
            ),
            (
                "tests.p4.test_evidence_gate.P4RepositoryGateTests."
                "test_real_hotfix_tree_is_an_accepted_p4_descendant"
            ),
            (
                "tests.p5.test_builder.P5RepositoryGateTests."
                "test_real_hotfix_tree_is_an_accepted_p5_descendant"
            ),
            (
                "tests.p6.test_repository.P6RepositoryGateTests."
                "test_exact_root_and_real_development_tree_pass"
            ),
            (
                "tests.p7.test_repository.P7RepositoryGateTests."
                "test_exact_root_and_real_development_tree_pass"
            ),
            (
                "tests.p8.test_repository.P8RepositoryTests."
                "test_real_tree_has_fixed_base_acceptance_history_and_required_files"
            ),
        ],
        "result": "exact_reproduction",
        "root_cause": (
            "npm setup residue was visible to Python, repository and public-boundary checks"
        ),
        "stage10_retry": False,
        "raw_logs_retained": False,
        "summary_count": 0,
        "evidence_count": 0,
        "publication_count": 0,
        "remote_mutation_count": 0,
    },
}

P10_RUNS: dict[str, tuple[str, str]] = {
    "34202520699": ("05e73ea23ac650edfae59fa409a770fdf967af3a", "success"),
    "34203006909": ("05e73ea23ac650edfae59fa409a770fdf967af3a", "failure"),
    "34204280131": ("ddc04021f94ca888235c53f96ed64218de8c3e67", "failure"),
    "34204837101": ("ae714c128f844466c76811986c0605e39fce12cc", "failure"),
    "34205272328": ("76b278feedbb79b9a4c0d023e328911096fe57ae", "failure"),
    "34206039435": ("a003d540093df9a08437c47e9c8ff16970e5e645", "success"),
    "34235760264": ("62b226064d2597a4ca6a67f9f2c20a79a815732b", "success"),
    "34236719816": ("d9fd27670a36f699bf299f6154afce180bea64cc", "failure"),
    "34237810474": ("cc4acd3bda3f4d2bdfee9392c7d0f85f90c07688", "success"),
}
P10_SUBJECTS = (
    "ghcr.io/jeremyliu1220/digital-colleagues-runtime",
    "ghcr.io/jeremyliu1220/digital-colleagues-studio",
)
P10_SETS: dict[str, dict[str, str]] = {
    "superseded": {
        "source_commit": "05e73ea23ac650edfae59fa409a770fdf967af3a",
        "source_tag": "sha-05e73ea23ac650edfae59fa409a770fdf967af3a",
        "runtime_digest": "sha256:41567ba87a088944cf9a2c17b9b0f4359554c66b2ec1f6d52db46067e1ab9092",
        "studio_digest": "sha256:b7dd4c2b35922ec31a9b38c15316283706a9aab0ffab2101a18f7bf106165f2e",
        "lifecycle": "superseded_contract_noncompliant_source",
    },
    "active": {
        "source_commit": "62b226064d2597a4ca6a67f9f2c20a79a815732b",
        "source_tag": "sha-62b226064d2597a4ca6a67f9f2c20a79a815732b",
        "runtime_digest": "sha256:a5bb41bdb85bf7b5a75dc79967e26943c098b024b64fdd345f5b4c6f4688991d",
        "studio_digest": "sha256:7791d80d9fa464bbd1574601deba5a30ca6d980dab8c8275c24c117fae81e4c9",
        "lifecycle": "passed",
    },
}
P10_GIT_IDENTITIES: dict[str, str] = {
    "4bef5629d450c6bb3940f606fc90194e008ee8fd^{tree}": "909b566b7ba9f7beb143cd0b29cf95fbd1178bbe",
    "99b0045bba48de8e4d44c10ce07d60ba20738a8b:docs/p10/acceptance.md": "c5ac3acd52a8732da617ce5d1d3a7e66e3671c80",
    "4bef5629d450c6bb3940f606fc90194e008ee8fd:artifacts/p10/summary.json": "a4c1a59fffec9c30160787a7bec584e228fb9f35",
    "4bef5629d450c6bb3940f606fc90194e008ee8fd:provenance/p10-migration-receipt.json": "07565307a35902206ee7c80af66b2a02ab876b83",
    "4bef5629d450c6bb3940f606fc90194e008ee8fd:distribution/p10/verification-policy.json": "02aff9c1f3bdd745a6fc479fed635f2f782c346a",
    "4bef5629d450c6bb3940f606fc90194e008ee8fd:docs/p10/distribution.md": "c55393db711f2db49169fbe35e45f5f5e227849a",
}

EVIDENCE_PREFLIGHT = {
    "github_authentication": "read_only_required",
    "read_packages": "manifest_lookup_required",
    "ci_result_transport": "two_exact_canonical_log_envelopes",
    "receipt_lifecycle": "one_use_pending_consumption",
    "python_declarations": "pyproject.toml",
    "python_locked_toolchain_and_transitives": "requirements/p8.lock",
    "installed_version_api": "importlib.metadata.version",
    "normalized_comparison": "packaging.version.Version",
    "tls_primary": "system_default",
    "tls_certificate_failure_fallback": "locked_certifi_only",
    "repository_evidence_write": False,
}
CHANGE_COUNTS = {
    "product_runtime_source": 0,
    "studio_product_behavior": 0,
    "database_schema": 0,
    "migration": 0,
    "dependency_or_lock": 0,
    "distribution": 0,
    "evidence": 0,
}
PRIVACY_DECLARATION = {
    "local_absolute_paths": False,
    "credentials": False,
    "private_identifiers": False,
    "personal_data": False,
    "live_receipts": False,
    "private_provider_data": False,
}
PUBLICATION_DECLARATION = {
    "remote_mutation": False,
    "secrets": False,
    "oidc": False,
    "write_permissions": False,
    "artifact_upload": False,
    "tags": False,
    "releases": False,
    "packages_or_images": False,
    "signatures_or_attestations": False,
}
FORBIDDEN_SELF_REFERENCE_KEYS = {
    "containing_commit",
    "implementation_head",
    "implementation_tree",
    "inventory_blob",
    "ci_run_id",
    "ci_run_attempt",
    "range_digest",
    "p12_change_receipt_blob",
}


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise P12GateError("P12 provenance receipt contains a duplicate JSON key")
        result[key] = value
    return result


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise P12GateError("P12 provenance receipt is unavailable or invalid") from exc


def _dict(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise P12GateError(f"P12 provenance {label} is invalid")
    return value


def _exact_json(actual: object, expected: object) -> bool:
    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and set(actual) == set(expected)
            and all(_exact_json(actual[key], item) for key, item in expected.items())
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(_exact_json(left, right) for left, right in zip(actual, expected, strict=True))
        )
    return type(actual) is type(expected) and actual == expected


def _reject_self_reference(value: object) -> None:
    if isinstance(value, dict):
        if set(value) & FORBIDDEN_SELF_REFERENCE_KEYS:
            raise P12GateError("P12 provenance contains a forbidden future/self reference")
        for item in value.values():
            _reject_self_reference(item)
    elif isinstance(value, list):
        for item in value:
            _reject_self_reference(item)


def _expected_migration_files() -> list[dict[str, str]]:
    return [
        {"path": MANIFEST[0], "blob": MANIFEST[1], "sha256": MANIFEST[2]},
        *[
            {"path": f"migrations/{name}", "blob": blob, "sha256": digest}
            for name, blob, digest in MIGRATIONS
        ],
    ]


def _expected_allowlist(root: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for path in acceptance_paths(root):
        if path == "docs/p12/acceptance.md":
            classification = "acceptance_only"
        elif path == "artifacts/p12/summary.json":
            classification = "summary_only"
        else:
            classification = "implementation"
        records.append({"path": path, "classification": classification})
    return records


def _check_git_identities(root: Path) -> None:
    for value in PORTABLE_OBJECTS.values():
        if git(root, "rev-parse", f"{value['commit']}^{{tree}}") != value["tree"]:
            raise P12GateError("P12 portable historical object identity drifted")
    for expression, expected in P10_GIT_IDENTITIES.items():
        if git(root, "rev-parse", expression) != expected:
            raise P12GateError("P12 protected P10 local Git identity drifted")
    for commit in (
        P10_SETS["superseded"]["source_commit"],
        P10_SETS["active"]["source_commit"],
    ):
        if git(root, "cat-file", "-t", str(commit)) != "commit":
            raise P12GateError("P12 protected P10 source commit is unreadable")
    v1 = REJECTED_ATTEMPTS["v1"]
    if (
        git(root, "rev-parse", f"{v1['commit']}^") != v1["sole_parent"]
        or git(root, "rev-parse", f"{v1['commit']}^{{tree}}") != v1["tree"]
    ):
        raise P12GateError("P12 rejected v1 Git identity drifted")
    v2 = REJECTED_ATTEMPTS["v2"]
    for entry in v2["commit_chain"]:
        if (
            git(root, "rev-parse", f"{entry['commit']}^") != entry["parent"]
            or git(root, "rev-parse", f"{entry['commit']}^{{tree}}") != entry["tree"]
        ):
            raise P12GateError("P12 rejected v2 commit-chain identity drifted")
    v3 = REJECTED_ATTEMPTS["v3"]
    if (
        git(root, "rev-parse", f"{v3['commit']}^") != v3["sole_parent"]
        or git(root, "rev-parse", f"{v3['commit']}^{{tree}}") != v3["tree"]
    ):
        raise P12GateError("P12 superseded v3 Git identity drifted")
    v2_acceptance = raw_blob_bytes(root, REJECTED_V2_ACCEPTANCE_BLOB)
    if hashlib.sha256(v2_acceptance).hexdigest() != REJECTED_V2_ACCEPTANCE_SHA256:
        raise P12GateError("P12 rejected v2 acceptance content drifted")
    v3_acceptance = raw_blob_bytes(root, SUPERSEDED_V3_ACCEPTANCE_BLOB)
    if (
        hashlib.sha256(v3_acceptance).hexdigest() != SUPERSEDED_V3_ACCEPTANCE_SHA256
        or len(v3_acceptance) != SUPERSEDED_V3_ACCEPTANCE_BYTE_COUNT
        or len(v3_acceptance.splitlines()) != SUPERSEDED_V3_ACCEPTANCE_LINE_COUNT
    ):
        raise P12GateError("P12 superseded v3 acceptance content drifted")


def check_provenance(root: Path) -> dict[str, object]:
    receipt = _dict(_read_json(root / RECEIPT_PATH), "root")
    expected_keys = {
        "schema_version",
        "change",
        "contract_version",
        "classification",
        "implementation_basis",
        "base_commit",
        "base_tree",
        "branch",
        "allowlist_path_count",
        "implementation_path_count",
        "implementation_changed_path_count",
        "final_changed_path_count",
        "acceptance",
        "blueprint_source",
        "parent_research_working_tree_read",
        "parent_source_read_count",
        "source_migration_count",
        "transformed_migration_count",
        "allowlist",
        "portable_historical_objects",
        "historical_anchors",
        "darwin_evidence_anchors",
        "rejected_attempts",
        "stage10_failure_diagnostics",
        "portable_historical_inventory",
        "migration_protection",
        "p10_protected_publication",
        "evidence_preflight",
        "change_counts",
        "privacy",
        "publication",
    }
    if set(receipt) != expected_keys:
        raise P12GateError("P12 v4 provenance root schema is not exact")
    _reject_self_reference(receipt)
    identity = {
        "schema_version": 1,
        "change": "P12",
        "contract_version": 4,
        "classification": "governance_only_platform_scoped_continuity_rebaseline",
        "base_commit": BASE_COMMIT,
        "base_tree": BASE_TREE,
        "branch": BRANCH,
        "allowlist_path_count": 42,
        "implementation_path_count": 40,
        "implementation_changed_path_count": 41,
        "final_changed_path_count": 42,
    }
    if any(not _exact_json(receipt.get(key), value) for key, value in identity.items()):
        raise P12GateError("P12 v4 provenance identity is invalid")
    if receipt.get("implementation_basis") != (
        "Immutable P12 v4 acceptance contract, approved blueprint identity, "
        "and accepted P0-P11R history"
    ):
        raise P12GateError("P12 v4 provenance implementation basis is invalid")
    acceptance = _dict(receipt.get("acceptance"), "acceptance")
    if not _exact_json(
        acceptance,
        {
            "commit": ACCEPTANCE_COMMIT,
            "tree": ACCEPTANCE_TREE,
            "blob": ACCEPTANCE_BLOB,
            "sha256": ACCEPTANCE_SHA256,
        },
    ):
        raise P12GateError("P12 provenance acceptance binding is invalid")
    if not _exact_json(receipt.get("blueprint_source"), BLUEPRINT_SOURCE):
        raise P12GateError("P12 v4 blueprint source identity is invalid")
    allowlist = _expected_allowlist(root)
    if not _exact_json(receipt.get("allowlist"), allowlist):
        raise P12GateError("P12 provenance allowlist coverage/classification is not exact")
    if (
        receipt.get("parent_research_working_tree_read") is not False
        or not _exact_json(receipt.get("parent_source_read_count"), 0)
        or not _exact_json(receipt.get("source_migration_count"), 0)
        or not _exact_json(receipt.get("transformed_migration_count"), 0)
    ):
        raise P12GateError("P12 source provenance boundary is invalid")
    if not _exact_json(receipt.get("portable_historical_objects"), PORTABLE_OBJECTS):
        raise P12GateError("P12 portable historical object coverage is invalid")
    if not _exact_json(receipt.get("historical_anchors"), HISTORY):
        raise P12GateError("P12 historical anchor coverage is invalid")
    if not _exact_json(receipt.get("darwin_evidence_anchors"), DARWIN_EVIDENCE_ANCHORS):
        raise P12GateError("P12 accepted P8/P10 Darwin anchor identity drifted")
    if not _exact_json(receipt.get("rejected_attempts"), REJECTED_ATTEMPTS):
        raise P12GateError("P12 rejected/superseded v1/v2/v3 history drifted")
    if not _exact_json(receipt.get("stage10_failure_diagnostics"), STAGE10_FAILURE_DIAGNOSTICS):
        raise P12GateError("P12 Stage 10 failure diagnostics are not exact")
    inventory = _dict(receipt.get("portable_historical_inventory"), "portable inventory")
    if not _exact_json(
        inventory,
        {
            "path": "docs/p12/portable-historical-inventory.json",
            "object_order": ["P8", "P9", "P10", "P11", "P11R"],
            "setup_count": 5,
            "included_acceptance_gate_count": 124,
            "evidence_anchor_count": 17,
            "excluded_acceptance_gate_count": 5,
            "total_item_count": 151,
            "accepted_aggregate_acceptance_gate_count": 129,
            "gate_entrypoint_null_count": 19,
            "gate_entrypoint_non_null_count": 110,
            "inventory_entrypoint_null_count": 41,
            "historical_python_test_count": 616,
            "accepted_minus_included": list(EXCLUDED_GATE_IDS),
            "excluded_gate_ids": list(EXCLUDED_GATE_IDS),
            "excluded_gate_result": "not_run_platform_excluded",
            "ubuntu_historical_execution_status": {
                gate_id: "not_proven" for gate_id in EXCLUDED_GATE_IDS
            },
            "linux_public_pilot_readiness": "blocked",
            "embedded_darwin_anchor_ids": list(EXCLUDED_GATE_IDS),
            "per_object_checkout_venv_npm_isolation": True,
            "recursive_historical_aggregates_forbidden": True,
            "object_deadline_seconds": {
                "P8": 2700,
                "P9": 900,
                "P10": 3000,
                "P11": 1800,
                "P11R": 1500,
            },
            "sequential_executor_deadline_seconds": 9900,
        },
    ):
        raise P12GateError("P12 portable historical inventory provenance drifted")
    migration = _dict(receipt.get("migration_protection"), "migration protection")
    expected_files = _expected_migration_files()
    if not _exact_json(migration, {"immutable_files": expected_files, "future_owners": OWNERS}):
        raise P12GateError("P12 future migration ownership provenance drifted")
    p10 = _dict(receipt.get("p10_protected_publication"), "P10 publication")
    expected_p10 = {
        "receipt": {
            "path": "provenance/p10-migration-receipt.json",
            "blob": "07565307a35902206ee7c80af66b2a02ab876b83",
        },
        "subjects": list(P10_SUBJECTS),
        "sets": P10_SETS,
        "runs": {
            run: {"head": identity[0], "conclusion": identity[1]}
            for run, identity in P10_RUNS.items()
        },
        "runtime_version_count": 14,
        "studio_version_count": 14,
        "inventory_identity": "docs/p12/acceptance.md#exact-p12-start-ghcr-inventory-oracle",
        "inventory_sha256": "b58cce2af1e3b672114b050ffd6cb55e9625cbcb8fb54c0a863ea00ebb617f3c",
        "overwrite_retag_republish_delete_forbidden": True,
    }
    if not _exact_json(p10, expected_p10):
        raise P12GateError("P12 complete P10 protection identity is invalid")
    counts = _dict(receipt.get("change_counts"), "change counts")
    if not _exact_json(counts, CHANGE_COUNTS):
        raise P12GateError("P12 product, evidence, schema, or migration count is nonzero")
    privacy = _dict(receipt.get("privacy"), "privacy")
    publication = _dict(receipt.get("publication"), "publication")
    if not _exact_json(privacy, PRIVACY_DECLARATION) or not _exact_json(
        publication, PUBLICATION_DECLARATION
    ):
        raise P12GateError("P12 privacy or zero-publication declaration is invalid")
    if not _exact_json(receipt.get("evidence_preflight"), EVIDENCE_PREFLIGHT):
        raise P12GateError("P12 evidence-preflight policy declaration is invalid")
    serialized = json.dumps(receipt, ensure_ascii=False)
    unsafe = ("/Users/", "/home/", ".codex/", "sk-", "dc_session=", "ghp_")
    if any(marker in serialized for marker in unsafe):
        raise P12GateError("P12 provenance contains local, private, or credential material")
    inventory_result = check_historical_inventory(root)
    if any(
        inventory_result.get(key) != inventory[key]
        for key in (
            "setup_count",
            "included_acceptance_gate_count",
            "evidence_anchor_count",
            "excluded_acceptance_gate_count",
            "total_item_count",
        )
    ):
        raise P12GateError("P12 provenance inventory semantics do not match the canonical file")
    _check_git_identities(root)
    return {
        "schema_version": 1,
        "gate": "p12_provenance",
        "status": "passed",
        "covered_path_count": len(implementation_paths(root)),
        "allowlist_path_count": len(allowlist),
        "historical_anchor_count": len(HISTORY),
        "portable_object_count": len(PORTABLE_OBJECTS),
        "portable_inventory_item_count": inventory["total_item_count"],
        "accepted_gate_count": inventory["accepted_aggregate_acceptance_gate_count"],
        "included_acceptance_gate_count": inventory["included_acceptance_gate_count"],
        "excluded_acceptance_gate_count": inventory["excluded_acceptance_gate_count"],
        "darwin_anchor_count": len(DARWIN_EVIDENCE_ANCHORS),
        "historical_python_test_count": inventory["historical_python_test_count"],
        "immutable_migration_file_count": len(expected_files),
        "protected_p10_subject_count": len(P10_SUBJECTS),
        "protected_p10_set_count": len(P10_SETS),
        "protected_p10_run_count": len(P10_RUNS),
        "protected_p10_local_git_identity_count": len(P10_GIT_IDENTITIES) + 2,
        "rejected_attempt_count": len(REJECTED_ATTEMPTS),
        "source_migration_count": 0,
        "parent_source_read_count": 0,
        "privacy_leak_count": 0,
        "publication_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        result = check_provenance(Path(args.root).resolve())
    except P12GateError as exc:
        print(f"P12 provenance check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
