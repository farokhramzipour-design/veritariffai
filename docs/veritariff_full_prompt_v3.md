# VeriTariff — AI Agent Prompt (v3)
## Feature: Tariff & VAT Data Pipeline (EU + UK) with Full Measure Conditions

---

## YOUR ROLE

You are a senior Python backend engineer implementing a tariff data pipeline for
**VeriTariff**, a web application that allows users to look up import duty rates,
VAT, and all associated border compliance requirements by HS code, origin country,
and destination country.

Your task is to build a **production-ready data pipeline in Python / FastAPI** that
fetches, normalises, stores, and refreshes tariff data from free official sources
for the **EU and UK markets** — including full measure condition parsing so the
calculator can show users exactly what documents they need and what rate applies
in each case.

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

## UNDERSTANDING DUTY EXPRESSIONS (CRITICAL — READ ALL OF THIS)

The TARIC duty column can contain many different expression formats.
You must parse **every** format listed below and store it correctly.
Never silently drop an expression you cannot parse — log it as an error.

### 1. Pure Ad Valorem (percentage only)

```
8.000 %
0.000 %
12.800 %
```

Store in `duty_rates`: `duty_rate = 8.0`, `duty_amount = null`, `duty_expression_code = '01'`.

---

### 2. Pure Specific Duty (fixed amount per unit, no percentage)

```
30.900 EUR DTN          → amount=30.9, currency='EUR', unit='DTN' (= decitonnes = 100 kg)
41.200 EUR DTN
93.100 EUR DTN
52.000 EUR MIL          → amount=52.0, unit='MIL' (per thousand items)
39.000 EUR MIL
114.000 EUR MIL
34.000 EUC DTN          → EUC = EU customs unit (effectively EUR here)
795.000 EUR TNE         → TNE = metric tonnes
131.000 EUR TNE
0.000 EUR TNE
0.000 EUR MIL
0.000 EUR DTN
```

Store in `duty_rates`: `duty_rate = null`, `duty_amount = 30.9`, `currency = 'EUR'`,
`duty_unit = 'DTN'`, `duty_expression_code = '02'`.

**Unit codes and their meanings** — store the raw code AND the resolved description:

| Unit Code | Meaning                          |
|-----------|----------------------------------|
| DTN       | 100 kg (decitonnes)              |
| TNE       | Metric tonne (1000 kg)           |
| KGM       | Kilogram                         |
| HLT       | Hectolitre (100 litres)          |
| LTR       | Litre                            |
| MIL       | Thousand items (per mille)       |
| NAR       | Number of items (each)           |
| MTQ       | Cubic metre                      |
| MTK       | Square metre                     |
| MTR       | Linear metre                     |
| GRM       | Gram                             |
| KNS       | Kilogram net of sugars           |
| KSD       | Kilogram of sucrose dry matter   |
| KMA       | Kilogram of methylamine          |
| KNI       | Kilogram of nitrogen             |
| KPO       | Kilogram of potassium oxide      |
| KPH       | Kilogram of phosphorus pentoxide |
| KSH       | Kilogram of shelled product      |
| KPP       | Kilogram of diphosphorus pentoxide |
| KUR       | Kilogram of uranium              |
| GFI       | Gram of fissile isotopes         |
| ASV       | % volume (alcohol strength)      |
| DAP       | Decitonne of raw product         |
| HMT       | Hectometre                       |
| ENP       | Effective number of primary cells |
| CCT       | Carrying capacity (tonnes)       |
| CEN       | Hundred items                    |
| LPA       | Litre of pure (100%) alcohol     |
| KPO       | Kilogram of potassium oxide      |

Store a `duty_units` reference table containing all these codes.
Never hardcode unit descriptions in parsing logic — look up from the reference table.

---

### 3. Compound Duty — Ad Valorem + Specific Amount

```
10.200 % + 93.100 EUR DTN
7.600 % + 69.820 EUR DTN
12.800 % + 176.800 EUR DTN
2.500 % + 35.300 EUR DTN
15.000 % + 994.500 EUR TNE
15.000 % + 1,554.300 EUR TNE    ← note comma as thousands separator
12.800 % + 265.200 EUR DTN
0.000 % + 93.100 EUR DTN
0.000 % + 171.300 EUR DTN
```

Both the percentage AND the specific amount apply simultaneously.
Store in `duty_rates`:
- `duty_rate = 10.2` (ad valorem component)
- `duty_amount = 93.1` (specific component)
- `currency = 'EUR'`
- `duty_unit = 'DTN'`
- `duty_expression_code = '03'` (compound: av + specific)

When rendering to user: "10.2% **plus** EUR 93.10 per 100kg".

---

### 4. Specific Duty with Alcohol Strength Component (ASV)

```
0.230 EUR KGM P + 5.500 EUR DTN
1.190 EUR KGM P + 27.500 EUR DTN
0.000 EUR KGM P
0.230 EUR KGM P + 4.200 EUR DTN
```

The `P` suffix on the unit means the specific amount is per unit **of pure alcohol content**
(the `ASV` quantity declared on the entry — alcohol strength by volume × volume).
Store extra field `is_alcohol_strength = true` in `duty_rates`.

```
0.320 EUR KGM P + 4.400 EUR DTN
1.310 EUR KGM P + 22.000 EUR DTN
```

Parse pattern: `{amount} EUR {unit} P + {amount2} EUR {unit2}` →
`duty_amount_primary = 0.23`, `unit_primary = 'KGM'`, `alcohol_per_unit = true`,
`duty_amount_secondary = 5.5`, `unit_secondary = 'DTN'`.

---

### 5. Entry Price / Agricultural Representative Price (EA / EAR / ADSZ / ADSZR / ADFM / ADFMR)

These are **price-based duties** used for agricultural goods.
The actual amount owed depends on the declared CIF price at the border.
They CANNOT be pre-calculated by VeriTariff — only stored as reference data.

```
7.600 % + EA           → ad valorem + entry price component
0.000 % + EA
1.190 % + EA
5.500 % + EA
9.000 % + EA
6.000 % + EA
0.000 % + EAR          → EAR = reduced entry price (for quotas/agreements)
5.600 % + EAR
6.200 % + EAR
4.000 % + EAR
0.900 % + EAR
1.900 % + EAR
1.100 % + EAR
4.700 % + EAR
5.800 % + EAR
2.700 % + EAR
4.100 % + EAR
5.700 % + EAR
6.500 % + EA
4.800 % + EA MAX 18.700 % +ADSZ
8.300 % + EA MAX 18.700 % +ADSZ
0.000 % + EA MAX 18.700 % +ADSZ
9.000 % + EA MAX 18.700 % +ADSZ
5.500 % + EA MAX 18.700 % +ADSZ
0.000 % + EAR MAX 18.700 % +ADSZR
0.000 % + EAR MAX 9.300 % +ADSZR
4.500 % + EAR MAX 9.300 % +ADSZR MAX 35.150 EUR DTN
4.100 % + EAR MAX 9.300 % +ADSZR MAX 35.150 EUR DTN
0.000 % + EAR MAX 12.100 % +ADSZR
4.500 % + EAR MAX 12.100 % +ADSZR MAX 35.150 EUR DTN
0.000 % + EAR MAX 24.200 % +ADSZR
0.000 % + EAR MAX 20.700 % +ADSZR
0.000 % + EAR MAX 20.700 % +ADFMR
4.500 % + EAR MAX 10.300 % +ADFMR MAX 35.150 EUR DTN
6.200 % + EA
9.700 % + EA
10.700 % + EA
15.400 % + EA
4.100 % + EA
0.000 % + EA MAX 0.000 % +ADSZ
0.000 % + EA MAX 20.700 % +ADFM
9.000 % + EA MAX 20.700 % +ADFM
5.500 % + EA MAX 20.700 % +ADFM
```

**Component abbreviation meanings:**

| Code   | Meaning |
|--------|---------|
| EA     | Entry price component (agricultural) — full MFN |
| EAR    | Entry price component — reduced (preferential/quota) |
| ADSZ   | Additional duty on sugar (full rate) |
| ADSZR  | Additional duty on sugar — reduced |
| ADFM   | Additional duty on flour/starch (full rate) |
| ADFMR  | Additional duty on flour/starch — reduced |

Store these in `duty_rates` with:
- `duty_rate = 7.6` (ad valorem component)
- `has_entry_price = true`
- `entry_price_type = 'EA'` or `'EAR'`
- `entry_price_max_rate = 18.7` (if `MAX` clause present, i.e. `MAX 18.700 % +ADSZ`)
- `entry_price_max_additional_type = 'ADSZ'`
- `entry_price_max_specific = 35.15` (if `MAX 35.150 EUR DTN` present)

Route these to `price_measures` table (not `duty_rates`) because the final amount
is calculated at the border. Show user: "X% ad valorem plus entry price charge (EA).
Maximum charge is Y% + additional Z% on sugar content. Actual amount depends on
your declared CIF price."

---

### 6. MAX clause on ad valorem — Maximum Duty

```
9.600 % MIN 1.100 EUR DTN      → minimum duty applies if % produces less than this
13.600 % MIN 1.600 EUR DTN
12.000 % MIN 0.400 EUR DTN
10.400 % MIN 1.300 EUR DTN G   → G suffix = Gross weight basis
12.000 % MIN 2.000 EUR DTN G
10.400 % MIN 1.600 EUR DTN
18.400 % MIN 22.000 EUR DTN MAX 24.000 EUR DTN
14.900 % MAX 24.000 EUR DTN
11.200 % MIN 22.000 EUR DTN MAX 56.000 EUR DTN
10.000 % MIN 22.000 EUR DTN MAX 56.000 EUR DTN
3.800 % MIN 0.600 EUR DTN G
3.800 % MIN 0.400 EUR DTN G
4.400 % MIN 0.400 EUR DTN G
3.000 % MIN 1.200 EUR DTN G
2.300 % MAX 3.000 EUR DTN
7.400 % MAX 12.000 EUR DTN
3.200 % MAX 12.000 EUR DTN
1.900 % MAX 28.000 EUR DTN
3.800 % MAX 28.000 EUR DTN
7.700 % MAX 56.000 EUR DTN
1.400 % MAX 7.000 EUR DTN
1.900 % MAX 3.000 EUR DTN
6.400 % MAX 24.000 EUR DTN
3.900 % MAX 56.000 EUR DTN
```

Parse pattern: `{rate}% [MIN {min_amount} EUR {unit}] [MAX {max_amount} EUR {unit}] [G]`

Store:
- `duty_rate = 9.6`
- `duty_min_amount = 1.1`
- `duty_max_amount = null` (if no MAX)
- `duty_unit = 'DTN'`
- `duty_gross_weight_basis = true` (if G suffix)
- `duty_expression_code = '12'` (for MIN), `'14'` (for MAX), `'15'` (for MIN+MAX)

When rendering to user: "9.6% (minimum EUR 1.10 per 100kg, maximum EUR 24.00 per 100kg)."

---

### 7. MIN with absolute amount only (no percentage)

```
1.800 % MIN 0.090 EUR DTN
2.800 % MIN 0.360 EUR DTN
7.200 % MIN 0.360 EUR DTN
8.000 % MAX 2.800 EUR MTK
6.400 % MAX 2.800 EUR MTK
0.360 EUR DTN              ← standalone minimum (the minimum IS the duty)
```

Parse the standalone `0.360 EUR DTN` as a pure specific duty.

---

### 8. Per-unit duty on alcohol (ASV — % vol basis)

