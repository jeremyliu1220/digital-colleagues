# SPDX-License-Identifier: Apache-2.0

"""Build the complete P8 candidate twice and compare every declared artifact byte."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.p8_release_support import ARTIFACT_NAMES, ReleaseError, build_candidate


def check_reproducibility(root: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="digital-colleagues-p8-reproducibility-") as name:
        temporary = Path(name)
        first = build_candidate(root, temporary / "build-a", python=Path(sys.executable))
        second = build_candidate(root, temporary / "build-b", python=Path(sys.executable))
        first_digests = dict(first.artifacts)
        second_digests = dict(second.artifacts)
        if first.source_commit != second.source_commit or first_digests != second_digests:
            raise ReleaseError("release_reproducibility_mismatch")
        if set(first_digests) != set(ARTIFACT_NAMES):
            raise ReleaseError("release_reproducibility_incomplete")
        result = {
            "schema_version": 1,
            "gate": "p8_reproducibility_clean",
            "status": "passed",
            "source_commit": first.source_commit,
            "independent_build_workspaces": 2,
            "artifact_count": len(first_digests),
            "artifact_digests": dict(sorted(first_digests.items())),
            "byte_equal_artifacts": sorted(first_digests),
            "normalized": [
                "ordering",
                "mtime",
                "owner_group",
                "file_modes",
                "locale",
                "timezone",
                "gzip_metadata",
                "archive_metadata",
            ],
            "oci_claim": "immutable_inputs_and_runtime_content_only",
            "raw_oci_image_reproducibility_claimed": False,
            "repository_residue": 0,
        }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P8 release reproducibility.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_reproducibility(Path(arguments.root).resolve())
    except (OSError, ReleaseError) as exc:
        safe = str(exc).replace(str(Path(arguments.root).resolve()), "<project>")
        print(f"P8 reproducibility check failed: {safe}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
