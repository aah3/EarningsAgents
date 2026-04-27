import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

# ─── Broker / Backend ────────────────────────────────────────────────────────

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ─── App ──────────────────────────────────────────────────────────────────────

celery_app = Celery(
    "earnings_agents",
    broker=redis_url,
    backend=redis_url,
    include=["api.tasks"],
)

# ─── Configuration ────────────────────────────────────────────────────────────

# Beat schedule hour/minute are configurable via env so staging vs. prod can
# differ without rebuilding the image.
SCORE_HOUR   = int(os.getenv("CELERY_SCORE_HOUR",   "6"))   # 06:00 UTC default
SCORE_MINUTE = int(os.getenv("CELERY_SCORE_MINUTE", "0"))

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Time
    timezone="UTC",
    enable_utc=True,

    # Result TTL — keep task results for 24 h then purge
    result_expires=86400,

    # Windows / gevent pool compat
    worker_pool_restarts=True,

    # ── Beat schedule ────────────────────────────────────────────────────────
    beat_schedule={
        # Daily accuracy scorer: runs once per day after market open.
        # Waits SCORE_AFTER_DAYS (default 1) calendar day post-report_date
        # before attempting to fetch ground truth from Yahoo Finance.
        "score-predictions-daily": {
            "task": "api.tasks.score_predictions_task",
            "schedule": crontab(hour=SCORE_HOUR, minute=SCORE_MINUTE),
        },

        # Liveness heartbeat: 1-minute pulse so monitoring systems can
        # detect a dead beat scheduler within one interval.
        "beat-heartbeat": {
            "task": "api.tasks.beat_heartbeat",
            "schedule": 60.0,   # every 60 seconds
        },
    },
)

if __name__ == "__main__":
    celery_app.start()
