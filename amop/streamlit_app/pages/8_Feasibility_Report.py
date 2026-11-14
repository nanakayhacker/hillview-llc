import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import explain_this, get_pit_composites

from alluvial_mcp.core.feasibility import (
    FeasibilityAssumptions, SCOPE_DISCLAIMER, build_sensitivity_grid, classify_resource_prototype,
    run_feasibility_model,
)

st.set_page_config(page_title="Feasibility Report", layout="wide")
st.title("Alluvial Project Feasibility Report")
st.warning(SCOPE_DISCLAIMER)

tab1, tab2, tab3 = st.tabs(["Resource Classification (prototype)", "DCF / NPV / IRR", "Sensitivity"])

with tab1:
    st.caption("Prototype confidence mapping from the grade engine's Z-credibility -- "
               "not a JORC Code or NI 43-101 classification.")
    composites = get_pit_composites()
    rows = []
    for pit_id, c in composites.items():
        cls = classify_resource_prototype(pit_id, c.z_credibility, qaqc_pass=True,
                                           class_vs_cutoff=c.class_vs_cutoff)
        rows.append({"Pit": pit_id, "Grade (g/m3)": round(c.grade_g_m3, 5), "Z": round(c.z_credibility, 3),
                     "Resource category": cls.resource_category, "Reserve category": cls.reserve_category,
                     "Rationale": cls.rationale})
    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("No panning log data available.")

with tab2:
    st.subheader("Assumptions")
    c1, c2, c3 = st.columns(3)
    gold_price = c1.number_input("Gold price ($/oz)", value=4500.0)
    royalty = c1.number_input("Royalty rate", value=0.05, step=0.01)
    head_grade = c1.number_input("Head grade (g/m3)", value=0.2, step=0.01)
    recovery = c2.number_input("Metallurgical recovery", value=0.75, step=0.01)
    feed_rate = c2.number_input("Feed rate (m3/hr)", value=43.0)
    op_hours = c2.number_input("Operating hours/day", value=22.0)
    op_days = c3.number_input("Operating days/year", value=240.0)
    availability = c3.number_input("Availability factor", value=0.85, step=0.01)
    opex = c3.number_input("Operating cost ($/m3)", value=12.0)

    a = FeasibilityAssumptions(gold_price_usd_oz=gold_price, royalty_rate=royalty, head_grade_g_m3=head_grade,
                                metallurgical_recovery=recovery, feed_rate_m3_hr=feed_rate,
                                operating_hours_per_day=op_hours, operating_days_per_year=op_days,
                                availability_factor=availability, operating_cost_usd_m3=opex)
    result = run_feasibility_model(a)
    e = result.annual_economics

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Material processed (m3/yr)", f"{e.material_processed_m3_yr:,.0f}")
    c2.metric("Recovered gold (oz/yr)", f"{e.recovered_gold_oz_yr:,.1f}")
    c3.metric("Gross revenue ($/yr)", f"US$ {e.gross_revenue_usd_yr:,.0f}")
    c4.metric("EBITDA ($/yr)", f"US$ {e.ebitda_usd_yr:,.0f}")

    c1, c2, c3 = st.columns(3)
    c1.metric("NPV", f"US$ {result.npv_usd:,.0f}")
    c2.metric("IRR", f"{result.irr*100:.1f}%" if result.irr else "N/A")
    c3.metric("Payback (years)", result.payback_years if result.payback_years is not None else "N/A")

    st.caption(f"Operating break-even grade: {e.operating_breakeven_grade_g_m3:.4f} g/m3 | "
               f"All-in break-even grade: {e.all_in_breakeven_grade_g_m3:.4f} g/m3")

    st.subheader("Cash flow schedule")
    cf_rows = [{"Year": cf.year, "EBITDA": cf.ebitda_usd, "Depreciation": cf.depreciation_usd,
               "Tax": cf.tax_usd, "Capex": cf.capex_usd, "FCF": cf.free_cash_flow_usd,
               "Cumulative": cf.cumulative_usd} for cf in result.cash_flows]
    st.dataframe(cf_rows, use_container_width=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=[r["Year"] for r in cf_rows], y=[r["FCF"] for r in cf_rows], name="FCF"))
    fig.add_trace(go.Scatter(x=[r["Year"] for r in cf_rows], y=[r["Cumulative"] for r in cf_rows],
                              name="Cumulative", mode="lines+markers"))
    fig.update_layout(title="Free cash flow and cumulative position", height=400)
    st.plotly_chart(fig, use_container_width=True)

    explain_this("DCF model", "core.feasibility.run_feasibility_model",
                 "Verified bit-for-bit against Alluvial_Campaign_Control_Workbook_Guyana.xlsx!Feasibility",
                 {"total_initial_capex_usd": e.total_initial_capex_usd})

with tab3:
    st.subheader("NPV sensitivity: head grade x gold price")
    grades = [0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5]
    prices = [3000, 3500, 4000, 4500, 5000]
    grid = build_sensitivity_grid(FeasibilityAssumptions(), grades, prices)
    fig = go.Figure(data=go.Heatmap(z=grid["npv_grid_usd"], x=[str(p) for p in prices],
                                     y=[str(g) for g in grades], colorscale="RdYlGn",
                                     colorbar={"title": "NPV ($)"}))
    fig.update_layout(title="NPV ($) by head grade (rows) and gold price (columns)",
                       xaxis_title="Gold price ($/oz)", yaxis_title="Head grade (g/m3)", height=450)
    st.plotly_chart(fig, use_container_width=True)
