import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import get_pit_composites, verdict_badge

from alluvial_mcp.core.adjudication import Severity, adjudicate_full_chain

st.set_page_config(page_title="Adjudication", layout="wide")
st.title("Cross-Module Adjudication -- Full Chain Verdict")
st.caption("Runs R-1.1 through R-1.4 in order. The verdict JSON is explained, never re-derived.")

composites = get_pit_composites()

st.subheader("Inputs")
c1, c2 = st.columns(2)
with c1:
    pit_shares_and_z = {}
    for pit_id, c in composites.items():
        share = st.slider(f"{pit_id} blend share", 0.0, 1.0, 0.25, 0.05, key=f"share_{pit_id}")
        pit_shares_and_z[pit_id] = (share, c.z_credibility)
    daily_energy_cost = st.number_input("Daily energy cost (US$)", value=48576.0)
    gross_revenue = st.number_input("Gross revenue (US$)", value=48402.95)
with c2:
    runway_weeks = st.number_input("Cash runway (weeks)", value=3.1)
    blend_target_m3 = st.number_input("Blend target (m3)", value=950.0)
    include_pipeline = st.checkbox("Include pipeline (cash runway) rule", True)

if st.button("Run adjudicate_full_chain"):
    verdict = adjudicate_full_chain(
        pit_shares_and_z=pit_shares_and_z, stockpile_deficits={}, compatibility={},
        daily_energy_cost_usd=daily_energy_cost, gross_revenue_usd=gross_revenue,
        runway_weeks=runway_weeks, blend_target_m3=blend_target_m3, include_pipeline=include_pipeline,
    )
    st.session_state["adjudication_verdict"] = {"verdict": verdict.verdict}

    verdict_badge(verdict.verdict)
    st.subheader("Rule tree")
    for r in verdict.tree:
        icon = "PASS" if r.passed else f"FAIL ({r.severity.value})"
        with st.expander(f"{r.rule_id} {r.name} -- {icon}"):
            st.json({"actual": r.actual, "expected": r.expected, "blocking_reason": r.blocking_reason})
    if verdict.blocking_reasons:
        st.error("Blocking: " + "; ".join(verdict.blocking_reasons))
    if verdict.recommended_actions:
        st.subheader("Recommended actions")
        for a in verdict.recommended_actions:
            st.markdown(f"- {a}")
