from __future__ import annotations

import asyncio
import os
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import HSCode, IngestionRun, TariffMeasure
from app.infrastructure.database.session import AsyncSessionMaker


_CONSULT_URL = "https://ec.europa.eu/taxation_customs/dds2/taric/taric_consultation.jsp"


def _digits(hs_code: str) -> str:
    return "".join(ch for ch in hs_code if ch.isdigit())


def _parse_pct_from_html(html: str) -> Decimal | None:
    patterns = [
        r"Third\s+country\s+duty[^%]{0,200}([\d.]+)\s*%",
        r"Erga\s+omnes[^%]{0,200}([\d.]+)\s*%",
        r"MFN[^%]{0,200}([\d.]+)\s*%",
    ]
    for pat in patterns:
        m = re.search(pat, html, flags=re.IGNORECASE)
        if m:
            try:
                return Decimal(m.group(1))
            except Exception:
                pass
    m = re.search(r"([\d.]+)\s*%", html)
    if not m:
        return None
    try:
        return Decimal(m.group(1))
    except Exception:
        return None


def _parse_description_from_html(html: str, hs_code: str) -> str:
    m = re.search(r"Description\s*</[^>]+>\s*<[^>]+>\s*([^<]{3,200})\s*<", html, flags=re.IGNORECASE)
    if m:
        desc = m.group(1).strip()
        if desc:
            return desc
    m = re.search(rf"{re.escape(hs_code)}[^<]{{0,80}}</[^>]+>\s*<[^>]+>\s*([^<]{{3,200}})<", html, flags=re.IGNORECASE)
    if m:
        desc = m.group(1).strip()
        if desc:
            return desc
    return f"HS {hs_code}"


async def _get_html_with_retries(client: httpx.AsyncClient, hs_code: str) -> tuple[str, str]:
    backoff_s = 0.5
    last_exc: Exception | None = None
    params = {"Lang": "en", "LangDescr": "EN", "Taric": hs_code}
    for _ in range(3):
        try:
            resp = await client.get(_CONSULT_URL, params=params, headers={"Accept": "text/html"})
            resp.raise_for_status()
            return resp.text, str(resp.url)
        except Exception as exc:
            last_exc = exc
            await asyncio.sleep(backoff_s)
            backoff_s *= 2
    raise last_exc or RuntimeError("Request failed")


async def _upsert_hs_code(db: AsyncSession, *, hs_code: str, description: str) -> None:
    stmt = (
        insert(HSCode)
        .values(
            code=hs_code,
            jurisdiction="EU",
            description=description,
            parent_code=None,
            level=len(hs_code),
            supplementary_unit=None,
            valid_from=date.today(),
            valid_to=None,
        )
        .on_conflict_do_update(
            index_elements=[HSCode.code],
            set_={
                "jurisdiction": "EU",
                "description": description,
                "level": len(hs_code),
                "valid_to": None,
            },
        )
    )
    await db.execute(stmt)


async def _upsert_mfn_measure(db: AsyncSession, *, hs_code: str, mfn_rate: Decimal | None, raw: dict[str, Any]) -> None:
    stmt = (
        insert(TariffMeasure)
        .values(
            id=uuid4(),
            hs_code=hs_code,
            jurisdiction="EU",
            measure_type="MFN",
            country_of_origin=None,
            preferential_agreement=None,
            rate_ad_valorem=mfn_rate,
            rate_specific_amount=None,
            rate_specific_unit=None,
            rate_minimum=None,
            rate_maximum=None,
            agricultural_component=None,
            quota_id=None,
            suspension=False,
            measure_condition=None,
            raw_json=raw,
            valid_from=date.today(),
            valid_to=None,
            source_dataset="TARIC",
            source_measure_id=f"EU_MFN:{hs_code}",
            ingested_at=datetime.utcnow(),
        )
        .on_conflict_do_update(
            index_elements=[TariffMeasure.source_dataset, TariffMeasure.source_measure_id],
            index_where=sa.text("source_measure_id IS NOT NULL"),
            set_={
                "rate_ad_valorem": mfn_rate,
                "raw_json": raw,
                "valid_from": date.today(),
                "valid_to": None,
                "ingested_at": datetime.utcnow(),
            },
        )
    )
    await db.execute(stmt)


async def ingest_delta() -> dict[str, Any]:
    hs_codes_env = os.getenv("EU_TARIC_HS_CODES", "")
    hs_codes = [_digits(c.strip()) for c in hs_codes_env.split(",") if _digits(c.strip())]

    started = datetime.utcnow()
    async with AsyncSessionMaker() as db:
        run = IngestionRun(source="TARIC", status="running", started_at=started)
        db.add(run)
        await db.commit()
        await db.refresh(run)

        processed = 0
        try:
            async with httpx.AsyncClient(timeout=25) as client:
                for hs in hs_codes:
                    html, url = await _get_html_with_retries(client, hs)
                    desc = _parse_description_from_html(html, hs)
                    mfn = _parse_pct_from_html(html)
                    await _upsert_hs_code(db, hs_code=hs, description=desc)
                    await _upsert_mfn_measure(db, hs_code=hs, mfn_rate=mfn, raw={"url": url, "mfn": str(mfn) if mfn is not None else None})
                    processed += 1
                    await db.commit()
                    await asyncio.sleep(0.2)

            run.status = "success"
            run.records_processed = processed
            run.completed_at = datetime.utcnow()
            await db.commit()
            return {"source": "TARIC", "status": run.status, "hs_codes_processed": processed}
        except Exception as exc:
            await db.rollback()
            run.status = "failed"
            run.error_details = str(exc)
            run.completed_at = datetime.utcnow()
            await db.commit()
            return {"source": "TARIC", "status": run.status, "error": str(exc)}


async def ingest_full() -> dict[str, Any]:
    return await ingest_delta()


def ingest_delta_sync() -> dict[str, Any]:
    return asyncio.run(ingest_delta())


def ingest_full_sync() -> dict[str, Any]:
    return asyncio.run(ingest_full())
