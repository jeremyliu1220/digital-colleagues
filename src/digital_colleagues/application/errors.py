# SPDX-License-Identifier: Apache-2.0

"""Stable framework-neutral application failures."""

from __future__ import annotations


class ApplicationError(RuntimeError):
    """Base failure safe for typed edge mapping."""


class NotFoundError(ApplicationError):
    """A namespaced durable record was not found."""


class ConflictError(ApplicationError):
    """A revision, lease, replay, or idempotency conflict occurred."""


class StaleConflictError(ConflictError):
    """An exact revision, digest, lifecycle, or base binding is stale."""


class ReplayConflictError(ConflictError):
    """An idempotency key was rebound to different request content."""


class PermissionDeniedError(ApplicationError):
    """Server-derived authority does not permit the operation."""


class ValidationError(ApplicationError):
    """A request cannot be mapped to a valid application command."""


class PersistenceError(ApplicationError):
    """Durable state could not be read or committed safely."""


class AmbiguousEffectError(ApplicationError):
    """An effect requires reconciliation before any further dispatch."""


class ExternalAdapterError(ApplicationError):
    """A provider-neutral adapter failure safe for durable causal recording."""

    def __init__(self, *, failure_category: str, diagnostic_digest: str) -> None:
        if (
            not failure_category
            or len(failure_category) > 128
            or not failure_category.replace("_", "").isalnum()
            or not diagnostic_digest.startswith("sha256:")
            or len(diagnostic_digest) != 71
        ):
            raise ValueError("external adapter failure metadata is invalid")
        self.failure_category = failure_category
        self.diagnostic_digest = diagnostic_digest
        self.args = (
            f"external adapter failure category={failure_category} digest={diagnostic_digest}",
        )
