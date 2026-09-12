# SPDX-License-Identifier: Apache-2.0

"""Validate the literal P12 v4 portable historical inventory.

The manifest is policy, not evidence.  Its membership never depends on the host
platform, discovery, a glob, or a historical aggregate.  Exact Git objects are
read only to bind the literal entrypoint paths to their immutable blobs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import unicodedata
from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = "docs/p12/portable-historical-inventory.json"

OBJECT_ORDER = ("P8", "P9", "P10", "P11", "P11R")
OBJECTS: dict[str, dict[str, object]] = {
    "P8": {
        "commit": "0bb80ab187932fbad42fbf665b8310987609a1f5",
        "tree": "311eb777c3d17a9a3722a16c394b9913c283b416",
        "branch": "codex/p8-release-readiness",
        "base": "df47f8d075f7c0660ab5ed6035f8acfa3d3da4dc",
        "python_environment": True,
        "npm_workspace": True,
    },
    "P9": {
        "commit": "11aa240af8db2ca515325dc059b1a77f7badc874",
        "tree": "a27cb6ce9f568b04083a88f7ba06f033235f4cbc",
        "branch": "codex/p9-productization-rebaseline",
        "base": "b093a4fa54bf30cef838c72222d1ae63c4eab9d9",
        "python_environment": True,
        "npm_workspace": False,
    },
    "P10": {
        "commit": "4bef5629d450c6bb3940f606fc90194e008ee8fd",
        "tree": "909b566b7ba9f7beb143cd0b29cf95fbd1178bbe",
        "branch": "codex/p10-mac-quickstart",
        "base": "11aa240af8db2ca515325dc059b1a77f7badc874",
        "python_environment": True,
        "npm_workspace": True,
    },
    "P11": {
        "commit": "7e5387f148f86b5c9b07820dd8b8f4e18e12dc38",
        "tree": "6d7c1b3053fefc1f3b14a4b39fde2d5adb641990",
        "branch": "codex/p11-agent-packages",
        "base": "4bef5629d450c6bb3940f606fc90194e008ee8fd",
        "python_environment": True,
        "npm_workspace": True,
    },
    "P11R": {
        "commit": "c1562ea5201394d8a278f4b644daf4029cbb5bd4",
        "tree": "ae0f33263cfc7445fef69656ad9c5cb04d4a2d00",
        "branch": "codex/p11r-ci-alignment",
        "base": "7e5387f148f86b5c9b07820dd8b8f4e18e12dc38",
        "python_environment": True,
        "npm_workspace": True,
    },
}

ITEM_COUNTS = {
    "setup": 5,
    "included_acceptance_gate": 124,
    "evidence_anchor": 17,
    "excluded_acceptance_gate": 5,
    "total": 151,
}
PARTITION_COUNTS = {"P8": 56, "P9": 7, "P10": 21, "P11": 19, "P11R": 21}
EXCLUDED_GATE_IDS = (
    "p8_compose_runtime",
    "p8_golden_path",
    "p10_compose_runtime",
    "p10_quickstart",
    "p10_remote_distribution",
)
EXCLUDED_REASON_TOKENS = {
    "p8_compose_runtime": "linux_host_uid_private_bind_incompatible_with_container_uid_10001",
    "p8_golden_path": "transitively_invokes_excluded_p8_compose_runtime",
    "p10_compose_runtime": "immutable_darwin_guard_actual_macos_required",
    "p10_quickstart": "immutable_darwin_only_local_candidate_and_macos_result",
    "p10_remote_distribution": (
        "immutable_remote_gate_includes_darwin_quickstart_and_macos_result"
    ),
}
OBJECT_TIMEOUTS = {"P8": 2700, "P9": 900, "P10": 3000, "P11": 1800, "P11R": 1500}
OPERATION_TIMEOUTS = {
    "checkout_ref": 120,
    "venv_install": 600,
    "npm_install": 600,
    "static": 300,
    "python": 900,
    "studio": 600,
    "reproducibility_release_compose_quickstart": 1200,
    "remote_distribution": 1200,
    "executor": 9900,
}
OBJECT_RESULT_SCHEMA = "digital-colleagues.p12-v4-portable-object-result.v1"
PREDECESSOR_OBJECTS = {"P9": "P8", "P10": "P9", "P11": "P10", "P11R": "P11"}
CHILD_ENVIRONMENT = {
    "P10_REMOTE_USE_INSTALLED_TOOLS": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONUNBUFFERED": "1",
}
FORBIDDEN_AGGREGATES = (
    "make ci",
    "make p11r-check",
    "make p11-check",
    "make p10-check",
    "make p9-check",
    "--scope all",
)
COMMAND_KINDS = {
    "git",
    "identity_check",
    "npm_script",
    "object_setup",
    "predecessor_result",
    "python_function",
    "python_module",
    "python_script",
}
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_GATE_ID = re.compile(r"^[a-z][a-z0-9_]*$")

# This universe is transcribed independently from the exact accepted historical
# contracts/runners (acceptance Appendix A).  It is deliberately not derived
# from CANONICAL_INVENTORY or from any item_type classification.
ACCEPTED_GATE_IDS = (
    "p8_ruff_lint",
    "p8_ruff_format",
    "p8_mypy_strict",
    "p8_python_unittest",
    "p8_studio_eslint",
    "p8_studio_prettier",
    "p8_studio_typescript",
    "p8_studio_vitest",
    "p8_studio_vite_build",
    "p8_repository",
    "p8_provenance",
    "p8_operations",
    "p8_backup_restore",
    "p8_diagnostics",
    "p8_supply_chain",
    "p8_reproducibility",
    "p8_release",
    "p2_core_current_tree",
    "p3_architecture_current_tree",
    "p3_migrations_current_tree",
    "p3_persistence_current_tree",
    "p3_runtime_current_tree",
    "p3_golden_current_tree",
    "p4_architecture_current_tree",
    "p4_migrations_current_tree",
    "p4_authentication_current_tree",
    "p4_studio_current_tree",
    "p4_compose_current_tree",
    "p4_golden_current_tree",
    "p5_architecture_current_tree",
    "p5_migrations_current_tree",
    "p5_builder_current_tree",
    "p5_policy_current_tree",
    "p5_studio_current_tree",
    "p5_compose_current_tree",
    "p5_golden_current_tree",
    "p6_architecture_current_tree",
    "p6_migrations_current_tree",
    "p6_authentication_current_tree",
    "p6_rbac_current_tree",
    "p6_change_approval_current_tree",
    "p6_effect_approval_current_tree",
    "p6_audit_export_current_tree",
    "p6_abuse_current_tree",
    "p6_studio_current_tree",
    "p6_compose_current_tree",
    "p6_golden_current_tree",
    "p7_architecture_current_tree",
    "p7_model_adapter_current_tree",
    "p7_channel_adapter_current_tree",
    "p7_configuration_current_tree",
    "p7_abuse_current_tree",
    "p7_compose_current_tree",
    "p7_golden_current_tree",
    "p8_public_boundary",
    "p8_git_diff_check",
    "p8_compose_runtime",
    "p8_golden_path",
    "p9_retained_p8_portable",
    "p9_repository",
    "p9_provenance",
    "p9_rebaseline",
    "p9_test",
    "p9_public_boundary",
    "p9_git_diff_check",
    "p10_retained_p9_portable",
    "p10_ruff_lint",
    "p10_ruff_format",
    "p10_mypy_strict",
    "p10_unittest",
    "p10_studio_eslint",
    "p10_studio_prettier",
    "p10_studio_typescript",
    "p10_studio_vitest",
    "p10_studio_vite_build",
    "p10_repository",
    "p10_provenance",
    "p10_distribution",
    "p10_security",
    "p10_operations",
    "p10_i18n",
    "p10_compatibility",
    "p10_reproducibility",
    "p10_public_boundary",
    "p10_git_diff_check",
    "p10_evidence",
    "p10_compose_runtime",
    "p10_quickstart",
    "p10_remote_distribution",
    "p11_retained_p10_portable",
    "p11_ruff_lint",
    "p11_ruff_format",
    "p11_mypy_strict",
    "p11_unittest",
    "p11_studio_eslint",
    "p11_studio_prettier",
    "p11_studio_typescript",
    "p11_studio_vitest",
    "p11_studio_vite_build",
    "p11_repository",
    "p11_provenance",
    "p11_architecture",
    "p11_migrations",
    "p11_compatibility",
    "p11_studio",
    "p11_public_boundary",
    "p11_candidate_diff",
    "p11_compose_runtime",
    "p11r_retained_p11_portable",
    "p11r_ruff_lint",
    "p11r_ruff_format",
    "p11r_mypy_strict",
    "p11r_current_p11_tests",
    "p11r_governance_tests",
    "p11r_studio_eslint",
    "p11r_studio_prettier",
    "p11r_studio_typescript",
    "p11r_studio_vitest",
    "p11r_studio_vite_build",
    "p11r_architecture",
    "p11r_migrations",
    "p11r_compatibility",
    "p11r_studio_contract",
    "p11r_ci_policy",
    "p11r_repository_ci",
    "p11r_provenance",
    "p11r_public_boundary",
    "p11r_candidate_repository",
    "p11r_compose_runtime",
)

EMBEDDED_DARWIN_ANCHORS: dict[str, dict[str, object]] = {
    "p8_compose_runtime": {
        "anchor_historical_status": "passed",
        "anchor_platform": "darwin",
        "canonical_bytes": 2348,
        "canonical_sha256": "a2acd8e3f935d9c520f58e76b8384514e596e59f94f7bb62e1881ce9183c9bbd",
        "canonicalization": "P12-CJ-1",
        "gate_id": "p8_compose_runtime",
        "purpose": "immutable_platform_scoped_identity_only",
        "selection": 'result = p8_summary["compose_runtime"]',
        "source_blob": "964406b20e9fc1e98b8eeda3c24bf3f22f226768",
        "source_commit": "0bb80ab187932fbad42fbf665b8310987609a1f5",
        "source_file_sha256": ("78905893f9a06bf6b5361c76a8e152dbe8de2ec53d1aede84fca2f7ce1b5921b"),
        "source_path": "artifacts/p8/summary.json",
        "source_tree": "311eb777c3d17a9a3722a16c394b9913c283b416",
    },
    "p8_golden_path": {
        "anchor_historical_status": "passed",
        "anchor_platform": "darwin",
        "canonical_bytes": 2034,
        "canonical_sha256": "c1f1f8148cd3b0184d92720e862bbadfe7e330fd4087b7eb03190400d6742f44",
        "canonicalization": "P12-CJ-1",
        "gate_id": "p8_golden_path",
        "purpose": "immutable_platform_scoped_identity_only",
        "selection": 'result = p8_summary["golden_path"]',
        "source_blob": "964406b20e9fc1e98b8eeda3c24bf3f22f226768",
        "source_commit": "0bb80ab187932fbad42fbf665b8310987609a1f5",
        "source_file_sha256": ("78905893f9a06bf6b5361c76a8e152dbe8de2ec53d1aede84fca2f7ce1b5921b"),
        "source_path": "artifacts/p8/summary.json",
        "source_tree": "311eb777c3d17a9a3722a16c394b9913c283b416",
    },
    "p10_compose_runtime": {
        "anchor_historical_status": "passed",
        "anchor_platform": "darwin",
        "canonical_bytes": 476,
        "canonical_sha256": "4f6f5de0a92d2aa3bea1ab80ad94b869a4fd1cbe5f459804eea3cd86377e137b",
        "canonicalization": "P12-CJ-1",
        "gate_id": "p10_compose_runtime",
        "purpose": "immutable_platform_scoped_identity_only",
        "selection": 'result = p10_summary["compose_runtime"]',
        "source_blob": "a4c1a59fffec9c30160787a7bec584e228fb9f35",
        "source_commit": "4bef5629d450c6bb3940f606fc90194e008ee8fd",
        "source_file_sha256": ("876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae"),
        "source_path": "artifacts/p10/summary.json",
        "source_tree": "909b566b7ba9f7beb143cd0b29cf95fbd1178bbe",
    },
    "p10_quickstart": {
        "anchor_historical_status": "passed",
        "anchor_platform": "darwin",
        "canonical_bytes": 874,
        "canonical_sha256": "75c18fadb57dd93914a8f99996857af22c2da8c82c504582b9eaa412c1f00c1b",
        "canonicalization": "P12-CJ-1",
        "gate_id": "p10_quickstart",
        "purpose": "immutable_platform_scoped_identity_only",
        "selection": 'result = p10_summary["quickstart"]',
        "source_blob": "a4c1a59fffec9c30160787a7bec584e228fb9f35",
        "source_commit": "4bef5629d450c6bb3940f606fc90194e008ee8fd",
        "source_file_sha256": ("876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae"),
        "source_path": "artifacts/p10/summary.json",
        "source_tree": "909b566b7ba9f7beb143cd0b29cf95fbd1178bbe",
    },
    "p10_remote_distribution": {
        "anchor_historical_status": "passed",
        "anchor_platform": "darwin",
        "canonical_bytes": 2538,
        "canonical_sha256": "4383d540c4cd95f62db32aaadc1dfdf8e027eb0bd81b9909c4a0dda9a3d06c78",
        "canonicalization": "P12-CJ-1",
        "gate_id": "p10_remote_distribution",
        "purpose": "immutable_platform_scoped_identity_only",
        "selection": (
            'result = {"distribution":p10_summary["remote_distribution"],'
            '"quickstart":p10_summary["remote_quickstart"]}'
        ),
        "source_blob": "a4c1a59fffec9c30160787a7bec584e228fb9f35",
        "source_commit": "4bef5629d450c6bb3940f606fc90194e008ee8fd",
        "source_file_sha256": ("876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae"),
        "source_path": "artifacts/p10/summary.json",
        "source_tree": "909b566b7ba9f7beb143cd0b29cf95fbd1178bbe",
    },
}


class HistoricalInventoryError(RuntimeError):
    """The P12 portable historical inventory failed closed."""


def _git(root: Path, *arguments: str) -> str:
    environment = os.environ.copy()
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise HistoricalInventoryError("historical Git object verification failed")
    return completed.stdout.strip()


ENTRYPOINT_IDENTITIES: dict[tuple[str, str], tuple[str, str]] = {
    ("P8", "scripts/run_p8_unittest_suite.py"): (
        "100644",
        "35d0ef6a88025ef5bc10925009e044c6a84025c8",
    ),
    ("P8", "studio/package.json"): ("100644", "f7aac57ff88ce1b7f779c3b3f63fdf7b79b6c916"),
    ("P8", "scripts/check_p8_repository.py"): (
        "100644",
        "097b8078ba391062ac83bf44ab6cbd1bc14493f1",
    ),
    ("P8", "scripts/check_p8_provenance.py"): (
        "100644",
        "576831f10c9f9729299dec8276cfccbb993dde4a",
    ),
    ("P8", "scripts/check_p8_operations.py"): (
        "100644",
        "694d75f8ecb9be367493d42b581d627abbd03491",
    ),
    ("P8", "scripts/check_p8_backup_restore.py"): (
        "100644",
        "5badb7f63b774c822dc5d5ed406b4e1eecc386fa",
    ),
    ("P8", "scripts/check_p8_diagnostics.py"): (
        "100644",
        "382397c88eb7f160af7c5d694d4a509476b2909f",
    ),
    ("P8", "scripts/check_p8_supply_chain.py"): (
        "100644",
        "cd2ceb94d838e3f3879a78517ad7cce84361bfed",
    ),
    ("P8", "scripts/check_p8_reproducibility.py"): (
        "100644",
        "72eb4312018c6fdc665921837e58a24f86b3b36a",
    ),
    ("P8", "scripts/check_p8_release.py"): ("100644", "19763335f7920429b1ad40be5b7ad96675bef0b5"),
    ("P8", "scripts/check_p8_golden_path.py"): (
        "100644",
        "d5f38a86baa02583ee2ec1639c3163954a188399",
    ),
    ("P8", "scripts/check_p2_core_contracts.py"): (
        "100644",
        "3343498dd780c42acf2245e348368ce6c8d2b37c",
    ),
    ("P8", "scripts/check_p3_architecture.py"): (
        "100644",
        "6305a93830769c0e179f1c824850a42d1240abe1",
    ),
    ("P8", "scripts/check_p3_migrations.py"): (
        "100644",
        "91fecea248d055a661c3da0dcafeb723062e794e",
    ),
    ("P8", "scripts/check_p3_persistence.py"): (
        "100644",
        "40b5e115a650fb92cdeb752a6e46b6d879d19ba4",
    ),
    ("P8", "scripts/check_p3_runtime_contracts.py"): (
        "100644",
        "4b50ecba4a52d6cf05a38e5a2b4da608e60a89c9",
    ),
    ("P8", "scripts/check_p3_golden_path.py"): (
        "100644",
        "470fb9d415e2c9874c3c1b29878d12d9b095a432",
    ),
    ("P8", "scripts/check_p4_architecture.py"): (
        "100644",
        "a4da981f34d3d422f3d92653ec00c43cc1e29d97",
    ),
    ("P8", "scripts/check_p4_migrations.py"): (
        "100644",
        "d05ae05cfd6fee4b1e6f29fe745e4d1b535513d5",
    ),
    ("P8", "scripts/check_p4_authentication.py"): (
        "100644",
        "97d1e8157fc02be14548fc1b873d4b408bcbb995",
    ),
    ("P8", "scripts/check_p4_studio.py"): ("100644", "827c11a15b43f093eb898b5c8efe779f5909c475"),
    ("P8", "scripts/check_p4_compose.py"): ("100644", "2e23588b0113aa1eecb47679c5f0348bed2d9234"),
    ("P8", "scripts/check_p4_golden_path.py"): (
        "100644",
        "7e215b9744cf70de9cd4e8076b5d8d6e14525514",
    ),
    ("P8", "scripts/check_p5_architecture.py"): (
        "100644",
        "b82a1c3f05f5a010ae89ae3c4f1637759c5413c2",
    ),
    ("P8", "scripts/check_p5_migrations.py"): (
        "100644",
        "1186a334bf446d7713e5ec2824a79bfc3e2f5ad4",
    ),
    ("P8", "scripts/check_p5_builder.py"): ("100644", "94e9de8a0c85f7970d2a0b9d3bccc9beb3ef16d3"),
    ("P8", "scripts/check_p5_policy.py"): ("100644", "955e90a89c8b1560784db14caf4c3c1f9f2326df"),
    ("P8", "scripts/check_p5_studio.py"): ("100644", "7e119453c466de532bd3511d0dc7bbaf7ad9b920"),
    ("P8", "scripts/check_p5_compose.py"): ("100644", "4a2d4448bc00d1ea358c7e8a08f00d3a06752a31"),
    ("P8", "scripts/check_p5_golden_path.py"): (
        "100644",
        "2488d2bdc5c68b464d620c096cb9799854f1a254",
    ),
    ("P8", "scripts/check_p6_architecture.py"): (
        "100644",
        "5e4eb3f1f29560847476b5178e8200b5c12b9fa9",
    ),
    ("P8", "scripts/check_p6_migrations.py"): (
        "100644",
        "b40171620a15f54cb4eda4e68214cc0da0d8a453",
    ),
    ("P8", "scripts/check_p6_authentication.py"): (
        "100644",
        "bafd28cf374d0cd642b97858d6d6a8729b2e8f23",
    ),
    ("P8", "scripts/check_p6_rbac.py"): ("100644", "dac61082e6ad9bcd0565b0dff81cb05f6ef8dffe"),
    ("P8", "scripts/check_p6_change_approval.py"): (
        "100644",
        "2d700b49c3a20993b33001fe1b0c233b4d3f910a",
    ),
    ("P8", "scripts/check_p6_effect_approval.py"): (
        "100644",
        "98cccb76aa86bec56b6187d380deea879ccd7fbe",
    ),
    ("P8", "scripts/check_p6_audit_export.py"): (
        "100644",
        "f67bcb5632ddd58cd4574381ad450ff07c10137b",
    ),
    ("P8", "scripts/check_p6_abuse.py"): ("100644", "abe3d255ea073bf643c5dea069e5e11c740f34fd"),
    ("P8", "scripts/check_p6_studio.py"): ("100644", "053f300fbfa3f32ecb84e5299a76ac5975501312"),
    ("P8", "scripts/check_p6_compose.py"): ("100644", "e83e69e99a7e2e477abda883ced68179e07e5366"),
    ("P8", "scripts/check_p6_golden_path.py"): (
        "100644",
        "af64539cc5549c2f8f2a1c58be685e38d63143bc",
    ),
    ("P8", "scripts/check_p7_architecture.py"): (
        "100644",
        "148f9671542a0669731fd3e703de4cdb547e0abf",
    ),
    ("P8", "scripts/check_p7_model_adapter.py"): (
        "100644",
        "bf9d9bfda708d42ef3dc2ffb786d3b6b84cfe2df",
    ),
    ("P8", "scripts/check_p7_channel_adapter.py"): (
        "100644",
        "f601ff5faa6ca2a90e99039af67cb87d6dbd1d6f",
    ),
    ("P8", "scripts/check_p7_configuration.py"): (
        "100644",
        "ecf21611975848a275104bf2b20a94e87ebfbf70",
    ),
    ("P8", "scripts/check_p7_abuse.py"): ("100644", "38470a0a876957980bd08bdc731be7cf25339bf3"),
    ("P8", "scripts/check_p7_compose.py"): ("100644", "854b7214798fccfd929f464fcb05faf63bd92187"),
    ("P8", "scripts/check_p7_golden_path.py"): (
        "100644",
        "8a819094259acc56380a2ab01b09d9bb15dac9ca",
    ),
    ("P8", "scripts/check_public_boundary.py"): (
        "100644",
        "35f6cb4e729987b2c0b18cf8981f328e72445297",
    ),
    ("P8", "scripts/check_p8_compose_runtime.py"): (
        "100644",
        "e8e3f496d7bde9c5eb2859d1d87e1b8532b60467",
    ),
    ("P9", "scripts/check_p9_repository.py"): (
        "100644",
        "ccc048673bc14b02c63cbf91e93a978adf481ad0",
    ),
    ("P9", "scripts/check_p9_provenance.py"): (
        "100644",
        "f1922e74cad974809ced823c4b780d7c7e5fd85e",
    ),
    ("P9", "scripts/check_p9_rebaseline.py"): (
        "100644",
        "e07f55736ffd25fbe1add7458b0b6e72c409316f",
    ),
    ("P9", "scripts/run_p8_unittest_suite.py"): (
        "100644",
        "35d0ef6a88025ef5bc10925009e044c6a84025c8",
    ),
    ("P9", "scripts/check_public_boundary.py"): (
        "100644",
        "35f6cb4e729987b2c0b18cf8981f328e72445297",
    ),
    ("P10", "scripts/run_p8_unittest_suite.py"): (
        "100644",
        "35d0ef6a88025ef5bc10925009e044c6a84025c8",
    ),
    ("P10", "studio/package.json"): ("100644", "7ea47041d96282f8c98690789dd5b40880969326"),
    ("P10", "scripts/check_p10_repository.py"): (
        "100644",
        "6db14ae002894c14204734c564ee827dc0465835",
    ),
    ("P10", "scripts/check_p10_provenance.py"): (
        "100644",
        "51a2163866a1cd1aebf37c69f0de3abd35ad3f33",
    ),
    ("P10", "scripts/check_p10_distribution.py"): (
        "100644",
        "a4687649f3ab6e64f13c41015527f17265b1130a",
    ),
    ("P10", "scripts/check_p10_security.py"): (
        "100644",
        "aa0ce7c10f0a3bde84270521830f54c7156f2657",
    ),
    ("P10", "scripts/check_p10_operations.py"): (
        "100644",
        "64173d44dab2c4fd646ed5a4e72278dcd329bd9c",
    ),
    ("P10", "scripts/check_p10_i18n.py"): ("100644", "5ae8590ee118191de99108f08809faa01b74abcc"),
    ("P10", "scripts/check_p10_compatibility.py"): (
        "100644",
        "3d1a5c85409aa5a3741c8a7ea6365c9814184209",
    ),
    ("P10", "scripts/check_p10_reproducibility.py"): (
        "100644",
        "50f766427755c650795e04b0bc92c69927840fef",
    ),
    ("P10", "scripts/check_public_boundary.py"): (
        "100644",
        "35f6cb4e729987b2c0b18cf8981f328e72445297",
    ),
    ("P10", "scripts/check_p10_compose_runtime.py"): (
        "100644",
        "44cf5504f0728e571cfeaa2e33d75c8b58bec738",
    ),
    ("P10", "scripts/check_p10_quickstart.py"): (
        "100644",
        "6b352a180683969deed9b396b9b94b4488232411",
    ),
    ("P10", "scripts/check_p10_evidence.py"): (
        "100644",
        "0d8079d60b8459eccc71e62af3b70fd4bc4eb591",
    ),
    ("P11", "scripts/run_p8_unittest_suite.py"): (
        "100644",
        "35d0ef6a88025ef5bc10925009e044c6a84025c8",
    ),
    ("P11", "studio/package.json"): ("100644", "7ea47041d96282f8c98690789dd5b40880969326"),
    ("P11", "scripts/check_p11_repository.py"): (
        "100644",
        "f8537817378b7265071112250d8fadeaa134a616",
    ),
    ("P11", "scripts/check_p11_provenance.py"): (
        "100644",
        "fb3c7aaaf935388bfcf8e46f5d8e816f927bea8b",
    ),
    ("P11", "scripts/check_p11_architecture.py"): (
        "100644",
        "82a9d85f4ec7d0d2761d7b312f317df88cbbbbe1",
    ),
    ("P11", "scripts/check_p11_migrations.py"): (
        "100644",
        "75076416c8e5aa82517c35166ea3d3a99e2642d7",
    ),
    ("P11", "scripts/check_p11_compatibility.py"): (
        "100644",
        "369517b0b95043cb0349af124eaed27e98746f9e",
    ),
    ("P11", "scripts/check_p11_studio.py"): ("100644", "f152f82baaf7f830f88bc5c72d19a87dd7c4589f"),
    ("P11", "scripts/check_public_boundary.py"): (
        "100644",
        "35f6cb4e729987b2c0b18cf8981f328e72445297",
    ),
    ("P11", "scripts/p11_gate_support.py"): ("100644", "02024443d0f8399e3168eef5abd8601873c2f39a"),
    ("P11", "scripts/check_p11_compose_runtime.py"): (
        "100644",
        "61486f133fe2279eebfa2d19ed8144a4f8fdb85c",
    ),
    ("P11R", "scripts/run_p11r_toolchain.py"): (
        "100644",
        "599f2328a03db9216ed2fdc1b1a1af919834800a",
    ),
    ("P11R", "studio/package.json"): ("100644", "7ea47041d96282f8c98690789dd5b40880969326"),
    ("P11R", "scripts/check_p11_architecture.py"): (
        "100644",
        "82a9d85f4ec7d0d2761d7b312f317df88cbbbbe1",
    ),
    ("P11R", "scripts/check_p11_migrations.py"): (
        "100644",
        "75076416c8e5aa82517c35166ea3d3a99e2642d7",
    ),
    ("P11R", "scripts/check_p11_compatibility.py"): (
        "100644",
        "369517b0b95043cb0349af124eaed27e98746f9e",
    ),
    ("P11R", "scripts/check_p11_studio.py"): ("100644", "f152f82baaf7f830f88bc5c72d19a87dd7c4589f"),
    ("P11R", "scripts/check_p11r_ci_policy.py"): (
        "100644",
        "ce0bbf7f3e18062d6d77f1d16e303376c58df2f4",
    ),
    ("P11R", "scripts/check_p11r_repository.py"): (
        "100644",
        "e684975be4b651c3f731bd30b1cf09f89046978e",
    ),
    ("P11R", "scripts/check_p11r_provenance.py"): (
        "100644",
        "51673c267cef7c16836f588d72cad60bed32c995",
    ),
    ("P11R", "scripts/check_public_boundary.py"): (
        "100644",
        "35f6cb4e729987b2c0b18cf8981f328e72445297",
    ),
    ("P11R", "scripts/check_p11_compose_runtime.py"): (
        "100644",
        "61486f133fe2279eebfa2d19ed8144a4f8fdb85c",
    ),
}


def _entrypoint(
    object_name: str,
    path: str,
    callable_name: str,
) -> dict[str, str]:
    try:
        mode, blob = ENTRYPOINT_IDENTITIES[(object_name, path)]
    except KeyError as exc:
        raise HistoricalInventoryError("a fixed historical entrypoint is absent") from exc
    return {"blob": blob, "callable": callable_name, "mode": mode, "path": path}


def _common(
    object_name: str,
    gate_id: str,
    *,
    item_type: str,
    command_kind: str,
    command: str,
    entrypoint: dict[str, str] | None,
    expected: dict[str, object],
    platform_scope: str,
    reason: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    metadata = OBJECTS[object_name]
    commit = str(metadata["commit"])
    branch = str(metadata["branch"])
    base = str(metadata["base"])
    return {
        "branch": branch,
        "command": command,
        "command_kind": command_kind,
        "commit": commit,
        "entrypoint": entrypoint,
        "expected": expected,
        "gate_id": gate_id,
        "item_type": item_type,
        "object": object_name,
        "platform_scope": platform_scope,
        "reason": reason,
        "ref_layout": {
            "branch_ref": f"refs/heads/{branch}",
            "head": commit,
            "main": base,
            "origin_main": base,
        },
        "resource_scope": object_name.lower(),
        "timeout_seconds": timeout_seconds,
        "tree": str(metadata["tree"]),
    }


def _setup(object_name: str) -> dict[str, Any]:
    lower = object_name.lower()
    npm_required = bool(OBJECTS[object_name]["npm_workspace"])
    lock_anchor_ids = [f"{lower}_python_lock_anchor"]
    if npm_required:
        lock_anchor_ids.append(f"{lower}_npm_lock_anchor")
    return _common(
        object_name,
        f"{lower}_setup",
        item_type="setup",
        command_kind="object_setup",
        command="create one exact-object checkout and isolated locked resources",
        entrypoint=None,
        expected={
            "cleanup_residue_count": 0,
            "npm_workspace": "one_locked" if npm_required else "absent",
            "python_environment": "one_hash_locked",
            "status": "passed",
        },
        platform_scope="portable_linux",
        reason=f"Create the sole isolated checkout and reusable resources for {object_name}.",
        timeout_seconds=OBJECT_TIMEOUTS[object_name],
    ) | {
        "resources": {
            "checkout_count": 1,
            "checkout_timeout_seconds": OPERATION_TIMEOUTS["checkout_ref"],
            "cleanup_before_next_object": True,
            "cleanup_residue_count": 0,
            "environment": CHILD_ENVIRONMENT,
            "lock_anchor_ids": lock_anchor_ids,
            "npm_install_timeout_seconds": OPERATION_TIMEOUTS["npm_install"],
            "npm_workspace_count": 1 if npm_required else 0,
            "object_timeout_seconds": OBJECT_TIMEOUTS[object_name],
            "python_environment_count": 1,
            "venv_install_timeout_seconds": OPERATION_TIMEOUTS["venv_install"],
        }
    }


def _anchor(
    object_name: str,
    gate_id: str,
    *,
    path: str,
    blob: str,
    sha256: str,
    anchor_commit: str,
    anchor_tree: str,
    reason: str,
    platform_scope: str = "object_identity_all_platforms",
    json_expectations: dict[str, object] | None = None,
    json_pointer_expectations: dict[str, object] | None = None,
) -> dict[str, Any]:
    expected: dict[str, object] = {
        "anchor_commit": anchor_commit,
        "anchor_tree": anchor_tree,
        "blob": blob,
        "path": path,
        "sha256": sha256,
        "status": "identity_verified",
    }
    if json_expectations is not None and json_pointer_expectations is not None:
        raise HistoricalInventoryError("anchor cannot mix key and JSON-pointer expectations")
    if json_expectations is not None:
        expected["json_expectations"] = json_expectations
    if json_pointer_expectations is not None:
        expected["json_pointer_expectations"] = json_pointer_expectations
    return _common(
        object_name,
        gate_id,
        item_type="evidence_anchor",
        command_kind="identity_check",
        command=f"verify {anchor_commit}:{path}",
        entrypoint=None,
        expected=expected,
        platform_scope=platform_scope,
        reason=reason,
        timeout_seconds=OPERATION_TIMEOUTS["static"],
    )


def _gate(
    object_name: str,
    gate_id: str,
    *,
    command_kind: str,
    command: str,
    reason: str,
    path: str | None = None,
    callable_name: str | None = None,
    expected: dict[str, object] | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    if path is None:
        entrypoint = None
    else:
        entrypoint = _entrypoint(object_name, path, callable_name or "main")
    if timeout_seconds is None:
        timeout_seconds = OPERATION_TIMEOUTS["static"]
    return _common(
        object_name,
        gate_id,
        item_type="included_acceptance_gate",
        command_kind=command_kind,
        command=command,
        entrypoint=entrypoint,
        expected=expected or {"status": "passed"},
        platform_scope="portable_linux",
        reason=reason,
        timeout_seconds=timeout_seconds,
    )


def _excluded_gate(
    object_name: str,
    gate_id: str,
    path: str,
    *,
    suffix: str = ".",
) -> dict[str, Any]:
    lower = object_name.lower()
    return _common(
        object_name,
        gate_id,
        item_type="excluded_acceptance_gate",
        command_kind="python_script",
        command=f"<{lower}-python> -B {path} {suffix}".rstrip(),
        entrypoint=_entrypoint(object_name, path, "main"),
        expected={
            "disposition": "excluded_acceptance_gate",
            "executor_result": "not_run_platform_excluded",
            "exit_status": None,
            "linux_public_pilot_readiness": "blocked",
            "replay_platform": "ubuntu-24.04",
            "ubuntu_historical_execution_status": "not_proven",
        },
        platform_scope=("replay=ubuntu-24.04; Ubuntu status=not_proven; Darwin anchor=passed"),
        reason=EXCLUDED_REASON_TOKENS[gate_id],
        timeout_seconds=OPERATION_TIMEOUTS["reproducibility_release_compose_quickstart"],
    ) | {"embedded_anchor": deepcopy(EMBEDDED_DARWIN_ANCHORS[gate_id])}


_P8_PRIOR: tuple[tuple[str, str], ...] = (
    ("p2_core_current_tree", "scripts/check_p2_core_contracts.py"),
    ("p3_architecture_current_tree", "scripts/check_p3_architecture.py"),
    ("p3_migrations_current_tree", "scripts/check_p3_migrations.py"),
    ("p3_persistence_current_tree", "scripts/check_p3_persistence.py"),
    ("p3_runtime_current_tree", "scripts/check_p3_runtime_contracts.py"),
    ("p3_golden_current_tree", "scripts/check_p3_golden_path.py"),
    ("p4_architecture_current_tree", "scripts/check_p4_architecture.py"),
    ("p4_migrations_current_tree", "scripts/check_p4_migrations.py"),
    ("p4_authentication_current_tree", "scripts/check_p4_authentication.py"),
    ("p4_studio_current_tree", "scripts/check_p4_studio.py"),
    ("p4_compose_current_tree", "scripts/check_p4_compose.py"),
    ("p4_golden_current_tree", "scripts/check_p4_golden_path.py"),
    ("p5_architecture_current_tree", "scripts/check_p5_architecture.py"),
    ("p5_migrations_current_tree", "scripts/check_p5_migrations.py"),
    ("p5_builder_current_tree", "scripts/check_p5_builder.py"),
    ("p5_policy_current_tree", "scripts/check_p5_policy.py"),
    ("p5_studio_current_tree", "scripts/check_p5_studio.py"),
    ("p5_compose_current_tree", "scripts/check_p5_compose.py"),
    ("p5_golden_current_tree", "scripts/check_p5_golden_path.py"),
    ("p6_architecture_current_tree", "scripts/check_p6_architecture.py"),
    ("p6_migrations_current_tree", "scripts/check_p6_migrations.py"),
    ("p6_authentication_current_tree", "scripts/check_p6_authentication.py"),
    ("p6_rbac_current_tree", "scripts/check_p6_rbac.py"),
    ("p6_change_approval_current_tree", "scripts/check_p6_change_approval.py"),
    ("p6_effect_approval_current_tree", "scripts/check_p6_effect_approval.py"),
    ("p6_audit_export_current_tree", "scripts/check_p6_audit_export.py"),
    ("p6_abuse_current_tree", "scripts/check_p6_abuse.py"),
    ("p6_studio_current_tree", "scripts/check_p6_studio.py"),
    ("p6_compose_current_tree", "scripts/check_p6_compose.py"),
    ("p6_golden_current_tree", "scripts/check_p6_golden_path.py"),
    ("p7_architecture_current_tree", "scripts/check_p7_architecture.py"),
    ("p7_model_adapter_current_tree", "scripts/check_p7_model_adapter.py"),
    ("p7_channel_adapter_current_tree", "scripts/check_p7_channel_adapter.py"),
    ("p7_configuration_current_tree", "scripts/check_p7_configuration.py"),
    ("p7_abuse_current_tree", "scripts/check_p7_abuse.py"),
    ("p7_compose_current_tree", "scripts/check_p7_compose.py"),
    ("p7_golden_current_tree", "scripts/check_p7_golden_path.py"),
)


def _python_script(
    object_name: str,
    gate_id: str,
    path: str,
    *,
    reason: str,
    expected: dict[str, object] | None = None,
    timeout_seconds: int | None = None,
    suffix: str = ".",
) -> dict[str, Any]:
    lower = object_name.lower()
    return _gate(
        object_name,
        gate_id,
        command_kind="python_script",
        command=f"<{lower}-python> -B {path} {suffix}".rstrip(),
        path=path,
        reason=reason,
        expected=expected,
        timeout_seconds=timeout_seconds,
    )


def _npm_gate(object_name: str, gate_id: str, command: str, script: str) -> dict[str, Any]:
    return _gate(
        object_name,
        gate_id,
        command_kind="npm_script",
        command=command,
        path="studio/package.json",
        callable_name=script,
        reason=f"Execute the {object_name} Studio {script} leaf separately.",
        timeout_seconds=OPERATION_TIMEOUTS["studio"],
    )


def _quality_gates(object_name: str, unittest_gate: str, count: int) -> list[dict[str, Any]]:
    lower = object_name.lower()
    start = "tests" if object_name == "P8" else f"tests/{lower}"
    output_name = "p8-unittest.json" if object_name == "P8" else f"{lower}-unittest.json"
    result = [
        _gate(
            object_name,
            f"{lower}_ruff_lint",
            command_kind="python_module",
            command=f"<{lower}-python> -m ruff check src scripts tests",
            reason=f"Retain the exact {object_name} Ruff lint leaf.",
            timeout_seconds=OPERATION_TIMEOUTS["python"],
        ),
        _gate(
            object_name,
            f"{lower}_ruff_format",
            command_kind="python_module",
            command=f"<{lower}-python> -m ruff format --check src scripts tests",
            reason=f"Retain the exact {object_name} Ruff format leaf.",
            timeout_seconds=OPERATION_TIMEOUTS["python"],
        ),
        _gate(
            object_name,
            f"{lower}_mypy_strict",
            command_kind="python_module",
            command=f"<{lower}-python> -m mypy src scripts tests",
            reason=f"Retain the exact {object_name} strict Mypy leaf.",
            timeout_seconds=OPERATION_TIMEOUTS["python"],
        ),
        _gate(
            object_name,
            unittest_gate,
            command_kind="python_script",
            command=(
                f"<{lower}-python> -B scripts/run_p8_unittest_suite.py "
                f"--start-directory {start} --top-level-directory . "
                f"--json-output <{lower}-temp>/{output_name}"
            ),
            path="scripts/run_p8_unittest_suite.py",
            reason=f"Run the exact {object_name} Python unittest leaf without batching it.",
            expected={
                "error_count": 0,
                "failure_count": 0,
                "skip_count": 0,
                "status": "passed",
                "test_count": count,
                "test_count_semantics": "historical_python_unittest_cases",
            },
            timeout_seconds=OPERATION_TIMEOUTS["python"],
        ),
        _npm_gate(object_name, f"{lower}_studio_eslint", "corepack npm run lint", "lint"),
        _npm_gate(
            object_name,
            f"{lower}_studio_prettier",
            "corepack npm run format:check",
            "format:check",
        ),
        _npm_gate(
            object_name,
            f"{lower}_studio_typescript",
            "corepack npm run typecheck",
            "typecheck",
        ),
    ]
    if object_name == "P8":
        result.append(
            _gate(
                object_name,
                "p8_studio_vitest",
                command_kind="npm_script",
                command=(
                    "corepack npm test -- --reporter=json --outputFile=<p8-temp>/studio-vitest.json"
                ),
                path="studio/package.json",
                callable_name="test",
                reason="Retain the exact accepted P8 Vitest result as its own leaf.",
                expected={"exception_count": 0, "status": "passed"},
                timeout_seconds=OPERATION_TIMEOUTS["studio"],
            )
        )
    else:
        result.append(
            _npm_gate(object_name, f"{lower}_studio_vitest", "corepack npm test -- --run", "test")
        )
    result.append(
        _npm_gate(object_name, f"{lower}_studio_vite_build", "corepack npm run build", "build")
    )
    return result


def _p8_items() -> list[dict[str, Any]]:
    meta = OBJECTS["P8"]
    items = [_setup("P8")]
    items.extend(
        (
            _anchor(
                "P8",
                "p8_accepted_p7_summary_anchor",
                path="artifacts/p7/summary.json",
                blob="6ded4e77c45ec7e2886aa67dd59a32ab41e47c0e",
                sha256="799caaa90bb66465df55c243cdfdd5fb9ee68730dc9ab2ddd58cdbf79cbc01f5",
                anchor_commit="df47f8d075f7c0660ab5ed6035f8acfa3d3da4dc",
                anchor_tree="4ebfc2bdfcd97e34256ec7a34ff58b0063c05ed7",
                reason="Bind the accepted P7 summary used by the P8 historical boundary.",
                json_expectations={
                    "claim": "optional_adapter_contracts_passed",
                    "status": "development_complete_awaiting_independent_acceptance",
                },
            ),
            _anchor(
                "P8",
                "p8_acceptance_anchor",
                path="docs/p8/acceptance.md",
                blob="6f36506b601c2ebf3bd4df5397f5acbde423bcca",
                sha256="dd49f823569d51dede299ece002a053b2e3c8790e642f8014d59478bc6367732",
                anchor_commit="eeb13ca643d5b512faab93e2e762ef4558dab688",
                anchor_tree="5c807edd18fd7986a3c4fc2e8c5a9d28ba4ef6f1",
                reason="Bind the immutable P8 acceptance object without executing it.",
            ),
            _anchor(
                "P8",
                "p8_summary_anchor",
                path="artifacts/p8/summary.json",
                blob="964406b20e9fc1e98b8eeda3c24bf3f22f226768",
                sha256="78905893f9a06bf6b5361c76a8e152dbe8de2ec53d1aede84fca2f7ce1b5921b",
                anchor_commit=str(meta["commit"]),
                anchor_tree=str(meta["tree"]),
                reason="Preserve the accepted Darwin-scoped P8 result as identity-only evidence.",
                platform_scope="darwin_historical_evidence_identity",
                json_pointer_expectations={
                    "/claim": "v0_1_local_reference_release_candidate",
                    "/compose_runtime/environment/host": "darwin",
                    "/compose_runtime/status": "passed",
                    "/status": "development_complete_awaiting_independent_acceptance",
                },
            ),
            _anchor(
                "P8",
                "p8_receipt_anchor",
                path="provenance/p8-migration-receipt.json",
                blob="1b475cb999a8dffeaeb2e474059e5ff2476e6be1",
                sha256="c1c9a08a4c18783720a6a3fa0c8e0b5a3aa6d9cf91f5e0d465c31067141d21eb",
                anchor_commit=str(meta["commit"]),
                anchor_tree=str(meta["tree"]),
                reason="Bind the immutable P8 provenance receipt.",
            ),
            _anchor(
                "P8",
                "p8_python_lock_anchor",
                path="requirements/p8.lock",
                blob="819980980ba87d1b7166af4b4b0da53ca4e4ac63",
                sha256="5afb5bc2f6bf2cfdc77d0457b92255f822d89cd3cd754ebb876741d7ee6430d0",
                anchor_commit=str(meta["commit"]),
                anchor_tree=str(meta["tree"]),
                reason="Bind the P8 object-scoped hash-locked Python environment.",
            ),
            _anchor(
                "P8",
                "p8_npm_lock_anchor",
                path="studio/package-lock.json",
                blob="ec0730513988e98adaf2d935885859ba1b58f7b9",
                sha256="1c0f4648743f99241f380cf96b4f971ec71bdc1ef7bcadbd558f55e68d6747fd",
                anchor_commit=str(meta["commit"]),
                anchor_tree=str(meta["tree"]),
                reason="Bind the P8 object-scoped locked npm workspace.",
            ),
        )
    )
    items.extend(_quality_gates("P8", "p8_python_unittest", 308))
    focused = (
        ("p8_repository", "scripts/check_p8_repository.py", "Exact repository identity"),
        ("p8_provenance", "scripts/check_p8_provenance.py", "Exact provenance identity"),
        ("p8_operations", "scripts/check_p8_operations.py", "Static/operator contract"),
        (
            "p8_backup_restore",
            "scripts/check_p8_backup_restore.py",
            "Portable static/synthetic backup semantics",
        ),
        ("p8_diagnostics", "scripts/check_p8_diagnostics.py", "Safe diagnostic contract"),
        ("p8_supply_chain", "scripts/check_p8_supply_chain.py", "Dependency/input identities"),
        (
            "p8_reproducibility",
            "scripts/check_p8_reproducibility.py",
            "Deterministic build comparison",
        ),
        ("p8_release", "scripts/check_p8_release.py", "Release artifact contract"),
    )
    slow = {"p8_reproducibility", "p8_release"}
    for gate_id, path, reason in focused:
        items.append(
            _python_script(
                "P8",
                gate_id,
                path,
                reason=reason,
                timeout_seconds=(
                    OPERATION_TIMEOUTS["reproducibility_release_compose_quickstart"]
                    if gate_id in slow
                    else OPERATION_TIMEOUTS["static"]
                ),
            )
        )
    for gate_id, path in _P8_PRIOR:
        items.append(
            _python_script(
                "P8",
                gate_id,
                path,
                reason="Retain this accepted P2-P7 current-tree leaf from the P8 aggregate.",
            )
        )
    items.append(
        _python_script(
            "P8",
            "p8_public_boundary",
            "scripts/check_public_boundary.py",
            reason="Retain the P8 public-boundary leaf as an individual result.",
        )
    )
    items.append(
        _gate(
            "P8",
            "p8_git_diff_check",
            command_kind="git",
            command="git diff --check",
            reason="Retain the P8 committed-diff whitespace leaf.",
        )
    )
    items.extend(
        (
            _excluded_gate("P8", "p8_compose_runtime", "scripts/check_p8_compose_runtime.py"),
            _excluded_gate("P8", "p8_golden_path", "scripts/check_p8_golden_path.py"),
        )
    )
    return items


def _summary_anchor(
    object_name: str,
    blob: str,
    sha256: str,
    claim: str,
    status_value: str,
) -> dict[str, Any]:
    lower = object_name.lower()
    meta = OBJECTS[object_name]
    return _anchor(
        object_name,
        f"{lower}_summary_anchor",
        path=f"artifacts/{lower}/summary.json",
        blob=blob,
        sha256=sha256,
        anchor_commit=str(meta["commit"]),
        anchor_tree=str(meta["tree"]),
        reason=f"Bind the immutable {object_name} summary as identity-only evidence.",
        json_expectations={"claim": claim, "status": status_value},
    )


def _python_lock_anchor(object_name: str) -> dict[str, Any]:
    meta = OBJECTS[object_name]
    return _anchor(
        object_name,
        f"{object_name.lower()}_python_lock_anchor",
        path="requirements/p8.lock",
        blob="819980980ba87d1b7166af4b4b0da53ca4e4ac63",
        sha256="5afb5bc2f6bf2cfdc77d0457b92255f822d89cd3cd754ebb876741d7ee6430d0",
        anchor_commit=str(meta["commit"]),
        anchor_tree=str(meta["tree"]),
        reason=f"Bind the {object_name} object-scoped hash-locked Python environment.",
    )


def _npm_lock_anchor(object_name: str) -> dict[str, Any]:
    meta = OBJECTS[object_name]
    return _anchor(
        object_name,
        f"{object_name.lower()}_npm_lock_anchor",
        path="studio/package-lock.json",
        blob="e1ca59eac16dec46a290aaf2c010b5fc9de9cd91",
        sha256="44dba55271fa10c3b7bea09aa333c98dbf868f6cc55a8e59776ca1464c067875",
        anchor_commit=str(meta["commit"]),
        anchor_tree=str(meta["tree"]),
        reason=f"Bind the {object_name} object-scoped locked npm workspace.",
    )


def _retained(object_name: str, predecessor: str) -> dict[str, Any]:
    lower = object_name.lower()
    predecessor_lower = predecessor.lower()
    return _gate(
        object_name,
        f"{lower}_retained_{predecessor_lower}_portable",
        command_kind="predecessor_result",
        command=f"verify exact completed {predecessor} portable result and inventory digest",
        reason=f"Bind {object_name} to the completed {predecessor} portable layer without rerun.",
        expected={"predecessor_object": predecessor, "rerun_count": 0, "status": "passed"},
    )


def _p9_items() -> list[dict[str, Any]]:
    items = [
        _setup("P9"),
        _summary_anchor(
            "P9",
            "117b033f8f516dff269577ff28a8e51174e7f6a3",
            "a8085fa1889db4baa50b5aad4a2b574f614bf6f15a3efbf947f9a528a709df1c",
            "p9_productization_rebaseline_candidate",
            "development_complete_awaiting_independent_acceptance",
        ),
        _python_lock_anchor("P9"),
        _retained("P9", "P8"),
    ]
    for gate_id, path, reason in (
        ("p9_repository", "scripts/check_p9_repository.py", "Exact P9 repository identity"),
        ("p9_provenance", "scripts/check_p9_provenance.py", "Exact P9 provenance identity"),
        ("p9_rebaseline", "scripts/check_p9_rebaseline.py", "Exact P9 rebaseline contract"),
    ):
        items.append(_python_script("P9", gate_id, path, reason=reason))
    items.append(
        _gate(
            "P9",
            "p9_test",
            command_kind="python_script",
            command=(
                "<p9-python> -B scripts/run_p8_unittest_suite.py --start-directory tests/p9 "
                "--top-level-directory . --json-output <p9-temp>/p9-unittest.json"
            ),
            path="scripts/run_p8_unittest_suite.py",
            reason="Run the exact 32-test P9 suite as one counted historical leaf.",
            expected={
                "error_count": 0,
                "failure_count": 0,
                "skip_count": 0,
                "status": "passed",
                "test_count": 32,
                "test_count_semantics": "historical_python_unittest_cases",
            },
            timeout_seconds=OPERATION_TIMEOUTS["python"],
        )
    )
    items.append(
        _python_script(
            "P9",
            "p9_public_boundary",
            "scripts/check_public_boundary.py",
            reason="Retain the P9 public-boundary leaf.",
        )
    )
    items.append(
        _gate(
            "P9",
            "p9_git_diff_check",
            command_kind="git",
            command="git diff --check",
            reason="Retain the P9 committed-diff whitespace leaf.",
        )
    )
    return items


def _p10_items() -> list[dict[str, Any]]:
    items = [
        _setup("P10"),
        _summary_anchor(
            "P10",
            "a4c1a59fffec9c30160787a7bec584e228fb9f35",
            "876ddbf43f1fe09d67bf341f9a6cdd9f7ba39271a2fd2cc876a8423142cf4eae",
            "p10_mac_quickstart_distribution_candidate",
            "remote_distribution_candidate_ready_for_independent_acceptance",
        ),
        _python_lock_anchor("P10"),
        _npm_lock_anchor("P10"),
        _retained("P10", "P9"),
    ]
    items.extend(_quality_gates("P10", "p10_unittest", 39))
    for gate_id, path, reason in (
        ("p10_repository", "scripts/check_p10_repository.py", "Exact P10 repository identity"),
        ("p10_provenance", "scripts/check_p10_provenance.py", "Exact P10 provenance identity"),
        ("p10_distribution", "scripts/check_p10_distribution.py", "P10 distribution contract"),
        ("p10_security", "scripts/check_p10_security.py", "P10 security boundary"),
        ("p10_operations", "scripts/check_p10_operations.py", "P10 operations contract"),
        ("p10_i18n", "scripts/check_p10_i18n.py", "P10 language contract"),
        ("p10_compatibility", "scripts/check_p10_compatibility.py", "P10 compatibility contract"),
        (
            "p10_reproducibility",
            "scripts/check_p10_reproducibility.py",
            "P10 reproducibility contract",
        ),
    ):
        items.append(
            _python_script(
                "P10",
                gate_id,
                path,
                reason=reason,
                timeout_seconds=(
                    OPERATION_TIMEOUTS["reproducibility_release_compose_quickstart"]
                    if gate_id == "p10_reproducibility"
                    else OPERATION_TIMEOUTS["static"]
                ),
            )
        )
    items.extend(
        (
            _python_script(
                "P10",
                "p10_public_boundary",
                "scripts/check_public_boundary.py",
                reason="Retain the P10 public-boundary leaf.",
            ),
            _gate(
                "P10",
                "p10_git_diff_check",
                command_kind="git",
                command="git diff --check",
                reason="Retain the P10 committed-diff whitespace leaf.",
            ),
            _python_script(
                "P10",
                "p10_evidence",
                "scripts/check_p10_evidence.py",
                reason="Verify the accepted P10 evidence identity without rewriting it.",
            ),
            _excluded_gate("P10", "p10_compose_runtime", "scripts/check_p10_compose_runtime.py"),
            _excluded_gate("P10", "p10_quickstart", "scripts/check_p10_quickstart.py"),
            _excluded_gate(
                "P10",
                "p10_remote_distribution",
                "scripts/check_p10_quickstart.py",
                suffix=". --remote-distribution",
            ),
        )
    )
    return items


def _p11_items() -> list[dict[str, Any]]:
    items = [
        _setup("P11"),
        _summary_anchor(
            "P11",
            "f9f58cd3094147f724a622a929eb98331af441a1",
            "5f8072da2027265d9ee1ac959607d905fa68e1e88802f45a4f9bcb918707c7c9",
            "p11_agent_package_multi_agent_lifecycle_candidate",
            "development_complete_awaiting_independent_acceptance",
        ),
        _python_lock_anchor("P11"),
        _npm_lock_anchor("P11"),
        _retained("P11", "P10"),
    ]
    items.extend(_quality_gates("P11", "p11_unittest", 101))
    for gate_id, path, reason in (
        ("p11_repository", "scripts/check_p11_repository.py", "Exact P11 repository identity"),
        ("p11_provenance", "scripts/check_p11_provenance.py", "Exact P11 provenance identity"),
        ("p11_architecture", "scripts/check_p11_architecture.py", "P11 architecture boundary"),
        ("p11_migrations", "scripts/check_p11_migrations.py", "P11 migration boundary"),
        ("p11_compatibility", "scripts/check_p11_compatibility.py", "P11 compatibility boundary"),
        ("p11_studio", "scripts/check_p11_studio.py", "P11 Studio contract"),
        ("p11_public_boundary", "scripts/check_public_boundary.py", "P11 public boundary"),
    ):
        items.append(_python_script("P11", gate_id, path, reason=reason))
    items.append(
        _gate(
            "P11",
            "p11_candidate_diff",
            command_kind="python_function",
            command="scripts.p11_gate_support.candidate_diff_check(.)",
            path="scripts/p11_gate_support.py",
            callable_name="candidate_diff_check",
            reason="Invoke the exact unmodified P11 candidate diff function in a subprocess.",
        )
    )
    items.append(
        _python_script(
            "P11",
            "p11_compose_runtime",
            "scripts/check_p11_compose_runtime.py",
            reason="Retain the accepted portable P11 Compose leaf and zero cleanup.",
            expected={"cleanup_residue_count": 0, "status": "passed"},
            timeout_seconds=OPERATION_TIMEOUTS["reproducibility_release_compose_quickstart"],
        )
    )
    return items


def _p11r_items() -> list[dict[str, Any]]:
    items = [
        _setup("P11R"),
        _summary_anchor(
            "P11R",
            "30d4d3ac2360b165863c156b50628141141f13e9",
            "6d44960d9dc9035995acc36e4734648bc5bd67cc79c412192a790745d178084f",
            "p11r_post_p11_governance_and_ci_alignment_candidate",
            "development_complete_awaiting_independent_acceptance",
        ),
        _python_lock_anchor("P11R"),
        _npm_lock_anchor("P11R"),
        _retained("P11R", "P11"),
    ]
    items.extend(
        (
            _gate(
                "P11R",
                "p11r_ruff_lint",
                command_kind="python_module",
                command="<p11r-python> -m ruff check src scripts tests",
                reason="Retain the exact P11R Ruff lint leaf.",
                timeout_seconds=OPERATION_TIMEOUTS["python"],
            ),
            _gate(
                "P11R",
                "p11r_ruff_format",
                command_kind="python_module",
                command="<p11r-python> -m ruff format --check src scripts tests",
                reason="Retain the exact P11R Ruff format leaf.",
                timeout_seconds=OPERATION_TIMEOUTS["python"],
            ),
            _gate(
                "P11R",
                "p11r_mypy_strict",
                command_kind="python_module",
                command="<p11r-python> -m mypy src scripts tests",
                reason="Retain the exact P11R strict Mypy leaf.",
                timeout_seconds=OPERATION_TIMEOUTS["python"],
            ),
            _gate(
                "P11R",
                "p11r_current_p11_tests",
                command_kind="python_script",
                command=(
                    "<p11r-python> -B -m scripts.run_p11r_toolchain --scope current-tests "
                    "--json-output <p11r-temp>/current-p11.json"
                ),
                path="scripts/run_p11r_toolchain.py",
                callable_name="main:current-tests",
                reason="Run the exact 100-test branch-independent P11 regression leaf.",
                expected={
                    "error_count": 0,
                    "failure_count": 0,
                    "skip_count": 0,
                    "status": "passed",
                    "test_count": 100,
                    "test_count_semantics": "historical_python_unittest_cases",
                },
                timeout_seconds=OPERATION_TIMEOUTS["python"],
            ),
            _gate(
                "P11R",
                "p11r_governance_tests",
                command_kind="python_script",
                command=(
                    "<p11r-python> -B -m scripts.run_p11r_toolchain --scope p11r-tests "
                    "--json-output <p11r-temp>/p11r.json"
                ),
                path="scripts/run_p11r_toolchain.py",
                callable_name="main:p11r-tests",
                reason="Run the exact 36-test P11R governance leaf separately.",
                expected={
                    "error_count": 0,
                    "failure_count": 0,
                    "skip_count": 0,
                    "status": "passed",
                    "test_count": 36,
                    "test_count_semantics": "historical_python_unittest_cases",
                },
                timeout_seconds=OPERATION_TIMEOUTS["python"],
            ),
            _npm_gate("P11R", "p11r_studio_eslint", "corepack npm run lint", "lint"),
            _npm_gate(
                "P11R",
                "p11r_studio_prettier",
                "corepack npm run format:check",
                "format:check",
            ),
            _npm_gate(
                "P11R",
                "p11r_studio_typescript",
                "corepack npm run typecheck",
                "typecheck",
            ),
            _npm_gate("P11R", "p11r_studio_vitest", "corepack npm test -- --run", "test"),
            _npm_gate("P11R", "p11r_studio_vite_build", "corepack npm run build", "build"),
        )
    )
    for gate_id, path, reason in (
        ("p11r_architecture", "scripts/check_p11_architecture.py", "P11R P11 architecture leaf"),
        ("p11r_migrations", "scripts/check_p11_migrations.py", "P11R P11 migration leaf"),
        (
            "p11r_compatibility",
            "scripts/check_p11_compatibility.py",
            "P11R P11 compatibility leaf",
        ),
        ("p11r_studio_contract", "scripts/check_p11_studio.py", "P11R P11 Studio leaf"),
        ("p11r_ci_policy", "scripts/check_p11r_ci_policy.py", "Exact P11R CI policy"),
        (
            "p11r_repository_ci",
            "scripts/check_p11r_repository.py",
            "Branch-independent P11R repository CI mode",
        ),
        ("p11r_provenance", "scripts/check_p11r_provenance.py", "Exact P11R provenance"),
        ("p11r_public_boundary", "scripts/check_public_boundary.py", "P11R public boundary"),
        (
            "p11r_candidate_repository",
            "scripts/check_p11r_repository.py",
            "P11R candidate repository mode",
        ),
    ):
        suffix = "."
        if gate_id == "p11r_repository_ci":
            suffix = ". --mode ci"
        elif gate_id == "p11r_candidate_repository":
            suffix = ". --mode candidate"
        items.append(_python_script("P11R", gate_id, path, reason=reason, suffix=suffix))
    items.append(
        _python_script(
            "P11R",
            "p11r_compose_runtime",
            "scripts/check_p11_compose_runtime.py",
            reason="Retain the bounded accepted P11R Compose leaf and zero cleanup.",
            expected={"cleanup_residue_count": 0, "status": "passed"},
            timeout_seconds=OPERATION_TIMEOUTS["reproducibility_release_compose_quickstart"],
        )
    )
    return items


CANONICAL_INVENTORY: tuple[dict[str, Any], ...] = tuple(
    _p8_items() + _p9_items() + _p10_items() + _p11_items() + _p11r_items()
)
INCLUDED_GATE_IDS = tuple(
    str(item["gate_id"])
    for item in CANONICAL_INVENTORY
    if item["item_type"] == "included_acceptance_gate"
)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise HistoricalInventoryError("inventory JSON contains a duplicate key")
        value[key] = item
    return value


def _normalize_json(value: object) -> object:
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        raise HistoricalInventoryError("inventory JSON contains a floating number")
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list) or isinstance(value, tuple):
        return [_normalize_json(item) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise HistoricalInventoryError("inventory JSON contains a non-string key")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                raise HistoricalInventoryError("inventory JSON keys collide after NFC")
            normalized[normalized_key] = _normalize_json(item)
        return normalized
    raise HistoricalInventoryError("inventory JSON contains an unsupported value")


def canonical_json(value: object) -> bytes:
    normalized = _normalize_json(value)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _anchor_canonical_json(value: object) -> bytes:
    """Reproduce Appendix C's exact immutable historical-anchor bytes."""

    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise HistoricalInventoryError("embedded Darwin anchor cannot be canonicalized") from exc


