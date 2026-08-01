"""
Application entrypoint. Wires together config, logging, middleware,
exception handling, and the versioned API router.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.limiter import limiter
from app.core.logging import configure_logging

# Import models package so all tables are registered on Base.metadata / mappers.
import app.models  # noqa: F401

configure_logging()

logger = logging.getLogger(__name__)

# Sentry — no-op if SENTRY_DSN is unset, same "configured/no-op" pattern
# used throughout notification_channels.py. Initialized before the
# exception handlers below are registered so Sentry actually sees
# exceptions that register_exception_handlers would otherwise catch and
# convert into a JSON response before Sentry's own middleware runs.
if settings.SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
else:
    logger.info("[sentry:noop] SENTRY_DSN not set — error monitoring disabled.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
