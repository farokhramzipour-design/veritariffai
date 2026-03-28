# VeriTariff — AI Agent Prompt (v3)
## Feature: Tariff & VAT Data Pipeline (EU + UK) with Complete Duty Expression Parsing

---

## YOUR ROLE

You are a senior Python backend engineer implementing a tariff data pipeline for
**VeriTariff**, a web application that allows users to look up import duty rates,
VAT, and all associated border compliance requirements by HS code, origin country,
and destination country.

Your task is to build a **production-ready data pipeline in Python / FastAPI** that
fetches, normalises, stores, and refreshes tariff data from free official sources
for the **EU and UK markets** — including full measure condition parsing and ALL
duty expression types so the calculator can show users exactly what documents they
need and what rate applies in each case.

---

## DATA SOURCES TO INTEGRATE

### 1. UK Trade Tariff API (free, no auth required)
- **Sections**: `GET https://www.trade-tariff.service.gov.uk/api/v2/sections`
- **Chapters**: `GET https://www.trade-tariff.service.gov.uk/api/v2/sections/{id}`
- **Headings**: `GET https://www.trade-tariff.service.gov.uk/api/v2/chapters/{id}`
- **Commodities**: `GET https://www.trade-tariff.service.gov.uk/api/v2/headings/{id}`
- **Full detail**: `GET https://www.trade-tariff.service.gov.uk/api/v2/commodities/{10_digit_code}`
- Returns: duty rates, VAT, trade agreements, measure conditions, certificates required.
- Update frequency: daily.

### 2. EU TARIC Data (free XML bulk download)
- **Full snapshot**: `https://ec.europa.eu/taxation_customs/dds2/taric/xml/taric_download.jsp`
- **Daily delta**: append `?Expand=true&Lang=EN&Year=YYYY&Month=MM&Day=DD`
- Returns: all goods nomenclature codes, all measures, all conditions.
- Update frequency: daily delta after initial full snapshot.

### 3. EU VAT Rates (euvatrates.com)
- **Endpoint**: `GET https://euvatrates.com/rates.json`
- Returns: standard, reduced, super_reduced, parking rates per EU country.
- Update frequency: weekly.

### 4. EU VAT TEDB (official EC backup)
- URL: `https://taxsud.ec.europa.eu/tedb/`
- Use as validation against euvatrates.com.

---

## COMPLETE DUTY EXPRESSION CATALOGUE

This section documents EVERY duty expression pattern found in real TARIC data.
The parser MUST handle all of them. A duty expression is the string in the
`Duty` column in TARIC — it defines what financial obligation (if any) applies.

### Category 1 — Simple ad valorem (percentage of customs value)

```
0.000 %
2.000 %
4.200 %
8.000 %
12.800 %
20.000 %
35.000 %
```

**Parse rule:** Extract the numeric value. Store in `duty_rate` column.
`duty_amount = NULL`, `unit_code = NULL`.

---

### Category 2 — Specific duty (fixed amount per unit of quantity)

```
30.900 EUR DTN          # EUR per 100 kg (decitonnes)
268.000 EUR TNE         # EUR per tonne
0.740 EUR KGM           # EUR per kilogram
52.000 EUR MIL          # EUR per thousand items
4.480 EUR NAR           # EUR per item/unit
27.000 EUR HLT          # EUR per hectolitre
0.360 EUR DTN
32.710 EUR TNE
4.580 EUR KGM
```

**Parse rule:** Extract amount and unit. Store in `duty_amount` + `currency` + `unit_code`.
`duty_rate = NULL`.

**Unit code reference:**
| Code | Meaning |
|------|---------|
| DTN  | Per 100 kg (decitonnes) |
| TNE  | Per tonne (1000 kg) |
| KGM  | Per kilogram |
| MIL  | Per thousand items |
| NAR  | Per item (number of articles) |
| HLT  | Per hectolitre (100 litres) |
| LTR  | Per litre |
| LPA  | Per litre pure (100%) alcohol |
| MTQ  | Per cubic metre |
| MTK  | Per square metre |
| MTR  | Per metre |
| KPP  | Per kilogram per percent |
| KPH  | Per kilogram hydrogen peroxide |
| KPO  | Per kilogram potassium oxide |
| KNI  | Per kilogram nitrogen |
| KSD  | Per kilogram sodium hydroxide |
| KMA  | Per kilogram methylamine |
| KMT  | Per kilogram methanol |
| KNS  | Per kilogram nitrogen per sulfate |
| GRM  | Per gram |
| GFI  | Per gram fissile isotopes |
| KUR  | Per kilogram uranium |
| CCT  | Per carrying capacity in tonnes |
| CEN  | Per hundred items |
| TCE  | Per tonne CO2 equivalent |
| NPR  | Per net pair |
| NCL  | Per cell |
| CTM  | Per carat |
| ASV  | Per percent of alcohol by volume |
| HMT  | Per hundred metres |

---

### Category 3 — Mixed duty (ad valorem + specific)

```
10.200 % + 93.100 EUR DTN
7.600 % + 69.820 EUR DTN
12.800 % + 176.800 EUR DTN
0.000 % + 176.800 EUR DTN
2.500 % + 35.300 EUR DTN
15.000 % + 994.500 EUR TNE
12.800 % + 265.200 EUR DTN
15.000 % + 1,554.300 EUR TNE
15.000 % + 2,138.400 EUR TNE
0.000 % + 93.100 EUR DTN
```

**Parse rule:** Both `duty_rate` (%) AND `duty_amount` + `unit_code` are populated.
The total duty = (CIF value x duty_rate%) + (quantity x duty_amount).

---

### Category 4 — Duty with minimum threshold

```
9.600 % MIN 1.100 EUR DTN
13.600 % MIN 1.600 EUR DTN
12.000 % MIN 0.400 EUR DTN
10.400 % MIN 1.300 EUR DTN G
12.000 % MIN 2.000 EUR DTN G
3.800 % MIN 0.600 EUR DTN G
3.800 % MIN 0.400 EUR DTN G
4.400 % MIN 0.400 EUR DTN G
3.000 % MIN 1.200 EUR DTN G
10.400 % MIN 1.600 EUR DTN
18.400 % MIN 22.000 EUR DTN MAX 24.000 EUR DTN
11.200 % MIN 22.000 EUR DTN MAX 56.000 EUR DTN
10.000 % MIN 22.000 EUR DTN MAX 56.000 EUR DTN
1.800 % MIN 0.090 EUR DTN
2.800 % MIN 0.360 EUR DTN
7.200 % MIN 0.360 EUR DTN
```

**Parse rule:** `duty_rate` is populated. Also populate `duty_min_amount` and
`duty_min_unit_code`. If `G` suffix present, the minimum applies to gross weight.
If both MIN and MAX present, also populate `duty_max_amount`.

---

### Category 5 — Duty with maximum threshold

```
14.900 % MAX 24.000 EUR DTN
2.300 % MAX 3.000 EUR DTN
7.400 % MAX 12.000 EUR DTN
6.400 % MAX 24.000 EUR DTN
3.200 % MAX 12.000 EUR DTN
3.900 % MAX 56.000 EUR DTN
1.900 % MAX 28.000 EUR DTN
8.000 % MAX 2.800 EUR MTK
6.400 % MAX 2.800 EUR MTK
4.500 % MIN 0.300 EUR NAR MAX 0.800 EUR NAR
5.000 % MIN 0.170 EUR NAR
0.500 EUR NAR MIN 2.700 % MAX 4.600 %
```

**Parse rule:** Populate `duty_rate`, `duty_max_amount`, `duty_max_unit_code`.

---

### Category 6 — MAX combined with formula expression

```
0.000 % + 45.100 EUR DTN MAX 18.900 % + 16.500 EUR DTN
5.600 % + 45.100 EUR DTN MAX 18.900 % + 16.500 EUR DTN
9.100 % + 45.100 EUR DTN MAX 18.900 % + 16.500 EUR DTN
0.000 % + 22.550 EUR DTN MAX 9.400 % + 8.250 EUR DTN MAX 35.150 EUR DTN
4.500 % + 22.550 EUR DTN MAX 9.400 % + 8.250 EUR DTN MAX 35.150 EUR DTN
6.700 % MAX 35.150 EUR DTN
0.000 % + 25.850 EUR DTN MAX 17.900 %
0.000 % + 27.100 EUR DTN MAX 17.900 %
6.200 % + 27.100 EUR DTN MAX 17.900 %
0.000 % + 15.210 EUR DTN M
0.000 % + 35.500 EUR DTN M
```

**Parse rule:** The full expression is complex. Store the entire raw expression
string in `duty_expression_raw`. Parse the base rate/amount and max cap.
Surface to user as: "Whichever of [base formula] and [cap formula] is lower applies."

---

### Category 7 — Agricultural Entry Price / EA (Entree Agricole)

```
7.600 % + EA
0.000 % + EA
1.190 % + EA
5.500 % + EA
9.000 % + EA
6.000 % + EA
4.800 % + EA
8.300 % + EA
10.700 % + EA
15.400 % + EA
```

And EAR (reduced entry price):
```
0.000 % + EAR
6.200 % + EAR
1.900 % + EAR
5.700 % + EAR
4.000 % + EAR
0.900 % + EAR
4.700 % + EAR
2.700 % + EAR
1.100 % + EAR
5.600 % + EAR
5.800 % + EAR
4.100 % + EAR
6.500 % + EA
```

EA/EAR with MAX cap and additional duty components:
```
0.000 % + EA MAX 18.700 % +ADSZ
5.500 % + EA MAX 18.700 % +ADSZ
9.000 % + EA MAX 18.700 % +ADSZ
4.800 % + EA MAX 18.700 % +ADSZ
8.300 % + EA MAX 18.700 % +ADSZ
0.000 % + EA MAX 0.000 % +ADSZ
0.000 % + EA MAX 24.200 % +ADSZ
9.000 % + EA MAX 24.200 % +ADSZ
5.500 % + EA MAX 24.200 % +ADSZ
0.000 % + EA MAX 20.700 % +ADFM
9.000 % + EA MAX 20.700 % +ADFM
5.500 % + EA MAX 20.700 % +ADFM
4.500 % + EAR MAX 9.300 % +ADSZR MAX 35.150 EUR DTN
4.100 % + EAR MAX 9.300 % +ADSZR MAX 35.150 EUR DTN
4.500 % + EAR MAX 12.100 % +ADSZR MAX 35.150 EUR DTN
0.000 % + EAR MAX 9.300 % +ADSZR
0.000 % + EAR MAX 18.700 % +ADSZR
6.000 % + EAR MAX 18.700 % +ADSZR
4.150 % + EAR MAX 9.350 % +ADSZR
0.000 % + EAR MAX 12.100 % +ADSZR
0.000 % + EAR MAX 10.300 % +ADSZR
0.000 % + EAR MAX 20.700 % +ADFMR
4.500 % + EAR MAX 10.300 % +ADFMR MAX 35.150 EUR DTN
6.200 % + EAR
9.700 % + EA
6.000 % + EAR
4.100 % + EA
```

