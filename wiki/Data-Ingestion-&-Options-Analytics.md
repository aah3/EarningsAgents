# 📈 Data Ingestion & Options Analytics

The data aggregation layer (`data/data_aggregator.py`) combines financial data feeds into a unified context packet passed to the agents prior to debate.

---

## 🌐 Integrated Data Feeds

```
                   ┌─────────────────────────────────────────┐
                   │          Data Aggregator Engine         │
                   │        (data/data_aggregator.py)        │
                   └────────────────────┬────────────────────┘
                                        │
      ┌──────────────────┬──────────────┴───────┬──────────────────┐
      ▼                  ▼                      ▼                  ▼
┌───────────┐      ┌───────────┐          ┌───────────┐      ┌───────────┐
│   Yahoo   │      │ SEC EDGAR │          │  NewsAPI  │      │   Alpha   │
│  Finance  │      │ 10-K/10-Q │          │ Headlines │      │ Vantage   │
└─────┬─────┘      └─────┬─────┘          └─────┬─────┘      └─────┬─────┘
      │                  │                      │                  │
      └──────────────────┴──────────────┬───────┴──────────────────┘
                                        ▼
                           UNIFIED AGENT CONTEXT PACKET
```

### 1. Yahoo Finance API (`data/yahoo_finance.py`)
- **Fundamentals:** Company profile, industry sector, market cap, enterprise value, EV/EBITDA, forward P/E ratio.
- **Surprise History:** Past 4 quarters reported EPS vs. estimates, surprise percentages.
- **Price Momentum:** 5-day, 21-day, and 63-day relative price momentum vs S&P 500 index.
- **Analyst Ratings:** Consensus recommendation (Buy/Hold/Sell) and target price range.

### 2. SEC EDGAR Parser (`data/sec_edgar.py`)
- Ingests official SEC filings (10-K annual reports, 10-Q quarterly reports, 8-K current reports).
- Maps tickers to Central Index Key (CIK) numbers.
- Extracts Management's Discussion and Analysis (MD&A) sections and risk factors.
- *Rate Limits:* Adheres to SEC 10 requests/second policy. Controlled via `SEC_ENABLED` setting.

### 3. News & Sentiment Ingestion (`data/alpha_vantage.py`)
- **NewsAPI:** Pulls media coverage across financial publications over the 14 days leading to earnings.
- **Alpha Vantage Sentiment:** Assigns pre-calculated sentiment scores ($-1.0$ extreme negative to $+1.0$ extreme positive) and ticker relevance weights to recent articles.

### 4. Pluggable Custom Data Providers (`data/provider_registry.py`)
- **Domain Protocols:** `IPriceProvider`, `IOptionChainProvider`, `IEarningsEstimateProvider`, `IFinancialsProvider`, `INewsTranscriptProvider`.
- **Custom Client Connectors (`data/adapters/`):** Clients can plug in internal SQL databases (PostgreSQL, Snowflake), custom REST APIs, or enterprise feeds (FactSet/Bloomberg) for any field domain.
- **Fallback Cascades (`data/provider_chain.py`):** `DataAggregator` checks client-registered providers first, falling back to default feeds if data is missing or raises an exception.
- For complete setup instructions and adapter code templates, see [Custom Data Ingestion Guide](file:///c:/Users/alfredo/Project/EarningsAgents/docs/CUSTOM_DATA_SOURCES.md).

---

## 🎯 Options Chain Analytics & ATM Straddles

The Options analysis module (`data/options.py`) computes expected stock price movements using option chain pricing near earnings expiration dates:

### 1. ATM Straddle Implied Move Calculation

The expected percentage move implied by option markets is derived from the At-The-Money (ATM) call and put premiums:

$$Implied\ Move\ (\%) = \frac{\text{ATM Call Price} + \text{ATM Put Price}}{\text{Current Stock Price}} \times 100$$

Alternatively, when using Black-Scholes implied volatility ($\sigma$), contract duration ($t$), and standard adjustment factors ($0.8$ straddle rule):

$$Implied\ Move\ (\%) \approx 0.8 \times \sigma \times \sqrt{t}$$

### 2. Market Metrics Parsed by Quant Agent
- **Implied Volatility (IV) Percentile:** Position of current IV relative to 52-week IV range. High IV percentile indicates elevated market anticipation/uncertainty.
- **Put/Call Volume & Open Interest Ratios:** Gauges institutional positioning and hedging demand.
- **Move vs. Implied Comparison:** The Quant Agent compares the model's expected price move against the market's implied move to identify potential over- or under-priced volatility opportunities.
