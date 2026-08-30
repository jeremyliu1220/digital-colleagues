# SPDX-License-Identifier: Apache-2.0

"""Bounded in-process worker facade; no loop, network binding, or hidden clock."""

from __future__ import annotations

from dataclasses import dataclass

from digital_colleagues.application.contracts import DispatchResult, WakeRunResult
from digital_colleagues.application.services import DispatchService, WakeService
from digital_colleagues.core.namespace import Namespace


@dataclass(frozen=True, slots=True)
class WorkerOutcome:
    trigger_materialized: bool
    wake: WakeRunResult
    dispatch: DispatchResult


class HeadlessWorker:
    def __init__(self, wake: WakeService, dispatch: DispatchService) -> None:
        self._wake = wake
        self._dispatch = dispatch

    def run_once(self, namespace: Namespace) -> WorkerOutcome:
        materialized = self._wake.materialize_next(namespace) is not None
        wake = self._wake.run(namespace)
        dispatch = self._dispatch.dispatch_once(namespace)
        return WorkerOutcome(materialized, wake, dispatch)
