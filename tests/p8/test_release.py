# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast

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


class P8ReleaseTests(unittest.TestCase):
    def test_supply_chain_is_complete_sorted_hash_pinned_and_notice_scoped(self) -> None:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        first = build_supply_chain_inventory(ROOT, commit)
        second = build_supply_chain_inventory(ROOT, commit)
        self.assertEqual(first, second)
        records = cast(list[dict[str, Any]], first["records"])
        self.assertEqual(len(records), 242)
        identities = [(item["ecosystem"], item["name"], item["version"]) for item in records]
        self.assertEqual(identities, sorted(identities))
        self.assertEqual(len(identities), len(set(identities)))
        self.assertTrue(all(item["declared_license"] for item in records))
        self.assertTrue(all(item["immutable_references"] for item in records))
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
