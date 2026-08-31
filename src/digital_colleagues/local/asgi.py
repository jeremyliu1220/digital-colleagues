# SPDX-License-Identifier: Apache-2.0

"""Uvicorn import target for the local P4 API container."""

from digital_colleagues.local.runtime import build_app_from_environment

app = build_app_from_environment()
