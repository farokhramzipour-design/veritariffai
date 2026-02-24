from fastapi import APIRouter, Request, Header
from app.core.responses import ok
from app.config import settings
import hmac
import hashlib


router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(request: Request, stripe_signature: str | None = Header(default=None, alias="Stripe-Signature")):
    raw_body = await request.body()
    if not settings.stripe_webhook_secret or not stripe_signature:
        return ok({"skipped": True})
    parts = dict(p.split("=", 1) for p in stripe_signature.split(",") if "=" in p)
    t = parts.get("t")
    v1 = parts.get("v1")
    if not t or not v1:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid signature header")
    signed_payload = f"{t}.{raw_body.decode()}".encode()
    expected = hmac.new(settings.stripe_webhook_secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, v1):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Signature verification failed")
    return ok({"received": True})