**EA = Entry price component.** The exact EUR/kg amount is computed daily by the
European Commission from world market prices.
EAR = reduced entry price component (under FTA or preference).

**ADSZ, ADSZR, ADFM, ADFMR** = additional specific duties:
- **ADSZ** = additional duty based on sugar/starch content (ZUC/AMI)
- **ADSZR** = reduced version under preference
- **ADFM** = additional duty based on flour/meal content
- **ADFMR** = reduced version under preference

**Parse rule:**
- Set `has_entry_price = TRUE`, `entry_price_is_reduced` based on EAR vs EA
- Store which additional duty components apply in `additional_duty_components JSONB`
- Store max cap if present in `duty_max_amount`
- Surface to user: "Entry price component applies — exact amount calculated daily by
  EC from world market prices. Cannot be pre-calculated."

---

### Category 8 — EUC (EU Customs computed unit price)

```
43.860 EUC DTN
97.340 EUC DTN
173.370 EUC DTN
256.350 EUC DTN
777.070 EUC DTN
182.580 EUC DTN
139.430 EUC DTN
548.550 EUC DTN
300.010 EUC DTN
179.450 EUC DTN
242.300 EUC DTN
247.500 EUC DTN
172.560 EUC DTN
399.840 EUC DTN
1,206.610 EUC DTN
110.920 EUC DTN
80.890 EUC DTN
112.700 EUC DTN
125.610 EUC DTN
52.730 EUC DTN
```

**EUC = EU Customs computed amount.** Often appears for processed agricultural
products. These are computed amounts that change daily.

**Parse rule:** Same as Category 2 but set `unit_code = 'EUC_DTN'` to distinguish
from plain EUR DTN. Set `is_computed_daily = TRUE`.

---

### Category 9 — Alcohol by volume specific duty (ASV)

```
0.000 EUR ASV X
1.750 EUR ASV X
0.075 EUR ASV X
0.380 EUR ASV X
0.600 EUR ASV X
0.900 EUR ASV X
0.125 EUR ASV X
0.250 EUR ASV X
0.460 EUR ASV X
0.700 EUR ASV X
1.000 EUR ASV X
```

Combined ASV + HLT:
```
0.000 EUR ASV X + 4.400 EUR HLT
0.000 EUR ASV X + 0.800 EUR HLT
0.000 EUR ASV X + 2.930 EUR HLT
0.900 EUR ASV X + 6.400 EUR HLT
0.075 EUR ASV X + 0.400 EUR HLT
0.380 EUR ASV X + 2.000 EUR HLT
0.600 EUR ASV X + 3.200 EUR HLT
0.700 EUR ASV X + 4.400 EUR HLT
0.125 EUR ASV X + 0.800 EUR HLT
0.250 EUR ASV X + 1.600 EUR HLT
0.460 EUR ASV X + 2.930 EUR HLT
1.000 EUR ASV X + 6.400 EUR HLT
```

**ASV = per percent of alcohol by volume. `X` = per supplementary quantity declared.**

**Parse rule:** Store `duty_asv_amount` (per ASV%) and optionally `duty_amount`
(per hectolitre base). Total = (ASV% x asv_rate) + hlt_rate.
Surface to user: "Duty per degree of alcohol content. Exact amount depends on
declared alcohol strength."

---

### Category 10 — Specific duty on declared per-unit price (P suffix)

```
0.230 EUR KGM P
1.190 EUR KGM P
0.680 EUR KGM P + 12.130 EUR DTN
1.080 EUR KGM P + 19.400 EUR DTN
0.260 EUR KGM P + 4.400 EUR DTN
1.310 EUR KGM P + 22.000 EUR DTN
0.320 EUR KGM P + 4.400 EUR DTN
1.620 EUR KGM P + 22.000 EUR DTN
0.170 EUR KGM P + 21.100 EUR DTN
0.110 EUR KGM P + 13.190 EUR DTN
0.200 EUR KGM P + 21.100 EUR DTN
0.130 EUR KGM P + 13.190 EUR DTN
0.540 EUR KGM P + 21.100 EUR DTN
0.340 EUR KGM P + 13.190 EUR DTN
1.130 EUR KGM P + 19.400 EUR DTN
1.810 EUR KGM P + 19.400 EUR DTN
```

**`P` suffix = applied per unit of the supplementary quantity (price per unit).**

**Parse rule:** Store `duty_per_unit_price` and `duty_unit = 'KGM_P'`. Combined
with a specific DTN component if present.

---

### Category 11 — Duty based on tare weight (T suffix)

```
0.040 EUR KGM T
0.070 EUR KGM T
0.040 EUR KGM T + 10.500 EUR DTN
0.070 EUR KGM T + 16.800 EUR DTN
```

**`T` suffix = per kg tare weight.**

**Parse rule:** Store `duty_tare_amount` + optional `duty_amount` for the DTN component.

---

### Category 12 — Graduated variable rate based on CIF price (V conditions)

These define a sliding scale where the duty depends on the actual CIF import price.

```
Cond: V 52.600 EUR/DTN(01):12.000 % ; V 51.500 EUR/DTN(01):12.000 % + 1.100 EUR DTN ; ...
Cond: V 84.600 EUR/DTN(01):0.000 % ; V 82.900 EUR/DTN(01):0.000 % + 1.700 EUR DTN ; ... ; V 0.000 EUR/DTN(01):0.000 % + 29.800 EUR DTN
Cond: V 110.500 EUR/DTN(01):2.500 % ; V 108.300 EUR/DTN(01):2.500 % + 2.200 EUR DTN ; ...
```

Also combined with B-cert conditions:
```
Cond: B cert: U-088 (27):; B (07):; V 84.600 EUR/DTN(01):0.000 % ; ...
Cond: B cert: Y-086 (27):; B (07):; V 62.600 EUR/DTN(01):0.000 % ; ...
```

And Y-cert conditions:
```
Cond: V 84.600 EUR/DTN(01):0.000 % ; ... ; Y cert: Y-864 (27):; Y (07):
```

**Parse rule:** These are **variable duty schedules** tied to the declared CIF price.
Store as `variable_duty_schedule JSONB`:
```json
[
  {"price_threshold_eur_per_dtn": 84.60, "price_condition": ">=", "duty_rate_pct": 0.0, "duty_amount": null, "duty_unit": null},
  {"price_threshold_eur_per_dtn": 0.0, "price_condition": ">=", "duty_rate_pct": 0.0, "duty_amount": 29.80, "duty_unit": "DTN"}
]
```

Surface to user: "Duty varies by declared CIF price — provide your import price to
calculate the exact rate."

---

### Category 13 — Weight/price ratio conditions (R conditions)

```
Cond: R 80.001/KGM(10):; R 0.000/KGM(28):
Cond: R 160.001/KGM(10):; R 80.001/KGM(28):; R 0.000/KGM(10):
Cond: R 300.001/KGM(10):; R 160.001/KGM(28):; R 0.000/KGM(10):
Cond: R 0.860/KGM(10):; R 0.700/KGM(28):; R 0.000/KGM(10):
Cond: R 2.600/KGM(10):; R 1.100/KGM(28):; R 0.000/KGM(10):
Cond: R 1.160/KGM(10):; R 0.952/KGM(28):; R 0.000/KGM(10):
Cond: R 5.000/KGM(10):; R 1.000/KGM(28):; R 0.000/KGM(10):
Cond: R 120.000/KGM(10):; R 0.500/KGM(28):; R 0.000/KGM(10):
```

**R = Range/Ratio condition.** `(10)` = applies when value >= threshold;
`(28)` = applies when value < threshold.

**Parse rule:** Store `quantity_condition_schedule JSONB`:
```json
[
  {"threshold": 80.001, "unit": "KGM", "applies_code": "10", "meaning": "above_threshold"},
  {"threshold": 0.0, "unit": "KGM", "applies_code": "28", "meaning": "below_threshold"}
]
```

---

### Category 14 — Quantity/Size threshold conditions (J, X, U)

```
Cond: J 4.999/KGM(28):; J 0.000/KGM(21):    # net weight per piece
Cond: J 5.000/KGM(28):; J 0.000/KGM(21):
Cond: J 9.999/KGM(28):; J 0.000/KGM(21):
Cond: J 99.999/KGM(28):; J 0.000/KGM(21):

Cond: X 49.999/LTR(28):; X 0.000/LTR(22):   # volume per vessel
Cond: X 19.999/LTR(28):; X 0.000/LTR(22):
Cond: X 2,499.000/NAR(28):; X 0.000/NAR(22):
Cond: X 999.000/NAR(28):; X 0.000/NAR(22):
Cond: X 99.000/NAR(28):; X 0.000/NAR(22):

Cond: U 7.900 EUR/LPA(28):; U 0.000 EUR/LPA(10):   # price per LPA
Cond: U 7.900 EUR/LPA(10):; U 0.000 EUR/LPA(28):
Cond: U 2.000 EUR/LPA(28):; U 0.000 EUR/LPA(10):
Cond: U 65.000 EUR/NAR(28):; U 0.000 EUR/NAR(10):
Cond: U 65.000 EUR/NAR(10):; U 0.000 EUR/NAR(28):
```

**Parse rule:** Store `size_condition_schedule JSONB`. Surface to user:
"Rate depends on pack size / volume per container / price per unit."

---

### Category 15 — Price-based admission conditions (L conditions)

```
Cond: L 143.010 EUR/DTN(01):0.000 EUR DTN ; L 95.340 EUR/DTN(01):42.903 EUR DTN - 30.000 % ; L 63.560 EUR/DTN(01):61.971 EUR DTN - 50.000 % ; L 39.725 EUR/DTN(01):74.683 EUR DTN - 70.000 % ; L 0.000 EUR/DTN(01):82.628 EUR DTN - 90.000 %
Cond: L 244.260 EUR/DTN(01):0.000 EUR DTN ; L 162.840 EUR/DTN(01):73.278 EUR DTN - 30.000 % ; L 108.560 EUR/DTN(01):105.846 EUR DTN - 50.000 % ; L 67.850 EUR/DTN(01):127.558 EUR DTN - 70.000 % ; L 0.000 EUR/DTN(01):141.128 EUR DTN - 90.000 %
```

**L = EU fruit/vegetable entry price system.** Each tier shows the fixed duty
(EUR/DTN) when declared CIF falls below the threshold.

