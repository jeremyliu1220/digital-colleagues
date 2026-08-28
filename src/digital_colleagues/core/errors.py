# SPDX-License-Identifier: Apache-2.0

"""Stable framework-independent failures raised by the pure core."""


class CoreInvariantError(ValueError):
    """A core value violates a construction-time invariant."""


class NamespaceMismatchError(CoreInvariantError):
    """Values from different namespaces were combined."""


class RevisionMismatchError(CoreInvariantError):
    """An expected immutable revision does not match."""


class AuthorizationError(CoreInvariantError):
    """A principal is not authoritative for the requested operation."""


class ReplayError(CoreInvariantError):
    """A one-time decision or idempotency key was already consumed."""


class LifecycleError(CoreInvariantError):
    """A requested lifecycle transition is invalid."""