def excluded_platform_result(item: dict[str, Any]) -> dict[str, object]:
    """Return the closed platform-result projection for one excluded gate."""

    gate_id = item.get("gate_id")
    expected = item.get("expected")
    if (
        item.get("item_type") != "excluded_acceptance_gate"
        or gate_id not in EXCLUDED_GATE_IDS
        or not isinstance(expected, dict)
    ):
        raise HistoricalInventoryError("platform result requested for a non-excluded item")
    return {
        "disposition": expected.get("disposition"),
        "executor_result": expected.get("executor_result"),
        "exit_status": expected.get("exit_status"),
        "linux_public_pilot_readiness": expected.get("linux_public_pilot_readiness"),
        "reason": item.get("reason"),
        "replay_platform": expected.get("replay_platform"),
        "ubuntu_historical_execution_status": expected.get("ubuntu_historical_execution_status"),
    }


def _validate_excluded_contract(item: dict[str, Any]) -> None:
    gate_id = str(item.get("gate_id"))
    expected = {
        "disposition": "excluded_acceptance_gate",
        "executor_result": "not_run_platform_excluded",
        "exit_status": None,
        "linux_public_pilot_readiness": "blocked",
        "replay_platform": "ubuntu-24.04",
        "ubuntu_historical_execution_status": "not_proven",
    }
    if (
        gate_id not in EXCLUDED_GATE_IDS
        or item.get("expected") != expected
        or item.get("reason") != EXCLUDED_REASON_TOKENS[gate_id]
        or item.get("platform_scope")
        != "replay=ubuntu-24.04; Ubuntu status=not_proven; Darwin anchor=passed"
        or item.get("embedded_anchor") != EMBEDDED_DARWIN_ANCHORS[gate_id]
    ):
        raise HistoricalInventoryError("excluded platform result or Darwin anchor drifted")
    platform_result = excluded_platform_result(item)
    if set(platform_result) != {
        "disposition",
        "executor_result",
        "exit_status",
        "linux_public_pilot_readiness",
        "reason",
        "replay_platform",
        "ubuntu_historical_execution_status",
    }:
        raise HistoricalInventoryError("excluded platform-result field set is not exact")


