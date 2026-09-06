# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast

from scripts.check_p8_supply_chain import check_supply_chain
from scripts.p8_release_support import (
    ARTIFACT_NAMES,
    ReleaseError,
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
