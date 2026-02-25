from __future__ import annotations
import re
from typing import Optional, Tuple
import httpx
from app.config import settings


async def fetch_duty_rate(hs_code: str, origin_country: str) -> Optional[Tuple[float, str]]:
    url = f"https://www.trade-tariff.service.gov.uk/api/v2/commodities/{hs_code}"
    params = {"country": origin_country.upper()}
    headers = {"Accept": "application/vnd.hmrc.2.0+json"}
    if settings.hmrc_api_key:
        headers["X-Api-Key"] = settings.hmrc_api_key
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params, headers=headers)
            if r.status_code != 200:
                return None
            text = r.text
            m = re.search(r"(\\d+(?:\\.\\d+)?)\\s*%", text)
            if not m:
                return None
            rate = float(m.group(1))
            return rate, "AD_VALOREM"
    except Exception:
        return None