**Parse rule:** Store `entry_price_schedule JSONB`:
```json
[
  {"price_threshold_eur_per_dtn": 143.01, "condition": ">=", "duty_amount": 0.0, "reduction_pct": null},
  {"price_threshold_eur_per_dtn": 95.34, "condition": ">=", "duty_amount": 42.903, "reduction_pct": 30.0},
  {"price_threshold_eur_per_dtn": 0.0, "condition": ">=", "duty_amount": 82.628, "reduction_pct": 90.0}
]
```

---

### Category 16 — Refundable duty (R suffix on amount)

```
16.950 EUR DTN R
4.237 EUR DTN R
33.900 EUR DTN R
0.000 EUR DTN R
```

**`R` suffix = refundable.** Rate may be subject to refund/drawback.

**Parse rule:** Same as Category 2 but set `is_refundable = TRUE`.

---

### Category 17 — Monetary supplement (M suffix)

```
21.350 EUR DTN M
32.020 EUR DTN M
5.337 EUR DTN M
42.700 EUR DTN M
0.000 % + 50.700 EUR DTN M
12.500 % + 50.700 EUR DTN M
2.000 % + 6.337 EUR DTN M
8.000 % + 25.340 EUR DTN M
0.000 % + 15.210 EUR DTN M
16.000 % + 50.700 EUR DTN M
0.000 % + 35.500 EUR DTN M
25.340 EUR DTN M
6.337 EUR DTN M
50.700 EUR DTN M
0.000 EUR DTN M
```

**`M` suffix = monetary supplement.** Used for processed agricultural products.

**Parse rule:** Same as Category 2/3 but set `duty_component_type = 'monetary_supplement'`.

---

### Category 18 — Sugar supplement (Z suffix)

```
0.050 EUR DTN Z
0.200 EUR DTN Z
0.300 EUR DTN Z
0.400 EUR DTN Z
```

**`Z` suffix = sugar content additional duty per 100 kg.**

**Parse rule:** Set `duty_component_type = 'sugar_supplement'`.

---

### Category 19 — Export restitution equivalent (E suffix)

```
0.000 % + 191.000 EUR DTN E
9.600 % + 191.000 EUR DTN E
KGM E
6.100 % + 191.000 EUR DTN E
191.000 EUR DTN E
4.500 % + 143.250 EUR DTN E
14.900 % + 191.000 EUR DTN E
18.400 % + 191.000 EUR DTN E
18.400 % + 222.000 EUR DTN E
0.000 % + 222.000 EUR DTN E
222.000 EUR DTN E
0.000 % + 3.800 EUR DTN E
4.800 % + 3.800 EUR DTN E
8.300 % + 3.800 EUR DTN E
9.400 EUR DTN E
0.000 % + 9.400 EUR DTN E
1.600 % + 9.400 EUR DTN E
5.100 % + 9.400 EUR DTN E
```

**`E` suffix = export restitution-linked equivalent duty.**

**Parse rule:** Set `duty_component_type = 'export_restitution_equivalent'`.

---

### Category 20 — Informative price (I suffix)

```
172.200 EUR TNE I
237.000 EUR TNE I
```

**`I` suffix = Informative / indicative only — not a charged amount.**

**Parse rule:** Set `is_informative = TRUE`.

---

### Category 21 — MAX duty per HMT unit

```
6.500 % MAX 5.000 EUR HMT
5.400 % MAX 3.500 EUR HMT
```

**Parse rule:** Store `duty_rate` + `duty_max_amount` + `duty_max_unit = 'HMT'`.

---

### Category 22 — MAX percentage cap on combined formula

```
0.000 % + 8.900 EUR DTN MAX 12.800 %
8.300 % + 8.900 EUR DTN MAX 12.800 %
5.000 % + 8.900 EUR DTN MAX 12.800 %
0.000 % + 4.500 EUR DTN MAX 11.500 %
1.000 % + 0.562 EUR DTN MAX 1.400 %
4.100 % + 2.250 EUR DTN MAX 5.700 %
5.500 % + 3.000 EUR DTN MAX 7.600 %
0.000 % + 3.640 EUR DTN MAX 11.500 %
8.300 % + 4.500 EUR DTN MAX 11.500 %
0.000 % + 12.400 EUR DTN MAX 12.800 %
5.000 % + 12.400 EUR DTN MAX 12.800 %
0.000 % + 15.100 EUR DTN MAX 12.800 %
8.300 % + 15.100 EUR DTN MAX 12.800 %
5.000 % + 15.100 EUR DTN MAX 12.800 %
0.000 % + 17.700 EUR DTN MAX 12.800 %
8.300 % + 17.700 EUR DTN MAX 12.800 %
5.000 % + 17.700 EUR DTN MAX 12.800 %
```

**Parse rule:** Store `duty_rate`, `duty_amount`, `duty_unit_code`,
`duty_combined_max_pct`. The rule: total = min(rate%+amount, max%xCIF).

---

### Category 23 — NIHIL (zero duty)

```
NIHIL
```

**Parse rule:** `duty_rate = 0.0`, `duty_amount = NULL`. Set `is_free = TRUE`.

---

### Category 24 — Standalone unit code (supplementary declaration only)

```
NAR      MTQ C    MTQ     LTR     MWH     KPP
KSH      KPH      KPO     KNI     GRM     KFI
KSD      GFI      KUR     KNS     KMA     KMT
NPR      NCL      CTM     TJO     LPA     HLT
DTN      TNE      KGM     MIL     ASV     HMT
CCT      CEN      TCE
```

These appear alone — meaning the supplementary unit must be declared but monetary
duty is zero / not applicable.

**Parse rule:** Route to `supplementary_units` table. Set `unit_code` from value,
`duty_rate = 0`, `financial_charge = FALSE`.

---

### Category 25 — MAX duty with EA/EAR + additional components (consolidated)

Already covered under Category 7. Key patterns not repeated here.

---

### Category 26 — Quota/licence-gated rates (A-series B-conditions)

```
Cond: B cert: A-001 (28):; B (08):
Cond: B cert: A-004 (28):; B (08):
Cond: B cert: A-007 (28):; B (08):
Cond: B cert: A-019 (28):; B (08):
Cond: B cert: A-022 (28):; B (08):
```

**A-series under B-type = quota/licence access certificates.**

**Parse rule:** Store as `measure_conditions` with `condition_type = 'B'`.

---

### Category 27 — Preferential duty with trade agreement licence (Y-155)

```
Cond: B cert: Y-155 (01):50.000 % ; B (01):0.000 %
Cond: B cert: Y-155 (01):50.000 % ; B (01):7.700 %
Cond: B cert: Y-155 (01):50.000 % ; B (01):4.500 %
Cond: B cert: Y-155 (01):95.000 EUR TNE ; B (01):44.000 EUR TNE
Cond: B cert: Y-155 (01):148.000 EUR TNE ; B (01):0.000 EUR TNE
Cond: B cert: Y-155 (01):95.000 EUR TNE ; B (01):12.800 %
Cond: B cert: Y-155 (01):95.000 EUR TNE ; B (01):6.400 %
Cond: B cert: Y-155 (01):6.500 % + 40.000 EUR TNE ; B (01):0.000 % + 0.000 EUR TNE
Cond: B cert: Y-155 (01):6.500 % + 45.000 EUR TNE ; B (01):6.500 % + 0.000 EUR TNE
Cond: B cert: Y-155 (01):50.000 % ; B (01):2.000 %
Cond: B cert: Y-155 (01):50.000 % ; B (01):3.200 %
Cond: B cert: Y-155 (01):50.000 % ; B (01):10.900 %
Cond: B cert: Y-155 (01):50.000 % ; B (01):1.600 %
Cond: B cert: Y-155 (01):50.000 % ; B (01):23.000 EUR TNE
Cond: B cert: Y-155 (01):50.000 % ; B (01):55.000 EUR TNE
Cond: B cert: Y-155 (01):50.000 % ; B (01):102.000 EUR TNE
Cond: B cert: Y-155 (01):50.000 % ; B (01):12.000 %
Cond: B cert: Y-155 (01):50.000 % ; B (01):12.800 %
Cond: B cert: Y-155 (01):50.000 % ; B (01):9.600 %
```

**Y-155 = Import licence for trade policy.** First value = rate with licence;
second B(01) = fallback if no licence.

**Parse rule:** Both rates stored in `measure_conditions`:
- `duty_rate_if_met` = first value (with cert)
- `duty_rate_if_not_met` = second value (fallback)

---

### Category 28 — Anti-dumping conditions (D-series + F price undertakings)

```
Cond: A cert: D-008 (01):7.300 % ; A (01):35.600 %
Cond: A cert: D-008 (01):47.700 % ; A (01):58.200 %
Cond: A cert: D-008 (01):0.000 % ; A (01):172.200 EUR TNE I
Cond: A cert: D-025 (01):0.625 ENC ENP ; A cert: D-027 (01):0.625 ENC ENP ; A cert: D-028 (01):0.625 ENC ENP ; A (08):
Cond: A cert: D-017 (01):0.000 % ; A cert: D-018 (01):28.200 % ; A cert: D-008 (01):28.200 % ; A (01):33.400 %
Cond: A cert: D-008 (01):531.200 EUR TNE ; A (01):531.200 EUR TNE
Cond: A cert: D-008 (01):NIHIL ; A (01):32.710 EUR TNE
Cond: A cert: D-020 (28):; A (08):; F 2,043.000 EUR/TNE(01):0.000 EUR TNE ; F 1,681.480 EUR/TNE(11):2,043.000 EUR TNE ; F 0.000 EUR/TNE(01):21.500 %
Cond: A cert: D-020 (28):; A (08):; F 1,873.000 EUR/TNE(01):0.000 EUR TNE ; F 1,541.570 EUR/TNE(11):1,873.000 EUR TNE ; F 0.000 EUR/TNE(01):21.500 %
Cond: A cert: D-020 (28):; A (08):; F 1,536.000 EUR/TNE(01):0.000 EUR TNE ; F 1,105.030 EUR/TNE(11):1,536.000 EUR TNE ; F 0.000 EUR/TNE(01):39.000 %
```

**F conditions = price undertaking for anti-dumping.**
`F VALUE EUR/TNE(01)` = rate when price >= threshold (often 0%).
`F VALUE EUR/TNE(11)` = rate when price < threshold.

**ENC ENP = Encoded Number of Products units.**

**Parse rule:**
- F-conditions: store `price_undertaking_schedule JSONB`
- D-cert conditions: standard `measure_conditions` with cert codes
- `NIHIL` in A-condition = 0 duty with cert

---

### Category 29 — Multi-certificate anti-dumping + price undertaking

