"""
Fiscal reporting-period helpers for `Prediction` rows.

A prediction's "reporting period" is the fiscal quarter the company is
*reporting on*, not the quarter the report date falls in — a company filing on
2026-08-13 is almost always reporting the quarter that ended around 2026-06-30.

Resolution prefers real data over arithmetic:
  1. A matching `EarningsHistory` row (populated from the earnings API sync),
     which carries an authoritative `fiscal_quarter` / `fiscal_year`.
  2. A hint passed in from the live pipeline (`CompanyData.fiscal_quarter` /
     `fiscal_year`, resolved by `data.resolvers.FiscalPeriodResolver`).
  3. A date heuristic, which is always available and never raises.

Quarters are stored in the same shape as `EarningsHistory`: `"Q1"`..`"Q4"` plus
an integer year. `format_fiscal_period` renders the display/filter token the UI
uses, e.g. `"2026Q1"`.
"""

from datetime import date, datetime, timedelta
from typing import Optional, Tuple

from sqlmodel import Session, select

from database.models import EarningsHistory

# Companies typically report 2–8 weeks after a quarter closes. Shifting the
# report date back by ~45 days lands inside the quarter being reported for the
# overwhelming majority of calendar-aligned filers.
_REPORT_LAG_DAYS = 45

# How far from the prediction's report_date an EarningsHistory row may sit and
# still be considered the same earnings event (calendars drift by a few days).
_MATCH_WINDOW_DAYS = 5


def _as_date(value) -> Optional[date]:
    """Coerce a date/datetime/ISO string to a `date`, or None if not possible."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return None


def infer_fiscal_period(report_date) -> Tuple[Optional[str], Optional[int]]:
    """Infer (quarter, year) from a report date alone. Never raises."""
    d = _as_date(report_date)
    if d is None:
        return None, None
    period_end = d - timedelta(days=_REPORT_LAG_DAYS)
    quarter = f"Q{((period_end.month - 1) // 3) + 1}"
    return quarter, period_end.year


def normalize_quarter(quarter) -> Optional[str]:
    """Normalize a quarter-ish value ("q1", 1, "Q1") to canonical "Q1"..."Q4"."""
    if quarter is None:
        return None
    text = str(quarter).strip().upper()
    if not text:
        return None
    if text.startswith("Q"):
        text = text[1:]
    try:
        n = int(text)
    except ValueError:
        return None
    if n < 1 or n > 4:
        return None
    return f"Q{n}"


def format_fiscal_period(quarter, year) -> Optional[str]:
    """Render ("Q1", 2026) as "2026Q1". Returns None when either part is missing."""
    q = normalize_quarter(quarter)
    if q is None or year is None:
        return None
    try:
        y = int(year)
    except (TypeError, ValueError):
        return None
    if y <= 0:
        return None
    return f"{y}{q}"


def parse_fiscal_period(token) -> Tuple[Optional[str], Optional[int]]:
    """Parse a "2026Q1" token back into ("Q1", 2026). Inverse of format_fiscal_period."""
    if not token:
        return None, None
    text = str(token).strip().upper()
    if "Q" not in text:
        return None, None
    year_part, _, quarter_part = text.partition("Q")
    quarter = normalize_quarter(quarter_part)
    try:
        year = int(year_part)
    except ValueError:
        return None, None
    if quarter is None or year <= 0:
        return None, None
    return quarter, year


def _lookup_earnings_history(
    session: Session, ticker: str, report_date: date
) -> Tuple[Optional[str], Optional[int]]:
    """Find the closest EarningsHistory row within the match window."""
    low = report_date - timedelta(days=_MATCH_WINDOW_DAYS)
    high = report_date + timedelta(days=_MATCH_WINDOW_DAYS)
    rows = session.exec(
        select(EarningsHistory).where(
            EarningsHistory.ticker == ticker.upper(),
            EarningsHistory.report_date >= low,
            EarningsHistory.report_date <= high,
        )
    ).all()

    candidates = [
        r for r in rows if normalize_quarter(r.fiscal_quarter) and r.fiscal_year
    ]
    if not candidates:
        return None, None

    closest = min(candidates, key=lambda r: abs((r.report_date - report_date).days))
    return normalize_quarter(closest.fiscal_quarter), int(closest.fiscal_year)


def resolve_fiscal_period(
    session: Optional[Session],
    ticker: str,
    report_date,
    hint_quarter=None,
    hint_year=None,
) -> Tuple[Optional[str], Optional[int]]:
    """
    Resolve (quarter, year) for a prediction, preferring stored earnings history,
    then a pipeline-supplied hint, then date inference. Never raises — a failure
    in any source degrades to the next one.
    """
    d = _as_date(report_date)
    if d is None:
        return None, None

    if session is not None and ticker:
        try:
            quarter, year = _lookup_earnings_history(session, ticker, d)
            if quarter and year:
                return quarter, year
        except Exception:
            pass  # fall through to hint / inference

    hint_q = normalize_quarter(hint_quarter)
    try:
        hint_y = int(hint_year) if hint_year else None
    except (TypeError, ValueError):
        hint_y = None
    if hint_q and hint_y and hint_y > 0:
        return hint_q, hint_y

    return infer_fiscal_period(d)
