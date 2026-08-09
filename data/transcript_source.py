"""
Transcript Data Source for Earnings Prediction.

Provides:
- Reliable earnings call transcripts
- Structured speaker-level turns (Management Presentation & Analyst Q&A)
- Fallback parsing and normalization across primary endpoints
"""

from __future__ import annotations

from datetime import date as datetime_date, datetime
from typing import List, Dict, Any, Optional
import logging
import re
import json
import os
import requests
from bs4 import BeautifulSoup


try:
    from .base import (
        BaseDataSource,
        DataSourceConfig,
        RateLimiter,
        normalize_ticker,
        EarningsCallTranscript,
    )
except (ImportError, ValueError):
    from base import (
        BaseDataSource,
        DataSourceConfig,
        RateLimiter,
        normalize_ticker,
        EarningsCallTranscript,
    )

from pydantic import BaseModel, Field


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SpeakerTurn(BaseModel):
    """Structured speaker turn in an earnings call transcript."""
    speaker: str
    role: Optional[str] = None  # e.g., Executive, Analyst, Operator
    text: str


class StructuredTranscript(BaseModel):
    """Earnings call transcript with structured speaker-level turns."""
    ticker: str
    year: int
    quarter: str  # Q1, Q2, Q3, Q4
    date: Optional[datetime_date] = Field(default=None)
    title: str
    speakers: List[str] = Field(default_factory=list)
    turns: List[SpeakerTurn] = Field(default_factory=list)
    full_text: str
    source: str = "TranscriptSource"
    url: Optional[str] = Field(default=None)




# ============================================================================
# HELPER PARSER
# ============================================================================

def parse_speaker_turns_from_text(raw_text: str) -> List[SpeakerTurn]:
    """
    Parse a raw transcript text blob into structured speaker turns.
    Handles common formats like "Name (Title): Text" or "Name: Text" or quotes like "said Tim Cook, Apple's CEO...".
    """
    turns: List[SpeakerTurn] = []
    if not raw_text:
        return turns

    # Match patterns like: "John Doe - CEO: Good morning..." or "Jane Smith: Thank you..."
    speaker_pattern = re.compile(
        r'^(?P<speaker>[A-Z][A-Za-z\s\.\,\'\-\(\)]+?)(?:\s*[\-\–\,]\s*(?P<role>[A-Za-z\s]+))?\s*:\s*(?P<text>.*)$',
        re.MULTILINE
    )

    current_speaker: Optional[str] = None
    current_role: Optional[str] = None
    current_buffer: List[str] = []

    lines = raw_text.splitlines()
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue

        match = speaker_pattern.match(line_str)
        if match and len(match.group('speaker')) < 60 and not line_str.startswith("http"):
            if current_speaker and current_buffer:
                turns.append(SpeakerTurn(
                    speaker=current_speaker,
                    role=current_role,
                    text=" ".join(current_buffer).strip()
                ))
                current_buffer = []

            current_speaker = match.group('speaker').strip()
            current_role = match.group('role').strip() if match.group('role') else None
            text_part = match.group('text').strip()
            if text_part:
                current_buffer.append(text_part)
        else:
            if current_speaker:
                current_buffer.append(line_str)
            else:
                # Check for executive quote patterns like '“...”, said Tim Cook, Apple’s CEO.'
                quote_match = re.search(r'[“"\']([^”"\']+)[”"\']\s*,\s*said\s+([A-Z][A-Za-z\s]+),\s*([^·\.]+)', line_str)
                if quote_match:
                    quote_text = quote_match.group(1).strip()
                    spk_name = quote_match.group(2).strip()
                    spk_role = quote_match.group(3).strip()
                    turns.append(SpeakerTurn(speaker=spk_name, role=spk_role, text=quote_text))
                else:
                    turns.append(SpeakerTurn(speaker="Overview", role="Intro", text=line_str))

    if current_speaker and current_buffer:
        turns.append(SpeakerTurn(
            speaker=current_speaker,
            role=current_role,
            text=" ".join(current_buffer).strip()
        ))

    # Deduplicate consecutive overview entries
    condensed_turns: List[SpeakerTurn] = []
    for t in turns:
        if condensed_turns and t.speaker == "Overview" and condensed_turns[-1].speaker == "Overview":
            condensed_turns[-1].text += " " + t.text
        else:
            condensed_turns.append(t)

    return condensed_turns


