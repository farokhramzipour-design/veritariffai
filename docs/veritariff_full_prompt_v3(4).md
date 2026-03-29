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

---

## ORIGIN CODES & GEOGRAPHY (NEW SECTION — v4 ADDITION)

The TARIC system associates every measure with an **origin** — the country or group
of countries from which the goods must originate for the measure to apply.
Origin is expressed as two columns in the raw TARIC data:

| Column | Example values |
|--------|---------------|
| `origin_code` | `GB`, `1011`, `UA`, `2005`, `4001`, `5005` |
| `origin` | `United Kingdom`, `ERGA OMNES`, `Ukraine`, `GSP-EBA (Special arrangement …)` |

You must parse, store, and use both columns. The origin code determines which
duty rate, quota, or non-tariff measure applies to a shipment from a given country.

---

### Origin Code Type Classification

Origin codes fall into four distinct types. Detect type from the code pattern:

| Type | Code Pattern | Examples | Meaning |
|------|-------------|---------|---------|
| `country` | 2-letter ISO 3166-1 alpha-2 | `GB`, `UA`, `CN`, `US` | Single country |
| `erga_omnes` | `1011` | `1011` | All third countries (MFN / universal) |
| `group_numeric` | 4-digit starting with 1, 2, 3 | `1006`, `1033`, `1035`, `2000`, `2005`, `2012`, `2020`, `2027`, `2038`, `2080`, `2200`, `2300`, `2301`, `2500`, `2501`, `3000` | Named trade-agreement group or arrangement |
| `phytosanitary` | 4-digit starting with 4 | `4000`–`4013` | Phytosanitary country group (plant/pest control) |
| `safeguard` | 4-digit starting with 5 | `5005`, `5007` | Safeguard measure group |

Add a `origin_code_type` column to the origins reference table using these categories.

---

### Database — `origins` Reference Table

```sql
CREATE TABLE origins (
    id                  SERIAL PRIMARY KEY,
    origin_code         VARCHAR(10) NOT NULL UNIQUE,
    origin_name         TEXT NOT NULL,
    origin_code_type    VARCHAR(20) NOT NULL,
        -- 'country', 'erga_omnes', 'group_numeric', 'phytosanitary', 'safeguard'
    iso2                VARCHAR(2),
        -- ISO 3166-1 alpha-2 for country-type codes; NULL for groups
    iso3                VARCHAR(3),
        -- ISO 3166-1 alpha-3 (resolved from iso2 lookup); NULL for groups
    is_eu_member        BOOLEAN DEFAULT FALSE,
        -- TRUE only for EU member states (EU bloc imports handled separately)
    is_erga_omnes       BOOLEAN DEFAULT FALSE,
        -- TRUE only for code 1011
    is_group            BOOLEAN DEFAULT FALSE,
        -- TRUE for all non-country, non-erga-omnes codes
    member_iso2_codes   VARCHAR(2)[],
        -- For group codes: array of ISO2 codes of member countries
        -- (seed from the phytosanitary / group definitions below)
    group_category      VARCHAR(30),
        -- 'trade_agreement', 'gsp', 'phytosanitary', 'safeguard',
        --  'erga_omnes', 'wto', 'other' — NULL for country codes
    notes               TEXT,
        -- Long description for complex group codes
    last_updated        TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_origins_iso2        ON origins (iso2);
CREATE INDEX idx_origins_code_type   ON origins (origin_code_type);
CREATE INDEX idx_origins_group_cat   ON origins (group_category);
```

---

### Complete Origin Seed Data

Seed the `origins` table with all codes found in TARIC. The full list is:

#### Single Countries (origin_code_type = 'country')

| origin_code | origin_name | group_category |
|------------|-------------|----------------|
| AD | Andorra | trade_agreement |
| AE | United Arab Emirates | other |
| AL | Albania | other |
| AR | Argentina | other |
| AU | Australia | other |
| AZ | Azerbaijan | other |
| BA | Bosnia and Herzegovina | other |
| BD | Bangladesh | other |
| BF | Burkina Faso | other |
| BO | Bolivia | other |
| BR | Brazil | other |
| BY | Belarus | other |
| CA | Canada | trade_agreement |
| CH | Switzerland | trade_agreement |
| CI | Ivory Coast | other |
| CL | Chile | trade_agreement |
| CM | Cameroon | other |
| CN | China | other |
| CO | Colombia | trade_agreement |
| CR | Costa Rica | other |
| CU | Cuba | other |
| DO | Dominican Republic | other |
| DZ | Algeria | trade_agreement |
| EC | Ecuador | trade_agreement |
| EG | Egypt | trade_agreement |
| ET | Ethiopia | other |
| EU | European Union | other |
| FJ | Fiji | trade_agreement |
| FO | Faroe Islands | trade_agreement |
| GB | United Kingdom | other |
| GE | Georgia | trade_agreement |
| GH | Ghana | other |
| GL | Greenland | other |
| GT | Guatemala | other |
| GY | Guyana | other |
| HK | Hong Kong | other |
| HN | Honduras | other |
| ID | Indonesia | other |
| IL | Israel | trade_agreement |
| IN | India | other |
| IQ | Iraq | other |
| IR | Iran, Islamic Republic of | other |
| IS | Iceland | trade_agreement |
| JO | Jordan | trade_agreement |
| JP | Japan | trade_agreement |
| KE | Kenya | other |
| KH | Cambodia | other |
| KP | Korea, Democratic People's Republic of | other |
| KR | Korea, Republic of (South Korea) | trade_agreement |
| KZ | Kazakhstan | other |
| LB | Lebanon | trade_agreement |
| LI | Liechtenstein | trade_agreement |
| LK | Sri Lanka | other |
| LY | Libya | other |
| MA | Morocco | trade_agreement |
| MD | Moldova, Republic of | trade_agreement |
| ME | Montenegro | other |
| MG | Madagascar | other |
| MK | North Macedonia | other |
| MY | Malaysia | other |
| MX | Mexico | trade_agreement |
| NA | Namibia | other |
| NG | Nigeria | other |
| NI | Nicaragua | other |
| NO | Norway | trade_agreement |
| NZ | New Zealand | trade_agreement |
| OM | Oman | other |
| PA | Panama | other |
| PE | Peru | trade_agreement |
| PG | Papua New Guinea | trade_agreement |
| PH | Philippines | other |
| PK | Pakistan | other |
| PS | Occupied Palestinian Territory | trade_agreement |
| PY | Paraguay | other |
| RU | Russian Federation | other |
| RW | Rwanda | other |
| SA | Saudi Arabia | other |
| SB | Solomon Islands | trade_agreement |
| SD | Sudan | other |
| SG | Singapore | trade_agreement |
| SH | Saint Helena, Ascension and Tristan da Cunha | other |
| SM | San Marino | trade_agreement |
| SO | Somalia | other |
| SV | El Salvador | other |
| SY | Syria | other |
| TH | Thailand | other |
| TN | Tunisia | trade_agreement |
| TR | Türkiye | trade_agreement |
| TT | Trinidad and Tobago | other |
| TW | Taiwan | other |
| UA | Ukraine | trade_agreement |
| UG | Uganda | other |
| US | United States | other |
| UY | Uruguay | other |
| VN | Viet Nam | trade_agreement |
| WS | Samoa | trade_agreement |
| XC | Ceuta | other |
| XK | Kosovo | other |
| XL | Melilla | other |
| XS | Serbia | other |
| ZA | South Africa | trade_agreement |
| ZM | Zambia | other |

#### Special / Pseudo-Country Codes

| origin_code | origin_name | origin_code_type | group_category |
|------------|-------------|-----------------|----------------|
| 1011 | ERGA OMNES | erga_omnes | erga_omnes |

#### Named Trade-Agreement & Arrangement Groups

| origin_code | origin_name | group_category | member_iso2_codes (indicative) |
|------------|-------------|----------------|-------------------------------|
| 1006 | EU-Canada agreement: re-imported goods | trade_agreement | `{CA}` |
| 1007 | EU-Switzerland agreement: re-imported goods | trade_agreement | `{CH}` |
| 1008 | All third countries | other | NULL (all) |
| 1033 | CARIFORUM | trade_agreement | `{AG,BB,BZ,DM,DO,GD,GY,HT,JM,KN,LC,SR,TT,VC}` |
| 1034 | Eastern and Southern Africa States | trade_agreement | `{CF,KM,MG,MU,RW,SC,SD,UG,ZM,ZW}` |
| 1035 | SADC EPA | trade_agreement | `{BW,LS,MZ,NA,SZ,ZA}` |
| 1098 | Western Balkan countries | other | `{AL,BA,ME,MK,XK,XS}` |
| 2000 | Preferential origin — Morocco amended protocol | trade_agreement | `{MA}` |
| 2005 | GSP-EBA (Everything But Arms) | gsp | NULL (LDC list — ~49 countries) |
| 2012 | EEA — European Economic Area | trade_agreement | `{IS,LI,NO}` |
| 2014 | EEA — Iceland | trade_agreement | `{IS}` |
| 2020 | GSP — General arrangements | gsp | NULL (developing countries list) |
| 2027 | GSP+ | gsp | NULL (eligible GSP+ countries) |
| 2038 | Countries submitted to import restrictions following the Chernobyl accident | other | NULL |
| 2080 | OCTs (Overseas Countries and Territories) | trade_agreement | NULL |
| 2200 | Central America | trade_agreement | `{CR,SV,GT,HN,NI,PA}` |
| 2300 | Silk or cotton handloom products | other | NULL |
| 2301 | Certain handicraft products (Handicrafts) | other | NULL |
| 2500 | Member countries of WTO | wto | NULL |
| 2501 | Countries not members of the WTO | other | NULL |
| 3000 | Non-cooperating countries in fighting IUU fishing | other | NULL |

#### Phytosanitary Groups (origin_code_type = 'phytosanitary')

| origin_code | origin_name | member_iso2_codes |
|------------|-------------|------------------|
| 4000 | Phytosanitary G003/G027 | `{AF,IN,IR,IQ,MX,NP,PK,ZA,US}` |
| 4001 | Phytosanitary G008 | `{AU,NZ,US}` |
| 4002 | Phytosanitary G014 (all third countries excl. list) | NULL (exclusion list: AL,AD,AM,AZ,BY,BA,FO,GE,IS,LI,MD,ME,MK,NO,SM,XS,CH,TR,UA,GB,RU) |
| 4003 | Phytosanitary G016 | `{BY,CA,CN,JP,KR,MN,KP,RU,TW,UA,US}` |
| 4004 | Phytosanitary G018 | `{CA,GB,US,VN}` |
| 4005 | Phytosanitary G022 (African continent) | NULL (all African countries) |
| 4006 | Phytosanitary G026 | `{AR,AU,BO,BR,CL,NZ,UY}` |
| 4007 | Phytosanitary G043 | `{CA,US,VN}` |
| 4008 | Phytosanitary G044 | `{AL,AM,TR,US}` |
| 4009 | Phytosanitary (American continent) | NULL (all American countries) |
| 4010 | Phytosanitary G053 | `{CA,US,VN,GB}` |
| 4011 | Phytosanitary G054 | NULL (see regulation for list) |
| 4012 | Phytosanitary G056 | `{AF,IN,IR,KG,PK,TJ,TM,UZ}` |
| 4013 | Phytosanitary G057 | `{CN,KR,KP,RU,TW,VN}` |

#### Safeguard Groups (origin_code_type = 'safeguard')

| origin_code | origin_name | group_category |
|------------|-------------|----------------|
| 5005 | Countries subject to safeguard measures | safeguard |
| 5007 | Countries subject to safeguard duties — ferro-alloying elements | safeguard |

---

### Link Origin to Measures

Every measure in TARIC has an origin. Add an `origin_code` foreign key to the
`duty_rates`, `tariff_quotas`, `price_measures`, and `non_tariff_measures` tables:

```sql
ALTER TABLE duty_rates         ADD COLUMN origin_code VARCHAR(10) REFERENCES origins(origin_code);
ALTER TABLE tariff_quotas      ADD COLUMN origin_code VARCHAR(10) REFERENCES origins(origin_code);
ALTER TABLE price_measures     ADD COLUMN origin_code VARCHAR(10) REFERENCES origins(origin_code);
ALTER TABLE non_tariff_measures ADD COLUMN origin_code VARCHAR(10) REFERENCES origins(origin_code);

CREATE INDEX idx_duty_rates_origin          ON duty_rates (origin_code);
CREATE INDEX idx_tariff_quotas_origin       ON tariff_quotas (origin_code);
CREATE INDEX idx_price_measures_origin      ON price_measures (origin_code);
CREATE INDEX idx_non_tariff_measures_origin ON non_tariff_measures (origin_code);
```

