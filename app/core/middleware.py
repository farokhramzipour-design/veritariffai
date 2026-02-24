from __future__ import annotations
from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.ratelimit import rate_limiter
from app.config import settings
from starlette.responses import Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        if not settings.rate_limit_enabled:
            return await call_next(request)
        endpoint_group = request.url.path.split("/")[1] if request.url.path.startswith("/") else "root"
        user_id = request.headers.get("X-User-Id", "anonymous")
        limit = settings.rate_limit_hourly_default
        allowed = rate_limiter.allow(user_id, endpoint_group, limit)
        if not allowed:
            resp = Response(content="Too Many Requests", status_code=429)
            resp.headers["Retry-After"] = "3600"
            return resp
        return await call_next(request)
