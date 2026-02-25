from __future__ import annotations
from typing import Any, Optional
from app.config import settings
import hashlib
import json

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore


TTL_24H = 60 * 60 * 24
TTL_HS_LOOKUP = 60 * 60 * 24 * 7
TTL_AUTOFILL = 60 * 60 * 24


def get_client():
    if not redis:
        return None
    try:
        return redis.Redis.from_url(settings.redis_url, decode_responses=True)  # type: ignore
    except Exception:
        return None


def get(key: str) -> Optional[str]:
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


def _make_key(prefix: str, *parts: str) -> str:
    raw = ":".join(str(p).lower().strip() for p in parts)
    hashed = hashlib.md5(raw.encode()).hexdigest()[:16]
    return f"{prefix}:{hashed}"


def get_hs_cache(product_description: str, origin_country: Optional[str]) -> Optional[dict]:
    client = get_client()
    if not client:
        return None
    try:
        key = _make_key("hs", product_description, origin_country or "")
        v = client.get(key)
        return json.loads(v) if v else None
    except Exception:
        return None


def set_hs_cache(product_description: str, origin_country: Optional[str], data: dict) -> bool:
    client = get_client()
    if not client:
        return False
    try:
        key = _make_key("hs", product_description, origin_country or "")
        client.setex(key, TTL_HS_LOOKUP, json.dumps(data))
        return True
    except Exception:
        return False


def get_autofill_cache(description: str) -> Optional[dict]:
    client = get_client()
    if not client:
        return None
    try:
        key = _make_key("autofill", description)
        v = client.get(key)
        return json.loads(v) if v else None
    except Exception:
        return None


def set_autofill_cache(description: str, data: dict) -> bool:
    client = get_client()
    if not client:
        return False
    try:
        key = _make_key("autofill", description)
        client.setex(key, TTL_AUTOFILL, json.dumps(data))
        return True
    except Exception:
        return False
