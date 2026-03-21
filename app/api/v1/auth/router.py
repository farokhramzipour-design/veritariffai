from __future__ import annotations

import time
import logging
from typing import Optional

import jwt as pyjwt
import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.jwt import create_jwt
from app.core.responses import ok
from app.infrastructure.database.models import User
from app.infrastructure.database.session import get_session

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_token(db_user: User, extra: dict | None = None) -> str:
    """Issue a signed JWT that includes the DB UUID as `user_id`."""
    now = int(time.time())
    payload = {
        "sub": str(db_user.google_sub),   # keep sub for compatibility
        "user_id": str(db_user.id),        # ← DB UUID used everywhere internally
        "email": db_user.email,
        "name": db_user.display_name or db_user.email,
        "plan": db_user.plan.upper(),
        "iat": now,
        "exp": now + 3600 * 24,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    if extra:
        payload.update(extra)
    return create_jwt(payload)


async def _upsert_user(
    db: AsyncSession,
    *,
    google_sub: str,
    email: str,
    display_name: str | None = None,
    avatar_url: str | None = None,
) -> User:
    """Get or create a user row, returning the ORM object."""
    result = await db.execute(
        select(User).where(User.google_sub == google_sub)
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Try by email (handles accounts that previously signed in differently)
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user is None:
        user = User(
            google_sub=google_sub,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            plan="free",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("Created new user id=%s email=%s", user.id, user.email)
    else:
        # Keep profile fields fresh
        changed = False
        if display_name and user.display_name != display_name:
            user.display_name = display_name
            changed = True
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
            changed = True
        if user.google_sub != google_sub:
            user.google_sub = google_sub
            changed = True
        if changed:
            await db.commit()
            await db.refresh(user)

    return user


# ---------------------------------------------------------------------------
# Google OAuth – redirect flow
# ---------------------------------------------------------------------------

@router.get("/google/login")
async def login_google():
    if not settings.google_client_id or not settings.google_redirect_uri:
        raise HTTPException(status_code=500, detail="Google Auth not configured")
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.google_client_id}"
        f"&redirect_uri={settings.google_redirect_uri}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
        "&access_type=offline"
        "&prompt=consent"
    )
    return RedirectResponse(url=url)


@router.get("/google/callback")
async def callback_google(
    code: str,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
):
    if error:
        raise HTTPException(status_code=400, detail=f"Google Auth Error: {error}")
    if not settings.google_client_id or not settings.google_client_secret or not settings.google_redirect_uri:
        raise HTTPException(status_code=500, detail="Google Auth not configured")

    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.google_redirect_uri,
        },
    )
    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to retrieve token from Google")

    id_token_str = token_resp.json().get("id_token")
    try:
        id_info = id_token.verify_oauth2_token(
            id_token_str, google_requests.Request(), settings.google_client_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Google token: {exc}")

    user = await _upsert_user(
        db,
        google_sub=id_info["sub"],
        email=id_info.get("email", ""),
        display_name=id_info.get("name"),
        avatar_url=id_info.get("picture"),
    )
    token = _build_token(user)
    return RedirectResponse(url=f"https://veritariffai.co?token={token}")


# ---------------------------------------------------------------------------
# Google OAuth – token flow (frontend sends Google ID token directly)
# ---------------------------------------------------------------------------

class GoogleAuthRequest(BaseModel):
    id_token: str
    role: Optional[str] = None


@router.post("/google")
async def auth_google(
    payload: GoogleAuthRequest,
    db: AsyncSession = Depends(get_session),
):
    try:
        id_info = id_token.verify_oauth2_token(
            payload.id_token, google_requests.Request(), settings.google_client_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {exc}")
    except Exception as exc:
        logger.exception("Google token verification failed")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {exc}")

    user = await _upsert_user(
        db,
        google_sub=id_info["sub"],
        email=id_info.get("email", ""),
        display_name=id_info.get("name"),
        avatar_url=id_info.get("picture"),
    )
    token = _build_token(user, extra={"role": payload.role or "researcher"})

    return ok({
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 3600 * 24,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "picture": user.avatar_url,
            "plan": user.plan,
        },
    })


# ---------------------------------------------------------------------------
# Microsoft OAuth
# ---------------------------------------------------------------------------

class MicrosoftAuthRequest(BaseModel):
    id_token: str
    role: Optional[str] = None


@router.post("/microsoft")
async def auth_microsoft(
    payload: MicrosoftAuthRequest,
    db: AsyncSession = Depends(get_session),
):
    try:
        decoded = pyjwt.decode(
            payload.id_token,
            options={"verify_signature": False, "verify_aud": False},
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Microsoft token: {exc}")

    ms_sub = str(decoded.get("sub") or decoded.get("oid") or decoded.get("tid") or "")
    email = decoded.get("email") or decoded.get("upn") or f"{ms_sub}@microsoft.com"
    name = decoded.get("name") or decoded.get("preferred_username") or email

    user = await _upsert_user(
        db,
        google_sub=f"ms:{ms_sub}",   # namespace to avoid collision with Google subs
        email=email,
        display_name=name,
    )
    token = _build_token(user, extra={"role": payload.role or "researcher"})

    return ok({
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 3600 * 24,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "plan": user.plan,
            "role": payload.role or "researcher",
        },
    })


# ---------------------------------------------------------------------------
# Academic / mock login (dev & demo)
# ---------------------------------------------------------------------------

class AcademicMockRequest(BaseModel):
    email: str
    name: Optional[str] = None
    role: Optional[str] = None


@router.post("/academic/mock")
async def auth_academic_mock(
    payload: AcademicMockRequest,
    db: AsyncSession = Depends(get_session),
):
    if not settings.academic_mock_enabled:
        raise HTTPException(status_code=403, detail="Academic auth disabled")

    user = await _upsert_user(
        db,
        google_sub=f"ac:{payload.email}",
        email=payload.email,
        display_name=payload.name or payload.email,
    )
    token = _build_token(user, extra={"role": payload.role or "researcher"})

    return ok({
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 3600 * 24,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "plan": user.plan,
            "role": payload.role or "researcher",
        },
    })


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

@router.post("/refresh")
async def refresh():
    return ok({"access_token": "jwt_string", "token_type": "bearer", "expires_in": 3600})


@router.delete("/session")
async def logout():
    return ok({"success": True})
