"""
Generates the BI-ready data layer for Tableau and Power BI, plus a built-in
Plotly dashboard needing no license. Run directly (`python scripts/
generate_bi_exports.py`) or imported and called from the Streamlit BI_Exports
page. Writes CSV extracts + a Tableau .twb (textscan connections, no license
needed to generate) + a Power BI .pbids pointer into data/exports/bi/.

Tableau Desktop and Power BI Desktop are licensed GUI applications that
cannot be installed or activated by a script -- this only prepares the data
and a ready-to-open workbook/pointer for whichever the user already has.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPORTS_DIR = REPO_ROOT / "data" / "exports" / "bi"


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _pit_grades_rows() -> list[dict]:
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from alluvial_mcp.core.grade import build_pit_composite
    from alluvial_mcp.io.workbooks import load_panning_log

    log = load_panning_log()
    rows = []
    for pit_id, horizons in log.items():
        c = build_pit_composite(pit_id, horizons)
        rows.append({
            "pit_id": pit_id, "grade_g_m3": c.grade_g_m3, "grade_g_t": c.grade_g_t,
            "z_credibility": c.z_credibility, "class_vs_cutoff": c.class_vs_cutoff,
            "panned_ore_thickness_m": c.panned_ore_thickness_m,
            "total_ore_thickness_m": c.total_ore_thickness_m, "ci_lower_90": c.ci_lower_90,
            "ci_upper_90": c.ci_upper_90,
        })
    return rows


def _vouchers_rows() -> list[dict]:
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from alluvial_mcp.core.cost_tracking import summarize_vouchers
    from alluvial_mcp.io.workbooks import load_campaign_vouchers

    vouchers = load_campaign_vouchers()
    if not vouchers:
        return []
    summary = summarize_vouchers(vouchers)
    return [
        {"voucher_id": v.voucher_id, "cost_code": v.cost_code, "payee": v.payee, "amount_usd": v.amount_usd,
         "status": r["status"], "hold_reasons": "; ".join(r["hold_reasons"])}
        for v, r in zip(vouchers, summary["results"])
    ]


def _budget_rows() -> list[dict]:
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from alluvial_mcp.core.cost_tracking import evaluate_budget_line
    from alluvial_mcp.io.workbooks import load_campaign_budget

    lines = load_campaign_budget()
    return [
        {"cost_code": r.cost_code, "category": r.category, "phase": r.phase,
         "planned_bac_usd": r.planned_bac_usd, "actual_validated_usd": r.actual_validated_usd,
         "variance_usd": r.variance_usd, "pct_consumed": r.pct_consumed}
        for r in (evaluate_budget_line(l) for l in lines)
    ]


def _feasibility_cashflow_rows() -> list[dict]:
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from alluvial_mcp.core.feasibility import FeasibilityAssumptions, run_feasibility_model

    result = run_feasibility_model(FeasibilityAssumptions())
    return [
        {"year": cf.year, "ebitda_usd": cf.ebitda_usd, "depreciation_usd": cf.depreciation_usd,
         "tax_usd": cf.tax_usd, "capex_usd": cf.capex_usd, "free_cash_flow_usd": cf.free_cash_flow_usd,
         "cumulative_usd": cf.cumulative_usd}
        for cf in result.cash_flows
    ]


TWB_TEMPLATE = """<?xml version='1.0' encoding='utf-8' ?>
<workbook source-build='1.0' source-platform='amop' version='18.1'>
  <datasources>
{datasources}
  </datasources>
  <worksheets>
{worksheets}
  </worksheets>
</workbook>
"""

DATASOURCE_TEMPLATE = """    <datasource caption='{caption}' name='{name}'>
      <connection class='textscan' directory='{directory}' filename='{filename}' />
    </datasource>
"""

WORKSHEET_TEMPLATE = """    <worksheet name='{name}'>
      <table>
        <view>
          <datasources>
            <datasource name='{ds_name}' />
          </datasources>
        </view>
      </table>
    </worksheet>
"""


def _build_twb(csv_files: dict[str, Path]) -> str:
    datasources, worksheets = [], []
    for ds_name, path in csv_files.items():
        datasources.append(DATASOURCE_TEMPLATE.format(
            caption=ds_name, name=ds_name, directory=str(path.parent), filename=path.name,
        ))
        worksheets.append(WORKSHEET_TEMPLATE.format(name=f"{ds_name} overview", ds_name=ds_name))
    return TWB_TEMPLATE.format(datasources="".join(datasources), worksheets="".join(worksheets))


def generate_all() -> dict:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_files = {
        "pit_grades": EXPORTS_DIR / "pit_grades.csv",
        "vouchers": EXPORTS_DIR / "vouchers.csv",
        "budget": EXPORTS_DIR / "budget.csv",
        "feasibility_cashflow": EXPORTS_DIR / "feasibility_cashflow.csv",
    }
    _write_csv(csv_files["pit_grades"], _pit_grades_rows())
    _write_csv(csv_files["vouchers"], _vouchers_rows())
    _write_csv(csv_files["budget"], _budget_rows())
    _write_csv(csv_files["feasibility_cashflow"], _feasibility_cashflow_rows())

    twb_path = EXPORTS_DIR / "AMOP_Dashboard.twb"
    twb_path.write_text(_build_twb(csv_files), encoding="utf-8")

    pbids_path = EXPORTS_DIR / "AMOP_Dashboard.pbids"
    pbids_path.write_text(json.dumps({
        "version": "0.1", "connections": [{
            "details": {"protocol": "folder", "address": {"path": str(EXPORTS_DIR)}},
            "mode": "import",
        }],
    }, indent=2), encoding="utf-8")

    return {
        "csv_files": {k: str(v) for k, v in csv_files.items()},
        "twb_path": str(twb_path),
        "pbids_path": str(pbids_path),
        "exports_dir": str(EXPORTS_DIR),
    }


if __name__ == "__main__":
    result = generate_all()
    print("BI exports written:")
    for k, v in result.items():
        print(f"  {k}: {v}")
