"""
Centralized exception handling so every error response has a consistent shape:

    {"error": {"code": "...", "message": "..."}}
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings

logger = logging.getLogger("taxflow")


def _cors_headers_for(request: Request) -> dict:
    """A handler registered for the base `Exception` class is special-cased
    by Starlette to run inside ServerErrorMiddleware — the OUTERMOST layer,
    sitting *outside* app.add_middleware(CORSMiddleware, ...) (see
    app/main.py). That means a response built by unhandled_exception_handler
    below never passes back through CORSMiddleware, so it's missing
    Access-Control-Allow-Origin — and a cross-origin browser then reports
    the failure as a CORS error, masking the real 500 underneath it. This
    is a well-documented FastAPI/Starlette gotcha (see
    https://github.com/fastapi/fastapi/discussions/13398), not something
    specific to this app — the fix is to attach the same headers
    CORSMiddleware would have, by hand, on this one response path only
    (every other exception handler below runs inside ExceptionMiddleware,
    which IS inside CORSMiddleware, so they don't need this).

    Mirrors CORSMiddleware's actual allow_origins check (settings.
    BACKEND_CORS_ORIGINS) rather than reflecting the request's Origin
    unconditionally — an unhandled-exception response is exactly the kind
    of response that shouldn't get looser CORS treatment than every other
    response the app returns.
    """
    origin = request.headers.get("origin")
    if origin and origin in settings.BACKEND_CORS_ORIGINS:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
    return {}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.status_code, "message": exc.detail}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": "validation_error", "message": exc.errors()}},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": "internal_error", "message": "An unexpected error occurred"}},
            headers=_cors_headers_for(request),
        )
