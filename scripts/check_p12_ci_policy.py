# SPDX-License-Identifier: Apache-2.0

"""Validate the canonical read-only P12 v4 GitHub Actions policy."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p12_repository import P12GateError  # noqa: E402

WORKFLOW_PATH = ".github/workflows/ci.yml"
CHECKOUT_PIN = "d23441a48e516b6c34aea4fa41551a30e30af803"
PYTHON_PIN = "ece7cb06caefa5fff74198d8649806c4678c61a1"
NODE_PIN = "249970729cb0ef3589644e2896645e5dc5ba9c38"
COSIGN_INSTALLER_PIN = "6f9f17788090df1f26f669e9d70d6ae9567deba6"
COSIGN_RELEASE = "v3.0.6"
NODE_VERSION = "24.15.0"
NODE_ENGINE = ">=24.15.0 <25"
NPM_VERSION = "11.12.1"
PACKAGE_MANAGER = "npm@11.12.1+sha224.8b8077c959144afd9fbfc0f0a36ecf5b5375c7b1a202f32c0c06cdcb"
RUNNER_FAMILY = "ubuntu-24.04"
CURRENT_JOB_ID = "current-ci"
PORTABLE_JOB_ID = "portable-history"
MAIN_COMPOSE_JOB_ID = "main-compose-smoke"
CURRENT_JOB_NAME = "Current P12 governance non-publishing verification"
PORTABLE_JOB_NAME = "Portable historical replay"
MAIN_COMPOSE_JOB_NAME = "Bounded current P11R Compose smoke"
REQUIRED_JOBS = {
    CURRENT_JOB_ID: (CURRENT_JOB_NAME, 45),
    PORTABLE_JOB_ID: (PORTABLE_JOB_NAME, 180),
}
MAIN_COMPOSE_JOB = (MAIN_COMPOSE_JOB_NAME, 30)
EXPECTED_WORKFLOW = '# SPDX-License-Identifier: Apache-2.0\n\nname: CI\n\non:\n  pull_request:\n    branches:\n      - main\n  push:\n    branches:\n      - main\n\npermissions:\n  contents: read\n\nconcurrency:\n  group: ci-${{ github.workflow }}-${{ github.ref }}-${{ github.event_name }}\n  cancel-in-progress: false\n\njobs:\n  current-ci:\n    name: Current P12 governance non-publishing verification\n    runs-on: ubuntu-24.04\n    timeout-minutes: 45\n    steps:\n      - name: Check out exact event head\n        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6\n        with:\n          fetch-depth: 0\n          persist-credentials: false\n          ref: ${{ github.event_name == \'pull_request\' && github.event.pull_request.head.sha || github.sha }}\n      - name: Set up Python\n        uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6\n        with:\n          python-version: "3.12"\n          cache: pip\n          cache-dependency-path: requirements/p8.lock\n      - name: Set up Node.js\n        uses: actions/setup-node@249970729cb0ef3589644e2896645e5dc5ba9c38 # v6\n        with:\n          node-version-file: .nvmrc\n          cache: npm\n          cache-dependency-path: studio/package-lock.json\n      - name: Enable the package-manager integrity boundary\n        run: corepack enable\n      - name: Run current P12 governance and emit one result envelope\n        shell: bash\n        run: |\n          set +e\n          umask 077\n          gate_dir="${RUNNER_TEMP}/p12-current-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"\n          install -d -m 0700 "${gate_dir}"\n          export P12_JSON_OUTPUT="${gate_dir}/gate.json"\n          install -m 0600 /dev/null "${P12_JSON_OUTPUT}"\n          make p12-current-ci\n          gate_status=$?\n          python3 -B scripts/run_p12_toolchain.py --scope emit-ci-envelope --job-kind current_governance --gate-result "${P12_JSON_OUTPUT}" --gate-exit-status "${gate_status}"\n          envelope_status=$?\n          cleanup_status=0\n          find "${gate_dir}" -type f -delete || cleanup_status=$?\n          rmdir "${gate_dir}" || cleanup_status=$?\n          if [ "${envelope_status}" -ne 0 ]; then exit "${envelope_status}"; fi\n          if [ "${gate_status}" -ne 0 ]; then exit "${gate_status}"; fi\n          exit "${cleanup_status}"\n\n  portable-history:\n    name: Portable historical replay\n    runs-on: ubuntu-24.04\n    timeout-minutes: 180\n    steps:\n      - name: Check out exact event head\n        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6\n        with:\n          fetch-depth: 0\n          persist-credentials: false\n          ref: ${{ github.event_name == \'pull_request\' && github.event.pull_request.head.sha || github.sha }}\n      - name: Set up Python\n        uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6\n        with:\n          python-version: "3.12"\n          cache: pip\n          cache-dependency-path: requirements/p8.lock\n      - name: Set up Node.js\n        uses: actions/setup-node@249970729cb0ef3589644e2896645e5dc5ba9c38 # v6\n        with:\n          node-version-file: .nvmrc\n          cache: npm\n          cache-dependency-path: studio/package-lock.json\n      - name: Install Cosign verification tool\n        uses: sigstore/cosign-installer@6f9f17788090df1f26f669e9d70d6ae9567deba6\n        with:\n          cosign-release: v3.0.6\n      - name: Enable the package-manager integrity boundary\n        run: corepack enable\n      - name: Run portable history and emit one result envelope\n        shell: bash\n        run: |\n          set +e\n          umask 077\n          gate_dir="${RUNNER_TEMP}/p12-history-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"\n          install -d -m 0700 "${gate_dir}"\n          export P12_JSON_OUTPUT="${gate_dir}/gate.json"\n          install -m 0600 /dev/null "${P12_JSON_OUTPUT}"\n          timeout --foreground --signal=TERM --kill-after=30s 9900s make p12-portable-history\n          gate_status=$?\n          python3 -B scripts/run_p12_toolchain.py --scope emit-ci-envelope --job-kind portable_history --gate-result "${P12_JSON_OUTPUT}" --gate-exit-status "${gate_status}"\n          envelope_status=$?\n          cleanup_status=0\n          find "${gate_dir}" -type f -delete || cleanup_status=$?\n          rmdir "${gate_dir}" || cleanup_status=$?\n          if [ "${envelope_status}" -ne 0 ]; then exit "${envelope_status}"; fi\n          if [ "${gate_status}" -ne 0 ]; then exit "${gate_status}"; fi\n          exit "${cleanup_status}"\n\n  main-compose-smoke:\n    name: Bounded current P11R Compose smoke\n    if: github.event_name == \'push\' && github.ref == \'refs/heads/main\'\n    needs:\n      - current-ci\n      - portable-history\n    runs-on: ubuntu-24.04\n    timeout-minutes: 30\n    steps:\n      - name: Check out exact main push\n        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6\n        with:\n          fetch-depth: 0\n          persist-credentials: false\n          ref: ${{ github.sha }}\n      - name: Set up Python\n        uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6\n        with:\n          python-version: "3.12"\n          cache: pip\n          cache-dependency-path: requirements/p8.lock\n      - name: Run bounded current P11R Compose smoke\n        env:\n          PYTHONPATH: src\n        run: make p11r-compose-smoke\n'

_EMITTER_TAIL_BEFORE_CLEANUP = (
    "          envelope_status=$?\n"
    "          cleanup_status=0\n"
    '          find "${gate_dir}" -type f -delete || cleanup_status=$?\n'
    '          rmdir "${gate_dir}" || cleanup_status=$?\n'
    '          if [ "${envelope_status}" -ne 0 ]; then exit "${envelope_status}"; fi\n'
    '          if [ "${gate_status}" -ne 0 ]; then exit "${gate_status}"; fi\n'
    '          exit "${cleanup_status}"\n'
)
_EMITTER_TAIL_AFTER_CLEANUP = (
    "          envelope_status=$?\n"
    "          cleanup_status=0\n"
    '          find "${gate_dir}" -type f -delete || cleanup_status=$?\n'
    '          rmdir "${gate_dir}" || cleanup_status=$?\n'
    '          if [ "${envelope_status}" -ne 0 ]; then exit "${envelope_status}"; fi\n'
    '          if [ "${cleanup_status}" -ne 0 ]; then exit "${cleanup_status}"; fi\n'
    "          printf '%s\\n' \"${envelope_line}\"\n"
    '          if [ "${gate_status}" -ne 0 ]; then exit "${gate_status}"; fi\n'
    "          exit 0\n"
)
for _job_kind in ("current_governance", "portable_history"):
    _direct_emitter = (
        "          python3 -B scripts/run_p12_toolchain.py --scope emit-ci-envelope "
        f'--job-kind {_job_kind} --gate-result "${{P12_JSON_OUTPUT}}" '
        '--gate-exit-status "${gate_status}"\n'
    )
    _captured_emitter = (
        '          envelope_line="$(python3 -B scripts/run_p12_toolchain.py '
        "--scope emit-ci-envelope "
        f'--job-kind {_job_kind} --gate-result "${{P12_JSON_OUTPUT}}" '
        '--gate-exit-status "${gate_status}")"\n'
    )
    if EXPECTED_WORKFLOW.count(_direct_emitter) != 1:
        raise RuntimeError("P12 canonical emitter scaffold drifted")
    EXPECTED_WORKFLOW = EXPECTED_WORKFLOW.replace(_direct_emitter, _captured_emitter, 1)
if EXPECTED_WORKFLOW.count(_EMITTER_TAIL_BEFORE_CLEANUP) != 2:
    raise RuntimeError("P12 canonical cleanup scaffold drifted")
EXPECTED_WORKFLOW = EXPECTED_WORKFLOW.replace(
    _EMITTER_TAIL_BEFORE_CLEANUP, _EMITTER_TAIL_AFTER_CLEANUP
)

EXPECTED_ACTIONS = Counter(
    {
        f"actions/checkout@{CHECKOUT_PIN}": 3,
        f"actions/setup-python@{PYTHON_PIN}": 3,
        f"actions/setup-node@{NODE_PIN}": 2,
        f"sigstore/cosign-installer@{COSIGN_INSTALLER_PIN}": 1,
    }
)
EXPECTED_ACTIONS_BY_JOB = {
    CURRENT_JOB_ID: Counter(
        {
            f"actions/checkout@{CHECKOUT_PIN}": 1,
            f"actions/setup-python@{PYTHON_PIN}": 1,
            f"actions/setup-node@{NODE_PIN}": 1,
        }
    ),
    PORTABLE_JOB_ID: Counter(
        {
            f"actions/checkout@{CHECKOUT_PIN}": 1,
            f"actions/setup-python@{PYTHON_PIN}": 1,
            f"actions/setup-node@{NODE_PIN}": 1,
            f"sigstore/cosign-installer@{COSIGN_INSTALLER_PIN}": 1,
        }
    ),
    MAIN_COMPOSE_JOB_ID: Counter(
        {
            f"actions/checkout@{CHECKOUT_PIN}": 1,
            f"actions/setup-python@{PYTHON_PIN}": 1,
        }
    ),
}


@dataclass(frozen=True)
class _YamlLine:
    """One token in the deliberately small workflow-YAML dialect."""

    indent: int
    content: str
    number: int
    literal: str | None = None


def _fail_yaml(number: int, finding: str) -> NoReturn:
    raise P12GateError(f"P12 restricted YAML line {number}: {finding}")


def _strip_yaml_comment(value: str, number: int) -> str:
    """Remove a YAML comment without treating quoted hashes as comments."""

    quote: str | None = None
    index = 0
    while index < len(value):
        character = value[index]
        if quote == "'":
            if character == "'":
                if index + 1 < len(value) and value[index + 1] == "'":
                    index += 2
                    continue
                quote = None
        elif quote == '"':
            if character == "\\":
                index += 2
                continue
            if character == '"':
                quote = None
        elif character in {"'", '"'}:
            quote = character
        elif character == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
        index += 1
    if quote is not None:
        _fail_yaml(number, "unterminated quoted scalar")
    return value.rstrip()


def _tokenize_restricted_yaml(workflow: str) -> list[_YamlLine]:
    if workflow.startswith("\ufeff"):
        raise P12GateError("P12 workflow must not contain a UTF-8 BOM")
    if "\r" in workflow or "\t" in workflow:
        raise P12GateError("P12 workflow uses a forbidden carriage return or tab")
    if any(ord(character) < 32 and character != "\n" for character in workflow):
        raise P12GateError("P12 workflow contains a forbidden control character")

    physical = workflow.splitlines()
    tokens: list[_YamlLine] = []
    index = 0
    while index < len(physical):
        raw = physical[index]
        number = index + 1
        stripped = raw.lstrip(" ")
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        indent = len(raw) - len(stripped)
        if indent % 2:
            _fail_yaml(number, "indentation is not a multiple of two")
        content = _strip_yaml_comment(stripped, number)
        if not content:
            index += 1
            continue

        if content.endswith(": |"):
            block_indent = indent + 2
            body: list[str] = []
            index += 1
            while index < len(physical):
                candidate = physical[index]
                candidate_stripped = candidate.lstrip(" ")
                candidate_indent = len(candidate) - len(candidate_stripped)
                if candidate_stripped and candidate_indent <= indent:
                    break
                if candidate_stripped and candidate_indent < block_indent:
                    _fail_yaml(index + 1, "literal block indentation is invalid")
                body.append(candidate[block_indent:] if candidate else "")
                index += 1
            if not body or not any(line for line in body):
                _fail_yaml(number, "literal block is empty")
            tokens.append(_YamlLine(indent, content, number, "\n".join(body).rstrip("\n") + "\n"))
            continue

        if re.search(r"(?:^|\s)(?:&|\*|!{1,2})[A-Za-z0-9_.-]+(?:\s|$)", content):
            _fail_yaml(number, "YAML anchors, aliases, and tags are forbidden")
        if content.startswith("<<:") or content.startswith("- <<:"):
            _fail_yaml(number, "YAML merge keys are forbidden")
        if content.endswith((": >", ": |-", ": |+", ": >-", ": >+")):
            _fail_yaml(number, "only the plain literal-block form is permitted")
        tokens.append(_YamlLine(indent, content, number))
        index += 1
    if not tokens:
        raise P12GateError("P12 workflow YAML is empty")
    return tokens


def _split_mapping(value: str, number: int) -> tuple[str, str]:
    match = re.fullmatch(r"([A-Za-z0-9_-]+):(.*)", value)
    if match is None:
        _fail_yaml(number, "expected a simple mapping key")
    key, remainder = match.groups()
    if key == "<<":
        _fail_yaml(number, "YAML merge keys are forbidden")
    return key, remainder.strip()


def _parse_scalar(value: str, number: int) -> object:
    if not value:
        _fail_yaml(number, "empty scalar is ambiguous")
    if value[0] in "[{":
        _fail_yaml(number, "flow-style YAML is forbidden")
    if value in {"true", "false"}:
        return value == "true"
    if value in {"null", "~"}:
        return None
    if re.fullmatch(r"-?(?:0|[1-9][0-9]*)", value):
        return int(value)
    if value.startswith('"'):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            _fail_yaml(number, f"invalid double-quoted scalar: {exc.msg}")
        if not isinstance(decoded, str):
            _fail_yaml(number, "double-quoted scalar is not a string")
        return decoded
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            _fail_yaml(number, "invalid single-quoted scalar")
        return value[1:-1].replace("''", "'")
    if value.startswith(("&", "*", "!")):
        _fail_yaml(number, "YAML anchors, aliases, and tags are forbidden")
    return value


class _RestrictedYamlParser:
    def __init__(self, tokens: list[_YamlLine]) -> None:
        self.tokens = tokens

    def parse(self) -> dict[str, object]:
        value, index = self._parse_block(0, 0)
        if index != len(self.tokens):
            _fail_yaml(self.tokens[index].number, "unexpected trailing structure")
        if not isinstance(value, dict):
            raise P12GateError("P12 workflow root must be a mapping")
        return value

    def _parse_block(self, index: int, indent: int) -> tuple[object, int]:
        if index >= len(self.tokens) or self.tokens[index].indent != indent:
            number = self.tokens[index].number if index < len(self.tokens) else 0
            _fail_yaml(number, "invalid nested indentation")
        if self.tokens[index].content.startswith("-"):
            return self._parse_sequence(index, indent)
        return self._parse_mapping(index, indent)

    def _mapping_entry(
        self,
        mapping: dict[str, object],
        token: _YamlLine,
        source: str,
        index: int,
    ) -> int:
        key, remainder = _split_mapping(source, token.number)
        if key in mapping:
            _fail_yaml(token.number, f"duplicate mapping key {key!r}")
        if token.literal is not None:
            if remainder != "|":
                _fail_yaml(token.number, "invalid literal-block declaration")
            mapping[key] = token.literal
            return index + 1
        if remainder:
            mapping[key] = _parse_scalar(remainder, token.number)
            return index + 1
        child_index = index + 1
        if child_index >= len(self.tokens) or self.tokens[child_index].indent != token.indent + 2:
            _fail_yaml(token.number, f"mapping key {key!r} has no nested value")
        mapping[key], child_index = self._parse_block(child_index, token.indent + 2)
        return child_index

    def _parse_mapping(self, index: int, indent: int) -> tuple[dict[str, object], int]:
        mapping: dict[str, object] = {}
        while index < len(self.tokens):
            token = self.tokens[index]
            if token.indent < indent:
                break
            if token.indent > indent:
                _fail_yaml(token.number, "unexpected mapping indentation")
            if token.content.startswith("-"):
                break
            index = self._mapping_entry(mapping, token, token.content, index)
        return mapping, index

    def _parse_sequence(self, index: int, indent: int) -> tuple[list[object], int]:
        sequence: list[object] = []
        while index < len(self.tokens):
            token = self.tokens[index]
            if token.indent < indent:
                break
            if token.indent > indent:
                _fail_yaml(token.number, "unexpected sequence indentation")
            if token.content == "-":
                child_index = index + 1
                if child_index >= len(self.tokens) or self.tokens[child_index].indent != indent + 2:
                    _fail_yaml(token.number, "sequence item has no nested value")
                block_value, index = self._parse_block(child_index, indent + 2)
                sequence.append(block_value)
                continue
            if not token.content.startswith("- "):
                break
            source = token.content[2:].strip()
            if re.fullmatch(r"[A-Za-z0-9_-]+:.*", source):
                mapping_item: dict[str, object] = {}
                index = self._mapping_entry(mapping_item, token, source, index)
                while index < len(self.tokens) and self.tokens[index].indent == indent + 2:
                    nested = self.tokens[index]
                    if nested.content.startswith("-"):
                        break
                    index = self._mapping_entry(mapping_item, nested, nested.content, index)
                sequence.append(mapping_item)
            else:
                sequence.append(_parse_scalar(source, token.number))
                index += 1
        return sequence, index


def _parse_restricted_yaml(workflow: str) -> dict[str, object]:
    return _RestrictedYamlParser(_tokenize_restricted_yaml(workflow)).parse()


def _shell_script(lines: tuple[str, ...]) -> str:
    return "\n".join(lines) + "\n"


def _gate_commands(job_kind: str) -> tuple[str, ...]:
    if job_kind == "current_governance":
        stem = "current"
        gate = "make p12-current-ci"
    elif job_kind == "portable_history":
        stem = "history"
        gate = "timeout --foreground --signal=TERM --kill-after=30s 9900s make p12-portable-history"
    else:  # pragma: no cover - closed internal call site
        raise AssertionError(job_kind)
    return (
        "set +e",
        "umask 077",
        f'gate_dir="${{RUNNER_TEMP}}/p12-{stem}-${{GITHUB_RUN_ID}}-${{GITHUB_RUN_ATTEMPT}}"',
        'install -d -m 0700 "${gate_dir}"',
        'export P12_JSON_OUTPUT="${gate_dir}/gate.json"',
        'install -m 0600 /dev/null "${P12_JSON_OUTPUT}"',
        gate,
        "gate_status=$?",
        'envelope_line="$(python3 -B scripts/run_p12_toolchain.py --scope emit-ci-envelope '
        f'--job-kind {job_kind} --gate-result "${{P12_JSON_OUTPUT}}" '
        '--gate-exit-status "${gate_status}")"',
        "envelope_status=$?",
        "cleanup_status=0",
        'find "${gate_dir}" -type f -delete || cleanup_status=$?',
        'rmdir "${gate_dir}" || cleanup_status=$?',
        'if [ "${envelope_status}" -ne 0 ]; then exit "${envelope_status}"; fi',
        'if [ "${cleanup_status}" -ne 0 ]; then exit "${cleanup_status}"; fi',
        "printf '%s\\n' \"${envelope_line}\"",
        'if [ "${gate_status}" -ne 0 ]; then exit "${gate_status}"; fi',
        "exit 0",
    )


def _checkout_step(name: str, ref: str) -> dict[str, object]:
    return {
        "name": name,
        "uses": f"actions/checkout@{CHECKOUT_PIN}",
        "with": {"fetch-depth": 0, "persist-credentials": False, "ref": ref},
    }


def _python_step() -> dict[str, object]:
    return {
        "name": "Set up Python",
        "uses": f"actions/setup-python@{PYTHON_PIN}",
        "with": {
            "python-version": "3.12",
            "cache": "pip",
            "cache-dependency-path": "requirements/p8.lock",
        },
    }


def _node_step() -> dict[str, object]:
    return {
        "name": "Set up Node.js",
        "uses": f"actions/setup-node@{NODE_PIN}",
        "with": {
            "node-version-file": ".nvmrc",
            "cache": "npm",
            "cache-dependency-path": "studio/package-lock.json",
        },
    }


def _required_job(job_kind: str) -> dict[str, object]:
    job_id = CURRENT_JOB_ID if job_kind == "current_governance" else PORTABLE_JOB_ID
    name, timeout = REQUIRED_JOBS[job_id]
    steps: list[dict[str, object]] = [
        _checkout_step(
            "Check out exact event head",
            "${{ github.event_name == 'pull_request' && "
            "github.event.pull_request.head.sha || github.sha }}",
        ),
        _python_step(),
        _node_step(),
    ]
    if job_kind == "portable_history":
        steps.append(
            {
                "name": "Install Cosign verification tool",
                "uses": f"sigstore/cosign-installer@{COSIGN_INSTALLER_PIN}",
                "with": {"cosign-release": COSIGN_RELEASE},
            }
        )
    steps.extend(
        [
            {
                "name": "Enable the package-manager integrity boundary",
                "run": "corepack enable",
            },
            {
                "name": (
                    "Run current P12 governance and emit one result envelope"
                    if job_kind == "current_governance"
                    else "Run portable history and emit one result envelope"
                ),
                "shell": "bash",
                "run": _shell_script(_gate_commands(job_kind)),
            },
        ]
    )
    return {
        "name": name,
        "runs-on": RUNNER_FAMILY,
        "timeout-minutes": timeout,
        "steps": steps,
    }


def _expected_workflow_structure() -> dict[str, object]:
    return {
        "name": "CI",
        "on": {
            "pull_request": {"branches": ["main"]},
            "push": {"branches": ["main"]},
        },
        "permissions": {"contents": "read"},
        "concurrency": {
            "group": "ci-${{ github.workflow }}-${{ github.ref }}-${{ github.event_name }}",
            "cancel-in-progress": False,
        },
        "jobs": {
            CURRENT_JOB_ID: _required_job("current_governance"),
            PORTABLE_JOB_ID: _required_job("portable_history"),
            MAIN_COMPOSE_JOB_ID: {
                "name": MAIN_COMPOSE_JOB[0],
                "if": "github.event_name == 'push' && github.ref == 'refs/heads/main'",
                "needs": ["current-ci", "portable-history"],
                "runs-on": RUNNER_FAMILY,
                "timeout-minutes": MAIN_COMPOSE_JOB[1],
                "steps": [
                    _checkout_step("Check out exact main push", "${{ github.sha }}"),
                    _python_step(),
                    {
                        "name": "Run bounded current P11R Compose smoke",
                        "env": {"PYTHONPATH": "src"},
                        "run": "make p11r-compose-smoke",
                    },
                ],
            },
        },
    }


def _walk_workflow(value: object) -> tuple[list[str], list[str]]:
    actions: list[str] = []
    commands: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "uses" and isinstance(child, str):
                actions.append(child)
            if key == "run" and isinstance(child, str):
                commands.append(child)
            nested_actions, nested_commands = _walk_workflow(child)
            actions.extend(nested_actions)
            commands.extend(nested_commands)
    elif isinstance(value, list):
        for child in value:
            nested_actions, nested_commands = _walk_workflow(child)
            actions.extend(nested_actions)
            commands.extend(nested_commands)
    return actions, commands


def _validate_per_job_action_inventory(document: dict[str, object]) -> None:
    """Keep each immutable action in its contracted job, not merely in a global total."""

    jobs = document.get("jobs")
    if not isinstance(jobs, dict) or set(jobs) != set(EXPECTED_ACTIONS_BY_JOB):
        raise P12GateError("P12 CI job identity set is not exact")
    for job_id, expected in EXPECTED_ACTIONS_BY_JOB.items():
        job = jobs.get(job_id)
        if not isinstance(job, dict):
            raise P12GateError(f"P12 CI job {job_id!r} is not a mapping")
        actions, _ = _walk_workflow(job)
        if Counter(actions) != expected or len(actions) != sum(expected.values()):
            raise P12GateError(f"P12 action inventory for job {job_id!r} is not exact")


def _load_json_object(path: Path) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise P12GateError(f"P12 JSON duplicate key: {key}")
            value[key] = item
        return value

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise P12GateError("P12 package metadata must be a JSON object")
    return value


def check_ci_policy(root: Path) -> dict[str, object]:
    workflow_path = root / WORKFLOW_PATH
    if not workflow_path.is_file() or workflow_path.is_symlink():
        raise P12GateError("P12 CI workflow must be a regular non-symlink file")
    workflow = workflow_path.read_bytes().decode("utf-8", errors="strict")
    document = _parse_restricted_yaml(workflow)
    if document != _expected_workflow_structure():
        raise P12GateError("P12 CI workflow structure or closed command oracle differs")
    _validate_per_job_action_inventory(document)

    actions, commands = _walk_workflow(document)
    if Counter(actions) != EXPECTED_ACTIONS or len(actions) != 9:
        raise P12GateError("P12 action invocation inventory is not exactly nine")
    if any(not re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", value) for value in actions):
        raise P12GateError("P12 action reference is not immutable")
    expected_commands = [
        "corepack enable",
        _shell_script(_gate_commands("current_governance")),
        "corepack enable",
        _shell_script(_gate_commands("portable_history")),
        "make p11r-compose-smoke",
    ]
    if commands != expected_commands:
        raise P12GateError("P12 closed shell-command and lifecycle oracle changed")

    nvm = (root / ".nvmrc").read_text(encoding="utf-8")
    package = _load_json_object(root / "studio/package.json")
    if (
        nvm != f"{NODE_VERSION}\n"
        or package.get("engines", {}).get("node") != NODE_ENGINE
        or package.get("packageManager") != PACKAGE_MANAGER
    ):
        raise P12GateError("P12 Node/npm repository identity is inconsistent")

    return {
        "schema_version": 1,
        "gate": "p12_ci_policy",
        "status": "passed",
        "runner_family": RUNNER_FAMILY,
        "required_job_count": 2,
        "main_compose_job_count": 1,
        "action_pin_count": 9,
        "cosign_installer_pin": COSIGN_INSTALLER_PIN,
        "cosign_release": COSIGN_RELEASE,
        "node_version": NODE_VERSION,
        "node_engine": NODE_ENGINE,
        "npm_version": NPM_VERSION,
        "package_manager": PACKAGE_MANAGER,
        "result_envelope_count_per_required_job": 1,
        "portable_executor_deadline_seconds": 9900,
        "secret_count": 0,
        "oidc_count": 0,
        "write_permission_count": 0,
        "publication_command_count": 0,
        "artifact_transport_count": 0,
        "pull_request_compose_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        result = check_ci_policy(Path(args.root).resolve())
    except (OSError, UnicodeError, json.JSONDecodeError, P12GateError) as exc:
        print(f"P12 CI policy check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
