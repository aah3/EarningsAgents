---
name: options-analytics-modeling
description: Workflow for processing options chain data, calculating ATM straddle implied volatility/moves, and feeding analytics to the Quant agent.
---

# Options Analytics & Implied Move Workflow

Follow this procedure when modifying options analytics in [`data/options.py`](file:///c:/Users/alfredo/Project/EarningsAgents/data/options.py) or updating market hours volatility labeling.

## 1. Options Data Pipeline Architecture
1. [`data/options.py`](file:///c:/Users/alfredo/Project/EarningsAgents/data/options.py) fetches options chains (Yahoo Finance / AlphaVantage).
2. Calculates ATM (At-The-Money) straddle prices to derive expected earnings implied movement:
   $$\text{Implied Move \%} = \frac{\text{Call Price} + \text{Put Price}}{\text{Underlying Price}}$$
3. Extracts implied volatility (IV) crush expectations and Greeks.

## 2. Market Hours Invariant (`data/market_hours.py`)
- Options snapshot metrics are labeled with market session state (`LIVE` vs `LAST-CLOSE`).
- **Quant Agent Invariant**: The Quant agent system prompt in [`agents/huggingface_agents.py`](file:///c:/Users/alfredo/Project/EarningsAgents/agents/huggingface_agents.py) explicitly distinguishes `LIVE` vs `LAST-CLOSE` options metrics. Never remove session tagging when modifying options models.

## 3. Verification
1. Test options analytics standalone:
   ```bash
   python -m pytest tests/test_custom_data_ingestion.py -v
   ```
2. Run pipeline options check:
   ```bash
   python verify_settings.py
   ```
