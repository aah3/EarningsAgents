# ─────────────────────────────────────────────────────────────────────────────
# EarningsAgents — Makefile
# Common developer and operations commands.
#
# Usage: make <target>
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: help dev dev-api dev-worker dev-beat dev-web \
        build up down logs restart \
        migrate test smoke \
        score-now clean

# Default target: show help
help:
	@echo ""
	@echo "  EarningsAgents — available targets"
	@echo "  ─────────────────────────────────────────────────"
	@echo "  Local dev"
	@echo "    dev-api      Start FastAPI dev server"
	@echo "    dev-worker   Start Celery worker (local)"
	@echo "    dev-beat     Start Celery Beat scheduler (local)"
	@echo "    dev-web      Start Next.js dev server"
	@echo ""
	@echo "  Docker"
	@echo "    build        Build all Docker images"
	@echo "    up           Start all services in background"
	@echo "    down         Stop and remove containers"
	@echo "    logs         Tail logs from api + worker + beat"
	@echo "    restart      Rebuild and restart all services"
	@echo ""
	@echo "  Database"
	@echo "    migrate      Run Alembic migrations (head)"
	@echo ""
	@echo "  Testing"
	@echo "    test         Run pytest suite"
	@echo "    smoke        Run all phase smoke tests"
	@echo ""
	@echo "  Ops"
	@echo "    score-now    Manually trigger the scoring task on the running worker"
	@echo "    clean        Remove Python caches and build output"
	@echo ""

# ─── Local Dev ────────────────────────────────────────────────────────────────

dev-api:
	.venv/Scripts/uvicorn main_api:app --reload --host 0.0.0.0 --port 8000

dev-worker:
	.venv/Scripts/celery -A api.celery_app worker --loglevel=info --concurrency=2 --pool=solo

dev-beat:
	.venv/Scripts/celery -A api.celery_app beat --loglevel=info

dev-web:
	cd web && npm run dev

# ─── Docker ───────────────────────────────────────────────────────────────────

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f api worker beat

restart:
	docker compose down
	docker compose up --build -d

# ─── Database ─────────────────────────────────────────────────────────────────

migrate:
	.venv/Scripts/python -m alembic upgrade head

# ─── Testing ─────────────────────────────────────────────────────────────────

test:
	.venv/Scripts/pytest tests/ -v

smoke:
	@echo "── Phase 1 ────────────────────────────────────────────────"
	.venv/Scripts/python smoke_test_phase1.py
	@echo "── Phase 2 ────────────────────────────────────────────────"
	.venv/Scripts/python smoke_test_phase2.py
	@echo "── Combined ───────────────────────────────────────────────"
	.venv/Scripts/python smoke_test_combined.py
	@echo "── Phase 4 ────────────────────────────────────────────────"
	.venv/Scripts/python smoke_test_phase4.py

# ─── Ops ─────────────────────────────────────────────────────────────────────

# Manually kick off the daily scoring job against the running worker container.
score-now:
	docker compose exec worker celery -A api.celery_app call api.tasks.score_predictions_task

# Remove Python caches, test artefacts, local DB.
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -f celerybeat-schedule celerybeat.pid
	rm -f earnings_agents.db
