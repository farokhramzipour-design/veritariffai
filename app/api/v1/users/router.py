from __future__ import annotations
from fastapi import APIRouter, Depends
from app.core.deps import get_current_user, CurrentUser
from app.core.responses import ok


router = APIRouter()


@router.get("/me")
async def me(user: CurrentUser = Depends(get_current_user)):
    return ok({"id": user.id, "email": user.email, "plan": user.plan, "plan_expires_at": user.plan_expires_at, "created_at": "2025-01-01T00:00:00Z"})
