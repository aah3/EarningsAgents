"""
Sample Client REST API Adapter for Earnings Agents AI.

Demonstrates connecting a client's internal microservice endpoint
to supply consensus analyst estimates and estimate revisions.
"""

from datetime import date
from typing import Optional, List
from data.base import (
    IEarningsEstimateProvider,
    ConsensusEstimate,
    HistoricalEarning,
    EstimateRevision,
    RevisionDirection,
)


class ClientAPIEstimatesProvider(IEarningsEstimateProvider):
    """
    Client adapter for fetching analyst consensus and earnings history from a REST API.
    """

    def __init__(self, api_url: str = "https://api.client.com", api_token: Optional[str] = None):
        self.api_url = api_url
        self.api_token = api_token

    def get_consensus_estimates(self, ticker: str) -> Optional[ConsensusEstimate]:
        """
        Fetch consensus estimates from client API and map to ConsensusEstimate canonical schema.
        """
        if not ticker:
            return None

        return ConsensusEstimate(
            eps_mean=2.45,
            eps_median=2.44,
            eps_high=2.55,
            eps_low=2.35,
            eps_std=0.05,
            revenue_mean=85000000000.0,
            revenue_median=84800000000.0,
            num_analysts=28,
            as_of_date=date.today()
        )

    def get_historical_earnings(self, ticker: str, num_quarters: int = 8) -> List[HistoricalEarning]:
        """
        Fetch historical quarterly earnings results from client API.
        """
        results = []
        for i in range(min(num_quarters, 4)):
            results.append(
                HistoricalEarning(
                    date=date(2025, 12 - i*3, 15),
                    actual_eps=2.10 + i * 0.10,
                    estimate_eps=2.00 + i * 0.10,
                    surprise_pct=5.0,
                    beat=True,
                    fiscal_quarter=f"Q{4-i}",
                    fiscal_year=2025
                )
            )
        return results

    def get_estimate_revisions(self, ticker: str, days_back: int = 90) -> List[EstimateRevision]:
        """
        Fetch analyst estimate revisions from client API.
        """
        return [
            EstimateRevision(
                date=date.today(),
                old_estimate=2.40,
                new_estimate=2.45,
                direction=RevisionDirection.UP,
                change_pct=2.08,
                analyst_name="Jane Doe",
                firm="Global Capital"
            )
        ]
