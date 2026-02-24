import time
import hashlib
from typing import Optional
from app.config import settings

try:
    import redis  # type: ignore
except ImportError:
    redis = None


class RateLimiter:
    def __init__(self) -> None:
        self._local_store: dict[str, list[float]] = {}
        self._redis = None
        if redis:
            try:
                self._redis = redis.Redis.from_url(settings.redis_url)
            except Exception:
                self._redis = None

    def allow(self, user_id: str, endpoint_group: str, limit: int) -> bool:
        if not settings.rate_limit_enabled:
            return True
        
        now = time.time()
        window_start = now - 3600
        
        if self._redis:
            try:
                # Simple sliding window counter using Redis Sorted Sets
                key = f"ratelimit:{user_id}:{endpoint_group}"
                pipe = self._redis.pipeline()
                # Add current timestamp
                pipe.zadd(key, {str(now): now})
                # Remove timestamps older than window
                pipe.zremrangebyscore(key, 0, window_start)
                # Count remaining timestamps
                pipe.zcard(key)
                # Set expiry for the key
                pipe.expire(key, 3600)
                _, _, count, _ = pipe.execute()
                return count <= limit
            except Exception:
                # Fallback to local store if Redis fails
                pass

        key = f"{user_id}:{endpoint_group}"
        bucket = self._local_store.get(key, [])
        # Filter out old timestamps
        bucket = [ts for ts in bucket if ts > window_start]
        bucket.append(now)
        self._local_store[key] = bucket
        return len(bucket) <= limit


rate_limiter = RateLimiter()
