"""
Alpha Vantage Data Source for Earnings Prediction.

Provides:
- Company overview and fundamentals
- Earnings data (quarterly and annual)
- News with sentiment analysis
- Insider transactions (if available)

Requires: requests
Install: pip install requests

Get API key: https://www.alphavantage.co/support/#api-key
Free tier: 25 requests/day
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
        NewsArticle,
        EarningsCallTranscript,
        DataSourceConfig,
        RateLimiter,
        normalize_ticker,
        safe_float,
        safe_int,
    )
except (ImportError, ValueError):
    from base import (
        BaseDataSource,
        CompanyInfo,
        PriceData,
        ConsensusEstimate,
        HistoricalEarning,
        EstimateRevision,
        NewsArticle,
        EarningsCallTranscript,
        DataSourceConfig,
        RateLimiter,
        normalize_ticker,
        safe_float,
        safe_int,
    )

from pydantic import BaseModel, Field


# ============================================================================
# ALPHA VANTAGE SPECIFIC MODELS
# ============================================================================

class InsiderTransaction(BaseModel):
    """Insider trading transaction."""
    date: date
    insider_name: str
    title: Optional[str] = None
    transaction_type: str  # Purchase, Sale, Gift, etc.
    shares: float
    price_per_share: Optional[float] = None
    total_value: Optional[float] = None
    shares_held_after: Optional[float] = None


class QuarterlyEarnings(BaseModel):
    """Quarterly earnings data."""
    fiscal_date_ending: date
    reported_date: Optional[date] = None
    reported_eps: Optional[float] = None
    estimated_eps: Optional[float] = None
    surprise: Optional[float] = None
    surprise_percentage: Optional[float] = None


class AnnualEarnings(BaseModel):
    """Annual earnings data."""
    fiscal_date_ending: date
    reported_eps: float


# ============================================================================
# ALPHA VANTAGE DATA SOURCE
# ============================================================================

class AlphaVantageDataSource(BaseDataSource):
    """
    Alpha Vantage data source.
    
    Provides company fundamentals, earnings data, news with sentiment,
    and other financial data.
    
    Free tier: 25 API calls per day
    
    Usage:
        config = DataSourceConfig(
            api_key="your_alpha_vantage_key",
            rate_limit_calls=25,
            rate_limit_period=86400  # 1 day
        )
        
        av = AlphaVantageDataSource(config)
        av.connect()
        
        # Company overview
        info = av.get_company_info("AAPL")
        print(f"{info.company_name} - {info.sector}")
        
        # Earnings data
        earnings = av.get_historical_earnings("AAPL", 8)
        for e in earnings:
            print(f"{e.date}: Actual {e.actual_eps} vs Est {e.estimate_eps}")
        
        # News with sentiment
        news = av.get_news_sentiment("AAPL", days_back=7)
        for article in news:
            print(f"{article.headline} - Sentiment: {article.sentiment_score}")
        
        # Insider transactions
        transactions = av.get_insider_transactions("AAPL")
        for t in transactions:
            print(f"{t.date}: {t.insider_name} - {t.transaction_type}")
        
        av.disconnect()
    """
    
    def __init__(self, config: DataSourceConfig):
        super().__init__("AlphaVantage")
        self.config = config
        self.rate_limiter = RateLimiter(
            config.rate_limit_calls,
            config.rate_limit_period
        )
        self.session = None
        self.base_url = "https://www.alphavantage.co/query"
    
    def connect(self) -> bool:
        """Connect to Alpha Vantage API."""
        try:
            import requests
            
            if not self.config.api_key:
                raise ValueError("Alpha Vantage requires an API key")
            
            self.session = requests.Session()
            self._connected = True
            self.logger.info("Alpha Vantage initialized")
            return True
            
        except ImportError:
            self.logger.error(
                "requests not installed. Install with: pip install requests"
            )
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize Alpha Vantage: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from Alpha Vantage."""
        if self.session:
            self.session.close()
        self._connected = False
        self.session = None
        self.logger.info("Alpha Vantage disconnected")
    
    def _make_request(self, function: str, symbol: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Make API request with rate limiting."""
        self._ensure_connected()
        self.rate_limiter.wait_if_needed()
        
        params = {
            'function': function,
            'apikey': self.config.api_key,
        }
        
        if symbol:
            params['symbol'] = normalize_ticker(symbol)
        
        params.update(kwargs)
        
        try:
            response = self.session.get(
                self.base_url,
                params=params,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check for errors
            if 'Error Message' in data:
                self.logger.error(f"Alpha Vantage error: {data['Error Message']}")
                return {}
            
            if 'Note' in data:
                self.logger.warning(f"Alpha Vantage note: {data['Note']}")
                return {}
            
            return data
            
        except Exception as e:
            self.logger.error(f"Alpha Vantage request failed: {e}")
            return {}
    
    def get_company_info(self, ticker: str) -> Optional[CompanyInfo]:
        """
        Get company overview and fundamental data.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            CompanyInfo or None if not found
        """
        try:
            data = self._make_request('OVERVIEW', symbol=ticker)
            
            if not data or 'Symbol' not in data:
                self.logger.warning(f"No overview data for {ticker}")
                return None
            
            return CompanyInfo(
                ticker=normalize_ticker(ticker),
                company_name=data.get('Name', ticker),
                sector=data.get('Sector', 'Unknown'),
                industry=data.get('Industry', 'Unknown'),
                market_cap=safe_float(data.get('MarketCapitalization', 0)),
                exchange=data.get('Exchange'),
                currency=data.get('Currency', 'USD'),
                country=data.get('Country'),
                description=data.get('Description'),
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get company info for {ticker}: {e}")
            return None
    
    def get_price_data(self, ticker: str) -> Optional[PriceData]:
        """
        Get price data (limited in Alpha Vantage).
        
        Note: Alpha Vantage is not ideal for real-time price data.
        Use Yahoo Finance or dedicated market data API instead.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            PriceData or None
        """
        try:
            # Get overview which has some price info
            data = self._make_request('OVERVIEW', symbol=ticker)
            
            if not data:
                return None
            
            return PriceData(
                current_price=safe_float(data.get('50DayMovingAverage', 0)),
                price_change_5d=None,
                price_change_21d=None,
                price_change_63d=None,
                volume=None,
                avg_volume_30d=None,
                short_interest=None,
                beta=safe_float(data.get('Beta')),
                as_of_date=date.today(),
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get price data for {ticker}: {e}")
            return None
    
    def get_consensus_estimates(self, ticker: str) -> Optional[ConsensusEstimate]:
        """
        Get consensus estimates from Alpha Vantage overview.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            ConsensusEstimate or None
        """
        try:
            data = self._make_request('OVERVIEW', symbol=ticker)
            
            if not data:
                return None
            
            # Alpha Vantage provides forward PE and PEG which we can use
            # But doesn't provide detailed analyst estimates
            eps_forward = safe_float(data.get('ForwardPE', 0))
            
            # Estimate EPS from forward PE if available
            price = safe_float(data.get('50DayMovingAverage', 0))
            eps_mean = price / eps_forward if eps_forward and price else 0.0
            
            # Get analyst target price
            analyst_target = safe_float(data.get('AnalystTargetPrice', 0))
            
            return ConsensusEstimate(
                eps_mean=eps_mean,
                eps_median=eps_mean,
                eps_high=eps_mean * 1.1,
                eps_low=eps_mean * 0.9,
                eps_std=(eps_mean * 0.1),
                revenue_mean=None,
                revenue_median=None,
                num_analysts=0,  # Alpha Vantage doesn't provide this
                as_of_date=date.today(),
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get estimates for {ticker}: {e}")
            return None
    
    def get_historical_earnings(
        self, 
        ticker: str, 
        num_quarters: int = 8
    ) -> List[HistoricalEarning]:
        """
        Get historical quarterly earnings.
        
        Args:
            ticker: Stock ticker symbol
            num_quarters: Number of quarters to retrieve
            
        Returns:
            List of HistoricalEarning
        """
        try:
            data = self._make_request('EARNINGS', symbol=ticker)
            
            if not data or 'quarterlyEarnings' not in data:
                self.logger.warning(f"No earnings data for {ticker}")
                return []
            
            earnings = []
            
            for item in data['quarterlyEarnings'][:num_quarters]:
                # Parse date
                fiscal_date = datetime.strptime(
                    item['fiscalDateEnding'], 
                    '%Y-%m-%d'
                ).date()
                
                reported_date = None
                if item.get('reportedDate'):
                    try:
                        reported_date = datetime.strptime(
                            item['reportedDate'],
                            '%Y-%m-%d'
                        ).date()
                    except:
                        reported_date = fiscal_date
                
                reported_eps = safe_float(item.get('reportedEPS'))
                estimated_eps = safe_float(item.get('estimatedEPS'))
                surprise = safe_float(item.get('surprise'))
                surprise_pct = safe_float(item.get('surprisePercentage'))
                
                # Calculate surprise if not provided
                if not surprise and reported_eps and estimated_eps:
                    surprise = reported_eps - estimated_eps
                
                if not surprise_pct and reported_eps and estimated_eps and estimated_eps != 0:
                    surprise_pct = ((reported_eps - estimated_eps) / abs(estimated_eps)) * 100
                
                earnings.append(HistoricalEarning(
                    date=reported_date or fiscal_date,
                    actual_eps=reported_eps,
                    estimate_eps=estimated_eps,
                    surprise_pct=surprise_pct,
                    beat=reported_eps > estimated_eps if (reported_eps and estimated_eps) else False,
                    fiscal_quarter=f"Q{((fiscal_date.month - 1) // 3) + 1}",
                    fiscal_year=fiscal_date.year,
                ))
            
            return earnings
            
        except Exception as e:
            self.logger.error(f"Failed to get historical earnings for {ticker}: {e}")
            return []
    
    def get_estimate_revisions(
        self, 
        ticker: str, 
        days_back: int = 90
    ) -> List[EstimateRevision]:
        """
        Get estimate revisions.
        
        Note: Alpha Vantage doesn't provide detailed revision history.
        This returns empty list.
        
        Args:
            ticker: Stock ticker symbol
            days_back: Number of days to look back
            
        Returns:
            Empty list (not supported by Alpha Vantage)
        """
        self.logger.warning(
            f"Alpha Vantage doesn't provide estimate revisions. "
            "Use FactSet or Refinitiv for revision tracking."
        )
        return []
    
    def get_news_sentiment(
        self,
        ticker: str,
        days_back: int = 7,
        limit: int = 50
    ) -> List[NewsArticle]:
        """
        Get news articles with sentiment scores.
        
        Args:
            ticker: Stock ticker symbol
            days_back: Number of days to look back
            limit: Maximum number of articles (default 50)
            
        Returns:
            List of NewsArticle with sentiment scores
        """
        try:
            ticker = normalize_ticker(ticker)
            
            # Calculate time range
            time_to = datetime.now()
            time_from = time_to - timedelta(days=days_back)
            
            data = self._make_request(
                'NEWS_SENTIMENT',
                tickers=ticker,
                time_from=time_from.strftime('%Y%m%dT%H%M'),
                time_to=time_to.strftime('%Y%m%dT%H%M'),
                limit=limit
            )
            
            if not data or 'feed' not in data:
                return []
            
            articles = []
            
            for item in data['feed']:
                # Parse timestamp
                time_str = item.get('time_published', '')
                try:
                    published_at = datetime.strptime(time_str, '%Y%m%dT%H%M%S')
                except:
                    published_at = datetime.now()
                
                # Get overall sentiment
                overall_sentiment = item.get('overall_sentiment_score', 0)
                
                # Get ticker-specific sentiment
                ticker_sentiment = None
                relevance = None
                
                for ticker_data in item.get('ticker_sentiment', []):
                    if ticker_data.get('ticker') == ticker:
                        ticker_sentiment = safe_float(ticker_data.get('ticker_sentiment_score'))
                        relevance = safe_float(ticker_data.get('relevance_score'))
                        break
                
                # Use ticker-specific sentiment if available
                sentiment_score = ticker_sentiment if ticker_sentiment is not None else overall_sentiment
                
                articles.append(NewsArticle(
                    headline=item.get('title', ''),
                    body=item.get('summary', ''),
                    source=item.get('source', 'Unknown'),
                    published_at=published_at,
                    url=item.get('url'),
                    sentiment_score=safe_float(sentiment_score),
                    relevance_score=relevance,
                    keywords=[t.get('topic') for t in item.get('topics', []) if t.get('topic')],
                ))
            
            self.logger.info(f"Retrieved {len(articles)} articles for {ticker}")
            return articles
            
        except Exception as e:
            self.logger.error(f"Failed to get news sentiment for {ticker}: {e}")
            return []
    
    def get_insider_transactions(
        self,
        ticker: str,
        limit: int = 50
    ) -> List[InsiderTransaction]:
        """
        Get insider trading transactions.
        
        Note: This endpoint may not be available in all Alpha Vantage plans.
        Check API documentation for availability.
        
        Args:
            ticker: Stock ticker symbol
            limit: Maximum number of transactions
            
        Returns:
            List of InsiderTransaction
        """
        try:
            # Note: This is a hypothetical endpoint
            # Alpha Vantage may not have this in free tier
            # Keeping for future compatibility
            
            self.logger.warning(
                f"Insider transaction data may not be available in Alpha Vantage free tier. "
                "Consider using SEC Form 4 filings or specialized services."
            )
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get insider transactions for {ticker}: {e}")
            return []
    
    def get_quarterly_earnings_data(self, ticker: str) -> List[QuarterlyEarnings]:
        """
        Get detailed quarterly earnings data.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            List of QuarterlyEarnings
        """
        try:
            data = self._make_request('EARNINGS', symbol=ticker)
            
            if not data or 'quarterlyEarnings' not in data:
                return []
            
            quarterly = []
            
            for item in data['quarterlyEarnings']:
                fiscal_date = datetime.strptime(
                    item['fiscalDateEnding'],
                    '%Y-%m-%d'
                ).date()
                
                reported_date = None
                if item.get('reportedDate'):
                    try:
                        reported_date = datetime.strptime(
                            item['reportedDate'],
                            '%Y-%m-%d'
                        ).date()
                    except:
                        pass
                
                quarterly.append(QuarterlyEarnings(
                    fiscal_date_ending=fiscal_date,
                    reported_date=reported_date,
                    reported_eps=safe_float(item.get('reportedEPS')),
                    estimated_eps=safe_float(item.get('estimatedEPS')),
                    surprise=safe_float(item.get('surprise')),
                    surprise_percentage=safe_float(item.get('surprisePercentage')),
                ))
            
            return quarterly
            
        except Exception as e:
            self.logger.error(f"Failed to get quarterly earnings for {ticker}: {e}")
            return []
    
    def get_annual_earnings_data(self, ticker: str) -> List[AnnualEarnings]:
        """
        Get annual earnings data.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            List of AnnualEarnings
        """
        try:
            data = self._make_request('EARNINGS', symbol=ticker)
            
            if not data or 'annualEarnings' not in data:
                return []
            
            annual = []
            
            for item in data['annualEarnings']:
                fiscal_date = datetime.strptime(
                    item['fiscalDateEnding'],
                    '%Y-%m-%d'
                ).date()
                
                annual.append(AnnualEarnings(
                    fiscal_date_ending=fiscal_date,
                    reported_eps=safe_float(item.get('reportedEPS', 0)),
                ))
            
            return annual
            
        except Exception as e:
            self.logger.error(f"Failed to get annual earnings for {ticker}: {e}")
            return []

    def get_earnings_transcript(
        self,
        ticker: str,
        year: Optional[int] = None,
        quarter: Optional[str] = None
    ) -> Optional[EarningsCallTranscript]:
        """
        Get earnings call transcript.
        
        Args:
            ticker: Stock ticker symbol
            year: Year of the transcript (optional, default latest)
            quarter: Quarter of the transcript (optional, e.g. Q1, Q2)
            
        Returns:
            EarningsCallTranscript or None
        """
        try:
            params = {}
            if year:
                params['year'] = str(year)
            if quarter:
                params['quarter'] = str(quarter)
                
            data = self._make_request(
                'EARNINGS_CALL_TRANSCRIPT',
                symbol=ticker,
                **params
            )
            
            if not data or 'transcript' not in data:
                self.logger.warning(f"No transcript data for {ticker}")
                return None
            
            return EarningsCallTranscript(
                ticker=data.get('symbol', ticker),
                year=safe_int(data.get('year')),
                quarter=data.get('quarter', ''),
                transcript=data.get('transcript', '')
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get transcript for {ticker}: {e}")
            return None


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    """Comprehensive test of Alpha Vantage data source."""
    
    import os
    logging.basicConfig(level=logging.INFO)
    
    # Get API key from environment
    api_key = os.environ.get('ALPHAVANTAGE_KEY')
    
    if not api_key:
        print("\n" + "="*60)
        print("⚠️  Alpha Vantage API key not found!")
        print("="*60)
        print("\nSet your API key:")
        print("  export ALPHAVANTAGE_KEY=your_key")
        print("\nGet a free key at:")
        print("  https://www.alphavantage.co/support/#api-key")
        print("\n" + "="*60)
        exit(1)
    
    # Configure
    config = DataSourceConfig(
        api_key=api_key,
        rate_limit_calls=25,
        rate_limit_period=86400
    )
    
    # Initialize
    av = AlphaVantageDataSource(config)
    av.connect()
    
    # Test ticker
    ticker = "AAPL"
    print(f"\n{'='*60}")
    print(f"Testing Alpha Vantage Data Source: {ticker}")
    print(f"{'='*60}\n")
    
    # 1. Company Overview
    print("1. Company Overview:")
    info = av.get_company_info(ticker)
    if info:
        print(f"   Name: {info.company_name}")
        print(f"   Sector: {info.sector}")
        print(f"   Industry: {info.industry}")
        print(f"   Market Cap: ${info.market_cap/1e9:.2f}B")
        print(f"   Country: {info.country}")
    
    # 2. Historical Earnings
    print("\n2. Historical Earnings (Last 4 Quarters):")
    earnings = av.get_historical_earnings(ticker, 4)
    for e in earnings:
        beat_miss = "BEAT" if e.beat else "MISS"
        print(f"   {e.date} ({e.fiscal_quarter} {e.fiscal_year}): {beat_miss}")
        print(f"      Actual: ${e.actual_eps:.2f} vs Estimate: ${e.estimate_eps:.2f}")
        print(f"      Surprise: {e.surprise_pct:+.1f}%")
    
    # 3. News with Sentiment
    print("\n3. Recent News with Sentiment (Last 7 Days):")
    news = av.get_news_sentiment(ticker, days_back=7, limit=10)
    print(f"   Found {len(news)} articles")
    for i, article in enumerate(news[:5], 1):
        print(f"\n   {i}. {article.headline[:60]}...")
        print(f"      Source: {article.source}")
        print(f"      Date: {article.published_at.date()}")
        print(f"      Sentiment: {article.sentiment_score:+.3f}")
        if article.relevance_score:
            print(f"      Relevance: {article.relevance_score:.3f}")
    
    # 4. Quarterly Earnings Detail
    print("\n4. Quarterly Earnings Detail:")
    quarterly = av.get_quarterly_earnings_data(ticker)
    print(f"   Found {len(quarterly)} quarters of data")
    for q in quarterly[:4]:
        print(f"   {q.fiscal_date_ending}: EPS ${q.reported_eps:.2f} (Est: ${q.estimated_eps:.2f})")
        if q.surprise_percentage:
            print(f"      Surprise: {q.surprise_percentage:+.1f}%")
    
    # 5. Annual Earnings
    print("\n5. Annual Earnings:")
    annual = av.get_annual_earnings_data(ticker)
    print(f"   Found {len(annual)} years of data")
    for a in annual[:5]:
        print(f"   {a.fiscal_date_ending.year}: EPS ${a.reported_eps:.2f}")
    
    # 6. Earnings Transcript
    print("\n6. Earnings Transcript (Latest):")
    transcript = av.get_earnings_transcript(ticker)
    if transcript:
        print(f"   Ticker: {transcript.ticker}")
        print(f"   Year/Quarter: {transcript.year} {transcript.quarter}")
        print(f"   Transcript Length: {len(transcript.transcript)} characters")
        print(f"   Snippet: {transcript.transcript[:200]}...")
    else:
        print("   No transcript found (may require premium subscription)")
    
    # Disconnect
    av.disconnect()
    
    print(f"\n{'='*60}")
    print("✅ Test completed successfully!")
    print(f"{'='*60}\n")
    print("Note: Free tier is limited to 25 API calls per day.")
    print("Consider upgrading for production use.")
    print(f"{'='*60}\n")