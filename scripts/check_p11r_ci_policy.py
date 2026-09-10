# SPDX-License-Identifier: Apache-2.0

"""Validate the exact read-only, branch-appropriate P11R CI workflow."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p11r_repository import P11RGateError

WORKFLOW_PATH = ".github/workflows/ci.yml"
CHECKOUT_PIN = "d23441a48e516b6c34aea4fa41551a30e30af803"
PYTHON_PIN = "ece7cb06caefa5fff74198d8649806c4678c61a1"
NODE_PIN = "249970729cb0ef3589644e2896645e5dc5ba9c38"
NODE_VERSION = "24.15.0"
NODE_ENGINE = ">=24.15.0 <25"
NPM_VERSION = "11.12.1"
PACKAGE_MANAGER = "npm@11.12.1+sha224.8b8077c959144afd9fbfc0f0a36ecf5b5375c7b1a202f32c0c06cdcb"

EXPECTED_WORKFLOW = """# SPDX-License-Identifier: Apache-2.0

name: CI

on:
  pull_request:
    branches:
      - main
  push:
    branches:
      - main

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}-${{ github.event_name }}
  cancel-in-progress: false

jobs:
  current-ci:
    name: Current P11-aware non-publishing verification
    runs-on: ubuntu-latest
    timeout-minutes: 45
    steps:
      - name: Check out source
        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6
        with:
          fetch-depth: 0
          persist-credentials: false
          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}
      - name: Set up Python
        uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: requirements/p8.lock
      - name: Set up Node.js
        uses: actions/setup-node@249970729cb0ef3589644e2896645e5dc5ba9c38 # v6
        with:
          node-version-file: .nvmrc
          cache: npm
          cache-dependency-path: studio/package-lock.json
      - name: Enable the package-manager integrity boundary
        run: corepack enable
      - name: Run current P11-aware non-publishing verification
        env:
          PYTHONPATH: src
        run: make ci

  main-compose-smoke:
    name: Bounded main Compose smoke
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: current-ci
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - name: Check out exact main push
        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6
        with:
          fetch-depth: 0
          persist-credentials: false
          ref: ${{ github.sha }}
      - name: Set up Python
        uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: requirements/p8.lock
      - name: Run bounded main Compose smoke
        env:
          PYTHONPATH: src
        run: make p11r-compose-smoke
"""


def check_ci_policy(root: Path) -> dict[str, object]:
    workflow = (root / WORKFLOW_PATH).read_text(encoding="utf-8")
    if workflow != EXPECTED_WORKFLOW:
        raise P11RGateError("P11R CI workflow differs from the fixed canonical policy")
    actions = re.findall(r"^\s*uses:\s*([^\s#]+)", workflow, re.MULTILINE)
    if len(actions) != 5 or any(
        not re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", action) for action in actions
    ):
        raise P11RGateError("P11R action pins are incomplete or mutable")
    expected_actions = {
        f"actions/checkout@{CHECKOUT_PIN}",
        f"actions/setup-python@{PYTHON_PIN}",
        f"actions/setup-node@{NODE_PIN}",
    }
    if set(actions) != expected_actions:
        raise P11RGateError("P11R action identity allowlist changed")
    forbidden = (
        "pull_request_target",
        "workflow_dispatch",
        "schedule:",
        "id-token:",
        "packages: write",
        "${{ secrets.",
        "git push",
        "git tag",
        "gh release",
        "npm publish",
        "twine upload",
        "docker push",
        "--push",
        "cosign sign",
        "cosign attest",
        "make p10-ci",
        "make p11-test",
        "make p11-check",
        "make check",
        "scripts/check_p11_repository.py",
    )
    lowered = workflow.lower()
    if any(token.lower() in lowered for token in forbidden):
        raise P11RGateError("P11R CI contains a forbidden trigger, authority, or command")
    nvm = (root / ".nvmrc").read_text(encoding="utf-8").strip()
    package = json.loads((root / "studio/package.json").read_text(encoding="utf-8"))
    if (
        nvm != NODE_VERSION
        or package.get("engines", {}).get("node") != NODE_ENGINE
        or package.get("packageManager") != PACKAGE_MANAGER
    ):
        raise P11RGateError("P11R Node/npm repository identity is inconsistent")
    return {
        "schema_version": 1,
        "gate": "p11r_ci_policy",
        "status": "passed",
        "pull_request_base": "main",
        "push_branch": "main",
        "permission": "contents: read",
        "action_pin_count": len(actions),
        "node_version_file": ".nvmrc",
        "node_version": NODE_VERSION,
        "node_engine": NODE_ENGINE,
        "npm_version": NPM_VERSION,
        "package_manager": PACKAGE_MANAGER,
        "secret_count": 0,
        "oidc_count": 0,
        "write_permission_count": 0,
        "publication_command_count": 0,
        "pull_request_compose_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        result = check_ci_policy(Path(args.root).resolve())
    except (OSError, UnicodeError, json.JSONDecodeError, P11RGateError) as exc:
        print(f"P11R CI policy check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