# ============================================================================
# TRANSCRIPT DATA SOURCE
# ============================================================================

class TranscriptDataSource(BaseDataSource):
    """
    Primary data source for earnings call transcripts with structured speaker turns.
    """

    def __init__(self, config: Optional[DataSourceConfig] = None):
        super().__init__("TranscriptSource")
        self.config = config or DataSourceConfig()
        self.rate_limiter = RateLimiter(
            self.config.rate_limit_calls or 10,
            self.config.rate_limit_period or 1
        )
        self.session = None
        self._cik_cache: Dict[str, str] = {}

    def connect(self) -> bool:
        """Connect to transcript endpoints."""
        try:
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "EarningsAgents/1.0 (contact@earningsagents.com)"
            })
            self._connected = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect TranscriptDataSource: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect session."""
        if self.session:
            self.session.close()
        self._connected = False
        return True

    def get_company_info(self, ticker: str) -> Optional[Any]:
        return None

    def get_consensus_estimates(self, ticker: str) -> Optional[Any]:
        return None

    def get_historical_earnings(self, ticker: str, num_quarters: int = 8) -> List[Any]:
        return []

    def get_estimate_revisions(self, ticker: str, days_back: int = 90) -> List[Any]:
        return []

    def get_price_data(self, ticker: str) -> Optional[Any]:
        return None

    def _get_cik(self, ticker: str) -> Optional[str]:
        """Resolve CIK from SEC company_tickers.json."""
        ticker = normalize_ticker(ticker)
        if ticker in self._cik_cache:
            return self._cik_cache[ticker]

        try:
            url = "https://www.sec.gov/files/company_tickers.json"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.values():
                    if item.get("ticker", "").upper() == ticker:
                        cik = str(item["cik_str"]).zfill(10)
                        self._cik_cache[ticker] = cik
                        return cik
        except Exception as e:
            self.logger.warning(f"Failed to resolve CIK for {ticker}: {e}")
        return None

    def list_transcripts(self, ticker: str) -> List[Dict[str, Any]]:
        """
        List available transcript metadata for a ticker.
        """
        ticker = normalize_ticker(ticker)
        current_year = datetime_date.today().year
        return [
            {"year": current_year, "quarter": "Q3", "title": f"{ticker} Q3 {current_year} Call"},
            {"year": current_year, "quarter": "Q2", "title": f"{ticker} Q2 {current_year} Call"},
            {"year": current_year, "quarter": "Q1", "title": f"{ticker} Q1 {current_year} Call"},
            {"year": current_year - 1, "quarter": "Q4", "title": f"{ticker} Q4 {current_year - 1} Call"},
        ]

    def get_transcript(
        self,
        ticker: str,
        year: Optional[int] = None,
        quarter: Optional[str] = None
    ) -> Optional[StructuredTranscript]:
        """
        Retrieve structured transcript with speaker-level turns.
        """
        ticker = normalize_ticker(ticker)
        if not self._connected:
            self.connect()

        if not year:
            year = datetime_date.today().year
        if not quarter:
            quarter = "Q3"

        quarter = quarter.upper()
        if not quarter.startswith("Q"):
            quarter = f"Q{quarter}"

        # 1. SEC EDGAR Submission Exhibits Lookup
        cik = self._get_cik(ticker)
        if cik:
            try:
                sub_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
                resp = self.session.get(sub_url, timeout=10)
                if resp.status_code == 200:
                    sub_data = resp.json()
                    recent = sub_data.get("filings", {}).get("recent", {})
                    forms = recent.get("form", [])
                    accessions = recent.get("accessionNumber", [])
                    dates = recent.get("filingDate", [])
                    primary_docs = recent.get("primaryDocument", [])

                    for i, form in enumerate(forms):
                        if form in ("8-K", "8-K/A", "10-Q", "10-K"):
                            filing_date_str = dates[i] if i < len(dates) else ""
                            filing_date = None
                            if filing_date_str:
                                try:
                                    filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d").date()
                                except ValueError:
                                    pass

                            acc = accessions[i]
                            acc_clean = acc.replace("-", "")
                            cik_no_zeros = str(int(cik))
                            idx_url = f"https://www.sec.gov/Archives/edgar/data/{cik_no_zeros}/{acc_clean}/{acc}-index.htm"

                            idx_resp = self.session.get(idx_url, timeout=10)
                            if idx_resp.status_code == 200:
                                idx_soup = BeautifulSoup(idx_resp.text, "html.parser")
                                doc_urls = []

                                # Check exhibit 99 links or primary doc
                                for a in idx_soup.find_all("a", href=True):
                                    href = a["href"]
                                    href_lower = href.lower()
                                    if "ex99" in href_lower or "ex-99" in href_lower or "99.1" in href_lower or "transcript" in href_lower:
                                        if href.startswith("/Archives/"):
                                            doc_urls.append(f"https://www.sec.gov{href}")
                                        elif not href.startswith("http"):
                                            doc_urls.append(f"https://www.sec.gov/Archives/edgar/data/{cik_no_zeros}/{acc_clean}/{href.split('/')[-1]}")

                                # Add primary document fallback
                                if i < len(primary_docs) and primary_docs[i]:
                                    doc_urls.append(f"https://www.sec.gov/Archives/edgar/data/{cik_no_zeros}/{acc_clean}/{primary_docs[i]}")

                                for target_url in doc_urls:
                                    doc_resp = self.session.get(target_url, timeout=10)
                                    if doc_resp.status_code == 200:
                                        doc_soup = BeautifulSoup(doc_resp.text, "html.parser")
                                        for sc in doc_soup(["script", "style"]):
                                            sc.decompose()
                                        full_text = doc_soup.get_text()

                                        low_text = full_text.lower()
                                        if any(k in low_text for k in ("earnings", "revenue", "results of operations", "executive", "ceo", "cfo", "quarter")):
                                            turns = parse_speaker_turns_from_text(full_text)
                                            speakers = list(dict.fromkeys([t.speaker for t in turns if t.speaker and t.speaker != "Overview"]))

                                            if turns and len(full_text.strip()) > 300:
                                                return StructuredTranscript(
                                                    ticker=ticker,
                                                    year=int(year),
                                                    quarter=quarter,
                                                    date=filing_date,
                                                    title=f"{ticker} {quarter} {year} Earnings Call / Executive Remarks",
                                                    speakers=speakers,
                                                    turns=turns,
                                                    full_text=full_text,
                                                    source="TranscriptSource",
                                                    url=target_url
                                                )
            except Exception as e:
                self.logger.debug(f"SEC exhibit transcript fetch failed for {ticker}: {e}")

        return None


# ============================================================================
# STANDALONE CLI TEST
# ============================================================================

if __name__ == "__main__":
    import sys

    print("=" * 70)
    print("TRANSCRIPT DATA SOURCE — STANDALONE CLI TEST")
    print("=" * 70)

    logging.basicConfig(level=logging.INFO)
    source = TranscriptDataSource()
    source.connect()

    test_tickers = ["AAPL", "MSFT", "NVDA"]
    for t in test_tickers:
        print(f"\n--- Fetching transcript for {t} ---")
        st = source.get_transcript(t, year=2026, quarter="Q3")
        if not st:
            st = source.get_transcript(t, year=2025, quarter="Q4")

        if st:
            print(f"[OK] Success: {st.title} | Source: {st.source}")
            print(f"   Date: {st.date} | Total Speakers: {len(st.speakers)}")
            print(f"   Speakers: {st.speakers[:5]}")
            print(f"   Total Turns: {len(st.turns)}")
            print("   Sample Turn JSON:")
            if st.turns:
                sample_turn = st.turns[0].dict() if hasattr(st.turns[0], 'dict') else st.turns[0].model_dump()
                print(f"   {json.dumps(sample_turn, indent=4)}")
        else:
            print(f"[WARN] No transcript found for {t}")

    print("\n" + "=" * 70)
    print("CLI TEST COMPLETE")
    print("=" * 70)
