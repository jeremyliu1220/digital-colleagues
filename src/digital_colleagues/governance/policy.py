# SPDX-License-Identifier: Apache-2.0

"""Pure deterministic evaluation of typed P5 colleague policy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from digital_colleagues.core.common import require_utc
from digital_colleagues.core.policy import (
    WEEKDAY_INDEX,
    ColleaguePolicy,
    WakeBudgetPeriod,
)


def within_working_hours(policy: ColleaguePolicy, evaluated_at: datetime) -> bool:
    """Match an injected UTC instant against local weekly wall-clock windows.

    UTC-to-local conversion never fabricates a nonexistent local time. Both rollback folds
    have the same weekday/minute and therefore receive the same policy outcome.
    """

    require_utc(evaluated_at, "evaluated_at")
    local = evaluated_at.astimezone(ZoneInfo(policy.timezone))
    day = local.weekday()
    minute = local.hour * 60 + local.minute
    for window in policy.weekly_windows:
        start_day = WEEKDAY_INDEX[window.weekday]
        if window.end_minute > window.start_minute:
            if day == start_day and window.start_minute <= minute < window.end_minute:
                return True
            continue
        if day == start_day and minute >= window.start_minute:
            return True
        if day == (start_day + 1) % 7 and minute < window.end_minute:
            return True
    return False


def budget_bucket_start(period: WakeBudgetPeriod, evaluated_at: datetime) -> datetime:
    require_utc(evaluated_at, "evaluated_at")
    current = evaluated_at.astimezone(UTC)
    if period is WakeBudgetPeriod.HOUR:
        return current.replace(minute=0, second=0, microsecond=0)
    if period is WakeBudgetPeriod.DAY:
        return current.replace(hour=0, minute=0, second=0, microsecond=0)
    start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    return start - timedelta(days=start.weekday())
