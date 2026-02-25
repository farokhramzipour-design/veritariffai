from fastapi import APIRouter, HTTPException
from app.schemas.models import HSLookupRequest, HSLookupResponse
from app.services.ai_agent import classify_hs_code
from app.services.cache import get_hs_cache, set_hs_cache
from app.services.confidence import score_hs_confidence
import logging


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/hs-lookup", response_model=HSLookupResponse)
async def hs_lookup(request: HSLookupRequest):
    cached = get_hs_cache(request.product_description, request.origin_country)
    if cached:
        try:
            return HSLookupResponse(**cached, cached=True, source="cache")
        except TypeError:
            pass
    try:
        result = classify_hs_code(request.product_description, request.origin_country)
    except Exception as e:
        logger.error(f"openai HS lookup failed: {e}")
        raise HTTPException(status_code=502, detail="AI classification unavailable. Please enter HS code manually.")
    result["confidence"] = score_hs_confidence(result["hs_code"], result["confidence"])
    set_hs_cache(request.product_description, request.origin_country, result)
    return HSLookupResponse(**result, cached=False, source="openai")

