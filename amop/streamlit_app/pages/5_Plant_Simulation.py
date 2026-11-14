import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import data_issue_banner, explain_this

from alluvial_mcp.core.plant import (
    PitFeed, PlantParameters, compute_daily_energy_cost, compute_net_revenue, compute_recovered_oz,
    build_daily_blend, evaluate_plant_efficiency, total_connected_load_kw,
)

st.set_page_config(page_title="Plant Simulation", layout="wide")
st.title("Plant Simulation & Recovery")
data_issue_banner(["DATA-03"])

st.subheader("Plant parameters")
c1, c2, c3 = st.columns(3)
rpm_actual = c1.number_input("RPM actual", value=30.0)
rpm_optimal = c1.number_input("RPM optimal", value=32.0)
tilt_actual = c2.number_input("Tilt actual (deg)", value=8.0)
tilt_optimal = c2.number_input("Tilt optimal (deg)", value=12.0)
water_actual = c3.number_input("Water flow actual (m3/hr)", value=120.0)

p = PlantParameters(rpm_actual=rpm_actual, rpm_optimal=rpm_optimal, tilt_actual_deg=tilt_actual,
                     tilt_optimal_deg=tilt_optimal, water_flow_actual=water_actual)
eff = evaluate_plant_efficiency(p)

c1, c2, c3, c4 = st.columns(4)
c1.metric("RPM factor", f"{eff.rpm_factor:.3f}")
c2.metric("Tilt factor", f"{eff.tilt_factor:.3f}")
c3.metric("Overall efficiency", f"{eff.overall_efficiency:.4f}")
c4.metric("Effective recovery", f"{eff.effective_recovery:.4f}")

st.divider()
st.subheader("Daily blend")
pits = [
    PitFeed("PIT-01", 0.3, 1.5, 450, 229808, 697313),
    PitFeed("PIT-02", 0.8, 1.5, 300, 231293, 698263),
    PitFeed("PIT-03", 0.3, 1.5, 200, 231273, 698278),
    PitFeed("PIT-04", 0.2, 1.5, 1200, 231281, 698300),
    PitFeed("PIT-05", 0.6, 1.5, 300, 231265, 698313),
]
st.dataframe([{"Pit": p.pit_id, "Grade": p.grade_g_m3, "Volume (m3)": p.available_volume_m3} for p in pits],
             use_container_width=True)

strategy = st.selectbox("Blend strategy", ["grade", "distance", "composite", "holistic"], index=3)
target_m3 = st.number_input("Target blend volume (m3)", value=950.0)
blend = build_daily_blend(pits, eff, target_m3, strategy, plant_x=229400, plant_y=697300)

c1, c2 = st.columns(2)
c1.metric("Total volume achieved (m3)", f"{blend.total_volume_m3:.0f}")
c2.metric("Weighted avg grade (g/m3)", f"{blend.weighted_avg_grade_g_m3:.4f}")
if not blend.feasible:
    st.error("; ".join(blend.blocking_reasons))
st.dataframe([{"Pit": l.pit_id, "Volume (m3)": l.volume_m3, "Grade": l.grade_g_m3} for l in blend.lines],
             use_container_width=True)

st.divider()
st.subheader("Energy & revenue")
load_kw = total_connected_load_kw()
energy_rate = st.number_input("Energy rate as entered ($/kWh)", value=12.0)
energy = compute_daily_energy_cost(load_kw, p.operating_hours, energy_rate)
if energy["data_issue"]:
    st.warning(f"DATA_ISSUE {energy['data_issue']['id']}: rate entered as {energy['data_issue']['value_found']}, "
               f"recommended {energy['data_issue']['recommended_value']}. Both figures shown below -- neither is silently substituted.")
c1, c2 = st.columns(2)
c1.metric("Daily energy cost (as entered)", f"US$ {energy['daily_cost_as_entered_usd']:,.2f}")
c2.metric("Daily energy cost (corrected 0.12)", f"US$ {energy['daily_cost_corrected_usd']:,.2f}")

recovered_oz = compute_recovered_oz(blend.contained_gold_g, eff.effective_recovery)
gold_price = st.number_input("Gold price ($/oz)", value=4050.0)
gross = recovered_oz * gold_price
net = compute_net_revenue(gross, energy["daily_cost_as_entered_usd"], 0.0)
c1, c2, c3 = st.columns(3)
c1.metric("Recovered gold (oz)", f"{recovered_oz:.3f}")
c2.metric("Gross revenue", f"US$ {gross:,.2f}")
c3.metric("Net revenue after energy", f"US$ {net['net_revenue_after_energy_usd']:,.2f}")

explain_this("Plant efficiency", "core.plant.evaluate_plant_efficiency",
             "Overall = Setup x RPM_factor x Tilt_factor x Water_factor (docs/AMOP_MCP_SPEC.md 11.4)",
             {"setup_efficiency": p.setup_efficiency, "rpm_factor": eff.rpm_factor, "tilt_factor": eff.tilt_factor})
