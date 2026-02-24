from __future__ import annotations
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from app.core.deps import get_current_user, CurrentUser
from app.core.responses import ok


router = APIRouter()


class CheckoutRequest(BaseModel):
    plan: str
    billing_period: str


@router.post("/checkout")
async def checkout(payload: CheckoutRequest, user: CurrentUser = Depends(get_current_user)):
    return ok({"checkout_url": "https://checkout.stripe.com/test"})


@router.post("/portal")
async def portal(user: CurrentUser = Depends(get_current_user)):
    return ok({"portal_url": "https://billing.stripe.com/test"})


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    return ok({"received": True})