def _validate_common(item: dict[str, Any]) -> None:
    common_keys = {
        "branch",
        "command",
        "command_kind",
        "commit",
        "entrypoint",
        "expected",
        "gate_id",
        "item_type",
        "object",
        "platform_scope",
        "reason",
        "ref_layout",
        "resource_scope",
        "timeout_seconds",
        "tree",
    }
    allowed_keys = set(common_keys)
    if item.get("item_type") == "setup":
        allowed_keys.add("resources")
    if item.get("item_type") == "excluded_acceptance_gate":
        allowed_keys.add("embedded_anchor")
    if set(item) != allowed_keys:
        raise HistoricalInventoryError("inventory item field set is not exact")
    gate_id = item.get("gate_id")
    if not isinstance(gate_id, str) or _GATE_ID.fullmatch(gate_id) is None:
        raise HistoricalInventoryError("inventory gate ID is invalid or dynamic")
    object_name = item.get("object")
    if object_name not in OBJECTS:
        raise HistoricalInventoryError("inventory object is unknown")
    metadata = OBJECTS[str(object_name)]
    if (
        item.get("commit") != metadata["commit"]
        or item.get("tree") != metadata["tree"]
        or item.get("branch") != metadata["branch"]
        or item.get("resource_scope") != str(object_name).lower()
    ):
        raise HistoricalInventoryError("inventory object identity or resource scope drifted")
    commit = item.get("commit")
    tree = item.get("tree")
    if not isinstance(commit, str) or _HEX40.fullmatch(commit) is None:
        raise HistoricalInventoryError("inventory commit identity is malformed")
    if not isinstance(tree, str) or _HEX40.fullmatch(tree) is None:
        raise HistoricalInventoryError("inventory tree identity is malformed")
    command = item.get("command")
    command_kind = item.get("command_kind")
    reason = item.get("reason")
    platform_scope = item.get("platform_scope")
    if not all(isinstance(value, str) and value for value in (command, reason, platform_scope)):
        raise HistoricalInventoryError("inventory command, reason, or platform scope is empty")
    if command_kind not in COMMAND_KINDS:
        raise HistoricalInventoryError(
            "inventory command kind is not a closed subprocess operation"
        )
    dynamic_tokens = ("*", "${", "$(", "latest", "glob", "discover")
    if any(token in str(command) for token in dynamic_tokens):
        raise HistoricalInventoryError("inventory command uses dynamic membership or indirection")
    timeout = item.get("timeout_seconds")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise HistoricalInventoryError("inventory timeout is not a positive integer")
    if timeout > OBJECT_TIMEOUTS[str(object_name)]:
        raise HistoricalInventoryError("inventory leaf timeout exceeds its object limit")
    ref_layout = item.get("ref_layout")
    branch = str(metadata["branch"])
    base = str(metadata["base"])
    expected_refs = {
        "branch_ref": f"refs/heads/{branch}",
        "head": metadata["commit"],
        "main": base,
        "origin_main": base,
    }
    if ref_layout != expected_refs:
        raise HistoricalInventoryError("inventory historical ref layout drifted")
    entrypoint = item.get("entrypoint")
    if command_kind in {"npm_script", "python_function", "python_script"} and entrypoint is None:
        raise HistoricalInventoryError("historical subprocess lacks its exact entrypoint")
    if (
        command_kind
        in {
            "git",
            "identity_check",
            "object_setup",
            "predecessor_result",
            "python_module",
        }
        and entrypoint is not None
    ):
        raise HistoricalInventoryError("non-entrypoint operation gained an entrypoint")
    if entrypoint is not None:
        if not isinstance(entrypoint, dict) or set(entrypoint) != {
            "blob",
            "callable",
            "mode",
            "path",
        }:
            raise HistoricalInventoryError("inventory entrypoint field set is not exact")
        path = entrypoint.get("path")
        blob = entrypoint.get("blob")
        mode = entrypoint.get("mode")
        callable_name = entrypoint.get("callable")
        if (
            not isinstance(path, str)
            or path.startswith("/")
            or ".." in Path(path).parts
            or not isinstance(blob, str)
            or _HEX40.fullmatch(blob) is None
            or mode not in {"100644", "100755"}
            or not isinstance(callable_name, str)
            or not callable_name
        ):
            raise HistoricalInventoryError("inventory entrypoint identity is unsafe")


