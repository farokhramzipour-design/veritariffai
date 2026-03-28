from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from app.infrastructure.database.models import IngestionRun, VATRate
from app.infrastructure.database.session import AsyncSessionMaker


_RATES_URL = "https://euvatrates.com/rates.json"


async def _get_json_with_retries(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
    backoff_s = 0.5
    last_exc: Exception | None = None
    for _ in range(3):
        try:
            resp = await client.get(url, headers={"Accept": "application/json"})
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict):
                raise ValueError("Unexpected response shape")
            return data
        except Exception as exc:
            last_exc = exc
            await asyncio.sleep(backoff_s)
            backoff_s *= 2
    raise last_exc or RuntimeError("Request failed")


def _as_decimal_rate(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, (int, float, str)):
        try:
            return Decimal(str(value))
        except Exception:
            return None
    return None


def _extract_rate(entry: dict[str, Any], key: str) -> Any:
    if key in entry:
        return entry.get(key)
    alt = f"{key}_rate"
    if alt in entry:
        return entry.get(alt)
    if key == "super_reduced" and "super_reduced_rate" in entry:
        return entry.get("super_reduced_rate")
    return None


async def ingest() -> dict[str, Any]:
    started = datetime.utcnow()
    async with AsyncSessionMaker() as db:
        run = IngestionRun(source="EU_VAT", status="running", started_at=started)
        db.add(run)
        await db.commit()
        await db.refresh(run)

        records_upserted = 0
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                payload = await _get_json_with_retries(client, _RATES_URL)

            rates = payload.get("rates")
            if not isinstance(rates, dict):
                raise ValueError("Missing 'rates' in response")

            for country_code, entry in rates.items():
                if not isinstance(country_code, str) or len(country_code) != 2:
                    continue
                if not isinstance(entry, dict):
                    continue

                for rate_type in ("standard", "reduced", "reduced_alt", "super_reduced", "parking"):
                    vat_rate = _as_decimal_rate(_extract_rate(entry, rate_type))
                    if vat_rate is None:
                        continue

                    stmt = (
                        insert(VATRate)
                        .values(
                            id=uuid4(),
                            country_code=country_code.upper(),
                            jurisdiction="EU",
                            rate_type=rate_type,
                            vat_rate=vat_rate,
                            hs_code_prefix=None,
                            valid_from=None,
                            valid_to=None,
                            source="euvatrates",
                            raw_json={"country": country_code, "rate_type": rate_type, "value": _extract_rate(entry, rate_type)},
                            ingested_at=datetime.utcnow(),
                        )
                        .on_conflict_do_update(
                        index_elements=[
                            VATRate.country_code,
                            VATRate.jurisdiction,
                            VATRate.rate_type,
                            sa.text("COALESCE(hs_code_prefix, '')"),
                            sa.text("COALESCE(valid_from, '0001-01-01'::date)"),
                        ],
                        set_={
                            "vat_rate": vat_rate,
                            "valid_to": None,
                            "source": "euvatrates",
                            "raw_json": {"country": country_code, "rate_type": rate_type, "value": _extract_rate(entry, rate_type)},
                            "ingested_at": datetime.utcnow(),
                        },
                        )
                    )
                    await db.execute(stmt)
                    records_upserted += 1

            run.status = "success"
            run.records_processed = records_upserted
            run.records_inserted = None
            run.records_updated = None
            run.completed_at = datetime.utcnow()
            await db.commit()
            return {"source": "EU_VAT", "status": run.status, "records_upserted": records_upserted}
        except Exception as exc:
            await db.rollback()
            run.status = "failed"
            run.error_details = str(exc)
            run.completed_at = datetime.utcnow()
            await db.commit()
            return {"source": "EU_VAT", "status": run.status, "error": str(exc)}


def ingest_sync() -> dict[str, Any]:
    return asyncio.run(ingest())
