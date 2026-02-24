from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.responses import ok


router = APIRouter()


class GoogleAuthRequest(BaseModel):
    id_token: str


@router.post("/google")
async def auth_google(payload: GoogleAuthRequest):
    return ok({"access_token": "jwt_string", "token_type": "bearer", "expires_in": 3600, "user": {"id": "uuid", "email": "user@example.com", "display_name": "Jane Smith", "plan": "free"}})


@router.post("/refresh")
async def refresh():
    return ok({"access_token": "jwt_string", "token_type": "bearer", "expires_in": 3600})


@router.delete("/session")
async def logout():
    return ok({"success": True})
