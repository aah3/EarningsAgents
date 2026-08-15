---
name: run-backtest-and-scoring
description: Workflow for running historical earnings backtests, evaluating prediction accuracy, computing Brier scores, and generating summary reports.
---

# Backtesting & Scoring Workflow

Follow this procedure when evaluating earnings agent performance on historical earnings events, scoring predictions, or generating summary reports.

## 1. Setup Target Batch & Date Ranges
1. Prepare batch prediction list or ticker parameters using `main.py` CLI or a dedicated runner script (e.g. `run_batch_debate.py`).
2. Ensure earnings announcement timing metadata (BMO / AMC) and target report dates are correctly set.

## 2. Execute Prediction Batch
1. Run execution via CLI or script:
   ```bash
   python main.py single --ticker AAPL --report-date 2026-07-30
   ```
2. Verify output consensus reports are saved in `scratch_output/`, `reports/`, or `output/`.

## 3. Score Outcomes & Verify EPS Metrics
1. Execute outcome evaluation via [`database/scoring_service.py`](file:///c:/Users/alfredo/Project/EarningsAgents/database/scoring_service.py) or `make score-now`:
   ```bash
   make score-now
   ```
2. **Verification Check**: Confirm that `actual_eps` and `actual_price_move_pct` reflect verified reported numbers and have not defaulted to `0.0` or `null` silently.
3. Review updated Brier scores: `(confidence/100 - correct)^2`.

## 4. Verification
1. Inspect database records or report JSON files to confirm metrics.
2. Run automated test suite:
   ```bash
   python -m pytest tests/test_scoring.py -v
   ```
