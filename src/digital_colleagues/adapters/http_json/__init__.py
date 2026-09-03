# SPDX-License-Identifier: Apache-2.0

"""Provider-neutral, explicitly optional HTTP JSON adapters."""

from digital_colleagues.adapters.http_json.channel import HttpJsonChannel
from digital_colleagues.adapters.http_json.configuration import (
    AdapterMode,
    AdapterSelection,
    HttpJsonSettings,
    load_adapter_selection,
)
from digital_colleagues.adapters.http_json.errors import (
    AdapterFailure,
    AdapterFailureCategory,
)
from digital_colleagues.adapters.http_json.model import HttpJsonIntelligence

__all__ = [
    "AdapterFailure",
    "AdapterFailureCategory",
    "AdapterMode",
    "AdapterSelection",
    "HttpJsonChannel",
    "HttpJsonIntelligence",
    "HttpJsonSettings",
    "load_adapter_selection",
]
