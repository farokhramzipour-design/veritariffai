from __future__ import annotations

import asyncio
import os
import re
from uuid import uuid4
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import httpx
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import HSCode, IngestionRun, TariffMeasure, VATRate
from app.infrastructure.database.session import AsyncSessionMaker


_API_V2 = "https://www.trade-tariff.service.gov.uk/api/v2"
_UK_API = "https://www.trade-tariff.service.gov.uk/uk/api/commodities"

_MT_THIRD_COUNTRY = "103"
_MT_TARIFF_PREF = "142"
_MT_ADDITIONAL = "551"
_MT_SUSPENSION = "115"
_MT_END_USE = "106"
_MT_ANTIDUMPING = "552"
_MT_COUNTERVAILING = "672"


def _digits(hs_code: str) -> str:
    return "".join(ch for ch in hs_code if ch.isdigit())


def _parse_pct(text: str | None) -> Decimal | None:
    if not text:
        return None
    m = re.search(r"([\d.]+)\s*%", text)
    if not m:
        return None
    try:
        return Decimal(m.group(1))
    except Exception:
        return None


async def _get_json_with_retries(client: httpx.AsyncClient, url: str, *, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
    backoff_s = 0.5
    last_exc: Exception | None = None
    for _ in range(3):
        try:
            resp = await client.get(url, headers=headers, params=params)
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


async def _fetch_all_pages(client: httpx.AsyncClient, url: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    next_url: str | None = url
    while next_url:
        payload = await _get_json_with_retries(
            client,
            next_url,
            headers={"Accept": "application/vnd.hmrc.2.0+json"},
        )
        data = payload.get("data")
        if isinstance(data, list):
            out.extend([d for d in data if isinstance(d, dict)])
        links = payload.get("links") if isinstance(payload.get("links"), dict) else {}
        next_url = links.get("next") if isinstance(links.get("next"), str) else None
        await asyncio.sleep(0.05)
    return out


def _build_index(included: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    index: dict[str, dict[str, dict[str, Any]]] = {}
    for obj in included:
        if not isinstance(obj, dict):
            continue
        t = obj.get("type", "")
        i = obj.get("id", "")
        if isinstance(t, str) and isinstance(i, str) and t and i:
            index.setdefault(t, {})[i] = obj
    return index


def _measure_type_from_id(mt_id: str) -> str:
    if mt_id == _MT_TARIFF_PREF:
        return "PREFERENTIAL"
    if mt_id == _MT_THIRD_COUNTRY:
        return "MFN"
    if mt_id == _MT_ANTIDUMPING:
        return "ANTI_DUMPING"
    if mt_id == _MT_COUNTERVAILING:
        return "COUNTERVAILING"
    if mt_id == _MT_ADDITIONAL:
        return "ADDITIONAL"
    if mt_id in (_MT_SUSPENSION, _MT_END_USE):
        return "SUSPENSION"
    return "OTHER"


async def _upsert_hs_code(db: AsyncSession, *, hs_code: str, jurisdiction: str, description: str) -> None:
    stmt = (
        insert(HSCode)
        .values(
            code=hs_code,
            jurisdiction=jurisdiction,
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
                "jurisdiction": jurisdiction,
                "description": description,
                "level": len(hs_code),
                "valid_to": None,
            },
        )
    )
    await db.execute(stmt)


async def _upsert_measure(
    db: AsyncSession,
    *,
    hs_code: str,
    jurisdiction: str,
    source_dataset: str,
    source_measure_id: str,
    measure_type: str,
    country_of_origin: str | None,
    preferential_agreement: str | None,
    rate_ad_valorem: Decimal | None,
    raw_json: dict[str, Any] | None,
    valid_from: date,
    valid_to: date | None,
    suspension: bool,
) -> None:
    stmt = (
        insert(TariffMeasure)
        .values(
            id=uuid4(),
            hs_code=hs_code,
            jurisdiction=jurisdiction,
            measure_type=measure_type,
            country_of_origin=country_of_origin,
            preferential_agreement=preferential_agreement,
            rate_ad_valorem=rate_ad_valorem,
            rate_specific_amount=None,
            rate_specific_unit=None,
            rate_minimum=None,
            rate_maximum=None,
            agricultural_component=None,
            quota_id=None,
            suspension=suspension,
            measure_condition=None,
            raw_json=raw_json,
            valid_from=valid_from,
            valid_to=valid_to,
            source_dataset=source_dataset,
            source_measure_id=source_measure_id,
            ingested_at=datetime.utcnow(),
        )
        .on_conflict_do_update(
            index_elements=[TariffMeasure.source_dataset, TariffMeasure.source_measure_id],
            index_where=sa.text("source_measure_id IS NOT NULL"),
            set_={
                "hs_code": hs_code,
                "jurisdiction": jurisdiction,
                "measure_type": measure_type,
                "country_of_origin": country_of_origin,
                "preferential_agreement": preferential_agreement,
                "rate_ad_valorem": rate_ad_valorem,
                "suspension": suspension,
                "raw_json": raw_json,
                "valid_from": valid_from,
                "valid_to": valid_to,
                "ingested_at": datetime.utcnow(),
            },
        )
    )
    await db.execute(stmt)


async def _upsert_gb_vat(db: AsyncSession, vat_rate: Decimal | None, raw_json: dict[str, Any]) -> None:
    if vat_rate is None:
        return
    stmt = (
        insert(VATRate)
        .values(
            id=uuid4(),
            country_code="GB",
            jurisdiction="GB",
            rate_type="standard",
            vat_rate=vat_rate,
            hs_code_prefix=None,
            valid_from=None,
            valid_to=None,
            source="UK Trade Tariff",
            raw_json=raw_json,
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
                "source": "UK Trade Tariff",
                "raw_json": raw_json,
                "ingested_at": datetime.utcnow(),
            },
        )
    )
    await db.execute(stmt)


async def _ingest_commodity(db: AsyncSession, client: httpx.AsyncClient, hs_code: str) -> dict[str, int]:
    hs = _digits(hs_code)
    payload = await _get_json_with_retries(
        client,
        f"{_UK_API}/{hs}",
        params={"currency": "GBP"},
        headers={"Accept": "application/json"},
    )
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    included = payload.get("included") if isinstance(payload.get("included"), list) else []
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}

    attrs = data.get("attributes") if isinstance(data.get("attributes"), dict) else {}
    description = str(attrs.get("formatted_description") or attrs.get("description") or "").strip() or f"HS {hs}"

    await _upsert_hs_code(db, hs_code=hs, jurisdiction="GB", description=description)

    index = _build_index([i for i in included if isinstance(i, dict)])
    rels = data.get("relationships") if isinstance(data.get("relationships"), dict) else {}

    mfn_pct: Decimal | None = None
    ts_rel = (rels.get("import_trade_summary") if isinstance(rels.get("import_trade_summary"), dict) else {}).get("data")
    if isinstance(ts_rel, dict):
        ts_id = ts_rel.get("id")
        if isinstance(ts_id, str):
            ts_obj = index.get("import_trade_summary", {}).get(ts_id, {})
            ts_attrs = ts_obj.get("attributes") if isinstance(ts_obj.get("attributes"), dict) else {}
            mfn_pct = _parse_pct(ts_attrs.get("basic_third_country_duty"))

    if mfn_pct is not None:
        await _upsert_measure(
            db,
            hs_code=hs,
            jurisdiction="GB",
            source_dataset="UK_TARIFF",
            source_measure_id=f"UK_MFN:{hs}",
            measure_type="MFN",
            country_of_origin=None,
            preferential_agreement=None,
            rate_ad_valorem=mfn_pct,
            raw_json={"mfn": str(mfn_pct), "source": "import_trade_summary"},
            valid_from=date.today(),
            valid_to=None,
            suspension=False,
        )

    dc = meta.get("duty_calculator") if isinstance(meta.get("duty_calculator"), dict) else {}
    vat_opts = dc.get("applicable_vat_options") if isinstance(dc.get("applicable_vat_options"), dict) else {}
    vat_pct: Decimal | None = None
    for _, text in vat_opts.items():
        if isinstance(text, str):
            vat_pct = _parse_pct(text)
            if vat_pct is not None:
                break
    if vat_pct is not None:
        await _upsert_gb_vat(db, vat_pct, {"vat_options": vat_opts})

    measure_rels = rels.get("import_measures") if isinstance(rels.get("import_measures"), dict) else {}
    measure_ids = measure_rels.get("data") if isinstance(measure_rels.get("data"), list) else []
    measures = []
    for m in measure_ids:
        if isinstance(m, dict):
            mid = m.get("id")
            if isinstance(mid, str) and mid in index.get("measure", {}):
                measures.append(index["measure"][mid])

    measures_upserted = 0
    for measure in measures:
        m_id = measure.get("id")
        if not isinstance(m_id, str):
            continue
        m_rels = measure.get("relationships") if isinstance(measure.get("relationships"), dict) else {}
        mt_id = ((m_rels.get("measure_type") if isinstance(m_rels.get("measure_type"), dict) else {}).get("data") or {}).get("id", "")
        geo_id = ((m_rels.get("geographical_area") if isinstance(m_rels.get("geographical_area"), dict) else {}).get("data") or {}).get("id", "")
        duty_expr_id = ((m_rels.get("duty_expression") if isinstance(m_rels.get("duty_expression"), dict) else {}).get("data") or {}).get("id", "")

        duty_expr = index.get("duty_expression", {}).get(str(duty_expr_id), {})
        duty_attrs = duty_expr.get("attributes") if isinstance(duty_expr.get("attributes"), dict) else {}
        rate_text = duty_attrs.get("base")
        rate_pct = _parse_pct(rate_text if isinstance(rate_text, str) else None)
        mtype = _measure_type_from_id(str(mt_id))
        if mtype == "OTHER":
            continue

        suspension = mtype == "SUSPENSION"
        await _upsert_measure(
            db,
            hs_code=hs,
            jurisdiction="GB",
            source_dataset="UK_TARIFF",
            source_measure_id=f"UK:{m_id}",
            measure_type=mtype,
            country_of_origin=str(geo_id) if geo_id else None,
            preferential_agreement=None,
            rate_ad_valorem=rate_pct,
            raw_json={"measure": measure},
            valid_from=date.today(),
            valid_to=None,
            suspension=suspension,
        )
        measures_upserted += 1

    return {"commodities": 1, "measures": measures_upserted}


