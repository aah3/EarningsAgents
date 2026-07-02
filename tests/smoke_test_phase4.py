"""
smoke_test_phase4.py — Phase 4 (containerisation) pre-flight validation.

Checks that all artefacts required to run `docker compose up --build` are
present and structurally correct WITHOUT needing Docker to be running.
Also verifies the Python-side fixes (task names, timedelta import, CORS, etc.)

Checks:
  1.  Dockerfile.api       — exists, references correct CMD
  2.  Dockerfile.worker    — exists, references celery worker command
  3.  Dockerfile.beat      — exists, references celery beat command
  4.  web/Dockerfile       — exists, is a multi-stage build, references standalone
  5.  docker-compose.yml   — exists, each service has build.dockerfile (not top-level)
  6.  .dockerignore        — exists, excludes .venv and .env
  7.  web/.dockerignore    — exists
  8.  .env.example         — exists, contains CORS_ORIGINS key
  9.  next.config.ts       — contains output: "standalone"
  10. requirements.txt     — contains celery, redis, fastapi-cache2
  11. api/celery_app.py    — beat schedule uses "api.tasks." prefix
  12. api/tasks.py         — score task name uses "api.tasks." prefix
  13. api/tasks.py         — no "datetime.timedelta" anti-pattern (fixed with _timedelta)
  14. main_api.py          — CORS uses ALLOWED_ORIGINS (not hardcoded "*")
  15. Python import check  — api.tasks and api.celery_app import without error
"""

import os
import sys
import importlib

ROOT = os.path.dirname(__file__)

pass_count = 0
fail_count = 0

def check(label: str, condition: bool, detail: str = ""):
    global pass_count, fail_count
    if condition:
        print(f"[PASS] {label}")
        pass_count += 1
    else:
        print(f"[FAIL] {label}{' — ' + detail if detail else ''}")
        fail_count += 1

def read(rel_path: str) -> str:
    try:
        with open(os.path.join(ROOT, rel_path), encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

# ─── 1-4. Dockerfile existence & content ─────────────────────────────────────

api_df   = read("Dockerfile.api")
worker_df = read("Dockerfile.worker")
beat_df  = read("Dockerfile.beat")
web_df   = read("web/Dockerfile")

check("Dockerfile.api exists",    bool(api_df))
check("Dockerfile.api CMD runs uvicorn", "uvicorn" in api_df)
check("Dockerfile.api runs alembic upgrade", "alembic upgrade head" in api_df)

check("Dockerfile.worker exists", bool(worker_df))
check("Dockerfile.worker CMD runs celery worker", "worker" in worker_df and "celery" in worker_df)

check("Dockerfile.beat exists",   bool(beat_df))
check("Dockerfile.beat CMD runs celery beat", "beat" in beat_df and "celery" in beat_df)

check("web/Dockerfile exists",    bool(web_df))
check("web/Dockerfile is multi-stage (has AS builder)", "AS builder" in web_df)
check("web/Dockerfile runner copies standalone output", "standalone" in web_df)

# ─── 5. docker-compose.yml structure ─────────────────────────────────────────

compose = read("docker-compose.yml")
check("docker-compose.yml exists", bool(compose))

# Each service must use build.dockerfile (indented under build:), NOT top-level
# Quick structural heuristic: "dockerfile: Dockerfile." must never appear at 4-space indent
bad_toplevel_dockerfile = any(
    line.startswith("    dockerfile:") for line in compose.splitlines()
)
check("docker-compose.yml: dockerfile nested under build (not top-level)",
      not bad_toplevel_dockerfile,
      "Found 'dockerfile:' at service root level — must be under build:")

check("docker-compose.yml: api service present",    "earningsagents-api" in compose)
check("docker-compose.yml: worker service present", "earningsagents-worker" in compose)
check("docker-compose.yml: beat service present",   "earningsagents-beat" in compose)
check("docker-compose.yml: web service present",    "earningsagents-web" in compose)

# ─── 6-7. .dockerignore files ────────────────────────────────────────────────

di      = read(".dockerignore")
web_di  = read("web/.dockerignore")

check(".dockerignore exists",         bool(di))
check(".dockerignore excludes .venv", ".venv" in di)
check(".dockerignore excludes .env",  ".env" in di)
check("web/.dockerignore exists",     bool(web_di))

# ─── 8. .env.example ─────────────────────────────────────────────────────────

env_ex = read(".env.example")
check(".env.example exists",                 bool(env_ex))
check(".env.example documents CORS_ORIGINS", "CORS_ORIGINS" in env_ex)
check(".env.example documents REDIS_URL",    "REDIS_URL" in env_ex)
check(".env.example documents DATABASE_URL", "DATABASE_URL" in env_ex)
check(".env.example documents SCORE_AFTER_DAYS", "SCORE_AFTER_DAYS" in env_ex)

# ─── 9. next.config.ts  ──────────────────────────────────────────────────────

next_cfg = read("web/next.config.ts")
check("web/next.config.ts has output: 'standalone'", "standalone" in next_cfg)

# ─── 10. requirements.txt ────────────────────────────────────────────────────

reqs = read("requirements.txt")
check("requirements.txt includes celery[redis]", "celery" in reqs and "redis" in reqs)
check("requirements.txt includes fastapi-cache2", "fastapi-cache2" in reqs)

# ─── 11-13. celery_app.py / tasks.py correctness ─────────────────────────────

celery_cfg = read("api/celery_app.py")
check("celery_app.py beat schedule uses 'api.tasks.' prefix",
      '"api.tasks.score_predictions_task"' in celery_cfg)
check("celery_app.py heartbeat task registered",
      '"api.tasks.beat_heartbeat"' in celery_cfg)
check("celery_app.py score hour configurable via CELERY_SCORE_HOUR",
      "CELERY_SCORE_HOUR" in celery_cfg)

tasks_src = read("api/tasks.py")
check("api/tasks.py score task name is 'api.tasks.score_predictions_task'",
      '"api.tasks.score_predictions_task"' in tasks_src)
check("api/tasks.py beat_heartbeat task present",
      '"api.tasks.beat_heartbeat"' in tasks_src)
check("api/tasks.py uses _timedelta (not datetime.timedelta)",
      "_timedelta" in tasks_src and "datetime.timedelta" not in tasks_src)
check("api/tasks.py uses SCORE_AFTER_DAYS env var",
      "SCORE_AFTER_DAYS" in tasks_src)

# ─── 14. main_api.py CORS ────────────────────────────────────────────────────

main_api = read("main_api.py")
check("main_api.py CORS not hardcoded to '*'",
      'allow_origins=["*"]' not in main_api,
      "Found: allow_origins=[\"*\"] — must use env-configured list")
check("main_api.py CORS uses ALLOWED_ORIGINS",
      "ALLOWED_ORIGINS" in main_api)
check("main_api.py imports uvicorn",
      "import uvicorn" in main_api)

# ─── 15. Python module import ─────────────────────────────────────────────────

try:
    import api.celery_app  # noqa: F401
    import api.tasks       # noqa: F401
    check("api.celery_app and api.tasks import cleanly", True)
except Exception as exc:
    check("api.celery_app and api.tasks import cleanly", False, str(exc))

# ─── Summary ─────────────────────────────────────────────────────────────────

print()
print(f"Phase 4 smoke test: {pass_count} passed, {fail_count} failed")
if fail_count:
    print("Fix the failures above before running docker compose up --build.")
    sys.exit(1)
else:
    print("All checks PASSED — ready to run: docker compose up --build -d")
