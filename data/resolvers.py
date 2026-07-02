"""
resolvers.py

ReportTimeResolver  — resolves BMO/AMC/UNKNOWN for an upcoming earnings report.
FiscalPeriodResolver — resolves fiscal_quarter and fiscal_year for an upcoming report.

Both use multi-source fallback chains and return typed result objects carrying
`source` and `confidence` fields so callers can log or gate on data quality.

No external API calls are made at import time. All network I/O happens inside
the `resolve()` method of each class.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import date

try:
    from settings import ReportTime
except ImportError:
    pass

@dataclass
class ReportTimeResult:
    value: 'ReportTime'
    source: str
    confidence: str

@dataclass
class FiscalPeriodResult:
    fiscal_quarter: str
    fiscal_year: int
    source: str
    confidence: str


class ReportTimeResolver:
    def __init__(self, yahoo_source=None, finviz_source=None):
        self.yahoo_source = yahoo_source
        self.finviz_source = finviz_source

    def resolve(self, ticker: str, report_date: date) -> ReportTimeResult:
        # 1. Yahoo Finance
        if self.yahoo_source:
            try:
                ticker_obj = self.yahoo_source._get_ticker(ticker)
                cal = ticker_obj.calendar
                if cal and "Earnings Date" in cal:
                    val = cal["Earnings Date"]
                    if isinstance(val, list) and len(val) > 0:
                        val = val[0]
                    if hasattr(val, "hour"):
                        if val.hour < 12:
                            return ReportTimeResult(value=ReportTime.BMO, source="yahoo", confidence="high")
                        elif val.hour >= 16:
                            return ReportTimeResult(value=ReportTime.AMC, source="yahoo", confidence="high")
            except Exception:
                pass

        # 2. FinViz
        if self.finviz_source:
            try:
                res = self._scrape_finviz_report_time(ticker)
                if res in (ReportTime.BMO, ReportTime.AMC):
                    return ReportTimeResult(value=res, source="finviz", confidence="high")
            except Exception:
                pass

        # 3. Inference
        return ReportTimeResult(value=ReportTime.UNKNOWN, source="inferred", confidence="low")

    def _scrape_finviz_report_time(self, ticker: str) -> Optional['ReportTime']:
        from data.base import create_retry_session
        import re
        headers = {'User-Agent': 'Mozilla/5.0'}
        session = None
        try:
            session = create_retry_session(max_retries=3)
            resp = session.get(f"https://finviz.com/quote.ashx?t={ticker}", headers=headers, timeout=5)
            if resp.status_code == 200:
                match = re.search(r'Earnings.*?class="snapshot-td2".*?>(.*?)<', resp.text, re.IGNORECASE)
                if match:
                    val = match.group(1).strip()
                    if val.endswith(" AMC"):
                        return ReportTime.AMC
                    elif val.endswith(" BMO"):
                        return ReportTime.BMO
        except Exception:
            pass
        finally:
            if session:
                session.close()
        return None


class FiscalPeriodResolver:
    def __init__(self, alphavantage_source=None, yahoo_source=None, sec_source=None):
        self.alphavantage_source = alphavantage_source
        self.yahoo_source = yahoo_source
        self.sec_source = sec_source

    def _next_quarter(self, q: str, y: int) -> tuple[str, int]:
        try:
            n = int(q[1])
            if n == 4:
                return "Q1", y + 1
            return f"Q{n + 1}", y
        except Exception:
            return "Q1", y

    def resolve(self, ticker: str, report_date: date) -> FiscalPeriodResult:
        # 1. Alpha Vantage
        if self.alphavantage_source:
            try:
                hist = self.alphavantage_source.get_historical_earnings(ticker)
                if hist and len(hist) > 0:
                    most_recent = hist[0]
                    gap = (report_date - most_recent.date).days
                    if abs(gap) <= 180:
                        q, y = self._next_quarter(most_recent.fiscal_quarter, most_recent.fiscal_year)
                        return FiscalPeriodResult(fiscal_quarter=q, fiscal_year=y, source="alpha_vantage", confidence="high")
            except Exception:
                pass

        # 2. Yahoo Finance
        if self.yahoo_source:
            try:
                ticker_obj = self.yahoo_source._get_ticker(ticker)
                qe = ticker_obj.quarterly_earnings
                if qe is not None and not qe.empty:
                    last_idx = qe.index[-1]
                    q = f"Q{((last_idx.month - 1) // 3) + 1}"
                    y = last_idx.year
                    # Not advancing here to match simple instruction, or maybe I should?
                    # "Derive fiscal_quarter from the month: Q{((month - 1) // 3) + 1} and fiscal_year from the year."
                    # I'll just derive it as instructed.
                    return FiscalPeriodResult(fiscal_quarter=q, fiscal_year=y, source="yahoo", confidence="high")
            except Exception:
                pass

        # 3. SEC EDGAR
        if self.sec_source:
            try:
                filings = self.sec_source.get_filings(ticker, filing_type="10-Q", limit=1)
                if filings and len(filings) > 0:
                    f = filings[0]
                    fq = getattr(f, "fiscal_quarter", None)
                    fy = getattr(f, "fiscal_year", None)
                    if fq is not None and fy is not None:
                        return FiscalPeriodResult(fiscal_quarter=fq, fiscal_year=fy, source="sec_edgar", confidence="medium")
            except Exception:
                pass

        # 4. Inference
        try:
            q = f"Q{((report_date.month - 1) // 3) + 1}"
            y = report_date.year
        except Exception:
            q = "Q1"
            y = 2000
        return FiscalPeriodResult(fiscal_quarter=q, fiscal_year=y, source="inferred", confidence="low")
