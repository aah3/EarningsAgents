# Data Module Documentation

The data module provides a unified interface for accessing multiple financial data sources for earnings prediction.

## Architecture

```
data/
├── base.py                  # Base classes, Pydantic models, utilities
├── yahoo_finance.py         # Yahoo Finance data source
├── sec_edgar.py            # SEC EDGAR filings and transcripts
├── news_sources.py         # NewsAPI and Alpha Vantage sentiment
├── data_aggregator.py      # Combines all sources
└── __init__.py             # Module exports
```

## Data Sources

### 1. Yahoo Finance (Primary)
**Purpose:** Market data, fundamentals, analyst estimates  
**Cost:** Free  
**Rate Limit:** ~2000 requests/hour (unofficial)

**Provides:**
- Company information (sector, industry, market cap)
- Price data and momentum indicators
- Historical earnings results
- Consensus estimates
- Analyst recommendations
- Earnings calendar

**Installation:**
```bash
pip install yfinance
```

**Usage:**
```python
from data import YahooFinanceDataSource, DataSourceConfig

config = DataSourceConfig(rate_limit_calls=2000, rate_limit_period=3600)
yahoo = YahooFinanceDataSource(config)
yahoo.connect()

# Get company info
info = yahoo.get_company_info("AAPL")
print(f"{info.company_name} - ${info.market_cap/1e9:.1f}B")

# Get price data
price = yahoo.get_price_data("AAPL")
print(f"Price: ${price.current_price:.2f}")
print(f"5D Change: {price.price_change_5d:.2%}")

# Get historical earnings
earnings = yahoo.get_historical_earnings("AAPL", 8)
for e in earnings:
    print(f"{e.date}: {'BEAT' if e.beat else 'MISS'} by {e.surprise_pct:+.1f}%")

yahoo.disconnect()
```

### 2. SEC EDGAR
**Purpose:** Official company filings and transcripts  
**Cost:** Free  
**Rate Limit:** 10 requests/second (SEC requirement)

**Provides:**
- 10-K, 10-Q, 8-K filings
- Earnings call transcripts (some companies)
- XBRL financial data
- Company CIK lookup

**Installation:**
```bash
pip install requests beautifulsoup4
```

**Usage:**
```python
from data import SECEdgarDataSource, DataSourceConfig

config = DataSourceConfig(rate_limit_calls=10, rate_limit_period=1)
sec = SECEdgarDataSource(config, user_agent="MyApp/1.0 (email@example.com)")
sec.connect()

# Get CIK
cik = sec.get_cik("AAPL")

# Get recent 8-K filings
filings = sec.get_filings("AAPL", filing_type="8-K", limit=10)
for f in filings:
    print(f"{f.filing_date}: {f.filing_type}")

# Search for transcripts
transcripts = sec.get_earnings_transcripts("AAPL", year=2024)

sec.disconnect()
```

**Note:** Not all companies file transcripts with SEC. For comprehensive coverage, use specialized services like FactSet CallStreet or AlphaSense.

### 3. NewsAPI
**Purpose:** News headlines from 80,000+ sources  
**Cost:** Free tier (100 requests/day), Paid plans available  
**Rate Limit:** 100/day (free), 1000/day (developer)

**Provides:**
- Recent news headlines
- Article summaries
- Source attribution
- Time-based filtering

**Setup:**
1. Get API key: https://newsapi.org/
2. Set environment variable: `export NEWSAPI_KEY=your_key`

**Usage:**
```python
from data import NewsAPIDataSource, DataSourceConfig
import os

config = DataSourceConfig(
    api_key=os.environ['NEWSAPI_KEY'],
    rate_limit_calls=100,
    rate_limit_period=86400
)

news_api = NewsAPIDataSource(config)
news_api.connect()

# Get company news
articles = news_api.get_ticker_news("AAPL", "Apple", days_back=7)
for article in articles:
    print(f"{article.published_at.date()}: {article.headline}")
    print(f"  Source: {article.source}")

news_api.disconnect()
```

### 4. Alpha Vantage News Sentiment
**Purpose:** News with pre-calculated sentiment scores  
**Cost:** Free tier (25 requests/day), Paid plans available  
**Rate Limit:** 25/day (free), 75/day (basic)