```
Cond: B cert: Y-321 (01):0.000 % ; B cert: Y-320 (01):2.200 % ; B cert: N-018 (01):0.000 % ; B (01):5.700 %
Cond: B cert: Y-321 (01):0.000 % ; B cert: N-018 (01):0.000 % ; B (01):2.700 %
Cond: B cert: Y-020 (01):0.000 % ; B cert: N-018 (01):0.000 % ; B (01):2.700 %
Cond: B cert: N-018 (01):0.000 % ; B (01):2.700 %
Cond: C cert: Y-500 (07):; C (27):; F 1,316.000 EUR/TNE(01):0.000 EUR TNE ; F 0.000 EUR/TNE(11):1,316.000 EUR TNE
Cond: C cert: Y-500 (07):; C (27):; F 2,408.000 EUR/TNE(01):0.000 EUR TNE ; F 0.000 EUR/TNE(11):2,408.000 EUR TNE
Cond: C cert: Y-500 (07):; C (27):; F 1,392.000 EUR/TNE(01):0.000 EUR TNE ; F 0.000 EUR/TNE(11):1,392.000 EUR TNE
Cond: C cert: Y-500 (07):; C (27):; F 3,647.000 EUR/TNE(01):0.000 EUR TNE ; F 0.000 EUR/TNE(11):3,647.000 EUR TNE
```

**Y-321, Y-320, Y-020 = origin/movement certificates.**
**N-018 = import licence.**
**C-type + Y-500 = price undertaking acceptance (both import and export side).**

**Parse rule:** Multi-cert — store each as separate `measure_conditions` row.
F-type price undertakings → store in `price_measures` with `price_undertaking_schedule`.

---

### Category 30 — Quota variable rate with N-990 (in-quota CIF schedule)

```
Cond: B cert: N-990 (27):; B (08):; V 48.100 EUR/DTN(01):2.500 % ; V 47.100 EUR/DTN(01):2.500 % ; ... ; V 0.000 EUR/DTN(01):2.500 % + 37.800 EUR DTN
Cond: B cert: N-990 (27):; B (08):; V 68.300 EUR/DTN(01):0.000 % ; ... ; V 0.000 EUR/DTN(01):0.000 % + 37.800 EUR DTN
Cond: B cert: N-990 (27):; B (08):; V 48.100 EUR/DTN(01):0.000 % ; ... ; V 0.000 EUR/DTN(01):0.000 % + 37.800 EUR DTN
```

**N-990 = quota exhaustion certificate.** V-schedule inside a quota condition
= variable rate within quota.

**Parse rule:** Combine Category 12 (variable duty) with quota certificate requirement.
Store in `tariff_quotas` with `variable_duty_schedule` populated.

---

### Category 31 — Triple duty (% + HLT + DTN — alcoholic beverages)

```
0.000 % + 39.930 EUR HLT + 6.790 EUR DTN
0.000 % + 121.000 EUR HLT + 20.600 EUR DTN
40.000 % + 121.000 EUR HLT + 20.600 EUR DTN
36.500 % + 121.000 EUR HLT + 20.600 EUR DTN
24.300 % + 80.660 EUR HLT + 13.730 EUR DTN
0.000 % + 131.000 EUR HLT + 20.600 EUR DTN
22.400 % + 131.000 EUR HLT + 20.600 EUR DTN
18.900 % + 131.000 EUR HLT + 20.600 EUR DTN
12.600 % + 87.330 EUR HLT + 13.730 EUR DTN
0.000 % + 8.910 EUR HLT + 6.790 EUR DTN
12.600 % + 18.000 EUR HLT + 13.730 EUR DTN
12.600 % + 18.000 EUR HLT
```

**Triple component: ad valorem + per hectolitre + per 100 kg.**

**Parse rule:** Store all three. `duty_component_type = 'alcohol_triple'`.

---

### Category 32 — Agricultural MAX formula with combined cap

```
0.000 % + EAR MAX 12.100 % +ADSZR
9.000 % + EA MAX 24.200 % +ADSZ
5.500 % + EA MAX 24.200 % +ADSZ
0.000 % + EAR MAX 24.200 % +ADSZR
0.000 % + EA MAX 20.700 % +ADFM
9.000 % + EA MAX 20.700 % +ADFM
5.500 % + EA MAX 20.700 % +ADFM
0.000 % + EAR MAX 10.300 % +ADSZR
0.000 % + EAR MAX 20.700 % +ADFMR
4.500 % + EAR MAX 10.300 % +ADFMR MAX 35.150 EUR DTN
```

Consolidated under Category 7 — no separate handling needed.

---

## DUTY EXPRESSION PARSING FUNCTION

Implement this comprehensive standalone module `app/duty_parser.py`:

```python
import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ParsedDuty:
    # Primary components
    duty_rate_pct: Optional[float] = None         # Ad valorem percentage
    duty_amount: Optional[float] = None           # Specific duty amount (primary)
    duty_unit: Optional[str] = None               # Unit code (DTN, TNE, KGM, etc.)
    currency: str = "EUR"

    # Secondary components (for triple duties: % + HLT + DTN)
    duty_amount_2: Optional[float] = None
    duty_unit_2: Optional[str] = None

    # Threshold constraints
    duty_min_amount: Optional[float] = None
    duty_min_unit: Optional[str] = None
    duty_min_is_gross: bool = False               # G suffix = gross weight basis
    duty_max_amount: Optional[float] = None       # Amount or percentage cap
    duty_max_unit: Optional[str] = None           # Unit code or '%'
    duty_combined_max_pct: Optional[float] = None # Cap on total combined duty as %

    # Agricultural / EA components
    has_entry_price: bool = False                 # EA component present
    entry_price_is_reduced: bool = False          # EAR (reduced rate)
    additional_duty_components: list = field(default_factory=list)  # ADSZ/ADSZR/ADFM/ADFMR

    # Supplementary alcohol duty
    duty_asv_amount: Optional[float] = None       # Per ASV%
    duty_per_unit_price: Optional[float] = None   # P suffix
    duty_tare_amount: Optional[float] = None      # T suffix

    # Special flags
    is_free: bool = False                         # NIHIL
    is_informative: bool = False                  # I suffix
    is_refundable: bool = False                   # R suffix
    is_computed_daily: bool = False               # EUC
    is_supplementary_unit_only: bool = False      # Standalone unit code

    # Variable schedules (JSONB)
    variable_duty_schedule: list = field(default_factory=list)
    entry_price_schedule: list = field(default_factory=list)
    price_undertaking_schedule: list = field(default_factory=list)
    quantity_condition_schedule: list = field(default_factory=list)
    size_condition_schedule: list = field(default_factory=list)

    # Component type classification
    duty_component_type: Optional[str] = None
    # Values: 'standard', 'monetary_supplement', 'sugar_supplement',
    # 'export_restitution_equivalent', 'alcohol_triple', 'entry_price',
    # 'computed_unit_price'

    # Raw string — always preserved for auditability
    raw_expression: str = ""


# Unit codes that appear ALONE meaning "declare this unit, no monetary duty"
STANDALONE_UNIT_CODES = {
    "NAR", "MTQ", "MTK", "MTR", "MWH", "KPP", "KSH", "KPH", "KPO",
    "KNI", "GRM", "KFI", "KSD", "GFI", "KUR", "KNS", "KMA", "KMT",
    "NPR", "NCL", "CTM", "TJO", "LTR", "LPA", "HLT", "DTN", "TNE",
    "KGM", "MIL", "ASV", "HMT", "CCT", "CEN", "TCE", "MTQ C",
}


def _parse_float(s: str) -> Optional[float]:
    """Parse a float, handling European thousands separators."""
    try:
        return float(s.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def parse_duty_expression(raw: str) -> ParsedDuty:
    """
    Parse ANY TARIC duty expression string into a structured ParsedDuty object.
    Handles all 32 documented categories. Never raises — always returns ParsedDuty.
    """
    if not raw or not raw.strip():
        return ParsedDuty(raw_expression=raw or "")

    result = ParsedDuty(raw_expression=raw)
    s = raw.strip()

    # ── Category 23: NIHIL ─────────────────────────────────────────────────
    if s.upper() == "NIHIL":
        result.is_free = True
        result.duty_rate_pct = 0.0
        result.duty_component_type = "standard"
        return result

    # ── Category 24: Standalone unit codes ────────────────────────────────
    upper_s = s.upper().rstrip(" C").strip()
    if upper_s in STANDALONE_UNIT_CODES or s.upper() in STANDALONE_UNIT_CODES:
        result.is_supplementary_unit_only = True
        result.duty_unit = s.upper()
        result.duty_rate_pct = 0.0
        return result

    # ── Strip and detect suffix flags ──────────────────────────────────────
    working = s

    # M suffix (monetary supplement) — strip before parsing
    if re.search(r'\b(DTN|TNE|KGM|NAR)\s+M\b', working):
        result.duty_component_type = "monetary_supplement"
        working = re.sub(r'\b(DTN|TNE|KGM|NAR)\s+M\b', r'\1', working)

    # Z suffix (sugar supplement)
    if re.search(r'\bDTN\s+Z\b', working):
        result.duty_component_type = "sugar_supplement"
        working = re.sub(r'\bDTN\s+Z\b', 'DTN', working)

    # E suffix (export restitution equivalent)
    if re.search(r'\b(DTN|TNE|KGM)\s+E\b', working):
        result.duty_component_type = "export_restitution_equivalent"
        working = re.sub(r'\b(DTN|TNE|KGM)\s+E\b', r'\1', working)
    # "KGM E" alone
    if working.strip().upper() == "KGM E":
        result.duty_component_type = "export_restitution_equivalent"
        result.is_supplementary_unit_only = True
        result.duty_unit = "KGM"
        return result

    # R suffix on amounts (refundable) — only when on amount, not standalone R
    if re.search(r'\b(DTN|TNE|KGM)\s+R\b', working):
        result.is_refundable = True
        working = re.sub(r'\b(DTN|TNE|KGM)\s+R\b', r'\1', working)

    # I suffix (informative)
    if working.rstrip().endswith(" I") and not working.strip().endswith("EUR"):
        result.is_informative = True
        working = working.rstrip()[:-2].strip()

    if result.duty_component_type is None:
        result.duty_component_type = "standard"

    # ── Category 7/25/32: Entry price (EA/EAR) ─────────────────────────────
    if re.search(r'\bEAR?\b', working):
        result.has_entry_price = True
        result.entry_price_is_reduced = bool(re.search(r'\bEAR\b', working))
        result.duty_component_type = "entry_price"

        # Base rate
        rate_m = re.match(r'^(\d+\.\d+)\s*%', working)
        if rate_m:
            result.duty_rate_pct = _parse_float(rate_m.group(1))

        # Additional duty components
        for comp in ["ADSZR", "ADSZ", "ADFMR", "ADFM"]:
            if comp in working:
                result.additional_duty_components.append(comp)

        # MAX cap — can be % or EUR amount
        max_pct_m = re.search(r'MAX\s+(\d+[\.,]\d+)\s*%', working)
        max_eur_m = re.search(r'MAX\s+(\d+[\.,]\d+)\s+EUR\s+(\w+)', working)
        if max_pct_m:
            result.duty_max_amount = _parse_float(max_pct_m.group(1))
            result.duty_max_unit = '%'
        if max_eur_m:
            result.duty_max_amount = _parse_float(max_eur_m.group(1))
            result.duty_max_unit = max_eur_m.group(2)

        return result

    # ── Category 9: ASV (alcohol by volume) ────────────────────────────────
    asv_m = re.search(r'(\d+\.\d+)\s+EUR\s+ASV\s+X', working)
    if asv_m:
        result.duty_asv_amount = _parse_float(asv_m.group(1))
        hlt_m = re.search(r'\+\s*(\d+\.\d+)\s+EUR\s+(HLT)', working)
        if hlt_m:
            result.duty_amount = _parse_float(hlt_m.group(1))
            result.duty_unit = hlt_m.group(2)
        return result

    # ── Category 31: Triple duty (% + HLT + DTN) ───────────────────────────
    triple_m = re.match(
        r'^(\d+\.\d+)\s*%\s*\+\s*([\d,]+\.\d+)\s+EUR\s+(HLT)\s*\+\s*([\d,]+\.\d+)\s+EUR\s+(DTN)',
        working
    )
    if triple_m:
        result.duty_rate_pct = _parse_float(triple_m.group(1))
        result.duty_amount = _parse_float(triple_m.group(2))
        result.duty_unit = triple_m.group(3)
        result.duty_amount_2 = _parse_float(triple_m.group(4))
        result.duty_unit_2 = triple_m.group(5)
        result.duty_component_type = "alcohol_triple"
        return result

    # ── Extract MIN/MAX clauses before main parsing ─────────────────────────
    min_m = re.search(r'MIN\s+([\d,]+\.?\d*)\s+EUR\s+(\w+)(\s+G)?', working)
    if min_m:
        result.duty_min_amount = _parse_float(min_m.group(1))
        result.duty_min_unit = min_m.group(2)
        result.duty_min_is_gross = bool(min_m.group(3))
        working = working[:min_m.start()].strip()

    max_m = re.search(r'MAX\s+([\d,]+\.?\d*)\s+(EUR\s+(\w+)|%)', working)
    if max_m:
        result.duty_max_amount = _parse_float(max_m.group(1))
        if '%' in max_m.group(2):
            result.duty_max_unit = '%'
        else:
            result.duty_max_unit = max_m.group(3)
        working = re.sub(r'\s*MAX\s+[\d,\.]+\s+(?:EUR\s+\w+|%)[^;]*', '', working).strip()

    # Combined max formula with percentage after MAX (Category 22)
    max_pct_m = re.search(r'MAX\s+([\d,]+\.?\d*)\s*%', working)
    if max_pct_m and not result.duty_max_unit:
        result.duty_combined_max_pct = _parse_float(max_pct_m.group(1))
        working = re.sub(r'\s*MAX\s+[\d,\.]+\s*%[^;]*', '', working).strip()

    # ── Category 10: P suffix (per supplementary unit price) ───────────────
    p_m = re.search(r'([\d,]+\.\d+)\s+EUR\s+(\w+)\s+P\b', working)
    if p_m:
        result.duty_per_unit_price = _parse_float(p_m.group(1))
        result.duty_unit = p_m.group(2) + "_P"
        dtn_m = re.search(r'\+\s*([\d,]+\.\d+)\s+EUR\s+(DTN)', working)
        if dtn_m:
            result.duty_amount = _parse_float(dtn_m.group(1))
            result.duty_unit = dtn_m.group(2)
        return result

    # ── Category 11: T suffix (tare weight) ────────────────────────────────
    t_m = re.search(r'([\d,]+\.\d+)\s+EUR\s+(\w+)\s+T\b', working)
    if t_m:
        result.duty_tare_amount = _parse_float(t_m.group(1))
        dtn_m = re.search(r'\+\s*([\d,]+\.\d+)\s+EUR\s+(DTN)', working)
        if dtn_m:
            result.duty_amount = _parse_float(dtn_m.group(1))
            result.duty_unit = dtn_m.group(2)
        return result

    # ── Category 8: EUC (computed unit price) ──────────────────────────────
    euc_m = re.match(r'^([\d,]+\.\d+)\s+EUC\s+DTN$', working)
    if euc_m:
        result.duty_amount = _parse_float(euc_m.group(1))
        result.duty_unit = "EUC_DTN"
        result.is_computed_daily = True
        result.duty_component_type = "computed_unit_price"
        return result

    # ── Category 3/29: Mixed (% + EUR UNIT) ────────────────────────────────
    mixed_m = re.match(
        r'^(\d+\.\d+)\s*%\s*\+\s*([\d,]+\.\d+)\s+EUR\s+(\w+)$', working
    )
    if mixed_m:
        result.duty_rate_pct = _parse_float(mixed_m.group(1))
        result.duty_amount = _parse_float(mixed_m.group(2))
        result.duty_unit = mixed_m.group(3)
        return result

    # ── Category 2: Specific duty (EUR UNIT) ───────────────────────────────
    specific_m = re.match(r'^([\d,]+\.\d+)\s+EUR\s+(\w+)$', working)
    if specific_m:
        result.duty_amount = _parse_float(specific_m.group(1))
        result.duty_unit = specific_m.group(2)
        return result

    # ── Category 1: Ad valorem (%) ──────────────────────────────────────────
    pct_m = re.match(r'^(\d+\.\d+)\s*%$', working)
    if pct_m:
        result.duty_rate_pct = _parse_float(pct_m.group(1))
        return result

    # ── Fallback: log and preserve raw ─────────────────────────────────────
    logger.warning(f"Unrecognised duty expression: {raw!r}")
    return result
```