def _validate_resources(items: Sequence[dict[str, Any]]) -> None:
    setups = [item for item in items if item.get("item_type") == "setup"]
    if [item.get("object") for item in setups] != list(OBJECT_ORDER):
        raise HistoricalInventoryError("one ordered setup per historical object is required")
    positions = {
        name: next(i for i, item in enumerate(items) if item.get("object") == name)
        for name in OBJECT_ORDER
    }
    if any(items[positions[name]].get("item_type") != "setup" for name in OBJECT_ORDER):
        raise HistoricalInventoryError("object setup must precede every item for that object")
    for setup in setups:
        object_name = str(setup["object"])
        resources = setup.get("resources")
        if not isinstance(resources, dict):
            raise HistoricalInventoryError("setup resource contract is missing")
        expected = {
            "checkout_count": 1,
            "checkout_timeout_seconds": OPERATION_TIMEOUTS["checkout_ref"],
            "cleanup_before_next_object": True,
            "cleanup_residue_count": 0,
            "environment": CHILD_ENVIRONMENT,
            "lock_anchor_ids": [f"{object_name.lower()}_python_lock_anchor"]
            + (
                [f"{object_name.lower()}_npm_lock_anchor"]
                if OBJECTS[object_name]["npm_workspace"]
                else []
            ),
            "npm_install_timeout_seconds": OPERATION_TIMEOUTS["npm_install"],
            "npm_workspace_count": 1 if OBJECTS[object_name]["npm_workspace"] else 0,
            "object_timeout_seconds": OBJECT_TIMEOUTS[object_name],
            "python_environment_count": 1,
            "venv_install_timeout_seconds": OPERATION_TIMEOUTS["venv_install"],
        }
        if resources != expected:
            raise HistoricalInventoryError("per-object resource or cleanup policy drifted")
        expected_result = {
            "cleanup_residue_count": 0,
            "npm_workspace": "one_locked" if OBJECTS[object_name]["npm_workspace"] else "absent",
            "python_environment": "one_hash_locked",
            "status": "passed",
        }
        if setup.get("expected") != expected_result:
            raise HistoricalInventoryError("setup result or zero-residue requirement drifted")
    object_sequence: list[str] = []
    for item in items:
        name = str(item.get("object"))
        if not object_sequence or object_sequence[-1] != name:
            object_sequence.append(name)
    if tuple(object_sequence) != OBJECT_ORDER:
        raise HistoricalInventoryError("historical objects are interleaved or reordered")


