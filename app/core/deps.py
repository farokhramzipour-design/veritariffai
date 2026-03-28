from __future__ import annotations

import logging
import hmac
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError
from app.core.jwt import verify_jwt
from app.config import settings
from app.domain.plan import PlanTier, requires_plan, PlanUpgradeRequired
from app.infrastructure.database.session import get_session

try:
    import redis  # type: ignore
except Exception:
    redis = None

logger = logging.getLogger(__name__)


class CurrentUser(BaseModel):
    id: str          # Always a valid UUID string (the DB primary key)
    email: str
    plan: PlanTier
    plan_expires_at: str | None = None


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except ValueError:
        return False


async def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: AsyncSession = Depends(get_session),
) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise APIError(401, "UNAUTHENTICATED", "Missing or invalid JWT")

    token = authorization.split(" ", 1)[1]
    try:
        claims = verify_jwt(token)
    except Exception:
        raise APIError(401, "UNAUTHENTICATED", "Invalid JWT")

    # New tokens have "user_id" = DB UUID.
    # Legacy tokens only have "sub" = Google numeric ID.
    user_id = str(claims.get("user_id") or "")
    sub = str(claims.get("sub") or "")
    email = str(claims.get("email") or "")

    if not user_id or not _is_uuid(user_id):
        # Old token — resolve the real DB UUID via google_sub or email
        user_id = await _resolve_db_uuid(db, google_sub=sub, email=email)
        if not user_id:
            raise APIError(401, "UNAUTHENTICATED", "User not found. Please log in again.")

    blocked = False
    if redis:
        try:
            r = redis.Redis.from_url(settings.redis_url)
            blocked = bool(r.get(f"blocklist:{user_id}"))
        except Exception:
            blocked = False
    if blocked:
        raise APIError(401, "UNAUTHENTICATED", "Session invalidated")

    plan_str = str(claims.get("plan") or "FREE").upper()
    plan = PlanTier[plan_str] if plan_str in PlanTier.__members__ else PlanTier.FREE

    return CurrentUser(id=user_id, email=email or "user@example.com", plan=plan)


async def _resolve_db_uuid(db: AsyncSession, *, google_sub: str, email: str) -> str | None:
    """
    Look up the real DB user UUID when the JWT only contains a Google/MS sub claim.
    Also auto-creates the user if they authenticated via Google but were never
    persisted (covers the window before the auth router fix was deployed).
    """
    from app.infrastructure.database.models import User

    # 1. Try by google_sub
    if google_sub:
        result = await db.execute(select(User).where(User.google_sub == google_sub))
        user = result.scalar_one_or_none()
        if user:
            return str(user.id)

    # 2. Try by email
    if email:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            # Back-fill google_sub if missing
            if google_sub and not user.google_sub:
                user.google_sub = google_sub
                await db.commit()
            return str(user.id)

    # 3. Auto-create so the user isn't stuck in a broken state
    if google_sub and email:
        from app.infrastructure.database.models import User
        user = User(google_sub=google_sub, email=email, plan="free")
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
            logger.info("Auto-created user id=%s email=%s (legacy token)", user.id, email)
            return str(user.id)
        except Exception:
            await db.rollback()
            logger.exception("Failed to auto-create user google_sub=%s email=%s", google_sub, email)

    return None


def require_plan(required: PlanTier):
    async def checker(user: Annotated[CurrentUser, Depends(get_current_user)]):
        requires_plan(user.plan, required, None)
        return user
    return checker


async def require_admin_key(
    x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key")] = None,
) -> None:
    expected = settings.admin_api_key
    if not expected:
        raise APIError(503, "ADMIN_NOT_CONFIGURED", "Admin API key is not configured")
    if not x_admin_key or not hmac.compare_digest(x_admin_key, expected):
        raise APIError(403, "FORBIDDEN", "Invalid admin key")
