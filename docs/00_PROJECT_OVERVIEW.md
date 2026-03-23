# Veritariff Workflow — Claude Code Build Prompt

## Context

You are building the **Veritariff 7-Step Export Workflow** — the core product screen that sits behind the `/calculator` login. The user has already landed on `veritariffai.co`, seen the marketing site, and clicked **"Start Free"**. This is what they land on after authentication.

The workflow has already been partially built: the **HS Classification Calculator (Step 1)** is live. You are now building **Steps 2–7** as a full, connected workflow UI — plus the **Collaborative Workspace** sidebar that sits alongside it.

---

## Design System — Match veritariffai.co Exactly

**Brand palette (extract from live site):**
- Background: deep navy `#0D1F3C` (page bg) and near-black surfaces
- Primary accent: `#185FA5` (blue — CTAs, active states, links)
- Success/clear: `#0F6E56` (teal/green — cleared statuses, origin confirmed)
- Warning: `#854F0B` (amber — TRQ alerts, pending states)
- Danger/block: `#A32D2D` (red — hard blocks, errors, sanctions)
- Surface cards: `#1a2e4a` (slightly lighter than page bg)
- Borders: `rgba(255,255,255,0.08)` subtle
- Text primary: `#F8F6F0` (warm white)
- Text muted: `#8BA3C1`
- Mono/code: `#5BA3D9`

**Typography:**
- Font stack: `'IBM Plex Sans', system-ui, sans-serif` for body
- Mono: `'IBM Plex Mono', monospace` for codes, hashes, API values
- The site uses clean sans-serif, generous line-height, tight letter-spacing on labels

**Component language from the site:**
- Step numbers: circular badges, dark bg, accent border
- Status pills: small rounded tags — green "LIVE", amber "Q3 2026", red "BLOCKED"
- Cards: dark surface, subtle border, hover lift
- CTAs: solid `#185FA5` primary button, ghost secondary
- Progress: thin accent line connecting steps
- The "// How It Works" section uses numbered step cards with a timing badge — replicate this pattern inside the workflow

**Layout:**
- Left sidebar: workflow steps navigation (collapsible on mobile)
- Main panel: active step content
- Right sidebar (240px): Collaborative Workspace panel
- Top bar: shipment reference, corridor badge, overall progress bar

---

## What You Are Building