def _validate_semantics(items: Sequence[dict[str, Any]]) -> None:
    if len(items) != ITEM_COUNTS["total"]:
        raise HistoricalInventoryError("portable inventory total is not exactly 151")
    if any(not isinstance(item, dict) for item in items):
        raise HistoricalInventoryError("portable inventory item is not an object")
    for item in items:
        _validate_common(item)
    gate_ids = [str(item["gate_id"]) for item in items]
    if len(set(gate_ids)) != len(gate_ids):
        raise HistoricalInventoryError("portable inventory IDs are not unique")
    counts = {
        item_type: sum(item["item_type"] == item_type for item in items)
        for item_type in (
            "setup",
            "included_acceptance_gate",
            "evidence_anchor",
            "excluded_acceptance_gate",
        )
    }
    if counts != {key: ITEM_COUNTS[key] for key in counts}:
        raise HistoricalInventoryError("portable inventory typed counts drifted")
    unknown_types = {str(item["item_type"]) for item in items} - set(counts)
    if unknown_types:
        raise HistoricalInventoryError("portable inventory contains an unknown item type")
    included = tuple(
        str(item["gate_id"]) for item in items if item["item_type"] == "included_acceptance_gate"
    )
    excluded = tuple(
        str(item["gate_id"]) for item in items if item["item_type"] == "excluded_acceptance_gate"
    )
    if included != INCLUDED_GATE_IDS or excluded != EXCLUDED_GATE_IDS:
        raise HistoricalInventoryError("included or excluded acceptance-gate identity drifted")
    partitions = {
        name: sum(
            item["object"] == name and item["item_type"] == "included_acceptance_gate"
            for item in items
        )
        for name in OBJECT_ORDER
    }
    if partitions != PARTITION_COUNTS:
        raise HistoricalInventoryError("portable acceptance-gate partition drifted")
    accepted = set(ACCEPTED_GATE_IDS)
    included_set = set(included)
    excluded_set = set(excluded)
    difference = accepted - included_set
    if (
        len(ACCEPTED_GATE_IDS) != 129
        or len(accepted) != 129
        or included_set & excluded_set
        or accepted != included_set | excluded_set
        or difference != excluded_set
        or tuple(gate_id for gate_id in EXCLUDED_GATE_IDS if gate_id in difference)
        != EXCLUDED_GATE_IDS
    ):
        raise HistoricalInventoryError(
            "independently derived accepted set does not equal included disjoint-union excluded"
        )
    setup_or_anchors = {
        str(item["gate_id"]) for item in items if item["item_type"] in {"setup", "evidence_anchor"}
    }
    if setup_or_anchors & accepted:
        raise HistoricalInventoryError("setup or evidence anchor masquerades as a gate")
    if "p8_bootstrap" in accepted or "p8_bootstrap" in gate_ids:
        raise HistoricalInventoryError("the former P8 bootstrap label cannot be a gate")
    commands = tuple(str(item["command"]) for item in items)
    if any(forbidden in command for forbidden in FORBIDDEN_AGGREGATES for command in commands):
        raise HistoricalInventoryError("portable inventory invokes a recursive aggregate")
    predecessor_items = [item for item in items if item["command_kind"] == "predecessor_result"]
    if tuple(str(item["object"]) for item in predecessor_items) != tuple(PREDECESSOR_OBJECTS):
        raise HistoricalInventoryError("predecessor-result object order drifted")
    for item in predecessor_items:
        object_name = str(item["object"])
        predecessor = PREDECESSOR_OBJECTS[object_name]
        expected = {
            "predecessor_object": predecessor,
            "rerun_count": 0,
            "status": "passed",
        }
        if (
            item["expected"] != expected
            or item["command"]
            != f"verify exact completed {predecessor} portable result and inventory digest"
        ):
            raise HistoricalInventoryError(
                "predecessor-result identity, digest binding, or recursion policy drifted"
            )
    for item in items:
        if item["item_type"] == "excluded_acceptance_gate":
            _validate_excluded_contract(item)
    p8_anchor = next(item for item in items if item["gate_id"] == "p8_summary_anchor")
    if (
        p8_anchor["item_type"] != "evidence_anchor"
        or p8_anchor["platform_scope"] != "darwin_historical_evidence_identity"
    ):
        raise HistoricalInventoryError("P8 Darwin evidence is not platform scoped")
    gate_items = [
        item
        for item in items
        if item["item_type"] in {"included_acceptance_gate", "excluded_acceptance_gate"}
    ]
    gate_null_entrypoints = sum(item["entrypoint"] is None for item in gate_items)
    inventory_null_entrypoints = sum(item["entrypoint"] is None for item in items)
    if (
        len(gate_items) != 129
        or gate_null_entrypoints != 19
        or len(gate_items) - gate_null_entrypoints != 110
        or inventory_null_entrypoints != 41
        or len(items) - inventory_null_entrypoints != 110
    ):
        raise HistoricalInventoryError("historical entrypoint nullability counts drifted")
    command_kind_counts = {
        kind: sum(item["command_kind"] == kind for item in gate_items) for kind in COMMAND_KINDS
    }
    if command_kind_counts != {
        "git": 3,
        "identity_check": 0,
        "npm_script": 20,
        "object_setup": 0,
        "predecessor_result": 4,
        "python_function": 1,
        "python_module": 12,
        "python_script": 89,
    }:
        raise HistoricalInventoryError("accepted-gate command-kind counts drifted")
    _validate_resources(items)


