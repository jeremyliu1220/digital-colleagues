# SPDX-License-Identifier: Apache-2.0

"""Finite-output command line for private P8 operator operations."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from digital_colleagues.operations import (
    BackupError,
    BackupReport,
    DiagnosticsError,
    DiagnosticsReport,
    RestoreReport,
    backup_database,
    create_diagnostics_bundle,
    restore_database,
    verify_backup,
)
from digital_colleagues.operations.metadata import accepted_p7_source_binding_document


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Digital Colleagues local operator tools")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("backup", "verify-backup", "restore", "diagnostics"):
        child = subparsers.add_parser(command)
        if command in {"backup", "verify-backup"}:
            child.add_argument("--source-binding", type=Path, required=True)
        elif command == "restore":
            child.add_argument("--backup-source-binding", type=Path, required=True)
            child.add_argument("--current-source-binding", type=Path)
        else:
            child.add_argument("--release-manifest", type=Path, required=True)
        child.add_argument("--migrations", type=Path, required=True)
        if command != "diagnostics":
            child.add_argument("--backup", type=Path, required=True)
        if command in {"backup", "restore", "diagnostics"}:
            child.add_argument("--database", type=Path, required=True)
        if command == "restore":
            child.add_argument("--replace", action="store_true")
            child.add_argument("--offline-confirmed", action="store_true")
            child.add_argument("--rollback-backup", type=Path)
        if command == "diagnostics":
            child.add_argument("--output", type=Path, required=True)
            child.add_argument("--causal-id", action="append", default=[])
    subparsers.add_parser(
        "accepted-p7-source-binding",
        help="print the fixed first-release P7 source binding",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.command == "accepted-p7-source-binding":
        print(json.dumps(accepted_p7_source_binding_document(), sort_keys=True))
        return 0
    result: BackupReport | RestoreReport | DiagnosticsReport
    try:
        if arguments.command == "backup":
            result = backup_database(
                arguments.database,
                arguments.backup,
                source_binding=arguments.source_binding,
                migrations_directory=arguments.migrations,
            )
        elif arguments.command == "verify-backup":
            result = verify_backup(
                arguments.backup,
                source_binding=arguments.source_binding,
                migrations_directory=arguments.migrations,
            )
        elif arguments.command == "restore":
            result = restore_database(
                arguments.backup,
                arguments.database,
                backup_source_binding=arguments.backup_source_binding,
                migrations_directory=arguments.migrations,
                current_source_binding=arguments.current_source_binding,
                replace=arguments.replace,
                offline_confirmed=arguments.offline_confirmed,
                rollback_backup=arguments.rollback_backup,
            )
        else:
            result = create_diagnostics_bundle(
                arguments.database,
                arguments.output,
                release_manifest=arguments.release_manifest,
                migrations_directory=arguments.migrations,
                causal_identifiers=tuple(arguments.causal_id),
            )
    except (BackupError, DiagnosticsError) as exc:
        print(
            json.dumps({"status": "failed", "category": str(exc)}, sort_keys=True), file=sys.stderr
        )
        return 2
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