```
0.075 EUR ASV X + 0.400 EUR HLT
0.380 EUR ASV X + 2.000 EUR HLT
0.600 EUR ASV X + 3.200 EUR HLT
0.075 EUR ASV X
0.380 EUR ASV X
0.600 EUR ASV X
0.125 EUR ASV X + 0.800 EUR HLT
0.460 EUR ASV X + 2.930 EUR HLT
1.000 EUR ASV X + 6.400 EUR HLT
0.700 EUR ASV X + 4.400 EUR HLT
0.700 EUR ASV X
0.125 EUR ASV X
0.460 EUR ASV X
1.000 EUR ASV X
0.320 EUR ASV X MIN 1.800 EUR HLT
1.300 EUR ASV X MIN 7.200 EUR HLT
0.900 EUR ASV X + 6.400 EUR HLT
0.900 EUR ASV X
0.000 EUR ASV X + 4.400 EUR HLT
0.000 EUR ASV X + 0.800 EUR HLT
0.000 EUR ASV X + 2.930 EUR HLT
```

`ASV X` = duty per % vol per hectolitre (alcohol-strength-by-volume).
The `X` indicates the measurement is per degree of alcohol per unit volume.
Store: `duty_amount_primary`, `unit = 'ASV'`, plus optional secondary amount in `HLT`.
Set `is_alcohol_duty = true`.

---

### 9. Conditional / Variable Rate — V (SIV / Entry Price Steps)

These are **Standard Import Value (SIV)** step duties — the rate changes based on
the declared import price (c.i.f.) compared to the SIV threshold bands.

```
Cond: V 52.600 EUR/DTN(01):12.000 % ; V 51.500 EUR/DTN(01):12.000 % + 1.100 EUR DTN ; ... ; V 0.000 EUR/DTN(01):0.000 % + 29.800 EUR DTN
Cond: V 84.600 EUR/DTN(01):0.000 % ; V 82.900 EUR/DTN(01):0.000 % + 1.700 EUR DTN ; ... ; V 0.000 EUR/DTN(01):0.000 % + 29.800 EUR DTN
Cond: V 112.600 EUR/DTN(01):0.000 % ; V 110.300 EUR/DTN(01):0.000 % + 2.300 EUR DTN ; ... ; V 0.000 EUR/DTN(01):0.000 % + 29.800 EUR DTN
```

**Parse logic:**
Each `V {threshold} EUR/{unit}({expr_id}):{rate}% [+ {amount} EUR {unit}]` segment
defines one price band.

The condition is: "IF declared CIF price ≥ threshold, apply this rate/amount."
The bands are ordered descending — first matching threshold wins.

Store as a JSON array in `price_measures.siv_bands`:
```json
[
  {"threshold_eur_per_dtn": 52.6, "duty_rate": 12.0, "duty_amount": null},
  {"threshold_eur_per_dtn": 51.5, "duty_rate": 12.0, "duty_amount": 1.1},
  {"threshold_eur_per_dtn": 0.0,  "duty_rate": 0.0,  "duty_amount": 29.8}
]
```

Route to `price_measures` table (not `duty_rates`).
Tell user: "Variable rate based on your declared CIF price. The applicable rate
is calculated at the border using the Standard Import Value table."

These also appear combined with certificate conditions and Y-cert exemptions:
```
Cond: V 84.600 EUR/DTN(01):0.000 % ; ... ; Y cert: Y-864 (27):; Y (07):
Cond: B cert: U-088 (27):; B (07):; V 84.600 EUR/DTN(01):0.000 % ; ...
```
Parse the V-bands regardless of the surrounding B/Y conditions.

---

### 10. Conditional Rate — R (Weight-Based Threshold)

```
Cond: R 80.001/KGM(10):; R 0.000/KGM(28):
Cond: R 160.001/KGM(10):; R 80.001/KGM(28):; R 0.000/KGM(10):
Cond: R 300.001/KGM(10):; R 160.001/KGM(28):; R 0.000/KGM(10):
Cond: R 470.001/KGM(10):; R 320.000/KGM(28):; R 0.000/KGM(10):
Cond: R 0.186/KGM(10):; R 0.000/KGM(28):
Cond: R 0.186/KGM(28):; R 0.000/KGM(10):
Cond: R 2.600/KGM(10):; R 1.100/KGM(28):; R 0.000/KGM(10):
Cond: R 1.200/KGM(10):; R 0.800/KGM(28):; R 0.000/KGM(10):
Cond: R 50.000/KGM(10):; R 0.000/KGM(28):
Cond: R 250.000/KGM(10):; R 0.900/KGM(28):; R 0.000/KGM(10):
Cond: R 45.000/KGM(10):; R 1.000/KGM(28):; R 0.000/KGM(10):
Cond: R 120.000/KGM(10):; R 0.500/KGM(28):; R 0.000/KGM(10):
Cond: R 300.001/KGM(10):; R 5.000/KGM(28):; R 0.000/KGM(10):
Cond: R 0.501/KGM(10):; R 0.150/KGM(28):; R 0.000/KGM(10):
Cond: R 0.081/KGM(10):; R 0.001/KGM(28):; R 0.000/KGM(10):
Cond: R 0.025/KGM(10):; R 0.021/KGM(28):; R 0.000/KGM(10):
```

`R {threshold}/{unit}({measure_type_code})` = measure applies if quantity exceeds threshold.
Measure type code `(10)` = import, `(28)` = preferential import.
Multiple R thresholds define price bands similar to V-conditions.

Store as `weight_threshold_bands` JSON array in `price_measures` or `duty_rates`.
Example: `[{"threshold_per_kg": 80.001, "measure_type": "10"}, {"threshold_per_kg": 0.0, "measure_type": "28"}]`

---

### 11. Conditional Rate — L (Price-Triggered Concession)

```
Cond: L 143.010 EUR/DTN(01):0.000 EUR DTN ; L 95.340 EUR/DTN(01):42.903 EUR DTN - 30.000 % ; L 63.560 EUR/DTN(01):61.971 EUR DTN - 50.000 % ; L 39.725 EUR/DTN(01):74.683 EUR DTN - 70.000 % ; L 0.000 EUR/DTN(01):82.628 EUR DTN - 90.000 %
Cond: L 244.260 EUR/DTN(01):0.000 EUR DTN ; L 162.840 EUR/DTN(01):73.278 EUR DTN - 30.000 % ; ...
```

Parse pattern: `L {price_threshold} EUR/{unit}({expr_id}):{duty_amount} EUR {unit} - {reduction}%`
These are price-reduction concession bands — the higher the declared price,
the lower the duty reduction applied.

Store as `reduction_bands` JSON array in `price_measures`.

---

### 12. Conditional Rate — J (Quantity Threshold)

```
Cond: J 4.999/KGM(28):; J 0.000/KGM(21):
Cond: J 5.000/KGM(28):; J 0.000/KGM(21):
Cond: J 9.999/KGM(28):; J 0.000/KGM(21):
Cond: J 99.999/KGM(28):; J 0.000/KGM(21):
```

`J {threshold}/{unit}({duty_expression})` = measure applies below/above quantity threshold.
Measure expression `(28)` = preferential, `(21)` = not applicable.

Store as `quantity_threshold_bands` JSON in relevant table.

---

### 13. Conditional Rate — M (Value Threshold)

```
Cond: M 0.301 EUR/KGM(10):; M 0.000 EUR/KGM(28):
Cond: M 0.301 EUR/KGM(28):; M 0.000 EUR/KGM(10):
Cond: M 4.500 EUR/KGM(28):; M 0.000 EUR/KGM(10):
Cond: M 35.010 EUR/KGM(28):; M 0.000 EUR/KGM(10):
Cond: M 35.010 EUR/KGM(10):; M 0.000 EUR/KGM(28):
Cond: M 17.501 EUR/KGM(28):; M 0.000 EUR/KGM(10):
Cond: M 17.501 EUR/KGM(10):; M 0.000 EUR/KGM(28):
Cond: M 1,536.000 EUR/TNE(01):0.000 EUR TNE ; M 1,264.200 EUR/TNE(11):1,536.000 EUR TNE ; M 0.000 EUR/TNE(01):21.500 %
```

`M {value}/{unit}({code})` = measure applies if declared value exceeds/falls below threshold.
Store as `value_threshold_bands` JSON.

---

### 14. Conditional Rate — X (Item Count / NAR Threshold)

```
Cond: X 2,499.000/NAR(28):; X 0.000/NAR(22):
Cond: X 999.000/NAR(28):; X 0.000/NAR(22):
Cond: X 99.000/NAR(28):; X 0.000/NAR(22):
Cond: X 19.999/LTR(28):; X 0.000/LTR(22):
Cond: X 49.999/LTR(28):; X 0.000/LTR(22):
```

`X {count}/{unit}({code})` = measure applies to items above/below count threshold.
`(22)` = outside scope.
Store as `count_threshold_bands` JSON.

---

### 15. Conditional Rate — U (Price per NAR/LPA Threshold)

```
Cond: U 7.900 EUR/LPA(28):; U 0.000 EUR/LPA(10):
Cond: U 7.900 EUR/LPA(10):; U 0.000 EUR/LPA(28):
Cond: U 2.000 EUR/LPA(28):; U 0.000 EUR/LPA(10):
Cond: U 2.000 EUR/LPA(10):; U 0.000 EUR/LPA(28):
Cond: U 65.000 EUR/NAR(28):; U 0.000 EUR/NAR(10):
Cond: U 65.000 EUR/NAR(10):; U 0.000 EUR/NAR(28):
```

`U {price} EUR/{unit}({code})` = measure applies if unit price exceeds/falls below threshold.
Store as `unit_price_threshold_bands` JSON.

---

### 16. Specific Duty per KGM — Graduated (P suffix)

```
0.040 EUR KGM T             → T = per whole item (tonne or unit)
0.070 EUR KGM T
0.040 EUR KGM T + 10.500 EUR DTN
0.070 EUR KGM T + 16.800 EUR DTN
```

`T` suffix = measure applies per item (individual unit), not per kg.
Store `duty_per_item = true`.

---

### 17. Duty with NAR Prefix (per item, per number)

```
0.000 EUR KGM A     → A = per item (pieces/articles)
1.620 EUR KGM A
```

The `A` suffix = per article/item number.
Store `duty_per_article = true`.

---

### 18. Provisional Anti-Dumping / Countervailing (per unit with specific component)

All the complex compound expressions for anti-dumping measures follow the same
compound structure as above but must be tagged `rate_type = 'anti-dumping'`
or `rate_type = 'countervailing'` based on the measure type ID.

---

### 19. Amount with Reduction from F-condition (tariff suspension / preference)

```
Cond: F 325.000 EUR/MIL(01):0.000 EUR MIL ; F 0.000 EUR/MIL(11):325.000 EUR MIL
Cond: F 2,408.000 EUR/TNE(01):0.000 EUR TNE ; F 0.000 EUR/TNE(11):2,408.000 EUR TNE
Cond: F 1,316.000 EUR/TNE(01):0.000 EUR TNE ; F 0.000 EUR/TNE(11):1,316.000 EUR TNE
Cond: F 3,647.000 EUR/TNE(01):0.000 EUR TNE ; F 0.000 EUR/TNE(11):3,647.000 EUR TNE
Cond: F 1,392.000 EUR/TNE(01):0.000 EUR TNE ; F 0.000 EUR/TNE(11):1,392.000 EUR TNE
```

`F {full_amount} EUR/{unit}({expr_if_full}):0.000 EUR {unit} ; F 0.000 EUR/{unit}({expr_if_suspended}):{full_amount} EUR {unit}`

