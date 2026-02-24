from __future__ import annotations
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from app.core.responses import ok
from app.config import settings
import requests
from typing import Optional
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.core.jwt import create_jwt
import time

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
    id_token_str = tokens.get("id_token")
    
    # Redirect to frontend with the ID token
    redirect_url = f"https://veritariffai.co?token={id_token_str}"
    return RedirectResponse(url=redirect_url)

@router.post("/google")
async def auth_google(payload: GoogleAuthRequest):
    """
    Verifies the Google ID token sent by the frontend, creates/retrieves the user,
    and returns an application-specific access token (JWT).
    """
    try:
        # Verify the token
        id_info = id_token.verify_oauth2_token(
            payload.id_token, 
            google_requests.Request(), 
            settings.google_client_id
        )

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        google_user_id = id_info['sub']
        email = id_info.get('email')
        name = id_info.get('name')
        picture = id_info.get('picture')

        # TODO: Implement User Logic
        # 1. Check if user exists in DB by email or google_user_id
        # 2. If not, create a new user record
        
        # 3. Generate a JWT for YOUR application (not the Google one)
        # We need to generate a token that our own verify_jwt function can understand (HS256)
        
        now = int(time.time())
        token_payload = {
            "sub": google_user_id, # Or your internal user ID
            "email": email,
            "name": name,
            "plan": "FREE", # Default plan
            "iat": now,
            "exp": now + 3600 * 24, # 24 hours
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience
        }
        
        access_token = create_jwt(token_payload)
        
        return ok({
            "access_token": access_token, 
            "token_type": "bearer", 
            "expires_in": 3600 * 24, 
            "user": {
                "id": google_user_id,
                "email": email, 
                "display_name": name, 
                "picture": picture,
                "plan": "free"
            }
        })

    except ValueError as e:
        # Invalid token
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.post("/refresh")
async def refresh():
    return ok({"access_token": "jwt_string", "token_type": "bearer", "expires_in": 3600})


@router.delete("/session")
async def logout():
    return ok({"success": True})
