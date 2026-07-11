"""
agent_tools.py  –  Flat-layout project root copy.

Tool registry for ReAct-loop agents. Each callable reads from pre-loaded
CompanyData and NewsArticle objects — no external API calls are made here.

FIX 3: import is now `from settings import ...` (flat layout), no config/ package.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from settings import CompanyData, NewsArticle
except ImportError:
    from config.settings import CompanyData, NewsArticle


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class ToolResult:
    """Standardised return type for every tool in AgentToolRegistry."""
    tool_name: str
    result: Any
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class AgentToolRegistry:
    """
    A collection of read-only tools that agents can invoke during a ReAct loop.

    Parameters
    ----------
    company : CompanyData
        Already-fetched company snapshot.
    news : List[NewsArticle]
        Already-fetched news articles.
    """

    def __init__(
        self,
        company: CompanyData,
        news: List[NewsArticle],
        sec_source=None,
    ) -> None:
        self.company = company
        self.news = news
        self.sec_source = sec_source

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_missing(value: Any) -> bool:
        """Return True when a value should be excluded (None or NaN float)."""
        if value is None:
            return True
        try:
            return math.isnan(float(value))
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _fmt_large_number(value: float) -> str:
        """Format a large dollar figure as $XB or $XM."""
        try:
            v = float(value)
        except (TypeError, ValueError):
            return str(value)
        abs_v = abs(v)
        sign = "-" if v < 0 else ""
        if abs_v >= 1_000_000_000:
            return f"{sign}${abs_v / 1_000_000_000:.2f}B"
        if abs_v >= 1_000_000:
            return f"{sign}${abs_v / 1_000_000:.2f}M"
        return f"{sign}${abs_v:,.2f}"

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def get_earnings_history(self) -> ToolResult:
        """Return the last 4 quarters of historical EPS beats/misses."""
        try:
            history = getattr(self.company, "historical_eps", []) or []
            last_4 = history[-4:] if len(history) >= 4 else history
            return ToolResult(
                tool_name="get_earnings_history",
                result={"quarters": last_4, "count": len(last_4)},
            )
        except Exception as exc:
            return ToolResult(tool_name="get_earnings_history", result=None, error=str(exc))

    def get_estimate_revisions(self) -> ToolResult:
        """Return the last 5 estimate revisions."""
        try:
            revisions = getattr(self.company, "estimate_revisions", []) or []
            last_5 = revisions[-5:] if len(revisions) >= 5 else revisions
            return ToolResult(
                tool_name="get_estimate_revisions",
                result={"revisions": last_5, "count": len(last_5)},
            )
        except Exception as exc:
            return ToolResult(tool_name="get_estimate_revisions", result=None, error=str(exc))

    def get_options_signals(self) -> ToolResult:
        """Return put/call ratio, IV skew, net gamma, max pain — skipping None/NaN fields."""
        try:
            opts = getattr(self.company, "options_features", None) or {}
            keys_of_interest = ["put_call_volume_ratio", "iv_skew", "net_gamma_exposure", "max_pain_to_spot"]
            signals: Dict[str, Any] = {}
            for key in keys_of_interest:
                val = opts.get(key)
                if not self._is_missing(val):
                    signals[key] = val
            for key, val in opts.items():
                if key not in signals and not self._is_missing(val):
                    signals[key] = val
            return ToolResult(tool_name="get_options_signals", result=signals)
        except Exception as exc:
            return ToolResult(tool_name="get_options_signals", result=None, error=str(exc))

    def get_sec_transcript(self, max_chars: int = 3000) -> ToolResult:
        """Return the latest transcript snippet, capped at *max_chars* characters."""
        try:
            transcripts = getattr(self.company, "recent_transcripts", None) or []
            if not transcripts:
                return ToolResult(
                    tool_name="get_sec_transcript",
                    result=None,
                    error="No transcripts available",
                )
            latest = transcripts[0]
            if isinstance(latest, str):
                snippet = latest[:max_chars]
                meta: Dict[str, Any] = {"snippet": snippet, "truncated": len(latest) > max_chars}
            elif isinstance(latest, dict):
                text = latest.get("transcript") or latest.get("text") or latest.get("content") or str(latest)
                snippet = text[:max_chars]
                meta = {
                    **{k: v for k, v in latest.items() if k not in ("text", "content")},
                    "snippet": snippet,
                    "truncated": len(text) > max_chars,
                }
            else:
                text = str(latest)
                snippet = text[:max_chars]
                meta = {"snippet": snippet, "truncated": len(text) > max_chars}
            return ToolResult(tool_name="get_sec_transcript", result=meta)
        except Exception as exc:
            return ToolResult(tool_name="get_sec_transcript", result=None, error=str(exc))

    def get_sec_transcript_by_period(
        self,
        fiscal_year: Optional[int] = None,
        fiscal_quarter: Optional[str] = None,
        max_chars: int = 4000,
    ) -> ToolResult:
        """
        Fetch an earnings call transcript for a specific fiscal period directly
        from SEC EDGAR. Requires sec_source to be set on the registry.

        Parameters
        ----------
        fiscal_year : int, optional
            Fiscal year to query (e.g. 2025). Defaults to report_date.year - 1.
        fiscal_quarter : str, optional
            One of "Q1", "Q2", "Q3", "Q4". If omitted, returns the most recent
            transcript for the given fiscal year.
        max_chars : int
            Maximum characters of transcript text to return (default 4000).
        """
        try:
            if self.sec_source is None:
                return ToolResult(
                    tool_name="get_sec_transcript_by_period",
                    result=None,
                    error=(
                        "SEC EDGAR source not available — "
                        "use get_sec_transcript for pre-loaded transcript."
                    ),
                )

            # Resolve defaults
            if fiscal_year is None:
                if self.company.fiscal_year and self.company.fiscal_year > 0:
                    fiscal_year = self.company.fiscal_year
                else:
                    report_year = (
                        self.company.report_date.year
                        if self.company.report_date else
                        __import__("datetime").date.today().year
                    )
                    fiscal_year = report_year - 1

            # Validate fiscal_quarter
            valid_quarters = {"Q1", "Q2", "Q3", "Q4", None}
            if fiscal_quarter not in valid_quarters:
                return ToolResult(
                    tool_name="get_sec_transcript_by_period",
                    result=None,
                    error=(
                        f"Invalid fiscal_quarter {fiscal_quarter!r}. "
                        "Must be one of Q1, Q2, Q3, Q4 or omitted."
                    ),
                )

            transcripts = self.sec_source.get_earnings_transcripts(
                self.company.ticker,
                year=fiscal_year,
                quarter=fiscal_quarter,
            )

            if not transcripts:
                return ToolResult(
                    tool_name="get_sec_transcript_by_period",
                    result=None,
                    error=(
                        f"No transcript found for {self.company.ticker} "
                        f"FY{fiscal_year}"
                        + (f" {fiscal_quarter}" if fiscal_quarter else "")
                        + "."
                    ),
                )

            t = transcripts[0]
            text = t.full_text or ""
            snippet = text[:max_chars]

            return ToolResult(
                tool_name="get_sec_transcript_by_period",
                result={
                    "ticker": t.ticker,
                    "fiscal_year": t.fiscal_year,
                    "fiscal_quarter": t.fiscal_quarter,
                    "filing_date": t.date.isoformat(),
                    "snippet": snippet,
                    "truncated": len(text) > max_chars,
                    "source": "SEC_EDGAR",
                    "url": t.url,
                },
            )

        except Exception as exc:
            return ToolResult(
                tool_name="get_sec_transcript_by_period",
                result=None,
                error=str(exc),
            )

    def get_sec_facts(self) -> ToolResult:
        """Return company facts dict, formatting large numbers as $XB / $XM."""
        try:
            raw_facts = getattr(self.company, "company_facts", None)
            if raw_facts is None:
                return ToolResult(
                    tool_name="get_sec_facts",
                    result=None,
                    error="company_facts not available",
                )
            formatted: Dict[str, Any] = {}
            for key, val in raw_facts.items():
                if isinstance(val, (int, float)) and not self._is_missing(val):
                    formatted[key] = self._fmt_large_number(val)
                else:
                    formatted[key] = val
            return ToolResult(tool_name="get_sec_facts", result=formatted)
        except Exception as exc:
            return ToolResult(tool_name="get_sec_facts", result=None, error=str(exc))

    def get_news_sentiment(self) -> ToolResult:
        """Return the top 10 news headlines with their sentiment scores."""
        try:
            top_10 = self.news[:10] if self.news else []
            articles = [
                {
                    "headline": a.headline,
                    "sentiment_score": a.sentiment_score,
                    "source": a.source,
                    "published_at": a.published_at.isoformat() if a.published_at else None,
                }
                for a in top_10
            ]
            return ToolResult(
                tool_name="get_news_sentiment",
                result={"articles": articles, "count": len(articles)},
            )
        except Exception as exc:
            return ToolResult(tool_name="get_news_sentiment", result=None, error=str(exc))

    def get_price_momentum(self) -> ToolResult:
        """Return current price, 5d change, 21d change, and short interest."""
        try:
            result = {
                "current_price": self.company.current_price,
                "price_change_5d": self.company.price_change_5d,
                "price_change_21d": self.company.price_change_21d,
                "short_interest": self.company.short_interest,
            }
            return ToolResult(tool_name="get_price_momentum", result=result)
        except Exception as exc:
            return ToolResult(tool_name="get_price_momentum", result=None, error=str(exc))

    def get_company_summary(self) -> ToolResult:
        """Return high-level company metadata and consensus figures."""
        try:
            c = self.company
            result = {
                "ticker": c.ticker,
                "name": c.company_name,
                "sector": c.sector,
                "industry": c.industry,
                "market_cap": self._fmt_large_number(c.market_cap) if c.market_cap else None,
                "report_date": c.report_date.isoformat() if c.report_date else None,
                "consensus_eps": c.consensus_eps,
                "consensus_revenue": self._fmt_large_number(c.consensus_revenue) if c.consensus_revenue else None,
                "num_analysts": c.num_analysts,
                "beat_rate_4q": c.beat_rate_4q,
                "avg_surprise_4q": c.avg_surprise_4q,
            }
            return ToolResult(tool_name="get_company_summary", result=result)
        except Exception as exc:
            return ToolResult(tool_name="get_company_summary", result=None, error=str(exc))

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    _TOOL_MAP: Dict[str, str] = {
        "get_earnings_history": "get_earnings_history",
        "get_estimate_revisions": "get_estimate_revisions",
        "get_options_signals": "get_options_signals",
        "get_sec_transcript": "get_sec_transcript",
        "get_sec_transcript_by_period": "get_sec_transcript_by_period",
        "get_sec_facts": "get_sec_facts",
        "get_news_sentiment": "get_news_sentiment",
        "get_price_momentum": "get_price_momentum",
        "get_company_summary": "get_company_summary",
    }

    def dispatch(self, tool_name: str, tool_args: Dict[str, Any]) -> ToolResult:
        """
        Route *tool_name* to the corresponding method.

        Returns a ToolResult with an error message for unknown tool names
        (never raises).
        """
        method_name = self._TOOL_MAP.get(tool_name)
        if method_name is None:
            return ToolResult(
                tool_name=tool_name,
                result=None,
                error=f"Unknown tool: {tool_name}",
            )
        method = getattr(self, method_name)
        try:
            return method(**tool_args) if tool_args else method()
        except TypeError as exc:
            return ToolResult(tool_name=tool_name, result=None, error=f"Bad arguments: {exc}")

    # ------------------------------------------------------------------
    # Prompt injection metadata
    # ------------------------------------------------------------------

    def get_tool_descriptions(self) -> List[Dict[str, str]]:
        """Return a list of tool descriptor dicts for prompt injection."""
        return [
            {
                "name": "get_earnings_history",
                "description": (
                    "Returns the last 4 quarters of historical EPS results, "
                    "including beat/miss/meet outcome and surprise percentage. "
                    "No arguments required."
                ),
            },
            {
                "name": "get_estimate_revisions",
                "description": (
                    "Returns the last 5 analyst EPS estimate revisions (date, "
                    "direction, and magnitude). No arguments required."
                ),
            },
            {
                "name": "get_options_signals",
                "description": (
                    "Returns options market signals: put/call ratio, IV skew, "
                    "net gamma exposure, and max pain level. Fields that are "
                    "missing or NaN are omitted. No arguments required."
                ),
            },
            {
                "name": "get_sec_transcript",
                "description": (
                    "Returns a snippet from the most recent earnings call transcript. "
                    "Optional argument: max_chars (int, default 3000) — maximum "
                    "number of characters to return."
                ),
            },
            {
                "name": "get_sec_transcript_by_period",
                "description": (
                    "Fetches an earnings call transcript directly from SEC EDGAR for a "
                    "specific fiscal period. Use this when you need a transcript for a "
                    "particular quarter, not just whatever was pre-loaded. "
                    "Optional arguments: "
                    "fiscal_year (int, e.g. 2025 — defaults to report year minus 1), "
                    "fiscal_quarter (str, one of 'Q1'/'Q2'/'Q3'/'Q4' — omit for most recent), "
                    "max_chars (int, default 4000). "
                    "Returns error if SEC EDGAR source is not available."
                ),
            },
            {
                "name": "get_sec_facts",
                "description": (
                    "Returns the company's SEC-reported financial facts dictionary. "
                    "Large numeric values are formatted as $XB or $XM for readability. "
                    "No arguments required."
                ),
            },
            {
                "name": "get_news_sentiment",
                "description": (
                    "Returns the top 10 recent news headlines along with their "
                    "sentiment scores (range −1 to +1), source, and publication date. "
                    "No arguments required."
                ),
            },
            {
                "name": "get_price_momentum",
                "description": (
                    "Returns current stock price, 5-day price change, 21-day price "
                    "change, and short interest ratio. No arguments required."
                ),
            },
            {
                "name": "get_company_summary",
                "description": (
                    "Returns a high-level company snapshot: ticker, name, sector, "
                    "industry, market cap, report date, consensus EPS, consensus "
                    "revenue, number of analysts, 4-quarter beat rate, and average "
                    "EPS surprise. No arguments required."
                ),
            },
        ]