def validate_inventory(items: Sequence[dict[str, Any]], *, require_literal: bool = True) -> None:
    _validate_semantics(items)
    if require_literal and tuple(items) != CANONICAL_INVENTORY:
        raise HistoricalInventoryError("portable inventory differs from the full literal contract")


def load_inventory(root: Path) -> tuple[dict[str, Any], ...]:
    path = root / INVENTORY_PATH
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or path.is_symlink() or metadata.st_size > 1_048_576:
            raise HistoricalInventoryError("portable inventory file type or size is invalid")
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except HistoricalInventoryError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HistoricalInventoryError(
            "portable inventory cannot be read as one JSON document"
        ) from exc
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise HistoricalInventoryError("portable inventory must be one JSON array of objects")
    if raw != canonical_json(value):
        raise HistoricalInventoryError(
            "portable inventory bytes are not exact P12-CJ-1 canonical JSON"
        )
    items = tuple(value)
    validate_inventory(items)
    return items


def _read_object_bytes(root: Path, commit: str, path: str) -> bytes:
    environment = os.environ.copy()
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=root,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise HistoricalInventoryError("historical Git blob cannot be read")
    return completed.stdout


def _verify_anchor_content(item: dict[str, Any], raw: bytes) -> None:
    expected = item["expected"]
    assert isinstance(expected, dict)
    json_expectations = expected.get("json_expectations")
    json_pointer_expectations = expected.get("json_pointer_expectations")
    if json_expectations is None and json_pointer_expectations is None:
        return
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise HistoricalInventoryError("historical JSON anchor is malformed") from exc
    if not isinstance(value, dict):
        raise HistoricalInventoryError("historical JSON anchor contract is malformed")
    if json_expectations is not None:
        if not isinstance(json_expectations, dict) or json_pointer_expectations is not None:
            raise HistoricalInventoryError("historical JSON anchor contract is malformed")
        for key, expected_value in json_expectations.items():
            if value.get(key) != expected_value:
                raise HistoricalInventoryError("historical JSON anchor status or claim drifted")
    if json_pointer_expectations is not None:
        if not isinstance(json_pointer_expectations, dict) or json_expectations is not None:
            raise HistoricalInventoryError("historical JSON anchor contract is malformed")
        for pointer, expected_value in json_pointer_expectations.items():
            if not isinstance(pointer, str) or not pointer.startswith("/"):
                raise HistoricalInventoryError("historical JSON anchor pointer is invalid")
            actual: object = value
            for raw_token in pointer.removeprefix("/").split("/"):
                token = raw_token.replace("~1", "/").replace("~0", "~")
                if not isinstance(actual, dict) or token not in actual:
                    raise HistoricalInventoryError("historical JSON anchor pointer is absent")
                actual = actual[token]
            if actual != expected_value:
                raise HistoricalInventoryError("historical JSON anchor status or claim drifted")


