from __future__ import annotations
from fastapi import APIRouter, Query
from app.core.responses import ok


router = APIRouter()


@router.get("/hs-codes/search")
async def hs_search(q: str = Query(""), jurisdiction: str = Query("UK"), limit: int = Query(10)):
    return ok({"results": [{"code": "8471300000", "description": "Portable automatic data processing machines", "level": 10, "supplementary_unit": "p/st"}], "total": 1})


@router.get("/hs-codes/{code}")
async def hs_detail(code: str, jurisdiction: str = Query("UK")):
    return ok({"code": code, "description": "...", "measures": [{"measure_type": "AD_VALOREM", "rate_ad_valorem": 0.0, "country_of_origin": None, "valid_from": "2024-01-01", "valid_to": None}], "supplementary_unit": "p/st"})