async def _ingest_targeted(hs_codes: list[str]) -> dict[str, Any]:
    started = datetime.utcnow()
    async with AsyncSessionMaker() as db:
        run = IngestionRun(source="UK_TARIFF", status="running", started_at=started)
        db.add(run)
        await db.commit()
        await db.refresh(run)

        records_processed = 0
        measures_upserted = 0
        try:
            async with httpx.AsyncClient(timeout=25) as client:
                for hs in hs_codes:
                    counts = await _ingest_commodity(db, client, hs)
                    records_processed += counts["commodities"]
                    measures_upserted += counts["measures"]
                    await db.commit()
                    await asyncio.sleep(0.2)

            run.status = "success"
            run.records_processed = records_processed
            run.records_inserted = None
            run.records_updated = None
            run.completed_at = datetime.utcnow()
            await db.commit()
            return {
                "source": "UK_TARIFF",
                "status": run.status,
                "commodities_ingested": records_processed,
                "measures_upserted": measures_upserted,
            }
        except Exception as exc:
            await db.rollback()
            run.status = "failed"
            run.error_details = str(exc)
            run.completed_at = datetime.utcnow()
            await db.commit()
            return {"source": "UK_TARIFF", "status": run.status, "error": str(exc)}


async def _ingest_full(max_commodities: int | None) -> dict[str, Any]:
    started = datetime.utcnow()
    async with AsyncSessionMaker() as db:
        run = IngestionRun(source="UK_TARIFF_FULL", status="running", started_at=started)
        db.add(run)
        await db.commit()
        await db.refresh(run)

        commodities_ingested = 0
        measures_upserted = 0
        try:
            async with httpx.AsyncClient(timeout=25) as client:
                sections = await _fetch_all_pages(client, f"{_API_V2}/sections")
                for section in sections:
                    rels = section.get("relationships") if isinstance(section.get("relationships"), dict) else {}
                    chapters = rels.get("chapters") if isinstance(rels.get("chapters"), dict) else {}
                    chapters_link = (chapters.get("links") if isinstance(chapters.get("links"), dict) else {}).get("related")
                    if not isinstance(chapters_link, str):
                        continue
                    chapter_items = await _fetch_all_pages(client, chapters_link)
                    for chapter in chapter_items:
                        c_rels = chapter.get("relationships") if isinstance(chapter.get("relationships"), dict) else {}
                        headings = c_rels.get("headings") if isinstance(c_rels.get("headings"), dict) else {}
                        headings_link = (headings.get("links") if isinstance(headings.get("links"), dict) else {}).get("related")
                        if not isinstance(headings_link, str):
                            continue
                        heading_items = await _fetch_all_pages(client, headings_link)
                        for heading in heading_items:
                            h_rels = heading.get("relationships") if isinstance(heading.get("relationships"), dict) else {}
                            commodities = h_rels.get("commodities") if isinstance(h_rels.get("commodities"), dict) else {}
                            commodities_link = (commodities.get("links") if isinstance(commodities.get("links"), dict) else {}).get("related")
                            if not isinstance(commodities_link, str):
                                continue
                            commodity_items = await _fetch_all_pages(client, commodities_link)
                            for commodity in commodity_items:
                                attrs = commodity.get("attributes") if isinstance(commodity.get("attributes"), dict) else {}
                                code = attrs.get("goods_nomenclature_item_id") or attrs.get("code") or commodity.get("id")
                                if not isinstance(code, str):
                                    continue
                                hs = _digits(code)
                                if len(hs) < 6:
                                    continue
                                counts = await _ingest_commodity(db, client, hs)
                                commodities_ingested += counts["commodities"]
                                measures_upserted += counts["measures"]
                                await db.commit()
                                await asyncio.sleep(0.2)
                                if max_commodities is not None and commodities_ingested >= max_commodities:
                                    raise StopAsyncIteration()
        except StopAsyncIteration:
            run.status = "partial"
            run.records_processed = commodities_ingested
            run.completed_at = datetime.utcnow()
            await db.commit()
            return {
                "source": "UK_TARIFF_FULL",
                "status": run.status,
                "commodities_ingested": commodities_ingested,
                "measures_upserted": measures_upserted,
            }
        except Exception as exc:
            await db.rollback()
            run.status = "failed"
            run.error_details = str(exc)
            run.completed_at = datetime.utcnow()
            await db.commit()
            return {"source": "UK_TARIFF_FULL", "status": run.status, "error": str(exc)}

        run.status = "success"
        run.records_processed = commodities_ingested
        run.completed_at = datetime.utcnow()
        await db.commit()
        return {
            "source": "UK_TARIFF_FULL",
            "status": run.status,
            "commodities_ingested": commodities_ingested,
            "measures_upserted": measures_upserted,
        }


async def ingest_delta() -> dict[str, Any]:
    hs_codes_env = os.getenv("UK_TARIFF_HS_CODES", "")
    hs_codes = [c.strip() for c in hs_codes_env.split(",") if c.strip()]
    if not hs_codes:
        return await _ingest_targeted([])
    return await _ingest_targeted(hs_codes)


async def ingest_full() -> dict[str, Any]:
    max_commodities_env = os.getenv("UK_TARIFF_MAX_COMMODITIES", "").strip()
    max_commodities = int(max_commodities_env) if max_commodities_env.isdigit() else None
    return await _ingest_full(max_commodities)


def ingest_delta_sync() -> dict[str, Any]:
    return asyncio.run(ingest_delta())


def ingest_full_sync() -> dict[str, Any]:
    return asyncio.run(ingest_full())