**On ingest:** if an origin_code arrives that is not in the `origins` table, auto-insert
it with `origin_name` from the `origin` column value, set `origin_code_type = 'unknown'`,
log a WARNING, and continue. Never drop a record due to an unknown origin.

---

### Origin Lookup Logic for the `/tariff/lookup` Endpoint

When a user queries by HS code + origin country + destination, resolve the applicable
measures using this priority chain:

```python
def resolve_origin_codes_for_country(iso2: str, db) -> list[str]:
    """
    Return all origin_codes that could match a shipment from this country.
    Order: most specific → least specific.
    A rate under a specific country code beats a group-level rate.
    """
    codes = []

    # 1. Exact country code (highest priority)
    codes.append(iso2.upper())

    # 2. Any group codes that include this country in member_iso2_codes
    groups = db.query(Origin).filter(
        Origin.member_iso2_codes.contains([iso2.upper()]),
        Origin.is_group == True
    ).all()
    codes.extend([g.origin_code for g in groups])

    # 3. GSP eligibility (2005, 2020, 2027) — determined by separate GSP eligibility table
    gsp_codes = get_gsp_eligibility(iso2, db)
    codes.extend(gsp_codes)

    # 4. WTO membership (2500 or 2501)
    codes.append(get_wto_membership_code(iso2, db))

    # 5. ERGA OMNES — always included last (catches all MFN rates)
    codes.append("1011")

    # Deduplicate preserving order
    seen = set()
    return [c for c in codes if not (c in seen or seen.add(c))]
```

When fetching duty rates for a lookup, query:

```sql
SELECT * FROM duty_rates
WHERE commodity_code = :hs_code
  AND origin_code = ANY(:resolved_origin_codes)
ORDER BY
  CASE origin_code_type
    WHEN 'country'      THEN 1   -- most specific
    WHEN 'group_numeric' THEN 2
    WHEN 'phytosanitary' THEN 3
    WHEN 'safeguard'    THEN 4
    WHEN 'erga_omnes'   THEN 5   -- least specific (MFN fallback)
    ELSE 6
  END,
  duty_rate ASC NULLS LAST;      -- within same specificity, lower rate first
```

---

### ERGA OMNES — MFN Fallback

Origin code `1011` (ERGA OMNES) means the measure applies to ALL countries
that do not have a more specific measure. It is the **MFN (Most Favoured Nation) rate**.

Rules:
- Always include `1011` as the final fallback in origin resolution.
- If a country has a preferential rate (under its country code or a group code),
  that rate takes precedence over `1011`.
- If NO more specific measure exists for the resolved origin codes,
  return the ERGA OMNES measure.
- Store `is_erga_omnes = TRUE` on the origins row for `1011`.
- Tag rates with `origin_code = '1011'` in the API response as `"rate_basis": "MFN"`.

---

### GSP Tiers — Differentiated Storage

The three GSP group codes represent different preference tiers:

| Code | Name | Preference Level |
|------|------|-----------------|
| 2020 | GSP General arrangements | Standard GSP reduction |
| 2027 | GSP+ | Enhanced GSP reduction (deeper cut) |
| 2005 | GSP-EBA (Everything But Arms) | Full duty-free access (LDCs only) |

When displaying to user:
- 2020: "Standard GSP preferential rate — check if your origin country is GSP-eligible."
- 2027: "GSP+ enhanced rate — requires GSP+ beneficiary status."
- 2005: "EBA duty-free rate — applies only to Least Developed Countries."

Add a `gsp_tier` column to `duty_rates`:

```sql
ALTER TABLE duty_rates ADD COLUMN gsp_tier VARCHAR(10);
  -- 'EBA', 'GSP+', 'GSP', NULL
```

Set `gsp_tier` when `origin_code IN ('2005', '2027', '2020')`.

---

### Phytosanitary Origin Groups — Special Handling

Phytosanitary codes (4000–4013) are linked to **non-tariff measures** (prohibitions,
requirements), NOT duty rates. They define WHICH countries' goods require a
phytosanitary certificate or are subject to an import ban/restriction.

- Route these to `non_tariff_measures` only (never `duty_rates`).
- Store the phytosanitary group code as `origin_code` on the NTM row.
- Add a warning to the API response when the user's country matches a phytosanitary group:
  `"Phytosanitary controls apply to goods of this origin. A phytosanitary certificate
   may be required — check the specific plant health requirements for this commodity."`

---

### Safeguard Origin Groups — Special Handling

Safeguard codes (5005, 5007) apply **additional duties** on top of MFN/preferential rates.
- Route to `duty_rates` with `rate_type = 'safeguard'`.
- Always display BOTH the underlying MFN/preferential rate AND the safeguard surcharge.
- Add warning: `"A safeguard duty applies to goods from this origin.
  This is in addition to the standard import duty."`

---

### Origin — API Response Fields

Add origin information to the `/tariff/lookup` response:

```json
{
  "origin": {
    "origin_code": "UA",
    "origin_name": "Ukraine",
    "origin_code_type": "country",
    "iso2": "UA",
    "iso3": "UKR",
    "is_erga_omnes": false,
    "is_group": false,
    "group_category": null,
    "gsp_tier": null
  },
  "rates_by_origin": [
    {
      "origin_code": "UA",
      "origin_name": "Ukraine",
      "rate_basis": "bilateral_preference",
      "duty_rate": 0.0,
      "duty_expression": "0.000 %",
      "human_readable": "0% (Ukraine preferential rate)"
    },
    {
      "origin_code": "1011",
      "origin_name": "ERGA OMNES",
      "rate_basis": "MFN",
      "duty_rate": 12.0,
      "duty_expression": "12.000 %",
      "human_readable": "12% (MFN rate)"
    }
  ],
  "best_rate": {
    "origin_code": "UA",
    "rate_basis": "bilateral_preference",
    "duty_rate": 0.0,
    "saving_vs_mfn": 12.0,
    "saving_pct": 100.0
  }
}
```

`rate_basis` values:

| Value | Meaning |
|-------|---------|
| `MFN` | Most Favoured Nation — applies to all WTO members without a FTA |
| `bilateral_preference` | Country-specific bilateral trade agreement rate |
| `gsp` | Standard GSP rate |
| `gsp_plus` | GSP+ enhanced rate |
| `eba` | EBA duty-free (LDCs only) |
| `erga_omnes` | Applies to all origins (same as MFN in most cases) |
| `safeguard` | Additional safeguard duty on top of base rate |
| `anti_dumping` | Anti-dumping or countervailing duty |
| `quota` | Rate valid only while quota balance available |
| `end_use` | Rate conditional on authorised end-use |
| `group_preference` | Rate applies via a named group (e.g. CARIFORUM, SADC) |

---

### Origin Pipeline Module — `app/pipeline/origins.py` (NEW)

```python
"""
origins.py — Seed and maintain the origins reference table.

Sources:
  - Static seed: the full origin code list from TARIC (hardcoded from prompt).
  - Dynamic: on every TARIC XML ingest, auto-insert any origin codes not yet present.
"""

from app.db import SessionLocal
from app.models import Origin

ORIGIN_SEED = [
    # --- ERGA OMNES ---
    {"origin_code": "1011", "origin_name": "ERGA OMNES",
     "origin_code_type": "erga_omnes", "is_erga_omnes": True,
     "is_group": False, "group_category": "erga_omnes"},

    # --- Countries ---
    {"origin_code": "AD", "origin_name": "Andorra",
     "origin_code_type": "country", "iso2": "AD", "iso3": "AND"},
    {"origin_code": "AE", "origin_name": "United Arab Emirates",
     "origin_code_type": "country", "iso2": "AE", "iso3": "ARE"},
    {"origin_code": "AL", "origin_name": "Albania",
     "origin_code_type": "country", "iso2": "AL", "iso3": "ALB"},
    # ... (all countries from the seed table above) ...

    # --- Groups ---
    {"origin_code": "1033", "origin_name": "CARIFORUM",
     "origin_code_type": "group_numeric", "is_group": True,
     "group_category": "trade_agreement",
     "member_iso2_codes": ["AG","BB","BZ","DM","DO","GD","GY","HT",
                           "JM","KN","LC","SR","TT","VC"]},
    {"origin_code": "1035", "origin_name": "SADC EPA",
     "origin_code_type": "group_numeric", "is_group": True,
     "group_category": "trade_agreement",
     "member_iso2_codes": ["BW","LS","MZ","NA","SZ","ZA"]},
    {"origin_code": "2005", "origin_name": "GSP-EBA (Everything But Arms)",
     "origin_code_type": "group_numeric", "is_group": True,
     "group_category": "gsp", "gsp_tier": "EBA"},
    {"origin_code": "2020", "origin_name": "GSP — General arrangements",
     "origin_code_type": "group_numeric", "is_group": True,
     "group_category": "gsp", "gsp_tier": "GSP"},
    {"origin_code": "2027", "origin_name": "GSP+",
     "origin_code_type": "group_numeric", "is_group": True,
     "group_category": "gsp", "gsp_tier": "GSP+"},

    # --- Phytosanitary groups ---
    {"origin_code": "4000", "origin_name": "Phytosanitary G003/G027",
     "origin_code_type": "phytosanitary", "is_group": True,
     "group_category": "phytosanitary",
     "member_iso2_codes": ["AF","IN","IR","IQ","MX","NP","PK","ZA","US"]},
    {"origin_code": "4001", "origin_name": "Phytosanitary G008",
     "origin_code_type": "phytosanitary", "is_group": True,
     "group_category": "phytosanitary",
     "member_iso2_codes": ["AU","NZ","US"]},
    {"origin_code": "4002",
     "origin_name": "Phytosanitary G014 — all third countries excluding specific list",
     "origin_code_type": "phytosanitary", "is_group": True,
     "group_category": "phytosanitary",
     "notes": "Excludes: AL,AD,AM,AZ,BY,BA,FO,GE,IS,LI,MD,ME,MK,NO,SM,XS,CH,TR,UA,GB,RU"},
    {"origin_code": "4003", "origin_name": "Phytosanitary G016",
     "origin_code_type": "phytosanitary", "is_group": True,
     "group_category": "phytosanitary",
     "member_iso2_codes": ["BY","CA","CN","JP","KR","MN","KP","RU","TW","UA","US"]},
    {"origin_code": "4004", "origin_name": "Phytosanitary G018",
     "origin_code_type": "phytosanitary", "is_group": True,
     "group_category": "phytosanitary",
     "member_iso2_codes": ["CA","GB","US","VN"]},
    {"origin_code": "4005",
     "origin_name": "Phytosanitary G022 — African continent",
     "origin_code_type": "phytosanitary", "is_group": True,
     "group_category": "phytosanitary",
     "notes": "All countries of the African continent"},
    {"origin_code": "4006", "origin_name": "Phytosanitary G026",
     "origin_code_type": "phytosanitary", "is_group": True,
     "group_category": "phytosanitary",
     "member_iso2_codes": ["AR","AU","BO","BR","CL","NZ","UY"]},
    {"origin_code": "4007", "origin_name": "Phytosanitary G043",
     "origin_code_type": "phytosanitary", "is_group": True,
     "group_category": "phytosanitary",
     "member_iso2_codes": ["CA","US","VN"]},
    {"origin_code": "4008", "origin_name": "Phytosanitary G044",
     "origin_code_type": "phytosanitary", "is_group": True,
     "group_category": "phytosanitary",
     "member_iso2_codes": ["AL","AM","TR","US"]},
    {"origin_code": "4009",
     "origin_name": "Phytosanitary — American continent countries",
     "origin_code_type": "phytosanitary", "is_group": True,
     "group_category": "phytosanitary",
     "notes": "All countries of the American continent"},
    {"origin_code": "4010", "origin_name": "Phytosanitary G053",
     "origin_code_type": "phytosanitary", "is_group": True,
     "group_category": "phytosanitary",
     "member_iso2_codes": ["CA","US","VN","GB"]},
    {"origin_code": "4011", "origin_name": "Phytosanitary G054",
     "origin_code_type": "phytosanitary", "is_group": True,
     "group_category": "phytosanitary",
     "notes": "See specific EU regulation for country list"},
    {"origin_code": "4012", "origin_name": "Phytosanitary G056",
     "origin_code_type": "phytosanitary", "is_group": True,
     "group_category": "phytosanitary",
     "member_iso2_codes": ["AF","IN","IR","KG","PK","TJ","TM","UZ"]},
    {"origin_code": "4013", "origin_name": "Phytosanitary G057",
     "origin_code_type": "phytosanitary", "is_group": True,
     "group_category": "phytosanitary",
     "member_iso2_codes": ["CN","KR","KP","RU","TW","VN"]},

    # --- Safeguard groups ---
    {"origin_code": "5005",
     "origin_name": "Countries subject to safeguard measures",
     "origin_code_type": "safeguard", "is_group": True,
     "group_category": "safeguard"},
    {"origin_code": "5007",
     "origin_name": "Countries subject to safeguard duties — ferro-alloying elements",
     "origin_code_type": "safeguard", "is_group": True,
     "group_category": "safeguard"},
]


def seed_origins(db=None):
    """Seed or refresh the origins reference table."""
    if db is None:
        db = SessionLocal()
    try:
        for row in ORIGIN_SEED:
            existing = db.query(Origin).filter_by(
                origin_code=row["origin_code"]
            ).first()
            if existing:
                for k, v in row.items():
                    setattr(existing, k, v)
            else:
                db.add(Origin(**row))
        db.commit()
    finally:
        db.close()


def auto_insert_unknown_origin(origin_code: str, origin_name: str, db) -> None:
    """
    Called during TARIC ingest when an origin_code is not in the table.
    Inserts a placeholder row so the FK constraint is satisfied.
    Logs a WARNING for manual review.
    """
    import logging
    logging.warning(
        f"Unknown origin_code encountered during ingest: "
        f"{origin_code!r} ({origin_name!r}) — auto-inserting placeholder."
    )
    existing = db.query(Origin).filter_by(origin_code=origin_code).first()
    if not existing:
        code_type = _detect_code_type(origin_code)
        db.add(Origin(
            origin_code=origin_code,
            origin_name=origin_name or f"Unknown ({origin_code})",
            origin_code_type=code_type,
            is_group=code_type != "country",
        ))
        db.commit()


def _detect_code_type(code: str) -> str:
    """Classify an origin code by its format."""
    if code == "1011":
        return "erga_omnes"
    if len(code) == 2 and code.isalpha():
        return "country"
    if code.isdigit():
        n = int(code)
        if 4000 <= n <= 4999:
            return "phytosanitary"
        if 5000 <= n <= 5999:
            return "safeguard"
        return "group_numeric"
    return "unknown"
```

