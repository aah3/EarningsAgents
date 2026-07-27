# 🐳 Deployment & Celery Operations

EarningsAgents is built to run as a containerized microservice ecosystem powered by Docker Compose, Redis, Celery, PostgreSQL, and Next.js.

---

## 🏗️ Docker Architecture

```
                                  [ Browser / Client ]
                                           │
                                    Port 3000 (HTTP)
                                           ▼
                                 ┌──────────────────┐
                                 │   web (Next.js)  │
                                 └────────┬─────────┘
                                          │
                                    Port 8000 (HTTP/WS)
                                          ▼
                                 ┌──────────────────┐
                                 │   api (FastAPI)  │
                                 └────────┬─────────┘
                                          │
                   ┌──────────────────────┼──────────────────────┐
                   ▼                      ▼                      ▼
         ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
         │   db (Postgres)  │   │   Redis Cache    │   │  worker (Celery) │
         └──────────────────┘   └────────┬─────────┘   └────────┬─────────┘
                                         │                      │
                                         └──────────┬───────────┘
                                                    ▼
                                           ┌──────────────────┐
                                           │   beat (Celery)  │
                                           └──────────────────┘
```

---

## 🚀 Environment Variables Setup

Copy `.env.example` to `.env` and configure key variables:

```bash
# Model Credentials
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Data Feeds
NEWSAPI_API_KEY=your_newsapi_key
ALPHAVANTAGE_API_KEY=your_alphavantage_key

# Database & Celery Broker
DATABASE_URL=postgresql://postgres:postgres@db:5432/earningsagents
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Authentication (Clerk)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_JWKS_URL=https://.../.well-known/jwks.json
```

---

## ⚙️ Operating Celery Workers & Beat Scheduler

### Celery Tasks (`api/tasks.py`)
1. **`analyze_ticker_task`**: Executes full multi-agent pipeline for a ticker on a specified date. Updates task status and broadcasts progress events over WebSockets.
2. **`score_predictions_task`**: Iterates through past predictions, checks Yahoo Finance for actual reported EPS and post-earnings stock price moves, and calculates Brier scores.

### Celery Beat Schedule
- **Daily Scoring Job:** Triggered automatically every day at **06:00 UTC**.
- **Manual Trigger:** Force execution at any time via:
  ```bash
  make score-now
  ```
  *(Or inside Docker container)*:
  ```bash
  docker compose exec worker celery -A api.celery_app call api.tasks.score_predictions_task
  ```

---

## ⚡ Worker Scaling & High Availability

During heavy earnings seasons (e.g., hundreds of reports per day), scale Celery worker instances:

```bash
docker compose up -d --scale worker=4
```

---

## ☁️ Cloud Deployment Guidelines

- **Railway Deployment:** Configured via `railway.api.json`, `railway.worker.json`, and `railway.beat.json`.
- **Database:** Connect to Supabase or Managed PostgreSQL by supplying `DATABASE_URL`.
- **SSL / CORS:** Configure `ALLOWED_ORIGINS` in `.env` for production domain security.
