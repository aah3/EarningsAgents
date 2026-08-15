---
name: add-data-source
description: Workflow for adding, configuring, and integrating a new market, financial, or news data provider into the EarningsAgents data pipeline.
---

# Add Data Source Workflow

Follow this procedure when implementing a new data provider (e.g., FMP, Polygon, custom RSS, or SEC filings expansion) into the `EarningsAgents` data pipeline.

## 1. Create Provider Client (`data/`)
1. Create a new module in `data/` (e.g., `data/fmp_source.py`) subclassing or matching `data/base.py` interface patterns.
2. Ensure robust error handling, standard timeout/retry logic, and rate-limiting safeguards.
3. Normalize all ticker input (strip whitespace, upper-case).
4. Return structures compatible with `CompanyData` / `DataSourceConfig` defined in [`config/settings.py`](file:///c:/Users/alfredo/Project/EarningsAgents/config/settings.py).

## 2. Config & Dual-Import Preservation
1. Add configuration flags / API keys to `DataSourceConfig` in [`config/settings.py`](file:///c:/Users/alfredo/Project/EarningsAgents/config/settings.py) and `.env.example`.
2. Preserve the project's dual-import shim pattern when importing settings or helpers:
   ```python
   try:
       from settings import load_config
   except ImportError:
       from config.settings import load_config
   ```

## 3. Register in DataAggregator & Provider Chain
1. Instantiate the provider in `DataAggregator.__init__` in [`data/data_aggregator.py`](file:///c:/Users/alfredo/Project/EarningsAgents/data/data_aggregator.py).
2. Register the source in [`data/provider_chain.py`](file:///c:/Users/alfredo/Project/EarningsAgents/data/provider_chain.py) or `data/provider_registry.py` to support graceful fallback ordering.
3. Update `get_company_data(...)` in `DataAggregator` to invoke the provider when enabled.

## 4. Verification & Testing
1. Run standalone configuration verification:
   ```bash
   python verify_settings.py
   ```
2. Write unit/integration tests in `tests/` mocking API calls.
3. Run test suite:
   ```bash
   python -m pytest tests/ -v
   ```
