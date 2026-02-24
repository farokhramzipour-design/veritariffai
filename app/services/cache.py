from __future__ import annotations
from typing import Any, Optional
from app.config import settings

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore


TTL_24H = 60 * 60 * 24


def get_client():
    if not redis:
        return None
    try:
        return redis.Redis.from_url(settings.redis_url)  # type: ignore
    except Exception:
        return None


def get(key: str) -> Optional[bytes]:
    client = get_client()
    if not client:
        return None
    try:
        return client.get(key)  # type: ignore
    except Exception:
        return None


def setex(key: str, ttl: int, value: Any) -> bool:
    client = get_client()
    if not client:
        return False
    try:
        client.setex(key, ttl, value)  # type: ignore
        return True
    except Exception:
        return False