def _verify_embedded_anchor(root: Path, item: dict[str, Any]) -> None:
    anchor = item.get("embedded_anchor")
    if not isinstance(anchor, dict):
        raise HistoricalInventoryError("excluded gate lacks its embedded Darwin anchor")
    source_commit = str(anchor["source_commit"])
    source_tree = str(anchor["source_tree"])
    source_path = str(anchor["source_path"])
    source_blob = str(anchor["source_blob"])
    if _git(root, "rev-parse", f"{source_commit}^{{tree}}") != source_tree:
        raise HistoricalInventoryError("embedded Darwin anchor tree identity drifted")
    if _git(root, "ls-tree", source_commit, "--", source_path) != (
        f"100644 blob {source_blob}\t{source_path}"
    ):
        raise HistoricalInventoryError("embedded Darwin anchor blob or mode drifted")
    raw = _read_object_bytes(root, source_commit, source_path)
    if hashlib.sha256(raw).hexdigest() != anchor["source_file_sha256"]:
        raise HistoricalInventoryError("embedded Darwin anchor source SHA-256 drifted")
    try:
        summary = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise HistoricalInventoryError("embedded Darwin anchor JSON is malformed") from exc
    if not isinstance(summary, dict):
        raise HistoricalInventoryError("embedded Darwin anchor source is not an object")
    gate_id = str(item["gate_id"])
    if gate_id == "p8_compose_runtime":
        selected = summary.get("compose_runtime")
    elif gate_id == "p8_golden_path":
        selected = summary.get("golden_path")
    elif gate_id == "p10_compose_runtime":
        selected = summary.get("compose_runtime")
    elif gate_id == "p10_quickstart":
        selected = summary.get("quickstart")
    elif gate_id == "p10_remote_distribution":
        selected = {
            "distribution": summary.get("remote_distribution"),
            "quickstart": summary.get("remote_quickstart"),
        }
    else:  # pragma: no cover - guarded by the exact excluded set
        raise HistoricalInventoryError("unknown embedded Darwin anchor gate")
    payload = _anchor_canonical_json({"gate_id": gate_id, "result": selected})
    if (
        len(payload) != anchor["canonical_bytes"]
        or hashlib.sha256(payload).hexdigest() != anchor["canonical_sha256"]
    ):
        raise HistoricalInventoryError("embedded Darwin anchor canonical identity drifted")
    verified_gates = summary.get("verified_gates")
    aggregate = summary.get("aggregate")
    p10_aggregate_passed = isinstance(aggregate, dict) and aggregate.get("status") == "passed"
    if gate_id == "p8_compose_runtime":
        valid = (
            isinstance(selected, dict)
            and selected.get("gate") == "p8_compose_runtime_clean"
            and selected.get("status") == "passed"
            and selected.get("environment", {}).get("host") == "darwin"
        )
    elif gate_id == "p8_golden_path":
        compose = summary.get("compose_runtime")
        valid = (
            isinstance(selected, dict)
            and selected.get("gate") == "p8_golden_path_clean"
            and selected.get("status") == "passed"
            and isinstance(compose, dict)
            and compose.get("environment", {}).get("host") == "darwin"
        )
    elif gate_id == "p10_compose_runtime":
        valid = (
            isinstance(selected, dict)
            and isinstance(verified_gates, list)
            and gate_id in verified_gates
            and p10_aggregate_passed
            and selected.get("gate") == "p10_compose_runtime_clean"
            and selected.get("native_architecture") == "arm64"
        )
    elif gate_id == "p10_quickstart":
        valid = (
            isinstance(selected, dict)
            and isinstance(verified_gates, list)
            and gate_id in verified_gates
            and p10_aggregate_passed
            and selected.get("gate") == "p10_quickstart_clean"
            and selected.get("actual_macos") is True
            and selected.get("platform_class") == "macos/arm64"
        )
    else:
        distribution = selected.get("distribution") if isinstance(selected, dict) else None
        quickstart = selected.get("quickstart") if isinstance(selected, dict) else None
        valid = (
            isinstance(verified_gates, list)
            and gate_id in verified_gates
            and p10_aggregate_passed
            and isinstance(distribution, dict)
            and distribution.get("gate") == "p10_remote_distribution_clean"
            and distribution.get("remote_distribution_gate") == "passed"
            and distribution.get("anonymous_pull") == "passed"
            and isinstance(quickstart, dict)
            and quickstart.get("actual_macos") is True
            and quickstart.get("platform_class") == "macos/arm64"
        )
    if not valid:
        raise HistoricalInventoryError("embedded Darwin anchor proof is incomplete")


def _verify_git_objects(root: Path, items: Sequence[dict[str, Any]]) -> int:
    verified_entrypoints: set[tuple[str, str, str]] = set()
    for object_name in OBJECT_ORDER:
        metadata = OBJECTS[object_name]
        if _git(root, "rev-parse", f"{metadata['commit']}^{{tree}}") != metadata["tree"]:
            raise HistoricalInventoryError("historical object tree identity drifted")
    for item in items:
        entrypoint = item.get("entrypoint")
        if isinstance(entrypoint, dict):
            identity = (str(item["commit"]), str(entrypoint["path"]), str(entrypoint["blob"]))
            if identity not in verified_entrypoints:
                line = _git(root, "ls-tree", str(item["commit"]), "--", str(entrypoint["path"]))
                expected_line = (
                    f"{entrypoint['mode']} blob {entrypoint['blob']}\t{entrypoint['path']}"
                )
                if line != expected_line:
                    raise HistoricalInventoryError("historical entrypoint blob or mode drifted")
                raw = _read_object_bytes(root, str(item["commit"]), str(entrypoint["path"]))
                callable_name = str(entrypoint["callable"])
                if item["command_kind"] in {"python_script", "python_function"}:
                    text = raw.decode("utf-8")
                    symbol = callable_name.split(":", 1)[0]
                    if symbol == "main":
                        if "def main(" not in text or '__name__ == "__main__"' not in text:
                            raise HistoricalInventoryError(
                                "historical Python CLI identity is not callable"
                            )
                    elif f"def {symbol}(" not in text:
                        raise HistoricalInventoryError(
                            "historical Python function identity is absent"
                        )
                elif item["command_kind"] == "npm_script":
                    package = json.loads(
                        raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
                    )
                    if (
                        not isinstance(package, dict)
                        or not isinstance(package.get("scripts"), dict)
                        or callable_name not in package["scripts"]
                    ):
                        raise HistoricalInventoryError("historical npm script identity is absent")
                verified_entrypoints.add(identity)
        if item["item_type"] == "evidence_anchor":
            expected = item["expected"]
            assert isinstance(expected, dict)
            anchor_commit = str(expected["anchor_commit"])
            anchor_path = str(expected["path"])
            if _git(root, "rev-parse", f"{anchor_commit}^{{tree}}") != expected["anchor_tree"]:
                raise HistoricalInventoryError("historical anchor tree identity drifted")
            if _git(root, "rev-parse", f"{anchor_commit}:{anchor_path}") != expected["blob"]:
                raise HistoricalInventoryError("historical anchor blob identity drifted")
            raw = _read_object_bytes(root, anchor_commit, anchor_path)
            if hashlib.sha256(raw).hexdigest() != expected["sha256"]:
                raise HistoricalInventoryError("historical anchor SHA-256 drifted")
            _verify_anchor_content(item, raw)
        elif item["item_type"] == "excluded_acceptance_gate":
            _verify_embedded_anchor(root, item)
    return len(verified_entrypoints)


