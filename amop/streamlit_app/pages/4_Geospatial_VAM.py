import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import data_issue_banner, explain_this, get_cost_grade_vam

from alluvial_mcp.core.vam import (
    HeuristicParameters, adjudicate_vam_solution, build_heuristic_matrix,
    compute_naive_proportional_baseline, compute_vam_savings, solve_vam,
)

st.set_page_config(page_title="Geospatial VAM", layout="wide")
st.title("Geospatial Grade-Controlled VAM & Stockpile Optimization")
data_issue_banner(["DATA-06", "DATA-11"])

data = get_cost_grade_vam()
if not data.get("pit_ids"):
    st.warning("No pit/distance/cost data found at data/workbooks/Cost_Grade_Heuristic_Prioritized_VAM_Cost_MATRIX.xlsx")
else:
    pit_ids, grades = data["pit_ids"], data["grades"]
    stockpile_ids, distance_matrix, cost_matrix = data["stockpile_ids"], data["distance_matrix"], data["cost_matrix"]

    st.subheader("Pit registry")
    st.dataframe([{"Pit": p, "Grade": g} for p, g in zip(pit_ids, grades)], use_container_width=True)

    with st.expander("Heuristic parameters"):
        c1, c2, c3 = st.columns(3)
        lam = c1.slider("Lambda (grade-penalty strength)", 0.0, 2.0, 0.5, 0.1)
        theta = c2.slider("Theta (max spatial adjustment)", 0.0, 0.5, 0.3, 0.05)
        alpha = c3.slider("Alpha (grade sensitivity)", 0.5, 2.0, 1.0, 0.1)

    params = HeuristicParameters(alpha=alpha, lam=lam, theta=theta)
    out = build_heuristic_matrix(cost_matrix, grades, distance_matrix, params)
    h = out["H"]

    st.subheader("Bounded heuristic cost matrix H(i,j)")
    st.dataframe(
        [{"Pit": pit_ids[i], **{stockpile_ids[j]: round(h[i][j], 2) for j in range(len(stockpile_ids))}}
         for i in range(len(pit_ids))],
        use_container_width=True,
    )
    explain_this("Heuristic matrix", "core.vam.build_heuristic_matrix",
                 "H(i,j) = C(i,j) * GP(i) * SM(i,j), bounded to [C*(1-theta), C*GP_max*(1+theta)] "
                 "(docs/AMOP_MCP_SPEC.md 11.2). Verified against Heuristic Calculation, not the "
                 "workbook's stale Verification sheet -- see README.",
                 {"GPF": out["GPF"], "GP": out["GP"]})

    st.subheader("Supply / demand and VAM solve")
    supply = [st.number_input(f"{pit_ids[i]} supply (m3)", value=450.0, key=f"sup_{i}") for i in range(len(pit_ids))]
    demand = [st.number_input(f"{stockpile_ids[j]} demand (m3)", value=500.0, key=f"dem_{j}") for j in range(len(stockpile_ids))]

    if st.button("Solve VAM"):
        res = solve_vam(h, supply, demand, pit_ids, stockpile_ids)
        naive = compute_naive_proportional_baseline(supply, demand, h)
        savings = compute_vam_savings(res.total_cost, naive["total_cost"])
        verdict = adjudicate_vam_solution(res.allocation, supply, demand)

        c1, c2, c3 = st.columns(3)
        c1.metric("VAM total cost", f"US$ {res.total_cost:,.2f}")
        c2.metric("Naive baseline cost", f"US$ {naive['total_cost']:,.2f}")
        c3.metric("Savings", f"US$ {savings['savings_usd']:,.2f} ({savings['savings_pct']*100:.1f}%)")

        st.success(verdict["verdict"]) if verdict["verdict"] == "VAM_ACCEPTED" else st.error(verdict["verdict"])
        st.caption(res.balance_note)

        st.subheader("Allocation")
        st.dataframe(
            [{"Pit": pit_ids[i], **{stockpile_ids[j]: round(res.allocation[i][j], 1) for j in range(len(stockpile_ids))}}
             for i in range(len(pit_ids))],
            use_container_width=True,
        )

        with st.expander("VAM iteration audit log"):
            st.dataframe([{
                "Iter": it.iteration, "Type": it.selected_type, "Penalty": round(it.penalty, 2),
                "Source": it.source, "Dest": it.destination, "Qty": it.qty_allocated,
                "Unit cost": round(it.unit_cost, 2), "Subtotal": round(it.subtotal, 2),
            } for it in res.iterations], use_container_width=True)
