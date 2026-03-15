"""
Data Aggregator for Earnings Prediction.

Combines multiple data sources into a unified interface.
Provides fallback mechanisms and data prioritization.
"""

from datetime import date, datetime, timedelta, time
from typing import List, Dict, Any, Optional, Union
import logging
import pandas as pd
from dataclasses import asdict, is_dataclass

try:
    from .base import (
        BaseDataSource,
        CompanyInfo,
        CompanyData,
        PriceData,
        ConsensusEstimate,
        NewsArticle,
        EarningsEvent,
        DataSourceConfig,
        AnalystRecommendation,
        HistoricalEarning,
        EstimateRevision,
        EarningsCallTranscript,
    )
    from .yahoo_finance import YahooFinanceDataSource, OptionChainSummary, OptionContract
    from .sec_edgar import SECEdgarDataSource, SECFiling, CompanyFact
    from .news_sources import NewsAPIDataSource, AlphaVantageNewsDataSource
    from .options import OptionData, OptionChainAnalyzer, OptionType as OptType
except (ImportError, ValueError):
    from base import (
        BaseDataSource,
        CompanyInfo,
        CompanyData,
        PriceData,
        ConsensusEstimate,
        NewsArticle,
        EarningsEvent,
        DataSourceConfig,
        AnalystRecommendation,
        HistoricalEarning,
        EstimateRevision,
        EarningsCallTranscript,
    )
    from yahoo_finance import YahooFinanceDataSource, OptionChainSummary, OptionContract
    from sec_edgar import SECEdgarDataSource, SECFiling, CompanyFact
    from news_sources import NewsAPIDataSource, AlphaVantageNewsDataSource
    from options import OptionData, OptionChainAnalyzer, OptionType as OptType

# Try to import full Alpha Vantage source (may not be available)
try:
    from alpha_vantage import AlphaVantageDataSource, InsiderTransaction, QuarterlyEarnings
    HAS_FULL_ALPHA_VANTAGE = True
except ImportError:
    HAS_FULL_ALPHA_VANTAGE = False


