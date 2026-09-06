# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from scripts.check_p9_rebaseline import DOCUMENTS

ROOT = Path(__file__).resolve().parents[2]


def clone_repository(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "repository"
    subprocess.run(["git", "clone", "--quiet", "--shared", str(ROOT), str(destination)], check=True)
    return destination


def commit_all(root: Path, message: str) -> str:
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
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def copy_documents(directory: Path) -> Path:
    destination = directory / "documents"
    for relative in DOCUMENTS:
        source = ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return destination
