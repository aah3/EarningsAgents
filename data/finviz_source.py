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
            
            target_date = date.today()
            date_range = None
            if timeframe == "Next Week":
                days_ahead = 7 - target_date.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                next_monday = target_date + timedelta(days=days_ahead)
                next_friday = next_monday + timedelta(days=4)
                target_date = next_monday
                date_range = f"{next_monday.strftime('%Y-%m-%d')} to {next_friday.strftime('%Y-%m-%d')}"
            elif timeframe == "This Week":
                days_ago = target_date.weekday()
                this_monday = target_date - timedelta(days=days_ago)
                this_friday = this_monday + timedelta(days=4)
                date_range = f"{this_monday.strftime('%Y-%m-%d')} to {this_friday.strftime('%Y-%m-%d')}"
            elif timeframe == "Tomorrow":
                target_date = target_date + timedelta(days=1)
                date_range = target_date.strftime('%Y-%m-%d')
            elif timeframe == "Today":
                date_range = target_date.strftime('%Y-%m-%d')

            def format_mkt_cap(mc):
                try:
                    val = float(mc)
                    if val >= 1e12: return f"{val/1e12:.1f}T"
                    if val >= 1e9: return f"{val/1e9:.1f}B"
                    if val >= 1e6: return f"{val/1e6:.1f}M"
                    return f"{val:.1f}"
                except: return str(mc) if mc else None

            def format_volume(vol):
                try:
                    val = float(vol)
                    if val >= 1e6: return f"{val/1e6:.1f}M"
                    if val >= 1e3: return f"{val/1e3:.1f}K"
                    return f"{val:.1f}"
                except: return str(vol) if vol else None

            for r in records:
                events.append(
                    EarningsEvent(
                        ticker=r.get("Ticker", ""),
                        report_date=target_date,
                        report_time=ReportTime.UNKNOWN,
                        company_name=str(r.get("Company", "")),
                        sector=str(r.get("Sector", "")),
                        industry=str(r.get("Industry", "")),
                        market_cap=format_mkt_cap(r.get("Market Cap")),
                        volume=format_volume(r.get("Volume")),
                        date_range=date_range
                    )
                )
            return events

        except Exception as e:
            self.logger.error(f"Error fetching Finviz upcoming earnings: {e}")
            raise RuntimeError(f"DEBUG FINVIZ ERR: {e}")
