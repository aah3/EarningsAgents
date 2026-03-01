"""
News and Sentiment Data Sources for Earnings Prediction.

Provides:
- NewsAPI: News headlines and articles
- Alpha Vantage: News sentiment analysis

Requires: requests
Install: pip install requests
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

try:
    from .base import (
        NewsArticle,
        DataSourceConfig,
        RateLimiter,
        normalize_ticker,
        safe_float,
    )
except (ImportError, ValueError):
    from base import (
        NewsArticle,
        DataSourceConfig,
        RateLimiter,
        normalize_ticker,
        safe_float,
    )


# ============================================================================
# NEWS API DATA SOURCE
# ============================================================================

class NewsAPIDataSource:
    """
    NewsAPI data source for news articles.
    
    Provides news headlines and articles from 80,000+ sources.
    Free tier: 100 requests/day
    
    Get API key: https://newsapi.org/
    
    Usage:
        config = DataSourceConfig(
            api_key="your_newsapi_key",
            rate_limit_calls=100,
            rate_limit_period=86400  # 1 day
        )
        
        news_api = NewsAPIDataSource(config)
        news_api.connect()
        
        # Get company news
        articles = news_api.get_company_news("Apple", days_back=7)
        for article in articles:
            print(f"{article.published_at}: {article.headline}")
        
        # Search by ticker
        articles = news_api.search_news("AAPL earnings", days_back=30)
        
        news_api.disconnect()
    """
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.logger = logging.getLogger("NewsAPI")
        self.rate_limiter = RateLimiter(
            config.rate_limit_calls,
            config.rate_limit_period
        )
        self.session = None
        self.base_url = "https://newsapi.org/v2"
        self._connected = False
    
    def connect(self) -> bool:
        """Connect to NewsAPI."""
        try:
            import requests
            
            if not self.config.api_key:
                raise ValueError("NewsAPI requires an API key")
            
            self.session = requests.Session()
            self.session.headers.update({
                'Authorization': f'Bearer {self.config.api_key}'
            })
            
            self._connected = True
            self.logger.info("NewsAPI initialized")
            return True
            
        except ImportError:
            self.logger.error(
                "requests not installed. Install with: pip install requests"
            )
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize NewsAPI: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from NewsAPI."""
        if self.session:
            self.session.close()
        self._connected = False
        self.session = None
        self.logger.info("NewsAPI disconnected")
    
    def _ensure_connected(self):
        """Ensure connection is established."""
        if not self._connected or self.session is None:
            raise RuntimeError("NewsAPI not connected. Call connect() first.")
    
    def search_news(
        self,
        query: str,
        days_back: int = 7,
        language: str = "en",
        sort_by: str = "publishedAt"
    ) -> List[NewsArticle]:
        """
        Search for news articles.
        
        Args:
            query: Search query
            days_back: Number of days to look back
            language: Language code (en, es, fr, etc.)
            sort_by: Sort order (publishedAt, relevancy, popularity)
            
        Returns:
            List of NewsArticle
        """
        try:
            self._ensure_connected()
            self.rate_limiter.wait_if_needed()
            
            # Calculate date range
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days_back)
            
            # Build request
            url = f"{self.base_url}/everything"
            params = {
                'q': query,
                'from': from_date.isoformat(),
                'to': to_date.isoformat(),
                'language': language,
                'sortBy': sort_by,
                'apiKey': self.config.api_key,
            }
            
            response = self.session.get(url, params=params, timeout=getattr(self.config, 'timeout', 30))
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') != 'ok':
                self.logger.error(f"NewsAPI error: {data.get('message')}")
                return []
            
            articles = []
            
            for item in data.get('articles', []):
                # Parse published date
                published_str = item.get('publishedAt', '')
                try:
                    published_at = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                except:
                    published_at = datetime.now()
                
                articles.append(NewsArticle(
                    headline=item.get('title', ''),
                    body=item.get('description', ''),
                    source=item.get('source', {}).get('name', 'Unknown'),
                    published_at=published_at,
                    url=item.get('url'),
                    sentiment_score=None,  # NewsAPI doesn't provide sentiment
                    relevance_score=None,
                ))
            
            self.logger.info(f"Retrieved {len(articles)} articles for query: {query}")
            return articles
            
        except Exception as e:
            self.logger.error(f"Failed to search news: {e}")
            return []
    
    def get_company_news(
        self,
        company_name: str,
        days_back: int = 7
    ) -> List[NewsArticle]:
        """
        Get news for a company by name.
        
        Args:
            company_name: Company name (e.g., "Apple", "Microsoft")
            days_back: Number of days to look back
            
        Returns:
            List of NewsArticle
        """
        return self.search_news(company_name, days_back=days_back)
    
    def get_ticker_news(
        self,
        ticker: str,
        company_name: str,
        days_back: int = 7
    ) -> List[NewsArticle]:
        """
        Get news for a ticker, searching by both ticker and company name.
        
        Args:
            ticker: Stock ticker symbol
            company_name: Company name
            days_back: Number of days to look back
            
        Returns:
            List of NewsArticle
        """
        ticker = normalize_ticker(ticker)
        
        # Search by both ticker and company name
        query = f'"{ticker}" OR "{company_name}"'
        
        return self.search_news(query, days_back=days_back)


