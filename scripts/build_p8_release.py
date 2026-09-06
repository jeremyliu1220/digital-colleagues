# SPDX-License-Identifier: Apache-2.0

"""Build an unpublished v0.1 local reference release candidate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.p8_release_support import ReleaseError, build_candidate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the P8 release candidate locally.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    arguments = parser.parse_args(argv)
    try:
        result = build_candidate(
            arguments.root.resolve(), arguments.output, python=Path(sys.executable)
        )
    except (OSError, ReleaseError) as exc:
        safe = (
            str(exc)
            .replace(str(arguments.root.resolve()), "<project>")
            .replace(str(Path.home()), "<home>")
        )
        print(json.dumps({"status": "failed", "category": safe}, sort_keys=True), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": "candidate_built_not_published",
                "source_commit": result.source_commit,
                "artifacts": [name for name, _ in result.artifacts],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
