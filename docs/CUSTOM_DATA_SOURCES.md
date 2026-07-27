# Custom Data Ingestion Guide for Earnings Agents AI Framework

This guide explains how to plug custom client data sources (internal databases, proprietary REST APIs, FactSet/Bloomberg feeds, or local datasets) into the **Earnings Agents AI Framework**.

---

## 1. Architecture Overview

The Earnings Agents AI framework uses a **Pluggable Data Provider Architecture**. AI Agents (`QuantAgent`, `OptionsAgent`, `FundamentalAgent`, `DebateEngine`) operate strictly on canonical Pydantic domain models (`CompanyData`, `PriceData`, `ConsensusEstimate`, etc.). 

To inject your own data sources:
1. Implement one or more **Domain Interfaces** (`IPriceProvider`, `IOptionChainProvider`, `IEarningsEstimateProvider`, `IFinancialsProvider`, `INewsTranscriptProvider`).
2. Register your custom adapter using `ProviderRegistry` or pass it directly to `DataAggregator`.
3. Optionally configure custom field routing and fallbacks.

---

## 2. Implementing a Custom Data Adapter

Create a Python class implementing the required interface methods.

### Example: PostgreSQL / Snowflake Price Provider

```python
from datetime import date
from typing import Optional
from data.base import IPriceProvider, PriceData
import psycopg2

class ClientSQLPriceProvider(IPriceProvider):
    def __init__(self, db_url: str):
        self.db_url = db_url

    def get_price_data(self, ticker: str) -> Optional[PriceData]:
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT price, volume, beta, as_of_date 
                    FROM market_prices 
                    WHERE ticker = %s 
                    ORDER BY as_of_date DESC LIMIT 1
                """, (ticker,))
                row = cur.fetchone()
                if not row:
                    return None
                
                return PriceData(
                    current_price=float(row[0]),
                    volume=float(row[1]),
                    beta=float(row[2]),
                    as_of_date=row[3]
                )
```

---

## 3. Registering Your Custom Provider

### Option A: Programmatic Registration

```python
from data.provider_registry import ProviderRegistry
from data.data_aggregator import DataAggregator

# 1. Instantiate your custom provider
my_sql_provider = ClientSQLPriceProvider("postgresql://user:pass@localhost:5432/finance")

# 2. Register it globally
ProviderRegistry.register_provider("client_sql", my_sql_provider)

# 3. (Optional) Direct specific domains to use your provider first
ProviderRegistry.set_domain_providers("price_data", ["client_sql", "yahoo"])

# 4. Initialize DataAggregator as usual
aggregator = DataAggregator()
aggregator.initialize()
```

### Option B: Configuration-Driven Loading

Pass a configuration dictionary to `DataAggregator`:

```python
config = {
    "clients": {
        "client_sql": {
            "class": "data.adapters.client_sql_source.ClientSQLPriceProvider",
            "connection_string": "postgresql://user:pass@localhost:5432/finance"
        }
    },
    "routes": {
        "price_data": ["client_sql", "yahoo"],
        "consensus_estimates": ["client_api", "yahoo"]
    }
}

aggregator = DataAggregator(custom_config=config)
aggregator.initialize()
```

---

## 4. Fallback Mechanics

When fetching data for any field domain (e.g. `price_data`, `consensus_estimates`, `historical_earnings`), `ProviderChain` attempts data resolution in the configured priority order:
1. Primary Provider (e.g. `client_sql`)
2. Secondary Fallback (e.g. `yahoo`)

If the primary provider returns `None` or raises an exception (e.g. missing ticker or database timeout), `ProviderChain` automatically falls back to secondary sources while logging the event.
