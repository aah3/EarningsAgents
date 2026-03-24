import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Redis URL from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "earnings_agents",
    broker=redis_url,
    backend=redis_url,
    include=["api.tasks"]
)

# Optional configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Windows compatibility fixes
    worker_pool_restarts=True,
)

if __name__ == "__main__":
    celery_app.start()