---

### Origin — ORM Model Addition

```python
from sqlalchemy import Column, String, Boolean, Text, ARRAY
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from app.db import Base

class Origin(Base):
    __tablename__ = "origins"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    origin_code         = Column(String(10), unique=True, nullable=False, index=True)
    origin_name         = Column(Text, nullable=False)
    origin_code_type    = Column(String(20), nullable=False)
    iso2                = Column(String(2), index=True)
    iso3                = Column(String(3))
    is_eu_member        = Column(Boolean, default=False)
    is_erga_omnes       = Column(Boolean, default=False)
    is_group            = Column(Boolean, default=False)
    member_iso2_codes   = Column(PG_ARRAY(String(2)))
    group_category      = Column(String(30), index=True)
    gsp_tier            = Column(String(10))   # 'EBA', 'GSP+', 'GSP', NULL
    notes               = Column(Text)
    last_updated        = Column(DateTime, default=func.now(), onupdate=func.now())
```

---

### Tests — `tests/test_origins.py` (NEW)

Add pytest tests covering:

1. `_detect_code_type('GB')` → `'country'`
2. `_detect_code_type('1011')` → `'erga_omnes'`
3. `_detect_code_type('2005')` → `'group_numeric'`
4. `_detect_code_type('4001')` → `'phytosanitary'`
5. `_detect_code_type('5005')` → `'safeguard'`
6. `resolve_origin_codes_for_country('UA', db)` includes `'UA'`, `'1011'`, and any applicable group codes.
7. `resolve_origin_codes_for_country('US', db)` includes `'US'`, `'4000'`, `'4001'`, `'4003'`, `'4009'`, `'2500'`, `'1011'` (US is in multiple phytosanitary groups).
8. Seeding runs without error on a fresh database.
9. `auto_insert_unknown_origin` inserts exactly one row and does not raise on a duplicate call.
10. API response for a UA origin includes both the bilateral preference rate AND the ERGA OMNES MFN rate in `rates_by_origin`.

---

### Pipeline Update — `app/pipeline/eu_taric.py`

During TARIC XML measure parsing, resolve origin as follows:

```python
def parse_measure_origin(measure_xml) -> str:
    """Extract and validate origin_code from a TARIC measure XML node."""
    geographical_area_id = measure_xml.findtext("geographical.area.id", "").strip()
    geographical_area_desc = measure_xml.findtext(
        "geographical.area.description", ""
    ).strip()

    if not geographical_area_id:
        # Fallback: assume ERGA OMNES if no origin specified
        return "1011"

    # Auto-insert if not already known
    db = SessionLocal()
    try:
        existing = db.query(Origin).filter_by(
            origin_code=geographical_area_id
        ).first()
        if not existing:
            auto_insert_unknown_origin(
                geographical_area_id, geographical_area_desc, db
            )
    finally:
        db.close()

    return geographical_area_id
```

---

### WHAT TO DELIVER (additions for origin handling)

8. `app/pipeline/origins.py` — complete `seed_origins()`, `auto_insert_unknown_origin()`, `_detect_code_type()`, `resolve_origin_codes_for_country()`.
9. `app/models/origin.py` — complete SQLAlchemy ORM model.
10. Alembic migration for the `origins` table and new `origin_code` FK columns on all four measure tables.
11. `tests/test_origins.py` — 10 pytest tests as listed above.
12. Updated `/tariff/lookup` endpoint to resolve origin codes and return `rates_by_origin`, `best_rate`, and `origin` in the response.


---

## ORIGIN CODES & COUNTRY/GROUP RESOLUTION (NEW SECTION — CRITICAL)

TARIC measures are always associated with an **origin** — either a single country/territory
or a named group of countries. The origin determines which measure applies to a given shipment.

Every row in the TARIC XML has two fields:
- `origin_code` — the raw code (e.g. `GB`, `1011`, `2020`, `4003`)
- `origin` — the human-readable label (e.g. `United Kingdom`, `ERGA OMNES`, `GSP - General arrangements`)

You must store, resolve, and expose both. Never discard the group codes — they are not
just labels, they define which countries a measure actually applies to.

---

### ORIGIN CODE TAXONOMY

Origin codes fall into five distinct categories. Parse the code format to determine the category:

| Category | Code Pattern | Examples | Logic |
|----------|-------------|---------|-------|
| **ISO country** | 2-letter ISO 3166-1 alpha-2 | `GB`, `UA`, `CN`, `US` | Single country |
| **ISO territory** | 2-letter non-standard / special | `XS` (Serbia), `XK` (Kosovo), `XC` (Ceuta), `XL` (Melilla), `EU`, `FO`, `GL` | Single territory (not UN member or special customs territory) |
| **ERGA OMNES / all** | `1011` | ERGA OMNES | Applies to ALL origins (universal MFN measure) |
| **Trade agreement / preference group** | `1xxx`, `2xxx` | `1033`, `1034`, `1035`, `2005`, `2012`, `2020`, `2027`, `2038`, `2080`, `2200`, `2300`, `2301`, `2500`, `2501` | Named group of countries under a specific regime |
| **Phytosanitary / control group** | `4xxx` | `4000`–`4013` | Countries subject to specific border biosecurity controls |
| **Safeguard group** | `5xxx` | `5005`, `5007` | Countries subject to safeguard measures / anti-dumping |

---

### DATABASE SCHEMA — ORIGIN TABLES

```sql
-- Master origin code reference table
CREATE TABLE origin_codes (
    code                VARCHAR(10) PRIMARY KEY,  -- e.g. 'GB', '1011', '2020', '4003'
    description         TEXT NOT NULL,            -- human-readable label from TARIC
    category            VARCHAR(30) NOT NULL,      -- see categories below
    is_group            BOOLEAN NOT NULL DEFAULT FALSE,  -- true if code represents >1 country
    is_erga_omnes       BOOLEAN NOT NULL DEFAULT FALSE,  -- true only for 1011
    iso_alpha2          VARCHAR(2),               -- if category='iso_country', same as code
    notes               TEXT,                    -- supplementary detail
    last_updated        TIMESTAMP DEFAULT NOW()
);

-- Members of each group code (many-to-many)
CREATE TABLE origin_group_members (
    group_code          VARCHAR(10) NOT NULL REFERENCES origin_codes(code),
    member_iso2         VARCHAR(10) NOT NULL,     -- ISO2 country code that is a member
    PRIMARY KEY (group_code, member_iso2)
);

-- Index for fast reverse lookup: "which groups does country X belong to?"
CREATE INDEX idx_origin_group_members_iso2
    ON origin_group_members(member_iso2);
```

**Category enum values** (store in `origin_codes.category`):

```python
ORIGIN_CATEGORY = Literal[
    "iso_country",          # standard 2-letter ISO 3166-1 country
    "iso_territory",        # non-standard territory with 2-letter code
    "erga_omnes",           # 1011 — applies to all origins
    "trade_agreement",      # 1xxx / 2xxx — preferential/agreement group
    "phytosanitary_group",  # 4xxx — biosecurity control group
    "safeguard_group",      # 5xxx — safeguard/anti-dumping group
    "special_group",        # other numeric groups not fitting above
]
```

---

### COMPLETE ORIGIN CODE SEED DATA

Seed the `origin_codes` table with all codes observed in TARIC.

#### ISO Countries and Territories (category = `iso_country` or `iso_territory`)

