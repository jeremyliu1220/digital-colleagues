# SPDX-License-Identifier: Apache-2.0

"""Create a sanitized digest fingerprint for the pre-existing parent source tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Protocol

DEFAULT_SOURCE_LABEL = "digital-colleague-runtime-research"
DEFAULT_SOURCE_REVISION = "dea9a9accc82fbedd35deb7117dcb5173223cf44"
DEFAULT_EXCLUDED_SUBTREE = "digital-colleagues"


class FingerprintError(RuntimeError):
    """A sanitized fingerprint failure."""


class _Hasher(Protocol):
    def update(self, value: bytes) -> None: ...


def _safe_relative(value: str) -> str:
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or not candidate.parts or ".." in candidate.parts:
        raise FingerprintError("the authorized target subtree must be repository-relative")
    return candidate.as_posix().rstrip("/")


def _git(source: Path, *arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=source,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise FingerprintError("source Git inspection failed") from exc
    return completed.stdout


def _framed(hasher: _Hasher, value: bytes) -> None:
    """Hash one byte string without ambiguous concatenation."""

    hasher.update(len(value).to_bytes(8, byteorder="big"))
    hasher.update(value)


def _fingerprint_worktree_entries(source: Path, paths: bytes) -> tuple[int, str]:
    """Aggregate path, type, mode, and content without returning any individual value."""

    raw_paths = paths.split(b"\0")
    if raw_paths and raw_paths[-1] == b"":
        raw_paths.pop()
    if len(raw_paths) != len(set(raw_paths)):
        raise FingerprintError("source worktree enumeration was unsafe")

    aggregate = hashlib.sha256()
    for raw_path in sorted(raw_paths):
        parts = raw_path.split(b"/")
        if (
            not raw_path
            or raw_path.startswith(b"/")
            or any(part in {b"", b".", b".."} for part in parts)
        ):
            raise FingerprintError("source worktree enumeration was unsafe")
        candidate = source / os.fsdecode(raw_path)
        try:
            before = candidate.lstat()
            entry = hashlib.sha256()
            _framed(entry, raw_path)
            _framed(entry, str(stat.S_IMODE(before.st_mode)).encode("ascii"))
            if stat.S_ISREG(before.st_mode):
                _framed(entry, b"regular-file")
                with candidate.open("rb") as stream:
                    while chunk := stream.read(1024 * 1024):
                        entry.update(chunk)
                after = candidate.lstat()
                stable = (
                    before.st_dev,
                    before.st_ino,
                    before.st_mode,
                    before.st_size,
                    before.st_mtime_ns,
                ) == (
                    after.st_dev,
                    after.st_ino,
                    after.st_mode,
                    after.st_size,
                    after.st_mtime_ns,
                )
                if not stable:
                    raise FingerprintError("source worktree changed during inspection")
            elif stat.S_ISLNK(before.st_mode):
                _framed(entry, b"symbolic-link")
                _framed(entry, os.fsencode(os.readlink(candidate)))
            else:
                raise FingerprintError("source worktree contains an unsupported entry")
        except FingerprintError:
            raise
        except (OSError, ValueError) as exc:
            raise FingerprintError("source worktree content inspection failed") from exc
        _framed(aggregate, entry.digest())
    return len(raw_paths), aggregate.hexdigest()


def fingerprint_source_tree(
    source: Path,
    *,
    source_label: str,
    source_revision: str,
    excluded_subtree: str,
) -> dict[str, object]:
    if not source.is_dir():
        raise FingerprintError("source checkout is unavailable")

    exclusion = _safe_relative(excluded_subtree)
    _git(source, "cat-file", "-e", f"{source_revision}^{{commit}}")
    head_revision = _git(source, "rev-parse", "HEAD").decode("ascii").strip()
    pathspec = ["--", ".", f":(exclude){exclusion}"]
    status = _git(
        source,
        "status",
        "--porcelain=v2",
        "-z",
        "--ignored=matching",
        "--untracked-files=all",
        *pathspec,
    )
    tracked_diff = _git(source, "diff", "--binary", "--no-ext-diff", *pathspec)
    index_diff = _git(
        source,
        "diff",
        "--cached",
        "--binary",
        "--no-ext-diff",
        *pathspec,
    )
    untracked_paths = _git(
        source,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
        *pathspec,
    )
    ignored_paths = _git(
        source,
        "ls-files",
        "--others",
        "--ignored",
        "--exclude-standard",
        "-z",
        *pathspec,
    )
    untracked_entry_count, untracked_state_digest = _fingerprint_worktree_entries(
        source, untracked_paths
    )
    ignored_entry_count, ignored_state_digest = _fingerprint_worktree_entries(source, ignored_paths)

    return {
        "schema_version": 2,
        "source_label": source_label,
        "source_revision": source_revision,
        "head_revision": head_revision,
        "scope": "parent_source_excluding_authorized_target_subtree",
        "excluded_repo_relative_subtree": exclusion,
        "status_entry_count": status.count(b"\0"),
        "status_digest": hashlib.sha256(status).hexdigest(),
        "tracked_diff_digest": hashlib.sha256(tracked_diff).hexdigest(),
        "index_diff_digest": hashlib.sha256(index_diff).hexdigest(),
        "untracked_entry_count": untracked_entry_count,
        "untracked_state_digest": untracked_state_digest,
        "ignored_entry_count": ignored_entry_count,
        "ignored_state_digest": ignored_state_digest,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print a path-free source worktree fingerprint as JSON."
    )
    parser.add_argument("--source", required=True, help="Runtime source checkout location.")
    parser.add_argument("--source-label", default=DEFAULT_SOURCE_LABEL)
    parser.add_argument("--revision", default=DEFAULT_SOURCE_REVISION)
    parser.add_argument("--exclude-relative", default=DEFAULT_EXCLUDED_SUBTREE)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        result = fingerprint_source_tree(
            Path(arguments.source),
            source_label=arguments.source_label,
            source_revision=arguments.revision,
            excluded_subtree=arguments.exclude_relative,
        )
    except FingerprintError as exc:
        print(f"fingerprint failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