---

## CONDITION TYPE CATALOGUE (COMPLETE)

| Code | Name | Logic | Description |
|------|------|-------|-------------|
| A | Certificate to GET rate | ALL_REQUIRED | All listed A-certs must be presented to receive the stated rate. Missing any = fallback rate. |
| B | Authorisation / Licence required | ALL_REQUIRED | Import/export authorisation, end-use approval, quota licence. All must be held. |
| C | Combined certificate (import + export) | ALL_REQUIRED | Certificate required both at export AND import country level. |
| E | Export licence required | ALL_REQUIRED | Export licence from exporting country must accompany goods. |
| F | Price undertaking condition | PRICE_SCHEDULE | Anti-dumping price undertaking. Rate = 0 if price >= minimum; otherwise full ADD. |
| H | Statistical document | INFORMATIONAL | No gate — document must be presented but does not affect rate. |
| I | Informational certificate | INFORMATIONAL | Shown for information only; does not gate duty. |
| J | Net weight per piece | QUANTITY_THRESHOLD | Rate depends on net weight per piece within threshold range. |
| L | Price-based admission | PRICE_SCHEDULE | Rate depends on declared CIF price vs price schedule thresholds. |
| M | Weight/quantity threshold | QUANTITY_THRESHOLD | Rate depends on quantity/weight threshold. |
| R | Weight/price ratio range | RANGE_THRESHOLD | Rate depends on weight or price per unit in specified range. |
| U | Price per supplementary unit | UNIT_PRICE_THRESHOLD | Rate depends on declared price per supplementary unit. |
| V | Variable duty by CIF price | PRICE_SCHEDULE | Full graduated rate schedule based on declared CIF price per unit. |
| X | Volume per vessel/container | QUANTITY_THRESHOLD | Rate depends on volume per container. |
| Y | Certificate to be EXEMPT | ANY_SUFFICIENT | ANY ONE certificate exempts from measure. Absence = fallback applies. |
| Z | Erga omnes | GEOGRAPHIC | Applies regardless of origin. |

---

## DATABASE SCHEMA (COMPLETE — ALL COLUMNS)