Meaning: if the suspension/preference condition (from A-type above) is met → 0% rate.
If not met → the full amount specified applies.
Store `duty_suspended_to = 0.0`, `duty_full_amount = 325.0`, `duty_unit = 'MIL'`.

---

### 20. Reduced amounts from A-cert + F-condition combination

```
Cond: A cert: D-020 (28):; A (08):; F 2,043.000 EUR/TNE(01):0.000 EUR TNE ; F 1,681.480 EUR/TNE(11):2,043.000 EUR TNE ; F 0.000 EUR/TNE(01):21.500 %
Cond: A cert: D-020 (28):; A (08):; F 2,043.000 EUR/TNE(01):0.000 EUR TNE ; F 1,469.780 EUR/TNE(11):2,043.000 EUR TNE ; F 0.000 EUR/TNE(01):39.000 %
Cond: A cert: D-020 (28):; A (08):; M 1,536.000 EUR/TNE(01):0.000 EUR TNE ; M 1,264.200 EUR/TNE(11):1,536.000 EUR TNE ; M 0.000 EUR/TNE(01):21.500 %
```

The A cert (e.g. D-020 = TRQ licence) gates a specific amount suspension.
The F/M condition defines what amount applies with vs without the cert.
Store both in `duty_rates` + link a `measure_condition` with the cert requirement.

---

### 21. Special suffixes on amounts

```
16.950 EUR DTN R     → R = reduced/preferential rate flag
4.237 EUR DTN R
33.900 EUR DTN R
0.000 EUR DTN R
20.950 EUR DTN       → no suffix = standard rate
25.340 EUR DTN M     → M = minimum rate flag
6.337 EUR DTN M
50.700 EUR DTN M
```

The R suffix means the row represents the **reduced** rate (used when comparing standard vs preferential).
The M suffix means **minimum** (this is the minimum duty floor, not the ad valorem rate).
Store as `duty_rate_flag = 'R'` or `'M'` on the `duty_rates` row.

---

### 22. Duty per KGM S / Z flags

```
KGM S               → S = net weight (dry substance basis)
0.050 EUR DTN Z     → Z = per unit declared (additional statistical component)
0.200 EUR DTN Z
0.300 EUR DTN Z
0.400 EUR DTN Z
```

Store `duty_basis_flag = 'S'` (dry substance net weight basis) or `'Z'` (statistical component).

---

### 23. Duty on Representative Price (EUC / EUR specific)

```
43.860 EUC DTN      → EUC = EU Customs duty unit (effectively EUR for duty purposes)
173.370 EUC DTN
97.340 EUC DTN
256.350 EUC DTN
179.450 EUC DTN
182.580 EUC DTN
242.300 EUC DTN
247.500 EUC DTN
139.430 EUC DTN
548.550 EUC DTN
110.920 EUC DTN
80.890 EUC DTN
112.700 EUC DTN
125.610 EUC DTN
399.840 EUC DTN
1,206.610 EUC DTN
300.010 EUC DTN
52.730 EUC DTN
172.560 EUC DTN
777.070 EUC DTN
```

Treat `EUC` identically to `EUR` for all storage and calculation purposes.
Normalise to `currency = 'EUR'` in the database.

---

### 24. Supplementary unit declarations (no duty amount)

```
NAR         → number of articles/items (must declare count)
MTQ C       → cubic metres (commercial quantity)
MTQ         → cubic metres
MWH         → megawatt-hours
LPA         → litres of pure alcohol
TJO         → terajoules (energy)
CCT         → carrying capacity in tonnes
CTM         → carat (metric)
NCL         → number of cells
NPR         → number of pairs
KPP         → kilograms of diphosphorus pentoxide
KNI         → kilograms of nitrogen
KUR         → kilograms of uranium
GFI         → grams of fissile isotopes
```

These appear as measure duty expressions that are just a unit code with no amount.
Route to `supplementary_units` table.
Store: `unit_code`, `unit_description`, `declaration_type = 'supplementary unit'`.

---

### 25. Proportional duty with declared quantity (ENC ENP / per cell)

```
0.192 ENC ENP        → per effective number of primary cells
0.625 ENC ENP        → per cell equivalent
Cond: A cert: D-025 (01):0.625 ENC ENP ; A cert: D-027 (01):0.625 ENC ENP ; ...
Cond: A cert: D-008 (01):0.075 ENC ENP ; A (01):0.192 ENC ENP
Cond: A cert: D-008 (01):0.072 ENC ENP ; A (01):0.192 ENC ENP
Cond: A cert: D-008 (01):0.144 ENC ENP ; A (01):0.192 ENC ENP
Cond: A cert: D-008 (01):0.112 ENC ENP ; A (01):0.192 ENC ENP
```

`ENC ENP` = duty per effective number of primary cells (batteries).
Store: `duty_amount = 0.192`, `duty_unit = 'ENP'`.

---

### 26. Alcohol content duty (per LPA — litre of pure alcohol)

```
4.700 EUR HLT        → straightforward, per hectolitre
7.600 EUR HLT
6.300 EUR HLT
...
0.000 EUR HLT
```

Store normally with `duty_unit = 'HLT'`.

---

### 27. Specific duty per HLT (wine/spirits) + ad valorem compound

```
0.000 % + 27.000 EUR HLT
22.400 % + 27.000 EUR HLT
18.900 % + 27.000 EUR HLT
0.000 % + 121.000 EUR HLT
40.000 % + 121.000 EUR HLT
36.500 % + 121.000 EUR HLT
0.000 % + 131.000 EUR HLT
22.400 % + 131.000 EUR HLT
18.900 % + 131.000 EUR HLT
12.600 % + 87.330 EUR HLT
0.000 % + 39.930 EUR HLT + 6.790 EUR DTN        ← triple component
0.000 % + 121.000 EUR HLT + 20.600 EUR DTN
40.000 % + 121.000 EUR HLT + 20.600 EUR DTN
36.500 % + 121.000 EUR HLT + 20.600 EUR DTN
22.400 % + 131.000 EUR HLT + 20.600 EUR DTN
18.900 % + 131.000 EUR HLT + 20.600 EUR DTN
0.000 % + 27.000 EUR HLT + 20.600 EUR DTN
22.400 % + 27.000 EUR HLT + 20.600 EUR DTN
18.900 % + 27.000 EUR HLT + 20.600 EUR DTN
12.600 % + 18.000 EUR HLT + 13.730 EUR DTN
```

**Triple-component duty** (`rate% + amount1 EUR unit1 + amount2 EUR unit2`):
Store:
- `duty_rate = 0.0`
- `duty_amount_primary = 121.0`, `duty_unit_primary = 'HLT'`
- `duty_amount_secondary = 20.6`, `duty_unit_secondary = 'DTN'`
- `duty_expression_code = '04'` (triple compound)

---

### 28. Anti-dumping per-unit with contingent rate (I/E suffix)

```
0.000 % + 191.000 EUR DTN E     → E = the specific amount represents the FULL anti-dumping rate
9.600 % + 191.000 EUR DTN E     → combined: 9.6% av + EUR 191/DTN AD duty
6.100 % + 191.000 EUR DTN E
191.000 EUR DTN E
4.500 % + 143.250 EUR DTN E
0.000 % + 126.490 EUR DTN
0.000 % + 95.000 EUR DTN
4.800 % + 95.000 EUR DTN
8.300 % + 95.000 EUR DTN
5.100 % + 59.370 EUR DTN
0.000 % + 222.000 EUR DTN E
14.900 % + 222.000 EUR DTN E
18.400 % + 222.000 EUR DTN E
222.000 EUR DTN E
11.100 % + 143.250 EUR DTN E
18.400 % + 191.000 EUR DTN E
14.900 % + 191.000 EUR DTN E
11.100 % + 166.500 EUR DTN E
14.900 % + 222.000 EUR DTN E
9.400 EUR DTN E
6.260 EUR DTN E
0.000 % + 6.580 EUR DTN E
0.000 % + 9.400 EUR DTN E
1.600 % + 9.400 EUR DTN E
9.400 EUR DTN E
0.800 % + 4.700 EUR DTN E
0.000 % + 7.580 EUR DTN E
5.100 % + 9.400 EUR DTN E
0.000 % + 3.800 EUR DTN E
4.800 % + 3.800 EUR DTN E
0.000 % + 2.530 EUR DTN E
0.000 % + 3.030 EUR DTN E
8.300 % + 3.800 EUR DTN E
8.300 % + 3.030 EUR DTN E
0.000 % + 3.800 EUR DTN
```

The `E` suffix = **definitive anti-dumping component** (the specific amount is the AD duty).
Set `rate_type = 'anti-dumping'` and `anti_dumping_specific = true` when `E` suffix present.

---

### 29. NAR amounts (per item/number, common in luxury goods, vehicles, cigarettes)

```
4.480 EUR NAR
57.280 EUR NAR
32.710 EUR TNE
Cond: A cert: D-008 (01):4.480 EUR NAR ; A (01):4.480 EUR NAR
Cond: A cert: D-008 (01):57.280 EUR NAR ; A (01):57.280 EUR NAR
Cond: A cert: D-008 (01):27.690 EUR NAR ; A (01):57.280 EUR NAR
```

Store `duty_unit = 'NAR'`.

---

### 30. Percentage with Specific per Measurement — MIN and MAX combos

```
0.000 % + 4.500 EUR DTN MAX 11.500 %
0.000 % + 8.900 EUR DTN MAX 11.500 %
0.000 % + 12.400 EUR DTN MAX 11.500 %
0.000 % + 17.700 EUR DTN MAX 11.500 %
4.100 % + 2.250 EUR DTN MAX 5.700 %
5.500 % + 3.000 EUR DTN MAX 7.600 %
0.000 % + 3.640 EUR DTN MAX 11.500 %
8.300 % + 4.500 EUR DTN MAX 11.500 %
0.000 % + 9.700 EUR DTN MAX 12.800 %
0.000 % + 15.100 EUR DTN MAX 12.800 %
0.000 % + 17.700 EUR DTN MAX 12.800 %
8.300 % + 8.900 EUR DTN MAX 12.800 %
```

Parse pattern: `{av}% + {amount} EUR {unit} MAX {max_av}%`
The MAX percentage is a ceiling on the TOTAL effective rate.
Store: `duty_rate`, `duty_amount`, `duty_unit`, `duty_max_total_rate`.

---

### 31. Percentage with specific amount + MAX absolute amount

```
6.700 % MAX 35.150 EUR DTN
4.500 % + 22.550 EUR DTN MAX 9.400 % + 8.250 EUR DTN MAX 35.150 EUR DTN
0.000 % + 45.100 EUR DTN MAX 18.900 % + 16.500 EUR DTN
5.600 % + 45.100 EUR DTN MAX 18.900 % + 16.500 EUR DTN
0.000 % + 43.590 EUR DTN MAX 18.900 % + 16.500 EUR DTN
9.100 % + 45.100 EUR DTN MAX 18.900 % + 16.500 EUR DTN
4.500 % + EAR MAX 9.300 % +ADSZR MAX 35.150 EUR DTN
```

Store all MAX components in dedicated fields:
`duty_max_rate_pct`, `duty_max_amount`, `duty_max_unit`.

---

### 32. Specific amount per measurement with percentage

```
KGM S           → per kg, dry substance
KGM E           → per kg, energy-equivalent
KGM P           → per kg pure alcohol
KGM A           → per kg article (item)
KGM T           → per kg of the item
```

These suffix letters on `KGM` indicate the measurement basis.
Store as `duty_measurement_basis = 'S'|'E'|'P'|'A'|'T'`.

---

### 33. Import price range — % duty that ranges by HS sub-band

