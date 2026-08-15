---
name: docker-and-deployment-ops
description: Workflow for managing Docker Compose multi-service architecture, container builds, Railway production deployments, and service logs.
---

# Docker Containers & Deployment Ops Workflow

Follow this procedure when managing containerized services, updating production deployment specs, or debugging container logs.

## 1. Multi-Service Container Architecture (`docker-compose.yml`)
The local container environment spins up 5 services:
- `db` (Postgres 15)
- `api` (`Dockerfile.api` running FastAPI main_api)
- `worker` (`Dockerfile.worker` running Celery worker)
- `beat` (`Dockerfile.beat` running Celery beat scheduler)
- `web` (`web/Dockerfile` running Next.js)

## 2. Docker Operations & Commands
1. Build and start all services in background:
   ```bash
   make build && make up
   # or: docker compose up --build -d
   ```
2. Inspect container logs:
   ```bash
   make logs
   # or: docker compose logs -f api worker beat
   ```
3. Stop containers (preserving DB volumes):
   ```bash
   make down
   ```

## 3. Railway Cloud Deployments
- Railway split deployment configs live in:
  - [`railway.api.json`](file:///c:/Users/alfredo/Project/EarningsAgents/railway.api.json)
  - [`railway.worker.json`](file:///c:/Users/alfredo/Project/EarningsAgents/railway.worker.json)
  - [`railway.beat.json`](file:///c:/Users/alfredo/Project/EarningsAgents/railway.beat.json)
- Ensure any changes to start commands or environment dependencies are reflected across all three deployment JSON configs.
