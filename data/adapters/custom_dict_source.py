"""
In-Memory Dictionary Data Provider for Earnings Agents AI.

Ideal for testing, backtesting, or embedding client static datasets.
"""

from typing import Dict, Any, Optional, List
from data.base import (
    IPriceProvider,
    IEarningsEstimateProvider,
    IFinancialsProvider,
    PriceData,
    ConsensusEstimate,
    HistoricalEarning,
    EstimateRevision,
    CompanyInfo,
)


class InMemoryCustomDataProvider(
    IPriceProvider,
    IEarningsEstimateProvider,
    IFinancialsProvider
):
    """
    Flexible custom data provider seeded from in-memory dictionary data structures.
    """

    def __init__(self, data_store: Optional[Dict[str, Any]] = None):
        self.data_store = data_store or {}

    def set_ticker_data(self, ticker: str, data: Dict[str, Any]) -> None:
        """Store custom domain payloads for a ticker."""
        self.data_store[ticker.upper()] = data

    def get_company_info(self, ticker: str) -> Optional[CompanyInfo]:
        ticker_data = self.data_store.get(ticker.upper(), {})
        info = ticker_data.get("company_info")
        if isinstance(info, CompanyInfo):
            return info
        if isinstance(info, dict):
            return CompanyInfo(**info)
        return None

    def get_price_data(self, ticker: str) -> Optional[PriceData]:
        ticker_data = self.data_store.get(ticker.upper(), {})
        price = ticker_data.get("price_data")
        if isinstance(price, PriceData):
            return price
        if isinstance(price, dict):
            return PriceData(**price)
        return None

    def get_consensus_estimates(self, ticker: str) -> Optional[ConsensusEstimate]:
        ticker_data = self.data_store.get(ticker.upper(), {})
        estimates = ticker_data.get("consensus_estimates")
        if isinstance(estimates, ConsensusEstimate):
            return estimates
        if isinstance(estimates, dict):
            return ConsensusEstimate(**estimates)
        return None

    def get_historical_earnings(self, ticker: str, num_quarters: int = 8) -> List[HistoricalEarning]:
        ticker_data = self.data_store.get(ticker.upper(), {})
        hist = ticker_data.get("historical_earnings", [])
        results = []
        for item in hist[:num_quarters]:
            if isinstance(item, HistoricalEarning):
                results.append(item)
            elif isinstance(item, dict):
                results.append(HistoricalEarning(**item))
        return results

    def get_estimate_revisions(self, ticker: str, days_back: int = 90) -> List[EstimateRevision]:
        ticker_data = self.data_store.get(ticker.upper(), {})
        revs = ticker_data.get("estimate_revisions", [])
        results = []
        for item in revs:
            if isinstance(item, EstimateRevision):
                results.append(item)
            elif isinstance(item, dict):
                results.append(EstimateRevision(**item))
        return results