# ============================================================================
# ALPHA VANTAGE NEWS SENTIMENT
# ============================================================================

class AlphaVantageNewsDataSource:
    """
    Alpha Vantage News Sentiment API.
    
    Provides news articles with sentiment scores.
    Free tier: 25 requests/day
    
    Get API key: https://www.alphavantage.co/support/#api-key
    
    Usage:
        config = DataSourceConfig(
            api_key="your_alpha_vantage_key",
            rate_limit_calls=25,
            rate_limit_period=86400  # 1 day
        )
        
        av = AlphaVantageNewsDataSource(config)
        av.connect()
        
        # Get news with sentiment
        articles = av.get_news_sentiment("AAPL", days_back=7)
        for article in articles:
            print(f"{article.headline}")
            print(f"  Sentiment: {article.sentiment_score:.2f}")
            print(f"  Relevance: {article.relevance_score:.2f}")
        
        av.disconnect()
    """
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.logger = logging.getLogger("AlphaVantage")
        self.rate_limiter = RateLimiter(
            config.rate_limit_calls,
            config.rate_limit_period
        )
        self.session = None
        self.base_url = "https://www.alphavantage.co/query"
        self._connected = False
    
    def connect(self) -> bool:
        """Connect to Alpha Vantage."""
        try:
            import requests
            
            if not self.config.api_key:
                raise ValueError("Alpha Vantage requires an API key")
            
            self.session = requests.Session()
            self._connected = True
            self.logger.info("Alpha Vantage News initialized")
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
    
    def _ensure_connected(self):
        """Ensure connection is established."""
        if not self._connected or self.session is None:
            raise RuntimeError("Alpha Vantage not connected. Call connect() first.")
    
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
            self._ensure_connected()
            self.rate_limiter.wait_if_needed()
            
            ticker = normalize_ticker(ticker)
            
            # Calculate time range
            time_to = datetime.now()
            time_from = time_to - timedelta(days=days_back)
            
            # Build request
            params = {
                'function': 'NEWS_SENTIMENT',
                'tickers': ticker,
                'time_from': time_from.strftime('%Y%m%dT%H%M'),
                'time_to': time_to.strftime('%Y%m%dT%H%M'),
                'limit': limit,
                'apikey': self.config.api_key,
            }
            
            response = self.session.get(
                self.base_url,
                params=params,
                timeout=getattr(self.config, 'timeout', 30)
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check for errors
            if 'Error Message' in data:
                self.logger.error(f"Alpha Vantage error: {data['Error Message']}")
                return []
            
            if 'Note' in data:
                self.logger.warning(f"Alpha Vantage note: {data['Note']}")
                return []
            
            articles = []
            
            for item in data.get('feed', []):
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
                
                # Use ticker-specific sentiment if available, otherwise overall
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
            
            self.logger.info(f"Retrieved {len(articles)} articles with sentiment for {ticker}")
            return articles
            
        except Exception as e:
            self.logger.error(f"Failed to get news sentiment for {ticker}: {e}")
            return []
    
    def get_market_news(self, limit: int = 50) -> List[NewsArticle]:
        """
        Get general market news with sentiment.
        
        Args:
            limit: Maximum number of articles
            
        Returns:
            List of NewsArticle
        """
        try:
            self._ensure_connected()
            self.rate_limiter.wait_if_needed()
            
            params = {
                'function': 'NEWS_SENTIMENT',
                'limit': limit,
                'apikey': self.config.api_key,
            }
            
            response = self.session.get(
                self.base_url,
                params=params,
                timeout=getattr(self.config, 'timeout', 30)
            )
            response.raise_for_status()
            
            data = response.json()
            
            if 'Error Message' in data or 'Note' in data:
                return []
            
            articles = []
            
            for item in data.get('feed', []):
                time_str = item.get('time_published', '')
                try:
                    published_at = datetime.strptime(time_str, '%Y%m%dT%H%M%S')
                except:
                    published_at = datetime.now()
                
                articles.append(NewsArticle(
                    headline=item.get('title', ''),
                    body=item.get('summary', ''),
                    source=item.get('source', 'Unknown'),
                    published_at=published_at,
                    url=item.get('url'),
                    sentiment_score=safe_float(item.get('overall_sentiment_score')),
                    relevance_score=None,
                    keywords=[t.get('topic') for t in item.get('topics', []) if t.get('topic')],
                ))
            
            return articles
            
        except Exception as e:
            self.logger.error(f"Failed to get market news: {e}")
            return []


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    """Simple test of news data sources."""
    
    import os
    logging.basicConfig(level=logging.INFO)
    
    ticker = "AAPL"
    company = "Apple"
    
    # Test NewsAPI
    print(f"\n{'='*60}")
    print("Testing NewsAPI")
    print(f"{'='*60}\n")
    
    newsapi_key = os.environ.get('NEWSAPI_KEY')
    if newsapi_key:
        config = DataSourceConfig(
            api_key=newsapi_key,
            rate_limit_calls=100,
            rate_limit_period=86400
        )
        
        news_api = NewsAPIDataSource(config)
        news_api.connect()
        
        articles = news_api.get_ticker_news(ticker, company, days_back=7)
        print(f"Found {len(articles)} articles from NewsAPI")
        
        for i, article in enumerate(articles[:5], 1):
            print(f"\n{i}. {article.headline}")
            print(f"   Source: {article.source}")
            print(f"   Date: {article.published_at.date()}")
        
        news_api.disconnect()
    else:
        print("Skipping NewsAPI test (no API key in NEWSAPI_KEY env var)")
    
    # Test Alpha Vantage
    print(f"\n{'='*60}")
    print("Testing Alpha Vantage News Sentiment")
    print(f"{'='*60}\n")
    
    av_key = os.environ.get('ALPHAVANTAGE_KEY')
    if av_key:
        config = DataSourceConfig(
            api_key=av_key,
            rate_limit_calls=25,
            rate_limit_period=86400
        )
        
        av = AlphaVantageNewsDataSource(config)
        av.connect()
        
        articles = av.get_news_sentiment(ticker, days_back=7)
        print(f"Found {len(articles)} articles with sentiment from Alpha Vantage")
        
        for i, article in enumerate(articles[:5], 1):
            print(f"\n{i}. {article.headline}")
            print(f"   Source: {article.source}")
            print(f"   Date: {article.published_at.date()}")
            print(f"   Sentiment: {article.sentiment_score:.3f}")
            print(f"   Relevance: {article.relevance_score:.3f}" if article.relevance_score else "")
        
        av.disconnect()
    else:
        print("Skipping Alpha Vantage test (no API key in ALPHAVANTAGE_KEY env var)")
    
    print(f"\n{'='*60}")
    print("Tests completed!")
    print(f"{'='*60}\n")