```python
ISO_ORIGINS = [
    # Standard ISO 3166-1 alpha-2 countries
    {"code": "AD", "description": "Andorra",                                        "category": "iso_country"},
    {"code": "AE", "description": "United Arab Emirates",                           "category": "iso_country"},
    {"code": "AF", "description": "Afghanistan",                                    "category": "iso_country"},
    {"code": "AL", "description": "Albania",                                        "category": "iso_country"},
    {"code": "AM", "description": "Armenia",                                        "category": "iso_country"},
    {"code": "AR", "description": "Argentina",                                      "category": "iso_country"},
    {"code": "AU", "description": "Australia",                                      "category": "iso_country"},
    {"code": "AZ", "description": "Azerbaijan",                                     "category": "iso_country"},
    {"code": "BA", "description": "Bosnia and Herzegovina",                         "category": "iso_country"},
    {"code": "BD", "description": "Bangladesh",                                     "category": "iso_country"},
    {"code": "BF", "description": "Burkina Faso",                                   "category": "iso_country"},
    {"code": "BO", "description": "Bolivia",                                        "category": "iso_country"},
    {"code": "BR", "description": "Brazil",                                         "category": "iso_country"},
    {"code": "BY", "description": "Belarus",                                        "category": "iso_country"},
    {"code": "CA", "description": "Canada",                                         "category": "iso_country"},
    {"code": "CH", "description": "Switzerland",                                    "category": "iso_country"},
    {"code": "CI", "description": "Ivory Coast",                                    "category": "iso_country"},
    {"code": "CL", "description": "Chile",                                          "category": "iso_country"},
    {"code": "CM", "description": "Cameroon",                                       "category": "iso_country"},
    {"code": "CN", "description": "China",                                          "category": "iso_country"},
    {"code": "CO", "description": "Colombia",                                       "category": "iso_country"},
    {"code": "CR", "description": "Costa Rica",                                     "category": "iso_country"},
    {"code": "CU", "description": "Cuba",                                           "category": "iso_country"},
    {"code": "DO", "description": "Dominican Republic",                             "category": "iso_country"},
    {"code": "DZ", "description": "Algeria",                                        "category": "iso_country"},
    {"code": "EC", "description": "Ecuador",                                        "category": "iso_country"},
    {"code": "EG", "description": "Egypt",                                          "category": "iso_country"},
    {"code": "ET", "description": "Ethiopia",                                       "category": "iso_country"},
    {"code": "FJ", "description": "Fiji",                                           "category": "iso_country"},
    {"code": "FO", "description": "Faroe Islands",                                  "category": "iso_territory"},
    {"code": "GB", "description": "United Kingdom",                                 "category": "iso_country"},
    {"code": "GE", "description": "Georgia",                                        "category": "iso_country"},
    {"code": "GH", "description": "Ghana",                                          "category": "iso_country"},
    {"code": "GL", "description": "Greenland",                                      "category": "iso_territory"},
    {"code": "GT", "description": "Guatemala",                                      "category": "iso_country"},
    {"code": "GY", "description": "Guyana",                                         "category": "iso_country"},
    {"code": "HK", "description": "Hong Kong",                                     "category": "iso_territory"},
    {"code": "HN", "description": "Honduras",                                      "category": "iso_country"},
    {"code": "ID", "description": "Indonesia",                                      "category": "iso_country"},
    {"code": "IL", "description": "Israel",                                         "category": "iso_country"},
    {"code": "IN", "description": "India",                                          "category": "iso_country"},
    {"code": "IQ", "description": "Iraq",                                           "category": "iso_country"},
    {"code": "IR", "description": "Iran, Islamic Republic of",                      "category": "iso_country"},
    {"code": "IS", "description": "Iceland",                                        "category": "iso_country"},
    {"code": "JP", "description": "Japan",                                          "category": "iso_country"},
    {"code": "JO", "description": "Jordan",                                         "category": "iso_country"},
    {"code": "KE", "description": "Kenya",                                          "category": "iso_country"},
    {"code": "KG", "description": "Kyrgyzstan",                                     "category": "iso_country"},
    {"code": "KH", "description": "Cambodia",                                       "category": "iso_country"},
    {"code": "KP", "description": "North Korea (Democratic People's Republic of Korea)", "category": "iso_country"},
    {"code": "KR", "description": "Korea, Republic of (South Korea)",               "category": "iso_country"},
    {"code": "KZ", "description": "Kazakhstan",                                     "category": "iso_country"},
    {"code": "LB", "description": "Lebanon",                                        "category": "iso_country"},
    {"code": "LI", "description": "Liechtenstein",                                  "category": "iso_country"},
    {"code": "LK", "description": "Sri Lanka",                                      "category": "iso_country"},
    {"code": "LY", "description": "Libya",                                          "category": "iso_country"},
    {"code": "MA", "description": "Morocco",                                        "category": "iso_country"},
    {"code": "MD", "description": "Moldova, Republic of",                           "category": "iso_country"},
    {"code": "ME", "description": "Montenegro",                                     "category": "iso_country"},
    {"code": "MG", "description": "Madagascar",                                     "category": "iso_country"},
    {"code": "MK", "description": "North Macedonia",                                "category": "iso_country"},
    {"code": "MN", "description": "Mongolia",                                       "category": "iso_country"},
    {"code": "MY", "description": "Malaysia",                                       "category": "iso_country"},
    {"code": "MX", "description": "Mexico",                                         "category": "iso_country"},
    {"code": "NA", "description": "Namibia",                                        "category": "iso_country"},
    {"code": "NG", "description": "Nigeria",                                        "category": "iso_country"},
    {"code": "NI", "description": "Nicaragua",                                      "category": "iso_country"},
    {"code": "NO", "description": "Norway",                                         "category": "iso_country"},
    {"code": "NP", "description": "Nepal",                                          "category": "iso_country"},
    {"code": "NZ", "description": "New Zealand",                                    "category": "iso_country"},
    {"code": "OM", "description": "Oman",                                           "category": "iso_country"},
    {"code": "PA", "description": "Panama",                                         "category": "iso_country"},
    {"code": "PE", "description": "Peru",                                           "category": "iso_country"},
    {"code": "PG", "description": "Papua New Guinea",                               "category": "iso_country"},
    {"code": "PH", "description": "Philippines",                                    "category": "iso_country"},
    {"code": "PK", "description": "Pakistan",                                       "category": "iso_country"},
    {"code": "PS", "description": "Occupied Palestinian Territory",                 "category": "iso_territory"},
    {"code": "PY", "description": "Paraguay",                                       "category": "iso_country"},
    {"code": "RU", "description": "Russian Federation",                             "category": "iso_country"},
    {"code": "RW", "description": "Rwanda",                                         "category": "iso_country"},
    {"code": "SA", "description": "Saudi Arabia",                                   "category": "iso_country"},
    {"code": "SB", "description": "Solomon Islands",                                "category": "iso_country"},
    {"code": "SD", "description": "Sudan",                                          "category": "iso_country"},
    {"code": "SG", "description": "Singapore",                                      "category": "iso_country"},
    {"code": "SH", "description": "Saint Helena, Ascension and Tristan da Cunha",   "category": "iso_territory"},
    {"code": "SM", "description": "San Marino",                                     "category": "iso_country"},
    {"code": "SO", "description": "Somalia",                                        "category": "iso_country"},
    {"code": "SV", "description": "El Salvador",                                    "category": "iso_country"},
    {"code": "SY", "description": "Syria",                                          "category": "iso_country"},
    {"code": "TH", "description": "Thailand",                                       "category": "iso_country"},
    {"code": "TJ", "description": "Tajikistan",                                     "category": "iso_country"},
    {"code": "TM", "description": "Turkmenistan",                                   "category": "iso_country"},
    {"code": "TN", "description": "Tunisia",                                        "category": "iso_country"},
    {"code": "TR", "description": "Türkiye",                                        "category": "iso_country"},
    {"code": "TT", "description": "Trinidad and Tobago",                            "category": "iso_country"},
    {"code": "TW", "description": "Taiwan",                                         "category": "iso_territory"},
    {"code": "UA", "description": "Ukraine",                                        "category": "iso_country"},
    {"code": "UG", "description": "Uganda",                                         "category": "iso_country"},
    {"code": "US", "description": "United States",                                  "category": "iso_country"},
    {"code": "UY", "description": "Uruguay",                                        "category": "iso_country"},
    {"code": "UZ", "description": "Uzbekistan",                                     "category": "iso_country"},
    {"code": "VN", "description": "Viet Nam",                                       "category": "iso_country"},
    {"code": "WS", "description": "Samoa",                                          "category": "iso_country"},
    {"code": "ZA", "description": "South Africa",                                   "category": "iso_country"},
    {"code": "ZM", "description": "Zambia",                                         "category": "iso_country"},

    # Special / non-ISO territories
    {"code": "EU", "description": "European Union",                                 "category": "iso_territory"},
    {"code": "XC", "description": "Ceuta",                                          "category": "iso_territory"},
    {"code": "XK", "description": "Kosovo",                                         "category": "iso_territory"},
    {"code": "XL", "description": "Melilla",                                        "category": "iso_territory"},
    {"code": "XS", "description": "Serbia",                                         "category": "iso_territory"},
]
```

#### Group Codes (category = `trade_agreement`, `phytosanitary_group`, `safeguard_group`, `erga_omnes`)