```
20.800 % + 8.400 EUR DTN
0.000 % + 8.400 EUR DTN
13.800 % + 5.600 EUR DTN
8.400 EUR DTN
20.800 %
11.500 % + 5.600 EUR DTN
0.000 % + 5.300 EUR DTN
9.500 % + 5.300 EUR DTN
13.000 % + 5.300 EUR DTN
17.300 % + 8.400 EUR DTN
```

These are straightforward compound duties — already covered by type 3.

---

### 34. NIHIL

```
NIHIL
```

Meaning: duty is explicitly zero (nil) — differs from `0.000 %` in that NIHIL
is used to explicitly state no duty is owed rather than a 0% rate.
Store: `duty_rate = 0.0`, `duty_expression_code = '00'`, `is_nihil = true`.

---

### 35. Zero-suffix variants

```
0         → rare, same as 0.000%
```

Store `duty_rate = 0.0`, `duty_expression_code = '01'`.

---

### 36. Duty with I suffix (per item, import licence context)

```
172.200 EUR TNE I
237.000 EUR TNE I
Cond: A cert: D-008 (01):237.000 EUR TNE I ; A (01):237.000 EUR TNE I
Cond: A cert: D-008 (01):68.600 EUR TNE I ; A (01):172.200 EUR TNE I
Cond: A cert: D-008 (01):0.000 EUR TNE I ; A (01):172.200 EUR TNE I
Cond: A cert: D-008 (01):213.800 EUR TNE I ; A (01):237.000 EUR TNE I
```

`I` suffix = rate is contingent on import licence (IQ measure).
Store `requires_import_licence = true`, `duty_expression_code_suffix = 'I'`.

---

### 37. Percentage with percentage fallback and conditions (preferential cascade)

```
Cond: B cert: Y-155 (01):50.000 % ; B (01):0.000 %
Cond: B cert: Y-155 (01):95.000 EUR TNE ; B (01):0.000 EUR TNE
Cond: B cert: Y-155 (01):50.000 % ; B (01):7.700 %
Cond: B cert: Y-155 (01):50.000 % ; B (01):4.500 %
Cond: B cert: Y-155 (01):50.000 % ; B (01):6.400 %
Cond: B cert: Y-155 (01):50.000 % ; B (01):3.200 %
Cond: B cert: Y-155 (01):50.000 % ; B (01):12.800 %
Cond: B cert: Y-155 (01):50.000 % ; B (01):10.900 %
Cond: B cert: Y-155 (01):50.000 % ; B (01):9.600 %
Cond: B cert: Y-155 (01):50.000 % ; B (01):1.600 %
Cond: B cert: Y-155 (01):50.000 % ; B (01):23.000 EUR TNE
Cond: B cert: Y-155 (01):50.000 % ; B (01):55.000 EUR TNE
Cond: B cert: Y-155 (01):50.000 % ; B (01):102.000 EUR TNE
Cond: B cert: Y-155 (01):50.000 % ; B (01):12.000 %
Cond: B cert: Y-155 (01):50.000 % ; B (01):2.000 %
Cond: B cert: Y-155 (01):148.000 EUR TNE ; B (01):0.000 EUR TNE
Cond: B cert: Y-155 (01):95.000 EUR TNE ; B (01):6.400 %
Cond: B cert: Y-155 (01):95.000 EUR TNE ; B (01):37.000 EUR TNE
Cond: B cert: Y-155 (01):95.000 EUR TNE ; B (01):56.000 EUR TNE
Cond: B cert: Y-155 (01):95.000 EUR TNE ; B (01):12.800 %
Cond: B cert: Y-155 (01):93.000 EUR TNE ; B (01):0.000 EUR TNE
Cond: B cert: Y-155 (01):94.000 EUR TNE ; B (01):0.000 EUR TNE
```

`B cert: {cert}({market_code}):{rate_if_cert_presented} ; B ({market_code}):{fallback_rate}`

Meaning:
- If certificate `Y-155` (certificate of authenticity / preferential origin) is presented → rate in first B-block.
- If not presented → fallback rate in second B-block.

Parse both sides of the B-condition:
- `duty_rate_if_met` = value after `B cert: Y-155 (01):`
- `duty_rate_if_not_met` = value after `B (01):`

Store both in `measure_conditions`. The rates can be a percentage OR a specific amount.

---

### 38. Compound conditions with multiple cert types (A cert cascade)

```
Cond: A cert: D-008 (01):7.300 % ; A (01):35.600 %
Cond: A cert: D-008 (01):35.600 % ; A (01):35.600 %
Cond: A cert: D-008 (01):23.400 % ; A (01):35.600 %
Cond: A cert: D-017 (01):0.000 % ; A cert: D-018 (01):28.200 % ; A cert: D-008 (01):28.200 % ; A (01):33.400 %
```

Multiple A-conditions create a cascade — each cert unlocks progressively better rates.
Parse each `;` separated A-block as a separate condition row in `measure_conditions`.
The last `A (01):{rate}` (no cert) is the fallback rate when NO cert is presented.

---

### 39. Quota-linked measure Y with cert condition

```
Cond: B cert: N-990 (27):; B (08):; V 48.100 EUR/DTN(01):2.500 % ; ... V 0.000 EUR/DTN(01):2.500 % + 37.800 EUR DTN
Cond: B cert: N-990 (27):; B (08):; V 68.300 EUR/DTN(01):0.000 % ; ... V 0.000 EUR/DTN(01):0.000 % + 37.800 EUR DTN
Cond: B cert: A-007 (28):; B (08):
Cond: B cert: A-001 (28):; B (08):
Cond: B cert: A-004 (28):; B (08):
Cond: B cert: A-019 (28):; B (08):
Cond: B cert: A-022 (28):; B (08):
```

`N-990` = Tariff Quota Licence. `A-xxx` = specific quota allocation licence.
These B-conditions on quotas mean the V-rate (SIV band rate) ONLY applies if the
quota licence is presented. Without the licence, MFN applies.
Parse V-bands normally and link the B-condition as an `ALL_REQUIRED` cert requirement.

---

## DUTY FIELD SCHEMA ADDITIONS (add to `duty_rates` table)

The existing `duty_rates` table is insufficient. Add these columns:

```sql
ALTER TABLE duty_rates ADD COLUMN duty_unit VARCHAR(10);
          -- storage unit: DTN, TNE, KGM, HLT, LTR, NAR, MIL, MTQ, ASV, ENP, LPA, etc.
ALTER TABLE duty_rates ADD COLUMN duty_unit_secondary VARCHAR(10);
          -- second unit for triple-component duties
ALTER TABLE duty_rates ADD COLUMN duty_amount_secondary NUMERIC(14,4);
          -- second specific amount for triple-component duties
ALTER TABLE duty_rates ADD COLUMN duty_min_amount NUMERIC(14,4);
          -- minimum duty amount (for MIN clause)
ALTER TABLE duty_rates ADD COLUMN duty_max_amount NUMERIC(14,4);
          -- maximum duty amount (for MAX clause)
ALTER TABLE duty_rates ADD COLUMN duty_min_rate NUMERIC(8,4);
          -- minimum as percentage
ALTER TABLE duty_rates ADD COLUMN duty_max_rate NUMERIC(8,4);
          -- maximum as percentage
ALTER TABLE duty_rates ADD COLUMN duty_gross_weight_basis BOOLEAN DEFAULT FALSE;
          -- G suffix: calculated on gross weight
ALTER TABLE duty_rates ADD COLUMN duty_rate_flag VARCHAR(2);
          -- 'R' (reduced), 'M' (minimum), NULL otherwise
ALTER TABLE duty_rates ADD COLUMN duty_measurement_basis VARCHAR(2);
          -- 'S' (dry substance), 'E' (energy), 'P' (pure alcohol), 'A' (article), 'T' (item)
ALTER TABLE duty_rates ADD COLUMN has_entry_price BOOLEAN DEFAULT FALSE;
          -- true when EA or EAR component present
ALTER TABLE duty_rates ADD COLUMN entry_price_type VARCHAR(6);
          -- 'EA', 'EAR', 'ADSZ', 'ADSZR', 'ADFM', 'ADFMR'
ALTER TABLE duty_rates ADD COLUMN entry_price_max_rate NUMERIC(8,4);
          -- from MAX clause on entry price
ALTER TABLE duty_rates ADD COLUMN entry_price_max_additional_type VARCHAR(8);
          -- 'ADSZ', 'ADSZR', 'ADFM', 'ADFMR'
ALTER TABLE duty_rates ADD COLUMN entry_price_max_specific NUMERIC(12,4);
          -- from MAX {amount} EUR DTN clause on entry price
ALTER TABLE duty_rates ADD COLUMN is_nihil BOOLEAN DEFAULT FALSE;
          -- true when expressed as NIHIL
ALTER TABLE duty_rates ADD COLUMN is_alcohol_duty BOOLEAN DEFAULT FALSE;
          -- true when duty includes ASV component
ALTER TABLE duty_rates ADD COLUMN requires_import_licence BOOLEAN DEFAULT FALSE;
          -- true when I suffix present on amount
ALTER TABLE duty_rates ADD COLUMN anti_dumping_specific BOOLEAN DEFAULT FALSE;
          -- true when E suffix present (AD/CVD specific amount component)
ALTER TABLE duty_rates ADD COLUMN duty_suspended_to NUMERIC(8,4);
          -- rate under suspension (usually 0)
ALTER TABLE duty_rates ADD COLUMN duty_full_amount NUMERIC(14,4);
          -- full rate before suspension applies
ALTER TABLE duty_rates ADD COLUMN duty_expression_code_suffix VARCHAR(2);
          -- 'I', 'E', 'P', 'A', 'T', 'S', 'Z', 'G' etc.
ALTER TABLE duty_rates ADD COLUMN siv_bands JSONB;
          -- for V-condition SIV step bands
ALTER TABLE duty_rates ADD COLUMN weight_threshold_bands JSONB;
          -- for R-condition weight threshold bands
ALTER TABLE duty_rates ADD COLUMN quantity_threshold_bands JSONB;
          -- for J-condition quantity threshold bands
ALTER TABLE duty_rates ADD COLUMN value_threshold_bands JSONB;
          -- for M-condition value threshold bands
ALTER TABLE duty_rates ADD COLUMN unit_price_threshold_bands JSONB;
          -- for U-condition unit price threshold bands
ALTER TABLE duty_rates ADD COLUMN count_threshold_bands JSONB;
          -- for X-condition count threshold bands
ALTER TABLE duty_rates ADD COLUMN reduction_bands JSONB;
          -- for L-condition price-triggered reduction bands
ALTER TABLE duty_rates ADD COLUMN duty_max_total_rate NUMERIC(8,4);
          -- ceiling on total rate (from MAX {rate}% clause)
ALTER TABLE duty_rates ADD COLUMN duty_per_item BOOLEAN DEFAULT FALSE;
          -- T suffix: per whole item
ALTER TABLE duty_rates ADD COLUMN duty_per_article BOOLEAN DEFAULT FALSE;
          -- A suffix: per article
```

---

## DUTY EXPRESSION PARSING FUNCTION

Implement a single, comprehensive duty expression parser:

```python
import re
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Unit normalisation
# ---------------------------------------------------------------------------
UNIT_DESCRIPTIONS = {
    "DTN": "per 100 kg (decitonnes)",
    "TNE": "per metric tonne",
    "KGM": "per kilogram",
    "HLT": "per hectolitre (100 L)",
    "LTR": "per litre",
    "MIL": "per 1,000 items",
    "NAR": "per item",
    "MTQ": "per cubic metre",
    "MTK": "per square metre",
    "MTR": "per linear metre",
    "GRM": "per gram",
    "KNS": "per kg of sugar",
    "KSD": "per kg sucrose dry matter",
    "KMA": "per kg methylamine",
    "KNI": "per kg nitrogen",
    "KPO": "per kg potassium oxide",
    "KPH": "per kg phosphorus pentoxide",
    "KSH": "per kg shelled product",
    "KPP": "per kg diphosphorus pentoxide",
    "KUR": "per kg uranium",
    "GFI": "per gram fissile isotopes",
    "ASV": "per % vol alcohol",
    "DAP": "per decitonne raw product",
    "HMT": "per hectometre",
    "ENP": "per effective number of primary cells",
    "CCT": "per tonne carrying capacity",
    "CEN": "per 100 items",
    "LPA": "per litre pure alcohol",
    "ENC": "per cell equivalent",
    "MWH": "per megawatt-hour",
    "TJO": "per terajoule",
    "CTM": "per metric carat",
    "NPR": "per pair",
    "NCL": "per number of cells",
    "KPO": "per kg potassium oxide",
}

EA_COMPONENTS = {"EA", "EAR", "ADSZ", "ADSZR", "ADFM", "ADFMR"}

MEASUREMENT_BASIS_CODES = {"S", "E", "P", "A", "T"}


@dataclass
class ParsedDuty:
    """Normalised duty expression, ready to map to duty_rates columns."""
    duty_rate: Optional[Decimal] = None        # ad valorem %
    duty_amount: Optional[Decimal] = None      # primary specific amount
    duty_unit: Optional[str] = None            # primary unit code
    duty_amount_secondary: Optional[Decimal] = None
    duty_unit_secondary: Optional[str] = None
    duty_min_amount: Optional[Decimal] = None
    duty_max_amount: Optional[Decimal] = None
    duty_min_rate: Optional[Decimal] = None
    duty_max_rate: Optional[Decimal] = None
    duty_max_total_rate: Optional[Decimal] = None
    currency: str = "EUR"
    duty_expression_code: str = "01"           # 01=av, 02=specific, 03=compound, 04=triple, 00=nihil
    duty_expression_code_suffix: Optional[str] = None
    duty_rate_flag: Optional[str] = None       # R, M
    duty_measurement_basis: Optional[str] = None  # S, E, P, A, T
    duty_gross_weight_basis: bool = False      # G suffix
    has_entry_price: bool = False
    entry_price_type: Optional[str] = None
    entry_price_max_rate: Optional[Decimal] = None
    entry_price_max_additional_type: Optional[str] = None
    entry_price_max_specific: Optional[Decimal] = None
    is_nihil: bool = False
    is_alcohol_duty: bool = False
    requires_import_licence: bool = False
    anti_dumping_specific: bool = False
    duty_per_item: bool = False
    duty_per_article: bool = False
    siv_bands: Optional[list] = None
    weight_threshold_bands: Optional[list] = None
    reduction_bands: Optional[list] = None
    quantity_threshold_bands: Optional[list] = None
    value_threshold_bands: Optional[list] = None
    unit_price_threshold_bands: Optional[list] = None
    count_threshold_bands: Optional[list] = None
    raw_expression: str = ""
    parse_errors: list = field(default_factory=list)


def parse_amount(s: str) -> Optional[Decimal]:
    """Parse a number string that may contain commas as thousands separators."""
    try:
        return Decimal(s.replace(",", ""))
    except InvalidOperation:
        return None


def _extract_unit_and_suffixes(unit_str: str) -> tuple[str, Optional[str], Optional[str]]:
    """
    Given a token like 'KGM P' or 'KGM S' or 'DTN R' or 'DTN M' or 'DTN E'
    returns (base_unit, measurement_basis, rate_flag).
    """
    parts = unit_str.strip().split()
    base = parts[0] if parts else ""
    basis = None
    flag = None
    for p in parts[1:]:
        if p in MEASUREMENT_BASIS_CODES:
            basis = p
        elif p in ("R", "M"):
            flag = p
    return base, basis, flag


def parse_duty_expression(raw: str) -> ParsedDuty:
    """
    Parse a raw duty expression string (a single cell from the TARIC duty column,
    AFTER condition prefixes such as Cond: A cert: D-008 (01): have been stripped).
    Returns a ParsedDuty dataclass.
    """
    result = ParsedDuty(raw_expression=raw)
    s = raw.strip()

    # ── NIHIL ────────────────────────────────────────────────────────────────
    if s.upper() == "NIHIL":
        result.is_nihil = True
        result.duty_rate = Decimal("0")
        result.duty_expression_code = "00"
        return result

    # ── Zero shorthand ───────────────────────────────────────────────────────
    if s == "0":
        result.duty_rate = Decimal("0")
        result.duty_expression_code = "01"
        return result

    # ── Pure supplementary unit (unit code only, no amount) ─────────────────
    pure_unit_codes = set(UNIT_DESCRIPTIONS.keys()) | {
        "NAR", "MTQ C", "MTQ", "MWH", "LPA", "TJO", "CCT", "CTM", "NCL", "NPR",
        "KPP", "KNI", "KUR", "GFI", "KGM S", "MTR", "MTK",
    }
    if s in pure_unit_codes:
        result.duty_expression_code = "21"  # supplementary unit
        result.duty_unit = s
        return result

    # ── EA / EAR / ADSZ component only (no number) ──────────────────────────
    if s in EA_COMPONENTS:
        result.has_entry_price = True
        result.entry_price_type = s
        result.duty_expression_code = "06"  # entry price
        return result

    # ── Detect E/I suffix on specific duty ───────────────────────────────────
    e_suffix = bool(re.search(r'\bE\b', s))
    i_suffix = bool(re.search(r'\bI\b', s))
    if e_suffix:
        result.anti_dumping_specific = True
        result.duty_expression_code_suffix = "E"
        s = re.sub(r'\s+E\b', '', s)
    if i_suffix:
        result.requires_import_licence = True
        result.duty_expression_code_suffix = "I"
        s = re.sub(r'\s+I\b', '', s)

    # ── Strip G suffix (gross weight) ────────────────────────────────────────
    if re.search(r'\bG\s*$', s):
        result.duty_gross_weight_basis = True
        s = re.sub(r'\s*G\s*$', '', s).strip()

    # ── Parse MAX clause(s) ──────────────────────────────────────────────────
    # MAX {rate}% or MAX {amount} EUR {unit}
    max_matches = list(re.finditer(
        r'MAX\s+([\d,\.]+)\s*(EUR\s+\w+|%)', s
    ))
    for m in reversed(max_matches):
        val_str, unit_or_pct = m.group(1), m.group(2).strip()
        val = parse_amount(val_str)
        if unit_or_pct == "%":
            result.duty_max_rate = val
        elif "EUR" in unit_or_pct:
            unit = unit_or_pct.replace("EUR", "").strip()
            result.duty_max_amount = val
            if not result.duty_unit:
                result.duty_unit = unit
        s = s[:m.start()].strip()

    # ── Parse MIN clause ─────────────────────────────────────────────────────
    min_match = re.search(r'MIN\s+([\d,\.]+)\s+EUR\s+(\w+)', s)
    if min_match:
        result.duty_min_amount = parse_amount(min_match.group(1))
        result.duty_unit = min_match.group(2)
        s = s[:min_match.start()].strip()

    # ── Parse EA/EAR/ADSZ component ──────────────────────────────────────────
    ea_match = re.search(
        r'\+\s*(EA|EAR|ADSZ|ADSZR|ADFM|ADFMR)(?:\s+MAX\s+([\d,\.]+)\s*(%|EUR\s+\w+))?(?:\s+MAX\s+([\d,\.]+)\s*EUR\s+(\w+))?',
        s
    )
    if ea_match:
        result.has_entry_price = True
        result.entry_price_type = ea_match.group(1)
        result.duty_expression_code = "06"
        if ea_match.group(2):
            result.entry_price_max_rate = parse_amount(ea_match.group(2))
        if ea_match.group(4):
            result.entry_price_max_specific = parse_amount(ea_match.group(4))
            result.entry_price_max_additional_type = ea_match.group(5)
        s = s[:ea_match.start()].strip()

    # ── ASV alcohol duty detection ────────────────────────────────────────────
    if "ASV" in s:
        result.is_alcohol_duty = True

    # ── Now parse the numeric components that remain ──────────────────────────
    # Pattern: {amount}% + {amount2} EUR {unit2} + {amount3} EUR {unit3}
    # OR: {amount} EUR {unit} [P|S|E|A|T] + {amount2} EUR {unit2}
    # OR: {amount}%
    # OR: {amount} EUR {unit}

    # Try triple-component: rate% + specific1 + specific2
    triple = re.match(
        r'^([\d,\.]+)\s*%\s*\+\s*([\d,\.]+)\s+EUR\s+(\w+(?:\s+[SPEAT])?)\s*\+\s*([\d,\.]+)\s+EUR\s+(\w+(?:\s+[SPEAT])?)$',
        s
    )
    if triple:
        result.duty_rate = parse_amount(triple.group(1))
        result.duty_amount = parse_amount(triple.group(2))
        base1, basis1, _ = _extract_unit_and_suffixes(triple.group(3))
        result.duty_unit = base1
        result.duty_measurement_basis = basis1
        result.duty_amount_secondary = parse_amount(triple.group(4))
        base2, _, _ = _extract_unit_and_suffixes(triple.group(5))
        result.duty_unit_secondary = base2
        result.duty_expression_code = "04"
        return result

    # Try compound: rate% + specific
    compound = re.match(
        r'^([\d,\.]+)\s*%\s*\+\s*([\d,\.]+)\s+(?:EUR|EUC)\s+(\w+(?:\s+[SPEAT])?)$',
        s
    )
    if compound:
        result.duty_rate = parse_amount(compound.group(1))
        result.duty_amount = parse_amount(compound.group(2))
        base, basis, flag = _extract_unit_and_suffixes(compound.group(3))
        result.duty_unit = base
        result.duty_measurement_basis = basis
        result.duty_rate_flag = flag
        result.currency = "EUR"
        result.duty_expression_code = "03"
        return result

    # Try pure ad valorem
    av_only = re.match(r'^([\d,\.]+)\s*%$', s)
    if av_only:
        result.duty_rate = parse_amount(av_only.group(1))
        result.duty_expression_code = "01"
        if result.duty_min_amount or result.duty_max_amount:
            result.duty_expression_code = "15"  # av with min/max
        return result

    # Try pure specific: amount EUR unit [suffix]
    specific = re.match(
        r'^([\d,\.]+)\s+(?:EUR|EUC)\s+(\w+(?:\s+[SPEAT])?)\s*$',
        s
    )
    if specific:
        result.duty_amount = parse_amount(specific.group(1))
        base, basis, flag = _extract_unit_and_suffixes(specific.group(2))
        result.duty_unit = base
        result.duty_measurement_basis = basis
        result.duty_rate_flag = flag
        result.currency = "EUR"
        result.duty_expression_code = "02"
        return result

    # Try ASV compound: amount EUR ASV X + amount2 EUR unit2
    asv_compound = re.match(
        r'^([\d,\.]+)\s+EUR\s+(\w+)\s+[XP]\s*(?:\+\s*([\d,\.]+)\s+EUR\s+(\w+))?$',
        s
    )
    if asv_compound:
        result.duty_amount = parse_amount(asv_compound.group(1))
        result.duty_unit = asv_compound.group(2)
        if asv_compound.group(3):
            result.duty_amount_secondary = parse_amount(asv_compound.group(3))
            result.duty_unit_secondary = asv_compound.group(4)
            result.duty_expression_code = "03"
        else:
            result.duty_expression_code = "02"
        result.is_alcohol_duty = True
        return result

    # Try ENC ENP: amount ENC ENP
    enc_match = re.match(r'^([\d,\.]+)\s+ENC\s+ENP$', s)
    if enc_match:
        result.duty_amount = parse_amount(enc_match.group(1))
        result.duty_unit = "ENP"
        result.duty_expression_code = "02"
        return result

    # If nothing matched, log and return partial
    result.parse_errors.append(f"Could not fully parse duty expression: {raw!r}")
    return result


def parse_siv_condition(cond_str: str) -> Optional[list]:
    """
    Parse a V-condition SIV band string.
    Returns a list of band dicts or None if not a V-condition.
    """
    if not cond_str.startswith("V "):
        return None
    bands = []
    # Each segment: V {threshold} EUR/{unit}({expr}):{rate}% [+ {amount} EUR {unit}]
    segments = re.findall(
        r'V\s+([\d,\.]+)\s+EUR/(\w+)\((\d+)\):([\d,\.]+)\s*%?\s*(?:\+\s*([\d,\.]+)\s+EUR\s+(\w+))?',
        cond_str
    )
    for seg in segments:
        threshold, unit, expr_id, rate_str, amount_str, amount_unit = seg
        bands.append({
            "threshold": float(threshold.replace(",", "")),
            "threshold_unit": unit,
            "duty_expression_id": expr_id,
            "duty_rate": float(rate_str.replace(",", "")) if rate_str else 0.0,
            "duty_amount": float(amount_str.replace(",", "")) if amount_str else None,
            "duty_amount_unit": amount_unit or None,
        })
    return bands if bands else None


def parse_threshold_condition(prefix: str, cond_str: str) -> Optional[list]:
    """
    Parse R/J/M/U/X threshold conditions.
    prefix: 'R', 'J', 'M', 'U', 'X'
    """
    pattern = rf'{prefix}\s+([\d,\.]+)(?:\s+EUR)?/(\w+)\((\d+)\)'
    segments = re.findall(pattern, cond_str)
    if not segments:
        return None
    return [
        {
            "threshold": float(s[0].replace(",", "")),
            "unit": s[1],
            "measure_expression_code": s[2],
        }
        for s in segments
    ]
```