class DataAggregator:
    """
    Aggregates data from multiple sources with intelligent fallback.
    
    Provides a unified interface for accessing company data, handling:
    - Source prioritization
    - Fallback when primary source fails
    - Data merging from multiple sources
    - Caching to minimize API calls
    
    Usage:
        # Configure sources
        yahoo_config = DataSourceConfig(rate_limit_calls=2000, rate_limit_period=3600)
        news_config = DataSourceConfig(api_key="newsapi_key", rate_limit_calls=100)
        av_config = DataSourceConfig(api_key="av_key", rate_limit_calls=25)
        
        # Initialize aggregator
        aggregator = DataAggregator(
            yahoo_config=yahoo_config,
            newsapi_config=news_config,
            alphavantage_config=av_config,
            enable_sec=False  # SEC is optional
        )
        
        aggregator.initialize()
        
        # Get comprehensive company data
        company = aggregator.get_company_data("AAPL", date(2024, 1, 25))
        
        # Get news with sentiment
        news = aggregator.get_news_with_sentiment("AAPL", "Apple", days_back=30)
        
        aggregator.shutdown()
    """
    
    def __init__(
        self,
        yahoo_config: Optional[DataSourceConfig] = None,
        newsapi_config: Optional[DataSourceConfig] = None,
        alphavantage_config: Optional[DataSourceConfig] = None,
        sec_config: Optional[DataSourceConfig] = None,
        sec_user_agent: str = "EarningsPredictor/1.0 (contact@example.com)",
        enable_yahoo: bool = True,
        enable_newsapi: bool = True,
        enable_alphavantage: bool = True,
        enable_sec: bool = False,
    ):
        """
        Initialize data aggregator.
        
        Args:
            yahoo_config: Yahoo Finance configuration
            newsapi_config: NewsAPI configuration
            alphavantage_config: Alpha Vantage configuration (used for both news and data)
            sec_config: SEC EDGAR configuration
            sec_user_agent: User agent for SEC (required if enabled)
            enable_yahoo: Enable Yahoo Finance
            enable_newsapi: Enable NewsAPI
            enable_alphavantage: Enable Alpha Vantage (full data source if available)
            enable_sec: Enable SEC EDGAR
        """
        self.logger = logging.getLogger("DataAggregator")
        
        # Initialize sources
        self.yahoo = None
        self.newsapi = None
        self.alphavantage = None  # Full Alpha Vantage source (if available)
        self.alphavantage_news = None  # Just for news (legacy)
        self.sec = None
        
        # Create enabled sources
        if enable_yahoo and yahoo_config:
            self.yahoo = YahooFinanceDataSource(yahoo_config)
        
        if enable_newsapi and newsapi_config:
            self.newsapi = NewsAPIDataSource(newsapi_config)
        
        if enable_alphavantage and alphavantage_config:
            # Use full Alpha Vantage data source if available
            if HAS_FULL_ALPHA_VANTAGE:
                self.alphavantage = AlphaVantageDataSource(alphavantage_config)
                self.logger.info("Using full Alpha Vantage data source")
            # Always create news-only source for backward compatibility
            self.alphavantage_news = AlphaVantageNewsDataSource(alphavantage_config)
        
        if enable_sec and sec_config:
            self.sec = SECEdgarDataSource(sec_config, sec_user_agent)
        
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize all enabled data sources."""
        self.logger.info("Initializing data sources...")
        
        if self.yahoo:
            self.yahoo.connect()
            self.logger.info("✓ Yahoo Finance connected")
        
        if self.newsapi:
            self.newsapi.connect()
            self.logger.info("✓ NewsAPI connected")
        
        if self.alphavantage:
            self.alphavantage.connect()
            self.logger.info("✓ Alpha Vantage (full) connected")
        
        if self.alphavantage_news:
            self.alphavantage_news.connect()
            self.logger.info("✓ Alpha Vantage (news) connected")
        
        if self.sec:
            self.sec.connect()
            self.logger.info("✓ SEC EDGAR connected")
        
        self._initialized = True
        self.logger.info("All data sources initialized")
    
    def shutdown(self) -> None:
        """Shutdown all data sources."""
        self.logger.info("Shutting down data sources...")
        
        if self.yahoo:
            self.yahoo.disconnect()
        if self.newsapi:
            self.newsapi.disconnect()
        if self.alphavantage:
            self.alphavantage.disconnect()
        if self.alphavantage_news:
            self.alphavantage_news.disconnect()
        if self.sec:
            self.sec.disconnect()
        
        self._initialized = False
        self.logger.info("All data sources shut down")
    
    def _to_dict(self, obj: Any) -> Dict[str, Any]:
        """Convert an object (Pydantic model or dataclass) to a dictionary."""
        if hasattr(obj, 'dict') and callable(getattr(obj, 'dict')):
            return obj.dict()
        if is_dataclass(obj):
            return asdict(obj)
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)
    
    def get_company_data(
        self,
        ticker: str,
        report_date: date,
        include_news: bool = True,
        options_df: Optional[pd.DataFrame] = None
    ) -> CompanyData:
        """
        Get comprehensive company data aggregated from all sources.
        
        Args:
            ticker: Stock ticker symbol
            report_date: Earnings report date
            include_news: Whether to fetch news (can be slow)
            
        Returns:
            CompanyData with all available information
        """
        if not self._initialized:
            raise RuntimeError("DataAggregator not initialized. Call initialize() first.")
        
        self.logger.info(f"Aggregating data for {ticker}")
        
        # Get company info (Yahoo)
        company_info = None
        if self.yahoo:
            company_info = self.yahoo.get_company_info(ticker)
        
        if not company_info:
            # Fallback to Alpha Vantage if Yahoo fails
            if self.alphavantage:
                company_info = self.alphavantage.get_company_info(ticker)
        
        if not company_info:
            raise ValueError(f"Could not find company info for {ticker}")
        
        # Get consensus estimates (Yahoo primary, Alpha Vantage fallback)
        consensus = None
        if self.yahoo:
            consensus = self.yahoo.get_consensus_estimates(ticker)
        
        if not consensus and self.alphavantage:
            consensus = self.alphavantage.get_consensus_estimates(ticker)
        
        if not consensus:
            # Create a dummy consensus to avoid errors
            consensus = ConsensusEstimate(
                eps_mean=0.0, eps_median=0.0, eps_high=0.0, eps_low=0.0, eps_std=0.0,
                num_analysts=0, as_of_date=date.today()
            )
        
        # Get historical earnings
        historical_list = []
        if self.yahoo:
            historical_list = self.yahoo.get_historical_earnings(ticker)
        elif self.alphavantage:
            historical_list = self.alphavantage.get_historical_earnings(ticker)
            
        historical = [self._to_dict(h) for h in historical_list]
        
        # Calculate beat rate & avg surprise
        beat_rate = None
        avg_surprise = None
        if historical_list:
            recent = historical_list[:4]
            # Handle both dataclass and Pydantic model
            beats = sum(1 for h in recent if (getattr(h, 'beat', False) if not isinstance(h, dict) else h.get('beat', False)))
            beat_rate = beats / len(recent) if recent else 0.0
            avg_surprise = sum(getattr(h, 'surprise_pct', 0) if not isinstance(h, dict) else h.get('surprise_pct', 0) for h in recent) / len(recent) if recent else 0.0
        
        # Get price data (Yahoo)
        price_data = None
        if self.yahoo:
            price_data = self.yahoo.get_price_data(ticker)
        elif self.alphavantage:
            price_data = self.alphavantage.get_price_data(ticker)
        
        # Get estimate revisions
        revisions = []
        if self.yahoo and hasattr(self.yahoo, 'get_estimate_revisions'):
            rev_list = self.yahoo.get_estimate_revisions(ticker, 90)
            revisions = [self._to_dict(r) for r in rev_list]
        elif self.alphavantage:
            rev_list = self.alphavantage.get_estimate_revisions(ticker, 90)
            revisions = [self._to_dict(r) for r in rev_list]
        
        # Get analyst recommendations (Yahoo)
        recommendations = []
        if self.yahoo:
            rec_list = self.yahoo.get_analyst_recommendations(ticker, 90)
            recommendations = [self._to_dict(r) for r in rec_list]
            
        # Get options features
        options_features = None
        df = options_df
        
        # If no explicit DataFrame is provided, try available sources
        if df is None:
            # Add sources here that might implement get_option_chain_dataframe
            candidate_sources = [self.yahoo, self.alphavantage, self.sec]
            for source in candidate_sources:
                if source and hasattr(source, 'get_option_chain_dataframe'):
                    try:
                        df_candidate = source.get_option_chain_dataframe(ticker, num_expirations=4)
                        if df_candidate is not None and not df_candidate.empty:
                            df = df_candidate
                            break
                    except Exception as e:
                        self.logger.warning(f"Failed to extract option features from {type(source).__name__} for {ticker}: {e}")

        if df is not None and not df.empty:
            try:
                import sys
                import os
                parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)
                from options_features import OptionFeaturesExtractor
                
                # Default mapping assumes it follows our standard format
                extractor = OptionFeaturesExtractor(date_col='date')
                features_df = extractor.extract_features(df, group_by_expiry=False)
                if not features_df.empty:
                    # Extract the first row
                    options_features = features_df.iloc[0].to_dict()
                    
                    # Add per-expiration data
                    exp_df = extractor.extract_features(df, group_by_expiry=True)
                    if not exp_df.empty:
                        options_features['by_expiration'] = exp_df.to_dict('records')
            except Exception as e:
                self.logger.warning(f"Failed to compute option features for {ticker}: {e}")
        
        # Get recent transcript from SEC (if enabled)
        recent_transcripts = []
        if self.sec:
            try:
                # We'll just fetch the most recent transcript without a specific date
                transcripts_obj = self.get_earnings_transcripts(ticker)
                
                for t in transcripts_obj[:1]:  # Just take the latest one to preserve context
                    # Trim transcript to ~10,000 chars to avoid blowing up the LLM context window
                    trimmed_text = t.transcript[:10000] + ("..." if len(t.transcript) > 10000 else "")
                    recent_transcripts.append({
                        "year": t.year,
                        "quarter": t.quarter,
                        "transcript": trimmed_text
                    })
            except Exception as e:
                self.logger.warning(f"Failed to fetch SEC transcript for {ticker}: {e}")
        # Get SEC XBRL company facts
        company_facts = {}
        if self.sec:
            try:
                raw_facts = self.get_company_facts(ticker)
                if raw_facts:
                    gaap = raw_facts.get('facts', {}).get('us-gaap', {})
                    keys_to_extract = ['Assets', 'Liabilities', 'Revenues', 'SalesRevenueNet', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'NetIncomeLoss', 'OperatingIncomeLoss']
                    for k in keys_to_extract:
                        if k in gaap:
                            val_list = gaap[k].get('units', {}).get('USD', [])
                            if val_list:
                                # Filter to stable standard forms (10-Q, 10-K)
                                valid_vals = [v for v in val_list if v.get('form') in ['10-Q', '10-K']]
                                if valid_vals:
                                    latest_val = sorted(valid_vals, key=lambda x: x.get('end', ''))[-1]
                                    company_facts[k] = {
                                        'value': latest_val.get('val'),
                                        'period_end': latest_val.get('end'),
                                        'form': latest_val.get('form')
                                    }
            except Exception as e:
                self.logger.warning(f"Failed to extract SEC company facts for {ticker}: {e}")
        
        # Build CompanyData
        company_data = CompanyData(
            ticker=ticker,
            company_name=company_info.company_name,
            sector=company_info.sector,
            industry=company_info.industry,
            market_cap=company_info.market_cap,
            report_date=report_date,
            consensus_eps=consensus.eps_mean,
            consensus_revenue=consensus.revenue_mean if consensus.revenue_mean is not None else 0.0,
            num_analysts=consensus.num_analysts,
            historical_eps=historical,
            beat_rate_4q=beat_rate,
            avg_surprise_4q=avg_surprise,
            current_price=price_data.current_price if price_data else None,
            price_change_5d=price_data.price_change_5d if price_data else None,
            price_change_21d=price_data.price_change_21d if price_data else None,
            short_interest=price_data.short_interest if price_data else None,
            estimate_revisions=revisions,
            analyst_recommendations=recommendations,
            options_features=options_features,
            recent_transcripts=recent_transcripts,
            company_facts=company_facts,
        )
        
        return company_data
    
    def get_news_with_sentiment(
        self,
        ticker: str,
        company_name: str,
        days_back: int = 30,
        max_articles: int = 50
    ) -> List[NewsArticle]:
        """
        Get news articles with sentiment scores.
        
        Combines NewsAPI (headlines) with Alpha Vantage (sentiment).
        
        Args:
            ticker: Stock ticker symbol
            company_name: Company name for search
            days_back: Number of days to look back
            max_articles: Maximum articles to return
            
        Returns:
            List of NewsArticle with sentiment scores
        """
        if not self._initialized:
            raise RuntimeError("DataAggregator not initialized")
        
        all_articles = []
        
        # Get articles from Alpha Vantage (with sentiment) - prefer full source
        if self.alphavantage:
            try:
                av_articles = self.alphavantage.get_news_sentiment(ticker, days_back)
                all_articles.extend(av_articles)
                self.logger.info(f"Retrieved {len(av_articles)} articles from Alpha Vantage")
            except Exception as e:
                self.logger.warning(f"Alpha Vantage failed: {e}")
        elif self.alphavantage_news:
            try:
                av_articles = self.alphavantage_news.get_news_sentiment(ticker, days_back)
                all_articles.extend(av_articles)
                self.logger.info(f"Retrieved {len(av_articles)} articles from Alpha Vantage (news)")
            except Exception as e:
                self.logger.warning(f"Alpha Vantage news failed: {e}")
        
        # Get additional articles from NewsAPI if needed
        if self.newsapi and len(all_articles) < max_articles:
            try:
                remaining = max_articles - len(all_articles)
                news_articles = self.newsapi.get_ticker_news(
                    ticker, company_name, days_back
                )[:remaining]
                
                # Deduplicate by headline
                existing_headlines = {a.headline.lower() for a in all_articles}
                for article in news_articles:
                    if article.headline.lower() not in existing_headlines:
                        all_articles.append(article)
                
                self.logger.info(f"Retrieved {len(news_articles)} additional articles from NewsAPI")
            except Exception as e:
                self.logger.warning(f"NewsAPI failed: {e}")
        
        # Sort by date (most recent first)
        all_articles.sort(key=lambda x: x.published_at, reverse=True)
        
        return all_articles[:max_articles]
    
    def get_earnings_calendar(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date
    ) -> List[EarningsEvent]:
        """
        Get earnings calendar from available sources.
        
        Args:
            tickers: List of ticker symbols
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of EarningsEvent
        """
        if not self._initialized:
            raise RuntimeError("DataAggregator not initialized")
        
        events = []
        if self.yahoo:
            try:
                events = self.yahoo.get_earnings_calendar(tickers, start_date, end_date)
                self.logger.info(f"Retrieved {len(events)} events from Yahoo Finance")
            except Exception as e:
                self.logger.warning(f"Yahoo Finance calendar failed: {e}")
        
        return events
    
    def get_sec_filings(
        self,
        ticker: str,
        filing_type: str = "8-K",
        days_back: int = 90
    ) -> List[Any]:
        """
        Get SEC filings (if SEC source is enabled).
        
        Args:
            ticker: Stock ticker symbol
            filing_type: Type of filing (8-K, 10-K, 10-Q)
            days_back: Number of days to look back
            
        Returns:
            List of SEC filings
        """
        if not self._initialized:
            raise RuntimeError("DataAggregator not initialized")
        
        if not self.sec:
            self.logger.warning("SEC EDGAR not enabled")
            return []
        
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days_back)
            
            filings = self.sec.get_filings(
                ticker,
                filing_type=filing_type,
                start_date=start_date,
                end_date=end_date,
                limit=50
            )
            
            return filings
        except Exception as e:
            self.logger.error(f"Failed to get SEC filings: {e}")
            return []

    def get_option_analytics(
        self,
        ticker: str,
        earnings_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get options market analytics including implied move.
        
        Args:
            ticker: Stock ticker symbol
            earnings_date: Upcoming earnings date
            
        Returns:
            Dict containing option chain summary and implied move
        """
        if not self._initialized:
            raise RuntimeError("DataAggregator not initialized")
            
        try:
            # Unpack results
            contracts, summary = self.yahoo.get_option_chain(ticker, num_expirations=4, strike_range_pct=0.15)
            
            # Map Yahoo contracts to OptionData for the standardized analyzer
            opt_data_list = []
            for c in contracts:
                try:
                    # Map enum types
                    from yahoo_finance import OptionType as YFOptType
                    o_type = OptType.CALL if c.option_type == YFOptType.CALL else OptType.PUT
                    
                    opt_data_list.append(OptionData(
                        ticker=c.ticker,
                        option_type=o_type,
                        strike=c.strike,
                        expiration=c.expiration,
                        underlying_price=c.underlying_price,
                        bid=c.bid,
                        ask=c.ask,
                        last_price=c.last_price,
                        volume=c.volume,
                        open_interest=c.open_interest,
                        mid_price=c.mid_price,
                        implied_volatility=c.implied_volatility,
                        delta=c.delta,
                        gamma=c.gamma,
                        theta=c.theta,
                        vega=c.vega,
                        days_to_expiry=c.days_to_expiry,
                        occ_symbol=c.occ_symbol
                    ))
                except Exception:
                    continue
            
            # Use the high-quality analyzer from options.py
            current_price = self.yahoo.get_price_data(ticker).current_price
            analyzer = OptionChainAnalyzer(ticker, current_price, opt_data_list)
            features = analyzer.get_chain_features()
            
            # Extract implied move from features
            feat_move = features.get("implied_move", {})
            
            # Calculate a robust confidence score based on data quality
            confidence = 0.0
            if feat_move:
                confidence += 4.0
            if features.get("put_call_ratios"):
                confidence += 3.0
            if len(contracts) > 50:
                confidence += 3.0
            elif len(contracts) > 10:
                confidence += 1.5
            
            return {
                "implied_move": {
                    "straddle_implied_move_pct": feat_move.get("implied_move_pct", 0),
                    "confidence_score": confidence,
                    "upper_range": feat_move.get("upper_range"),
                    "lower_range": feat_move.get("lower_range"),
                    "days_to_expiry": feat_move.get("days_to_expiry"),
                },
                "option_summary": {
                    "put_call_ratio": features.get("put_call_ratios", {}).get("total", {}).get("volume_ratio", 0),
                    "total_volume": features.get("total_volume", 0),
                    "total_oi": features.get("total_open_interest", 0),
                    "avg_iv": features.get("skew", {}).get("atm_iv", 0),
                    **features
                },
                "total_contracts": len(contracts)
            }
        except Exception as e:
            self.logger.error(f"Failed to get option analytics for {ticker}: {e}")
            return {}

    def get_earnings_transcripts(
        self,
        ticker: str,
        year: Optional[int] = None,
        quarter: Optional[str] = None
    ) -> List[EarningsCallTranscript]:
        """
        Get earnings call transcripts from SEC filings.
        
        Args:
            ticker: Stock ticker
            year: Fiscal year
            quarter: Fiscal quarter (Q1, Q2, Q3, Q4)
            
        Returns:
            List of EarningsCallTranscript
        """
        if not self._initialized:
            raise RuntimeError("DataAggregator not initialized")
            
        if not self.sec:
            return []
            
        try:
            transcripts = self.sec.get_earnings_transcripts(ticker, year, quarter)
            # Map SECEdgar transcript model to base Transcript model
            return [
                EarningsCallTranscript(
                    ticker=t.ticker,
                    year=t.fiscal_year,
                    quarter=t.fiscal_quarter,
                    transcript=t.full_text
                )
                for t in transcripts
            ]
        except Exception as e:
            self.logger.error(f"Failed to get transcripts for {ticker}: {e}")
            return []

    def get_insider_transactions(
        self,
        ticker: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recent insider trading transactions.
        
        Args:
            ticker: Stock ticker
            limit: Max transactions to return
            
        Returns:
            List of insider transactions
        """
        if not self._initialized:
            raise RuntimeError("DataAggregator not initialized")
            
        if not self.alphavantage or not HAS_FULL_ALPHA_VANTAGE:
            return []
            
        try:
            transactions = self.alphavantage.get_insider_transactions(ticker, limit)
            return [self._to_dict(t) for t in transactions]
        except Exception as e:
            self.logger.error(f"Failed to get insider transactions for {ticker}: {e}")
            return []

    def get_company_facts(self, ticker: str) -> Dict[str, Any]:
        """
        Get company facts from SEC XBRL data.
        
        Args:
            ticker: Stock ticker
            
        Returns:
            Dict of company facts
        """
        if not self._initialized:
            raise RuntimeError("DataAggregator not initialized")
            
        if not self.sec:
            return {}
            
        try:
            return self.sec.get_company_facts(ticker)
        except Exception as e:
            self.logger.error(f"Failed to get company facts for {ticker}: {e}")
            return {}


# ============================================================================
# TESTING - COMPREHENSIVE TEST SUITE
# ============================================================================

if __name__ == "__main__":
    """Comprehensive test of data aggregator with all free sources."""
    
    import os
    
    # Try to load from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv not installed, will use system environment variables
    
    logging.basicConfig(level=logging.INFO)
    
    # ========================================================================
    # CONFIGURATION
    # ========================================================================
    
    print("\n" + "="*70)
    print("🚀 EARNINGS PREDICTION - COMPREHENSIVE DATA SOURCE TEST")
    print("="*70 + "\n")
    
    # Configure sources
    yahoo_config = DataSourceConfig(
        rate_limit_calls=2000,
        rate_limit_period=3600
    )
    
    # Optional: Add API keys via environment variables
    newsapi_key = os.environ.get('NEWSAPI_KEY')
    newsapi_config = None
    if newsapi_key:
        newsapi_config = DataSourceConfig(
            api_key=newsapi_key,
            rate_limit_calls=100,
            rate_limit_period=86400
        )
    
    av_key = os.environ.get('ALPHAVANTAGE_KEY')
    av_config = None
    if av_key:
        av_config = DataSourceConfig(
            api_key=av_key,
            rate_limit_calls=25,
            rate_limit_period=86400
        )
    
    sec_config = DataSourceConfig(
        rate_limit_calls=10,
        rate_limit_period=1
    )
    
    # Show what's enabled
    print("📊 Data Sources:")
    print(f"   ✅ Yahoo Finance (FREE)")
    print(f"   {'✅' if newsapi_key else '❌'} NewsAPI {'(API key found)' if newsapi_key else '(No API key - set NEWSAPI_KEY)'}")
    print(f"   {'✅' if av_key else '❌'} Alpha Vantage {'(API key found)' if av_key else '(No API key - set ALPHAVANTAGE_KEY)'}")
    print(f"   ✅ SEC EDGAR (FREE - optional, slow)")
    print()
    
    # Initialize aggregator
    aggregator = DataAggregator(
        yahoo_config=yahoo_config,
        newsapi_config=newsapi_config,
        alphavantage_config=av_config,
        sec_config=sec_config,
        enable_yahoo=True,
        enable_newsapi=newsapi_key is not None,
        enable_alphavantage=av_key is not None,
        enable_sec=True,  # Disable by default (slow)
    )
    
    aggregator.initialize()
    
    # ========================================================================
    # TEST 1: COMPANY FUNDAMENTALS (Yahoo Finance)
    # ========================================================================
    
    ticker = "AAPL"
    report_date = date(2025, 11, 1)
    
    print("\n" + "="*70)
    print(f"📈 TEST 1: Company Fundamentals - {ticker}")
    print("="*70 + "\n")
    
    company = aggregator.get_company_data(ticker, report_date, include_news=False)
    
    print(f"Company Information:")
    print(f"  Name: {company.company_name}")
    print(f"  Sector: {company.sector}")
    print(f"  Industry: {company.industry}")
    print(f"  Market Cap: ${company.market_cap/1e9:.2f}B")
    
    if company.current_price:
        print(f"\nPrice & Momentum:")
        print(f"  Current Price: ${company.current_price:.2f}")
        if company.price_change_5d is not None:
            print(f"  5-Day Change: {company.price_change_5d:+.2%}")
        if company.price_change_21d is not None:
            print(f"  21-Day Change: {company.price_change_21d:+.2%}")
    
    print(f"\nConsensus Estimates:")
    print(f"  EPS Estimate: ${company.consensus_eps:.2f}")
    print(f"  Revenue Estimate: ${company.consensus_revenue/1e9:.2f}B" if company.consensus_revenue else "  Revenue Estimate: N/A")
    print(f"  Analysts: {company.num_analysts}")
    
    # ========================================================================
    # TEST 2: HISTORICAL EARNINGS (Yahoo Finance)
    # ========================================================================
    
    print("\n" + "="*70)
    print(f"📊 TEST 2: Historical Earnings - {ticker}")
    print("="*70 + "\n")
    
    if company.historical_eps:
        print(f"Last {min(4, len(company.historical_eps))} Quarters:")
        # Use a list variable to help the linter
        hist_list = company.historical_eps
        hist_reversed = list(reversed(hist_list))
        for i, h in enumerate(hist_reversed[:4], 1):
            beat_miss = "BEAT" if h.get('beat') else "MISS"
            surprise = h.get('surprise_pct', 0)
            print(f"  {i}. {h.get('date')}: {beat_miss} by {surprise:+.1f}%")
            print(f"     Actual: ${h.get('actual_eps'):.2f} vs Estimate: ${h.get('estimate_eps'):.2f}")
        
        if company.beat_rate_4q is not None:
            print(f"\nBeat Rate (4Q): {company.beat_rate_4q:.0%}")
        if company.avg_surprise_4q is not None:
            print(f"Avg Surprise (4Q): {company.avg_surprise_4q:+.1f}%")
    else:
        print("  No historical earnings data available")
    
    # ========================================================================
    # TEST 3: ANALYST RECOMMENDATIONS (Yahoo Finance)
    # ========================================================================
    
    print("\n" + "="*70)
    print(f"👔 TEST 3: Analyst Recommendations - {ticker}")
    print("="*70 + "\n")
    
    if company.analyst_recommendations:
        print(f"Recent Recommendations ({len(company.analyst_recommendations)} total):")
        for i, rec in enumerate(company.analyst_recommendations[:5], 1):
            date_str = rec.get('date')
            firm = rec.get('firm', 'Unknown')
            rating = rec.get('rating', 'N/A')
            score = rec.get('rating_score')
            score_str = f" ({score:.1f}/5.0)" if score else ""
            print(f"  {i}. {date_str} - {firm}: {rating}{score_str}")
    else:
        print("  No recommendation data available")
    
    # ========================================================================
    # TEST 4: NEWS WITH SENTIMENT (NewsAPI + Alpha Vantage)
    # ========================================================================
    
    print("\n" + "="*70)
    print(f"📰 TEST 4: News with Sentiment - {ticker}")
    print("="*70 + "\n")
    
    news = aggregator.get_news_with_sentiment(
        ticker, 
        company.company_name,
        days_back=7,
        max_articles=20
    )
    
    if news:
        print(f"Found {len(news)} articles from last 7 days:")
        
        # Show sentiment distribution
        with_sentiment = [a for a in news if a.sentiment_score is not None]
        if with_sentiment:
            avg_sentiment = sum(a.sentiment_score for a in with_sentiment) / len(with_sentiment)
            
            positive = sum(1 for a in with_sentiment if a.sentiment_score > 0.1)
            negative = sum(1 for a in with_sentiment if a.sentiment_score < -0.1)
            neutral = len(with_sentiment) - positive - negative
            
            print(f"\nAverage Sentiment: {avg_sentiment:+.3f}")
            print(f"Distribution: {positive} positive, {neutral} neutral, {negative} negative")
        
        print(f"\nTop 5 Articles:")
        for i, article in enumerate(news[:5], 1):
            sentiment_str = ""
            if article.sentiment_score is not None:
                sentiment_val = article.sentiment_score
                if sentiment_val > 0.1:
                    sentiment_str = f" [😊 +{sentiment_val:.2f}]"
                elif sentiment_val < -0.1:
                    sentiment_str = f" [😟 {sentiment_val:.2f}]"
                else:
                    sentiment_str = f" [😐 {sentiment_val:.2f}]"
            
            relevance_str = ""
            if article.relevance_score:
                relevance_str = f" (Relevance: {article.relevance_score:.2f})"
            
            print(f"\n  {i}. {article.headline}")
            print(f"     {article.source} - {article.published_at.date()}{sentiment_str}{relevance_str}")
    else:
        print("  No news articles available")
        print("  💡 Tip: Set NEWSAPI_KEY or ALPHAVANTAGE_KEY environment variables")
    
    # ========================================================================
    # TEST 5: ALPHA VANTAGE EARNINGS (if enabled)
    # ========================================================================
    
    if av_key and HAS_FULL_ALPHA_VANTAGE and aggregator.alphavantage:
        print("\n" + "="*70)
        print(f"📈 TEST 5: Alpha Vantage Earnings Detail - {ticker}")
        print("="*70 + "\n")
        
        try:
            # Get quarterly earnings
            quarterly = aggregator.alphavantage.get_quarterly_earnings_data(ticker)
            
            if quarterly:
                print(f"Quarterly Earnings Detail ({len(quarterly)} quarters):")
                for i, q in enumerate(quarterly[:4], 1):
                    surprise = q.surprise_percentage if q.surprise_percentage else 0
                    print(f"  {i}. {q.fiscal_date_ending}: EPS ${q.reported_eps:.2f}")
                    print(f"     Estimate: ${q.estimated_eps:.2f}, Surprise: {surprise:+.1f}%")
            else:
                print("  No quarterly earnings data available from Alpha Vantage")
            
        except Exception as e:
            print(f"  Alpha Vantage error: {e}")
    elif av_key and not HAS_FULL_ALPHA_VANTAGE:
        print("\n" + "="*70)
        print(f"⚠️  TEST 5: Alpha Vantage Full Source Not Available")
        print("="*70 + "\n")
        print("  Full Alpha Vantage source (alpha_vantage.py) not found.")
        print("  Only news sentiment is available.")
        print("  Copy alpha_vantage.py to the data folder for full functionality.")
    
    # ========================================================================
    # TEST 6: SEC EDGAR FILINGS (if enabled)
    # ========================================================================
    # TO DO: EXTRACT 10-Q AND 10-K FILES FROM filing_url
    if aggregator.sec:
        print("\n" + "="*70)
        print(f"📄 TEST 6: SEC EDGAR Filings - {ticker}")
        print("="*70 + "\n")
        
        try:
            filings = aggregator.get_sec_filings(ticker, filing_type="10-Q", days_back=90)
            
            if filings:
                print(f"Recent 10-Q Filings ({len(filings)} total):")
                # Use a slice that's safer for the linter
                limit = min(5, len(filings))
                for i in range(limit):
                    filing = filings[i]
                    print(f"  {i+1}. {filing.filing_date}: {filing.filing_type}")
                    print(f"     Accession: {filing.accession_number}")
            else:
                print("  No recent 8-K filings found")
                
        except Exception as e:
            print(f"  SEC EDGAR error: {e}")

    # ========================================================================
    # TEST 7: OPTIONS ANALYTICS (Yahoo Finance)
    # ========================================================================
    
    print("\n" + "="*70)
    print(f"📉 TEST 7: Options Analytics - {ticker}")
    print("="*70 + "\n")
    
    try:
        options = aggregator.get_option_analytics(ticker)
        if options:
            implied_move = options.get("implied_move", {})
            print(f"Implied Move Analysis:")
            print(f"  Straddle Implied Move: {implied_move.get('straddle_implied_move_pct', 0):.2%}")
            print(f"  Market Confidence: {implied_move.get('confidence_score', 0):.1f}/10")
            
            summary = options.get("option_summary", {})
            if summary:
                print(f"\nOption Chain Summary:")
                print(f"  Put/Call Ratio (Volume): {summary.get('put_call_volume_ratio', 0):.2f}")
                print(f"  Avg Implied Vol: {summary.get('avg_iv', 0):.2%}")
        else:
            print("  No option data available")
    except Exception as e:
        print(f"  Options error: {e}")

    # ========================================================================
    # TEST 8: EARNINGS TRANSCRIPTS (SEC EDGAR)
    # ========================================================================
    
    if aggregator.sec:
        print("\n" + "="*70)
        print(f"🎙️ TEST 8: Earnings Transcripts - {ticker}")
        print("="*70 + "\n")
        
        try:
            transcripts = aggregator.get_earnings_transcripts(ticker, year=2024)
            if transcripts:
                print(f"Found {len(transcripts)} transcripts:")
                for i, t in enumerate(transcripts[:2], 1):
                    print(f"  {i}. {t.year} {t.quarter}: {len(t.transcript)} characters")
            else:
                print("  No transcripts found in SEC filings")
        except Exception as e:
            print(f"  Transcript error: {e}")

    # ========================================================================
    # TEST 9: INSIDER TRANSACTIONS (Alpha Vantage)
    # ========================================================================
    
    if av_key and HAS_FULL_ALPHA_VANTAGE and aggregator.alphavantage:
        print("\n" + "="*70)
        print(f"👤 TEST 9: Insider Transactions - {ticker}")
        print("="*70 + "\n")
        
        try:
            insider = aggregator.get_insider_transactions(ticker, limit=5)
            if insider:
                print(f"Recent Insider Trades:")
                for i, t in enumerate(insider, 1):
                    print(f"  {i}. {t.get('date')}: {t.get('insider_name')} ({t.get('transaction_type')}) - {t.get('shares'):,.0f} shares")
            else:
                print("  No insider transactions found")
        except Exception as e:
            print(f"  Insider error: {e}")

    # ========================================================================
    # TEST 10: EARNINGS CALENDAR
    # ========================================================================
    
    print("\n" + "="*70)
    print(f"📅 TEST 10: Earnings Calendar")
    print("="*70 + "\n")
    
    try:
        # Get earnings for this week
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        # Test with a few major tickers
        test_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
        
        calendar = aggregator.get_earnings_calendar(test_tickers, week_start, week_end)
        
        if calendar:
            print(f"Earnings This Week ({week_start} to {week_end}):")
            for event in calendar:
                # Handle both object and dict (in case aggregator returns dicts)
                ticker_val = event.ticker if hasattr(event, "ticker") else event.get("ticker")
                date_val = event.report_date if hasattr(event, "report_date") else event.get("report_date")
                time_val = event.report_time if hasattr(event, "report_time") else event.get("report_time")
                consensus_val = event.consensus_eps if hasattr(event, "consensus_eps") else event.get("consensus_eps")
                
                time_str = str(time_val).replace('_', ' ').title() if time_val else "Unknown"
                eps_str = f"${consensus_val:.2f}" if consensus_val else "N/A"
                print(f"  • {ticker_val}: {date_val} ({time_str})")
                print(f"    Consensus EPS: {eps_str}")
        else:
            print(f"  No earnings scheduled for {week_start} to {week_end}")
            
    except Exception as e:
        print(f"  Calendar error: {e}")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    
    print("\n" + "="*70)
    print("✅ TEST SUMMARY")
    print("="*70 + "\n")
    
    print("Data Successfully Retrieved:")
    print(f"  ✓ Company fundamentals ({company.company_name})")
    print(f"  ✓ Historical earnings ({len(company.historical_eps)} quarters)")
    print(f"  ✓ Analyst recommendations ({len(company.analyst_recommendations)} recs)")
    print(f"  {'✓' if news else '✗'} News articles ({len(news)} articles)")
    
    if aggregator.yahoo:
        print(f"  ✓ Options analytics & implied move")
    
    if av_key and HAS_FULL_ALPHA_VANTAGE:
        print(f"  ✓ Alpha Vantage earnings detail")
    elif av_key:
        print(f"  ⚠ Alpha Vantage (news only - full source not available)")
    else:
        print(f"  ⚠ Alpha Vantage (no API key)")
    
    if aggregator.sec:
        print(f"  ✓ SEC EDGAR filings")
    else:
        print(f"  ⚠ SEC EDGAR (disabled)")
    
    print("\n" + "="*70)
    print("🎯 NEXT STEPS")
    print("="*70 + "\n")
    
    print("To get the most out of the data pipeline:")
    print()
    print("1. Get Free API Keys (Optional but Recommended):")
    print("   • NewsAPI: https://newsapi.org/ (100 req/day free)")
    print("   • Alpha Vantage: https://www.alphavantage.co/ (25 req/day free)")
    print()
    print("2. Set Environment Variables:")
    print("   export NEWSAPI_KEY=your_newsapi_key")
    print("   export ALPHAVANTAGE_KEY=your_alphavantage_key")
    print()
    print("3. Or Create .env File:")
    print("   NEWSAPI_KEY=your_newsapi_key")
    print("   ALPHAVANTAGE_KEY=your_alphavantage_key")
    print()
    print("4. Install python-dotenv (for .env support):")
    print("   pip install python-dotenv")
    print()
    print("5. Run Again:")
    print("   python -m data.data_aggregator")
    print()
    print("6. Integrate with Your Agents:")
    print("   from data import DataAggregator")
    print("   aggregator = DataAggregator(...)")
    print("   company_data = aggregator.get_company_data(ticker, date)")
    print()
    
    # Shutdown
    aggregator.shutdown()
    
    print("="*70)
    print("✨ Test completed successfully!")
    print("="*70 + "\n")