```python
GROUP_ORIGINS = [

    # ── Universal ──────────────────────────────────────────────────────────────
    {
        "code": "1011",
        "description": "ERGA OMNES",
        "category": "erga_omnes",
        "is_group": True,
        "is_erga_omnes": True,
        "notes": "Applies to all origins — the standard MFN (Most Favoured Nation) measure.",
        "members": [],  # special: means ALL countries
    },

    # ── Trade / preference groups (1xxx) ──────────────────────────────────────
    {
        "code": "1006",
        "description": "EU-Canada agreement: re-imported goods",
        "category": "trade_agreement",
        "is_group": True,
        "members": ["CA"],
    },
    {
        "code": "1007",
        "description": "EU-Switzerland agreement: re-imported goods",
        "category": "trade_agreement",
        "is_group": True,
        "members": ["CH"],
    },
    {
        "code": "1008",
        "description": "All third countries",
        "category": "trade_agreement",
        "is_group": True,
        "notes": "All countries except EU member states. Subset of ERGA OMNES excluding EU.",
        "members": [],  # dynamic — all non-EU
    },
    {
        "code": "1033",
        "description": "CARIFORUM",
        "category": "trade_agreement",
        "is_group": True,
        "notes": "Caribbean Forum EPA — EU-CARIFORUM Economic Partnership Agreement.",
        "members": [
            "AG", "BS", "BB", "BZ", "DM", "DO", "GD", "GY", "HT",
            "JM", "KN", "LC", "VC", "SR", "TT",
        ],
    },
    {
        "code": "1034",
        "description": "Eastern and Southern Africa States",
        "category": "trade_agreement",
        "is_group": True,
        "notes": "ESA EPA — Comoros, Madagascar, Mauritius, Seychelles, Zimbabwe, Zambia.",
        "members": ["KM", "MG", "MU", "SC", "ZW", "ZM"],
    },
    {
        "code": "1035",
        "description": "SADC EPA",
        "category": "trade_agreement",
        "is_group": True,
        "notes": "Southern African Development Community Economic Partnership Agreement.",
        "members": ["BW", "LS", "MZ", "NA", "SZ", "ZA"],
    },
    {
        "code": "1098",
        "description": "Western Balkan countries (AL, BA, ME, MK, XK, XS)",
        "category": "trade_agreement",
        "is_group": True,
        "members": ["AL", "BA", "ME", "MK", "XK", "XS"],
    },

    # ── GSP / preference arrangements (2xxx) ──────────────────────────────────
    {
        "code": "2000",
        "description": (
            "Preferential origin in accordance with the Agreement in the form of "
            "an Exchange of Letters between the European Union and the Kingdom of Morocco "
            "on the amendment of Protocols 1 and 4 to the Euro-Mediterranean Agreement."
        ),
        "category": "trade_agreement",
        "is_group": True,
        "members": ["MA"],
    },
    {
        "code": "2005",
        "description": "GSP-EBA (Special arrangement for the least-developed countries - Everything But Arms)",
        "category": "trade_agreement",
        "is_group": True,
        "notes": (
            "EBA: duty-free quota-free access for all products from LDCs except arms/ammunition. "
            "Member list is dynamic — based on UN LDC list. Key members include: "
            "BD, BF, BI, BJ, CD, CF, ET, GN, GW, HT, KH, KM, LA, LR, LS, "
            "MG, ML, MM, MR, MW, MZ, NE, NP, RW, SD, SH, SL, SO, SS, ST, "
            "TD, TG, TL, TZ, UG, VU, WS, YE, ZM."
        ),
        "members": [
            "BD", "BF", "BI", "BJ", "CD", "CF", "ET", "GN", "GW", "HT",
            "KH", "KM", "LA", "LR", "LS", "MG", "ML", "MM", "MR", "MW",
            "MZ", "NE", "NP", "RW", "SD", "SH", "SL", "SO", "SS", "ST",
            "TD", "TG", "TL", "TZ", "UG", "VU", "WS", "YE", "ZM",
        ],
    },
    {
        "code": "2012",
        "description": "EEA - European Economic Area",
        "category": "trade_agreement",
        "is_group": True,
        "members": ["IS", "LI", "NO"],  # plus EU member states
    },
    {
        "code": "2014",
        "description": "European Economic Area - Iceland",
        "category": "trade_agreement",
        "is_group": True,
        "members": ["IS"],
    },
    {
        "code": "2020",
        "description": "GSP - General arrangements",
        "category": "trade_agreement",
        "is_group": True,
        "notes": (
            "Standard GSP: reduced duties for developing countries. "
            "Dynamic list — determined by EU GSP regulation in force. "
            "Indicative members include: AM, AZ, BO, CN, CO, EC, GE, GH, "
            "ID, IN, KE, KG, KH, LK, MD, MN, MY, NG, PH, PK, TH, TJ, TM, "
            "TN, TZ, UA, UZ, VN, ZM and others."
        ),
        "members": [
            "AM", "AZ", "BO", "CN", "CO", "EC", "GE", "GH", "ID", "IN",
            "KE", "KG", "KH", "LK", "MD", "MN", "MY", "NG", "PH", "PK",
            "TH", "TJ", "TM", "TN", "UA", "UZ", "VN", "ZM",
        ],
    },
    {
        "code": "2027",
        "description": "GSP+ (incentive arrangement for sustainable development and good governance)",
        "category": "trade_agreement",
        "is_group": True,
        "notes": (
            "GSP+: additional tariff reductions for countries that ratify and implement "
            "27 international conventions. Members include: AM, BO, CO, EC, GE, KG, "
            "MN, PA, PE, PH, SV, TJ, UZ."
        ),
        "members": ["AM", "BO", "CO", "EC", "GE", "KG", "MN", "PA", "PE", "PH", "SV", "TJ", "UZ"],
    },
    {
        "code": "2038",
        "description": "Countries submitted to import restrictions following the Chernobyl accident",
        "category": "trade_agreement",
        "is_group": True,
        "notes": "Specific control regime for food imports from affected countries.",
        "members": ["BY", "RU", "UA"],
    },
    {
        "code": "2080",
        "description": "OCTs (Overseas Countries and Territories)",
        "category": "trade_agreement",
        "is_group": True,
        "notes": (
            "EU Overseas Countries and Territories associated with EU member states. "
            "Duty-free access under the OCT Decision. "
            "Includes: GL, NC, PF, PM, TF, WF, YT, BL, MF, SH, FK, AI, VG, KY, "
            "TC, MS, BM, GI, PN, SH, AW, CW, SX, BQ and others."
        ),
        "members": ["GL", "NC", "PF", "PM", "WF", "YT", "SH", "FK", "AI", "BM", "GI"],
    },
    {
        "code": "2200",
        "description": "Central America",
        "category": "trade_agreement",
        "is_group": True,
        "notes": "EU-Central America Association Agreement (AA).",
        "members": ["CR", "GT", "HN", "NI", "PA", "SV"],
    },
    {
        "code": "2300",
        "description": "Silk or cotton handloom products",
        "category": "special_group",
        "is_group": True,
        "notes": "Special tariff treatment for traditional handloom products from eligible countries.",
        "members": [],  # product-specific, not country-limited
    },
    {
        "code": "2301",
        "description": "Certain handicraft products (Handicrafts)",
        "category": "special_group",
        "is_group": True,
        "notes": "Reduced duty for certified handicraft products.",
        "members": [],
    },
    {
        "code": "2500",
        "description": "Member countries of WTO",
        "category": "trade_agreement",
        "is_group": True,
        "notes": "All World Trade Organisation member states. Dynamic — see WTO member list.",
        "members": [],  # dynamic
    },
    {
        "code": "2501",
        "description": "Countries not members of the WTO",
        "category": "trade_agreement",
        "is_group": True,
        "notes": "Non-WTO members: primarily IRQ, IRN, PRK, SOM, SSD, LBY, SYR and others.",
        "members": ["IQ", "IR", "KP", "SO", "LY", "SY"],
    },

    # ── Phytosanitary groups (4xxx) ───────────────────────────────────────────
    {
        "code": "4000",
        "description": "Phytosanitary - G003 G027 AF, IN, IR, IQ, MX, NP, PK, ZA, US",
        "category": "phytosanitary_group",
        "is_group": True,
        "members": ["AF", "IN", "IR", "IQ", "MX", "NP", "PK", "ZA", "US"],
    },
    {
        "code": "4001",
        "description": "Phytosanitary - G008 AU, NZ, US",
        "category": "phytosanitary_group",
        "is_group": True,
        "members": ["AU", "NZ", "US"],
    },
    {
        "code": "4002",
        "description": (
            "Phytosanitary - G014 All third countries, excluding: "
            "AL, AD, AM, AZ, BY, BA, FO, GE, IS, LI, MD, ME, MK, NO, SM, XS, CH, TR, UA, GB, ex RU"
        ),
        "category": "phytosanitary_group",
        "is_group": True,
        "notes": "Exclusion list: AL, AD, AM, AZ, BY, BA, FO, GE, IS, LI, MD, ME, MK, NO, SM, XS, CH, TR, UA, GB, RU.",
        "members": [],  # special: all third countries MINUS the exclusion list
        "exclusions": ["AL", "AD", "AM", "AZ", "BY", "BA", "FO", "GE", "IS", "LI",
                        "MD", "ME", "MK", "NO", "SM", "XS", "CH", "TR", "UA", "GB", "RU"],
    },
    {
        "code": "4003",
        "description": "Phytosanitary - G016 BY, CA, CN, JP, KR, MN, KP, RU, TW, UA, US",
        "category": "phytosanitary_group",
        "is_group": True,
        "members": ["BY", "CA", "CN", "JP", "KR", "MN", "KP", "RU", "TW", "UA", "US"],
    },
    {
        "code": "4004",
        "description": "Phytosanitary - G018 CA, GB, US, VN",
        "category": "phytosanitary_group",
        "is_group": True,
        "members": ["CA", "GB", "US", "VN"],
    },
    {
        "code": "4005",
        "description": "Phytosanitary - G022 Countries of the African continent",
        "category": "phytosanitary_group",
        "is_group": True,
        "notes": "All African Union member states. Dynamic — see AU member list.",
        "members": [
            "DZ", "AO", "BJ", "BW", "BF", "BI", "CV", "CM", "CF", "TD",
            "KM", "CD", "CG", "CI", "DJ", "EG", "GQ", "ER", "SZ", "ET",
            "GA", "GM", "GH", "GN", "GW", "KE", "LS", "LR", "LY", "MG",
            "MW", "ML", "MR", "MU", "MA", "MZ", "NA", "NE", "NG", "RW",
            "ST", "SN", "SC", "SL", "SO", "ZA", "SS", "SD", "TZ", "TG",
            "TN", "UG", "ZM", "ZW",
        ],
    },
    {
        "code": "4006",
        "description": "Phytosanitary - G026 AR, AU, BO, BR, CL, NZ, UY",
        "category": "phytosanitary_group",
        "is_group": True,
        "members": ["AR", "AU", "BO", "BR", "CL", "NZ", "UY"],
    },
    {
        "code": "4007",
        "description": "Phytosanitary - G043 CA, US, VN",
        "category": "phytosanitary_group",
        "is_group": True,
        "members": ["CA", "US", "VN"],
    },
    {
        "code": "4008",
        "description": "Phytosanitary - G044 AL, AM, TR, US",
        "category": "phytosanitary_group",
        "is_group": True,
        "members": ["AL", "AM", "TR", "US"],
    },
    {
        "code": "4009",
        "description": "Phytosanitary - American continent countries",
        "category": "phytosanitary_group",
        "is_group": True,
        "notes": "All countries in North, Central, and South America.",
        "members": [
            "AG", "AR", "AW", "BB", "BL", "BO", "BR", "BS", "BZ", "CA",
            "CL", "CO", "CR", "CU", "DM", "DO", "EC", "GD", "GP", "GT",
            "GY", "HN", "HT", "JM", "KN", "LC", "MQ", "MX", "NI", "PA",
            "PE", "PR", "PY", "SR", "SV", "TT", "US", "UY", "VC", "VE",
        ],
    },
    {
        "code": "4010",
        "description": "Phytosanitary - G053 CA, US, VN, UK",
        "category": "phytosanitary_group",
        "is_group": True,
        "members": ["CA", "US", "VN", "GB"],
    },
    {
        "code": "4011",
        "description": "Phytosanitary - G054",
        "category": "phytosanitary_group",
        "is_group": True,
        "notes": "Specific phytosanitary group G054 — member list defined in EC implementing regulation.",
        "members": [],  # resolve from regulation
    },
    {
        "code": "4012",
        "description": "Phytosanitary - G056 AF, IN, IR, KG, PK, TJ, TM, UZ",
        "category": "phytosanitary_group",
        "is_group": True,
        "members": ["AF", "IN", "IR", "KG", "PK", "TJ", "TM", "UZ"],
    },
    {
        "code": "4013",
        "description": "Phytosanitary - G057 CN, KR, KP, RU, TW, VN",
        "category": "phytosanitary_group",
        "is_group": True,
        "members": ["CN", "KR", "KP", "RU", "TW", "VN"],
    },

    # ── Safeguard groups (5xxx) ───────────────────────────────────────────────
    {
        "code": "5005",
        "description": "Countries subject to safeguard measures",
        "category": "safeguard_group",
        "is_group": True,
        "notes": "Dynamic — countries named in the safeguard regulation currently in force.",
        "members": [],  # set per active regulation
    },
    {
        "code": "5007",
        "description": "Countries subject to safeguard duties - ferro-alloying elements",
        "category": "safeguard_group",
        "is_group": True,
        "notes": "Countries subject to specific safeguard on ferro-alloy imports.",
        "members": [],  # set per active regulation
    },
]
```

---

### ORIGIN RESOLUTION LOGIC

When a lookup is made for a given `(hs_code, origin_country_iso2, destination)`,
the pipeline must find all measures that apply. A measure applies if its `origin_code`
matches the shipment origin. The resolution order is:

```python
def measure_applies_to_origin(measure_origin_code: str, shipment_iso2: str) -> bool:
    """
    Determine whether a measure with the given origin_code applies
    to a shipment originating from shipment_iso2.
    """
    # 1. ERGA OMNES — always matches
    if measure_origin_code == "1011":
        return True

    # 2. Direct country or territory match
    if measure_origin_code == shipment_iso2:
        return True

    # 3. Group membership match
    group = get_origin_group(measure_origin_code)
    if group and group.is_group:

        # 4001-style explicit list
        if shipment_iso2 in group.members:
            return True

        # 4002-style exclusion list (all countries EXCEPT these)
        if hasattr(group, "exclusions") and group.exclusions:
            return shipment_iso2 not in group.exclusions

        # 1008-style "all third countries" — all except EU member states
        if measure_origin_code == "1008":
            return shipment_iso2 not in EU_MEMBER_STATES

        # 2500-style WTO members — check WTO list
        if measure_origin_code == "2500":
            return shipment_iso2 in WTO_MEMBERS

        # 2501-style non-WTO members
        if measure_origin_code == "2501":
            return shipment_iso2 not in WTO_MEMBERS

    return False
```

**EU member states** — define as a constant:

```python
EU_MEMBER_STATES = frozenset([
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI",
    "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
    "NL", "PL", "PT", "RO", "SE", "SI", "SK",
])
```

---

### DATABASE SCHEMA — MEASURE ORIGIN LINK

Add origin to the `measures` table and a lookup index:

```sql
-- Add to existing measures table
ALTER TABLE measures ADD COLUMN origin_code VARCHAR(10) REFERENCES origin_codes(code);
ALTER TABLE measures ADD COLUMN origin_is_erga_omnes BOOLEAN DEFAULT FALSE;
ALTER TABLE measures ADD COLUMN origin_is_group BOOLEAN DEFAULT FALSE;

-- Fast index for origin-based lookup
CREATE INDEX idx_measures_origin_code ON measures(origin_code);
CREATE INDEX idx_measures_hs_origin ON measures(goods_nomenclature_sid, origin_code);
```

---

### API — ORIGIN FIELDS IN LOOKUP RESPONSE

Add to the `/tariff/lookup?hs={code}&origin={iso2}&destination={iso2}` response:

```json
{
  "origin": {
    "code": "UA",
    "description": "Ukraine",
    "category": "iso_country",
    "is_group": false
  },
  "applicable_measures": [
    {
      "measure_type": "preferential",
      "origin_code": "UA",
      "origin_description": "Ukraine",
      "duty": { "duty_rate": 0.0, "human_readable": "0%" },
      "conditions": [...]
    },
    {
      "measure_type": "mfn",
      "origin_code": "1011",
      "origin_description": "ERGA OMNES",
      "duty": { "duty_rate": 12.0, "human_readable": "12%" },
      "conditions": []
    }
  ],
  "best_rate": {
    "origin_code": "UA",
    "origin_description": "Ukraine",
    "duty_rate": 0.0,
    "human_readable": "0% (Ukraine preferential rate)"
  }
}
```

**Rate selection logic**: when multiple measures match the same origin,
apply the following priority order:

1. Tariff suspension (measure type 112) — lowest priority number wins
2. Quota (measure type 143) — if quota open
3. Preferential rate (country-specific, e.g. `UA`)
4. Trade agreement group rate (e.g. `2020` GSP)
5. ERGA OMNES MFN rate (`1011`) — fallback of last resort

Always return ALL matching measures to the API consumer, ranked by priority,
with `best_rate` pre-selected.

---

### WARNINGS — ORIGIN-RELATED

Add to `calculated.warnings[]`:

