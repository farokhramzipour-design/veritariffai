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
_UK_API = "https://www.trade-tariff.service.gov.uk/api/v2/commodities"

_MT_THIRD_COUNTRY = "103"
_MT_TARIFF_PREF = "105"
_MT_TARIFF_PREF_ALT = "142"
_MT_ANTI_DUMPING = "551"
_MT_COUNTERVAILING = "552"
_MT_COUNTERVAILING_ALT = "672"
_MT_SUSPENSION = "112"
_MT_END_USE = "115"
_MT_END_USE_ALT = "106"
_MT_VAT = "305"


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
    if mt_id in (_MT_TARIFF_PREF, _MT_TARIFF_PREF_ALT):
        return "PREFERENTIAL"
    if mt_id == _MT_THIRD_COUNTRY:
        return "MFN"
    if mt_id == _MT_ANTI_DUMPING:
        return "ANTI_DUMPING"
    if mt_id in (_MT_COUNTERVAILING, _MT_COUNTERVAILING_ALT):
        return "COUNTERVAILING"
    if mt_id in (_MT_SUSPENSION, _MT_END_USE, _MT_END_USE_ALT):
        return "SUSPENSION"
    if mt_id == _MT_VAT:
        return "VAT"
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
        headers={"Accept": "application/vnd.hmrc.2.0+json"},
    )
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    included = payload.get("included") if isinstance(payload.get("included"), list) else []

    attrs = data.get("attributes") if isinstance(data.get("attributes"), dict) else {}
    description = str(attrs.get("formatted_description") or attrs.get("description") or "").strip() or f"HS {hs}"

    await _upsert_hs_code(db, hs_code=hs, jurisdiction="GB", description=description)

    index = _build_index([i for i in included if isinstance(i, dict)])
    measures_upserted = 0
    measures = [obj for obj in included if isinstance(obj, dict) and obj.get("type") == "measure"]
    for measure in measures:
        m_id = measure.get("id")
        if not isinstance(m_id, str) or not m_id:
            continue

        m_attrs = measure.get("attributes") if isinstance(measure.get("attributes"), dict) else {}
        m_rels = measure.get("relationships") if isinstance(measure.get("relationships"), dict) else {}

        mt_id = ((m_rels.get("measure_type") if isinstance(m_rels.get("measure_type"), dict) else {}).get("data") or {}).get("id", "")
        geo_id = ((m_rels.get("geographical_area") if isinstance(m_rels.get("geographical_area"), dict) else {}).get("data") or {}).get("id", "")
        legal_act_id = ((m_rels.get("legal_act") if isinstance(m_rels.get("legal_act"), dict) else {}).get("data") or {}).get("id", "")

        mtype = _measure_type_from_id(str(mt_id))
        if mtype == "OTHER":
            continue

        duty_expr = m_attrs.get("duty_expression") if isinstance(m_attrs.get("duty_expression"), dict) else None
        rate_text = None
        if duty_expr and isinstance(duty_expr.get("base"), str):
            rate_text = duty_expr.get("base")
        else:
            duty_expr_id = ((m_rels.get("duty_expression") if isinstance(m_rels.get("duty_expression"), dict) else {}).get("data") or {}).get("id", "")
            de_obj = index.get("duty_expression", {}).get(str(duty_expr_id), {})
            de_attrs = de_obj.get("attributes") if isinstance(de_obj.get("attributes"), dict) else {}
            if isinstance(de_attrs.get("base"), str):
                rate_text = de_attrs.get("base")

        rate_pct = _parse_pct(rate_text if isinstance(rate_text, str) else None)

        valid_from = None
        valid_to = None
        if isinstance(m_attrs.get("effective_start_date"), str):
            try:
                valid_from = date.fromisoformat(m_attrs["effective_start_date"])
            except Exception:
                valid_from = None
        if isinstance(m_attrs.get("effective_end_date"), str) and m_attrs["effective_end_date"].strip():
            try:
                valid_to = date.fromisoformat(m_attrs["effective_end_date"])
            except Exception:
                valid_to = None
        valid_from = valid_from or date.today()

        if mtype == "VAT":
            await _upsert_gb_vat(db, rate_pct, {"measure": measure})
            continue

        trade_agreement = None
        if legal_act_id:
            la = index.get("legal_act", {}).get(str(legal_act_id), {})
            la_attrs = la.get("attributes") if isinstance(la.get("attributes"), dict) else {}
            if isinstance(la_attrs.get("title"), str):
                trade_agreement = la_attrs.get("title")
            elif isinstance(la_attrs.get("description"), str):
                trade_agreement = la_attrs.get("description")

        origin = None
        if geo_id and geo_id != "1011":
            origin = str(geo_id)

        suspension = mtype == "SUSPENSION"
        await _upsert_measure(
            db,
            hs_code=hs,
            jurisdiction="GB",
            source_dataset="UK_TARIFF",
            source_measure_id=f"UK:{m_id}",
            measure_type=mtype,
            country_of_origin=origin,
            preferential_agreement=trade_agreement,
            rate_ad_valorem=rate_pct,
            raw_json={"measure": measure},
            valid_from=valid_from,
            valid_to=valid_to,
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
                    section_id = section.get("id")
                    if not isinstance(section_id, str) or not section_id:
                        continue

                    section_detail = await _get_json_with_retries(
                        client,
                        f"{_API_V2}/sections/{section_id}",
                        headers={"Accept": "application/vnd.hmrc.2.0+json"},
                    )
                    s_data = section_detail.get("data") if isinstance(section_detail.get("data"), dict) else {}
                    s_rels = s_data.get("relationships") if isinstance(s_data.get("relationships"), dict) else {}
                    chapters_rel = s_rels.get("chapters") if isinstance(s_rels.get("chapters"), dict) else {}
                    chapter_ids = chapters_rel.get("data") if isinstance(chapters_rel.get("data"), list) else []
                    chapter_ids_norm = [c.get("id") for c in chapter_ids if isinstance(c, dict) and isinstance(c.get("id"), str)]

                    for chapter_id in chapter_ids_norm:
                        chapter_detail = await _get_json_with_retries(
                            client,
                            f"{_API_V2}/chapters/{chapter_id}",
                            headers={"Accept": "application/vnd.hmrc.2.0+json"},
                        )
                        c_data = chapter_detail.get("data") if isinstance(chapter_detail.get("data"), dict) else {}
                        c_rels = c_data.get("relationships") if isinstance(c_data.get("relationships"), dict) else {}
                        headings_rel = c_rels.get("headings") if isinstance(c_rels.get("headings"), dict) else {}
                        heading_ids = headings_rel.get("data") if isinstance(headings_rel.get("data"), list) else []
                        heading_ids_norm = [h.get("id") for h in heading_ids if isinstance(h, dict) and isinstance(h.get("id"), str)]

                        for heading_id in heading_ids_norm:
                            heading_detail = await _get_json_with_retries(
                                client,
                                f"{_API_V2}/headings/{heading_id}",
                                headers={"Accept": "application/vnd.hmrc.2.0+json"},
                            )
                            included = heading_detail.get("included") if isinstance(heading_detail.get("included"), list) else []
                            commodity_codes: list[str] = []
                            for obj in included:
                                if not isinstance(obj, dict):
                                    continue
                                if obj.get("type") not in {"commodity", "commodities"}:
                                    continue
                                attrs = obj.get("attributes") if isinstance(obj.get("attributes"), dict) else {}
                                if str(attrs.get("productline_suffix") or "") != "80":
                                    continue
                                code = attrs.get("goods_nomenclature_item_id") or obj.get("id")
                                if isinstance(code, str):
                                    hs = _digits(code)
                                    if hs and len(hs) >= 6:
                                        commodity_codes.append(hs)

                            if not commodity_codes:
                                h_data = heading_detail.get("data") if isinstance(heading_detail.get("data"), dict) else {}
                                h_rels = h_data.get("relationships") if isinstance(h_data.get("relationships"), dict) else {}
                                comm_rel = h_rels.get("commodities") if isinstance(h_rels.get("commodities"), dict) else {}
                                comm_ids = comm_rel.get("data") if isinstance(comm_rel.get("data"), list) else []
                                for c in comm_ids:
                                    if isinstance(c, dict) and isinstance(c.get("id"), str):
                                        hs = _digits(c["id"])
                                        if hs and len(hs) >= 6:
                                            commodity_codes.append(hs)

                            for hs in commodity_codes:
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
