# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest

from scripts.check_p10_compatibility import check_compatibility, route_inventory
from tests.p10.fixtures import ROOT


class P10CompatibilityTests(unittest.TestCase):
    def test_metadata_mapping_and_route_inventory_pass(self) -> None:
        result = check_compatibility(ROOT)
        self.assertEqual(result["python_version"], "0.2.0.dev0")
        self.assertEqual(result["display_version"], "0.2.0-dev.0")
        self.assertEqual(result["route_method_pair_count"], 40)
        self.assertEqual(result["route_drift_count"], 0)

    def test_route_parser_fixes_method_and_path(self) -> None:
        source = '@app.post("/fixed")\ndef route():\n    pass\n'
        self.assertEqual(route_inventory(source), {("POST", "/fixed")})

    def test_route_removal_and_milestone_metadata_are_detectable(self) -> None:
        source = (ROOT / "src/digital_colleagues/api/p6_app.py").read_text(encoding="utf-8")
        routes = route_inventory(source)
        changed = source.replace('@app.get("/governance/rbac")', '@app.get("/removed")', 1)
        self.assertNotEqual(route_inventory(changed), routes)
        for relative in (
            "src/digital_colleagues/api/app.py",
            "src/digital_colleagues/api/p4_app.py",
            "src/digital_colleagues/local/runtime.py",
        ):
            current = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotRegex(current, r'(?:title|version)\s*=\s*"[^\"]*P[3-7]')


if __name__ == "__main__":
    unittest.main()