- Any `ERGA OMNES` measure with an overriding country-specific measure: `"A preferential rate applies for {origin}. The MFN rate of {mfn_rate} is superseded."`
- If origin is a phytosanitary group (`4xxx`): `"Additional phytosanitary controls apply for goods from {origin}. A plant health certificate may be required."`
- If origin is a safeguard group (`5xxx`): `"Safeguard measures are in force for goods from {origin}. Additional duties may apply."`
- If origin is `2501` (non-WTO): `"This country is not a WTO member. Standard MFN rates may not apply — verify applicable treaty obligations."`
- If origin is `KP` (North Korea) or `BY` (Belarus) or `RU` (Russian Federation): `"Sanctions or trade restrictions may apply to goods from this origin. Verify current restrictions before shipping."`
- If origin_code is `2038` (Chernobyl restriction group): `"Import restrictions apply to certain food and feed products from this origin following the Chernobyl accident."`

---

### PIPELINE MODULE — `app/pipeline/origin_codes.py` (NEW)

```python
"""
Seed and manage the origin_codes and origin_group_members reference tables.
Run at bootstrap and refresh weekly from TARIC updates.
"""
from app.database import get_session
from app.models import OriginCode, OriginGroupMember
from app.pipeline.origin_data import ISO_ORIGINS, GROUP_ORIGINS


def seed_origin_codes() -> None:
    """Upsert all origin codes into the database."""
    with get_session() as session:
        for entry in ISO_ORIGINS:
            obj = OriginCode(
                code=entry["code"],
                description=entry["description"],
                category=entry["category"],
                is_group=False,
                is_erga_omnes=False,
                iso_alpha2=entry["code"] if len(entry["code"]) == 2 else None,
            )
            session.merge(obj)

        for entry in GROUP_ORIGINS:
            obj = OriginCode(
                code=entry["code"],
                description=entry["description"],
                category=entry["category"],
                is_group=entry.get("is_group", True),
                is_erga_omnes=entry.get("is_erga_omnes", False),
                notes=entry.get("notes"),
            )
            session.merge(obj)

            # Seed group membership rows
            for member_iso2 in entry.get("members", []):
                member = OriginGroupMember(
                    group_code=entry["code"],
                    member_iso2=member_iso2,
                )
                session.merge(member)

        session.commit()


def resolve_origin_groups(iso2: str) -> list[str]:
    """
    Return all origin_codes (including group codes) that include
    the given ISO2 country code as a member.
    Used during measure lookup to find all relevant measures.
    """
    with get_session() as session:
        memberships = (
            session.query(OriginGroupMember.group_code)
            .filter(OriginGroupMember.member_iso2 == iso2)
            .all()
        )
        group_codes = [m.group_code for m in memberships]
        # Always include ERGA OMNES and direct country code
        return [iso2, "1011"] + group_codes
```

---

### PROJECT STRUCTURE — ADDITIONS

```
veritariff/
├── app/
│   ├── pipeline/
│   │   ├── origin_codes.py        ← NEW: seed + resolve origin groups
│   │   ├── origin_data.py         ← NEW: ISO_ORIGINS + GROUP_ORIGINS seed lists
│   ├── models/
│   │   ├── origin_code.py         ← NEW: ORM model for origin_codes table
│   │   ├── origin_group_member.py ← NEW: ORM model for origin_group_members table
```

---

### TESTS — `tests/test_origin_resolution.py` (NEW)

Write pytest tests covering:

1. `measure_applies_to_origin("1011", "CN")` → `True` (ERGA OMNES matches all)
2. `measure_applies_to_origin("UA", "UA")` → `True` (direct country match)
3. `measure_applies_to_origin("UA", "CN")` → `False` (wrong country)
4. `measure_applies_to_origin("2020", "VN")` → `True` (VN is GSP member)
5. `measure_applies_to_origin("2020", "US")` → `False` (US not in GSP)
6. `measure_applies_to_origin("4003", "CN")` → `True` (CN in phyto group G016)
7. `measure_applies_to_origin("4002", "GB")` → `False` (GB is excluded from G014)
8. `measure_applies_to_origin("4002", "IN")` → `True` (IN not excluded from G014)
9. `measure_applies_to_origin("1098", "XS")` → `True` (Serbia in Western Balkans)
10. `measure_applies_to_origin("2005", "BD")` → `True` (Bangladesh is EBA/LDC)
11. `resolve_origin_groups("UA")` returns `["UA", "1011", "2020", "2038"]` (or superset)
12. `resolve_origin_groups("US")` returns `["US", "1011", "4001", "4003", "4009"]`


---

## LOOKUP RESOLUTION & FALLBACK LOGIC (NEW SECTION — v5 ADDITION)

This section defines the exact behaviour of the `/tariff/lookup` endpoint when
the queried origin has no direct TARIC measure row. It was written from observed
production behaviour on HS 7208510000 origin=GB destination=DE.

---

### The GB → EU problem (and every equivalent case)

After Brexit, GB is a third country to the EU. TARIC contains **zero rows** with
`origin_code = 'GB'` for standard duty measures — this is correct source data,
not a bug. The MFN rate applies via `origin_code = '1011'` (ERGA OMNES).

The same situation occurs for ANY country that:
- Has no EU bilateral trade agreement
- Has a trade agreement that does not cover this specific HS code
- Is subject to sanctions / restrictions that suspended the preference
- Has a preference only within a quota (and quota is exhausted)

The API must NEVER return `duty: null` when a valid ERGA OMNES row exists.
The ERGA OMNES (1011) row IS the rate for that country — it is not a fallback
of last resort, it IS the applicable rate for all third countries without a
more specific measure.

---

### Mandatory ingest rule — measure type 103

TARIC measure type `103` = Third country duty (MFN / ERGA OMNES).
This is the single most important measure type in the entire dataset.

**In `eu_taric.py`:**

```python
# These measure type IDs MUST map to duty_rates — never drop them
MFN_MEASURE_TYPE_IDS = {
    "103",   # Third country duty (ERGA OMNES — MFN)
    "105",   # Third country duty (autonomous)
    "106",   # Third country duty (conventional)
    "112",   # Customs union duty
    "115",   # Autonomous tariff suspension
    "117",   # End-use tariff
    "119",   # Airworthiness tariffs
    "142",   # Tariff preference (generic)
    "143",   # Tariff preference (GSP)
    "145",   # Tariff preference (bilateral)
}

def route_measure(measure_type_id: str, ...) -> str | None:
    if measure_type_id in MFN_MEASURE_TYPE_IDS:
        return "DUTY"
    # ... rest of routing
```

**Post-ingest validation** — run after every TARIC delta import:

```python
def validate_erga_omnes_coverage(db, market: str = "EU") -> list[str]:
    """
    After each ingest, verify that every commodity code that has ANY measure
    also has at least one ERGA OMNES (1011) duty row.
    Returns a list of HS codes missing MFN coverage.
    """
    all_codes = db.execute(
        "SELECT DISTINCT commodity_code FROM tariff_measures WHERE market = :m",
        {"m": market}
    ).scalars().all()

    missing = []
    for code in all_codes:
        has_mfn = db.query(DutyRate).filter(
            DutyRate.commodity_code == code,
            DutyRate.origin_code == "1011",
            DutyRate.market == market,
        ).first()
        if not has_mfn:
            missing.append(code)
            logger.error(
                f"MFN gap: no ERGA OMNES duty row for {code} market={market}. "
                f"Check TARIC ingest for measure type 103."
            )
    return missing
```

---

### Lookup resolution algorithm (complete, ordered)

Replace the existing lookup logic with this exact priority chain.
Every step is mandatory — never skip a step:

```python
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ResolvedRate:
    origin_code: str
    origin_name: str
    rate_basis: str
    duty_rate: Optional[float]
    duty_amount: Optional[float]
    duty_unit: Optional[str]
    human_readable: Optional[str]
    conditions: list
    warnings: list
    source_measure_type: str
    valid_from: Optional[str]
    valid_to: Optional[str]


def resolve_duty(
    hs_code: str,
    origin_iso2: str,
    destination_market: str,
    db,
    reference_date: str,  # today's date — for valid_from/valid_to filtering
) -> tuple[Optional[ResolvedRate], list[str]]:
    """
    Resolve the best applicable duty rate for a shipment.
    Returns (best_rate, warnings_list).
    Never returns (None, []) — always explains why no rate was found.
    """
    warnings = []

    # ── STEP 1: Build the full ordered resolution list ───────────────────────
    # Order: most specific → least specific
    candidate_codes = build_origin_resolution_list(origin_iso2, db)
    # e.g. for GB: ["GB", "1011"]
    # for IN:      ["IN", "2005", "2020", "2500", "1011"]
    # for TR:      ["TR", "1008", "2500", "1011"]

    # ── STEP 2: Query ALL duty rows for this HS code and ALL candidate origins
    all_rows = db.query(DutyRate).filter(
        DutyRate.commodity_code == hs_code,
        DutyRate.market == destination_market,
        DutyRate.origin_code.in_(candidate_codes),
        # Date filter — include rows with no expiry OR expiry in the future
        or_(DutyRate.valid_to == None, DutyRate.valid_to >= reference_date),
        or_(DutyRate.valid_from == None, DutyRate.valid_from <= reference_date),
    ).all()

    if not all_rows:
        # ── STEP 3: Hard fallback — try 1011 with NO date filter ──────────────
        # TARIC sometimes has perpetual rows with null valid_from/valid_to.
        fallback = db.query(DutyRate).filter(
            DutyRate.commodity_code == hs_code,
            DutyRate.market == destination_market,
            DutyRate.origin_code == "1011",
        ).first()

        if fallback:
            warnings.append(
                "No date-bounded MFN row found; using undated ERGA OMNES record."
            )
            all_rows = [fallback]
        else:
            # ── STEP 4: Data gap — report clearly ────────────────────────────
            warnings.append(
                f"No duty data found for HS {hs_code} from origin {origin_iso2} "
                f"into {destination_market}. "
                f"ERGA OMNES (MFN) row is also missing — "
                f"check TARIC ingest for measure type 103 on this commodity."
            )
            logger.error(
                f"COMPLETE_DUTY_GAP hs={hs_code} origin={origin_iso2} "
                f"market={destination_market} candidates={candidate_codes}"
            )
            return None, warnings

    # ── STEP 5: Pick best rate by origin specificity ─────────────────────────
    SPECIFICITY = {
        "country":       1,
        "group_numeric": 2,
        "phytosanitary": 3,
        "safeguard":     4,
        "erga_omnes":    5,
        "unknown":       6,
    }

    # Sort: most specific first, then lowest rate within same specificity
    def sort_key(row):
        origin = db.query(Origin).filter_by(origin_code=row.origin_code).first()
        code_type = origin.origin_code_type if origin else "unknown"
        spec = SPECIFICITY.get(code_type, 6)
        rate = row.duty_rate if row.duty_rate is not None else 9999
        return (spec, rate)

    all_rows.sort(key=sort_key)
    best = all_rows[0]

    # ── STEP 6: Build warnings based on what we found ────────────────────────
    best_origin = db.query(Origin).filter_by(origin_code=best.origin_code).first()

    if best.origin_code == "1011":
        # Explain WHY the MFN rate applies
        warnings.append(
            f"{origin_iso2} has no bilateral trade agreement with the "
            f"{destination_market}. The MFN (Most Favoured Nation) rate applies. "
            f"This is the standard third-country duty."
        )

    if origin_iso2 == "GB" and destination_market == "EU":
        warnings.append(
            "The UK left the EU in 2021. No EU-UK preferential duty agreement "
            "covers goods of UK origin entering the EU. The standard MFN rate applies."
        )

    # ── STEP 7: Check for stacked measures (safeguard, anti-dumping) ─────────
    stacked = check_stacked_measures(hs_code, origin_iso2, destination_market,
                                     reference_date, db)
    warnings.extend(stacked.get("warnings", []))

    return build_resolved_rate(best, best_origin, warnings), warnings


def build_origin_resolution_list(iso2: str, db) -> list[str]:
    """
    Build the full ordered list of origin codes that could apply to
    a shipment from this country. Most specific first.
    """
    codes = []

    # 1. Exact country code
    codes.append(iso2.upper())

    # 2. Any named groups that contain this country
    groups = db.query(Origin).filter(
        Origin.member_iso2_codes.contains([iso2.upper()]),
        Origin.is_group == True,
        Origin.origin_code_type.in_(["group_numeric", "safeguard"]),
    ).order_by(Origin.origin_code).all()
    codes.extend(g.origin_code for g in groups)

    # 3. GSP eligibility (checked against a separate gsp_eligibility table
    #    or a hardcoded set — depends on data availability)
    gsp = resolve_gsp_tier(iso2, db)
    if gsp:
        codes.append(gsp)  # '2005', '2027', or '2020'

    # 4. WTO membership
    wto = resolve_wto_code(iso2, db)
    if wto:
        codes.append(wto)  # '2500' or '2501'

    # 5. "All third countries" group
    codes.append("1008")

    # 6. ERGA OMNES — always last
    codes.append("1011")

    # Deduplicate preserving order
    seen = set()
    return [c for c in codes if not (c in seen or seen.add(c))]


def check_stacked_measures(
    hs_code: str,
    origin_iso2: str,
    destination_market: str,
    reference_date: str,
    db,
) -> dict:
    """
    Check for measures that STACK ON TOP of the base duty:
    - Safeguard duties (measure type 696)
    - Anti-dumping duties (measure type 551, 552, 553, 554)
    - Countervailing duties (measure type 555, 556)
    - Import controls / prohibitions (measure type 763, 745, 277)

    Returns a dict with 'stacked_duties' and 'warnings' lists.
    """
    stacked_duties = []
    warnings = []

    STACKING_MEASURE_TYPES = {
        "696": "safeguard",
        "551": "anti_dumping",
        "552": "anti_dumping",
        "553": "anti_dumping",
        "554": "anti_dumping",
        "555": "countervailing",
        "556": "countervailing",
        "763": "import_control",
        "745": "import_prohibition",
        "277": "import_restriction",
    }

    # Build stacking-eligible origin codes
    candidate_codes = build_origin_resolution_list(origin_iso2, db)

    rows = db.query(TariffMeasure).filter(
        TariffMeasure.commodity_code == hs_code,
        TariffMeasure.market == destination_market,
        TariffMeasure.measure_type_code.in_(STACKING_MEASURE_TYPES.keys()),
        TariffMeasure.origin_code.in_(candidate_codes),
        or_(TariffMeasure.valid_to == None,
            TariffMeasure.valid_to >= reference_date),
        or_(TariffMeasure.valid_from == None,
            TariffMeasure.valid_from <= reference_date),
    ).all()

    for row in rows:
        measure_kind = STACKING_MEASURE_TYPES[row.measure_type_code]

        if measure_kind == "safeguard":
            # Check if this country is actually in the safeguard group
            if is_country_in_safeguard_group(origin_iso2, row.origin_code, db):
                stacked_duties.append({
                    "type": "safeguard",
                    "duty_rate": row.duty_rate,
                    "origin_code": row.origin_code,
                    "legal_base": row.details.get("legal_base"),
                    "valid_to": row.valid_to,
                })
                warnings.append(
                    f"SAFEGUARD DUTY: An additional {row.duty_rate}% safeguard duty "
                    f"applies on top of the base rate "
                    f"(legal base: {row.details.get('legal_base', 'unknown')}). "
                    f"A tariff quota (order no {row.details.get('order_no', '?')}) "
                    f"may be available at 0% — check quota balance before shipping."
                )

        elif measure_kind in ("anti_dumping", "countervailing"):
            stacked_duties.append({
                "type": measure_kind,
                "duty_rate": row.duty_rate,
                "origin_code": row.origin_code,
            })
            warnings.append(
                f"{'ANTI-DUMPING' if measure_kind == 'anti_dumping' else 'COUNTERVAILING'} "
                f"DUTY: An additional duty applies. "
                f"Rate: {row.duty_rate}%. This stacks on top of the base customs duty."
            )

        elif measure_kind in ("import_control", "import_prohibition",
                               "import_restriction"):
            # Parse required certificates from duty_text
            certs = parse_cert_codes_from_duty_text(
                row.details.get("duty_text", "")
            )
            warnings.append(
                f"IMPORT CONTROL: This commodity is subject to import controls "
                f"from origin {origin_iso2} "
                f"(regulation {row.details.get('legal_base', 'unknown')}). "
                + (f"Required certificates: {', '.join(certs)}." if certs else
                   "Check the specific import conditions.")
            )

    return {"stacked_duties": stacked_duties, "warnings": warnings}


def is_country_in_safeguard_group(iso2: str, group_code: str, db) -> bool:
    """
    Determine if a country is subject to a safeguard group measure.
    Safeguard group 5005 = 'Countries subject to safeguard measures'.
    The EU publishes a list — in the absence of member_iso2_codes being fully
    seeded, default to TRUE (conservative — better to warn than to miss it).
    """
    origin = db.query(Origin).filter_by(origin_code=group_code).first()
    if origin and origin.member_iso2_codes:
        return iso2.upper() in origin.member_iso2_codes
    # If member list is not seeded: default conservatively to True
    # and include a note in the warning
    return True
```

