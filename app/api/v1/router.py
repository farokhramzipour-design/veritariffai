from fastapi import APIRouter, Depends

from app.core.deps import get_current_user

from app.api.v1.health.router import router as health_router
from app.api.v1.auth.router import router as auth_router

from app.api.v1.calculations.router import router as calculations_router
from app.api.v1.users.router import router as users_router
from app.api.v1.subscriptions.router import router as subs_router
from app.api.v1.tariff.router import router as tariff_router
from app.api.v1.internal.router import router as internal_router
from app.api.v1.webhooks.router import router as webhooks_router
from app.api.v1.duty_rate.router import router as duty_rate_router
from app.api.v1.autofill.router import router as autofill_router
from app.api.v1.hs_lookup.router import router as hs_lookup_router
from app.api.v1.kyb.router import router as kyb_router
from app.api.v1.classification.router import router as classification_router
from app.api.v1.origin.router import router as origin_router
from app.api.v1.compliance.router import router as compliance_router
from app.api.v1.invoice.router import router as invoice_router
from app.api.v1.workflow.router import router as workflow_router


# ── Public routes (no token required) ────────────────────────────────────────
_public = APIRouter()
_public.include_router(health_router, prefix="/health", tags=["health"])
_public.include_router(auth_router, prefix="/auth", tags=["auth"])

# ── Protected routes (valid Bearer JWT required on every request) ─────────────
_protected = APIRouter(dependencies=[Depends(get_current_user)])
_protected.include_router(calculations_router, prefix="/calculations", tags=["calculations"])
_protected.include_router(users_router, prefix="/users", tags=["users"])
_protected.include_router(subs_router, prefix="/subscriptions", tags=["subscriptions"])
_protected.include_router(tariff_router, prefix="/tariff", tags=["tariff"])
_protected.include_router(internal_router, prefix="/internal", tags=["internal"])
_protected.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
_protected.include_router(duty_rate_router, tags=["duty-rate"])
_protected.include_router(autofill_router, tags=["autofill"])
_protected.include_router(hs_lookup_router, tags=["hs-lookup"])
_protected.include_router(kyb_router, prefix="/kyb", tags=["kyb"])
_protected.include_router(classification_router, prefix="/classification", tags=["classification"])
_protected.include_router(origin_router, prefix="/origin", tags=["origin"])
_protected.include_router(compliance_router, prefix="/compliance", tags=["compliance"])
_protected.include_router(invoice_router, prefix="/invoice", tags=["invoice"])
_protected.include_router(workflow_router, prefix="/workflow", tags=["workflow"])

# ── Master router ─────────────────────────────────────────────────────────────
api_router = APIRouter()
api_router.include_router(_public)
api_router.include_router(_protected)
