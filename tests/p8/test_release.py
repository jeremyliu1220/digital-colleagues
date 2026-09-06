# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast

from scripts.check_p8_release import (
    PUBLIC_STATUS_PATHS,
    _release_documents,
)
from scripts.check_p8_supply_chain import SupplyChainError, check_supply_chain
from scripts.p8_release_support import (
    ARTIFACT_NAMES,
    ReleaseError,
    _npm_package_name,
    _source_entries,
    build_candidate,
    build_supply_chain_inventory,
)
from tests.p8.fixtures import ROOT


def _public_status_fixture(directory: Path) -> Path:
    root = directory / "repository"
    subprocess.run(["git", "clone", "--quiet", "--shared", str(ROOT), str(root)], check=True)
    for relative in PUBLIC_STATUS_PATHS:
        shutil.copyfile(ROOT / relative, root / relative)
    return root


def _replace(root: Path, relative: str, old: str, new: str) -> None:
    path = root / relative
    document = path.read_text(encoding="utf-8")
    if old not in document:
        raise AssertionError(f"fixture text missing from {relative}: {old}")
    path.write_text(document.replace(old, new, 1), encoding="utf-8")


class P8ReleaseTests(unittest.TestCase):
    def test_public_post_merge_status_passes_without_rejecting_historical_terms(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-status-") as name:
            root = _public_status_fixture(Path(name))
            self.assertIn(
                "development complete,\nawaiting independent acceptance",
                (root / "docs/p8/acceptance.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                '"status": "development_complete_awaiting_independent_acceptance"',
                (root / "artifacts/p8/summary.json").read_text(encoding="utf-8"),
            )
            _release_documents(root)

    def test_readme_pre_acceptance_status_fails_real_release_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-readme-stale-") as name:
            root = _public_status_fixture(Path(name))
            _replace(
                root,
                "README.md",
                "P8 passed independent acceptance",
                "P8 development complete, awaiting independent acceptance",
            )
            with self.assertRaises(ReleaseError):
                _release_documents(root)

    def test_roadmap_rejected_or_p7_checkpoint_status_fails_real_release_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-roadmap-stale-") as name:
            temporary = Path(name)
            for label, old, new in (
                (
                    "not-accepted",
                    "P8 passed independent acceptance",
                    "P8 is not accepted and P8 is not merged",
                ),
                (
                    "p7-checkpoint",
                    "Current checkpoint:\n\n- P8 passed independent acceptance",
                    "Current checkpoint:\n\n- P7 has passed independent acceptance",
                ),
            ):
                root = _public_status_fixture(temporary / label)
                _replace(root, "docs/roadmap.md", old, new)
                with self.assertRaises(ReleaseError, msg=label):
                    _release_documents(root)

    def test_capability_matrix_pre_acceptance_status_fails_real_release_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-matrix-stale-") as name:
            root = _public_status_fixture(Path(name))
            _replace(
                root,
                "docs/product/capability-matrix.md",
                "| Upgrade, backup, restore, and release rollback | Yes | P8 accepted main baseline |",
                "| Upgrade, backup, restore, and release rollback | Yes | "
                "P8 development complete, awaiting independent acceptance |",
            )
            with self.assertRaises(ReleaseError):
                _release_documents(root)

    def test_release_checklist_development_branch_requirement_fails_real_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-checklist-stale-") as name:
            root = _public_status_fixture(Path(name))
            _replace(
                root,
                "docs/p8/release-checklist.md",
                "Release work starts from a clean `main` containing accepted P8 commit",
                "HEAD is on `codex/p8-release-readiness`, clean, and contains accepted P8 commit",
            )
            with self.assertRaises(ReleaseError):
                _release_documents(root)

    def test_missing_unpublished_limitation_fails_real_release_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-release-limit-") as name:
            root = _public_status_fixture(Path(name))
            _replace(root, "README.md", "no tag has been created", "a tag has been created")
            with self.assertRaises(ReleaseError):
                _release_documents(root)

    def test_formal_release_production_and_live_provider_overclaims_fail_real_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-overclaim-") as name:
            temporary = Path(name)
            cases = (
                (
                    "formal-release",
                    "no tag has been created",
                    "P8 is formally released and a tag has been created",
                ),
                ("production", "It is not production-ready", "P8 is production-ready"),
                (
                    "live-provider",
                    "Human evaluation, live-provider evidence",
                    "P8 is live-provider accepted; Human evaluation and live-provider evidence",
                ),
            )
            for label, old, new in cases:
                root = _public_status_fixture(temporary / label)
                _replace(root, "README.md", old, new)
                with self.assertRaises(ReleaseError, msg=label):
                    _release_documents(root)

    def test_supply_chain_is_complete_sorted_hash_pinned_and_notice_scoped(self) -> None:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        first = build_supply_chain_inventory(ROOT, commit)
        second = build_supply_chain_inventory(ROOT, commit)
        self.assertEqual(first, second)
        records = cast(list[dict[str, Any]], first["records"])
        self.assertEqual(len(records), 243)
        identities = [(item["ecosystem"], item["name"], item["version"]) for item in records]
        self.assertEqual(identities, sorted(identities))
        self.assertEqual(len(identities), len(set(identities)))
        self.assertTrue(all(item["declared_license"] for item in records))
        self.assertTrue(all(item["immutable_references"] for item in records))
        network_guard = [
            item
            for item in records
            if item["ecosystem"] == "oci" and item["name"] == "docker.io/library/busybox"
        ]
        self.assertEqual(len(network_guard), 1)
        self.assertEqual(network_guard[0]["version"], "1.37.0-glibc")
        self.assertEqual(
            network_guard[0]["immutable_references"],
            ["sha256:4279d9b47df4c1b02d80efd8d02cd59b3a8182c1e785a4ff3f6983bee19dc8b0"],
        )
        bundled = [item for item in records if item["included_in_release_artifact"]]
        self.assertEqual({item["name"] for item in bundled}, {"react", "react-dom", "scheduler"})
        self.assertEqual(check_supply_chain(ROOT)["gate"], "p8_supply_chain_clean")

    def test_nested_npm_package_identities_are_exact_and_scoped_names_survive(self) -> None:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        records = cast(list[dict[str, Any]], build_supply_chain_inventory(ROOT, commit)["records"])
        identities = {
            (item["name"], item["version"]) for item in records if item["ecosystem"] == "npm"
        }
        self.assertIn(("eslint-visitor-keys", "3.4.3"), identities)
        self.assertIn(("ignore", "7.0.6"), identities)
        self.assertIn(("semver", "7.8.5"), identities)
        self.assertNotIn(
            ("@eslint-community/eslint-utils/node_modules/eslint-visitor-keys", "3.4.3"),
            identities,
        )
        self.assertEqual(
            _npm_package_name("node_modules/parent/node_modules/@scope/package"),
            "@scope/package",
        )
        for malformed in ("package", "node_modules/@scope", "node_modules/a/b"):
            with self.assertRaisesRegex(ReleaseError, "studio_lock_path_invalid"):
                _npm_package_name(malformed)

    def test_container_host_toolchain_and_os_dependency_drift_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-toolchain-drift-") as name:
            for label, relative, old, new in (
                ("container-node", "studio/Dockerfile", "v24.15.0", "v24.20.0"),
                ("host-node", ".nvmrc", "24.15.0", "24.20.0"),
                (
                    "os-package",
                    "Dockerfile.p7",
                    "RUN python -m pip install",
                    "RUN apt-get install --yes iproute2 && python -m pip install",
                ),
                (
                    "network-guard",
                    "Dockerfile.p7",
                    "BusyBox v1.37.0",
                    "BusyBox v1.36.1",
                ),
            ):
                root = Path(name) / label
                subprocess.run(
                    ["git", "clone", "--quiet", "--shared", str(ROOT), str(root)], check=True
                )
                for source_relative in (
                    "Dockerfile.p7",
                    "release/supply-chain-inputs.json",
                    "studio/Dockerfile",
                    "studio/Dockerfile.p7",
                ):
                    shutil.copyfile(ROOT / source_relative, root / source_relative)
                self.assertEqual(check_supply_chain(root)["gate"], "p8_supply_chain_clean")
                path = root / relative
                content = path.read_text(encoding="utf-8")
                self.assertIn(old, content)
                path.write_text(content.replace(old, new, 1), encoding="utf-8")
                with self.assertRaises(SupplyChainError, msg=label):
                    check_supply_chain(root)

    def test_source_archive_policy_excludes_evidence_and_private_residue(self) -> None:
        entries = _source_entries(
            ROOT, subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        )
        paths = [item[0] for item in entries]
        self.assertTrue(paths)
        self.assertFalse(any(path.startswith("artifacts/") for path in paths))
        for forbidden in ("node_modules", "__pycache__", ".sqlite", ".backup", ".log"):
            self.assertFalse(any(forbidden in path for path in paths), forbidden)
        self.assertEqual(
            ARTIFACT_NAMES,
            (
                "digital-colleagues-0.1.0-source.tar.gz",
                "digital_colleagues-0.1.0-py3-none-any.whl",
                "digital-colleagues-studio-0.1.0.tar.gz",
                "digital-colleagues-sbom-0.1.0.json",
                "digital-colleagues-release-manifest-0.1.0.json",
                "SHA256SUMS",
            ),
        )

    def test_release_builder_refuses_dirty_tree_before_emitting_candidate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-dirty-") as name:
            root = Path(name) / "repository"
            subprocess.run(
                ["git", "clone", "--quiet", "--shared", str(ROOT), str(root)], check=True
            )
            marker = root / "dirty-marker.txt"
            marker.write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(ReleaseError, "release_tree_dirty"):
                build_candidate(root, Path(name) / "output", python=Path("python3"))
            self.assertEqual(list((Path(name) / "output").iterdir()), [])

    def test_release_metadata_versions_and_package_manager_integrity_are_consistent(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        package = json.loads((ROOT / "studio/package.json").read_text(encoding="utf-8"))
        lock = json.loads((ROOT / "studio/package-lock.json").read_text(encoding="utf-8"))
        self.assertIn('version = "0.1.0"', pyproject)
        self.assertEqual(package["version"], "0.1.0")
        self.assertEqual(lock["version"], "0.1.0")
        self.assertEqual(lock["packages"][""]["version"], "0.1.0")
        self.assertRegex(package["packageManager"], r"^npm@11\.12\.1\+sha224\.[0-9a-f]{56}$")