---

## CONDITION TYPE REFERENCE (EXTENDED)

Every measure condition in TARIC is identified by a condition type code.
You must parse and store ALL of these — not just A and Y:

| Code | Name | Logic | Meaning |
|------|------|-------|---------|
| A | Certificate required for rate | ALL_REQUIRED | Importer MUST present the certificate to get the stated rate. Without it, fallback applies. |
| B | End-use authorisation | ALL_REQUIRED | Goods must be used for a specific authorised end-use. Cert shows authorisation. |
| C | Certificate required (compliance) | ALL_REQUIRED | Compliance certificate — often for phytosanitary, veterinary, organic certification. |
| D | Certificate required (origin preference) | ALL_REQUIRED | Document proves preferential origin for the claimed trade agreement rate. |
| E | Licence required (import/export) | ALL_REQUIRED | Importer must hold a valid import or export licence. |
| F | Flat suspension / price-linked | CONDITIONAL | Specific amount suspended or reduced if condition met (see F-condition parsing above). |
| H | Document for statistical purposes | INFORMATIONAL | No financial gating — just a statistical reporting requirement. |
| I | Presentation of certificate (informational) | INFORMATIONAL | Certificate must be presented but does not gate a financial rate. |
| J | Quantity threshold | THRESHOLD | Measure applies only within specified quantity bands. |
| L | Price-triggered reduction | THRESHOLD | Duty reduction triggered when declared price exceeds threshold bands. |
| M | Value threshold | THRESHOLD | Measure applies above/below declared value threshold. |
| N | Certificate (negative / exemption) | ANY_SUFFICIENT | Presenting this cert exempts from the measure (import prohibition context). |
| O | Document for origin proof | ALL_REQUIRED | Documentary proof of non-preferential origin. |
| Q | Quota balance | THRESHOLD | Measure linked to available quota balance. |
| R | Weight / quantity threshold | THRESHOLD | Measure applies above/below weight or quantity threshold. |
| S | Security / guarantee | REQUIRED | Financial security (guarantee) must be lodged before importation. |
| U | Unit price threshold | THRESHOLD | Measure applies above/below a declared unit price threshold. |
| V | Standard import value / entry price | THRESHOLD | Duty determined by declared CIF price vs SIV/entry price band table. |
| X | Item count threshold | THRESHOLD | Measure applies above/below an item count threshold. |
| Y | Certificate for exemption from measure | ANY_SUFFICIENT | Presenting ANY ONE of these certs exempts the shipment from the measure entirely. |
| Z | Certificate (additional information) | INFORMATIONAL | Additional information certificate — no financial gating. |

Store `condition_logic` as:
- `'ALL_REQUIRED'` for A, B, C, D, E, O
- `'ANY_SUFFICIENT'` for N, Y
- `'THRESHOLD'` for J, L, M, Q, R, U, V, X
- `'CONDITIONAL'` for F
- `'INFORMATIONAL'` for H, I, Z
- `'QUOTA'` for Q, S

**Add these columns to `measure_conditions`:**
```sql
ALTER TABLE measure_conditions ADD COLUMN condition_code_raw VARCHAR(4);
          -- Raw condition code letter(s) from source
ALTER TABLE measure_conditions ADD COLUMN threshold_data JSONB;
          -- Parsed threshold bands (for V, R, L, J, M, U, X conditions)
ALTER TABLE measure_conditions ADD COLUMN suspension_full_amount NUMERIC(14,4);
          -- For F-conditions: the full (pre-suspension) amount
ALTER TABLE measure_conditions ADD COLUMN suspension_reduced_amount NUMERIC(14,4);
          -- For F-conditions: the suspended (reduced) amount
ALTER TABLE measure_conditions ADD COLUMN is_threshold_condition BOOLEAN DEFAULT FALSE;
          -- true for V, R, L, J, M, U, X
ALTER TABLE measure_conditions ADD COLUMN is_financial BOOLEAN DEFAULT TRUE;
          -- false for H, I, Z (informational only)
```

---

## DUTY UNITS REFERENCE TABLE (NEW)

Add a reference table for all unit codes:

```sql
CREATE TABLE duty_units (
    code            VARCHAR(10) PRIMARY KEY,
    description     TEXT NOT NULL,
    category        VARCHAR(20),    -- 'weight', 'volume', 'count', 'energy', 'alcohol', 'other'
    base_si_unit    VARCHAR(10),    -- e.g. 'kg' for DTN and TNE, 'L' for HLT and LTR
    conversion_to_si NUMERIC(18,8)  -- factor to convert to base_si_unit
);
```

Seed with all codes from the unit table above.

---

## CERTIFICATE CODE REFERENCE (EXTENDED)

Add these additional certificate codes to the `certificate_codes` seed table,
beyond what was in v2:

