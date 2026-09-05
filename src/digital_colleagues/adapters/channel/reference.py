# SPDX-License-Identifier: Apache-2.0

"""Synthetic reference channel with explicit outcomes and reconciliation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from digital_colleagues.application.contracts import (
    ChannelEffect,
    ChannelOutcome,
    ChannelOutcomeKind,
    ReconciliationKind,
    ReconciliationOutcome,
)
from digital_colleagues.core.common import FrozenJsonObject


def _digest(kind: str, effect_key: str) -> str:
    encoded = json.dumps(
        {"effect_key": effect_key, "kind": kind}, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


@dataclass(slots=True)
class ReferenceChannel:
    outcomes: tuple[ChannelOutcomeKind, ...] = (ChannelOutcomeKind.SUCCEEDED,)
    reconciliation: ReconciliationKind = ReconciliationKind.STILL_UNKNOWN
    call_count: int = 0
    reconciliation_count: int = 0
    observed_effect_keys: list[str] = field(default_factory=list)

    def apply(self, effect: ChannelEffect) -> ChannelOutcome:
        position = min(self.call_count, len(self.outcomes) - 1)
        kind = self.outcomes[position]
        self.call_count += 1
        self.observed_effect_keys.append(effect.effect_idempotency_key)
        projection = FrozenJsonObject.from_mapping({"adapter": "reference", "outcome": kind.value})
        return ChannelOutcome(kind, projection, _digest(kind.value, effect.effect_idempotency_key))

    def reconcile(
        self,
        effect_idempotency_key: str,
        binding_digest: str | None = None,
    ) -> ReconciliationOutcome:
        del binding_digest
        self.reconciliation_count += 1
        projection = FrozenJsonObject.from_mapping(
            {"adapter": "reference", "reconciliation": self.reconciliation.value}
        )
        return ReconciliationOutcome(
            self.reconciliation,
            projection,
            _digest(self.reconciliation.value, effect_idempotency_key),
        )
