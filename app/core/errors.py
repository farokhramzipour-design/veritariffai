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


async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(status_code=exc.status_code, content=error(exc.code, exc.message, exc.details))


async def plan_upgrade_handler(request: Request, exc: PlanUpgradeRequired):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=error("PLAN_UPGRADE_REQUIRED", "This feature requires a Pro subscription.", {"required_plan": "pro", "upgrade_url": exc.upgrade_url}),
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=error("INTERNAL_ERROR", "An unexpected error occurred. Please try again later."),
    )
