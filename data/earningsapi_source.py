"""
EarningsAPI.com Data Source for Earnings Prediction.

Provides:
- Daily earnings calendar
- Company earnings history (actuals & estimates)
- Post-earnings price reactions
- Company profile enrichment
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

try:
    from .base import (
        BaseDataSource,
        CompanyInfo,
        PriceData,
        ConsensusEstimate,
        HistoricalEarning,
        EstimateRevision,
        DataSourceConfig,
        RateLimiter,
        normalize_ticker,
    )
except (ImportError, ValueError):
    from base import (
        BaseDataSource,
        CompanyInfo,
        PriceData,
        ConsensusEstimate,
        HistoricalEarning,
        EstimateRevision,
        DataSourceConfig,
        RateLimiter,
        normalize_ticker,
    )


def summarize_reaction(reactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Summarize the price reaction from a list of post-earnings sessions.
    reactions assumed ordered by date ascending; first entry = first post-report session.
    """
    if not reactions:
        return {"reaction_1d_pct": None, "reaction_5d_pct": None, "reaction_volume": None}
    
    # Sort reactions chronologically ascending by date to guarantee correct session slice
    sorted_reactions = sorted(reactions, key=lambda x: x.get("date", ""))
    first = sorted_reactions[0]
    window = sorted_reactions[:5]
    
    # cumulative % over up-to-5 sessions
    cum = 1.0
    for r in window:
        pc = r.get("priceChange")
        if pc is not None:
            cum *= (1.0 + pc / 100.0)
            
    return {
        "reaction_1d_pct": first.get("priceChange"),
        "reaction_5d_pct": (cum - 1.0) * 100.0 if window else None,
        "reaction_volume": first.get("volume"),
    }



class EarningsAPIDataSource(BaseDataSource):
    """
    EarningsAPI.com data source.
    """
    
    def __init__(self, config: DataSourceConfig):
        super().__init__("EarningsAPI")
        self.config = config
        self.rate_limiter = RateLimiter(
            config.rate_limit_calls,
            config.rate_limit_period
        )
        self.session = None
        self.base_url = "https://api.earningsapi.com"
        self._profile_cache = {}  # In-process cache keyed by symbol

    def connect(self) -> bool:
        """Connect to EarningsAPI API."""
        try:
            import requests
            
            if not self.config.api_key:
                raise ValueError("EarningsAPI requires an API key")
            
            try:
                from .base import create_retry_session
            except (ImportError, ValueError):
                from base import create_retry_session

            self.session = create_retry_session(
                max_retries=getattr(self.config, 'max_retries', 3)
            )
            self._connected = True
            self.logger.info("EarningsAPI initialized")
            return True
            
        except ImportError:
            self.logger.error("requests not installed.")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize EarningsAPI: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from EarningsAPI."""
        if self.session:
            self.session.close()
        self._connected = False
        self.session = None
        self.logger.info("EarningsAPI disconnected")

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make an API request to EarningsAPI with rate limiting."""
        self._ensure_connected()
        self.rate_limiter.wait_if_needed()
        
        req_params = {"apikey": self.config.api_key}
        if params:
            req_params.update(params)
            
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(
                url,
                params=req_params,
                timeout=getattr(self.config, 'timeout', 30)
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Request failed to {url}: {e}")
            raise

    def get_calendar_by_date(self, day: date) -> List[Dict[str, Any]]:
        """
        GET /v1/calendar/earnings?date=YYYY-MM-DD
        Returns normalized list of calendar events.
        """
        if isinstance(day, str):
            date_str = day
            day = date.fromisoformat(day)
        else:
            date_str = day.strftime("%Y-%m-%d")
            
        try:
            data = self._make_request("/v1/calendar/earnings", params={"date": date_str})
            if not data or not isinstance(data, dict):
                return []
            
            normalized_events = []
            buckets = {
                "pre": "BMO",
                "after": "AMC",
                "notSupplied": "UNKNOWN"
            }
            
            for bucket_key, report_time in buckets.items():
                items = data.get(bucket_key) or []
                for item in items:
                    normalized_events.append({
                        "ticker": normalize_ticker(item.get("symbol", "")),
                        "company_name": item.get("name"),
                        "report_date": day,
                        "report_time": report_time,
                        "eps_estimate": item.get("epsEstimate"),
                        "revenue_estimate": item.get("revenueEstimate"),
                        "num_estimates": item.get("noOfEsts") or item.get("numEstimates"),
                    })
            return normalized_events
        except Exception as e:
            self.logger.error(f"Error fetching calendar for {date_str}: {e}")
            return []

    def get_company_earnings(self, symbol: str) -> List[Dict[str, Any]]:
        """
        GET /v1/earnings?symbol=SYMBOL
        Returns list of past and upcoming earnings events.
        """
        ticker = normalize_ticker(symbol)
        try:
            data = self._make_request("/v1/earnings", params={"symbol": ticker})
            if not isinstance(data, list):
                return []
            return data
        except Exception as e:
            self.logger.error(f"Error fetching company earnings for {ticker}: {e}")
            return []

    def get_earnings_reactions(self, symbol: str) -> List[Dict[str, Any]]:
        """
        GET /v1/earnings-reactions?symbol=SYMBOL
        Returns list of historical price reactions.
        """
        ticker = normalize_ticker(symbol)
        try:
            data = self._make_request("/v1/earnings-reactions", params={"symbol": ticker})
            if not isinstance(data, list):
                return []
            return data
        except Exception as e:
            self.logger.error(f"Error fetching earnings reactions for {ticker}: {e}")
            return []

    def get_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        GET /v1/profile/SYMBOL
        Returns company profile.
        """
        ticker = normalize_ticker(symbol)
        if ticker in self._profile_cache:
            return self._profile_cache[ticker]
            
        try:
            data = self._make_request(f"/v1/profile/{ticker}")
            if not data or not isinstance(data, dict):
                return None
                
            normalized = {
                "company_name": data.get("companyName"),
                "sector": data.get("sector"),
                "industry": data.get("industry"),
                "market_cap": data.get("marketCap"),
                "exchange": data.get("exchange"),
                "country": data.get("country"),
                "cik": data.get("cik"),
                "outstanding_shares": data.get("outstandingShares"),
            }
            self._profile_cache[ticker] = normalized
            return normalized
        except Exception as e:
            self.logger.error(f"Error fetching profile for {ticker}: {e}")
            return None

    # Implement remaining abstract methods to satisfy ABC
    def get_company_info(self, ticker: str) -> Optional[CompanyInfo]:
        return None

    def get_price_data(self, ticker: str) -> Optional[PriceData]:
        return None

    def get_consensus_estimates(self, ticker: str) -> Optional[ConsensusEstimate]:
        return None

    def get_historical_earnings(self, ticker: str, num_quarters: int = 8) -> List[HistoricalEarning]:
        return []

    def get_estimate_revisions(self, ticker: str, days_back: int = 90) -> List[EstimateRevision]:
        return []