| Code  | Description | Category |
|-------|-------------|----------|
| Y-155 | Certificate of authenticity / preferential origin proof | origin |
| N-990 | Tariff Rate Quota licence | quota_licence |
| A-001 | Tariff quota allocation licence (type 1) | quota_licence |
| A-004 | Tariff quota allocation licence (type 4) | quota_licence |
| A-007 | Tariff quota allocation licence (type 7) | quota_licence |
| A-019 | Tariff quota allocation licence (type 19) | quota_licence |
| A-022 | Tariff quota allocation licence (type 22) | quota_licence |
| D-017 | ATR movement certificate | origin |
| D-019 | EUR-MED movement certificate | origin |
| D-020 | Import licence (TRQ) | quota_licence |
| D-023 | Form A (GSP) — variant 23 | origin |
| D-024 | Form A (GSP) — variant 24 | origin |
| D-025 | Battery cell compliance certificate | compliance |
| D-027 | Battery cell compliance certificate (type 27) | compliance |
| D-028 | Battery cell compliance certificate (type 28) | compliance |
| D-029 | Proof of preferential origin (additional) | origin |
| Y-020 | Declaration — goods not subject to anti-dumping (type 20) | anti_dumping |
| Y-019 | Declaration — goods not subject to anti-dumping (type 19) | anti_dumping |
| Y-022 | Declaration — goods not subject to anti-dumping (type 22) | anti_dumping |
| Y-036 | Wine analysis document | control |
| Y-046 | Declaration goods not subject to restriction | exemption |
| Y-057 | Import authorization for ozone-depleting substances | licence |
| Y-060 | Plant health certificate | sanitary |
| Y-062 | Certificate for special purposes (type 62) | compliance |
| Y-063 | Certificate for special purposes (type 63) | compliance |
| Y-070 | ODS import licence | licence |
| Y-072 | Veterinary/sanitary certificate (beef) | sanitary |
| Y-073 | Veterinary/sanitary certificate (pork) | sanitary |
| Y-074 | Veterinary/sanitary certificate (poultry) | sanitary |
| Y-075 | Veterinary/sanitary certificate (sheep/goat) | sanitary |
| Y-076 | Veterinary/sanitary certificate (game) | sanitary |
| Y-077 | Veterinary/sanitary certificate (fish) | sanitary |
| Y-078 | Veterinary/sanitary certificate (dairy) | sanitary |
| Y-079 | Veterinary/sanitary certificate (eggs) | sanitary |
| Y-080 | CITES certificate | cites |
| Y-084 | Timber FLEGT licence | licence |
| Y-085 | Timber exemption declaration | exemption |
| Y-086 | REX declaration (individual supplier) | origin |
| Y-087 | REX declaration — variant 87 | origin |
| Y-088 | REX declaration — variant 88 | origin |
| Y-089 | REX declaration — variant 89 | origin |
| Y-090 | REX declaration — variant 90 | origin |
| Y-091 | REX declaration — variant 91 | origin |
| Y-104 | CITES appendix certificate | cites |
| Y-105 | CITES re-export certificate | cites |
| Y-106 | CITES import permit | cites |
| Y-109 | CITES pre-Convention certificate | cites |
| Y-110 | CITES Annex IV certificate | cites |
| Y-111 | CITES Annex V certificate | cites |
| Y-112 | CITES Annex VI certificate | cites |
| Y-113 | CITES Annex VII certificate | cites |
| Y-115 | CITES personal effects exemption | cites |
| Y-116 | EUR-MED origin declaration | origin |
| Y-120 | Declaration of conformity (product safety) | compliance |
| Y-121 | Declaration of end-use | end_use |
| Y-122 | Declaration of non-preference | origin |
| Y-123 | Authorisation for end-use procedure | end_use |
| Y-125 | Specific exemption certificate | exemption |
| Y-127 | Steel import licence | licence |
| Y-128 | Renewable energy guarantee of origin | compliance |
| Y-134 | Electricity certificate of origin | compliance |
| Y-135 | Biomass sustainability certificate | compliance |
| Y-136 | Biogas sustainability certificate | compliance |
| Y-137 | Hydrogen certificate of origin | compliance |
| Y-138 | Wine certificate of origin | origin |
| Y-146 | Dual-use item control document | control |
| Y-151 | Honey geographic origin declaration | origin |
| Y-152 | Declaration goods comply with regulation | compliance |
| Y-154 | End-use simplified procedure declaration | end_use |
| Y-160 | Annex II declaration — goods not listed | exemption |
| Y-162 | Entry under simplified procedure | compliance |
| Y-163 | Oral/email declaration (threshold goods) | compliance |
| Y-166 | AEO authorisation | aeo |
| Y-167 | Approved exporter status | origin |
| Y-169 | Goods not containing controlled items | exemption |
| Y-170 | Phytosanitary certificate (type 170) | sanitary |
| Y-171 | Phytosanitary — additional declaration | sanitary |
| Y-172 | Phytosanitary — re-export | sanitary |
| Y-173 | Phytosanitary — transit | sanitary |
| Y-174 | Phytosanitary — wood packaging | sanitary |
| Y-175 | Phytosanitary — regulated commodity | sanitary |
| Y-176 | Phytosanitary — high-risk commodity | sanitary |
| Y-177 | Phytosanitary — priority pest list | sanitary |
| Y-178 | Phytosanitary — interception history | sanitary |
| Y-179 | Import authorisation (product safety) | licence |
| Y-182 | Radioactivity certificate | compliance |
| Y-185 | CITES appendix (specific type) | cites |
| Y-199 | CITES re-export certificate (type 199) | cites |
| Y-235 | Wildlife import permit | licence |
| Y-237 | Renewable electricity declaration | compliance |
| Y-238 | Guarantees of origin (electricity) | compliance |
| Y-239 | Honey authenticity declaration | compliance |
| Y-240 | Organic farming equivalence | compliance |
| Y-241 | Organic import authorisation | licence |
| Y-242 | Food contact material declaration | compliance |
| Y-250 | CITES permit (import) | cites |
| Y-251 | CITES permit (re-export) | cites |
| Y-257 | Steel safeguard import licence | licence |
| Y-321 | REX registered exporter declaration | origin |
| Y-320 | REX statement on invoice | origin |
| Y-323 | Statement of origin (non-REX) | origin |
| Y-693 | Honey import certificate | compliance |
| Y-694 | Honey origin certificate | origin |
| Y-695 | Honey authenticity report | compliance |
| Y-698 | Aquaculture certificate | sanitary |
| Y-699 | Shellfish purification certificate | sanitary |
| Y-704 | Health certificate (live bivalve molluscs) | sanitary |
| Y-705 | Health certificate (fishery products) | sanitary |
| Y-709 | Health certificate (aquaculture animals) | sanitary |
| Y-710 | Health certificate (processed fishery products) | sanitary |
| Y-711 | Health certificate (live fish for human consumption) | sanitary |
| Y-712 | Health certificate (crustaceans) | sanitary |
| Y-713 | Health certificate (raw milk products) | sanitary |
| Y-715 | Sanitary certificate (live animals) | sanitary |
| Y-727 | Prior notification of food/feed imports | control |
| Y-728 | Common Health Entry Document (CHED) | control |
| Y-729 | CHED (plants) | control |
| Y-731 | CHED (animal products) | control |
| Y-732 | CHED (live animals) | control |
| Y-733 | CHED (food of non-animal origin) | control |
| Y-734 | CHED (composite products) | control |
| Y-738 | CHED (fish) | control |
| Y-739 | CHED (aquaculture) | control |
| Y-740 | CHED (composite — animal by-products) | control |
| Y-747 | CHED (veterinary) | control |
| Y-749 | CHED (organic) | control |
| Y-750 | CITES (type 750) | cites |
| Y-756 | Organic equivalence declaration | compliance |
| Y-759 | Dual-use export control document | control |
| Y-769 | GMO notification document | control |
| Y-786 | Battery regulation compliance | compliance |
| Y-787 | Battery SoC technical file | compliance |
| Y-788 | Battery recycled content declaration | compliance |
| Y-789 | Battery due diligence report | compliance |
| Y-790 | Battery performance & durability | compliance |
| Y-791 | Battery labelling declaration | compliance |
| Y-792 | Battery end-of-life management | compliance |
| Y-793 | Battery traceability document | compliance |
| Y-795 | Battery QMS declaration | compliance |
| Y-796 | Battery safety certificate | compliance |
| Y-797 | Battery recycled content certificate | compliance |
| Y-798 | Battery lifecycle assessment | compliance |
| Y-799 | Battery carbon footprint declaration | compliance |
| Y-824 | Declaration goods don't fall under measure | exemption |
| Y-835 | Wine origin certificate (type 835) | origin |
| Y-840 | FLEGT licence (type 840) | licence |
| Y-841 | FLEGT licence — bilateral agreement | licence |
| Y-842 | Timber origin proof | origin |
| Y-843 | Health certificate (meat) | sanitary |
| Y-845 | Veterinary certificate (meat products) | sanitary |
| Y-854 | Seal product exemption | exemption |
| Y-855 | Seal product indigenous exemption | exemption |
| Y-859 | Declaration goods meet exemption criteria | exemption |
| Y-862 | End-use simplification authorisation | end_use |
| Y-864 | Proof of preferential origin (FTA specific) | origin |
| Y-870 | CHED notification reference | control |
| Y-872 | Health certificate (variant 872) | sanitary |
| Y-873 | Health certificate (variant 873) | sanitary |
| Y-874 | FLEGT licence (variant 874) | licence |
| Y-875 | FLEGT — forest management certificate | licence |
| Y-877 | Timber legality verification | compliance |
| Y-878 | End-use exemption declaration | end_use |
| Y-879 | Animal welfare declaration | compliance |
| Y-882 | Organic import control document | control |
| Y-889 | Honey processing certificate | compliance |
| Y-897 | Veterinary certificate (processed meat) | sanitary |
| Y-904 | Cultural goods import licence | licence |
| Y-920 | Ozone-depleting substance quota licence | licence |
| Y-921 | Fluorinated gas quota licence | licence |
| Y-922 | Mercury import consent | licence |
| Y-923 | Dual-use licence | licence |
| Y-924 | CITES permit (type 924) | cites |
| Y-927 | Steel safeguard country exemption | exemption |
| Y-930 | Organic certification (additional) | compliance |
| Y-931 | Organic import authorisation (additional) | licence |
| Y-937 | Specific border control document | control |
| Y-942 | Seal — indigenous community certificate | exemption |
| Y-944 | CBAM declarant ID | compliance |
| Y-945 | CBAM installation declaration | compliance |
| Y-946 | CBAM embedded emissions report | compliance |
| Y-948 | CBAM transitional period certificate | compliance |
| Y-949 | Endangered species certificate | cites |
| Y-951 | Battery responsible sourcing certificate | compliance |
| Y-955 | Battery regulation compliance (type 955) | compliance |
| Y-957 | Battery state-of-health certificate | compliance |
| Y-958 | Energy label certificate | compliance |
| Y-959 | Ecodesign compliance declaration | compliance |
| Y-960 | IUU fishing catch certificate | compliance |
| Y-961 | Aquaculture growth stage certificate | sanitary |
| Y-962 | Dual-use end-use statement | control |
| Y-963 | Battery digital product passport | compliance |
| Y-964 | POP (persistent organic pollutants) exemption | exemption |
| Y-965 | Radioactive material transport certificate | compliance |
| Y-966 | REACH restriction exemption | exemption |
| Y-969 | CITES personal effects declaration | cites |
| Y-970 | F-gas quota allocation | licence |
| Y-971 | Renewable energy certificate (type 971) | compliance |
| Y-972 | Battery responsible minerals declaration | compliance |
| Y-978 | Phytosanitary emergency measure certificate | sanitary |
| Y-979 | Dual-use catch-all document | control |
| Y-980 | Mercury article exemption | exemption |
| Y-984 | Steel surveillance document | control |
| Y-986 | Simplified origin declaration | origin |
| Y-997 | Steel import licence (safeguard type) | licence |
| C-040 | INN declaration (product name) | compliance |
| C-041 | Non-preferential origin declaration | origin |
| C-042 | Preferential origin statement | origin |
| C-043 | Tariff-preference claim document | origin |
| C-045 | End-use simplified declaration | end_use |
| C-046 | Authorised use certificate | end_use |
| C-047 | Authorised use authorisation (type 47) | end_use |
| C-050 | Generalised Scheme of Preferences Form A (type 50) | origin |
| C-055 | ODS declaration (type 55) | compliance |
| C-056 | ODS import notification | control |
| C-057 | Exemption declaration (type 57) | exemption |
| C-058 | Endangered species management plan | cites |
| C-060 | ODS permit (type 60) | licence |
| C-064 | Cultural goods licence | licence |
| C-065 | Seal product commercial chain certificate | exemption |
| C-067 | CITES Annex B import permit | cites |
| C-071 | CITES export permit (type 71) | cites |
| C-073 | CITES re-export certificate (type 73) | cites |
| C-079 | Exemption claim document (type 79) | exemption |
| C-082 | Technical file (product safety) | compliance |
| C-083 | Wine analysis certificate | compliance |
| C-084 | End-use authorisation | end_use |
| C-085 | Dual-use item authorisation | licence |
| C-091 | Generalised preference (non-tariff origin) | origin |
| C-092 | Preference claim (type 92) | origin |
| C-101 | HACCP certificate (fishery products) | sanitary |
| C-121 | Freezer vessel document | compliance |
| C-126 | Organic certification authority document | compliance |
| C-400 | Import surveillance document | control |
| C-631 | F-gas equipment declaration | compliance |
| C-640 | Country of origin certificate for steel | origin |
| C-641 | Steel surveillance licence | licence |
| C-644 | Steel safeguard certificate | exemption |
| C-652 | Wine accompanying document (VI 1) | compliance |
| C-666 | Greenhouse gas monitoring permit | compliance |
| C-667 | Emissions trading permit | compliance |
| C-668 | CBAM compliance declaration | compliance |
| C-669 | Dual-use export authorisation (type 669) | licence |
| C-670 | Dual-use transit authorisation | licence |
| C-672 | Dual-use brokering authorisation | licence |
| C-673 | Steel origin certificate (variant 673) | origin |
| C-676 | ODS certificate (type 676) | licence |
| C-678 | Phytosanitary high-risk plant certificate | sanitary |
| C-679 | IAS prevention document | control |
| C-680 | IAS risk assessment | control |
| C-683 | IAS emergency permit | control |
| C-690 | ODS import permit (type 690) | licence |
| C-701 | Battery regulation type approval | compliance |
| C-809 | Dual-use catch-all (type 809) | control |
| L-001 | Wine import authorisation | licence |
| L-049 | CITES appendix import notification | cites |
| L-050 | CITES import permit (type L-050) | cites |
| L-065 | CITES — breeding farm certificate | cites |
| L-079 | Timber legality assessment | compliance |
| L-100 | Battery regulation type-approval | compliance |
| L-116 | Wine VI 1 import document | compliance |
| L-128 | FLEGT — partner country timber | licence |
| L-129 | FLEGT — bilateral VPA timber | licence |
| L-137 | FLEGT — due diligence regulation | compliance |
| L-138 | Timber legality regulation document | compliance |
| L-139 | Goods outside scope of measure | exemption |
| L-142 | FLEGT partner agreement | licence |
| L-143 | Documentary proof goods are exempt | exemption |
| L-146 | Health certificate — annex variant 146 | sanitary |
| L-147 | Health certificate — annex variant 147 | sanitary |
| L-148 | FLEGT timber import licence | licence |
| L-149 | CHED (type L-149) | control |
| L-150 | CHED-PP (plants) | control |
| L-151 | CHED-A (animals) | control |
| L-152 | CHED-D (feed and food) | control |
| L-153 | CHED (type L-153) | control |
| L-155 | Organic inspection certificate | compliance |
| L-156 | FLEGT licence (type L-156) | licence |
| L-157 | Organic operator authorisation | compliance |
| L-838 | Aquaculture origin certificate | origin |
| N-002 | Import licence (general) | licence |
| N-018 | Import declaration — goods not requiring licence | exemption |
| N-851 | Sanitary / phytosanitary certificate | sanitary |
| N-853 | Phytosanitary certificate (N-853) | sanitary |
| N-854 | Additional declaration (sanitary) | sanitary |
| N-990 | Tariff Rate Quota licence | quota_licence |
| U-004 | Authorised use (type U-004) | end_use |
| U-045 | Steel safeguard developing country certificate | exemption |
| U-078 | Steel safeguard exemption document | exemption |
| U-079 | Steel safeguard exemption variant | exemption |
| U-088 | REX registered exporter declaration | origin |
| K-020 | FLEGT partner country | licence |
| K-022 | FLEGT VPA country | licence |
| K-025 | Timber legality (type K-025) | compliance |
| K-027 | Timber origin (type K-027) | origin |
| K-028 | FLEGT bilateral | licence |
| K-029 | FLEGT additional | licence |
| K-030 | FLEGT (type K-030) | licence |
| K-031 | FLEGT (type K-031) | licence |
| K-032 | FLEGT (type K-032) | licence |
| K-520 | Trade agreement preference (type 520) | origin |
| K-521 | Trade agreement preference (type 521) | origin |
| K-522 | Trade agreement preference (type 522) | origin |
| K-523 | Trade agreement preference (type 523) | origin |
| K-524 | Trade agreement preference (type 524) | origin |
| K-525 | Trade agreement preference (type 525) | origin |
| K-526 | Trade agreement preference (type 526) | origin |
| K-527 | Trade agreement preference (type 527) | origin |

