# SPDX-License-Identifier: Apache-2.0

"""Run the complete P8 reproducible release and operational Golden Path."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p4_compose_runtime import ComposeRuntimeError
from scripts.check_p8_compose_runtime import check_compose_runtime
from scripts.check_p8_reproducibility import check_reproducibility
from scripts.p8_release_support import ReleaseError


def check_golden_path(root: Path) -> dict[str, object]:
    reproducibility = check_reproducibility(root)
    runtime = check_compose_runtime(root)
    cleanup = runtime.get("cleanup")
    if (
        reproducibility.get("status") != "passed"
        or runtime.get("status") != "passed"
        or not isinstance(cleanup, dict)
        or cleanup.get("passed") is not True
    ):
        raise ComposeRuntimeError("P8 Golden Path prerequisite did not pass")
    return {
        "schema_version": 1,
        "gate": "p8_golden_path_clean",
        "status": "passed",
        "claim": "v0_1_local_reference_release_candidate",
        "source_commit": runtime["release_source_commit"],
        "release_artifact_count": reproducibility["artifact_count"],
        "double_build_byte_equal": True,
        "candidate_default_compose": "deterministic_reference",
        "health_authenticated_smoke": "passed",
        "first_release_transition": runtime["first_release_transition"],
        "durable_fixture": runtime["durable_fixture"],
        "online_backup": runtime["online_backup"],
        "restore_restart_state_equal": runtime["fresh_restart_state_equal"],
        "diagnostics_redaction": runtime["diagnostics_redaction"],
        "external_provider_calls": 0,
        "cleanup": cleanup,
        "evidence_class": "synthetic_offline",
        "human_evaluation": "not_evaluated",
        "live_provider_evidence": "not_evaluated",
        "five_minute_target": "not_evaluated",
        "claim_exclusions": [
            "formal_release_or_publication",
            "production_readiness",
            "production_security_or_privacy",
            "enterprise_iam_or_tenancy",
            "named_provider_compatibility",
            "real_message_delivery",
            "human_evaluation",
            "five_minute_target",
            "post_v0_1_capabilities",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the P8 operations Golden Path.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_golden_path(Path(arguments.root).resolve())
    except (OSError, ComposeRuntimeError, ReleaseError) as exc:
        safe = (
            str(exc)
            .replace(str(Path(arguments.root).resolve()), "<project>")
            .replace(str(Path.home()), "<home>")
        )
        print(f"P8 Golden Path check failed: {safe}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
