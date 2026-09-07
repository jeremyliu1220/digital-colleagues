# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_p10_security import check_security
from scripts.p10_gate_support import GateError
from tests.p10.fixtures import ROOT, copy_paths


class P10SecurityTests(unittest.TestCase):
    def test_filesystem_filevault_and_secret_boundaries_pass(self) -> None:
        result = check_security(ROOT)
        self.assertEqual(result["secret_leak_count"], 0)
        self.assertFalse(result["filevault_off_live_ready"])
        self.assertFalse(result["filevault_unknown_live_ready"])

    def test_eval_secret_mount_and_wrong_mode_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="dc-p10-security-") as name:
            temp = copy_paths(Path(name), "dc", "compose.p10.yaml")
            launcher = temp / "dc"
            launcher.write_text(
                launcher.read_text(encoding="utf-8") + "\neval unsafe\n", encoding="utf-8"
            )
            with self.assertRaises(GateError):
                check_security(temp)
            launcher.write_bytes((ROOT / "dc").read_bytes())
            launcher.chmod(0o644)
            with self.assertRaisesRegex(GateError, "launcher_mode_invalid"):
                check_security(temp)

    def test_studio_secret_mount_and_credential_material_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="dc-p10-secret-mount-") as name:
            temp = copy_paths(Path(name), "dc", "compose.p10.yaml")
            compose = temp / "compose.p10.yaml"
            original = compose.read_text(encoding="utf-8")
            compose.write_text(
                original.replace(
                    "  studio:\n",
                    "  studio:\n    volumes:\n      - /private/secrets:/secrets:ro\n",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(GateError, "studio_secret_or_state_mount_forbidden"):
                check_security(temp)
            compose.write_text(original + "\n# OPENAI_API_KEY\n", encoding="utf-8")
            with self.assertRaisesRegex(GateError, "secret_material_in_compose"):
                check_security(temp)


if __name__ == "__main__":
    unittest.main()