---

## MEASURE TYPE CLASSIFICATION (UNCHANGED FROM V2 — RETAINED FOR COMPLETENESS)

```
duty_rates          → flat financial charges (MFN, preferential, anti-dumping, suspensions, end-use duties)
tariff_quotas       → quota-gated rates (rate only applies while quota volume remains open)
price_measures      → price/quantity-triggered charges (entry price, SIV, representative prices, AD pending)
non_tariff_measures → border compliance (prohibitions, restrictions, veterinary, phytosanitary, CITES, sanctions)
supplementary_units → quantity declarations (pieces, pairs, kg, L, m² — must be declared on customs entry)
```

Routing function logic is unchanged from v2. The new condition types (V, R, L, J, M, U, X)
are handled within parsing — the destination table is still determined by measure type ID.
V/R/L/J/M/U/X conditions produce `threshold_data` on the `measure_conditions` row and
may also create a linked `price_measures` record if the measure itself is price-based.

---

## DATABASE SCHEMA (ADDITIONS TO V2)

Add the following new table and columns to the v2 schema:

```sql
-- Duty units reference table
CREATE TABLE duty_units (
    code            VARCHAR(10) PRIMARY KEY,
    description     TEXT NOT NULL,
    category        VARCHAR(20),
    base_si_unit    VARCHAR(10),
    conversion_to_si NUMERIC(18,8),
    last_updated    TIMESTAMP DEFAULT NOW()
);

-- Price measure SIV bands (linked to price_measures)
ALTER TABLE price_measures ADD COLUMN siv_bands JSONB;
ALTER TABLE price_measures ADD COLUMN reduction_bands JSONB;
ALTER TABLE price_measures ADD COLUMN weight_threshold_bands JSONB;
ALTER TABLE price_measures ADD COLUMN unit_price_threshold_bands JSONB;
ALTER TABLE price_measures ADD COLUMN count_threshold_bands JSONB;
ALTER TABLE price_measures ADD COLUMN quantity_threshold_bands JSONB;
ALTER TABLE price_measures ADD COLUMN value_threshold_bands JSONB;

-- duty_rates additions (all listed in DUTY FIELD SCHEMA ADDITIONS above)
-- Paste ALL ALTER TABLE duty_rates statements from that section.

-- measure_conditions additions
ALTER TABLE measure_conditions ADD COLUMN condition_code_raw VARCHAR(4);
ALTER TABLE measure_conditions ADD COLUMN threshold_data JSONB;
ALTER TABLE measure_conditions ADD COLUMN suspension_full_amount NUMERIC(14,4);
ALTER TABLE measure_conditions ADD COLUMN suspension_reduced_amount NUMERIC(14,4);
ALTER TABLE measure_conditions ADD COLUMN is_threshold_condition BOOLEAN DEFAULT FALSE;
ALTER TABLE measure_conditions ADD COLUMN is_financial BOOLEAN DEFAULT TRUE;
```

---

## API RESPONSE ADDITIONS

### Duty object — new fields

Add to the `duty` object in the `/tariff/lookup` response:

```json
{
  "duty_unit": "DTN",
  "duty_unit_description": "per 100 kg",
  "duty_amount_secondary": 20.6,
  "duty_unit_secondary": "DTN",
  "duty_min_amount": null,
  "duty_max_amount": null,
  "duty_min_rate": null,
  "duty_max_rate": null,
  "has_entry_price": false,
  "entry_price_type": null,
  "is_nihil": false,
  "is_alcohol_duty": false,
  "anti_dumping_specific": false,
  "siv_bands": null,
  "human_readable": "12.8% + EUR 176.80 per 100 kg"
}
```

The `human_readable` field must be generated for every duty expression:

```python
def duty_to_human_readable(d: ParsedDuty) -> str:
    """Generate a plain-English description of the duty."""
    parts = []

    if d.is_nihil:
        return "Nil (no duty)"

    if d.duty_rate is not None:
        parts.append(f"{d.duty_rate:g}%")

    if d.has_entry_price:
        parts.append(f"+ {d.entry_price_type} (entry price component — calculated at border)")

    if d.duty_amount is not None and d.duty_unit:
        unit_desc = UNIT_DESCRIPTIONS.get(d.duty_unit, d.duty_unit)
        parts.append(f"EUR {d.duty_amount:,.3f} {unit_desc}")

    if d.duty_amount_secondary is not None and d.duty_unit_secondary:
        unit_desc = UNIT_DESCRIPTIONS.get(d.duty_unit_secondary, d.duty_unit_secondary)
        parts.append(f"+ EUR {d.duty_amount_secondary:,.3f} {unit_desc}")

    if d.duty_min_amount is not None and d.duty_unit:
        parts.append(f"(minimum EUR {d.duty_min_amount:,.3f} {d.duty_unit})")

    if d.duty_max_amount is not None and d.duty_unit:
        parts.append(f"(maximum EUR {d.duty_max_amount:,.3f} {d.duty_unit})")

    if d.duty_min_rate is not None:
        parts.append(f"(minimum {d.duty_min_rate:g}%)")

    if d.duty_max_rate is not None:
        parts.append(f"(maximum {d.duty_max_rate:g}%)")

    if d.anti_dumping_specific:
        parts.append("[anti-dumping specific duty]")

    if d.is_alcohol_duty:
        parts.append("[per % vol alcohol]")

    if d.siv_bands:
        parts.append(
            f"(variable rate — {len(d.siv_bands)} price bands, calculated at border from declared CIF price)"
        )

    return " ".join(parts) if parts else "See conditions"
```

### Warnings — extended list

Add to `calculated.warnings[]` for:
- Any SIV/V-condition duty: "Rate is determined by SIV price bands. Provide your declared CIF price for an indicative rate."
- Any EA/EAR duty: "An agricultural entry price (EA) component applies. Exact amount cannot be pre-calculated — depends on declared CIF import price."
- Any MIN/MAX clause: "Minimum EUR {X} per {unit} applies — rate cannot be less than this."
- Any anti-dumping E-suffix: "An anti-dumping specific duty (EUR {X} per {unit}) applies in addition to the ad valorem rate."
- Any alcohol ASV duty: "Duty includes an alcohol-strength component — amount varies with actual % vol."
- Any import licence (I suffix): "An import licence is required for this rate to apply."
- Any quota N-990 cert: "This rate requires a valid Tariff Rate Quota licence (N-990). Check quota balance before shipping."
- Any NIHIL: "No duty is payable (explicitly nil by regulation)."
- Any compound duty: "Duty is calculated as a combination of ad valorem percentage AND a specific per-unit amount — both components apply simultaneously."

---

## PIPELINE MODULES (ADDITIONS TO V2)

### `app/pipeline/duty_units.py` (NEW)

Seed the `duty_units` reference table. Run once at bootstrap.
Source: the unit table in this prompt. Hardcode as a Python list of dicts.

### Updated `app/pipeline/eu_taric.py`

In the measure XML parser, after identifying the duty expression:
1. Call `parse_duty_expression()` on the raw duty string.
2. If parse result has `parse_errors`, log them with measure SID and raw string.
   Never drop the record — store with `raw_json` containing the error.
3. Map all `ParsedDuty` fields to `duty_rates` columns.
4. If `is_threshold_condition` (V/R/L/J/M/U/X), also upsert a `price_measures` record.
5. Seed `duty_units` table with any unit codes not already present.

### Updated `app/pipeline/uk_tariff.py`

The UK API returns duty as a formatted string in `attributes.duty_expression`.
Pass this string through `parse_duty_expression()` before upserting.

---

## PROJECT STRUCTURE (ADDITIONS TO V2)

```
veritariff/
├── app/
│   ├── pipeline/
│   │   ├── duty_parser.py         ← NEW: parse_duty_expression(), duty_to_human_readable(),
│   │   │                          ←      parse_siv_condition(), parse_threshold_condition()
│   │   ├── duty_units.py          ← NEW: seed duty_units reference table
│   │   ├── eu_taric.py            ← UPDATED: use duty_parser
│   │   └── uk_tariff.py           ← UPDATED: use duty_parser
```

---

## REQUIREMENTS & CONSTRAINTS (V2 UNCHANGED — ADDITIONS BELOW)

- All conditions of types V, R, L, J, M, U, X must be stored in `measure_conditions.threshold_data` as JSONB.
- The `duty_parser.py` module must be fully self-contained and independently testable.
- Add pytest unit tests for `parse_duty_expression()` covering all 37 expression types documented above. Put them in `tests/test_duty_parser.py`.
- Never mutate `UNIT_DESCRIPTIONS` at runtime — it is a read-only constant.
- EUC amounts must be normalised to EUR on ingest — store `currency = 'EUR'` always.
- Comma thousands separators in duty amounts (e.g. `1,554.300`) must be handled by `parse_amount()` before calling `Decimal()`.
- Any duty expression containing both an ad valorem percentage AND a specific amount must set `duty_expression_code = '03'` (compound); triple-component must use `'04'`.
- Any expression that cannot be parsed must be logged at ERROR level with measure SID, HS code, and raw string. A partial `ParsedDuty` with `parse_errors` populated must still be upserted so the raw data is not lost.
- The `human_readable` string must always be generated and returned in the API response — never expose raw TARIC notation to the frontend.

---

## WHAT TO DELIVER (V2 LIST PLUS ADDITIONS)

1. All Python files — fully implemented, no stubs, no TODOs.
2. SQLAlchemy ORM models for all tables including the new `duty_units` table and all new columns.
3. Alembic migration covering all new columns and tables.
4. `app/pipeline/duty_parser.py` — complete implementation of `parse_duty_expression()`, `parse_siv_condition()`, `parse_threshold_condition()`, `duty_to_human_readable()`.
5. `app/pipeline/duty_units.py` — seed function.
6. `tests/test_duty_parser.py` — pytest tests for all 37 expression types.
7. Updated `requirements.txt`.
8. Updated `README.md`.

Every parser must handle every duty expression type documented in this prompt.
The `parse_duty_expression()` function must never raise an exception — all errors go into `parse_errors`. No stubs. No TODOs.
