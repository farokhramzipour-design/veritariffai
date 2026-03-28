# VeriTariff — Agent Prompt Addon
## HS Code Discovery & Full Crawl Strategy

Append this section to the main VeriTariff agent prompt. It replaces the
stub references to uk_tariff.py and eu_taric.py with fully specified crawl logic.

---

## THE CORE PROBLEM: YOU NEED HS CODES BEFORE YOU CAN FETCH DATA

You do NOT need a pre-built list of HS codes. Both the UK and EU APIs are
tree-structured — you discover all valid codes by walking the tree from the
top. Build this bootstrap crawler before building the daily delta pipeline.

---

## UK TRADE TARIFF — FULL TREE CRAWL

The UK API is a clean REST API. The hierarchy is:
  Sections (21) → Chapters (~99) → Headings (~1200) → Commodities (leaf nodes, 10-digit)

All endpoints are free, no authentication, no rate limit headers — but add a
200ms delay between requests to be a polite client.

### Step 1 — Fetch all sections
```
GET https://www.trade-tariff.service.gov.uk/api/v2/sections
```
Returns a JSON array. Each object has `"id"` (1–21) and `"position"`.

### Step 2 — Fetch chapters per section
```
GET https://www.trade-tariff.service.gov.uk/api/v2/sections/{section_id}
```
The `"relationships.chapters.data"` array gives you chapter IDs (2-digit codes, e.g. "01" to "99").

### Step 3 — Fetch headings per chapter
```
GET https://www.trade-tariff.service.gov.uk/api/v2/chapters/{chapter_id}
```
The `"relationships.headings.data"` array gives you heading IDs (4-digit codes, e.g. "0101").

### Step 4 — Fetch all commodities under a heading
```
GET https://www.trade-tariff.service.gov.uk/api/v2/headings/{heading_id}
```
The `"relationships.commodities.data"` array gives you commodity goods_nomenclature_item_id
values (10-digit codes, e.g. "0101210000").
Filter: only keep leaf nodes where `"productline_suffix" == "80"` — these are
the actual declarable codes with duty rates. Parent/grouping nodes have suffix "10" and no rates.

### Step 5 — Fetch full commodity detail
```
GET https://www.trade-tariff.service.gov.uk/api/v2/commodities/{10_digit_code}
```
This returns the full duty and VAT data. Parse as follows:

**Duty rates** — look in `included[]` for objects with `type == "measure"`.
For each measure:
- `relationships.measure_type.data.id` → the measure type
  - "103" = third country (MFN) duty
  - "105" = preferential duty (trade agreement)
  - "551" = anti-dumping
- `relationships.geographical_area.data.id` → origin country ISO2 (or "1011" = erga omnes / all countries)
- `attributes.duty_expression.base` → the rate string, e.g. "12.00 %" or "4.70 GBP / kg"
  Parse percentage values into `duty_rate NUMERIC`. Non-% values go into `duty_amount + currency`.
- `attributes.effective_start_date` / `attributes.effective_end_date` → valid_from / valid_to
- Look in `included[]` for `type == "legal_act"` linked from the measure for `trade_agreement` name.

**VAT rates** — look in `included[]` for objects with `type == "measure"` AND
`relationships.measure_type.data.id == "305"` (VAT).
- `attributes.duty_expression.base` → e.g. "20.00 %" → vat_rate
- `attributes.geographical_area` is always GB for UK VAT

### Implementation — `app/pipeline/uk_tariff.py`