**Provides:**
- News articles with sentiment analysis
- Ticker-specific relevance scores
- Overall and ticker-level sentiment
- Topic categorization

**Setup:**
1. Get API key: https://www.alphavantage.co/support/#api-key
2. Set environment variable: `export ALPHAVANTAGE_KEY=your_key`

**Usage:**
```python
from data import AlphaVantageNewsDataSource, DataSourceConfig
import os

config = DataSourceConfig(
    api_key=os.environ['ALPHAVANTAGE_KEY'],
    rate_limit_calls=25,
    rate_limit_period=86400
)

av = AlphaVantageNewsDataSource(config)
av.connect()

# Get news with sentiment
articles = av.get_news_sentiment("AAPL", days_back=7)
for article in articles:
    print(f"{article.headline}")
    print(f"  Sentiment: {article.sentiment_score:+.3f}")
    print(f"  Relevance: {article.relevance_score:.3f}")

av.disconnect()
```

### 5. Options Market Data
**Purpose:** Pre-earnings implied moves, sentiment, and volatility  
**Cost:** Free (via Yahoo Finance options chain)

**Provides:**
- Implied percent move from straddle pricing
- Call/Put volume and Open Interest ratios
- ATM Implied Volatility
- Detailed option contract metrics and Greeks

**Usage:**
Options data is automatically fetched and parsed by the `DataAggregator` during the company data retrieval process to populate `options_features` and is processed by the Quant agent.

## Data Aggregator (Recommended)

The `DataAggregator` combines all sources with intelligent fallback:

```python
from data import DataAggregator, DataSourceConfig
from datetime import date
import os

# Configure sources
yahoo_config = DataSourceConfig(rate_limit_calls=2000, rate_limit_period=3600)
newsapi_config = DataSourceConfig(
    api_key=os.environ.get('NEWSAPI_KEY'),
    rate_limit_calls=100,
    rate_limit_period=86400
)
av_config = DataSourceConfig(
    api_key=os.environ.get('ALPHAVANTAGE_KEY'),
    rate_limit_calls=25,
    rate_limit_period=86400
)

# Initialize aggregator
aggregator = DataAggregator(
    yahoo_config=yahoo_config,
    newsapi_config=newsapi_config,
    alphavantage_config=av_config,
    enable_yahoo=True,
    enable_newsapi=True,
    enable_alphavantage=True,
    enable_sec=False,  # Optional
)

aggregator.initialize()

# Get comprehensive company data
ticker = "AAPL"
report_date = date(2024, 2, 1)

company = aggregator.get_company_data(ticker, report_date)
print(f"Company: {company.company_name}")
print(f"Sector: {company.sector}")
print(f"Consensus EPS: ${company.consensus_eps:.2f}")
print(f"Beat Rate (4Q): {company.beat_rate_4q:.0%}")
if company.options_features and 'implied_move' in company.options_features:
    implied_pct = company.options_features['implied_move'].get('straddle_implied_move_pct', 0)
    print(f"Options Implied Move: {implied_pct:.1%}")

# Get news with sentiment (combines NewsAPI + Alpha Vantage)
news = aggregator.get_news_with_sentiment(
    ticker, 
    company.company_name,
    days_back=30,
    max_articles=50
)

for article in news[:10]:
    sentiment_str = f" [{article.sentiment_score:+.2f}]" if article.sentiment_score else ""
    print(f"{article.published_at.date()}: {article.headline}{sentiment_str}")

aggregator.shutdown()
```

## Pydantic Models

All data is returned as strongly-typed Pydantic models:

### CompanyInfo
```python
CompanyInfo(
    ticker="AAPL",
    company_name="Apple Inc.",
    sector="Technology",
    industry="Consumer Electronics",
    market_cap=3000000000000.0,
    exchange="NASDAQ",
    currency="USD"
)
```

### PriceData
```python
PriceData(
    current_price=182.52,
    price_change_5d=0.023,
    price_change_21d=-0.045,
    volume=45000000.0,
    beta=1.25,
    as_of_date=date(2024, 2, 7)
)
```

