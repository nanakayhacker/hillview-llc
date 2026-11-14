# Changelog

## 1.0.0 -- Initial build

Implemented from `docs/AMOP_MCP_SPEC.md` (the handoff specification) plus
14 real source workbooks, extended with two new modules not in the
original spec:

### Added
- `core/grade.py`, `core/vam.py`, `core/plant.py`, `core/finance.py`,
  `core/adjudication.py` -- the platform's five deterministic engines, each
  verified bit-for-bit against real workbook data (see README "What's
  verified").
- `core/cost_tracking.py` (**new**) -- exploration-through-HSE/admin
  cost-code taxonomy, budget BAC/EV/AC/variance rollups, voucher
  validation workflow, Trommel BOM costing, camp sizing for ~140 employees,
  T0-T3 tranche-release gating.
- `core/feasibility.py` (**new**) -- JORC-style prototype resource/reserve
  classification (explicitly non-compliant, pending Competent Person
  sign-off) and a full DCF/NPV/IRR/break-even economics engine.
- `core/workbook_loader.py` -- loads all of the above from the real
  `data/workbooks/*.xlsx`/`.xlsm` files rather than synthetic fixtures.
- 5 MCP servers (`alluvial-finance`, `alluvial-geospatial`, `alluvial-plant`,
  `alluvial-adjudication`, `alluvial-feasibility`) wrapping 55 tools total,
  registered in `mcp.json`.
- 10-page Streamlit application (Dashboard, Finance & Pipeline, Grade
  Control, Geospatial VAM, Plant Simulation, Operational Optimizer, Cost
  Tracking, Feasibility Report, Adjudication, BI Exports).
- `scripts/generate_bi_exports.py` -- CSV extracts, Tableau `.twb`, Power BI
  `.pbids`.
- `build_windows.bat` -- one-click install, golden-test verification, BI
  export generation and launch.
- 23 golden regression tests (`tests/`), all passing against real
  workbook-derived fixtures.

### Data issues surfaced (not silently fixed)
DATA-01, DATA-02, DATA-03, DATA-04, DATA-06 (from the original spec, all
confirmed present in the real workbooks) and **DATA-11** (new finding: the
`Cost_Grade_Heuristic_Prioritized_VAM_Cost_MATRIX.xlsx!Verification` sheet
is stale and does not match that workbook's own `Heuristic Calculation`
sheet or the independent `VAM_OPTIMISER_MACRO.xlsm` solver, both of which
agree with each other exactly).

### Engineering deviations from the handoff spec
Dependency manifest corrected (`turboswarm`, `ORKit`, `OTTools` are not
installable packages; substituted `scipy.optimize.linprog` and dropped the
unused GIS/DB stack). See README for the full list and rationale.

`breaking_change: false` -- this is the first build; there is no prior
version to break.
