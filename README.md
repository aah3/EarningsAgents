# 📈 EarningsAgents — AI-Powered Multi-Agent Earnings Platform

A production-grade, distributed research platform designed to predict and analyze corporate earnings surprises. The system uses a **multi-agent debate framework** that ingests market data, SEC filings, options flows, and news sentiment, debates the outcomes, and publishes consensus predictions with real-time tracking.

---

## 🏗️ System Architecture

```
                  Company Data (Yahoo / SEC / News / Alpha Vantage)
                                          │
                    ┌──────────────┬──────┴───────┬──────────────┐
                    ▼              ▼              ▼              ▼
              ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌───────────┐
              │   BULL   │   │   BEAR   │   │  QUANT   │   │   USER    │
              │  Agent   │   │  Agent   │   │  Agent   │   │(Optional) │
              │ (BEAT)   │   │ (MISS)   │   │ (DATA)   │   │ (Insight) │
              └────┬─────┘   └────┬─────┘   └────┬─────┘   └─────┬─────┘
                   │              │              │               │
                   └──────────────┴──────┬───────┴───────────────┘
                                         ▼
                                ┌──────────────────┐
                                │    CONSENSUS     │
                                │     Agent        │
                                └────────┬─────────┘
                                         ▼
                                  FINAL PREDICTION
```

### ⚡ Key Capabilities
1. **Multi-Agent Debate:** Bull and Bear agents cross-examine each other with counter-arguments (rebuttal rounds) to reduce LLM confirmation bias.
2. **Quant Agent Integration:** Analyzes historical earnings surprises, short interest, options chain data (implied moves via ATM straddles), and Greeks.
3. **Distributed Task Queue:** Backend prediction workloads and daily scoring metrics run asynchronously via **Celery & Redis**.
4. **Real-time Live Progress:** Prediction tasks communicate live state changes to the Next.js frontend using **WebSockets**.
5. **Automated Accuracy Scorer:** A daily Celery Beat task fetches reported earnings from Yahoo Finance, tracks the accuracy of past forecasts, and calculates **Brier scores**.
6. **Premium Web UI:** Includes a comprehensive Next.js web application equipped with Clerk user authentication, interactive dashboard analysis cards, historical search databases, and chat features.

---

## 📂 Project Structure

```
EarningsAgents/
├── api/                   # FastAPI Web App
│   ├── dependencies/      # Auth (Clerk JWT validation) & DB dependencies
│   ├── routers/           # Endpoints: /predict, /history, /calendar, /chat, etc.
│   ├── celery_app.py      # Celery broker configuration & periodic schedules
│   └── tasks.py           # Celery tasks (analyze_ticker_task, score_predictions_task)
├── agents/                # LLM agent definitions (Bull, Bear, Quant, Consensus)
│   └── huggingface_agents.py
├── data/                  # Unified data ingestion engine
│   ├── alpha_vantage.py   # Alpha Vantage financial reports & news
│   ├── sec_edgar.py       # SEC filings downloader & XML/HTML parsers
│   ├── yahoo_finance.py   # Yahoo Finance stocks, fundamentals, and options
│   ├── options.py         # Option chain & implied move calculations
│   └── data_aggregator.py # Master orchestrator for data fetching & caching
├── database/              # SQLModel Database definitions & engines
│   ├── db.py              # Session lifecycle
│   └── models.py          # User, Prediction, and Chat SQL schemas
├── web/                   # Next.js Frontend Dashboard (port 3000)
├── Dockerfile.api         # FastAPI container
├── Dockerfile.worker      # Celery Worker container
├── Dockerfile.beat        # Celery Beat Scheduler container
├── docker-compose.yml     # Multi-container local orchestration
├── Makefile               # Helper commands for local & container development
├── settings.py            # Master Pydantic/dataclass configuration loader
└── main_api.py            # API server entrypoint (port 8000)
```

---

## 🛠️ Prerequisites & Local Setup

### ⚙️ Prerequisites
- **Python 3.11+**
- **Node.js 20+**
- **Docker & Docker Compose** (Desktop or CLI)