```python
import asyncio
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import CommodityCode, DutyRate, VatRate, PipelineRun

BASE = "https://www.trade-tariff.service.gov.uk/api/v2"
DELAY = 0.2  # seconds between requests

async def crawl_all(session: AsyncSession):
    """Full bootstrap crawl. Run once to populate the DB. ~4–8 hours for all ~20,000 leaf codes."""
    run = PipelineRun(source="uk_tariff_full", status="running")
    session.add(run)
    await session.commit()

    async with httpx.AsyncClient(timeout=30) as client:
        sections = await _get(client, f"{BASE}/sections")
        for section in sections["data"]:
            chapter_ids = await _get_chapter_ids(client, section["id"])
            for chapter_id in chapter_ids:
                heading_ids = await _get_heading_ids(client, chapter_id)
                for heading_id in heading_ids:
                    commodity_ids = await _get_commodity_ids(client, heading_id)
                    for commodity_id in commodity_ids:
                        await _fetch_and_store_commodity(client, session, commodity_id)
                        await asyncio.sleep(DELAY)

    run.status = "success"
    await session.commit()

async def crawl_commodity(session: AsyncSession, hs_code: str):
    """Targeted single-code fetch. Used for on-demand lookups and incremental updates."""
    async with httpx.AsyncClient(timeout=30) as client:
        await _fetch_and_store_commodity(client, session, hs_code)

async def _fetch_and_store_commodity(client, session, commodity_id):
    data = await _get(client, f"{BASE}/commodities/{commodity_id}")
    # Upsert commodity_codes
    # Parse included[] for measure types 103, 105, 551 → duty_rates
    # Parse included[] for measure type 305 → vat_rates
    # Store raw data["data"] as raw_json
    # Use INSERT ... ON CONFLICT (hs_code, market, origin_country, rate_type) DO UPDATE
    ...

async def _get(client, url):
    for attempt in range(3):
        try:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt == 2:
                raise
            await asyncio.sleep(2 ** attempt)
```

Implement all helper functions (`_get_chapter_ids`, `_get_heading_ids`,
`_get_commodity_ids`) following the tree walk described above.

---

## EU TARIC — XML BULK DOWNLOAD (NO CODE LIST NEEDED)

The EU TARIC data is distributed as a bulk XML file that contains ALL goods
nomenclature codes and ALL their measures in one download. You do NOT walk a
tree — you download the file and parse it all at once.

### Download URL
```
https://ec.europa.eu/taxation_customs/dds2/taric/xml/taric_download.jsp
```
This returns a large XML file (~50–200 MB). Download it once for the full
snapshot, then download daily deltas after that.

For daily deltas, add the date parameter:
```
https://ec.europa.eu/taxation_customs/dds2/taric/xml/taric_download.jsp?Expand=true&Lang=EN&Year=YYYY&Month=MM&Day=DD
```

### XML Structure to Parse

The TARIC XML uses this hierarchy. Navigate it with Python's `lxml` or
`xml.etree.ElementTree`:

```xml
<taricdoc>
  <TARIC.PUBLICATION>
    <!-- Goods nomenclature codes -->
    <GOODS.NOMENCLATURE>
      <GOODS.NOMENCLATURE.ITEM.ID>6403910000</GOODS.NOMENCLATURE.ITEM.ID>
      <PRODUCTLINE.SUFFIX>80</PRODUCTLINE.SUFFIX>  <!-- 80 = declarable leaf -->
      <GOODS.NOMENCLATURE.DESCRIPTION.PERIOD>
        <LANGUAGE.ID>EN</LANGUAGE.ID>
        <GOODS.NOMENCLATURE.DESCRIPTION>Footwear with outer soles of leather</GOODS.NOMENCLATURE.DESCRIPTION>
      </GOODS.NOMENCLATURE.DESCRIPTION.PERIOD>
    </GOODS.NOMENCLATURE>

    <!-- Measures (duty rates) -->
    <MEASURE>
      <MEASURE.SID>12345678</MEASURE.SID>
      <GOODS.NOMENCLATURE.ITEM.ID>6403910000</GOODS.NOMENCLATURE.ITEM.ID>
      <MEASURE.TYPE.ID>103</MEASURE.TYPE.ID>   <!-- 103=MFN, 142=preferential, 551=anti-dumping -->
      <GEOGRAPHICAL.AREA.ID>CN</GEOGRAPHICAL.AREA.ID>  <!-- origin, or "1011"=erga omnes -->
      <MEASURE.CONDITION>
        <MEASURE.CONDITION.DUTY.AMOUNT>8.000</MEASURE.CONDITION.DUTY.AMOUNT>
        <MONETARY.UNIT.CODE>EUR</MONETARY.UNIT.CODE>  <!-- absent if percentage -->
        <DUTY.EXPRESSION.ID>01</DUTY.EXPRESSION.ID>  <!-- 01=%, 02=specific -->
      </MEASURE.CONDITION>
      <VALIDITY.START.DATE>2024-01-01</VALIDITY.START.DATE>
      <VALIDITY.END.DATE/>  <!-- empty = still valid -->
    </MEASURE>
  </TARIC.PUBLICATION>
</taricdoc>
```