---

### Certificate code resolution (fix for "Unknown — code X")

Your current response shows:
```json
"certificate_details": {
  "L-143": "Unknown — code L-143",
  "Y-859": "Unknown — code Y-859",
  ...
}
```

This means the `certificate_codes` table is not seeded. The full seed list is
in the v4 section of this prompt. Additionally, implement auto-resolution:

```python
def resolve_certificate_details(cert_codes: list[str], db) -> dict:
    """
    Resolve human-readable descriptions for certificate codes found in
    measure conditions. Falls back gracefully for unknown codes.
    """
    result = {}
    for code in cert_codes:
        cert = db.query(CertificateCode).filter_by(code=code).first()
        if cert:
            result[code] = {
                "code": code,
                "description": cert.description,
                "category": cert.category,
                "action_required": build_cert_action(cert),
            }
        else:
            # Auto-insert placeholder and flag for review
            logger.warning(f"Unknown certificate code: {code}")
            db.add(CertificateCode(
                code=code,
                description=f"Certificate {code} — description pending",
                category="unknown",
            ))
            db.commit()
            result[code] = {
                "code": code,
                "description": f"Certificate {code} — see TARIC documentation",
                "category": "unknown",
                "action_required": "Verify this certificate requirement with your "
                                   "customs broker or the relevant authority.",
            }
    return result


def build_cert_action(cert) -> str:
    """Generate a plain-English action instruction for a certificate."""
    actions = {
        "sanitary":       "Obtain a phytosanitary or veterinary certificate "
                          "from the competent authority in the exporting country.",
        "origin":         "Provide documentary proof of preferential origin "
                          "(e.g. EUR.1, REX declaration, or statement on invoice).",
        "quota_licence":  "Apply for a Tariff Rate Quota licence before shipment. "
                          "Check available quota balance with the relevant authority.",
        "end_use":        "Obtain end-use authorisation from the customs authority "
                          "before importation.",
        "licence":        "Ensure a valid import licence is held before shipment.",
        "compliance":     "Provide the required compliance certificate or "
                          "declaration with the customs entry.",
        "exemption":      "Provide the exemption declaration to claim this relief.",
        "cites":          "Obtain a CITES import/export permit from the management "
                          "authority in both the origin and destination country.",
        "control":        "Ensure the required control document accompanies the "
                          "shipment and is presented at the border.",
        "anti_dumping":   "No action required — this is a declaration confirming "
                          "goods are not subject to anti-dumping measures.",
    }
    return actions.get(cert.category, "Contact your customs broker for guidance.")
```

---

### API response — fixed schema for zero-rate and missing-rate cases

The current response returns `duty: null` for many fields when no specific
rate is found. This must be replaced with explicit, actionable output.

**Case 1 — ERGA OMNES (MFN) rate applies (e.g. GB → EU):**
```json
{
  "duty": {
    "rate_type": "MFN",
    "rate_basis": "erga_omnes",
    "origin_code": "1011",
    "origin_name": "ERGA OMNES",
    "duty_rate": 0.0,
    "human_readable": "0% (MFN — standard third-country duty)",
    "conditions": []
  },
  "calculated": {
    "effective_duty_rate": 0.0,
    "warnings": [
      "GB has no bilateral preferential trade agreement with the EU. The MFN rate applies.",
      "SAFEGUARD: A 25% safeguard duty may apply (Regulation 0159/19). Check quota availability.",
      "IMPORT CONTROL: Certificates L-139, Y-859, Y-878, L-143 required (Regulation 0833/14)."
    ]
  }
}
```

**Case 2 — Safeguard stacked on MFN:**
```json
{
  "duty": {
    "rate_type": "MFN",
    "duty_rate": 0.0,
    "human_readable": "0% MFN base rate"
  },
  "stacked_duties": [
    {
      "type": "safeguard",
      "duty_rate": 25.0,
      "origin_code": "5005",
      "legal_base": "Regulation 0159/19",
      "valid_to": "2026-06-30",
      "human_readable": "25% safeguard duty (additional, on top of base rate)",
      "quota_available": true,
      "quota_order_no": "098617",
      "quota_rate": 0.0,
      "quota_note": "0% within quota — verify balance before shipment"
    }
  ],
  "calculated": {
    "effective_duty_rate": 25.0,
    "effective_duty_rate_within_quota": 0.0,
    "note": "Total duty = MFN base (0%) + safeguard (25%) = 25% unless quota applies"
  }
}
```

**Case 3 — Complete data gap (no MFN row in DB):**
```json
{
  "duty": null,
  "calculated": {
    "warnings": [
      "DATA GAP: No duty record found for HS 7208510000 origin GB market EU.",
      "The ERGA OMNES (MFN) row is also missing from the database.",
      "This indicates a pipeline ingest problem — measure type 103 may have been dropped.",
      "Contact support or re-run the TARIC ingest for this commodity."
    ]
  }
}
```

The difference between Case 1 and Case 3 must be clear to the frontend:
Case 1 = valid response (rate is genuinely 0% or known); Case 3 = data problem.
Add a `data_status` field to distinguish:
```json
"data_status": "complete"       // Case 1 — rate found and returned
"data_status": "mfn_fallback"   // Case 2 — no specific rate, MFN applied
"data_status": "data_gap"       // Case 3 — MFN row also missing
"data_status": "partial"        // Some measures found but base duty missing
```

---

### origin_name hydration (fix for "GB" instead of "United Kingdom")

Your response shows `"origin_name": "GB"` — the name was never resolved.
The ingest stored the raw code as the name. Fix in two places:

**1. Ingest fix — `eu_taric.py`:**
```python
def resolve_origin_name(origin_code: str, origin_text: str, db) -> str:
    """Always prefer the seeded name over the raw TARIC text field."""
    seeded = db.query(Origin).filter_by(origin_code=origin_code).first()
    if seeded and seeded.origin_name and seeded.origin_name != origin_code:
        return seeded.origin_name
    # Fallback to TARIC text, then to code itself
    return origin_text or origin_code
```

**2. API fix — hydrate on read:**
```python
def hydrate_origin_name(origin_code: str, db) -> str:
    origin = db.query(Origin).filter_by(origin_code=origin_code).first()
    return origin.origin_name if origin else origin_code
```

Call `hydrate_origin_name` on every `origin_code` in the response before
serialising — never expose raw codes as names to the frontend.

---

### Tariff quota handling (fix for empty tariff_quotas in response)

Your response returns `"tariff_quotas": []` even though the origin_matrix
shows 5 active tariff quota records (5005, ID, IN, KR, TR).
The quota records ARE in the DB — they are just not being returned.

Fix: always include tariff quota records in the response when they exist
for ANY origin code in the resolved list OR in the available_origin_codes:

```python
def get_tariff_quotas(
    hs_code: str,
    origin_iso2: str,
    destination_market: str,
    reference_date: str,
    db,
) -> list[dict]:
    """
    Return all active tariff quotas relevant to this shipment.
    Includes quotas for:
    - The exact origin country
    - Any safeguard/group codes that include this country
    - ERGA OMNES quotas (apply to all countries)
    """
    candidate_codes = build_origin_resolution_list(origin_iso2, db)

    quotas = db.query(TariffMeasure).filter(
        TariffMeasure.commodity_code == hs_code,
        TariffMeasure.market == destination_market,
        TariffMeasure.measure_type == "TARIFF_QUOTA",
        TariffMeasure.origin_code.in_(candidate_codes),
        or_(TariffMeasure.valid_to == None,
            TariffMeasure.valid_to >= reference_date),
    ).all()

    result = []
    for q in quotas:
        origin_name = hydrate_origin_name(q.origin_code, db)
        applies_to_this_country = (
            q.origin_code == origin_iso2
            or q.origin_code == "1011"
            or is_country_in_safeguard_group(origin_iso2, q.origin_code, db)
        )
        result.append({
            "order_no": q.details.get("order_no"),
            "origin_code": q.origin_code,
            "origin_name": origin_name,
            "quota_duty_rate": q.duty_rate,
            "valid_from": q.valid_from,
            "valid_to": q.valid_to,
            "legal_base": q.details.get("legal_base"),
            "applies_to_origin": applies_to_this_country,
            "note": (
                "This quota rate applies to your shipment — check balance availability."
                if applies_to_this_country else
                f"This quota applies to {origin_name} origin only, not {origin_iso2}."
            ),
        })

    return result
```

