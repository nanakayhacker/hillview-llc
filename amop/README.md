# AMOP -- Alluvial Mining Operations Platform

A planning and decision-support platform for a medium-scale alluvial gold
project: grade control, geospatial VAM blend optimization, plant simulation,
finance/outreach pipeline, exploration-through-HSE cost tracking, and a
JORC-style prototype feasibility report -- all built on deterministic
`core/` engines, each verified bit-for-bit against the real source
workbooks (see "What's verified" below), plus a dashboard and one-click
Windows installer.

## Quick start (Windows)

Double-click **`build_windows.bat`**. It will:

1. Find Python 3.10+ (installs nothing itself -- if Python is missing it
   tells you exactly where to get it and what to tick during setup).
2. Create a virtual environment (`.venv`) and install every dependency.
3. Run the full golden-test suite (23 tests) to confirm the install works.
4. Generate the Tableau/Power BI data exports.
5. Launch the app and open it in your browser.

Close the window (or Ctrl+C) to stop the platform. Run the batch file again
any time -- it reuses the existing `.venv` and is fast after the first run.

A copy also lives at the repository root (`../build_windows.bat`) and simply
forwards into this folder.

## Quick start (macOS/Linux/dev)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
pytest tests/ -q
streamlit run streamlit_app/streamlit_app.py
```

## What this is, and what it is not

This is a **planning and decision-support tool**. It does **not** produce a
compliant Mineral Resource or Reserve statement, a JORC Code (2012) or NI
43-101 declaration, or a legal opinion. The resource/reserve classification
in the Feasibility Report page is an explicit **prototype** pending sign-off
by a Competent/Qualified Person. Every placeholder financial input must be
replaced with a quoted figure before any investment decision is made on
this platform's output.

No arithmetic happens in a prompt. Every number on every page and every MCP
tool response comes from a deterministic Python function in `alluvial_mcp/
core/`, most of them verified bit-for-bit against the source workbooks.

## Repository layout

```
amop/
├── build_windows.bat          <- double-click this
├── requirements.txt
├── mcp.json                   <- MCP server registration (5 servers)
├── alluvial_mcp/
│   ├── core/                  <- deterministic engines (grade, vam, plant,
│   │                             finance, adjudication, cost_tracking,
│   │                             feasibility, workbook_loader)
│   ├── finance_server.py       <- MCP: cash book, stage costs, fraud check, PSO
│   ├── geospatial_server.py    <- MCP: distance/cost/heuristic matrices, VAM
│   ├── plant_server.py         <- MCP: grade engine + plant sim + recovery
│   ├── adjudication_server.py  <- MCP: cross-module verdict rules
│   └── feasibility_server.py   <- MCP: cost tracking + feasibility/JORC prototype
├── streamlit_app/              <- the UI (10 pages, loads core/ directly)
├── scripts/generate_bi_exports.py  <- CSV + Tableau .twb + Power BI .pbids
├── tests/                      <- golden regression tests (pytest)
├── data/workbooks/             <- the 14 source Excel/macro workbooks
└── docs/AMOP_MCP_SPEC.md       <- the original handoff specification
```

## What's verified against real workbook data (not just the spec's summary)

| Engine | Workbook(s) | Verified exactly |
|---|---|---|
| `core/grade.py` | `Refined_Au_Grade_Model.xlsx` | PRN093 and PRN094 pit composite grade, 90% CI, Z-credibility, sum N_eff -- bit-for-bit |
| `core/vam.py` (heuristic) | `Cost_Grade_Heuristic_Prioritized_VAM_Cost_MATRIX.xlsx!Heuristic Calculation` | All 20 cells of the bounded H(i,j) matrix |
| `core/vam.py` (solver) | `VAM_OPTIMISER_MACRO.xlsm` (independent solver, same cost matrix) | Allocation matrix and total cost ($151,977.6258222659) exactly |
| `core/plant.py` | `FINALGEOS_VAM_..._GEOSPATIAL.xlsx!Plant_Parameters/Recovery_Dashboard` | Overall efficiency, effective recovery, recovered oz, net revenue |
| `core/finance.py` | `COMPREHENSIVE_FEEDING.xlsx!CASH BOOK`, `Guyana_Outreach_Cost_Pipeline_Workbook.xlsx` | Running balance, Fraud_Check risk scores (P02, P03), 12-stage cost totals |
| `core/cost_tracking.py` | `Alluvial_Campaign_Control_Workbook_Guyana.xlsx!Vouchers` | Sample voucher validation outcomes |
| `core/feasibility.py` | `Alluvial_Campaign_Control_Workbook_Guyana.xlsx!Feasibility` | The entire 6-year DCF: material processed, EBITDA, break-even grades, every cash-flow line, NPV, IRR, payback |

Run `pytest tests/ -v` to see all 23 checks pass.

## Engineering corrections to the handoff spec (`docs/AMOP_MCP_SPEC.md`)

Found while implementing, surfaced here rather than silently worked around:

- **Non-installable dependencies.** The spec's Python manifest (§8.3) lists
  `turboswarm`, `ORKit` and `OTTools` -- none are published PyPI packages.
  `requirements.txt` uses working substitutes instead: `scipy.optimize.
  linprog` for VAM optimality verification (replacing "ORKit" MODI/
  stepping-stone), and drops the unused heavy GIS/DB stack (`geopandas`,
  `shapely`, `pyproj`, `geoalchemy2`, `duckdb`, `sqlalchemy`, `ortools`,
  `redis`) since pit/stockpile coordinates here are plain survey eastings/
  northings, not a GIS problem. `pyswarms` and `deap` are kept -- both are
  real, pip-installable, no-compiler packages.
- **DATA-11 (new).** `Cost_Grade_Heuristic_Prioritized_VAM_Cost_MATRIX.xlsx!
  Verification` does not match that same workbook's own `!Heuristic
  Calculation` sheet, nor the independent `VAM_OPTIMISER_MACRO.xlsm` (which
  cross-validates `Heuristic Calculation` exactly). `Verification` is a
  stale leftover from an earlier parameter set; `core/vam.py` matches
  `Heuristic Calculation`, confirmed by the independent macro workbook --
  not the workbook's own `Verification` tab.
- **DATA-01/02/03/04/06** from the original spec (§10) all reproduce
  exactly in the real workbooks and are surfaced as flagged findings in the
  relevant tool output, never silently corrected (e.g. `compute_daily_
  energy_cost` always returns both the as-entered and the 0.12 $/kWh
  corrected figure).
- **Grade-engine formulas not fully specified in the handoff doc** were
  reverse-engineered from the real cell values in
  `Refined_Au_Grade_Model.xlsx` and verified by hand before being
  implemented: the decay-weighted class-share model for free-text
  descriptions (including a literal transposed-letter typo,
  "submicroscpoic", that appears in the real panning log and is handled via
  a tolerant keyword match), the "A - B" dash-range grammar (distinct from
  "intermix of A and B"), the natural-log uplift/reduction modifiers, and
  the empirical limit-cap multiplier for `L`-coded pan entries
  (`1.49877596105616`, not the spec's `1.5` approximation).

## Cost-code taxonomy (exploration -> ... -> HSE/admin)

`core/cost_tracking.py` defines the full systematic, sequential cost
structure for a medium-scale alluvial campaign:

- **EXPLORATION (1xxx):** mobilisation, coordination, lodging, field
  logistics, personnel, jurisdictional permitting, employee contracts/
  payroll, prospecting equipment, mineral title acquisition & licensing.
- **MINING_OPERATIONS (2xxx):** haulage, excavation, access/earthworks,
  stockpiling, fuelling, operational overheads.
- **PLANT_PROCESSING (3xxx):** sourcing/procurement, retaining wall,
  trommel fabrication & welding, water pumps, piping, rotor motors, fans,
  screens, hoppers, conveyors, sluice boards, dump box, reservoir tank.
- **CAMP_DEVELOPMENT (4xxx):** prefab housing, offices, power plant, wiring
  & electrification, Starlink/router, sized for ~140 employees (placeholder
  sizing -- replace with a quoted BOQ before use).
- **HSE_ADMIN (5xxx):** health & safety, kitchen, HR, accounting.
- **CONTINGENCY (9xxx).**

Voucher validation, budget BAC/EV/AC/variance/CPI rollups, Trommel BOM
costing and T0-T3 tranche-release gating are all modeled on
`Alluvial_Campaign_Control_Workbook_Guyana.xlsx` and verified against its
real sample vouchers.

## Dashboard / BI exports

Tableau Desktop and Power BI Desktop are licensed GUI applications -- no
script can install or activate them. `scripts/generate_bi_exports.py`
(wired into `build_windows.bat` and the "BI Exports" page) instead:

- Writes CSV extracts (pit grades, vouchers, budget, feasibility cash flow)
  to `data/exports/bi/`.
- Writes `AMOP_Dashboard.twb` (opens directly in Tableau Desktop if
  installed).
- Writes `AMOP_Dashboard.pbids` (opens directly in Power BI Desktop if
  installed, which then imports the CSVs).
- The Streamlit "BI Exports" page always shows a built-in Plotly dashboard
  that needs **no license at all**, regardless of whether Tableau or Power
  BI are installed.

## Non-negotiable engineering rules (carried over from the spec, §8.4)

1. No arithmetic in the LLM or UI -- every number comes from `core/`.
2. No silent data correction -- known workbook defects are surfaced as
   `DATA_ISSUE` findings, never quietly fixed.
3. No mutation without adjudication -- every write path returns the
   post-write verdict, not just the new state.
4. Determinism -- all randomness (PSO) is seeded and the seed is returned.
5. Idempotency -- re-running a tool with identical inputs returns identical
   output.
6. Scope boundary -- this is planning/decision support, not a resource or
   reserve statement, JORC/NI 43-101 declaration, or legal opinion.
