"""
Data module for Earnings Prediction POC.

Provides unified access to multiple data sources:
- Yahoo Finance: Market data, fundamentals, estimates
- SEC EDGAR: Filings and transcripts
- NewsAPI: News headlines
- Alpha Vantage: News with sentiment scores

Usage:
    from data import DataAggregator, DataSourceConfig
    
    # Configure
    config = DataSourceConfig(rate_limit_calls=2000)
    aggregator = DataAggregator(yahoo_config=config)
    aggregator.initialize()
    
    # Get data
    company = aggregator.get_company_data("AAPL", date.today())
    news = aggregator.get_news_with_sentiment("AAPL", "Apple", days_back=30)
    
    aggregator.shutdown()
"""

from .base import (
    # Enums
    PredictionDirection,
    ReportTime,
    RevisionDirection,
    
    # Models
    HistoricalEarning,
    EstimateRevision,
    AnalystRecommendation,
    ConsensusEstimate,
    PriceData,
    NewsArticle,
    CompanyInfo,
    EarningsEvent,
    CompanyData,
    
    # Base classes
    BaseDataSource,
    DataSourceConfig,
    RateLimiter,
    
    # Utilities
    normalize_ticker,
    safe_float,
    safe_int,
)

from .yahoo_finance import YahooFinanceDataSource
from .sec_edgar import SECEdgarDataSource, SECFiling, EarningsTranscript
from .news_sources import NewsAPIDataSource, AlphaVantageNewsDataSource
from .data_aggregator import DataAggregator


__all__ = [
    # Enums
    'PredictionDirection',
    'ReportTime',
    'RevisionDirection',
    
    # Models
    'HistoricalEarning',
    'EstimateRevision',
    'AnalystRecommendation',
    'ConsensusEstimate',
    'PriceData',
    'NewsArticle',
    'CompanyInfo',
    'EarningsEvent',
    'CompanyData',
    'SECFiling',
    'EarningsTranscript',
    
    # Data sources
    'YahooFinanceDataSource',
    'SECEdgarDataSource',
    'NewsAPIDataSource',
    'AlphaVantageNewsDataSource',
    'DataAggregator',
    
    # Configuration
    'BaseDataSource',
    'DataSourceConfig',
    'RateLimiter',
    
    # Utilities
    'normalize_ticker',
    'safe_float',
    'safe_int',
]
