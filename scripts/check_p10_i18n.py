# SPDX-License-Identifier: Apache-2.0

"""Validate complete zh-TW/en-US key parity and translated Studio chrome."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.p10_gate_support import GateError, emit_main

ENTRY = re.compile(
    r'^\s*"([^"]+)":\s*("(?:[^"\\]|\\.)*")\s*,?\s*$',
    re.MULTILINE,
)
PLACEHOLDER = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")


def parse_dictionary(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in ENTRY.finditer(path.read_text(encoding="utf-8")):
        key = match.group(1)
        if key in values:
            raise GateError("translation_key_duplicate")
        value = json.loads(match.group(2))
        if not isinstance(value, str) or not value.strip():
            raise GateError("translation_value_invalid")
        values[key] = value
    if not values:
        raise GateError("translation_dictionary_empty")
    return values


def check_i18n(root: Path) -> dict[str, object]:
    english = parse_dictionary(root / "studio/src/locales/en-US.ts")
    chinese = parse_dictionary(root / "studio/src/locales/zh-TW.ts")
    if set(english) != set(chinese):
        raise GateError("translation_key_parity_invalid")
    for key in english:
        if sorted(PLACEHOLDER.findall(english[key])) != sorted(PLACEHOLDER.findall(chinese[key])):
            raise GateError("translation_placeholder_parity_invalid")
    app = (root / "studio/src/App.tsx").read_text(encoding="utf-8")
    used = set(re.findall(r'(?<![A-Za-z0-9_.])t\("([^"]+)"', app))
    missing = used - set(english)
    if missing:
        raise GateError("translation_key_usage_missing")
    visible_banned = (
        "P6 local governance control plane",
        "P6 under verification",
        "P7 optional adapters",
    )
    if any(
        value in app or value in "\n".join(english.values()) or value in "\n".join(chinese.values())
        for value in visible_banned
    ):
        raise GateError("user_visible_milestone_branding")
    raw_visible = {
        value.strip()
        for value in re.findall(r">\s*([A-Za-z\u4e00-\u9fff][^<>{}\n]*)\s*<", app)
        if value.strip()
    }
    if raw_visible - {"English", "Promise", "繁體中文"}:
        raise GateError("untranslated_studio_copy")
    if re.search(r"api(?:<[^>]+>)?\([^)]*\bt\(", app, re.DOTALL) or re.search(
        r"(?:role|effect|permission|schema_version|idempotency_key)\s*:\s*t\(", app
    ):
        raise GateError("locale_dependent_api_or_authority")
    module = (root / "studio/src/i18n.ts").read_text(encoding="utf-8")
    if 'return "en-US"' not in module or "translation_placeholder_mismatch" not in module:
        raise GateError("locale_fallback_or_validation_missing")
    return {
        "schema_version": 1,
        "gate": "p10_i18n_clean",
        "locales": ["en-US", "zh-TW"],
        "translation_key_count": len(english),
        "missing_key_count": 0,
        "extra_key_count": 0,
        "placeholder_mismatch_count": 0,
        "unknown_locale_fallback": "en-US",
    }


def main(argv: list[str] | None = None) -> int:
    return emit_main(check_i18n, argv, __doc__)


if __name__ == "__main__":
    raise SystemExit(main())
