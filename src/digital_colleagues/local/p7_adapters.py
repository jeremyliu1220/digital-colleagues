# SPDX-License-Identifier: Apache-2.0

"""Composition-only selection for the finite P7 adapter allowlists."""

from __future__ import annotations

from collections.abc import Mapping

from digital_colleagues.adapters.channel.reference import ReferenceChannel
from digital_colleagues.adapters.http_json.channel import HttpJsonChannel
from digital_colleagues.adapters.http_json.configuration import (
    AdapterMode,
    AdapterSelection,
    load_adapter_selection,
)
from digital_colleagues.adapters.http_json.model import HttpJsonIntelligence
from digital_colleagues.adapters.intelligence.deterministic import DeterministicIntelligence
from digital_colleagues.application.ports import IntelligencePort, ReferenceChannelPort


def build_selected_adapters(
    environment: Mapping[str, str],
) -> tuple[IntelligencePort, ReferenceChannelPort, AdapterSelection]:
    selection = load_adapter_selection(environment)
    if selection.model_mode is AdapterMode.DETERMINISTIC:
        intelligence: IntelligencePort = DeterministicIntelligence()
    else:
        assert selection.model is not None
        intelligence = HttpJsonIntelligence(selection.model)
    if selection.channel_mode is AdapterMode.REFERENCE:
        channel: ReferenceChannelPort = ReferenceChannel()
    else:
        assert selection.channel is not None
        channel = HttpJsonChannel(selection.channel)
    return intelligence, channel, selection
