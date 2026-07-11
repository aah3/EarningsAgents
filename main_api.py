from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import earnings, websockets
from database.db import init_db
import os
import uvicorn
import redis.asyncio as redis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from api.rate_limit import limiter

# Allowed origins: comma-separated list from env, falls back to localhost only.
# Example: CORS_ORIGINS=https://app.yourdomain.com,https://yourdomain.com
_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Database
    try:
        import database.models
        init_db()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Warning: Failed to initialize database: {e}")

    # Initialize Redis Cache
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        r = redis.from_url(redis_url, encoding="utf8", decode_responses=True)
        FastAPICache.init(RedisBackend(r), prefix="fastapi-cache")
    except Exception as e:
        print(f"Warning: Failed to initialize Redis cache: {e}")

    yield


app = FastAPI(
    title="Earnings Agents API",
    description="API for fetching and analyzing earnings data using multiple agents.",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiting (slowapi) - only routes explicitly decorated with
# @limiter.limit(...) are affected; no default/global limit is set here.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(earnings.router)
app.include_router(websockets.router)

# CORS — restrict to configured origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Welcome to the Earnings Agents API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("main_api:app", host="0.0.0.0", port=8000, reload=True)
