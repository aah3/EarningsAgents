---
name: run-batch-debate
description: Workflow and best practices for executing single-ticker and multi-ticker earnings agent debates efficiently via CLI, Celery tasks, or parameterized runners.
---

# Single-Ticker & Batch Stock Debate Skill

This skill defines the standardized workflow for running Bull/Bear/Quant multi-agent earnings debates for single stocks or ticker batches.

---

## 1. Key Learnings & Architecture

### What We Learned From Previous Runs
1. **Avoid One-Off Script Sprawl**: Creating bespoke files like `run_googl_debate.py` or `run_nflx_debate.py` for every stock or date causes severe root workspace clutter. All single and batch runs should use parameterized entry points (`main.py` or `scripts/batch_runners/`).
2. **Sequential vs. Parallel Execution**:
   - Running multi-ticker batches sequentially in a single Python loop can take 2–5 minutes per ticker (especially if ReAct tool loops or rebuttal passes are enabled).
   - Pass 1 (Bull, Bear, Quant agents) executes in parallel within `ThreeAgentSystem`.
   - Batch runs across multiple tickers should leverage **Celery background workers** (`api.tasks.analyze_ticker_task`) or async task queues for maximum throughput.
3. **Execution Modes**:
   - **Fast Mode**: Standard 1-pass generation without ReAct tools or rebuttals. Best for large batch screening.
   - **Deep Mode**: Enables `AgentConfig.use_react=True` (ReAct tool-call loop) and `AgentConfig.enable_rebuttals=True` (cross-examination pass). Best for high-conviction single-stock analysis.
4. **Data Verification Invariants**:
   - `actual_eps` and `actual_price_move_pct` must never default to `0.0` or `null` during outcome evaluation without explicit verification against financial data providers.
   - Always sanitize ticker symbols (e.g. `AAPL`, `GOOGL`) before rendering or database insertion.

---

## 2. Running Single-Stock Debates

### Standard CLI Entry Point (Recommended)
Use `main.py` directly without creating new Python files:

```bash
# Standard single stock prediction
.venv/Scripts/python main.py single --ticker GOOGL --report-date 2026-07-23

# Single stock with user-provided qualitative analysis / context
.venv/Scripts/python main.py single --ticker INTC --report-date 2026-07-24 --user-analysis "Management indicated server chip recovery in Q3."
```

### Scripted Single Debate (if customizing Pipeline parameters)
If special overrides (e.g., forcing BMO/AMC report time) are required, execute via `scripts/batch_runners/run_batch_debate.py` or modify parameters dynamically instead of creating a top-level file:

```python
from settings import load_config, ReportTime
from pipeline import EarningsPipeline

config = load_config()
pipeline = EarningsPipeline(config)
result = pipeline.predict_single(ticker="GOOGL", report_date=date(2026, 7, 23), force_report_time=ReportTime.AMC)
```

---

## 3. Running Multi-Ticker Batch Debates

### Option A: Parameterized Batch Runner (CLI)
To run a batch of specific tickers without writing new code:

```bash
.venv/Scripts/python scripts/batch_runners/run_batch_debate.py --tickers AAPL,AMZN,GOOGL,MSFT --report-date 2026-07-25
```

### Option B: Calendar-Driven Daily/Weekly Batch
To run predictions for all earnings announcements scheduled for a given day or week:

```bash
# Daily predictions for a specific date
.venv/Scripts/python main.py daily --date 2026-07-25

# Weekly predictions for an entire week
.venv/Scripts/python main.py weekly --week 2026-07-21 --output csv
```

### Option C: Parallel Async Execution via Celery (High Efficiency)
For large batches, dispatch predictions to Celery workers for parallel background processing:

```python
from api.tasks import analyze_ticker_task

tickers = ["PLTR", "ADUS", "CLPT", "CBT"]
report_date = "2026-08-03"

for ticker in tickers:
    # Dispatches to Celery worker pool
    analyze_ticker_task.delay(ticker=ticker, report_date=report_date)
```

---

## 4. Efficiency & Performance Guidelines

1. **Leverage Client-Side & Provider Caching**:
   - Ticker metadata and recent price history are cached client-side/in-memory to prevent redundant API calls to Yahoo Finance or SEC EDGAR.
2. **Provider Fallback & Rate Limiting**:
   - The LLM client automatically handles rate limits (`429`) with backoff and falls back using `FALLBACK_MAP` (e.g. Gemini -> Anthropic -> OpenAI).
3. **Output Reporting**:
   - Generated reports auto-export to `reports/` or `scratch_output/`.
   - Predictions are automatically saved to `earnings_agents.db` (or Postgres) for Brier score tracking.

---

## 5. Verification & Output Checklist

When completing a debate run, verify:
- [ ] Prediction record created in DB with valid direction (`BEAT` / `MISS` / `MEET`) and confidence percentage.
- [ ] Reasoning summary and Bull/Bear factors populated in prediction output.
- [ ] Markdown report emitted to `reports/` or `scratch_output/`.
- [ ] Actual EPS and price move validated prior to post-earnings outcome scoring.