### Overall Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  TOPBAR: Shipment #VT-2026-0047 │ UK→DE │ HS 7224900289 │ ████░ Step 3/7  │
├──────────┬──────────────────────────────────────┬───────────────┤
│          │                                      │  WORKSPACE    │
│  STEPS   │        ACTIVE STEP CONTENT           │  PANEL        │
│  NAV     │                                      │  (Collab)     │
│  (left)  │                                      │  (right)      │
└──────────┴──────────────────────────────────────┴───────────────┘
```

---

## Step Navigation Sidebar (Left)

Seven steps. Each shows:
- Step number (circular badge)
- Step name
- Status icon: ✓ (complete, teal), ● (active, blue pulse), ○ (pending, muted), ⚠ (blocked, amber), ✗ (hard blocked, red)
- Estimated time badge

```
✓  1  Classification          ~2 min   [COMPLETE]
●  2  Duties & Origin         ~3 min   [ACTIVE]
○  3  Proof of Origin         ~5 min   [PENDING]
○  4  Supplier Declaration    ~3 min   [PENDING]
○  5  Sanctions & Licences    ~1 min   [PENDING]
○  6  CDS Declaration         ~4 min   [PENDING]
○  7  Barrister's Bundle      ~instant [PENDING]
```

Clicking a completed step navigates back to it (review mode).
Locked steps (not yet reached) are dimmed but show the step name.
A thin vertical accent line connects all steps on the left.

---

## Step 1 — Classification (ALREADY BUILT — show as complete)

Display a read-only summary card:
- HS Code: **7224 90 02 89**
- Description: Other alloy steel semi-finished — billets (42CrMo4)
- Classification path: Other Alloy → Ingot/Semi-finished → 7224
- Status badge: `CLASSIFIED ✓`
- "Edit classification" link (goes back to calculator)

---

## Step 2 — Duties & Rules of Origin

### 2a — MFN Gateway

Show a duty summary card with three columns:

| Duty type | Rate | Status |
|-----------|------|--------|
| EU MFN Customs Duty | 0% | ✓ Duty Free |
| TCA Preferential | 0% | Optional — but claim it |
| EU Safeguard (in-quota) | 0% | TRQ check required |
| EU Safeguard (out-of-quota) | 25% | Quota at [LIVE]% |
| NEW Safeguard (Jul 2026+) | 50% | If COM(2025)726 adopted |
| CBAM | Variable | >50t threshold: MANDATORY |
| German EUSt | 19% | On CIF + duty |
| Anti-Dumping / CVD | None | UK-origin — verify at shipment |

**TRQ Live Quota Widget** (prominent, prominent):
```
┌─────────────────────────────────────────┐
│  TRQ CATEGORY 26 — LIVE QUOTA           │
│  ████████████████░░░░  68% remaining    │
│  Estimated depletion: ~11 weeks         │
│  [⚠ Alert me at 25%]  [View TARIC]     │
└─────────────────────────────────────────┘
```
- Colour: green >50%, amber 25-50%, red <25%
- Show: raw tonnes remaining + % + estimated weeks at current burn rate
- "Last updated: [timestamp]" in muted mono text
- If quota exhausted: show red block with decision modal — (1) Wait for Q reset, (2) Re-route, (3) Absorb duty

### 2b — Rules of Origin Decision Tree

Show as an interactive decision flow. Each gate is a card that expands when reached:

**Upload zone (prominent, above the gates):**
```
┌──────────────────────┐  ┌──────────────────────┐
│  📄 Upload           │  │  📄 Upload           │
│  Supplier's Dec      │  │  Statement of Origin │
│  (TCA Annex ORIG-3)  │  │  (TCA Annex ORIG-4)  │
│  [Drop or browse]    │  │  [Drop or browse]    │
└──────────────────────┘  └──────────────────────┘
```
Accept: PDF, DOCX, JPG, PNG. Max 10MB each.

If document uploaded: show AI validation result inline:
- ✓ Green: field-by-field checklist (wording match %, EORI valid, cumulation stated, not expired)
- ⚠ Amber: specific field flagged with correction instruction
- ✗ Red: block with reason

If neither uploaded: show the RoO wizard gates sequentially:

**Gate 3A — Wholly Obtained**
Radio question: "Were ALL materials — including scrap and all ferroalloys — sourced entirely from the UK?"
- YES → green pill "WHOLLY OBTAINED" → skip to Step 3
- NO → expand Gate 3B

**Gate 3B — CTH Rule**
Show the input materials table (collapsible):

| Input | HS | Same as 7224? | Result |
|-------|----|---------------|--------|
| Scrap steel | 7204 | No | ✓ CTH satisfied |
| Ferro-chromium | 7202 | No | ✓ CTH satisfied |
| Ferro-molybdenum | 7202 | No | ✓ CTH satisfied |
| Iron ore / DRI | 2601/7203 | No | ✓ CTH satisfied |

Then: Melt and Pour question — two dropdown fields:
- "Where did melting occur?" → country ISO selector
- "Where did casting/pour occur?" → country ISO selector
- If both = GB → green "MELT + POUR: UK ✓"
- If melt = RU or BY → immediate red HARD BLOCK with message:
  > "🚫 HARD BLOCK: Russian/Belarusian melt origin detected. This shipment cannot proceed. This is not a classification issue — it is a sanctions violation."

**Gate 3C — Cumulation** (only shown if 3B borderline)
Toggle: "Do any input materials originate in the EU?"
- YES → show EU supplier declaration upload zone + note that statement must say "Cumulation applied with EU"
- NO → proceed

**Gate 3D — Sufficient Processing**
Checkbox list: "Which operations were performed in the UK?"
- ☑ EAF melting + continuous casting → origin-conferring
- ☑ Hot rolling → origin-conferring
- ☑ Heat treatment → origin-conferring
- ☐ Cutting to length → NOT sufficient alone
- ☐ Surface treatment → NOT sufficient alone

If only insufficient operations checked → NOT ORIGINATING → route to Gate 5 (non-preferential)

**Origin Result Card:**
```
┌─────────────────────────────────────────┐
│  ORIGIN DETERMINATION                   │
│  ✓ UK PREFERENTIAL ORIGIN CONFIRMED     │
│  Basis: CTH satisfied · Melt+pour UK    │
│  Cumulation: No cumulation applied      │
│  Evidence: MTC required (Step 4)        │
└─────────────────────────────────────────┘
```

---

## Step 3 — Proof of Origin (5 Methods)

Show as a selection panel. AI pre-selects the correct method and highlights it. Others are visible but dimmed.

**Method cards (horizontal scroll or 2-column grid):**

```
[RECOMMENDED]
┌──────────────────────────────────┐
│  Method 2: Statement on Origin   │
│  TCA Annex ORIG-4                │
│  Value £420,040 → EORI required  │
│  [Generate Statement]            │
└──────────────────────────────────┘

