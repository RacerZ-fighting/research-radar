"""Application-local calendar date helpers."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE_NAME = "Asia/Shanghai"
TIMEZONE_ENV_VAR = "RESEARCH_RADAR_TIMEZONE"


def app_timezone() -> ZoneInfo:
    """Return the configured local timezone for daily views."""

    timezone_name = os.getenv(TIMEZONE_ENV_VAR, DEFAULT_TIMEZONE_NAME)
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo(DEFAULT_TIMEZONE_NAME)


def app_today() -> date:
    """Return today's date in the configured local timezone."""

    return datetime.now(app_timezone()).date()


def local_date(value: datetime | None) -> date | None:
    """Return one timestamp's configured local calendar date.

    SQLite drops timezone info for aware datetimes, so naive values are treated
    as UTC because crawler and pipeline writes use UTC timestamps.
    """

    if value is None:
        return None
    timestamp = value
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(app_timezone()).date()


def local_day_utc_range(target_date: date) -> tuple[datetime, datetime]:
    """Return UTC timestamps covering one configured local calendar day."""

    local_start = datetime.combine(target_date, time.min, tzinfo=app_timezone())
    local_end = local_start + timedelta(days=1)
    return local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc)