```sql
-- Commodity codes master table
CREATE TABLE commodity_codes (
    id              SERIAL PRIMARY KEY,
    hs_code         VARCHAR(12) NOT NULL,
    market          VARCHAR(2) NOT NULL,        -- 'EU' or 'GB'
    description     TEXT,
    parent_code     VARCHAR(12),
    last_updated    TIMESTAMP DEFAULT NOW(),
    UNIQUE (hs_code, market)
);

-- Duty / tariff measures
CREATE TABLE duty_rates (
    id                          SERIAL PRIMARY KEY,
    hs_code                     VARCHAR(12) NOT NULL,
    market                      VARCHAR(2) NOT NULL,
    origin_country              VARCHAR(2),
    rate_type                   VARCHAR(30) NOT NULL,
    -- Ad valorem
    duty_rate                   NUMERIC(10,4),
    -- Specific duty (primary)
    duty_amount                 NUMERIC(14,4),
    duty_unit                   VARCHAR(20),
    -- Specific duty (secondary — for triple duties HLT + DTN)
    duty_amount_2               NUMERIC(14,4),
    duty_unit_2                 VARCHAR(20),
    -- Currency
    currency                    VARCHAR(3) DEFAULT 'EUR',
    -- Threshold constraints
    duty_min_amount             NUMERIC(14,4),
    duty_min_unit               VARCHAR(20),
    duty_min_is_gross           BOOLEAN DEFAULT FALSE,
    duty_max_amount             NUMERIC(14,4),
    duty_max_unit               VARCHAR(20),        -- unit code OR '%'
    duty_combined_max_pct       NUMERIC(8,4),       -- cap as % of CIF value
    -- Agricultural / entry price flags
    has_entry_price             BOOLEAN DEFAULT FALSE,
    entry_price_is_reduced      BOOLEAN DEFAULT FALSE,
    additional_duty_components  JSONB,              -- ['ADSZ','ADSZR','ADFM','ADFMR']
    -- Supplementary duty components
    duty_asv_amount             NUMERIC(10,4),      -- per ASV%
    duty_per_unit_price         NUMERIC(14,4),      -- P suffix
    duty_tare_amount            NUMERIC(14,4),      -- T suffix
    -- Variable schedules (JSONB arrays)
    variable_duty_schedule      JSONB,              -- V-condition price schedule
    entry_price_schedule        JSONB,              -- L-condition price schedule
    price_undertaking_schedule  JSONB,              -- F-condition anti-dumping
    quantity_condition_schedule JSONB,              -- R-condition weight/quantity
    size_condition_schedule     JSONB,              -- J/X/U condition schedules
    -- Flags
    is_free                     BOOLEAN DEFAULT FALSE,
    is_informative              BOOLEAN DEFAULT FALSE,
    is_refundable               BOOLEAN DEFAULT FALSE,
    is_computed_daily           BOOLEAN DEFAULT FALSE,
    -- Component type
    duty_component_type         VARCHAR(40),
    -- Raw expression for auditability
    duty_expression_raw         TEXT,
    -- Metadata
    trade_agreement             VARCHAR(100),
    valid_from                  DATE,
    valid_to                    DATE,
    financial_charge            BOOLEAN DEFAULT TRUE,
    source                      VARCHAR(20),
    measure_sid                 VARCHAR(20),
    raw_json                    JSONB,
    last_updated                TIMESTAMP DEFAULT NOW(),
    UNIQUE (hs_code, market, origin_country, rate_type, measure_sid)
);

-- Measure conditions
CREATE TABLE measure_conditions (
    id                          SERIAL PRIMARY KEY,
    duty_rate_id                INTEGER REFERENCES duty_rates(id) ON DELETE CASCADE,
    measure_id                  INTEGER REFERENCES non_tariff_measures(id) ON DELETE CASCADE,
    condition_type              VARCHAR(2) NOT NULL,
    condition_logic             VARCHAR(30) NOT NULL,
        -- 'ALL_REQUIRED', 'ANY_SUFFICIENT', 'PRICE_SCHEDULE',
        -- 'QUANTITY_THRESHOLD', 'RANGE_THRESHOLD', 'UNIT_PRICE_THRESHOLD',
        -- 'GEOGRAPHIC', 'INFORMATIONAL', 'UNKNOWN'
    certificate_code            VARCHAR(20),
    duty_expression_code        VARCHAR(4),
    -- Conditional rates
    duty_rate_if_met            NUMERIC(10,4),
    duty_rate_if_not_met        NUMERIC(10,4),
    duty_amount_if_met          NUMERIC(14,4),
    duty_unit_if_met            VARCHAR(20),
    duty_amount_if_not_met      NUMERIC(14,4),
    duty_unit_if_not_met        VARCHAR(20),
    -- For V/L/F/R/J/X/U conditions
    condition_schedule          JSONB,
    -- Thresholds (R/J/X/U)
    threshold_value             NUMERIC(14,4),
    threshold_unit              VARCHAR(20),
    threshold_applies_code      VARCHAR(4),         -- '10'=above, '28'=below
    action_code                 VARCHAR(10),
    sequence_number             INTEGER,
    last_updated                TIMESTAMP DEFAULT NOW()
);

-- Non-tariff measures
CREATE TABLE non_tariff_measures (
    id                      SERIAL PRIMARY KEY,
    hs_code                 VARCHAR(12) NOT NULL,
    market                  VARCHAR(2) NOT NULL,
    origin_country          VARCHAR(2),
    measure_type_id         VARCHAR(10) NOT NULL,
    measure_type_description TEXT,
    geographical_area       VARCHAR(10),
    financial_charge        BOOLEAN DEFAULT FALSE,
    valid_from              DATE,
    valid_to                DATE,
    source                  VARCHAR(20),
    measure_sid             VARCHAR(20),
    raw_json                JSONB,
    last_updated            TIMESTAMP DEFAULT NOW(),
    UNIQUE (hs_code, market, measure_type_id, measure_sid)
);

-- Certificate code reference table
CREATE TABLE certificate_codes (
    code                    VARCHAR(20) PRIMARY KEY,
    description             TEXT NOT NULL,
    category                VARCHAR(40),
        -- 'origin', 'licence', 'exemption', 'sanitary', 'statistical',
        -- 'anti_dumping', 'quota', 'end_use', 'movement', 'price_undertaking',
        -- 'cites', 'fisheries', 'chemical', 'nuclear', 'organic'
    last_updated            TIMESTAMP DEFAULT NOW()
);

-- VAT rates per country
CREATE TABLE vat_rates (
    id                      SERIAL PRIMARY KEY,
    country_code            VARCHAR(2) NOT NULL,
    market                  VARCHAR(2) NOT NULL,
    rate_type               VARCHAR(20) NOT NULL,
    vat_rate                NUMERIC(6,3) NOT NULL,
    hs_code_prefix          VARCHAR(6),
    valid_from              DATE,
    source                  VARCHAR(30),
    last_updated            TIMESTAMP DEFAULT NOW(),
    UNIQUE (country_code, market, rate_type, hs_code_prefix)
);

-- Tariff quotas
CREATE TABLE tariff_quotas (
    id                      SERIAL PRIMARY KEY,
    hs_code                 VARCHAR(12) NOT NULL,
    market                  VARCHAR(2) NOT NULL,
    origin_country          VARCHAR(2),
    quota_order_number      VARCHAR(20),
    quota_type              VARCHAR(40) NOT NULL,
    quota_type_detail       VARCHAR(80),
    customs_union_code      VARCHAR(10),
    duty_rate               NUMERIC(10,4),
    duty_amount             NUMERIC(14,4),
    duty_unit               VARCHAR(20),
    currency                VARCHAR(3) DEFAULT 'EUR',
    trade_agreement         VARCHAR(100),
    end_use_required        BOOLEAN DEFAULT FALSE,
    variable_duty_schedule  JSONB,          -- V-schedule within quota
    valid_from              DATE,
    valid_to                DATE,
    source                  VARCHAR(20),
    measure_sid             VARCHAR(20),
    raw_json                JSONB,
    last_updated            TIMESTAMP DEFAULT NOW(),
    UNIQUE (hs_code, market, quota_order_number, measure_sid)
);

-- Supplementary units and legal declaration requirements
CREATE TABLE supplementary_units (
    id                      SERIAL PRIMARY KEY,
    hs_code                 VARCHAR(12) NOT NULL,
    market                  VARCHAR(2) NOT NULL,
    unit_code               VARCHAR(20),
    unit_description        TEXT,
    declaration_type        VARCHAR(60),
    legal_note              TEXT,
    valid_from              DATE,
    valid_to                DATE,
    source                  VARCHAR(20),
    measure_sid             VARCHAR(20),
    last_updated            TIMESTAMP DEFAULT NOW(),
    UNIQUE (hs_code, market, unit_code, measure_sid)
);

-- Price-based measures (agricultural / trade defence)
CREATE TABLE price_measures (
    id                          SERIAL PRIMARY KEY,
    hs_code                     VARCHAR(12) NOT NULL,
    market                      VARCHAR(2) NOT NULL,
    origin_country              VARCHAR(2),
    measure_type_id             VARCHAR(10) NOT NULL,
    measure_type_description    TEXT NOT NULL,
    representative_price        NUMERIC(14,4),
    unit_price                  NUMERIC(14,4),
    standard_import_value       NUMERIC(14,4),
    security_amount             NUMERIC(14,4),
    price_undertaking_schedule  JSONB,
    currency                    VARCHAR(3) DEFAULT 'EUR',
    unit_qualifier              VARCHAR(20),
    financial_charge            BOOLEAN DEFAULT TRUE,
    valid_from                  DATE,
    valid_to                    DATE,
    source                      VARCHAR(20),
    measure_sid                 VARCHAR(20),
    raw_json                    JSONB,
    last_updated                TIMESTAMP DEFAULT NOW(),
    UNIQUE (hs_code, market, measure_type_id, measure_sid)
);

-- Pipeline run log
CREATE TABLE pipeline_runs (
    id                      SERIAL PRIMARY KEY,
    source                  VARCHAR(30) NOT NULL,
    status                  VARCHAR(10) NOT NULL,   -- 'running','success','failed','partial'
    records_fetched         INTEGER,
    records_upserted        INTEGER,
    error_message           TEXT,
    started_at              TIMESTAMP,
    finished_at             TIMESTAMP
);

-- Config / flags table (prevents accidental re-bootstrap)
CREATE TABLE pipeline_config (
    key                     VARCHAR(50) PRIMARY KEY,
    value                   TEXT,
    updated_at              TIMESTAMP DEFAULT NOW()
);
```

**Indexes:**
```sql
CREATE INDEX idx_duty_rates_lookup      ON duty_rates (hs_code, market, origin_country);
CREATE INDEX idx_duty_rates_variable    ON duty_rates (hs_code, market) WHERE variable_duty_schedule IS NOT NULL;
CREATE INDEX idx_duty_rates_ea          ON duty_rates (hs_code, market) WHERE has_entry_price = TRUE;
CREATE INDEX idx_quota_lookup           ON tariff_quotas (hs_code, market, origin_country);
CREATE INDEX idx_price_lookup           ON price_measures (hs_code, market);
CREATE INDEX idx_ntm_lookup             ON non_tariff_measures (hs_code, market);
CREATE INDEX idx_su_lookup              ON supplementary_units (hs_code, market);
CREATE INDEX idx_conditions_duty        ON measure_conditions (duty_rate_id);
CREATE INDEX idx_conditions_ntm         ON measure_conditions (measure_id);
```

---

## MEASURE TYPE CLASSIFICATION (COMPLETE)

### GROUP 1 - duty_rates

```python
DUTY_RATE_MEASURE_TYPES = {
    "103": "MFN",
    "105": "MFN (processing)",
    "106": "customs union",
    "107": "customs union (end-use)",
    "112": "suspension",
    "115": "suspension (end-use)",
    "142": "preferential",
    "145": "preferential (end-use)",
    "305": "VAT",           # route to vat_rates instead
    "551": "anti-dumping",
    "552": "anti-dumping (provisional)",
    "553": "anti-dumping (registration)",
    "554": "countervailing",
    "555": "countervailing (provisional)",
    "556": "countervailing (registration)",
    "695": "safeguard",
}
```

### GROUP 2 - tariff_quotas

```python
QUOTA_MEASURE_TYPES = {
    "122": "non-preferential quota",
    "123": "non-preferential quota",
    "124": "non-preferential quota",
    "125": "non-preferential quota under end-use",
    "126": "non-preferential quota under end-use",
    "132": "customs union quota",
    "133": "customs union quota",
    "143": "preferential quota",
    "144": "preferential quota",
    "145": "preferential quota",
    "146": "preferential quota",
    "147": "preferential quota",
    "148": "preferential quota under end-use",
    "696": "security quota (representative price)",
    "697": "additional duty quota (CIF price)",
}
```

### GROUP 3 - price_measures

```python
PRICE_MEASURE_TYPES = {
    "488": "representative price",
    "489": "security (representative price)",
    "490": "additional duty (CIF price)",
    "491": "standard import value",
    "492": "unit price",
    "557": "anti-dumping (pending collection)",
    "558": "anti-dumping/cv (control)",
    "559": "anti-dumping/cv (statistic)",
    "560": "anti-dumping/cv (review)",
    "561": "anti-dumping/cv (registration)",
    "562": "anti-dumping/cv (notice)",
}
```