### HistoricalEarning
```python
HistoricalEarning(
    date=date(2024, 1, 25),
    actual_eps=2.18,
    estimate_eps=2.10,
    surprise_pct=3.81,
    beat=True,
    fiscal_quarter="Q1",
    fiscal_year=2024
)
```

### NewsArticle
```python
NewsArticle(
    headline="Apple Reports Record Quarter",
    body="Apple Inc. announced...",
    source="Bloomberg",
    published_at=datetime(2024, 2, 1, 15, 30),
    url="https://...",
    sentiment_score=0.75,  # -1 to 1
    relevance_score=0.92,  # 0 to 1
    keywords=["earnings", "revenue"]
)
```

## Testing Each Source

Each data source file includes a test script at the bottom:

```bash
# Test Yahoo Finance
python -m data.yahoo_finance

# Test SEC EDGAR
python -m data.sec_edgar

# Test News Sources
export NEWSAPI_KEY=your_key
export ALPHAVANTAGE_KEY=your_key
python -m data.news_sources

# Test Aggregator
python -m data.data_aggregator
```

## Rate Limiting

All sources implement automatic rate limiting:

```python
from data import RateLimiter

# 10 calls per second
limiter = RateLimiter(max_calls=10, period=1.0)

for i in range(100):
    limiter.wait_if_needed()  # Automatically sleeps if needed
    make_api_call()
```

## Error Handling

All data source methods handle errors gracefully:

- Return `None` for missing single items
- Return empty lists `[]` for collections
- Log warnings for non-critical failures
- Raise exceptions only for critical initialization failures

```python
info = yahoo.get_company_info("INVALID")  # Returns None, logs warning

articles = newsapi.get_ticker_news("XYZ", "XYZ Corp", days_back=7)  # Returns [], logs warning
```

## Best Practices

### 1. Use DataAggregator for Production
The aggregator handles fallback, deduplication, and merging:

```python
aggregator = DataAggregator(yahoo_config=config)
company = aggregator.get_company_data("AAPL", report_date)
```

### 2. Enable Only Needed Sources
Don't enable sources you won't use:

```python
aggregator = DataAggregator(
    yahoo_config=yahoo_config,
    enable_yahoo=True,
    enable_newsapi=False,  # Skip if no API key
    enable_alphavantage=False,
    enable_sec=False,
)
```

### 3. Respect Rate Limits
Configure appropriate rate limits:

```python
# NewsAPI free tier
newsapi_config = DataSourceConfig(
    api_key=key,
    rate_limit_calls=100,
    rate_limit_period=86400  # 1 day
)

# Alpha Vantage free tier
av_config = DataSourceConfig(
    api_key=key,
    rate_limit_calls=25,
    rate_limit_period=86400
)
```

### 4. Cache Results
For batch processing, cache data to minimize API calls:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_company_data_cached(ticker: str, report_date: date):
    return aggregator.get_company_data(ticker, report_date)
```

## Limitations

### Yahoo Finance
- ❌ No detailed estimate revisions history
- ❌ Limited fundamental data
- ❌ Unofficial API (may break)
- ✅ Free and reliable for basic data

### SEC EDGAR
- ❌ Not all companies file transcripts
- ❌ Delayed filings
- ✅ Official, authoritative source
- ✅ Free and comprehensive

### NewsAPI
- ❌ Free tier limited to 100 requests/day
- ❌ No sentiment analysis
- ✅ 80,000+ sources
- ✅ Good coverage

### Alpha Vantage
- ❌ Free tier limited to 25 requests/day
- ❌ Sometimes slow response
- ✅ Pre-calculated sentiment
- ✅ Ticker-specific relevance

## Upgrade Path for Production

For production use, consider:

1. **FactSet or Refinitiv** - Professional estimates and revisions
2. **Bloomberg Terminal** - Gold standard for institutional data
3. **CallStreet/AlphaSense** - Comprehensive transcript coverage
4. **RavenPack** - Professional news analytics
5. **Polygon.io** - Reliable market data API

## Support

For issues or questions:
- Yahoo Finance: Community support (unofficial API)
- SEC EDGAR: https://www.sec.gov/os/accessing-edgar-data
- NewsAPI: https://newsapi.org/docs
- Alpha Vantage: https://www.alphavantage.co/support/
