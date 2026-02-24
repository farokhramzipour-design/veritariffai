from __future__ import annotations
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from app.core.responses import ok
from app.config import settings
import requests
from typing import Optional

router = APIRouter()

class GoogleAuthRequest(BaseModel):
    id_token: str

@router.get("/google/login")
async def login_google():
    if not settings.google_client_id or not settings.google_redirect_uri:
        raise HTTPException(status_code=500, detail="Google Auth not configured")
    
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.google_client_id}"
        f"&redirect_uri={settings.google_redirect_uri}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
        "&access_type=offline"
        "&prompt=consent"
    )
    return RedirectResponse(url=google_auth_url)

@router.get("/google/callback")
async def callback_google(code: str, error: Optional[str] = None):
    if error:
        raise HTTPException(status_code=400, detail=f"Google Auth Error: {error}")
    
    if not settings.google_client_id or not settings.google_client_secret or not settings.google_redirect_uri:
        raise HTTPException(status_code=500, detail="Google Auth not configured")

    # Exchange code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.google_redirect_uri,
    }
    
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to retrieve token from Google")
    
    tokens = response.json()
    id_token = tokens.get("id_token")
    # access_token = tokens.get("access_token")
    
    # In a real app, you would:
    # 1. Verify the id_token
    # 2. Check if user exists in DB or create one
    # 3. Generate your own JWT access token
    
    # For now, we will redirect to the frontend with the Google ID token
    # The frontend can then use this token to authenticate or we can assume this IS the token.
    # We are using the id_token as it is the most useful for identity assertion.
    
    redirect_url = f"https://veritariffai.co?token={id_token}"
    return RedirectResponse(url=redirect_url)

@router.post("/google")
async def auth_google(payload: GoogleAuthRequest):
    # This endpoint might be used if the frontend handles the OAuth flow and sends the ID token
    return ok({"access_token": "jwt_string", "token_type": "bearer", "expires_in": 3600, "user": {"id": "uuid", "email": "user@example.com", "display_name": "Jane Smith", "plan": "free"}})


@router.post("/refresh")
async def refresh():
    return ok({"access_token": "jwt_string", "token_type": "bearer", "expires_in": 3600})


@router.delete("/session")
async def logout():
    return ok({"success": True})