### 💻 Local Development Setup

1. **Clone the Repository & Create Virtual Environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   
   pip install -r requirements.txt
   ```

2. **Setup Frontend:**
   ```bash
   cd web
   npm install
   ```

3. **Initialize Database Migrations:**
   ```bash
   python -m alembic upgrade head
   ```

4. **Running Services Locally (Manual Mode):**
   *   **FastAPI Backend:** `python -m uvicorn main_api:app --host 0.0.0.0 --port 8000 --reload`
   *   **Celery Worker:** `celery -A api.celery_app worker --loglevel=info -P solo`
   *   **Celery Beat:** `celery -A api.celery_app beat --loglevel=info`
   *   **Next.js Frontend:** `cd web && npm run dev`

### 🏁 First-Time Setup Checklist

If you are running the platform for the first time, follow this quick checklist to ensure everything is configured properly:
1. **Configure Environment Variables:** Copy `.env.example` to `.env` and fill in at least one LLM key (e.g. `GEMINI_API_KEY`).
2. **Verify Configuration:** Run the configuration verification script (which checks all models, data dataclasses, and settings without hitting any live endpoints):
   ```bash
   python verify_settings.py
   ```
3. **Initialize the Database:** Apply the database schema migrations locally:
   ```bash
   python -m alembic upgrade head
   ```
4. **Validate with Smoke Tests:** Run the verification suite to ensure all internal endpoints are wired correctly:
   ```bash
   make smoke
   ```

---

## 🖥️ Running Predictions via CLI

You can run predictions, test the multi-agent system, or generate batch earnings analyses directly from the command line using `main.py`. This is ideal for manual evaluation, scripting, and offline batch analysis.

### 1. Single Company Analysis
Run a deep prediction on a specific ticker for a given report date:
```bash
python main.py single --ticker NVDA --report-date 2026-05-22
```
To guide the debate, you can inject qualitative analyst notes or custom insights using the `--user-analysis` flag:
```bash
python main.py single --ticker NVDA --report-date 2026-05-22 --user-analysis "Hyperscale AI demand remains extremely strong; supply constraints for H200/Blackwell chip architectures are easing."
```

### 2. Daily Batch Predictions
Run predictions for all tickers scheduled to report earnings on a specific date:
```bash
python main.py daily --date 2026-06-29
```

### 3. Weekly Batch Predictions
Run predictions for all tickers scheduled to report earnings during the week starting on a given Monday:
```bash
python main.py weekly --week 2026-06-29
```

### ⚙️ CLI Options & Configuration Flags
You can append these global flags to any subcommand to override defaults:
*   `--model <model_name>`: Specify the model (defaults to `gemini-1.5-flash-002`). Supported models include:
    *   **Gemini:** `gemini-1.5-flash-002`, `gemini-1.5-pro-002` (requires `GEMINI_API_KEY`)
    *   **OpenAI:** `gpt-4o-mini`, `gpt-4o` (requires `OPENAI_API_KEY`)
    *   **Anthropic:** `claude-3-5-sonnet` (requires `ANTHROPIC_API_KEY`)
*   `-v`, `--verbose`: Enable debug logging to display raw API payloads and agent thoughts.
*   `--output {parquet,csv,json}`: Set output format for weekly/daily batch runs (default: `parquet`).
*   `--output-dir <directory_path>`: Target folder for saving exported files (default: `./output`).
*   `--enable-sec`: Enable tool-calling to fetch, parse, and ingest official SEC EDGAR 10-K/10-Q documents (slows down execution but enhances report quality).
*   `--newsapi-key <key>` / `--av-key <key>`: Explicitly provide API credentials for NewsAPI or Alpha Vantage overrides.
*   `--local`: Use local LLM instances instead of cloud-hosted API models.

---

## 📊 AI Agent Outputs & Model Evaluation

The multi-agent system generates rich, structured insights during its debate. You can inspect these outputs across different layers of the platform and evaluate the model's accuracy.

### 🔍 Examining Agent Outputs

1. **Terminal Console Output:**
   When running `python main.py single ...`, the consensus result is printed directly to the console. It includes:
   - Consensus direction (`BEAT` / `MISS` / `MEET`)
   - Final confidence score (%)
   - Reasoning summary
   - Breakdown of individual agent votes (e.g. `Bull: BEAT`, `Bear: MISS`, `Quant: BEAT`, `Consensus: BEAT`)
   - Top 3 Bull & Bear factors list

2. **File Exports (`/output`):**
   Daily and weekly batch commands export files to the `./output` folder. The generated JSON, CSV, or Parquet files contain:
   - `debate_summary`: Comprehensive text overview of the consensus resolution.
   - `bull_factors` / `bear_factors`: Complete JSON lists of specific bullish/bearish arguments compiled by the agents.
   - `agent_votes`: Key-value map of individual agent decisions.
   - `options_features`: Options chain analytics (implied move, IV, call/put ratios) parsed by the Quant agent.

3. **Database Records (`Prediction` Table):**
   Predictions run through the backend API or Celery tasks are persisted to the database. They store:
   - `rebuttal_summary`: The detailed transcript of the Bull and Bear agents' cross-examination / rebuttal rounds.
   - `options_features`: Implied move and volatility data.
   - All standard prediction metrics (ticker, direction, confidence, reasoning summary).

### 🎯 Evaluating Model Accuracy (Brier Score)

Evaluating the predictive power of the model is built directly into the framework.

- **Daily Scorer Task:** A Celery Beat task runs daily at **06:00 UTC** to fetch actual reported earnings and market data for past predictions.
- **Accuracy Metric (Brier Score):**
  The accuracy of predictions is evaluated using the **Brier Score** (`accuracy_score` in the database), which is calculated as:
  $$Brier = (Confidence\% / 100 - Correct)^2$$
  where $Correct = 1.0$ if the predicted direction matches the actual surprise direction, and $0.0$ otherwise.
  - *Interpretation:* Brier scores range from `0.0` (perfect forecast with 100% confidence) to `1.0` (entirely incorrect forecast with 100% confidence). Lower scores represent better-calibrated models.
- **Manual Evaluation Trigger:**
  You can force the scoring engine to evaluate pending predictions on the database at any time using:
  ```bash
  make score-now
  ```

---

## 🗄️ Ingested Financial Data Sources

The data aggregation layer parses and combines multiple financial data feeds to provide context to the Bull, Bear, and Quant agents:

1. **Yahoo Finance API (Primary, Free)**
   - Used for core company details (sector, industry, market cap).
   - Ingests historical earnings results (actuals, estimates, surprise percent) and current price momentum (5-day and 21-day changes).
   - Retrieves consensus analyst expectations and recommendations.
   - Parses active options chains to extract Implied Volatility (IV) and Call/Put volume ratios.

2. **SEC EDGAR Filings (Free)**
   - Downloads official company filings (10-K, 10-Q, 8-K) and CIK identifiers.
   - Feeds historical filing sentiment and earnings transcripts (where available) to the LLM context.
   - *Note:* Rate-limited to 10 requests/second per SEC guidelines. Enabled via the `--enable-sec` CLI flag or by setting `SEC_ENABLED=true` in `.env`.

3. **NewsAPI & Alpha Vantage Sentiment (API Keys Required)**
   - **NewsAPI**: Queries recent media headlines and article summaries from 80,000+ sources.
   - **Alpha Vantage**: Provides news articles enriched with pre-calculated sentiment scores (-1.0 to +1.0) and ticker relevance metrics.

4. **Options Chain & Implied Move Analytics**
   - Implied percent price moves are computed from **At-The-Money (ATM) straddle options pricing** using the near-term expiration dates around earnings.
   - Helps the Quant agent evaluate if the market's implied price move is over- or under-priced compared to historical and agent predictions.

---

## 🐳 Docker Deployment Guide (Recommended)

Running the framework in Docker containerizes the database, Redis cache, Next.js frontend, FastAPI backend, and Celery workers/schedulers into a single, cohesive environment.

### 📋 Step 1: Configure Environment Variables

Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```

