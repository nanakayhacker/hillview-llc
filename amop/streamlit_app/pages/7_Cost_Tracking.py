import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import explain_this, get_campaign_budget, get_campaign_vouchers, get_trommel_bom

from alluvial_mcp.core.cost_tracking import (
    COST_CODE_TAXONOMY, CampSizingAssumptions, Voucher, estimate_camp_requirements,
    evaluate_tranche_release, required_approval_level, rollup_bom_total, rollup_budget_by_phase,
    summarize_vouchers, validate_voucher,
)

st.set_page_config(page_title="Cost Tracking", layout="wide")
st.title("Exploration & Operations Cost Tracking")
st.caption(
    "Systematic, sequential cost-code taxonomy: EXPLORATION -> MINING_OPERATIONS -> "
    "PLANT_PROCESSING -> CAMP_DEVELOPMENT -> HSE_ADMIN -> CONTINGENCY."
)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Cost Code Taxonomy", "Budget Rollup", "Voucher Validation", "Trommel BOM", "Camp Sizing (140 pax)"]
)

with tab1:
    st.dataframe([{"Code": c.code, "Phase": c.phase, "Category": c.name} for c in COST_CODE_TAXONOMY],
                 use_container_width=True, height=600)

with tab2:
    budget = get_campaign_budget()
    phases = rollup_budget_by_phase(budget)
    cols = st.columns(len(phases) or 1)
    for col, (phase, v) in zip(cols, phases.items()):
        col.metric(phase, f"US$ {v['planned_bac_usd']:,.0f}", f"{v['pct_consumed']*100:.0f}% consumed")
    for phase, v in phases.items():
        with st.expander(f"{phase} -- {len(v['lines'])} line(s)"):
            st.dataframe([{"Cost code": l.cost_code, "Category": l.category, "Planned": l.planned_bac_usd,
                           "Actual": l.actual_validated_usd, "Variance": l.variance_usd,
                           "% consumed": f"{l.pct_consumed*100:.1f}%"} for l in v["lines"]],
                         use_container_width=True)
    st.markdown("---")
    st.subheader("Tranche release gates")
    gates = {}
    cols = st.columns(4)
    for i, g in enumerate(["T0", "A", "B", "C"]):
        gates[g] = cols[i].checkbox(f"Gate {g} passed" if g != "T0" else "T0: baseline approved", key=f"gate_{g}")
    st.dataframe(evaluate_tranche_release(gates), use_container_width=True)

with tab3:
    st.subheader("Loaded vouchers (Alluvial_Campaign_Control_Workbook_Guyana.xlsx)")
    vouchers = get_campaign_vouchers()
    if vouchers:
        summary = summarize_vouchers(vouchers)
        c1, c2 = st.columns(2)
        c1.metric("Valid total", f"US$ {summary['valid_total_usd']:,.0f}")
        c2.metric("On hold total", f"US$ {summary['hold_total_usd']:,.0f}")
        st.dataframe([{"Voucher": v.voucher_id, "Amount": v.amount_usd, "Status": r["status"],
                       "Hold reasons": "; ".join(r["hold_reasons"])}
                      for v, r in zip(vouchers, summary["results"])], use_container_width=True)
    st.markdown("---")
    st.subheader("Validate a new voucher")
    c1, c2, c3 = st.columns(3)
    amount = c1.number_input("Amount (US$)", value=1000.0)
    cost_code = c2.selectbox("Cost code", [c.code for c in COST_CODE_TAXONOMY])
    approval = c3.number_input("Approval level given", 1, 3, 1)
    inv = st.checkbox("Has invoice", True)
    po = st.checkbox("Has contract/PO", True)
    receipt = st.checkbox("Has receipt/acceptance", True)
    tax = st.checkbox("Has tax reference", True)
    st.info(f"Required approval level for US$ {amount:,.0f}: {required_approval_level(amount)}")
    if st.button("Validate voucher"):
        v = Voucher("NEW", None, cost_code, "payee", "desc", amount, inv, po, receipt, tax, int(approval))
        result = validate_voucher(v)
        st.success(result) if result["status"] == "VALID" else st.error(result)

with tab4:
    bom = get_trommel_bom()
    if bom:
        rollup = rollup_bom_total(bom)
        c1, c2 = st.columns(2)
        c1.metric("Total BOM cost", f"US$ {rollup['total_usd']:,.0f}")
        c2.metric("Quoted lines", f"{rollup['quoted_count']} / {rollup['total_lines']}")
        st.dataframe([{"ID": b.component_id, "Assembly": b.assembly, "Component": b.component,
                       "Qty": b.qty, "Unit": b.unit, "Unit cost": b.unit_cost_usd, "Status": b.status}
                      for b in bom], use_container_width=True, height=400)

with tab5:
    headcount = st.number_input("Headcount", value=140, step=10)
    camp = estimate_camp_requirements(CampSizingAssumptions(headcount=int(headcount)))
    c1, c2, c3 = st.columns(3)
    c1.metric("Housing area (m2)", f"{camp['housing_m2']:,.0f}")
    c2.metric("Office area (m2)", f"{camp['office_m2']:,.0f}")
    c3.metric("Recommended generator (kW)", f"{camp['recommended_generator_kw']:,.0f}")
    st.caption(camp["note"])
    explain_this("Camp sizing", "core.cost_tracking.estimate_camp_requirements",
                 "Structured placeholder sizing, not an engineering design.", camp)
