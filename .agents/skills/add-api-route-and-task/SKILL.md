---
name: add-api-route-and-task
description: Workflow for adding FastAPI endpoints, Celery background tasks, Redis WebSocket progress channels, and rate-limited routes.
---

# API Endpoint & Async Task Workflow

Follow this procedure when creating new API endpoints, Celery background workers, or WebSocket progress channels.

## 1. Create FastAPI Endpoint (`api/routers/`)
1. Add new route to existing router in [`api/routers/earnings.py`](file:///c:/Users/alfredo/Project/EarningsAgents/api/routers/earnings.py) or create a new module in `api/routers/`.
2. Apply `slowapi` rate limiter if applicable:
   ```python
   from api.rate_limit import limiter
   @router.post("/...")
   @limiter.limit("10/minute")
   ```
3. **Authentication Invariant**: Preserve dev-only Clerk token bypass check in [`api/dependencies/auth.py`](file:///c:/Users/alfredo/Project/EarningsAgents/api/dependencies/auth.py) (`mock_`/`test_` tokens accepted strictly when `ENV=dev`).

## 2. Define Async Celery Task (`api/tasks.py`)
1. Implement worker logic in [`api/tasks.py`](file:///c:/Users/alfredo/Project/EarningsAgents/api/tasks.py).
2. If task needs to report progress to the frontend, publish JSON updates to Redis pub/sub channel `task_updates:{task_id}` consumed by [`api/routers/websockets.py`](file:///c:/Users/alfredo/Project/EarningsAgents/api/routers/websockets.py).
3. If creating recurring beat tasks, register schedule in [`api/celery_app.py`](file:///c:/Users/alfredo/Project/EarningsAgents/api/celery_app.py).

## 3. Verification & Local Execution
1. **Windows Dev Invariant**: Celery worker MUST run with `--pool=solo`.
   ```bash
   make dev-api      # Runs uvicorn main_api:app --reload (port 8000)
   make dev-worker   # Runs celery worker --pool=solo
   ```
2. Test API endpoints:
   ```bash
   python -m pytest tests/test_api.py -v
   ```
