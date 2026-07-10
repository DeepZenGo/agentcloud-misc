"""Session-window helpers (US equity RTH)."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo


def parse_hhmm(value: str) -> time:
    h, m = value.split(":")
    return time(int(h), int(m))


def in_session(
    now: datetime | None = None,
    *,
    tz_name: str = "America/New_York",
    start: str = "09:35",
    end: str = "15:50",
    market_hours_only: bool = True,
) -> bool:
    if not market_hours_only:
        return True
    tz = ZoneInfo(tz_name)
    now = now.astimezone(tz) if now else datetime.now(tz)
    if now.weekday() >= 5:
        return False
    t = now.time()
    return parse_hhmm(start) <= t <= parse_hhmm(end)
