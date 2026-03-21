from __future__ import annotations
import logging
from fastapi import HTTPException, Request, status
from app.domain.plan import PlanUpgradeRequired
from app.core.responses import error
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class APIError(HTTPException):
    def __init__(self, http_status: int, code: str, message: str, details: dict | None = None):
        super().__init__(status_code=http_status, detail=message)
        self.code = code
        self.message = message
        self.details = details or {}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


async def api_error_handler(request: Request, exc: APIError):
    log = logger.warning if exc.status_code < 500 else logger.error
    log(
        "APIError %d [%s] on %s %s — %s",
        exc.status_code,
        exc.code,
        request.method,
        request.url.path,
        exc.message,
        extra={
            "request_id": _request_id(request),
            "status": exc.status_code,
            "error_code": exc.code,
            "path": request.url.path,
            "method": request.method,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error(exc.code, exc.message, exc.details),
    )


async def plan_upgrade_handler(request: Request, exc: PlanUpgradeRequired):
    logger.warning(
        "PlanUpgradeRequired on %s %s — required: %s",
        request.method,
        request.url.path,
        exc.required_plan,
        extra={
            "request_id": _request_id(request),
            "path": request.url.path,
            "required_plan": str(exc.required_plan),
        },
    )
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=error(
            "PLAN_UPGRADE_REQUIRED",
            "This feature requires a Pro subscription.",
            {"required_plan": "pro", "upgrade_url": exc.upgrade_url},
        ),
    )


def _cors_headers(request: Request) -> dict:
    """
    Build explicit CORS headers for the response.

    add_exception_handler(Exception, ...) binds to ServerErrorMiddleware which
    sits OUTSIDE Starlette's CORSMiddleware, so CORS headers are never injected
    automatically for unhandled 500 responses. We must set them manually.
    """
    origin = request.headers.get("origin", "*")
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled %s on %s %s",
        type(exc).__name__,
        request.method,
        request.url.path,
        extra={
            "request_id": _request_id(request),
            "exc_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        },
    )
    return JSONResponse(
        status_code=500,
        content=error("INTERNAL_ERROR", "An unexpected error occurred. Please try again later."),
        headers=_cors_headers(request),
    )
