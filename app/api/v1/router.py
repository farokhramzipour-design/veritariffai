from fastapi import APIRouter
from app.api.v1.health.router import router as health_router
from app.api.v1.calculations.router import router as calculations_router
from app.api.v1.auth.router import router as auth_router
from app.api.v1.users.router import router as users_router
from app.api.v1.subscriptions.router import router as subs_router
from app.api.v1.tariff.router import router as tariff_router
from app.api.v1.internal.router import router as internal_router
from app.api.v1.webhooks.router import router as webhooks_router
from app.api.v1.duty_rate.router import router as duty_rate_router
from app.api.v1.autofill.router import router as autofill_router
from app.api.v1.hs_lookup.router import router as hs_lookup_router
from app.api.v1.kyb.router import router as kyb_router


api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(calculations_router, prefix="/calculations", tags=["calculations"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(subs_router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(tariff_router, prefix="/tariff", tags=["tariff"])
api_router.include_router(internal_router, prefix="/internal", tags=["internal"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(duty_rate_router, tags=["duty-rate"])
api_router.include_router(autofill_router, tags=["autofill"])
api_router.include_router(hs_lookup_router, tags=["hs-lookup"])
api_router.include_router(kyb_router, prefix="/kyb", tags=["kyb"])
