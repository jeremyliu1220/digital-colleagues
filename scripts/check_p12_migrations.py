# SPDX-License-Identifier: Apache-2.0

"""Protect migrations 001-008 and validate exact prospective 009-014 ownership."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p12_repository import BASE_COMMIT, P12GateError  # noqa: E402

MANIFEST = (
    "migrations/manifest.json",
    "bfd142486041029bfcc1106ef6ffd4aeb125ed36",
    "3ce53dd7d4e0e7cbc0e9cf4731d6001af8bab57861acfe55184e6f6ab685cc10",
)
MIGRATIONS = (
    (
        "001_initial.sql",
        "c8758dd18f9dea402e368f93e4942a9da65edb60",
        "9a9a9c031bd27072333ee30603bcd6c7e2f33f60e7920f3a69ff251836093c02",
    ),
    (
        "002_runtime_indexes.sql",
        "505485460ce443e80ef2177e2a07aab1218e022a",
        "b0728e3e910e0f0921271b2121308518945968874a667c340d9dc007cbfea11f",
    ),
    (
        "003_timer_triggers.sql",
        "0ff7035e489fda052c6d82c401e5db3b06e8203a",
        "98325116ff022277aee6ee9038083a3866e912c907d08afeb0da4c48f97d7e98",
    ),
    (
        "004_local_authentication.sql",
        "edc24adb566568b397b30c88c610cd309f7666bb",
        "dfe550129f32128eadc685cb54b70feed276ceb3274dbcbd76e214053d77e58b",
    ),
    (
        "005_evaluation_observations.sql",
        "42612d8c47967707fb33b772bf414872f35b5ecc",
        "6649985cf92d9efd378b8b69447357193fdb98eead7d3d23f9bbec1db02b2a61",
    ),
    (
        "006_revisioned_colleague_builder.sql",
        "581e3ba9a75c15002c7bc513b69ea9a920771892",
        "7909da4b0b3eb514222f1fd1068c19eb6e8b98d466a786b76c20ae7999e26bcd",
    ),
    (
        "007_governance_hardening.sql",
        "feb7b658c8e356bf0e717ce69e5896a7c6b00c34",
        "ba572b74ffe7d16ed09ffd58791d7bb23b875806996ec897b2e73c82a593cf9c",
    ),
    (
        "008_agent_packages_and_deployments.sql",
        "a20386ab196e1ab826a0c9a9770999b0e41cb8cf",
        "e7c8b61c54393933e5e4fda06da4a06b11b2b2c1e38bec3163853e41136b0253",
    ),
)
OWNERS = {
    "009": "P13",
    "010": "P14",
    "011": "P15",
    "012": "P16",
    "013": "P17",
    "014": "P18",
    "015": "No owner",
}


def validate_owner_map(owners: dict[str, str]) -> None:
    if owners != OWNERS:
        raise P12GateError("P12 future migration ownership is not exact")


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=root, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise P12GateError("P12 migration Git identity inspection failed")
    return completed.stdout.strip()


def _check_file(root: Path, relative: str, blob: str, sha256: str) -> None:
    path = root / relative
    if path.is_symlink() or not path.exists() or not stat.S_ISREG(os.lstat(path).st_mode):
        raise P12GateError("P12 protected migration identity is not a regular file")
    if _git(root, "rev-parse", f"{BASE_COMMIT}:{relative}") != blob:
        raise P12GateError("P12 protected migration base blob drifted")
    if _git(root, "hash-object", relative) != blob:
        raise P12GateError("P12 protected migration working blob drifted")
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha256:
        raise P12GateError("P12 protected migration SHA-256 drifted")


def check_migrations(root: Path) -> dict[str, object]:
    _check_file(root, *MANIFEST)
    for name, blob, digest in MIGRATIONS:
        _check_file(root, f"migrations/{name}", blob, digest)
    files = tuple(sorted(path.name for path in (root / "migrations").glob("*.sql")))
    if files != tuple(item[0] for item in MIGRATIONS):
        raise P12GateError("P12 migration SQL inventory is not exactly 001-008")
    manifest = json.loads((root / MANIFEST[0]).read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or len(manifest.get("migrations", [])) != 8:
        raise P12GateError("P12 migration manifest does not contain exactly eight entries")
    acceptance = (root / "docs/p12/acceptance.md").read_text(encoding="utf-8")
    for version, owner in OWNERS.items():
        if f"| {version} | {owner} |" not in acceptance:
            raise P12GateError("P12 acceptance migration owner table drifted")
    required = (
        "Exact five-value ProjectContinuationState",
        "admit/reject MemoryAdmissionDecision",
        "without fixing the lifecycle-decision type name or schema",
        "TriggerCorrelation received, matched, ambiguous, consumed and ignored states",
        "Unauthorized; P19 and P20 add no migration",
    )
    if any(marker not in acceptance for marker in required):
        raise P12GateError("P12 migration purpose contract is incomplete")
    validate_owner_map(dict(OWNERS))
    return {
        "schema_version": 1,
        "gate": "p12_migrations",
        "status": "passed",
        "manifest_blob": MANIFEST[1],
        "immutable_migration_count": len(MIGRATIONS),
        "future_owner_count": 6,
        "unauthorized_migration": "015",
        "migration_change_count": 0,
        "manifest_change_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        result = check_migrations(Path(args.root).resolve())
    except (OSError, UnicodeError, json.JSONDecodeError, P12GateError) as exc:
        print(f"P12 migration check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
