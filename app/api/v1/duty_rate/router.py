from __future__ import annotations
from fastapi import APIRouter, Query, HTTPException, Response
from app.core.responses import ok
from app.schemas.models import DutyRateResponse
from app.services import cache as cache_service
from app.services.uk_tariff_client import fetch_duty_rate as fetch_uk
from app.services.eu_taric_client import fetch_duty_rate as fetch_eu
import json


router = APIRouter()


EU_COUNTRIES = {
    "AT",
    "BE",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "GR",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SK",
    "SI",
    "ES",
    "SE",
}


def is_eu(code: str) -> bool:
    return code.upper() in EU_COUNTRIES


@router.get("/duty-rate", response_model=dict)
async def get_duty_rate(
    hs_code: str = Query(...),
    origin_country: str = Query(...),
    destination_country: str = Query(...),
    response: Response = None,
):
    hs = "".join(ch for ch in hs_code if ch.isdigit())
    if not hs or len(hs) < 4:
        raise HTTPException(status_code=422, detail="Invalid hs_code")
    origin = origin_country.upper()
    dest = destination_country.upper()
    cache_key = f"duty:{hs}:{origin}:{dest}"
    cached_blob = cache_service.get(cache_key)
    if cached_blob:
        try:
            data = json.loads(cached_blob)
            return ok(data)
        except Exception:
            pass
    source = ""
    duty_rate = 0.0
    duty_type = "UNKNOWN"
    try:
        if dest in {"GB", "UK"}:
            result = await fetch_uk(hs, origin)
            if result:
                duty_rate, duty_type = result
                source = "UK Tariff"
        elif is_eu(dest):
            result = await fetch_eu(hs, origin)
            if result:
                duty_rate, duty_type = result
                source = "TARIC"
    except Exception:
        pass
    cached = False
    if not source:
        source = "fallback"
        if response:
            response.headers["X-Warning"] = "Fallback duty rate used"
    payload = DutyRateResponse(
        duty_rate=float(duty_rate),
        duty_type=duty_type,
        source=source,
        cached=cached,
    ).model_dump()
    cache_service.setex(cache_key, cache_service.TTL_24H, json.dumps(payload))
    return ok(payload)

