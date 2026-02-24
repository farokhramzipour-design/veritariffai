from __future__ import annotations
from fastapi import APIRouter, Depends
from app.core.deps import get_current_user, CurrentUser
from app.core.responses import ok
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter()

class UserResponse(BaseModel):
    id: str
    email: str
    plan: str
    plan_expires_at: Optional[str] = None
    created_at: str

@router.get("/me", response_model=dict)
async def me(user: CurrentUser = Depends(get_current_user)):
    """
    Get current user profile.
    """
    # In a real application, you might fetch additional details from the database here
    # using user.id
    
    response_data = UserResponse(
        id=user.id,
        email=user.email,
        plan=user.plan.value,
        plan_expires_at=user.plan_expires_at,
        created_at="2025-01-01T00:00:00Z" # Placeholder
    )
    
    return ok(response_data.model_dump())
