# 🛠️ Developer Guide & Testing

This guide covers local development workflows, command line interface (CLI) execution, test suites, and guidelines for extending EarningsAgents.

---

## 💻 CLI Commands (`main.py`)

You can run predictions directly from the command line without starting the web application or Celery workers.

### 1. Single Ticker Execution
```bash
python main.py single --ticker AAPL --report-date 2026-05-01
```

Inject analyst comments into the debate context:
```bash
python main.py single --ticker AAPL --report-date 2026-05-01 --user-analysis "Services growth expected to offset iPhone softness in China."
```

### 2. Daily Batch Run
Run analysis for all companies reporting on a specific date:
```bash
python main.py daily --date 2026-06-29 --output json --output-dir ./output
```

### 3. Weekly Batch Run
Run analysis for all companies scheduled to report during a specific week:
```bash
python main.py weekly --week 2026-06-29 --output parquet
```

---

## 🧪 Testing & Verification Suite

### 1. Pytest Unit & Integration Tests
Execute the full test suite using `pytest`:

```bash
python -m pytest tests/
```

### 2. Smoke Tests
Run end-to-end smoke verification using the Makefile shortcut:

```bash
make smoke
```

### 3. Settings & Model Verification
Verify Pydantic schemas, settings loaders, and LLM dataclasses without invoking live APIs:

```bash
python verify_settings.py
```

---

## ➕ Extending the Platform

### Adding a New LLM Provider
1. Open [agents/llm_client.py](file:///c:/Users/alfredo/Project/EarningsAgents/agents/llm_client.py).
2. Implement the API request handler inside `LLMClient.complete()`.
3. Add the provider key configuration to [settings.py](file:///c:/Users/alfredo/Project/EarningsAgents/settings.py).
4. Update `UserSettings` model in [database/models.py](file:///c:/Users/alfredo/Project/EarningsAgents/database/models.py).

### Adding Custom Agent Roles
1. Inherit from `BaseAgent` in [agents/huggingface_agents.py](file:///c:/Users/alfredo/Project/EarningsAgents/agents/huggingface_agents.py).
2. Override system prompt and output JSON parsing schema.
3. Register the agent in `EarningsPipeline.run()` in [pipeline.py](file:///c:/Users/alfredo/Project/EarningsAgents/pipeline.py).