def validate_entrypoint_resolution(
    item: dict[str, Any],
    *,
    checkout_root: Path,
    resolved_path: Path,
    resolved_blob: str,
) -> None:
    entrypoint = item.get("entrypoint")
    if not isinstance(entrypoint, dict):
        raise HistoricalInventoryError("inventory item has no historical entrypoint")
    try:
        expected_path = (checkout_root.resolve() / str(entrypoint["path"])).resolve(strict=False)
        actual_path = resolved_path.resolve(strict=False)
        actual_path.relative_to(checkout_root.resolve())
    except (OSError, ValueError) as exc:
        raise HistoricalInventoryError(
            "historical module resolved outside its exact checkout"
        ) from exc
    if actual_path != expected_path:
        raise HistoricalInventoryError("historical module resolved to a same-name shadow")
    if resolved_blob != entrypoint["blob"]:
        raise HistoricalInventoryError("historical module blob does not match the manifest")


def _validate_result_sequence(
    items: Sequence[dict[str, Any]], results: Sequence[dict[str, object]]
) -> dict[str, object]:
    if len(results) != len(items):
        raise HistoricalInventoryError("historical leaf results are not one-for-one")
    failure_seen = False
    executed_count = 0
    for item, result in zip(items, results, strict=True):
        item_type = item["item_type"]
        required_keys = {"exit_status", "gate_id", "item_type", "result"}
        if item_type == "excluded_acceptance_gate":
            required_keys |= {"embedded_anchor", "platform_result"}
        if set(result) != required_keys:
            raise HistoricalInventoryError("historical compact result field set is not exact")
        if result.get("gate_id") != item["gate_id"] or result.get("item_type") != item["item_type"]:
            raise HistoricalInventoryError("historical compact result identity or order drifted")
        if item_type == "excluded_acceptance_gate" and (
            result.get("platform_result") != excluded_platform_result(item)
            or result.get("embedded_anchor") != item["embedded_anchor"]
        ):
            raise HistoricalInventoryError("excluded result platform or anchor binding drifted")
        outcome = result.get("result")
        exit_status = result.get("exit_status")
        if failure_seen:
            if outcome != "not_run_due_to_prior_failure" or exit_status is not None:
                raise HistoricalInventoryError("a result after failure was executed or inferred")
            continue
        if item_type == "excluded_acceptance_gate":
            if outcome != "not_run_platform_excluded" or exit_status is not None:
                raise HistoricalInventoryError("a platform exclusion was executed or relabeled")
        elif outcome == "failed":
            if (
                not isinstance(exit_status, int)
                or isinstance(exit_status, bool)
                or exit_status == 0
            ):
                raise HistoricalInventoryError("failed historical result lacks its nonzero status")
            failure_seen = True
            executed_count += 1
        elif item_type in {"setup", "included_acceptance_gate"}:
            if outcome != "passed" or exit_status != 0:
                raise HistoricalInventoryError("executed historical leaf did not pass exactly")
            executed_count += 1
        elif item_type == "evidence_anchor":
            if outcome != "identity_verified" or exit_status is not None:
                raise HistoricalInventoryError("evidence anchor was represented as a gate result")
        else:
            raise HistoricalInventoryError("historical result has an unknown item type")
    return {
        "executed_item_count": executed_count,
        "failure_count": 1 if failure_seen else 0,
        "item_result_count": len(results),
        "status": "failed" if failure_seen else "passed",
    }


def validate_item_results(
    items: Sequence[dict[str, Any]], results: Sequence[dict[str, object]]
) -> dict[str, object]:
    validate_inventory(items)
    return _validate_result_sequence(items, results)


def _sha256_digest(value: object) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(value)).hexdigest()}"


def _validate_inventory_digest(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or _HEX64.fullmatch(value.removeprefix("sha256:")) is None
    ):
        raise HistoricalInventoryError("object result inventory digest is malformed")
    if value != _sha256_digest(CANONICAL_INVENTORY):
        raise HistoricalInventoryError(
            "object result is not bound to the complete canonical inventory"
        )
    return value


def build_object_result(
    object_name: str,
    *,
    inventory_digest: str,
    ordered_item_results: Sequence[dict[str, object]],
    cleanup_residue_count: int = 0,
) -> dict[str, object]:
    """Build one closed, canonicalizable exact-object result."""

    if object_name not in OBJECTS:
        raise HistoricalInventoryError("object result names an unknown historical object")
    _validate_inventory_digest(inventory_digest)
    if (
        not isinstance(cleanup_residue_count, int)
        or isinstance(cleanup_residue_count, bool)
        or cleanup_residue_count != 0
    ):
        raise HistoricalInventoryError("completed object result must prove zero cleanup residue")
    object_items = tuple(item for item in CANONICAL_INVENTORY if item["object"] == object_name)
    copied_results = list(deepcopy(ordered_item_results))
    summary = _validate_result_sequence(object_items, copied_results)
    metadata = OBJECTS[object_name]
    return {
        "schema": OBJECT_RESULT_SCHEMA,
        "object": object_name,
        "commit": metadata["commit"],
        "tree": metadata["tree"],
        "inventory_digest": inventory_digest,
        "ordered_item_results": copied_results,
        "cleanup_residue_count": cleanup_residue_count,
        "status": summary["status"],
    }


def validate_object_result(
    result: dict[str, object],
    *,
    expected_object: str,
    expected_inventory_digest: str,
    expected_digest: str | None = None,
    require_passed: bool = False,
) -> dict[str, object]:
    """Validate exact object identity, complete ordered leaves, cleanup, and digest."""

    if expected_object not in OBJECTS:
        raise HistoricalInventoryError("object-result expectation names an unknown object")
    expected_inventory_digest = _validate_inventory_digest(expected_inventory_digest)
    if set(result) != {
        "schema",
        "object",
        "commit",
        "tree",
        "inventory_digest",
        "ordered_item_results",
        "cleanup_residue_count",
        "status",
    }:
        raise HistoricalInventoryError("object result field set is not exact")
    metadata = OBJECTS[expected_object]
    if (
        result.get("schema") != OBJECT_RESULT_SCHEMA
        or result.get("object") != expected_object
        or result.get("commit") != metadata["commit"]
        or result.get("tree") != metadata["tree"]
        or result.get("inventory_digest") != expected_inventory_digest
    ):
        raise HistoricalInventoryError("object result identity or inventory binding drifted")
    cleanup_residue_count = result.get("cleanup_residue_count")
    if (
        not isinstance(cleanup_residue_count, int)
        or isinstance(cleanup_residue_count, bool)
        or cleanup_residue_count != 0
    ):
        raise HistoricalInventoryError("object result cleanup residue is not zero")
    ordered_item_results = result.get("ordered_item_results")
    if not isinstance(ordered_item_results, list) or any(
        not isinstance(item, dict) for item in ordered_item_results
    ):
        raise HistoricalInventoryError("object result leaves are not one ordered array")
    object_items = tuple(item for item in CANONICAL_INVENTORY if item["object"] == expected_object)
    summary = _validate_result_sequence(object_items, ordered_item_results)
    if result.get("status") != summary["status"]:
        raise HistoricalInventoryError("object result status does not match its leaves")
    if require_passed and result.get("status") != "passed":
        raise HistoricalInventoryError("predecessor object result did not pass")
    digest = _sha256_digest(result)
    if expected_digest is not None:
        if (
            not isinstance(expected_digest, str)
            or not expected_digest.startswith("sha256:")
            or _HEX64.fullmatch(expected_digest.removeprefix("sha256:")) is None
            or digest != expected_digest
        ):
            raise HistoricalInventoryError("object result digest is missing or mismatched")
    return {**summary, "object_result_digest": digest}


def object_result_digest(result: dict[str, object]) -> str:
    """Return the P12-CJ-1 digest of an already closed object result."""

    object_name = result.get("object")
    inventory_digest = result.get("inventory_digest")
    if not isinstance(object_name, str) or not isinstance(inventory_digest, str):
        raise HistoricalInventoryError("object result lacks its identity or inventory digest")
    validated = validate_object_result(
        result,
        expected_object=object_name,
        expected_inventory_digest=inventory_digest,
    )
    return str(validated["object_result_digest"])


def validate_object_result_bytes(
    raw: bytes,
    *,
    expected_object: str,
    expected_inventory_digest: str,
    expected_digest: str,
    require_passed: bool = False,
) -> dict[str, object]:
    """Parse and validate exact P12-CJ-1 object-result bytes."""

    if not isinstance(raw, bytes) or len(raw) > 1_048_576:
        raise HistoricalInventoryError("object result bytes are missing or oversized")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except HistoricalInventoryError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise HistoricalInventoryError("object result is not one JSON document") from exc
    if not isinstance(value, dict) or raw != canonical_json(value):
        raise HistoricalInventoryError("object result is not exact P12-CJ-1 canonical JSON")
    validate_object_result(
        value,
        expected_object=expected_object,
        expected_inventory_digest=expected_inventory_digest,
        expected_digest=expected_digest,
        require_passed=require_passed,
    )
    return value


def validate_predecessor_result(
    current_object: str,
    *,
    object_result_bytes: bytes,
    object_result_digest_value: str,
    inventory_digest: str,
) -> dict[str, object]:
    """Verify the immediate predecessor's exact bytes without re-execution."""

    predecessor = PREDECESSOR_OBJECTS.get(current_object)
    if predecessor is None:
        raise HistoricalInventoryError("historical object has no immediate predecessor result")
    predecessor_items = [
        item
        for item in CANONICAL_INVENTORY
        if item["object"] == current_object and item["command_kind"] == "predecessor_result"
    ]
    if len(predecessor_items) != 1 or predecessor_items[0]["expected"] != {
        "predecessor_object": predecessor,
        "rerun_count": 0,
        "status": "passed",
    }:
        raise HistoricalInventoryError("predecessor-result inventory binding drifted")
    return validate_object_result_bytes(
        object_result_bytes,
        expected_object=predecessor,
        expected_inventory_digest=inventory_digest,
        expected_digest=object_result_digest_value,
        require_passed=True,
    )


def check_historical_inventory(root: Path) -> dict[str, object]:
    root = root.resolve()
    items = load_inventory(root)
    entrypoint_count = _verify_git_objects(root, items)
    raw = (root / INVENTORY_PATH).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    blob = _git(root, "hash-object", INVENTORY_PATH)
    try:
        committed_blob = _git(root, "rev-parse", f"HEAD:{INVENTORY_PATH}")
    except HistoricalInventoryError:
        committed_blob = ""
    return {
        "accepted_acceptance_gate_count": 129,
        "accepted_gate_set_difference": list(EXCLUDED_GATE_IDS),
        "evidence_anchor_count": ITEM_COUNTS["evidence_anchor"],
        "excluded_acceptance_gate_count": ITEM_COUNTS["excluded_acceptance_gate"],
        "excluded_gate_ids": list(EXCLUDED_GATE_IDS),
        "gate": "p12_portable_historical_inventory",
        "gate_non_null_entrypoint_count": 110,
        "gate_null_entrypoint_count": 19,
        "historical_python_test_count": 616,
        "included_acceptance_gate_count": ITEM_COUNTS["included_acceptance_gate"],
        "inventory_blob": blob,
        "inventory_committed": committed_blob == blob,
        "inventory_digest": f"sha256:{digest}",
        "inventory_non_null_entrypoint_count": 110,
        "inventory_null_entrypoint_count": 41,
        "inventory_path": INVENTORY_PATH,
        "inventory_sha256": digest,
        "object_result_schema": OBJECT_RESULT_SCHEMA,
        "object_order": list(OBJECT_ORDER),
        "partition_counts": PARTITION_COUNTS,
        "setup_count": ITEM_COUNTS["setup"],
        "status": "passed",
        "total_item_count": ITEM_COUNTS["total"],
        "unique_entrypoint_count": entrypoint_count,
    }


def canonical_inventory_copy() -> list[dict[str, Any]]:
    return list(deepcopy(CANONICAL_INVENTORY))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--print-canonical", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        if arguments.print_canonical:
            sys.stdout.buffer.write(canonical_json(CANONICAL_INVENTORY))
            return 0
        result = check_historical_inventory(Path(arguments.root))
    except HistoricalInventoryError as exc:
        print(f"P12 historical inventory failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
