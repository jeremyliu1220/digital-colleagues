# SPDX-License-Identifier: Apache-2.0

"""Check P11 Studio translation, lifecycle, error, and accessibility contracts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.p11_gate_support import GateError  # noqa: E402

KEY = re.compile(r'^\s*"([a-z0-9_.-]+)":', re.MULTILINE)
PLACEHOLDER = re.compile(r"{{([a-z0-9_]+)}}")


def _values(source: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in KEY.finditer(source):
        start = match.end()
        end = source.find('\n  "', start)
        if end < 0:
            end = len(source)
        values[match.group(1)] = source[start:end]
    return values


def check_studio(root: Path) -> dict[str, object]:
    en = _values((root / "studio/src/locales/en-US.ts").read_text())
    zh = _values((root / "studio/src/locales/zh-TW.ts").read_text())
    if set(en) != set(zh):
        raise GateError("P11 Studio locale key sets differ")
    if any(not value.strip() for value in (*en.values(), *zh.values())):
        raise GateError("P11 Studio translation is blank")
    for key in en:
        if set(PLACEHOLDER.findall(en[key])) != set(PLACEHOLDER.findall(zh[key])):
            raise GateError("P11 Studio translation placeholders differ")
    required = {
        "registry.validate",
        "registry.provenance",
        "registry.verification_result",
        "registry.signer",
        "registry.repository",
        "registry.workflow",
        "registry.build_identity",
        "registry.signer_digest",
        "registry.artifact_digest",
        "registry.archive_digest",
        "registry.source_ref",
        "registry.source_digest",
        "registry.predicate_type",
        "registry.attestation_origin_only",
        "registry.trust_independent",
        "registry.authority_unbound",
        "registry.requested",
        "registry.granted",
        "registry.trust",
        "registry.revoke",
        "registry.install",
        "registry.register",
        "registry.create_draft",
        "registry.select_capabilities",
        "registry.confirm_extra",
        "registry.review",
        "registry.confirm",
        "registry.activate",
        "registry.pause",
        "registry.block",
        "registry.retire",
        "registry.upgrade",
        "registry.rollback",
        "registry.select",
        "registry.audit",
        "registry.drafts",
    }
    if not required <= set(en):
        raise GateError("P11 Studio control translations are incomplete")
    component = (root / "studio/src/AgentRegistry.tsx").read_text()
    for marker in (
        "aria-live",
        "disabled={Boolean(busy)}",
        "permission_diff",
        "active_limit",
        "AuthoritySelection",
        "signer_digest",
        "attestation_origin_only",
        "authority_unbound",
    ):
        if marker not in component:
            raise GateError("P11 Studio accessibility or lifecycle marker is absent")
    return {
        "schema_version": 1,
        "gate": "p11_studio",
        "status": "passed",
        "locale_key_count": len(en),
        "locale_mismatch_count": 0,
        "placeholder_mismatch_count": 0,
        "required_control_count": len(required),
        "aria_live_count": component.count("aria-live"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        result = check_studio(Path(args.root).resolve())
    except (OSError, GateError) as exc:
        print(f"P11 Studio check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
