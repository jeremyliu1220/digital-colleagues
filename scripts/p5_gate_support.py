# SPDX-License-Identifier: Apache-2.0

"""Shared sanitized unittest execution for focused P5 mechanical gates."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


class FocusedGateError(RuntimeError):
    """A focused P5 unittest boundary did not pass without exceptions."""


def run_focused_tests(root: Path, *test_names: str) -> int:
    completed = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "-v", *test_names],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    sanitized = completed.stdout.replace(str(root), "<project>").replace(str(Path.home()), "<home>")
    match = re.search(r"Ran (\d+) tests? in", sanitized)
    if (
        completed.returncode != 0
        or match is None
        or int(match.group(1)) < 1
        or "skipped=" in sanitized
        or "unexpected success" in sanitized.lower()
    ):
        raise FocusedGateError("focused unittest boundary failed\n" + sanitized[-8_000:])
    return int(match.group(1))
