from __future__ import annotations
from typing import Optional, Tuple
import httpx


async def fetch_duty_rate(hs_code: str, origin_country: str) -> Optional[Tuple[float, str]]:
    url = f"https://taric.ec.europa.eu/api/commodities/{hs_code}"
    params = {"country": origin_country.upper()}
    headers = {"Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params, headers=headers)
            if r.status_code != 200:
                return None
            data = r.json()
            rate = None
            duty_type = None
            if isinstance(data, dict):
                if "duty" in data and isinstance(data["duty"], dict):
                    v = data["duty"].get("ad_valorem")
                    if isinstance(v, (int, float)):
                        rate = float(v)
                        duty_type = "AD_VALOREM"
            if rate is None:
                return None
            return rate, duty_type or "UNKNOWN"
    except Exception:
        return None

