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
import jwt as pyjwt

router = APIRouter()

class GoogleAuthRequest(BaseModel):
    id_token: str
    role: Optional[str] = None

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
    
    # Decode the ID token to get user info (without verification for now, as we trust the direct response from Google)
    # In a production environment, you should verify the signature, but since we just got it from Google via HTTPS, it's reasonably safe for extraction.
    # However, to be strictly correct, we should verify it.
    
    try:
        # We use the google library to verify and decode
        id_info = id_token.verify_oauth2_token(
            id_token_str, 
            google_requests.Request(), 
            settings.google_client_id
        )
        
        google_user_id = id_info['sub']
        email = id_info.get('email')
        name = id_info.get('name')
        
        # Generate OUR application JWT
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
        
        app_access_token = create_jwt(token_payload)
        
        # Redirect to frontend with OUR application token
        redirect_url = f"https://veritariffai.co?token={app_access_token}"
        return RedirectResponse(url=redirect_url)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid Google token: {str(e)}")


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
            "role": payload.role or "researcher",
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


class MicrosoftAuthRequest(BaseModel):
    id_token: str
    role: Optional[str] = None


@router.post("/microsoft")
async def auth_microsoft(payload: MicrosoftAuthRequest):
    try:
        decoded = pyjwt.decode(payload.id_token, options={"verify_signature": False, "verify_aud": False})
        sub = str(decoded.get("sub") or decoded.get("oid") or decoded.get("tid") or "microsoft-user")
        email = decoded.get("email") or decoded.get("upn")
        name = decoded.get("name") or decoded.get("preferred_username") or email or sub
        now = int(time.time())
        token_payload = {
            "sub": f"ms:{sub}",
            "email": email or f"{sub}@example.com",
            "name": name,
            "plan": "FREE",
            "role": payload.role or "researcher",
            "iat": now,
            "exp": now + 3600 * 24,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        }
        access_token = create_jwt(token_payload)
        return ok({
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 3600 * 24,
            "user": {
                "id": token_payload["sub"],
                "email": token_payload["email"],
                "display_name": token_payload["name"],
                "plan": "free",
                "role": token_payload["role"],
            },
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


class AcademicMockRequest(BaseModel):
    email: str
    name: Optional[str] = None
    role: Optional[str] = None


@router.post("/academic/mock")
async def auth_academic_mock(payload: AcademicMockRequest):
    if not settings.academic_mock_enabled:
        raise HTTPException(status_code=403, detail="Academic auth disabled")
    now = int(time.time())
    token_payload = {
        "sub": f"ac:{payload.email}",
        "email": payload.email,
        "name": payload.name or payload.email,
        "plan": "FREE",
        "role": payload.role or "researcher",
        "iat": now,
        "exp": now + 3600 * 24,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    access_token = create_jwt(token_payload)
    return ok({
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 3600 * 24,
        "user": {
            "id": token_payload["sub"],
            "email": token_payload["email"],
            "display_name": token_payload["name"],
            "plan": "free",
            "role": token_payload["role"],
        },
    })

@router.post("/refresh")
async def refresh():
    return ok({"access_token": "jwt_string", "token_type": "bearer", "expires_in": 3600})


@router.delete("/session")
async def logout():
    return ok({"success": True})