---

### Non-tariff measures and import controls (fix for empty non_tariff_measures)

Your response returns `"non_tariff_measures": []` even though two IMPORT_CONTROL
records exist (origin 1008 and RU). The NTMs ARE in the DB — they are just not
being mapped into the response.

Fix: query NTMs separately and always include them when they apply to the resolved
origin codes:

```python
def get_non_tariff_measures(
    hs_code: str,
    origin_iso2: str,
    destination_market: str,
    reference_date: str,
    db,
) -> list[dict]:
    NTM_MEASURE_TYPES = {
        "763": "Import control",
        "745": "Import prohibition",
        "277": "Import restriction",
        "750": "Import surveillance",
        "724": "Import licensing",
        "730": "Import monitoring",
        "481": "Phytosanitary certificate required",
        "482": "Veterinary certificate required",
        "483": "Organic farming certificate required",
    }

    candidate_codes = build_origin_resolution_list(origin_iso2, db)

    rows = db.query(TariffMeasure).filter(
        TariffMeasure.commodity_code == hs_code,
        TariffMeasure.market == destination_market,
        TariffMeasure.measure_type_code.in_(NTM_MEASURE_TYPES.keys()),
        TariffMeasure.origin_code.in_(candidate_codes),
        or_(TariffMeasure.valid_to == None,
            TariffMeasure.valid_to >= reference_date),
    ).all()

    result = []
    for row in rows:
        certs = parse_cert_codes_from_duty_text(
            row.details.get("duty_text", "")
        )
        cert_details = resolve_certificate_details(certs, db)

        result.append({
            "measure_type": NTM_MEASURE_TYPES.get(
                row.measure_type_code, row.measure_type_code
            ),
            "measure_type_code": row.measure_type_code,
            "origin_code": row.origin_code,
            "origin_name": hydrate_origin_name(row.origin_code, db),
            "legal_base": row.details.get("legal_base"),
            "valid_from": row.valid_from,
            "valid_to": row.valid_to,
            "required_certificates": certs,
            "certificate_details": cert_details,
            "applies_to_origin": row.origin_code in [origin_iso2, "1008", "1011"],
            "summary": build_ntm_summary(row, certs, origin_iso2),
        })

    return result


def build_ntm_summary(row, certs: list[str], origin_iso2: str) -> str:
    """Build a single plain-English summary sentence for an NTM."""
    cert_str = (
        f" Required documents: {', '.join(certs)}."
        if certs else ""
    )
    return (
        f"Import control applies to goods from {origin_iso2} under "
        f"{row.details.get('legal_base', 'EU regulation')}.{cert_str} "
        f"Verify compliance before shipment."
    )
```

---

### Final response assembly — complete `/tariff/lookup` handler

```python
@router.get("/tariff/lookup")
async def tariff_lookup(
    hs_code: str,
    origin: str,
    destination: str,
    full_report: bool = False,
    db: Session = Depends(get_db),
):
    reference_date = date.today().isoformat()
    destination_market = resolve_destination_market(destination)  # "EU" or "UK"

    # 1. Resolve origin
    origin_record = db.query(Origin).filter_by(origin_code=origin.upper()).first()
    if not origin_record:
        auto_insert_unknown_origin(origin.upper(), origin.upper(), db)
        origin_record = db.query(Origin).filter_by(origin_code=origin.upper()).first()

    # 2. Resolve duty rate (with full fallback chain)
    best_rate, duty_warnings = resolve_duty(
        hs_code, origin.upper(), destination_market, db, reference_date
    )

    # 3. Get stacked duties (safeguard, AD, CVD)
    stacked = check_stacked_measures(
        hs_code, origin.upper(), destination_market, reference_date, db
    )

    # 4. Get tariff quotas
    quotas = get_tariff_quotas(
        hs_code, origin.upper(), destination_market, reference_date, db
    )

    # 5. Get non-tariff measures
    ntms = get_non_tariff_measures(
        hs_code, origin.upper(), destination_market, reference_date, db
    )

    # 6. Get VAT
    vat = get_vat_rate(destination, db)

    # 7. Get supplementary units
    sup_units = get_supplementary_units(hs_code, destination_market, db)

    # 8. Calculate effective rate
    base_rate = best_rate.duty_rate if best_rate else None
    safeguard_rate = sum(
        s["duty_rate"] for s in stacked.get("stacked_duties", [])
        if s["type"] == "safeguard" and s["duty_rate"] is not None
    )
    effective_rate = (
        (base_rate or 0) + safeguard_rate
        if base_rate is not None else None
    )

    # 9. Determine data_status
    if best_rate is None:
        data_status = "data_gap"
    elif best_rate.origin_code == "1011":
        data_status = "mfn_fallback"
    elif best_rate.origin_code == origin.upper():
        data_status = "complete"
    else:
        data_status = "partial"

    # 10. Collect all warnings (deduplicated)
    all_warnings = list(dict.fromkeys(
        duty_warnings + stacked.get("warnings", [])
    ))

    return {
        "data": {
            "hs_code": hs_code,
            "origin_country": origin.upper(),
            "destination_country": destination.upper(),
            "destination_market": destination_market,
            "data_status": data_status,
            "origin": serialize_origin(origin_record),
            "duty": serialize_rate(best_rate) if best_rate else None,
            "stacked_duties": stacked.get("stacked_duties", []),
            "tariff_quotas": quotas,
            "non_tariff_measures": ntms,
            "supplementary_units": sup_units,
            "vat": vat,
            "calculated": {
                "base_duty_rate": base_rate,
                "safeguard_rate": safeguard_rate or None,
                "effective_duty_rate": effective_rate,
                "effective_duty_rate_within_quota": (
                    min(q["quota_duty_rate"] for q in quotas
                        if q.get("applies_to_origin"))
                    if any(q.get("applies_to_origin") for q in quotas)
                    else None
                ),
                "vat_applies_to": "goods_value + duty",
                "warnings": all_warnings,
            },
            "origin_resolution": [
                serialize_origin(db.query(Origin).filter_by(
                    origin_code=c).first() or Origin(origin_code=c))
                for c in build_origin_resolution_list(origin.upper(), db)
            ],
        }
    }
```

---

### Tests for lookup resolution — `tests/test_lookup_resolution.py`

Add these pytest tests. They must all pass before deploying:

```python
"""Tests for the core lookup resolution logic."""

def test_gb_eu_returns_mfn_not_null(client, db_with_erga_omnes_seed):
    """GB has no EU preferential rate — must return MFN, never null duty."""
    r = client.get("/tariff/lookup?hs_code=7208510000&origin=GB&destination=DE")
    data = r.json()["data"]
    assert data["duty"] is not None
    assert data["duty"]["origin_code"] == "1011"
    assert data["data_status"] == "mfn_fallback"
    assert any("MFN" in w or "no bilateral" in w.lower()
               for w in data["calculated"]["warnings"])

def test_mfn_fallback_includes_safeguard_warning(client, db_with_safeguard_seed):
    """When a safeguard applies to a third country, warn about it."""
    r = client.get("/tariff/lookup?hs_code=7208510000&origin=GB&destination=DE")
    data = r.json()["data"]
    assert any("safeguard" in w.lower()
               for w in data["calculated"]["warnings"])

def test_tariff_quotas_not_empty_when_records_exist(client, db_with_quota_seed):
    """Quota records in DB must appear in the response."""
    r = client.get("/tariff/lookup?hs_code=7208510000&origin=TR&destination=DE")
    data = r.json()["data"]
    assert len(data["tariff_quotas"]) > 0
    tr_quota = next((q for q in data["tariff_quotas"]
                     if q["origin_code"] == "TR"), None)
    assert tr_quota is not None
    assert tr_quota["applies_to_origin"] is True

def test_ntm_not_empty_when_import_control_exists(client, db_with_ntm_seed):
    """Import control measures in DB must appear in non_tariff_measures."""
    r = client.get("/tariff/lookup?hs_code=7208510000&origin=GB&destination=DE")
    data = r.json()["data"]
    assert len(data["non_tariff_measures"]) > 0
    assert any(n["measure_type_code"] == "763"
               for n in data["non_tariff_measures"])

def test_certificate_details_not_unknown(client, db_with_cert_seed):
    """Seeded certificate codes must resolve to proper descriptions."""
    r = client.get("/tariff/lookup?hs_code=7208510000&origin=GB&destination=DE")
    data = r.json()["data"]
    for ntm in data["non_tariff_measures"]:
        for code, detail in ntm["certificate_details"].items():
            assert "Unknown" not in detail["description"], (
                f"Certificate {code} has no seeded description"
            )

def test_origin_name_is_not_raw_code(client, db_with_origin_seed):
    """origin_name must be the full country name, not the ISO2 code."""
    r = client.get("/tariff/lookup?hs_code=7208510000&origin=GB&destination=DE")
    data = r.json()["data"]
    assert data["origin"]["origin_name"] != "GB"
    assert data["origin"]["origin_name"] == "United Kingdom"

def test_data_gap_returns_clear_error(client, empty_db):
    """When no data exists at all, data_status must be 'data_gap'."""
    r = client.get("/tariff/lookup?hs_code=9999999999&origin=XX&destination=DE")
    data = r.json()["data"]
    assert data["data_status"] == "data_gap"
    assert data["duty"] is None
    assert any("DATA GAP" in w or "ingest" in w.lower()
               for w in data["calculated"]["warnings"])

def test_effective_rate_includes_safeguard(client, db_full_seed):
    """Effective rate = base + safeguard, shown separately and combined."""
    r = client.get("/tariff/lookup?hs_code=7208510000&origin=CN&destination=DE")
    data = r.json()["data"]
    calc = data["calculated"]
    if calc["safeguard_rate"]:
        assert calc["effective_duty_rate"] == (
            (calc["base_duty_rate"] or 0) + calc["safeguard_rate"]
        )

def test_ru_import_control_warning(client, db_with_ntm_seed):
    """RU origin must trigger the Regulation 0833/14 import control warning."""
    r = client.get("/tariff/lookup?hs_code=7208510000&origin=RU&destination=DE")
    data = r.json()["data"]
    assert any("0833" in w for w in data["calculated"]["warnings"])

def test_quota_within_quota_rate_in_calculated(client, db_with_quota_seed):
    """When a quota applies, effective_duty_rate_within_quota must be populated."""
    r = client.get("/tariff/lookup?hs_code=7208510000&origin=TR&destination=DE")
    data = r.json()["data"]
    assert data["calculated"]["effective_duty_rate_within_quota"] is not None
```

---

### Summary of all fixes required (checklist)

Implement ALL of the following before considering the lookup endpoint production-ready:

- [ ] Measure type 103 ingested into `duty_rates` with `origin_code = '1011'`
- [ ] Post-ingest validation: log ERROR for any HS code missing ERGA OMNES row
- [ ] `resolve_duty()` with full 4-step fallback chain implemented
- [ ] `build_origin_resolution_list()` includes groups, GSP, WTO, 1008, 1011
- [ ] `check_stacked_measures()` checks safeguard, AD, CVD, import controls
- [ ] `get_tariff_quotas()` queries all candidate origin codes, not just exact match
- [ ] `get_non_tariff_measures()` queries all candidate origin codes
- [ ] `resolve_certificate_details()` seeded from v4 certificate table
- [ ] `hydrate_origin_name()` called on every origin_code before serialisation
- [ ] `data_status` field on every response: `complete | mfn_fallback | partial | data_gap`
- [ ] `stacked_duties[]` populated and included in response body
- [ ] `effective_duty_rate` = base + safeguard (separate + combined)
- [ ] `effective_duty_rate_within_quota` populated when quota applies
- [ ] All 10 tests in `tests/test_lookup_resolution.py` pass
