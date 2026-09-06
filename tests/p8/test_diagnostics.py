# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import contextlib
import io
import json
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from digital_colleagues.operations.__main__ import main
from digital_colleagues.operations.diagnostics import (
    DiagnosticsError,
    create_diagnostics_bundle,
)
from tests.p8.fixtures import ROOT, create_full_state, write_release_manifest


class P8DiagnosticsTests(unittest.TestCase):
    def test_bundle_is_exact_allowlisted_bounded_and_canary_free(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-diagnostics-") as name:
            root = Path(name)
            database = root / "state.sqlite"
            release_manifest = write_release_manifest(root)
            harness, _ = create_full_state(database)
            harness.store.close()
            credential = "support-" + "credential-canary-value"
            private_marker = "private-" + "payload-canary-value"
            local_path = str(root / "sensitive-local-location")
            bundle = root / "support-bundle.tar.gz"
            with patch.dict(
                os.environ,
                {
                    "DC_ADAPTER_CREDENTIAL": credential,
                    "DC_PRIVATE_PAYLOAD": private_marker,
                    "DC_LOCAL_PATH": local_path,
                },
            ):
                report = create_diagnostics_bundle(
                    database,
                    bundle,
                    release_manifest=release_manifest,
                    migrations_directory=ROOT / "migrations",
                    causal_identifiers=("correlation-synthetic", "proposal-synthetic"),
                )
            self.assertEqual((report.status, report.causal_digest_count), ("created", 2))
            self.assertEqual(bundle.stat().st_mode & 0o777, 0o600)
            raw = bundle.read_bytes()
            for forbidden in (credential, private_marker, local_path, str(Path.home())):
                self.assertNotIn(forbidden.encode(), raw)
            with tarfile.open(bundle, mode="r:gz") as archive:
                self.assertEqual([item.name for item in archive.getmembers()], ["diagnostics.json"])
                handle = archive.extractfile("diagnostics.json")
                assert handle is not None
                document = json.load(handle)
            self.assertEqual(
                set(document),
                {
                    "schema_version",
                    "bundle_format_version",
                    "release",
                    "database",
                    "environment",
                    "health",
                    "causal_identifier_digests",
                    "evidence_class",
                },
            )
            self.assertEqual(document["database"]["migration_checksums"], "verified")
            self.assertEqual(document["database"]["integrity"], "passed")
            self.assertEqual(len(document["causal_identifier_digests"]), 2)
            serialized = json.dumps(document)
            for forbidden in (credential, private_marker, local_path, str(Path.home())):
                self.assertNotIn(forbidden, serialized)

    def test_diagnostics_rejects_unbounded_ids_existing_output_and_path_errors_are_finite(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="digital-colleagues-p8-diagnostic-refusal-"
        ) as name:
            root = Path(name)
            database = root / "state.sqlite"
            release_manifest = write_release_manifest(root)
            harness, _ = create_full_state(database)
            harness.store.close()
            output = root / "bundle.tar.gz"
            with self.assertRaisesRegex(DiagnosticsError, "causal_identifier_limit"):
                create_diagnostics_bundle(
                    database,
                    output,
                    release_manifest=release_manifest,
                    migrations_directory=ROOT / "migrations",
                    causal_identifiers=tuple(str(value) for value in range(17)),
                )
            output.write_bytes(b"preserve")
            with self.assertRaisesRegex(DiagnosticsError, "diagnostics_destination_exists"):
                create_diagnostics_bundle(
                    database,
                    output,
                    release_manifest=release_manifest,
                    migrations_directory=ROOT / "migrations",
                )
            stdout = io.StringIO()
            stderr = io.StringIO()
            missing = root / "private" / "state.sqlite"
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(
                    [
                        "diagnostics",
                        "--database",
                        str(missing),
                        "--output",
                        str(root / "unused.tar.gz"),
                        "--release-manifest",
                        str(release_manifest),
                        "--migrations",
                        str(ROOT / "migrations"),
                    ]
                )
            self.assertEqual(code, 2)
            combined = stdout.getvalue() + stderr.getvalue()
            self.assertNotIn(str(root), combined)
            self.assertEqual(json.loads(stderr.getvalue())["category"], "database_source_invalid")
