from fastapi import APIRouter, HTTPException
from app.schemas.models import AutofillRequest, AutofillResponse
from app.services.ai_agent import parse_nl_description
from app.services.cache import get_autofill_cache, set_autofill_cache
from app.services.confidence import score_hs_confidence
import logging


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/autofill", response_model=AutofillResponse)
async def autofill(request: AutofillRequest):
    cached = get_autofill_cache(request.description)
    if cached:
        try:
            return AutofillResponse(**cached, cached=True)
        except TypeError:
            pass
    try:
        result = parse_nl_description(request.description)
    except Exception as e:
        logger.error(f"openai autofill failed: {e}")
        raise HTTPException(status_code=502, detail="AI service unavailable. Please fill fields manually.")
    if result.get("hs_code") and result.get("hs_confidence") is not None:
        result["hs_confidence"] = score_hs_confidence(result["hs_code"], result["hs_confidence"])
    set_autofill_cache(request.description, result)
    return AutofillResponse(**result)