Open `.env` and fill out the required variables:
*   **LLM API Keys:** Provide at least one key (e.g. `GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`).
*   **Data API Keys:** Provide a `NEWSAPI_API_KEY` and/or `ALPHAVANTAGE_API_KEY` for sentiment signals.
*   **Clerk Auth:** Enter your `CLERK_JWKS_URL` and `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` (from your Clerk dashboard).
*   **URLs:** Set `NEXT_PUBLIC_API_URL=http://localhost:8000` and `NEXT_PUBLIC_WS_URL=ws://localhost:8000` for default local Docker networking.

### 🚀 Step 2: Build & Start Containers

Build all Docker images and start the services in the background using the [Makefile](file:///c:/Users/alfredo/Project/EarningsAgents/Makefile):
```bash
make restart
```
*Or, using raw Docker commands:*
```bash
docker compose down
docker compose up --build -d
```

This commands spins up 5 services:
1.  **`db`**: PostgreSQL 15 database instance (runs health checks to verify readiness).
2.  **`api`**: FastAPI backend (automatically runs Alembic upgrades on boot, then starts Uvicorn on port `8000`).
3.  **`worker`**: Celery worker executing the background analyses.
4.  **`beat`**: Celery Beat scheduler dispatching daily scoring jobs.
5.  **`web`**: Next.js app serving the React UI on port `3000`.

### 📊 Step 3: Verify the Deployment

Ensure all containers are running and healthy:
```bash
docker compose ps
```

You can test the endpoint responses via terminal:
```bash
# Health Check
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

# Root API Check
curl http://localhost:8000/
# Expected: {"message": "Welcome to the Earnings Agents API"}
```

Access the user interfaces:
*   **Frontend Dashboard:** [http://localhost:3000](http://localhost:3000)
*   **Backend OpenAPI / Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

### 📈 Step 4: Scaling Worker Capacities

For high volumes during peak earnings seasons, scale Celery workers to run multiple analysis predictions concurrently:
```bash
docker compose up -d --scale worker=3
```

### 🎯 Step 5: Daily Prediction Scoring & Manual Triggers

Predictions are evaluated daily at **06:00 UTC** via Celery Beat, retrieving actual earnings surprises and calculating Brier accuracy scores. You can force-trigger this scoring routine manually at any time:
```bash
make score-now
```
*Or, using raw Docker:*
```bash
docker compose exec worker celery -A api.celery_app call api.tasks.score_predictions_task
```

### 🛑 Step 6: Shutdown the Stack

To stop and remove all container resources (preserving volumes):
```bash
make down
```
To also destroy database volumes and reset:
```bash
docker compose down -v
```

---

## 🛠️ Developer Command Reference (`Makefile`)

The project includes a [Makefile](file:///c:/Users/alfredo/Project/EarningsAgents/Makefile) loaded with shortcut targets:

| Command | Action |
|---|---|
| `make dev-api` | Launches local FastAPI backend with hot-reload enabled. |
| `make dev-worker` | Starts local Celery worker (configured for Windows single-process debugging). |
| `make dev-beat` | Launches local Celery Beat scheduler. |
| `make dev-web` | Starts Next.js dev server. |
| `make build` | Builds all Docker images. |
| `make up` | Starts all Docker containers in background. |
| `make down` | Halts and removes running Docker containers. |
| `make logs` | Streams live logs from API, Worker, and Beat containers. |
| `make restart` | Rebuilds and restarts the Docker-compose container ecosystem. |
| `make migrate` | Applies latest database schema migrations via Alembic. |
| `make test` | Executes the standard test suite. |
| `make smoke` | Runs all phase smoke validation scripts. |
| `make score-now` | Manually triggers the daily scoring job against the active worker container. |
| `make clean` | Clears all cached python files, local SQLite databases, and task schedules. |

---

## 🗺️ Roadmap & Next Steps

To review upcoming plans and help shape the next stage of features (such as SEC filers parsing, conversational AI copilot panels, and performance charts), read [RoadMap.md](file:///c:/Users/alfredo/Project/EarningsAgents/RoadMap.md).
