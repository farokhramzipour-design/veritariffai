from __future__ import annotations
from typing import Annotated
from fastapi import Depends, Header
from pydantic import BaseModel
from app.domain.plan import PlanTier, requires_plan, PlanUpgradeRequired
from app.core.errors import APIError
from app.core.jwt import verify_jwt
from app.config import settings
try:
    import redis  # type: ignore
except Exception:
    redis = None


class CurrentUser(BaseModel):
    id: str
    email: str
    plan: PlanTier
    plan_expires_at: str | None = None


async def get_current_user(authorization: Annotated[str | None, Header(alias="Authorization")] = None) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise APIError(401, "UNAUTHENTICATED", "Missing or invalid JWT")
    token = authorization.split(" ", 1)[1]
    try:
        claims = verify_jwt(token)
    except Exception:
        raise APIError(401, "UNAUTHENTICATED", "Invalid JWT")
    user_id = str(claims.get("sub") or claims.get("user_id") or "")
    if not user_id:
        raise APIError(401, "UNAUTHENTICATED", "Invalid JWT")
    blocked = False
    if redis:
        try:
            r = redis.Redis.from_url(settings.redis_url)
            blocked = bool(r.get(f"blocklist:{user_id}"))
        except Exception:
            blocked = False
    if blocked:
        raise APIError(401, "UNAUTHENTICATED", "Session invalidated")
    email = str(claims.get("email") or "user@example.com")
    plan_str = str(claims.get("plan") or "FREE").upper()
    plan = PlanTier[plan_str] if plan_str in PlanTier.__members__ else PlanTier.FREE
    return CurrentUser(id=user_id, email=email, plan=plan)


def require_plan(required: PlanTier):
    async def checker(user: Annotated[CurrentUser, Depends(get_current_user)]):
        requires_plan(user.plan, required, None)
        return user
    return checker
