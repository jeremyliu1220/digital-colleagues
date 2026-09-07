# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def clone_repository(destination: Path) -> Path:
    root = destination / "repository"
    subprocess.run(["git", "clone", "--quiet", "--shared", str(ROOT), str(root)], check=True)
    return root


def commit_all(root: Path, message: str) -> None:
    subprocess.run(["git", "add", "--all"], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Digital Colleagues Tests",
            "-c",
            "user.email=digital-colleagues-tests.invalid",
            "commit",
            "--quiet",
            "-m",
            message,
        ],
        cwd=root,
        check=True,
    )


def copy_paths(destination: Path, *paths: str) -> Path:
    for relative in paths:
        source = ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(source.stat().st_mode & 0o777)
    return destination
