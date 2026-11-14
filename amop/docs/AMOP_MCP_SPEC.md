---
project: Alluvial Mining Operations Platform (AMOP)
codename: minecon-amop
version: 1.0.0
status: specification-frozen
target_host: Claude (claude-sonnet-4-6 / claude-opus-4-5) via MCP
primary_gui: Streamlit multipage (Antigravity-IDE-assisted)
orchestration: Model Context Protocol (MCP), 4 servers, 1 adjudication layer
language: Python 3.11+
document_purpose: >
  Single shareable context file for Claude to reason about, continue building,
  and adjudicate the integrated alluvial mining operations platform across all
  eight supplied workbooks. Treat this file as the ground truth for scope,
  business rules, adjudication thresholds, schemas, and tool surfaces.
---

# 0. Instructions to Claude (read this first)

You are assisting with the design, implementation, and adjudication of the
**Alluvial Mining Operations Platform (AMOP)**. Your job is to:

1. **Orchestrate** the MCP tool calls; do **not** perform grade, cost, VAM, or
   grade-credibility arithmetic yourself. Every numeric result must come from a
   deterministic Python function exposed as an MCP tool. If a tool is missing,
   say so and propose it — do not improvise.
2. **Respect the adjudication layer.** Before recommending any operational
   change to a user, call `adjudicate_full_chain(...)` and explain its verdict.
   The verdict is JSON, not prose — do not paraphrase the thresholds.