### Key measure type IDs (MEASURE.TYPE.ID)
| ID  | Meaning             |
|-----|---------------------|
| 103 | MFN (third country) |
| 142 | Tariff preference   |
| 551 | Anti-dumping        |
| 552 | Countervailing      |
| 112 | Autonomous suspension |
| 115 | Autonomous end-use  |

### Implementation — `app/pipeline/eu_taric.py`

```python
import httpx
import gzip
from lxml import etree
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import CommodityCode, DutyRate, PipelineRun
from datetime import date

TARIC_URL = "https://ec.europa.eu/taxation_customs/dds2/taric/xml/taric_download.jsp"
MEASURE_TYPE_MAP = {
    "103": "MFN",
    "142": "preferential",
    "551": "anti-dumping",
    "552": "countervailing",
    "112": "suspension",
}

async def run_full_snapshot(session: AsyncSession):
    """Download full TARIC XML and populate DB. Run once for bootstrap."""
    run = PipelineRun(source="eu_taric_full", status="running")
    session.add(run)
    await session.commit()

    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.get(TARIC_URL, params={"Expand": "true", "Lang": "EN"})
        response.raise_for_status()
        xml_content = response.content
        # Handle gzip if returned compressed
        if xml_content[:2] == b'\x1f\x8b':
            xml_content = gzip.decompress(xml_content)

    records = _parse_taric_xml(xml_content)
    await _upsert_records(session, records)

    run.status = "success"
    run.records_upserted = len(records)
    await session.commit()

async def run_daily_delta(session: AsyncSession, delta_date: date = None):
    """Download and apply the daily delta XML."""
    if delta_date is None:
        from datetime import date as d
        delta_date = d.today()
    params = {
        "Expand": "true", "Lang": "EN",
        "Year": delta_date.year, "Month": f"{delta_date.month:02d}", "Day": f"{delta_date.day:02d}"
    }
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(TARIC_URL, params=params)
        response.raise_for_status()
    records = _parse_taric_xml(response.content)
    await _upsert_records(session, records)

def _parse_taric_xml(xml_bytes: bytes) -> list[dict]:
    """Parse TARIC XML and return list of duty rate dicts ready for upsert."""
    root = etree.fromstring(xml_bytes)
    ns = root.nsmap.get(None, "")
    def tag(name): return f"{{{ns}}}{name}" if ns else name

    # First pass: build code → description map
    code_descriptions = {}
    for node in root.iter(tag("GOODS.NOMENCLATURE")):
        code = node.findtext(tag("GOODS.NOMENCLATURE.ITEM.ID"))
        suffix = node.findtext(tag("PRODUCTLINE.SUFFIX"))
        if suffix == "80":  # declarable leaf only
            for desc_period in node.iter(tag("GOODS.NOMENCLATURE.DESCRIPTION.PERIOD")):
                if desc_period.findtext(tag("LANGUAGE.ID")) == "EN":
                    code_descriptions[code] = desc_period.findtext(tag("GOODS.NOMENCLATURE.DESCRIPTION"))

    # Second pass: parse measures
    records = []
    for measure in root.iter(tag("MEASURE")):
        hs_code = measure.findtext(tag("GOODS.NOMENCLATURE.ITEM.ID"))
        if hs_code not in code_descriptions:
            continue  # skip non-leaf codes
        measure_type_id = measure.findtext(tag("MEASURE.TYPE.ID"))
        rate_type = MEASURE_TYPE_MAP.get(measure_type_id)
        if not rate_type:
            continue

        origin = measure.findtext(tag("GEOGRAPHICAL.AREA.ID"))
        if origin == "1011":  # erga omnes = applies to all origins
            origin = None

        duty_rate = None
        duty_amount = None
        currency = None
        cond = measure.find(tag("MEASURE.CONDITION"))
        if cond is not None:
            amount_str = cond.findtext(tag("MEASURE.CONDITION.DUTY.AMOUNT"))
            unit = cond.findtext(tag("MONETARY.UNIT.CODE"))
            expr_id = cond.findtext(tag("DUTY.EXPRESSION.ID"))
            if amount_str:
                if expr_id == "01" or unit is None:
                    duty_rate = float(amount_str)
                else:
                    duty_amount = float(amount_str)
                    currency = unit

        valid_from_str = measure.findtext(tag("VALIDITY.START.DATE"))
        valid_to_str = measure.findtext(tag("VALIDITY.END.DATE"))

        records.append({
            "hs_code": hs_code,
            "market": "EU",
            "origin_country": origin,
            "rate_type": rate_type,
            "duty_rate": duty_rate,
            "duty_amount": duty_amount,
            "currency": currency,
            "valid_from": valid_from_str,
            "valid_to": valid_to_str if valid_to_str else None,
            "source": "TARIC",
            "description": code_descriptions.get(hs_code),
        })
    return records

async def _upsert_records(session: AsyncSession, records: list[dict]):
    """Bulk upsert using INSERT ... ON CONFLICT DO UPDATE."""
    from sqlalchemy.dialects.postgresql import insert
    from app.models import DutyRate, CommodityCode
    # Upsert commodity_codes first, then duty_rates
    # Use execute(insert(DutyRate).values(...).on_conflict_do_update(...)) in batches of 500
    ...
```

