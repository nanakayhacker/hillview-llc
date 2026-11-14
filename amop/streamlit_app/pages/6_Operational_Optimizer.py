import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import explain_this

from alluvial_mcp.core.vam import euclidean_distance_matrix, build_haul_cost_matrix, solve_vam, compute_naive_proportional_baseline, compute_vam_savings

st.set_page_config(page_title="Operational Optimizer", layout="wide")
st.title("Operational Optimization -- Zone/Destination VAM Transport")
st.caption("Operational_Optimization_Template.xlsx: 4 mining zones -> 3 destinations, haul-cost VAM.")

ZONES = [("Zone 1", 583185.67, 634469.63, 62477), ("Zone 2", 583626.14, 634915.45, 51697),
         ("Zone 3", 583421.50, 634210.25, 12500), ("Zone 4", 583204.77, 634533.77, 53597)]
DESTS = [("Primary Processing Plant", 583405.91, 634139.73, 99149),
         ("ROM Stockpile", 583714.24, 634774.41, 45068),
         ("Waste Rock Dump", 583097.58, 634844.93, 36054)]

rate_per_km = st.number_input("Haul rate ($/unit-volume per km)", value=0.05, step=0.01)

sources = [(z[1], z[2]) for z in ZONES]
destinations = [(d[1], d[2]) for d in DESTS]
dist = euclidean_distance_matrix(sources, destinations)
cost = build_haul_cost_matrix(dist, rate_per_km)

supply = [z[3] for z in ZONES]
demand = [d[3] for d in DESTS]

st.dataframe([{"Zone": ZONES[i][0], **{DESTS[j][0]: round(cost[i][j], 2) for j in range(3)}} for i in range(4)],
             use_container_width=True)

if st.button("Solve zone-transport VAM"):
    res = solve_vam(cost, supply, demand, [z[0] for z in ZONES], [d[0] for d in DESTS])
    naive = compute_naive_proportional_baseline(supply, demand, cost)
    savings = compute_vam_savings(res.total_cost, naive["total_cost"])
    c1, c2, c3 = st.columns(3)
    c1.metric("VAM cost", f"US$ {res.total_cost:,.0f}")
    c2.metric("Naive cost", f"US$ {naive['total_cost']:,.0f}")
    c3.metric("Savings", f"US$ {savings['savings_usd']:,.0f} ({savings['savings_pct']*100:.1f}%)")
    st.dataframe([{"Zone": ZONES[i][0], **{DESTS[j][0]: round(res.allocation[i][j], 0) for j in range(3)}}
                  for i in range(4)], use_container_width=True)

explain_this("Zone VAM", "core.vam.solve_vam", "Same Vogel's Approximation Method engine as Geospatial_VAM, "
             "applied to the Operational_Optimization_Template.xlsx zone/destination problem.",
             {"supply": supply, "demand": demand})
