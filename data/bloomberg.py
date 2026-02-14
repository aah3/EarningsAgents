"""
Bloomberg BQL Data Source for Earnings Prediction POC.

Requires Bloomberg Terminal or B-PIPE access with bql package installed.
Install: pip install bql (requires Bloomberg license)
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from config.settings import (
    BloombergConfig,
    CompanyData,
    NewsArticle,
    ReportTime,
)


class BloombergDataSource:
    """
    Bloomberg BQL data source for fetching financial data.
    
    Usage:
        config = BloombergConfig()
        ds = BloombergDataSource(config)
        ds.connect()
        
        # Get index constituents
        tickers = ds.get_index_constituents("SPX", date.today())
        
        # Get company data
        company = ds.get_company_data("AAPL", report_date)
        
        ds.disconnect()
    """
    
    def __init__(self, config: BloombergConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.bq = None
        self._connected = False
    
    def connect(self) -> bool:
        """Connect to Bloomberg BQL service."""
        try:
            import bql
            self.bq = bql.Service()
            self._connected = True
            self.logger.info("Connected to Bloomberg BQL")
            return True
        except ImportError:
            self.logger.error(
                "Bloomberg bql package not installed. "
                "Install with: pip install bql (requires Bloomberg license)"
            )
            raise
        except Exception as e:
            self.logger.error(f"Failed to connect to Bloomberg: {e}")
            raise
    
    def disconnect(self) -> None:
        """Disconnect from Bloomberg."""
        self._connected = False
        self.bq = None
        self.logger.info("Disconnected from Bloomberg")
    
    def _ensure_connected(self):
        """Ensure we're connected to Bloomberg."""
        if not self._connected or self.bq is None:
            raise RuntimeError("Not connected to Bloomberg. Call connect() first.")
    
    def get_index_constituents(
        self,
        index: str,
        as_of_date: date
    ) -> List[str]:
        """
        Get index constituents as of a specific date.
        
        Args:
            index: Index ticker (e.g., "SPX", "NDX", "RTY")
            as_of_date: Point-in-time date
            
        Returns:
            List of ticker symbols
        """
        self._ensure_connected()
        
        # Map common names to Bloomberg tickers
        index_map = {
            "SPX": "SPX Index",
            "NDX": "NDX Index",
            "RTY": "RTY Index",
            "DJI": "INDU Index",
        }
        
        bbg_index = index_map.get(index.upper(), f"{index} Index")
        
        try:
            # BQL query for historical index members
            query = f"""
            get(ID().members())
            for(['{bbg_index}'])
            with(dates=range(-1d, 0d), fill=prev)
            """
            
            # For point-in-time, use as_of
            if as_of_date < date.today():
                query = f"""
                get(ID().members())
                for(['{bbg_index}'])
                with(dates='{as_of_date.strftime("%Y-%m-%d")}', fill=prev)
                """
            
            response = self.bq.execute(query)
            df = response[0].df()
            
            # Extract tickers
            tickers = df['ID'].tolist()
            
            # Clean up ticker format (remove " US Equity" suffix)
            tickers = [t.replace(" US Equity", "").replace(" Equity", "") for t in tickers]
            
            self.logger.info(f"Found {len(tickers)} constituents for {index}")
            return tickers
            
        except Exception as e:
            self.logger.error(f"Failed to get index constituents: {e}")
            return []
    
    def get_company_info(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get basic company information.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            Dict mapping ticker to company info
        """
        self._ensure_connected()
        
        # Format tickers for BQL
        bbg_tickers = [f"{t} US Equity" for t in tickers]
        
        try:
            query = f"""
            get(
                NAME(),
                GICS_SECTOR_NAME(),
                GICS_INDUSTRY_NAME(),
                CUR_MKT_CAP()
            )
            for({bbg_tickers})
            """
            
            response = self.bq.execute(query)
            df = response[0].df()
            
            result = {}
            for _, row in df.iterrows():
                ticker = row['ID'].replace(" US Equity", "")
                result[ticker] = {
                    "name": row.get('NAME()', ticker),
                    "sector": row.get('GICS_SECTOR_NAME()', 'Unknown'),
                    "industry": row.get('GICS_INDUSTRY_NAME()', 'Unknown'),
                    "market_cap": row.get('CUR_MKT_CAP()', 0),
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get company info: {e}")
            return {}
    
    def get_earnings_calendar(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Get earnings calendar for tickers.
        
        Args:
            tickers: List of ticker symbols
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of earnings events
        """
        self._ensure_connected()
        
        bbg_tickers = [f"{t} US Equity" for t in tickers]
        
        try:
            query = f"""
            get(
                EARN_ANN_DT_TIME_HIST_WITH_EPS(),
                ANNOUNCEMENT_DT(),
                IS_EPS(),
                BEST_EPS_MEDIAN()
            )
            for({bbg_tickers})
            with(dates=range('{start_date}', '{end_date}'))
            """
            
            response = self.bq.execute(query)
            df = response[0].df()
            
            events = []
            for _, row in df.iterrows():
                ticker = row['ID'].replace(" US Equity", "")
                
                # Determine report time
                report_time_str = row.get('EARN_ANN_DT_TIME_HIST_WITH_EPS()', '')
                if 'BEF' in str(report_time_str).upper():
                    report_time = ReportTime.BMO
                elif 'AFT' in str(report_time_str).upper():
                    report_time = ReportTime.AMC
                else:
                    report_time = ReportTime.UNKNOWN
                
                events.append({
                    "ticker": ticker,
                    "report_date": row.get('ANNOUNCEMENT_DT()'),
                    "report_time": report_time,
                    "consensus_eps": row.get('BEST_EPS_MEDIAN()', 0),
                })
            
            return events
            
        except Exception as e:
            self.logger.error(f"Failed to get earnings calendar: {e}")
            return []
    
    def get_consensus_estimates(self, ticker: str) -> Dict[str, Any]:
        """
        Get consensus estimates for a company.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Dict with consensus data
        """
        self._ensure_connected()
        
        bbg_ticker = f"{ticker} US Equity"
        
        try:
            query = f"""
            get(
                BEST_EPS_MEDIAN(),
                BEST_SALES_MEDIAN(),
                BEST_EPS_HIGH(),
                BEST_EPS_LOW(),
                BEST_EPS_STD_DEV(),
                BEST_ANALYST_RECS_BULK()
            )
            for(['{bbg_ticker}'])
            """
            
            response = self.bq.execute(query)
            df = response[0].df()
            
            if df.empty:
                return {}
            
            row = df.iloc[0]
            
            return {
                "consensus_eps": row.get('BEST_EPS_MEDIAN()', 0),
                "consensus_revenue": row.get('BEST_SALES_MEDIAN()', 0),
                "eps_high": row.get('BEST_EPS_HIGH()', 0),
                "eps_low": row.get('BEST_EPS_LOW()', 0),
                "eps_std": row.get('BEST_EPS_STD_DEV()', 0),
                "num_analysts": len(row.get('BEST_ANALYST_RECS_BULK()', [])),
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get consensus for {ticker}: {e}")
            return {}
    
    def get_estimate_revisions(
        self,
        ticker: str,
        days_back: int = 90
    ) -> List[Dict[str, Any]]:
        """
        Get recent estimate revisions.
        
        Args:
            ticker: Ticker symbol
            days_back: Number of days to look back
            
        Returns:
            List of revision events
        """
        self._ensure_connected()
        
        bbg_ticker = f"{ticker} US Equity"
        start_date = date.today() - timedelta(days=days_back)
        
        try:
            query = f"""
            get(
                BEST_EPS_MEDIAN()
            )
            for(['{bbg_ticker}'])
            with(dates=range('{start_date}', '0d'), frq=d)
            """
            
            response = self.bq.execute(query)
            df = response[0].df()
            
            revisions = []
            prev_estimate = None
            
            for _, row in df.iterrows():
                current_estimate = row.get('BEST_EPS_MEDIAN()')
                revision_date = row.get('DATE')
                
                if prev_estimate is not None and current_estimate != prev_estimate:
                    revisions.append({
                        "date": revision_date,
                        "old_estimate": prev_estimate,
                        "new_estimate": current_estimate,
                        "direction": "up" if current_estimate > prev_estimate else "down",
                        "change_pct": (current_estimate - prev_estimate) / abs(prev_estimate) * 100 if prev_estimate else 0,
                    })
                
                prev_estimate = current_estimate
            
            return revisions
            
        except Exception as e:
            self.logger.error(f"Failed to get revisions for {ticker}: {e}")
            return []
    
    def get_historical_earnings(
        self,
        ticker: str,
        num_quarters: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Get historical earnings results.
        
        Args:
            ticker: Ticker symbol
            num_quarters: Number of quarters to retrieve
            
        Returns:
            List of historical earnings
        """
        self._ensure_connected()
        
        bbg_ticker = f"{ticker} US Equity"
        
        try:
            query = f"""
            get(
                IS_EPS(),
                BEST_EPS_MEDIAN(),
                ANNOUNCEMENT_DT()
            )
            for(['{bbg_ticker}'])
            with(dates=range(-{num_quarters}q, 0d), frq=q)
            """
            
            response = self.bq.execute(query)
            df = response[0].df()
            
            historical = []
            for _, row in df.iterrows():
                actual_eps = row.get('IS_EPS()', 0)
                estimate_eps = row.get('BEST_EPS_MEDIAN()', 0)
                
                if estimate_eps and estimate_eps != 0:
                    surprise_pct = (actual_eps - estimate_eps) / abs(estimate_eps) * 100
                else:
                    surprise_pct = 0
                
                historical.append({
                    "date": row.get('ANNOUNCEMENT_DT()'),
                    "actual_eps": actual_eps,
                    "estimate_eps": estimate_eps,
                    "surprise_pct": surprise_pct,
                    "beat": actual_eps > estimate_eps,
                })
            
            return historical
            
        except Exception as e:
            self.logger.error(f"Failed to get historical earnings for {ticker}: {e}")
            return []
    
    def get_price_data(self, ticker: str) -> Dict[str, Any]:
        """
        Get price and momentum data.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Dict with price data
        """
        self._ensure_connected()
        
        bbg_ticker = f"{ticker} US Equity"
        
        try:
            query = f"""
            get(
                PX_LAST(),
                CHG_PCT_5D(),
                CHG_PCT_1M(),
                CHG_PCT_3M(),
                SHORT_INT_RATIO()
            )
            for(['{bbg_ticker}'])
            """
            
            response = self.bq.execute(query)
            df = response[0].df()
            
            if df.empty:
                return {}
            
            row = df.iloc[0]
            
            return {
                "current_price": row.get('PX_LAST()', 0),
                "price_change_5d": row.get('CHG_PCT_5D()', 0) / 100,
                "price_change_21d": row.get('CHG_PCT_1M()', 0) / 100,
                "price_change_63d": row.get('CHG_PCT_3M()', 0) / 100,
                "short_interest": row.get('SHORT_INT_RATIO()', 0),
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get price data for {ticker}: {e}")
            return {}
    
    def get_news(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        max_articles: int = 50
    ) -> List[NewsArticle]:
        """
        Get news articles for a company.
        
        Args:
            ticker: Ticker symbol
            start_date: Start of date range
            end_date: End of date range
            max_articles: Maximum articles to retrieve
            
        Returns:
            List of NewsArticle objects
        """
        self._ensure_connected()
        
        bbg_ticker = f"{ticker} US Equity"
        
        try:
            query = f"""
            get(
                NEWS_HEADLINES()
            )
            for(['{bbg_ticker}'])
            with(dates=range('{start_date}', '{end_date}'))
            """
            
            response = self.bq.execute(query)
            
            articles = []
            # Parse news response (format varies)
            # This is a simplified implementation
            
            return articles[:max_articles]
            
        except Exception as e:
            self.logger.warning(f"Failed to get news for {ticker}: {e}")
            return []
    
    def get_company_data(
        self,
        ticker: str,
        report_date: date
    ) -> CompanyData:
        """
        Get all company data aggregated into CompanyData structure.
        
        Args:
            ticker: Ticker symbol
            report_date: Earnings report date
            
        Returns:
            CompanyData object
        """
        self._ensure_connected()
        
        # Get company info
        info = self.get_company_info([ticker]).get(ticker, {})
        
        # Get consensus estimates
        consensus = self.get_consensus_estimates(ticker)
        
        # Get historical earnings
        historical = self.get_historical_earnings(ticker, 8)
        
        # Calculate beat rate
        if historical:
            beats = sum(1 for h in historical[:4] if h.get("beat", False))
            beat_rate = beats / min(4, len(historical))
            avg_surprise = sum(h.get("surprise_pct", 0) for h in historical[:4]) / min(4, len(historical))
        else:
            beat_rate = None
            avg_surprise = None
        
        # Get price data
        price_data = self.get_price_data(ticker)
        
        # Get estimate revisions
        revisions = self.get_estimate_revisions(ticker, 90)
        
        return CompanyData(
            ticker=ticker,
            company_name=info.get("name", ticker),
            sector=info.get("sector", "Unknown"),
            industry=info.get("industry", "Unknown"),
            market_cap=info.get("market_cap", 0),
            report_date=report_date,
            consensus_eps=consensus.get("consensus_eps", 0),
            consensus_revenue=consensus.get("consensus_revenue", 0),
            num_analysts=consensus.get("num_analysts", 0),
            historical_eps=historical,
            beat_rate_4q=beat_rate,
            avg_surprise_4q=avg_surprise,
            current_price=price_data.get("current_price"),
            price_change_5d=price_data.get("price_change_5d"),
            price_change_21d=price_data.get("price_change_21d"),
            short_interest=price_data.get("short_interest"),
            estimate_revisions=revisions,
        )
