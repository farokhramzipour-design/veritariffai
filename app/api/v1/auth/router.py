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
    access_token = tokens.get("access_token")
    
    # Get user info
    user_info_response = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    if user_info_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get user info from Google")
        
    user_info = user_info_response.json()
    
    # Here you would typically:
    # 1. Check if user exists in your DB by email
    # 2. If not, create a new user
    # 3. Create a session/JWT for your app
    
    # For now, we'll just return the user info and tokens
    return ok({
        "user": user_info,
        "tokens": tokens
    })

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
