"""AMOP -- Alluvial Mining Operations Platform. Main entry / Dashboard."""
import streamlit as st

from common import (
    data_issue_banner, get_campaign_budget, get_campaign_vouchers, get_cash_book,
    get_cost_grade_vam, get_pit_composites, verdict_badge,
)

st.set_page_config(page_title="AMOP Dashboard", layout="wide")

st.title("Alluvial Mining Operations Platform")
st.caption(
    "Planning and decision-support platform. Not a resource/reserve statement, JORC/NI 43-101 "
    "declaration, or legal opinion. Every number on this page comes from a deterministic "
    "core/ function -- never arithmetic typed into a prompt."
)

data_issue_banner()

col1, col2, col3, col4 = st.columns(4)

cash = get_cash_book()
with col1:
    st.metric("Cash balance (opening + ledger)", f"US$ {cash['opening_balance']:,.2f}",
               help="COMPREHENSIVE_FEEDING.xlsx!CASH BOOK, running balance formula")

composites = get_pit_composites()
with col2:
    n_above = sum(1 for c in composites.values() if c.class_vs_cutoff == "ABOVE CUT-OFF")
    st.metric("Pits above cut-off grade", f"{n_above} / {len(composites)}")

vam_data = get_cost_grade_vam()
with col3:
    st.metric("Pits registered (geospatial)", len(vam_data.get("pit_ids", [])))

budget = get_campaign_budget()
with col4:
    total_bac = sum(b.planned_bac_usd for b in budget)
    st.metric("Total planned budget (BAC)", f"US$ {total_bac:,.0f}")

st.divider()

left, right = st.columns(2)
with left:
    st.subheader("Pit grade overview")
    rows = [
        {"Pit": pid, "Grade (g/m3)": c.grade_g_m3, "Z credibility": c.z_credibility,
         "Class": c.class_vs_cutoff, "Panned ore thickness (m)": c.panned_ore_thickness_m}
        for pid, c in composites.items()
    ]
    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("No panning log data found in data/workbooks/Refined_Au_Grade_Model.xlsx")

with right:
    st.subheader("Budget by phase")
    from alluvial_mcp.core.cost_tracking import rollup_budget_by_phase
    phases = rollup_budget_by_phase(budget)
    phase_rows = [
        {"Phase": p, "Planned (BAC)": v["planned_bac_usd"], "Actual": v["actual_validated_usd"],
         "% consumed": f"{v['pct_consumed']*100:.1f}%"}
        for p, v in phases.items()
    ]
    if phase_rows:
        st.dataframe(phase_rows, use_container_width=True)

st.divider()
st.subheader("Worst adjudication verdict across pages")
worst = st.session_state.get("adjudication_verdict")
if worst:
    verdict_badge(worst.get("verdict", "N/A"))
else:
    st.info("No adjudication has run yet this session. Visit the Adjudication page.")

st.divider()
st.markdown(
    "**Pages:** Finance & Pipeline · Grade Control · Geospatial VAM · Plant Simulation · "
    "Operational Optimizer · Cost Tracking · Feasibility Report · Adjudication · BI Exports"
)