### GROUP 4 - non_tariff_measures

```python
NON_TARIFF_MEASURE_TYPES = {
    "277": "import prohibition",
    "278": "import prohibition (torture goods)",
    "279": "restriction on entry into free circulation",
    "280": "entry into free circulation (quantitative limitation)",
    "281": "entry into free circulation (feed and food)",
    "410": "import control",
    "411": "import control",
    "420": "import control (organic products)",
    "421": "import control (organic products)",
    "430": "import control (luxury goods)",
    "431": "import control (luxury goods)",
    "465": "official control (plants)",
    "466": "phytosanitary control",
    "473": "veterinary control",
    "474": "veterinary control",
    "483": "import control (CITES)",
    "484": "import control (CITES)",
    "485": "import control (seal products)",
    "486": "import control (cat and dog fur)",
    "487": "import control (IAS)",
    "493": "import control (F-gases)",
    "494": "import control (ODS)",
    "495": "import control (POP)",
    "496": "import control (FLEGT)",
    "497": "import control (FLEGT-Ghana)",
    "498": "CBAM",
    "499": "import control (cultural goods)",
    "500": "import/export restriction (CML)",
    "501": "compliance (pre-export checks)",
}
```

**Collision resolution** — IDs 488-492 appear in both price_measures AND
non_tariff_measures. Resolve by description keyword:

```python
DESCRIPTION_OVERRIDES = {
    "representative price":         "price_measures",
    "standard import value":        "price_measures",
    "unit price":                   "price_measures",
    "security based on":            "price_measures",
    "additional duty based on cif": "price_measures",
    "pending collection":           "price_measures",
    "waste":                        "non_tariff_measures",
    "gmo":                          "non_tariff_measures",
    "reach":                        "non_tariff_measures",
    "mercury":                      "non_tariff_measures",
    "iuu":                          "non_tariff_measures",
    "invasive alien":               "non_tariff_measures",
}
```

### GROUP 5 - supplementary_units

```python
SUPPLEMENTARY_UNIT_MEASURE_TYPES = {
    "109": "supplementary unit",
    "110": "supplementary unit import",
    "111": "supplementary unit",
    "500": "declaration (legal restrictions - net weight/supplementary unit)",
    "501": "declaration (legal restrictions - declared net mass)",
    "502": "declaration (physical restrictions - net weight/supplementary unit)",
    "503": "declaration (legal restrictions - unit price)",
    "504": "declaration (legal restrictions - declared supplementary unit)",
    "505": "declaration (restrictions - import)",
    "506": "declaration (end-use provisions)",
}
```

### Routing decision function

```python
def route_measure(
    measure_type_id: str,
    measure_description: str,
    has_quota_order_number: bool,
) -> str:
    if measure_type_id == "305":
        return "vat_rates"
    if measure_type_id in SUPPLEMENTARY_UNIT_MEASURE_TYPES:
        return "supplementary_units"
    if measure_type_id in QUOTA_MEASURE_TYPES and has_quota_order_number:
        return "tariff_quotas"
    desc_lower = measure_description.lower()
    for keyword, destination in DESCRIPTION_OVERRIDES.items():
        if keyword in desc_lower:
            return destination
    if measure_type_id in PRICE_MEASURE_TYPES:
        return "price_measures"
    if measure_type_id in NON_TARIFF_MEASURE_TYPES:
        return "non_tariff_measures"
    if measure_type_id in DUTY_RATE_MEASURE_TYPES:
        return "duty_rates"
    import logging
    logging.warning(
        f"Unknown measure_type_id={measure_type_id!r} "
        f"description={measure_description!r} — skipped"
    )
    return "unknown"
```

---

## CERTIFICATE CODE REFERENCE (EXTENDED)

Seed `certificate_codes` with ALL codes encountered in TARIC conditions.

### A-series (Quota access / anti-dumping)
A-001, A-004, A-007, A-019, A-022

### C-series (Customs authorisation / combined conditions)
C-001, C-014, C-015, C-017, C-018, C-039, C-040, C-041, C-042, C-043,
C-045, C-046, C-047, C-050, C-055, C-056, C-057, C-058, C-060, C-064,
C-065, C-066, C-067, C-071, C-073, C-079, C-080, C-081, C-082, C-083,
C-084, C-085, C-091, C-092, C-101, C-121, C-126, C-400, C-630, C-631,
C-640, C-641, C-650, C-652, C-666, C-667, C-668, C-669, C-670, C-672,
C-673, C-676, C-678, C-679, C-680, C-683, C-690, C-701, C-809

### D-series (Origin / anti-dumping)
D-008 (GSP Form A), D-017, D-018 (EUR.1), D-019 (EUR-MED), D-020,
D-023, D-024, D-025, D-027, D-028, D-029

### K-series (FTA preferential origin)
K-020, K-022, K-025, K-027, K-028, K-029, K-030, K-031, K-032,
K-520, K-521, K-522, K-523, K-524, K-525, K-526, K-527

### L-series (Legal / documentary proofs)
L-001, L-049, L-050, L-065, L-079, L-100, L-116, L-128, L-129,
L-137, L-138, L-139, L-142, L-143, L-146, L-147, L-148, L-149,
L-150, L-151, L-152, L-153, L-155, L-156, L-157

### N-series (Licences / notifications)
N-002, N-018, N-853, N-851, N-854, N-990

### U-series (REX / Registered exporter)
U-004, U-045, U-078, U-079, U-088

### Y-series (Exemption / exclusion declarations)
Y-019, Y-020, Y-032, Y-033, Y-036, Y-038, Y-046, Y-054, Y-057,
Y-058, Y-059, Y-062, Y-063, Y-069, Y-070, Y-072 through Y-079,
Y-080, Y-084, Y-085, Y-086 through Y-091, Y-104, Y-105, Y-106,
Y-109, Y-110, Y-111, Y-112, Y-113, Y-115, Y-116, Y-120, Y-121,
Y-122, Y-123, Y-125, Y-127, Y-128, Y-134, Y-135, Y-136, Y-137,
Y-138, Y-146, Y-151, Y-152, Y-154, Y-155, Y-160, Y-162, Y-163,
Y-166, Y-167, Y-169, Y-170 through Y-177, Y-178, Y-179, Y-182,
Y-185, Y-186, Y-199, Y-235, Y-237, Y-238, Y-239, Y-240, Y-241,
Y-242, Y-250, Y-251, Y-257, Y-319, Y-320, Y-321, Y-323, Y-500,
Y-686, Y-687, Y-692, Y-693, Y-694, Y-695, Y-699, Y-704, Y-705,
Y-709, Y-710, Y-711, Y-712, Y-713, Y-715, Y-727, Y-728, Y-729,
Y-731, Y-732, Y-733, Y-734, Y-738, Y-739, Y-740, Y-747, Y-749,
Y-750, Y-756, Y-757, Y-758, Y-759, Y-769, Y-784, Y-786 through Y-799,
Y-824, Y-835, Y-840 through Y-845, Y-854, Y-855, Y-859, Y-864,
Y-870, Y-872, Y-873, Y-874, Y-875, Y-877, Y-878, Y-879, Y-882,
Y-889, Y-897, Y-904, Y-910, Y-920, Y-921, Y-922, Y-923, Y-924,
Y-927, Y-930, Y-931, Y-937, Y-942, Y-944, Y-945, Y-946, Y-948,
Y-949, Y-955, Y-957, Y-958, Y-959, Y-960, Y-961, Y-962, Y-963,
Y-964, Y-965, Y-966, Y-969, Y-970, Y-971, Y-972, Y-978, Y-979,
Y-980, Y-981, Y-984, Y-986, Y-997

Unknown codes encountered during parsing: INSERT with `description = "Unknown — code {code}"`.

---

## PARSING MEASURE CONDITIONS (COMPLETE)

### From TARIC XML

```python
CONDITION_LOGIC_MAP = {
    "A": "ALL_REQUIRED",
    "B": "ALL_REQUIRED",
    "C": "ALL_REQUIRED",
    "E": "ALL_REQUIRED",
    "F": "PRICE_SCHEDULE",
    "H": "INFORMATIONAL",
    "I": "INFORMATIONAL",
    "J": "QUANTITY_THRESHOLD",
    "L": "PRICE_SCHEDULE",
    "M": "QUANTITY_THRESHOLD",
    "R": "RANGE_THRESHOLD",
    "U": "UNIT_PRICE_THRESHOLD",
    "V": "PRICE_SCHEDULE",
    "X": "QUANTITY_THRESHOLD",
    "Y": "ANY_SUFFICIENT",
    "Z": "GEOGRAPHIC",
}


def parse_conditions(measure_element, tag) -> list[dict]:
    """Parse ALL condition types from a TARIC XML MEASURE element."""
    conditions = []
    for i, cond in enumerate(measure_element.findall(tag("MEASURE.CONDITION"))):
        cond_code = (cond.findtext(tag("CONDITION.CODE")) or "").strip()
        cert_type = (cond.findtext(tag("CERTIFICATE.TYPE.CODE")) or "").strip()
        cert_code_raw = (cond.findtext(tag("CERTIFICATE.CODE")) or "").strip()
        certificate = (
            f"{cert_type}-{cert_code_raw}".strip("-")
            if (cert_type or cert_code_raw)
            else None
        )
        expr_id = (cond.findtext(tag("DUTY.EXPRESSION.ID")) or "").strip()
        amount_str = cond.findtext(tag("MEASURE.CONDITION.DUTY.AMOUNT")) or ""
        monetary_unit = (cond.findtext(tag("MONETARY.UNIT.CODE")) or "").strip() or None
        measurement_unit = (cond.findtext(tag("MEASUREMENT.UNIT.CODE")) or "").strip() or None

        logic = CONDITION_LOGIC_MAP.get(cond_code, "UNKNOWN")

        duty_amount = None
        if amount_str:
            try:
                duty_amount = float(amount_str.replace(",", ""))
            except ValueError:
                pass

        condition = {
            "condition_type": cond_code,
            "condition_logic": logic,
            "certificate_code": certificate,
            "duty_expression_code": expr_id,
            "duty_amount": duty_amount,
            "monetary_unit": monetary_unit,
            "measurement_unit": measurement_unit,
            "sequence_number": i,
            "threshold_value": duty_amount if cond_code in "VRLJMXU" else None,
            "threshold_unit": measurement_unit or monetary_unit if cond_code in "VRLJMXU" else None,
            "threshold_applies_code": expr_id if cond_code in "VRLJMXU" else None,
        }

        # Separate if_met vs if_not_met for A and B conditions
        if cond_code in ("A", "B"):
            if certificate:
                condition["duty_rate_if_met"] = duty_amount
                condition["duty_rate_if_not_met"] = None
            else:
                condition["duty_rate_if_met"] = None
                condition["duty_rate_if_not_met"] = duty_amount

        conditions.append(condition)

    return conditions
```