---

## BOOTSTRAP SEQUENCE (run in this order on first deploy)

Add a FastAPI endpoint or CLI command that runs the bootstrap in the right order:

```
POST /pipeline/bootstrap
```

Sequence:
1. `eu_vat.run()` — fast, just one HTTP call, populates vat_rates for all EU countries
2. `eu_taric.run_full_snapshot()` — downloads full TARIC XML (~200 MB), parses ~20,000 codes
3. `uk_tariff.crawl_all()` — walks the tree, ~20,000 commodity API calls, expect 4–8 hours

After bootstrap, the scheduler takes over with daily deltas (TARIC) and daily
commodity refresh (UK — re-fetch only codes where `last_updated < NOW() - INTERVAL '7 days'`).

---

## IMPORTANT NOTES

- The TARIC XML does NOT include VAT rates. VAT is a national tax. Use euvatrates.com for EU VAT.
- The UK Trade Tariff API DOES include VAT (measure type 305 = UK VAT at 0%, 5%, or 20%).
- For EU VAT you need a separate mapping: HS code prefix → VAT rate category per country.
  For example, DE applies 7% VAT to most food (HS chapter 02–24) and 19% to everything else.
  Start with the country-level standard rate (NULL hs_code_prefix) and enhance later.
- The UK crawl will produce ~20,000 API calls. Do not run it repeatedly. Store a
  `crawl_completed` flag in a config table and guard the bootstrap endpoint against re-runs.
- TARIC XML filenames and parameters change occasionally — log the HTTP response
  headers on every download and alert if the content-length drops below 10 MB
  (likely an error page, not real data).
