# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A multi-agent LLM platform that predicts corporate earnings surprises (BEAT/MISS/MEET). A FastAPI backend + Celery workers run a **Bull / Bear / Quant / Consensus** agent debate over ingested market data (Yahoo Finance, SEC EDGAR, NewsAPI, Alpha Vantage, options chains), and a Next.js frontend (`web/`) presents predictions, history, and chat. Predictions are scored daily against actual reported earnings (Brier score).

## Commands

### Python backend (run from repo root; venv at `.venv/Scripts/`)
```bash
pip install -r requirements.txt          # exact-pinned deps; regenerate via pip freeze after intentional upgrades
python -m alembic upgrade head            # apply DB migrations
python verify_settings.py                 # sanity-check config/dataclasses without hitting live endpoints

make dev-api                              # uvicorn main_api:app --reload (port 8000)
make dev-worker                           # celery worker, --pool=solo (Windows-safe)
make dev-beat                             # celery beat scheduler
```

### Frontend (`web/`)
```bash
cd web && npm install
npm run dev      # Next.js dev server (port 3000)
npm run build
npm run lint
```

### Tests
```bash
make test                                 # pytest tests/ -v
python -m pytest tests/test_agents.py -v  # single file
python -m pytest tests/test_agents.py -v -k test_name   # single test
make smoke                                # runs tests/smoke_test_phase1.py, phase2, combined, phase4 (hit live/near-live paths)
```
`pytest.ini` sets `testpaths = tests test_earnings_enrichment.py`. Most files under `tests/` prefixed `run_*` or `smoke_test_*` are manual/integration scripts (some call live APIs or LLMs), not part of the default pytest collection filter (`test_*.py`) unless named accordingly — check a file's name before assuming `make test` covers it.

### Docker / ops
```bash
make build && make up      # or: docker compose up --build -d
make down                  # stop containers (keeps volumes)
make logs                  # tail api + worker + beat
make score-now             # manually trigger the daily Brier-score scoring task
make clean                 # remove __pycache__, celerybeat files, local sqlite db
```
`docker-compose.yml` runs 5 services: `db` (Postgres 15), `api`, `worker`, `beat`, `web`. `Dockerfile.api` / `Dockerfile.worker` / `Dockerfile.beat` are separate images from one codebase; Railway configs (`railway.*.json`) deploy the same split.

## Architecture

### Config has two layers, don't be confused by it
- **`config/settings.py`** is canonical: `PipelineConfig`, `AgentConfig`, `DataSourceConfig`, `CompanyData`, `EarningsPrediction`, `PredictionDirection`, `load_config()`.
- **`settings.py`** (repo root) is a one-line shim: `from config.settings import *`, kept so scripts invoked as `python agents/huggingface_agents.py` or similar (with root on `sys.path` but not as a package) resolve `import settings` directly.
- Because of this, several modules (e.g. `agents/huggingface_agents.py`) do a **try flat-import, except fall back to package-import** dance (`try: from settings import X / except ImportError: from config.settings import X`, same pattern for `llm_client` / `agents.llm_client`). Preserve this pattern when adding similarly-dual-imported modules — it's what lets the same file run both as `python agents/huggingface_agents.py` (standalone) and as part of the `api`/`pipeline` package imports.
- `load_config()` reads `.env` (via `find_dotenv(usecwd=False)`, walking up from the file location, not CWD) and picks the agent API key based on `LLM_PROVIDER` (`gemini` | `anthropic` | `openai`).

### The prediction pipeline (`pipeline.py` → `EarningsPipeline`)
`initialize()` wires a `DataAggregator` (data/) and a `ThreeAgentSystem` (agents/). `predict_single(ticker, report_date, ...)`:
1. Fetches `CompanyData` from `DataAggregator` (Yahoo primary, optional SEC/NewsAPI/AlphaVantage).
2. Enriches from the DB: pulls `EarningsHistory`/`EarningsCalendarEvent` via `database/earnings_repo.py`; if missing, lazily syncs from `EarningsAPIDataSource` — on a 429 it enqueues `api.tasks.sync_ticker_history_task` as a Celery task instead of blocking.
3. Pulls live/last-close options analytics (implied move via ATM straddle) from `DataAggregator.get_option_analytics`.
4. Fetches news + sentiment.
5. Calls `ThreeAgentSystem.predict(...)`, which runs Bull/Bear/Quant **in parallel** (Pass 1), optionally a **rebuttal round** where Bull/Bear cross-examine each other's thesis (Pass 2, gated by `AgentConfig.enable_rebuttals`), then `ConsensusAgent.synthesize(...)` produces the final call. If `task_id` is set, progress is published to Redis pub/sub (`task_updates:{task_id}`) for the frontend's WebSocket to consume.
6. Auto-exports a report (`output/report_generator.py`) unless `save_report=False`.

Two other execution flags compose independently and can both be on at once:
- `AgentConfig.use_react` — each agent runs a ReAct tool-call loop (`BaseAgent._react_analyze` in `agents/huggingface_agents.py`, tools defined in `agents/agent_tools.py::AgentToolRegistry`) instead of one-shot generation, calling `get_company_summary` first, then 2–4 more tools before a `final_answer`.
- `AgentConfig.enable_rebuttals` — adds the Bull/Bear cross-examination pass described above.

