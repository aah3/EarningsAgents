# Earnings Prediction POC

A simplified proof-of-concept for AI-powered earnings predictions using AI agents and open source or paid data providers such as Bloomberg BQL data.

## Overview

This POC uses a **three-agent debate system** to predict earnings surprises:

```
                    Company Data (Bloomberg BQL)
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │   BULL   │   │   BEAR   │   │  QUANT   │
        │  Agent   │   │  Agent   │   │  Agent   │
        │ (BEAT)   │   │ (MISS)   │   │ (DATA)   │
        └────┬─────┘   └────┬─────┘   └────┬─────┘
             └──────────────┼──────────────┘
                           ▼
                  ┌──────────────────┐
                  │    CONSENSUS     │
                  │     Agent        │
                  └────────┬─────────┘
                           ▼
                     FINAL PREDICTION
```

## Requirements

- Python 3.9+
- Bloomberg Terminal (for BQL data)
- Hugging Face account (for Inference API, optional)

## Installation

```bash
pip install -r requirements.txt

# If you have Bloomberg Terminal:
pip install bql
```

## Quick Start

### Single Company Prediction

```bash
python main.py single --ticker AAPL --report-date 2024-01-25
```

### Weekly Predictions

```bash
python main.py weekly --week 2024-01-15
```

### With Options

```bash
# Use different benchmark
python main.py weekly --week 2024-01-15 --benchmark NDX

# Output to CSV
python main.py weekly --week 2024-01-15 --output csv

# Use local model (requires GPU)
python main.py single --ticker AAPL --report-date 2024-01-25 --local

# Use different model
python main.py single --ticker AAPL --report-date 2024-01-25 \
    --model meta-llama/Llama-2-7b-chat-hf
```

## Python API

```python
from datetime import date
from config import PipelineConfig, AgentConfig
from pipeline import EarningsPipeline

# Configure
config = PipelineConfig(
    benchmark="SPX",
    agent=AgentConfig(
        model_name="mistralai/Mistral-7B-Instruct-v0.2",
        use_local=False,  # Use HF Inference API
    ),
    enable_debate=True,
)

# Run pipeline
pipeline = EarningsPipeline(config)
pipeline.initialize()

# Single prediction
prediction = pipeline.predict_single("AAPL", date(2024, 1, 25))
print(f"Prediction: {prediction.direction.value} ({prediction.confidence:.0%})")
print(f"Agent Votes: {prediction.agent_votes}")

# Weekly predictions
predictions = pipeline.run_weekly(date(2024, 1, 15))

pipeline.shutdown()
```

## Project Structure

```
earnings_poc/
├── config/
│   ├── __init__.py
│   └── settings.py      # Configuration dataclasses
├── data/
│   ├── __init__.py
│   └── bloomberg.py     # Bloomberg BQL data source
├── agents/
│   ├── __init__.py
│   └── huggingface_agents.py  # Bull, Bear, Quant, Consensus agents
├── output/
│   ├── __init__.py
│   └── writer.py        # Parquet/CSV/JSON output
├── pipeline.py          # Main orchestrator
├── main.py              # CLI entry point
├── requirements.txt
└── README.md
```

## Agent Roles

| Agent | Role | Focus |
|-------|------|-------|
| **Bull** | Advocate for BEAT | Revenue growth, margins, momentum |
| **Bear** | Advocate for MISS | Risks, headwinds, concerns |
| **Quant** | Data analysis | Historical patterns, statistics |
| **Consensus** | Final decision | Weighs all arguments |

## Output

Predictions are saved with:
- Ticker and company name
- Prediction (BEAT/MISS/MEET)
- Confidence score
- Reasoning summary
- Agent votes
- Full debate transcript

## Extending to Production

This POC can be expanded into a full product by:

1. **Add more data sources**: Yahoo Finance, Alpha Vantage for non-Bloomberg users
2. **Add more LLM providers**: Anthropic Claude, OpenAI GPT, Google Gemini
3. **Add backtesting**: Track prediction accuracy over time
4. **Add feature engineering**: More sophisticated signal extraction
5. **Add scheduling**: Automated weekly runs
6. **Add web interface**: Dashboard for viewing predictions

See the full framework in `earnings_predictor/` for reference implementation.

## License

MIT
