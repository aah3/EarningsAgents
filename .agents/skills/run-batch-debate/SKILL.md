---
name: run-batch-debate
description: Workflow for setting up, configuring, and executing multi-ticker earnings agent debate batch scripts.
---

# Batch Debate Pipeline Workflow

Follow this procedure when creating or running batch earnings agent analysis scripts (e.g., `run_july29_batch_gd_chef.py`):

## 1. Script Preparation
- Set up target tickers and earnings announcement metadata (date, market timing: AMC / BMO).
- Ensure output paths are configured to write consensus debate results and evaluation outputs to `scratch_output/` or `reports/`.

## 2. Environment Verification
- Verify required environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `SUPABASE_URL`, etc.) are configured.
- Ensure execution runs inside the virtual environment (`.venv/Scripts/python` on Windows).

## 3. Execution & Verification
- Execute batch script using background task runner or terminal command.
- Inspect emitted report files in `scratch_output/` to confirm all tickers completed debate loops without unhandled exceptions.