### Multi-provider LLM abstraction (`agents/llm_client.py`)
`LLMClient` wraps Gemini / Anthropic / OpenAI behind one interface (`generate`, `generate_stream`, `chat`). Provider-specific structured-output enforcement lives in `BaseAgent._get_llm_kwargs()` (OpenAI: `response_format` json_schema; Anthropic: forced tool-use; Gemini: `response_schema` with `additionalProperties` stripped, since Gemini's Schema type rejects that JSON-Schema keyword). Has automatic model fallback / retry-with-backoff on quota/transient errors (`FALLBACK_MAP`, `_rate_limiter`). All four agent roles use a strict `AGENT_RESPONSE_SCHEMA`; `clean_json_response()` in `huggingface_agents.py` repairs common LLM JSON mistakes (trailing commas, unescaped quotes/control chars) before parsing.

### Data layer (`data/`)
`DataAggregator` (`data/data_aggregator.py`) is the orchestrator over per-source clients: `yahoo_finance.py` (primary/free — company facts, earnings history, options), `sec_edgar.py` (10-K/10-Q/8-K + XBRL company facts, rate-limited to 10 req/s, opt-in via `--enable-sec` or `SEC_ENABLED=true`), `alpha_vantage.py` / `news_sources.py` (sentiment), `options.py` (ATM-straddle implied move + Greeks), `finviz_source.py`, `earningsapi_source.py`, `provider_chain.py` (fallback ordering), `market_hours.py` (LIVE vs last-close labeling of options data — the Quant agent's prompt explicitly treats these differently).

### Persistence (`database/`)
SQLModel models in `database/models.py`: `User`/`UserSettings` (per-user LLM provider + **Fernet-encrypted** API keys — see `database/crypto.py`; encrypt before `session.add`, decrypt only after read, never store/return plaintext), `Prediction` (the core record: direction, confidence, bull/bear factors as JSON, `rebuttal_summary`, `options_features`, plus outcome-tracking columns `actual_direction`/`accuracy_score`/`scored_at` populated by the scorer), `PredictionChat`, `Feedback`, `CompanyProfile`, `EarningsHistory`, `EarningsCalendarEvent`. `database/db.py` defaults to local SQLite (`sqlite:///./earnings_agents.db`) if `DATABASE_URL` is unset; normalizes `postgres://` → `postgresql://` for Postgres. `database/scoring_service.py` computes the Brier score (`(confidence/100 - correct)^2`) once actuals are known.

### API + async workers (`api/`)
- `main_api.py` — FastAPI app; lifespan hook calls `init_db()` and initializes a Redis-backed `FastAPICache`. Routers: `api/routers/earnings.py` (predict/history/calendar/chat/settings/feedback/batch/metrics — the primary router) and `api/routers/websockets.py` (live task-progress streaming, consumes the `task_updates:{task_id}` Redis channel published by the pipeline).
- `api/dependencies/auth.py` — Clerk JWT verification via `PyJWKClient`. Has a **dev-only bypass**: tokens prefixed `mock_`/`test_` are accepted verbatim, but only when `ENV=dev` — never touch this gating logic without preserving that env check.
- `api/celery_app.py` — Celery app + beat schedule: daily `score_predictions_task` (06:00 UTC, configurable via `CELERY_SCORE_HOUR`/`MINUTE`), daily `sync_earnings_calendar_task`, and a 60s `beat_heartbeat` liveness pulse. `api/tasks.py` holds the actual task bodies (`analyze_ticker_task`, `score_predictions_task`, `sync_ticker_history_task`, etc.).
- `api/rate_limit.py` — `slowapi` limiter; only routes explicitly decorated with `@limiter.limit(...)` are throttled (no global default).
- `api/sentry_init.py` — called at the top of both `main_api.py` and `api/celery_app.py` for error tracking.

### Frontend (`web/`)
Next.js 16 (App Router) + React 19 + Tailwind 4 + Clerk auth + Sentry. `src/app/(auth)` is the Clerk-gated route group, `src/app/dashboard` the main app, `src/lib/api.ts` the backend client. Talks to the FastAPI backend via `NEXT_PUBLIC_API_URL` and the WebSocket router via `NEXT_PUBLIC_WS_URL`.

### CLI (`main.py`)
`python main.py {single|daily|weekly} ...` drives the same `EarningsPipeline` outside the API/Celery path — useful for one-off runs and batch backfills. Loads config via `load_config()`, then applies CLI overrides (`--model` also infers `--provider`, `--enable-sec`, etc.). Root-level `run_*_debate.py` scripts (e.g. `run_jpm_debate.py`, `run_batch_debate.py`) are ad hoc one-off runners for specific tickers/batches, not part of the maintained CLI surface.

## Notes
- CI (`.github/workflows/ci.yml`) runs `pip install -r requirements.txt && python -m pytest -q` for backend, and `npm ci && npm run lint && npm run build` for frontend, on every PR/push to `main`.
- Windows dev: Celery worker must run with `--pool=solo` (see `make dev-worker`); the `Makefile` invokes `.venv/Scripts/...` (Windows venv layout) rather than `.venv/bin/...`.
- `requirements.txt` is exact-pinned from `pip freeze` — regenerate deliberately (`pip install -r requirements.txt --upgrade <pkg>; pip freeze > requirements.txt`), don't hand-edit versions.
