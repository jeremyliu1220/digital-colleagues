# SPDX-License-Identifier: Apache-2.0

"""Stable framework-neutral application failures."""


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
