"""
Rate limiting configuration (slowapi), shared between main_api.py (which
wires the Limiter into the FastAPI app) and api/routers/earnings.py (which
applies per-route limits to /predict, /chat, /batch).

Limits are keyed by authenticated user id when a valid/dev-bypass bearer
token is present, falling back to remote IP for unauthenticated callers so
a single anonymous caller can't exhaust another user's quota (and vice
versa). Limit values are configurable via env vars with sensible defaults.
"""
import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from api.dependencies.auth import resolve_user_id_from_token


def rate_limit_key(request: Request) -> str:
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            user_id = resolve_user_id_from_token(token)
            if user_id:
                return f"user:{user_id}"
        except Exception:
            # Invalid/expired token, or JWKS lookup failure - fall through to
            # IP-based limiting. The actual auth dependency (get_current_user)
            # is still responsible for rejecting the request as unauthorized.
            pass
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=rate_limit_key)

# Configurable via env, with sensible per-hour defaults.
RATE_LIMIT_PREDICT = os.getenv("RATE_LIMIT_PREDICT", "10/hour")
RATE_LIMIT_CHAT = os.getenv("RATE_LIMIT_CHAT", "30/hour")
RATE_LIMIT_BATCH = os.getenv("RATE_LIMIT_BATCH", "3/hour")
