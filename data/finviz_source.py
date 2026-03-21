import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
import logging
from .base import BaseDataSource, EarningsEvent, ReportTime

try:
    from finvizfinance.screener.overview import Overview
    HAS_FINVIZ = True
except ImportError:
    HAS_FINVIZ = False

class FinvizDataSource(BaseDataSource):
    """
    Finviz Screener for capturing upcoming earnings events across major indexes.
    """
    
    def __init__(self):
        super().__init__("Finviz")
        self.screener = Overview() if HAS_FINVIZ else None

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def get_company_info(self, ticker: str) -> None: return None
    def get_price_data(self, ticker: str) -> None: return None
    def get_consensus_estimates(self, ticker: str) -> None: return None
    def get_historical_earnings(self, ticker: str, num_quarters: int = 8) -> list: return []
    def get_estimate_revisions(self, ticker: str, days_back: int = 90) -> list: return []

    def get_upcoming_earnings(self, index_name: Optional[str] = None, timeframe: str = "This Week") -> List[EarningsEvent]:
        """
        Args:
            index_name: 'S&P 500', 'DJIA', etc.
            timeframe: 'Today', 'Tomorrow', 'This Week', 'Next Week'
        """
        self._ensure_connected()
        if not HAS_FINVIZ:
            self.logger.error("finvizfinance isn't installed.")
            return []

        filters = {}
        if index_name:
            filters['Index'] = index_name
            
        filters['Earnings Date'] = timeframe

        try:
            self.screener.set_filter(filters_dict=filters)
            df = self.screener.screener_view()
            
            if df is None or df.empty:
                self.logger.info(f"No results for {index_name} at {timeframe}")
                return []
            
            records = df.to_dict('records')
            
            events = []
            for r in records:
                # Mock up an approximation of the date
                # We can't know the exact day from the general Overview easily
                target_date = date.today()
                events.append(
                    EarningsEvent(
                        ticker=r.get("Ticker", ""),
                        report_date=target_date,
                        report_time=ReportTime.UNKNOWN,
                    )
                )
            return events

        except Exception as e:
            self.logger.error(f"Error fetching Finviz upcoming earnings: {e}")
            return []
