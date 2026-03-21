from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.ratelimit import rate_limiter
from app.config import settings

logger = logging.getLogger("veritariff.request")

# Paths to skip verbose logging (health checks etc.)
_SILENT_PATHS = {"/api/v1/health", "/health", "/favicon.ico"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log every HTTP request with:
      - A unique request_id (injected into response headers too)
      - Method, path, query string
      - User-id extracted from the Authorization header (no secret exposed)
      - Response status code and wall-clock duration in ms
      - On 4xx/5xx: log at WARNING/ERROR with extra context
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        # Attach request_id to the request state so handlers can reference it
        request.state.request_id = request_id

        # Best-effort user extraction from JWT sub-claim (no decoding needed,
        # just grab the payload segment — it's not security-critical here)
        user_id = _extract_user_hint(request)

        silent = request.url.path in _SILENT_PATHS

        if not silent:
            logger.info(
                "→ %s %s",
                request.method,
                request.url.path,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "query": str(request.url.query) or None,
                    "user_id": user_id,
                    "client": request.client.host if request.client else None,
                },
            )

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.error(
                "✗ %s %s — unhandled exception after %.1f ms: %s",
                request.method,
                request.url.path,
                duration_ms,
                exc,
                exc_info=exc,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "user_id": user_id,
                    "duration_ms": duration_ms,
                    "exc_type": type(exc).__name__,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        status = response.status_code

        response.headers["X-Request-Id"] = request_id

        if not silent:
            if status >= 500:
                log = logger.error
                symbol = "✗"
            elif status >= 400:
                log = logger.warning
                symbol = "!"
            else:
                log = logger.info
                symbol = "←"

            log(
                "%s %s %s  %d  %.1f ms",
                symbol,
                request.method,
                request.url.path,
                status,
                duration_ms,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": status,
                    "duration_ms": duration_ms,
                    "user_id": user_id,
                },
            )

        return response


def _extract_user_hint(request: Request) -> str | None:
    """
    Extract a non-sensitive user identifier from the Authorization header.
    Decodes the JWT payload segment (base64) to read the 'sub' claim only —
    no signature verification is performed here (it's already done in deps.py).
    Returns None if not present or not parseable.
    """
    try:
        auth = request.headers.get("Authorization", "")
        if not auth.lower().startswith("bearer "):
            return None
        token = auth.split(" ", 1)[1]
        parts = token.split(".")
        if len(parts) != 3:
            return None
        import base64, json as _json
        payload_b64 = parts[1] + "=="  # pad
        payload = _json.loads(base64.urlsafe_b64decode(payload_b64))
        return str(payload.get("sub") or payload.get("user_id") or "")[:36] or None
    except Exception:
        return None


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