3. **Cite the workbook of record** when asked where a number or rule came from
   (e.g., "This 0.75 verification threshold comes from `Guyana_Outreach_
   Cost_Pipeline_Workbook.xlsx`, Fraud_Check!G3").
4. **Never silently fix data.** If a workbook contains a known defect (e.g., the
   INT column mismatch in `Refined Au_Grade_Model.xlsx`, or the `12` vs `0.12`
   energy rate in `FINAL2GEOS_..._simulation.xlsx`), surface it as a `DATA_ISSUE`
   finding in the adjudication output; do not silently correct.
5. **Stay within scope.** This platform is a *planning and decision-support*
   tool. It does **not** produce a resource or reserve statement, a JORC/NI 43-
   101 declaration, a legal opinion, or a certified optimum. The VAM, PSO, and
   GA layers are heuristics — flag them as such when relaying results.

Everything else in this document supports those five instructions.

---

# 1. Domain Glossary

| Term | Definition | Notes |
|---|---|---|
| **Alluvial gold** | Placer gold hosted in unconsolidated gravel, terrace, channel and saprolite horizons | Density 19.32 g/cm³ pure, ~10.49 g/cm³ alloyed with silver |
| **Pit (PIT-xx)** | A source unit with a grade (g/m³), volume (m³), bulk density, and X/Y coordinates | Grade credibility is adjudicated by `Z` (see §5.3) |
| **Stockpile / dumping point (ST-xx)** | A destination pad with coordinates, dump capacity, and (optionally) target grade | Fed by pits via VAM allocation |
| **Trommel** | Rotary wash-plant drum that scrubs and classifies alluvial feed | Efficiency driven by tilt angle, RPM, water flow, setup |
| **VAM** | Vogel's Approximation Method — penalty-based heuristic for the transportation problem | Returns an allocation matrix, not a certified optimum |
| **PSO** | Particle Swarm Optimization — used for weekly outreach-hour allocation and blend optimization | `pyswarms.single.GlobalBestPSO` |
| **GA** | Genetic Algorithm — used as an alternative to PSO for the holistic blend optimizer | `deap` |
| **Pan / bowl** | One filled pan = 1/240 m³ of material. Three pans = one horizon = 3/240 m³ sampled | Field fact, do not re-derive |
| **Horizon** | A geological layer between From (m) and To (m) depth | Sampled by three pans |
| **Panning log** | Qualitative field record of gold particle counts per pan, with size-class description | Source of truth for grade |
| **N_eff / Z** | Effective particle count and credibility `Z = 1 − e^(−N_eff / N*)`, N* = 10 | `Z ≥ 0.6` required for a pit to contribute > 30% of blend volume |
| **GPF / GP** | Grade Priority Factor `GPF = (G/Gmax)^α`; Grade Penalty `GP = 1 + λ(1 − GPF)` | Drives heuristic cost matrix before VAM |
| **SM** | Bounded Spatial Multiplier `SM ∈ [1 − θ, 1 + θ]`, default `θ = 0.3` | Prevents heuristic cost runaway |
| **Fraud_Check hard stop** | Any triggered hard-stop flag forces RED risk class, blocking introduction | F01, F02, F08, F12, F13, F14, F15, F21 |
| **Cash runway** | Weeks of remaining budget given planned stage costs and contingency | Must leave ≥ 2 weeks when allocating outreach hours |
| **Energy rate discrepancy** | The workbook uses `12` ($/kWh) in one sheet and `0.22 / 0.11` (peak/off-peak) in another — flag as `DATA_ISSUE`, use `0.12` as the working assumption | |

---

# 2. Workbook Inventory (full structural reference)

The eight workbooks are independent but interrelated. Each is treated as a
**domain module** with a dedicated MCP server. This section is the definitive
list of what each workbook contains.

## 2.1 `COMPREHENSIVE FEEDING.xlsx`

**Owner:** Mining camp / camp management
**Sheets:** CASH BOOK, Sheet2, NEW TRIAL
**Opening cash balance:** `52583.07149999976` (at `CASH BOOK!F7`)
**Purpose:** Track camp cash-book activity, categorize expenses by project and
category, and reconcile feeding rotations against cash outflow.

**Structure (CASH BOOK sheet):**
- Columns A–E: `DATE`, `DESCRIPTION`, `SUPPLIER/CUSTOMER`, `REF. NO.`,
  `PROJECT_CODE`
- Columns F–H: `CASH RECEIVED`, `CASH PAID`, `CASH BALANCE` (running balance =
  `H_{n-1} + F_n − G_n`)
- Columns I: `TYP` (project type code)
- Columns J–AD: 21 category columns driven by `IF(I_row="XX", G_row, 0)`

**Project codes (PRJT column):** `GRM`, `ALV`, `NAN`, `KOC`, `ELIT`, `ANY`,
`SEWM`, `EAGL`

**Expense category codes (TYP column):** `IT` (Income Tax/PAYE), `SSF` (SSNIT),
`T2` (Tier 2), `OE` (Office Expenses), `PC` (Professional Charges),
`BP` (Business Promo), `CC` (Communication Cost), `RM` (Repairs & Maintenance),
`TT` (Travel & Transport), `ST` (Stationery), `FE` (Food & Entertainment),
`FL` (Fuel & Lubricant), `TP` (Tools & Protective Clothing),
`WM` (Welfare & Medicals), `CSA` (Cleaning & Sanitation),
`ACC` (Accommodation & Hotel), `IMP` (Imprest), `UT` (Utility),
`COMM` (Community Relations), `WGS` (Field Wages), `NA` (Asset)

**Sheet2:** Feeding rotation matrix — staff × month grid (January–December),
column layout `D` = name, `E–P` = Jan–Dec.

**NEW TRIAL:** Alternate feeding rotation with month-number date (1–12) and
event count.

**Reconciliation rule (adjudication):** Feeding rotation must reconcile to
`CASH BOOK!FE` total per person per week. Flag `FEEDING_MISMATCH` if the
weekly FE total per active staff member deviates > 10% from the rotation's
expected days.

## 2.2 `Geospatial_Grade_Controlled_VAM_Stockpile_Optimizer.xlsx`
## 2.3 `Cost_Grade_Heuristic_Prioritized_VAM_Cost_MATRIX.xlsx`

These two are **the same model, two versions**. The second (`Cost_Grade_...`)
is the **bounded reformulation** and is the one to implement.

**Owner:** Geospatial planning
**Sheets:** README, Parameters, Pit Data, Distance Matrix, Haul Cost Matrix,
Grade Factors, Final Heuristic Matrix, Heuristic Calculation, VAM Input,
Future Extensions, Verification

**Pit data (5 pits):**

| Pit | Material | Grade | Volume |
|---|---|---|---|
| PIT-01 | Alluvial Gravel – High Terrace | 0.3 | (blank in workbook) |
| PIT-02 | Alluvial Gravel – Channel | 0.15 | |
| PIT-03 | Overburden / Low Grade | 0.3 | |
| PIT-04 | High Grade Pocket | 0.2 | |
| PIT-05 | Alluvial Gravel – Terrace 2 | 0.9 (bounded) / 0.6 (original) | |

**Distance matrix (m), 5 pits × 4 stockpiles:**

```
PIT-01: 1732.7, 1633.4, 1599.2, 63.7
PIT-02:   34.1,  139.4,  166.4, 1748.9
PIT-03:   22.8,  141.8,  163.5, 1741.2
PIT-04:   45.7,  165.1,  185.8, 1760.5
PIT-05:   53.3,  171.1,  187.8, 1755.2
```

**Haul cost matrix ($/m³) — bounded version:**

```
PIT-01:   4.00,  34.00,  79.96,  68.00
PIT-02:  67.12,  42.40,  61.00,  87.45
PIT-03:  45.83,  54.00,  65.00,  87.06
PIT-04:  86.23,  60.88,  30.45,  88.02
PIT-05:  56.78, 212.00, 100.00,  87.76
```

**Parameters (bounded version — authoritative):**

| Param | Default | Meaning |
|---|---|---|
| α (alpha) | 1 | Grade sensitivity exponent |
| β (beta) | 1 | Distance-score shape exponent |
| γ (gamma) | 1 | Cost-score shape exponent |
| λ (lambda) | 0.5 | Grade-penalty strength |
| w_D | 0.5 | Distance weight |
| w_C | 0.5 | Cost weight |
| θ (theta) | 0.3 | Max spatial cost adjustment |
| Max grade | `MAX(Pit Data!D4:D8)` | |
| Dmin / Dmax | from Distance Matrix | |
| Cmin / Cmax | from Haul Cost Matrix | |

**Final heuristic (bounded, authoritative):**

```
GPF(i)   = (G(i) / Gmax)^α
GP(i)    = 1 + λ · (1 − GPF(i))
DNF(i,j) = (D(i,j) − Dmin) / (Dmax − Dmin)       ∈ [0, 1]
CNF(i,j) = (C(i,j) − Cmin) / (Cmax − Cmin)       ∈ [0, 1]
SM(i,j)  = (1 − θ) + 2·θ·(w_D·DNF^β + w_C·CNF^γ) ∈ [1−θ, 1+θ]
H(i,j)   = C(i,j) · GP(i) · SM(i,j)
```

**Verification values (bounded version) — use as pytest fixtures:**

| Pit \ Stockpile | ST-01 | ST-02 | ST-03 | ST-04 |
|---|---|---|---|---|
| PIT-01 | 64.2191 | 118.0470 | 105.3408 | 65.3744 |
| PIT-02 | 70.3753 | 43.1348 | 65.0261 | 131.3235 |
| PIT-03 | 41.5572 | 51.2635 | 63.4873 | 118.6393 |
| PIT-04 | 91.5333 | 62.8972 | 29.5625 | 128.5312 |
| PIT-05 | 42.5154 | 217.4278 | 108.4145 | 95.9932 |

**Stockpile-aware extension:** `Stockpile Requirements` (capacity, current
volume, target/min/max grade), `Stockpile Compatibility` matrix, and
`Stockpile-Aware Matrix` divide base heuristic by compatibility. Only used
when target grades are entered; otherwise the plain bounded matrix is used.

## 2.4 `Guyana_Outreach_Cost_Pipeline_Workbook (1).xlsx`

**Owner:** Business development / investor relations
**Sheets:** README, Dashboard, Assumptions, Stage_Costs, Expense_Log, Pipeline,
Greedy, PSO, Fraud_Check, Contacts

**Assumptions (authoritative):**

| Parameter | Value |
|---|---|
| Scenario default | Base |
| Cost multipliers | Low 0.85, Base 1.0, High 1.3 |
| Delay multipliers | Low 0.8, Base 1.0, High 1.6 |
| Relationship friction (extra weeks per stage) | 0.5 |
| GYD per USD | 209 (placeholder; verify) |
| Total personal budget (US$) | 20,000 |
| Contingency | 10% |
| Weekly outreach hours | 40 |
| Greedy planning horizon (weeks) | 4 |

**Stage sequence (S1–S12):**

| Stage | Description | Base wk | Gatekeeper |
|---|---|---|---|
| S1 | Due diligence on investor / mandate | 2 | ASIC/ABN; counsel |
| S2 | Legal & compliance set-up | 4 | Counsel, work-authorisation |
| S3 | Desk research & target-universe build | 4 | GGMC tenure map, Gazettes |
| S4 | Institutional access (GGMC, GGDMA, GO-Invest) | 4 | Appointments |
| S5 | Relationship building & referrals | 8 | Trust via referrals |
| S6 | Outreach waves & screening calls | 6 | Follow-ups |
| S7 | Title verification (fraud-check workflow) | 6 | GGMC, Gazette 21-day |
| S8 | Site visits & technical validation | 6 | Interior travel, sampling |
| S9 | NDA, LOI, non-binding terms | 4 | Counsel drafting |
| S10 | Investor presentation & data room | 4 | Calls with Phoenix |
| S11 | Term sheet & JV negotiation; consent | 8 | GGMC written consent |
| S12 | Close-out, handover, reporting | 2 | Final report |

**Fraud_Check scorecard — 22 flags (F01–F22):**
- **Hard stops (any one forces RED):** F01, F02, F08, F12, F13, F14, F15, F21
- Amber threshold: 15% risk; Red threshold: 35% risk
- Min verification completion to introduce: **0.75**
- Risk class: `RED` if any hard-stop or risk ≥ 35%; `AMBER` if risk ≥ 15%;
  else `GREEN`
- Cleared to introduce: `GREEN` AND `verification_completion ≥ 0.75` AND
  `fail_count == 0`

**Verification workflow (V01–V12):** GGMC title record, written confirmation,
Gazette check, rentals & bond, identity/TIN, company & beneficial ownership,
litigation search, Amerindian land overlap, production comparison, site visit,
laboratory, counsel opinion.

**PSO channels (5):**

| # | Channel | Cap (leads/wk) | Saturation rate k | Min hrs |
|---|---|---|---|---|
| 1 | GGMC public records | 3 | 0.3 | 4 |
| 2 | GGDMA & referrals | 4 | 0.12 | 4 |
| 3 | GO-Invest & gov | 2 | 0.15 | 2 |
| 4 | Attorneys & professional | 3.5 | 0.1 | 3 |
| 5 | Field visits & regional | 3 | 0.07 | 4 |

Expected leads per channel: `cap × (1 − e^(−k·hours))`. Fitness = total
expected leads − shortfall penalties (`3 × max(0, min_hrs − hours)`).

## 2.5 `Refined Au_Grade_Model.xlsx`

**Owner:** Geology / grade control
**Sheets:** README, Assumptions, Modifiers, QUALITATIVE PANNING LOG, PanCalc,
HorizonCalc, HorizonGrade, PitComposite, Validation

**Constants (authoritative):**

| Parameter | Value | Unit | Source |
|---|---|---|---|
| Gold density | 19.32 | g/cm³ | physical |
| Silver density | 10.49 | g/cm³ | physical |
| Gold fineness | 0.9 | fraction | assumption |
| Alloy density | 19.32×0.9 + 10.49×0.1 | g/cm³ | derived |
| Alloy density mm | (above)/1000 | g/mm³ | derived |
| Panning recovery R_inf | 0.95 | fraction | assumption |
| Recovery length d_R | 0.1 | mm | assumption |
| Size decay δ (delta) | 0.2 | mm | assumption |
| Taylor scale κ | 0.8 | per score unit | fixed |
| S_max | 5 | score | fixed |
| Pareto α | 3 | – | assumption |
| Bowls per m³ | 240 | bowls/m³ | field fact |
| Bowls per pan | 1 | bowl | field fact |
| Bank factor | 1.0 | – | adjustable |
| Gravel density | 1.2 / 1.35 / 1.5 | t/m³ | field spec |
| Nugget credibility N* | 10 | nuggets | assumption |
| Infer class 5 from class 4 | ON | ON/OFF | assumption |
| Cap method | MIN | MIN / EULER | fixed |
| λ (particle mass) | 1 | – | calibrate |
| Blend prior | OFF | ON/OFF | default |
| Below-detection grade | 0 | g/m³ | – |
| Confidence z | 1.645 | – | 90% two-sided |
| Cut-off grade | 0.03 | g/m³ | placeholder |
| Validation tolerance | 0.3 | fraction | – |

**Size classes (5):**

| i | Class | Range (mm) | d_i (mm) | φ_i | m_i formula | R_i | Ncap_i |
|---|---|---|---|---|---|---|---|
| 1 | Coarse | > 0.71 | 1.0 | 0.55 | π/6·ρ_mm·d³·φ | R_inf·(1−e^(−d/d_R)) | 50 |
| 2 | Medium | 0.355–0.71 | 0.5 | 0.50 | same | same | 100 |
| 3 | Fine | 0.18–0.355 | 0.25 | 0.45 | same | same | 200 |
| 4 | Very fine | 0.075–0.18 | 0.12 | 0.40 | same | same | 400 |
| 5 | Submicroscopic (flour) | < 0.075 | 0.03 | 0.35 | same | same | 800 |

**Modifiers (natural-log forms):**

| Param | Value |
|---|---|
| Apply modifiers | ON |
| Q_ref (reduction quotient) | 2.5 |
| γ (size-sensitivity) | 0.1 |
| d_m (reference diameter) | √(1.0·0.5) = 0.7071 mm |
| N_thr | 15 particles |
| u_min | 0.35 |
| u_max | 0.55 |
| N_half | 30 particles |

Uplift:
`U = 1 + u_min + (u_max − u_min)·ln(N_fs/N_thr)/(ln(N_fs/N_thr) + ln(N_half/N_thr))`

Reduction: `Q_i = Q_ref · (d_i/d_m)^γ`, factor applied = `1/Q_i`.

**Horizon grade formula (authoritative):**

```
Pooled count N_h     = Σ pan counts (after limit-cap with α/(α−1) = 1.5)
Sampled volume V_h   = (3 bowls) / 240
N_i                  = description share × N_h, capped at (3 × Ncap_i)
W                    = Σ_i λ · N_i · (m_i/R_i) · modifier_i
Grade (g/m³)         = (W / V_h) / bank_factor
Grade (g/t)          = Grade_g_m3 / rho_bulk
σ_W                  = √(Σ λ²·N_i·(m_i/R_i)²·modifier_i²)
N_eff                = W² / σ_W²
Z                    = 1 − e^(−N_eff/N*)
90% CI               = Grade ± 1.645·σ_W/V_h
```

**Pit composite:** thickness-weighted average over panned ore horizons;
below-detection horizons enter at grade 0.

**Validation:** compare composite grade to historical stockpile feed grade;
suggested λ = current λ × exp(mean(ln(old/model))). Use once ≥ 10 records.

## 2.6 `Predictive Robust 2 Mining_Operations_Data_Capture_Template (1).xlsx`

**Owner:** Operations / continuous improvement
**Sheets:** Data Entry, Legend & Instructions, Data Relevance, Predictive
Analysis, Lists

**Data Entry columns (18):**
A. Block Centroid X (m)
B. Block Centroid Y (m)
C. RL (m)
D. Hauling Distance (km)
E. Equipment Downtime (hrs)
F. Haulage Rate (t/hr or bcm/hr)
G. Rippability Index
H. Stripping Ratio
I. Break Down (Yes/No)
J. Weather Condition (dropdown)
K. Water Influx Rate (m³/hr)
L. Mining Date
M. Daily Mined Volume (bcm or t)
N. Geological Material Type (dropdown)
O. Depth of Horizon (m)
P. Equipment Availability (%) — formula
Q. Cost Proxy ($) — formula
R. Stripping Ratio Trend — formula

**Key assumptions (Data Entry!U5:U7):**
- Scheduled Hours per Day = 24
- Value per Unit ($/t or $/bcm) = 50
- Haulage Cost Rate ($/km per volume unit) = 2.5

**Live formulas:**
- `Availability = (ScheduledHours − Downtime) / ScheduledHours`
- `CostProxy = HaulDistance × Volume × HaulRate + Downtime × (HaulageRate × ValuePerUnit)`
- `Trend = Above Avg / Average / Below Avg` vs running average

**Predictive Analysis (module insights):**
- Model R² = 0.9799, 8 predictors
- Standardized β: Equipment Downtime **1.209** (dominant), Hauling Distance 0.331, Haulage Rate 0.147, Volume 0.143, Stripping 0.061, Rippability −0.06, Water 0.012, Depth 0.006
- Breakdown = Yes: avg 6.4 hrs downtime, $190,951 cost proxy vs No: 1.5 hrs, $84,241
- Wet weather: 3.1 hrs downtime vs 1.5 dry; $116,234 vs $84,600
- Fresh Rock: 20% breakdown rate (highest)
- Fleet availability avg 92.2%, low 62.4%

## 2.7 `Operational_Optimization_Template (1).xlsx`

**Owner:** Operations / plant
**Sheets:** Instructions, Scenario & Live KPIs, KPI Performance Analysis,
Optimizer Recommendations, VAM Transportation Optimization, Sensitivity Grid

**Scenario KPIs (blue cells):**
- Hauling Distance 2.31 km
- Equipment Downtime 1.12 hrs
- Haulage Rate 701 t/hr
- Daily Mined Volume 7890
- Key assumptions match Predictive template

**VAM Zones (4) and Destinations (3):**

| Zone | X | Y | Blocks | Material | Supply |
|---|---|---|---|---|---|
| Zone 1 | 583185.67 | 634469.63 | 8 | Oxide | 62,477 |
| Zone 2 | 583626.14 | 634915.45 | 7 | Saprolite | 51,697 |
| Zone 3 | 583421.50 | 634210.25 | 1 | Oxide | 12,500 |
| Zone 4 | 583204.77 | 634533.77 | 7 | Oxide | 53,597 |

| Destination | X | Y | Demand |
|---|---|---|---|
| Primary Processing Plant | 583405.91 | 634139.73 | 99,149 |
| ROM Stockpile | 583714.24 | 634774.41 | 45,068 |
| Waste Rock Dump | 583097.58 | 634844.93 | 36,054 |

Balanced (supply = demand = 180,271). VAM allocation total cost = **C59**;
naive nearest-destination = **C60 = 154,586**; savings = `C60 − C59`.

## 2.8 `FINAL2GEOS_VAM_alluvial_trommel_Ore_blend_simulation_GEOSPATIAL.xlsx`

**Owner:** Plant metallurgy / process
**Sheets:** README, Pit_Feed_Data, Spatial_Reference, Haul_Cost_Matrix,
VAM_Spatial_Optimizer, Grade_Spatial_Priority, Geospatial_Blend_Plan,
Holistic_Blend_Plan, Daily_Blend_Plan, Blend_Optimizer, Plant_Parameters,
Energy_Consumption, Energy_Reduction_Simulator, Recovery_Dashboard,
7Day_Simulation

**Pit_Feed_Data (5 pits):**

| Pit | Material | Grade g/m³ | ρ_bulk | Volume m³ | X | Y |
|---|---|---|---|---|---|---|
| PIT-01 | Alluvial Gravel – High Terrace | 0.3 | 1.5 | 450 | 229808 | 697313 |
| PIT-02 | Alluvial Gravel – Channel | 0.8 | 1.5 | 300 | 231293 | 698263 |
| PIT-03 | Overburden | 0.3 | 1.5 | 200 | 231273 | 698278 |
| PIT-04 | High Grade Pocket | 0.2 | 1.5 | 1200 | 231281 | 698300 |
| PIT-05 | Alluvial Gravel – Terrace 2 | 0.6 | 1.5 | 300 | 231265 | 698313 |

**Spatial reference:** Plant at (229400, 697300).
Stockpiles: ST-01 (231259, 698260, cap 800), ST-02 (231210, 698151, cap 400),
ST-03 (231170, 698151, cap 600), ST-04 (229854, 697269, cap 800).

**Haul cost rates:**
- Haul Cost Rate: **$50 per m³ per km**
- Haul Energy Factor: **5 kWh per m³ per km**

**Plant parameters:**

| Parameter | Value |
|---|---|
| Rated throughput | 250 t/hr ÷ 1.5 = 166.67 m³/hr |
| Feed rate setpoint | 75 m³/hr |
| Actual processing rate | 43 m³/hr |
| Operating hours | 22 |
| Max daily capacity | 43 × 22 = 946 m³/day |
| RPM actual / optimal | 30 / 32 |
| RPM deviation factor | max(0.8, 1 − abs(Δ)·0.005) |
| Tilt actual / optimal | 8° / 12° |
| Tilt deviation factor | max(0.8, 1 − abs(Δ)·0.02) |
| Water flow actual | 120 m³/hr |
| Water flow optimal | 110–135 m³/hr |
| Water flow factor | 1.0 inside band, else max(0.8, 1 − distance·0.01) |
| Setup efficiency | 0.92 |
| Base metallurgical recovery | 0.90 |
| Overall efficiency | Setup × RPM × Tilt × Water |
| Effective recovery | Base × Overall |

**Equipment loads:**

| Equipment | kW | Qty | Total kW |
|---|---|---|---|
| Trommel Drive | 45 | 1 | 45 |
| Water Supply Pumps | 30 | 2 | 60 |
| Feed Conveyor | 15 | 1 | 15 |
| Discharge/Stacker | 15 | 3 | 45 |
| Sluice/Jig Pump | 11 | 1 | 11 |
| Auxiliary | 8 | 1 | 8 |
| **Total connected load** | | | **184 kW** |

**Energy & economics:**
- Energy cost rate: **`12` in Energy_Consumption!B16 — DATA_ISSUE, should be 0.12**
- Peak tariff rate (Energy_Reduction_Simulator): 0.22 $/kWh
- Off-peak tariff rate: 0.11 $/kWh
- Gold price: **$4,050 / oz**
- Troy ounce: **31.1035 g**

**Blend optimizer target:** 950 m³ (in latest version) — earlier versions used
5000 m³; corrected target is bounded by total available volume.

**Holistic_Blend_Plan concurrency rule:** A pit is `CONCURRENT` (eligible for
blend-building while hauling is in progress) if it sends all its volume to a
single stockpile, or ≥ 66% to a dominant stockpile. Otherwise `SEQUENTIAL —
split, await consolidation`.

**Net margin adjudication (Holistic_Blend_Plan Step 4):**
`NetMargin($/m³) = GoldValue − HaulCost − ReclaimCost`
where `GoldValue = Grade × EffectiveRecovery/31.1035 × GoldPrice`. Net-negative
allocations must be flagged as `INFEASIBLE` in the daily plan.

**Recovery_Dashboard profitability chain:**

```
GoldRecovered_oz       = (ContainedGold_g × EffectiveRecovery) / 31.1035
GrossRevenue           = GoldRecovered_oz × GoldPrice
NetRevenue_afterEnergy = GrossRevenue − DailyEnergyCost
NetRevenue_fullyLoaded = NetRevenue_afterEnergy − ReclaimHaulCost
TrueNetMargin          = NetRevenue_fullyLoaded / GrossRevenue
```

**7-Day simulation:** Rolls Volume, Grade, Hours, Recovery, Gold, Revenue,
Energy, Net Revenue, Cumulative Gold and Cumulative Net Revenue across 7 days.

---

# 3. MCP Architecture

## 3.1 Server topology

Four MCP servers, each with a distinct failure domain and access scope:

| Server | Modules | Tools exposed | Resources |
|---|---|---|---|
| `alluvial-finance` | A1–A6 | Cash, feeding, stage-cost, pipeline, fraud, PSO, greedy | Outreach templates, stage definitions, contacts |
| `alluvial-geospatial` | B4 (pit composite), C1–C6 | Pit/stockpile registry, distance/cost matrices, grade-priority, VAM, naive comparison | Distance matrices, heuristic verifications |
| `alluvial-plant` | D1–D7 | Pit feed, plant efficiency, blend, energy, recovery, 7-day | Plant parameter templates |
| `alluvial-adjudication` | Cross-module | `adjudicate_full_chain` and per-rule verdict tools | Decision tree schemas, threshold registry |

The `alluvial-grade` functions (Module B1–B3) live in the **shared core
package**, exposed by `alluvial-plant` as tools, so plant and geology use the
same grade engine.

## 3.2 Registration

```json
{
  "mcpServers": {
    "alluvial-finance":       { "command": "python", "args": ["-m", "alluvial_mcp.finance_server"] },
    "alluvial-geospatial":    { "command": "python", "args": ["-m", "alluvial_mcp.geospatial_server"] },
    "alluvial-plant":         { "command": "python", "args": ["-m", "alluvial_mcp.plant_server"] },
    "alluvial-adjudication":  { "command": "python", "args": ["-m", "alluvial_mcp.adjudication_server"] }
  }
}
```

All four use `fastmcp>=2.0` with stdio transport for local Claude Desktop, or
HTTP+SSE for networked hosts.

## 3.3 Tool annotation policy

Every tool must declare `readOnlyHint` and `destructiveHint`:

- **Read-only tools** (`get_*`, `compute_*`, `adjudicate_*`) — `readOnlyHint: True`
- **Mutating tools** (`register_*`, `upsert_*`, `record_*`) — `readOnlyHint: False, destructiveHint: False`
- **Destructive tools** (`overwrite_*`, `reset_*`) — `readOnlyHint: False, destructiveHint: True`; used only via the Streamlit UI, never from an autonomous agent step without explicit human confirmation.

---

# 4. Module Specifications

Each module is a set of MCP tools grouped under one workbook. Full tool
signatures use Pydantic v2 models; only names, purpose, and adjudication are
listed here.

## 4.1 Module A — Finance & Stakeholder Pipeline

**Server:** `alluvial-finance`

| Sub-module | Tool | Adjudication / rule |
|---|---|---|
| A1 Cash Book | `record_cash_entry(date, desc, supplier, ref, project_code, cash_received, cash_paid, category_code)` | Category must be one of 21 valid codes |
| A1 Cash Book | `compute_running_balance()` | Balance = prior + received − paid; never negative |
| A1 Cash Book | `validate_project_category(project_code, category_code)` | Pairs must be valid |
| A2 Feeding | `get_feeding_rotation(month)` | Must reconcile to CASH BOOK FE total; else `FEEDING_MISMATCH` |
| A3 Stage Costs | `run_stage_cost_simulation(scenario, fx_rate, budget)` | Scenario ∈ {Low, Base, High}; returns full 12-stage schedule |
| A3 Stage Costs | `compute_runway()` | Weeks until budget exhausted |
| A4 Pipeline | `score_prospect(prospect_id, warmth, attractiveness, legal_clarity)` | 0–100 score |
| A4 Pipeline | `compute_risk_class(prospect_id)` | GREEN / AMBER / RED per Fraud_Check |
| A4 Pipeline | `compute_verification_completion(prospect_id)` | Fraction of V01–V12 passed |
| A4 Pipeline | `adjudicate_prospect_introduction(prospect_id)` | `ALLOW` iff GREEN AND completion ≥ 0.75 AND fails = 0 |
| A5 PSO | `optimize_weekly_hours(weekly_hours, channel_caps, saturation_rates, mins)` | Uses `pyswarms.single.GlobalBestPSO`; returns allocation and uplift vs equal split |
| A6 Greedy | `rank_prospects_by_value_per_hour(hours_budget)` | Value = priority score / effort hours; returns take/skip list |

## 4.2 Module B — Ore Body & Grade Control

**Server:** `alluvial-plant` (shared core)

| Sub-module | Tool | Adjudication / rule |
|---|---|---|
| B1 Panning Log | `parse_pan_entry(raw)` | Returns `{code: E/Q/S/A/L/X, value}` |
| B1 Panning Log | `convert_limit_count(limit, alpha=3)` | Returns `limit × α/(α−1) = limit × 1.5` |
| B2 Horizon | `compute_horizon_grade(pans, description, modifiers_on)` | Full formula per §2.5 |
| B2 Horizon | `compute_credibility_z(grade, sigma, N_star=10)` | Returns `Z` |
| B2 Horizon | `apply_modifiers(N_i, class, N_thresholds)` | Coarse/medium reduced; fine+ uplifted if N_fs > 15 |
| B3 Composite | `build_pit_composite(pit_id)` | Thickness-weighted mean; returns grade, CI, Z, class |
| B3 Composite | `get_adjudicated_pit_grade(pit_id)` | Returns point estimate + `credibility ∈ {LOW, MEDIUM, HIGH}` + `blocking: bool` |
| B4 Validation | `validate_against_feed_grades(records)` | Returns bias, MAE, correlation, suggested λ |
| B5 Ops Data | `validate_block_record(record)` | Enforces dropdowns, non-negative numerics |
| B6 Predictive | `run_correlation_matrix()` | Returns r for 8 predictors vs Cost Proxy |
| B6 Predictive | `run_breakdown_impact()` / `run_weather_impact()` | AVERAGEIFS-style summaries |

## 4.3 Module C — Geospatial VAM & Stockpile Optimization

**Server:** `alluvial-geospatial`

| Sub-module | Tool | Adjudication / rule |
|---|---|---|
| C1 Registry | `register_pit(pit)` / `register_stockpile(stockpile)` | Requires coordinates |
| C1 Registry | `build_distance_matrix(pits, stockpiles)` | Euclidean, m |
| C1 Registry | `build_haul_cost_matrix(distances, rate_per_m3_per_km)` | $/m³ |
| C2 Grade Priority | `compute_grade_priority_factor(grades)` | `(G/Gmax)^α` |
| C2 Grade Priority | `compute_grade_penalty(gpf, lambda)` | `1 + λ(1 − GPF)` |
| C3 Bounded Heuristic | `build_heuristic_matrix(cost, gp, distance, cost_norm, theta, w_d, w_c, beta, gamma)` | Returns bounded `H`; asserts `H ∈ [C·(1−θ), C·GP_max·(1+θ)]` |
| C4 Stockpile Compat | `compute_stockpile_compatibility(pit_grades, target_grades, current_grades, blend_need)` | Returns compatibility matrix |
| C5 VAM | `solve_vam(cost_matrix, supply, demand)` | Returns allocation, total cost, **iteration log**, feasibility check |
| C5 VAM | `verify_vam_optimality(allocation, cost_matrix)` | Optional MODI/Stepping-stone via `ORKit` |
| C6 Baseline | `compute_naive_proportional_baseline(supply, demand, cost_matrix)` | `qty_ij = supply_i × demand_j / total_demand` |
| C6 Baseline | `compute_vam_savings(vam_cost, naive_cost)` | Returns $ and % |

**VAM adjudication:** `adjudicate_vam_solution(allocation, supply, demand)`
verifies row sums, column sums, non-negativity, and `vam_cost ≤ naive_cost`;
returns `VAM_ACCEPTED` or `VAM_REJECTED` with the failing constraint.

## 4.4 Module D — Plant Simulation & Recovery

**Server:** `alluvial-plant`

| Sub-module | Tool | Adjudication / rule |
|---|---|---|
| D1 Pit Feed | `upsert_pit_feed(pit)` | Grade must be > 0 |
| D2 Spatial | `set_plant_coordinates(x, y)` / `register_stockpile(...)` | Single-source-of-truth |
| D3 Plant | `compute_rpm_factor(rpm_actual, rpm_opt)` | `max(0.8, 1 − abs(Δ)·0.005)` |
| D3 Plant | `compute_tilt_factor(...)` / `compute_water_flow_factor(...)` | Penalty curves per §2.8 |
| D3 Plant | `compute_overall_efficiency(setup, rpm_f, tilt_f, water_f)` | Multiplicative |
| D3 Plant | `compute_effective_recovery(base_recovery, overall_efficiency)` | Multiplicative |
| D4 Blend | `build_daily_blend(target_m3)` | Bounded by available volume and plant capacity |
| D4 Blend | `run_grade_priority_blend(target_m3)` | Greedy highest grade first |
| D4 Blend | `run_distance_priority_reclaim(target_m3)` | Nearest stockpile first |
| D4 Blend | `run_composite_priority_blend(target_m3, w_grade, w_distance)` | Grade + distance composite |
| D4 Blend | `run_concurrency_prefilter()` | `CONCURRENT` / `SEQUENTIAL` per pit |
| D4 Blend | `run_holistic_blend(target_m3)` | Concurrency-filtered composite blend |
| D5 Energy | `compute_daily_kwh()` | Connected load × operating hours |
| D5 Energy | `simulate_operating_hours_sensitivity(hours_range)` | Energy vs recovered revenue per hour |
| D5 Energy | `simulate_load_shedding(per_equipment_reduction)` | Additional daily $ saved |
| D5 Energy | `simulate_tariff_shifting(peak, off_peak, hours_peak)` | Blended cost reduction |
| D6 Recovery | `compute_recovered_oz(contained_g, recovery)` | `(g × recovery) / 31.1035` |
| D6 Recovery | `compute_net_revenue(gross, energy, haul)` | Returns both after-energy and fully-loaded |
| D7 7-Day | `roll_week_simulation(daily_volumes, daily_grades, daily_hours)` | Returns cumulative |

## 4.5 Module E — Operational Optimization

**Server:** `alluvial-plant` (same server as D, same core functions)

| Sub-module | Tool |
|---|---|
| E1 Scenario | `run_live_scenario(haul_km, downtime_hrs, haulage_rate, daily_volume)` |
| E2 KPIs | `pivot_by_material()`, `pivot_by_weather()`, `pivot_by_stripping_trend()`, `radar_normalize()` |
| E3 VAM Transport | `solve_vam_from_zones(zones, destinations, rate_per_km)` |
| E4 Sensitivity | `build_cost_sensitivity_grid(haul_range, downtime_range)` |
| E5 Recommendations | `compare_baseline_vs_recommended(material_type)` |

## 4.6 Module F — Outreach & Pipeline (protected server)

Same as Module A4–A6, but deployed on the `alluvial-finance` server with the
strictest tool annotations. **No resource is shared with other servers.**
Prospect names, fraud flags, and verification states are only readable by
`alluvial-finance` and the Streamlit admin page.

---

# 5. Cross-Module Adjudication Layer

**Server:** `alluvial-adjudication`

## 5.1 Composite tools

| Tool | Inputs | Rule | Output |
|---|---|---|---|
| `adjudicate_blend_against_grade_credibility` | Module B pit grade + Z → Module D blend share | A pit may contribute > 30% of blend volume only if `Z ≥ 0.6`; else cap at 20% | `{verdict, adjusted_share, blocking}` |
| `adjudicate_haul_against_stockpile_compatibility` | Module C allocation + stockpile requirements | No allocation to a stockpile whose target-grade deficit > 2× pit grade unless compatibility > 0.8 | `{verdict, reroute_suggestions}` |
| `adjudicate_plant_feed_against_energy_budget` | Module D blend + energy | Daily energy cost ≤ 15% of gross gold revenue | `{verdict, energy_ratio, budget_ratio}` |
| `adjudicate_prospect_against_cash_runway` | Module A PSO allocation + cash book | Allocated outreach must leave ≥ 2 weeks of runway | `{verdict, runway_weeks, sustainable}` |
| `adjudicate_full_chain(blend_target_m3, include_pipeline: bool)` | All modules | Runs the four rules above in order; returns a single verdict tree | `{verdict: PASS \| FAIL, tree: [...], blocking_reasons: [...]}` |

## 5.2 `adjudicate_full_chain` output contract (JSON)

```json
{
  "verdict": "PASS | FAIL | CONDITIONAL",
  "timestamp": "2026-11-13T14:22:00Z",
  "inputs": { "blend_target_m3": 950, "include_pipeline": true },
  "tree": [
    {
      "rule_id": "R-1.1",
      "name": "blend_grade_credibility",
      "passed": true,
      "actual": {"PIT-04_share": 0.284, "PIT-04_Z": 0.72},
      "expected": {"max_share_when_Z_below_0_6": 0.20, "threshold_Z": 0.6},
      "severity": "HARD"
    },
    {
      "rule_id": "R-1.2",
      "name": "stockpile_compatibility",
      "passed": true,
      "actual": {"ST-03_target_deficit": 0.0},
      "expected": {"max_deficit_multiple": 2.0},
      "severity": "SOFT"
    },
    {
      "rule_id": "R-1.3",
      "name": "energy_budget",
      "passed": false,
      "actual": {"energy_ratio": 0.187},
      "expected": {"max_ratio": 0.15},
      "severity": "HARD",
      "blocking_reason": "Energy cost 18.7% of gross gold revenue exceeds 15% budget"
    },
    {
      "rule_id": "R-1.4",
      "name": "cash_runway",
      "passed": true,
      "actual": {"runway_weeks": 3.1},
      "expected": {"min_weeks": 2.0},
      "severity": "HARD"
    }
  ],
  "blocking_reasons": ["Energy cost 18.7% of gross gold revenue exceeds 15% budget"],
  "recommended_actions": [
    "Reduce blend target from 950 to ~760 m³",
    "Or shift 3 hrs of run-time from peak to off-peak tariff"
  ]
}
```

The LLM explains this verdict in natural language; it does not re-interpret the
thresholds.

## 5.3 Adjudication rule registry (canonical)

| Rule ID | Name | Severity | Threshold | Source |
|---|---|---|---|---|
| R-1.1 | blend_grade_credibility | HARD | Z ≥ 0.6 else share ≤ 20% | `Refined Au_Grade_Model!Assumptions!B23` |
| R-1.2 | stockpile_compatibility | SOFT | deficit multiple ≤ 2 unless compat > 0.8 | `Geospatial_VAM!Stockpile Compatibility` |
| R-1.3 | energy_budget | HARD | energy ≤ 15% of gross revenue | Derived from `Recovery_Dashboard` + `Operational_Optimization` |
| R-1.4 | cash_runway | HARD | runway ≥ 2 weeks | `Guyana_Outreach!Stage_Costs!H21` + Assumptions |
| R-2.1 | prospect_clearance | HARD | GREEN & completion ≥ 0.75 & fails = 0 | `Guyana_Outreach!Fraud_Check!G3,F49` |
| R-2.2 | vam_feasibility | HARD | row/col totals match, non-negative, vam ≤ naive | `Cost_Grade_VAM!Verification` |
| R-3.1 | plant_efficiency_floor | SOFT | overall efficiency ≥ 0.8 × base | `FINAL2GEOS!Plant_Parameters` |
| R-3.2 | recovery_bounds | HARD | effective recovery ∈ [0.8×base, base] | `FINAL2GEOS!Plant_Parameters` |
| R-3.3 | blend_volume_feasibility | HARD | blend ≤ plant daily capacity AND ≤ available volume | `FINAL2GEOS!Holistic_Blend_Plan` |
| R-4.1 | feeding_reconciliation | SOFT | FE total deviation ≤ 10% | `COMPREHENSIVE FEEDING!Sheet2` |
| R-5.1 | data_integrity | WARN | INT = To − From; energy rate > 1 treated as DATA_ISSUE | `Refined Au_Grade_Model` + `FINAL2GEOS` |

Every tool that mutates state must call the relevant rules and include the
verdict in its response — no silent failures.

---

# 6. Data Schemas (Pydantic v2 — authoritative)

```python
# alluvial_mcp/schemas/finance.py
from pydantic import BaseModel, Field
from datetime import date
from typing import Literal

PROJECT_CODES = {"GRM","ALV","NAN","KOC","ELIT","ANY","SEWM","EAGL"}
CATEGORY_CODES = {"IT","SSF","T2","OE","PC","BP","CC","RM","TT","ST","FE",
                  "FL","TP","WM","CSA","ACC","IMP","UT","COMM","WGS","NA"}

class CashEntry(BaseModel):
    date: date
    description: str
    supplier_customer: str | None = None
    ref_no: str | None = None
    project_code: str = Field(pattern=r"^[A-Z]+$")
    cash_received: float = Field(ge=0, default=0)
    cash_paid: float = Field(ge=0, default=0)
    category_code: str

    def validate_codes(self):
        assert self.project_code in PROJECT_CODES
        assert self.category_code in CATEGORY_CODES

class Prospect(BaseModel):
    prospect_id: str
    name: str
    warmth: int = Field(ge=1, le=5)
    attractiveness: int = Field(ge=1, le=5)
    legal_clarity: int = Field(ge=1, le=5)
    effort_hours_to_milestone: float = Field(gt=0)

class FraudFlag(BaseModel):
    flag_id: str
    triggered: bool
    hard_stop: bool
```

```python
# alluvial_mcp/schemas/geospatial.py
class PitRegistration(BaseModel):
    pit_id: str
    material: str
    grade_g_m3: float = Field(gt=0)
    bulk_density: float = Field(default=1.5, gt=0)
    available_volume_m3: float = Field(ge=0)
    easting: float
    northing: float

class StockpileRegistration(BaseModel):
    stockpile_id: str
    description: str
    easting: float
    northing: float
    capacity_m3: float = Field(gt=0)
    target_grade_g_m3: float | None = None

class VAMRequest(BaseModel):
    cost_matrix: list[list[float]]
    supply: list[float]
    demand: list[float]

class VAMResponse(BaseModel):
    allocation: list[list[float]]
    total_cost: float
    iterations: list[dict]
    feasible: bool
    row_sums: list[float]
    column_sums: list[float]
    verification: dict
```

```python
# alluvial_mcp/schemas/grade.py
class PanEntry(BaseModel):
    pan_number: Literal[1, 2, 3]
    raw: str
    code: Literal["E", "Q", "S", "A", "L", "X"] | None = None

class HorizonGrade(BaseModel):
    horizon_id: str
    pit_id: str
    from_m: float
    to_m: float
    material: str
    min_zone: Literal["ORE", "OVERBURDEN", "WASTE"]
    description: str
    pans: list[PanEntry]

class CompositeGrade(BaseModel):
    pit_id: str
    grade_g_m3: float
    grade_g_t: float
    lower_90: float
    upper_90: float
    z_credibility: float
    class_vs_cutoff: Literal["ABOVE CUT-OFF", "BELOW CUT-OFF", "BELOW DETECTION", "NOT PANNED"]
    blocking: bool
```

```python
# alluvial_mcp/schemas/plant.py
class PlantParameters(BaseModel):
    rated_capacity_m3_hr: float = Field(default=166.67)
    feed_rate_setpoint_m3_hr: float = Field(default=75)
    actual_processing_rate_m3_hr: float = Field(default=43)
    operating_hours: float = Field(default=22)
    rpm_actual: float = Field(default=30)
    rpm_optimal: float = Field(default=32)
    tilt_actual_deg: float = Field(default=8)
    tilt_optimal_deg: float = Field(default=12)
    water_flow_actual: float = Field(default=120)
    water_flow_min: float = Field(default=110)
    water_flow_max: float = Field(default=135)
    setup_efficiency: float = Field(default=0.92)
    base_metallurgical_recovery: float = Field(default=0.90)

class BlendRequest(BaseModel):
    target_volume_m3: float = Field(gt=0)
    strategy: Literal["grade", "distance", "composite", "holistic"]

class BlendResult(BaseModel):
    total_volume_m3: float
    weighted_avg_grade_g_m3: float
    contained_gold_g: float
    effective_recovery: float
    recovered_oz: float
    gross_revenue_usd: float
    energy_cost_usd: float
    haul_cost_usd: float
    net_revenue_after_energy: float
    net_revenue_fully_loaded: float
    feasible: bool
    blocking_reasons: list[str]
```

```python
# alluvial_mcp/schemas/adjudication.py
from enum import Enum

class Severity(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"
    WARN = "WARN"

class RuleResult(BaseModel):
    rule_id: str
    name: str
    passed: bool
    actual: dict
    expected: dict
    severity: Severity
    blocking_reason: str | None = None

class FullChainVerdict(BaseModel):
    verdict: Literal["PASS", "FAIL", "CONDITIONAL"]
    timestamp: str
    inputs: dict
    tree: list[RuleResult]
    blocking_reasons: list[str]
    recommended_actions: list[str]
```

---

# 7. Golden Test Fixtures

Every module must reproduce the workbook verification values exactly. These are
the pytest fixtures — no module ships without passing them.

## 7.1 VAM heuristic (bounded)

```python
# tests/test_geospatial.py
BOUNDED_VERIFICATION = {
    "PIT-01": [64.2191, 118.0470, 105.3408, 65.3744],
    "PIT-02": [70.3753, 43.1348, 65.0261, 131.3235],
    "PIT-03": [41.5572, 51.2635, 63.4873, 118.6393],
    "PIT-04": [91.5333, 62.8972, 29.5625, 128.5312],
    "PIT-05": [42.5154, 217.4278, 108.4145, 95.9932],
}
# tolerance: rel=1e-4
```

## 7.2 Pit composite grade

Must match `Refined Au_Grade_Model!PitComposite` output for PRN093 and PRN094
using the sample panning log. No canonical numeric fixture is exposed here
because the input log defines it; the tool must produce the same grade as the
workbook when given the workbook's log.

## 7.3 Plant efficiency (FINAL2GEOS)

Inputs per §2.8. Expected:
- RPM factor: `max(0.8, 1 − |30−32|·0.005) = 0.99`
- Tilt factor: `max(0.8, 1 − |8−12|·0.02) = 0.92`
- Water flow factor: 1.0 (120 inside 110–135)
- Overall efficiency: `0.92 × 0.99 × 0.92 × 1.0 = 0.8381`
- Effective recovery: `0.90 × 0.8381 = 0.7543`

## 7.4 Cash running balance

`H_n = H_{n−1} + F_n − G_n`, opening balance `52583.07149999976`. Any deviation
must be reported as `DATA_ISSUE`.

## 7.5 Prospect adjudication

P01 sample: risk class GREEN (all flags 0), verification completion ≥ 0.75
after V01–V10 pass, fail count 0 → `ALLOW`.
P02 sample: F03 triggered (1), F15 triggered (1) — F15 is a hard stop → RED →
`DENY` with reason `HARD_STOP_F15`.

---

# 8. Implementation Instructions

## 8.1 Repository layout

```
amop/
├── pyproject.toml
├── alluvial_mcp/
│   ├── __init__.py
│   ├── core/
│   │   ├── grade.py
│   │   ├── vam.py
│   │   ├── plant.py
│   │   ├── finance.py
│   │   └── adjudication.py
│   ├── schemas/
│   ├── finance_server.py
│   ├── geospatial_server.py
│   ├── plant_server.py
│   └── adjudication_server.py
├── streamlit_app/
│   ├── streamlit_app.py
│   └── pages/
│       ├── 1_Dashboard.py
│       ├── 2_Finance_Pipeline.py
│       ├── 3_Grade_Control.py
│       ├── 4_Geospatial_VAM.py
│       ├── 5_Plant_Simulation.py
│       ├── 6_Operational_Optimizer.py
│       └── 7_Adjudication.py
├── tests/
│   ├── test_grade.py
│   ├── test_vam.py
│   ├── test_plant.py
│   ├── test_finance.py
│   └── test_adjudication.py
├── data/
│   ├── workbooks/
│   ├── fixtures/
│   └── exports/
└── README.md
```

## 8.2 Order of implementation (mandatory)

1. **Freeze schemas** (§6) — commit before any implementation.
2. **Implement `core/grade.py`** — verify against `Refined Au_Grade_Model`.
3. **Implement `core/vam.py`** — verify against §7.1.
4. **Implement `core/plant.py`** — verify against §7.3.
5. **Implement `core/finance.py`** — verify against §7.4.
6. **Implement `core/adjudication.py`** — implement each rule in §5.3.
7. **Wrap as MCP servers** — one tool per core function; annotations required.
8. **Build Streamlit pages** — each page calls `core/` directly (not via MCP).
9. **Wire adjudication into every page** — no page shows a recommendation
   without an adjacent `adjudicate_full_chain` result.
10. **Run golden tests** — CI blocks merge if any fail.

## 8.3 Python package manifest

```toml
[tool.poetry.dependencies]
python = "^3.11"
fastmcp = "^2.0"
anthropic = "^0.40"
claude-agent-sdk = "^0.2"
pydantic = "^2.7"
pandas = "^2.2"
numpy = "^1.26"
duckdb = "^1.0"
sqlalchemy = "^2.0"
geoalchemy2 = "^0.15"
geopandas = "^1.0"
shapely = "^2.0"
pyproj = "^3.6"
pyswarms = "^1.3"
turboswarm = "^0.1"
ortools = "^9.10"
OTTools = "^0.3"
ORKit = "^0.4"
deap = "^1.4"
scipy = "^1.13"
scikit-learn = "^1.5"
statsmodels = "^0.14"
streamlit = "^1.53"
streamlit-mcp = "^0.3"
plotly = "^5.22"
python-dotenv = "^1.0"
loguru = "^0.7"
```

## 8.4 Non-negotiable engineering rules

1. **No arithmetic in the LLM.** Every number comes from a `core/` function.
2. **No silent data correction.** Known workbook defects (energy rate, INT
   mismatch, PIT-05 grade difference between workbook versions) must be
   surfaced as `DATA_ISSUE`, not fixed in code.
3. **No mutation without adjudication.** Every write tool returns the
   post-write verdict, not just the new state.
4. **Determinism.** All randomness (PSO, GA) is seeded and the seed is
   returned in the response.
5. **Idempotency.** Re-running a tool with identical inputs must return
   identical outputs. Cache the last response per input hash in Redis.
6. **Audit trail.** Every tool call writes a JSONL line to
   `data/exports/audit-YYYY-MM-DD.jsonl` with `{ts, tool, input_hash,
   verdict, duration_ms}`.

---

# 9. Streamlit UI Specification

## 9.1 Page map

| Page | Purpose | Calls |
|---|---|---|
| 1_Dashboard | Cash, pipeline status, blend status, energy vs revenue KPI cards | Aggregated reads |
| 2_Finance_Pipeline | Cash book, feeding rotation, stage-cost sim, prospect pipeline, fraud check, PSO allocation | `alluvial-finance` tools |
| 3_Grade_Control | Panning log upload, per-horizon grade, pit composite, credibility Z, validation vs feed grades | `alluvial-plant` grade tools |
| 4_Geospatial_VAM | Pit/stockpile registry, distance/cost matrices, heuristic matrix, VAM iteration trace, VAM vs naive | `alluvial-geospatial` tools |
| 5_Plant_Simulation | Plant parameters, blend plan (4 strategies), efficiency, energy, recovery, 7-day | `alluvial-plant` tools |
| 6_Operational_Optimizer | Scenario KPIs, KPIs by material/weather/stripping, sensitivity grid, optimizer recommendations | `alluvial-plant` Module E tools |
| 7_Adjudication | Full-chain verdict tree, drill-down per rule, historical verdicts | `alluvial-adjudication` |

## 9.2 Shared components

- **Verdict badge** (`st.success`, `st.warning`, `st.error`) shows `PASS`,
  `CONDITIONAL`, `FAIL` — colors match the adjudication JSON.
- **DATA_ISSUE banner** at top of each page lists any workbook defects for
  that page's domain.
- **"Explain this"** button on every numeric result opens a `st.expander`
  showing the tool call, its input hash, and its formula citation.
- **Session state contract:** every page writes its current adjudication
  verdict to `st.session_state["adjudication_verdict"]`; the Dashboard reads
  it and shows the worst verdict across pages.

## 9.3 Antigravity workflow

1. In Antigravity, prompt: *"Read `alluvial_platform_handoff.md`, then install
   the dependencies in §8.3."*
2. Prompt: *"Scaffold the `core/` package from §8.1 and implement `grade.py`
   with the formulas in §2.5. Run the golden tests in §7."*
3. Prompt: *"Wrap `core/grade.py` as an MCP server using the schemas in §6.
   Add tool annotations."*
4. Prompt: *"Build the Streamlit page `3_Grade_Control.py`. It calls `core/`
   directly, not via MCP."*
5. Repeat for each module.

Antigravity runs the Streamlit process and opens the browser. It can also be
connected to the running MCP servers, so during development you can ask it to
invoke tools live.

## 9.4 `streamlit-mcp` for human-in-the-loop

For adjudication pages, enable `streamlit-mcp`:

```bash
streamlit-mcp serve streamlit_app/streamlit_app.py --transport http --port 8000
```

This exposes `list_widgets`, `set_widget`, `click`, `read_output`, `get_state`
over MCP. When the agent proposes a blend, the human can adjust sliders in the
browser; the agent calls `get_state` to read the updated values and re-runs
`adjudicate_full_chain` before presenting the next recommendation.

---

# 10. Data Issues Registry (must be surfaced, not fixed)

| ID | Workbook | Sheet | Cell | Issue | Correct value |
|---|---|---|---|---|---|
| DATA-01 | Refined Au_Grade_Model | QUALITATIVE PANNING LOG | INT column rows 5–7 | INT ≠ To − From | Use `To − From` |
| DATA-02 | Refined Au_Grade_Model | QUALITATIVE PANNING LOG | PRN093 2.6–2.8 m | Not panned | Exclude; flag `NOT PANNED` |
| DATA-03 | FINAL2GEOS | Energy_Consumption | B16 | Energy cost rate = `12` | Should be `0.12` |
| DATA-04 | FINAL2GEOS | Energy_Reduction_Simulator | B48–B50 | Peak 0.22, off-peak 0.11 vs single-rate 12 | Use 0.12 |
| DATA-05 | FINAL2GEOS | Daily_Blend_Plan | F7:F11 | #REF! | Route through Holistic_Blend_Plan + GA |
| DATA-06 | Cost_Grade_VAM | Pit Data | PIT-05 grade | 0.9 vs 0.6 | Use 0.9 (bounded) |
| DATA-07 | Guyana_Outreach | Fraud_Check | V07–V12 | Pending by default | Do not auto-clear |
| DATA-08 | Geospatial_VAM (original) | Final Heuristic Matrix | Verification | Values up to 700 | Superseded by bounded |
| DATA-09 | Operational_Optimization | Optimizer Recommendations | Haulage Rate | Fixed fleet spec, not a lever | Flag as `FIXED` |
| DATA-10 | COMPREHENSIVE FEEDING | CASH BOOK | Row 51, Row 52 | H52 references row 54 | Use `H_n = H_{n−1} + F_n − G_n` |

When the LLM encounters any of these, it must produce:

```json
{"finding": "DATA_ISSUE", "id": "DATA-03", "workbook": "FINAL2GEOS_...",
 "sheet": "Energy_Consumption", "cell": "B16", "value_found": 12,
 "recommended_value": 0.12, "action_taken": "none (surfaced to user)"}
```

---

# 11. Reference Appendix — Formula Quick-Reference

## 11.1 Grade engine (Module B)

```
N_count(pan)   = E → exact | Q → raw/f | S → S-scale | A → 0 | L → L×1.5 | X → excluded
N_horizon      = Σ N_count over 3 pans
V_horizon      = 3/240 = 0.0125 m³
share_i        = present_i · w_i / Σ present_j · w_j,  w_i = e^(−d_i/δ)
N_i            = min(share_i · N_horizon, 3 · Ncap_i)
W              = Σ_i λ · N_i · (m_i/R_i) · mod_i
grade_g_m3     = W / V_horizon / bank_factor
grade_g_t      = grade_g_m3 / ρ_bulk
σ_W            = √(Σ λ²·N_i·(m_i/R_i)²·mod_i²)
N_eff          = W² / σ_W²
Z              = 1 − e^(−N_eff/10)
CI_90          = grade ± 1.645·(σ_W/V_horizon)
```

## 11.2 VAM heuristic (Module C, bounded)

```
GPF_i = (G_i / Gmax)^α
GP_i  = 1 + λ(1 − GPF_i)
DNF   = (D − Dmin)/(Dmax − Dmin)
CNF   = (C − Cmin)/(Cmax − Cmin)
SM    = (1 − θ) + 2·θ·(w_D·DNF^β + w_C·CNF^γ)
H_ij  = C_ij · GP_i · SM_ij
```

## 11.3 VAM algorithm (audit trail required)

```
For each active row: penalty = 2nd_min − min
For each active col: penalty = 2nd_min − min
Pick max penalty; allocate min(supply, demand) to its min-cost cell
Eliminate the satisfied row or column; repeat
Return: allocation, total_cost, iteration_log, feasibility_check
```

## 11.4 Plant efficiency (Module D)

```
RPM_factor     = max(0.8, 1 − |RPM_actual − RPM_opt| × 0.005)
Tilt_factor    = max(0.8, 1 − |Tilt_actual − Tilt_opt| × 0.02)
Water_factor   = 1.0 if within band else max(0.8, 1 − |Δ| × 0.01)
Overall_eff    = Setup_eff × RPM_factor × Tilt_factor × Water_factor
Effective_rec  = Base_rec × Overall_eff
```

## 11.5 Economic chain (Module D)

```
GoldRecovered_oz       = (ContainedGold_g × EffectiveRec) / 31.1035
GrossRevenue           = GoldRecovered_oz × GoldPrice
EnergyCost             = ConnectedLoad_kW × OperatingHours × EnergyRate
NetRevenue_afterEnergy = GrossRevenue − EnergyCost
HaulCost               = VolumeReclaimed_m3 × Distance_m/1000 × HaulRate_$_m3_km
NetRevenue_fullyLoaded = NetRevenue_afterEnergy − HaulCost
TrueNetMargin          = NetRevenue_fullyLoaded / GrossRevenue
```

## 11.6 Prospect adjudication (Module A)

```
risk_score   = Σ(weight_i · flag_i) / Σ(weight_i) × 100
hard_stops   = Σ(flag_i · [flag is H])
risk_class   = RED    if hard_stops > 0 OR risk_score ≥ 35
             = AMBER  if risk_score ≥ 15
             = GREEN  otherwise
completion   = passed_verifications / 12
cleared      = (risk_class == GREEN) AND (completion ≥ 0.75) AND (fails == 0)
```

## 11.7 PSO effort allocation (Module A)

```
Channel c: leads_c(hours_c) = cap_c × (1 − e^(−k_c · hours_c))
Fitness: Σ leads_c − 3 × Σ max(0, min_hrs_c − hours_c)
Constraint: Σ hours_c = weekly_hours (default 40)
```

---

# 12. Change-Control Contract

Any change to:

- A threshold in §5.3,
- A formula in §11,
- A data-issue in §10,
- A schema in §6,

must include:

1. A diff of this file,
2. An updated golden test fixture (§7),
3. An entry in `CHANGELOG.md` explaining the rationale and the
   workbook-of-record citation,
4. An explicit `breaking_change: true|false` flag.

The LLM must refuse to apply a change that violates this contract and prompt
the user for the missing artifact.

---

# 13. First-Response Checklist (for Claude)

When a user opens a new session with this file, respond by:

1. Summarizing the **eight workbooks** and their owners in ≤ 8 lines.
2. Confirming the **four MCP servers** and their tool families.
3. Listing the **six non-negotiable engineering rules** (§8.4).
4. Asking which of the following the user wants first:
   - (a) freeze schemas and scaffold `core/`
   - (b) implement `core/grade.py` with golden tests
   - (c) build one Streamlit page end-to-end
   - (d) wire `adjudicate_full_chain` into an existing page
5. Never start implementing before the user picks a starting point.

---

*End of handoff document.*