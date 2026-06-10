from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _normalize_ts(value: int | float | str | None) -> int:
    try:
        ts = int(float(value or 0))
    except (TypeError, ValueError):
        return 0
    if ts > 10_000_000_000:
        ts //= 1000
    return ts


def format_timestamp(value: int | float | str | None, tz_name: str = "Asia/Shanghai") -> str:
    ts = _normalize_ts(value)
    if ts <= 0:
        return "未知时间"
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = timezone(timedelta(hours=8))
    return datetime.fromtimestamp(ts, tz=tz).strftime("%m-%d %H:%M")


def now_compact() -> str:
    try:
        tz = ZoneInfo("Asia/Shanghai")
    except ZoneInfoNotFoundError:
        tz = timezone(timedelta(hours=8))
    return datetime.now(tz=tz).strftime("%Y%m%d_%H%M%S")
