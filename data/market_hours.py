from datetime import datetime, time, date
from zoneinfo import ZoneInfo
from typing import Optional, Iterable

_ET = ZoneInfo("America/New_York")
_OPEN, _CLOSE = time(9, 30), time(16, 0)

def is_market_open(now: Optional[datetime] = None, holidays: Optional[Iterable[date]] = None) -> bool:
    """US equity regular session (9:30-16:00 ET, Mon-Fri, minus supplied holidays).
    Note: does not model half-days; it's a signal label, not an execution gate."""
    now = now or datetime.now(_ET)
    et = now.astimezone(_ET) if now.tzinfo else now.replace(tzinfo=_ET)
    if et.weekday() >= 5:
        return False
    if holidays and et.date() in set(holidays):
        return False
    return _OPEN <= et.time() < _CLOSE
