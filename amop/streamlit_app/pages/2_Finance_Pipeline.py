import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import data_issue_banner, explain_this, get_cash_book

from alluvial_mcp.core.finance import (
    DEFAULT_CHANNELS, FRAUD_FLAGS, adjudicate_prospect_introduction, compute_risk_class,
    optimize_weekly_hours, run_stage_cost_simulation,
)

st.set_page_config(page_title="Finance & Pipeline", layout="wide")
st.title("Finance & Stakeholder Pipeline")
data_issue_banner(["DATA-10"] if False else None)

tab1, tab2, tab3, tab4 = st.tabs(["Cash Book", "Stage-Cost Pipeline", "Fraud Check / Prospect", "PSO Outreach Hours"])

with tab1:
    st.subheader("COMPREHENSIVE_FEEDING.xlsx -- Cash Book")
    cash = get_cash_book()
    st.metric("Opening balance", f"US$ {cash['opening_balance']:,.2f}")
    from alluvial_mcp.core.finance import compute_running_balance
    ledger = compute_running_balance(cash["opening_balance"], cash["entries"])
    rows = [{"Date": e["date"], "Description": e["description"], "Project": e["project_code"],
             "Category": e["category_code"], "Paid": e["cash_paid"], "Received": e["cash_received"],
             "Balance": e["balance"]} for e in ledger]
    st.dataframe(rows, use_container_width=True, height=400)
    explain_this("Running balance", "core.finance.compute_running_balance",
                 "H_n = H_{n-1} + F_n - G_n (docs/AMOP_MCP_SPEC.md 11.6)",
                 {"opening_balance": cash["opening_balance"], "n_entries": len(cash["entries"])})

with tab2:
    st.subheader("Guyana_Outreach_Cost_Pipeline_Workbook.xlsx -- 12-Stage Simulation")
    scenario = st.selectbox("Scenario", ["Low", "Base", "High"], index=1)
    sim = run_stage_cost_simulation(scenario)
    c1, c2, c3 = st.columns(3)
    c1.metric("Horizon (weeks)", f"{sim['horizon_weeks']:.1f}")
    c2.metric("Total planned cost", f"US$ {sim['total_planned_cost_usd']:,.0f}")
    c3.metric("With contingency", f"US$ {sim['total_with_contingency_usd']:,.0f}")
    st.dataframe(sim["stages"], use_container_width=True)

with tab3:
    st.subheader("Fraud_Check scorecard")
    st.caption("Any hard-stop flag (F01,F02,F08,F12,F13,F14,F15,F21) forces RED regardless of score.")
    cols = st.columns(4)
    flags = {}
    for i, f in enumerate(FRAUD_FLAGS):
        with cols[i % 4]:
            flags[f.flag_id] = st.checkbox(f"{f.flag_id}{' (H)' if f.hard_stop else ''}", key=f"flag_{f.flag_id}")
    risk = compute_risk_class(flags)
    st.metric("Risk score", f"{risk['risk_score']:.1f}%")
    if risk["risk_class"] == "RED":
        st.error(f"Risk class: RED (hard stops: {risk['hard_stop_flags']})")
    elif risk["risk_class"] == "AMBER":
        st.warning("Risk class: AMBER")
    else:
        st.success("Risk class: GREEN")

    st.markdown("---")
    n_verified = st.slider("Verification steps passed (of 12)", 0, 12, 10)
    verifications = {f"V{i:02d}": True for i in range(1, n_verified + 1)}
    decision = adjudicate_prospect_introduction(flags, verifications)
    if decision["decision"] == "ALLOW":
        st.success(f"Decision: ALLOW (completion {decision['verification_completion']*100:.0f}%)")
    else:
        st.error(f"Decision: DENY -- {decision['reason']}")

with tab4:
    st.subheader("PSO weekly outreach-hour allocation (seeded, deterministic)")
    weekly_hours = st.number_input("Weekly hours to allocate", value=40.0, step=1.0)
    if st.button("Run PSO optimizer"):
        with st.spinner("Running seeded pyswarms PSO..."):
            result = optimize_weekly_hours(weekly_hours=weekly_hours, seed=42)
        st.dataframe(result["allocation"], use_container_width=True)
        st.metric("Total expected leads/week", f"{result['total_expected_leads']:.2f}")
        st.metric("Uplift vs equal split", f"+{result['uplift_vs_equal_split']:.2f} leads/week")
        st.caption(f"Seed: {result['seed']} (re-run reproduces this exact result)")
