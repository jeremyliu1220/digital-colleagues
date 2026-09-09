# SPDX-License-Identifier: Apache-2.0

"""Pure, bounded, non-executable AgentPackage contracts."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from digital_colleagues.core.common import require_digest, require_stable_id
from digital_colleagues.core.errors import CoreInvariantError

AGENT_PACKAGE_SCHEMA: Final = "dc-agent/v1"
AGENT_PACKAGE_SCHEMA_VERSION: Final = 1
RUNTIME_API_VERSION: Final = "1"
PACKAGE_MAX_BYTES: Final = 65_536
PROMPT_MAX_CHARACTERS: Final = 8_192
WORKFLOW_MAX_NODES: Final = 32
WORKFLOW_MAX_DEPTH: Final = 8
WORKFLOW_MAX_STEPS: Final = 16
WORKFLOW_MAX_BRANCHES: Final = 2
LOCALES: Final = ("en-US", "zh-TW")
_VERSION = re.compile(r"(?:0|[1-9][0-9]{0,8})\.(?:0|[1-9][0-9]{0,8})\.(?:0|[1-9][0-9]{0,8})\Z")


class PackageSource(StrEnum):
    OFFICIAL_BUILTIN = "official_builtin"
    LOCAL = "local"
    GITHUB_RELEASE = "github_release"


class WorkflowStepType(StrEnum):
    INSTRUCTION = "instruction"
    CONDITION = "condition"
    PROPOSE_EFFECT = "propose_effect"
    COMPLETE = "complete"


ALLOWED_CAPABILITIES: Final = frozenset(
    {
        "read_work",
        "manage_work",
        "propose_reference_message",
        "propose_internal_record",
        "notify_human",
        "read_audit",
    }
)
ALLOWED_PREDICATES: Final = frozenset(
    {"work_is_pending", "approval_is_required", "effect_is_allowed"}
)
ALLOWED_EFFECT_KINDS: Final = frozenset({"reference_message", "internal_record", "notification"})


def _mapping(value: object, field: str, keys: frozenset[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise CoreInvariantError(f"{field} must be an object")
    if frozenset(value) != keys:
        raise CoreInvariantError(f"{field} has unknown or missing fields")
    return value


def _string(value: object, field: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CoreInvariantError(f"{field} must be an exact non-empty string")
    if len(value) > maximum:
        raise CoreInvariantError(f"{field} exceeds its fixed bound")
    return value


def _sequence(value: object, field: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise CoreInvariantError(f"{field} must be an array")
    return value


def _canonical_value(value: object) -> object:
    if value is None or isinstance(value, (str, bool)):
        return value
    if type(value) is int:
        return value
    if isinstance(value, float):
        raise CoreInvariantError("canonical package JSON does not accept floating-point values")
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise CoreInvariantError("canonical package keys must be strings")
        return {key: _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    raise CoreInvariantError("canonical package content must be JSON data")


def canonical_json_bytes(value: object) -> bytes:
    """Return the one P11 semantic JSON encoding or fail closed."""

    canonical = _canonical_value(value)
    try:
        encoded = json.dumps(
            canonical,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, UnicodeEncodeError, ValueError) as exc:
        raise CoreInvariantError("package JSON cannot be canonically encoded") from exc
    return encoded


def sha256_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


@dataclass(frozen=True, slots=True)
class LocalizedDisplay:
    name: str
    summary: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _string(self.name, "display.name", maximum=128))
        object.__setattr__(
            self,
            "summary",
            _string(self.summary, "display.summary", maximum=512),
        )

    def to_data(self) -> dict[str, object]:
        return {"name": self.name, "summary": self.summary}


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    step_id: str
    step_type: WorkflowStepType
    prompt: str | None = None
    next_step: str | None = None
    predicate: str | None = None
    on_true: str | None = None
    on_false: str | None = None
    effect_kind: str | None = None

    def __post_init__(self) -> None:
        require_stable_id(self.step_id, "workflow step id")
        if not isinstance(self.step_type, WorkflowStepType):
            raise CoreInvariantError("workflow step type is unsupported")
        if self.step_type is WorkflowStepType.INSTRUCTION:
            if self.prompt != "primary" or self.next_step is None:
                raise CoreInvariantError("instruction step binding is incomplete")
            if any(
                value is not None
                for value in (self.predicate, self.on_true, self.on_false, self.effect_kind)
            ):
                raise CoreInvariantError("instruction step has forbidden fields")
            require_stable_id(self.next_step, "workflow next step")
        elif self.step_type is WorkflowStepType.CONDITION:
            if (
                self.predicate not in ALLOWED_PREDICATES
                or self.on_true is None
                or self.on_false is None
                or self.on_true == self.on_false
            ):
                raise CoreInvariantError("condition step binding is unsupported")
            if any(value is not None for value in (self.prompt, self.next_step, self.effect_kind)):
                raise CoreInvariantError("condition step has forbidden fields")
            require_stable_id(self.on_true, "workflow true branch")
            require_stable_id(self.on_false, "workflow false branch")
        elif self.step_type is WorkflowStepType.PROPOSE_EFFECT:
            if self.effect_kind not in ALLOWED_EFFECT_KINDS or self.next_step is None:
                raise CoreInvariantError("effect proposal step binding is unsupported")
            if any(
                value is not None
                for value in (self.prompt, self.predicate, self.on_true, self.on_false)
            ):
                raise CoreInvariantError("effect proposal step has forbidden fields")
            require_stable_id(self.next_step, "workflow next step")
        elif any(
            value is not None
            for value in (
                self.prompt,
                self.next_step,
                self.predicate,
                self.on_true,
                self.on_false,
                self.effect_kind,
            )
        ):
            raise CoreInvariantError("complete step must be terminal")

    def outgoing(self) -> tuple[str, ...]:
        if self.step_type is WorkflowStepType.CONDITION:
            assert self.on_true is not None and self.on_false is not None
            return (self.on_true, self.on_false)
        if self.next_step is not None:
            return (self.next_step,)
        return ()

    def to_data(self) -> dict[str, object]:
        if self.step_type is WorkflowStepType.INSTRUCTION:
            return {
                "id": self.step_id,
                "type": self.step_type.value,
                "prompt": self.prompt,
                "next": self.next_step,
            }
        if self.step_type is WorkflowStepType.CONDITION:
            return {
                "id": self.step_id,
                "type": self.step_type.value,
                "predicate": self.predicate,
                "on_true": self.on_true,
                "on_false": self.on_false,
            }
        if self.step_type is WorkflowStepType.PROPOSE_EFFECT:
            return {
                "id": self.step_id,
                "type": self.step_type.value,
                "effect_kind": self.effect_kind,
                "next": self.next_step,
            }
        return {"id": self.step_id, "type": self.step_type.value}


@dataclass(frozen=True, slots=True)
class DeclarativeWorkflow:
    entrypoint: str
    steps: tuple[WorkflowStep, ...]

    def __post_init__(self) -> None:
        require_stable_id(self.entrypoint, "workflow entrypoint")
        steps = tuple(self.steps)
        if not 1 <= len(steps) <= WORKFLOW_MAX_NODES:
            raise CoreInvariantError("workflow node count is outside the fixed bound")
        if any(not isinstance(step, WorkflowStep) for step in steps):
            raise CoreInvariantError("workflow contains an invalid step")
        by_id = {step.step_id: step for step in steps}
        if len(by_id) != len(steps) or self.entrypoint not in by_id:
            raise CoreInvariantError("workflow identities are duplicate or incomplete")
        if any(len(step.outgoing()) > WORKFLOW_MAX_BRANCHES for step in steps):
            raise CoreInvariantError("workflow branch count exceeds the fixed bound")
        if any(target not in by_id for step in steps for target in step.outgoing()):
            raise CoreInvariantError("workflow target is unknown")

        visiting: set[str] = set()
        reachable: set[str] = set()

        def walk(step_id: str, depth: int, traversed: int) -> None:
            if depth > WORKFLOW_MAX_DEPTH or traversed > WORKFLOW_MAX_STEPS:
                raise CoreInvariantError("workflow path exceeds the fixed bound")
            if step_id in visiting:
                raise CoreInvariantError("workflow cycle or recursion is forbidden")
            visiting.add(step_id)
            reachable.add(step_id)
            step = by_id[step_id]
            outgoing = step.outgoing()
            if not outgoing and step.step_type is not WorkflowStepType.COMPLETE:
                raise CoreInvariantError("workflow path does not terminate")
            for target in outgoing:
                walk(target, depth + 1, traversed + 1)
            visiting.remove(step_id)

        walk(self.entrypoint, 1, 1)
        if reachable != set(by_id):
            raise CoreInvariantError("workflow contains unreachable steps")
        object.__setattr__(self, "steps", steps)

    def to_data(self) -> dict[str, object]:
        return {
            "entrypoint": self.entrypoint,
            "steps": [step.to_data() for step in self.steps],
        }


@dataclass(frozen=True, slots=True)
class AgentPackage:
    package_id: str
    version: str
    display_en_us: LocalizedDisplay
    display_zh_tw: LocalizedDisplay
    prompt_en_us: str
    prompt_zh_tw: str
    requested_capabilities: tuple[str, ...]
    workflow: DeclarativeWorkflow
    content_digest: str
    schema: str = AGENT_PACKAGE_SCHEMA
    schema_version: int = AGENT_PACKAGE_SCHEMA_VERSION
    runtime_api: str = RUNTIME_API_VERSION

    def __post_init__(self) -> None:
        require_stable_id(self.package_id, "package_id")
        if _VERSION.fullmatch(self.version) is None:
            raise CoreInvariantError("package version must be canonical MAJOR.MINOR.PATCH")
        if (
            self.schema != AGENT_PACKAGE_SCHEMA
            or type(self.schema_version) is not int
            or self.schema_version != AGENT_PACKAGE_SCHEMA_VERSION
        ):
            raise CoreInvariantError("AgentPackage schema is unsupported")
        if self.runtime_api != RUNTIME_API_VERSION:
            raise CoreInvariantError("AgentPackage runtime API is unsupported")
        if not isinstance(self.display_en_us, LocalizedDisplay) or not isinstance(
            self.display_zh_tw, LocalizedDisplay
        ):
            raise CoreInvariantError("localized display metadata is incomplete")
        for prompt, locale in (
            (self.prompt_en_us, "en-US"),
            (self.prompt_zh_tw, "zh-TW"),
        ):
            if (
                not isinstance(prompt, str)
                or not prompt.strip()
                or len(prompt) > PROMPT_MAX_CHARACTERS
            ):
                raise CoreInvariantError(f"{locale} prompt must be inert bounded text")
        capabilities = tuple(self.requested_capabilities)
        if not capabilities or len(capabilities) > 16:
            raise CoreInvariantError("requested capabilities are empty or exceed the fixed bound")
        if len(capabilities) != len(set(capabilities)) or any(
            capability not in ALLOWED_CAPABILITIES for capability in capabilities
        ):
            raise CoreInvariantError("requested capability is duplicate or unsupported")
        if not isinstance(self.workflow, DeclarativeWorkflow):
            raise CoreInvariantError("workflow must be finite and declarative")
        object.__setattr__(self, "requested_capabilities", capabilities)
        require_digest(self.content_digest, "content_digest")
        if self.content_digest != sha256_digest(canonical_json_bytes(self.content_data())):
            raise CoreInvariantError("package manifest and content digest do not match")
        if len(canonical_json_bytes(self.to_data())) > PACKAGE_MAX_BYTES:
            raise CoreInvariantError("canonical package exceeds the fixed byte bound")

    def metadata_data(self) -> dict[str, object]:
        return {
            "package_id": self.package_id,
            "version": self.version,
            "runtime_api": self.runtime_api,
            "display": {
                "en-US": self.display_en_us.to_data(),
                "zh-TW": self.display_zh_tw.to_data(),
            },
        }

    def content_data(self) -> dict[str, object]:
        return {
            "prompts": {"en-US": self.prompt_en_us, "zh-TW": self.prompt_zh_tw},
            "requested_capabilities": list(self.requested_capabilities),
            "workflow": self.workflow.to_data(),
        }

    def to_data(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "metadata": self.metadata_data(),
            "content": self.content_data(),
            "content_digest": self.content_digest,
        }

    @property
    def package_digest(self) -> str:
        return sha256_digest(canonical_json_bytes(self.to_data()))


def _localized_display(value: object, locale: str) -> LocalizedDisplay:
    raw = _mapping(value, f"metadata.display.{locale}", frozenset({"name", "summary"}))
    return LocalizedDisplay(
        name=_string(raw["name"], f"metadata.display.{locale}.name", maximum=128),
        summary=_string(raw["summary"], f"metadata.display.{locale}.summary", maximum=512),
    )


def _workflow_step(value: object) -> WorkflowStep:
    if not isinstance(value, Mapping) or not isinstance(value.get("type"), str):
        raise CoreInvariantError("workflow step must be an object with an explicit type")
    try:
        step_type = WorkflowStepType(value["type"])
    except ValueError as exc:
        raise CoreInvariantError("workflow step type is unsupported") from exc
    expected = {
        WorkflowStepType.INSTRUCTION: frozenset({"id", "type", "prompt", "next"}),
        WorkflowStepType.CONDITION: frozenset({"id", "type", "predicate", "on_true", "on_false"}),
        WorkflowStepType.PROPOSE_EFFECT: frozenset({"id", "type", "effect_kind", "next"}),
        WorkflowStepType.COMPLETE: frozenset({"id", "type"}),
    }[step_type]
    raw = _mapping(value, "workflow step", expected)
    step_id = _string(raw["id"], "workflow step id", maximum=128)
    if step_type is WorkflowStepType.INSTRUCTION:
        return WorkflowStep(
            step_id,
            step_type,
            prompt=_string(raw["prompt"], "workflow prompt selector", maximum=32),
            next_step=_string(raw["next"], "workflow next step", maximum=128),
        )
    if step_type is WorkflowStepType.CONDITION:
        return WorkflowStep(
            step_id,
            step_type,
            predicate=_string(raw["predicate"], "workflow predicate", maximum=64),
            on_true=_string(raw["on_true"], "workflow true branch", maximum=128),
            on_false=_string(raw["on_false"], "workflow false branch", maximum=128),
        )
    if step_type is WorkflowStepType.PROPOSE_EFFECT:
        return WorkflowStep(
            step_id,
            step_type,
            effect_kind=_string(raw["effect_kind"], "workflow effect kind", maximum=64),
            next_step=_string(raw["next"], "workflow next step", maximum=128),
        )
    return WorkflowStep(step_id, step_type)


def agent_package_from_mapping(value: object) -> AgentPackage:
    """Parse the exact schema without treating any package text as an instruction."""

    root = _mapping(
        value,
        "AgentPackage",
        frozenset({"schema", "schema_version", "metadata", "content", "content_digest"}),
    )
    if root["schema"] != AGENT_PACKAGE_SCHEMA or type(root["schema_version"]) is not int:
        raise CoreInvariantError("AgentPackage schema or version is unsupported")
    if root["schema_version"] != AGENT_PACKAGE_SCHEMA_VERSION:
        raise CoreInvariantError("AgentPackage schema or version is unsupported")
    metadata = _mapping(
        root["metadata"],
        "metadata",
        frozenset({"package_id", "version", "runtime_api", "display"}),
    )
    display = _mapping(metadata["display"], "metadata.display", frozenset(LOCALES))
    content = _mapping(
        root["content"],
        "content",
        frozenset({"prompts", "requested_capabilities", "workflow"}),
    )
    prompts = _mapping(content["prompts"], "content.prompts", frozenset(LOCALES))
    capability_values = _sequence(content["requested_capabilities"], "requested_capabilities")
    capabilities = tuple(
        _string(item, "requested capability", maximum=64) for item in capability_values
    )
    workflow = _mapping(content["workflow"], "workflow", frozenset({"entrypoint", "steps"}))
    steps = tuple(_workflow_step(item) for item in _sequence(workflow["steps"], "workflow.steps"))
    return AgentPackage(
        package_id=_string(metadata["package_id"], "package_id", maximum=128),
        version=_string(metadata["version"], "version", maximum=32),
        runtime_api=_string(metadata["runtime_api"], "runtime_api", maximum=16),
        display_en_us=_localized_display(display["en-US"], "en-US"),
        display_zh_tw=_localized_display(display["zh-TW"], "zh-TW"),
        prompt_en_us=_string(prompts["en-US"], "en-US prompt", maximum=PROMPT_MAX_CHARACTERS),
        prompt_zh_tw=_string(prompts["zh-TW"], "zh-TW prompt", maximum=PROMPT_MAX_CHARACTERS),
        requested_capabilities=capabilities,
        workflow=DeclarativeWorkflow(
            entrypoint=_string(workflow["entrypoint"], "workflow entrypoint", maximum=128),
            steps=steps,
        ),
        content_digest=_string(root["content_digest"], "content_digest", maximum=71),
    )
