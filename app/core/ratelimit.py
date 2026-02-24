import time
import hashlib
from typing import Optional
from app.config import settings

try:
    import redis  # type: ignore
except Exception:
    redis = None


class RateLimiter:
    def __init__(self) -> None:
        self._local_store: dict[str, list[float]] = {}
        self._redis: Optional["redis.Redis"] = None
        if redis:
            try:
                self._redis = redis.Redis.from_url(settings.redis_url)
            except Exception:
                self._redis = None

    def _key(self, user_id: str, endpoint_group: str, window_start: int) -> str:
        base = f"ratelimit:{user_id}:{window_start}:{endpoint_group}"
        return hashlib.sha256(base.encode()).hexdigest()

    def allow(self, user_id: str, endpoint_group: str, limit: int) -> bool:
        if not settings.rate_limit_enabled:
            return True
        now = int(time.time())
        window_start = now - 3600
        if self._redis:
            key = self._key(user_id, endpoint_group, window_start)
            pipe = self._redis.pipeline()
            pipe.incr(key, amount=1)
            pipe.expire(key, time=3700)
            count, _ = pipe.execute()
            return int(count) <= limit
        key = f"{user_id}:{endpoint_group}"
        bucket = self._local_store.setdefault(key, [])
        bucket.append(now)
        self._local_store[key] = [ts for ts in bucket if ts >= window_start]
        return len(self._local_store[key]) <= limit


rate_limiter = RateLimiter()

