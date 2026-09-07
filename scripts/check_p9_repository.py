# SPDX-License-Identifier: Apache-2.0

"""Validate the exact P9 documentation/governance-only repository boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BASE_COMMIT = "b093a4fa54bf30cef838c72222d1ae63c4eab9d9"
ACCEPTED_P8_COMMIT = "0bb80ab187932fbad42fbf665b8310987609a1f5"
ACCEPTANCE_COMMIT = "597403bc151da75499acea5bb00ee298e7e5a005"
BRANCH = "codex/p9-productization-rebaseline"
ACCEPTANCE_PATH = "docs/p9/acceptance.md"
SUMMARY_PATH = "artifacts/p9/summary.json"

SUMMARY_KEYS = frozenset(
    {
        "schema_version",
        "milestone",
        "status",
        "claim",
        "fixed_base",
        "merge_base",
        "acceptance_commit",
        "development_branch",
        "implementation_commit",
        "tree_digest",
        "generated_at",
        "verified_gates",
        "unittest",
        "repository",
        "provenance",
        "rebaseline",
        "evidence_classes",
        "claim_exclusions",
        "migrations",
    }
)
CLAIM_EXCLUSIONS = [
    "product_or_runtime_implementation",
    "agent_package_or_multi_agent_runtime",
    "openai_or_microsoft_365_compatibility",
    "live_provider_acceptance",
    "human_evaluation",
    "formal_release_or_publication",
    "production_readiness",
    "production_security_or_privacy",
    "high_availability",
    "enterprise_iam_or_tenancy",
    "compliance_certification",
    "p10_through_p15_development",
]
EVIDENCE_CLASSES = {
    "documentation_and_governance": "static",
    "mechanical_regression": "synthetic_offline",
    "openai_live": "not_evaluated",
    "microsoft_365_live": "not_evaluated",
    "human_evaluation": "not_evaluated",
}
VERIFIED_GATES = [
    "git_diff_check",
    "p9_provenance",
    "p9_rebaseline",
    "p9_repository",
    "p9_unittest",
    "public_boundary",
    "python_lock_install",
    "retained_p8_toolchain",
]
UNITTEST_KEYS = frozenset(
    {
        "tests_run",
        "failures",
        "errors",
        "skipped",
        "expected_failures",
        "unexpected_successes",
        "gate_passed",
        "test_ids",
        "fault_boundaries",
    }
)
REQUIRED_FINAL_EVIDENCE_TESTS = frozenset(
    {
        "tests.p9.test_evidence_gate.P9EvidenceTests.test_final_gate_accepts_healthy_evidence_and_implementation_without_summary",
        "tests.p9.test_evidence_gate.P9EvidenceTests.test_final_gate_rejects_claim_status_and_live_promotion",
        "tests.p9.test_evidence_gate.P9EvidenceTests.test_final_gate_rejects_wrong_commit_digest_and_identity_metadata",
        "tests.p9.test_evidence_gate.P9EvidenceTests.test_final_gate_rejects_unknown_fields_and_unsafe_material",
        "tests.p9.test_evidence_gate.P9EvidenceTests.test_final_gate_rejects_mixed_or_nonfinal_evidence_commit",
        "tests.p9.test_evidence_gate.P9EvidenceTests.test_final_gate_rejects_embedded_gate_and_unittest_mutation",
    }
)
EXPECTED_FAULT_BOUNDARIES = [
    "p9_capability_confusion_refusal",
    "p9_evidence_fail_closed",
    "p9_exact_candidate",
    "p9_live_prerequisites",
    "p9_product_runtime_refusal",
    "p9_repository_bypass_refusal",
]
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
UTC_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")

P9_ALLOWED_PATHS = frozenset(
    {
        "AGENTS.md",
        "Makefile",
        "README.md",
        "SECURITY.md",
        SUMMARY_PATH,
        "docs/adr/0007-declarative-agent-package-and-deployment-model.md",
        "docs/adr/0008-external-identity-connections-and-automatic-authorization.md",
        "docs/architecture/target-architecture.md",
        "docs/development.md",
        ACCEPTANCE_PATH,
        "docs/p9/rebaseline-checklist.md",
        "docs/product/capability-matrix.md",
        "docs/product/post-v0.1-capability-outlook.md",
        "docs/product/v0.2-external-dependency-register.md",
        "docs/product/v0.2-public-pilot-capability-matrix.md",
        "docs/product/v0.2-public-pilot-product-brief.md",
        "docs/roadmap.md",
        "docs/security/privacy-boundary.md",
        "docs/security/threat-model.md",
        "docs/security/v0.2-public-pilot-privacy-boundary.md",
        "docs/security/v0.2-public-pilot-threat-model.md",
        "provenance/p9-migration-receipt.json",
        "scripts/check_p8_provenance.py",
        "scripts/check_p8_repository.py",
        "scripts/check_p9_provenance.py",
        "scripts/check_p9_rebaseline.py",
        "scripts/check_p9_repository.py",
        "scripts/collect_p9_evidence.py",
        "scripts/run_p9_toolchain.py",
        "tests/p8/test_repository.py",
        "tests/p9/__init__.py",
        "tests/p9/fixtures.py",
        "tests/p9/test_evidence_gate.py",
        "tests/p9/test_rebaseline.py",
        "tests/p9/test_repository.py",
    }
)
IMPLEMENTATION_PATHS = P9_ALLOWED_PATHS - {SUMMARY_PATH}
HISTORICAL_PATHS = (
    "artifacts/p0",
    "artifacts/p1",
    "artifacts/p2",
    "artifacts/p3",
    "artifacts/p4",
    "artifacts/p5",
    "artifacts/p6",
    "artifacts/p7",
    "artifacts/p8",
    "docs/p0",
    "docs/p1",
    "docs/p2",
    "docs/p3",
    "docs/p4",
    "docs/p5",
    "docs/p6",
    "docs/p7",
    "docs/p8",
    "migrations",
    "provenance/p2-migration-receipt.json",
    "provenance/p3-migration-receipt.json",
    "provenance/p4-migration-receipt.json",
    "provenance/p5-migration-receipt.json",
    "provenance/p6-migration-receipt.json",
    "provenance/p7-migration-receipt.json",
    "provenance/p8-migration-receipt.json",
    "provenance/source-allowlist.json",
    "provenance/source-rights-confirmation.json",
    "provenance/source-fingerprint-before.json",
    "provenance/source-fingerprint-after.json",
)
MIGRATION_FILES = (
    "001_initial.sql",
    "002_runtime_indexes.sql",
    "003_timer_triggers.sql",
    "004_local_authentication.sql",
    "005_evaluation_observations.sql",
    "006_revisioned_colleague_builder.sql",
    "007_governance_hardening.sql",
    "manifest.json",
)
FORBIDDEN_RESIDUE_PARTS = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}
FORBIDDEN_RESIDUE_SUFFIXES = (
    ".backup",
    ".db",
    ".log",
    ".pyc",
    ".sqlite",
    ".sqlite-shm",
    ".sqlite-wal",
    ".tar.gz",
    ".whl",
)
FORBIDDEN_PRODUCT_PREFIXES = (
    "src/digital_colleagues/",
    "studio/",
    "migrations/",
    "requirements/",
    "release/",
)
FORBIDDEN_PRODUCT_FILES = {
    "compose.yaml",
    "compose.p7.yaml",
    "Dockerfile",
    "Dockerfile.p7",
    "pyproject.toml",
}


class RepositoryError(RuntimeError):
    """The repository violates the fixed P9 boundary."""


@dataclass(frozen=True)
class GitChange:
    status: str
    paths: tuple[str, ...]


def _run_git(root: Path, *arguments: str, text: bool = True) -> str | bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=text,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryError("Git P9 repository inspection failed")
    return cast(str | bytes, completed.stdout)


def _require_commit(root: Path, commit: str, label: str) -> None:
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryError(f"the fixed {label} commit is unavailable")


def _is_ancestor(root: Path, ancestor: str, descendant: str = "HEAD") -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        raise RepositoryError("Git P9 ancestry inspection failed")
    return completed.returncode == 0


def _safe_path(field: bytes) -> str:
    try:
        value = field.decode("utf-8")
    except UnicodeError as exc:
        raise RepositoryError("Git P9 path is not UTF-8") from exc
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise RepositoryError("Git P9 path is invalid")
    return value


def _parse_name_status(output: bytes) -> tuple[GitChange, ...]:
    if not output:
        return ()
    fields = output.split(b"\0")
    if fields[-1] != b"":
        raise RepositoryError("Git P9 status is malformed")
    fields.pop()
    changes: list[GitChange] = []
    index = 0
    while index < len(fields):
        try:
            status_value = fields[index].decode("ascii")
        except UnicodeError as exc:
            raise RepositoryError("Git P9 status is invalid") from exc
        index += 1
        code = status_value[:1]
        paths: tuple[str, ...]
        if code in {"R", "C"}:
            score = status_value[1:]
            if not score.isdigit() or int(score) > 100 or index + 2 > len(fields):
                raise RepositoryError("Git P9 rename/copy status is malformed")
            paths = (_safe_path(fields[index]), _safe_path(fields[index + 1]))
            index += 2
        elif status_value in {"A", "D", "M", "T"}:
            if index >= len(fields):
                raise RepositoryError("Git P9 status is malformed")
            paths = (_safe_path(fields[index]),)
            index += 1
        elif code in {"U", "X", "B"}:
            raise RepositoryError("Git P9 change state is unresolved")
        else:
            raise RepositoryError("Git P9 status is unsupported")
        changes.append(GitChange(status_value, paths))
    return tuple(changes)


def _diff(root: Path, *arguments: str) -> tuple[GitChange, ...]:
    completed = subprocess.run(
        [
            "git",
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--name-status",
            "-z",
            "--break-rewrites",
            "--find-renames",
            "--find-copies-harder",
            *arguments,
            "--",
        ],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryError("Git P9 change inspection failed")
    return _parse_name_status(completed.stdout)


def _untracked(root: Path) -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryError("Git P9 untracked inspection failed")
    if not completed.stdout:
        return ()
    fields = completed.stdout.split(b"\0")
    if fields[-1] != b"":
        raise RepositoryError("Git P9 untracked output is malformed")
    return tuple(_safe_path(field) for field in fields[:-1])


def _paths(changes: tuple[GitChange, ...]) -> set[str]:
    return {path for change in changes for path in change.paths}


def _verify_acceptance_commit(root: Path) -> None:
    parent = _run_git(root, "rev-parse", f"{ACCEPTANCE_COMMIT}^")
    assert isinstance(parent, str)
    if parent.strip() != BASE_COMMIT:
        raise RepositoryError("P9 acceptance commit is not the isolated first P9 commit")
    acceptance_delta = _diff(root, f"{ACCEPTANCE_COMMIT}^", ACCEPTANCE_COMMIT)
    if (
        len(acceptance_delta) != 1
        or acceptance_delta[0].status != "A"
        or acceptance_delta[0].paths != (ACCEPTANCE_PATH,)
    ):
        raise RepositoryError("P9 acceptance commit is not isolated")
    accepted = _run_git(root, "show", f"{ACCEPTANCE_COMMIT}:{ACCEPTANCE_PATH}", text=False)
    assert isinstance(accepted, bytes)
    path = root / ACCEPTANCE_PATH
    if not path.is_file() or path.is_symlink() or path.read_bytes() != accepted:
        raise RepositoryError("P9 acceptance contract changed after its fixed commit")


def _verify_historical(root: Path) -> None:
    changed = _run_git(root, "diff", "--name-only", BASE_COMMIT, "HEAD", "--", *HISTORICAL_PATHS)
    assert isinstance(changed, str)
    if changed.strip():
        raise RepositoryError("P0-P8 historical acceptance, artifact, receipt, or migration drift")


def _verify_migrations(root: Path) -> None:
    directory = root / "migrations"
    actual = tuple(sorted(path.name for path in directory.iterdir() if path.is_file()))
    if actual != MIGRATION_FILES:
        raise RepositoryError("migrations must remain exactly 001-007 plus manifest.json")
    for name in MIGRATION_FILES:
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise RepositoryError("a historical migration path has an unsafe type")
        accepted = _run_git(root, "show", f"{BASE_COMMIT}:migrations/{name}", text=False)
        assert isinstance(accepted, bytes)
        if path.read_bytes() != accepted:
            raise RepositoryError("a historical migration digest changed")
    if tuple(directory.glob("008*")):
        raise RepositoryError("migration 008 must be absent in P9")


def _verify_file_types(root: Path, paths: set[str]) -> None:
    for relative in paths:
        path = root / relative
        try:
            mode = path.lstat().st_mode
        except OSError as exc:
            raise RepositoryError("a required P9 path is missing") from exc
        if not stat.S_ISREG(mode) or stat.S_ISLNK(mode):
            raise RepositoryError("P9 changed paths must be regular non-symlink files")


def _residue(root: Path) -> tuple[str, ...]:
    found: list[str] = []
    for directory, names, files in os.walk(root, topdown=True, followlinks=False):
        base = Path(directory)
        relative_dir = base.relative_to(root)
        if ".git" in relative_dir.parts:
            names[:] = []
            continue
        names[:] = [name for name in names if name != ".git"]
        for name in (*names, *files):
            path = base / name
            relative = path.relative_to(root)
            mode = path.lstat().st_mode
            unsafe_type = stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode))
            if (
                unsafe_type
                or any(part in FORBIDDEN_RESIDUE_PARTS for part in relative.parts)
                or name.endswith(FORBIDDEN_RESIDUE_SUFFIXES)
            ):
                found.append(relative.as_posix())
    return tuple(sorted(set(found)))


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise RepositoryError("P9 evidence summary contains a duplicate field")
        value[key] = child
    return value


def _reject_json_constant(_value: str) -> None:
    raise RepositoryError("P9 evidence summary contains a non-finite number")


def _strict_equal(actual: object, expected: object) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        assert isinstance(actual, dict)
        return set(actual) == set(expected) and all(
            _strict_equal(actual[key], child) for key, child in expected.items()
        )
    if isinstance(expected, list):
        assert isinstance(actual, list)
        return len(actual) == len(expected) and all(
            _strict_equal(actual_child, expected_child)
            for actual_child, expected_child in zip(actual, expected, strict=True)
        )
    return actual == expected


def _require_exact(actual: object, expected: object, label: str) -> None:
    if not _strict_equal(actual, expected):
        raise RepositoryError(f"P9 evidence summary {label} is invalid")


def _assert_summary_safe(value: object, *, root: Path) -> None:
    if isinstance(value, dict):
        forbidden_keys = {
            "account_id",
            "api_key",
            "client_secret",
            "cookie",
            "credential",
            "live_receipt",
            "password",
            "private_payload",
            "provider_id",
            "refresh_token",
            "session_credential",
            "tenant_id",
            "token",
        }
        for key, child in value.items():
            if key.lower() in forbidden_keys:
                raise RepositoryError("P9 evidence summary contains a private field")
            _assert_summary_safe(child, root=root)
        return
    if isinstance(value, list):
        for child in value:
            _assert_summary_safe(child, root=root)
        return
    if not isinstance(value, str):
        return

    forbidden_literals = (
        str(root),
        str(Path.home()),
        "/.codex/attachments/",
        "PRIVATE_LIVE_RECEIPT",
    )
    if any(marker and marker.lower() in value.lower() for marker in forbidden_literals):
        raise RepositoryError("P9 evidence summary contains local or private material")
    if re.search(r"/(?:Users|home)/[^\s`]+", value):
        raise RepositoryError("P9 evidence summary contains a local absolute path")
    if re.search(r"[A-Za-z]:\\(?:Users|Documents and Settings)\\[^\s`]+", value, re.I):
        raise RepositoryError("P9 evidence summary contains a local absolute path")
    if re.search(
        r"(?:sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._=-]{12,}|"
        r"(?:tenant|client|account|provider)[_-]?id\s*[:=]\s*[A-Za-z0-9._=-]{8,}|"
        r"(?:token|secret|password|credential)\s*[:=]\s*\S{8,})",
        value,
        re.I,
    ):
        raise RepositoryError("P9 evidence summary contains credential or live-identifier material")


def _public_tree_digest(root: Path, excluded: Path) -> str:
    aggregate = hashlib.sha256()
    documents = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path != excluded
        and ".git" not in path.relative_to(root).parts
        and not any(part in FORBIDDEN_RESIDUE_PARTS for part in path.relative_to(root).parts)
    )
    for document in documents:
        relative = document.relative_to(root).as_posix().encode()
        digest = hashlib.sha256(document.read_bytes()).digest()
        for value in (relative, digest):
            aggregate.update(len(value).to_bytes(8, "big"))
            aggregate.update(value)
    return "sha256:" + aggregate.hexdigest()


def _read_summary(root: Path, head: str) -> dict[str, Any]:
    path = root / SUMMARY_PATH
    try:
        if path.stat().st_size > 1_000_000:
            raise RepositoryError("P9 evidence summary is unbounded")
        summary_bytes = path.read_bytes()
        committed = _run_git(root, "show", f"{head}:{SUMMARY_PATH}", text=False)
        assert isinstance(committed, bytes)
        if summary_bytes != committed:
            raise RepositoryError("P9 evidence summary differs from the committed artifact")
        decoded = summary_bytes.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except RepositoryError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RepositoryError("P9 evidence summary is unreadable") from exc
    if type(value) is not dict:
        raise RepositoryError("P9 evidence summary must be a JSON object")
    return value


def _verify_unittest_summary(value: object) -> None:
    if type(value) is not dict or set(value) != UNITTEST_KEYS:
        raise RepositoryError("P9 evidence unittest result shape is invalid")
    assert isinstance(value, dict)
    count_fields = (
        "tests_run",
        "failures",
        "errors",
        "skipped",
        "expected_failures",
        "unexpected_successes",
    )
    if any(type(value[key]) is not int for key in count_fields):
        raise RepositoryError("P9 evidence unittest counts have invalid types")
    if (
        value["tests_run"] < 1
        or value["gate_passed"] is not True
        or any(value[key] != 0 for key in count_fields[1:])
    ):
        raise RepositoryError("P9 evidence unittest result is not a clean positive run")
    test_ids = value["test_ids"]
    if (
        type(test_ids) is not list
        or len(test_ids) != value["tests_run"]
        or any(
            type(test_id) is not str or not test_id.startswith("tests.p9.") for test_id in test_ids
        )
        or len(set(test_ids)) != len(test_ids)
        or test_ids != sorted(test_ids)
        or not REQUIRED_FINAL_EVIDENCE_TESTS.issubset(test_ids)
    ):
        raise RepositoryError("P9 evidence unittest identities are invalid")
    _require_exact(value["fault_boundaries"], EXPECTED_FAULT_BOUNDARIES, "fault boundaries")


def _verify_final_evidence(root: Path, repository_result: dict[str, object]) -> None:
    head = repository_result["head_commit"]
    assert isinstance(head, str)
    summary = _read_summary(root, head)
    _assert_summary_safe(summary, root=root)
    if set(summary) != SUMMARY_KEYS:
        raise RepositoryError("P9 evidence summary has missing or extra fields")

    fixed_values: dict[str, object] = {
        "schema_version": 1,
        "milestone": "P9",
        "status": "development_complete_awaiting_independent_acceptance",
        "claim": "p9_productization_rebaseline_candidate",
        "fixed_base": BASE_COMMIT,
        "merge_base": BASE_COMMIT,
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "development_branch": BRANCH,
        "verified_gates": VERIFIED_GATES,
        "evidence_classes": EVIDENCE_CLASSES,
        "claim_exclusions": CLAIM_EXCLUSIONS,
        "migrations": {
            "immutable_versions": [1, 2, 3, 4, 5, 6, 7],
            "migration_008": "absent",
        },
    }
    for key, expected in fixed_values.items():
        _require_exact(summary[key], expected, key)

    generated_at = summary["generated_at"]
    if type(generated_at) is not str or not UTC_TIMESTAMP_PATTERN.fullmatch(generated_at):
        raise RepositoryError("P9 evidence summary generated_at is invalid")
    try:
        if datetime.fromisoformat(generated_at.removesuffix("Z") + "+00:00").tzinfo != UTC:
            raise ValueError
    except ValueError as exc:
        raise RepositoryError("P9 evidence summary generated_at is invalid") from exc

    implementation_commit = summary["implementation_commit"]
    parents = str(_run_git(root, "rev-list", "--parents", "-n", "1", head)).split()
    if (
        type(implementation_commit) is not str
        or not COMMIT_PATTERN.fullmatch(implementation_commit)
        or len(parents) != 2
        or parents[0] != head
        or parents[1] != implementation_commit
        or implementation_commit in {BASE_COMMIT, ACCEPTANCE_COMMIT}
        or not _is_ancestor(root, BASE_COMMIT, implementation_commit)
        or not _is_ancestor(root, ACCEPTANCE_COMMIT, implementation_commit)
    ):
        raise RepositoryError("P9 implementation commit is not the evidence commit's direct parent")
    evidence_delta = _diff(root, implementation_commit, head)
    if (
        len(evidence_delta) != 1
        or evidence_delta[0].status != "A"
        or evidence_delta[0].paths != (SUMMARY_PATH,)
    ):
        raise RepositoryError("the last P9 evidence commit must add only the summary")

    tree_digest = summary["tree_digest"]
    if type(tree_digest) is not str or not DIGEST_PATTERN.fullmatch(tree_digest):
        raise RepositoryError("P9 evidence summary tree_digest is invalid")
    recomputed_digest = _public_tree_digest(root, root / SUMMARY_PATH)
    if tree_digest != recomputed_digest:
        raise RepositoryError("P9 evidence summary tree_digest does not match the public tree")

    expected_repository = dict(repository_result)
    expected_repository.update(
        {
            "candidate_phase": "implementation",
            "branch": BRANCH,
            "head_commit": implementation_commit,
            "changed_path_count": len(IMPLEMENTATION_PATHS),
            "allowed_path_count": len(IMPLEMENTATION_PATHS),
            "staged_change_path_count": 0,
            "unstaged_change_path_count": 0,
            "untracked_path_count": 0,
        }
    )
    _require_exact(summary["repository"], expected_repository, "repository result")

    from scripts.check_p9_provenance import ProvenanceError, check_provenance
    from scripts.check_p9_rebaseline import RebaselineError, check_rebaseline

    try:
        expected_provenance = check_provenance(root)
        expected_rebaseline = check_rebaseline(root)
    except (ProvenanceError, RebaselineError) as exc:
        raise RepositoryError("a fixed P9 gate failed during evidence validation") from exc
    _require_exact(summary["provenance"], expected_provenance, "provenance result")
    _require_exact(summary["rebaseline"], expected_rebaseline, "rebaseline result")
    _verify_unittest_summary(summary["unittest"])


def check_repository(root: Path, *, require_clean: bool = True) -> dict[str, object]:
    root = root.resolve()
    top = _run_git(root, "rev-parse", "--show-toplevel")
    assert isinstance(top, str)
    if Path(top.strip()).resolve() != root:
        raise RepositoryError("P9 repository root is not exact")
    for commit, label in (
        (BASE_COMMIT, "base"),
        (ACCEPTED_P8_COMMIT, "accepted P8"),
        (ACCEPTANCE_COMMIT, "acceptance"),
    ):
        _require_commit(root, commit, label)
        if not _is_ancestor(root, commit):
            raise RepositoryError(f"the fixed {label} commit is not an ancestor of HEAD")
    merge_base = _run_git(root, "merge-base", "HEAD", BASE_COMMIT)
    branch = _run_git(root, "branch", "--show-current")
    head = _run_git(root, "rev-parse", "HEAD")
    assert isinstance(merge_base, str) and isinstance(branch, str) and isinstance(head, str)
    if merge_base.strip() != BASE_COMMIT:
        raise RepositoryError("P9 exact base or merge-base drifted")

    _verify_acceptance_commit(root)
    _verify_historical(root)
    _verify_migrations(root)

    committed = _diff(root, BASE_COMMIT, "HEAD")
    if any(change.status[:1] in {"R", "C", "T", "D"} for change in committed):
        raise RepositoryError("P9 rename, copy, type change, or deletion is forbidden")
    committed_paths = _paths(committed)
    candidate_phase = "final_evidence" if SUMMARY_PATH in committed_paths else "implementation"
    expected = P9_ALLOWED_PATHS if candidate_phase == "final_evidence" else IMPLEMENTATION_PATHS
    if committed_paths - expected:
        raise RepositoryError("P9 committed change is outside the exact allowlist")
    if committed_paths != expected:
        raise RepositoryError("P9 committed delta is partial or incomplete")
    _verify_file_types(root, committed_paths)

    product_changes = {
        path
        for path in committed_paths
        if path in FORBIDDEN_PRODUCT_FILES
        or any(path.startswith(prefix) for prefix in FORBIDDEN_PRODUCT_PREFIXES)
    }
    if product_changes:
        raise RepositoryError("P9 contains a product/runtime implementation change")

    staged = _diff(root, "--cached", "HEAD")
    unstaged = _diff(root)
    untracked = _untracked(root)
    if require_clean and (staged or unstaged or untracked):
        raise RepositoryError("P9 evidence candidate requires a clean index and worktree")
    dirty_paths = _paths(staged) | _paths(unstaged) | set(untracked)
    if dirty_paths - P9_ALLOWED_PATHS:
        raise RepositoryError("P9 working tree changed a path outside the allowlist")

    residue = _residue(root)
    if residue:
        raise RepositoryError("repository contains runtime, credential, cache, or build residue")

    result: dict[str, object] = {
        "schema_version": 1,
        "gate": "p9_repository_clean",
        "candidate_phase": candidate_phase,
        "branch": branch.strip(),
        "head_commit": head.strip(),
        "base_commit": BASE_COMMIT,
        "merge_base": merge_base.strip(),
        "accepted_p8_commit": ACCEPTED_P8_COMMIT,
        "accepted_p8_ancestor": True,
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "acceptance_contract_immutable": True,
        "acceptance_commit_isolated": True,
        "changed_path_count": len(committed_paths),
        "allowed_path_count": len(expected),
        "historical_drift_count": 0,
        "migration_count": 7,
        "migration_008": False,
        "product_runtime_implementation_change_count": 0,
        "staged_change_path_count": len(_paths(staged)),
        "unstaged_change_path_count": len(_paths(unstaged)),
        "untracked_path_count": len(untracked),
        "cleanup_residue_count": 0,
    }
    if candidate_phase == "final_evidence":
        _verify_final_evidence(root, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P9 repository health.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_repository(Path(arguments.root))
    except (OSError, RepositoryError) as exc:
        print(f"P9 repository check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
