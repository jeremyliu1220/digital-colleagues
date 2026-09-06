# SPDX-License-Identifier: Apache-2.0

"""Run retained P8 regressions followed by P9 gates in locked workspaces."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from scripts.check_p9_repository import (
    ACCEPTANCE_COMMIT,
    BASE_COMMIT,
    BRANCH,
    IMPLEMENTATION_PATHS,
)
from scripts.collect_p9_evidence import (
    EvidenceError,
    public_tree_digest,
    validate_unittest,
    write_p9_evidence,
)
from scripts.run_p4_toolchain import ToolchainError, _json, _run
from scripts.run_p8_toolchain import _prepare_python

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "artifacts/p9/summary.json"
FOCUSED: dict[str, tuple[str, str, str]] = {
    "repository": ("P9 repository", "p9_repository", "scripts/check_p9_repository.py"),
    "provenance": ("P9 provenance", "p9_provenance", "scripts/check_p9_provenance.py"),
    "rebaseline": ("P9 rebaseline", "p9_rebaseline", "scripts/check_p9_rebaseline.py"),
}
SCOPES = {"all", "test", *FOCUSED}
P9_TEST_BOUNDARIES = {
    "tests.p9.test_repository.P9RepositoryTests.test_exact_healthy_candidate_passes_repository_and_provenance": "p9_exact_candidate",
    "tests.p9.test_repository.P9RepositoryTests.test_rename_copy_path_traversal_symlink_and_special_file_bypasses_fail": "p9_repository_bypass_refusal",
    "tests.p9.test_repository.P9RepositoryTests.test_product_studio_compose_dependency_and_version_changes_are_rejected": "p9_product_runtime_refusal",
    "tests.p9.test_rebaseline.P9RebaselineTests.test_package_self_grant_executable_skill_memory_and_collaboration_claims_fail": "p9_capability_confusion_refusal",
    "tests.p9.test_rebaseline.P9RebaselineTests.test_p15_live_prerequisites_are_complete": "p9_live_prerequisites",
    "tests.p9.test_evidence_gate.P9EvidenceTests.test_evidence_writer_rejects_failure_skip_dirty_branch_and_uncommitted_input": "p9_evidence_fail_closed",
}


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ToolchainError("Git P9 evidence inspection failed")
    return completed.stdout.strip()


def _gate(
    python: Path,
    *,
    label: str,
    script: str,
    temporary: Path,
    environment: dict[str, str],
) -> dict[str, Any]:
    return _json(
        _run(
            label,
            [str(python), "-B", script, "."],
            cwd=ROOT,
            temporary=temporary,
            environment=environment,
        ),
        label,
    )


def _p9_unittest(python: Path, *, temporary: Path, environment: dict[str, str]) -> dict[str, Any]:
    output_path = temporary / "p9-unittest.json"
    _run(
        "P9 Python unittest",
        [
            str(python),
            "-B",
            "scripts/run_p8_unittest_suite.py",
            "--start-directory",
            "tests/p9",
            "--top-level-directory",
            ".",
            "--json-output",
            str(output_path),
        ],
        cwd=ROOT,
        temporary=temporary,
        environment=environment,
    )
    try:
        value = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolchainError("P9 unittest outcome is invalid") from exc
    if not isinstance(value, dict):
        raise ToolchainError("P9 unittest outcome is not an object")
    test_ids = value.get("test_ids")
    if not isinstance(test_ids, list):
        raise ToolchainError("P9 unittest identities are invalid")
    value["fault_boundaries"] = sorted(
        boundary for test_id, boundary in P9_TEST_BOUNDARIES.items() if test_id in test_ids
    )
    return validate_unittest(value)


def _verify_implementation_commit() -> tuple[str, str, str]:
    if _git("status", "--porcelain"):
        raise ToolchainError("P9 evidence requires a clean implementation tree")
    branch = _git("branch", "--show-current")
    if branch != BRANCH:
        raise ToolchainError("P9 evidence requires the exact development branch")
    implementation_commit = _git("rev-parse", "HEAD")
    merge_base = _git("merge-base", "HEAD", BASE_COMMIT)
    if merge_base != BASE_COMMIT:
        raise ToolchainError("P9 evidence merge-base drifted")
    if (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ACCEPTANCE_COMMIT, implementation_commit],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        != 0
    ):
        raise ToolchainError("P9 acceptance commit is not trusted ancestry")
    changed = set(_git("diff", "--name-only", BASE_COMMIT, "HEAD", "--").splitlines())
    if changed != IMPLEMENTATION_PATHS:
        raise ToolchainError("P9 implementation commit does not have the exact path set")
    if EVIDENCE.exists():
        raise ToolchainError("P9 evidence must be absent from the implementation commit")
    return branch, implementation_commit, merge_base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run P9 gates in disposable environments.")
    parser.add_argument("--scope", choices=sorted(SCOPES), default="all")
    parser.add_argument("--write-evidence", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.write_evidence and arguments.scope != "all":
        print("P9 toolchain failed: evidence requires complete scope", file=sys.stderr)
        return 2

    verified: set[str] = set()
    results: dict[str, dict[str, Any]] = {}
    unittest_outcome: dict[str, Any] | None = None
    try:
        if arguments.write_evidence:
            branch, implementation_commit, merge_base = _verify_implementation_commit()
        else:
            branch = implementation_commit = merge_base = ""
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p9-toolchain-") as name:
            temporary = Path(name)
            if arguments.scope == "all":
                _run(
                    "Retained P8 locked toolchain",
                    [sys.executable, "-B", "-m", "scripts.run_p8_toolchain", "--scope", "all"],
                    cwd=ROOT,
                    temporary=temporary,
                )
                verified.add("retained_p8_toolchain")

            python, environment = _prepare_python(temporary)
            verified.add("python_lock_install")
            if arguments.scope in FOCUSED:
                label, gate, script = FOCUSED[arguments.scope]
                results[arguments.scope] = _gate(
                    python,
                    label=label,
                    script=script,
                    temporary=temporary,
                    environment=environment,
                )
                verified.add(gate)
            if arguments.scope == "all":
                for key, (label, gate, script) in FOCUSED.items():
                    results[key] = _gate(
                        python,
                        label=label,
                        script=script,
                        temporary=temporary,
                        environment=environment,
                    )
                    verified.add(gate)
                _run(
                    "Public boundary",
                    [str(python), "-B", "scripts/check_public_boundary.py", "."],
                    cwd=ROOT,
                    temporary=temporary,
                    environment=environment,
                )
                verified.add("public_boundary")
                _run(
                    "Git diff whitespace",
                    ["git", "diff", "--check"],
                    cwd=ROOT,
                    temporary=temporary,
                )
                verified.add("git_diff_check")
            if arguments.scope in {"all", "test"}:
                unittest_outcome = _p9_unittest(
                    python, temporary=temporary, environment=environment
                )
                verified.add("p9_unittest")
            if arguments.write_evidence:
                if unittest_outcome is None:
                    raise ToolchainError("P9 evidence lacks unittest results")
                tree_digest = public_tree_digest(ROOT, EVIDENCE)
                write_p9_evidence(
                    evidence_path=EVIDENCE,
                    root=ROOT,
                    results=results,
                    unittest_outcome=unittest_outcome,
                    verified_gates=verified,
                    branch=branch,
                    implementation_commit=implementation_commit,
                    merge_base=merge_base,
                    tree_digest=tree_digest,
                    tree_clean=True,
                    implementation_committed=True,
                )
                print("[pass] P9 evidence written")
            print(
                json.dumps(
                    {
                        "schema_version": 1,
                        "scope": arguments.scope,
                        "verified_gates": sorted(verified),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
    except (OSError, EvidenceError, ToolchainError) as exc:
        safe = str(exc).replace(str(ROOT), "<project>").replace(str(Path.home()), "<home>")
        print(f"P9 toolchain failed: {safe}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