┌──────────────────┐  ┌──────────────────┐
│  Method 1: EUR.1 │  │  Method 3:       │
│  Physical cert   │  │  Importer's      │
│  Not required    │  │  Knowledge       │
│  for this case   │  │  Importer bears  │
│                  │  │  full liability  │
└──────────────────┘  └──────────────────┘

┌──────────────────┐  ┌──────────────────┐
│  Method 4:       │  │  Method 5:       │
│  Form A (GSP)    │  │  Supplier's Dec  │
│  N/A — Germany   │  │  Supports SoO    │
│  not GSP         │  │  (see Step 4)    │
└──────────────────┘  └──────────────────┘
```

**Statement on Origin Generator panel** (expands when Method 2 selected):

Show the auto-generated statement in a styled box:
```
┌─────────────────────────────────────────────────────────────────┐
│  AI GENERATED — REVIEW BEFORE SIGNING                          │
│                                                                 │
│  "The exporter of the products covered by this document         │
│  (EORI No: GB123456789000) declares that, except where          │
│  otherwise clearly indicated, these products are of             │
│  UK preferential origin.                                        │
│                                                                 │
│  No cumulation applied.                                         │
│                                                                 │
│  Goods: Other alloy steel billets (42CrMo4) · HS 7224 90 02 89 │
│  · 500 tonnes · Invoice VT-INV-2026-0047                        │
│  Melt location: United Kingdom (GB) · Heat: [from MTC]"         │
│                                                                 │
│  [✏ Edit]  [✓ Confirm & Sign]  [⬇ Download PDF]               │
│            [+ Add to Barrister's Bundle]                       │
└─────────────────────────────────────────────────────────────────┘
```

Fields that need user input highlighted in amber (e.g., heat number if MTC not yet uploaded).

Show validation checklist below:
- ✓ TCA Annex ORIG-4 wording: exact match
- ✓ EORI GB123456789000: validated via HMRC API
- ✓ Cumulation state: "No cumulation applied" — present
- ⚠ Heat number: MTC not uploaded — required for steel (link to Step 4)
- ✓ Value £420,040 > £5,400: EORI correctly included
- ✓ Validity: 12 months from today's date

---

## Step 4 — Supplier Declaration

### Part A — Who needs one?

Show a simple role selector:
```
I am the:
○ UK Supplier  ● Exporter (manufacturer)  ○ Exporter (re-export)  ○ Importer
```

### Part B — Steel-specific: MTC Upload

**This is the most important element of Step 4.**

MTC Upload zone with AI extraction preview:
```
┌─────────────────────────────────────────────────────────────────┐
│  MILL TEST CERTIFICATE (EN 10204 3.1 or 3.2)                   │
│  Required for: TCA origin proof · CBAM SEE · Sanctions screen   │
│                                                                 │
│  [📄 Drop MTC here or browse]                                   │
│                                                                 │
│  AI will extract:                                               │
│  · Melt location (country ISO) ← TCA mandatory                 │
│  · Heat number ← traceability                                   │
│  · Pour location (country ISO) ← TCA mandatory                 │
│  · Chemical composition (Cr, Mo, C, Mn...) ← classification    │
│  · CBAM production route (BF-BOF / EAF / DRI-EAF)             │
└─────────────────────────────────────────────────────────────────┘
```

After upload, show extraction results as a field-by-field table with confidence scores:

| Field | Extracted value | Confidence | Status |
|-------|----------------|------------|--------|
| Melt country | United Kingdom (GB) | 99% | ✓ |
| Pour country | United Kingdom (GB) | 98% | ✓ |
| Heat number | 2026-EAF3-1847 | 97% | ✓ |
| Production route | EAF | 94% | ✓ |
| Cr content | 0.98% | 92% | ✓ Alloy min met |
| Mo content | 0.22% | 91% | ✓ Alloy min met |
| Issue date | 15 March 2026 | 99% | ✓ Within 12 months |

Any field with confidence <85%: show amber flag with "Review required" and editable input.
Any field with FAIL result: red block.
If melt = RU or BY: **immediate hard block propagated back to Step 2**.

### Part C — Declaration writer

Show the supplier declaration text generator (same pattern as SoO in Step 3).

Duration toggle: **One-off** / **Long-term (recurring)**

Mandatory fields checklist with inline editors:
1. Identification of goods
2. Origin country
3. Cumulation state (auto-set from Gate 3C)
4. Dates (long-term only)
5. Authorisation (signature field)

---

## Step 5 — Sanctions & Licences

Show as a sequential gate-check list. Each gate runs automatically and shows result:

```
Gate 1: Strategic Export Control
[████████████] CHECKING...
→ ✓ HS 7224900289 — NOT CONTROLLED under UK SECL
   No SIEL/OIEL required. Verify at shipment date.

Gate 2: Sanctions Screen
[████████████] SCREENING 4 PARTIES...
→ ✓ Sheffield Alloy Works Ltd (GB EORI: GB123456789000) — CLEAR
→ ✓ Stahlhandel Meier GmbH (DE EORI: DE4567890120) — CLEAR
→ ✓ Meridian Freight Ltd (GB EORI: GB987654321000) — CLEAR
→ ✓ Melt origin: United Kingdom (GB) — CLEAR (Not RU/BY)
   Screened against: OFSI · UN · OFAC · EU Consolidated · BIS · UFLPA
   Last updated: [timestamp]

Gate 3: EU Prior Surveillance (TARIC V710)
[████████████] CHECKING TARIC...
→ ✓ No V710 measure active for HS 7224900289 at [date]
   Fetched live from EU TARIC. Next check at shipment date.

Gate 4: Melt and Pour Declaration
→ ✓ Melt country: GB (from MTC SAW-MTC-2026-1847)
→ ✓ Pour country: GB (from MTC SAW-MTC-2026-1847)
→ ✓ Heat number: 2026-EAF3-1847 (present)
   Mandatory from 1 October 2026. Currently: advisory.
```

**CBAM Section** (prominent card):
```
┌─────────────────────────────────────────────────────────────────┐
│  CBAM — MANDATORY (500t > 50t threshold)           EU Reg 2023/956 │
│                                                                 │
│  Production route: EAF (from MTC)                               │
│  Actual SEE: 0.468 tCO₂/t  vs  BF-BOF default: 1.987 tCO₂/t   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  YOUR LIABILITY:   ~€18,252   (234 tCO₂ × €78/t)     │    │
│  │  IF DEFAULTS USED: ~€77,493                           │    │
│  │  ─────────────────────────────────────────────────    │    │
│  │  YOU SAVE:         €59,241   by using actual data     │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Authorised CBAM Declarant: DE-CBD-2026-88821                   │
│  First surrender deadline: 30 September 2027                    │
│  [+ Add CBAM sheet to Barrister's Bundle]                       │
└─────────────────────────────────────────────────────────────────┘
```

If any gate FAILS: red block with specific action required. Shipment cannot proceed to Step 6 until all gates pass.

---

## Step 6 — CDS Declaration

Show a structured form with all 17 Data Elements. Fields auto-populated from shipment object shown in green. Fields requiring user input highlighted in amber.

Group the DEs into logical sections:

**Declaration type**
- DE 1/1–1/2: `EX — B1 Standard Export Declaration` [auto] ✓
- DE 1/10: `1040 — Permanent export` [auto] ✓
- DE 1/11: `000 — No additional procedure` [auto] ✓

**Additional information**
- DE 2/2: Toggle — `ECONX (AEO holder)` or `RRSOI (RoRo pre-lodge)` — user selects
- DE 2/3: Document codes — `C514 (MTC) · 9022 (Sanctions) · Y128 (CBAM)` [auto from completed steps] ✓

**Parties**
- DE 3/1 Exporter EORI: `GB123456789000` [from profile] ✓ Validated
- DE 3/18 Declarant EORI: `GB987654321000` (Meridian Freight) [input]

**Delivery & valuation**
- DE 4/1 Incoterms: dropdown `DAP` / `DDP` / `FCA` — user selects + named place input
- DE 4/16: `1 — Transaction value` [auto] ✓

**Goods location**
- DE 5/8 Destination: `DE` [from corridor] ✓
- DE 5/14 Dispatch: `GB` [auto] ✓

**Goods description**
- DE 6/1 Net mass: input field (pre-filled from packing list if uploaded)
- DE 6/5 Gross mass: input field
- DE 6/8 Commodity code: `7224900289` [from Step 1] ✓

**EXS Timing Calculator** (shown below the DEs):
```
Transport mode: [Sea container ▼]
ETD: [28 March 2026]

EXS must be lodged by: 27 March 2026, 12:00 UTC
                        ← 24h before departure (container sea rule)
[⏰ Set reminder]
```

**Submit button:**
```
[🚀 Submit to HMRC CDS]
```
After submission: show MRN in mono text with copy button.
`MRN: 26GBIMM0000047VT1`

---

## Step 7 — Barrister's Bundle

### Document validation gate

Show a checklist of all mandatory and conditional documents. Each row shows: document name, status (uploaded/generated/missing), SHA-256 hash (truncated), and action button.

```
┌─────────────────────────────────────────────────────────────────────┐
│  DOCUMENT VALIDATION GATE                                           │
│                                                                     │
│  MANDATORY                                                          │
│  ✓ Commercial Invoice        VT-INV-2026-0047    a3f9...  [View]  │
│  ✓ Packing List              VT-PKG-2026-0047    b8e4...  [View]  │
│  ✓ Mill Test Certificate     SAW-MTC-2026-1847   c2d8...  [View]  │
│  ✓ CDS MRN                   26GBIMM0000047VT1   [auto]   [View]  │
│  ✓ Sanctions clearance       Screen #4821        d4e1...  [View]  │
│                                                                     │
│  CONDITIONAL                                                        │
│  ✓ Statement on Origin       [Generated Step 3]  e9a2...  [View]  │
│  ✓ CBAM Embedded Emissions   [Generated Step 5]  f1b3...  [View]  │
│                                                                     │
│  OPTIONAL                                                           │
│  ○ Supplier's Declaration    [Not uploaded]               [Add]   │
│  ○ EUR.1 Certificate         [Not required]               [Skip]  │
│                                                                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  RELEASE GATE:                                                      │
│  ✓ All mandatory documents: VALIDATED                               │
│  ✓ TCA declaration signed                                           │
│  ✓ CBAM data complete                                               │
│  ✓ Sanctions: all parties cleared                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Clearance Certificate

When all gates pass, show the certificate generation:

```
┌─────────────────────────────────────────────────────────────────────┐
│  ✓ CLEARED FOR EXPORT                                               │
│                                                                     │
│  VERITARIFF CLEARANCE CERTIFICATE                                   │
│  Shipment: VT-2026-0047                                             │
│  Corridor: UK → Germany                                             │
│  HS Code: 7224 90 02 89                                             │
│  Timestamp: 2026-03-21T09:47:33Z UTC                                │
│  SHA-256: [full hash in mono]                                       │
│                                                                     │
│  [⬇ Download Bundle (AES-256 ZIP)]                                 │
│  [📧 Send to: Exporter · Freight Forwarder · DE Importer]          │
│  [🏦 Submit to bank for trade finance]                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Collaborative Workspace Panel (Right sidebar — always visible)

This is the always-on right panel. 240px wide. Collapses to icon bar on mobile.

### Header
```
WORKSPACE
Shipment VT-2026-0047
3 participants active
```

### Participant list
```
● Hasti (You) — Exporter
● Klaus Meier — Importer (DE)
● Meridian Freight — Forwarder
  James H. — online
```

Each participant shows: avatar initials, role badge, online indicator.

### Document access by role
Show a mini table:

| Document | Exporter | Importer | Forwarder |
|----------|---------|---------|-----------|
| Commercial Invoice | ✓ Full | ✓ Full | ✓ Full |
| MTC | ✓ Full | View | View |
| Statement of Origin | ✓ Edit | View | View |
| CDS MRN | View | View | ✓ Full |
| CBAM Sheet | ✓ Full | ✓ Full | — |
| Clearance Cert | ✓ Full | ✓ Full | ✓ Full |

### Shipment timeline (mini)
```
✓ Classification    21 Mar 09:14
✓ Duties            21 Mar 09:31
● Origin            In progress...
○ Supplier Dec
○ Sanctions
○ CDS
○ Bundle
```

### In-workspace messaging
```
┌─────────────────────────────┐
│ Klaus Meier · 09:22         │
│ "Do you have the CBAM       │
│  verifier accreditation     │
│  number for the MTC?"       │
└─────────────────────────────┘
┌─────────────────────────────┐
│ You · 09:35                 │
│ "Yes — TÜV SÜD              │
│  DE-V-AKK-2024-0081"        │
└─────────────────────────────┘

[Type a message...]     [Send]
```

### Invite button
```
[+ Invite participant]
```
Opens modal: enter email, assign role (Exporter / Importer / Freight Forwarder), set document access level.

---

## Top Bar

Fixed. Always visible.

```
[Veritariff logo]  Shipment VT-2026-0047  |  🇬🇧 UK → 🇩🇪 Germany  |  HS 7224900289  |  500t · 42CrMo4
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Progress: [████████████████░░░░░░░░░░░░]  Step 3 of 7  ·  ETA: ~12 min remaining
                                                        [Save draft]  [← Back to dashboard]
```

---

## Technical Notes for Claude Code

**Framework:** Next.js 14 (App Router) — match existing site stack.
**Styling:** Tailwind CSS — match existing site.
**State:** Use React state + context for shipment object. The shipment object accumulates data across all 7 steps.

**Shipment object structure (build toward this):**
```typescript
interface Shipment {
  id: string                    // VT-2026-XXXX
  corridor: string              // 'UK-DE'
  hs_code: string               // '7224900289'
  classification_id: string
  supplementary_units: string
  origin_status: 'PREFERENTIAL' | 'NON_PREFERENTIAL' | 'PENDING'
  duty_rate_applied: number
  regulatory_flags: string[]    // ['CBAM', 'TRQ_CAT26', 'MELT_POUR']
  trq_quota_remaining: number   // live from TARIC
  cbam_applicable: boolean
  cbam_see_actual: number       // tCO2/t
  cbam_see_default: number
  cbam_saving: number           // £ saving vs defaults
  sanctions_cleared: boolean
  melt_country_iso: string      // 'GB'
  pour_country_iso: string      // 'GB'
  heat_number: string
  statement_of_origin: object
  mtc_hash: string              // SHA-256
  cds_mrn: string               // 18-char
  documents: Document[]
  workspace_participants: Participant[]
  step_status: Record<1|2|3|4|5|6|7, 'complete'|'active'|'pending'|'blocked'>
  created_at: string
  updated_at: string
}
```

**API integrations to mock (build with placeholder responses, wire to real APIs later):**
- UK Trade Tariff: `api.trade-tariff.service.gov.uk`
- HMRC EORI validation: `api.service.hmrc.gov.uk/customs/eori/{number}`
- EU TARIC quota balance: `ec.europa.eu/taxation_customs/dds2/taric`
- ITA CSL sanctions: `api.trade.gov/consolidated_screening_list/search?q={entity}`

**Document upload:** Accept PDF/DOCX/JPG/PNG. Show upload progress. On upload, trigger mock AI extraction that returns the field values shown in the MTC extraction table above.

**SHA-256 hashing:** Hash all uploaded documents client-side using `crypto.subtle.digest('SHA-256', buffer)`. Store hash in shipment object. Display truncated (first 8 chars + `...`) with copy-to-clipboard.

**The most important interaction:** When MTC is uploaded and melt_country = 'RU' or 'BY', the entire workflow must immediately show a hard block — red overlay on the active step, red status on step 5 in the sidebar, and a persistent banner at the top: `🚫 HARD BLOCK: Russian/Belarusian melt origin. This shipment cannot proceed.`

---

## File Structure

```
app/
  workflow/
    [shipmentId]/
      page.tsx              ← main workflow shell
      layout.tsx            ← topbar + sidebar + workspace panel
      steps/
        step1-classification/
        step2-duties/
          TRQWidget.tsx
          RoOGates.tsx
          DutyTable.tsx
        step3-origin/
          MethodSelector.tsx
          StatementGenerator.tsx
        step4-supplier/
          MTCUploader.tsx
          MTCExtraction.tsx
          DeclarationWriter.tsx
        step5-sanctions/
          GateChecklist.tsx
          CBAMCalculator.tsx
        step6-cds/
          DataElements.tsx
          EXSCalculator.tsx
        step7-bundle/
          DocumentGate.tsx
          ClearanceCertificate.tsx
      components/
        WorkspacePanel.tsx
        StepNav.tsx
        TopBar.tsx
        StatusPill.tsx
        UploadZone.tsx
        ShipmentContext.tsx
```

---

## What NOT to build

- Do not build the marketing homepage — it already exists at veritariffai.co
- Do not build the login/auth flow — assume authenticated user
- Do not build the HS Classification calculator — Step 1 is already built, show it as a completed read-only card
- Do not build the pricing page — it exists
- Do not build the Trade Hub (buyer matching) — future feature, show as "coming soon" in workspace

---

## Start here

Begin with:
1. `ShipmentContext.tsx` — the shared state that all steps read from and write to
2. `layout.tsx` — the three-panel shell (step nav + main + workspace)
3. `TopBar.tsx` — shipment reference, corridor, progress bar
4. `StepNav.tsx` — the left sidebar with step statuses
5. `WorkspacePanel.tsx` — the right sidebar with participants, docs, messaging
6. Then build each step in order, starting with Step 2 (Step 1 is already built)

The workflow should feel like a **professional compliance cockpit** — dark, precise, information-dense but not cluttered. Every number should be live or clearly marked as mocked. Every status should be immediately readable. No unnecessary decorative elements. This is a tool that CFOs and Supply Chain Managers use to protect millions of pounds of shipment value.
