---
name: run-test-suite-and-smoke
description: Workflow for executing Pytest unit tests, running live integration smoke tests, and adding tests for EarningsAgents.
---

# Test Suite & Smoke Testing Workflow

Follow this procedure when testing code changes, writing unit tests, or verifying system health.

## 1. Test Architecture Overview
- Default pytest collection covers `tests/test_*.py` and `test_earnings_enrichment.py` (configured in [`pytest.ini`](file:///c:/Users/alfredo/Project/EarningsAgents/pytest.ini)).
- Files in `tests/` starting with `run_*` or `smoke_test_*` are integration/smoke runners that call live/near-live endpoints or LLMs.

## 2. Running Automated Unit Tests
1. Run full unit test suite:
   ```bash
   make test
   # or: python -m pytest tests/ -v
   ```
2. Run single test file or specific test case:
   ```bash
   python -m pytest tests/test_agents.py -v
   python -m pytest tests/test_agents.py -v -k test_consensus
   ```

## 3. Running Live Integration Smoke Tests
1. Execute multi-phase smoke pipeline:
   ```bash
   make smoke
   ```
2. For specific API or data provider verification:
   ```bash
   python tests/smoke_test_phase1.py
   python verify_settings.py
   ```

## 4. Writing New Tests
1. Unit tests must use standard prefix `test_*.py` under `tests/`.
2. Mock external HTTP / LLM calls in unit tests to ensure fast execution without API quota consumption.
