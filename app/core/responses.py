from __future__ import annotations
from datetime import datetime, timezone
import uuid
from fastapi import Request


def _meta() -> dict:
    return {"request_id": str(uuid.uuid4()), "timestamp": datetime.now(timezone.utc).isoformat()}


def ok(data: dict | list | str | int | float | bool | None) -> dict:
    return {"data": data, "meta": _meta()}


def error(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}, "meta": _meta()}
