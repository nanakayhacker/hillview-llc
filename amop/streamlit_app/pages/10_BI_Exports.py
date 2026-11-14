import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common import get_campaign_budget, get_pit_composites

from scripts.generate_bi_exports import generate_all

st.set_page_config(page_title="BI Exports & Dashboard", layout="wide")
st.title("Alluvial Prospecting Dashboard & BI Exports")
st.caption(
    "Tableau Desktop and Power BI Desktop are licensed GUI applications -- this page cannot "
    "install or activate them. It prepares CSV extracts plus a ready-to-open .twb/.pbids file "
    "for whichever is already installed, and always gives you this built-in dashboard, which "
    "needs no license at all."
)

st.subheader("Built-in dashboard (no license required)")
composites = get_pit_composites()
budget = get_campaign_budget()

col1, col2 = st.columns(2)
with col1:
    if composites:
        df = pd.DataFrame([{"Pit": pid, "Grade (g/m3)": c.grade_g_m3, "Z": c.z_credibility,
                            "Class": c.class_vs_cutoff} for pid, c in composites.items()])
        fig = px.bar(df, x="Pit", y="Grade (g/m3)", color="Class", title="Pit grades vs cut-off")
        st.plotly_chart(fig, use_container_width=True)
with col2:
    if budget:
        from alluvial_mcp.core.cost_tracking import rollup_budget_by_phase
        phases = rollup_budget_by_phase(budget)
        df2 = pd.DataFrame([{"Phase": p, "Planned": v["planned_bac_usd"], "Actual": v["actual_validated_usd"]}
                            for p, v in phases.items()])
        if not df2.empty:
            fig2 = px.bar(df2, x="Phase", y=["Planned", "Actual"], barmode="group",
                          title="Budget planned vs actual by phase")
            st.plotly_chart(fig2, use_container_width=True)

st.divider()
st.subheader("Generate Tableau / Power BI exports")
if st.button("Generate BI exports now"):
    with st.spinner("Writing CSV extracts, .twb and .pbids..."):
        result = generate_all()
    st.success(f"Exports written to {result['exports_dir']}")
    st.json(result)
    st.markdown(
        "**To open in Tableau Desktop:** double-click `AMOP_Dashboard.twb` in that folder "
        "(or File > Open in Tableau).\n\n"
        "**To open in Power BI Desktop:** double-click `AMOP_Dashboard.pbids` -- Power BI will "
        "prompt to load the CSVs in that folder."
    )
else:
    st.info("Click the button to (re)generate the CSV/.twb/.pbids files from the latest data.")
