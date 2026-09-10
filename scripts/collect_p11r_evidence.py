# SPDX-License-Identifier: Apache-2.0

"""Run P11R gates and atomically create the separately authorized final summary."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p11r_ci_policy import (  # noqa: E402
    NODE_ENGINE,
    NODE_VERSION,
    NPM_VERSION,
    PACKAGE_MANAGER,
)
from scripts.check_p11r_repository import (  # noqa: E402
    ACCEPTANCE_COMMIT,
    ACCEPTANCE_PATH,
    BASE_COMMIT,
    BRANCH,
    SUMMARY_PATH,
    P11RGateError,
    acceptance_paths,
    git,
    implementation_paths,
)
from scripts.run_p11r_toolchain import ROOT, run_all  # noqa: E402

CLAIM = "p11r_post_p11_governance_and_ci_alignment_candidate"
STATUS = "development_complete_awaiting_independent_acceptance"
REPOSITORY = "jeremyliu1220/digital-colleagues"
WORKFLOW = "ci.yml"


def _tree_digest(root: Path, paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for relative in paths:
        encoded = relative.encode("utf-8")
        content = (root / relative).read_bytes()
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return "sha256:" + digest.hexdigest()


def _preconditions(root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if git(root, "branch", "--show-current") != BRANCH:
        raise P11RGateError("P11R evidence branch identity is invalid")
    if git(root, "status", "--porcelain", "--untracked-files=all"):
        raise P11RGateError("P11R evidence requires a clean committed implementation")
    if (root / SUMMARY_PATH).exists():
        raise P11RGateError("P11R summary already exists")
    expected = set(acceptance_paths(root)) - {SUMMARY_PATH}
    changed = set(git(root, "diff", "--name-only", BASE_COMMIT, "HEAD").splitlines())
    if changed != expected:
        raise P11RGateError("P11R committed implementation path set is not exact")
    commits = tuple(git(root, "rev-list", "--reverse", f"{ACCEPTANCE_COMMIT}..HEAD").splitlines())
    if not commits:
        raise P11RGateError("P11R implementation commit is absent")
    allowed = set(implementation_paths(root))
    for commit in commits:
        touched = set(
            git(
                root,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                commit,
            ).splitlines()
        )
        if not touched or not touched <= allowed:
            raise P11RGateError("P11R implementation commit path set is invalid")
        if ACCEPTANCE_PATH in touched or SUMMARY_PATH in touched:
            raise P11RGateError("P11R implementation changed protected contract or evidence")
    return tuple(sorted(expected)), commits


def _successful_pr_run(head: str) -> dict[str, object]:
    url = (
        f"https://api.github.com/repos/{REPOSITORY}/actions/workflows/{WORKFLOW}/runs"
        "?event=pull_request&status=completed&per_page=100"
    )
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "dc-p11r-evidence"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read())
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise P11RGateError("P11R public pull-request CI result is unavailable") from exc
    runs = payload.get("workflow_runs") if isinstance(payload, dict) else None
    if not isinstance(runs, list):
        raise P11RGateError("P11R public pull-request CI response is invalid")
    matches = [
        run
        for run in runs
        if isinstance(run, dict)
        and run.get("head_sha") == head
        and run.get("event") == "pull_request"
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
    ]
    if len(matches) != 1:
        raise P11RGateError("P11R requires exactly one successful pull-request run for HEAD")
    run = matches[0]
    run_id = run.get("id")
    run_url = run.get("html_url")
    if not isinstance(run_id, int) or not isinstance(run_url, str):
        raise P11RGateError("P11R pull-request run identity is invalid")
    return {
        "run_id": run_id,
        "url": run_url,
        "event": "pull_request",
        "head_sha": head,
        "status": "completed",
        "conclusion": "success",
    }


def build_summary(
    root: Path,
    *,
    results: dict[str, Any],
    changed_paths: tuple[str, ...],
    implementation_commits: tuple[str, ...],
    pr_run: dict[str, object],
) -> dict[str, object]:
    current_quality = results["current_ci"]["tests"]["quality"]
    accepted = results["accepted_p11"]
    current = current_quality["current_tree_p11"]
    governance = current_quality["p11r"]
    return {
        "schema_version": 1,
        "change": "P11R",
        "claim": CLAIM,
        "status": STATUS,
        "branch": BRANCH,
        "base_commit": BASE_COMMIT,
        "acceptance_commit": ACCEPTANCE_COMMIT,
        "evidence_generation_head": git(root, "rev-parse", "HEAD"),
        "implementation_commits": list(implementation_commits),
        "implementation_tree_digest": _tree_digest(root, implementation_paths(root)),
        "changed_paths": list((*changed_paths, SUMMARY_PATH)),
        "changed_path_count": len(changed_paths) + 1,
        "toolchain": {
            "python_lock": "requirements/p8.lock",
            "hash_locked_python": True,
            "node_version_file": ".nvmrc",
            "node_version": NODE_VERSION,
            "node_engine": NODE_ENGINE,
            "npm_version": NPM_VERSION,
            "package_manager": PACKAGE_MANAGER,
        },
        "tests": {
            "accepted_p11_exact_object_suite": accepted["tests"],
            "p11r_current_tree_p11_regression_suite": current,
            "p11r_governance_suite": governance,
        },
        "gates": results,
        "pull_request_ci": pr_run,
        "known_baseline": {
            "run_id": 34414627643,
            "classification": "post_merge_ci_configuration_drift",
            "p11_product_defect": False,
            "p11_acceptance_failure": False,
        },
        "change_counts": {
            "product_runtime_source": 0,
            "studio_product_behavior": 0,
            "database_schema": 0,
            "migration": 0,
        },
        "publication": {
            "secret_count": 0,
            "oidc_count": 0,
            "write_permission_count": 0,
            "tag_count": 0,
            "release_count": 0,
            "package_or_image_push_count": 0,
            "signature_or_attestation_count": 0,
            "publication_count": 0,
        },
        "provenance": "provenance/p11r-change-receipt.json",
        "exclusions": [
            "Roadmap rebaseline",
            "P12",
            "product/runtime changes",
            "Studio product behavior changes",
            "database schema or migration changes",
            "tag, Release, signature, attestation, package, image, or publication",
        ],
    }


def write_evidence(root: Path, summary: dict[str, object]) -> None:
    destination = root / SUMMARY_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    descriptor, temporary_name = tempfile.mkstemp(prefix=".p11r-summary-", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, destination)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def main() -> int:
    try:
        changed, commits = _preconditions(ROOT)
        head = git(ROOT, "rev-parse", "HEAD")
        pr_run = _successful_pr_run(head)
        with tempfile.TemporaryDirectory(prefix="dc-p11r-evidence-") as value:
            results = run_all(ROOT, Path(value))
        summary = build_summary(
            ROOT,
            results=results,
            changed_paths=changed,
            implementation_commits=commits,
            pr_run=pr_run,
        )
        write_evidence(ROOT, summary)
    except (OSError, UnicodeError, P11RGateError) as exc:
        safe = str(exc).replace(str(ROOT), "<project>")
        print(f"P11R evidence collection failed: {safe}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "written", "path": SUMMARY_PATH}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
