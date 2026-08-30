# SPDX-License-Identifier: Apache-2.0

"""Validate stable P3 ports, typed outcomes, and caller-authority exclusions."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from digital_colleagues.application.contracts import (  # noqa: E402
    ChannelOutcomeKind,
    ReconciliationKind,
)
from digital_colleagues.core.effects import ActionResultState, EffectAttemptState  # noqa: E402

REQUIRED_PORTS = {
    "CheckpointPort",
    "ClockPort",
    "EntropyPort",
    "IdentifierPort",
    "IntelligencePort",
    "OutboxPort",
    "PersistencePort",
    "ReferenceChannelPort",
    "RequestPrincipalContextPort",
    "RuntimePersistencePort",
    "TriggerAgendaPort",
    "UnitOfWorkPort",
    "WakeCyclePort",
}
MUTATION_MODELS = {"InputEventMutation", "ApprovalMutation"}
FORBIDDEN_AUTHORITY_FIELDS = {
    "namespace",
    "namespace_scope",
    "principal",
    "principal_id",
    "principal_kind",
    "role",
    "roles",
    "tenant",
    "tenant_id",
}
FORBIDDEN_TEMPORAL_FIELDS = {"occurred_at", "valid_until"}


class RuntimeContractError(RuntimeError):
    """A required P3 runtime contract is missing or unsafe."""


def _class_fields(tree: ast.Module, name: str) -> set[str]:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return {
                child.target.id
                for child in node.body
                if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name)
            }
    raise RuntimeContractError("a required typed mutation model is missing")


def check_runtime_contracts(root: Path) -> dict[str, object]:
    ports_path = root / "src/digital_colleagues/application/ports.py"
    api_path = root / "src/digital_colleagues/api/app.py"
    contracts_path = root / "src/digital_colleagues/application/contracts.py"
    try:
        ports_tree = ast.parse(ports_path.read_text(encoding="utf-8"))
        api_tree = ast.parse(api_path.read_text(encoding="utf-8"))
        contracts_tree = ast.parse(contracts_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise RuntimeContractError("P3 contract source is unreadable") from exc
    protocol_classes = {
        node.name
        for node in ports_tree.body
        if isinstance(node, ast.ClassDef)
        and any(isinstance(base, ast.Name) and base.id == "Protocol" for base in node.bases)
    }
    if not REQUIRED_PORTS.issubset(protocol_classes):
        raise RuntimeContractError("stable application ports are incomplete")
    mutation_field_count = 0
    for model in MUTATION_MODELS:
        fields = _class_fields(api_tree, model)
        mutation_field_count += len(fields)
        if fields & FORBIDDEN_AUTHORITY_FIELDS:
            raise RuntimeContractError("an HTTP mutation accepts caller authority")
        if fields & FORBIDDEN_TEMPORAL_FIELDS:
            raise RuntimeContractError("an HTTP mutation accepts caller-controlled time")
        if "idempotency_key" not in fields:
            raise RuntimeContractError("an HTTP mutation lacks idempotency identity")
    approval_fields = _class_fields(api_tree, "ApprovalMutation")
    if "expected_mandate_revision" not in approval_fields:
        raise RuntimeContractError("concurrent approval mapping lacks expected revision")
    for request_model in ("InputEventRequest", "ApprovalRequest"):
        if _class_fields(contracts_tree, request_model) & FORBIDDEN_TEMPORAL_FIELDS:
            raise RuntimeContractError("an application request accepts caller-controlled time")
    timer_fields = _class_fields(contracts_tree, "TimerScheduleRequest")
    if not {"timer_id", "occurrence_id", "due_at", "idempotency_key"}.issubset(timer_fields):
        raise RuntimeContractError("the durable timer trigger contract is incomplete")
    ports_text = ports_path.read_text(encoding="utf-8")
    if "TimerOccurrence" not in ports_text or "def ingest_timer(" not in ports_text:
        raise RuntimeContractError("the durable timer trigger port is incomplete")
    expected_channel = {
        "succeeded",
        "known_not_executed",
        "retryable_failure",
        "permanent_failure",
        "ambiguous",
    }
    if {item.value for item in ChannelOutcomeKind} != expected_channel:
        raise RuntimeContractError("reference channel outcomes are incomplete")
    if {item.value for item in ReconciliationKind} != {
        "confirmed_applied",
        "confirmed_absent",
        "still_unknown",
    }:
        raise RuntimeContractError("ambiguity reconciliation outcomes are incomplete")
    if "ambiguous" not in {item.value for item in EffectAttemptState}:
        raise RuntimeContractError("effect attempt ambiguity is not typed")
    required_results = {
        "succeeded",
        "not_executed",
        "retryable_failure",
        "permanent_failure",
        "ambiguous",
    }
    if not required_results.issubset({item.value for item in ActionResultState}):
        raise RuntimeContractError("action result classifications are incomplete")
    return {
        "schema_version": 1,
        "gate": "p3_runtime_contracts_clean",
        "stable_port_count": len(REQUIRED_PORTS),
        "mutation_model_count": len(MUTATION_MODELS),
        "mutation_field_count": mutation_field_count,
        "caller_authority_field_count": 0,
        "caller_temporal_field_count": 0,
        "timer_trigger_contract": "passed",
        "channel_outcome_count": len(ChannelOutcomeKind),
        "reconciliation_outcome_count": len(ReconciliationKind),
        "ambiguous_attempt_state": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate P3 stable runtime contracts.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_runtime_contracts(Path(arguments.root))
    except RuntimeContractError as exc:
        print(f"P3 runtime contract check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