### From UK Trade Tariff API

```python
def parse_uk_conditions(measure_data: dict, included: list) -> list[dict]:
    """Parse measure conditions from UK API included array."""
    condition_ids = [
        r["id"] for r in
        measure_data.get("relationships", {})
                    .get("measure_conditions", {})
                    .get("data", [])
    ]
    conditions = []
    for i, cid in enumerate(condition_ids):
        cond_obj = next(
            (x for x in included if x["type"] == "measure_condition" and x["id"] == cid),
            None
        )
        if not cond_obj:
            continue
        attrs = cond_obj["attributes"]
        cond_code = attrs.get("condition_code", "")
        cert_code = attrs.get("document_code")
        duty_str = attrs.get("duty_expression") or ""
        action_code = attrs.get("action_code")

        parsed = parse_duty_expression(duty_str) if duty_str.strip() else None
        duty_rate = parsed.duty_rate_pct if parsed else None
        duty_amount = parsed.duty_amount if parsed else None
        duty_unit = parsed.duty_unit if parsed else None

        logic = CONDITION_LOGIC_MAP.get(cond_code, "UNKNOWN")

        conditions.append({
            "condition_type": cond_code,
            "condition_logic": logic,
            "certificate_code": cert_code,
            "duty_expression_code": "01" if duty_rate else ("02" if duty_amount else "29"),
            "duty_rate_if_met": duty_rate if cert_code else None,
            "duty_rate_if_not_met": duty_rate if not cert_code else None,
            "duty_amount_if_met": duty_amount if cert_code else None,
            "duty_amount_if_not_met": duty_amount if not cert_code else None,
            "duty_unit_if_met": duty_unit if cert_code else None,
            "duty_unit_if_not_met": duty_unit if not cert_code else None,
            "action_code": action_code,
            "sequence_number": i,
        })

    return conditions
```

---

## PIPELINE MODULES TO BUILD

### `app/pipeline/uk_tariff.py`

Full tree crawl: sections -> chapters -> headings -> commodities (`productline_suffix == "80"` only).
For each commodity:
1. Upsert `commodity_codes`.
2. For each measure in `included[]`:
   - Classify using `route_measure()`.
   - Parse duty expression with `parse_duty_expression()` from `app/duty_parser.py`.
   - Upsert to destination table; get parent `id`.
   - Parse ALL conditions with `parse_uk_conditions()`; upsert to `measure_conditions`.
3. 200ms delay between commodity requests.
4. Log run to `pipeline_runs`.

### `app/pipeline/eu_taric.py`

Download TARIC XML. Two-pass parse:
- **Pass 1:** Build `code_descriptions` map from `GOODS.NOMENCLATURE` elements (`PRODUCTLINE.SUFFIX == "80"`).
- **Pass 2:** Iterate all `MEASURE` elements:
  - Classify with `route_measure()`.
  - Parse duty with `parse_duty_expression()`.
  - Parse ALL `MEASURE.CONDITION` children with `parse_conditions()`.
  - Handle ALL condition types: A, B, C, E, F, H, I, J, L, M, R, U, V, X, Y, Z.
  - Upsert parent record first; bulk upsert conditions.
- Batch upserts in groups of 500 rows.

### `app/pipeline/eu_vat.py`

Fetch euvatrates.com JSON, upsert all rate types into `vat_rates`.

### `app/pipeline/certificates.py`

Seed `certificate_codes` with ALL codes listed in this prompt. Unknown codes
auto-inserted with placeholder description.

### `app/pipeline/scheduler.py`

APScheduler (AsyncIOScheduler):
- `eu_taric.run_daily_delta()` — every day 06:00 UTC
- `uk_tariff.crawl_all()` — daily, re-fetch codes where `last_updated < NOW() - INTERVAL '7 days'`
- `eu_vat.run()` — every Sunday 08:00 UTC

---

## LOOKUP ENDPOINT

```
GET /tariff/lookup?hs_code={code}&origin={ISO2}&destination={ISO2}&cif_price_eur_per_dtn={float}
```

The optional `cif_price_eur_per_dtn` enables evaluation of V/L/F variable rate
schedules at lookup time.

### Response schema (complete)

```json
{
  "hs_code": "string",
  "description": "string",
  "origin_country": "string",
  "destination_country": "string",
  "destination_market": "EU|GB",

  "duty": {
    "rate_type": "MFN|preferential|anti-dumping|...",
    "duty_rate": null,
    "duty_amount": null,
    "duty_unit": null,
    "duty_amount_2": null,
    "duty_unit_2": null,
    "currency": "EUR",
    "duty_min_amount": null,
    "duty_min_unit": null,
    "duty_max_amount": null,
    "duty_max_unit": null,
    "has_entry_price": false,
    "entry_price_is_reduced": false,
    "additional_duty_components": [],
    "duty_asv_amount": null,
    "is_free": false,
    "is_informative": false,
    "is_refundable": false,
    "is_computed_daily": false,
    "variable_duty_schedule": null,
    "entry_price_schedule": null,
    "price_undertaking_schedule": null,
    "duty_component_type": "standard",
    "duty_expression_raw": "string",
    "trade_agreement": null,
    "financial_charge": true,
    "source": "TARIC|UK_TARIFF",
    "conditions": []
  },

  "vat": {
    "country_code": "string",
    "rate_type": "standard",
    "vat_rate": 20.0,
    "hs_code_prefix": null,
    "source": "string"
  },

  "price_measures": [],
  "non_tariff_measures": [],
  "tariff_quotas": [],
  "supplementary_units": [],

  "calculated": {
    "effective_duty_rate": null,
    "effective_duty_amount": null,
    "effective_duty_unit": null,
    "variable_rate_evaluated": false,
    "entry_price_component": false,
    "vat_base": "goods_value + customs_duty",
    "vat_rate": 20.0,
    "example_goods_value": 100.0,
    "example_customs_duty": null,
    "example_vat": null,
    "example_total_landed": null,
    "currency": "EUR",
    "warnings": []
  },

  "data_freshness": {
    "duty_last_updated": "2026-03-28",
    "vat_last_updated": "2026-03-28",
    "ntm_last_updated": "2026-03-28"
  }
}
```

### Warnings generation logic

Generate a warning for each of:
- **A/B-type condition:** cert required for lower rate; state fallback rate
- **Y-type on NTM:** border documents may be required
- **has_entry_price:** EA/EAR computed daily by EC; cannot pre-calculate
- **is_computed_daily (EUC):** rate changes daily; verify before shipment
- **variable_duty_schedule not null:** provide CIF price for exact rate
- **entry_price_schedule not null:** entry price threshold system applies
- **price_undertaking_schedule:** ADD and minimum import price applies
- **is_refundable:** duty may be eligible for drawback/refund
- **duty_min_amount:** minimum duty constraint applies
- **duty_max_amount:** maximum duty cap applies
- **ASV-based:** duty depends on declared alcohol content
- **tariff_quotas not empty:** in-quota rate available; verify quota balance
- **supplementary_units not empty:** declare unit quantity on customs entry
- **price_measures not empty:** reference price system; check before import

---

## ADDITIONAL ENDPOINTS

```
GET  /tariff/lookup?hs_code={code}&origin={ISO2}&destination={ISO2}&cif_price_eur_per_dtn={float}
GET  /tariff/conditions/{hs_code}?market=EU
GET  /tariff/certificates
GET  /tariff/ntm/{hs_code}?market=EU&origin=CN
GET  /tariff/quotas/{hs_code}?market=EU&origin=TR
GET  /tariff/supplementary-units/{hs_code}?market=EU
GET  /tariff/price-measures/{hs_code}?market=EU&origin=CN
GET  /tariff/variable-rate/{hs_code}?market=EU&origin=CN&cif_price_eur_per_dtn={float}
GET  /pipeline/status
GET  /pipeline/logs?source=&limit=
POST /pipeline/trigger/{source}
POST /pipeline/bootstrap
```

Admin endpoints (`/pipeline/*`) protected by `X-Admin-Key` header.

---

## PROJECT STRUCTURE

```
veritariff/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py               # All 11 SQLAlchemy models
│   ├── schemas.py              # Pydantic models for all response types
│   ├── duty_parser.py          # parse_duty_expression() — standalone module
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── uk_tariff.py
│   │   ├── eu_taric.py
│   │   ├── eu_vat.py
│   │   ├── certificates.py
│   │   └── scheduler.py
│   └── routers/
│       ├── pipeline.py
│       └── tariff.py
├── alembic/
├── requirements.txt
└── .env
```

---

## REQUIREMENTS & CONSTRAINTS

- Python 3.11+, FastAPI, SQLAlchemy 2.x async, asyncpg, httpx, APScheduler,
  alembic, lxml.
- All HTTP calls async (`httpx.AsyncClient`). All DB operations async.
- Upsert everywhere — `INSERT ... ON CONFLICT DO UPDATE`. Never plain INSERT.
- Retry logic: 3 attempts, exponential backoff (1s, 2s, 4s).
- Store full raw source response in `raw_json`.
- Store `duty_expression_raw` on every `duty_rates` row — never discard the raw string.
- When upserting `measure_conditions`: DELETE existing conditions for the parent
  measure first, then INSERT fresh.
- Batch all bulk DB writes in groups of 500 rows maximum.
- Guard bootstrap with `pipeline_config` table.
- Log every pipeline run to `pipeline_runs`.
- Alert (log ERROR level) if TARIC XML content-length < 10 MB.
- `parse_duty_expression()` MUST NOT raise exceptions — always return a valid
  `ParsedDuty` with at least `raw_expression` populated if parsing fails.
- Unknown condition types: log WARNING, store with `condition_logic = 'UNKNOWN'`, never skip.
- Unknown certificate codes: auto-insert into `certificate_codes` with placeholder description.
- Unknown measure_type_ids: log WARNING and return `'unknown'` from `route_measure()`.

---

## WHAT TO DELIVER

1. All Python files — fully implemented, no stubs, no TODOs.
2. `app/duty_parser.py` — complete `ParsedDuty` dataclass and `parse_duty_expression()`
   covering all 32 documented categories.
3. SQLAlchemy ORM models for all 11 tables with correct relationships and indexes.
4. Alembic `env.py` and initial migration.
5. `requirements.txt` with pinned versions.
6. `.env.example` with all required variables.
7. `README.md` section: "Running the pipeline for the first time."

Every parser must implement the five-group routing function (`route_measure`).
The response schema must include all sections: `duty`, `vat`, `tariff_quotas`,
`price_measures`, `non_tariff_measures`, `supplementary_units`, `calculated.warnings`.
Every function must be complete. No stubs.