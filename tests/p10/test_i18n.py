# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_p10_i18n import check_i18n, parse_dictionary
from scripts.p10_gate_support import GateError
from tests.p10.fixtures import ROOT, copy_paths


class P10I18nTests(unittest.TestCase):
    def test_key_and_placeholder_parity_passes(self) -> None:
        result = check_i18n(ROOT)
        key_count = result["translation_key_count"]
        if not isinstance(key_count, int):
            self.fail("translation key count is not an integer")
        self.assertGreater(key_count, 100)
        self.assertEqual(result["missing_key_count"], 0)
        self.assertEqual(result["unknown_locale_fallback"], "en-US")

    def test_blank_and_duplicate_translation_values_fail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="dc-p10-i18n-") as name:
            path = Path(name) / "locale.ts"
            path.write_text('  "key": "",\n', encoding="utf-8")
            with self.assertRaisesRegex(GateError, "translation_value_invalid"):
                parse_dictionary(path)
            path.write_text('  "key": "a",\n  "key": "b",\n', encoding="utf-8")
            with self.assertRaisesRegex(GateError, "translation_key_duplicate"):
                parse_dictionary(path)

    def test_missing_extra_wrong_type_and_placeholder_mismatch_fail(self) -> None:
        paths = (
            "studio/src/App.tsx",
            "studio/src/i18n.ts",
            "studio/src/locales/en-US.ts",
            "studio/src/locales/zh-TW.ts",
        )
        with tempfile.TemporaryDirectory(prefix="dc-p10-i18n-parity-") as name:
            temporary = Path(name)
            for label, old, new in (
                ("missing", '  "common.empty": "尚無資料",\n', ""),
                ("extra", "};", '  "extra.key": "額外",\n};'),
                ("wrong_type", '  "common.empty": "尚無資料",', '  "common.empty": 7,'),
                (
                    "placeholder",
                    "{{revision}}",
                    "{{different_revision}}",
                ),
            ):
                root = copy_paths(temporary / label, *paths)
                target = root / "studio/src/locales/zh-TW.ts"
                target.write_text(
                    target.read_text(encoding="utf-8").replace(old, new, 1), encoding="utf-8"
                )
                with self.subTest(label=label), self.assertRaises(GateError):
                    check_i18n(root)


if __name__ == "__main__":
    unittest.main()
