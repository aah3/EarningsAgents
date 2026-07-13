"""
Shared Sentry initialization for the API server and Celery worker/beat
processes, which run as separate OS processes and must each call init().

No-ops safely when SENTRY_DSN is unset (e.g. local dev), since
sentry_sdk.init(dsn=None) disables the SDK rather than raising.
"""
import os

import sentry_sdk


def init_sentry() -> None:
    dsn = os.getenv("SENTRY_DSN")
    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT", "development"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
    )
